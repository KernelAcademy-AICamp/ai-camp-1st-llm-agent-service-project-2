"""
Error Recovery - 에러 복구 및 폴백 관리 (Phase 7)

기능:
- 재시도 로직 (지수 백오프)
- 폴백 체인 관리
- 부분 실패 허용
- 에러 로깅 및 추적
"""

import asyncio
import logging
from typing import Callable, Any, List, Optional, TypeVar, Dict, Tuple
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RetryConfig:
    """재시도 설정"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_exceptions: Tuple[type, ...] = (
        asyncio.TimeoutError,
        ConnectionError,
        TimeoutError,
    )


@dataclass
class RecoveryResult:
    """복구 결과"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    attempts: int = 0
    fallback_used: Optional[str] = None
    total_time: float = 0.0


class ErrorRecoveryManager:
    """
    에러 복구 관리자

    재시도, 폴백, 부분 실패 처리를 담당합니다.
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._error_counts: Dict[str, int] = {}

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        fallback_funcs: Optional[List[Callable]] = None,
        operation_name: str = "operation",
        **kwargs,
    ) -> RecoveryResult:
        """
        재시도 및 폴백과 함께 함수 실행

        Args:
            func: 실행할 함수
            *args: 함수에 전달할 위치 인자
            fallback_funcs: 폴백 함수 목록
            operation_name: 작업 이름 (로깅용)
            **kwargs: 함수에 전달할 키워드 인자

        Returns:
            RecoveryResult
        """
        import time
        start_time = time.time()

        # 1. 메인 함수 재시도
        result = await self._execute_with_retries(
            func, args, kwargs, operation_name
        )

        if result.success:
            result.total_time = time.time() - start_time
            return result

        # 2. 폴백 시도
        if fallback_funcs:
            for i, fallback_func in enumerate(fallback_funcs):
                fallback_name = f"{operation_name}_fallback_{i}"
                logger.info(f"[ErrorRecovery] Trying fallback: {fallback_name}")

                fallback_result = await self._execute_with_retries(
                    fallback_func, args, kwargs, fallback_name,
                    max_retries=1,  # 폴백은 1회만
                )

                if fallback_result.success:
                    fallback_result.fallback_used = fallback_name
                    fallback_result.total_time = time.time() - start_time
                    fallback_result.attempts += result.attempts
                    return fallback_result

        result.total_time = time.time() - start_time
        return result

    async def _execute_with_retries(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        operation_name: str,
        max_retries: Optional[int] = None,
    ) -> RecoveryResult:
        """재시도 로직"""
        max_retries = max_retries if max_retries is not None else self.config.max_retries
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = self._calculate_delay(attempt)
                    logger.info(
                        f"[ErrorRecovery] Retry {attempt}/{max_retries} "
                        f"for {operation_name}, waiting {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)

                # 실행
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                return RecoveryResult(
                    success=True,
                    data=result,
                    attempts=attempt + 1,
                )

            except self.config.retryable_exceptions as e:
                last_error = str(e)
                logger.warning(
                    f"[ErrorRecovery] Retryable error in {operation_name}: {e}"
                )
                self._increment_error_count(operation_name)

            except Exception as e:
                # 재시도 불가능한 에러
                logger.error(
                    f"[ErrorRecovery] Non-retryable error in {operation_name}: {e}"
                )
                return RecoveryResult(
                    success=False,
                    error=str(e),
                    attempts=attempt + 1,
                )

        return RecoveryResult(
            success=False,
            error=f"Max retries exceeded: {last_error}",
            attempts=max_retries + 1,
        )

    def _calculate_delay(self, attempt: int) -> float:
        """지수 백오프 지연 계산"""
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        return min(delay, self.config.max_delay)

    def _increment_error_count(self, operation_name: str):
        """에러 카운트 증가"""
        self._error_counts[operation_name] = \
            self._error_counts.get(operation_name, 0) + 1

    def get_error_stats(self) -> Dict[str, int]:
        """에러 통계 반환"""
        return dict(self._error_counts)

    def reset_error_counts(self):
        """에러 카운트 리셋"""
        self._error_counts.clear()


# 데코레이터 버전
def with_recovery(
    max_retries: int = 3,
    fallback: Optional[Callable] = None,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
):
    """
    에러 복구 데코레이터

    Usage:
        @with_recovery(max_retries=3)
        async def my_function():
            ...

        @with_recovery(max_retries=2, fallback=fallback_func)
        async def my_function_with_fallback():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            manager = ErrorRecoveryManager(
                RetryConfig(
                    max_retries=max_retries,
                    base_delay=base_delay,
                    max_delay=max_delay,
                )
            )
            fallbacks = [fallback] if fallback else None
            result = await manager.execute_with_retry(
                func, *args,
                fallback_funcs=fallbacks,
                operation_name=func.__name__,
                **kwargs,
            )

            if result.success:
                return result.data
            else:
                raise RuntimeError(result.error)

        return wrapper
    return decorator


# 싱글톤 인스턴스
_recovery_manager: Optional[ErrorRecoveryManager] = None


def get_recovery_manager(config: Optional[RetryConfig] = None) -> ErrorRecoveryManager:
    """ErrorRecoveryManager 싱글톤"""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = ErrorRecoveryManager(config)
    return _recovery_manager


def reset_recovery_manager():
    """싱글톤 인스턴스 리셋 (테스트용)"""
    global _recovery_manager
    _recovery_manager = None
