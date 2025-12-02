"""
Aggregate Results Node - 결과 집계 노드

Phase 5: Agent Hub - Master Agent Graph Node

설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.3.3

역할:
- 워크플로우 실행 결과 집계
- 에러 처리 및 부분 결과 병합
- 결과 구조화 및 메타데이터 생성
"""

from datetime import datetime
import logging
from typing import Dict, Any, List, Optional

from apps.ai_service.agents.states.master_agent_state import (
    MasterAgentState,
    StreamingEvent,
    Intent,
    IntentCategory,
)

logger = logging.getLogger(__name__)


async def aggregate_results_node(state: MasterAgentState) -> MasterAgentState:
    """
    결과 집계 노드

    워크플로우와 도구의 실행 결과를 집계하고 구조화합니다.

    Args:
        state: MasterAgentState (현재 상태)

    Returns:
        업데이트된 MasterAgentState

    State 업데이트:
        - workflow_results: 집계된 워크플로우 결과
        - tool_results: 집계된 도구 결과
        - response_metadata: 응답 생성을 위한 메타데이터
        - streaming_events: 집계 완료 이벤트 추가

    이벤트 발생:
        1. results_aggregated: 결과 집계 완료
        2. partial_results_warning: 일부 결과만 성공한 경우
    """
    logger.info("[aggregate_results_node] Starting result aggregation")

    try:
        workflow_results = state.get("workflow_results", {})
        tool_results = state.get("tool_results", {})
        streaming_events = list(state.get("streaming_events", []))

        # 1. 실행 결과 분석
        analysis = _analyze_results(workflow_results, tool_results)

        logger.info(
            f"[aggregate_results_node] Analysis: "
            f"total={analysis['total']}, success={analysis['success_count']}, "
            f"failed={analysis['failed_count']}"
        )

        # 2. 부분 실패 경고
        if analysis["failed_count"] > 0 and analysis["success_count"] > 0:
            warning_event = StreamingEvent(
                event="partial_results_warning",
                data={
                    "message": f"일부 작업이 실패했습니다. "
                               f"({analysis['success_count']}/{analysis['total']} 성공)",
                    "failed_items": analysis["failed_items"],
                    "success_items": analysis["success_items"],
                },
                timestamp=datetime.now().isoformat(),
            )
            streaming_events.append(warning_event.model_dump())

        # 3. 전체 실패 처리
        if analysis["total"] > 0 and analysis["success_count"] == 0:
            logger.warning("[aggregate_results_node] All tasks failed")
            state["response_metadata"] = {
                "status": "failed",
                "message": "모든 작업이 실패했습니다.",
                "errors": analysis["failed_items"],
            }
            state["streaming_events"] = streaming_events
            return state

        # 4. 결과 집계 및 구조화
        aggregated = _aggregate_and_structure_results(
            workflow_results=workflow_results,
            tool_results=tool_results,
            intent_dict=state.get("intent"),
        )

        # 5. 응답 메타데이터 생성
        execution_time = _calculate_execution_time(state)
        response_metadata = {
            "status": "success" if analysis["failed_count"] == 0 else "partial",
            "total_steps": analysis["total"],
            "successful_steps": analysis["success_count"],
            "failed_steps": analysis["failed_count"],
            "execution_time": execution_time,
            "workflows_executed": list(workflow_results.keys()),
            "tools_executed": list(tool_results.keys()),
            "aggregated_summary": _create_summary(aggregated),
        }

        # 6. 집계 완료 이벤트
        aggregated_event = StreamingEvent(
            event="results_aggregated",
            data={
                "status": response_metadata["status"],
                "total_results": analysis["total"],
                "summary": response_metadata["aggregated_summary"],
            },
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(aggregated_event.model_dump())

        # 7. 상태 업데이트
        state["workflow_results"] = aggregated.get("workflows", {})
        state["tool_results"] = aggregated.get("tools", {})
        state["response_metadata"] = response_metadata
        state["streaming_events"] = streaming_events

        logger.info("[aggregate_results_node] Completed successfully")

        return state

    except Exception as e:
        logger.error(f"[aggregate_results_node] Error: {e}", exc_info=True)

        # 에러 이벤트
        error_event = StreamingEvent(
            event="error",
            data={
                "step": "aggregate_results",
                "error": str(e),
                "message": "결과 집계 중 오류가 발생했습니다.",
            },
            timestamp=datetime.now().isoformat(),
        )

        streaming_events = list(state.get("streaming_events", []))
        streaming_events.append(error_event.model_dump())

        # 에러 로그 추가
        errors = list(state.get("errors", []))
        errors.append({
            "step": "aggregate_results",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })

        state["response_metadata"] = {
            "status": "error",
            "error": str(e),
        }
        state["streaming_events"] = streaming_events
        state["errors"] = errors

        return state


def _analyze_results(
    workflow_results: Dict[str, Any],
    tool_results: Dict[str, Any],
) -> Dict[str, Any]:
    """
    실행 결과 분석

    Args:
        workflow_results: 워크플로우 결과
        tool_results: 도구 결과

    Returns:
        분석 결과 딕셔너리
    """
    success_items = []
    failed_items = []

    # 워크플로우 결과 분석
    for step_id, result in workflow_results.items():
        if isinstance(result, dict) and result.get("status") == "failed":
            failed_items.append({
                "type": "workflow",
                "id": step_id,
                "error": result.get("error", "Unknown error"),
            })
        elif isinstance(result, dict) and result.get("error"):
            failed_items.append({
                "type": "workflow",
                "id": step_id,
                "error": result.get("error"),
            })
        else:
            success_items.append({
                "type": "workflow",
                "id": step_id,
            })

    # 도구 결과 분석
    for tool_id, result in tool_results.items():
        if isinstance(result, dict) and result.get("status") == "failed":
            failed_items.append({
                "type": "tool",
                "id": tool_id,
                "error": result.get("error", "Unknown error"),
            })
        elif isinstance(result, dict) and result.get("error"):
            failed_items.append({
                "type": "tool",
                "id": tool_id,
                "error": result.get("error"),
            })
        else:
            success_items.append({
                "type": "tool",
                "id": tool_id,
            })

    total = len(workflow_results) + len(tool_results)

    return {
        "total": total,
        "success_count": len(success_items),
        "failed_count": len(failed_items),
        "success_items": success_items,
        "failed_items": failed_items,
    }


def _aggregate_and_structure_results(
    workflow_results: Dict[str, Any],
    tool_results: Dict[str, Any],
    intent_dict: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    결과 집계 및 구조화

    의도에 따라 결과를 적절하게 구조화합니다.

    Args:
        workflow_results: 워크플로우 결과
        tool_results: 도구 결과
        intent_dict: 의도 딕셔너리

    Returns:
        구조화된 결과
    """
    aggregated = {
        "workflows": {},
        "tools": {},
        "combined": {},
    }

    # 실패한 결과 필터링 (성공한 결과만 집계)
    for step_id, result in workflow_results.items():
        if isinstance(result, dict) and result.get("status") == "failed":
            continue
        aggregated["workflows"][step_id] = _extract_key_results(result)

    for tool_id, result in tool_results.items():
        if isinstance(result, dict) and result.get("status") == "failed":
            continue
        aggregated["tools"][tool_id] = _extract_key_results(result)

    # 의도에 따른 결과 병합
    if intent_dict:
        intent = Intent(**intent_dict)
        aggregated["combined"] = _merge_by_intent(
            aggregated["workflows"],
            aggregated["tools"],
            intent,
        )

    return aggregated


def _extract_key_results(result: Any) -> Dict[str, Any]:
    """
    주요 결과 추출

    Args:
        result: 실행 결과

    Returns:
        주요 결과 딕셔너리
    """
    if not isinstance(result, dict):
        return {"value": result}

    # 주요 키 추출
    key_fields = [
        "answer", "response", "result", "output",
        "summary", "analysis", "content", "text",
        "risks", "issues", "recommendations",
        "documents", "cases", "statutes",
        "sources", "confidence",  # RAG 워크플로우 결과 포함
    ]

    extracted = {}
    for key in key_fields:
        if key in result:
            extracted[key] = result[key]

    # 주요 키가 없으면 전체 반환 (error, status 제외)
    if not extracted:
        extracted = {
            k: v for k, v in result.items()
            if k not in ["error", "status", "metadata"]
        }

    return extracted


def _merge_by_intent(
    workflow_results: Dict[str, Any],
    tool_results: Dict[str, Any],
    intent: Intent,
) -> Dict[str, Any]:
    """
    의도에 따른 결과 병합

    Args:
        workflow_results: 워크플로우 결과
        tool_results: 도구 결과
        intent: 분류된 의도

    Returns:
        병합된 결과
    """
    category = intent.category

    if category == IntentCategory.QUERY:
        # RAG 응답 병합
        return _merge_query_results(workflow_results)

    elif category == IntentCategory.DOCUMENT_ANALYSIS:
        # 문서 분석 결과 병합
        return _merge_document_results(workflow_results)

    elif category == IntentCategory.CASE_ANALYSIS:
        # 사건 분석 결과 병합
        return _merge_case_results(workflow_results)

    elif category == IntentCategory.RISK_ASSESSMENT:
        # 리스크 평가 결과 병합
        return _merge_risk_results(workflow_results)

    elif category == IntentCategory.COMPARISON:
        # 비교 결과 병합
        return _merge_comparison_results(workflow_results)

    elif category == IntentCategory.SEARCH:
        # 검색 결과 병합
        return _merge_search_results(tool_results)

    elif category == IntentCategory.MULTI_TASK:
        # 복합 작업 결과 병합
        return {
            "workflows": workflow_results,
            "tools": tool_results,
        }

    else:
        # 기본 병합
        return {
            **workflow_results,
            **tool_results,
        }


def _merge_query_results(workflow_results: Dict[str, Any]) -> Dict[str, Any]:
    """RAG 질의응답 결과 병합"""
    merged = {
        "answer": "",
        "sources": [],
        "confidence": 0.0,
    }

    for result in workflow_results.values():
        if "answer" in result:
            merged["answer"] = result["answer"]
        if "response" in result:
            merged["answer"] = result["response"]
        if "sources" in result:
            merged["sources"].extend(result.get("sources", []))
        if "confidence" in result:
            merged["confidence"] = result["confidence"]

    return merged


def _merge_document_results(workflow_results: Dict[str, Any]) -> Dict[str, Any]:
    """문서 분석 결과 병합"""
    merged = {
        "summary": "",
        "document_type": "",
        "clauses": [],
        "key_points": [],
        "analysis": {},
    }

    for result in workflow_results.values():
        for key in merged.keys():
            if key in result:
                if isinstance(merged[key], list):
                    merged[key].extend(result.get(key, []))
                elif isinstance(merged[key], dict):
                    merged[key].update(result.get(key, {}))
                else:
                    merged[key] = result[key]

    return merged


def _merge_case_results(workflow_results: Dict[str, Any]) -> Dict[str, Any]:
    """사건 분석 결과 병합"""
    merged = {
        "parties": [],
        "issues": [],
        "facts": [],
        "holdings": [],
        "analysis": {},
    }

    for result in workflow_results.values():
        for key in merged.keys():
            if key in result:
                if isinstance(merged[key], list):
                    merged[key].extend(result.get(key, []))
                elif isinstance(merged[key], dict):
                    merged[key].update(result.get(key, {}))

    return merged


def _merge_risk_results(workflow_results: Dict[str, Any]) -> Dict[str, Any]:
    """리스크 평가 결과 병합"""
    merged = {
        "risks": [],
        "overall_risk_level": "",
        "recommendations": [],
        "mitigation_strategies": [],
    }

    for result in workflow_results.values():
        if "risks" in result:
            merged["risks"].extend(result.get("risks", []))
        if "overall_risk_level" in result:
            merged["overall_risk_level"] = result["overall_risk_level"]
        if "recommendations" in result:
            merged["recommendations"].extend(result.get("recommendations", []))

    return merged


def _merge_comparison_results(workflow_results: Dict[str, Any]) -> Dict[str, Any]:
    """비교 결과 병합"""
    merged = {
        "comparisons": [],
        "best_model": "",
        "metrics": {},
    }

    for result in workflow_results.values():
        if "comparisons" in result:
            merged["comparisons"].extend(result.get("comparisons", []))
        if "best_model" in result:
            merged["best_model"] = result["best_model"]
        if "metrics" in result:
            merged["metrics"].update(result.get("metrics", {}))

    return merged


def _merge_search_results(tool_results: Dict[str, Any]) -> Dict[str, Any]:
    """검색 결과 병합"""
    merged = {
        "results": [],
        "total_count": 0,
    }

    for result in tool_results.values():
        if "results" in result:
            merged["results"].extend(result.get("results", []))
        if "items" in result:
            merged["results"].extend(result.get("items", []))

    merged["total_count"] = len(merged["results"])

    return merged


def _calculate_execution_time(state: MasterAgentState) -> float:
    """
    실행 시간 계산

    Args:
        state: MasterAgentState

    Returns:
        실행 시간 (초)
    """
    try:
        start_time_str = state.get("start_time", "")
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
            return (datetime.now() - start_time).total_seconds()
    except Exception:
        pass

    return 0.0


def _create_summary(aggregated: Dict[str, Any]) -> str:
    """
    집계 결과 요약 생성

    Args:
        aggregated: 집계된 결과

    Returns:
        요약 문자열
    """
    parts = []

    workflow_count = len(aggregated.get("workflows", {}))
    tool_count = len(aggregated.get("tools", {}))

    if workflow_count > 0:
        parts.append(f"{workflow_count}개 워크플로우 실행 완료")

    if tool_count > 0:
        parts.append(f"{tool_count}개 도구 실행 완료")

    return ", ".join(parts) if parts else "결과 없음"


def aggregate_results_node_sync(state: MasterAgentState) -> MasterAgentState:
    """
    결과 집계 노드 (동기 버전)
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                aggregate_results_node(state)
            )
            return future.result()
    except RuntimeError:
        return asyncio.run(aggregate_results_node(state))
