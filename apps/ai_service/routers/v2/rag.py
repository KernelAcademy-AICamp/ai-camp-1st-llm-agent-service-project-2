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

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum
import logging
import json
import asyncio

from apps.ai_service.workflows.rag_workflow import RAGWorkflow
from apps.ai_service.mcp.tools.external_tools import fetch_court_api, fetch_statute_api

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/rag", tags=["rag-v2"])


# ===== Criminal Law Filter Types (Phase 4) =====

class CrimeType(str, Enum):
    """범죄 유형"""
    THEFT = "theft"              # 절도
    FRAUD = "fraud"              # 사기
    ASSAULT = "assault"          # 폭행/상해
    MURDER = "murder"            # 살인
    DRUG = "drug"                # 마약
    SEX_CRIME = "sex_crime"      # 성범죄
    EMBEZZLEMENT = "embezzlement"  # 횡령/배임
    DUI = "dui"                  # 음주운전


class CourtLevel(str, Enum):
    """법원 레벨"""
    SUPREME = "supreme"          # 대법원
    HIGH = "high"                # 고등법원
    DISTRICT = "district"        # 지방법원


class SentenceType(str, Enum):
    """판결 유형"""
    IMPRISONMENT = "imprisonment"  # 유죄 (실형)
    SUSPENDED = "suspended"        # 유죄 (집행유예)
    FINE = "fine"                  # 벌금형
    ACQUITTAL = "acquittal"        # 무죄


class RAGFilterOptions(BaseModel):
    """RAG 검색 필터 옵션 (Phase 4 확장)"""
    doc_types: Optional[List[str]] = Field(None, description="문서 유형 필터")
    statuses: Optional[List[str]] = Field(None, description="문서 상태 필터")
    date_from: Optional[str] = Field(None, description="검색 시작일 (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="검색 종료일 (YYYY-MM-DD)")
    keyword: Optional[str] = Field(None, description="키워드 검색")
    document_ids: Optional[List[str]] = Field(None, description="문서 ID 필터")

    # 형사법 특화 필터 (Phase 4)
    crime_types: Optional[List[CrimeType]] = Field(None, description="범죄 유형 필터")
    court_level: Optional[List[CourtLevel]] = Field(None, description="법원 레벨 필터")
    sentence_type: Optional[List[SentenceType]] = Field(None, description="판결 유형 필터")


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
    doc_type: str = ""  # 판결문, 결정례, 법령, 해석례
    relevance_score: float = 0.0
    text_snippet: str = ""  # 문서 내용 미리보기 (200자)
    full_text: str = ""  # 전체 문서 내용


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
async def rag_chat_v2(request: RAGv2Request, http_request: Request):
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
        http_request: FastAPI Request (app.state 접근용)

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
                _stream_rag_response(request, http_request),
                media_type="text/event-stream"
            )

        # app.state에서 retriever 가져오기 (이미 BM25가 로드됨)
        retriever = getattr(http_request.app.state, 'retriever', None)
        logger.info(f"[v2/rag/chat] retriever from app.state: {type(retriever).__name__ if retriever else 'None'}")

        # 일반 요청
        workflow = RAGWorkflow(retriever=retriever)
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
                    doc_type=src.get("doc_type", ""),
                    relevance_score=src.get("relevance_score", 0.0),
                    text_snippet=src.get("text_snippet", ""),
                    full_text=src.get("full_text", "")
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


async def _stream_rag_response(request: RAGv2Request, http_request: Request):
    """
    스트리밍 응답 생성기

    SSE (Server-Sent Events) 형식으로 응답
    """
    try:
        # 시작 이벤트
        yield f"data: {json.dumps({'event': 'start', 'query': request.query})}\n\n"

        # app.state에서 retriever 가져오기
        retriever = getattr(http_request.app.state, 'retriever', None)
        workflow = RAGWorkflow(retriever=retriever)

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
        from apps.ai_service.workflows.rag_workflow import RAGWorkflow

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


# ===== Full Document Endpoint =====

class FullDocumentRequest(BaseModel):
    """전체 문서 조회 요청"""
    filter_field: str = Field(..., description="필터 필드 (case_number, title, source)")
    filter_value: str = Field(..., description="필터 값")


