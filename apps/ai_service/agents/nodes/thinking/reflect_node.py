"""
Reflect Node - 목표 달성 여부 판단

Phase 6-2: Thinking Agent - ReAct 패턴의 Reflect 단계

역할:
- 현재까지의 진행 상황 평가
- 목표 달성 여부 판단
- 추가 사고 필요 여부 결정
"""

from datetime import datetime
from typing import Dict, Any
import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from apps.ai_service.agents.states.master_agent_state import (
    ThoughtStep,
    StreamingEvent,
)
from apps.ai_service.config.settings import settings

logger = logging.getLogger(__name__)


# =============================================================================
# 반성 프롬프트
# =============================================================================

REFLECT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """진행 상황을 평가하고 목표 달성 여부를 판단하세요.

## 목표
{goal}

## 진행 상황
{thought_history}

## 수집된 정보
{accumulated_context}

## 판단 기준
- 사용자 질문에 충분히 답변할 수 있는 정보가 수집되었는가?
- 추가 도구 실행이 필요한가?
- 현재 정보로 최종 답변을 제공할 수 있는가?

## 응답 형식 (JSON)
{{
    "reflection": "현재 상황 평가 (무엇을 수집했고, 무엇이 부족한가)",
    "goal_achieved": true/false,
    "confidence": 0.0-1.0
}}"""),
    ("human", "사용자 질문: {user_message}"),
])


# =============================================================================
# Reflect Node
# =============================================================================

async def reflect_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    반성 노드 - 목표 달성 여부 판단

    현재까지의 진행 상황을 평가하고, 목표 달성 여부를 판단합니다.
    LLM을 사용하여 충분한 정보가 수집되었는지 판단합니다.

    Args:
        state: Dict[str, Any] - 현재 상태
            주요 필드:
            - goal: 달성할 목표
            - user_message: 사용자 질문
            - thought_history: List[Dict] - 사고 이력
            - accumulated_context: List[str] - 누적 컨텍스트
            - current_step: int - 현재 단계 번호
            - max_steps: int - 최대 단계 수

    Returns:
        업데이트할 필드 딕셔너리:
        - thought_history: 업데이트된 사고 이력 (reflection 추가)
        - thinking_complete: 사고 완료 여부
        - completion_reason: 완료 사유 (goal_achieved, max_steps, error)
        - total_llm_calls: LLM 호출 횟수 증가
        - streaming_events: 새 이벤트 추가

    Note:
        state는 Dict[str, Any]로 받습니다.
    """
    logger.info("[reflect_node] Evaluating progress")

    goal = state.get("goal", "")
    user_message = state.get("user_message", "")
    thought_history = list(state.get("thought_history", []))
    accumulated_context = state.get("accumulated_context", [])
    streaming_events = list(state.get("streaming_events", []))
    current_step = state.get("current_step", 0)
    max_steps = state.get("max_steps", 10)

    if not thought_history:
        logger.debug("[reflect_node] No thought history, skipping")
        return {}

    last_step = ThoughtStep.from_dict(thought_history[-1])

    # FINAL_ANSWER면 바로 완료
    if last_step.is_final:
        last_step.reflection = "최종 답변 제시 완료"
        thought_history[-1] = last_step.to_dict()

        logger.info("[reflect_node] FINAL_ANSWER detected, completing")

        return {
            "thought_history": thought_history,
            "thinking_complete": True,
            "completion_reason": "goal_achieved",
            "streaming_events": streaming_events,
        }

    # 최대 단계 도달
    if current_step >= max_steps:
        last_step.reflection = f"최대 단계({max_steps}) 도달"
        thought_history[-1] = last_step.to_dict()

        logger.warning(f"[reflect_node] Max steps ({max_steps}) reached")

        streaming_events.append(StreamingEvent(
            event="max_steps_reached",
            data={"max_steps": max_steps, "current_step": current_step},
            timestamp=datetime.now().isoformat(),
        ).model_dump())

        return {
            "thought_history": thought_history,
            "thinking_complete": True,
            "completion_reason": "max_steps",
            "streaming_events": streaming_events,
        }

    # 반성 시작 이벤트
    streaming_events.append(StreamingEvent(
        event="reflecting",
        data={"step": current_step, "context_size": len(accumulated_context)},
        timestamp=datetime.now().isoformat(),
    ).model_dump())

    # LLM으로 목표 달성 여부 판단
    try:
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            temperature=0,
        )

        # 사고 이력 포맷팅
        thought_str = "\n".join([
            f"Step {ThoughtStep.from_dict(s).step_number}: {ThoughtStep.from_dict(s).thought[:100]}"
            for s in thought_history
        ])
        context_str = "\n".join(accumulated_context) if accumulated_context else "(없음)"

        prompt = REFLECT_PROMPT.format(
            goal=goal or user_message,
            thought_history=thought_str,
            accumulated_context=context_str,
            user_message=user_message,
        )

        response = await llm.ainvoke(prompt)
        parsed = _parse_response(response.content)

        # 반성 결과 업데이트
        last_step.reflection = parsed["reflection"]
        thought_history[-1] = last_step.to_dict()

        thinking_complete = parsed["goal_achieved"]
        confidence = parsed["confidence"]

        logger.info(
            f"[reflect_node] Result: goal_achieved={thinking_complete}, "
            f"confidence={confidence:.2f}"
        )

        # 반성 완료 이벤트
        streaming_events.append(StreamingEvent(
            event="reflection_complete",
            data={
                "goal_achieved": thinking_complete,
                "confidence": confidence,
                "reflection": parsed["reflection"][:100],
            },
            timestamp=datetime.now().isoformat(),
        ).model_dump())

        return {
            "thought_history": thought_history,
            "thinking_complete": thinking_complete,
            "completion_reason": "goal_achieved" if thinking_complete else None,
            "total_llm_calls": state.get("total_llm_calls", 0) + 1,
            "streaming_events": streaming_events,
        }

    except Exception as e:
        logger.error(f"[reflect_node] Error: {e}")

        # 에러 발생 시 계속 진행 (완료하지 않음)
        streaming_events.append(StreamingEvent(
            event="reflection_error",
            data={"error": str(e)[:100]},
            timestamp=datetime.now().isoformat(),
        ).model_dump())

        return {
            "thought_history": thought_history,
            "streaming_events": streaming_events,
        }


def reflect_node_sync(state: Dict[str, Any]) -> Dict[str, Any]:
    """동기 버전 Reflect Node"""
    import asyncio
    return asyncio.run(reflect_node(state))


# =============================================================================
# Helper Functions
# =============================================================================

def _parse_response(content: str) -> Dict[str, Any]:
    """
    LLM 응답 파싱

    Args:
        content: LLM 응답 텍스트

    Returns:
        파싱된 결과 딕셔너리:
        - reflection: str
        - goal_achieved: bool
        - confidence: float
    """
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
            "reflection": parsed.get("reflection", ""),
            "goal_achieved": parsed.get("goal_achieved", False),
            "confidence": float(parsed.get("confidence", 0.5)),
        }

    except (json.JSONDecodeError, ValueError, IndexError) as e:
        logger.warning(f"[_parse_response] Parse failed: {e}")
        # 파싱 실패 시 기본값
        return {
            "reflection": content[:300] if content else "",
            "goal_achieved": False,
            "confidence": 0.5,
        }
