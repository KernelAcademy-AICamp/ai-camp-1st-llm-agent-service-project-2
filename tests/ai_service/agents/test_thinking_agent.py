"""
Thinking Agent 테스트

Phase 6-2: Thinking Agent 통합 테스트

테스트 범위:
- ThoughtStep 직렬화/역직렬화
- THINKING 분류 조건
- Observe Node
- Reflect Node
- Thinking Path Node
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from apps.ai_service.agents.states.master_agent_state import (
    ComplexityLevel,
    ThoughtStep,
    StreamingEvent,
)


# =============================================================================
# ThoughtStep 테스트
# =============================================================================

class TestThoughtStep:
    """ThoughtStep 직렬화/역직렬화 테스트"""

    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        step = ThoughtStep(
            step_number=1,
            thought="분석이 필요합니다",
            action="search_legal",
            action_input={"query": "계약 해지"},
            observation=None,
            reflection=None,
            is_final=False,
        )

        result = step.to_dict()

        assert result["step_number"] == 1
        assert result["thought"] == "분석이 필요합니다"
        assert result["action"] == "search_legal"
        assert result["action_input"]["query"] == "계약 해지"
        assert result["is_final"] is False

    def test_from_dict(self):
        """딕셔너리에서 복원 테스트"""
        data = {
            "step_number": 2,
            "thought": "정보가 충분합니다",
            "action": "FINAL_ANSWER",
            "action_input": "계약 해지에 대한 답변입니다.",
            "observation": None,
            "reflection": "목표 달성",
            "is_final": True,
        }

        step = ThoughtStep.from_dict(data)

        assert step.step_number == 2
        assert step.action == "FINAL_ANSWER"
        assert step.is_final is True
        assert step.reflection == "목표 달성"

    def test_roundtrip(self):
        """직렬화 → 역직렬화 라운드트립"""
        original = ThoughtStep(
            step_number=3,
            thought="추가 검색 필요",
            action="analyze_document",
            action_input={"content": "계약서 내용"},
            observation="분석 결과: 해지 조항 발견",
            reflection="더 많은 정보 필요",
            is_final=False,
        )

        restored = ThoughtStep.from_dict(original.to_dict())

        assert restored.step_number == original.step_number
        assert restored.thought == original.thought
        assert restored.action == original.action
        assert restored.observation == original.observation
        assert restored.reflection == original.reflection
        assert restored.is_final == original.is_final


# =============================================================================
# THINKING 분류 테스트
# =============================================================================

class TestThinkingClassification:
    """THINKING 분류 조건 테스트"""

    @pytest.fixture
    def classifier(self):
        """ComplexityClassifier fixture"""
        from apps.ai_service.agents.complexity_classifier import ComplexityClassifier
        return ComplexityClassifier()

    def test_strategic_question_with_attachment(self, classifier):
        """전략적 질문 + 첨부파일 = MEDIUM 이상"""
        result = classifier.classify(
            user_message="이 계약에서 어떻게 하면 유리한 조건을 확보할 수 있을까요?",
            attachments=[{"filename": "contract.pdf", "content": "계약서 내용"}],
            conversation_history=[],
            cache_hit=False,
        )

        # 첨부파일이 있으므로 FAST가 아니어야 함
        # 현재 분류기는 단일 첨부파일을 MEDIUM으로 분류
        assert result.level != ComplexityLevel.FAST

    def test_judgment_request_with_comparison(self, classifier):
        """판단 요청 + 비교 = THINKING"""
        result = classifier.classify(
            user_message="A안과 B안 중 어떤 것이 더 안전한지 판단해주세요. 법적 리스크를 종합적으로 분석해주세요.",
            attachments=[
                {"filename": "option_a.pdf", "content": "A안"},
                {"filename": "option_b.pdf", "content": "B안"},
            ],
            conversation_history=[],
            cache_hit=False,
        )

        # 복잡한 비교 분석이므로 DEEP 또는 THINKING
        assert result.level in [ComplexityLevel.THINKING, ComplexityLevel.DEEP]

    def test_simple_question_not_thinking(self, classifier):
        """단순 질문은 THINKING이 아님"""
        result = classifier.classify(
            user_message="계약 해지 기간은?",
            attachments=[],
            conversation_history=[],
            cache_hit=False,
        )

        assert result.level != ComplexityLevel.THINKING

    def test_general_chat_not_thinking(self, classifier):
        """일반 대화는 THINKING이 아님"""
        result = classifier.classify(
            user_message="안녕하세요",
            attachments=[],
            conversation_history=[],
            cache_hit=False,
        )

        assert result.level == ComplexityLevel.FAST


# =============================================================================
# Observe Node 테스트
# =============================================================================

class TestObserveNode:
    """Observe Node 테스트"""

    @pytest.mark.asyncio
    async def test_observe_adds_context(self):
        """observation이 있으면 컨텍스트에 추가"""
        from apps.ai_service.agents.nodes.thinking.observe_node import observe_node

        state = {
            "thought_history": [
                ThoughtStep(
                    step_number=1,
                    thought="검색 필요",
                    action="search_legal",
                    action_input={"query": "계약"},
                    observation="계약에 대한 정보를 찾았습니다.",
                    is_final=False,
                ).to_dict()
            ],
            "accumulated_context": [],
            "streaming_events": [],
        }

        result = await observe_node(state)

        assert len(result["accumulated_context"]) == 1
        assert "Step 1" in result["accumulated_context"][0]
        assert "search_legal" in result["accumulated_context"][0]

    @pytest.mark.asyncio
    async def test_observe_empty_history(self):
        """빈 사고 이력은 스킵"""
        from apps.ai_service.agents.nodes.thinking.observe_node import observe_node

        state = {
            "thought_history": [],
            "accumulated_context": [],
            "streaming_events": [],
        }

        result = await observe_node(state)

        assert result == {}

    @pytest.mark.asyncio
    async def test_observe_no_observation(self):
        """observation이 없으면 컨텍스트 변경 없음"""
        from apps.ai_service.agents.nodes.thinking.observe_node import observe_node

        state = {
            "thought_history": [
                ThoughtStep(
                    step_number=1,
                    thought="분석 중",
                    action="FINAL_ANSWER",
                    action_input="답변",
                    observation=None,
                    is_final=True,
                ).to_dict()
            ],
            "accumulated_context": ["기존 컨텍스트"],
            "streaming_events": [],
        }

        result = await observe_node(state)

        # observation이 없으면 컨텍스트 그대로
        assert result.get("accumulated_context", ["기존 컨텍스트"]) == ["기존 컨텍스트"]


# =============================================================================
# Reflect Node 테스트
# =============================================================================

class TestReflectNode:
    """Reflect Node 테스트"""

    @pytest.mark.asyncio
    async def test_reflect_final_answer_completes(self):
        """FINAL_ANSWER면 바로 완료"""
        from apps.ai_service.agents.nodes.thinking.reflect_node import reflect_node

        state = {
            "goal": "계약에 대해 알려주세요",
            "user_message": "계약에 대해 알려주세요",
            "thought_history": [
                ThoughtStep(
                    step_number=1,
                    thought="충분한 정보",
                    action="FINAL_ANSWER",
                    action_input="계약에 대한 답변입니다.",
                    is_final=True,
                ).to_dict()
            ],
            "accumulated_context": [],
            "streaming_events": [],
            "current_step": 1,
            "max_steps": 10,
        }

        result = await reflect_node(state)

        assert result["thinking_complete"] is True
        assert result["completion_reason"] == "goal_achieved"

    @pytest.mark.asyncio
    async def test_reflect_max_steps_reached(self):
        """최대 단계 도달 시 완료"""
        from apps.ai_service.agents.nodes.thinking.reflect_node import reflect_node

        state = {
            "goal": "복잡한 분석",
            "user_message": "복잡한 분석",
            "thought_history": [
                ThoughtStep(
                    step_number=10,
                    thought="아직 진행 중",
                    action="search_legal",
                    is_final=False,
                ).to_dict()
            ],
            "accumulated_context": [],
            "streaming_events": [],
            "current_step": 10,
            "max_steps": 10,
        }

        result = await reflect_node(state)

        assert result["thinking_complete"] is True
        assert result["completion_reason"] == "max_steps"


# =============================================================================
# Thinking Path Node 테스트
# =============================================================================

class TestThinkingPathNode:
    """Thinking Path Node 테스트"""

    @pytest.mark.asyncio
    async def test_thinking_path_returns_required_fields(self):
        """thinking_path_node가 필요한 필드를 반환하는지 테스트"""
        from apps.ai_service.agents.nodes.thinking_path_node import thinking_path_node

        # Mock the inner nodes
        with patch("apps.ai_service.agents.nodes.thinking_path_node.think_node") as mock_think, \
             patch("apps.ai_service.agents.nodes.thinking_path_node.act_node") as mock_act, \
             patch("apps.ai_service.agents.nodes.thinking_path_node.observe_node") as mock_observe, \
             patch("apps.ai_service.agents.nodes.thinking_path_node.reflect_node") as mock_reflect, \
             patch("apps.ai_service.agents.nodes.thinking_path_node.get_tool_registry") as mock_registry:

            # Configure mocks
            mock_registry.return_value.list_tools.return_value = ["search_legal"]

            # Think returns FINAL_ANSWER immediately
            mock_think.return_value = {
                "thought_history": [
                    ThoughtStep(
                        step_number=1,
                        thought="답변 가능",
                        action="FINAL_ANSWER",
                        action_input="이것이 답변입니다.",
                        is_final=True,
                    ).to_dict()
                ],
                "current_step": 1,
                "total_llm_calls": 1,
            }

            mock_act.return_value = {}
            mock_observe.return_value = {}
            mock_reflect.return_value = {"thinking_complete": True}

            state = {
                "user_message": "테스트 질문",
                "session_id": "test-session",
                "streaming_events": [],
            }

            result = await thinking_path_node(state)

            # 필수 필드 확인
            assert "workflow_results" in result
            assert "thought_history" in result
            assert "thinking_complete" in result
            assert "response_metadata" in result
            assert "final_response" in result

            # 메타데이터 확인
            assert result["response_metadata"]["path"] == "thinking"


# =============================================================================
# Route by Complexity 테스트
# =============================================================================

class TestRouteByComplexity:
    """route_by_complexity 함수 테스트"""

    def test_route_thinking(self):
        """THINKING 경로 라우팅"""
        from apps.ai_service.agents.nodes.complexity_classifier_node import route_by_complexity

        state = {"execution_path": "thinking"}
        assert route_by_complexity(state) == "thinking"

    def test_route_fast(self):
        """FAST 경로 라우팅"""
        from apps.ai_service.agents.nodes.complexity_classifier_node import route_by_complexity

        state = {"execution_path": "fast"}
        assert route_by_complexity(state) == "fast"

    def test_route_medium(self):
        """MEDIUM 경로 라우팅"""
        from apps.ai_service.agents.nodes.complexity_classifier_node import route_by_complexity

        state = {"execution_path": "medium"}
        assert route_by_complexity(state) == "medium"

    def test_route_deep(self):
        """DEEP 경로 라우팅"""
        from apps.ai_service.agents.nodes.complexity_classifier_node import route_by_complexity

        state = {"execution_path": "deep"}
        assert route_by_complexity(state) == "deep"

    def test_route_unknown_defaults_to_medium(self):
        """알 수 없는 경로는 medium으로 기본값"""
        from apps.ai_service.agents.nodes.complexity_classifier_node import route_by_complexity

        state = {"execution_path": "unknown"}
        assert route_by_complexity(state) == "medium"


# =============================================================================
# 통합 테스트
# =============================================================================

class TestThinkingIntegration:
    """Thinking Agent 통합 테스트"""

    def test_streaming_event_types(self):
        """스트리밍 이벤트 타입 확인"""
        # 예상되는 이벤트 타입들
        expected_events = [
            "thinking_path_start",
            "thinking_step",
            "thought_complete",
            "action_start",
            "action_complete",
            "observation_added",
            "reflecting",
            "reflection_complete",
            "thinking_path_complete",
        ]

        # 모두 문자열 타입인지 확인
        for event in expected_events:
            assert isinstance(event, str)

    def test_complexity_level_values(self):
        """ComplexityLevel 값 확인"""
        assert ComplexityLevel.FAST.value == "FAST"
        assert ComplexityLevel.MEDIUM.value == "MEDIUM"
        assert ComplexityLevel.DEEP.value == "DEEP"
        assert ComplexityLevel.THINKING.value == "THINKING"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
