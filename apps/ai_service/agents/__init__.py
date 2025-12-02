"""
Agent Hub - Master Agent Orchestrator

Phase 5: Agent Hub 통합 AI 법률 어시스턴트

핵심 컴포넌트:
- MasterAgentState: Master Agent 상태 정의
- IntentClassifier: 사용자 의도 분류
- WorkflowRouter: 워크플로우 라우팅
- MasterAgent: 통합 오케스트레이터 (LangGraph)

사용:
    from apps.ai_service.agents import (
        create_master_agent_graph,
        MasterAgent,
        run_master_agent,
        IntentClassifier,
    )
    from apps.ai_service.agents.states import MasterAgentState, Intent

참고: docs/AGENT_HUB_DESIGN.md
"""

# 지연 import로 순환 참조 방지

def get_master_agent():
    """Master Agent 인스턴스 반환"""
    from apps.ai_service.agents.master_agent import MasterAgent
    return MasterAgent()


def create_master_agent_graph(use_checkpointing: bool = True, use_async: bool = True):
    """
    Master Agent Graph 생성

    Args:
        use_checkpointing: MemorySaver 사용 여부
        use_async: 비동기 노드 사용 여부

    Returns:
        컴파일된 StateGraph
    """
    from apps.ai_service.agents.master_agent import create_master_agent_graph as _create
    return _create(use_checkpointing=use_checkpointing, use_async=use_async)


def get_intent_classifier():
    """IntentClassifier 인스턴스 반환"""
    from apps.ai_service.agents.intent_classifier import IntentClassifier
    return IntentClassifier()


def get_workflow_router():
    """WorkflowRouter 인스턴스 반환"""
    from apps.ai_service.agents.workflow_router import WorkflowRouter
    return WorkflowRouter()


# 클래스 직접 import (타입 힌트용)
from apps.ai_service.agents.intent_classifier import (
    IntentClassifier,
    INTENT_CATEGORIES,
    CATEGORY_WORKFLOW_MAP,
)

from apps.ai_service.agents.workflow_router import (
    WorkflowRouter,
    INTENT_WORKFLOW_MAP,
    WORKFLOW_REGISTRY,
    TOOL_METADATA,
    ExecutionPriority,
)

from apps.ai_service.agents.workflow_executor import (
    WorkflowExecutor,
    WorkflowResult,
    WorkflowLoadError,
    WorkflowExecutionError,
    get_workflow_executor,
    execute_workflow,
)

from apps.ai_service.agents.master_agent import (
    MasterAgent,
    run_master_agent,
    run_master_agent_with_sse,
    get_graph_mermaid,
)


__all__ = [
    # Master Agent
    "get_master_agent",
    "create_master_agent_graph",
    "MasterAgent",
    "run_master_agent",
    "run_master_agent_with_sse",
    "get_graph_mermaid",
    # Intent Classifier
    "get_intent_classifier",
    "IntentClassifier",
    "INTENT_CATEGORIES",
    "CATEGORY_WORKFLOW_MAP",
    # Workflow Router
    "get_workflow_router",
    "WorkflowRouter",
    "INTENT_WORKFLOW_MAP",
    "WORKFLOW_REGISTRY",
    "TOOL_METADATA",
    "ExecutionPriority",
    # Workflow Executor
    "get_workflow_executor",
    "WorkflowExecutor",
    "WorkflowResult",
    "WorkflowLoadError",
    "WorkflowExecutionError",
    "execute_workflow",
]
