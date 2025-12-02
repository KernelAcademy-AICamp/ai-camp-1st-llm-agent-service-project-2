"""
Execute Workflows Node - 워크플로우 실행 노드

Phase 5: Agent Hub - Master Agent Graph Node

설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.3.3

역할:
- 병렬/순차 실행 로직
- 개별 워크플로우 실행
- 진행 상황 스트리밍 (workflow_progress, workflow_completed)
- 에러 핸들링 및 폴백
"""

from datetime import datetime
import asyncio
import importlib
import logging
from typing import Dict, Any, List, Optional, Callable

from apps.ai_service.agents.states.master_agent_state import (
    MasterAgentState,
    ExecutionPlan,
    WorkflowStep,
    ToolCall,
    StreamingEvent,
    ExecutionLog,
)
from apps.ai_service.agents.workflow_router import (
    WORKFLOW_REGISTRY,
    WorkflowConfig,
)
from apps.ai_service.agents.workflow_executor import (
    WorkflowExecutor,
    WorkflowInput,
    get_workflow_executor,
)

logger = logging.getLogger(__name__)

# 모듈 레벨 WorkflowExecutor 인스턴스 (지연 초기화)
_workflow_executor: Optional[WorkflowExecutor] = None


def _get_executor() -> WorkflowExecutor:
    """WorkflowExecutor 인스턴스 반환 (지연 초기화)"""
    global _workflow_executor
    if _workflow_executor is None:
        _workflow_executor = get_workflow_executor()
    return _workflow_executor


async def execute_workflows_node(state: MasterAgentState) -> MasterAgentState:
    """
    워크플로우 실행 노드

    실행 계획에 따라 워크플로우와 도구를 실행합니다.

    Args:
        state: MasterAgentState (현재 상태)

    Returns:
        업데이트된 MasterAgentState

    State 업데이트:
        - workflow_results: 워크플로우 실행 결과
        - tool_results: 도구 실행 결과
        - streaming_events: 진행 상황 이벤트 추가
        - execution_logs: 실행 로그 추가

    이벤트 발생:
        1. workflow_started: 워크플로우 시작
        2. workflow_progress: 진행률 업데이트
        3. workflow_completed: 워크플로우 완료
        4. workflow_failed: 워크플로우 실패
        5. tool_executed: 도구 실행 완료
    """
    logger.info("[execute_workflows_node] Starting workflow execution")

    try:
        # 1. ExecutionPlan 복원
        plan_dict = state.get("execution_plan")
        if not plan_dict:
            raise ValueError("Execution plan not found in state")

        plan = ExecutionPlan(**plan_dict)

        if not plan.workflows and not plan.tools:
            logger.warning("[execute_workflows_node] No workflows or tools to execute")

            # 빈 결과로 상태 업데이트
            state["workflow_results"] = {}
            state["tool_results"] = {}
            return state

        logger.info(
            f"[execute_workflows_node] Executing: "
            f"{len(plan.workflows)} workflows, {len(plan.tools)} tools"
        )

        # 2. 결과 저장소 초기화
        workflow_results: Dict[str, Any] = {}
        tool_results: Dict[str, Any] = {}
        execution_logs: List[Dict[str, Any]] = list(state.get("execution_logs", []))
        streaming_events = list(state.get("streaming_events", []))

        # 3. 실행 컨텍스트 구성
        context = {
            "user_message": state["user_message"],
            "attachments": state.get("attachments", []),
            "conversation_history": state.get("conversation_history", []),
            "user_context": state.get("user_context"),
        }

        # 4. 병렬/순차 실행 결정
        if plan.can_parallelize and len(plan.parallel_groups) > 1:
            # 병렬 실행
            workflow_results, tool_results, streaming_events, execution_logs = \
                await _execute_parallel(
                    plan=plan,
                    context=context,
                    streaming_events=streaming_events,
                    execution_logs=execution_logs,
                )
        else:
            # 순차 실행
            workflow_results, tool_results, streaming_events, execution_logs = \
                await _execute_sequential(
                    plan=plan,
                    context=context,
                    streaming_events=streaming_events,
                    execution_logs=execution_logs,
                )

        # 5. 상태 업데이트
        state["workflow_results"] = workflow_results
        state["tool_results"] = tool_results
        state["streaming_events"] = streaming_events
        state["execution_logs"] = execution_logs

        logger.info(
            f"[execute_workflows_node] Completed: "
            f"{len(workflow_results)} workflow results, {len(tool_results)} tool results"
        )

        return state

    except Exception as e:
        logger.error(f"[execute_workflows_node] Error: {e}", exc_info=True)

        # 에러 이벤트
        error_event = StreamingEvent(
            event="error",
            data={
                "step": "execute_workflows",
                "error": str(e),
                "message": "워크플로우 실행 중 오류가 발생했습니다.",
            },
            timestamp=datetime.now().isoformat(),
        )

        streaming_events = list(state.get("streaming_events", []))
        streaming_events.append(error_event.model_dump())

        # 에러 로그 추가
        errors = list(state.get("errors", []))
        errors.append({
            "step": "execute_workflows",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })

        state["workflow_results"] = state.get("workflow_results", {})
        state["tool_results"] = state.get("tool_results", {})
        state["streaming_events"] = streaming_events
        state["errors"] = errors

        return state


