"""
Medium Path Node

MEDIUM 경로 처리 노드:
1. Quick Plan 확인
2. 단일 워크플로우 실행 또는 단일 도구 실행
3. 결과를 workflow_results에 저장

목표 응답 시간: 3-5초
LLM 호출: 1-2회
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

from apps.ai_service.agents.states.master_agent_state import (
    ExtendedMasterAgentState,
    StreamingEvent,
    QuickPlan,
    ProgressStep,
    create_progress_event,
)
from apps.ai_service.agents.tools.registry import (
    get_tool_registry,
    ToolResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 워크플로우 이름 → 친화적 설명 매핑
# =============================================================================

WORKFLOW_DESCRIPTIONS = {
    "rag_workflow": "법률 정보를 검색하고 있습니다...",
    "document_workflow": "문서를 분석하고 있습니다...",
    "case_workflow": "판례를 분석하고 있습니다...",
    "risk_workflow": "리스크를 평가하고 있습니다...",
    "llm_comparison_workflow": "다양한 모델로 비교 분석하고 있습니다...",
}


# =============================================================================
# Medium Path Node
# =============================================================================

async def medium_path_node(state: ExtendedMasterAgentState) -> Dict[str, Any]:
    """
    Medium Path 처리 노드

    처리 흐름:
    1. quick_plan 확인 (complexity_classifier_node에서 설정)
    2. quick_plan이 없으면 Intent 기반으로 생성
    3. 워크플로우 또는 도구 실행
    4. 결과를 workflow_results에 저장

    입력:
        - user_message: 사용자 메시지
        - quick_plan: QuickPlan (선택)
        - intent: Intent (fallback용)
        - attachments: 첨부 파일

    출력:
        - workflow_results: 실행 결과
        - response_metadata: {"path": "medium", "workflow": "..."}

    Args:
        state: ExtendedMasterAgentState

    Returns:
        업데이트할 필드 딕셔너리
    """
    logger.info("[medium_path_node] Processing MEDIUM path")

    user_message = state.get("user_message", "")
    quick_plan_dict = state.get("quick_plan")
    intent_dict = state.get("intent", {})
    attachments = state.get("attachments", [])

    streaming_events = list(state.get("streaming_events", []))

    # =========================================================================
    # 1. Quick Plan 확인 또는 생성
    # =========================================================================
    if quick_plan_dict:
        quick_plan = QuickPlan.from_dict(quick_plan_dict)
    else:
        quick_plan = _create_quick_plan_from_intent(intent_dict, user_message)

    logger.info(
        f"[medium_path_node] Quick plan: "
        f"workflow={quick_plan.workflow_name}, tool={quick_plan.tool_name}"
    )

    # 처리 시작 이벤트
    workflow_desc = WORKFLOW_DESCRIPTIONS.get(
        quick_plan.workflow_name or "",
        "요청을 처리하고 있습니다..."
    )

    # 진행 상황 이벤트: 실행 시작 (30%)
    progress_start = create_progress_event(
        step=ProgressStep.EXECUTING,
        percentage=30,
        message=workflow_desc,
        execution_path="medium",
        step_details={
            "workflow": quick_plan.workflow_name,
            "tool": quick_plan.tool_name,
        },
    )
    streaming_events.append(progress_start.model_dump())

    start_event = StreamingEvent(
        event="medium_path_start",
        data={
            "step": "medium_path",
            "message": workflow_desc,
            "workflow": quick_plan.workflow_name,
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(start_event.model_dump())

    # =========================================================================
    # 2. 입력 파라미터 준비
    # =========================================================================
    inputs = _prepare_inputs(quick_plan, user_message, attachments or [])

    # =========================================================================
    # 3. 워크플로우 또는 도구 실행
    # =========================================================================
    registry = get_tool_registry()

    if quick_plan.workflow_name:
        result = await registry.execute_workflow(
            workflow_name=quick_plan.workflow_name,
            inputs=inputs,
        )
    elif quick_plan.tool_name:
        result = await registry.execute_tool(
            tool_name=quick_plan.tool_name,
            inputs=inputs,
        )
    else:
        # Fallback: RAG 워크플로우
        logger.warning("[medium_path_node] No workflow or tool specified, falling back to RAG")
        result = await registry.execute_workflow(
            workflow_name="rag_workflow",
            inputs={"query": user_message, "top_k": 5},
        )

    # =========================================================================
    # 4. 결과 처리
    # =========================================================================

    # 진행 상황 이벤트: 실행 완료 (70%)
    progress_complete = create_progress_event(
        step=ProgressStep.EXECUTING,
        percentage=70,
        message="결과를 정리하고 있습니다...",
        execution_path="medium",
        step_details={
            "success": result.success,
            "workflow": quick_plan.workflow_name,
        },
    )
    streaming_events.append(progress_complete.model_dump())

    complete_event = StreamingEvent(
        event="medium_path_complete",
        data={
            "success": result.success,
            "workflow": quick_plan.workflow_name,
            "has_results": result.data is not None,
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(complete_event.model_dump())

    if result.success:
        return {
            "workflow_results": {
                "medium_path_result": result.data,
                "workflow_name": quick_plan.workflow_name,
            },
            "response_metadata": {
                "path": "medium",
                "workflow": quick_plan.workflow_name,
                "tool": quick_plan.tool_name,
            },
            "streaming_events": streaming_events,
        }
    else:
        logger.error(f"[medium_path_node] Execution failed: {result.error}")
        return {
            "errors": [{"step": "medium_path", "error": result.error}],
            "response_metadata": {
                "path": "medium",
                "workflow": quick_plan.workflow_name,
                "error": True,
            },
            "streaming_events": streaming_events,
        }


def medium_path_node_sync(state: ExtendedMasterAgentState) -> Dict[str, Any]:
    """Medium Path 노드 (동기 버전)"""
    import asyncio
    return asyncio.run(medium_path_node(state))


# =============================================================================
# Helper 함수들
# =============================================================================

def _create_quick_plan_from_intent(
    intent_dict: Dict[str, Any],
    user_message: str,
) -> QuickPlan:
    """
    Intent에서 QuickPlan 생성

    Args:
        intent_dict: Intent 딕셔너리
        user_message: 사용자 메시지

    Returns:
        QuickPlan 객체
    """
    category = intent_dict.get("category", "QUERY")
    suggested_workflows = intent_dict.get("suggested_workflows", [])

    # 카테고리 → 워크플로우 매핑
    category_workflow_map = {
        "QUERY": "rag_workflow",
        "DOCUMENT_ANALYSIS": "document_workflow",
        "CASE_ANALYSIS": "case_workflow",
        "RISK_ASSESSMENT": "risk_workflow",
        "COMPARISON": "llm_comparison_workflow",
        "SEARCH": "rag_workflow",
    }

    workflow_name = None
    if suggested_workflows:
        workflow_name = suggested_workflows[0]
    else:
        workflow_name = category_workflow_map.get(category, "rag_workflow")

    return QuickPlan(
        workflow_name=workflow_name,
        inputs={"query": user_message},
        expected_output="text",
    )


def _prepare_inputs(
    quick_plan: QuickPlan,
    user_message: str,
    attachments: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    워크플로우/도구 실행을 위한 입력 준비

    Args:
        quick_plan: QuickPlan
        user_message: 사용자 메시지
        attachments: 첨부 파일 목록

    Returns:
        입력 딕셔너리
    """
    inputs = dict(quick_plan.inputs)

    # 기본 입력 추가
    if "query" not in inputs:
        inputs["query"] = user_message

    if "user_message" not in inputs:
        inputs["user_message"] = user_message

    # 첨부 파일 처리
    if attachments:
        # 첫 번째 첨부 파일의 내용 추가 (단일 문서 가정)
        first_attachment = attachments[0]
        if "content" in first_attachment:
            # WorkflowExecutor가 "content" 또는 "text" 키를 찾으므로 "content"로 설정
            inputs["content"] = first_attachment["content"]
        if "filename" in first_attachment:
            inputs["filename"] = first_attachment["filename"]

    return inputs
