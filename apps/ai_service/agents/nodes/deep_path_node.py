"""
Deep Path Node - 복잡한 분석 경로 (Phase 7: 병렬 실행)

DEEP 경로 처리 노드:
1. 복합 요청 분석 및 계획 수립
2. 의존성 기반 병렬 그룹화
3. 그룹별 병렬 실행 (asyncio.gather)
4. 결과 종합

목표 응답 시간: 5-15초
LLM 호출: 3-5회 (병렬 실행으로 시간 단축)
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Set
import asyncio
import uuid
import logging

from apps.ai_service.agents.states.master_agent_state import (
    ExtendedMasterAgentState,
    StreamingEvent,
    DeepPlan,
    ExecutionStep,
    ProgressStep,
    create_progress_event,
)
from apps.ai_service.agents.tools.registry import (
    get_tool_registry,
    ToolResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 설정
# =============================================================================

MAX_PARALLEL_TASKS = 3  # 동시 실행 최대 수
MAX_STEPS = 5           # 최대 단계 수 (무한 루프 방지)
STEP_TIMEOUT = 30       # 단계별 타임아웃 (초)


# =============================================================================
# 의존성 기반 병렬 그룹화 (Phase 7)
# =============================================================================

def build_execution_groups(steps: List[ExecutionStep]) -> List[List[ExecutionStep]]:
    """
    의존성 기반 병렬 실행 그룹 생성

    의존성이 없는 단계들을 같은 그룹에 배치하여 병렬 실행 가능하게 합니다.

    알고리즘:
    1. 의존성이 모두 완료된 단계를 찾음
    2. 해당 단계들을 현재 그룹에 추가
    3. 그룹 크기가 MAX_PARALLEL_TASKS를 초과하면 분할
    4. 완료 표시 후 다음 반복

    Args:
        steps: 실행 단계 목록

    Returns:
        병렬 실행 그룹 목록 (그룹 내 단계는 병렬 실행 가능)
    """
    if not steps:
        return []

    # 완료된 단계 추적
    completed: Set[str] = set()
    remaining = list(steps)
    groups: List[List[ExecutionStep]] = []

    while remaining:
        # 현재 실행 가능한 단계 찾기 (의존성이 모두 완료된 단계)
        current_group = []
        still_remaining = []

        for step in remaining:
            # depends_on 필드 확인 (없으면 빈 리스트)
            deps = step.depends_on if hasattr(step, 'depends_on') and step.depends_on else []
            deps_satisfied = all(dep in completed for dep in deps)

            if deps_satisfied:
                current_group.append(step)
            else:
                still_remaining.append(step)

        if not current_group:
            # 순환 의존성 또는 잘못된 의존성
            logger.warning(
                f"[build_execution_groups] Circular dependency detected or "
                f"missing dependencies. Remaining: {[s.step_id for s in still_remaining]}"
            )
            # 남은 것들 순차 처리
            for step in still_remaining:
                groups.append([step])
            break

        # 우선순위 정렬 (낮을수록 먼저)
        current_group.sort(key=lambda s: getattr(s, 'priority', 0))

        # 그룹 크기 제한 (MAX_PARALLEL_TASKS 단위로 분할)
        while current_group:
            batch = current_group[:MAX_PARALLEL_TASKS]
            groups.append(batch)

            # 완료 표시
            for step in batch:
                completed.add(step.step_id)

            current_group = current_group[MAX_PARALLEL_TASKS:]

        remaining = still_remaining

    logger.info(
        f"[build_execution_groups] Created {len(groups)} groups from {len(steps)} steps"
    )

    return groups


# =============================================================================
# 개별 단계 실행 (타임아웃 지원)
# =============================================================================

async def _execute_step_with_timeout(
    registry,
    step: ExecutionStep,
    previous_results: Dict[str, Any],
    user_message: str,
    attachments: List[Dict[str, Any]],
    timeout: float = STEP_TIMEOUT,
) -> Dict[str, Any]:
    """
    타임아웃과 함께 단계 실행

    Args:
        registry: ToolRegistry 인스턴스
        step: 실행할 단계
        previous_results: 이전 단계 결과 (의존성 주입용)
        user_message: 사용자 메시지
        attachments: 첨부 파일 목록
        timeout: 타임아웃 (초)

    Returns:
        {
            "step_id": str,
            "step_name": str,
            "success": bool,
            "data": Any,
            "error": str or None,
            "tokens_used": int,
            "execution_time": float
        }
    """
    import time
    start_time = time.time()

    # 입력 준비 (의존성 결과 주입)
    inputs = _prepare_step_inputs(step, previous_results, user_message, attachments)

    try:
        # 워크플로우 또는 도구 실행
        step_type = getattr(step, 'step_type', 'workflow')

        if step_type == "workflow":
            result = await asyncio.wait_for(
                registry.execute_workflow(step.name, inputs),
                timeout=timeout,
            )
        else:  # tool
            result = await asyncio.wait_for(
                registry.execute_tool(step.name, inputs),
                timeout=timeout,
            )

        execution_time = time.time() - start_time

        return {
            "step_id": step.step_id,
            "step_name": step.name,
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "tokens_used": getattr(result, 'tokens_used', 0),
            "execution_time": execution_time,
        }

    except asyncio.TimeoutError:
        execution_time = time.time() - start_time
        logger.error(f"[_execute_step_with_timeout] Step {step.name} timed out after {timeout}s")
        return {
            "step_id": step.step_id,
            "step_name": step.name,
            "success": False,
            "data": None,
            "error": f"Step timed out after {timeout}s",
            "tokens_used": 0,
            "execution_time": execution_time,
        }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"[_execute_step_with_timeout] Step {step.name} failed: {e}")
        return {
            "step_id": step.step_id,
            "step_name": step.name,
            "success": False,
            "data": None,
            "error": str(e),
            "tokens_used": 0,
            "execution_time": execution_time,
        }


# =============================================================================
# Deep Path Node (Phase 7: 병렬 실행)
# =============================================================================

async def deep_path_node(state: ExtendedMasterAgentState) -> Dict[str, Any]:
    """
    Deep Path 처리 노드 (Phase 7: 병렬 실행 지원)

    처리 흐름:
    1. 복합 요청 분석
    2. 실행 계획 수립 (DeepPlan)
    3. 의존성 기반 그룹화
    4. 그룹별 병렬 실행 (asyncio.gather)
    5. 결과 종합

    입력:
        - user_message: 사용자 메시지
        - intent: Intent (하위 작업 추출용)
        - attachments: 첨부 파일 목록

    출력:
        - workflow_results: 모든 단계 실행 결과
        - response_metadata: {"path": "deep", "steps_executed": N}
        - execution_logs: 실행 로그

    Args:
        state: ExtendedMasterAgentState

    Returns:
        업데이트할 필드 딕셔너리
    """
    logger.info("[deep_path_node] Processing DEEP path with parallel execution")

    user_message = state.get("user_message", "")
    intent_dict = state.get("intent", {})
    attachments = state.get("attachments", []) or []

    streaming_events = list(state.get("streaming_events", []))
    execution_logs = list(state.get("execution_logs", []))

    # 진행 상황 이벤트: Deep Path 시작 (15%)
    progress_start = create_progress_event(
        step=ProgressStep.PLANNING,
        percentage=15,
        message="복합 요청을 분석하고 있습니다...",
        execution_path="deep",
    )
    streaming_events.append(progress_start.model_dump())

    # 처리 시작 이벤트 (기존 호환성 유지)
    start_event = StreamingEvent(
        event="deep_path_start",
        data={
            "step": "deep_path",
            "message": "복합 요청을 분석하고 있습니다...",
            "max_parallel": MAX_PARALLEL_TASKS,
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(start_event.model_dump())

    # =========================================================================
    # 1. 실행 계획 수립
    # =========================================================================
    plan = await _create_deep_plan(user_message, intent_dict, attachments)

    # 진행 상황 이벤트: 계획 수립 완료 (25%)
    progress_plan = create_progress_event(
        step=ProgressStep.PLANNING,
        percentage=25,
        message=f"{plan.total_steps}단계 실행 계획이 수립되었습니다.",
        execution_path="deep",
        step_details={"total_steps": plan.total_steps},
    )
    streaming_events.append(progress_plan.model_dump())

    plan_event = StreamingEvent(
        event="deep_path_plan",
        data={
            "total_steps": plan.total_steps,
            "estimated_time": plan.estimated_time,
            "steps": [s.name for s in plan.steps],
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(plan_event.model_dump())

    logger.info(f"[deep_path_node] Plan created: {plan.total_steps} steps")

    # =========================================================================
    # 2. 의존성 기반 그룹화
    # =========================================================================
    execution_groups = build_execution_groups(plan.steps)

    # parallel_groups 업데이트
    plan.parallel_groups = [[s.step_id for s in group] for group in execution_groups]

    logger.info(
        f"[deep_path_node] Created {len(execution_groups)} execution groups "
        f"from {plan.total_steps} steps"
    )

    # =========================================================================
    # 3. 그룹별 병렬 실행
    # =========================================================================
    all_results: Dict[str, Any] = {}
    total_tool_calls = 0
    total_tokens = 0

    registry = get_tool_registry()

    for group_idx, group in enumerate(execution_groups):
        group_start = datetime.now()

        logger.info(
            f"[deep_path_node] Executing group {group_idx + 1}/{len(execution_groups)} "
            f"with {len(group)} tasks"
        )

        # 진행 상황 이벤트: 그룹 실행 (30% ~ 65% 범위)
        # 그룹 수에 따라 진행률 계산: 30 + (group_idx / total_groups) * 35
        group_progress = 30 + int((group_idx / max(len(execution_groups), 1)) * 35)
        progress_group = create_progress_event(
            step=ProgressStep.EXECUTING,
            percentage=group_progress,
            message=f"그룹 {group_idx + 1}/{len(execution_groups)} 실행 중...",
            execution_path="deep",
            step_details={
                "group_index": group_idx,
                "total_groups": len(execution_groups),
                "tasks": [s.name for s in group],
            },
        )
        streaming_events.append(progress_group.model_dump())

        # 그룹 시작 이벤트 (기존 호환성 유지)
        group_event = StreamingEvent(
            event="deep_group_start",
            data={
                "group_index": group_idx,
                "total_groups": len(execution_groups),
                "tasks": [s.name for s in group],
                "parallel": len(group) > 1,
            },
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(group_event.model_dump())

        # 병렬 실행 (그룹 내 단계들)
        if len(group) > 1:
            # asyncio.gather로 병렬 실행
            tasks = [
                _execute_step_with_timeout(
                    registry,
                    step,
                    all_results,
                    user_message,
                    attachments,
                    timeout=STEP_TIMEOUT,
                )
                for step in group
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 처리
            for i, result in enumerate(results):
                step = group[i]
                if isinstance(result, Exception):
                    logger.error(f"[deep_path_node] Step {step.step_id} exception: {result}")
                    step_result = {
                        "step_id": step.step_id,
                        "step_name": step.name,
                        "success": False,
                        "data": None,
                        "error": str(result),
                        "tokens_used": 0,
                        "execution_time": 0.0,
                    }
                else:
                    step_result = result

                all_results[step.step_id] = step_result
                total_tool_calls += 1
                total_tokens += step_result.get("tokens_used", 0)

                # 실행 로그
                execution_logs.append({
                    "step_id": step.step_id,
                    "step_name": step.name,
                    "group_index": group_idx,
                    "status": "completed" if step_result.get("success") else "failed",
                    "started_at": group_start.isoformat(),
                    "completed_at": datetime.now().isoformat(),
                    "execution_time": step_result.get("execution_time", 0),
                    "result": {"success": step_result.get("success")},
                    "error": step_result.get("error"),
                    "parallel": True,
                })
        else:
            # 단일 작업은 직접 실행
            step = group[0]
            result = await _execute_step_with_timeout(
                registry,
                step,
                all_results,
                user_message,
                attachments,
                timeout=STEP_TIMEOUT,
            )

            all_results[step.step_id] = result
            total_tool_calls += 1
            total_tokens += result.get("tokens_used", 0)

            # 실행 로그
            execution_logs.append({
                "step_id": step.step_id,
                "step_name": step.name,
                "group_index": group_idx,
                "status": "completed" if result.get("success") else "failed",
                "started_at": group_start.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "execution_time": result.get("execution_time", 0),
                "result": {"success": result.get("success")},
                "error": result.get("error"),
                "parallel": False,
            })

            logger.info(
                f"[deep_path_node] Step {step.name} "
                f"{'completed' if result.get('success') else 'failed'}"
            )

        # 그룹 완료 이벤트
        group_complete_event = StreamingEvent(
            event="deep_group_complete",
            data={
                "group_index": group_idx,
                "completed_tasks": len(group),
                "successful": sum(
                    1 for s in group
                    if all_results.get(s.step_id, {}).get("success", False)
                ),
            },
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(group_complete_event.model_dump())

    # =========================================================================
    # 4. 결과 종합
    # =========================================================================
    successful_steps = sum(
        1 for r in all_results.values()
        if r.get("success", False)
    )
    total_steps = len(all_results)

    # 진행 상황 이벤트: 결과 종합 중 (70%)
    progress_aggregating = create_progress_event(
        step=ProgressStep.EXECUTING,
        percentage=70,
        message="결과를 종합하고 있습니다...",
        execution_path="deep",
        step_details={
            "steps_executed": total_steps,
            "successful_steps": successful_steps,
        },
    )
    streaming_events.append(progress_aggregating.model_dump())

    # 최종 응답 집계
    aggregated_response = _aggregate_deep_results(all_results, user_message)

    complete_event = StreamingEvent(
        event="deep_path_complete",
        data={
            "steps_executed": total_steps,
            "steps_successful": successful_steps,
            "total_groups": len(execution_groups),
            "total_tool_calls": total_tool_calls,
            "total_tokens": total_tokens,
            "all_success": successful_steps == total_steps,
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(complete_event.model_dump())

    logger.info(
        f"[deep_path_node] Completed: {successful_steps}/{total_steps} steps successful, "
        f"{len(execution_groups)} groups, {total_tokens} tokens"
    )

    return {
        "workflow_results": {
            "deep_path_results": all_results,
            "plan": plan.to_dict(),
            "aggregated_response": aggregated_response,
            "execution_groups": len(execution_groups),
        },
        "final_response": aggregated_response,
        "response_metadata": {
            "path": "deep",
            "steps_executed": total_steps,
            "steps_successful": successful_steps,
            "total_groups": len(execution_groups),
            "total_tool_calls": total_tool_calls,
            "total_tokens": total_tokens,
        },
        "execution_logs": execution_logs,
        "streaming_events": streaming_events,
        "total_tool_calls": state.get("total_tool_calls", 0) + total_tool_calls,
    }


def deep_path_node_sync(state: ExtendedMasterAgentState) -> Dict[str, Any]:
    """Deep Path 노드 (동기 버전)"""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 이미 이벤트 루프가 실행 중인 경우
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, deep_path_node(state))
                return future.result()
        else:
            return loop.run_until_complete(deep_path_node(state))
    except RuntimeError:
        return asyncio.run(deep_path_node(state))


# =============================================================================
# 결과 집계 함수 (Phase 7)
# =============================================================================

def _aggregate_deep_results(
    results: Dict[str, Any],
    user_message: str,
) -> str:
    """
    Deep Path 결과 집계

    여러 단계의 결과를 하나의 응답으로 종합합니다.

    Args:
        results: 모든 단계 결과 {step_id: result_dict}
        user_message: 원본 사용자 메시지

    Returns:
        종합된 응답 문자열
    """
    parts = []

    # 성공한 결과들만 수집
    successful_results = {
        k: v for k, v in results.items()
        if v.get("success", False) and v.get("data")
    }

    if not successful_results:
        # 모든 단계 실패
        failed_steps = [
            f"- {v.get('step_name', k)}: {v.get('error', 'Unknown error')}"
            for k, v in results.items()
        ]
        return f"요청을 처리하는 중 오류가 발생했습니다:\n" + "\n".join(failed_steps)

    # 결과 유형별 분류 및 집계
    search_results = []
    analysis_results = []
    comparison_results = []
    other_results = []

    for step_id, result in successful_results.items():
        data = result.get("data", {})
        step_name = result.get("step_name", step_id)

        # 검색 결과
        if "search" in step_id.lower() or "rag" in step_name.lower():
            if data.get("answer"):
                search_results.append(data["answer"])
            elif data.get("results"):
                search_results.append(str(data["results"]))

        # 분석 결과
        elif "analysis" in step_id.lower() or "analyze" in step_name.lower():
            if data.get("summary"):
                analysis_results.append(f"**{step_name} 분석 결과:**\n{data['summary']}")
            elif data.get("analysis"):
                analysis_results.append(f"**{step_name}:**\n{data['analysis']}")

        # 비교 결과
        elif "compare" in step_id.lower() or "comparison" in step_name.lower():
            if data.get("differences"):
                comparison_results.append(f"**차이점:** {data['differences']}")
            if data.get("similarities"):
                comparison_results.append(f"**공통점:** {data['similarities']}")

        # 리스크 평가
        elif "risk" in step_id.lower():
            if data.get("risks"):
                risks = data["risks"]
                if isinstance(risks, list):
                    risks_text = "\n".join(f"- {r}" for r in risks)
                else:
                    risks_text = str(risks)
                analysis_results.append(f"**리스크 평가:**\n{risks_text}")

        # 기타
        else:
            if isinstance(data, dict):
                # 주요 필드 추출
                for key in ["answer", "result", "summary", "output", "response"]:
                    if data.get(key):
                        other_results.append(str(data[key]))
                        break
            elif data:
                other_results.append(str(data))

    # 결과 조합
    if search_results:
        parts.append("## 검색 결과\n" + "\n\n".join(search_results))

    if analysis_results:
        parts.append("## 분석 결과\n" + "\n\n".join(analysis_results))

    if comparison_results:
        parts.append("## 비교 결과\n" + "\n\n".join(comparison_results))

    if other_results:
        if len(parts) > 0:
            parts.append("## 추가 정보\n" + "\n\n".join(other_results))
        else:
            parts.extend(other_results)

    if not parts:
        return "요청을 처리했지만 표시할 결과가 없습니다."

    return "\n\n".join(parts)


# =============================================================================
# 계획 수립 함수
# =============================================================================

async def _create_deep_plan(
    user_message: str,
    intent_dict: Dict[str, Any],
    attachments: List[Dict[str, Any]],
) -> DeepPlan:
    """
    DeepPlan 생성

    복합 요청을 분석하여 실행 계획을 수립합니다.

    분석 휴리스틱:
    1. 다중 첨부 → 각 문서 분석 + 비교
    2. "~하고 ~해줘" → 순차 실행
    3. "비교해줘" → 각 대상 분석 → 비교 종합

    Args:
        user_message: 사용자 메시지
        intent_dict: Intent 딕셔너리
        attachments: 첨부 파일 목록

    Returns:
        DeepPlan 객체
    """
    plan_id = str(uuid.uuid4())[:8]
    steps: List[ExecutionStep] = []

    # 1. 다중 첨부 파일 처리 (병렬 가능)
    if len(attachments) >= 2:
        # 각 문서 분석 (병렬 실행 가능 - 의존성 없음)
        for i, attachment in enumerate(attachments[:MAX_STEPS - 1]):
            step_id = f"doc_analysis_{i}"
            steps.append(ExecutionStep(
                step_id=step_id,
                step_type="workflow",
                name="document_workflow",
                inputs={"document_index": i},
                priority=i,
                depends_on=[],  # 의존성 없음 → 병렬 실행 가능
            ))

        # 비교/종합 단계 (이전 분석 완료 후)
        steps.append(ExecutionStep(
            step_id="comparison",
            step_type="workflow",
            name="document_workflow",
            inputs={"analysis_type": "comparison"},
            depends_on=[f"doc_analysis_{i}" for i in range(min(len(attachments), MAX_STEPS - 1))],
            priority=len(steps),
        ))

    # 2. 복합 요청 키워드 분석
    elif _has_multi_request_keywords(user_message):
        # 분석 → 생성 순서
        if "분석" in user_message and ("생성" in user_message or "만들어" in user_message):
            steps.append(ExecutionStep(
                step_id="analysis",
                step_type="workflow",
                name="document_workflow" if attachments else "rag_workflow",
                inputs={},
                priority=0,
                depends_on=[],
            ))
            steps.append(ExecutionStep(
                step_id="generation",
                step_type="workflow",
                name="rag_workflow",
                inputs={"generation_mode": True},
                depends_on=["analysis"],
                priority=1,
            ))

        # 리스크 평가 + 수정안
        elif "리스크" in user_message and ("수정" in user_message or "개선" in user_message):
            steps.append(ExecutionStep(
                step_id="risk_assessment",
                step_type="workflow",
                name="risk_workflow",
                inputs={},
                priority=0,
                depends_on=[],
            ))
            steps.append(ExecutionStep(
                step_id="suggestion",
                step_type="workflow",
                name="rag_workflow",
                inputs={"suggestion_mode": True},
                depends_on=["risk_assessment"],
                priority=1,
            ))

        # 검토 + 작성
        elif ("검토" in user_message or "분석" in user_message) and ("작성" in user_message or "제시" in user_message):
            steps.append(ExecutionStep(
                step_id="review",
                step_type="workflow",
                name="document_workflow" if attachments else "rag_workflow",
                inputs={},
                priority=0,
                depends_on=[],
            ))
            steps.append(ExecutionStep(
                step_id="drafting",
                step_type="workflow",
                name="rag_workflow",
                inputs={"drafting_mode": True},
                depends_on=["review"],
                priority=1,
            ))

        # 판례 + 법령 동시 검색 (병렬 가능)
        elif "판례" in user_message and "법령" in user_message:
            steps.append(ExecutionStep(
                step_id="search_precedents",
                step_type="tool",
                name="search_precedents",
                inputs={"query": user_message, "top_k": 5},
                priority=0,
                depends_on=[],  # 병렬 가능
            ))
            steps.append(ExecutionStep(
                step_id="search_statutes",
                step_type="tool",
                name="search_statutes",
                inputs={"query": user_message},
                priority=0,
                depends_on=[],  # 병렬 가능
            ))
            # 종합 단계
            steps.append(ExecutionStep(
                step_id="synthesis",
                step_type="workflow",
                name="rag_workflow",
                inputs={"synthesis_mode": True},
                depends_on=["search_precedents", "search_statutes"],
                priority=1,
            ))

        else:
            # 기본: 분석 후 응답
            steps.append(ExecutionStep(
                step_id="main_analysis",
                step_type="workflow",
                name=_get_workflow_from_intent(intent_dict),
                inputs={},
                priority=0,
                depends_on=[],
            ))

    # 3. 비교 요청 처리
    elif "비교" in user_message:
        # 첨부 파일이 있으면 문서 비교
        if attachments:
            for i, _ in enumerate(attachments[:2]):
                steps.append(ExecutionStep(
                    step_id=f"analyze_{i}",
                    step_type="workflow",
                    name="document_workflow",
                    inputs={"document_index": i},
                    priority=i,
                    depends_on=[],  # 병렬 가능
                ))
            steps.append(ExecutionStep(
                step_id="compare",
                step_type="workflow",
                name="document_workflow",
                inputs={"analysis_type": "comparison"},
                depends_on=[f"analyze_{i}" for i in range(min(len(attachments), 2))],
                priority=2,
            ))
        else:
            # RAG 기반 비교
            steps.append(ExecutionStep(
                step_id="comparison",
                step_type="workflow",
                name="rag_workflow",
                inputs={"analysis_type": "comparison"},
                priority=0,
                depends_on=[],
            ))

    # 4. 기본 케이스
    else:
        workflow = _get_workflow_from_intent(intent_dict)
        steps.append(ExecutionStep(
            step_id="main",
            step_type="workflow",
            name=workflow,
            inputs={},
            priority=0,
            depends_on=[],
        ))

    # 단계 수 제한
    steps = steps[:MAX_STEPS]

    return DeepPlan(
        plan_id=plan_id,
        steps=steps,
        parallel_groups=[],  # build_execution_groups에서 채워짐
        total_steps=len(steps),
        estimated_time=len(steps) * 3.0,  # 단계당 3초 예상
    )


def _has_multi_request_keywords(message: str) -> bool:
    """복합 요청 키워드 확인"""
    keywords = ["그리고", "한 뒤", "다음에", "후에", "하고", "한 후", "및", "또한"]
    return any(kw in message for kw in keywords)


def _get_workflow_from_intent(intent_dict: Dict[str, Any]) -> str:
    """Intent에서 워크플로우 추출"""
    category = intent_dict.get("category", "QUERY")
    workflows = intent_dict.get("suggested_workflows", [])

    if workflows:
        return workflows[0]

    category_map = {
        "DOCUMENT_ANALYSIS": "document_workflow",
        "CASE_ANALYSIS": "case_workflow",
        "RISK_ASSESSMENT": "risk_workflow",
        "COMPARISON": "document_workflow",
        "SEARCH": "rag_workflow",
        "QUERY": "rag_workflow",
    }

    return category_map.get(category, "rag_workflow")


def _prepare_step_inputs(
    step: ExecutionStep,
    previous_results: Dict[str, Any],
    user_message: str,
    attachments: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    단계 입력 준비

    이전 단계 결과를 입력에 주입합니다.
    """
    inputs = dict(step.inputs) if step.inputs else {}
    inputs["user_message"] = user_message
    inputs["query"] = user_message

    # 이전 단계 결과 추가 (의존성 주입)
    depends_on = step.depends_on if hasattr(step, 'depends_on') and step.depends_on else []
    if depends_on:
        inputs["previous_results"] = {}
        for dep_id in depends_on:
            if dep_id in previous_results:
                dep_result = previous_results[dep_id]
                if dep_result.get("success") and dep_result.get("data"):
                    inputs["previous_results"][dep_id] = dep_result["data"]
                    # 컨텍스트로도 주입
                    inputs[f"context_{dep_id}"] = dep_result["data"]

    # 첨부 파일 처리
    if attachments:
        doc_index = inputs.get("document_index", 0)
        if doc_index < len(attachments):
            attachment = attachments[doc_index]
            if "content" in attachment:
                # WorkflowExecutor가 "content" 또는 "text" 키를 찾으므로 "content"로 설정
                inputs["content"] = attachment["content"]
            if "filename" in attachment:
                inputs["filename"] = attachment["filename"]

    return inputs
