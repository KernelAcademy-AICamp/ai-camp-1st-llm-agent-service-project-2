"""
Phase 7: CostEstimator 테스트

단계별 비용 추정 기능 테스트
"""

import pytest
from unittest.mock import patch, MagicMock

from apps.ai_service.agents.cost_estimator import (
    CostEstimator,
    CostEstimate,
    ActualCost,
    CostSummary,
    CostTier,
    get_cost_estimator,
    calculate_actual_cost,
    estimate_cost,
    init_cost_estimator,
    COMPLEXITY_BASE_TOKENS,
    MODEL_COSTS,
)


class TestCostEstimator:
    """CostEstimator 클래스 테스트"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """각 테스트 전 싱글톤 초기화"""
        import apps.ai_service.agents.cost_estimator as module
        module._cost_estimator = None
        yield

    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        estimator1 = get_cost_estimator()
        estimator2 = get_cost_estimator()
        assert estimator1 is estimator2

    def test_init_cost_estimator(self):
        """명시적 초기화 테스트"""
        estimator = init_cost_estimator("gpt-4o")
        assert estimator.model == "gpt-4o"

    def test_estimate_for_complexity_fast(self):
        """FAST 복잡도 비용 예측 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        estimate = estimator.estimate_for_complexity(
            complexity="FAST",
            message_length=20,
        )

        assert isinstance(estimate, CostEstimate)
        assert estimate.estimated_tokens > 0
        assert estimate.estimated_cost_usd >= 0
        assert estimate.cost_tier in CostTier
        assert "base" in estimate.breakdown
        assert estimate.breakdown["base"] == COMPLEXITY_BASE_TOKENS["FAST"]

    def test_estimate_for_complexity_medium(self):
        """MEDIUM 복잡도 비용 예측 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        estimate = estimator.estimate_for_complexity(
            complexity="MEDIUM",
            message_length=100,
        )

        assert estimate.estimated_tokens > 0
        # MEDIUM은 FAST보다 높은 비용 예상
        fast_estimate = estimator.estimate_for_complexity(
            complexity="FAST",
            message_length=100,
        )
        assert estimate.estimated_tokens > fast_estimate.estimated_tokens

    def test_estimate_for_complexity_deep(self):
        """DEEP 복잡도 비용 예측 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        estimate = estimator.estimate_for_complexity(
            complexity="DEEP",
            message_length=500,
        )

        assert estimate.estimated_tokens > 0
        # DEEP은 더 높은 기본 토큰
        assert estimate.breakdown["base"] == COMPLEXITY_BASE_TOKENS["DEEP"]

    def test_estimate_for_complexity_thinking(self):
        """THINKING 복잡도 비용 예측 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        estimate = estimator.estimate_for_complexity(
            complexity="THINKING",
            message_length=1000,
        )

        assert estimate.estimated_tokens > 0
        # THINKING은 가장 높은 비용 예상
        assert estimate.cost_tier == CostTier.VERY_HIGH

    def test_estimate_with_attachments(self):
        """첨부파일 포함 비용 예측 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        # 첨부파일 없이
        estimate_no_attach = estimator.estimate_for_complexity(
            complexity="MEDIUM",
            message_length=100,
            has_attachments=False,
        )

        # 첨부파일 있이
        estimate_with_attach = estimator.estimate_for_complexity(
            complexity="MEDIUM",
            message_length=100,
            has_attachments=True,
            attachment_size=10000,  # 10KB
        )

        # 첨부파일 있으면 토큰 더 많이 예상
        assert estimate_with_attach.estimated_tokens > estimate_no_attach.estimated_tokens
        assert "attachments" in estimate_with_attach.breakdown

    def test_estimate_with_tools(self):
        """도구 포함 비용 예측 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        estimate = estimator.estimate_for_complexity(
            complexity="MEDIUM",
            message_length=100,
            tool_names=["rag_workflow", "document_workflow"],
        )

        assert estimate.estimated_tokens > 0
        assert "tools" in estimate.breakdown
        assert estimate.breakdown["tools"] > 0

    def test_cost_tier_classification(self):
        """비용 등급 분류 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        # 낮은 비용
        low_estimate = estimator.estimate_for_complexity(
            complexity="FAST",
            message_length=10,
        )
        assert low_estimate.cost_tier == CostTier.LOW

    def test_should_warn_and_block(self):
        """경고/차단 필요 여부 확인 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        # 낮은 비용 - 경고 불필요
        low_estimate = estimator.estimate_for_complexity(
            complexity="FAST",
            message_length=10,
        )
        assert not low_estimate.needs_warning
        assert not low_estimate.should_block

    def test_to_dict(self):
        """CostEstimate to_dict 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        estimate = estimator.estimate_for_complexity(
            complexity="MEDIUM",
            message_length=100,
        )

        result = estimate.to_dict()
        assert "estimated_tokens" in result
        assert "estimated_cost_usd" in result
        assert "cost_tier" in result
        assert "model" in result


