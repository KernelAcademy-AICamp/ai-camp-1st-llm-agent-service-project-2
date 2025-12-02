"""
V2 Agent Hub Router - Master Agent Orchestrator API

Phase 4 - Agent Hub: 통합 AI 법률 어시스턴트 API

특징:
- Master Agent Orchestrator 기반 의도 분류 및 워크플로우 라우팅
- JWT 인증 통합 (Backend API)
- SSE 스트리밍 응답
- 세션/대화 관리
- 역할 기반 접근 제어 (RBAC)
- 사용량 쿼터 관리

엔드포인트:
- POST /v2/agent-hub/chat - 통합 채팅 API (SSE 스트리밍)
- POST /v2/agent-hub/sessions - 새 세션 생성
- GET /v2/agent-hub/sessions/{session_id}/history - 대화 기록 조회
- DELETE /v2/agent-hub/sessions/{session_id} - 세션 삭제
- GET /v2/agent-hub/capabilities - 사용 가능한 기능 목록
"""

from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
import uuid
import asyncio

# 내부 모듈 import
from apps.ai_service.middleware.auth import verify_token, get_optional_user
from apps.ai_service.services.session_service import (
    get_session_service,
    SessionService,
)
from apps.ai_service.services.conversation_service import (
    get_conversation_service,
    ConversationService,
    add_user_message,
    add_assistant_message,
    get_conversation_history,
)
from apps.ai_service.repositories.agent_hub_repository import (
    ensure_session_record,
    update_session_metadata,
    record_message as persist_message,
    fetch_session_history as fetch_persistent_history,
    list_user_sessions as list_persistent_sessions,
    delete_session_record,
    get_session_record,
)
from apps.ai_service.services.usage_service import (
    get_usage_service,
    UsageService,
    check_user_quota,
    record_usage,
)
from apps.ai_service.agents.master_agent import (
    MasterAgent,
    run_master_agent_with_sse,
)
from apps.ai_service.agents.nodes.generate_response_node import (
    _extract_document_analysis,
)
import httpx
from apps.ai_service.agents.states.master_agent_state import (
    UserContext,
    create_initial_master_agent_state,
)
from apps.ai_service.services.title_generator import (
    generate_simple_title,
    generate_and_update_title,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/agent-hub", tags=["Agent Hub"])


# ===== Enums =====

class IntentCategory(str, Enum):
    """의도 카테고리"""
    GENERAL_CHAT = "GENERAL_CHAT"        # 일반 대화 (법률과 무관)
    QUERY = "QUERY"                      # 일반 법률 질의응답
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"  # 문서 분석
    CASE_ANALYSIS = "CASE_ANALYSIS"      # 사건 분석
    RISK_ASSESSMENT = "RISK_ASSESSMENT"  # 리스크 평가
    COMPARISON = "COMPARISON"            # 비교 분석
    SEARCH = "SEARCH"                    # 판례/법령 검색
    GENERATION = "GENERATION"            # 문서/보고서 생성
    ANALYTICS = "ANALYTICS"              # 통계/분석
    MULTI_TASK = "MULTI_TASK"            # 복합 작업


class ResponseFormat(str, Enum):
    """응답 포맷 타입"""
    TEXT = "text"                        # 일반 텍스트
    STRUCTURED = "structured"            # 구조화된 데이터 (표, 리스트)
    COMPARISON = "comparison"            # 비교 뷰
    CHART = "chart"                      # 차트/그래프
    DOCUMENT = "document"                # 문서 미리보기
    TIMELINE = "timeline"                # 타임라인
    MIXED = "mixed"                      # 혼합


# ===== Request Models =====

class Attachment(BaseModel):
    """첨부 파일 정보"""

    type: str = Field(..., description="파일 타입 (file, url, document)")
    url: Optional[str] = Field(
        default=None,
        description="파일 URL (선택)"
    )
    filename: Optional[str] = Field(
        default=None,
        description="파일명"
    )
    mime_type: Optional[str] = Field(
        default=None,
        description="MIME 타입"
    )
    size: Optional[int] = Field(
        default=None,
        description="파일 크기 (bytes)"
    )
    doc_type: Optional[str] = Field(
        default=None,
        description="문서 타입 (CONTRACT, STATUTE 등)"
    )
    document_id: Optional[str] = Field(
       default=None,
       description="멤버 문서 ID (선택)"
    )
    content: Optional[str] = Field(
        default=None,
        description="추출된 텍스트 컨텐츠"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="추가 메타데이터"
    )


class ChatPreferences(BaseModel):
    """채팅 설정"""
    response_detail: str = Field(
        "standard",
        description="응답 상세도 (concise, standard, detailed)"
    )
    include_sources: bool = Field(True, description="출처 포함 여부")
    max_execution_time: int = Field(60, description="최대 실행 시간 (초)")
    language: str = Field("ko", description="응답 언어")


class ChatRequest(BaseModel):
    """Agent Hub 채팅 요청"""
    message: str = Field(..., description="사용자 메시지", min_length=1)
    attachments: Optional[List[Attachment]] = Field(
        default=None,
        description="첨부 파일 목록"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="세션 ID (없으면 새 세션 생성)"
    )
    project_id: Optional[str] = Field(
        default=None,
        description="프로젝트 ID (선택)"
    )
    stream: bool = Field(True, description="스트리밍 응답 여부")
    preferences: Optional[ChatPreferences] = Field(
        default=None,
        description="응답 설정"
    )


class CreateSessionRequest(BaseModel):
    """세션 생성 요청"""
    organization_id: Optional[str] = Field(
        default=None,
        description="조직 ID"
    )
    project_id: Optional[str] = Field(
        default=None,
        description="프로젝트 ID"
    )
    title: Optional[str] = Field(
        default=None,
        description="세션 제목"
    )


class UpdateSessionRequest(BaseModel):
    """세션 업데이트 요청"""
    title: Optional[str] = Field(
        default=None,
        description="세션 제목"
    )
    project_id: Optional[str] = Field(
        default=None,
        description="프로젝트 ID"
    )


# ===== Response Models =====

class IntentInfo(BaseModel):
    """의도 분류 정보"""
    category: IntentCategory
    sub_category: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_params: Dict[str, Any] = Field(default_factory=dict)


class ExecutionStep(BaseModel):
    """실행 단계 정보"""
    step_id: str
    workflow: str
    status: str  # pending, running, completed, failed
    progress: float = Field(ge=0.0, le=1.0)
    result_preview: Optional[str] = None


class ChatResponse(BaseModel):
    """채팅 응답 (비스트리밍)"""
    response: str
    format: ResponseFormat
    session_id: str
    intent: IntentInfo
    execution_time: float
    workflows_used: List[str]
    structured_data: Optional[Dict[str, Any]] = None
    visualizations: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class SessionResponse(BaseModel):
    """세션 응답"""
    session_id: str
    created_at: str
    expires_at: str
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    title: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int = 0
    last_message: Optional[str] = None
    user_id: Optional[str] = None


class SessionListResponse(BaseModel):
    """세션 목록 응답"""
    sessions: List["SessionResponse"]
    total: int
    page: int
    page_size: int
    has_next: bool


class SuggestedQuestion(BaseModel):
    """추천 질문"""
    id: str
    text: str
    category: Optional[str] = None


class MessageItem(BaseModel):
    """대화 메시지"""
    role: str = Field(..., description="메시지 역할 (user, assistant)")
    content: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HistoryResponse(BaseModel):
    """대화 기록 응답"""
    session_id: str
    messages: List[MessageItem]
    total_messages: int


class WorkflowCapability(BaseModel):
    """워크플로우 기능 정보"""
    name: str
    description: str
    required_roles: List[str]
    quota_weight: int
    supports_streaming: bool


class CapabilitiesResponse(BaseModel):
    """기능 목록 응답"""
    workflows: List[WorkflowCapability]
    intent_categories: List[str]
    version: str
    timestamp: str


# ===== Streaming Event Models =====

class StreamingEvent(BaseModel):
    """스트리밍 이벤트"""
    event: str
    data: Dict[str, Any]
    timestamp: str


# ===== Workflow Permissions (RBAC) =====

WORKFLOW_PERMISSIONS = {
    "rag_workflow": {
        "required_roles": ["VIEWER", "EDITOR", "ADMIN"],
        "description": "법률 질의응답",
        "quota_weight": 1,
        "supports_streaming": True
    },
    "document_workflow": {
        "required_roles": ["VIEWER", "EDITOR", "ADMIN"],  # 모든 사용자에게 개방
        "description": "문서 분석",
        "quota_weight": 3,
        "supports_streaming": True
    },
    "case_workflow": {
        "required_roles": ["VIEWER", "EDITOR", "ADMIN"],  # 모든 사용자에게 개방
        "description": "사건 분석",
        "quota_weight": 3,
        "supports_streaming": True
    },
    "risk_workflow": {
        "required_roles": ["VIEWER", "EDITOR", "ADMIN"],  # 모든 사용자에게 개방
        "description": "리스크 평가",
        "quota_weight": 5,
        "supports_streaming": True
    },
    "llm_comparison_workflow": {
        "required_roles": ["VIEWER", "EDITOR", "ADMIN"],  # 모든 사용자에게 개방
        "description": "LLM 비교 분석 (고급 기능)",
        "quota_weight": 10,
        "supports_streaming": True
    },
    "analytics_workflow": {
        "required_roles": ["VIEWER", "EDITOR", "ADMIN"],  # 모든 사용자에게 개방
        "description": "통계 및 분석",
        "quota_weight": 2,
        "supports_streaming": False
    },
    "crawler_workflow": {
        "required_roles": ["VIEWER", "EDITOR", "ADMIN"],  # 모든 사용자에게 개방
        "description": "크롤러 (외부 데이터 수집)",
        "quota_weight": 8,
        "supports_streaming": False
    }
}


# ===== Helper Functions =====

def generate_session_id() -> str:
    """새 세션 ID 생성"""
    return str(uuid.uuid4())


def user_info_to_context(user_info: Dict[str, Any]) -> UserContext:
    """
    인증 미들웨어에서 반환한 user_info를 UserContext로 변환

    Args:
        user_info: verify_token에서 반환한 사용자 정보

    Returns:
        UserContext 객체
    """
    return UserContext(
        user_id=user_info.get("user_id", ""),
        email=user_info.get("email", ""),
        name=user_info.get("name", ""),
        organization_id=user_info.get("organization_id"),
        organization_name=user_info.get("organization_name"),
        role=user_info.get("role", "VIEWER"),
        permissions=user_info.get("permissions", {})
    )


async def get_or_create_session(
    user_id: str,
    session_id: Optional[str],
    organization_id: Optional[str] = None,
    project_id: Optional[str] = None
) -> tuple[str, bool]:
    """
    세션 조회 또는 생성

    Args:
        user_id: 사용자 UUID
        session_id: 기존 세션 ID (없으면 None)
        organization_id: 조직 UUID
        project_id: 프로젝트 UUID

    Returns:
        (session_id, is_new): 세션 ID와 새로 생성 여부
    """
    session_service = get_session_service()

    if session_id:
        # 기존 세션 확인
        try:
            session = await session_service.get_session(session_id)
            if session and session.get("user_id") == user_id:
                # 세션 활동 업데이트
                await session_service.update_session_activity(session_id)
                await ensure_session_record(
                    session_id=session_id,
                    user_id=user_id,
                    organization_id=organization_id,
                    project_id=project_id,
                )
                return session_id, False
        except Exception as e:
            logger.warning(f"세션 조회 실패 (새 세션 생성): {e}")

    # 새 세션 생성
    try:
        new_session_id = await session_service.create_session(
            user_id=user_id,
            organization_id=organization_id,
            project_id=project_id
        )
        await ensure_session_record(
            session_id=new_session_id,
            user_id=user_id,
            organization_id=organization_id,
            project_id=project_id,
        )
        return new_session_id, True
    except Exception as e:
        logger.error(f"세션 생성 실패: {e}")
        # 폴백: 메모리 기반 세션 ID
        return generate_session_id(), True


# ===== API Endpoints =====

@router.post("/chat")
async def agent_hub_chat(
    request: ChatRequest,
    http_request: Request,
    user_info: Dict[str, Any] = Depends(verify_token)
):
    """
    Agent Hub 통합 채팅 API (인증 필수)

    사용자의 자연어 메시지를 분석하여 적절한 워크플로우를 자동 선택하고 실행합니다.

    Features:
    - JWT 인증 필수
    - 의도 분류 (Intent Classification)
    - 워크플로우 라우팅
    - SSE 스트리밍 응답
    - 대화 컨텍스트 유지
    - 사용량 쿼터 관리

    Headers:
        Authorization: Bearer {jwt_token}

    Args:
        request: 채팅 요청
        http_request: FastAPI Request
        user_info: JWT에서 추출한 사용자 정보

    Returns:
        스트리밍: SSE 이벤트 스트림
        비스트리밍: ChatResponse

    Raises:
        401 Unauthorized: 인증 실패
        429 Too Many Requests: 쿼터 초과
        403 Forbidden: 권한 없음
    """
    start_time = datetime.now()

    try:
        logger.info(
            f"[agent-hub/chat] user={user_info['user_id']}, "
            f"message='{request.message[:50]}...'"
        )

        # 1. 쿼터 확인
        try:
            quota_result = await check_user_quota(
                user_id=user_info["user_id"],
                organization_id=user_info.get("organization_id"),
                raise_on_exceed=True
            )
            logger.debug(f"[agent-hub/chat] Quota: {quota_result}")
        except HTTPException:
            raise
        except Exception as e:
            # 쿼터 확인 실패해도 서비스는 계속 (graceful degradation)
            logger.warning(f"[agent-hub/chat] Quota check failed (proceeding): {e}")
            quota_result = None

        # 2. 세션 관리
        session_id, is_new_session = await get_or_create_session(
            user_id=user_info["user_id"],
            session_id=request.session_id,
            organization_id=user_info.get("organization_id"),
            project_id=request.project_id
        )

        logger.debug(
            f"[agent-hub/chat] Session: {session_id}, "
            f"is_new={is_new_session}"
        )

        # 3. 사용자 메시지 저장
        try:
            await add_user_message(
                session_id=session_id,
                content=request.message,
                metadata={
                    "attachments_count": len(request.attachments) if request.attachments else 0,
                    "preferences": request.preferences.model_dump() if request.preferences else {}
                }
            )
        except Exception as e:
            logger.warning(f"[agent-hub/chat] Failed to save user message: {e}")

        # 4. UserContext 생성
        user_context = user_info_to_context(user_info)

        # 5. 대화 기록 조회
        try:
            conversation_history = await get_conversation_history(
                session_id=session_id,
                limit=10  # 최근 10개 메시지
            )
        except Exception as e:
            logger.warning(f"[agent-hub/chat] Failed to get conversation history: {e}")
            conversation_history = []

        # 5.1. 현재 세션 정보 조회 (제목 생성용)
        current_title = ""
        is_first_message = is_new_session or len(conversation_history) == 0
        try:
            session_record = await get_session_record(session_id)
            if session_record:
                current_title = session_record.title or ""
                # 제목이 없거나 기본 제목이면 첫 메시지로 간주
                if current_title in ["", "새 대화", "New Chat"]:
                    is_first_message = True
        except Exception as e:
            logger.debug(f"[agent-hub/chat] Session record check: {e}")

        # 6. 스트리밍 응답
        if request.stream:
            return StreamingResponse(
                _stream_agent_response(
                    request=request,
                    session_id=session_id,
                    user_context=user_context,
                    user_info=user_info,
                    conversation_history=conversation_history,
                    start_time=start_time,
                    is_first_message=is_first_message,
                    current_title=current_title,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Session-Id": session_id,
                }
            )

        # 7. 비스트리밍 응답
        return await _non_streaming_response(
            request=request,
            session_id=session_id,
            user_context=user_context,
            user_info=user_info,
            conversation_history=conversation_history,
            start_time=start_time,
            is_first_message=is_first_message,
            current_title=current_title,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[agent-hub/chat] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def _stream_agent_response(
    request: ChatRequest,
    session_id: str,
    user_context: UserContext,
    user_info: Dict[str, Any],
    conversation_history: List[Dict[str, Any]],
    start_time: datetime,
    is_first_message: bool = False,
    current_title: str = "",
):
    """
    SSE 스트리밍 응답 생성기

    Master Agent를 실행하면서 실시간으로 이벤트를 전송합니다.
    """
    final_response = ""
    workflows_used = []
    intent_category = "UNKNOWN"

    try:
        # 1. 시작 이벤트
        yield _format_sse_event("start", {
            "session_id": session_id,
            "message": request.message,
            "user_id": user_info["user_id"],
            "timestamp": start_time.isoformat()
        })

        # 2. Master Agent 실행 (스트리밍)
        agent = MasterAgent()

        # 대화 기록 포맷 변환 (LangGraph용)
        formatted_history = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            for msg in conversation_history
        ]

        # 첨부파일 포맷 변환
        attachments = None
        if request.attachments:
            attachments = [att.model_dump() for att in request.attachments]

        # 스트리밍 실행
        async for event in agent.stream(
            message=request.message,
            session_id=session_id,
            user_context=user_context,
            attachments=attachments,
            conversation_history=formatted_history,
        ):
            # 이벤트 타입 추출
            event_type = event.get("event", "message")
            event_data = event.get("data", {})

            # 이벤트별 처리
            if event_type == "intent_classified":
                intent_category = event_data.get("category", "UNKNOWN")

            elif event_type == "execution_plan":
                workflows_used = event_data.get("workflows", [])

            elif event_type == "complete":
                final_response = event_data.get("response", "")
                workflows_used = event_data.get("workflows_used", workflows_used)

            # SSE 이벤트 전송
            yield _format_sse_event(event_type, event_data)

        # 3. 완료 후 처리
        execution_time = (datetime.now() - start_time).total_seconds()

        # 어시스턴트 메시지 저장
        try:
            await add_assistant_message(
                session_id=session_id,
                content=final_response,
                metadata={
                    "intent": intent_category,
                    "workflows_used": workflows_used,
                    "execution_time": execution_time,
                }
            )
        except Exception as e:
            logger.warning(f"[stream] Failed to save assistant message: {e}")

        # 사용량 기록
        try:
            await record_usage(
                user_id=user_info["user_id"],
                organization_id=user_info.get("organization_id"),
                workflows=workflows_used,
                execution_time=execution_time,
            )
        except Exception as e:
            logger.warning(f"[stream] Failed to record usage: {e}")

        # 4. 제목 자동 생성 (첫 메시지인 경우)
        generated_title = current_title
        if is_first_message and not current_title:
            try:
                # 비동기로 제목 생성 및 업데이트 (하이브리드 방식)
                generated_title = await generate_and_update_title(
                    session_id=session_id,
                    message=request.message,
                    response=final_response,
                    intent=intent_category,
                    current_title=current_title,
                )
                logger.debug(f"[stream] Title generated: {generated_title}")
            except Exception as e:
                logger.warning(f"[stream] Failed to generate title: {e}")

        # 5. 완료 이벤트 (최종)
        yield _format_sse_event("done", {
            "session_id": session_id,
            "execution_time": execution_time,
            "workflows_executed": workflows_used,
            "title": generated_title,  # 생성된 제목 포함
        })

    except Exception as e:
        logger.error(f"[stream] Error: {e}", exc_info=True)

        # 에러 이벤트 전송
        yield _format_sse_event("error", {
            "message": str(e),
            "type": type(e).__name__,
        })

        # 에러 응답 저장
        try:
            await add_assistant_message(
                session_id=session_id,
                content=f"오류가 발생했습니다: {str(e)}",
                metadata={
                    "error": True,
                    "error_type": type(e).__name__,
                }
            )
        except Exception:
            pass


async def _non_streaming_response(
    request: ChatRequest,
    session_id: str,
    user_context: UserContext,
    user_info: Dict[str, Any],
    conversation_history: List[Dict[str, Any]],
    start_time: datetime,
    is_first_message: bool = False,
    current_title: str = "",
) -> ChatResponse:
    """
    비스트리밍 응답 생성

    Master Agent를 실행하고 최종 결과만 반환합니다.
    """
    try:
        # Master Agent 실행
        agent = MasterAgent()

        # 대화 기록 포맷 변환
        formatted_history = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            for msg in conversation_history
        ]

        # 첨부파일 포맷 변환
        attachments = None
        if request.attachments:
            attachments = [att.model_dump() for att in request.attachments]

        # 동기 실행
        final_state = await agent.run(
            message=request.message,
            session_id=session_id,
            user_context=user_context,
            attachments=attachments,
            conversation_history=formatted_history,
        )

        execution_time = (datetime.now() - start_time).total_seconds()

        # 결과 추출
        intent_dict = final_state.get("intent", {})
        execution_plan = final_state.get("execution_plan", {})
        final_response_text = final_state.get("final_response", "")
        workflow_results = final_state.get("workflow_results", {})
        document_analysis = _extract_document_analysis(workflow_results)

        # Intent 정보 변환
        intent_info = IntentInfo(
            category=IntentCategory(intent_dict.get("category", "UNKNOWN")),
            sub_category=intent_dict.get("sub_category"),
            confidence=intent_dict.get("confidence", 0.0),
            extracted_params=intent_dict.get("extracted_params", {}),
        )

        workflows_used = list(workflow_results.keys())

        # 어시스턴트 메시지 저장
        try:
            await add_assistant_message(
                session_id=session_id,
                content=final_response_text,
                metadata={
                    "intent": intent_info.category.value,
                    "workflows_used": workflows_used,
                    "execution_time": execution_time,
                }
            )
        except Exception as e:
            logger.warning(f"[non-streaming] Failed to save assistant message: {e}")

        # 사용량 기록
        try:
            await record_usage(
                user_id=user_info["user_id"],
                organization_id=user_info.get("organization_id"),
                workflows=workflows_used,
                execution_time=execution_time,
            )
        except Exception as e:
            logger.warning(f"[non-streaming] Failed to record usage: {e}")

        # 제목 자동 생성 (첫 메시지인 경우)
        generated_title = current_title
        if is_first_message and not current_title:
            try:
                generated_title = await generate_and_update_title(
                    session_id=session_id,
                    message=request.message,
                    response=final_response_text,
                    intent=intent_info.category.value,
                    current_title=current_title,
                )
                logger.debug(f"[non-streaming] Title generated: {generated_title}")
            except Exception as e:
                logger.warning(f"[non-streaming] Failed to generate title: {e}")

        metadata = {
            "user_id": user_info["user_id"],
            "execution_plan": execution_plan,
            "session_title": generated_title,  # 생성된 제목 포함
        }
        if document_analysis:
            metadata["document_analysis"] = document_analysis

        return ChatResponse(
            response=final_response_text,
            format=ResponseFormat.TEXT,
            session_id=session_id,
            intent=intent_info,
            execution_time=execution_time,
            workflows_used=workflows_used,
            structured_data=workflow_results if workflow_results else None,
            metadata=metadata,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"[non-streaming] Error: {e}", exc_info=True)

        # 에러 응답 저장
        try:
            await add_assistant_message(
                session_id=session_id,
                content=f"오류가 발생했습니다: {str(e)}",
                metadata={"error": True}
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


def _format_sse_event(event: str, data: Dict[str, Any]) -> str:
    """SSE 이벤트 포맷"""
    event_data = {
        "event": event,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    return f"event: {event}\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    user_info: Dict[str, Any] = Depends(verify_token)
):
    """
    새 세션 생성 (인증 필수)

    Headers:
        Authorization: Bearer {jwt_token}

    Args:
        request: 세션 생성 요청
        user_info: JWT에서 추출한 사용자 정보

    Returns:
        생성된 세션 정보
    """
    try:
        logger.info(f"[agent-hub/sessions] Creating session for user={user_info['user_id']}")

        # 조직/프로젝트 접근 권한 확인
        if request.organization_id:
            if request.organization_id != user_info.get("organization_id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="해당 조직에 대한 접근 권한이 없습니다"
                )

        session_service = get_session_service()

        try:
            session_id = await session_service.create_session(
                user_id=user_info["user_id"],
                organization_id=request.organization_id or user_info.get("organization_id"),
                project_id=request.project_id
            )
        except Exception as e:
            logger.error(f"Redis 세션 생성 실패: {e}")
            # 폴백: 메모리 기반 세션
            session_id = generate_session_id()

        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=12)
        title = request.title or "새 대화"

        await ensure_session_record(
            session_id=session_id,
            user_id=user_info["user_id"],
            organization_id=request.organization_id or user_info.get("organization_id"),
            project_id=request.project_id,
            title=title,
        )

        return SessionResponse(
            session_id=session_id,
            created_at=created_at.isoformat(),
            expires_at=expires_at.isoformat(),
            organization_id=request.organization_id or user_info.get("organization_id"),
            project_id=request.project_id,
            title=title,
            updated_at=created_at.isoformat(),
            user_id=user_info["user_id"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[agent-hub/sessions] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sessions/{session_id}/history", response_model=HistoryResponse)
async def get_session_history(
    session_id: str,
    limit: int = 10,
    user_info: Dict[str, Any] = Depends(verify_token)
):
    """
    세션 대화 기록 조회 (인증 필수)

    Headers:
        Authorization: Bearer {jwt_token}

    Args:
        session_id: 세션 ID
        limit: 조회할 메시지 수
        user_info: JWT에서 추출한 사용자 정보

    Returns:
        대화 기록
    """
    try:
        logger.info(f"[agent-hub/sessions/{session_id}/history] user={user_info['user_id']}, limit={limit}")

        session_service = get_session_service()
        owner_id = None
        try:
            session = await session_service.get_session(session_id)
            if session:
                owner_id = session.get("user_id")
        except Exception as e:
            logger.warning(f"세션 확인 실패 (Redis): {e}")

        db_session = await get_session_record(session_id)
        if db_session and owner_id is None:
            owner_id = str(db_session.user_id)

        if owner_id and owner_id != user_info["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 세션에 대한 접근 권한이 없습니다"
            )

        if owner_id is None and db_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다"
            )

        messages, total_messages = await fetch_persistent_history(session_id, limit=limit)

        if not messages:
            conversation_service = get_conversation_service()
            try:
                redis_messages = await conversation_service.get_history(session_id, limit=limit)
                messages = [
                    {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                        "timestamp": msg.get("timestamp", ""),
                        "metadata": msg.get("metadata", {}),
                    }
                    for msg in redis_messages
                ]
                total_messages = len(messages)
            except Exception as e:
                logger.warning(f"대화 기록 조회 실패: {e}")
                messages = []
                total_messages = 0

        message_items = [
            MessageItem(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", ""),
                metadata=msg.get("metadata", {})
            )
            for msg in messages
        ]

        return HistoryResponse(
            session_id=session_id,
            messages=message_items,
            total_messages=total_messages
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[agent-hub/sessions/{session_id}/history] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user_info: Dict[str, Any] = Depends(verify_token)
):
    """
    세션 삭제 (인증 필수)

    Headers:
        Authorization: Bearer {jwt_token}

    Args:
        session_id: 세션 ID
        user_info: JWT에서 추출한 사용자 정보

    Returns:
        삭제 결과
    """
    try:
        logger.info(f"[agent-hub/sessions/{session_id}] user={user_info['user_id']} deleting session")

        # 세션 소유권 확인
        session_service = get_session_service()
        owner_id = None
        try:
            session = await session_service.get_session(session_id)
            if session:
                owner_id = session.get("user_id")
        except Exception as e:
            logger.warning(f"세션 확인 실패 (Redis): {e}")

        db_session = await get_session_record(session_id)
        if db_session and owner_id is None:
            owner_id = str(db_session.user_id)

        if owner_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다"
            )

        if owner_id != user_info["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 세션에 대한 접근 권한이 없습니다"
            )

        try:
            deleted = await session_service.delete_session(session_id)
            if not deleted:
                logger.debug(f"세션 삭제 스킵 (Redis 없음): {session_id}")
        except Exception as e:
            logger.error(f"세션 삭제 중 오류: {e}")

        convo_service = get_conversation_service()
        try:
            await convo_service.clear_history(session_id)
        except Exception:
            pass

        await delete_session_record(session_id)

        return {
            "message": "세션이 삭제되었습니다",
            "session_id": session_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[agent-hub/sessions/{session_id}] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities():
    """
    Agent Hub 기능 목록 조회

    사용 가능한 워크플로우, 의도 카테고리, 권한 요구사항 등을 반환합니다.

    Returns:
        기능 목록
    """
    try:
        logger.info("[agent-hub/capabilities] Getting capabilities")

        workflows = [
            WorkflowCapability(
                name=name,
                description=config["description"],
                required_roles=config["required_roles"],
                quota_weight=config["quota_weight"],
                supports_streaming=config["supports_streaming"]
            )
            for name, config in WORKFLOW_PERMISSIONS.items()
        ]

        intent_categories = [category.value for category in IntentCategory]

        return CapabilitiesResponse(
            workflows=workflows,
            intent_categories=intent_categories,
            version="v2.0.0",
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"[agent-hub/capabilities] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/health")
async def agent_hub_health():
    """
    Agent Hub 헬스체크

    Returns:
        상태 정보
    """
    # 서비스 연결 상태 확인
    services_status = {}

    try:
        session_service = get_session_service()
        services_status["session_service"] = "connected" if session_service.is_connected() else "disconnected"
    except Exception:
        services_status["session_service"] = "error"

    try:
        conversation_service = get_conversation_service()
        services_status["conversation_service"] = "connected" if conversation_service.is_connected() else "disconnected"
    except Exception:
        services_status["conversation_service"] = "error"

    try:
        usage_service = get_usage_service()
        services_status["usage_service"] = "connected" if usage_service.is_connected() else "disconnected"
    except Exception:
        services_status["usage_service"] = "error"

    return {
        "status": "healthy",
        "version": "v2",
        "engine": "Master Agent Orchestrator",
        "features": [
            "intent_classification",
            "workflow_routing",
            "sse_streaming",
            "session_management",
            "conversation_history",
            "usage_quota",
            "jwt_authentication",
            "rbac"
        ],
        "implementation_status": {
            "api_router": "completed",
            "auth_middleware": "completed",
            "master_agent": "completed",
            "session_service": "completed",
            "conversation_service": "completed",
            "usage_service": "completed",
            "sse_streaming": "completed"
        },
        "services": services_status,
        "timestamp": datetime.now().isoformat()
    }


# ===== 추가 엔드포인트 (프론트엔드 호환) =====

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    project_id: Optional[str] = None,
    user_info: Dict[str, Any] = Depends(verify_token)
):
    """
    세션 목록 조회 (인증 필수)

    Headers:
        Authorization: Bearer {jwt_token}

    Args:
        page: 페이지 번호 (1부터 시작)
        page_size: 페이지 크기
        project_id: 프로젝트 ID로 필터 (선택)
        user_info: JWT에서 추출한 사용자 정보

    Returns:
        세션 목록
    """
    try:
        logger.info(f"[agent-hub/sessions] Listing sessions for user={user_info['user_id']}")

        db_sessions, total = await list_persistent_sessions(
            user_id=user_info["user_id"],
            page=page,
            page_size=page_size,
            project_id=project_id,
        )

        session_responses: List[SessionResponse] = []

        if not db_sessions and total == 0:
            session_service = get_session_service()
            try:
                redis_sessions = await session_service.list_user_sessions(
                    user_id=user_info["user_id"],
                    project_id=project_id,
                    page=page,
                    page_size=page_size
                )
                for session in redis_sessions.get("sessions", []):
                    session_responses.append(SessionResponse(
                        session_id=session.get("session_id", ""),
                        created_at=session.get("created_at", datetime.now().isoformat()),
                        expires_at=session.get("expires_at", (datetime.now() + timedelta(hours=12)).isoformat()),
                        organization_id=session.get("organization_id"),
                        project_id=session.get("project_id"),
                        title=session.get("title"),
                        updated_at=session.get("updated_at"),
                        message_count=session.get("message_count", 0),
                        user_id=session.get("user_id"),
                    ))
                total = redis_sessions.get("total", len(session_responses))
            except Exception as e:
                logger.warning(f"세션 목록 조회 실패 (Redis): {e}")

        for session in db_sessions:
            session_responses.append(
                SessionResponse(
                    session_id=str(session.session_id),
                    created_at=(session.created_at or datetime.now()).isoformat(),
                    expires_at=((session.last_activity or datetime.now()) + timedelta(hours=12)).isoformat(),
                    organization_id=str(session.organization_id) if session.organization_id else None,
                    project_id=str(session.project_id) if session.project_id else None,
                    title=session.title or "새 대화",
                    updated_at=(session.last_activity or session.created_at or datetime.now()).isoformat(),
                    message_count=session.total_messages,
                    last_message=session.last_message_preview or None,
                    user_id=str(session.user_id),
                )
            )

        has_next = (page * page_size) < total

        return SessionListResponse(
            sessions=session_responses,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[agent-hub/sessions] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user_info: Dict[str, Any] = Depends(verify_token)
):
    """
    세션 조회 (인증 필수)

    Headers:
        Authorization: Bearer {jwt_token}

    Args:
        session_id: 세션 ID
        user_info: JWT에서 추출한 사용자 정보

    Returns:
        세션 정보
    """
    try:
        logger.info(f"[agent-hub/sessions/{session_id}] Getting session for user={user_info['user_id']}")

        db_session = await get_session_record(session_id)
        owner_id = str(db_session.user_id) if db_session else None

        session_data = None
        if db_session:
            session_data = SessionResponse(
                session_id=str(db_session.session_id),
                created_at=(db_session.created_at or datetime.now()).isoformat(),
                expires_at=((db_session.last_activity or datetime.now()) + timedelta(hours=12)).isoformat(),
                organization_id=str(db_session.organization_id) if db_session.organization_id else None,
                project_id=str(db_session.project_id) if db_session.project_id else None,
                title=db_session.title or "새 대화",
                updated_at=(db_session.last_activity or db_session.created_at or datetime.now()).isoformat(),
                message_count=db_session.total_messages,
                last_message=db_session.last_message_preview or None,
                user_id=str(db_session.user_id),
            )

        if session_data is None:
            session_service = get_session_service()
            session = await session_service.get_session(session_id)
            if session:
                owner_id = session.get("user_id")
                session_data = SessionResponse(
                    session_id=session.get("session_id", session_id),
                    created_at=session.get("created_at", datetime.now().isoformat()),
                    expires_at=session.get("expires_at", (datetime.now() + timedelta(hours=12)).isoformat()),
                    organization_id=session.get("organization_id"),
                    project_id=session.get("project_id"),
                    title=session.get("title"),
                    updated_at=session.get("updated_at"),
                    message_count=session.get("message_count", 0),
                    user_id=session.get("user_id"),
                )

        if session_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다"
            )

        if owner_id and owner_id != user_info["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 세션에 대한 접근 권한이 없습니다"
            )

        return session_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[agent-hub/sessions/{session_id}] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    user_info: Dict[str, Any] = Depends(verify_token)
):
    """
    세션 업데이트 (인증 필수)

    Headers:
        Authorization: Bearer {jwt_token}

    Args:
        session_id: 세션 ID
        request: 업데이트 요청
        user_info: JWT에서 추출한 사용자 정보

    Returns:
        업데이트된 세션 정보
    """
    try:
        logger.info(f"[agent-hub/sessions/{session_id}] Updating session for user={user_info['user_id']}")

        session_service = get_session_service()

        db_session = await get_session_record(session_id)
        owner_id = str(db_session.user_id) if db_session else None

        try:
            redis_session = await session_service.get_session(session_id)
            if redis_session and owner_id is None:
                owner_id = redis_session.get("user_id")
        except Exception as e:
            logger.warning(f"세션 조회 실패 (Redis): {e}")

        if owner_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다"
            )

        if owner_id != user_info["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 세션에 대한 접근 권한이 없습니다"
            )

        update_data: Dict[str, Any] = {}
        if request.title is not None:
            update_data["title"] = request.title
        if request.project_id is not None:
            update_data["project_id"] = request.project_id

        if update_data:
            update_data["last_activity"] = datetime.now()
            await update_session_metadata(session_id, update_data)
            try:
                await session_service.update_session(session_id, {
                    key: value for key, value in update_data.items() if key in {"title", "project_id"}
                })
            except Exception as e:
                logger.warning(f"Redis 세션 업데이트 실패: {e}")

        latest_session = await get_session_record(session_id)
        if not latest_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다"
            )

        return SessionResponse(
            session_id=str(latest_session.session_id),
            created_at=(latest_session.created_at or datetime.now()).isoformat(),
            expires_at=((latest_session.last_activity or datetime.now()) + timedelta(hours=12)).isoformat(),
            organization_id=str(latest_session.organization_id) if latest_session.organization_id else None,
            project_id=str(latest_session.project_id) if latest_session.project_id else None,
            title=latest_session.title or "새 대화",
            updated_at=(latest_session.last_activity or datetime.now()).isoformat(),
            message_count=latest_session.total_messages,
            last_message=latest_session.last_message_preview or None,
            user_id=str(latest_session.user_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[agent-hub/sessions/{session_id}] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ===== Save Analysis Models =====

class RiskItemInput(BaseModel):
    """리스크 항목 입력"""
    category: str = Field(..., description="리스크 카테고리")
    title: str = Field(..., description="리스크 제목")
    description: str = Field(..., description="리스크 설명")
    severity: str = Field("MEDIUM", description="심각도 (CRITICAL, HIGH, MEDIUM, LOW, INFO)")
    score: int = Field(50, description="점수 (0-100)")
    clause_reference: Optional[str] = Field(None, description="관련 조항")


class ClauseInput(BaseModel):
    """조항 입력"""
    clause_type: str = Field(..., description="조항 타입")
    title: str = Field(..., description="조항 제목")
    content: str = Field(..., description="조항 내용")
    importance_score: int = Field(50, description="중요도 점수 (0-100)")


class SaveAnalysisRequest(BaseModel):
    """분석 결과 저장 요청"""
    session_id: str = Field(..., description="세션 ID")
    message_id: Optional[str] = Field(None, description="메시지 ID")

    # 문서 정보
    title: str = Field(..., description="문서 제목")
    doc_type: str = Field("OTHER", description="문서 타입 (CONTRACT, CASE, STATUTE, PRECEDENT, OTHER)")
    original_text: str = Field(..., description="원본 텍스트")

    # 분석 결과 (선택적)
    summary: Optional[str] = Field(None, description="요약")
    clauses: Optional[List[ClauseInput]] = Field(None, description="추출된 조항")
    risk_analysis: Optional[Dict[str, Any]] = Field(None, description="리스크 분석 결과")


class SaveAnalysisResponse(BaseModel):
    """분석 결과 저장 응답"""
    success: bool
    document_id: str
    document_url: str
    message: str
    saved_items: Dict[str, bool] = Field(default_factory=dict)


@router.post("/save-analysis", response_model=SaveAnalysisResponse)
async def save_analysis_to_documents(
    request: SaveAnalysisRequest,
    user_info: Dict[str, Any] = Depends(verify_token)
):
    """
    Agent Hub 분석 결과를 Documents 시스템에 저장

    Agent Hub에서 문서 분석 후 사용자가 '저장' 버튼을 클릭하면
    분석 결과를 Django Documents 시스템에 영구 저장합니다.

    Flow:
    1. Django에 문서 생성 (텍스트 기반)
    2. 요약이 있으면 Summary 저장
    3. 조항이 있으면 KeyClause 저장
    4. 리스크 분석이 있으면 RiskAnalysisResult 저장

    Headers:
        Authorization: Bearer {jwt_token}

    Returns:
        SaveAnalysisResponse: 저장 결과
    """
    from apps.ai_service.config.settings import settings

    logger.info(
        f"[agent-hub/save-analysis] user={user_info['user_id']}, "
        f"title='{request.title}', doc_type={request.doc_type}"
    )

    try:
        backend_url = settings.BACKEND_API_URL

        # 1. Django에 문서 생성 요청
        # 내부 서비스 간 통신이므로 서비스 인증 헤더 사용
        headers = {
            "Content-Type": "application/json",
            "X-Service-Auth": "agent-hub-internal",
            "X-User-Id": user_info["user_id"],
            "X-Organization-Id": user_info.get("organization_id", ""),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 문서 생성 (텍스트 기반)
            create_response = await client.post(
                f"{backend_url}/api/v1/documents/create-from-text/",
                json={
                    "title": request.title,
                    "doc_type": request.doc_type,
                    "text_content": request.original_text,
                    "source_type": "AGENT_HUB",
                    "metadata": {
                        "session_id": request.session_id,
                        "message_id": request.message_id,
                        "created_from": "agent_hub_save"
                    }
                },
                headers=headers
            )

            if create_response.status_code not in [200, 201]:
                logger.error(
                    f"Failed to create document: {create_response.status_code} - "
                    f"{create_response.text}"
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"문서 생성 실패: {create_response.text}"
                )

            doc_result = create_response.json()
            document_id = doc_result.get("document", {}).get("id") or doc_result.get("id")

            if not document_id:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="문서 ID를 받지 못했습니다"
                )

            saved_items = {"document": True}

            # 2. 요약 저장
            if request.summary:
                try:
                    summary_response = await client.post(
                        f"{backend_url}/api/v1/documents/{document_id}/save-summary/",
                        json={
                            "content": request.summary,
                            "summary_type": "GLOBAL",
                            "llm_model": "agent-hub",
                            "source": "agent_hub"
                        },
                        headers=headers
                    )
                    saved_items["summary"] = summary_response.status_code in [200, 201]
                    if not saved_items["summary"]:
                        logger.warning(f"Summary save failed: {summary_response.text}")
                except Exception as e:
                    logger.warning(f"Summary save error: {e}")
                    saved_items["summary"] = False

            # 3. 조항 저장
            if request.clauses:
                try:
                    clauses_data = [
                        {
                            "clause_type": c.clause_type,
                            "title": c.title,
                            "content": c.content,
                            "importance_score": c.importance_score
                        }
                        for c in request.clauses
                    ]
                    clauses_response = await client.post(
                        f"{backend_url}/api/v1/documents/{document_id}/save_selected_clauses/",
                        json={
                            "clauses": clauses_data,
                            "llm_model": "agent-hub"
                        },
                        headers=headers
                    )
                    saved_items["clauses"] = clauses_response.status_code in [200, 201]
                    if not saved_items["clauses"]:
                        logger.warning(f"Clauses save failed: {clauses_response.text}")
                except Exception as e:
                    logger.warning(f"Clauses save error: {e}")
                    saved_items["clauses"] = False

            # 4. 리스크 분석 저장
            if request.risk_analysis:
                try:
                    risk_response = await client.post(
                        f"{backend_url}/api/v1/documents/{document_id}/save-risk-analysis/",
                        json={
                            "overall_risk_score": request.risk_analysis.get("overall_risk_score", 50),
                            "severity": request.risk_analysis.get("severity", "MEDIUM"),
                            "risk_items": request.risk_analysis.get("risk_items", []),
                            "recommendations": request.risk_analysis.get("recommendations", []),
                            "summary": request.risk_analysis.get("summary", ""),
                            "llm_model": "agent-hub",
                            "source": "agent_hub"
                        },
                        headers=headers
                    )
                    saved_items["risk_analysis"] = risk_response.status_code in [200, 201]
                    if not saved_items["risk_analysis"]:
                        logger.warning(f"Risk analysis save failed: {risk_response.text}")
                except Exception as e:
                    logger.warning(f"Risk analysis save error: {e}")
                    saved_items["risk_analysis"] = False

            # 문서 URL 생성
            document_url = f"/documents/{document_id}"

            logger.info(
                f"[agent-hub/save-analysis] Saved document {document_id}: "
                f"saved_items={saved_items}"
            )

            return SaveAnalysisResponse(
                success=True,
                document_id=document_id,
                document_url=document_url,
                message="분석 결과가 저장되었습니다",
                saved_items=saved_items
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[agent-hub/save-analysis] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/suggestions", response_model=List[SuggestedQuestion])
async def get_suggestions(
    session_id: Optional[str] = None,
    limit: int = 5,
    user_info: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    추천 질문 조회

    세션 ID가 제공되면 해당 세션의 컨텍스트에 맞는 질문을,
    없으면 일반적인 추천 질문을 반환합니다.

    Args:
        session_id: 세션 ID (선택)
        limit: 반환할 질문 수
        user_info: 사용자 정보 (선택)

    Returns:
        추천 질문 목록
    """
    try:
        logger.info(f"[agent-hub/suggestions] Getting suggestions, session_id={session_id}")

        # 기본 추천 질문 (법률 서비스에 맞는 질문들)
        default_questions = [
            SuggestedQuestion(
                id="q1",
                text="최근 대법원 판례 중 주요한 것들을 알려주세요",
                category="판례검색"
            ),
            SuggestedQuestion(
                id="q2",
                text="계약서 작성 시 주의해야 할 사항은 무엇인가요?",
                category="계약"
            ),
            SuggestedQuestion(
                id="q3",
                text="근로기준법상 연차휴가 규정에 대해 설명해주세요",
                category="노동법"
            ),
            SuggestedQuestion(
                id="q4",
                text="부동산 매매 계약 시 체크리스트를 알려주세요",
                category="부동산"
            ),
            SuggestedQuestion(
                id="q5",
                text="형사사건에서 변호인의 역할은 무엇인가요?",
                category="형사법"
            ),
            SuggestedQuestion(
                id="q6",
                text="상속법의 기본 원칙에 대해 설명해주세요",
                category="상속"
            ),
            SuggestedQuestion(
                id="q7",
                text="개인정보보호법 위반 시 처벌 규정은 어떻게 되나요?",
                category="개인정보"
            ),
            SuggestedQuestion(
                id="q8",
                text="민사소송 절차에 대해 간략히 설명해주세요",
                category="민사소송"
            ),
        ]

        # 세션이 있으면 컨텍스트 기반 추천 (간단한 구현)
        if session_id and user_info:
            try:
                conversation_service = get_conversation_service()
                history = await conversation_service.get_history(session_id, limit=5)

                if history:
                    # 최근 대화 기반 추천 질문 생성 (간단한 로직)
                    last_message = history[-1].get("content", "") if history else ""

                    if "계약" in last_message:
                        return [
                            SuggestedQuestion(id="ctx1", text="계약 해지 시 주의사항은?", category="계약"),
                            SuggestedQuestion(id="ctx2", text="계약 불이행 시 구제 방법은?", category="계약"),
                            SuggestedQuestion(id="ctx3", text="표준계약서 양식을 보여주세요", category="계약"),
                        ][:limit]
                    elif "판례" in last_message or "판결" in last_message:
                        return [
                            SuggestedQuestion(id="ctx1", text="유사 판례를 더 검색해주세요", category="판례검색"),
                            SuggestedQuestion(id="ctx2", text="이 판례의 법적 의미를 분석해주세요", category="판례검색"),
                            SuggestedQuestion(id="ctx3", text="관련 하급심 판결도 알려주세요", category="판례검색"),
                        ][:limit]
            except Exception as e:
                logger.warning(f"컨텍스트 기반 추천 생성 실패: {e}")

        return default_questions[:limit]

    except Exception as e:
        logger.error(f"[agent-hub/suggestions] Error: {e}", exc_info=True)
        # 에러 발생 시에도 기본 질문 반환
        return [
            SuggestedQuestion(id="default", text="법률 관련 질문을 해보세요", category="일반")
        ]
