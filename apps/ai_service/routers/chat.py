"""
Chat Router
RAG 챗봇 API 엔드포인트
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from models.database import get_db
from services.feedback_adapter import DatabaseFeedbackProvider
from libs.rag_core import filter_results
from libs.rag_core.llm.orchestrator import LegalRAGOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/chat", tags=["chat"])

# ===== Request/Response Models =====

class RAGFilterOptions(BaseModel):
    """RAG 검색 필터 옵션 (Session 13-C)"""
    doc_types: Optional[List[str]] = Field(
        None,
        description="문서 타입 필터 (CONTRACT, CASE, STATUTE, PRECEDENT, OTHER)"
    )
    statuses: Optional[List[str]] = Field(
        None,
        description="문서 상태 필터 (UPLOADED, PREPROCESSED, EMBEDDED)"
    )
    date_from: Optional[str] = Field(
        None,
        description="시작 날짜 (YYYY-MM-DD)"
    )
    date_to: Optional[str] = Field(
        None,
        description="종료 날짜 (YYYY-MM-DD)"
    )
    keyword: Optional[str] = Field(
        None,
        description="키워드 검색 (문서 제목만)"
    )
    document_ids: Optional[List[str]] = Field(
        None,
        description="사전 필터링된 문서 ID 목록"
    )


class RAGRequest(BaseModel):
    """RAG 질의응답 요청"""
    query: str = Field(..., description="사용자 질문", min_length=1)
    top_k: Optional[int] = Field(None, description="검색할 문서 수 (자동 결정)", ge=1, le=10)
    include_sources: bool = Field(True, description="출처 포함 여부")
    enable_critique: Optional[bool] = Field(None, description="Constitutional AI 활성화 (자동 결정)")
    filters: Optional[RAGFilterOptions] = Field(
        None,
        description="검색 필터 옵션 (Session 13-C)"
    )

class Source(BaseModel):
    """출처 정보"""
    source: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}

class RAGResponse(BaseModel):
    """RAG 질의응답 응답"""
    answer: str
    sources: List[Source]
    query: str
    model: str
    timestamp: str
    critique_log: Optional[List[Dict[str, Any]]] = None
    response_mode: Optional[str] = None  # 사용된 응답 모드 (Orchestrator가 자동 결정)

# ===== Helper Functions =====

def apply_document_filters(
    sources: List[Dict[str, Any]],
    filters: RAGFilterOptions
) -> List[Dict[str, Any]]:
    """
    Session 13-C: 문서 필터 적용

    ChromaDB 메타데이터 스키마:
    - doc_title: 문서 제목
    - doc_doc_type: 문서 타입 (CONTRACT, CASE, STATUTE, PRECEDENT, OTHER)
    - doc_language: 언어
    - doc_file_type: 파일 타입
    - document_id: 문서 ID

    Note: status와 created_at은 Django DB에만 존재하므로
          document_ids 필터로 사전 필터링된 ID 목록을 받아 처리

    Args:
        sources: RAG 검색 결과 (각 source는 metadata 딕셔너리 포함)
        filters: 필터 옵션

    Returns:
        필터링된 sources 목록
    """
    if not sources:
        return sources

    filtered = sources

    # 1. 문서 타입 필터 (doc_doc_type)
    if filters.doc_types:
        filtered = [
            s for s in filtered
            if s.get('metadata', {}).get('doc_doc_type') in filters.doc_types
        ]
        logger.debug(f"After doc_types filter: {len(filtered)} sources")

    # 2. 키워드 필터 (doc_title에서 검색 - 대소문자 무시)
    if filters.keyword:
        keyword_lower = filters.keyword.lower()
        filtered = [
            s for s in filtered
            if keyword_lower in s.get('metadata', {}).get('doc_title', '').lower()
        ]
        logger.debug(f"After keyword filter: {len(filtered)} sources")

    # 3. 문서 ID 필터 (Django에서 status/date로 사전 필터링된 ID 목록)
    if filters.document_ids:
        doc_id_set = set(filters.document_ids)
        filtered = [
            s for s in filtered
            if s.get('metadata', {}).get('document_id') in doc_id_set
        ]
        logger.debug(f"After document_ids filter: {len(filtered)} sources")

    return filtered


# ===== API Endpoints =====

@router.post("/rag", response_model=RAGResponse)
async def rag_chat(
    request: RAGRequest,
    app_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    RAG 기반 질의응답

    - Constitutional AI 적용
    - Hybrid Retrieval (Semantic + BM25)
    - Feedback-based filtering

    인증:
        - 이 엔드포인트는 인증이 없습니다
        - Django Backend에서 이미 JWT 검증을 수행했다고 가정
        - user_id는 헤더로 전달받음: X-User-ID (선택)

    Args:
        request: RAG 요청 (query, top_k, include_sources)
        app_request: FastAPI Request 객체
        db: DB 세션 (피드백 조회용)

    Returns:
        RAG 응답 (answer, sources, metadata)
    """
    try:
        # AI 컴포넌트 가져오기
        chatbot = app_request.app.state.chatbot
        if not chatbot:
            raise HTTPException(
                status_code=503,
                detail="AI chatbot is not available. Please check LLM_API_KEY configuration."
            )

        # 사용자 ID (선택)
        user_id = app_request.headers.get("X-User-ID")
        if user_id:
            logger.info(f"📨 RAG request from user {user_id}: {request.query[:50]}...")
        else:
            logger.info(f"📨 RAG request (anonymous): {request.query[:50]}...")

        # 1. Orchestrator 생성 (기존 chatbot 래핑)
        # Orchestrator가 질문을 분석하여 응답 모드를 자동 결정
        orchestrator = LegalRAGOrchestrator(chatbot=chatbot)

        # 2. 피드백 필터 적용 (DB에서 제외할 판례 ID 조회)
        feedback_provider = DatabaseFeedbackProvider(db)
        excluded_ids = await feedback_provider.get_excluded_ids()

        # top_k 결정 (명시적 지정 또는 Orchestrator가 모드에 따라 자동 결정)
        effective_top_k = request.top_k
        if effective_top_k:
            # excluded 보정
            effective_top_k = effective_top_k + min(len(excluded_ids), 5)

        # 3. Orchestrator로 RAG 처리 (모드 자동 결정)
        enable_critique = request.enable_critique if request.enable_critique is not None else False
        orchestrator_result = orchestrator.chat(
            query=request.query,
            mode=None,  # Orchestrator가 QueryClassifier로 자동 분류
            top_k=effective_top_k,  # None이면 모드에 따라 자동
            include_critique_log=enable_critique
        )

        # Orchestrator 결과에서 필요한 값 추출
        result = {
            'answer': orchestrator_result.answer,
            'sources': orchestrator_result.sources,
            'model': chatbot.llm_client.model_name if hasattr(chatbot.llm_client, 'model_name') else 'Unknown'
        }
        response_mode = orchestrator_result.mode  # 자동 결정된 모드

        logger.info(f"🎯 Response mode: {response_mode}, strategy={orchestrator_result.strategy_used}")

        # 4. 피드백 필터 적용 (제외할 판례 제거)
        sources = result.get('sources', [])
        if excluded_ids:
            sources = filter_results(
                results=sources,
                excluded_ids=excluded_ids,
                id_key='source'
            )
            logger.info(f"🔍 Filtered {len(result['sources']) - len(sources)} precedents by feedback")

        # Session 13-C: 문서 필터 적용
        if request.filters:
            sources = apply_document_filters(sources, request.filters)
            logger.info(f"🔍 Applied document filters, remaining sources: {len(sources)}")

        # 5. top_k로 잘라내기
        final_top_k = request.top_k or len(sources)
        sources = sources[:final_top_k]

        # 6. 응답 생성
        return RAGResponse(
            answer=result['answer'],
            sources=[
                Source(
                    source=s.get('source', s.get('metadata', {}).get('doc_id', '')),
                    content=s.get('content', s.get('text', '')),
                    score=s.get('score', 0.0),
                    metadata=s.get('metadata', {})
                )
                for s in (sources if request.include_sources else [])
            ],
            query=request.query,
            model=result.get('model', 'Unknown'),
            timestamp=datetime.now().isoformat(),
            critique_log=result.get('critique_log') if enable_critique else None,
            response_mode=response_mode
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ RAG chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/health")
async def chat_health(app_request: Request):
    """Chat 라우터 헬스체크"""
    chatbot = app_request.app.state.chatbot
    return {
        "status": "healthy" if chatbot else "unavailable",
        "chatbot": "available" if chatbot else "not_initialized"
    }
