"""
MCP Interface - Model Context Protocol 인터페이스 (Phase 7)

MCP 표준에 따른 도구 정의 및 호출 인터페이스를 제공합니다.
OpenAI Function Calling 및 Anthropic Tool Use 형식과 호환됩니다.

Features:
- MCPToolDefinition: MCP 도구 정의 (멀티 포맷 지원)
- MCPToolCall/MCPToolResult: 도구 호출 및 결과
- MCPToolRegistry: MCP 도구 레지스트리 (병렬 실행 지원)
- create_mcp_registry_from_tool_registry: 기존 ToolRegistry 변환
"""

from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# MCP 도구 타입
# =============================================================================

class MCPToolType(Enum):
    """MCP 도구 타입"""
    FUNCTION = "function"           # 일반 함수 도구
    RETRIEVAL = "retrieval"         # 검색/조회 도구
    CODE_INTERPRETER = "code_interpreter"  # 코드 실행 도구
    WORKFLOW = "workflow"           # 워크플로우 도구


# =============================================================================
# MCP 도구 정의
# =============================================================================

@dataclass
class MCPToolDefinition:
    """
    MCP 도구 정의 (OpenAI/Anthropic 호환)

    MCP 표준에 따른 도구 정의로, OpenAI Function Calling 및
    Anthropic Tool Use 형식으로 변환할 수 있습니다.

    Attributes:
        name: 도구 이름
        description: 도구 설명
        parameters: 입력 파라미터 (JSON Schema 형식)
        tool_type: 도구 타입
        strict: strict mode 여부 (OpenAI)
        required_params: 필수 파라미터 목록
    """
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    tool_type: MCPToolType = MCPToolType.FUNCTION
    strict: bool = False
    required_params: List[str] = field(default_factory=list)

    def to_openai_format(self) -> Dict[str, Any]:
        """
        OpenAI Function Calling 형식으로 변환

        Returns:
            OpenAI tools 배열에 포함될 도구 정의
        """
        function_def = {
            "name": self.name,
            "description": self.description,
            "parameters": self._ensure_json_schema(self.parameters),
        }

        if self.strict:
            function_def["strict"] = True

        return {
            "type": "function",
            "function": function_def,
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """
        Anthropic Tool Use 형식으로 변환

        Returns:
            Anthropic tools 배열에 포함될 도구 정의
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self._ensure_json_schema(self.parameters),
        }

    def to_generic_format(self) -> Dict[str, Any]:
        """
        일반 형식으로 변환 (LangChain 등 호환)

        Returns:
            일반 도구 정의
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "type": self.tool_type.value,
        }

    def _ensure_json_schema(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """JSON Schema 형식 보장"""
        if "type" not in params:
            return {
                "type": "object",
                "properties": params.get("properties", params),
                "required": params.get("required", self.required_params),
            }
        return params


# =============================================================================
# MCP 도구 호출
# =============================================================================

@dataclass
class MCPToolCall:
    """
    MCP 도구 호출

    Attributes:
        tool_name: 호출할 도구 이름
        arguments: 도구 인자
        call_id: 호출 ID (없으면 자동 생성)
    """
    tool_name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None

    def __post_init__(self):
        if self.call_id is None:
            self.call_id = f"call_{uuid.uuid4().hex[:12]}"

    @classmethod
    def from_openai_format(cls, tool_call: Dict[str, Any]) -> "MCPToolCall":
        """OpenAI 도구 호출 형식에서 변환"""
        import json
        function = tool_call.get("function", {})
        arguments = function.get("arguments", "{}")

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        return cls(
            tool_name=function.get("name", ""),
            arguments=arguments,
            call_id=tool_call.get("id"),
        )

    @classmethod
    def from_anthropic_format(cls, tool_use: Dict[str, Any]) -> "MCPToolCall":
        """Anthropic 도구 사용 형식에서 변환"""
        return cls(
            tool_name=tool_use.get("name", ""),
            arguments=tool_use.get("input", {}),
            call_id=tool_use.get("id"),
        )


# =============================================================================
# MCP 도구 결과
# =============================================================================

@dataclass
class MCPToolResult:
    """
    MCP 도구 실행 결과

    Attributes:
        call_id: 호출 ID
        content: 결과 내용
        is_error: 에러 여부
        execution_time: 실행 시간 (초)
    """
    call_id: str
    content: Any
    is_error: bool = False
    execution_time: float = 0.0

    def to_openai_format(self) -> Dict[str, Any]:
        """OpenAI 도구 결과 형식으로 변환"""
        import json
        content = self.content
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)
        elif not isinstance(content, str):
            content = str(content)

        return {
            "tool_call_id": self.call_id,
            "role": "tool",
            "content": content,
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Anthropic 도구 결과 형식으로 변환"""
        content = self.content
        if isinstance(content, dict):
            content_block = {"type": "text", "text": str(content)}
        elif isinstance(content, str):
            content_block = {"type": "text", "text": content}
        else:
            content_block = {"type": "text", "text": str(content)}

        return {
            "type": "tool_result",
            "tool_use_id": self.call_id,
            "content": [content_block],
            "is_error": self.is_error,
        }


# =============================================================================
# MCP 도구 레지스트리
# =============================================================================

class MCPToolRegistry:
    """
    MCP 도구 레지스트리

    MCP 프로토콜에 따른 도구 등록 및 실행을 관리합니다.
    병렬 실행을 지원하며, OpenAI/Anthropic 형식과 호환됩니다.

    Usage:
        registry = MCPToolRegistry()
        registry.register_tool(
            name="search_legal",
            description="법률 정보 검색",
            parameters={"query": {"type": "string"}},
            handler=search_legal_handler,
        )

        definitions = registry.get_tool_definitions(format="openai")
        result = await registry.execute_tool_call(tool_call)
    """

    def __init__(self):
        self._tools: Dict[str, MCPToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        tool_type: MCPToolType = MCPToolType.FUNCTION,
        strict: bool = False,
        required_params: Optional[List[str]] = None,
    ) -> None:
        """
        도구 등록

        Args:
            name: 도구 이름
            description: 도구 설명
            parameters: 입력 파라미터 (JSON Schema)
            handler: 실행 핸들러 (sync 또는 async)
            tool_type: 도구 타입
            strict: strict mode 여부
            required_params: 필수 파라미터 목록
        """
        self._tools[name] = MCPToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            tool_type=tool_type,
            strict=strict,
            required_params=required_params or [],
        )
        self._handlers[name] = handler
        logger.info(f"[MCP] Registered tool: {name} (type={tool_type.value})")

    def unregister_tool(self, name: str) -> bool:
        """도구 등록 해제"""
        if name in self._tools:
            del self._tools[name]
            del self._handlers[name]
            logger.info(f"[MCP] Unregistered tool: {name}")
            return True
        return False

    def get_tool(self, name: str) -> Optional[MCPToolDefinition]:
        """도구 정의 조회"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """등록된 도구 이름 목록"""
        return list(self._tools.keys())

    def get_tool_definitions(
        self,
        format: str = "openai",
        tool_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        도구 정의 목록 반환

        Args:
            format: 출력 형식 ("openai" | "anthropic" | "generic")
            tool_names: 특정 도구만 반환 (None이면 전체)

        Returns:
            도구 정의 목록
        """
        tools = self._tools.values()
        if tool_names:
            tools = [t for t in tools if t.name in tool_names]

        definitions = []
        for tool in tools:
            if format == "openai":
                definitions.append(tool.to_openai_format())
            elif format == "anthropic":
                definitions.append(tool.to_anthropic_format())
            else:
                definitions.append(tool.to_generic_format())

        return definitions

    async def execute_tool_call(
        self,
        tool_call: MCPToolCall,
        timeout: float = 60.0,
    ) -> MCPToolResult:
        """
        도구 호출 실행

        Args:
            tool_call: 도구 호출 정보
            timeout: 타임아웃 (초)

        Returns:
            MCPToolResult
        """
        import time
        start_time = time.time()

        handler = self._handlers.get(tool_call.tool_name)

        if not handler:
            return MCPToolResult(
                call_id=tool_call.call_id or "",
                content={"error": f"Unknown tool: {tool_call.tool_name}"},
                is_error=True,
                execution_time=time.time() - start_time,
            )

        try:
            # 핸들러 실행 (async/sync 지원)
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**tool_call.arguments),
                    timeout=timeout,
                )
            else:
                # sync 함수를 executor에서 실행
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: handler(**tool_call.arguments),
                    ),
                    timeout=timeout,
                )

            return MCPToolResult(
                call_id=tool_call.call_id or "",
                content=result,
                is_error=False,
                execution_time=time.time() - start_time,
            )

        except asyncio.TimeoutError:
            logger.error(f"[MCP] Tool {tool_call.tool_name} timed out after {timeout}s")
            return MCPToolResult(
                call_id=tool_call.call_id or "",
                content={"error": f"Tool execution timed out after {timeout}s"},
                is_error=True,
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            logger.error(f"[MCP] Tool execution error: {e}")
            return MCPToolResult(
                call_id=tool_call.call_id or "",
                content={"error": str(e)},
                is_error=True,
                execution_time=time.time() - start_time,
            )

    async def execute_tool_calls(
        self,
        tool_calls: List[MCPToolCall],
        parallel: bool = True,
        max_concurrent: int = 5,
        timeout: float = 60.0,
    ) -> List[MCPToolResult]:
        """
        여러 도구 호출 실행 (병렬 지원)

        Args:
            tool_calls: 도구 호출 목록
            parallel: 병렬 실행 여부
            max_concurrent: 최대 동시 실행 수
            timeout: 개별 타임아웃 (초)

        Returns:
            MCPToolResult 목록 (입력 순서 유지)
        """
        if not tool_calls:
            return []

        if parallel and len(tool_calls) > 1:
            semaphore = asyncio.Semaphore(max_concurrent)

            async def execute_with_semaphore(tc: MCPToolCall) -> MCPToolResult:
                async with semaphore:
                    return await self.execute_tool_call(tc, timeout=timeout)

            tasks = [execute_with_semaphore(tc) for tc in tool_calls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 예외를 MCPToolResult로 변환
            converted_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    converted_results.append(MCPToolResult(
                        call_id=tool_calls[i].call_id or "",
                        content={"error": str(result)},
                        is_error=True,
                    ))
                else:
                    converted_results.append(result)

            return converted_results
        else:
            # 순차 실행
            results = []
            for tc in tool_calls:
                result = await self.execute_tool_call(tc, timeout=timeout)
                results.append(result)
            return results

    def get_stats(self) -> Dict[str, Any]:
        """레지스트리 통계"""
        type_counts = {}
        for tool in self._tools.values():
            type_name = tool.tool_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "total_tools": len(self._tools),
            "by_type": type_counts,
            "tool_names": list(self._tools.keys()),
        }


# =============================================================================
# 기존 ToolRegistry 변환 함수
# =============================================================================

def _python_type_to_json_type(python_type: str) -> str:
    """Python 타입을 JSON Schema 타입으로 변환"""
    mapping = {
        "str": "string",
        "int": "integer",
        "float": "number",
        "bool": "boolean",
        "list": "array",
        "dict": "object",
        "any": "string",  # 기본값
    }
    return mapping.get(python_type.lower(), "string")


def create_mcp_registry_from_tool_registry(
    tool_registry=None,
) -> MCPToolRegistry:
    """
    기존 ToolRegistry를 MCPToolRegistry로 변환

    Phase 1에서 구현된 ToolRegistry를 MCP 형식으로 변환하여
    OpenAI/Anthropic API와 호환되게 합니다.

    Args:
        tool_registry: 기존 ToolRegistry 인스턴스 (None이면 싱글톤 사용)

    Returns:
        MCPToolRegistry 인스턴스

    Usage:
        mcp_registry = create_mcp_registry_from_tool_registry()
        definitions = mcp_registry.get_tool_definitions(format="openai")
    """
    # 지연 import로 순환 참조 방지
    from apps.ai_service.agents.tools.registry import (
        get_tool_registry,
        ToolCategory,
    )

    if tool_registry is None:
        tool_registry = get_tool_registry()

    mcp_registry = MCPToolRegistry()

    # 카테고리 → MCP 도구 타입 매핑
    category_to_type = {
        ToolCategory.SEARCH: MCPToolType.RETRIEVAL,
        ToolCategory.ANALYSIS: MCPToolType.FUNCTION,
        ToolCategory.DOCUMENT: MCPToolType.FUNCTION,
        ToolCategory.EXTERNAL_API: MCPToolType.FUNCTION,
        ToolCategory.UTILITY: MCPToolType.FUNCTION,
    }

    for tool_name in tool_registry.list_tools():
        tool_def = tool_registry.get_tool(tool_name)
        if not tool_def:
            continue

        # JSON Schema 형식으로 파라미터 변환
        properties = {}
        required = []

        for param_name, param_type in tool_def.input_schema.items():
            json_type = _python_type_to_json_type(param_type)
            properties[param_name] = {
                "type": json_type,
                "description": f"{param_name} 파라미터",
            }
            required.append(param_name)

        parameters = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        # 핸들러 생성 (클로저로 tool_name 캡처)
        def create_handler(tn: str):
            async def handler(**kwargs):
                result = await tool_registry.execute_tool(tn, kwargs)
                if result.success:
                    return result.data
                else:
                    return {"error": result.error}
            return handler

        # MCP 도구 타입 결정
        mcp_type = category_to_type.get(
            tool_def.category,
            MCPToolType.FUNCTION,
        )

        # 도구 등록
        mcp_registry.register_tool(
            name=tool_name,
            description=tool_def.description,
            parameters=parameters,
            handler=create_handler(tool_name),
            tool_type=mcp_type,
            required_params=required,
        )

    logger.info(
        f"[MCP] Created MCPToolRegistry with {len(mcp_registry.list_tools())} tools "
        f"from ToolRegistry"
    )

    return mcp_registry


# =============================================================================
# 싱글톤 인스턴스
# =============================================================================

_mcp_registry_instance: Optional[MCPToolRegistry] = None


def get_mcp_registry(
    from_tool_registry: bool = True,
) -> MCPToolRegistry:
    """
    MCPToolRegistry 싱글톤 반환

    Args:
        from_tool_registry: True면 ToolRegistry에서 변환, False면 빈 레지스트리

    Returns:
        MCPToolRegistry 인스턴스
    """
    global _mcp_registry_instance

    if _mcp_registry_instance is None:
        if from_tool_registry:
            _mcp_registry_instance = create_mcp_registry_from_tool_registry()
        else:
            _mcp_registry_instance = MCPToolRegistry()

    return _mcp_registry_instance


def reset_mcp_registry() -> None:
    """MCPToolRegistry 싱글톤 초기화"""
    global _mcp_registry_instance
    _mcp_registry_instance = None
