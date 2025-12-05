"""
Phase 8: 에러 복구 및 폴백 통합 테스트

테스트 항목:
1. 재시도 로직 (지수 백오프)
2. 폴백 체인 실행
3. 부분 실패 허용
4. 에러 통계 추적
5. 데코레이터 기반 복구
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from apps.ai_service.agents.error_recovery import (
    ErrorRecoveryManager,
    RetryConfig,
    RecoveryResult,
    with_recovery,
    get_recovery_manager,
    reset_recovery_manager,
)


class TestRetryConfig:
    """재시도 설정 테스트"""

    def test_default_config(self):
        """기본 설정"""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert asyncio.TimeoutError in config.retryable_exceptions

    def test_custom_config(self):
        """커스텀 설정"""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=10.0,
            exponential_base=3.0,
        )

        assert config.max_retries == 5
        assert config.base_delay == 0.5


class TestRecoveryResult:
    """복구 결과 테스트"""

    def test_success_result(self):
        """성공 결과"""
        result = RecoveryResult(
            success=True,
            data={"key": "value"},
            attempts=1,
        )

        assert result.success
        assert result.data == {"key": "value"}
        assert result.attempts == 1
        assert result.error is None

    def test_failure_result(self):
        """실패 결과"""
        result = RecoveryResult(
            success=False,
            error="Something went wrong",
            attempts=3,
        )

        assert not result.success
        assert result.error == "Something went wrong"
        assert result.attempts == 3

    def test_fallback_used(self):
        """폴백 사용 결과"""
        result = RecoveryResult(
            success=True,
            data={"fallback": True},
            attempts=4,
            fallback_used="fallback_func",
        )

        assert result.success
        assert result.fallback_used == "fallback_func"


class TestErrorRecoveryManager:
    """ErrorRecoveryManager 테스트"""

    @pytest.fixture
    def manager(self):
        """테스트용 매니저"""
        return ErrorRecoveryManager(
            RetryConfig(
                max_retries=2,
                base_delay=0.01,  # 빠른 테스트
                max_delay=0.1,
            )
        )

    @pytest.mark.asyncio
    async def test_execute_success_first_try(self, manager):
        """첫 시도에 성공"""
        async def success_func():
            return {"status": "ok"}

        result = await manager.execute_with_retry(
            success_func,
            operation_name="test_op",
        )

        assert result.success
        assert result.data == {"status": "ok"}
        assert result.attempts == 1

    @pytest.mark.asyncio
    async def test_execute_retry_then_success(self, manager):
        """재시도 후 성공"""
        call_count = 0

        async def eventual_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise asyncio.TimeoutError("Timeout")
            return {"status": "ok"}

        result = await manager.execute_with_retry(
            eventual_success,
            operation_name="retry_test",
        )

        assert result.success
        assert result.attempts == 2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_all_retries_failed(self, manager):
        """모든 재시도 실패"""
        async def always_fail():
            raise asyncio.TimeoutError("Always timeout")

        result = await manager.execute_with_retry(
            always_fail,
            operation_name="fail_test",
        )

        assert not result.success
        assert "Max retries exceeded" in result.error
        assert result.attempts == 3  # 초기 + 2회 재시도

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self, manager):
        """재시도 불가능한 예외"""
        async def value_error():
            raise ValueError("Invalid value")

        result = await manager.execute_with_retry(
            value_error,
            operation_name="non_retry_test",
        )

        assert not result.success
        assert "Invalid value" in result.error
        assert result.attempts == 1  # 재시도 없음


class TestFallbackExecution:
    """폴백 실행 테스트"""

    @pytest.fixture
    def manager(self):
        """테스트용 매니저"""
        return ErrorRecoveryManager(
            RetryConfig(
                max_retries=1,
                base_delay=0.01,
            )
        )

    @pytest.mark.asyncio
    async def test_fallback_success(self, manager):
        """폴백 성공"""
        async def primary_fail():
            raise ConnectionError("Primary failed")

        async def fallback_success():
            return {"from": "fallback"}

        result = await manager.execute_with_retry(
            primary_fail,
            fallback_funcs=[fallback_success],
            operation_name="fallback_test",
        )

        assert result.success
        assert result.data == {"from": "fallback"}
        assert "fallback" in result.fallback_used

    @pytest.mark.asyncio
    async def test_multiple_fallbacks(self, manager):
        """여러 폴백 시도"""
        call_order = []

        async def primary():
            call_order.append("primary")
            raise ConnectionError("Primary failed")

        async def fallback1():
            call_order.append("fallback1")
            raise ConnectionError("Fallback1 failed")

        async def fallback2():
            call_order.append("fallback2")
            return {"from": "fallback2"}

        result = await manager.execute_with_retry(
            primary,
            fallback_funcs=[fallback1, fallback2],
            operation_name="multi_fallback",
        )

        assert result.success
        assert result.data == {"from": "fallback2"}
        assert "primary" in call_order
        assert "fallback1" in call_order
        assert "fallback2" in call_order

    @pytest.mark.asyncio
    async def test_all_fallbacks_fail(self, manager):
        """모든 폴백 실패"""
        async def always_fail():
            raise ConnectionError("Always fail")

        result = await manager.execute_with_retry(
            always_fail,
            fallback_funcs=[always_fail, always_fail],
            operation_name="all_fail",
        )

        assert not result.success


class TestExponentialBackoff:
    """지수 백오프 테스트"""

    def test_delay_calculation(self):
        """지연 시간 계산"""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
        )
        manager = ErrorRecoveryManager(config)

        # 첫 번째 재시도: 1 * 2^0 = 1
        assert manager._calculate_delay(1) == 1.0

        # 두 번째 재시도: 1 * 2^1 = 2
        assert manager._calculate_delay(2) == 2.0

        # 세 번째 재시도: 1 * 2^2 = 4
        assert manager._calculate_delay(3) == 4.0

    def test_delay_capped_at_max(self):
        """최대 지연 시간 제한"""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
        )
        manager = ErrorRecoveryManager(config)

        # 10번째 재시도: 1 * 2^9 = 512 → max_delay = 5
        assert manager._calculate_delay(10) == 5.0


class TestErrorStatistics:
    """에러 통계 테스트"""

    @pytest.fixture
    def manager(self):
        """테스트용 매니저"""
        return ErrorRecoveryManager(
            RetryConfig(max_retries=0, base_delay=0.01)
        )

    @pytest.mark.asyncio
    async def test_error_count_tracking(self, manager):
        """에러 카운트 추적"""
        async def fail_func():
            raise asyncio.TimeoutError("Timeout")

        # 여러 번 실패
        await manager.execute_with_retry(fail_func, operation_name="op1")
        await manager.execute_with_retry(fail_func, operation_name="op1")
        await manager.execute_with_retry(fail_func, operation_name="op2")

        stats = manager.get_error_stats()

        assert stats.get("op1", 0) >= 1
        assert stats.get("op2", 0) >= 1

    def test_reset_error_counts(self, manager):
        """에러 카운트 리셋"""
        manager._error_counts["test"] = 5
        manager.reset_error_counts()

        assert manager.get_error_stats() == {}


class TestWithRecoveryDecorator:
    """복구 데코레이터 테스트"""

    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """데코레이터 성공 케이스"""
        @with_recovery(max_retries=1)
        async def decorated_func():
            return {"status": "ok"}

        result = await decorated_func()

        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_decorator_with_retry(self):
        """데코레이터 재시도"""
        call_count = 0

        @with_recovery(max_retries=3, base_delay=0.01)
        async def retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise asyncio.TimeoutError("Timeout")
            return {"attempt": call_count}

        result = await retry_func()

        assert result == {"attempt": 2}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_with_fallback(self):
        """데코레이터 폴백"""
        async def fallback():
            return {"from": "fallback"}

        @with_recovery(max_retries=0, fallback=fallback)
        async def primary():
            raise ConnectionError("Primary failed")

        result = await primary()

        assert result == {"from": "fallback"}

    @pytest.mark.asyncio
    async def test_decorator_raises_on_failure(self):
        """데코레이터 최종 실패 시 예외 발생"""
        @with_recovery(max_retries=1, base_delay=0.01)
        async def always_fail():
            raise asyncio.TimeoutError("Always fail")

        with pytest.raises(RuntimeError) as exc_info:
            await always_fail()

        assert "Max retries exceeded" in str(exc_info.value)


class TestSyncFunctionSupport:
    """동기 함수 지원 테스트"""

    @pytest.fixture
    def manager(self):
        """테스트용 매니저"""
        return ErrorRecoveryManager(
            RetryConfig(max_retries=1, base_delay=0.01)
        )

    @pytest.mark.asyncio
    async def test_sync_function_execution(self, manager):
        """동기 함수 실행"""
        def sync_func():
            return {"status": "sync_ok"}

        result = await manager.execute_with_retry(
            sync_func,
            operation_name="sync_test",
        )

        assert result.success
        assert result.data == {"status": "sync_ok"}


class TestSingleton:
    """싱글톤 패턴 테스트"""

    def test_get_recovery_manager(self):
        """싱글톤 인스턴스"""
        reset_recovery_manager()

        manager1 = get_recovery_manager()
        manager2 = get_recovery_manager()

        assert manager1 is manager2

    def test_reset_recovery_manager(self):
        """싱글톤 리셋"""
        manager1 = get_recovery_manager()
        reset_recovery_manager()
        manager2 = get_recovery_manager()

        assert manager1 is not manager2


class TestIntegrationWithToolRegistry:
    """ToolRegistry와의 통합 테스트"""

    @pytest.mark.asyncio
    async def test_tool_execution_with_recovery(self):
        """도구 실행 시 복구 적용"""
        from apps.ai_service.agents.tools.registry import ToolRegistry

        registry = ToolRegistry()

        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(success=False, error="First attempt failed")
            return MagicMock(success=True, data={"result": "recovered"})

        with patch.object(registry._executor, "execute", side_effect=mock_execute):
            result = await registry.execute_tool(
                "search_legal",
                {"query": "테스트"},
                max_retries=2,
                use_fallback=False,
            )

        # 재시도 후 성공
        assert call_count >= 2


class TestTotalExecutionTime:
    """총 실행 시간 추적 테스트"""

    @pytest.fixture
    def manager(self):
        """테스트용 매니저"""
        return ErrorRecoveryManager(
            RetryConfig(max_retries=1, base_delay=0.05)
        )

    @pytest.mark.asyncio
    async def test_total_time_tracking(self, manager):
        """총 실행 시간 추적"""
        import time

        async def delayed_success():
            await asyncio.sleep(0.05)
            return {"status": "ok"}

        start = time.time()
        result = await manager.execute_with_retry(
            delayed_success,
            operation_name="time_test",
        )
        actual_time = time.time() - start

        assert result.total_time > 0
        assert result.total_time <= actual_time + 0.1  # 약간의 오차 허용


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
