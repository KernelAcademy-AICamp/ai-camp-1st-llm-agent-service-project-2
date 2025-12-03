"""
Complexity Classifier Node

LangGraph 노드: 복잡도 분류 및 경로 결정

Phase 7: 단계별 비용 추정
- 실행 전 비용 예측
- 비용 초과 시 경고
- 예상 비용 메타데이터 추가
"""

from datetime import datetime
from typing import Dict, Any
import logging

from apps.ai_service.agents.states.master_agent_state import (
    ExtendedMasterAgentState,
    StreamingEvent,
    ProgressStep,
    create_progress_event,
)
from apps.ai_service.agents.complexity_classifier import (
    get_complexity_classifier,
    ComplexityResult,
)
from apps.ai_service.agents.cost_estimator import (
    get_cost_estimator,
    CostTier,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Phase 7: 비용 임계값 설정
# =============================================================================

# 경고 임계값 (USD)
COST_WARNING_THRESHOLD = 0.05  # $0.05 이상 경고

# 확인 필요 임계값 (USD)
COST_CONFIRMATION_THRESHOLD = 0.10  # $0.10 이상 확인 필요

# 차단 임계값 (USD)
COST_BLOCKING_THRESHOLD = 0.50  # $0.50 이상 차단


async def complexity_classifier_node(
    state: ExtendedMasterAgentState
) -> Dict[str, Any]:
    """
    복잡도 분류 노드

    입력:
        - user_message: 사용자 메시지
        - attachments: 첨부 파일
        - cache_hit: 캐시 히트 여부 (이전 노드에서 설정)

    출력:
        - complexity_level: "FAST" | "MEDIUM" | "DEEP"
        - complexity_confidence: 신뢰도
        - complexity_reason: 분류 이유
        - execution_path: "fast" | "medium" | "deep"
        - quick_plan: MEDIUM 경로용 빠른 계획 (선택)

    스트리밍 이벤트:
        - classification_start: 분류 시작
        - classification_complete: 분류 완료

    Args:
        state: ExtendedMasterAgentState

    Returns:
        업데이트할 필드 딕셔너리
    """
    logger.info("[complexity_classifier_node] Starting complexity classification")

    user_message = state.get("user_message", "")
    attachments = state.get("attachments", [])
    cache_hit = state.get("cache_hit", False)

    # 스트리밍 이벤트 준비
    streaming_events = list(state.get("streaming_events", []))

    # 진행 상황 이벤트: 분석 시작 (5%)
    progress_event = create_progress_event(
        step=ProgressStep.ANALYZING,
        percentage=5,
        message="질문을 분석하고 있습니다...",
        execution_path="medium",  # 아직 경로 미결정
    )
    streaming_events.append(progress_event.model_dump())

    # 분류 시작 이벤트 (기존 호환성 유지)
    start_event = StreamingEvent(
        event="classification_start",
        data={"step": "complexity", "message": "질문 복잡도를 분석하고 있습니다..."},
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(start_event.model_dump())

    # 복잡도 분류 실행
    classifier = get_complexity_classifier()
    result: ComplexityResult = classifier.classify(
        user_message=user_message,
        attachments=attachments,
        conversation_history=state.get("conversation_history", []),
        cache_hit=cache_hit,
    )

    # 분류 완료 이벤트 (기존 호환성 유지)
    complete_event = StreamingEvent(
        event="classification_complete",
        data={
            "step": "complexity",
            "level": result.level.value,
            "confidence": result.confidence,
            "reason": result.reason,
            "path": result.suggested_path,
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(complete_event.model_dump())

    # 진행 상황 이벤트: 분류 완료 (경로에 따른 퍼센트)
    path_percentages = {"fast": 20, "medium": 15, "deep": 10, "thinking": 10}
    progress_complete = create_progress_event(
        step=ProgressStep.CLASSIFYING,
        percentage=path_percentages.get(result.suggested_path, 15),
        message=f"{result.level.value} 처리 경로가 선택되었습니다.",
        execution_path=result.suggested_path,
        step_details={
            "level": result.level.value,
            "confidence": result.confidence,
        },
    )
    streaming_events.append(progress_complete.model_dump())

    logger.info(
        f"[complexity_classifier_node] Result: "
        f"level={result.level.value}, "
        f"confidence={result.confidence:.2f}, "
        f"path={result.suggested_path}"
    )

    # =================================================================
    # Phase 7: 비용 예측
    # =================================================================
    cost_estimate = _estimate_execution_cost(
        complexity_level=result.level.value,
        user_message=user_message,
        attachments=attachments,
    )

    # 비용 경고 확인
    cost_warning = None
    if cost_estimate["estimated_cost_usd"] >= COST_BLOCKING_THRESHOLD:
        # 차단 임계값 초과 - 경고 이벤트 추가
        cost_warning = {
            "type": "blocking",
            "message": f"예상 비용이 높습니다 (${cost_estimate['estimated_cost_usd']:.4f}). "
                      f"더 간단한 질문으로 나누어 주세요.",
            "threshold": COST_BLOCKING_THRESHOLD,
            "estimated_cost": cost_estimate["estimated_cost_usd"],
        }
        warning_event = StreamingEvent(
            event="cost_warning",
            data=cost_warning,
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(warning_event.model_dump())
        logger.warning(
            f"[complexity_classifier_node] Cost blocking threshold exceeded: "
            f"${cost_estimate['estimated_cost_usd']:.4f}"
        )
    elif cost_estimate["estimated_cost_usd"] >= COST_CONFIRMATION_THRESHOLD:
        # 확인 필요 임계값 초과
        cost_warning = {
            "type": "confirmation_required",
            "message": f"예상 비용: ${cost_estimate['estimated_cost_usd']:.4f}",
            "threshold": COST_CONFIRMATION_THRESHOLD,
            "estimated_cost": cost_estimate["estimated_cost_usd"],
        }
        warning_event = StreamingEvent(
            event="cost_warning",
            data=cost_warning,
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(warning_event.model_dump())
        logger.info(
            f"[complexity_classifier_node] Cost confirmation threshold: "
            f"${cost_estimate['estimated_cost_usd']:.4f}"
        )
    elif cost_estimate["estimated_cost_usd"] >= COST_WARNING_THRESHOLD:
        # 경고 임계값 초과
        cost_warning = {
            "type": "warning",
            "message": f"예상 비용: ${cost_estimate['estimated_cost_usd']:.4f}",
            "threshold": COST_WARNING_THRESHOLD,
            "estimated_cost": cost_estimate["estimated_cost_usd"],
        }
        logger.debug(
            f"[complexity_classifier_node] Cost warning threshold: "
            f"${cost_estimate['estimated_cost_usd']:.4f}"
        )

    # Quick Plan 생성 (MEDIUM 경로인 경우)
    quick_plan = None
    if result.level.value == "MEDIUM" and result.suggested_workflow:
        quick_plan = {
            "workflow_name": result.suggested_workflow,
            "tool_name": None,
            "inputs": {"user_message": user_message},
            "expected_output": "text",
        }

    return {
        "complexity_level": result.level.value,
        "complexity_confidence": result.confidence,
        "complexity_reason": result.reason,
        "execution_path": result.suggested_path,
        "quick_plan": quick_plan,
        "streaming_events": streaming_events,
        # Phase 7: 비용 예측 정보
        "estimated_cost": cost_estimate,
        "cost_warning": cost_warning,
    }


def complexity_classifier_node_sync(
    state: ExtendedMasterAgentState
) -> Dict[str, Any]:
    """
    복잡도 분류 노드 (동기 버전)
    """
    import asyncio
    return asyncio.run(complexity_classifier_node(state))


# =============================================================================
# Phase 7: 비용 예측 헬퍼 함수
# =============================================================================

def _estimate_execution_cost(
    complexity_level: str,
    user_message: str,
    attachments: list,
) -> Dict[str, Any]:
    """
    Phase 7: 실행 전 비용 예측

    복잡도 레벨에 따라 예상되는 비용을 계산합니다.

    Args:
        complexity_level: 복잡도 레벨 ("FAST", "MEDIUM", "DEEP", "THINKING")
        user_message: 사용자 메시지
        attachments: 첨부 파일 목록

    Returns:
        비용 예측 정보:
        - estimated_tokens: 예상 토큰
        - estimated_cost_usd: 예상 비용 (USD)
        - cost_tier: 비용 등급
        - breakdown: 세부 분석
    """
    try:
        estimator = get_cost_estimator()

        # 메시지 길이와 첨부파일 정보 계산
        message_length = len(user_message) if user_message else 0
        has_attachments = bool(attachments)
        attachment_size = 0
        if attachments:
            for att in attachments:
                if isinstance(att, dict):
                    content = att.get("content", "")
                    attachment_size += len(content) if isinstance(content, (str, bytes)) else 0

        # 비용 예측 실행
        estimate = estimator.estimate_for_complexity(
            complexity=complexity_level,
            message_length=message_length,
            has_attachments=has_attachments,
            attachment_size=attachment_size,
        )

        return {
            "estimated_tokens": estimate.estimated_tokens,
            "estimated_cost_usd": estimate.estimated_cost_usd,
            "cost_tier": estimate.cost_tier.value,
            "complexity": complexity_level,
            "breakdown": {
                "base_tokens": estimate.breakdown.get("base", 0),
                "message_tokens": estimate.breakdown.get("message", 0),
                "attachment_tokens": estimate.breakdown.get("attachments", 0),
                "tool_tokens": estimate.breakdown.get("tools", 0),
            },
            "thresholds": {
                "warning": COST_WARNING_THRESHOLD,
                "confirmation": COST_CONFIRMATION_THRESHOLD,
                "blocking": COST_BLOCKING_THRESHOLD,
            },
        }

    except Exception as e:
        logger.warning(f"[_estimate_execution_cost] Error: {e}")
        # 오류 시 기본값 반환
        return {
            "estimated_tokens": 0,
            "estimated_cost_usd": 0.0,
            "cost_tier": CostTier.LOW.value,
            "complexity": complexity_level,
            "breakdown": {},
            "error": str(e),
        }


# =============================================================================
# 라우팅 함수
# =============================================================================

def route_by_complexity(state: ExtendedMasterAgentState) -> str:
    """
    복잡도에 따른 라우팅 결정

    Args:
        state: ExtendedMasterAgentState

    Returns:
        "fast" | "medium" | "deep" | "thinking"

    Note:
        state는 Dict[str, Any]로 받습니다.
        ExtendedMasterAgentState TypedDict는 타입 힌트용입니다.
    """
    execution_path = state.get("execution_path", "medium")

    # 유효한 경로 목록 (Phase 6: thinking 추가)
    valid_paths = ["fast", "medium", "deep", "thinking"]

    if execution_path not in valid_paths:
        logger.warning(f"Unknown execution_path: {execution_path}, defaulting to medium")
        return "medium"

    logger.info(f"[route_by_complexity] Routing to: {execution_path}")
    return execution_path
