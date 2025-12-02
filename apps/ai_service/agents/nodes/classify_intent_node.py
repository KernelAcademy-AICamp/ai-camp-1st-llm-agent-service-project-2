"""
Classify Intent Node - 의도 분류 노드

Phase 5: Agent Hub - Master Agent Graph Node

설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.3.3

역할:
- IntentClassifier를 사용하여 사용자 의도 분류
- 스트리밍 이벤트 발생 (intent_classified)
- clarification_needed 시 확인 질문 이벤트 발생
"""

from datetime import datetime
import logging
from typing import Any

from apps.ai_service.agents.states.master_agent_state import (
    MasterAgentState,
    Intent,
    StreamingEvent,
)
from apps.ai_service.agents.intent_classifier import (
    IntentClassifier,
    get_intent_classifier,
)

logger = logging.getLogger(__name__)


async def classify_intent_node(state: MasterAgentState) -> MasterAgentState:
    """
    의도 분류 노드

    사용자 메시지를 분석하여 의도를 파악합니다.

    Args:
        state: MasterAgentState (현재 상태)

    Returns:
        업데이트된 MasterAgentState

    State 업데이트:
        - intent: 분류된 Intent 객체 (dict)
        - streaming_events: intent_classified 이벤트 추가

    이벤트 발생:
        1. intent_classified: 의도 분류 완료
        2. clarification_required: 추가 정보 필요 시
    """
    logger.info(f"[classify_intent_node] Starting intent classification")
    logger.debug(f"User message: {state['user_message'][:100]}...")

    try:
        # 1. IntentClassifier 인스턴스 생성
        classifier = get_intent_classifier()

        # 2. 의도 분류 실행
        intent: Intent = classifier.classify_sync(
            user_message=state["user_message"],
            conversation_history=state.get("conversation_history"),
            attachments=state.get("attachments"),
        )

        # intent.category는 use_enum_values=True로 인해 문자열일 수 있음
        category_value = intent.category.value if hasattr(intent.category, 'value') else intent.category
        logger.info(
            f"[classify_intent_node] Intent classified: "
            f"category={category_value}, confidence={intent.confidence:.2f}"
        )

        # 3. 의도 분류 완료 이벤트
        intent_event = StreamingEvent(
            event="intent_classified",
            data={
                "category": category_value,
                "sub_category": intent.sub_category,
                "confidence": intent.confidence,
                "suggested_workflows": intent.suggested_workflows,
                "requires_attachment": intent.requires_attachment,
                "extracted_params": intent.extracted_params,
            },
            timestamp=datetime.now().isoformat(),
        )

        # 기존 이벤트 목록에 추가
        streaming_events = list(state.get("streaming_events", []))
        streaming_events.append(intent_event.model_dump())

        # 4. clarification_needed 처리
        if intent.clarification_needed:
            logger.info(
                f"[classify_intent_node] Clarification needed: "
                f"{intent.clarification_questions}"
            )

            clarification_event = StreamingEvent(
                event="clarification_required",
                data={
                    "questions": intent.clarification_questions,
                    "message": "요청을 더 잘 이해하기 위해 추가 정보가 필요합니다.",
                },
                timestamp=datetime.now().isoformat(),
            )
            streaming_events.append(clarification_event.model_dump())

        # 5. 저신뢰도 경고
        if not intent.is_high_confidence:
            logger.warning(
                f"[classify_intent_node] Low confidence intent: {intent.confidence:.2f}"
            )

            low_confidence_event = StreamingEvent(
                event="low_confidence_warning",
                data={
                    "confidence": intent.confidence,
                    "message": f"의도 분류 신뢰도가 낮습니다 ({intent.confidence:.0%}). "
                               "요청을 좀 더 구체적으로 해주시면 더 정확한 결과를 제공할 수 있습니다.",
                },
                timestamp=datetime.now().isoformat(),
            )
            streaming_events.append(low_confidence_event.model_dump())

        # 6. 상태 업데이트
        state["intent"] = intent.model_dump()
        state["streaming_events"] = streaming_events

        logger.info("[classify_intent_node] Completed successfully")

        return state

    except Exception as e:
        logger.error(f"[classify_intent_node] Error: {e}", exc_info=True)

        # 에러 발생 시 기본 의도로 설정
        from apps.ai_service.agents.states.master_agent_state import IntentCategory

        default_intent = Intent(
            category=IntentCategory.QUERY,
            confidence=0.3,
            clarification_needed=True,
            clarification_questions=["요청 내용을 조금 더 구체적으로 말씀해 주시겠어요?"],
        )

        # 에러 이벤트
        error_event = StreamingEvent(
            event="error",
            data={
                "step": "classify_intent",
                "error": str(e),
                "message": "의도 분류 중 오류가 발생했습니다. 기본 질의응답 모드로 진행합니다.",
            },
            timestamp=datetime.now().isoformat(),
        )

        streaming_events = list(state.get("streaming_events", []))
        streaming_events.append(error_event.model_dump())

        # 에러 로그 추가
        errors = list(state.get("errors", []))
        errors.append({
            "step": "classify_intent",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })

        state["intent"] = default_intent.model_dump()
        state["streaming_events"] = streaming_events
        state["errors"] = errors

        return state


def classify_intent_node_sync(state: MasterAgentState) -> MasterAgentState:
    """
    의도 분류 노드 (동기 버전)

    LangGraph가 동기 노드를 요구하는 경우 사용합니다.
    """
    import asyncio

    # 이벤트 루프가 이미 실행 중인지 확인
    try:
        loop = asyncio.get_running_loop()
        # 이미 실행 중이면 새 태스크로 실행
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                classify_intent_node(state)
            )
            return future.result()
    except RuntimeError:
        # 실행 중인 루프가 없으면 직접 실행
        return asyncio.run(classify_intent_node(state))
