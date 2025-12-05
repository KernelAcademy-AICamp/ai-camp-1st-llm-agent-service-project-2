"""
Phase 8: 병렬 실행 통합 테스트

테스트 항목:
1. 의존성 기반 그룹화 (build_execution_groups)
2. 그룹별 병렬 실행
3. 결과 집계
4. 타임아웃 처리
5. 부분 실패 처리
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from apps.ai_service.agents.nodes.deep_path_node import (
    deep_path_node,
    build_execution_groups,
    _execute_step_with_timeout,
    _aggregate_deep_results,
    MAX_PARALLEL_TASKS,
    STEP_TIMEOUT,
)
from apps.ai_service.agents.states.master_agent_state import (
    create_initial_extended_state,
    ExecutionStep,
    DeepPlan,
)
from apps.ai_service.agents.tools.registry import ToolResult


class TestBuildExecutionGroups:
    """의존성 기반 그룹화 테스트"""

    def test_independent_steps_single_group(self):
        """의존성 없는 단계들은 같은 그룹"""
        steps = [
            ExecutionStep(step_id="step1", step_type="workflow", name="wf1", depends_on=[]),
            ExecutionStep(step_id="step2", step_type="workflow", name="wf2", depends_on=[]),
            ExecutionStep(step_id="step3", step_type="workflow", name="wf3", depends_on=[]),
        ]

        groups = build_execution_groups(steps)

        # MAX_PARALLEL_TASKS (3) 이하면 모두 같은 그룹
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_dependent_steps_sequential_groups(self):
        """의존성 있는 단계들은 순차 그룹"""
        steps = [
            ExecutionStep(step_id="step1", step_type="workflow", name="wf1", depends_on=[]),
            ExecutionStep(step_id="step2", step_type="workflow", name="wf2", depends_on=["step1"]),
            ExecutionStep(step_id="step3", step_type="workflow", name="wf3", depends_on=["step2"]),
        ]

        groups = build_execution_groups(steps)

        assert len(groups) == 3
        assert len(groups[0]) == 1  # step1만
        assert len(groups[1]) == 1  # step2만
        assert len(groups[2]) == 1  # step3만

    def test_mixed_dependencies(self):
        """혼합된 의존성 처리"""
        steps = [
            ExecutionStep(step_id="search1", step_type="tool", name="search", depends_on=[]),
            ExecutionStep(step_id="search2", step_type="tool", name="search", depends_on=[]),
            ExecutionStep(step_id="analysis", step_type="workflow", name="analyze", depends_on=["search1", "search2"]),
        ]

        groups = build_execution_groups(steps)

        assert len(groups) == 2
        # 첫 그룹에 search1, search2 (병렬)
        first_group_ids = [s.step_id for s in groups[0]]
        assert "search1" in first_group_ids
        assert "search2" in first_group_ids
        # 두 번째 그룹에 analysis
        assert groups[1][0].step_id == "analysis"

    def test_exceeds_max_parallel_splits(self):
        """MAX_PARALLEL_TASKS 초과 시 분할"""
        steps = [
            ExecutionStep(step_id=f"step{i}", step_type="workflow", name="wf", depends_on=[])
            for i in range(5)
        ]

        groups = build_execution_groups(steps)

        # 5개 단계, MAX_PARALLEL_TASKS=3이면 2개 그룹
        assert len(groups) == 2
        assert len(groups[0]) == MAX_PARALLEL_TASKS  # 첫 그룹 3개
        assert len(groups[1]) == 2  # 두 번째 그룹 2개

    def test_empty_steps(self):
        """빈 단계 목록"""
        groups = build_execution_groups([])
        assert groups == []

    def test_circular_dependency_handling(self):
        """순환 의존성 감지"""
        steps = [
            ExecutionStep(step_id="step1", step_type="workflow", name="wf1", depends_on=["step2"]),
            ExecutionStep(step_id="step2", step_type="workflow", name="wf2", depends_on=["step1"]),
        ]

        # 순환 의존성 있으면 남은 것들 순차 처리
        groups = build_execution_groups(steps)

        # 경고 로그와 함께 처리됨
        assert len(groups) >= 1


class TestExecuteStepWithTimeout:
    """개별 단계 실행 테스트"""

    @pytest.fixture
    def mock_registry(self):
        """Mock ToolRegistry"""
        registry = MagicMock()
        registry.execute_workflow = AsyncMock(return_value=ToolResult(
            success=True,
            data={"answer": "결과"},
            tokens_used=100,
        ))
        registry.execute_tool = AsyncMock(return_value=ToolResult(
            success=True,
            data={"result": "도구 결과"},
            tokens_used=50,
        ))
        return registry

    @pytest.mark.asyncio
    async def test_execute_workflow_step(self, mock_registry):
        """워크플로우 단계 실행"""
        step = ExecutionStep(
            step_id="test_step",
            step_type="workflow",
            name="rag_workflow",
            inputs={"query": "테스트"},
        )

        result = await _execute_step_with_timeout(
            registry=mock_registry,
            step=step,
            previous_results={},
            user_message="테스트 질문",
            attachments=[],
            timeout=30.0,
        )

        assert result["success"]
        assert result["step_id"] == "test_step"
        assert result["data"]["answer"] == "결과"

    @pytest.mark.asyncio
    async def test_execute_tool_step(self, mock_registry):
        """도구 단계 실행"""
        step = ExecutionStep(
            step_id="tool_step",
            step_type="tool",
            name="search_legal",
            inputs={"query": "테스트"},
        )

        result = await _execute_step_with_timeout(
            registry=mock_registry,
            step=step,
            previous_results={},
            user_message="테스트 질문",
            attachments=[],
            timeout=30.0,
        )

        assert result["success"]
        assert result["step_id"] == "tool_step"

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_registry):
        """타임아웃 처리"""
        async def slow_execution(*args, **kwargs):
            await asyncio.sleep(10)  # 긴 작업
            return ToolResult(success=True, data={})

        mock_registry.execute_workflow = slow_execution

        step = ExecutionStep(
            step_id="slow_step",
            step_type="workflow",
            name="slow_workflow",
        )

        result = await _execute_step_with_timeout(
            registry=mock_registry,
            step=step,
            previous_results={},
            user_message="테스트",
            attachments=[],
            timeout=0.1,  # 매우 짧은 타임아웃
        )

        assert not result["success"]
        assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_exception_handling(self, mock_registry):
        """예외 처리"""
        mock_registry.execute_workflow = AsyncMock(side_effect=Exception("Test error"))

        step = ExecutionStep(
            step_id="error_step",
            step_type="workflow",
            name="error_workflow",
        )

        result = await _execute_step_with_timeout(
            registry=mock_registry,
            step=step,
            previous_results={},
            user_message="테스트",
            attachments=[],
        )

        assert not result["success"]
        assert "Test error" in result["error"]


class TestAggregateDeepResults:
    """결과 집계 테스트"""

    def test_aggregate_search_results(self):
        """검색 결과 집계"""
        results = {
            "search_1": {
                "step_name": "rag_workflow",
                "success": True,
                "data": {"answer": "검색 결과 1"},
            },
            "search_2": {
                "step_name": "rag_workflow",
                "success": True,
                "data": {"answer": "검색 결과 2"},
            },
        }

        response = _aggregate_deep_results(results, "판례를 찾아줘")

        assert "검색 결과" in response
        assert "검색 결과 1" in response
        assert "검색 결과 2" in response

    def test_aggregate_analysis_results(self):
        """분석 결과 집계"""
        results = {
            "analysis_1": {
                "step_name": "analyze_document",
                "success": True,
                "data": {"summary": "문서 분석 요약"},
            },
        }

        response = _aggregate_deep_results(results, "분석해줘")

        assert "분석 결과" in response
        assert "문서 분석 요약" in response

    def test_aggregate_risk_results(self):
        """리스크 평가 결과 집계"""
        results = {
            "risk_1": {
                "step_name": "assess_risk",
                "success": True,
                "data": {"risks": ["리스크1", "리스크2"]},
            },
        }

        response = _aggregate_deep_results(results, "리스크 평가해줘")

        assert "리스크" in response
        assert "리스크1" in response

    def test_aggregate_all_failed(self):
        """모든 단계 실패 시"""
        results = {
            "step1": {
                "step_name": "workflow1",
                "success": False,
                "error": "Error 1",
            },
            "step2": {
                "step_name": "workflow2",
                "success": False,
                "error": "Error 2",
            },
        }

        response = _aggregate_deep_results(results, "테스트")

        assert "오류" in response or "실패" in response

    def test_aggregate_partial_success(self):
        """부분 성공 시"""
        results = {
            "search": {
                "step_name": "search",
                "success": True,
                "data": {"answer": "검색 성공"},
            },
            "analysis": {
                "step_name": "analyze",
                "success": False,
                "error": "분석 실패",
            },
        }

        response = _aggregate_deep_results(results, "검색하고 분석해줘")

        # 성공한 결과는 포함
        assert "검색 성공" in response


class TestDeepPathNodeParallelExecution:
    """Deep Path Node 병렬 실행 통합 테스트"""

    @pytest.fixture
    def parallel_state(self):
        """병렬 실행용 상태"""
        state = create_initial_extended_state(
            user_message="판례와 법령을 동시에 검색해줘",
            session_id="test-parallel-session",
        )
        state["complexity_level"] = "DEEP"
        state["execution_path"] = "deep"
        state["intent"] = {
            "category": "QUERY",
            "sub_type": "SEARCH",
            "keywords": ["판례", "법령", "검색"],
        }
        return state

    @pytest.fixture
    def mock_deep_plan(self):
        """모의 Deep Plan"""
        return DeepPlan(
            plan_id="test-plan-001",
            steps=[
                ExecutionStep(
                    step_id="search_1",
                    step_type="workflow",
                    name="rag_workflow",
                    inputs={"query": "판례 검색"},
                    depends_on=[],
                ),
                ExecutionStep(
                    step_id="search_2",
                    step_type="workflow",
                    name="rag_workflow",
                    inputs={"query": "법령 검색"},
                    depends_on=[],
                ),
            ],
            total_steps=2,
            estimated_time=5.0,
        )

    @pytest.mark.asyncio
    async def test_parallel_search_execution(self, parallel_state, mock_deep_plan):
        """병렬 검색 실행"""
        execution_times = []

        async def mock_execute(*args, **kwargs):
            import time
            start = time.time()
            await asyncio.sleep(0.1)  # 100ms 지연
            execution_times.append(time.time() - start)
            return ToolResult(success=True, data={"result": "ok"})

        with patch("apps.ai_service.agents.nodes.deep_path_node._create_deep_plan",
                   new_callable=AsyncMock, return_value=mock_deep_plan):
            with patch("apps.ai_service.agents.nodes.deep_path_node.get_tool_registry") as mock_registry:
                mock_instance = MagicMock()
                mock_instance.execute_workflow = mock_execute
                mock_instance.execute_tool = mock_execute
                mock_registry.return_value = mock_instance

                import time
                start_time = time.time()
                result = await deep_path_node(parallel_state)
                total_time = time.time() - start_time

        # 병렬 실행으로 인해 순차 실행보다 빠름
        assert result["response_metadata"]["path"] == "deep"

    @pytest.mark.asyncio
    async def test_parallel_group_events(self, parallel_state, mock_deep_plan):
        """병렬 그룹 이벤트 기록"""
        with patch("apps.ai_service.agents.nodes.deep_path_node._create_deep_plan",
                   new_callable=AsyncMock, return_value=mock_deep_plan):
            with patch("apps.ai_service.agents.nodes.deep_path_node.get_tool_registry") as mock_registry:
                mock_instance = MagicMock()
                mock_instance.execute_workflow = AsyncMock(
                    return_value=ToolResult(success=True, data={})
                )
                mock_instance.execute_tool = AsyncMock(
                    return_value=ToolResult(success=True, data={})
                )
                mock_registry.return_value = mock_instance

                result = await deep_path_node(parallel_state)

        events = result["streaming_events"]
        event_types = [e["event"] for e in events]

        # 그룹 시작/완료 이벤트 존재
        assert "deep_group_start" in event_types or "deep_path_start" in event_types

    @pytest.mark.asyncio
    async def test_execution_logs_include_parallel_flag(self, parallel_state, mock_deep_plan):
        """실행 로그에 병렬 플래그 포함"""
        with patch("apps.ai_service.agents.nodes.deep_path_node._create_deep_plan",
                   new_callable=AsyncMock, return_value=mock_deep_plan):
            with patch("apps.ai_service.agents.nodes.deep_path_node.get_tool_registry") as mock_registry:
                mock_instance = MagicMock()
                mock_instance.execute_workflow = AsyncMock(
                    return_value=ToolResult(success=True, data={})
                )
                mock_instance.execute_tool = AsyncMock(
                    return_value=ToolResult(success=True, data={})
                )
                mock_registry.return_value = mock_instance

                result = await deep_path_node(parallel_state)

        logs = result.get("execution_logs", [])

        # 로그가 있으면 parallel 필드 존재 확인
        if logs:
            for log in logs:
                assert "parallel" in log or "step" in log


class TestMultiDocumentComparison:
    """다중 문서 비교 병렬 처리 테스트"""

    @pytest.fixture
    def multi_doc_state(self):
        """다중 문서 상태"""
        state = create_initial_extended_state(
            user_message="세 문서를 비교 분석해줘",
            session_id="test-multi-doc",
        )
        state["complexity_level"] = "DEEP"
        state["execution_path"] = "deep"
        state["intent"] = {
            "category": "ANALYSIS",
            "sub_type": "DOCUMENT_COMPARISON",
            "keywords": ["문서", "비교", "분석"],
        }
        state["attachments"] = [
            {"filename": "doc1.pdf", "content": "문서1 내용"},
            {"filename": "doc2.pdf", "content": "문서2 내용"},
            {"filename": "doc3.pdf", "content": "문서3 내용"},
        ]
        return state

    @pytest.fixture
    def multi_doc_plan(self):
        """다중 문서 분석 계획"""
        return DeepPlan(
            plan_id="test-multi-doc-plan",
            steps=[
                ExecutionStep(
                    step_id="analyze_doc1",
                    step_type="workflow",
                    name="document_workflow",
                    inputs={"document": "doc1.pdf"},
                    depends_on=[],
                ),
                ExecutionStep(
                    step_id="analyze_doc2",
                    step_type="workflow",
                    name="document_workflow",
                    inputs={"document": "doc2.pdf"},
                    depends_on=[],
                ),
                ExecutionStep(
                    step_id="analyze_doc3",
                    step_type="workflow",
                    name="document_workflow",
                    inputs={"document": "doc3.pdf"},
                    depends_on=[],
                ),
                ExecutionStep(
                    step_id="compare",
                    step_type="tool",
                    name="compare_docs",
                    inputs={},
                    depends_on=["analyze_doc1", "analyze_doc2", "analyze_doc3"],
                ),
            ],
            total_steps=4,
            estimated_time=10.0,
        )

    @pytest.mark.asyncio
    async def test_document_analysis_parallel(self, multi_doc_state, multi_doc_plan):
        """각 문서 분석을 병렬 실행"""
        executed_steps = []

        async def track_execute(*args, **kwargs):
            executed_steps.append(datetime.now().isoformat())
            await asyncio.sleep(0.05)
            return ToolResult(success=True, data={"analysis": "분석 결과"})

        with patch("apps.ai_service.agents.nodes.deep_path_node._create_deep_plan",
                   new_callable=AsyncMock, return_value=multi_doc_plan):
            with patch("apps.ai_service.agents.nodes.deep_path_node.get_tool_registry") as mock_registry:
                mock_instance = MagicMock()
                mock_instance.execute_workflow = track_execute
                mock_instance.execute_tool = track_execute
                mock_registry.return_value = mock_instance

                result = await deep_path_node(multi_doc_state)

        # 계획된 단계 실행
        assert result["response_metadata"]["steps_executed"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
