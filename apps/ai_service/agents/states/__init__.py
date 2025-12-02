"""
Agent Hub State Definitions

Phase 5: Master Agent 상태 정의

상태 정의:
- UserContext: 사용자 컨텍스트 (JWT에서 추출)
- Intent: 의도 분류 결과
- ExecutionPlan: 실행 계획
- MasterAgentState: Master Agent 전체 상태

사용:
    from apps.ai_service.agents.states import (
        MasterAgentState,
        UserContext,
        Intent,
        ExecutionPlan,
    )
"""

from apps.ai_service.agents.states.master_agent_state import (
    # User Context
    UserContext,

    # Intent Classification
    IntentCategory,
    Intent,

    # Execution Plan
    WorkflowStep,
    ToolCall,
    ExecutionPlan,

    # Master Agent State
    MasterAgentState,
    StreamingEvent,
    ExecutionLog,

    # Helper functions
    create_initial_master_agent_state,
)

__all__ = [
    # User Context
    "UserContext",

    # Intent Classification
    "IntentCategory",
    "Intent",

    # Execution Plan
    "WorkflowStep",
    "ToolCall",
    "ExecutionPlan",

    # Master Agent State
    "MasterAgentState",
    "StreamingEvent",
    "ExecutionLog",

    # Helper functions
    "create_initial_master_agent_state",
]
