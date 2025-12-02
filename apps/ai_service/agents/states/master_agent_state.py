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