class TestCalculateActualCost:
    """실제 비용 계산 테스트"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """각 테스트 전 싱글톤 초기화"""
        import apps.ai_service.agents.cost_estimator as module
        module._cost_estimator = None
        yield

    def test_calculate_actual_cost_basic(self):
        """기본 실제 비용 계산 테스트"""
        estimator = CostEstimator(model="gpt-4o")

        actual = estimator.calculate_actual_cost(
            input_tokens=1000,
            output_tokens=500,
        )

        assert isinstance(actual, ActualCost)
        assert actual.actual_tokens == 1500
        assert actual.actual_input_tokens == 1000
        assert actual.actual_output_tokens == 500
        assert actual.actual_cost_usd > 0

    def test_calculate_actual_cost_with_estimate(self):
        """예상치와 비교 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        actual = estimator.calculate_actual_cost(
            input_tokens=1000,
            output_tokens=500,
            estimated_tokens=1200,
        )

        assert actual.estimated_tokens == 1200
        assert actual.token_difference == 300  # 1500 - 1200

    def test_calculate_actual_cost_with_session(self):
        """세션 기록 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        # 여러 요청 기록
        estimator.calculate_actual_cost(
            input_tokens=1000,
            output_tokens=500,
            session_id="test-session-123",
        )
        estimator.calculate_actual_cost(
            input_tokens=800,
            output_tokens=400,
            session_id="test-session-123",
        )

        # 세션 요약 조회
        summary = estimator.get_session_summary("test-session-123")
        assert summary is not None
        assert summary.total_requests == 2
        assert summary.total_actual_tokens == 2700  # 1500 + 1200

    def test_calculate_actual_cost_function(self):
        """편의 함수 테스트"""
        result = calculate_actual_cost(
            input_tokens=1000,
            output_tokens=500,
            model="gpt-4o-mini",
        )

        assert isinstance(result, dict)
        assert "actual_tokens" in result
        assert "actual_cost_usd" in result
        assert result["actual_tokens"] == 1500


class TestEstimateCostFunction:
    """편의 함수 테스트"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """각 테스트 전 싱글톤 초기화"""
        import apps.ai_service.agents.cost_estimator as module
        module._cost_estimator = None
        yield

    def test_estimate_cost_function(self):
        """estimate_cost 편의 함수 테스트"""
        result = estimate_cost(
            complexity="MEDIUM",
            message_length=100,
        )

        assert isinstance(result, dict)
        assert "estimated_tokens" in result
        assert "estimated_cost_usd" in result
        assert "cost_tier" in result


class TestCostEstimatorForPlan:
    """계획 기반 비용 예측 테스트"""

    def test_estimate_for_plan(self):
        """실행 계획 기반 비용 예측 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        plan_steps = [
            {"step_id": "search", "workflow_name": "rag_workflow"},
            {"step_id": "analyze", "workflow_name": "document_workflow"},
            {"step_id": "summarize", "tool_name": "summary_tool"},
        ]

        estimate = estimator.estimate_for_plan(
            plan_steps=plan_steps,
            message_length=100,
        )

        assert estimate.estimated_tokens > 0
        assert estimate.estimated_cost_usd >= 0
        # 각 단계별 토큰이 breakdown에 포함
        assert any("step_" in key for key in estimate.breakdown.keys())

    def test_estimate_for_tools(self):
        """도구 기반 비용 예측 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        estimate = estimator.estimate_for_tools(
            tool_names=["rag_workflow", "document_workflow"],
            message_length=100,
        )

        assert estimate.estimated_tokens > 0
        assert estimate.estimated_cost_usd >= 0
        assert "tools" in estimate.breakdown


class TestCostSummary:
    """비용 요약 테스트"""

    def test_session_summary(self):
        """세션 비용 요약 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")
        session_id = "test-session-summary"

        # 여러 요청 기록
        for i in range(3):
            estimator.calculate_actual_cost(
                input_tokens=1000 + i * 100,
                output_tokens=500 + i * 50,
                session_id=session_id,
            )

        summary = estimator.get_session_summary(session_id)

        assert isinstance(summary, CostSummary)
        assert summary.total_requests == 3
        assert summary.total_actual_tokens > 0

    def test_empty_session_summary(self):
        """빈 세션 비용 요약 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        summary = estimator.get_session_summary("non-existent-session")
        assert summary is None

    def test_clear_session_costs(self):
        """세션 비용 기록 삭제 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")
        session_id = "test-clear-session"

        estimator.calculate_actual_cost(
            input_tokens=1000,
            output_tokens=500,
            session_id=session_id,
        )

        # 삭제 전
        assert estimator.get_session_summary(session_id) is not None

        # 삭제
        estimator.clear_session_costs(session_id)

        # 삭제 후
        assert estimator.get_session_summary(session_id) is None


