"""
Thinking Path Node - ReAct 루프 실행

Phase 6-2: Thinking Agent - 진입점 노드

역할:
- Thinking Path의 메인 진입점
- ReAct 루프 (Think → Act → Observe → Reflect) 실행
- 최대 반복 횟수 내에서 목표 달성까지 반복

워크플로우:
    ┌─────────────────────────────────────────┐
    │            thinking_path_node           │
    │                    ↓                    │
    │  ┌──────────────────────────────────┐   │
    │  │          ReAct Loop              │   │
    │  │  Think → Act → Observe → Reflect │   │
    │  │      ↑______________________|    │   │
    │  └──────────────────────────────────┘   │
    │                    ↓                    │
    │           (goal_achieved)               │
    └─────────────────────────────────────────┘
"""

from datetime import datetime
from typing import Dict, Any
import logging

from apps.ai_service.agents.states.master_agent_state import (
    ThoughtStep,
    StreamingEvent,
    ProgressStep,
    create_progress_event,
)
from apps.ai_service.agents.nodes.thinking import (
    think_node,
    act_node,
    observe_node,
    reflect_node,
)
from apps.ai_service.agents.tools.registry import get_tool_registry
from apps.ai_service.agents.cost_estimator import get_cost_estimator

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_MAX_STEPS = 10
MAX_LOOP_ITERATIONS = 15  # Safety limit

# Phase 7: 비용 임계값 (USD) - 실행 중 체크용
# 10단계 예상 비용: ~$0.027 (gpt-4o-mini 기준)
# 도구가 많은 토큰을 소비할 경우를 대비해 약간의 여유만 둠
RUNTIME_COST_SOFT_LIMIT = 0.025  # $0.025 - 경고 (계속 진행)
RUNTIME_COST_HARD_LIMIT = 0.04   # $0.04 - Graceful exit (부분 응답 생성)


# =============================================================================
# Thinking Path Node
# =============================================================================

