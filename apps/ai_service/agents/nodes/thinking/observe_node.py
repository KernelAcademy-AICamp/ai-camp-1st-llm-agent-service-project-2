"""
Observe Node - 실행 결과를 누적 컨텍스트에 추가

Phase 6-2: Thinking Agent - ReAct 패턴의 Observe 단계

역할:
- Act 노드의 실행 결과를 관찰
- 누적 컨텍스트에 관찰 결과 추가
- 다음 Think 단계를 위한 정보 축적
"""

from datetime import datetime
from typing import Dict, Any
import logging

from apps.ai_service.agents.states.master_agent_state import (
    ThoughtStep,
    StreamingEvent,
)

logger = logging.getLogger(__name__)


async def observe_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    관찰 노드 - 실행 결과를 컨텍스트에 추가

    Act 노드에서 실행된 도구의 결과(observation)를
    누적 컨텍스트에 추가합니다.

    Args:
        state: Dict[str, Any] - 현재 상태
            주요 필드:
            - thought_history: List[Dict] - 사고 이력
            - accumulated_context: List[str] - 누적 컨텍스트
            - streaming_events: List[Dict] - 스트리밍 이벤트

    Returns:
        업데이트할 필드 딕셔너리:
        - accumulated_context: 업데이트된 컨텍스트
        - streaming_events: 새 이벤트 추가

    Note:
        state는 Dict[str, Any]로 받습니다.
        FullMasterAgentState TypedDict는 타입 힌트용이며,
        실제 런타임에서는 일반 dict로 전달됩니다.
    """
    thought_history = state.get("thought_history", [])
    accumulated_context = list(state.get("accumulated_context", []))
    streaming_events = list(state.get("streaming_events", []))

    if not thought_history:
        logger.debug("[observe_node] No thought history, skipping")
        return {}

    # 마지막 사고 단계 가져오기
    last_step = ThoughtStep.from_dict(thought_history[-1])

    # observation이 있으면 컨텍스트에 추가
    if last_step.observation:
        context_entry = f"## Step {last_step.step_number}: {last_step.action}\n{last_step.observation}"
        accumulated_context.append(context_entry)

        logger.info(
            f"[observe_node] Added to context (step {last_step.step_number}), "
            f"context size: {len(accumulated_context)}"
        )

        # 스트리밍 이벤트
        streaming_events.append(StreamingEvent(
            event="observation_added",
            data={
                "step": last_step.step_number,
                "action": last_step.action,
                "context_size": len(accumulated_context),
            },
            timestamp=datetime.now().isoformat(),
        ).model_dump())
    else:
        logger.debug(f"[observe_node] No observation for step {last_step.step_number}")

    return {
        "accumulated_context": accumulated_context,
        "streaming_events": streaming_events,
    }


def observe_node_sync(state: Dict[str, Any]) -> Dict[str, Any]:
    """동기 버전 Observe Node"""
    import asyncio
    return asyncio.run(observe_node(state))