class FullDocumentResponse(BaseModel):
    """전체 문서 응답"""
    full_text: str
    chunk_count: int
    metadata: Dict[str, Any]
    timestamp: str


@router.post("/document/full", response_model=FullDocumentResponse)
async def get_full_document(request: FullDocumentRequest, http_request: Request):
    """
    문서의 전체 텍스트 조회 (모든 청크 합침)

    같은 문서의 모든 청크를 Qdrant에서 가져와서 합쳐서 반환합니다.
    메타데이터 필터(case_number, title, source 등)로 문서를 식별합니다.

    Args:
        request: 필터 필드와 값
        http_request: FastAPI Request (app.state 접근용)

    Returns:
        전체 문서 텍스트
    """
    try:
        logger.info(f"[document/full] {request.filter_field}='{request.filter_value}'")

        # app.state에서 vectordb 가져오기
        vectordb = getattr(http_request.app.state, 'vectordb', None)

        if not vectordb:
            raise HTTPException(
                status_code=503,
                detail="VectorDB not initialized"
            )

        # 필드명 매핑: API 필드명 → Qdrant 메타데이터 필드명 (여러 후보 지원)
        # 문서 유형에 따라 필드명이 다를 수 있어서 여러 후보 필드 지정
        field_mapping = {
            "case_number": ["case_num", "case_number", "사건번호"],  # 판결문/결정례의 사건번호
            "title": ["case_name", "title", "law_name"],  # 사건명/제목/법령명
            "court": ["court_name", "court", "법원명"],  # 법원명
            "date": ["sentence_date", "date", "final_date", "선고일자"],  # 판결일/날짜
            "source": ["source"],  # 소스 파일명
        }

        # 후보 필드 목록 (첫 번째 필드를 기본으로, 나머지는 fallback)
        candidate_fields = field_mapping.get(request.filter_field, [request.filter_field])
        if isinstance(candidate_fields, str):
            candidate_fields = [candidate_fields]

        logger.info(f"[document/full] Candidate fields for '{request.filter_field}': {candidate_fields}")

        # 전체 문서 조회 (여러 후보 필드로 시도)
        chunks = []
        used_field = None

        for qdrant_field in candidate_fields:
            logger.info(f"[document/full] Trying field: {qdrant_field}")
            chunks = vectordb.get_full_document(
                filter_field=qdrant_field,
                filter_value=request.filter_value,
                limit=200  # 최대 200개 청크
            )
            if chunks:
                used_field = qdrant_field
                logger.info(f"[document/full] Found {len(chunks)} chunks with field: {qdrant_field}")
                break

        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {request.filter_field}={request.filter_value} (tried fields: {candidate_fields})"
            )

        # 텍스트 합치기
        texts = [chunk['text'] for chunk in chunks]
        full_text = '\n\n'.join(texts)

        # 첫 번째 청크의 메타데이터 사용
        first_meta = chunks[0].get('metadata', {})

        return FullDocumentResponse(
            full_text=full_text,
            chunk_count=len(chunks),
            metadata={
                "title": first_meta.get("case_name", "") or first_meta.get("title", ""),
                "case_number": first_meta.get("case_num", "") or first_meta.get("case_number", ""),
                "court": first_meta.get("court_name", "") or first_meta.get("court", ""),
                "date": first_meta.get("sentence_date", "") or first_meta.get("final_date", "") or first_meta.get("date", ""),
                "doc_type": first_meta.get("doc_type", ""),
                "source": first_meta.get("source", "")
            },
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[document/full] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ===== Search Endpoint with Criminal Law Filters (Phase 4) =====

class SearchRequest(BaseModel):
    """검색 요청 모델 (형사법 필터 포함)"""
    query: str = Field(..., description="검색 쿼리", min_length=1)
    top_k: int = Field(10, description="반환할 문서 수", ge=1, le=50)
    filters: Optional[RAGFilterOptions] = Field(None, description="검색 필터")


class SearchResultItem(BaseModel):
    """검색 결과 항목"""
    id: str = ""
    case_number: str = ""
    title: str = ""
    court: str = ""
    date: str = ""
    doc_type: str = ""
    crime_type: Optional[str] = None
    sentence_type: Optional[str] = None
    relevance_score: float = 0.0
    text_snippet: str = ""


class SearchResponse(BaseModel):
    """검색 응답 모델"""
    results: List[SearchResultItem]
    total: int
    query: str
    filters_applied: Dict[str, Any]
    timestamp: str


# 법원 레벨 매핑 (API 값 → 한글)
COURT_LEVEL_MAP = {
    "supreme": "대법원",
    "high": "고등법원",
    "district": "지방법원",
}

# 범죄 유형 매핑 (API 값 → 한글 키워드)
CRIME_TYPE_KEYWORDS = {
    "theft": ["절도", "절취", "도난"],
    "fraud": ["사기", "기망", "편취"],
    "assault": ["폭행", "상해", "폭력"],
    "murder": ["살인", "살해", "사망"],
    "drug": ["마약", "향정", "대마", "필로폰", "메스암페타민"],
    "sex_crime": ["성폭력", "강간", "강제추행", "성범죄", "아동학대"],
    "embezzlement": ["횡령", "배임", "업무상횡령"],
    "dui": ["음주운전", "음주", "도로교통법위반"],
}

# 판결 유형 매핑
SENTENCE_TYPE_KEYWORDS = {
    "imprisonment": ["징역", "금고", "실형"],
    "suspended": ["집행유예", "유예"],
    "fine": ["벌금", "과료"],
    "acquittal": ["무죄", "무혐의", "공소기각"],
}


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest, http_request: Request):
    """
    문서 검색 (형사법 특화 필터 지원)

    Phase 4: 범죄 유형, 법원 레벨, 판결 유형 필터 지원

    Args:
        request: 검색 요청 (쿼리, top_k, 필터)
        http_request: FastAPI Request (app.state 접근용)

    Returns:
        검색 결과 목록
    """
    try:
        logger.info(f"[v2/rag/search] query='{request.query[:50]}...', filters={request.filters}")

        # app.state에서 retriever 가져오기 (QdrantHybridRetriever 또는 HybridRetriever)
        retriever = getattr(http_request.app.state, 'retriever', None)

        if not retriever:
            raise HTTPException(
                status_code=503,
                detail="Retriever not initialized"
            )

        # 메타데이터 필터 구성
        metadata_filter = {}
        filters_applied = {}

        if request.filters:
            # 문서 유형 필터
            if request.filters.doc_types:
                metadata_filter["type"] = {"$in": request.filters.doc_types}
                filters_applied["doc_types"] = request.filters.doc_types

            # 법원 레벨 필터 (한글 변환)
            if request.filters.court_level:
                courts = [
                    COURT_LEVEL_MAP.get(level.value, level.value)
                    for level in request.filters.court_level
                ]
                metadata_filter["court_name"] = {"$in": courts}
                filters_applied["court_level"] = [l.value for l in request.filters.court_level]

            # 범죄 유형 필터 (키워드 기반)
            if request.filters.crime_types:
                crime_keywords = []
                for crime_type in request.filters.crime_types:
                    crime_keywords.extend(CRIME_TYPE_KEYWORDS.get(crime_type.value, [crime_type.value]))
                metadata_filter["crime_type_keywords"] = crime_keywords
                filters_applied["crime_types"] = [c.value for c in request.filters.crime_types]

            # 판결 유형 필터
            if request.filters.sentence_type:
                sentence_keywords = []
                for sentence_type in request.filters.sentence_type:
                    sentence_keywords.extend(SENTENCE_TYPE_KEYWORDS.get(sentence_type.value, [sentence_type.value]))
                metadata_filter["sentence_type_keywords"] = sentence_keywords
                filters_applied["sentence_type"] = [s.value for s in request.filters.sentence_type]

            # 날짜 범위 필터
            if request.filters.date_from or request.filters.date_to:
                date_filter = {}
                if request.filters.date_from:
                    date_filter["$gte"] = request.filters.date_from
                if request.filters.date_to:
                    date_filter["$lte"] = request.filters.date_to
                if date_filter:
                    metadata_filter["sentence_date"] = date_filter
                    filters_applied["date_range"] = {
                        "from": request.filters.date_from,
                        "to": request.filters.date_to
                    }

        # 검색 실행
        logger.info(f"[v2/rag/search] metadata_filter={metadata_filter}")

        # retriever.retrieve 호출 (하이브리드 검색)
        search_results = await _search_with_retriever(
            retriever=retriever,
            query=request.query,
            top_k=request.top_k,
            metadata_filter=metadata_filter if metadata_filter else None
        )

        # 결과 변환
        results = []
        for idx, result in enumerate(search_results):
            meta = result.get("metadata", {})
            results.append(SearchResultItem(
                id=str(result.get("id", idx)),
                case_number=meta.get("case_num", "") or meta.get("case_number", ""),
                title=meta.get("case_name", "") or meta.get("title", ""),
                court=meta.get("court_name", "") or meta.get("court", ""),
                date=meta.get("sentence_date", "") or meta.get("date", ""),
                doc_type=meta.get("doc_type", "") or meta.get("type", ""),
                crime_type=meta.get("crime_type"),
                sentence_type=meta.get("sentence_type"),
                relevance_score=result.get("score", 0.0),
                text_snippet=result.get("text", "")[:200] if result.get("text") else ""
            ))

        return SearchResponse(
            results=results,
            total=len(results),
            query=request.query,
            filters_applied=filters_applied,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[v2/rag/search] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


async def _search_with_retriever(
    retriever,
    query: str,
    top_k: int,
    metadata_filter: Optional[Dict] = None
) -> List[Dict]:
    """
    Retriever를 사용한 하이브리드 검색 (QdrantHybridRetriever 또는 HybridRetriever)

    범죄 유형/판결 유형은 키워드 기반으로 후처리 필터링
    """
    import asyncio

    # 키워드 기반 필터는 별도 처리
    crime_keywords = metadata_filter.pop("crime_type_keywords", None) if metadata_filter else None
    sentence_keywords = metadata_filter.pop("sentence_type_keywords", None) if metadata_filter else None

    # 메타데이터 필터 변환 (Qdrant 형식으로)
    filter_dict = None
    if metadata_filter:
        filter_dict = {}
        for key, value in metadata_filter.items():
            if isinstance(value, dict):
                # {"$in": [...]} 형식 처리
                if "$in" in value:
                    filter_dict[key] = value["$in"]
                elif "$gte" in value or "$lte" in value:
                    # 날짜 범위는 현재 지원하지 않음 (TODO)
                    pass
                else:
                    filter_dict[key] = value
            else:
                filter_dict[key] = value

    # Retriever 검색 실행 (동기 함수를 비동기로 실행)
    try:
        search_limit = top_k * 2 if (crime_keywords or sentence_keywords) else top_k

        # QdrantHybridRetriever.retrieve()는 동기 함수
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: retriever.retrieve(
                query=query,
                top_k=search_limit,
                filter_metadata=filter_dict if filter_dict else None
            )
        )
    except Exception as e:
        logger.warning(f"[_search_with_retriever] Search error: {e}")
        results = []

    # 키워드 기반 후처리 필터링
    if crime_keywords or sentence_keywords:
        filtered_results = []
        for result in results:
            text = result.get("text", "").lower()
            meta = result.get("metadata", {})

            # 범죄 유형 키워드 검사
            if crime_keywords:
                if not any(kw.lower() in text or kw.lower() in str(meta).lower() for kw in crime_keywords):
                    continue

            # 판결 유형 키워드 검사
            if sentence_keywords:
                if not any(kw.lower() in text or kw.lower() in str(meta).lower() for kw in sentence_keywords):
                    continue

            filtered_results.append(result)

            if len(filtered_results) >= top_k:
                break

        return filtered_results

    return results[:top_k]