class TestModelCosts:
    """모델별 비용 테스트"""

    def test_different_models(self):
        """다른 모델별 비용 계산 테스트"""
        # GPT-4o
        gpt4o_estimator = CostEstimator(model="gpt-4o")
        gpt4o_cost = gpt4o_estimator.calculate_actual_cost(
            input_tokens=1000,
            output_tokens=500,
        )

        # GPT-4o-mini (더 저렴한 모델)
        gpt4o_mini_estimator = CostEstimator(model="gpt-4o-mini")
        gpt4o_mini_cost = gpt4o_mini_estimator.calculate_actual_cost(
            input_tokens=1000,
            output_tokens=500,
        )

        # GPT-4o-mini가 더 저렴해야 함
        assert gpt4o_mini_cost.actual_cost_usd < gpt4o_cost.actual_cost_usd

    def test_unknown_model_uses_default(self):
        """알 수 없는 모델은 기본값 사용"""
        estimator = CostEstimator(model="unknown-model-xyz")

        # 기본 비용으로 계산됨
        actual = estimator.calculate_actual_cost(
            input_tokens=1000,
            output_tokens=500,
        )

        assert actual.actual_cost_usd > 0


class TestCostEstimatorEdgeCases:
    """엣지 케이스 테스트"""

    def test_zero_message_length(self):
        """메시지 길이 0 비용 예측 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        estimate = estimator.estimate_for_complexity(
            complexity="FAST",
            message_length=0,
        )

        # 최소 기본 토큰은 있어야 함
        assert estimate.estimated_tokens > 0
        assert estimate.breakdown["message"] == 0

    def test_very_long_message(self):
        """매우 긴 메시지 비용 예측 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        long_message_length = 50000  # 약 12500 토큰

        estimate = estimator.estimate_for_complexity(
            complexity="DEEP",
            message_length=long_message_length,
        )

        # 긴 메시지는 높은 토큰 수
        assert estimate.estimated_tokens > 10000

    def test_large_attachment(self):
        """큰 첨부파일 비용 예측 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        estimate = estimator.estimate_for_complexity(
            complexity="MEDIUM",
            message_length=100,
            has_attachments=True,
            attachment_size=500000,  # 500KB
        )

        # 큰 첨부파일은 높은 토큰 수
        assert estimate.breakdown["attachments"] > 500

    def test_confidence_calculation(self):
        """신뢰도 계산 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        # 도구 명시된 경우 더 높은 신뢰도
        with_tools = estimator.estimate_for_complexity(
            complexity="MEDIUM",
            message_length=100,
            tool_names=["rag_workflow"],
        )

        # 도구 없는 경우
        without_tools = estimator.estimate_for_complexity(
            complexity="MEDIUM",
            message_length=100,
        )

        assert with_tools.confidence >= without_tools.confidence


class TestActualCostAccuracy:
    """실제 비용 정확도 테스트"""

    def test_accuracy_calculation(self):
        """정확도 계산 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        # 정확한 예측
        actual = estimator.calculate_actual_cost(
            input_tokens=600,
            output_tokens=400,
            estimated_tokens=1000,
        )

        result = actual.to_dict()
        assert "token_accuracy" in result
        assert result["token_accuracy"] == 100.0  # 정확함

    def test_accuracy_with_difference(self):
        """차이가 있는 경우 정확도 테스트"""
        estimator = CostEstimator(model="gpt-4o-mini")

        actual = estimator.calculate_actual_cost(
            input_tokens=600,
            output_tokens=400,
            estimated_tokens=500,  # 예상보다 실제가 2배
        )

        result = actual.to_dict()
        assert result["token_accuracy"] < 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
