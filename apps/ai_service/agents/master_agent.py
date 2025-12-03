"""
Master Agent - LangGraph 기반 통합 오케스트레이터

Phase 5: Agent Hub - Master Agent Graph 조립

설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.3.2

구성:
1. create_master_agent_graph() - StateGraph 생성 및 노드/엣지 연결
2. MasterAgent 클래스 - 편의 래퍼
3. run_master_agent() - 스트리밍 실행 함수

워크플로우:
    START
      ↓
    classify_intent       # 의도 분류
      ↓
    [조건부 엣지]         # clarification_needed 시 ask_clarification
      ↓
    plan_execution        # 실행 계획 수립
      ↓
    execute_workflows     # 워크플로우 실행
      ↓
    aggregate_results     # 결과 집계
      ↓
    generate_response     # 응답 생성
      ↓
    END
"""

from datetime import datetime
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from apps.ai_service.agents.states.master_agent_state import (
    MasterAgentState,
    UserContext,
    Intent,
    ExecutionPlan,
    StreamingEvent,
    create_initial_master_agent_state,
    create_anonymous_user_context,
    # Adaptive Agent 확장
    ExtendedMasterAgentState,
    create_initial_extended_state,
)
from apps.ai_service.agents.nodes import (
    classify_intent_node,
    plan_execution_node,
    execute_workflows_node,
    aggregate_results_node,
    generate_response_node,
    classify_intent_node_sync,
    plan_execution_node_sync,
    execute_workflows_node_sync,
    aggregate_results_node_sync,
    generate_response_node_sync,
    # Adaptive Agent 노드
    complexity_classifier_node,
    complexity_classifier_node_sync,
    route_by_complexity,
    # Fast Path (Adaptive Agent Phase 2)
    fast_path_node,
    fast_path_node_sync,
    # Medium Path (Adaptive Agent Phase 3)
    medium_path_node,
    medium_path_node_sync,
    # Deep Path (Adaptive Agent Phase 4)
    deep_path_node,
    deep_path_node_sync,
    # Thinking Path (Adaptive Agent Phase 6)
    thinking_path_node,
    thinking_path_node_sync,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 조건부 라우팅 함수
# =============================================================================

def should_ask_clarification(state: MasterAgentState) -> str:
    """
    clarification이 필요한지 확인하여 라우팅 결정

    Args:
        state: MasterAgentState

    Returns:
        "ask_clarification" 또는 "plan_execution"
    """
    intent_dict = state.get("intent")

    if intent_dict:
        # Intent 객체로 복원
        try:
            intent = Intent(**intent_dict)

            # clarification이 필요하고, 아직 응답받지 않은 경우
            if intent.clarification_needed:
                # 대화 기록에서 clarification 응답 확인
                conversation = state.get("conversation_history", [])
                # 마지막 메시지가 clarification 응답인지 확인
                # (구현 단순화를 위해 항상 진행)
                logger.info("[should_ask_clarification] Clarification needed but proceeding")

        except Exception as e:
            logger.warning(f"Error parsing intent: {e}")

    return "plan_execution"


def should_retry_on_error(state: MasterAgentState) -> str:
    """
    에러 발생 시 재시도 여부 결정

    Args:
        state: MasterAgentState

    Returns:
        "retry" 또는 "generate_response"
    """
    errors = state.get("errors", [])
    execution_plan = state.get("execution_plan")

    # 재시도 가능한 에러가 있고, 재시도 횟수가 제한 내인 경우
    if errors and len(errors) < 3:
        # 실행 계획이 있고, 일부 워크플로우만 실패한 경우
        if execution_plan:
            plan = ExecutionPlan(**execution_plan)
            workflow_results = state.get("workflow_results", {})

            # 성공한 워크플로우가 있으면 진행
            if workflow_results:
                return "generate_response"

    return "generate_response"


def has_executable_workflows(state: MasterAgentState) -> str:
    """
    실행 가능한 워크플로우가 있는지 확인

    Args:
        state: MasterAgentState

    Returns:
        "execute_workflows" 또는 "generate_response"
    """
    execution_plan = state.get("execution_plan")

    if execution_plan:
        plan = ExecutionPlan(**execution_plan)
        if plan.workflows or plan.tools:
            return "execute_workflows"

    # 실행할 것이 없으면 바로 응답 생성
    logger.info("[has_executable_workflows] No workflows to execute, skipping to response")
    return "generate_response"


# =============================================================================
# Ask Clarification 노드 (조건부 사용)
# =============================================================================

async def ask_clarification_node(state: MasterAgentState) -> MasterAgentState:
    """
    Clarification 요청 노드

    사용자에게 추가 정보를 요청합니다.
    이 노드는 실제로는 응답을 생성하고 대화를 중단합니다.

    Args:
        state: MasterAgentState

    Returns:
        업데이트된 MasterAgentState
    """
    logger.info("[ask_clarification_node] Requesting clarification from user")

    intent_dict = state.get("intent", {})
    questions = intent_dict.get("clarification_questions", [])

    # Clarification 메시지 생성
    if questions:
        message = "요청을 더 잘 이해하기 위해 몇 가지 확인이 필요합니다:\n\n"
        for i, q in enumerate(questions, 1):
            message += f"{i}. {q}\n"
    else:
        message = "요청 내용을 좀 더 구체적으로 말씀해 주시겠어요?"

    # 스트리밍 이벤트
    streaming_events = list(state.get("streaming_events", []))
    clarification_event = StreamingEvent(
        event="clarification_request",
        data={
            "message": message,
            "questions": questions,
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(clarification_event.model_dump())

    # 완료 이벤트 (clarification 응답 대기)
    complete_event = StreamingEvent(
        event="complete",
        data={
            "response": message,
            "format": "text",
            "status": "awaiting_clarification",
            "requires_input": True,
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(complete_event.model_dump())

    state["final_response"] = message
    state["streaming_events"] = streaming_events
    state["response_metadata"] = {
        "status": "awaiting_clarification",
        "requires_input": True,
    }

    return state


# =============================================================================
# Graph 생성 함수
# =============================================================================

def create_master_agent_graph(
    use_checkpointing: bool = True,
    use_async: bool = True,
) -> StateGraph:
    """
    Master Agent Graph 생성

    설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.3.2

    Args:
        use_checkpointing: MemorySaver 사용 여부 (대화 컨텍스트 유지)
        use_async: 비동기 노드 사용 여부

    Returns:
        컴파일된 StateGraph

    워크플로우:
        START
          ↓
        classify_intent
          ↓
        [조건부] → ask_clarification (clarification 필요시) → END
          ↓
        plan_execution
          ↓
        [조건부] → generate_response (실행할 것 없으면)
          ↓
        execute_workflows
          ↓
        aggregate_results
          ↓
        generate_response
          ↓
        END
    """
    logger.info(f"[create_master_agent_graph] Creating graph (async={use_async})")

    # StateGraph 생성
    workflow = StateGraph(MasterAgentState)

    # 노드 선택 (async vs sync)
    if use_async:
        intent_node = classify_intent_node
        plan_node = plan_execution_node
        execute_node = execute_workflows_node
        aggregate_node = aggregate_results_node
        response_node = generate_response_node
    else:
        intent_node = classify_intent_node_sync
        plan_node = plan_execution_node_sync
        execute_node = execute_workflows_node_sync
        aggregate_node = aggregate_results_node_sync
        response_node = generate_response_node_sync

    # =========================================================================
    # 노드 추가
    # =========================================================================
    workflow.add_node("classify_intent", intent_node)
    workflow.add_node("ask_clarification", ask_clarification_node)
    workflow.add_node("plan_execution", plan_node)
    workflow.add_node("execute_workflows", execute_node)
    workflow.add_node("aggregate_results", aggregate_node)
    workflow.add_node("generate_response", response_node)

    # =========================================================================
    # 엣지 연결
    # =========================================================================

    # START → classify_intent
    workflow.add_edge(START, "classify_intent")

    # classify_intent → [조건부] plan_execution 또는 ask_clarification
    # 현재는 항상 plan_execution으로 진행 (단순화)
    # TODO: clarification 처리 개선 시 조건부 엣지로 변경
    workflow.add_conditional_edges(
        "classify_intent",
        should_ask_clarification,
        {
            "plan_execution": "plan_execution",
            "ask_clarification": "ask_clarification",
        }
    )

    # ask_clarification → END (대화 중단, 사용자 입력 대기)
    workflow.add_edge("ask_clarification", END)

    # plan_execution → [조건부] execute_workflows 또는 generate_response
    workflow.add_conditional_edges(
        "plan_execution",
        has_executable_workflows,
        {
            "execute_workflows": "execute_workflows",
            "generate_response": "generate_response",
        }
    )

    # execute_workflows → aggregate_results
    workflow.add_edge("execute_workflows", "aggregate_results")

    # aggregate_results → generate_response
    workflow.add_edge("aggregate_results", "generate_response")

    # generate_response → END
    workflow.add_edge("generate_response", END)

    # =========================================================================
    # 체크포인팅 (대화 컨텍스트 유지)
    # =========================================================================
    checkpointer = None
    if use_checkpointing:
        checkpointer = MemorySaver()
        logger.info("[create_master_agent_graph] Checkpointing enabled")

    # 그래프 컴파일
    compiled_graph = workflow.compile(checkpointer=checkpointer)

    logger.info("[create_master_agent_graph] Graph compiled successfully")

    return compiled_graph


# =============================================================================
# Adaptive Master Agent Graph (Phase 1: Complexity-based Routing)
# =============================================================================

def create_adaptive_master_agent_graph(
    use_checkpointing: bool = True,
    use_async: bool = True,
) -> StateGraph:
    """
    Adaptive Master Agent Graph 생성 (Thinking Path 포함)

    복잡도 기반 4-way 분기를 지원하는 그래프입니다.

    Args:
        use_checkpointing: MemorySaver 사용 여부
        use_async: 비동기 노드 사용 여부

    Returns:
        컴파일된 StateGraph

    워크플로우:
        START
          ↓
        classify_complexity
          ↓
        [조건부 분기]
          ├─ fast → fast_path → generate_response
          ├─ medium → medium_path → generate_response
          ├─ deep → deep_path → generate_response
          └─ thinking → thinking_path → generate_response
          ↓
        END

    Note:
        StateGraph는 ExtendedMasterAgentState를 사용합니다.
        thinking_path_node 내부에서 Thinking 전용 필드들을 동적으로 추가합니다.
    """
    logger.info(f"[create_adaptive_master_agent_graph] Creating graph with Thinking Path (async={use_async})")

    workflow = StateGraph(ExtendedMasterAgentState)

    # 노드 선택
    if use_async:
        complexity_node = complexity_classifier_node
        fast_node = fast_path_node  # Phase 2: Fast Path 구현 완료
        medium_node = medium_path_node  # Phase 3: Medium Path 구현 완료
        deep_node = deep_path_node  # Phase 4: Deep Path 구현 완료
        thinking_node = thinking_path_node  # Phase 6: Thinking Path 구현 완료
        response_node = generate_response_node
    else:
        complexity_node = complexity_classifier_node_sync
        fast_node = fast_path_node_sync  # Phase 2: Fast Path 구현 완료
        medium_node = medium_path_node_sync  # Phase 3: Medium Path 구현 완료
        deep_node = deep_path_node_sync  # Phase 4: Deep Path 구현 완료
        thinking_node = thinking_path_node_sync  # Phase 6: Thinking Path 구현 완료
        response_node = generate_response_node_sync

    # =========================================================================
    # 노드 추가
    # =========================================================================
    workflow.add_node("classify_complexity", complexity_node)

    # Fast Path (Phase 2 구현 완료)
    workflow.add_node("fast_path", fast_node)

    # Medium Path (Phase 3 구현 완료)
    workflow.add_node("medium_path", medium_node)

    # Deep Path (Phase 4 구현 완료)
    workflow.add_node("deep_path", deep_node)

    # Thinking Path (Phase 6 구현 완료)
    workflow.add_node("thinking_path", thinking_node)

    workflow.add_node("generate_response", response_node)

    # =========================================================================
    # 엣지 연결
    # =========================================================================
    workflow.add_edge(START, "classify_complexity")

    # 4-way 분기 (Phase 6: thinking 추가)
    workflow.add_conditional_edges(
        "classify_complexity",
        route_by_complexity,
        {
            "fast": "fast_path",
            "medium": "medium_path",
            "deep": "deep_path",
            "thinking": "thinking_path",
        }
    )

    # 모든 경로 → generate_response
    workflow.add_edge("fast_path", "generate_response")
    workflow.add_edge("medium_path", "generate_response")
    workflow.add_edge("deep_path", "generate_response")
    workflow.add_edge("thinking_path", "generate_response")

    workflow.add_edge("generate_response", END)

    # 체크포인팅
    checkpointer = None
    if use_checkpointing:
        checkpointer = MemorySaver()

    compiled_graph = workflow.compile(checkpointer=checkpointer)

    logger.info("[create_adaptive_master_agent_graph] Graph compiled successfully with 4-way routing")

    return compiled_graph


# =============================================================================
# MasterAgent 클래스
# =============================================================================

class MasterAgent:
    """
    Master Agent 래퍼 클래스

    LangGraph 기반 Master Agent를 쉽게 사용하기 위한 래퍼입니다.

    사용 예시:
        agent = MasterAgent()

        # 단일 실행
        result = await agent.run("절도죄의 법정형은?")

        # 스트리밍 실행
        async for event in agent.stream("계약서를 분석해줘", attachments=[...]):
            print(event)
    """

    def __init__(
        self,
        use_checkpointing: bool = True,
        use_async: bool = True,
    ):
        """
        MasterAgent 초기화

        Args:
            use_checkpointing: MemorySaver 사용 여부
            use_async: 비동기 노드 사용 여부
        """
        self.use_checkpointing = use_checkpointing
        self.use_async = use_async
        self._graph = None

    @property
    def graph(self) -> StateGraph:
        """그래프 인스턴스 (지연 생성) - Adaptive Graph 사용"""
        if self._graph is None:
            # Phase 6: Adaptive Master Agent Graph 사용 (4-way 라우팅 포함)
            self._graph = create_adaptive_master_agent_graph(
                use_checkpointing=self.use_checkpointing,
                use_async=self.use_async,
            )
        return self._graph

    async def run(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_context: Optional[UserContext] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Master Agent 실행 (단일 응답)

        Args:
            message: 사용자 메시지
            session_id: 세션 ID
            user_context: 사용자 컨텍스트
            attachments: 첨부 파일 목록
            conversation_history: 대화 기록

        Returns:
            최종 상태 딕셔너리
        """
        # 초기 상태 생성 - Adaptive Agent용 ExtendedState 사용
        initial_state = create_initial_extended_state(
            user_message=message,
            session_id=session_id,
            user_context=user_context or create_anonymous_user_context(),
            attachments=attachments,
            conversation_history=conversation_history,
        )

        # 그래프 실행
        config = {}
        if session_id and self.use_checkpointing:
            config["configurable"] = {"thread_id": session_id}

        final_state = await self.graph.ainvoke(initial_state, config=config)

        return final_state

    async def stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_context: Optional[UserContext] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Master Agent 스트리밍 실행

        Args:
            message: 사용자 메시지
            session_id: 세션 ID
            user_context: 사용자 컨텍스트
            attachments: 첨부 파일 목록
            conversation_history: 대화 기록

        Yields:
            스트리밍 이벤트 딕셔너리
        """
        # 초기 상태 생성 - Adaptive Agent용 ExtendedState 사용
        initial_state = create_initial_extended_state(
            user_message=message,
            session_id=session_id,
            user_context=user_context or create_anonymous_user_context(),
            attachments=attachments,
            conversation_history=conversation_history,
        )

        # 그래프 스트리밍 실행
        config = {}
        if session_id and self.use_checkpointing:
            config["configurable"] = {"thread_id": session_id}

        # 이전 이벤트 수 추적 (중복 방지)
        seen_events = 0

        async for state in self.graph.astream(initial_state, config=config):
            # 노드 이름과 상태 추출
            for node_name, node_state in state.items():
                if isinstance(node_state, dict):
                    # 새로운 스트리밍 이벤트만 yield
                    events = node_state.get("streaming_events", [])
                    for event in events[seen_events:]:
                        yield event
                    seen_events = len(events)

    def run_sync(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_context: Optional[UserContext] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Master Agent 동기 실행

        Args:
            message: 사용자 메시지
            session_id: 세션 ID
            user_context: 사용자 컨텍스트
            attachments: 첨부 파일 목록
            conversation_history: 대화 기록

        Returns:
            최종 상태 딕셔너리
        """
        import asyncio

        return asyncio.run(self.run(
            message=message,
            session_id=session_id,
            user_context=user_context,
            attachments=attachments,
            conversation_history=conversation_history,
        ))


# =============================================================================
# 스트리밍 실행 함수
# =============================================================================

async def run_master_agent(
    message: str,
    session_id: Optional[str] = None,
    user_context: Optional[UserContext] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    stream: bool = True,
) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
    """
    Master Agent 실행 (스트리밍/단일)

    편의 함수로, MasterAgent 클래스를 직접 사용하지 않고 실행할 수 있습니다.

    Args:
        message: 사용자 메시지
        session_id: 세션 ID
        user_context: 사용자 컨텍스트
        attachments: 첨부 파일 목록
        conversation_history: 대화 기록
        stream: 스트리밍 여부

    Returns:
        스트리밍 모드: AsyncGenerator[Dict[str, Any], None]
        단일 모드: Dict[str, Any]
    """
    agent = MasterAgent()

    if stream:
        return agent.stream(
            message=message,
            session_id=session_id,
            user_context=user_context,
            attachments=attachments,
            conversation_history=conversation_history,
        )
    else:
        return await agent.run(
            message=message,
            session_id=session_id,
            user_context=user_context,
            attachments=attachments,
            conversation_history=conversation_history,
        )


async def run_master_agent_with_sse(
    message: str,
    session_id: Optional[str] = None,
    user_context: Optional[UserContext] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> AsyncGenerator[str, None]:
    """
    Master Agent SSE 스트리밍 실행

    Server-Sent Events 형식으로 이벤트를 yield합니다.
    FastAPI의 StreamingResponse와 함께 사용합니다.

    Args:
        message: 사용자 메시지
        session_id: 세션 ID
        user_context: 사용자 컨텍스트
        attachments: 첨부 파일 목록
        conversation_history: 대화 기록

    Yields:
        SSE 형식 문자열 ("event: {event}\\ndata: {json}\\n\\n")

    사용 예시:
        @app.post("/v2/agent-hub/chat")
        async def chat(request: ChatRequest):
            return StreamingResponse(
                run_master_agent_with_sse(
                    message=request.message,
                    session_id=request.session_id,
                ),
                media_type="text/event-stream"
            )
    """
    agent = MasterAgent()

    async for event in agent.stream(
        message=message,
        session_id=session_id,
        user_context=user_context,
        attachments=attachments,
        conversation_history=conversation_history,
    ):
        # SSE 형식으로 변환
        event_type = event.get("event", "message")
        event_data = json.dumps(event.get("data", {}), ensure_ascii=False)

        yield f"event: {event_type}\n"
        yield f"data: {event_data}\n\n"


# =============================================================================
# 그래프 시각화 (디버깅용)
# =============================================================================

def get_graph_mermaid() -> str:
    """
    그래프를 Mermaid 다이어그램으로 변환

    Returns:
        Mermaid 다이어그램 문자열
    """
    graph = create_master_agent_graph(use_checkpointing=False)

    try:
        # LangGraph의 내장 Mermaid 변환 (가능한 경우)
        if hasattr(graph, 'get_graph'):
            return graph.get_graph().draw_mermaid()
    except Exception:
        pass

    # 수동 생성
    return """
graph TD
    START([Start]) --> classify_intent[Classify Intent]
    classify_intent --> |clarification_needed| ask_clarification[Ask Clarification]
    classify_intent --> |proceed| plan_execution[Plan Execution]
    ask_clarification --> END([End])
    plan_execution --> |has_workflows| execute_workflows[Execute Workflows]
    plan_execution --> |no_workflows| generate_response[Generate Response]
    execute_workflows --> aggregate_results[Aggregate Results]
    aggregate_results --> generate_response
    generate_response --> END
"""


def print_graph_structure():
    """
    그래프 구조 출력 (디버깅용)
    """
    print("=" * 60)
    print("Master Agent Graph Structure")
    print("=" * 60)
    print(get_graph_mermaid())
    print("=" * 60)