async def thinking_path_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Thinking Path - ReAct 루프 실행

    복잡한 질문에 대해 단계별 사고와 도구 실행을 반복하여
    목표를 달성합니다.

    ReAct 루프:
        1. Think: 상황 분석 및 다음 행동 결정
        2. Act: 선택된 도구 실행
        3. Observe: 실행 결과 관찰 및 컨텍스트 축적
        4. Reflect: 목표 달성 여부 판단
        → 목표 달성 또는 최대 단계 도달까지 반복

    Args:
        state: Dict[str, Any] - ExtendedMasterAgentState 필드들을 포함하는 딕셔너리
            주요 필드:
            - user_message: str - 사용자 질문
            - attachments: List[Dict] - 첨부 파일
            - session_id: str - 세션 ID
            - streaming_events: List[Dict] - 스트리밍 이벤트

    Returns:
        업데이트할 필드 딕셔너리:
        - workflow_results: 사고 결과
        - thought_history: 사고 이력
        - accumulated_context: 누적 컨텍스트
        - thinking_complete: 완료 여부
        - total_llm_calls: LLM 호출 횟수
        - total_tool_calls: 도구 호출 횟수
        - response_metadata: 응답 메타데이터
        - streaming_events: 스트리밍 이벤트
        - final_response: 최종 응답 (있는 경우)

    Note:
        state는 Dict[str, Any]로 받습니다.
        ExtendedMasterAgentState 필드들이 포함되어 있으며,
        이 함수에서 Thinking 전용 필드들을 추가합니다.
    """
    logger.info("[thinking_path_node] Starting ReAct loop")

    user_message = state.get("user_message", "")
    streaming_events = list(state.get("streaming_events", []))

    # Phase 7: 질문에 관련된 도구만 필터링
    total_tools = 0
    try:
        registry = get_tool_registry()
        total_tools = len(registry.list_tools())

        # 컨텍스트 기반 도구 필터링
        filtered_tool_defs = registry.get_tools_for_context(
            query=user_message,
            max_tools=8,  # THINKING 경로는 최대 8개 도구
        )

        # 도구 이름 목록
        available_tools = [tool.name for tool in filtered_tool_defs]

        # 도구별 설명 포함 (LLM에게 제공)
        tool_descriptions = {
            tool.name: {
                "description": tool.description,
                "category": tool.category.value,
                "estimated_tokens": tool.estimated_tokens,
            }
            for tool in filtered_tool_defs
        }

        # 필터링된 카테고리 수집
        filtered_categories = list(set(
            tool.category.value for tool in filtered_tool_defs
        ))

        logger.info(
            f"[thinking_path_node] Filtered tools: {len(available_tools)} "
            f"from {total_tools} total"
        )

    except Exception as e:
        logger.warning(f"[thinking_path_node] Tool filtering failed: {e}")
        available_tools = []
        tool_descriptions = {}
        filtered_categories = []

    # 도구 필터링 이벤트 (Phase 7)
    streaming_events.append(StreamingEvent(
        event="tools_filtered",
        data={
            "available_tools": available_tools,
            "tool_count": len(available_tools),
            "total_tools": total_tools,
            "categories": filtered_categories,
        },
        timestamp=datetime.now().isoformat(),
    ).model_dump())

    # 진행 상황 이벤트: Thinking Path 시작 (15%)
    progress_start = create_progress_event(
        step=ProgressStep.THINKING,
        percentage=15,
        message="단계별 분석을 시작합니다...",
        execution_path="thinking",
        step_details={"max_steps": state.get("max_steps", DEFAULT_MAX_STEPS)},
    )
    streaming_events.append(progress_start.model_dump())

    # Thinking Path 시작 이벤트 (기존 호환성 유지)
    streaming_events.append(StreamingEvent(
        event="thinking_path_start",
        data={
            "message": "단계별 분석을 시작합니다...",
            "max_steps": state.get("max_steps", DEFAULT_MAX_STEPS),
        },
        timestamp=datetime.now().isoformat(),
    ).model_dump())

    # 초기 상태 설정 - 기존 state에 Thinking 전용 필드 추가
    current_state: Dict[str, Any] = {
        **state,
        "goal": user_message,
        "available_tools": available_tools,
        "tool_descriptions": tool_descriptions,  # Phase 7: 도구 설명 추가
        "thought_history": [],
        "accumulated_context": [],
        "current_step": 0,
        "max_steps": state.get("max_steps", DEFAULT_MAX_STEPS),
        "thinking_complete": False,
        "completion_reason": None,
        "total_llm_calls": state.get("total_llm_calls", 0),
        "total_tool_calls": state.get("total_tool_calls", 0),
        "streaming_events": streaming_events,
        # Phase 7: 비용 추적
        "accumulated_cost_usd": 0.0,
        "cost_warning_sent": False,
    }

    max_iterations = min(
        current_state.get("max_steps", DEFAULT_MAX_STEPS),
        MAX_LOOP_ITERATIONS
    )

    # =================================================================
    # ReAct 루프
    # =================================================================
    for iteration in range(max_iterations):
        logger.info(f"[thinking_path_node] Iteration {iteration + 1}/{max_iterations}")

        # 진행 상황 이벤트: ReAct 반복 (20% ~ 65% 범위)
        # 반복 횟수에 따라 진행률 계산: 20 + (iteration / max_iterations) * 45
        iteration_progress = 20 + int((iteration / max(max_iterations, 1)) * 45)
        progress_iteration = create_progress_event(
            step=ProgressStep.THINKING,
            percentage=iteration_progress,
            message=f"분석 단계 {iteration + 1}/{max_iterations} 진행 중...",
            execution_path="thinking",
            step_details={
                "iteration": iteration + 1,
                "max_iterations": max_iterations,
            },
        )
        current_state["streaming_events"] = list(current_state.get("streaming_events", [])) + [progress_iteration.model_dump()]

        # 1. Think - 상황 분석 및 다음 행동 결정
        try:
            think_result = await think_node(current_state)
            current_state = {**current_state, **think_result}
        except Exception as e:
            logger.error(f"[thinking_path_node] Think node error: {e}")
            break

        # FINAL_ANSWER 체크 - Think에서 최종 답변을 결정한 경우
        thought_history = current_state.get("thought_history", [])
        if thought_history:
            last_step = ThoughtStep.from_dict(thought_history[-1])
            if last_step.is_final:
                logger.info("[thinking_path_node] FINAL_ANSWER in think, completing")
                break

        # 2. Act - 도구 실행
        try:
            act_result = await act_node(current_state)
            current_state = {**current_state, **act_result}
        except Exception as e:
            logger.error(f"[thinking_path_node] Act node error: {e}")
            # 에러 발생해도 다음 iteration에서 LLM이 판단하도록 계속

        # 3. Observe - 결과 관찰 및 컨텍스트 축적
        try:
            observe_result = await observe_node(current_state)
            current_state = {**current_state, **observe_result}
        except Exception as e:
            logger.error(f"[thinking_path_node] Observe node error: {e}")

        # 4. Reflect - 목표 달성 여부 판단
        try:
            reflect_result = await reflect_node(current_state)
            current_state = {**current_state, **reflect_result}
        except Exception as e:
            logger.error(f"[thinking_path_node] Reflect node error: {e}")

        # 목표 달성 체크
        if current_state.get("thinking_complete", False):
            logger.info(
                f"[thinking_path_node] Completed: "
                f"reason={current_state.get('completion_reason')}"
            )
            break

        # =============================================================
        # Phase 7: 비용 체크 - 각 iteration 후
        # =============================================================
        cost_check_result = _check_runtime_cost(
            current_state, iteration + 1, max_iterations
        )
        current_state = {**current_state, **cost_check_result}
        streaming_events = current_state.get("streaming_events", [])

        # Hard limit 도달 시 Graceful exit
        if cost_check_result.get("cost_limit_reached", False):
            logger.warning(
                f"[thinking_path_node] Cost hard limit reached: "
                f"${current_state.get('accumulated_cost_usd', 0):.4f}"
            )
            current_state["thinking_complete"] = True
            current_state["completion_reason"] = "cost_limit_reached"
            break

    # =================================================================
    # 결과 정리
    # =================================================================
    thought_history = current_state.get("thought_history", [])
    streaming_events = current_state.get("streaming_events", [])
    completion_reason = current_state.get("completion_reason", "max_iterations")

    # 진행 상황 이벤트: 분석 완료 (70%)
    progress_completing = create_progress_event(
        step=ProgressStep.THINKING,
        percentage=70,
        message="분석 결과를 정리하고 있습니다...",
        execution_path="thinking",
        step_details={
            "total_steps": len(thought_history),
            "completion_reason": completion_reason,
        },
    )
    streaming_events.append(progress_completing.model_dump())

    # Phase 7: 비용 한도 도달 시 부분 응답 생성
    if completion_reason == "cost_limit_reached":
        final_answer = _generate_partial_response(
            accumulated_context=current_state.get("accumulated_context", []),
            thought_history=thought_history,
            user_message=user_message,
        )
        logger.info("[thinking_path_node] Generated partial response due to cost limit")
    else:
        # 최종 응답 추출
        final_answer = _extract_final_answer(thought_history)

    # 완료 이벤트
    streaming_events.append(StreamingEvent(
        event="thinking_path_complete",
        data={
            "total_steps": len(thought_history),
            "total_llm_calls": current_state.get("total_llm_calls", 0),
            "total_tool_calls": current_state.get("total_tool_calls", 0),
            "completion_reason": completion_reason,
            # Phase 7: 비용 정보 추가
            "accumulated_cost_usd": current_state.get("accumulated_cost_usd", 0.0),
            "is_partial_response": completion_reason == "cost_limit_reached",
        },
        timestamp=datetime.now().isoformat(),
    ).model_dump())

    logger.info(
        f"[thinking_path_node] Completed with {len(thought_history)} steps, "
        f"LLM calls: {current_state.get('total_llm_calls', 0)}, "
        f"Tool calls: {current_state.get('total_tool_calls', 0)}"
    )

    is_partial = completion_reason == "cost_limit_reached"

    return {
        # 워크플로우 결과 형식
        "workflow_results": {
            "thinking_results": {
                "thought_history": thought_history,
                "final_answer": final_answer,
                "accumulated_context": current_state.get("accumulated_context", []),
                "total_steps": len(thought_history),
                "is_partial": is_partial,  # Phase 7
            },
        },
        # Thinking 상태 필드
        "thought_history": thought_history,
        "accumulated_context": current_state.get("accumulated_context", []),
        "thinking_complete": True,
        "completion_reason": completion_reason,
        "total_llm_calls": current_state.get("total_llm_calls", 0),
        "total_tool_calls": current_state.get("total_tool_calls", 0),
        # 응답 메타데이터
        "response_metadata": {
            "path": "thinking",
            "total_steps": len(thought_history),
            "completion_reason": completion_reason,
            "is_partial_response": is_partial,  # Phase 7
            "accumulated_cost_usd": current_state.get("accumulated_cost_usd", 0.0),
        },
        "streaming_events": streaming_events,
        # 최종 응답 (generate_response_node에서 사용)
        "final_response": final_answer,
        # Phase 7: 부분 응답 플래그
        "is_partial_response": is_partial,
    }


def thinking_path_node_sync(state: Dict[str, Any]) -> Dict[str, Any]:
    """동기 버전 Thinking Path Node"""
    import asyncio
    return asyncio.run(thinking_path_node(state))


# =============================================================================
# Helper Functions
# =============================================================================

def _extract_final_answer(thought_history: list) -> str:
    """
    사고 이력에서 최종 답변 추출

    Args:
        thought_history: 사고 이력 목록

    Returns:
        최종 답변 문자열 (없으면 빈 문자열)
    """
    if not thought_history:
        return ""

    # 마지막 단계에서 FINAL_ANSWER 찾기
    for step_dict in reversed(thought_history):
        step = ThoughtStep.from_dict(step_dict)
        if step.is_final and step.action_input:
            # action_input이 문자열이면 그대로 반환
            if isinstance(step.action_input, str):
                return step.action_input
            # 딕셔너리이면 answer 키 우선
            elif isinstance(step.action_input, dict):
                return step.action_input.get("answer", str(step.action_input))
            else:
                return str(step.action_input)

    # FINAL_ANSWER가 없으면 마지막 observation 또는 thought 반환
    if thought_history:
        last_step = ThoughtStep.from_dict(thought_history[-1])
        if last_step.observation:
            return last_step.observation
        elif last_step.thought:
            return last_step.thought

    return ""


# =============================================================================
# Phase 7: 비용 체크 헬퍼 함수
# =============================================================================

def _check_runtime_cost(
    state: Dict[str, Any],
    current_iteration: int,
    max_iterations: int,
) -> Dict[str, Any]:
    """
    Phase 7: 실행 중 비용 체크

    각 ReAct iteration 후 누적 비용을 계산하고
    임계값 초과 여부를 확인합니다.

    Args:
        state: 현재 상태
        current_iteration: 현재 반복 횟수
        max_iterations: 최대 반복 횟수

    Returns:
        업데이트할 필드:
        - accumulated_cost_usd: 누적 비용
        - cost_warning_sent: 경고 전송 여부
        - cost_limit_reached: Hard limit 도달 여부
        - streaming_events: 업데이트된 이벤트 목록
    """
    streaming_events = list(state.get("streaming_events", []))

    try:
        estimator = get_cost_estimator()

        # 현재까지 사용된 토큰 추정
        # LLM 호출 횟수 * 평균 토큰 + 도구 호출 횟수 * 평균 토큰
        total_llm_calls = state.get("total_llm_calls", 0)
        total_tool_calls = state.get("total_tool_calls", 0)

        # 간단한 토큰 추정 (실제로는 더 정교해야 함)
        avg_tokens_per_llm_call = 2000  # 평균 LLM 호출당 토큰
        avg_tokens_per_tool_call = 500   # 평균 도구 호출당 토큰

        estimated_input_tokens = (
            total_llm_calls * avg_tokens_per_llm_call +
            total_tool_calls * avg_tokens_per_tool_call
        )
        estimated_output_tokens = total_llm_calls * 500  # 평균 출력 토큰

        # 실제 비용 계산
        actual_cost = estimator.calculate_actual_cost(
            input_tokens=estimated_input_tokens,
            output_tokens=estimated_output_tokens,
        )

        accumulated_cost = actual_cost.actual_cost_usd
        cost_warning_sent = state.get("cost_warning_sent", False)
        cost_limit_reached = False

        # Hard limit 체크 ($0.08)
        if accumulated_cost >= RUNTIME_COST_HARD_LIMIT:
            cost_limit_reached = True

            # Hard limit 이벤트
            streaming_events.append(StreamingEvent(
                event="cost_limit_reached",
                data={
                    "message": "분석 비용 한도에 도달하여 현재까지 수집한 정보로 답변을 생성합니다.",
                    "accumulated_cost_usd": accumulated_cost,
                    "limit_usd": RUNTIME_COST_HARD_LIMIT,
                    "iteration": current_iteration,
                },
                timestamp=datetime.now().isoformat(),
            ).model_dump())

            logger.warning(
                f"[_check_runtime_cost] Hard limit reached: "
                f"${accumulated_cost:.4f} >= ${RUNTIME_COST_HARD_LIMIT}"
            )

        # Soft limit 체크 ($0.03) - 경고만
        elif accumulated_cost >= RUNTIME_COST_SOFT_LIMIT and not cost_warning_sent:
            cost_warning_sent = True

            # 경고 이벤트
            streaming_events.append(StreamingEvent(
                event="cost_warning",
                data={
                    "type": "runtime_warning",
                    "message": f"분석 비용이 증가하고 있습니다 (${accumulated_cost:.4f})",
                    "accumulated_cost_usd": accumulated_cost,
                    "soft_limit_usd": RUNTIME_COST_SOFT_LIMIT,
                    "hard_limit_usd": RUNTIME_COST_HARD_LIMIT,
                    "iteration": current_iteration,
                    "remaining_iterations": max_iterations - current_iteration,
                },
                timestamp=datetime.now().isoformat(),
            ).model_dump())

            logger.info(
                f"[_check_runtime_cost] Soft limit warning: "
                f"${accumulated_cost:.4f} >= ${RUNTIME_COST_SOFT_LIMIT}"
            )

        return {
            "accumulated_cost_usd": accumulated_cost,
            "cost_warning_sent": cost_warning_sent,
            "cost_limit_reached": cost_limit_reached,
            "streaming_events": streaming_events,
        }

    except Exception as e:
        logger.warning(f"[_check_runtime_cost] Error: {e}")
        return {
            "accumulated_cost_usd": state.get("accumulated_cost_usd", 0.0),
            "cost_warning_sent": state.get("cost_warning_sent", False),
            "cost_limit_reached": False,
            "streaming_events": streaming_events,
        }


def _generate_partial_response(
    accumulated_context: list,
    thought_history: list,
    user_message: str,
) -> str:
    """
    Phase 7: 비용 한도 도달 시 부분 응답 생성

    지금까지 수집한 정보를 기반으로 최선의 답변을 생성합니다.

    Args:
        accumulated_context: 누적된 컨텍스트 (도구 실행 결과 등)
        thought_history: 사고 이력
        user_message: 원래 사용자 질문

    Returns:
        부분 응답 문자열
    """
    # 수집된 정보 요약
    collected_info = []

    # 1. accumulated_context에서 정보 추출
    if accumulated_context:
        for ctx in accumulated_context:
            if isinstance(ctx, dict):
                # 도구 실행 결과
                tool_name = ctx.get("tool", ctx.get("action", "정보"))
                result = ctx.get("result", ctx.get("observation", ""))
                if result and len(str(result)) > 50:
                    collected_info.append(f"- {tool_name}: {str(result)[:500]}...")
                elif result:
                    collected_info.append(f"- {tool_name}: {result}")
            elif isinstance(ctx, str) and ctx.strip():
                collected_info.append(f"- {ctx[:300]}")

    # 2. thought_history에서 observation 추출
    if thought_history:
        for step_dict in thought_history:
            step = ThoughtStep.from_dict(step_dict)
            if step.observation and step.observation not in str(collected_info):
                # 이미 포함되지 않은 observation만 추가
                obs_preview = step.observation[:300] if len(step.observation) > 300 else step.observation
                if obs_preview not in str(collected_info):
                    collected_info.append(f"- {obs_preview}")

    # 3. 부분 응답 구성
    if collected_info:
        info_text = "\n".join(collected_info[:5])  # 최대 5개 항목
        partial_response = f"""질문에 대해 현재까지 파악한 내용을 안내해 드립니다.

**수집된 정보:**
{info_text}

---
💡 **안내**: 더 자세한 분석이 필요하시면 질문을 구체적으로 나누어 주세요.
예: "{user_message[:30]}..." → 개별 주제별로 질문"""
    else:
        # 수집된 정보가 없는 경우
        partial_response = f"""죄송합니다. 질문을 분석하는 중 복잡도가 높아 완전한 답변을 드리기 어렵습니다.

💡 **권장 사항**: 질문을 더 구체적으로 나누어 주시면 정확한 답변을 드릴 수 있습니다.

원래 질문: "{user_message[:50]}..."

예시:
1. 특정 법령이나 조항에 대해 질문
2. 특정 상황에 대한 해석을 질문
3. 절차나 요건에 대해 개별적으로 질문"""

    return partial_response
