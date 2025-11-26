"""
Metrics Collector for Performance Benchmarking

Collects various metrics during benchmark execution:
- Performance metrics (response time, CPU, memory)
- LLM metrics (tokens, cost)
- Database metrics (query count, query time)
"""

import time
import psutil
import platform
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single operation"""
    operation: str
    start_time: str
    end_time: str
    duration_ms: float
    cpu_percent_before: float
    cpu_percent_after: float
    memory_mb_before: float
    memory_mb_after: float
    status: str  # 'success' or 'error'
    error_message: Optional[str] = None


@dataclass
class LLMMetrics:
    """LLM-specific metrics"""
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_name: str = ""


@dataclass
class DatabaseMetrics:
    """Database-specific metrics"""
    query_count: int = 0
    total_query_time_ms: float = 0.0
    avg_query_time_ms: float = 0.0


@dataclass
class BenchmarkResult:
    """Complete benchmark result for a single test"""
    test_id: str
    test_name: str
    category: str
    performance: PerformanceMetrics = None
    llm: LLMMetrics = field(default_factory=LLMMetrics)
    database: DatabaseMetrics = field(default_factory=DatabaseMetrics)
    response_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "category": self.category,
        }
        if self.performance:
            result["performance"] = asdict(self.performance)
        if self.llm:
            result["llm"] = asdict(self.llm)
        if self.database:
            result["database"] = asdict(self.database)
        if self.response_data:
            result["response_data"] = self.response_data
        return result


class MetricsCollector:
    """Collects performance, LLM, and database metrics"""

    # LLM pricing (per 1K tokens) - approximations
    LLM_PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "default": {"input": 0.002, "output": 0.006}
    }

    def __init__(self):
        self.process = psutil.Process()

    def get_cpu_percent(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return self.process.cpu_percent(interval=0.1)
        except Exception:
            return 0.0

    def get_memory_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            return self.process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    def collect_performance_metrics(
        self,
        operation: str,
        func: Callable,
        *args,
        **kwargs
    ) -> tuple[PerformanceMetrics, Any]:
        """
        Execute a function and collect performance metrics.

        Args:
            operation: Name of the operation
            func: Function to execute
            *args, **kwargs: Arguments for the function

        Returns:
            Tuple of (PerformanceMetrics, function result)
        """
        # Before metrics
        cpu_before = self.get_cpu_percent()
        memory_before = self.get_memory_mb()
        start_time = datetime.now()

        # Execute
        result = None
        error_message = None
        status = "success"

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            status = "error"
            error_message = str(e)

        # After metrics
        end_time = datetime.now()
        cpu_after = self.get_cpu_percent()
        memory_after = self.get_memory_mb()

        duration_ms = (end_time - start_time).total_seconds() * 1000

        metrics = PerformanceMetrics(
            operation=operation,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_ms=round(duration_ms, 2),
            cpu_percent_before=round(cpu_before, 2),
            cpu_percent_after=round(cpu_after, 2),
            memory_mb_before=round(memory_before, 2),
            memory_mb_after=round(memory_after, 2),
            status=status,
            error_message=error_message
        )

        return metrics, result

    def collect_llm_metrics(self, response: Dict[str, Any]) -> LLMMetrics:
        """
        Extract LLM metrics from API response.

        Args:
            response: API response containing LLM metadata

        Returns:
            LLMMetrics object
        """
        # Try to extract from different response formats
        usage = response.get("usage", {})
        meta = response.get("meta", {})

        total_tokens = (
            usage.get("total_tokens") or
            meta.get("total_tokens") or
            response.get("total_tokens", 0)
        )

        prompt_tokens = (
            usage.get("prompt_tokens") or
            meta.get("prompt_tokens") or
            response.get("prompt_tokens", 0)
        )

        completion_tokens = (
            usage.get("completion_tokens") or
            meta.get("completion_tokens") or
            response.get("completion_tokens", 0)
        )

        model_name = (
            response.get("model") or
            meta.get("model") or
            response.get("llm_model", "default")
        )

        # Calculate cost
        estimated_cost = self.estimate_cost(
            prompt_tokens,
            completion_tokens,
            model_name
        )

        return LLMMetrics(
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=round(estimated_cost, 6),
            model_name=model_name
        )

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model_name: str
    ) -> float:
        """
        Estimate cost based on token usage and model.

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            model_name: Name of the model used

        Returns:
            Estimated cost in USD
        """
        # Normalize model name
        model_key = "default"
        for key in self.LLM_PRICING:
            if key in model_name.lower():
                model_key = key
                break

        pricing = self.LLM_PRICING.get(model_key, self.LLM_PRICING["default"])

        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]

        return input_cost + output_cost

    def collect_database_metrics(
        self,
        query_count: int = 0,
        total_query_time_ms: float = 0.0
    ) -> DatabaseMetrics:
        """
        Create database metrics.

        Args:
            query_count: Number of database queries
            total_query_time_ms: Total time spent on queries

        Returns:
            DatabaseMetrics object
        """
        avg_time = total_query_time_ms / query_count if query_count > 0 else 0.0

        return DatabaseMetrics(
            query_count=query_count,
            total_query_time_ms=round(total_query_time_ms, 2),
            avg_query_time_ms=round(avg_time, 2)
        )

    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get system information for benchmark metadata"""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2)
        }


class TimingContext:
    """Context manager for timing code blocks"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration_ms = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        return False
