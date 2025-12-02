"""
Usage Service - 사용량 추적 및 제한 서비스

Agent Hub의 사용량을 추적하고 쿼터를 관리하는 서비스입니다.
설계 문서: docs/AGENT_HUB_BACKEND_INTEGRATION.md - 9. 사용량 추적 및 제한

주요 기능:
- 일일 사용량 쿼터 확인 (check_quota)
- 사용량 기록 (track_usage)
- 일일 사용량 조회 (get_daily_usage)
- 조직 설정 조회 (get_org_settings)

Redis Key 패턴:
- usage:daily:{user_id}:{date} : 일일 사용량 데이터 (JSON)
- usage:workflow:{user_id}:{date} : 워크플로우별 사용량 (JSON)
- org_settings:{org_id} : 조직 설정 캐시 (JSON)
"""

import json
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

import redis
from loguru import logger
from fastapi import HTTPException, status

from apps.ai_service.config.settings import settings
from apps.ai_service.middleware.permissions import WORKFLOW_PERMISSIONS, get_quota_weight


# ============================================================
# 쿼터 설정
# ============================================================

@dataclass
class QuotaConfig:
    """쿼터 설정"""
    daily_request_limit: int = 100  # 일일 요청 제한
    daily_token_limit: int = 100000  # 일일 토큰 제한
    max_execution_time: float = 300.0  # 최대 실행 시간 (초)


# 기본 쿼터 설정
DEFAULT_QUOTAS = {
    "personal": QuotaConfig(
        daily_request_limit=100,
        daily_token_limit=50000,
        max_execution_time=300.0
    ),
    "organization": QuotaConfig(
        daily_request_limit=1000,
        daily_token_limit=500000,
        max_execution_time=600.0
    ),
    "enterprise": QuotaConfig(
        daily_request_limit=10000,
        daily_token_limit=5000000,
        max_execution_time=1800.0
    ),
}


@dataclass
class UsageData:
    """일일 사용량 데이터"""
    user_id: str
    organization_id: Optional[str]
    date: str  # YYYY-MM-DD 형식
    total_requests: int = 0
    total_tokens: int = 0
    total_execution_time: float = 0.0
    workflow_usage: Dict[str, int] = None  # 워크플로우별 사용 횟수
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.workflow_usage is None:
            self.workflow_usage = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


# ============================================================
# UsageService 클래스
# ============================================================

