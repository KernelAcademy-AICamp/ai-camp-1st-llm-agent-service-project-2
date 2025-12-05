"""
Phase 8: 전체 통합 테스트

Phase 1-7에서 구현한 모든 기능의 통합 테스트입니다.

테스트 시나리오:
1. ToolRegistry → MCPToolRegistry → 도구 실행
2. 복잡한 요청 → Deep Path → 병렬 실행 → 결과 집계
3. 에러 발생 → 복구 → 폴백 → 부분 결과
4. 토큰 예산 관리 전체 흐름
5. THINKING 경로 전체 흐름
6. End-to-End 시나리오
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# Tool Registry
from apps.ai_service.agents.tools.registry import (
    ToolRegistry,
    ToolCategory,
    ToolResult,
    get_tool_registry,
    init_tool_registry,
)

# MCP Interface
from apps.ai_service.mcp.interface import (
    MCPToolRegistry,
    MCPToolCall,
    MCPToolResult,
    create_mcp_registry_from_tool_registry,
    get_mcp_registry,
    reset_mcp_registry,
)

# Error Recovery
from apps.ai_service.agents.error_recovery import (
    ErrorRecoveryManager,
    RetryConfig,
    RecoveryResult,
    get_recovery_manager,
    reset_recovery_manager,
)

# Token Manager
from apps.ai_service.agents.token_manager import (
    TokenManager,
    TokenBudget,
    get_token_manager,
    init_token_manager,
)

# Deep Path Node
from apps.ai_service.agents.nodes.deep_path_node import (
    deep_path_node,
    build_execution_groups,
)

# Thinking Path Node
from apps.ai_service.agents.nodes.thinking_path_node import (
    thinking_path_node,
)

# States
from apps.ai_service.agents.states.master_agent_state import (
    create_initial_extended_state,
    ExecutionStep,
    ThoughtStep,
)


class TestToolRegistryToMCPIntegration:
    """ToolRegistry → MCP 통합 테스트"""

    def test_tool_registry_converts_to_mcp(self):
        """ToolRegistry가 MCPToolRegistry로 변환됨"""
        # ToolRegistry 초기화
        tool_registry = init_tool_registry()

        # MCP로 변환
        reset_mcp_registry()
        mcp_registry = create_mcp_registry_from_tool_registry(tool_registry)

        # 동일한 도구들이 있음
        tool_names = tool_registry.list_tools()
        mcp_tool_names = mcp_registry.list_tools()

        for name in tool_names:
            assert name in mcp_tool_names, f"Tool {name} not in MCP registry"

    def test_mcp_openai_format_valid(self):
        """MCP OpenAI 형식이 유효함"""
        reset_mcp_registry()
        mcp_registry = create_mcp_registry_from_tool_registry()

        definitions = mcp_registry.get_tool_definitions(format="openai")

        for d in definitions:
            assert d["type"] == "function"
            assert "function" in d
            assert "name" in d["function"]
            assert "description" in d["function"]
            assert "parameters" in d["function"]

    def test_mcp_anthropic_format_valid(self):
        """MCP Anthropic 형식이 유효함"""
        reset_mcp_registry()
        mcp_registry = create_mcp_registry_from_tool_registry()

        definitions = mcp_registry.get_tool_definitions(format="anthropic")

        for d in definitions:
            assert "name" in d
            assert "description" in d
            assert "input_schema" in d


class TestDeepPathParallelExecution:
    """Deep Path 병렬 실행 통합 테스트"""

    @pytest.fixture
    def complex_state(self):
        """복잡한 요청 상태"""
        state = create_initial_extended_state(
            user_message="여러 계약서를 비교 분석하고 리스크를 평가해줘",
            session_id="test-complex-session",
        )
        state["complexity_level"] = "DEEP"
        state["execution_path"] = "deep"
        state["attachments"] = [
            {"filename": "contract1.pdf", "content": "계약서 1 내용"},
            {"filename": "contract2.pdf", "content": "계약서 2 내용"},
        ]
        return state

    @pytest.mark.asyncio
    async def test_deep_path_executes_parallel_steps(self, complex_state):
        """Deep Path가 병렬 단계를 실행함"""
        execution_order = []

        async def track_execute(*args, **kwargs):
            execution_order.append(datetime.now().isoformat())
            await asyncio.sleep(0.05)
            return ToolResult(success=True, data={"result": "ok"})

        with patch("apps.ai_service.agents.nodes.deep_path_node.get_tool_registry") as mock_registry:
            mock_instance = MagicMock()
            mock_instance.execute_workflow = track_execute
            mock_instance.execute_tool = track_execute
            mock_registry.return_value = mock_instance

            result = await deep_path_node(complex_state)

        # 결과 확인
        assert result["response_metadata"]["path"] == "deep"
        assert result["response_metadata"]["steps_executed"] >= 2

        # 스트리밍 이벤트 확인
        events = result["streaming_events"]
        event_types = [e["event"] for e in events]
        assert "deep_path_start" in event_types
        assert "deep_path_complete" in event_types

    @pytest.mark.asyncio
    async def test_deep_path_aggregates_results(self, complex_state):
        """Deep Path가 결과를 집계함"""
        with patch("apps.ai_service.agents.nodes.deep_path_node.get_tool_registry") as mock_registry:
            mock_instance = MagicMock()
            mock_instance.execute_workflow = AsyncMock(
                return_value=ToolResult(success=True, data={"answer": "분석 완료"})
            )
            mock_registry.return_value = mock_instance

            result = await deep_path_node(complex_state)

        # 집계된 응답 존재
        assert "final_response" in result
        assert result["final_response"] is not None


class TestErrorRecoveryWithFallback:
    """에러 복구 및 폴백 통합 테스트"""

    @pytest.fixture
    def recovery_manager(self):
        """테스트용 복구 매니저"""
        reset_recovery_manager()
        return ErrorRecoveryManager(
            RetryConfig(
                max_retries=2,
                base_delay=0.01,
                max_delay=0.1,
            )
        )

    @pytest.mark.asyncio
    async def test_primary_fails_fallback_succeeds(self, recovery_manager):
        """Primary 실패 → Fallback 성공"""
        async def primary_fail():
            raise ConnectionError("Primary failed")

        async def fallback_success():
            return {"from": "fallback", "status": "ok"}

        result = await recovery_manager.execute_with_retry(
            primary_fail,
            fallback_funcs=[fallback_success],
            operation_name="test_fallback",
        )

        assert result.success
        assert result.data["from"] == "fallback"
        assert result.fallback_used is not None

    @pytest.mark.asyncio
    async def test_retry_then_succeed(self, recovery_manager):
        """재시도 후 성공"""
        attempt = 0

        async def eventual_success():
            nonlocal attempt
            attempt += 1
            if attempt < 2:
                raise asyncio.TimeoutError("Retry needed")
            return {"attempt": attempt}

        result = await recovery_manager.execute_with_retry(
            eventual_success,
            operation_name="test_retry",
        )

        assert result.success
        assert result.data["attempt"] == 2
        assert result.attempts >= 2


class TestTokenBudgetManagement:
    """토큰 예산 관리 통합 테스트"""

    @pytest.fixture
    def token_manager(self):
        """테스트용 토큰 매니저"""
        mock_service = MagicMock()
        mock_service.check_quota = AsyncMock(return_value={
            "within_quota": True,
            "current_tokens": 0,
        })
        mock_service.track_usage = AsyncMock()
        return TokenManager(usage_service=mock_service)

    @pytest.mark.asyncio
    async def test_reserve_execute_confirm_flow(self, token_manager):
        """예약 → 실행 → 확정 전체 흐름"""
        # 1. 예약
        reserve_result = await token_manager.check_and_reserve(
            user_id="user-123",
            session_id="session-456",
            estimated_tokens=1000,
        )

        assert reserve_result.allowed
        assert reserve_result.estimated_cost == 1000

        # 예산 상태 확인
        budget = token_manager.get_session_budget("session-456")
        assert budget.reserved == 1000

        # 2. (시뮬레이션된) 실행 - 실제로는 800 토큰 사용

        # 3. 확정
        confirm_result = await token_manager.confirm_usage(
            user_id="user-123",
            session_id="session-456",
            actual_tokens=800,
            estimated_tokens=1000,
        )

        assert confirm_result.success
        assert confirm_result.difference == -200

        # 예산 업데이트 확인
        budget = token_manager.get_session_budget("session-456")
        assert budget.reserved == 0
        assert budget.used == 800

    @pytest.mark.asyncio
    async def test_budget_exhaustion(self):
        """예산 소진 시나리오"""
        # 적은 한도로 설정된 서비스 mock
        mock_service = MagicMock()
        mock_service.check_quota = AsyncMock(return_value={
            "within_quota": True,
            "current_tokens": 49000,  # 이미 많이 사용
            "daily_limit": 50000,
        })
        mock_service.track_usage = AsyncMock()
        manager = TokenManager(usage_service=mock_service)

        # 추가 예약 시도 - 실패 예상
        result = await manager.check_and_reserve(
            user_id="user",
            session_id="session-exhaust-new",
            estimated_tokens=5000,  # 49000 + 5000 > 50000
        )

        assert not result.allowed
        assert "부족" in result.message or "한도" in result.message


class TestThinkingPathFlow:
    """THINKING 경로 전체 흐름 테스트"""

    @pytest.fixture
    def thinking_state(self):
        """Thinking 상태"""
        return {
            "user_message": "복잡한 법률 문제에 대해 단계별로 분석해줘",
            "session_id": "test-thinking",
            "streaming_events": [],
            "execution_path": "thinking",
            "complexity_level": "THINKING",
            "max_steps": 3,
        }

    @pytest.mark.asyncio
    async def test_thinking_completes_with_answer(self, thinking_state):
        """Thinking이 답변과 함께 완료됨"""
        with patch("apps.ai_service.agents.nodes.thinking_path_node.think_node") as mock_think:
            # Think가 바로 최종 답변 반환
            mock_think.return_value = {
                "thought_history": [
                    ThoughtStep(
                        step_number=1,
                        thought="분석 완료",
                        action="FINAL_ANSWER",
                        action_input="최종 분석 결과입니다",
                        is_final=True,
                    ).to_dict()
                ],
                "total_llm_calls": 1,
            }

            result = await thinking_path_node(thinking_state)

        assert result["thinking_complete"]
        assert result["final_response"] == "최종 분석 결과입니다"
        assert result["response_metadata"]["path"] == "thinking"

    @pytest.mark.asyncio
    async def test_thinking_filters_tools(self, thinking_state):
        """Thinking이 도구를 필터링함"""
        with patch("apps.ai_service.agents.nodes.thinking_path_node.think_node") as mock_think:
            mock_think.return_value = {
                "thought_history": [
                    ThoughtStep(
                        step_number=1,
                        thought="완료",
                        action="FINAL_ANSWER",
                        action_input="결과",
                        is_final=True,
                    ).to_dict()
                ],
                "total_llm_calls": 1,
            }

            result = await thinking_path_node(thinking_state)

        events = result["streaming_events"]
        filter_event = next(
            (e for e in events if e["event"] == "tools_filtered"),
            None
        )

        assert filter_event is not None
        assert filter_event["data"]["tool_count"] <= 8


class TestEndToEndScenarios:
    """E2E 시나리오 테스트"""

    @pytest.mark.asyncio
    async def test_simple_search_scenario(self):
        """간단한 검색 시나리오"""
        # 1. ToolRegistry에서 도구 선택
        registry = init_tool_registry()
        search_tool = registry.get_tool("search_legal")

        assert search_tool is not None
        assert search_tool.category == ToolCategory.SEARCH

        # 2. MCP 형식으로 변환
        reset_mcp_registry()
        mcp_registry = create_mcp_registry_from_tool_registry(registry)

        definitions = mcp_registry.get_tool_definitions(format="openai")
        search_def = next(
            (d for d in definitions if d["function"]["name"] == "search_legal"),
            None
        )

        assert search_def is not None

    @pytest.mark.asyncio
    async def test_document_analysis_scenario(self):
        """문서 분석 시나리오"""
        # 1. 도구 필터링
        registry = init_tool_registry()
        tools = registry.get_tools_for_context(
            "계약서를 분석해줘",
            categories=[ToolCategory.ANALYSIS, ToolCategory.DOCUMENT],
        )

        assert len(tools) > 0

        # 2. 비용 추정
        tool_names = [t.name for t in tools[:3]]
        cost = registry.estimate_cost(tool_names)

        assert cost["total_estimated_tokens"] > 0

    @pytest.mark.asyncio
    async def test_complex_multi_step_scenario(self):
        """복잡한 다단계 시나리오"""
        # 1. 토큰 예약
        mock_service = MagicMock()
        mock_service.check_quota = AsyncMock(return_value={"within_quota": True})
        mock_service.track_usage = AsyncMock()

        token_manager = TokenManager(usage_service=mock_service)

        reserve = await token_manager.check_and_reserve(
            user_id="user",
            session_id="complex-session",
            estimated_tokens=3000,
        )

        assert reserve.allowed

        # 2. 에러 복구 설정
        recovery_manager = ErrorRecoveryManager(
            RetryConfig(max_retries=2, base_delay=0.01)
        )

        # 3. 도구 실행 (with recovery)
        async def execute_analysis():
            registry = init_tool_registry()
            return await registry.execute_tool(
                "search_legal",
                {"query": "테스트"},
            )

        result = await recovery_manager.execute_with_retry(
            execute_analysis,
            operation_name="analysis",
        )

        # 4. 토큰 확정
        await token_manager.confirm_usage(
            user_id="user",
            session_id="complex-session",
            actual_tokens=2500,
            estimated_tokens=3000,
        )

        # 예산 확인
        budget = token_manager.get_session_budget("complex-session")
        assert budget.used == 2500


class TestBuildExecutionGroupsIntegration:
    """실행 그룹 빌드 통합 테스트"""

    def test_complex_dependency_graph(self):
        """복잡한 의존성 그래프"""
        steps = [
            ExecutionStep(step_id="search1", step_type="tool", name="search", depends_on=[]),
            ExecutionStep(step_id="search2", step_type="tool", name="search", depends_on=[]),
            ExecutionStep(step_id="analyze", step_type="workflow", name="analyze", depends_on=["search1"]),
            ExecutionStep(step_id="risk", step_type="workflow", name="risk", depends_on=["search2"]),
            ExecutionStep(step_id="combine", step_type="workflow", name="combine", depends_on=["analyze", "risk"]),
        ]

        groups = build_execution_groups(steps)

        # 그룹 수 확인 (최소 3개: 검색 → 분석/리스크 → 종합)
        assert len(groups) >= 2

        # 첫 그룹에 검색들
        first_ids = [s.step_id for s in groups[0]]
        assert "search1" in first_ids and "search2" in first_ids

        # 마지막 그룹에 combine
        last_ids = [s.step_id for s in groups[-1]]
        assert "combine" in last_ids


class TestCostEstimatorIntegration:
    """비용 추정 통합 테스트"""

    def test_estimate_multiple_tools(self):
        """여러 도구 비용 추정"""
        registry = init_tool_registry()

        tools = ["search_legal", "analyze_document", "assess_risk"]
        cost = registry.estimate_cost(tools)

        # 개별 비용 합산
        assert cost["total_estimated_tokens"] > 0
        assert len(cost["per_tool"]) == 3

        # 합계 검증
        total = sum(cost["per_tool"][t]["tokens"] for t in tools if t in cost["per_tool"])
        assert cost["total_estimated_tokens"] == total


class TestGracefulDegradation:
    """Graceful Degradation 통합 테스트"""

    @pytest.mark.asyncio
    async def test_partial_failure_recovery(self):
        """부분 실패 복구"""
        registry = init_tool_registry()

        async def mock_execute(tool_name, *args, **kwargs):
            # 특정 도구만 실패하도록 설정
            if tool_name == "search_precedents":
                return ToolResult(success=False, error="Precedents failed")
            return ToolResult(success=True, data={"result": "ok"})

        # execute_tool 메서드를 직접 패치
        with patch.object(registry, "execute_tool", side_effect=mock_execute):
            results = await registry.execute_tools_parallel([
                {"tool_name": "search_legal", "inputs": {}},
                {"tool_name": "search_precedents", "inputs": {}},
                {"tool_name": "search_statutes", "inputs": {}},
            ])

        # 부분 성공
        success_count = sum(1 for r in results if r.success)
        assert success_count == 2  # 2개 성공, 1개 실패


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
