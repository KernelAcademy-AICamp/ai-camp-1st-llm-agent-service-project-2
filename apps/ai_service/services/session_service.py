"""
Session Service - Redis 기반 세션 관리

Agent Hub의 사용자별 세션을 관리하는 서비스입니다.
설계 문서: docs/AGENT_HUB_BACKEND_INTEGRATION.md - 6. 세션 관리

주요 기능:
- 세션 생성/조회/삭제
- 세션 활동 업데이트 (TTL 연장)
- 워크플로우 실행 카운트 추적
- 사용자별 세션 목록 관리
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import redis
from loguru import logger

from apps.ai_service.config.settings import settings


class SessionService:
    """
    Redis 기반 사용자 세션 관리 서비스

    Redis Key 패턴:
    - session:{session_id} : 세션 데이터 (JSON)
    - user_sessions:{user_id} : 사용자의 세션 ID Set
    """

    def __init__(self):
        """Redis 클라이언트 초기화"""
        self._redis_client: Optional[redis.Redis] = None
        self._session_expire_seconds = settings.SESSION_EXPIRE_HOURS * 3600  # 12시간 기본

    @property
    def redis_client(self) -> redis.Redis:
        """지연 초기화된 Redis 클라이언트 반환"""
        if self._redis_client is None:
            try:
                self._redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD or None,
                    decode_responses=True,  # 문자열로 자동 디코딩
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                # 연결 테스트
                self._redis_client.ping()
                logger.info(f"Redis 연결 성공: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except redis.ConnectionError as e:
                logger.error(f"Redis 연결 실패: {e}")
                raise
        return self._redis_client

    def _get_session_key(self, session_id: str) -> str:
        """세션 Redis 키 생성"""
        return f"session:{session_id}"

    def _get_user_sessions_key(self, user_id: str) -> str:
        """사용자 세션 목록 Redis 키 생성"""
        return f"user_sessions:{user_id}"

    async def create_session(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        새 세션 생성

        Args:
            user_id: 사용자 UUID
            organization_id: 조직 UUID (선택)
            project_id: 프로젝트 UUID (선택)
            metadata: 추가 메타데이터 (선택)

        Returns:
            session_id: 생성된 세션 ID

        Raises:
            redis.ConnectionError: Redis 연결 실패 시
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "project_id": project_id,
            "created_at": now.isoformat(),
            "last_activity": now.isoformat(),
            "conversation_count": 0,
            "total_workflows_executed": 0,
            "metadata": metadata or {}
        }

        try:
            # Redis에 세션 저장 (TTL: 12시간)
            session_key = self._get_session_key(session_id)
            self.redis_client.setex(
                session_key,
                self._session_expire_seconds,
                json.dumps(session_data, ensure_ascii=False)
            )

            # 사용자별 세션 목록에 추가
            user_sessions_key = self._get_user_sessions_key(user_id)
            self.redis_client.sadd(user_sessions_key, session_id)
            # 사용자 세션 목록도 만료 설정 (7일)
            self.redis_client.expire(user_sessions_key, 7 * 24 * 3600)

            logger.info(f"세션 생성: session_id={session_id}, user_id={user_id}")
            return session_id

        except redis.RedisError as e:
            logger.error(f"세션 생성 실패: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 조회

        Args:
            session_id: 세션 UUID

        Returns:
            세션 데이터 딕셔너리 또는 None (만료/없음)
        """
        try:
            session_key = self._get_session_key(session_id)
            session_json = self.redis_client.get(session_key)

            if session_json:
                return json.loads(session_json)
            return None

        except redis.RedisError as e:
            logger.error(f"세션 조회 실패: session_id={session_id}, error={e}")
            return None

    async def update_session_activity(self, session_id: str) -> bool:
        """
        세션 활동 업데이트 (마지막 활동 시간 갱신 + TTL 연장)

        Args:
            session_id: 세션 UUID

        Returns:
            성공 여부
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"세션 없음 (업데이트 불가): session_id={session_id}")
                return False

            # 활동 시간 및 대화 카운트 업데이트
            session["last_activity"] = datetime.now().isoformat()
            session["conversation_count"] += 1

            # Redis 업데이트 (TTL 재설정)
            session_key = self._get_session_key(session_id)
            self.redis_client.setex(
                session_key,
                self._session_expire_seconds,
                json.dumps(session, ensure_ascii=False)
            )

            logger.debug(f"세션 활동 업데이트: session_id={session_id}")
            return True

        except redis.RedisError as e:
            logger.error(f"세션 활동 업데이트 실패: session_id={session_id}, error={e}")
            return False

    async def increment_workflow_count(
        self,
        session_id: str,
        count: int = 1
    ) -> bool:
        """
        워크플로우 실행 카운트 증가

        Args:
            session_id: 세션 UUID
            count: 증가량 (기본: 1)

        Returns:
            성공 여부
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"세션 없음 (워크플로우 카운트 불가): session_id={session_id}")
                return False

            session["total_workflows_executed"] += count
            session["last_activity"] = datetime.now().isoformat()

            session_key = self._get_session_key(session_id)
            self.redis_client.setex(
                session_key,
                self._session_expire_seconds,
                json.dumps(session, ensure_ascii=False)
            )

            logger.debug(
                f"워크플로우 카운트 증가: session_id={session_id}, "
                f"total={session['total_workflows_executed']}"
            )
            return True

        except redis.RedisError as e:
            logger.error(f"워크플로우 카운트 증가 실패: session_id={session_id}, error={e}")
            return False

    async def get_user_sessions(self, user_id: str) -> List[str]:
        """
        사용자의 모든 활성 세션 ID 조회

        Args:
            user_id: 사용자 UUID

        Returns:
            세션 ID 리스트
        """
        try:
            user_sessions_key = self._get_user_sessions_key(user_id)
            session_ids = self.redis_client.smembers(user_sessions_key)

            # 실제 존재하는 세션만 필터링 (만료된 세션 제거)
            valid_sessions = []
            for session_id in session_ids:
                session_key = self._get_session_key(session_id)
                if self.redis_client.exists(session_key):
                    valid_sessions.append(session_id)
                else:
                    # 만료된 세션은 목록에서 제거
                    self.redis_client.srem(user_sessions_key, session_id)

            return valid_sessions

        except redis.RedisError as e:
            logger.error(f"사용자 세션 조회 실패: user_id={user_id}, error={e}")
            return []

    async def get_user_sessions_detail(self, user_id: str) -> List[Dict[str, Any]]:
        """
        사용자의 모든 활성 세션 상세 정보 조회

        Args:
            user_id: 사용자 UUID

        Returns:
            세션 데이터 리스트
        """
        session_ids = await self.get_user_sessions(user_id)
        sessions = []

        for session_id in session_ids:
            session = await self.get_session(session_id)
            if session:
                sessions.append(session)

        # 마지막 활동 시간 기준 정렬 (최신순)
        sessions.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
        return sessions

    async def list_user_sessions(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        사용자의 세션 목록 페이지네이션 조회

        Args:
            user_id: 사용자 UUID
            project_id: 프로젝트 ID로 필터 (선택)
            page: 페이지 번호 (1부터 시작)
            page_size: 페이지 크기

        Returns:
            세션 목록과 페이지네이션 정보
        """
        try:
            # 모든 세션 상세 정보 조회
            all_sessions = await self.get_user_sessions_detail(user_id)

            # 프로젝트 ID로 필터링
            if project_id:
                all_sessions = [
                    s for s in all_sessions
                    if s.get("project_id") == project_id
                ]

            # 페이지네이션
            total = len(all_sessions)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_sessions = all_sessions[start_idx:end_idx]

            return {
                "sessions": paginated_sessions,
                "total": total,
                "page": page,
                "page_size": page_size
            }

        except redis.RedisError as e:
            logger.error(f"세션 목록 조회 실패: user_id={user_id}, error={e}")
            return {"sessions": [], "total": 0, "page": page, "page_size": page_size}

    async def update_session(
        self,
        session_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        세션 데이터 업데이트

        Args:
            session_id: 세션 UUID
            update_data: 업데이트할 필드들

        Returns:
            성공 여부
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"세션 없음 (업데이트 불가): session_id={session_id}")
                return False

            # 업데이트 적용
            for key, value in update_data.items():
                if key not in ["session_id", "user_id", "created_at"]:  # 보호 필드
                    session[key] = value

            session["updated_at"] = datetime.now().isoformat()

            # Redis 업데이트
            session_key = self._get_session_key(session_id)
            # 현재 TTL 유지
            current_ttl = self.redis_client.ttl(session_key)
            if current_ttl > 0:
                self.redis_client.setex(
                    session_key,
                    current_ttl,
                    json.dumps(session, ensure_ascii=False)
                )
            else:
                self.redis_client.setex(
                    session_key,
                    self._session_expire_seconds,
                    json.dumps(session, ensure_ascii=False)
                )

            logger.debug(f"세션 업데이트: session_id={session_id}, fields={list(update_data.keys())}")
            return True

        except redis.RedisError as e:
            logger.error(f"세션 업데이트 실패: session_id={session_id}, error={e}")
            return False

    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 UUID

        Returns:
            성공 여부
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"세션 없음 (삭제 불가): session_id={session_id}")
                return False

            user_id = session.get("user_id")

            # 세션 데이터 삭제
            session_key = self._get_session_key(session_id)
            self.redis_client.delete(session_key)

            # 대화 기록 삭제 (conversation:{session_id})
            conversation_key = f"conversation:{session_id}"
            self.redis_client.delete(conversation_key)

            # 사용자 세션 목록에서 제거
            if user_id:
                user_sessions_key = self._get_user_sessions_key(user_id)
                self.redis_client.srem(user_sessions_key, session_id)

            logger.info(f"세션 삭제: session_id={session_id}")
            return True

        except redis.RedisError as e:
            logger.error(f"세션 삭제 실패: session_id={session_id}, error={e}")
            return False

    async def extend_session(
        self,
        session_id: str,
        additional_hours: int = 12
    ) -> bool:
        """
        세션 만료 시간 연장

        Args:
            session_id: 세션 UUID
            additional_hours: 연장 시간 (시간 단위)

        Returns:
            성공 여부
        """
        try:
            session_key = self._get_session_key(session_id)

            # 현재 TTL 확인
            current_ttl = self.redis_client.ttl(session_key)
            if current_ttl < 0:
                logger.warning(f"세션 없음 또는 만료됨: session_id={session_id}")
                return False

            # TTL 연장
            new_ttl = current_ttl + (additional_hours * 3600)
            self.redis_client.expire(session_key, new_ttl)

            logger.info(
                f"세션 만료 연장: session_id={session_id}, "
                f"new_ttl={new_ttl//3600}시간"
            )
            return True

        except redis.RedisError as e:
            logger.error(f"세션 연장 실패: session_id={session_id}, error={e}")
            return False

    async def cleanup_expired_sessions(self, user_id: str) -> int:
        """
        만료된 세션 정리

        Args:
            user_id: 사용자 UUID

        Returns:
            정리된 세션 수
        """
        try:
            user_sessions_key = self._get_user_sessions_key(user_id)
            session_ids = self.redis_client.smembers(user_sessions_key)

            cleaned = 0
            for session_id in session_ids:
                session_key = self._get_session_key(session_id)
                if not self.redis_client.exists(session_key):
                    self.redis_client.srem(user_sessions_key, session_id)
                    cleaned += 1

            if cleaned > 0:
                logger.info(f"만료된 세션 정리: user_id={user_id}, count={cleaned}")

            return cleaned

        except redis.RedisError as e:
            logger.error(f"세션 정리 실패: user_id={user_id}, error={e}")
            return 0

    def is_connected(self) -> bool:
        """Redis 연결 상태 확인"""
        try:
            self.redis_client.ping()
            return True
        except (redis.ConnectionError, redis.RedisError):
            return False

    def close(self):
        """Redis 연결 종료"""
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None
            logger.info("Redis 연결 종료")


# 싱글톤 인스턴스
_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """
    SessionService 싱글톤 인스턴스 반환

    Usage:
        session_service = get_session_service()
        session_id = await session_service.create_session(user_id="...")
    """
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service


async def create_session_for_user(
    user_id: str,
    organization_id: Optional[str] = None,
    project_id: Optional[str] = None
) -> str:
    """
    헬퍼 함수: 사용자를 위한 새 세션 생성

    Args:
        user_id: 사용자 UUID
        organization_id: 조직 UUID (선택)
        project_id: 프로젝트 UUID (선택)

    Returns:
        session_id: 생성된 세션 ID
    """
    service = get_session_service()
    return await service.create_session(
        user_id=user_id,
        organization_id=organization_id,
        project_id=project_id
    )
