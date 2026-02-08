"""
Master Agent State Definitions

Phase 5: Agent Hub - Master Agent 상태 정의

설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.3.1

상태 구성:
1. UserContext - 사용자 컨텍스트 (JWT에서 추출)
2. Intent - 의도 분류 결과
3. ExecutionPlan - 실행 계획
4. MasterAgentState - Master Agent 전체 상태

LangGraph 호환:
- TypedDict 기반 상태 정의
- Pydantic BaseModel로 복잡한 중첩 객체 정의
"""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import uuid


# =============================================================================
# 1. UserContext - 사용자 컨텍스트
# =============================================================================

class UserContext(BaseModel):
    """
    사용자 컨텍스트 (JWT에서 추출)

    Django 백엔드 API의 사용자 정보와 통합됩니다.

    Attributes:
        user_id: 사용자 UUID
        email: 사용자 이메일
        name: 사용자 이름
        organization_id: 조직 UUID (선택)
        organization_name: 조직명 (선택)
        project_id: 프로젝트 UUID (선택)
        role: 조직 내 역할 (ADMIN, EDITOR, VIEWER)
        permissions: 권한 맵
    """
    user_id: str
    email: str
    name: str
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    project_id: Optional[str] = None
    role: str = "VIEWER"  # ADMIN, EDITOR, VIEWER
    permissions: Dict[str, bool] = Field(default_factory=dict)

    @property
    def can_edit(self) -> bool:
        """편집 권한 여부"""
        return self.role in ["ADMIN", "EDITOR"]

    @property
    def can_admin(self) -> bool:
        """관리자 권한 여부"""
        return self.role == "ADMIN"


# =============================================================================
# 2. Intent - 의도 분류 결과
# =============================================================================

class IntentCategory(str, Enum):
    """의도 카테고리"""
    GENERAL_CHAT = "GENERAL_CHAT"            # 일반 대화 (법률과 무관)
    QUERY = "QUERY"                          # 일반 법률 질의응답
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"  # 문서 분석 요청
    CASE_ANALYSIS = "CASE_ANALYSIS"          # 사건 분석 요청
    RISK_ASSESSMENT = "RISK_ASSESSMENT"      # 리스크 평가 요청
    COMPARISON = "COMPARISON"                # 비교 분석
    SEARCH = "SEARCH"                        # 판례/법령 검색
    GENERATION = "GENERATION"                # 문서/보고서 생성
    ANALYTICS = "ANALYTICS"                  # 통계/분석
    MULTI_TASK = "MULTI_TASK"                # 복합 작업
    UNKNOWN = "UNKNOWN"                      # 분류 불가


class Intent(BaseModel):
    """
    의도 분류 결과

    IntentClassifier가 사용자 메시지를 분석하여 생성합니다.

    Attributes:
        category: 주요 카테고리
        sub_category: 세부 카테고리 (선택)
        confidence: 신뢰도 (0-1)
        extracted_params: 추출된 파라미터
        requires_attachment: 파일 첨부 필요 여부
        suggested_workflows: 추천 워크플로우 목록
        clarification_needed: 추가 정보 필요 여부
        clarification_questions: 확인 질문 목록
    """
    model_config = {"use_enum_values": True}  # enum을 값으로 직렬화

    category: IntentCategory = IntentCategory.UNKNOWN
    sub_category: Optional[str] = None
    confidence: float = 0.0
    extracted_params: Dict[str, Any] = Field(default_factory=dict)
    requires_attachment: bool = False
    suggested_workflows: List[str] = Field(default_factory=list)
    clarification_needed: bool = False
    clarification_questions: List[str] = Field(default_factory=list)

    @property
    def is_high_confidence(self) -> bool:
        """고신뢰도 여부 (0.8 이상)"""
        return self.confidence >= 0.8

    @property
    def is_multi_task(self) -> bool:
        """복합 작업 여부"""
        return self.category == IntentCategory.MULTI_TASK


# =============================================================================
# 3. ExecutionPlan - 실행 계획
# =============================================================================

