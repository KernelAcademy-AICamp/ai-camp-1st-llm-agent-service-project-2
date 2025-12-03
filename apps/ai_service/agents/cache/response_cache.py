"""
Response Cache - Redis 기반 응답 캐싱

Phase 5: Adaptive Agent - 캐싱 전략

기능:
- 조직별 캐시 키 분리 (멀티테넌시)
- TTL 기반 자동 만료
- 캐시 히트율 메트릭
"""

from typing import Optional, Dict, Any
from datetime import datetime
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# 캐시 설정
# =============================================================================

class CacheConfig:
    """캐시 설정"""

    # TTL (초)
    TTL_FAST_PATH = 3600       # 1시간 - 일반 대화, 단순 질문
    TTL_MEDIUM_PATH = 1800     # 30분 - 문서 분석 등
    TTL_DEEP_PATH = 900        # 15분 - 복합 분석 (자주 변경 가능)

    # 캐시 키 prefix
    KEY_PREFIX = "agent_hub:response"

    # 최대 캐시 크기 (문자)
    MAX_RESPONSE_SIZE = 50000


# =============================================================================
# 캐시 키 생성
# =============================================================================

def generate_cache_key(
    user_message: str,
    organization_id: Optional[str] = None,
    attachments: Optional[list] = None,
) -> str:
    """
    캐시 키 생성

    형식: {prefix}:{org_id}:{content_hash}

    Args:
        user_message: 사용자 메시지
        organization_id: 조직 ID (멀티테넌시)
        attachments: 첨부 파일 목록 (파일명만 해시에 포함)

    Returns:
        캐시 키 문자열
    """
    # 메시지 정규화
    normalized_message = user_message.strip().lower()

    # 첨부 파일명 추가 (있는 경우)
    attachment_str = ""
    if attachments:
        filenames = sorted([a.get("filename", "") for a in attachments])
        attachment_str = ":".join(filenames)

    # 해시 생성
    content = f"{normalized_message}:{attachment_str}"
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    # 조직 ID prefix
    org_prefix = organization_id if organization_id else "default"

    return f"{CacheConfig.KEY_PREFIX}:{org_prefix}:{content_hash}"


# =============================================================================
# ResponseCache 클래스
# =============================================================================

class ResponseCache:
    """
    응답 캐시

    Redis를 사용한 응답 캐싱을 제공합니다.

    사용 예시:
        cache = ResponseCache()

        # 캐시 확인
        cached = await cache.get(key)
        if cached:
            return cached

        # 응답 저장
        await cache.set(key, response, path="fast")
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        ResponseCache 초기화

        Args:
            redis_url: Redis URL (없으면 설정에서 가져옴)
        """
        self._redis = None
        self._redis_url = redis_url
        self._connected = False

        # 메트릭
        self._hits = 0
        self._misses = 0

    async def _ensure_connection(self):
        """Redis 연결 확인/생성"""
        if self._connected and self._redis:
            return

        try:
            import redis.asyncio as aioredis
            from apps.ai_service.config.settings import settings

            url = self._redis_url or settings.REDIS_URI
            self._redis = aioredis.from_url(url, decode_responses=True)
            self._connected = True
            logger.info(f"[ResponseCache] Connected to Redis: {url}")

        except Exception as e:
            logger.warning(f"[ResponseCache] Redis connection failed: {e}")
            self._connected = False

    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        캐시에서 응답 조회

        Args:
            cache_key: 캐시 키

        Returns:
            캐시된 응답 또는 None
        """
        try:
            await self._ensure_connection()

            if not self._redis:
                return None

            data = await self._redis.get(cache_key)

            if data:
                self._hits += 1
                logger.debug(f"[ResponseCache] Cache hit: {cache_key[:30]}...")
                return json.loads(data)
            else:
                self._misses += 1
                logger.debug(f"[ResponseCache] Cache miss: {cache_key[:30]}...")
                return None

        except Exception as e:
            logger.warning(f"[ResponseCache] Get failed: {e}")
            self._misses += 1
            return None

    async def set(
        self,
        cache_key: str,
        response: str,
        path: str = "fast",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        응답을 캐시에 저장

        Args:
            cache_key: 캐시 키
            response: 응답 텍스트
            path: 경로 ("fast", "medium", "deep")
            metadata: 추가 메타데이터

        Returns:
            저장 성공 여부
        """
        try:
            await self._ensure_connection()

            if not self._redis:
                return False

            # 크기 확인
            if len(response) > CacheConfig.MAX_RESPONSE_SIZE:
                logger.warning(f"[ResponseCache] Response too large to cache: {len(response)}")
                return False

            # TTL 결정
            ttl_map = {
                "fast": CacheConfig.TTL_FAST_PATH,
                "medium": CacheConfig.TTL_MEDIUM_PATH,
                "deep": CacheConfig.TTL_DEEP_PATH,
            }
            ttl = ttl_map.get(path, CacheConfig.TTL_FAST_PATH)

            # 저장 데이터
            cache_data = {
                "response": response,
                "path": path,
                "cached_at": datetime.now().isoformat(),
                "metadata": metadata or {},
            }

            await self._redis.set(
                cache_key,
                json.dumps(cache_data, ensure_ascii=False),
                ex=ttl,
            )

            logger.debug(f"[ResponseCache] Cached: {cache_key[:30]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"[ResponseCache] Set failed: {e}")
            return False

    async def delete(self, cache_key: str) -> bool:
        """캐시 삭제"""
        try:
            await self._ensure_connection()
            if self._redis:
                await self._redis.delete(cache_key)
                return True
            return False
        except Exception as e:
            logger.warning(f"[ResponseCache] Delete failed: {e}")
            return False

    async def clear_organization(self, organization_id: str) -> int:
        """
        조직의 모든 캐시 삭제

        Args:
            organization_id: 조직 ID

        Returns:
            삭제된 키 수
        """
        try:
            await self._ensure_connection()
            if not self._redis:
                return 0

            pattern = f"{CacheConfig.KEY_PREFIX}:{organization_id}:*"
            keys = []
            async for key in self._redis.scan_iter(pattern):
                keys.append(key)

            if keys:
                await self._redis.delete(*keys)
                logger.info(f"[ResponseCache] Cleared {len(keys)} keys for org: {organization_id}")

            return len(keys)

        except Exception as e:
            logger.warning(f"[ResponseCache] Clear failed: {e}")
            return 0

    @property
    def hit_rate(self) -> float:
        """캐시 히트율"""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
            "connected": self._connected,
        }

    async def close(self):
        """Redis 연결 종료"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._connected = False


# =============================================================================
# 싱글톤
# =============================================================================

_cache_instance: Optional[ResponseCache] = None


def get_response_cache() -> ResponseCache:
    """ResponseCache 인스턴스 반환 (싱글톤)"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResponseCache()
    return _cache_instance
