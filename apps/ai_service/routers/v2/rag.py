"""
V2 RAG Router - LangGraph Based

Phase 4 - Week 11: LangGraph 기반 RAG API

특징:
- LangGraph StateGraph 기반 워크플로우
- 조건부 분기 (confidence 기반 재검색)
- 기존 v1 API와 호환성 유지
- 스트리밍 응답 지원 (선택적)

엔드포인트:
- POST /v2/rag/chat - LangGraph 기반 RAG
- GET /v2/rag/health - 헬스체크
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import json
import asyncio

from apps.ai_service.graphs.rag_graph import RAGWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/rag", tags=["rag-v2"])


# ===== Request/Response Models =====

class RAGv2Request(BaseModel):
    """RAG v2 요청 모델"""
    query: str = Field(..., description="사용자 질문", min_length=1)
    mode: Optional[str] = Field(
        "standard",
        description="응답 모드 (concise, standard, detailed)"
    )
    top_k: int = Field(5, description="검색할 문서 수", ge=1, le=10)
    include_sources: bool = Field(True, description="출처 포함 여부")
    include_critique_log: bool = Field(False, description="Critique 로그 포함 여부")
    session_id: Optional[str] = Field(None, description="세션 ID (선택)")
    stream: bool = Field(False, description="스트리밍 응답 여부")


class SourceV2(BaseModel):
    """출처 정보 (v2)"""
    case_number: str = ""
    title: str = ""
    court: str = ""
    date: str = ""
    relevance_score: float = 0.0


class RAGv2Response(BaseModel):
    """RAG v2 응답 모델"""
    answer: str
    sources: List[SourceV2]
    query: str
    mode: str
    confidence: float
    revised: bool
    processing_time: float
    iteration_count: int
    session_id: Optional[str] = None
    critique_log: Optional[str] = None
    timestamp: str
    version: str = "v2"


class RAGv2ErrorResponse(BaseModel):
    """에러 응답"""
    error: str
    detail: Optional[str] = None
    timestamp: str


# ===== API Endpoints =====

@router.post("/chat", response_model=RAGv2Response)
async def rag_chat_v2(request: RAGv2Request):
    """
    LangGraph 기반 RAG Chatbot (v2)

    워크플로우:
    1. retrieve: 문서 검색 (Hybrid Retrieval)
    2. generate: 답변 생성 (Constitutional AI)
    3. check_confidence: 신뢰도 평가
    4. critique/refine: Self-Critique (DETAILED 모드)
    5. finalize: 최종 처리

    Args:
        request: RAG v2 요청

    Returns:
        RAG v2 응답

    Note:
        - 스트리밍 응답은 stream=True로 요청
        - Critique 로그는 include_critique_log=True로 요청
    """
    try:
        logger.info(f"[v2/rag/chat] query='{request.query[:50]}...', mode={request.mode}")

        # 스트리밍 요청
        if request.stream:
            return StreamingResponse(
                _stream_rag_response(request),
                media_type="text/event-stream"
            )

        # 일반 요청
        workflow = RAGWorkflow()
        result = await workflow.arun(
            query=request.query,
            mode=request.mode or "standard",
            top_k=request.top_k,
            session_id=request.session_id,
            include_critique_log=request.include_critique_log
        )

        # 응답 생성
        sources = []
        if request.include_sources:
            for src in result.get("sources", []):
                sources.append(SourceV2(
                    case_number=src.get("case_number", ""),
                    title=src.get("title", ""),
                    court=src.get("court", ""),
                    date=src.get("date", ""),
                    relevance_score=src.get("relevance_score", 0.0)
                ))

        return RAGv2Response(
            answer=result.get("answer", ""),
            sources=sources,
            query=request.query,
            mode=request.mode or "standard",
            confidence=result.get("confidence", 0),
            revised=result.get("revised", False),
            processing_time=result.get("processing_time", 0),
            iteration_count=result.get("iteration_count", 0),
            session_id=result.get("session_id"),
            critique_log=result.get("critique_log") if request.include_critique_log else None,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"[v2/rag/chat] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


async def _stream_rag_response(request: RAGv2Request):
    """
    스트리밍 응답 생성기

    SSE (Server-Sent Events) 형식으로 응답
    """
    try:
        # 시작 이벤트
        yield f"data: {json.dumps({'event': 'start', 'query': request.query})}\n\n"

        workflow = RAGWorkflow()

        # 검색 중 이벤트
        yield f"data: {json.dumps({'event': 'retrieving', 'status': 'searching documents'})}\n\n"

        # 워크플로우 실행
        result = await workflow.arun(
            query=request.query,
            mode=request.mode or "standard",
            top_k=request.top_k,
            session_id=request.session_id,
            include_critique_log=request.include_critique_log
        )

        # 생성 중 이벤트
        yield f"data: {json.dumps({'event': 'generating', 'status': 'creating response'})}\n\n"

        # 최종 결과
        response_data = {
            "event": "complete",
            "answer": result.get("answer", ""),
            "confidence": result.get("confidence", 0),
            "revised": result.get("revised", False),
            "processing_time": result.get("processing_time", 0),
            "sources_count": len(result.get("sources", []))
        }
        yield f"data: {json.dumps(response_data)}\n\n"

        # 종료 이벤트
        yield f"data: {json.dumps({'event': 'done'})}\n\n"

    except Exception as e:
        logger.error(f"[stream] Error: {e}")
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"


@router.get("/health")
async def rag_v2_health():
    """
    RAG v2 헬스체크

    Returns:
        상태 정보
    """
    try:
        # 워크플로우 초기화 테스트
        workflow = RAGWorkflow()

        return {
            "status": "healthy",
            "version": "v2",
            "engine": "LangGraph",
            "features": [
                "conditional_routing",
                "confidence_check",
                "self_critique",
                "streaming"
            ],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"[health] Error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/compare")
async def compare_v1_v2(request: RAGv2Request):
    """
    v1 vs v2 응답 비교 (테스트용)

    동일한 쿼리로 v1(Orchestrator)과 v2(LangGraph) 응답을 비교

    Returns:
        두 버전의 응답 비교 결과
    """
    try:
        from apps.ai_service.graphs.rag_graph import RAGWorkflow

        logger.info(f"[compare] query='{request.query[:50]}...'")

        # v2 실행
        workflow = RAGWorkflow()
        v2_result = await workflow.arun(
            query=request.query,
            mode=request.mode or "standard",
            top_k=request.top_k,
            include_critique_log=True
        )

        return {
            "query": request.query,
            "mode": request.mode or "standard",
            "v2": {
                "answer": v2_result.get("answer", "")[:500] + "..." if len(v2_result.get("answer", "")) > 500 else v2_result.get("answer", ""),
                "confidence": v2_result.get("confidence", 0),
                "revised": v2_result.get("revised", False),
                "processing_time": v2_result.get("processing_time", 0),
                "iteration_count": v2_result.get("iteration_count", 0),
                "sources_count": len(v2_result.get("sources", []))
            },
            "note": "v1 comparison requires app.state.chatbot (run from main.py)",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"[compare] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