class UsageService:
    """
    Redis 기반 사용량 추적 및 제한 서비스

    Features:
    - 일일 사용량 추적
    - 워크플로우별 사용량 통계
    - 쿼터 초과 검사
    - 조직별 설정 관리
    """

    def __init__(self):
        """Redis 클라이언트 초기화"""
        self._redis_client: Optional[redis.Redis] = None
        self._usage_expire_seconds = 7 * 24 * 3600  # 7일 (통계 보존)
        self._org_settings_cache_seconds = 300  # 5분 캐시

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
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                self._redis_client.ping()
                logger.info(f"UsageService Redis 연결 성공: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except redis.ConnectionError as e:
                logger.error(f"UsageService Redis 연결 실패: {e}")
                raise
        return self._redis_client

    # ============================================================
    # Redis Key 헬퍼
    # ============================================================

    def _get_daily_usage_key(self, user_id: str, date_str: str) -> str:
        """일일 사용량 Redis 키"""
        return f"usage:daily:{user_id}:{date_str}"

    def _get_org_usage_key(self, org_id: str, date_str: str) -> str:
        """조직 일일 사용량 Redis 키"""
        return f"usage:org:{org_id}:{date_str}"

    def _get_org_settings_key(self, org_id: str) -> str:
        """조직 설정 캐시 Redis 키"""
        return f"org_settings:{org_id}"

    def _get_today_str(self) -> str:
        """오늘 날짜 문자열 (YYYY-MM-DD)"""
        return date.today().isoformat()

    # ============================================================
    # 쿼터 확인
    # ============================================================

    async def check_quota(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        workflows: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        일일 사용량 쿼터 확인

        Args:
            user_id: 사용자 UUID
            organization_id: 조직 UUID (선택)
            workflows: 실행하려는 워크플로우 목록 (가중치 계산용)

        Returns:
            {
                "within_quota": bool,  # 쿼터 내인지 여부
                "current_usage": int,  # 현재 사용량
                "daily_limit": int,    # 일일 제한
                "remaining": int,      # 남은 사용량
                "required": int,       # 이번 요청에 필요한 쿼터
                "message": str         # 메시지
            }

        Raises:
            HTTPException(429): 쿼터 초과 시
        """
        today = self._get_today_str()

        # 1. 쿼터 설정 조회
        quota_config = await self._get_quota_config(organization_id)
        daily_limit = quota_config.daily_request_limit

        # 2. 현재 사용량 조회
        usage = await self.get_daily_usage(user_id, today)
        current_usage = usage.get("total_requests", 0)

        # 3. 이번 요청에 필요한 가중치 계산
        required = 1  # 기본 1회
        if workflows:
            required = sum(get_quota_weight(wf) for wf in workflows)

        # 4. 쿼터 확인
        remaining = max(0, daily_limit - current_usage)
        within_quota = (current_usage + required) <= daily_limit

        result = {
            "within_quota": within_quota,
            "current_usage": current_usage,
            "daily_limit": daily_limit,
            "remaining": remaining,
            "required": required,
            "percentage_used": round((current_usage / daily_limit) * 100, 1) if daily_limit > 0 else 0,
        }

        if not within_quota:
            result["message"] = f"일일 사용량 한도({daily_limit}회)를 초과했습니다. 내일 다시 시도해주세요."
            logger.warning(
                f"쿼터 초과: user_id={user_id}, "
                f"current={current_usage}, limit={daily_limit}, required={required}"
            )
        else:
            result["message"] = f"사용 가능 (남은 쿼터: {remaining}회)"

        return result

    async def check_quota_or_raise(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        workflows: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        쿼터 확인 및 초과 시 예외 발생

        Args:
            user_id: 사용자 UUID
            organization_id: 조직 UUID (선택)
            workflows: 실행하려는 워크플로우 목록

        Returns:
            쿼터 정보 딕셔너리

        Raises:
            HTTPException(429): 쿼터 초과 시
        """
        result = await self.check_quota(user_id, organization_id, workflows)

        if not result["within_quota"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "QUOTA_EXCEEDED",
                    "message": result["message"],
                    "current_usage": result["current_usage"],
                    "daily_limit": result["daily_limit"],
                    "reset_at": f"{(date.today() + timedelta(days=1)).isoformat()}T00:00:00Z"
                }
            )

        return result

    async def _get_quota_config(self, organization_id: Optional[str] = None) -> QuotaConfig:
        """
        쿼터 설정 조회

        Args:
            organization_id: 조직 UUID

        Returns:
            QuotaConfig 객체
        """
        if not organization_id:
            # 개인 사용자 기본 쿼터
            return DEFAULT_QUOTAS["personal"]

        # 조직 설정 조회 (캐시 또는 기본값)
        org_settings = await self.get_org_settings(organization_id)
        plan_type = org_settings.get("plan_type", "organization")

        if plan_type in DEFAULT_QUOTAS:
            base_config = DEFAULT_QUOTAS[plan_type]
        else:
            base_config = DEFAULT_QUOTAS["organization"]

        # 조직별 커스텀 쿼터 적용
        custom_limit = org_settings.get("daily_request_limit")
        if custom_limit:
            return QuotaConfig(
                daily_request_limit=custom_limit,
                daily_token_limit=org_settings.get("daily_token_limit", base_config.daily_token_limit),
                max_execution_time=org_settings.get("max_execution_time", base_config.max_execution_time)
            )

        return base_config

    # ============================================================
    # 사용량 기록
    # ============================================================

    async def track_usage(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        workflows: Optional[List[str]] = None,
        execution_time: float = 0.0,
        tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageData:
        """
        사용량 기록

        Args:
            user_id: 사용자 UUID
            organization_id: 조직 UUID (선택)
            workflows: 실행된 워크플로우 목록
            execution_time: 실행 시간 (초)
            tokens: 사용된 토큰 수
            metadata: 추가 메타데이터

        Returns:
            업데이트된 UsageData
        """
        today = self._get_today_str()
        workflows = workflows or []

        # 워크플로우별 가중치 적용된 요청 수
        total_weight = sum(get_quota_weight(wf) for wf in workflows) if workflows else 1

        try:
            # 1. 기존 사용량 조회 또는 생성
            usage_key = self._get_daily_usage_key(user_id, today)
            existing_json = self.redis_client.get(usage_key)

            if existing_json:
                usage_data = json.loads(existing_json)
            else:
                usage_data = asdict(UsageData(
                    user_id=user_id,
                    organization_id=organization_id,
                    date=today
                ))

            # 2. 사용량 업데이트
            usage_data["total_requests"] += total_weight
            usage_data["total_tokens"] += tokens
            usage_data["total_execution_time"] += execution_time
            usage_data["updated_at"] = datetime.now().isoformat()

            # 워크플로우별 사용 횟수 업데이트
            workflow_usage = usage_data.get("workflow_usage", {})
            for wf in workflows:
                workflow_usage[wf] = workflow_usage.get(wf, 0) + 1
            usage_data["workflow_usage"] = workflow_usage

            # 3. Redis에 저장 (TTL: 7일)
            self.redis_client.setex(
                usage_key,
                self._usage_expire_seconds,
                json.dumps(usage_data, ensure_ascii=False)
            )

            # 4. 조직 사용량도 업데이트 (있는 경우)
            if organization_id:
                await self._update_org_usage(
                    organization_id, today, total_weight, tokens, execution_time, workflows
                )

            logger.debug(
                f"사용량 기록: user_id={user_id}, "
                f"requests={usage_data['total_requests']}, "
                f"workflows={workflows}"
            )

            return UsageData(**usage_data)

        except redis.RedisError as e:
            logger.error(f"사용량 기록 실패: user_id={user_id}, error={e}")
            # 실패해도 서비스는 계속 (graceful degradation)
            return UsageData(user_id=user_id, organization_id=organization_id, date=today)

    async def _update_org_usage(
        self,
        org_id: str,
        date_str: str,
        requests: int,
        tokens: int,
        execution_time: float,
        workflows: List[str]
    ):
        """조직 사용량 업데이트 (내부용)"""
        try:
            org_key = self._get_org_usage_key(org_id, date_str)
            existing_json = self.redis_client.get(org_key)

            if existing_json:
                org_usage = json.loads(existing_json)
            else:
                org_usage = {
                    "organization_id": org_id,
                    "date": date_str,
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_execution_time": 0.0,
                    "workflow_usage": {},
                    "unique_users": []
                }

            org_usage["total_requests"] += requests
            org_usage["total_tokens"] += tokens
            org_usage["total_execution_time"] += execution_time

            # 워크플로우별 사용 횟수
            workflow_usage = org_usage.get("workflow_usage", {})
            for wf in workflows:
                workflow_usage[wf] = workflow_usage.get(wf, 0) + 1
            org_usage["workflow_usage"] = workflow_usage

            self.redis_client.setex(
                org_key,
                self._usage_expire_seconds,
                json.dumps(org_usage, ensure_ascii=False)
            )

        except redis.RedisError as e:
            logger.error(f"조직 사용량 업데이트 실패: org_id={org_id}, error={e}")

    # ============================================================
    # 사용량 조회
    # ============================================================

    async def get_daily_usage(
        self,
        user_id: str,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        일일 사용량 조회

        Args:
            user_id: 사용자 UUID
            date_str: 날짜 (YYYY-MM-DD), 기본값: 오늘

        Returns:
            사용량 딕셔너리
        """
        if date_str is None:
            date_str = self._get_today_str()

        try:
            usage_key = self._get_daily_usage_key(user_id, date_str)
            usage_json = self.redis_client.get(usage_key)

            if usage_json:
                return json.loads(usage_json)

            # 데이터 없으면 빈 데이터 반환
            return {
                "user_id": user_id,
                "date": date_str,
                "total_requests": 0,
                "total_tokens": 0,
                "total_execution_time": 0.0,
                "workflow_usage": {}
            }

        except redis.RedisError as e:
            logger.error(f"사용량 조회 실패: user_id={user_id}, date={date_str}, error={e}")
            return {
                "user_id": user_id,
                "date": date_str,
                "total_requests": 0,
                "total_tokens": 0,
                "total_execution_time": 0.0,
                "workflow_usage": {}
            }

    async def get_usage_history(
        self,
        user_id: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        사용량 기록 조회 (최근 N일)

        Args:
            user_id: 사용자 UUID
            days: 조회할 일수 (기본: 7일)

        Returns:
            일별 사용량 리스트
        """
        history = []
        today = date.today()

        for i in range(days):
            target_date = (today - timedelta(days=i)).isoformat()
            usage = await self.get_daily_usage(user_id, target_date)
            history.append(usage)

        return history

    async def get_org_usage(
        self,
        organization_id: str,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        조직 일일 사용량 조회

        Args:
            organization_id: 조직 UUID
            date_str: 날짜 (YYYY-MM-DD), 기본값: 오늘

        Returns:
            조직 사용량 딕셔너리
        """
        if date_str is None:
            date_str = self._get_today_str()

        try:
            org_key = self._get_org_usage_key(organization_id, date_str)
            usage_json = self.redis_client.get(org_key)

            if usage_json:
                return json.loads(usage_json)

            return {
                "organization_id": organization_id,
                "date": date_str,
                "total_requests": 0,
                "total_tokens": 0,
                "total_execution_time": 0.0,
                "workflow_usage": {}
            }

        except redis.RedisError as e:
            logger.error(f"조직 사용량 조회 실패: org_id={organization_id}, error={e}")
            return {
                "organization_id": organization_id,
                "date": date_str,
                "total_requests": 0,
                "total_tokens": 0,
                "total_execution_time": 0.0,
                "workflow_usage": {}
            }

    # ============================================================
    # 조직 설정 조회
    # ============================================================

    async def get_org_settings(self, organization_id: str) -> Dict[str, Any]:
        """
        조직 설정 조회 (캐시 사용)

        Args:
            organization_id: 조직 UUID

        Returns:
            조직 설정 딕셔너리
        """
        try:
            # 1. 캐시 확인
            cache_key = self._get_org_settings_key(organization_id)
            cached = self.redis_client.get(cache_key)

            if cached:
                return json.loads(cached)

            # 2. 캐시 없으면 기본값 반환
            # TODO: Backend API에서 조직 설정 조회 구현
            # 현재는 기본값 반환
            default_settings = {
                "organization_id": organization_id,
                "plan_type": "organization",  # personal, organization, enterprise
                "daily_request_limit": DEFAULT_QUOTAS["organization"].daily_request_limit,
                "daily_token_limit": DEFAULT_QUOTAS["organization"].daily_token_limit,
                "max_execution_time": DEFAULT_QUOTAS["organization"].max_execution_time,
                "features_enabled": ["rag", "document", "case", "risk"],
            }

            # 캐시 저장 (5분)
            self.redis_client.setex(
                cache_key,
                self._org_settings_cache_seconds,
                json.dumps(default_settings, ensure_ascii=False)
            )

            return default_settings

        except redis.RedisError as e:
            logger.error(f"조직 설정 조회 실패: org_id={organization_id}, error={e}")
            # 기본값 반환
            return {
                "plan_type": "organization",
                "daily_request_limit": DEFAULT_QUOTAS["organization"].daily_request_limit,
            }

    async def update_org_settings(
        self,
        organization_id: str,
        settings_update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        조직 설정 업데이트 (캐시 갱신)

        Args:
            organization_id: 조직 UUID
            settings_update: 업데이트할 설정

        Returns:
            업데이트된 설정
        """
        try:
            current = await self.get_org_settings(organization_id)
            current.update(settings_update)

            cache_key = self._get_org_settings_key(organization_id)
            self.redis_client.setex(
                cache_key,
                self._org_settings_cache_seconds,
                json.dumps(current, ensure_ascii=False)
            )

            logger.info(f"조직 설정 업데이트: org_id={organization_id}")
            return current

        except redis.RedisError as e:
            logger.error(f"조직 설정 업데이트 실패: org_id={organization_id}, error={e}")
            raise

    def invalidate_org_settings_cache(self, organization_id: str):
        """조직 설정 캐시 무효화"""
        try:
            cache_key = self._get_org_settings_key(organization_id)
            self.redis_client.delete(cache_key)
            logger.info(f"조직 설정 캐시 무효화: org_id={organization_id}")
        except redis.RedisError as e:
            logger.error(f"캐시 무효화 실패: org_id={organization_id}, error={e}")

    # ============================================================
    # 통계
    # ============================================================

    async def get_usage_summary(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        사용량 요약 조회

        Args:
            user_id: 사용자 UUID
            organization_id: 조직 UUID (선택)

        Returns:
            사용량 요약
        """
        today = self._get_today_str()
        user_usage = await self.get_daily_usage(user_id, today)
        quota_config = await self._get_quota_config(organization_id)

        summary = {
            "user_id": user_id,
            "date": today,
            "user_usage": {
                "total_requests": user_usage.get("total_requests", 0),
                "total_tokens": user_usage.get("total_tokens", 0),
                "total_execution_time": round(user_usage.get("total_execution_time", 0), 2),
                "workflow_breakdown": user_usage.get("workflow_usage", {})
            },
            "quota": {
                "daily_limit": quota_config.daily_request_limit,
                "remaining": max(0, quota_config.daily_request_limit - user_usage.get("total_requests", 0)),
                "percentage_used": round(
                    (user_usage.get("total_requests", 0) / quota_config.daily_request_limit) * 100, 1
                ) if quota_config.daily_request_limit > 0 else 0
            }
        }

        if organization_id:
            org_usage = await self.get_org_usage(organization_id, today)
            summary["organization_usage"] = {
                "total_requests": org_usage.get("total_requests", 0),
                "total_tokens": org_usage.get("total_tokens", 0),
                "total_execution_time": round(org_usage.get("total_execution_time", 0), 2),
                "workflow_breakdown": org_usage.get("workflow_usage", {})
            }

        return summary

    # ============================================================
    # 유틸리티
    # ============================================================

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
            logger.info("UsageService Redis 연결 종료")


# ============================================================
# 싱글톤 인스턴스 및 헬퍼 함수
# ============================================================

_usage_service: Optional[UsageService] = None


def get_usage_service() -> UsageService:
    """
    UsageService 싱글톤 인스턴스 반환

    Usage:
        usage_service = get_usage_service()
        result = await usage_service.check_quota(user_id="...")
    """
    global _usage_service
    if _usage_service is None:
        _usage_service = UsageService()
    return _usage_service


async def check_user_quota(
    user_id: str,
    organization_id: Optional[str] = None,
    workflows: Optional[List[str]] = None,
    raise_on_exceed: bool = True
) -> Dict[str, Any]:
    """
    헬퍼 함수: 사용자 쿼터 확인

    Args:
        user_id: 사용자 UUID
        organization_id: 조직 UUID (선택)
        workflows: 실행하려는 워크플로우 목록
        raise_on_exceed: 초과 시 예외 발생 여부

    Returns:
        쿼터 정보

    Raises:
        HTTPException(429): raise_on_exceed=True이고 쿼터 초과 시
    """
    service = get_usage_service()
    if raise_on_exceed:
        return await service.check_quota_or_raise(user_id, organization_id, workflows)
    return await service.check_quota(user_id, organization_id, workflows)


async def record_usage(
    user_id: str,
    organization_id: Optional[str] = None,
    workflows: Optional[List[str]] = None,
    execution_time: float = 0.0,
    tokens: int = 0
) -> UsageData:
    """
    헬퍼 함수: 사용량 기록

    Args:
        user_id: 사용자 UUID
        organization_id: 조직 UUID (선택)
        workflows: 실행된 워크플로우 목록
        execution_time: 실행 시간 (초)
        tokens: 사용된 토큰 수

    Returns:
        UsageData
    """
    service = get_usage_service()
    return await service.track_usage(
        user_id=user_id,
        organization_id=organization_id,
        workflows=workflows,
        execution_time=execution_time,
        tokens=tokens
    )
