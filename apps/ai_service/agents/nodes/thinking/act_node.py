"""
Act Node - 선택된 도구/워크플로우 실행

Phase 6-1: Thinking Agent - ReAct 패턴의 Act 단계

역할:
- Think 노드에서 결정한 도구 실행
- 워크플로우 실행
- 실행 결과를 observation으로 기록
"""

from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import logging

from apps.ai_service.agents.states.master_agent_state import (
    FullMasterAgentState,
    ThoughtStep,
    StreamingEvent,
)
from apps.ai_service.agents.tools.registry import get_tool_registry

logger = logging.getLogger(__name__)


# =============================================================================
# 상수
# =============================================================================

ACTION_TIMEOUT = 30  # 도구 실행 타임아웃 (초)


# =============================================================================
# Act Node
# =============================================================================

async def act_node(state: FullMasterAgentState) -> Dict[str, Any]:
    """
    실행 노드 - 도구/워크플로우 실행

    Args:
        state: FullMasterAgentState

    Returns:
        업데이트된 상태 필드 (observation 포함)
    """
    thought_history = list(state.get("thought_history", []))
    streaming_events = list(state.get("streaming_events", []))

    if not thought_history:
        logger.warning("[act_node] No thought history")
        return {}

    # 마지막 사고 단계 가져오기
    last_step = ThoughtStep.from_dict(thought_history[-1])
    action = last_step.action
    action_input = last_step.action_input

    logger.info(f"[act_node] Executing: {action}")

    # FINAL_ANSWER는 실행하지 않음
    if action == "FINAL_ANSWER":
        logger.info("[act_node] FINAL_ANSWER - skipping execution")
        return {}

    # 도구 정보 가져오기
    registry = get_tool_registry()
    tool_def = registry.get_tool(action)
    tool_category = tool_def.category.value if tool_def else "unknown"
    tool_description = tool_def.description if tool_def else ""

    # 실행 시작 이벤트 (상세 정보 포함)
    start_time = datetime.now()
    streaming_events.append(StreamingEvent(
        event="tool_execution_start",
        data={
            "step": last_step.step_number,
            "tool": action,
            "category": tool_category,
            "description": tool_description,
            "input_preview": _get_input_preview(action_input),
            "status": "running",
        },
        timestamp=start_time.isoformat(),
    ).model_dump())

    try:
        # 입력 정규화
        inputs = _normalize_inputs(action_input, state)

        # 도구 실행
        result = await asyncio.wait_for(
            registry.execute_tool(action, inputs),
            timeout=ACTION_TIMEOUT,
        )

        if result.success:
            observation = _format_result(result.data)
        else:
            observation = f"실패: {result.error}"

    except asyncio.TimeoutError:
        observation = f"시간 초과 ({ACTION_TIMEOUT}초)"
        logger.warning(f"[act_node] Timeout for action: {action}")
    except Exception as e:
        observation = f"오류: {str(e)}"
        logger.error(f"[act_node] Error executing {action}: {e}")

    # 관찰 결과 업데이트
    last_step.observation = observation
    thought_history[-1] = last_step.to_dict()

    # 누적 컨텍스트 업데이트
    accumulated_context = list(state.get("accumulated_context", []))
    accumulated_context.append(f"[{action}] {observation[:500]}")

    # 실행 시간 계산
    end_time = datetime.now()
    execution_time = (end_time - start_time).total_seconds()
    is_success = not observation.startswith("실패") and not observation.startswith("오류") and not observation.startswith("시간 초과")

    # 실행 완료 이벤트 (상세 정보 포함)
    streaming_events.append(StreamingEvent(
        event="tool_execution_complete",
        data={
            "step": last_step.step_number,
            "tool": action,
            "category": tool_category,
            "status": "completed" if is_success else "failed",
            "success": is_success,
            "execution_time": round(execution_time, 2),
            "result_preview": _get_result_preview(observation),
        },
        timestamp=end_time.isoformat(),
    ).model_dump())

    logger.info(f"[act_node] Observation: {observation[:100]}...")

    return {
        "thought_history": thought_history,
        "accumulated_context": accumulated_context,
        "total_tool_calls": state.get("total_tool_calls", 0) + 1,
        "streaming_events": streaming_events,
    }


def act_node_sync(state: FullMasterAgentState) -> Dict[str, Any]:
    """동기 버전 Act Node"""
    import asyncio
    return asyncio.run(act_node(state))


# =============================================================================
# Helper Functions
# =============================================================================

def _get_input_preview(action_input: Any, max_length: int = 80) -> str:
    """도구 입력값 미리보기 생성"""
    if action_input is None:
        return ""
    if isinstance(action_input, str):
        return action_input[:max_length] + ("..." if len(action_input) > max_length else "")
    if isinstance(action_input, dict):
        preview_keys = ["query", "user_message", "keyword", "search_query"]
        for key in preview_keys:
            if key in action_input:
                val = str(action_input[key])
                return val[:max_length] + ("..." if len(val) > max_length else "")
        if action_input:
            first_val = str(list(action_input.values())[0])
            return first_val[:max_length] + ("..." if len(first_val) > max_length else "")
    return str(action_input)[:max_length]


def _get_result_preview(observation: str, max_length: int = 150) -> str:
    """도구 실행 결과 미리보기 생성"""
    if not observation:
        return "(결과 없음)"
    # 에러/실패 메시지는 전체 표시
    if observation.startswith(("실패:", "오류:", "시간 초과")):
        return observation[:max_length]
    # 성공 결과는 미리보기
    preview = observation[:max_length]
    if len(observation) > max_length:
        preview += "..."
    return preview


def _normalize_inputs(
    action_input: Any,
    state: FullMasterAgentState,
) -> Dict[str, Any]:
    """
    도구 입력 정규화

    다양한 형태의 action_input을 표준 딕셔너리로 변환
    """
    # 문자열인 경우
    if isinstance(action_input, str):
        inputs = {
            "query": action_input,
            "user_message": action_input,
        }
    # 딕셔너리인 경우
    elif isinstance(action_input, dict):
        inputs = action_input.copy()
        if "query" not in inputs:
            inputs["query"] = state.get("user_message", "")
    # 그 외
    else:
        inputs = {"query": state.get("user_message", "")}

    # 첨부 파일 추가
    attachments = state.get("attachments", [])
    if attachments:
        inputs["attachments"] = attachments
        # 첫 번째 첨부 파일의 내용이 있으면 추가
        if attachments[0].get("content"):
            inputs["document_content"] = attachments[0]["content"]

    # 세션 정보 추가
    inputs["session_id"] = state.get("session_id", "")

    # 사용자 ID 추가 (사용자 문서/사건 조회 도구용)
    user_context = state.get("user_context", {})
    if user_context:
        user_id = user_context.get("user_id")
        if user_id:
            inputs["user_id"] = user_id

    return inputs


def _format_result(data: Dict[str, Any]) -> str:
    """
    도구 실행 결과 포맷팅

    결과를 읽기 쉬운 문자열로 변환
    """
    if not data:
        return "(결과 없음)"

    # 주요 필드 우선 추출
    priority_keys = ["answer", "response", "result", "analysis", "summary"]
    for key in priority_keys:
        if key in data:
            value = data[key]
            if isinstance(value, str):
                return value[:2000]
            elif isinstance(value, dict):
                import json
                return json.dumps(value, ensure_ascii=False, indent=2)[:2000]

    # 전체 데이터 JSON 변환
    try:
        import json
        return json.dumps(data, ensure_ascii=False, indent=2)[:2000]
    except (TypeError, ValueError):
        return str(data)[:2000]
