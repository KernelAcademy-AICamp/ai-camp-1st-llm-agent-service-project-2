"""
Act Node - 선택된 도구/워크플로우 실행

Phase 6-1: Thinking Agent - ReAct 패턴의 Act 단계

역할:
- Think 노드에서 결정한 도구 실행
- 워크플로우 실행
- 실행 결과를 observation으로 기록
"""

from datetime import datetime
from typing import Dict, Any
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

    # 실행 시작 이벤트
    streaming_events.append(StreamingEvent(
        event="action_start",
        data={"step": last_step.step_number, "action": action},
        timestamp=datetime.now().isoformat(),
    ).model_dump())

    registry = get_tool_registry()

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

    # 실행 완료 이벤트
    streaming_events.append(StreamingEvent(
        event="action_complete",
        data={
            "step": last_step.step_number,
            "action": action,
            "success": not observation.startswith("실패") and not observation.startswith("오류"),
        },
        timestamp=datetime.now().isoformat(),
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
