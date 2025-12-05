"""
Think Node - 현재 상황 분석 및 다음 행동 결정

Phase 6-1: Thinking Agent - ReAct 패턴의 Think 단계

역할:
- 현재 상황 분석
- 목표 달성을 위한 다음 행동 결정
- 적절한 도구 선택 또는 최종 답변 제시
"""

from datetime import datetime
from typing import Dict, Any, Optional
import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from apps.ai_service.agents.states.master_agent_state import (
    FullMasterAgentState,
    ThoughtStep,
    StreamingEvent,
)
from apps.ai_service.agents.tools.registry import get_tool_registry
from apps.ai_service.config.settings import settings

logger = logging.getLogger(__name__)


# =============================================================================
# 사고 프롬프트
# =============================================================================

THINK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 법률 전문 AI 어시스턴트입니다.
목표 달성을 위해 단계별로 사고하고 적절한 도구를 사용합니다.

## 목표
{goal}

## 사용 가능한 도구
{available_tools}

## 지금까지의 과정
{thought_history}

## 수집된 정보
{accumulated_context}

## 지시사항
1. 현재 상황을 분석하세요
2. 목표 달성에 필요한 다음 행동을 결정하세요
3. 충분한 정보가 있으면 FINAL_ANSWER를 선택하세요

## 응답 형식 (JSON)
{{
    "thought": "현재 상황 분석과 다음 행동에 대한 생각",
    "action": "도구이름 또는 FINAL_ANSWER",
    "action_input": {{"param": "value"}} 또는 "최종 답변"
}}"""),
    ("human", "사용자 질문: {user_message}"),
])


# =============================================================================
# Think Node
# =============================================================================

async def think_node(state: FullMasterAgentState) -> Dict[str, Any]:
    """
    사고 노드 - 상황 분석 및 다음 행동 결정

    Args:
        state: FullMasterAgentState

    Returns:
        업데이트된 상태 필드
    """
    logger.info(f"[think_node] Step {state.get('current_step', 0) + 1}")

    user_message = state.get("user_message", "")
    goal = state.get("goal", user_message)
    thought_history = list(state.get("thought_history", []))
    accumulated_context = list(state.get("accumulated_context", []))
    available_tools = state.get("available_tools", [])
    tool_descriptions = state.get("tool_descriptions", {})  # Phase 7
    streaming_events = list(state.get("streaming_events", []))

    # 도구 목록 가져오기 (Phase 7: 폴백도 질문 기반 필터링 사용)
    if not available_tools:
        registry = get_tool_registry()
        # 질문 기반 필터링 시도
        filtered_defs = registry.get_tools_for_context(query=user_message, max_tools=8)
        available_tools = [tool.name for tool in filtered_defs]
        tool_descriptions = {
            tool.name: {
                "description": tool.description,
                "category": tool.category.value,
                "estimated_tokens": tool.estimated_tokens,
            }
            for tool in filtered_defs
        }
        logger.info(f"[think_node] Fallback filtered {len(available_tools)} tools")

    # 포맷팅
    thought_str = _format_history(thought_history)
    tools_str = _format_tools_with_details(available_tools, tool_descriptions)  # Phase 7
    context_str = "\n".join(accumulated_context) if accumulated_context else "(없음)"

    # 사고 시작 이벤트
    streaming_events.append(StreamingEvent(
        event="thinking_step",
        data={"step": state.get("current_step", 0) + 1, "phase": "thinking"},
        timestamp=datetime.now().isoformat(),
    ).model_dump())

    # LLM 호출 (settings 사용)
    # base_url 정규화: /v1이 없으면 추가
    base_url = None
    if settings.LLM_BASE_URL:
        normalized_url = settings.LLM_BASE_URL.rstrip("/")
        if not normalized_url.endswith("/v1"):
            normalized_url += "/v1"
        base_url = normalized_url

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=base_url,
        temperature=0.1,
    )

    try:
        prompt = THINK_PROMPT.format(
            goal=goal,
            available_tools=tools_str,
            thought_history=thought_str,
            accumulated_context=context_str,
            user_message=user_message,
        )
        response = await llm.ainvoke(prompt)
        parsed = _parse_response(response.content)

        new_step = ThoughtStep(
            step_number=state.get("current_step", 0) + 1,
            thought=parsed["thought"],
            action=parsed["action"],
            action_input=parsed["action_input"],
            is_final=parsed["action"] == "FINAL_ANSWER",
        )
        thought_history.append(new_step.to_dict())

        streaming_events.append(StreamingEvent(
            event="thought_complete",
            data={"step": new_step.step_number, "action": new_step.action},
            timestamp=datetime.now().isoformat(),
        ).model_dump())

        # 도구 선택 이벤트 (FINAL_ANSWER가 아닌 경우)
        if new_step.action != "FINAL_ANSWER":
            tool_info = tool_descriptions.get(new_step.action, {})
            streaming_events.append(StreamingEvent(
                event="tool_selected",
                data={
                    "step": new_step.step_number,
                    "tool": new_step.action,
                    "reason": new_step.thought[:200] if new_step.thought else "",
                    "category": tool_info.get("category", "unknown"),
                    "description": tool_info.get("description", ""),
                    "input_preview": _get_input_preview(new_step.action_input),
                    "status": "pending",
                },
                timestamp=datetime.now().isoformat(),
            ).model_dump())

        logger.info(f"[think_node] Action: {parsed['action']}")

        return {
            "goal": goal,
            "thought_history": thought_history,
            "current_step": state.get("current_step", 0) + 1,
            "available_tools": available_tools,
            "total_llm_calls": state.get("total_llm_calls", 0) + 1,
            "streaming_events": streaming_events,
        }

    except Exception as e:
        logger.error(f"[think_node] Error: {e}")
        error_step = ThoughtStep(
            step_number=state.get("current_step", 0) + 1,
            thought=f"에러: {str(e)}",
            action="FINAL_ANSWER",
            action_input="분석 중 오류가 발생했습니다.",
            is_final=True,
        )
        thought_history.append(error_step.to_dict())
        return {
            "thought_history": thought_history,
            "thinking_complete": True,
            "completion_reason": "error",
            "streaming_events": streaming_events,
        }


def think_node_sync(state: FullMasterAgentState) -> Dict[str, Any]:
    """동기 버전 Think Node"""
    import asyncio
    return asyncio.run(think_node(state))


# =============================================================================
# Helper Functions
# =============================================================================

def _format_history(history: list) -> str:
    """사고 이력 포맷팅"""
    if not history:
        return "(없음)"
    lines = []
    for step_dict in history:
        step = ThoughtStep.from_dict(step_dict)
        lines.append(f"Step {step.step_number}: {step.thought[:100]}")
        if step.action:
            lines.append(f"  → {step.action}")
        if step.observation:
            lines.append(f"  → 관찰: {step.observation[:100]}")
    return "\n".join(lines)


def _format_tools(tools: list) -> str:
    """도구 목록 포맷팅 (레거시 호환용)"""
    registry = get_tool_registry()
    lines = []
    for name in tools:
        tool = registry.get_tool(name)
        desc = tool.description if tool else "(설명 없음)"
        lines.append(f"- {name}: {desc}")
    lines.append("- FINAL_ANSWER: 최종 답변 제시")
    return "\n".join(lines)


def _format_tools_with_details(tools: list, tool_details: dict) -> str:
    """
    도구 목록 포맷팅 (Phase 6-2: 상세 정보 포함)

    카테고리별로 그룹화하고, 예상 토큰 정보를 포함합니다.
    LLM이 더 효율적으로 도구를 선택할 수 있도록 합니다.

    Args:
        tools: 도구 이름 목록
        tool_details: 도구 상세 정보 딕셔너리

    Returns:
        포맷팅된 도구 목록 문자열
    """
    if not tools:
        return "- FINAL_ANSWER: 최종 답변 제시"

    # 카테고리별 그룹화
    categorized = {}
    for name in tools:
        details = tool_details.get(name, {})
        category = details.get("category", "utility")
        if category not in categorized:
            categorized[category] = []
        categorized[category].append((name, details))

    # 카테고리 한글 매핑
    category_labels = {
        "search": "🔍 검색 도구",
        "analysis": "📊 분석 도구",
        "document": "📄 문서 처리",
        "external": "🌐 외부 API",
        "utility": "🔧 유틸리티",
    }

    lines = []
    for category, tools_in_cat in categorized.items():
        label = category_labels.get(category, category)
        lines.append(f"\n{label}:")
        for name, details in tools_in_cat:
            desc = details.get("description", "(설명 없음)")
            tokens = details.get("estimated_tokens", 0)
            requires_context = details.get("requires_context", False)

            # 도구 정보 포맷
            tool_line = f"  - {name}: {desc}"
            meta = []
            if tokens > 0:
                meta.append(f"~{tokens}토큰")
            if requires_context:
                meta.append("컨텍스트필요")
            if meta:
                tool_line += f" ({', '.join(meta)})"

            lines.append(tool_line)

    lines.append("\n📝 기타:")
    lines.append("  - FINAL_ANSWER: 최종 답변 제시 (충분한 정보 수집 후)")

    return "\n".join(lines)


def _get_input_preview(action_input: Any, max_length: int = 100) -> str:
    """도구 입력값 미리보기 생성"""
    if action_input is None:
        return ""
    if isinstance(action_input, str):
        return action_input[:max_length] + ("..." if len(action_input) > max_length else "")
    if isinstance(action_input, dict):
        # 주요 필드만 추출
        preview_keys = ["query", "user_message", "keyword", "search_query"]
        for key in preview_keys:
            if key in action_input:
                val = str(action_input[key])
                return val[:max_length] + ("..." if len(val) > max_length else "")
        # 없으면 첫 번째 값
        if action_input:
            first_val = str(list(action_input.values())[0])
            return first_val[:max_length] + ("..." if len(first_val) > max_length else "")
    return str(action_input)[:max_length]


def _parse_response(content: str) -> Dict[str, Any]:
    """LLM 응답 파싱"""
    try:
        # JSON 블록 추출
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()

        parsed = json.loads(json_str)
        return {
            "thought": parsed.get("thought", ""),
            "action": parsed.get("action", "FINAL_ANSWER"),
            "action_input": parsed.get("action_input", ""),
        }
    except json.JSONDecodeError:
        # 파싱 실패시 전체 내용을 최종 답변으로
        return {
            "thought": content[:500],
            "action": "FINAL_ANSWER",
            "action_input": content,
        }
