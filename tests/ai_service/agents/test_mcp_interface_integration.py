"""
Phase 8: MCP 인터페이스 통합 테스트

테스트 항목:
1. MCP 도구 정의 (MCPToolDefinition)
2. 도구 호출/결과 형식 변환
3. MCPToolRegistry 등록 및 실행
4. OpenAI/Anthropic 형식 변환
5. 병렬 도구 실행
6. ToolRegistry → MCPToolRegistry 변환
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from apps.ai_service.mcp.interface import (
    MCPToolType,
    MCPToolDefinition,
    MCPToolCall,
    MCPToolResult,
    MCPToolRegistry,
    create_mcp_registry_from_tool_registry,
    get_mcp_registry,
    reset_mcp_registry,
    _python_type_to_json_type,
)


class TestMCPToolDefinition:
    """MCPToolDefinition 테스트"""

    def test_basic_definition(self):
        """기본 도구 정의"""
        definition = MCPToolDefinition(
            name="search_legal",
            description="법률 정보 검색",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색 쿼리"},
                },
                "required": ["query"],
            },
        )

        assert definition.name == "search_legal"
        assert definition.tool_type == MCPToolType.FUNCTION
        assert not definition.strict

    def test_to_openai_format(self):
        """OpenAI 형식 변환"""
        definition = MCPToolDefinition(
            name="analyze_document",
            description="문서 분석",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                },
            },
            strict=True,
        )

        openai_format = definition.to_openai_format()

        assert openai_format["type"] == "function"
        assert openai_format["function"]["name"] == "analyze_document"
        assert openai_format["function"]["description"] == "문서 분석"
        assert openai_format["function"]["strict"] is True
        assert "parameters" in openai_format["function"]

    def test_to_anthropic_format(self):
        """Anthropic 형식 변환"""
        definition = MCPToolDefinition(
            name="search_precedents",
            description="판례 검색",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer"},
                },
            },
        )

        anthropic_format = definition.to_anthropic_format()

        assert anthropic_format["name"] == "search_precedents"
        assert anthropic_format["description"] == "판례 검색"
        assert "input_schema" in anthropic_format

    def test_to_generic_format(self):
        """일반 형식 변환"""
        definition = MCPToolDefinition(
            name="test_tool",
            description="테스트 도구",
            parameters={"query": "string"},
            tool_type=MCPToolType.RETRIEVAL,
        )

        generic_format = definition.to_generic_format()

        assert generic_format["name"] == "test_tool"
        assert generic_format["type"] == "retrieval"

    def test_ensure_json_schema(self):
        """JSON Schema 형식 보장"""
        definition = MCPToolDefinition(
            name="simple_tool",
            description="간단한 도구",
            parameters={"query": "string"},  # 간단한 형식
            required_params=["query"],
        )

        openai_format = definition.to_openai_format()
        params = openai_format["function"]["parameters"]

        # JSON Schema 형식으로 변환됨
        assert params["type"] == "object"
        assert "properties" in params


class TestMCPToolCall:
    """MCPToolCall 테스트"""

    def test_basic_call(self):
        """기본 도구 호출"""
        call = MCPToolCall(
            tool_name="search_legal",
            arguments={"query": "계약 해지"},
        )

        assert call.tool_name == "search_legal"
        assert call.arguments == {"query": "계약 해지"}
        assert call.call_id is not None  # 자동 생성

    def test_call_with_id(self):
        """ID가 있는 도구 호출"""
        call = MCPToolCall(
            tool_name="analyze",
            arguments={},
            call_id="call_12345",
        )

        assert call.call_id == "call_12345"

    def test_from_openai_format(self):
        """OpenAI 형식에서 변환"""
        openai_call = {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "search_legal",
                "arguments": '{"query": "테스트"}',
            },
        }

        call = MCPToolCall.from_openai_format(openai_call)

        assert call.tool_name == "search_legal"
        assert call.arguments == {"query": "테스트"}
        assert call.call_id == "call_abc123"

    def test_from_anthropic_format(self):
        """Anthropic 형식에서 변환"""
        anthropic_use = {
            "id": "toolu_123",
            "type": "tool_use",
            "name": "analyze_document",
            "input": {"content": "문서 내용"},
        }

        call = MCPToolCall.from_anthropic_format(anthropic_use)

        assert call.tool_name == "analyze_document"
        assert call.arguments == {"content": "문서 내용"}
        assert call.call_id == "toolu_123"


class TestMCPToolResult:
    """MCPToolResult 테스트"""

    def test_success_result(self):
        """성공 결과"""
        result = MCPToolResult(
            call_id="call_123",
            content={"answer": "검색 결과"},
            is_error=False,
            execution_time=0.5,
        )

        assert result.call_id == "call_123"
        assert result.content == {"answer": "검색 결과"}
        assert not result.is_error
        assert result.execution_time == 0.5

    def test_error_result(self):
        """에러 결과"""
        result = MCPToolResult(
            call_id="call_456",
            content={"error": "Something went wrong"},
            is_error=True,
        )

        assert result.is_error
        assert "error" in result.content

    def test_to_openai_format(self):
        """OpenAI 형식으로 변환"""
        result = MCPToolResult(
            call_id="call_789",
            content={"data": "결과"},
        )

        openai_format = result.to_openai_format()

        assert openai_format["tool_call_id"] == "call_789"
        assert openai_format["role"] == "tool"
        assert isinstance(openai_format["content"], str)

    def test_to_anthropic_format(self):
        """Anthropic 형식으로 변환"""
        result = MCPToolResult(
            call_id="toolu_abc",
            content="텍스트 결과",
            is_error=True,
        )

        anthropic_format = result.to_anthropic_format()

        assert anthropic_format["type"] == "tool_result"
        assert anthropic_format["tool_use_id"] == "toolu_abc"
        assert anthropic_format["is_error"] is True
        assert isinstance(anthropic_format["content"], list)


class TestMCPToolRegistry:
    """MCPToolRegistry 테스트"""

    @pytest.fixture
    def registry(self):
        """테스트용 레지스트리"""
        reg = MCPToolRegistry()

        # 테스트 도구 등록
        reg.register_tool(
            name="test_search",
            description="테스트 검색 도구",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
            },
            handler=AsyncMock(return_value={"results": ["결과1", "결과2"]}),
            tool_type=MCPToolType.RETRIEVAL,
        )

        reg.register_tool(
            name="test_analyze",
            description="테스트 분석 도구",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                },
            },
            handler=AsyncMock(return_value={"analysis": "분석 결과"}),
        )

        return reg

    def test_register_tool(self, registry):
        """도구 등록"""
        tools = registry.list_tools()

        assert "test_search" in tools
        assert "test_analyze" in tools

    def test_get_tool(self, registry):
        """도구 정의 조회"""
        tool = registry.get_tool("test_search")

        assert tool is not None
        assert tool.name == "test_search"
        assert tool.tool_type == MCPToolType.RETRIEVAL

    def test_unregister_tool(self, registry):
        """도구 등록 해제"""
        result = registry.unregister_tool("test_search")

        assert result is True
        assert "test_search" not in registry.list_tools()

    def test_unregister_nonexistent(self, registry):
        """존재하지 않는 도구 해제"""
        result = registry.unregister_tool("nonexistent")
        assert result is False

    def test_get_tool_definitions_openai(self, registry):
        """OpenAI 형식 도구 정의 목록"""
        definitions = registry.get_tool_definitions(format="openai")

        assert len(definitions) == 2
        assert all(d["type"] == "function" for d in definitions)

    def test_get_tool_definitions_anthropic(self, registry):
        """Anthropic 형식 도구 정의 목록"""
        definitions = registry.get_tool_definitions(format="anthropic")

        assert len(definitions) == 2
        assert all("input_schema" in d for d in definitions)

    def test_get_tool_definitions_filtered(self, registry):
        """특정 도구만 조회"""
        definitions = registry.get_tool_definitions(
            format="openai",
            tool_names=["test_search"],
        )

        assert len(definitions) == 1
        assert definitions[0]["function"]["name"] == "test_search"

    @pytest.mark.asyncio
    async def test_execute_tool_call_success(self, registry):
        """도구 호출 성공"""
        call = MCPToolCall(
            tool_name="test_search",
            arguments={"query": "테스트"},
        )

        result = await registry.execute_tool_call(call)

        assert not result.is_error
        assert result.content == {"results": ["결과1", "결과2"]}
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, registry):
        """알 수 없는 도구 호출"""
        call = MCPToolCall(
            tool_name="unknown_tool",
            arguments={},
        )

        result = await registry.execute_tool_call(call)

        assert result.is_error
        assert "Unknown tool" in str(result.content)

    @pytest.mark.asyncio
    async def test_execute_tool_timeout(self, registry):
        """도구 실행 타임아웃"""
        async def slow_handler(**kwargs):
            await asyncio.sleep(10)
            return {"result": "ok"}

        registry.register_tool(
            name="slow_tool",
            description="느린 도구",
            parameters={},
            handler=slow_handler,
        )

        call = MCPToolCall(tool_name="slow_tool", arguments={})

        result = await registry.execute_tool_call(call, timeout=0.1)

        assert result.is_error
        assert "timed out" in str(result.content)

    @pytest.mark.asyncio
    async def test_execute_tool_exception(self, registry):
        """도구 실행 예외"""
        async def error_handler(**kwargs):
            raise ValueError("Test error")

        registry.register_tool(
            name="error_tool",
            description="에러 도구",
            parameters={},
            handler=error_handler,
        )

        call = MCPToolCall(tool_name="error_tool", arguments={})

        result = await registry.execute_tool_call(call)

        assert result.is_error
        assert "Test error" in str(result.content)


class TestParallelExecution:
    """병렬 도구 실행 테스트"""

    @pytest.fixture
    def registry(self):
        """병렬 실행 테스트용 레지스트리"""
        reg = MCPToolRegistry()

        for i in range(5):
            async def handler(index=i, **kwargs):
                await asyncio.sleep(0.05)  # 50ms 지연
                return {"tool_index": index}

            reg.register_tool(
                name=f"tool_{i}",
                description=f"도구 {i}",
                parameters={},
                handler=handler,
            )

        return reg

    @pytest.mark.asyncio
    async def test_parallel_execution(self, registry):
        """병렬 실행"""
        calls = [
            MCPToolCall(tool_name=f"tool_{i}", arguments={})
            for i in range(5)
        ]

        import time
        start = time.time()
        results = await registry.execute_tool_calls(
            calls,
            parallel=True,
            max_concurrent=5,
        )
        elapsed = time.time() - start

        assert len(results) == 5
        assert all(not r.is_error for r in results)

        # 병렬 실행으로 순차보다 빠름
        # 순차: 5 * 0.05 = 0.25s, 병렬: ~0.05s + 오버헤드
        assert elapsed < 0.2

    @pytest.mark.asyncio
    async def test_sequential_execution(self, registry):
        """순차 실행"""
        calls = [
            MCPToolCall(tool_name=f"tool_{i}", arguments={})
            for i in range(3)
        ]

        import time
        start = time.time()
        results = await registry.execute_tool_calls(
            calls,
            parallel=False,
        )
        elapsed = time.time() - start

        assert len(results) == 3

        # 순차 실행: 3 * 0.05 = 0.15s 이상
        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_parallel_with_failures(self, registry):
        """병렬 실행 중 일부 실패"""
        async def fail_handler(**kwargs):
            raise Exception("Failed")

        registry.register_tool(
            name="fail_tool",
            description="실패 도구",
            parameters={},
            handler=fail_handler,
        )

        calls = [
            MCPToolCall(tool_name="tool_0", arguments={}),
            MCPToolCall(tool_name="fail_tool", arguments={}),
            MCPToolCall(tool_name="tool_1", arguments={}),
        ]

        results = await registry.execute_tool_calls(calls, parallel=True)

        assert len(results) == 3
        assert not results[0].is_error
        assert results[1].is_error
        assert not results[2].is_error

    @pytest.mark.asyncio
    async def test_max_concurrent_limit(self, registry):
        """최대 동시 실행 제한"""
        execution_times = []

        async def tracking_handler(**kwargs):
            import time
            start = time.time()
            await asyncio.sleep(0.05)
            execution_times.append((start, time.time()))
            return {"ok": True}

        for i in range(5):
            registry.unregister_tool(f"tool_{i}")
            registry.register_tool(
                name=f"tool_{i}",
                description=f"도구 {i}",
                parameters={},
                handler=tracking_handler,
            )

        calls = [
            MCPToolCall(tool_name=f"tool_{i}", arguments={})
            for i in range(5)
        ]

        await registry.execute_tool_calls(
            calls,
            parallel=True,
            max_concurrent=2,  # 최대 2개 동시
        )

        # 실행 완료 확인
        assert len(execution_times) == 5


class TestToolRegistryConversion:
    """ToolRegistry → MCPToolRegistry 변환 테스트"""

    def test_create_mcp_registry_from_tool_registry(self):
        """ToolRegistry에서 MCPToolRegistry 생성"""
        # 실제 ToolRegistry에서 변환
        mcp_registry = create_mcp_registry_from_tool_registry()

        tools = mcp_registry.list_tools()

        # 기본 도구들이 변환됨
        assert len(tools) > 0
        assert "search_legal" in tools or any("search" in t for t in tools)

    def test_converted_tool_definitions(self):
        """변환된 도구 정의"""
        mcp_registry = create_mcp_registry_from_tool_registry()

        definitions = mcp_registry.get_tool_definitions(format="openai")

        # 각 정의가 유효함
        for d in definitions:
            assert d["type"] == "function"
            assert "name" in d["function"]
            assert "description" in d["function"]
            assert "parameters" in d["function"]

    def test_stats(self):
        """레지스트리 통계"""
        mcp_registry = create_mcp_registry_from_tool_registry()

        stats = mcp_registry.get_stats()

        assert "total_tools" in stats
        assert "by_type" in stats
        assert "tool_names" in stats
        assert stats["total_tools"] == len(stats["tool_names"])


class TestPythonTypeConversion:
    """Python 타입 → JSON 타입 변환 테스트"""

    def test_basic_types(self):
        """기본 타입 변환"""
        assert _python_type_to_json_type("str") == "string"
        assert _python_type_to_json_type("int") == "integer"
        assert _python_type_to_json_type("float") == "number"
        assert _python_type_to_json_type("bool") == "boolean"
        assert _python_type_to_json_type("list") == "array"
        assert _python_type_to_json_type("dict") == "object"

    def test_unknown_type(self):
        """알 수 없는 타입은 string"""
        assert _python_type_to_json_type("unknown") == "string"
        assert _python_type_to_json_type("Any") == "string"


class TestSingleton:
    """싱글톤 패턴 테스트"""

    def test_get_mcp_registry(self):
        """싱글톤 인스턴스"""
        reset_mcp_registry()

        registry1 = get_mcp_registry()
        registry2 = get_mcp_registry()

        assert registry1 is registry2

    def test_reset_mcp_registry(self):
        """싱글톤 리셋"""
        registry1 = get_mcp_registry()
        reset_mcp_registry()
        registry2 = get_mcp_registry()

        assert registry1 is not registry2

    def test_get_empty_registry(self):
        """빈 레지스트리"""
        reset_mcp_registry()

        registry = get_mcp_registry(from_tool_registry=False)

        assert len(registry.list_tools()) == 0


class TestSyncFunctionSupport:
    """동기 함수 핸들러 지원 테스트"""

    @pytest.mark.asyncio
    async def test_sync_handler(self):
        """동기 핸들러 실행"""
        registry = MCPToolRegistry()

        def sync_handler(**kwargs):
            return {"sync": True, "query": kwargs.get("query")}

        registry.register_tool(
            name="sync_tool",
            description="동기 도구",
            parameters={},
            handler=sync_handler,
        )

        call = MCPToolCall(
            tool_name="sync_tool",
            arguments={"query": "테스트"},
        )

        result = await registry.execute_tool_call(call)

        assert not result.is_error
        assert result.content["sync"] is True
        assert result.content["query"] == "테스트"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
