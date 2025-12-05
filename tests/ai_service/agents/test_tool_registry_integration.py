"""
Phase 8: ToolRegistry 통합 테스트

테스트 항목:
1. 도구 등록 및 조회
2. 카테고리별 필터링
3. 폴백 체인 조회
4. 비용 추정
5. 외부 API 도구 등록
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from apps.ai_service.agents.tools.registry import (
    ToolRegistry,
    ToolDefinition,
    ToolCategory,
    ToolResult,
    TOOL_WORKFLOW_MAP,
    TOOL_FALLBACK_CHAIN,
    get_tool_registry,
    init_tool_registry,
)


class TestToolRegistration:
    """도구 등록 및 조회 테스트"""

    def test_default_tools_registered(self):
        """기본 도구들이 등록되어 있는지 확인"""
        registry = ToolRegistry()
        tools = registry.list_tools()

        # 기본 검색/분석 도구 확인
        expected_tools = [
            "search_legal",
            "search_precedents",
            "search_statutes",
            "analyze_document",
            "analyze_case",
            "assess_risk",
        ]

        for tool in expected_tools:
            assert tool in tools, f"Expected tool '{tool}' not found"

    def test_get_tool_returns_definition(self):
        """도구 정의 조회"""
        registry = ToolRegistry()
        tool = registry.get_tool("search_legal")

        assert tool is not None
        assert isinstance(tool, ToolDefinition)
        assert tool.name == "search_legal"
        assert tool.category == ToolCategory.SEARCH
        assert tool.workflow_name == "rag_workflow"

    def test_get_nonexistent_tool_returns_none(self):
        """존재하지 않는 도구는 None 반환"""
        registry = ToolRegistry()
        tool = registry.get_tool("nonexistent_tool")
        assert tool is None

    def test_tool_definition_fields(self):
        """도구 정의 필드 확인"""
        registry = ToolRegistry()
        tool = registry.get_tool("analyze_document")

        assert tool is not None
        assert tool.description  # 설명 존재
        assert tool.input_schema  # 입력 스키마 존재
        assert tool.output_schema  # 출력 스키마 존재
        assert tool.estimated_tokens > 0  # 예상 토큰
        assert tool.timeout > 0  # 타임아웃


class TestCategoryFiltering:
    """카테고리별 도구 필터링 테스트"""

    def test_list_tools_by_category_search(self):
        """검색 카테고리 필터링"""
        registry = ToolRegistry()
        search_tools = registry.list_tools_by_category(ToolCategory.SEARCH)

        assert "search_legal" in search_tools
        assert "search_precedents" in search_tools
        assert "analyze_document" not in search_tools

    def test_list_tools_by_category_analysis(self):
        """분석 카테고리 필터링"""
        registry = ToolRegistry()
        analysis_tools = registry.list_tools_by_category(ToolCategory.ANALYSIS)

        assert "analyze_document" in analysis_tools or "analyze_case" in analysis_tools
        assert "search_legal" not in analysis_tools

    def test_get_tools_for_context_search_query(self):
        """검색 키워드에 맞는 도구 필터링"""
        registry = ToolRegistry()
        tools = registry.get_tools_for_context("판례를 검색해줘")

        tool_names = [t.name for t in tools]
        # 검색 또는 외부 API 카테고리 도구가 포함되어야 함
        assert any("search" in name for name in tool_names)

    def test_get_tools_for_context_analysis_query(self):
        """분석 키워드에 맞는 도구 필터링"""
        registry = ToolRegistry()
        tools = registry.get_tools_for_context("계약서를 분석해줘")

        tool_names = [t.name for t in tools]
        # 분석 또는 문서 카테고리 도구가 포함되어야 함
        assert any("analy" in name or "document" in name or "contract" in name for name in tool_names)

    def test_get_tools_for_context_max_tools(self):
        """최대 도구 수 제한"""
        registry = ToolRegistry()
        tools = registry.get_tools_for_context("판례와 법령을 검색해줘", max_tools=3)

        assert len(tools) <= 3

    def test_get_tools_for_context_with_category_filter(self):
        """카테고리 필터와 함께 도구 조회"""
        registry = ToolRegistry()
        tools = registry.get_tools_for_context(
            "검색해줘",
            categories=[ToolCategory.SEARCH],
            max_tools=5,
        )

        # 모든 도구가 SEARCH 카테고리여야 함
        for tool in tools:
            assert tool.category == ToolCategory.SEARCH


class TestFallbackChain:
    """폴백 체인 테스트"""

    def test_get_fallback_tools(self):
        """폴백 도구 목록 조회"""
        registry = ToolRegistry()
        fallbacks = registry.get_fallback_tools("search_legal")

        assert isinstance(fallbacks, list)
        assert len(fallbacks) > 0

    def test_fallback_chain_exists(self):
        """폴백 체인 정의 확인"""
        assert "search_legal" in TOOL_FALLBACK_CHAIN
        assert "search_precedents" in TOOL_FALLBACK_CHAIN

    def test_nonexistent_tool_no_fallback(self):
        """존재하지 않는 도구는 빈 폴백"""
        registry = ToolRegistry()
        fallbacks = registry.get_fallback_tools("nonexistent_tool")

        assert fallbacks == []


class TestCostEstimation:
    """비용 추정 테스트"""

    def test_estimate_cost_single_tool(self):
        """단일 도구 비용 추정"""
        registry = ToolRegistry()
        cost = registry.estimate_cost(["search_legal"])

        assert "total_estimated_tokens" in cost
        assert "total_estimated_time" in cost
        assert "per_tool" in cost
        assert cost["total_estimated_tokens"] > 0

    def test_estimate_cost_multiple_tools(self):
        """다중 도구 비용 추정"""
        registry = ToolRegistry()
        cost = registry.estimate_cost(["search_legal", "analyze_document"])

        # 개별 비용 합산과 같아야 함
        per_tool = cost["per_tool"]
        total = sum(t["tokens"] for t in per_tool.values())
        assert cost["total_estimated_tokens"] == total

    def test_estimate_cost_nonexistent_tool(self):
        """존재하지 않는 도구는 비용 0"""
        registry = ToolRegistry()
        cost = registry.estimate_cost(["nonexistent"])

        assert cost["total_estimated_tokens"] == 0
        assert cost["total_estimated_time"] == 0


class TestToolExecution:
    """도구 실행 테스트"""

    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """도구 실행 성공"""
        registry = ToolRegistry()

        # WorkflowExecutor를 mock
        with patch.object(registry._executor, "execute", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = MagicMock(
                success=True,
                data={"answer": "검색 결과"},
            )

            result = await registry.execute_tool(
                "search_legal",
                {"query": "테스트 쿼리"},
            )

            assert result.success
            assert result.data["answer"] == "검색 결과"

    @pytest.mark.asyncio
    async def test_execute_tool_with_fallback(self):
        """도구 실패 시 폴백 실행"""
        registry = ToolRegistry()

        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 첫 번째 호출 실패
                return MagicMock(success=False, error="Primary failed")
            return MagicMock(success=True, data={"result": "fallback result"})

        with patch.object(registry._executor, "execute", side_effect=mock_execute):
            result = await registry.execute_tool(
                "search_legal",
                {"query": "테스트"},
                use_fallback=True,
                max_retries=0,  # 재시도 없이 바로 폴백
            )

            # 폴백 성공 가능 (폴백 도구도 실패할 수 있음)
            # 여기서는 call_count > 1 확인
            assert call_count > 1

    @pytest.mark.asyncio
    async def test_execute_tool_retry(self):
        """도구 실행 재시도"""
        registry = ToolRegistry()

        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return MagicMock(success=False, error="Retry needed")
            return MagicMock(success=True, data={"result": "success"})

        with patch.object(registry._executor, "execute", side_effect=mock_execute):
            result = await registry.execute_tool(
                "search_legal",
                {"query": "테스트"},
                use_fallback=False,
                max_retries=3,
            )

            assert call_count >= 2  # 적어도 재시도가 발생

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        """알 수 없는 도구 실행"""
        registry = ToolRegistry()

        result = await registry.execute_tool(
            "unknown_tool",
            {"query": "테스트"},
        )

        assert not result.success
        assert "Unknown tool" in result.error


class TestParallelExecution:
    """병렬 실행 테스트"""

    @pytest.mark.asyncio
    async def test_execute_tools_parallel(self):
        """여러 도구 병렬 실행"""
        registry = ToolRegistry()

        with patch.object(registry._executor, "execute", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = MagicMock(
                success=True,
                data={"result": "ok"},
            )

            tool_calls = [
                {"tool_name": "search_legal", "inputs": {"query": "쿼리1"}},
                {"tool_name": "search_precedents", "inputs": {"query": "쿼리2"}},
                {"tool_name": "search_statutes", "inputs": {"query": "쿼리3"}},
            ]

            results = await registry.execute_tools_parallel(tool_calls, max_concurrent=3)

            assert len(results) == 3
            assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_execute_tools_parallel_with_failures(self):
        """병렬 실행 중 일부 실패"""
        registry = ToolRegistry()

        async def mock_execute(tool_name, *args, **kwargs):
            # 특정 도구만 실패하도록 설정
            if tool_name == "search_precedents":
                return ToolResult(success=False, error="Precedents search failed")
            return ToolResult(success=True, data={"result": "ok"})

        # execute_tool 메서드를 직접 패치
        with patch.object(registry, "execute_tool", side_effect=mock_execute):
            tool_calls = [
                {"tool_name": "search_legal", "inputs": {}},
                {"tool_name": "search_precedents", "inputs": {}},
                {"tool_name": "search_statutes", "inputs": {}},
            ]

            results = await registry.execute_tools_parallel(tool_calls)

            assert len(results) == 3
            # 하나는 실패
            success_count = sum(1 for r in results if r.success)
            assert success_count == 2


class TestSingleton:
    """싱글톤 패턴 테스트"""

    def test_get_tool_registry_returns_same_instance(self):
        """싱글톤 인스턴스 반환"""
        # 기존 인스턴스 초기화
        init_tool_registry()

        registry1 = get_tool_registry()
        registry2 = get_tool_registry()

        assert registry1 is registry2

    def test_init_tool_registry_creates_new_instance(self):
        """명시적 초기화 시 새 인스턴스 생성"""
        registry1 = init_tool_registry()
        registry2 = init_tool_registry()

        # 다른 인스턴스
        assert registry1 is not registry2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