class WorkflowStep(BaseModel):
    """
    워크플로우 실행 단계

    Attributes:
        step_id: 단계 고유 ID
        workflow_name: 워크플로우 이름
        inputs: 입력 파라미터
        depends_on: 의존하는 단계 ID 목록
        estimated_time: 예상 실행 시간 (초)
        priority: 실행 우선순위 (낮을수록 먼저)
    """
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    workflow_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    estimated_time: float = 0.0
    priority: int = 0


class ToolCall(BaseModel):
    """
    도구 호출 정보

    Attributes:
        tool_id: 도구 호출 고유 ID
        tool_name: 도구 이름 (MCP Tool Name)
        inputs: 입력 파라미터
        depends_on: 의존하는 단계/도구 ID 목록
    """
    tool_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    tool_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    """
    실행 계획

    WorkflowRouter가 Intent를 기반으로 생성합니다.

    Attributes:
        plan_id: 계획 고유 ID
        workflows: 실행할 워크플로우 단계 목록
        tools: 실행할 도구 호출 목록
        execution_order: 실행 순서 (step_id 또는 tool_id)
        estimated_total_time: 예상 총 실행 시간 (초)
        can_parallelize: 병렬 실행 가능 여부
        parallel_groups: 병렬 실행 가능한 그룹 목록
    """
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflows: List[WorkflowStep] = Field(default_factory=list)
    tools: List[ToolCall] = Field(default_factory=list)
    execution_order: List[str] = Field(default_factory=list)
    estimated_total_time: float = 0.0
    can_parallelize: bool = False
    parallel_groups: List[List[str]] = Field(default_factory=list)

    @property
    def total_steps(self) -> int:
        """총 실행 단계 수"""
        return len(self.workflows) + len(self.tools)

    @property
    def workflow_names(self) -> List[str]:
        """워크플로우 이름 목록"""
        return [w.workflow_name for w in self.workflows]


# =============================================================================
# 4. Supporting Types
# =============================================================================

class StreamingEvent(BaseModel):
    """
    스트리밍 이벤트

    실시간 진행 상황을 프론트엔드에 전달합니다.

    Attributes:
        event: 이벤트 타입
        data: 이벤트 데이터
        timestamp: 이벤트 발생 시간
    """
    event: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# Progress Event Helpers
# =============================================================================

class ProgressStep(str, Enum):
    """진행 단계 정의"""
    ANALYZING = "analyzing"           # 질문 분석 중
    CLASSIFYING = "classifying"       # 복잡도 분류 중
    PLANNING = "planning"             # 실행 계획 수립 중
    SEARCHING = "searching"           # 검색 중 (RAG)
    ANALYZING_DOC = "analyzing_doc"   # 문서 분석 중
    THINKING = "thinking"             # 추론 중 (THINKING path)
    EXECUTING = "executing"           # 워크플로우 실행 중
    GENERATING = "generating"         # 응답 생성 중
    COMPLETE = "complete"             # 완료


# 단계별 친화적 메시지 매핑
PROGRESS_MESSAGES = {
    ProgressStep.ANALYZING: "질문을 분석하고 있습니다...",
    ProgressStep.CLASSIFYING: "요청 유형을 파악하고 있습니다...",
    ProgressStep.PLANNING: "실행 계획을 수립하고 있습니다...",
    ProgressStep.SEARCHING: "관련 정보를 검색하고 있습니다...",
    ProgressStep.ANALYZING_DOC: "문서를 분석하고 있습니다...",
    ProgressStep.THINKING: "심층 분석 중입니다...",
    ProgressStep.EXECUTING: "작업을 수행하고 있습니다...",
    ProgressStep.GENERATING: "답변을 생성하고 있습니다...",
    ProgressStep.COMPLETE: "완료되었습니다!",
}

