"""
MCP (Model Context Protocol) Server

Phase 4 - Week 12 예정: FastMCP 기반 MCP 서버
Phase 7 - MCP 인터페이스 통합

디렉토리 구조:
- server.py: MCP 서버 진입점
- interface.py: MCP 인터페이스 (Phase 7)
- tools/: MCP Tool 정의
- resources/: MCP Resource 정의

Features (Phase 7):
- MCPToolType: 도구 타입 enum
- MCPToolDefinition: 도구 정의 (OpenAI/Anthropic 호환)
- MCPToolCall/MCPToolResult: 도구 호출 및 결과
- MCPToolRegistry: MCP 도구 레지스트리 (병렬 실행 지원)
- create_mcp_registry_from_tool_registry: 기존 ToolRegistry 변환

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""

from apps.ai_service.mcp.interface import (
    # Enums
    MCPToolType,
    # Dataclasses
    MCPToolDefinition,
    MCPToolCall,
    MCPToolResult,
    # Classes
    MCPToolRegistry,
    # Factory functions
    create_mcp_registry_from_tool_registry,
    get_mcp_registry,
    reset_mcp_registry,
)

__all__ = [
    # Enums
    "MCPToolType",
    # Dataclasses
    "MCPToolDefinition",
    "MCPToolCall",
    "MCPToolResult",
    # Classes
    "MCPToolRegistry",
    # Factory functions
    "create_mcp_registry_from_tool_registry",
    "get_mcp_registry",
    "reset_mcp_registry",
]
