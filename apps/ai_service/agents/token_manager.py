"""
Token Manager - 토큰 사용량 관리 및 제한 (Phase 7)

Agent 실행 시 토큰 사용량을 관리하고 제한하는 모듈입니다.
기존 UsageService를 래핑하여 세션별 토큰 예산 관리를 제공합니다.

주요 기능:
- 실행 전 토큰 쿼터 확인 및 예약 (check_and_reserve)
- 실행 후 토큰 사용량 확정 (confirm_usage)
- 예약 해제 (release_reservation)
- 세션별 토큰 예산 관리

설계 문서: docs/adaptive-agent/07_IMPLEMENTATION_GUIDE.md - 4. 토큰 제한 통합
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from apps.ai_service.services.usage_service import (
    UsageService,
    get_usage_service,
    DEFAULT_QUOTAS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class TokenBudget:
    """
    토큰 예산

    세션별 토큰 사용량과 한도를 추적합니다.
    """
    total_limit: int  # 총 토큰 한도
    used: int = 0  # 사용된 토큰
    reserved: int = 0  # 예약된 토큰 (실행 중)

    @property
    def available(self) -> int:
        """사용 가능한 토큰 수"""
        return max(0, self.total_limit - self.used - self.reserved)

    @property
    def utilization(self) -> float:
        """사용률 (0.0 ~ 1.0)"""
        if self.total_limit == 0:
            return 1.0
        return (self.used + self.reserved) / self.total_limit

    @property
    def remaining_percentage(self) -> float:
        """남은 비율 (0.0 ~ 100.0)"""
        if self.total_limit == 0:
            return 0.0
        return (self.available / self.total_limit) * 100

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "total_limit": self.total_limit,
            "used": self.used,
            "reserved": self.reserved,
            "available": self.available,
            "utilization": round(self.utilization, 4),
            "remaining_percentage": round(self.remaining_percentage, 2),
        }


@dataclass
class TokenUsageResult:
    """
    토큰 사용 결과

    check_and_reserve() 호출 결과를 담습니다.
    """
    allowed: bool  # 사용 허용 여부
    budget: TokenBudget  # 현재 예산 상태
    estimated_cost: int = 0  # 예상 토큰 비용
    message: str = ""  # 상태 메시지

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "allowed": self.allowed,
            "budget": self.budget.to_dict(),
            "estimated_cost": self.estimated_cost,
            "message": self.message,
        }


@dataclass
class TokenUsageConfirmation:
    """
    토큰 사용량 확정 결과

    confirm_usage() 호출 결과를 담습니다.
    """
    success: bool
    actual_tokens: int
    estimated_tokens: int
    difference: int  # actual - estimated
    budget: Optional[TokenBudget] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "success": self.success,
            "actual_tokens": self.actual_tokens,
            "estimated_tokens": self.estimated_tokens,
            "difference": self.difference,
            "budget": self.budget.to_dict() if self.budget else None,
            "error": self.error,
        }


# =============================================================================
# TokenManager 클래스
# =============================================================================

class TokenManager:
    """
    토큰 사용량 관리자

    UsageService를 래핑하여 Agent 실행에 필요한 토큰 관리를 제공합니다.
    세션별로 토큰 예산을 관리하고, 실행 전 예약/실행 후 확정 패턴을 지원합니다.

    Usage:
        manager = get_token_manager()

        # 1. 실행 전 예약
        result = await manager.check_and_reserve(
            user_id="user-123",
            session_id="session-456",
            estimated_tokens=1000,
        )

        if result.allowed:
            # 2. 작업 실행
            actual_tokens = execute_work()

            # 3. 사용량 확정
            await manager.confirm_usage(
                user_id="user-123",
                session_id="session-456",
                actual_tokens=actual_tokens,
                estimated_tokens=1000,
            )
        else:
            # 4. 실패 시 예약 해제 (자동으로 되지만 명시적으로도 가능)
            await manager.release_reservation(
                session_id="session-456",
                estimated_tokens=1000,
            )
    """

    def __init__(self, usage_service: Optional[UsageService] = None):
        """
        TokenManager 초기화

        Args:
            usage_service: UsageService 인스턴스 (없으면 싱글톤 사용)
        """
        self._usage_service = usage_service
        self._session_budgets: Dict[str, TokenBudget] = {}
        self._reservation_history: Dict[str, list] = {}  # 디버깅용
        logger.info("TokenManager initialized")

    @property
    def usage_service(self) -> UsageService:
        """지연 초기화된 UsageService"""
        if self._usage_service is None:
            self._usage_service = get_usage_service()
        return self._usage_service

    # =========================================================================
    # 주요 메서드
    # =========================================================================

    async def check_and_reserve(
        self,
        user_id: str,
        session_id: str,
        estimated_tokens: int,
        organization_id: Optional[str] = None,
    ) -> TokenUsageResult:
        """
        토큰 사용 가능 여부 확인 및 예약

        실행 전에 호출하여 토큰을 예약합니다.
        예약된 토큰은 confirm_usage() 또는 release_reservation()으로 해제됩니다.

        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            estimated_tokens: 예상 토큰 사용량
            organization_id: 조직 ID (선택)

        Returns:
            TokenUsageResult: 예약 결과
        """
        logger.debug(
            f"[TokenManager] check_and_reserve: user={user_id}, "
            f"session={session_id}, estimated={estimated_tokens}"
        )

        try:
            # 1. UsageService를 통해 일일 쿼터 확인
            quota_result = await self.usage_service.check_quota(
                user_id=user_id,
                organization_id=organization_id,
            )

            # 2. 쿼터 초과 시 거부
            if not quota_result.get("within_quota", True):
                budget = self._get_or_create_session_budget(
                    session_id, quota_result, organization_id
                )
                return TokenUsageResult(
                    allowed=False,
                    budget=budget,
                    estimated_cost=estimated_tokens,
                    message=quota_result.get("message", "일일 요청 한도 초과"),
                )

            # 3. 세션 예산 조회/생성
            budget = self._get_or_create_session_budget(
                session_id, quota_result, organization_id
            )

            # 4. 토큰 예산 확인
            if budget.available < estimated_tokens:
                return TokenUsageResult(
                    allowed=False,
                    budget=budget,
                    estimated_cost=estimated_tokens,
                    message=(
                        f"토큰 예산 부족: 필요 {estimated_tokens:,}, "
                        f"가용 {budget.available:,}"
                    ),
                )

            # 5. 토큰 예약
            budget.reserved += estimated_tokens
            self._session_budgets[session_id] = budget

            # 예약 기록 (디버깅용)
            self._record_reservation(session_id, estimated_tokens, "reserve")

            logger.info(
                f"[TokenManager] Tokens reserved: session={session_id}, "
                f"reserved={estimated_tokens}, available={budget.available}"
            )

            return TokenUsageResult(
                allowed=True,
                budget=budget,
                estimated_cost=estimated_tokens,
                message="OK",
            )

        except Exception as e:
            logger.error(f"[TokenManager] check_and_reserve error: {e}")
            # 에러 시에도 기본 예산으로 허용 (graceful degradation)
            default_budget = TokenBudget(
                total_limit=DEFAULT_QUOTAS["personal"].daily_token_limit
            )
            return TokenUsageResult(
                allowed=True,
                budget=default_budget,
                estimated_cost=estimated_tokens,
                message=f"쿼터 확인 실패, 기본값 사용: {str(e)}",
            )

    async def confirm_usage(
        self,
        user_id: str,
        session_id: str,
        actual_tokens: int,
        estimated_tokens: int,
        organization_id: Optional[str] = None,
        workflow_name: Optional[str] = None,
    ) -> TokenUsageConfirmation:
        """
        토큰 사용량 확정

        예약된 토큰을 실제 사용량으로 전환합니다.
        실제 사용량이 예상과 다르면 차이를 조정합니다.

        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            actual_tokens: 실제 사용량
            estimated_tokens: 예약했던 예상 사용량
            organization_id: 조직 ID (선택)
            workflow_name: 워크플로우 이름 (선택)

        Returns:
            TokenUsageConfirmation: 확정 결과
        """
        logger.debug(
            f"[TokenManager] confirm_usage: user={user_id}, session={session_id}, "
            f"actual={actual_tokens}, estimated={estimated_tokens}"
        )

        try:
            # 1. UsageService에 사용량 기록
            workflows = [workflow_name] if workflow_name else None
            await self.usage_service.track_usage(
                user_id=user_id,
                organization_id=organization_id,
                workflows=workflows,
                tokens=actual_tokens,
                execution_time=0.0,  # 별도 추적
            )

            # 2. 세션 예산 업데이트
            budget = self._session_budgets.get(session_id)
            if budget:
                # 예약 해제
                budget.reserved = max(0, budget.reserved - estimated_tokens)
                # 실제 사용량 반영
                budget.used += actual_tokens
                self._session_budgets[session_id] = budget

            # 확정 기록 (디버깅용)
            self._record_reservation(session_id, actual_tokens, "confirm")

            difference = actual_tokens - estimated_tokens
            logger.info(
                f"[TokenManager] Usage confirmed: user={user_id}, "
                f"session={session_id}, actual={actual_tokens}, "
                f"diff={difference:+d}"
            )

            return TokenUsageConfirmation(
                success=True,
                actual_tokens=actual_tokens,
                estimated_tokens=estimated_tokens,
                difference=difference,
                budget=budget,
            )

        except Exception as e:
            logger.error(f"[TokenManager] confirm_usage error: {e}")
            return TokenUsageConfirmation(
                success=False,
                actual_tokens=actual_tokens,
                estimated_tokens=estimated_tokens,
                difference=actual_tokens - estimated_tokens,
                error=str(e),
            )

    async def release_reservation(
        self,
        session_id: str,
        estimated_tokens: int,
    ) -> bool:
        """
        토큰 예약 해제

        실행이 취소되거나 실패했을 때 예약된 토큰을 해제합니다.

        Args:
            session_id: 세션 ID
            estimated_tokens: 예약했던 예상 사용량

        Returns:
            성공 여부
        """
        logger.debug(
            f"[TokenManager] release_reservation: session={session_id}, "
            f"tokens={estimated_tokens}"
        )

        try:
            budget = self._session_budgets.get(session_id)
            if budget:
                budget.reserved = max(0, budget.reserved - estimated_tokens)
                self._session_budgets[session_id] = budget

                # 해제 기록 (디버깅용)
                self._record_reservation(session_id, estimated_tokens, "release")

                logger.info(
                    f"[TokenManager] Reservation released: session={session_id}, "
                    f"tokens={estimated_tokens}, reserved_now={budget.reserved}"
                )

            return True

        except Exception as e:
            logger.error(f"[TokenManager] release_reservation error: {e}")
            return False

    # =========================================================================
    # 조회 메서드
    # =========================================================================

    def get_session_budget(self, session_id: str) -> Optional[TokenBudget]:
        """세션 예산 조회"""
        return self._session_budgets.get(session_id)

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        세션 토큰 통계 조회

        Args:
            session_id: 세션 ID

        Returns:
            통계 딕셔너리
        """
        budget = self._session_budgets.get(session_id)
        if not budget:
            return {}

        return budget.to_dict()

    def get_all_sessions_stats(self) -> Dict[str, Dict[str, Any]]:
        """모든 세션 통계 조회"""
        return {
            session_id: budget.to_dict()
            for session_id, budget in self._session_budgets.items()
        }

    # =========================================================================
    # 관리 메서드
    # =========================================================================

    def clear_session(self, session_id: str) -> bool:
        """
        세션 예산 정리

        세션이 종료될 때 호출하여 메모리를 정리합니다.

        Args:
            session_id: 세션 ID

        Returns:
            세션이 존재했는지 여부
        """
        existed = session_id in self._session_budgets
        self._session_budgets.pop(session_id, None)
        self._reservation_history.pop(session_id, None)

        if existed:
            logger.info(f"[TokenManager] Session cleared: {session_id}")

        return existed

    def clear_all_sessions(self):
        """모든 세션 예산 정리"""
        count = len(self._session_budgets)
        self._session_budgets.clear()
        self._reservation_history.clear()
        logger.info(f"[TokenManager] All sessions cleared: {count} sessions")

    # =========================================================================
    # 유틸리티 메서드
    # =========================================================================

    async def estimate_workflow_tokens(
        self,
        workflow_name: str,
        complexity: str = "medium",
    ) -> int:
        """
        워크플로우별 예상 토큰 추정

        Args:
            workflow_name: 워크플로우 이름
            complexity: 복잡도 (simple, medium, complex)

        Returns:
            예상 토큰 수
        """
        # 워크플로우별 기본 토큰 추정치
        base_estimates = {
            "rag_workflow": 800,
            "document_workflow": 1500,
            "case_workflow": 1200,
            "risk_workflow": 1000,
            "search_legal": 800,
            "analyze_document": 1500,
            "analyze_case": 1200,
            "assess_risk": 1000,
            "compare_documents": 2000,
        }

        # 복잡도 배수
        complexity_multipliers = {
            "simple": 0.5,
            "medium": 1.0,
            "complex": 2.0,
            "very_complex": 3.0,
        }

        base = base_estimates.get(workflow_name, 500)
        multiplier = complexity_multipliers.get(complexity, 1.0)

        return int(base * multiplier)

    async def can_execute_workflow(
        self,
        user_id: str,
        session_id: str,
        workflow_name: str,
        complexity: str = "medium",
        organization_id: Optional[str] = None,
    ) -> TokenUsageResult:
        """
        워크플로우 실행 가능 여부 확인

        예상 토큰을 자동 계산하여 check_and_reserve()를 호출합니다.

        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            workflow_name: 워크플로우 이름
            complexity: 복잡도
            organization_id: 조직 ID (선택)

        Returns:
            TokenUsageResult
        """
        estimated_tokens = await self.estimate_workflow_tokens(
            workflow_name, complexity
        )

        return await self.check_and_reserve(
            user_id=user_id,
            session_id=session_id,
            estimated_tokens=estimated_tokens,
            organization_id=organization_id,
        )

    # =========================================================================
    # 내부 헬퍼 메서드
    # =========================================================================

    def _get_or_create_session_budget(
        self,
        session_id: str,
        quota_result: Dict[str, Any],
        organization_id: Optional[str] = None,
    ) -> TokenBudget:
        """세션별 토큰 예산 조회 또는 생성"""
        if session_id in self._session_budgets:
            return self._session_budgets[session_id]

        # 조직 또는 개인 쿼터 설정
        if organization_id:
            daily_limit = DEFAULT_QUOTAS.get(
                "organization", DEFAULT_QUOTAS["personal"]
            ).daily_token_limit
        else:
            daily_limit = DEFAULT_QUOTAS["personal"].daily_token_limit

        # quota_result에서 현재 사용량 가져오기
        current_tokens = quota_result.get("current_tokens", 0)

        budget = TokenBudget(
            total_limit=daily_limit,
            used=current_tokens,
            reserved=0,
        )

        self._session_budgets[session_id] = budget
        logger.debug(
            f"[TokenManager] Session budget created: session={session_id}, "
            f"limit={daily_limit}, used={current_tokens}"
        )

        return budget

    def _record_reservation(
        self,
        session_id: str,
        tokens: int,
        action: str,
    ):
        """예약 기록 (디버깅용)"""
        if session_id not in self._reservation_history:
            self._reservation_history[session_id] = []

        self._reservation_history[session_id].append({
            "action": action,
            "tokens": tokens,
            "timestamp": datetime.now().isoformat(),
        })

        # 최대 100개 유지
        if len(self._reservation_history[session_id]) > 100:
            self._reservation_history[session_id] = \
                self._reservation_history[session_id][-100:]


# =============================================================================
# 싱글톤 인스턴스
# =============================================================================

_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """
    TokenManager 싱글톤 인스턴스 반환

    Usage:
        manager = get_token_manager()
        result = await manager.check_and_reserve(...)
    """
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager


def init_token_manager(usage_service: Optional[UsageService] = None) -> TokenManager:
    """
    TokenManager 명시적 초기화 (기존 인스턴스 덮어씀)

    Args:
        usage_service: UsageService 인스턴스 (선택)

    Returns:
        새 TokenManager 인스턴스
    """
    global _token_manager
    _token_manager = TokenManager(usage_service=usage_service)
    return _token_manager