async def _search_with_filters(
    vectordb,
    query: str,
    top_k: int,
    metadata_filter: Optional[Dict] = None
) -> List[Dict]:
    """
    필터가 적용된 벡터 검색 수행 (DEPRECATED - _search_with_retriever 사용 권장)

    범죄 유형/판결 유형은 키워드 기반으로 후처리 필터링
    """
    # 키워드 기반 필터는 별도 처리
    crime_keywords = metadata_filter.pop("crime_type_keywords", None) if metadata_filter else None
    sentence_keywords = metadata_filter.pop("sentence_type_keywords", None) if metadata_filter else None

    # 벡터 검색 실행 (메타데이터 필터 적용)
    try:
        # vectordb가 search 메서드를 가지고 있는지 확인
        if hasattr(vectordb, 'search'):
            results = vectordb.search(
                query=query,
                top_k=top_k * 2 if (crime_keywords or sentence_keywords) else top_k,  # 후처리 필터링을 위해 더 많이 검색
                filters=metadata_filter if metadata_filter else None
            )
        else:
            # 대체: similarity_search 사용
            results = vectordb.similarity_search(
                query=query,
                k=top_k * 2 if (crime_keywords or sentence_keywords) else top_k,
                filter=metadata_filter if metadata_filter else None
            )
            # 형식 변환
            results = [
                {
                    "id": getattr(doc, "id", idx),
                    "text": doc.page_content if hasattr(doc, "page_content") else doc.get("text", ""),
                    "metadata": doc.metadata if hasattr(doc, "metadata") else doc.get("metadata", {}),
                    "score": getattr(doc, "score", 0.0)
                }
                for idx, doc in enumerate(results)
            ]
    except Exception as e:
        logger.warning(f"[_search_with_filters] Search error: {e}, falling back to basic search")
        # 폴백: 기본 검색
        results = []

    # 키워드 기반 후처리 필터링
    if crime_keywords or sentence_keywords:
        filtered_results = []
        for result in results:
            text = result.get("text", "").lower()
            meta = result.get("metadata", {})

            # 범죄 유형 키워드 검사
            if crime_keywords:
                if not any(kw.lower() in text or kw.lower() in str(meta).lower() for kw in crime_keywords):
                    continue

            # 판결 유형 키워드 검사
            if sentence_keywords:
                if not any(kw.lower() in text or kw.lower() in str(meta).lower() for kw in sentence_keywords):
                    continue

            filtered_results.append(result)

            if len(filtered_results) >= top_k:
                break

        return filtered_results

    return results[:top_k]