async def _execute_sequential(
    plan: ExecutionPlan,
    context: Dict[str, Any],
    streaming_events: List[Dict[str, Any]],
    execution_logs: List[Dict[str, Any]],
) -> tuple:
    """
    순차 실행

    실행 순서에 따라 워크플로우와 도구를 차례로 실행합니다.
    """
    workflow_results: Dict[str, Any] = {}
    tool_results: Dict[str, Any] = {}
    total_steps = plan.total_steps
    current_step = 0

    # 워크플로우 맵 생성
    workflow_map = {wf.step_id: wf for wf in plan.workflows}
    tool_map = {t.tool_id: t for t in plan.tools}

    for step_id in plan.execution_order:
        current_step += 1
        progress = current_step / total_steps if total_steps > 0 else 1.0

        if step_id in workflow_map:
            # 워크플로우 실행
            workflow_step = workflow_map[step_id]
            result, events, logs = await _execute_single_workflow(
                workflow_step=workflow_step,
                context=context,
                current_step=current_step,
                total_steps=total_steps,
                progress=progress,
            )
            workflow_results[step_id] = result
            streaming_events.extend(events)
            execution_logs.extend(logs)

        elif step_id in tool_map:
            # 도구 실행
            tool_call = tool_map[step_id]
            result, events, logs = await _execute_single_tool(
                tool_call=tool_call,
                context=context,
                current_step=current_step,
                total_steps=total_steps,
            )
            tool_results[step_id] = result
            streaming_events.extend(events)
            execution_logs.extend(logs)

    return workflow_results, tool_results, streaming_events, execution_logs


