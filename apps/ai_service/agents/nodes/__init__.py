"""
Agent Hub - Master Agent Nodes

Phase 5: Master Agent LangGraph 노드 정의

노드 목록:
- classify_intent_node: 의도 분류 노드
- plan_execution_node: 실행 계획 수립 노드
- execute_workflows_node: 워크플로우 실행 노드
- aggregate_results_node: 결과 집계 노드
- generate_response_node: 응답 생성 노드

사용:
    from apps.ai_service.agents.nodes import (
        classify_intent_node,
        plan_execution_node,
        execute_workflows_node,
        aggregate_results_node,
        generate_response_node,
    )

LangGraph 그래프 생성 예시:
    from langgraph.graph import StateGraph, START, END
    from apps.ai_service.agents.states.master_agent_state import MasterAgentState
    from apps.ai_service.agents.nodes import (
        classify_intent_node,
        plan_execution_node,
        execute_workflows_node,
        aggregate_results_node,
        generate_response_node,
    )

    workflow = StateGraph(MasterAgentState)

    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("plan_execution", plan_execution_node)
    workflow.add_node("execute_workflows", execute_workflows_node)
    workflow.add_node("aggregate_results", aggregate_results_node)
    workflow.add_node("generate_response", generate_response_node)

    workflow.add_edge(START, "classify_intent")
    workflow.add_edge("classify_intent", "plan_execution")
    workflow.add_edge("plan_execution", "execute_workflows")
    workflow.add_edge("execute_workflows", "aggregate_results")
    workflow.add_edge("aggregate_results", "generate_response")
    workflow.add_edge("generate_response", END)

    graph = workflow.compile()
"""

# Async 노드 (권장)
from apps.ai_service.agents.nodes.classify_intent_node import (
    classify_intent_node,
    classify_intent_node_sync,
)
from apps.ai_service.agents.nodes.plan_execution_node import (
    plan_execution_node,
    plan_execution_node_sync,
)
from apps.ai_service.agents.nodes.execute_workflows_node import (
    execute_workflows_node,
    execute_workflows_node_sync,
)
from apps.ai_service.agents.nodes.aggregate_results_node import (
    aggregate_results_node,
    aggregate_results_node_sync,
)
from apps.ai_service.agents.nodes.generate_response_node import (
    generate_response_node,
    generate_response_node_sync,
    ResponseFormat,
)


__all__ = [
    # Async 노드 (LangGraph async 실행 시 사용)
    "classify_intent_node",
    "plan_execution_node",
    "execute_workflows_node",
    "aggregate_results_node",
    "generate_response_node",
    # Sync 노드 (LangGraph sync 실행 시 사용)
    "classify_intent_node_sync",
    "plan_execution_node_sync",
    "execute_workflows_node_sync",
    "aggregate_results_node_sync",
    "generate_response_node_sync",
    # 타입
    "ResponseFormat",
]