# ===== 실시간 법령정보센터 API 엔드포인트 =====

class LivePrecedentSearchRequest(BaseModel):
    """실시간 판례 검색 요청"""
    keyword: Optional[str] = Field(None, description="검색 키워드")
    case_number: Optional[str] = Field(None, description="사건번호 (예: 2020도1234)")
    court: Optional[str] = Field(None, description="법원명 (예: 대법원)")
    start_date: Optional[str] = Field(None, description="선고일자 시작 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="선고일자 종료 (YYYY-MM-DD)")
    page: int = Field(1, description="페이지 번호", ge=1)
    display: int = Field(20, description="결과 개수", ge=1, le=100)
    fetch_content: bool = Field(True, description="본문 상세 조회 여부")


class LivePrecedentItem(BaseModel):
    """실시간 판례 검색 결과 항목"""
    prec_id: str = ""
    case_number: str = ""
    case_name: str = ""
    court: str = ""
    decision_date: str = ""
    case_type: str = ""
    judgment_type: str = ""
    content: str = ""
    source_url: Optional[str] = None


class LivePrecedentSearchResponse(BaseModel):
    """실시간 판례 검색 응답"""
    success: bool
    total_count: int
    precedents: List[LivePrecedentItem]
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    timestamp: str


@router.post("/live/precedents", response_model=LivePrecedentSearchResponse)
async def search_live_precedents(request: LivePrecedentSearchRequest):
    """
    실시간 판례 검색 (국가법령정보센터 API)

    국가법령정보센터 Open API를 통해 실시간으로 판례를 검색합니다.
    인덱싱된 문서가 아닌 법령정보센터의 최신 데이터를 직접 조회합니다.

    Args:
        request: 검색 조건 (키워드, 사건번호, 법원, 날짜 범위 등)

    Returns:
        실시간 판례 검색 결과

    Note:
        - 환경변수 LAW_GO_KR_OC에 API 키가 설정되어 있어야 합니다.
        - API 호출 제한이 있을 수 있습니다.
    """
    try:
        logger.info(f"[live/precedents] keyword='{request.keyword}', case_number='{request.case_number}'")

        result = await fetch_court_api(
            case_number=request.case_number,
            keyword=request.keyword,
            start_date=request.start_date,
            end_date=request.end_date,
            court=request.court,
            page=request.page,
            display=request.display,
            fetch_content=request.fetch_content
        )

        # 결과 변환
        precedents = []
        for prec in result.get("precedents", []):
            precedents.append(LivePrecedentItem(
                prec_id=prec.get("prec_id", ""),
                case_number=prec.get("case_number", ""),
                case_name=prec.get("case_name", ""),
                court=prec.get("court", ""),
                decision_date=prec.get("decision_date", ""),
                case_type=prec.get("case_type", ""),
                judgment_type=prec.get("judgment_type", ""),
                content=prec.get("content", ""),
                source_url=prec.get("source_url")
            ))

        return LivePrecedentSearchResponse(
            success=result.get("success", False),
            total_count=result.get("total_count", 0),
            precedents=precedents,
            error=result.get("error"),
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"[live/precedents] Error: {e}", exc_info=True)
        return LivePrecedentSearchResponse(
            success=False,
            total_count=0,
            precedents=[],
            error=str(e),
            timestamp=datetime.now().isoformat()
        )


class LiveStatuteSearchRequest(BaseModel):
    """실시간 법령 검색 요청"""
    keyword: Optional[str] = Field(None, description="검색 키워드")
    law_code: Optional[str] = Field(None, description="법령 MST 코드")
    law_type: Optional[str] = Field(None, description="법령 종류 (법률, 시행령, 시행규칙 등)")
    ministry: Optional[str] = Field(None, description="소관부처")
    start_date: Optional[str] = Field(None, description="시행일자 시작 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="시행일자 종료 (YYYY-MM-DD)")
    page: int = Field(1, description="페이지 번호", ge=1)
    display: int = Field(20, description="결과 개수", ge=1, le=100)
    fetch_content: bool = Field(False, description="본문 상세 조회 여부")


class LiveStatuteItem(BaseModel):
    """실시간 법령 검색 결과 항목"""
    law_id: str = ""
    law_mst: str = ""
    law_name: str = ""
    law_type: str = ""
    ministry: str = ""
    promulgation_date: str = ""
    enforcement_date: str = ""
    content: str = ""
    source_url: Optional[str] = None


class LiveStatuteSearchResponse(BaseModel):
    """실시간 법령 검색 응답"""
    success: bool
    total_count: int
    statutes: List[LiveStatuteItem]
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    timestamp: str


@router.post("/live/statutes", response_model=LiveStatuteSearchResponse)
async def search_live_statutes(request: LiveStatuteSearchRequest):
    """
    실시간 법령 검색 (국가법령정보센터 API)

    국가법령정보센터 Open API를 통해 실시간으로 법령을 검색합니다.

    Args:
        request: 검색 조건 (키워드, 법령코드, 법령종류, 소관부처 등)

    Returns:
        실시간 법령 검색 결과
    """
    try:
        logger.info(f"[live/statutes] keyword='{request.keyword}', law_type='{request.law_type}'")

        result = await fetch_statute_api(
            law_code=request.law_code,
            keyword=request.keyword,
            law_type=request.law_type,
            ministry=request.ministry,
            start_date=request.start_date,
            end_date=request.end_date,
            page=request.page,
            display=request.display,
            fetch_content=request.fetch_content
        )

        # 결과 변환
        statutes = []
        for statute in result.get("statutes", []):
            statutes.append(LiveStatuteItem(
                law_id=statute.get("law_id", ""),
                law_mst=statute.get("law_mst", ""),
                law_name=statute.get("law_name", ""),
                law_type=statute.get("law_type", ""),
                ministry=statute.get("ministry", ""),
                promulgation_date=statute.get("promulgation_date", ""),
                enforcement_date=statute.get("enforcement_date", ""),
                content=statute.get("content", ""),
                source_url=statute.get("source_url")
            ))

        return LiveStatuteSearchResponse(
            success=result.get("success", False),
            total_count=result.get("total_count", 0),
            statutes=statutes,
            error=result.get("error"),
            metadata=result.get("metadata", {}),
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"[live/statutes] Error: {e}", exc_info=True)
        return LiveStatuteSearchResponse(
            success=False,
            total_count=0,
            statutes=[],
            error=str(e),
            timestamp=datetime.now().isoformat()
        )
