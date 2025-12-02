"""
Plan Execution Node - 실행 계획 수립 노드

Phase 5: Agent Hub - Master Agent Graph Node

설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.3.3

역할:
- WorkflowRouter를 사용하여 실행 계획 생성
- 권한 검증 (check_workflow_permission)
- 스트리밍 이벤트 발생 (execution_plan)
- 권한 없는 워크플로우 필터링 및 알림
"""

from datetime import datetime
import logging
from typing import Dict, Any, List

from apps.ai_service.agents.states.master_agent_state import (
    MasterAgentState,
    Intent,
    IntentCategory,
    ExecutionPlan,
    StreamingEvent,
    WorkflowStep,
)
from apps.ai_service.agents.workflow_router import (
    WorkflowRouter,
    get_workflow_router,
    WORKFLOW_REGISTRY,
)
from apps.ai_service.middleware.permissions import (
    check_workflow_permission,
    filter_workflows_by_permission,
    WORKFLOW_PERMISSIONS,
)

logger = logging.getLogger(__name__)


async def plan_execution_node(state: MasterAgentState) -> MasterAgentState:
    """
    실행 계획 수립 노드

    분류된 의도를 바탕으로 실행할 워크플로우와 도구를 결정합니다.

    Args:
        state: MasterAgentState (현재 상태)

    Returns:
        업데이트된 MasterAgentState

    State 업데이트:
        - execution_plan: ExecutionPlan 객체 (dict)
        - streaming_events: execution_plan 이벤트 추가

    이벤트 발생:
        1. execution_plan: 실행 계획 수립 완료
        2. permission_denied: 권한 없는 워크플로우 알림
        3. no_workflows_available: 실행 가능한 워크플로우가 없는 경우
    """
    logger.info("[plan_execution_node] Starting execution planning")

    try:
        # 1. Intent 복원
        intent_dict = state.get("intent")
        if not intent_dict:
            raise ValueError("Intent not found in state")

        intent = Intent(**intent_dict)
        # intent.category는 use_enum_values=True로 인해 문자열일 수 있음
        category_value = intent.category.value if hasattr(intent.category, 'value') else intent.category
        logger.debug(f"Intent: {category_value}")

        # 2. 사용자 컨텍스트에서 역할 추출
        user_context = state.get("user_context") or {}
        user_role = user_context.get("role", "VIEWER")
        logger.debug(f"User role: {user_role}")

        # 3. 실행 컨텍스트 구성
        context: Dict[str, Any] = {
            "user_message": state["user_message"],
            "attachments": state.get("attachments", []),
            "conversation_history": state.get("conversation_history", []),
            "query": state["user_message"],
        }

        # 4. WorkflowRouter로 실행 계획 생성
        router = get_workflow_router()
        plan: ExecutionPlan = router.route(intent, context)

        logger.info(
            f"[plan_execution_node] Initial plan: "
            f"{len(plan.workflows)} workflows, {len(plan.tools)} tools"
        )

        # 5. 권한 검증 및 필터링
        streaming_events = list(state.get("streaming_events", []))
        filtered_workflows: List[WorkflowStep] = []
        denied_workflows: List[Dict[str, Any]] = []

        for workflow_step in plan.workflows:
            workflow_name = workflow_step.workflow_name

            if check_workflow_permission(workflow_name, user_role):
                filtered_workflows.append(workflow_step)
                logger.debug(f"Workflow {workflow_name}: ALLOWED")
            else:
                # 권한 없음 - 거부 목록에 추가
                config = WORKFLOW_PERMISSIONS.get(workflow_name, {})
                required_roles = [r.value for r in config.get("required_roles", [])]

                denied_info = {
                    "workflow": workflow_name,
                    "required_roles": required_roles,
                    "user_role": user_role,
                    "description": config.get("description", "알 수 없는 워크플로우"),
                }
                denied_workflows.append(denied_info)

                logger.warning(
                    f"Workflow {workflow_name}: DENIED "
                    f"(requires {required_roles}, user has {user_role})"
                )

        # 6. 권한 거부 이벤트 발생
        if denied_workflows:
            for denied in denied_workflows:
                permission_event = StreamingEvent(
                    event="permission_denied",
                    data={
                        "workflow": denied["workflow"],
                        "required_roles": denied["required_roles"],
                        "user_role": denied["user_role"],
                        "message": f"'{denied['description']}'은(는) "
                                   f"{', '.join(denied['required_roles'])} 역할에서만 사용 가능합니다.",
                    },
                    timestamp=datetime.now().isoformat(),
                )
                streaming_events.append(permission_event.model_dump())

        # 7. 실행 가능한 워크플로우가 없는 경우 처리
        if not filtered_workflows and not plan.tools:
            logger.warning("[plan_execution_node] No executable workflows or tools")

            no_workflows_event = StreamingEvent(
                event="no_workflows_available",
                data={
                    "message": "현재 역할로 실행 가능한 기능이 없습니다. "
                               "권한 업그레이드가 필요하거나 요청 내용을 확인해 주세요.",
                    "user_role": user_role,
                    "denied_workflows": denied_workflows,
                },
                timestamp=datetime.now().isoformat(),
            )
            streaming_events.append(no_workflows_event.model_dump())

            # 빈 실행 계획 저장
            empty_plan = ExecutionPlan(
                plan_id=plan.plan_id,
                workflows=[],
                tools=[],
                execution_order=[],
                estimated_total_time=0.0,
                can_parallelize=False,
                parallel_groups=[],
            )
            state["execution_plan"] = empty_plan.model_dump()
            state["streaming_events"] = streaming_events

            return state

        # 8. 필터링된 워크플로우로 계획 업데이트
        plan.workflows = filtered_workflows

        # 실행 순서 업데이트
        valid_step_ids = {wf.step_id for wf in filtered_workflows}
        valid_tool_ids = {t.tool_id for t in plan.tools}
        plan.execution_order = [
            step_id for step_id in plan.execution_order
            if step_id in valid_step_ids or step_id in valid_tool_ids
        ]

        # 병렬 그룹 업데이트
        plan.parallel_groups = [
            [step_id for step_id in group if step_id in valid_step_ids or step_id in valid_tool_ids]
            for group in plan.parallel_groups
        ]
        plan.parallel_groups = [g for g in plan.parallel_groups if g]  # 빈 그룹 제거

        # 9. 실행 계획 이벤트
        execution_plan_event = StreamingEvent(
            event="execution_plan",
            data={
                "plan_id": plan.plan_id,
                "steps": _format_execution_steps(plan),
                "workflows": [wf.workflow_name for wf in plan.workflows],
                "tools": [t.tool_name for t in plan.tools],
                "estimated_time": plan.estimated_total_time,
                "can_parallelize": plan.can_parallelize,
                "total_steps": plan.total_steps,
            },
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(execution_plan_event.model_dump())

        # 10. 상태 업데이트
        state["execution_plan"] = plan.model_dump()
        state["streaming_events"] = streaming_events

        logger.info(
            f"[plan_execution_node] Final plan: "
            f"{len(plan.workflows)} workflows, {len(plan.tools)} tools, "
            f"estimated_time={plan.estimated_total_time:.1f}s"
        )

        return state

    except Exception as e:
        logger.error(f"[plan_execution_node] Error: {e}", exc_info=True)

        # 에러 이벤트
        error_event = StreamingEvent(
            event="error",
            data={
                "step": "plan_execution",
                "error": str(e),
                "message": "실행 계획 수립 중 오류가 발생했습니다.",
            },
            timestamp=datetime.now().isoformat(),
        )

        streaming_events = list(state.get("streaming_events", []))
        streaming_events.append(error_event.model_dump())

        # 에러 로그 추가
        errors = list(state.get("errors", []))
        errors.append({
            "step": "plan_execution",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })

        # 빈 실행 계획
        empty_plan = ExecutionPlan(
            workflows=[],
            tools=[],
            execution_order=[],
            estimated_total_time=0.0,
            can_parallelize=False,
            parallel_groups=[],
        )

        state["execution_plan"] = empty_plan.model_dump()
        state["streaming_events"] = streaming_events
        state["errors"] = errors

        return state


def _format_execution_steps(plan: ExecutionPlan) -> List[str]:
    """
    실행 단계를 사용자 친화적인 문자열로 포맷팅

    Args:
        plan: ExecutionPlan

    Returns:
        포맷팅된 단계 목록
    """
    steps = []

    # 워크플로우 단계
    for idx, wf in enumerate(plan.workflows, 1):
        config = WORKFLOW_REGISTRY.get(wf.workflow_name, {})
        description = getattr(config, 'description', wf.workflow_name) if config else wf.workflow_name
        steps.append(f"{idx}. {description}")

    # 도구 단계
    tool_start_idx = len(plan.workflows) + 1
    for idx, tool in enumerate(plan.tools, tool_start_idx):
        steps.append(f"{idx}. {tool.tool_name}")

    return steps


def plan_execution_node_sync(state: MasterAgentState) -> MasterAgentState:
    """
    실행 계획 수립 노드 (동기 버전)
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                plan_execution_node(state)
            )
            return future.result()
    except RuntimeError:
        return asyncio.run(plan_execution_node(state))
