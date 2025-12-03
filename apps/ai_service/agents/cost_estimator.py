"""
Cost Estimator - 실행 비용 추정 (Phase 7)

Agent 실행 전후의 토큰 비용을 추정하고 추적하는 모듈입니다.

주요 기능:
- 도구/워크플로우 실행 전 토큰 비용 예상
- 복잡도별 예상 비용 계산
- LLM 모델별 실제 비용 계산 (USD/KRW)
- 비용 초과 시 경고/차단 지원
- 실행 후 실제 비용 추적 및 비교

Phase 1 (ToolRegistry) 및 Phase 4 (TokenManager)와 연동됩니다.

설계 문서: docs/adaptive-agent/07_IMPLEMENTATION_GUIDE.md - 8. 단계별 비용 추정
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# 상수 정의
# =============================================================================

class CostTier(str, Enum):
    """비용 등급"""
    LOW = "low"           # 저비용 (캐시 히트, 일반 대화)
    MEDIUM = "medium"     # 중간 비용 (단일 워크플로우)
    HIGH = "high"         # 고비용 (복합 워크플로우)
    VERY_HIGH = "very_high"  # 매우 높은 비용 (THINKING 경로)


# 복잡도별 기본 토큰 비용
COMPLEXITY_BASE_TOKENS: Dict[str, int] = {
    "FAST": 200,          # 캐시 히트, 일반 대화
    "MEDIUM": 800,        # 단일 워크플로우
    "DEEP": 2000,         # 복합 워크플로우
    "THINKING": 3000,     # ReAct 자율 추론
}

# 워크플로우별 예상 토큰
WORKFLOW_ESTIMATED_TOKENS: Dict[str, int] = {
    "rag_workflow": 800,
    "document_workflow": 1500,
    "case_workflow": 1200,
    "risk_workflow": 1000,
    "llm_comparison_workflow": 3000,
}

# LLM 모델별 토큰 비용 (USD per 1M tokens)
MODEL_COSTS: Dict[str, Dict[str, float]] = {
    # OpenAI 모델
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},

    # Anthropic Claude 모델
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},

    # 기본값 (알 수 없는 모델)
    "default": {"input": 1.00, "output": 3.00},
}

# 환율 (USD to KRW) - 실제 운영 시 동적으로 가져오거나 설정 파일에서 관리
USD_TO_KRW = 1350.0

# 비용 임계값 (USD)
COST_THRESHOLDS: Dict[str, float] = {
    "warning": 0.01,      # 경고 표시 임계값
    "confirm": 0.05,      # 사용자 확인 요청 임계값
    "block": 0.10,        # 차단 임계값
}


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class CostEstimate:
    """
    비용 추정 결과

    실행 전 예상 토큰/비용을 담습니다.
    """
    # 토큰 추정
    estimated_tokens: int
    estimated_input_tokens: int
    estimated_output_tokens: int

    # 비용 추정
    estimated_cost_usd: float
    estimated_cost_krw: float

    # 상세 정보
    breakdown: Dict[str, int]  # 항목별 토큰
    model: str
    confidence: float  # 추정 신뢰도 (0.0-1.0)

    # 비용 등급
    cost_tier: CostTier = CostTier.MEDIUM

    # 경고/차단 정보
    needs_warning: bool = False
    needs_confirmation: bool = False
    should_block: bool = False
    warning_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "estimated_tokens": self.estimated_tokens,
            "estimated_input_tokens": self.estimated_input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "estimated_cost_krw": round(self.estimated_cost_krw, 2),
            "breakdown": self.breakdown,
            "model": self.model,
            "confidence": round(self.confidence, 2),
            "cost_tier": self.cost_tier.value,
            "needs_warning": self.needs_warning,
            "needs_confirmation": self.needs_confirmation,
            "should_block": self.should_block,
            "warning_message": self.warning_message,
        }


@dataclass
class ActualCost:
    """
    실제 비용 결과

    실행 후 실제 사용된 토큰/비용을 담습니다.
    """
    # 실제 토큰
    actual_tokens: int
    actual_input_tokens: int
    actual_output_tokens: int

    # 실제 비용
    actual_cost_usd: float
    actual_cost_krw: float

    # 예상치와 비교
    estimated_tokens: int
    token_difference: int  # actual - estimated
    cost_difference_usd: float

    # 추가 정보
    model: str
    execution_time: float
    tool_calls: int

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "actual_tokens": self.actual_tokens,
            "actual_input_tokens": self.actual_input_tokens,
            "actual_output_tokens": self.actual_output_tokens,
            "actual_cost_usd": round(self.actual_cost_usd, 6),
            "actual_cost_krw": round(self.actual_cost_krw, 2),
            "estimated_tokens": self.estimated_tokens,
            "token_difference": self.token_difference,
            "token_accuracy": round(self._calculate_accuracy(), 2),
            "cost_difference_usd": round(self.cost_difference_usd, 6),
            "model": self.model,
            "execution_time": round(self.execution_time, 3),
            "tool_calls": self.tool_calls,
        }

    def _calculate_accuracy(self) -> float:
        """추정 정확도 계산 (%)"""
        if self.estimated_tokens == 0:
            return 0.0
        accuracy = 1 - abs(self.token_difference) / self.estimated_tokens
        return max(0.0, accuracy * 100)


@dataclass
class CostSummary:
    """
    세션/요청별 비용 요약
    """
    session_id: str
    total_requests: int
    total_estimated_tokens: int
    total_actual_tokens: int
    total_estimated_cost_usd: float
    total_actual_cost_usd: float
    average_accuracy: float
    cost_breakdown: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "total_requests": self.total_requests,
            "total_estimated_tokens": self.total_estimated_tokens,
            "total_actual_tokens": self.total_actual_tokens,
            "total_estimated_cost_usd": round(self.total_estimated_cost_usd, 6),
            "total_actual_cost_usd": round(self.total_actual_cost_usd, 6),
            "total_estimated_cost_krw": round(self.total_estimated_cost_usd * USD_TO_KRW, 2),
            "total_actual_cost_krw": round(self.total_actual_cost_usd * USD_TO_KRW, 2),
            "average_accuracy": round(self.average_accuracy, 2),
            "cost_breakdown": self.cost_breakdown,
        }


# =============================================================================
# CostEstimator 클래스
# =============================================================================

class CostEstimator:
    """
    비용 추정기

    실행 전 예상 토큰/비용 계산 및 실행 후 실제 비용 추적을 담당합니다.
    ToolRegistry의 estimate_cost()와 연동하여 도구별 비용을 계산합니다.

    Usage:
        estimator = CostEstimator(model="gpt-4o-mini")

        # 1. 실행 전 비용 추정
        estimate = estimator.estimate_for_complexity(
            complexity="MEDIUM",
            tool_names=["search_legal"],
            message_length=100,
        )

        if estimate.should_block:
            # 비용 초과로 차단
            return error_response

        # 2. 실행 후 실제 비용 계산
        actual = estimator.calculate_actual_cost(
            input_tokens=500,
            output_tokens=300,
            execution_time=2.5,
            tool_calls=1,
            estimated_tokens=estimate.estimated_tokens,
        )
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        exchange_rate: float = USD_TO_KRW,
    ):
        """
        CostEstimator 초기화

        Args:
            model: LLM 모델명
            exchange_rate: USD to KRW 환율
        """
        self.model = model
        self.exchange_rate = exchange_rate
        self.model_costs = self._get_model_costs(model)
        self._session_costs: Dict[str, List[ActualCost]] = {}

        logger.info(
            f"CostEstimator initialized: model={model}, "
            f"costs={self.model_costs}"
        )

    def _get_model_costs(self, model: str) -> Dict[str, float]:
        """모델별 비용 조회"""
        if model in MODEL_COSTS:
            return MODEL_COSTS[model]

        # 부분 매칭 시도
        for model_key, costs in MODEL_COSTS.items():
            if model_key in model or model in model_key:
                return costs

        logger.warning(f"Unknown model: {model}, using default costs")
        return MODEL_COSTS["default"]

    # =========================================================================
    # 비용 추정 메서드
    # =========================================================================

    def estimate_for_complexity(
        self,
        complexity: str,
        tool_names: Optional[List[str]] = None,
        message_length: int = 0,
        has_attachments: bool = False,
        attachment_size: int = 0,
    ) -> CostEstimate:
        """
        복잡도 기반 비용 추정

        Args:
            complexity: 복잡도 레벨 ("FAST", "MEDIUM", "DEEP", "THINKING")
            tool_names: 사용할 도구/워크플로우 목록
            message_length: 사용자 메시지 길이 (문자)
            has_attachments: 첨부 파일 여부
            attachment_size: 첨부 파일 총 크기 (bytes)

        Returns:
            CostEstimate
        """
        breakdown: Dict[str, int] = {}

        # 1. 기본 비용 (복잡도별)
        base_tokens = COMPLEXITY_BASE_TOKENS.get(complexity, 500)
        breakdown["base"] = base_tokens

        # 2. 메시지 길이 기반 추가 (대략 4자당 1토큰)
        message_tokens = max(0, message_length // 4)
        breakdown["message"] = message_tokens

        # 3. 첨부 파일 추가 비용
        if has_attachments:
            # 기본 첨부 파일 처리 비용 + 크기 기반 추가
            attachment_tokens = 500  # 기본값
            if attachment_size > 0:
                # 대략 1KB당 50토큰 추가
                attachment_tokens += min(5000, attachment_size // 1024 * 50)
            breakdown["attachments"] = attachment_tokens

        # 4. 도구/워크플로우별 토큰 추가
        tool_tokens = self._calculate_tool_tokens(tool_names)
        breakdown["tools"] = tool_tokens

        # 5. 총 토큰 계산
        total_tokens = sum(breakdown.values())

        # 6. 입력/출력 비율 추정 (복잡도별 조정)
        input_ratio = self._get_input_ratio(complexity)
        input_tokens = int(total_tokens * input_ratio)
        output_tokens = total_tokens - input_tokens

        # 7. 비용 계산
        cost_usd = self._calculate_cost_usd(input_tokens, output_tokens)
        cost_krw = cost_usd * self.exchange_rate

        # 8. 신뢰도 계산
        confidence = self._calculate_confidence(
            complexity, tool_names, has_attachments
        )

        # 9. 비용 등급 결정
        cost_tier = self._determine_cost_tier(cost_usd, complexity)

        # 10. 경고/차단 여부 결정
        needs_warning, needs_confirmation, should_block, warning_msg = \
            self._check_cost_thresholds(cost_usd)

        estimate = CostEstimate(
            estimated_tokens=total_tokens,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost_usd=cost_usd,
            estimated_cost_krw=cost_krw,
            breakdown=breakdown,
            model=self.model,
            confidence=confidence,
            cost_tier=cost_tier,
            needs_warning=needs_warning,
            needs_confirmation=needs_confirmation,
            should_block=should_block,
            warning_message=warning_msg,
        )

        logger.debug(
            f"[CostEstimator] estimate_for_complexity: "
            f"complexity={complexity}, tokens={total_tokens}, "
            f"cost_usd={cost_usd:.6f}, tier={cost_tier.value}"
        )

        return estimate

    def estimate_for_plan(
        self,
        plan_steps: List[Dict[str, Any]],
        message_length: int = 0,
    ) -> CostEstimate:
        """
        실행 계획 기반 비용 추정

        DeepPlan 또는 QuickPlan의 단계별 비용을 계산합니다.

        Args:
            plan_steps: 실행 계획 단계 목록
                [{"step_id": "...", "tool_name": "...", "workflow_name": "..."}]
            message_length: 사용자 메시지 길이

        Returns:
            CostEstimate
        """
        breakdown: Dict[str, int] = {}
        breakdown["message"] = max(0, message_length // 4)

        # 각 단계별 토큰 계산
        for step in plan_steps:
            step_id = step.get("step_id", f"step_{len(breakdown)}")
            tool_name = step.get("tool_name") or step.get("workflow_name")

            if tool_name:
                step_tokens = self._get_single_tool_tokens(tool_name)
            else:
                step_tokens = 500  # 기본값

            breakdown[f"step_{step_id}"] = step_tokens

        total_tokens = sum(breakdown.values())
        input_tokens = int(total_tokens * 0.65)  # 계획 기반은 입력이 더 많음
        output_tokens = total_tokens - input_tokens

        cost_usd = self._calculate_cost_usd(input_tokens, output_tokens)
        cost_krw = cost_usd * self.exchange_rate

        # 계획 기반은 신뢰도가 더 높음
        confidence = 0.75 if len(plan_steps) <= 3 else 0.65

        cost_tier = self._determine_cost_tier(cost_usd, "DEEP")
        needs_warning, needs_confirmation, should_block, warning_msg = \
            self._check_cost_thresholds(cost_usd)

        return CostEstimate(
            estimated_tokens=total_tokens,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost_usd=cost_usd,
            estimated_cost_krw=cost_krw,
            breakdown=breakdown,
            model=self.model,
            confidence=confidence,
            cost_tier=cost_tier,
            needs_warning=needs_warning,
            needs_confirmation=needs_confirmation,
            should_block=should_block,
            warning_message=warning_msg,
        )

    def estimate_for_tools(
        self,
        tool_names: List[str],
        message_length: int = 0,
    ) -> CostEstimate:
        """
        도구 목록 기반 비용 추정

        ToolRegistry의 estimate_cost()와 연동합니다.

        Args:
            tool_names: 실행할 도구 목록
            message_length: 사용자 메시지 길이

        Returns:
            CostEstimate
        """
        # ToolRegistry에서 도구별 비용 가져오기
        try:
            from apps.ai_service.agents.tools.registry import get_tool_registry
            registry = get_tool_registry()
            registry_estimate = registry.estimate_cost(tool_names)
            tool_tokens = registry_estimate.get("total_estimated_tokens", 0)
        except Exception as e:
            logger.warning(f"Failed to get registry estimate: {e}")
            tool_tokens = self._calculate_tool_tokens(tool_names)

        breakdown = {
            "message": max(0, message_length // 4),
            "tools": tool_tokens,
        }

        total_tokens = sum(breakdown.values())
        input_tokens = int(total_tokens * 0.6)
        output_tokens = total_tokens - input_tokens

        cost_usd = self._calculate_cost_usd(input_tokens, output_tokens)
        cost_krw = cost_usd * self.exchange_rate

        confidence = 0.7 if tool_tokens > 0 else 0.5
        cost_tier = self._determine_cost_tier(cost_usd, "MEDIUM")
        needs_warning, needs_confirmation, should_block, warning_msg = \
            self._check_cost_thresholds(cost_usd)

        return CostEstimate(
            estimated_tokens=total_tokens,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost_usd=cost_usd,
            estimated_cost_krw=cost_krw,
            breakdown=breakdown,
            model=self.model,
            confidence=confidence,
            cost_tier=cost_tier,
            needs_warning=needs_warning,
            needs_confirmation=needs_confirmation,
            should_block=should_block,
            warning_message=warning_msg,
        )

    # =========================================================================
    # 실제 비용 계산 메서드
    # =========================================================================

    def calculate_actual_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        execution_time: float = 0.0,
        tool_calls: int = 0,
        estimated_tokens: int = 0,
        session_id: Optional[str] = None,
    ) -> ActualCost:
        """
        실제 비용 계산

        실행 후 실제 사용된 토큰으로 비용을 계산하고,
        예상치와 비교합니다.

        Args:
            input_tokens: 실제 입력 토큰 수
            output_tokens: 실제 출력 토큰 수
            execution_time: 실행 시간 (초)
            tool_calls: 도구 호출 횟수
            estimated_tokens: 예상했던 토큰 수
            session_id: 세션 ID (세션별 집계용)

        Returns:
            ActualCost
        """
        actual_tokens = input_tokens + output_tokens
        actual_cost_usd = self._calculate_cost_usd(input_tokens, output_tokens)
        actual_cost_krw = actual_cost_usd * self.exchange_rate

        # 예상 비용 계산 (비교용)
        estimated_input = int(estimated_tokens * 0.6)
        estimated_output = estimated_tokens - estimated_input
        estimated_cost_usd = self._calculate_cost_usd(
            estimated_input, estimated_output
        )

        actual = ActualCost(
            actual_tokens=actual_tokens,
            actual_input_tokens=input_tokens,
            actual_output_tokens=output_tokens,
            actual_cost_usd=actual_cost_usd,
            actual_cost_krw=actual_cost_krw,
            estimated_tokens=estimated_tokens,
            token_difference=actual_tokens - estimated_tokens,
            cost_difference_usd=actual_cost_usd - estimated_cost_usd,
            model=self.model,
            execution_time=execution_time,
            tool_calls=tool_calls,
        )

        # 세션별 집계
        if session_id:
            self._record_session_cost(session_id, actual)

        logger.debug(
            f"[CostEstimator] calculate_actual_cost: "
            f"tokens={actual_tokens}, estimated={estimated_tokens}, "
            f"diff={actual.token_difference}, cost_usd={actual_cost_usd:.6f}"
        )

        return actual

    def get_session_summary(self, session_id: str) -> Optional[CostSummary]:
        """
        세션별 비용 요약 조회

        Args:
            session_id: 세션 ID

        Returns:
            CostSummary 또는 None
        """
        if session_id not in self._session_costs:
            return None

        costs = self._session_costs[session_id]
        if not costs:
            return None

        total_estimated = sum(c.estimated_tokens for c in costs)
        total_actual = sum(c.actual_tokens for c in costs)
        total_estimated_cost = sum(
            self._calculate_cost_usd(
                int(c.estimated_tokens * 0.6),
                int(c.estimated_tokens * 0.4)
            )
            for c in costs
        )
        total_actual_cost = sum(c.actual_cost_usd for c in costs)

        # 평균 정확도
        accuracies = [c._calculate_accuracy() for c in costs]
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0

        return CostSummary(
            session_id=session_id,
            total_requests=len(costs),
            total_estimated_tokens=total_estimated,
            total_actual_tokens=total_actual,
            total_estimated_cost_usd=total_estimated_cost,
            total_actual_cost_usd=total_actual_cost,
            average_accuracy=avg_accuracy,
        )

    def clear_session_costs(self, session_id: str):
        """세션 비용 기록 삭제"""
        self._session_costs.pop(session_id, None)

    # =========================================================================
    # 내부 헬퍼 메서드
    # =========================================================================

    def _calculate_tool_tokens(
        self,
        tool_names: Optional[List[str]],
    ) -> int:
        """도구 목록의 총 예상 토큰 계산"""
        if not tool_names:
            return 0

        total = 0
        for name in tool_names:
            total += self._get_single_tool_tokens(name)

        return total

    def _get_single_tool_tokens(self, tool_name: str) -> int:
        """단일 도구의 예상 토큰"""
        # 워크플로우 매핑에서 찾기
        if tool_name in WORKFLOW_ESTIMATED_TOKENS:
            return WORKFLOW_ESTIMATED_TOKENS[tool_name]

        # ToolRegistry에서 찾기
        try:
            from apps.ai_service.agents.tools.registry import get_tool_registry
            registry = get_tool_registry()
            tool = registry.get_tool(tool_name)
            if tool:
                return tool.estimated_tokens
        except Exception:
            pass

        # 기본값
        return 500

    def _get_input_ratio(self, complexity: str) -> float:
        """복잡도별 입력 토큰 비율"""
        ratios = {
            "FAST": 0.8,      # 입력이 대부분
            "MEDIUM": 0.65,   # 입력 > 출력
            "DEEP": 0.55,     # 비슷
            "THINKING": 0.45, # 출력이 더 많음 (추론)
        }
        return ratios.get(complexity, 0.6)

    def _calculate_cost_usd(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """USD 비용 계산"""
        input_cost = (input_tokens / 1_000_000) * self.model_costs["input"]
        output_cost = (output_tokens / 1_000_000) * self.model_costs["output"]
        return input_cost + output_cost

    def _calculate_confidence(
        self,
        complexity: str,
        tool_names: Optional[List[str]],
        has_attachments: bool,
    ) -> float:
        """추정 신뢰도 계산"""
        confidence = 0.8  # 기본값

        # 도구가 명시된 경우 신뢰도 상승
        if tool_names:
            confidence = min(1.0, confidence + 0.1)
        else:
            confidence -= 0.1

        # 첨부 파일이 있으면 변동성이 커서 신뢰도 하락
        if has_attachments:
            confidence -= 0.15

        # 복잡도가 높을수록 신뢰도 하락
        complexity_penalty = {
            "FAST": 0,
            "MEDIUM": 0.05,
            "DEEP": 0.1,
            "THINKING": 0.2,
        }
        confidence -= complexity_penalty.get(complexity, 0.1)

        return max(0.3, min(1.0, confidence))

    def _determine_cost_tier(
        self,
        cost_usd: float,
        complexity: str,
    ) -> CostTier:
        """비용 등급 결정"""
        if complexity == "FAST" or cost_usd < 0.001:
            return CostTier.LOW
        elif complexity == "THINKING" or cost_usd > 0.05:
            return CostTier.VERY_HIGH
        elif complexity == "DEEP" or cost_usd > 0.01:
            return CostTier.HIGH
        else:
            return CostTier.MEDIUM

    def _check_cost_thresholds(
        self,
        cost_usd: float,
    ) -> Tuple[bool, bool, bool, Optional[str]]:
        """
        비용 임계값 확인

        Returns:
            (needs_warning, needs_confirmation, should_block, warning_message)
        """
        needs_warning = cost_usd >= COST_THRESHOLDS["warning"]
        needs_confirmation = cost_usd >= COST_THRESHOLDS["confirm"]
        should_block = cost_usd >= COST_THRESHOLDS["block"]

        warning_msg = None
        if should_block:
            warning_msg = (
                f"예상 비용(${cost_usd:.4f})이 제한(${COST_THRESHOLDS['block']})을 "
                f"초과합니다. 요청을 처리할 수 없습니다."
            )
        elif needs_confirmation:
            warning_msg = (
                f"예상 비용이 ${cost_usd:.4f}입니다. 계속 진행하시겠습니까?"
            )
        elif needs_warning:
            warning_msg = (
                f"이 요청은 예상 비용이 ${cost_usd:.4f}입니다."
            )

        return needs_warning, needs_confirmation, should_block, warning_msg

    def _record_session_cost(self, session_id: str, actual: ActualCost):
        """세션별 비용 기록"""
        if session_id not in self._session_costs:
            self._session_costs[session_id] = []

        self._session_costs[session_id].append(actual)

        # 최대 100건 유지
        if len(self._session_costs[session_id]) > 100:
            self._session_costs[session_id] = \
                self._session_costs[session_id][-100:]


# =============================================================================
# 싱글톤 및 편의 함수
# =============================================================================

_cost_estimator: Optional[CostEstimator] = None


def get_cost_estimator(model: Optional[str] = None) -> CostEstimator:
    """
    CostEstimator 싱글톤 인스턴스 반환

    Args:
        model: LLM 모델명 (None이면 기본값 사용)

    Returns:
        CostEstimator 인스턴스
    """
    global _cost_estimator
    if _cost_estimator is None:
        from apps.ai_service.config.settings import settings
        model_name = model or getattr(settings, 'LLM_MODEL', 'gpt-4o-mini')
        _cost_estimator = CostEstimator(model=model_name)
    return _cost_estimator


def init_cost_estimator(model: str) -> CostEstimator:
    """
    CostEstimator 명시적 초기화

    Args:
        model: LLM 모델명

    Returns:
        새 CostEstimator 인스턴스
    """
    global _cost_estimator
    _cost_estimator = CostEstimator(model=model)
    return _cost_estimator


def estimate_cost(
    complexity: str,
    tool_names: Optional[List[str]] = None,
    message_length: int = 0,
    has_attachments: bool = False,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    간편 비용 추정 함수

    Args:
        complexity: 복잡도 레벨 ("FAST", "MEDIUM", "DEEP", "THINKING")
        tool_names: 사용할 도구/워크플로우 목록
        message_length: 사용자 메시지 길이
        has_attachments: 첨부 파일 여부
        model: LLM 모델명 (None이면 기본값)

    Returns:
        비용 추정 딕셔너리
    """
    estimator = get_cost_estimator(model)
    estimate = estimator.estimate_for_complexity(
        complexity=complexity,
        tool_names=tool_names,
        message_length=message_length,
        has_attachments=has_attachments,
    )
    return estimate.to_dict()


def calculate_actual_cost(
    input_tokens: int,
    output_tokens: int,
    execution_time: float = 0.0,
    tool_calls: int = 0,
    estimated_tokens: int = 0,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    간편 실제 비용 계산 함수

    Args:
        input_tokens: 실제 입력 토큰 수
        output_tokens: 실제 출력 토큰 수
        execution_time: 실행 시간 (초)
        tool_calls: 도구 호출 횟수
        estimated_tokens: 예상했던 토큰 수
        session_id: 세션 ID
        model: LLM 모델명

    Returns:
        실제 비용 딕셔너리
    """
    estimator = get_cost_estimator(model)
    actual = estimator.calculate_actual_cost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        execution_time=execution_time,
        tool_calls=tool_calls,
        estimated_tokens=estimated_tokens,
        session_id=session_id,
    )
    return actual.to_dict()