async def _execute_parallel(
    plan: ExecutionPlan,
    context: Dict[str, Any],
    streaming_events: List[Dict[str, Any]],
    execution_logs: List[Dict[str, Any]],
) -> tuple:
    """
    병렬 실행

    병렬 실행 그룹별로 동시 실행합니다.
    """
    workflow_results: Dict[str, Any] = {}
    tool_results: Dict[str, Any] = {}
    total_steps = plan.total_steps
    completed_steps = 0

    # 맵 생성
    workflow_map = {wf.step_id: wf for wf in plan.workflows}
    tool_map = {t.tool_id: t for t in plan.tools}

    for group_idx, group in enumerate(plan.parallel_groups):
        if not group:
            continue

        logger.debug(f"Executing parallel group {group_idx + 1}: {group}")

        # 그룹 내 병렬 실행
        tasks = []
        for step_id in group:
            completed_steps += 1
            progress = completed_steps / total_steps if total_steps > 0 else 1.0

            if step_id in workflow_map:
                task = _execute_single_workflow(
                    workflow_step=workflow_map[step_id],
                    context=context,
                    current_step=completed_steps,
                    total_steps=total_steps,
                    progress=progress,
                )
                tasks.append(("workflow", step_id, task))

            elif step_id in tool_map:
                task = _execute_single_tool(
                    tool_call=tool_map[step_id],
                    context=context,
                    current_step=completed_steps,
                    total_steps=total_steps,
                )
                tasks.append(("tool", step_id, task))

        # 병렬 실행
        if tasks:
            results = await asyncio.gather(
                *[t[2] for t in tasks],
                return_exceptions=True
            )

            # 결과 처리
            for (task_type, step_id, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    logger.error(f"Task {step_id} failed: {result}")
                    error_result = {
                        "error": str(result),
                        "status": "failed",
                    }
                    if task_type == "workflow":
                        workflow_results[step_id] = error_result
                    else:
                        tool_results[step_id] = error_result
                else:
                    res, events, logs = result
                    streaming_events.extend(events)
                    execution_logs.extend(logs)

                    if task_type == "workflow":
                        workflow_results[step_id] = res
                    else:
                        tool_results[step_id] = res

    return workflow_results, tool_results, streaming_events, execution_logs


async def _execute_single_workflow(
    workflow_step: WorkflowStep,
    context: Dict[str, Any],
    current_step: int,
    total_steps: int,
    progress: float,
) -> tuple:
    """
    개별 워크플로우 실행 (WorkflowExecutor 사용)

    Args:
        workflow_step: WorkflowStep
        context: 실행 컨텍스트
        current_step: 현재 단계
        total_steps: 전체 단계 수
        progress: 진행률

    Returns:
        (결과, 이벤트 목록, 로그 목록)
    """
    workflow_name = workflow_step.workflow_name
    step_id = workflow_step.step_id
    streaming_events = []
    execution_logs = []

    logger.info(f"[execute_single_workflow] Starting: {workflow_name}")

    # 1. 시작 이벤트
    start_event = StreamingEvent(
        event="workflow_started",
        data={
            "step_id": step_id,
            "workflow": workflow_name,
            "current_step": current_step,
            "total_steps": total_steps,
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(start_event.model_dump())

    # 2. 실행 로그 시작
    log = ExecutionLog(
        step_id=step_id,
        step_name=workflow_name,
        status="running",
        started_at=datetime.now().isoformat(),
    )

    try:
        # 3. WorkflowInput 생성
        attachment_content = _get_attachment_content(context.get("attachments", []))
        attachments = context.get("attachments", [])
        doc_type = attachments[0].get("type") if attachments else None

        workflow_input = WorkflowInput(
            query=context.get("user_message", ""),
            mode=workflow_step.inputs.get("mode", "standard"),
            top_k=workflow_step.inputs.get("top_k", 5),
            session_id=workflow_step.inputs.get("session_id"),
            user_id=workflow_step.inputs.get("user_id"),
            content=attachment_content or workflow_step.inputs.get("content"),
            doc_type=doc_type or workflow_step.inputs.get("doc_type"),
            extra=workflow_step.inputs,  # 나머지 파라미터는 extra로 전달
        )

        # 4. 진행 상황 이벤트
        progress_event = StreamingEvent(
            event="workflow_progress",
            data={
                "step_id": step_id,
                "workflow": workflow_name,
                "status": "running",
                "progress": progress,
                "message": f"{workflow_name} 실행 중...",
            },
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(progress_event.model_dump())

        # 5. WorkflowExecutor로 실행
        executor = _get_executor()
        output = await executor.execute_with_input(workflow_name, workflow_input)

        # 6. 결과 변환 (WorkflowOutput → Dict)
        if output.success:
            result = {
                "answer": output.answer,
                "sources": output.sources,
                "confidence": output.confidence,
                "processing_time": output.processing_time,
                **output.metadata,
            }
        else:
            result = {
                "error": output.error,
                "answer": output.answer,
                "status": "failed",
            }

        # 7. 완료 이벤트
        complete_event = StreamingEvent(
            event="workflow_completed",
            data={
                "step_id": step_id,
                "workflow": workflow_name,
                "status": "completed" if output.success else "failed",
                "result_preview": _get_result_preview(result),
            },
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(complete_event.model_dump())

        # 8. 로그 업데이트
        log.status = "completed" if output.success else "failed"
        log.completed_at = datetime.now().isoformat()
        log.result = _get_result_preview(result)
        if not output.success:
            log.error = output.error
        execution_logs.append(log.model_dump())

        logger.info(f"[execute_single_workflow] Completed: {workflow_name}")

        return result, streaming_events, execution_logs

    except Exception as e:
        logger.error(f"[execute_single_workflow] Failed {workflow_name}: {e}")

        # 실패 이벤트
        fail_event = StreamingEvent(
            event="workflow_failed",
            data={
                "step_id": step_id,
                "workflow": workflow_name,
                "status": "failed",
                "error": str(e),
            },
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(fail_event.model_dump())

        # 로그 업데이트
        log.status = "failed"
        log.completed_at = datetime.now().isoformat()
        log.error = str(e)
        execution_logs.append(log.model_dump())

        return {"error": str(e), "status": "failed"}, streaming_events, execution_logs


async def _execute_single_tool(
    tool_call: ToolCall,
    context: Dict[str, Any],
    current_step: int,
    total_steps: int,
) -> tuple:
    """
    개별 도구 실행

    Args:
        tool_call: ToolCall
        context: 실행 컨텍스트
        current_step: 현재 단계
        total_steps: 전체 단계 수

    Returns:
        (결과, 이벤트 목록, 로그 목록)
    """
    tool_name = tool_call.tool_name
    tool_id = tool_call.tool_id
    streaming_events = []
    execution_logs = []

    logger.info(f"[execute_single_tool] Starting: {tool_name}")

    # 실행 로그 시작
    log = ExecutionLog(
        step_id=tool_id,
        step_name=tool_name,
        status="running",
        started_at=datetime.now().isoformat(),
    )

    try:
        # 도구 로드 및 실행
        tool_func = _load_tool(tool_name)

        if tool_func is None:
            raise ValueError(f"Tool not found: {tool_name}")

        # 입력 준비
        inputs = {**tool_call.inputs}
        inputs["query"] = context.get("user_message", "")

        # 도구 실행
        result = await _run_tool(tool_func, inputs)

        # 완료 이벤트
        complete_event = StreamingEvent(
            event="tool_executed",
            data={
                "tool_id": tool_id,
                "tool": tool_name,
                "status": "completed",
                "result_preview": _get_result_preview(result),
            },
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(complete_event.model_dump())

        # 로그 업데이트
        log.status = "completed"
        log.completed_at = datetime.now().isoformat()
        log.result = _get_result_preview(result)
        execution_logs.append(log.model_dump())

        logger.info(f"[execute_single_tool] Completed: {tool_name}")

        return result, streaming_events, execution_logs

    except Exception as e:
        logger.error(f"[execute_single_tool] Failed {tool_name}: {e}")

        # 로그 업데이트
        log.status = "failed"
        log.completed_at = datetime.now().isoformat()
        log.error = str(e)
        execution_logs.append(log.model_dump())

        return {"error": str(e), "status": "failed"}, streaming_events, execution_logs


# =============================================================================
# 레거시 함수들 (WorkflowExecutor로 대체됨)
# =============================================================================
# 아래 함수들은 WorkflowExecutor 클래스로 대체되었습니다:
# - _load_workflow() → WorkflowExecutor._get_workflow_instance()
# - _filter_valid_params() → WorkflowExecutor._map_input_params() (명시적 매핑)
# - _run_workflow() → WorkflowExecutor._execute_workflow_internal()
#
# WorkflowExecutor 사용 이점:
# 1. inspect.signature() 런타임 호출 제거 (성능 향상)
# 2. 워크플로우별 파라미터 매핑 명시적 정의 (유지보수성)
# 3. 워크플로우 인스턴스 캐싱 (메모리 효율)
# 4. 표준화된 입력/출력 형식 (WorkflowInput/WorkflowOutput)
# =============================================================================


# =============================================================================
# MCP 도구 레지스트리 (동적 레지스트리 패턴)
# =============================================================================
# apps/ai_service/mcp/tools/__init__.py의 __all__을 활용해 자동으로 레지스트리 생성
# 도구 추가 시 __init__.py만 수정하면 됨 (이 파일 수정 불필요)
# MCP 서버가 별도 프로세스로 실행되는 경우 MCP 클라이언트로 대체 가능

_tool_registry: Optional[Dict[str, Callable]] = None


def _build_tool_registry() -> Dict[str, Callable]:
    """
    MCP 도구 레지스트리 빌드

    apps/ai_service/mcp/tools/__init__.py의 __all__에서
    도구 이름을 읽어 자동으로 레지스트리를 생성합니다.

    Returns:
        도구 이름 → 도구 함수 매핑
    """
    from apps.ai_service.mcp import tools

    registry = {}
    for tool_name in tools.__all__:
        tool_func = getattr(tools, tool_name, None)
        if callable(tool_func):
            registry[tool_name] = tool_func
        else:
            logger.warning(f"[_build_tool_registry] '{tool_name}' is not callable, skipping")

    return registry


def _get_tool_registry() -> Dict[str, Callable]:
    """
    MCP 도구 레지스트리 반환 (지연 로딩 + 싱글톤)

    Returns:
        도구 이름 → 도구 함수 매핑

    등록된 도구 카테고리:
        - Precedent Tools: search_precedents, get_precedent_details, search_with_feedback_filtering
        - Document Tools: analyze_document, extract_clauses, summarize_document, detect_document_type
        - Case Tools: analyze_case, extract_parties, identify_issues, search_related_cases, assess_case_complexity
        - Analysis Tools: analyze_risks, calculate_metrics, compare_documents, generate_report, aggregate_statistics
        - LLM Tools: execute_on_model, get_model_metadata, calculate_llm_metrics, store_comparison_log, select_best_model
        - External API Tools: fetch_court_api, fetch_statute_api, parse_legal_document, validate_document_structure
    """
    global _tool_registry

    if _tool_registry is not None:
        return _tool_registry

    logger.info("[_get_tool_registry] Building MCP tool registry...")

    try:
        _tool_registry = _build_tool_registry()
        logger.info(f"[_get_tool_registry] Loaded {len(_tool_registry)} MCP tools: {list(_tool_registry.keys())}")
        return _tool_registry

    except ImportError as e:
        logger.error(f"[_get_tool_registry] Failed to import MCP tools: {e}")
        _tool_registry = {}
        return _tool_registry


def _load_tool(tool_name: str) -> Optional[Callable]:
    """
    MCP 도구 로드

    Args:
        tool_name: 도구 이름 (예: "search_precedents", "analyze_document")

    Returns:
        도구 함수 또는 None
    """
    registry = _get_tool_registry()
    tool_func = registry.get(tool_name)

    if tool_func is None:
        logger.warning(f"[_load_tool] Tool not found: {tool_name}")
        logger.debug(f"[_load_tool] Available tools: {list(registry.keys())}")

    return tool_func


async def _run_tool(tool_func: Callable, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    도구 실행

    Args:
        tool_func: 도구 함수
        inputs: 입력 파라미터

    Returns:
        실행 결과
    """
    try:
        if asyncio.iscoroutinefunction(tool_func):
            result = await tool_func(**inputs)
        else:
            result = tool_func(**inputs)

        return result if isinstance(result, dict) else {"result": result}

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        raise


def _get_attachment_content(attachments: List[Dict[str, Any]]) -> str:
    """
    첨부 파일에서 content 추출

    Args:
        attachments: 첨부 파일 목록

    Returns:
        첫 번째 첨부 파일의 content 또는 빈 문자열
    """
    if attachments and len(attachments) > 0:
        attachment = attachments[0]
        if attachment.get("content"):
            return attachment.get("content", "")
        metadata = attachment.get("metadata") or {}
        if isinstance(metadata, dict):
            # 일부 전처리 엔드포인트는 text 필드를 metadata에 담아 전달
            text = metadata.get("text") or metadata.get("extracted_text")
            if text:
                return text
    return ""


def _get_result_preview(result: Any, max_length: int = 200) -> Dict[str, Any]:
    """
    결과 미리보기 생성

    Args:
        result: 실행 결과
        max_length: 최대 문자열 길이

    Returns:
        미리보기 딕셔너리
    """
    if isinstance(result, dict):
        preview = {}
        for key, value in result.items():
            if isinstance(value, str) and len(value) > max_length:
                preview[key] = value[:max_length] + "..."
            elif isinstance(value, (list, dict)):
                preview[key] = f"[{type(value).__name__}, length={len(value)}]"
            else:
                preview[key] = value
        return preview
    elif isinstance(result, str):
        return {"text": result[:max_length] + "..." if len(result) > max_length else result}
    else:
        return {"result": str(result)[:max_length]}


def execute_workflows_node_sync(state: MasterAgentState) -> MasterAgentState:
    """
    워크플로우 실행 노드 (동기 버전)
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                execute_workflows_node(state)
            )
            return future.result()
    except RuntimeError:
        return asyncio.run(execute_workflows_node(state))
