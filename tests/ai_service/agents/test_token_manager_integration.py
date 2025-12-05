"""
Phase 8: 토큰 제한 통합 테스트

테스트 항목:
1. 토큰 예약 및 확인
2. 세션별 예산 관리
3. 쿼터 초과 거부
4. 사용량 확정 및 추적
5. Graceful degradation
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from apps.ai_service.agents.token_manager import (
    TokenManager,
    TokenBudget,
    TokenUsageResult,
    TokenUsageConfirmation,
    get_token_manager,
    init_token_manager,
)


class TestTokenBudget:
    """TokenBudget 데이터클래스 테스트"""

    def test_available_calculation(self):
        """사용 가능 토큰 계산"""
        budget = TokenBudget(
            total_limit=10000,
            used=3000,
            reserved=2000,
        )

        assert budget.available == 5000  # 10000 - 3000 - 2000

    def test_available_never_negative(self):
        """음수 불가"""
        budget = TokenBudget(
            total_limit=1000,
            used=800,
            reserved=500,
        )

        assert budget.available == 0  # max(0, 1000 - 800 - 500)

    def test_utilization(self):
        """사용률 계산"""
        budget = TokenBudget(
            total_limit=10000,
            used=5000,
            reserved=2500,
        )

        assert budget.utilization == 0.75  # (5000 + 2500) / 10000

    def test_utilization_zero_limit(self):
        """한도 0일 때 사용률"""
        budget = TokenBudget(
            total_limit=0,
            used=0,
            reserved=0,
        )

        assert budget.utilization == 1.0

    def test_remaining_percentage(self):
        """남은 비율 계산"""
        budget = TokenBudget(
            total_limit=10000,
            used=2000,
            reserved=1000,
        )

        assert budget.remaining_percentage == 70.0  # (7000/10000) * 100

    def test_to_dict(self):
        """딕셔너리 변환"""
        budget = TokenBudget(
            total_limit=10000,
            used=3000,
            reserved=2000,
        )

        d = budget.to_dict()

        assert d["total_limit"] == 10000
        assert d["used"] == 3000
        assert d["reserved"] == 2000
        assert d["available"] == 5000
        assert "utilization" in d
        assert "remaining_percentage" in d


class TestTokenUsageResult:
    """TokenUsageResult 테스트"""

    def test_allowed_result(self):
        """허용된 결과"""
        budget = TokenBudget(total_limit=10000)
        result = TokenUsageResult(
            allowed=True,
            budget=budget,
            estimated_cost=500,
            message="OK",
        )

        assert result.allowed
        assert result.message == "OK"

    def test_denied_result(self):
        """거부된 결과"""
        budget = TokenBudget(total_limit=1000, used=900, reserved=200)
        result = TokenUsageResult(
            allowed=False,
            budget=budget,
            estimated_cost=500,
            message="토큰 예산 부족",
        )

        assert not result.allowed
        assert "부족" in result.message

    def test_to_dict(self):
        """딕셔너리 변환"""
        budget = TokenBudget(total_limit=10000)
        result = TokenUsageResult(
            allowed=True,
            budget=budget,
            estimated_cost=500,
        )

        d = result.to_dict()

        assert d["allowed"] is True
        assert "budget" in d
        assert d["estimated_cost"] == 500


class TestTokenManager:
    """TokenManager 테스트"""

    @pytest.fixture
    def mock_usage_service(self):
        """Mock UsageService"""
        service = MagicMock()
        service.check_quota = AsyncMock(return_value={
            "within_quota": True,
            "current_tokens": 1000,
            "daily_limit": 100000,
        })
        service.track_usage = AsyncMock()
        return service

    @pytest.fixture
    def manager(self, mock_usage_service):
        """테스트용 TokenManager"""
        return TokenManager(usage_service=mock_usage_service)

    @pytest.mark.asyncio
    async def test_check_and_reserve_success(self, manager):
        """예약 성공"""
        result = await manager.check_and_reserve(
            user_id="user-123",
            session_id="session-456",
            estimated_tokens=500,
        )

        assert result.allowed
        assert result.estimated_cost == 500
        assert result.message == "OK"

        # 세션 예산 확인
        budget = manager.get_session_budget("session-456")
        assert budget is not None
        assert budget.reserved == 500

    @pytest.mark.asyncio
    async def test_check_and_reserve_quota_exceeded(self, manager, mock_usage_service):
        """쿼터 초과 시 거부"""
        mock_usage_service.check_quota = AsyncMock(return_value={
            "within_quota": False,
            "message": "일일 요청 한도 초과",
        })

        result = await manager.check_and_reserve(
            user_id="user-123",
            session_id="session-789",
            estimated_tokens=500,
        )

        assert not result.allowed
        assert "한도 초과" in result.message

    @pytest.mark.asyncio
    async def test_check_and_reserve_budget_insufficient(self, manager, mock_usage_service):
        """예산 부족 시 거부"""
        # 쿼터 확인 시 이미 총 한도에 가깝게 사용 중인 상태
        mock_usage_service.check_quota = AsyncMock(return_value={
            "within_quota": True,
            "current_tokens": 49000,  # 한도의 98% 사용
            "daily_limit": 50000,
        })

        # 예산 초과 예약 시도
        result = await manager.check_and_reserve(
            user_id="user-123",
            session_id="session-budget-test",  # 새 세션
            estimated_tokens=5000,  # 49000 + 5000 > 50000
        )

        # 예산 부족으로 거부되어야 함
        assert not result.allowed
        assert "부족" in result.message or "한도" in result.message

    @pytest.mark.asyncio
    async def test_confirm_usage(self, manager, mock_usage_service):
        """사용량 확정"""
        # 초기 current_tokens를 0으로 설정
        mock_usage_service.check_quota = AsyncMock(return_value={
            "within_quota": True,
            "current_tokens": 0,  # 초기 사용량 0
            "daily_limit": 100000,
        })

        # 먼저 예약
        await manager.check_and_reserve(
            user_id="user-123",
            session_id="session-confirm-new",  # 새 세션
            estimated_tokens=1000,
        )

        # 확정
        confirmation = await manager.confirm_usage(
            user_id="user-123",
            session_id="session-confirm-new",
            actual_tokens=800,
            estimated_tokens=1000,
        )

        assert confirmation.success
        assert confirmation.actual_tokens == 800
        assert confirmation.difference == -200  # 800 - 1000

        # 예산 업데이트 확인
        budget = manager.get_session_budget("session-confirm-new")
        assert budget.reserved == 0  # 예약 해제
        assert budget.used == 800  # 실제 사용량 반영

    @pytest.mark.asyncio
    async def test_release_reservation(self, manager):
        """예약 해제"""
        # 예약
        await manager.check_and_reserve(
            user_id="user-123",
            session_id="session-release",
            estimated_tokens=500,
        )

        # 해제
        success = await manager.release_reservation(
            session_id="session-release",
            estimated_tokens=500,
        )

        assert success

        budget = manager.get_session_budget("session-release")
        assert budget.reserved == 0


class TestSessionManagement:
    """세션 관리 테스트"""

    @pytest.fixture
    def manager(self):
        """테스트용 매니저"""
        return TokenManager(usage_service=MagicMock(
            check_quota=AsyncMock(return_value={"within_quota": True}),
            track_usage=AsyncMock(),
        ))

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, manager):
        """여러 세션 관리"""
        await manager.check_and_reserve("user", "session-1", 1000)
        await manager.check_and_reserve("user", "session-2", 2000)

        assert manager.get_session_budget("session-1") is not None
        assert manager.get_session_budget("session-2") is not None

        all_stats = manager.get_all_sessions_stats()
        assert len(all_stats) >= 2

    @pytest.mark.asyncio
    async def test_clear_session(self, manager):
        """세션 정리"""
        await manager.check_and_reserve("user", "session-clear", 1000)
        assert manager.get_session_budget("session-clear") is not None

        existed = manager.clear_session("session-clear")

        assert existed
        assert manager.get_session_budget("session-clear") is None

    def test_clear_nonexistent_session(self, manager):
        """존재하지 않는 세션 정리"""
        existed = manager.clear_session("nonexistent")
        assert not existed

    @pytest.mark.asyncio
    async def test_clear_all_sessions(self, manager):
        """모든 세션 정리"""
        await manager.check_and_reserve("user", "session-a", 1000)
        await manager.check_and_reserve("user", "session-b", 2000)

        manager.clear_all_sessions()

        assert len(manager.get_all_sessions_stats()) == 0


class TestWorkflowTokenEstimation:
    """워크플로우 토큰 추정 테스트"""

    @pytest.fixture
    def manager(self):
        """테스트용 매니저"""
        return TokenManager(usage_service=MagicMock(
            check_quota=AsyncMock(return_value={"within_quota": True}),
        ))

    @pytest.mark.asyncio
    async def test_estimate_rag_workflow(self, manager):
        """RAG 워크플로우 토큰 추정"""
        tokens = await manager.estimate_workflow_tokens("rag_workflow", "medium")

        assert tokens > 0
        assert tokens == 800  # 기본값

    @pytest.mark.asyncio
    async def test_estimate_complex_workflow(self, manager):
        """복잡한 워크플로우 토큰 추정"""
        tokens = await manager.estimate_workflow_tokens("document_workflow", "complex")

        # complex 배수 적용
        assert tokens == 3000  # 1500 * 2.0

    @pytest.mark.asyncio
    async def test_estimate_unknown_workflow(self, manager):
        """알 수 없는 워크플로우"""
        tokens = await manager.estimate_workflow_tokens("unknown_workflow", "medium")

        assert tokens == 500  # 기본값

    @pytest.mark.asyncio
    async def test_can_execute_workflow(self, manager):
        """워크플로우 실행 가능 여부"""
        result = await manager.can_execute_workflow(
            user_id="user-123",
            session_id="session-can",
            workflow_name="rag_workflow",
            complexity="medium",
        )

        assert result.allowed
        assert result.estimated_cost == 800


class TestGracefulDegradation:
    """Graceful Degradation 테스트"""

    @pytest.mark.asyncio
    async def test_quota_check_error_allows_execution(self):
        """쿼터 확인 실패 시에도 실행 허용"""
        mock_service = MagicMock()
        mock_service.check_quota = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        manager = TokenManager(usage_service=mock_service)

        result = await manager.check_and_reserve(
            user_id="user-123",
            session_id="session-degrade",
            estimated_tokens=500,
        )

        # 에러에도 불구하고 허용 (graceful degradation)
        assert result.allowed
        assert "실패" in result.message or "기본값" in result.message


class TestTokenUsageConfirmation:
    """TokenUsageConfirmation 테스트"""

    def test_confirmation_success(self):
        """확정 성공"""
        budget = TokenBudget(total_limit=10000, used=1000)
        confirmation = TokenUsageConfirmation(
            success=True,
            actual_tokens=800,
            estimated_tokens=1000,
            difference=-200,
            budget=budget,
        )

        assert confirmation.success
        assert confirmation.difference == -200

    def test_confirmation_failure(self):
        """확정 실패"""
        confirmation = TokenUsageConfirmation(
            success=False,
            actual_tokens=0,
            estimated_tokens=1000,
            difference=-1000,
            error="Tracking failed",
        )

        assert not confirmation.success
        assert confirmation.error == "Tracking failed"

    def test_to_dict(self):
        """딕셔너리 변환"""
        budget = TokenBudget(total_limit=10000, used=1000)
        confirmation = TokenUsageConfirmation(
            success=True,
            actual_tokens=800,
            estimated_tokens=1000,
            difference=-200,
            budget=budget,
        )

        d = confirmation.to_dict()

        assert d["success"] is True
        assert d["actual_tokens"] == 800
        assert d["difference"] == -200
        assert "budget" in d


class TestSingleton:
    """싱글톤 패턴 테스트"""

    def test_get_token_manager_returns_same_instance(self):
        """싱글톤 인스턴스"""
        init_token_manager()

        manager1 = get_token_manager()
        manager2 = get_token_manager()

        assert manager1 is manager2

    def test_init_creates_new_instance(self):
        """명시적 초기화"""
        manager1 = init_token_manager()
        manager2 = init_token_manager()

        assert manager1 is not manager2


class TestReservationHistory:
    """예약 이력 추적 테스트"""

    @pytest.fixture
    def manager(self):
        """테스트용 매니저"""
        return TokenManager(usage_service=MagicMock(
            check_quota=AsyncMock(return_value={"within_quota": True}),
            track_usage=AsyncMock(),
        ))

    @pytest.mark.asyncio
    async def test_reservation_recorded(self, manager):
        """예약 기록"""
        await manager.check_and_reserve("user", "session-history", 1000)

        history = manager._reservation_history.get("session-history", [])

        assert len(history) >= 1
        assert history[0]["action"] == "reserve"
        assert history[0]["tokens"] == 1000

    @pytest.mark.asyncio
    async def test_confirmation_recorded(self, manager):
        """확정 기록"""
        await manager.check_and_reserve("user", "session-confirm-hist", 1000)
        await manager.confirm_usage("user", "session-confirm-hist", 800, 1000)

        history = manager._reservation_history.get("session-confirm-hist", [])

        # 예약 + 확정 기록
        assert len(history) >= 2
        assert any(h["action"] == "confirm" for h in history)

    @pytest.mark.asyncio
    async def test_history_max_entries(self, manager):
        """이력 최대 항목 수"""
        # 많은 예약 생성
        for i in range(150):
            manager._record_reservation(f"session-max", i * 10, "reserve")

        history = manager._reservation_history.get("session-max", [])

        # 최대 100개 유지
        assert len(history) <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