# 경로별 단계 및 퍼센트 매핑
PATH_PROGRESS_CONFIG = {
    "fast": [
        (ProgressStep.CLASSIFYING, 20),
        (ProgressStep.GENERATING, 80),
        (ProgressStep.COMPLETE, 100),
    ],
    "medium": [
        (ProgressStep.CLASSIFYING, 15),
        (ProgressStep.EXECUTING, 50),
        (ProgressStep.GENERATING, 85),
        (ProgressStep.COMPLETE, 100),
    ],
    "deep": [
        (ProgressStep.CLASSIFYING, 10),
        (ProgressStep.PLANNING, 20),
        (ProgressStep.EXECUTING, 60),
        (ProgressStep.GENERATING, 90),
        (ProgressStep.COMPLETE, 100),
    ],
    "thinking": [
        (ProgressStep.CLASSIFYING, 10),
        (ProgressStep.THINKING, 70),
        (ProgressStep.GENERATING, 90),
        (ProgressStep.COMPLETE, 100),
    ],
}


def create_progress_event(
    step: ProgressStep,
    percentage: int,
    message: Optional[str] = None,
    execution_path: str = "medium",
    step_details: Optional[Dict[str, Any]] = None,
) -> StreamingEvent:
    """
    표준화된 진행 상황 이벤트 생성

    Args:
        step: 현재 진행 단계
        percentage: 진행률 (0-100)
        message: 사용자에게 표시할 메시지 (없으면 기본 메시지 사용)
        execution_path: 실행 경로 ("fast", "medium", "deep", "thinking")
        step_details: 추가 세부 정보

    Returns:
        StreamingEvent 객체
    """
    return StreamingEvent(
        event="progress",
        data={
            "step": step.value,
            "percentage": min(max(percentage, 0), 100),  # 0-100 범위 보장
            "message": message or PROGRESS_MESSAGES.get(step, "처리 중..."),
            "execution_path": execution_path,
            "step_details": step_details or {},
        },
        timestamp=datetime.now().isoformat(),
    )


class ExecutionLog(BaseModel):
    """
    실행 로그

    Attributes:
        step_id: 단계 ID
        step_name: 단계 이름
        status: 상태 (pending, running, completed, failed)
        started_at: 시작 시간
        completed_at: 완료 시간
        result: 결과 요약
        error: 에러 메시지 (실패 시)
    """
    step_id: str
    step_name: str
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# =============================================================================
# 5. MasterAgentState - Master Agent 전체 상태
# =============================================================================

class MasterAgentState(TypedDict):
    """
    Master Agent 상태 (LangGraph StateGraph 호환)

    설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.3.1

    Attributes:
        ===== 사용자 컨텍스트 =====
        user_context: 사용자 정보 객체

        ===== 입력 =====
        user_message: 사용자 메시지
        attachments: 첨부 파일 목록
        session_id: 세션 ID

        ===== 대화 컨텍스트 =====
        conversation_history: 대화 기록 목록

        ===== 의도 분류 =====
        intent: 분류된 의도

        ===== 실행 계획 =====
        execution_plan: 실행 계획

        ===== 워크플로우 결과 =====
        workflow_results: 워크플로우 실행 결과
        tool_results: 도구 실행 결과

        ===== 최종 응답 =====
        final_response: 최종 응답 텍스트
        response_metadata: 응답 메타데이터

        ===== 실행 정보 =====
        start_time: 시작 시간
        execution_logs: 실행 로그 목록
        errors: 에러 목록

        ===== 스트리밍 =====
        streaming_events: 스트리밍 이벤트 목록
    """
    # ===== 사용자 컨텍스트 =====
    user_context: Optional[Dict[str, Any]]  # UserContext.model_dump()

    # ===== 입력 =====
    user_message: str
    attachments: Optional[List[Dict[str, Any]]]
    session_id: str

    # ===== 대화 컨텍스트 =====
    conversation_history: List[Dict[str, str]]

    # ===== 의도 분류 =====
    intent: Optional[Dict[str, Any]]  # Intent.model_dump()

    # ===== 실행 계획 =====
    execution_plan: Optional[Dict[str, Any]]  # ExecutionPlan.model_dump()

    # ===== 워크플로우 결과 =====
    workflow_results: Dict[str, Any]
    tool_results: Dict[str, Any]

    # ===== 최종 응답 =====
    final_response: str
    response_metadata: Dict[str, Any]

    # ===== 실행 정보 =====
    start_time: str  # ISO format datetime
    execution_logs: List[Dict[str, Any]]  # List[ExecutionLog.model_dump()]
    errors: List[Dict[str, Any]]

    # ===== 스트리밍 =====
    streaming_events: List[Dict[str, Any]]  # List[StreamingEvent.model_dump()]


