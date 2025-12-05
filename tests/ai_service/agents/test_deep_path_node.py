"""
Deep Path Node 테스트
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from apps.ai_service.agents.nodes.deep_path_node import (
    deep_path_node,
    _create_deep_plan,
    _has_multi_request_keywords,
    _get_workflow_from_intent,
    _prepare_step_inputs,
)
from apps.ai_service.agents.states.master_agent_state import (
    create_initial_extended_state,
    ExecutionStep,
    DeepPlan,
)
from apps.ai_service.agents.tools.registry import ToolResult


class TestDeepPlanCreation:
    """DeepPlan 생성 테스트"""

    @pytest.mark.asyncio
    async def test_multi_attachment_creates_comparison_plan(self):
        """다중 첨부 시 비교 계획 생성"""
        attachments = [
            {"filename": "doc1.pdf", "content": "문서1"},
            {"filename": "doc2.pdf", "content": "문서2"},
        ]

        plan = await _create_deep_plan(
            "두 문서를 비교해줘",
            {},
            attachments,
        )

        assert plan.total_steps >= 3  # 분석1, 분석2, 비교
        assert any(s.name == "document_workflow" for s in plan.steps)
        # 마지막 단계는 비교
        assert plan.steps[-1].step_id == "comparison"
        assert plan.steps[-1].depends_on  # 이전 단계에 의존

    @pytest.mark.asyncio
    async def test_analysis_and_generation_plan(self):
        """분석 + 생성 요청 시 순차 계획"""
        plan = await _create_deep_plan(
            "분석하고 보고서를 만들어줘",
            {},
            [],
        )

        assert plan.total_steps >= 2
        # 두 번째 단계가 첫 번째에 의존
        if len(plan.steps) >= 2:
            assert plan.steps[1].depends_on

    @pytest.mark.asyncio
    async def test_risk_and_suggestion_plan(self):
        """리스크 평가 + 수정안 요청 시 순차 계획"""
        plan = await _create_deep_plan(
            "리스크를 평가하고 수정안을 제시해줘",
            {},
            [],
        )

        assert plan.total_steps >= 2
        assert any(s.name == "risk_workflow" for s in plan.steps)
        # 수정안 단계가 리스크 평가에 의존
        suggestion_step = next((s for s in plan.steps if "suggestion" in s.step_id), None)
        if suggestion_step:
            assert "risk_assessment" in suggestion_step.depends_on

    @pytest.mark.asyncio
    async def test_comparison_without_attachments(self):
        """첨부 없이 비교 요청"""
        plan = await _create_deep_plan(
            "A와 B를 비교해줘",
            {},
            [],
        )

        assert plan.total_steps >= 1
        assert any(s.name == "rag_workflow" for s in plan.steps)

    @pytest.mark.asyncio
    async def test_single_request_defaults_to_intent(self):
        """단일 요청 시 Intent 기반 워크플로우"""
        plan = await _create_deep_plan(
            "계약서를 분석해줘",
            {"category": "DOCUMENT_ANALYSIS", "suggested_workflows": []},
            [],
        )

        assert plan.total_steps == 1
        assert plan.steps[0].name == "document_workflow"


class TestMultiRequestKeywords:
    """복합 요청 키워드 테스트"""

    def test_detects_compound_request(self):
        """복합 요청 감지"""
        assert _has_multi_request_keywords("분석하고 수정안도 제시해줘")
        assert _has_multi_request_keywords("검토한 뒤 보고서를 만들어줘")
        assert _has_multi_request_keywords("분석 그리고 비교해줘")
        assert _has_multi_request_keywords("먼저 확인한 후에 알려줘")

    def test_single_request(self):
        """단일 요청은 False"""
        assert not _has_multi_request_keywords("분석해줘")
        assert not _has_multi_request_keywords("계약서를 검토해줘")
        assert not _has_multi_request_keywords("비교해서 알려줘")


class TestWorkflowFromIntent:
    """Intent에서 워크플로우 추출 테스트"""

    def test_uses_suggested_workflows(self):
        """suggested_workflows 우선 사용"""
        intent = {
            "category": "DOCUMENT_ANALYSIS",
            "suggested_workflows": ["case_workflow"],
        }
        assert _get_workflow_from_intent(intent) == "case_workflow"

    def test_falls_back_to_category(self):
        """워크플로우 없으면 카테고리 기반"""
        intent = {"category": "RISK_ASSESSMENT"}
        assert _get_workflow_from_intent(intent) == "risk_workflow"

    def test_defaults_to_rag(self):
        """알 수 없는 카테고리는 rag_workflow"""
        intent = {"category": "UNKNOWN"}
        assert _get_workflow_from_intent(intent) == "rag_workflow"


class TestPrepareStepInputs:
    """단계 입력 준비 테스트"""

    def test_includes_user_message(self):
        """사용자 메시지 포함"""
        step = ExecutionStep(
            step_id="test",
            step_type="workflow",
            name="rag_workflow",
        )
        inputs = _prepare_step_inputs(step, {}, "테스트 질문", [])
        assert inputs["user_message"] == "테스트 질문"
        assert inputs["query"] == "테스트 질문"

    def test_includes_previous_results(self):
        """이전 결과 포함"""
        step = ExecutionStep(
            step_id="step2",
            step_type="workflow",
            name="rag_workflow",
            depends_on=["step1"],
        )
        previous = {"step1": {"data": "result1"}}
        inputs = _prepare_step_inputs(step, previous, "테스트", [])
        assert "previous_results" in inputs
        assert inputs["previous_results"]["step1"] == {"data": "result1"}

    def test_includes_attachment_content(self):
        """첨부 파일 내용 포함"""
        step = ExecutionStep(
            step_id="test",
            step_type="workflow",
            name="document_workflow",
            inputs={"document_index": 0},
        )
        attachments = [{"filename": "test.pdf", "content": "문서 내용"}]
        inputs = _prepare_step_inputs(step, {}, "분석해줘", attachments)
        assert inputs["document_content"] == "문서 내용"
        assert inputs["filename"] == "test.pdf"


class TestDeepPathNode:
    """Deep Path Node 테스트"""

    @pytest.fixture
    def base_state(self):
        """기본 상태 fixture"""
        state = create_initial_extended_state(
            user_message="두 계약서를 비교 분석해줘",
            session_id="test-session",
        )
        state["complexity_level"] = "DEEP"
        state["execution_path"] = "deep"
        state["attachments"] = [
            {"filename": "contract1.pdf", "content": "계약서1 내용"},
            {"filename": "contract2.pdf", "content": "계약서2 내용"},
        ]
        return state

    @pytest.mark.asyncio
    async def test_executes_all_steps(self, base_state):
        """모든 단계 실행"""
        mock_result = ToolResult(success=True, data={"analysis": "결과"})

        with patch(
            "apps.ai_service.agents.nodes.deep_path_node.get_tool_registry"
        ) as mock_registry:
            mock_instance = MagicMock()
            mock_instance.execute_workflow = AsyncMock(return_value=mock_result)
            mock_registry.return_value = mock_instance

            result = await deep_path_node(base_state)

        assert "deep_path_results" in result["workflow_results"]
        assert result["response_metadata"]["path"] == "deep"
        assert result["response_metadata"]["steps_executed"] >= 1

    @pytest.mark.asyncio
    async def test_handles_step_failure(self, base_state):
        """단계 실패 처리"""
        mock_result = ToolResult(success=False, error="Step failed")

        with patch(
            "apps.ai_service.agents.nodes.deep_path_node.get_tool_registry"
        ) as mock_registry:
            mock_instance = MagicMock()
            mock_instance.execute_workflow = AsyncMock(return_value=mock_result)
            mock_registry.return_value = mock_instance

            result = await deep_path_node(base_state)

        # 실패해도 결과 반환
        assert result["response_metadata"]["path"] == "deep"
        assert result["response_metadata"]["steps_successful"] == 0

    @pytest.mark.asyncio
    async def test_records_streaming_events(self, base_state):
        """스트리밍 이벤트 기록"""
        mock_result = ToolResult(success=True, data={})

        with patch(
            "apps.ai_service.agents.nodes.deep_path_node.get_tool_registry"
        ) as mock_registry:
            mock_instance = MagicMock()
            mock_instance.execute_workflow = AsyncMock(return_value=mock_result)
            mock_registry.return_value = mock_instance

            result = await deep_path_node(base_state)

        events = result["streaming_events"]
        event_types = [e["event"] for e in events]

        assert "deep_path_start" in event_types
        assert "deep_path_plan" in event_types
        assert "deep_path_complete" in event_types

    @pytest.mark.asyncio
    async def test_records_execution_logs(self, base_state):
        """실행 로그 기록"""
        mock_result = ToolResult(success=True, data={})

        with patch(
            "apps.ai_service.agents.nodes.deep_path_node.get_tool_registry"
        ) as mock_registry:
            mock_instance = MagicMock()
            mock_instance.execute_workflow = AsyncMock(return_value=mock_result)
            mock_registry.return_value = mock_instance

            result = await deep_path_node(base_state)

        logs = result["execution_logs"]
        assert len(logs) > 0
        assert all("step_id" in log for log in logs)
        assert all("status" in log for log in logs)

    @pytest.mark.asyncio
    async def test_handles_timeout(self, base_state):
        """타임아웃 처리"""
        import asyncio

        async def slow_execution(*args, **kwargs):
            await asyncio.sleep(100)  # 오래 걸리는 작업
            return ToolResult(success=True, data={})

        with patch(
            "apps.ai_service.agents.nodes.deep_path_node.get_tool_registry"
        ) as mock_registry:
            mock_instance = MagicMock()
            mock_instance.execute_workflow = slow_execution
            mock_registry.return_value = mock_instance

            # STEP_TIMEOUT을 1초로 패치
            with patch("apps.ai_service.agents.nodes.deep_path_node.STEP_TIMEOUT", 0.1):
                result = await deep_path_node(base_state)

        # 타임아웃 에러가 기록됨
        logs = result["execution_logs"]
        assert any(log.get("error") == "Timeout" for log in logs)


class TestDeepPlanDataClass:
    """DeepPlan 데이터클래스 테스트"""

    def test_to_dict(self):
        """딕셔너리 변환"""
        plan = DeepPlan(
            plan_id="test-plan",
            steps=[
                ExecutionStep(
                    step_id="step1",
                    step_type="workflow",
                    name="rag_workflow",
                    inputs={"key": "value"},
                    depends_on=[],
                    priority=0,
                )
            ],
            total_steps=1,
            estimated_time=3.0,
        )

        d = plan.to_dict()
        assert d["plan_id"] == "test-plan"
        assert len(d["steps"]) == 1
        assert d["steps"][0]["step_id"] == "step1"

    def test_from_dict(self):
        """딕셔너리에서 생성"""
        data = {
            "plan_id": "test-plan",
            "steps": [
                {
                    "step_id": "step1",
                    "step_type": "tool",
                    "name": "search_legal",
                    "inputs": {},
                    "depends_on": [],
                    "priority": 1,
                }
            ],
            "total_steps": 1,
            "estimated_time": 5.0,
        }

        plan = DeepPlan.from_dict(data)
        assert plan.plan_id == "test-plan"
        assert len(plan.steps) == 1
        assert plan.steps[0].step_type == "tool"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
