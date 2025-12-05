"""
Medium Path Node 테스트
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from apps.ai_service.agents.nodes.medium_path_node import (
    medium_path_node,
    _create_quick_plan_from_intent,
    _prepare_inputs,
)
from apps.ai_service.agents.states.master_agent_state import (
    create_initial_extended_state,
    QuickPlan,
)
from apps.ai_service.agents.tools.registry import ToolResult


class TestQuickPlan:
    """QuickPlan 테스트"""

    def test_quick_plan_to_dict(self):
        """QuickPlan을 딕셔너리로 변환"""
        plan = QuickPlan(
            workflow_name="rag_workflow",
            tool_name=None,
            inputs={"query": "테스트"},
            expected_output="text",
        )
        result = plan.to_dict()

        assert result["workflow_name"] == "rag_workflow"
        assert result["tool_name"] is None
        assert result["inputs"]["query"] == "테스트"
        assert result["expected_output"] == "text"

    def test_quick_plan_from_dict(self):
        """딕셔너리에서 QuickPlan 생성"""
        data = {
            "workflow_name": "document_workflow",
            "tool_name": None,
            "inputs": {"query": "분석"},
            "expected_output": "json",
        }
        plan = QuickPlan.from_dict(data)

        assert plan.workflow_name == "document_workflow"
        assert plan.inputs["query"] == "분석"
        assert plan.expected_output == "json"

    def test_quick_plan_from_dict_with_defaults(self):
        """빈 딕셔너리에서 기본값으로 QuickPlan 생성"""
        plan = QuickPlan.from_dict({})

        assert plan.workflow_name is None
        assert plan.tool_name is None
        assert plan.inputs == {}
        assert plan.expected_output == "text"


class TestCreateQuickPlanFromIntent:
    """_create_quick_plan_from_intent 테스트"""

    def test_create_from_document_analysis_intent(self):
        """DOCUMENT_ANALYSIS Intent에서 QuickPlan 생성"""
        intent_dict = {
            "category": "DOCUMENT_ANALYSIS",
            "suggested_workflows": ["document_workflow"],
        }
        plan = _create_quick_plan_from_intent(intent_dict, "문서 분석해줘")

        assert plan.workflow_name == "document_workflow"
        assert plan.inputs["query"] == "문서 분석해줘"

    def test_create_from_case_analysis_intent(self):
        """CASE_ANALYSIS Intent에서 QuickPlan 생성"""
        intent_dict = {
            "category": "CASE_ANALYSIS",
            "suggested_workflows": [],
        }
        plan = _create_quick_plan_from_intent(intent_dict, "판례 분석")

        assert plan.workflow_name == "case_workflow"

    def test_create_from_risk_assessment_intent(self):
        """RISK_ASSESSMENT Intent에서 QuickPlan 생성"""
        intent_dict = {
            "category": "RISK_ASSESSMENT",
            "suggested_workflows": [],
        }
        plan = _create_quick_plan_from_intent(intent_dict, "리스크 평가")

        assert plan.workflow_name == "risk_workflow"

    def test_fallback_to_rag_workflow(self):
        """Intent가 비어있으면 RAG로 fallback"""
        intent_dict = {}
        plan = _create_quick_plan_from_intent(intent_dict, "질문")

        assert plan.workflow_name == "rag_workflow"

    def test_suggested_workflows_priority(self):
        """suggested_workflows가 있으면 우선 사용"""
        intent_dict = {
            "category": "QUERY",
            "suggested_workflows": ["case_workflow", "rag_workflow"],
        }
        plan = _create_quick_plan_from_intent(intent_dict, "질문")

        # suggested_workflows의 첫 번째가 사용됨
        assert plan.workflow_name == "case_workflow"


class TestPrepareInputs:
    """_prepare_inputs 테스트"""

    def test_basic_inputs(self):
        """기본 입력 준비"""
        plan = QuickPlan(workflow_name="rag_workflow", inputs={})
        result = _prepare_inputs(plan, "법률 질문", [])

        assert result["query"] == "법률 질문"
        assert result["user_message"] == "법률 질문"

    def test_with_existing_query(self):
        """기존 query가 있으면 유지"""
        plan = QuickPlan(
            workflow_name="rag_workflow",
            inputs={"query": "기존 질문"},
        )
        result = _prepare_inputs(plan, "새 질문", [])

        # 기존 query 유지
        assert result["query"] == "기존 질문"
        assert result["user_message"] == "새 질문"

    def test_with_attachment(self):
        """첨부 파일 처리"""
        plan = QuickPlan(workflow_name="document_workflow", inputs={})
        attachments = [
            {"content": "문서 내용", "filename": "test.pdf"},
        ]
        result = _prepare_inputs(plan, "분석해줘", attachments)

        assert result["document_content"] == "문서 내용"
        assert result["filename"] == "test.pdf"


class TestMediumPathNode:
    """Medium Path Node 테스트"""

    @pytest.fixture
    def base_state(self):
        """기본 상태 fixture"""
        state = create_initial_extended_state(
            user_message="이 계약서를 분석해줘",
            session_id="test-session",
        )
        state["complexity_level"] = "MEDIUM"
        state["execution_path"] = "medium"
        return state

    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, base_state):
        """워크플로우 실행 성공"""
        base_state["quick_plan"] = {
            "workflow_name": "document_workflow",
            "inputs": {"query": "분석"},
        }

        mock_result = ToolResult(
            success=True,
            data={"analysis": "분석 결과", "summary": "요약"},
        )

        with patch(
            "apps.ai_service.agents.nodes.medium_path_node.get_tool_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.execute_workflow = AsyncMock(return_value=mock_result)
            mock_get_registry.return_value = mock_registry

            result = await medium_path_node(base_state)

        assert result["workflow_results"]["medium_path_result"] == mock_result.data
        assert result["response_metadata"]["path"] == "medium"
        assert result["response_metadata"]["workflow"] == "document_workflow"

    @pytest.mark.asyncio
    async def test_execute_workflow_failure(self, base_state):
        """워크플로우 실행 실패"""
        base_state["quick_plan"] = {
            "workflow_name": "document_workflow",
            "inputs": {},
        }

        mock_result = ToolResult(
            success=False,
            error="Workflow execution failed",
        )

        with patch(
            "apps.ai_service.agents.nodes.medium_path_node.get_tool_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.execute_workflow = AsyncMock(return_value=mock_result)
            mock_get_registry.return_value = mock_registry

            result = await medium_path_node(base_state)

        assert result["errors"][0]["error"] == "Workflow execution failed"
        assert result["response_metadata"]["error"] is True

    @pytest.mark.asyncio
    async def test_fallback_to_rag_without_quick_plan(self, base_state):
        """quick_plan이 없으면 Intent 기반으로 생성"""
        base_state["quick_plan"] = None
        base_state["intent"] = {
            "category": "QUERY",
            "suggested_workflows": [],
        }

        mock_result = ToolResult(
            success=True,
            data={"answer": "법률 답변", "sources": []},
        )

        with patch(
            "apps.ai_service.agents.nodes.medium_path_node.get_tool_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.execute_workflow = AsyncMock(return_value=mock_result)
            mock_get_registry.return_value = mock_registry

            result = await medium_path_node(base_state)

        # RAG 워크플로우로 fallback
        mock_registry.execute_workflow.assert_called_once()
        call_args = mock_registry.execute_workflow.call_args
        assert call_args[1]["workflow_name"] == "rag_workflow"

    @pytest.mark.asyncio
    async def test_execute_tool(self, base_state):
        """도구 실행"""
        base_state["quick_plan"] = {
            "workflow_name": None,
            "tool_name": "search_legal",
            "inputs": {"query": "검색"},
        }

        mock_result = ToolResult(
            success=True,
            data={"answer": "검색 결과"},
        )

        with patch(
            "apps.ai_service.agents.nodes.medium_path_node.get_tool_registry"
        ) as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.execute_tool = AsyncMock(return_value=mock_result)
            mock_get_registry.return_value = mock_registry

            result = await medium_path_node(base_state)

        mock_registry.execute_tool.assert_called_once()
        assert result["response_metadata"]["tool"] == "search_legal"


class TestToolRegistry:
    """ToolRegistry 테스트"""

    def test_list_tools(self):
        """도구 목록 조회"""
        from apps.ai_service.agents.tools.registry import ToolRegistry

        with patch(
            "apps.ai_service.agents.tools.registry.get_workflow_executor"
        ) as mock_get_executor:
            mock_executor = MagicMock()
            mock_get_executor.return_value = mock_executor

            registry = ToolRegistry()
            tools = registry.list_tools()

        assert "search_legal" in tools
        assert "analyze_document" in tools
        assert "analyze_case" in tools
        assert "assess_risk" in tools

    def test_get_tool(self):
        """도구 정의 조회"""
        from apps.ai_service.agents.tools.registry import ToolRegistry

        with patch(
            "apps.ai_service.agents.tools.registry.get_workflow_executor"
        ) as mock_get_executor:
            mock_executor = MagicMock()
            mock_get_executor.return_value = mock_executor

            registry = ToolRegistry()
            tool = registry.get_tool("search_legal")

        assert tool is not None
        assert tool.workflow_name == "rag_workflow"
        assert tool.description == "법률 정보 검색 (RAG)"

    def test_get_unknown_tool(self):
        """존재하지 않는 도구 조회"""
        from apps.ai_service.agents.tools.registry import ToolRegistry

        with patch(
            "apps.ai_service.agents.tools.registry.get_workflow_executor"
        ) as mock_get_executor:
            mock_executor = MagicMock()
            mock_get_executor.return_value = mock_executor

            registry = ToolRegistry()
            tool = registry.get_tool("unknown_tool")

        assert tool is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