# =============================================================================
# 6. Helper Functions
# =============================================================================

def create_initial_master_agent_state(
    user_message: str,
    session_id: Optional[str] = None,
    user_context: Optional[UserContext] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> MasterAgentState:
    """
    초기 MasterAgentState 생성

    Args:
        user_message: 사용자 메시지
        session_id: 세션 ID (없으면 자동 생성)
        user_context: 사용자 컨텍스트
        attachments: 첨부 파일 목록
        conversation_history: 대화 기록

    Returns:
        초기화된 MasterAgentState
    """
    return MasterAgentState(
        # 사용자 컨텍스트
        user_context=user_context.model_dump() if user_context else None,

        # 입력
        user_message=user_message,
        attachments=attachments or [],
        session_id=session_id or str(uuid.uuid4()),

        # 대화 컨텍스트
        conversation_history=conversation_history or [],

        # 의도 분류 (초기값)
        intent=None,

        # 실행 계획 (초기값)
        execution_plan=None,

        # 워크플로우 결과 (초기값)
        workflow_results={},
        tool_results={},

        # 최종 응답 (초기값)
        final_response="",
        response_metadata={},

        # 실행 정보
        start_time=datetime.now().isoformat(),
        execution_logs=[],
        errors=[],

        # 스트리밍 이벤트
        streaming_events=[],
    )


def create_anonymous_user_context() -> UserContext:
    """
    익명 사용자 컨텍스트 생성 (테스트/개발용)

    Returns:
        기본 권한의 UserContext
    """
    return UserContext(
        user_id="anonymous",
        email="anonymous@example.com",
        name="Anonymous User",
        role="VIEWER",
        permissions={
            "can_edit": False,
            "can_admin": False,
        }
    )


# =============================================================================
# 7. Complexity Classification (Adaptive Agent)
# =============================================================================

class ComplexityLevel(str, Enum):
    """복잡도 수준"""
    FAST = "FAST"        # 일반 대화, 캐시 히트, 단순 질문
    MEDIUM = "MEDIUM"    # 단일 워크플로우, 단일 도구
    DEEP = "DEEP"        # 복합 작업, 다단계 실행
    THINKING = "THINKING"  # ReAct 패턴 자율 추론


@dataclass
class ComplexityResult:
    """복잡도 분류 결과"""
    level: ComplexityLevel
    confidence: float  # 0.0 ~ 1.0
    reason: str        # 분류 이유
    suggested_path: str  # "fast", "medium", "deep"

    # MEDIUM/DEEP 경로용 추가 정보
    suggested_workflow: Optional[str] = None
    suggested_tools: List[str] = field(default_factory=list)
    requires_planning: bool = False


# =============================================================================
# 8. Extended State (Adaptive Agent용)
# =============================================================================

class ExtendedMasterAgentState(TypedDict):
    """
    Adaptive Agent용 확장 State

    MasterAgentState의 모든 필드 + 복잡도 분류 관련 필드
    """
    # ===== 기존 MasterAgentState 필드 =====
    user_context: Optional[Dict[str, Any]]
    user_message: str
    attachments: Optional[List[Dict[str, Any]]]
    session_id: str
    conversation_history: List[Dict[str, str]]
    intent: Optional[Dict[str, Any]]
    execution_plan: Optional[Dict[str, Any]]
    workflow_results: Dict[str, Any]
    tool_results: Dict[str, Any]
    final_response: str
    response_metadata: Dict[str, Any]
    start_time: str
    execution_logs: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    streaming_events: List[Dict[str, Any]]

    # ===== 복잡도 분류 관련 (신규) =====
    complexity_level: Optional[str]       # "FAST", "MEDIUM", "DEEP"
    complexity_confidence: float          # 분류 신뢰도
    complexity_reason: str                # 분류 이유
    execution_path: str                   # 실제 실행 경로

    # ===== Quick Plan (MEDIUM Path용) =====
    quick_plan: Optional[Dict[str, Any]]  # QuickPlan 직렬화

    # ===== 캐시 관련 =====
    cache_key: Optional[str]
    cache_hit: bool


def create_initial_extended_state(
    user_message: str,
    session_id: Optional[str] = None,
    user_context: Optional[UserContext] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> ExtendedMasterAgentState:
    """
    초기 ExtendedMasterAgentState 생성
    """
    base_state = create_initial_master_agent_state(
        user_message=user_message,
        session_id=session_id,
        user_context=user_context,
        attachments=attachments,
        conversation_history=conversation_history,
    )

    # 확장 필드 추가
    extended_state = ExtendedMasterAgentState(
        **base_state,
        # 복잡도 분류 (초기값)
        complexity_level=None,
        complexity_confidence=0.0,
        complexity_reason="",
        execution_path="",
        # Quick Plan
        quick_plan=None,
        # 캐시
        cache_key=None,
        cache_hit=False,
    )

    return extended_state


# =============================================================================
# 9. QuickPlan (MEDIUM Path용)
# =============================================================================

@dataclass
class QuickPlan:
    """
    MEDIUM Path용 빠른 실행 계획

    단일 워크플로우 또는 단일 도구 실행을 위한 간단한 계획

    Attributes:
        workflow_name: 실행할 워크플로우 이름 (또는 None)
        tool_name: 실행할 도구 이름 (또는 None)
        inputs: 입력 파라미터
        expected_output: 예상 출력 형태 ("text", "json", "table")
    """
    workflow_name: Optional[str] = None
    tool_name: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_output: str = "text"

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "workflow_name": self.workflow_name,
            "tool_name": self.tool_name,
            "inputs": self.inputs,
            "expected_output": self.expected_output,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuickPlan":
        """딕셔너리에서 생성"""
        return cls(
            workflow_name=data.get("workflow_name"),
            tool_name=data.get("tool_name"),
            inputs=data.get("inputs", {}),
            expected_output=data.get("expected_output", "text"),
        )


# =============================================================================
# 10. DeepPlan (DEEP Path용)
# =============================================================================

@dataclass
class ExecutionStep:
    """
    실행 단계

    Attributes:
        step_id: 단계 고유 ID
        step_type: "workflow" | "tool"
        name: 워크플로우/도구 이름
        inputs: 입력 파라미터
        depends_on: 의존하는 단계 ID 목록 (순서 보장)
        priority: 우선순위 (낮을수록 먼저)
    """
    step_id: str
    step_type: str  # "workflow" | "tool"
    name: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    priority: int = 0


@dataclass
class DeepPlan:
    """
    DEEP Path용 실행 계획

    다단계 워크플로우 및 도구 실행을 위한 계획

    Attributes:
        plan_id: 계획 고유 ID
        steps: 실행 단계 목록
        parallel_groups: 병렬 실행 가능한 그룹 (step_id 목록)
        total_steps: 총 단계 수
        estimated_time: 예상 소요 시간 (초)
    """
    plan_id: str
    steps: List[ExecutionStep] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    total_steps: int = 0
    estimated_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "plan_id": self.plan_id,
            "steps": [
                {
                    "step_id": s.step_id,
                    "step_type": s.step_type,
                    "name": s.name,
                    "inputs": s.inputs,
                    "depends_on": s.depends_on,
                    "priority": s.priority,
                }
                for s in self.steps
            ],
            "parallel_groups": self.parallel_groups,
            "total_steps": self.total_steps,
            "estimated_time": self.estimated_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeepPlan":
        """딕셔너리에서 생성"""
        steps = [
            ExecutionStep(
                step_id=s["step_id"],
                step_type=s["step_type"],
                name=s["name"],
                inputs=s.get("inputs", {}),
                depends_on=s.get("depends_on", []),
                priority=s.get("priority", 0),
            )
            for s in data.get("steps", [])
        ]
        return cls(
            plan_id=data.get("plan_id", ""),
            steps=steps,
            parallel_groups=data.get("parallel_groups", []),
            total_steps=data.get("total_steps", len(steps)),
            estimated_time=data.get("estimated_time", 0.0),
        )


# =============================================================================
# 11. Thinking Agent State
# =============================================================================

@dataclass
class ThoughtStep:
    """
    단일 사고 단계 - ReAct 루프의 한 사이클

    Attributes:
        step_number: 사고 단계 번호
        thought: 현재 상황 분석 및 추론
        action: 선택된 도구 또는 "FINAL_ANSWER"
        action_input: 도구 입력 또는 최종 답변
        observation: 도구 실행 결과 (Act 후 채워짐)
        reflection: 결과에 대한 반성 (선택)
        is_final: 최종 답변 여부
    """
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    reflection: Optional[str] = None
    is_final: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "reflection": self.reflection,
            "is_final": self.is_final,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThoughtStep":
        return cls(
            step_number=data.get("step_number", 0),
            thought=data.get("thought", ""),
            action=data.get("action"),
            action_input=data.get("action_input"),
            observation=data.get("observation"),
            reflection=data.get("reflection"),
            is_final=data.get("is_final", False),
        )


class FullMasterAgentState(TypedDict):
    """
    Full Master Agent State (Thinking 포함)

    ExtendedMasterAgentState + Thinking 전용 필드
    """
    # ===== ExtendedMasterAgentState 필드 =====
    user_context: Optional[Dict[str, Any]]
    user_message: str
    attachments: Optional[List[Dict[str, Any]]]
    session_id: str
    conversation_history: List[Dict[str, str]]
    intent: Optional[Dict[str, Any]]
    execution_plan: Optional[Dict[str, Any]]
    workflow_results: Dict[str, Any]
    tool_results: Dict[str, Any]
    final_response: str
    response_metadata: Dict[str, Any]
    start_time: str
    execution_logs: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    streaming_events: List[Dict[str, Any]]
    complexity_level: Optional[str]
    complexity_confidence: float
    complexity_reason: str
    execution_path: str
    quick_plan: Optional[Dict[str, Any]]
    cache_key: Optional[str]
    cache_hit: bool

    # ===== Thinking 전용 필드 =====
    goal: str                               # 달성할 목표
    thought_history: List[Dict[str, Any]]   # ThoughtStep 목록
    current_step: int                       # 현재 단계 번호
    max_steps: int                          # 최대 단계 수
    available_tools: List[str]              # 사용 가능한 도구 목록
    accumulated_context: List[str]          # 누적 컨텍스트
    thinking_complete: bool                 # 사고 완료 여부
    completion_reason: Optional[str]        # 완료 사유
    total_llm_calls: int                    # 총 LLM 호출 횟수
    total_tool_calls: int                   # 총 도구 호출 횟수


def create_initial_full_state(
    user_message: str,
    session_id: Optional[str] = None,
    user_context: Optional[UserContext] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    max_thinking_steps: int = 10,
) -> FullMasterAgentState:
    """
    초기 FullMasterAgentState 생성

    Note: TypedDict는 생성자에서 **spread를 지원하지 않으므로
    딕셔너리를 직접 구성하여 반환합니다.

    Args:
        user_message: 사용자 메시지
        session_id: 세션 ID (없으면 자동 생성)
        user_context: 사용자 컨텍스트
        attachments: 첨부 파일 목록
        conversation_history: 대화 기록
        max_thinking_steps: 최대 사고 단계 수

    Returns:
        초기화된 FullMasterAgentState
    """
    # ExtendedMasterAgentState 기본값 가져오기
    extended_state = create_initial_extended_state(
        user_message=user_message,
        session_id=session_id,
        user_context=user_context,
        attachments=attachments,
        conversation_history=conversation_history,
    )

    # Thinking 전용 필드 추가
    full_state: FullMasterAgentState = {
        **extended_state,
        "goal": "",
        "thought_history": [],
        "current_step": 0,
        "max_steps": max_thinking_steps,
        "available_tools": [],
        "accumulated_context": [],
        "thinking_complete": False,
        "completion_reason": None,
        "total_llm_calls": 0,
        "total_tool_calls": 0,
    }

    return full_state
