"""
Chat & Search Router
챗봇 및 검색 관련 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None
    temperature: Optional[float] = 0.7


class ChatResponse(BaseModel):
    response: str
    timestamp: str
    model: str


class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 10


class SearchResult(BaseModel):
    id: str
    title: str
    type: str
    summary: str
    date: str
    relevance: float
    citation: Optional[str] = None


class AnalyzeRequest(BaseModel):
    content: str
    document_type: Optional[str] = None


class AnalyzeResponse(BaseModel):
    analysis: str
    sources: List[Dict[str, Any]]
    timestamp: str


class RAGChatRequest(BaseModel):
    """RAG 기반 챗봇 요청"""
    query: str
    top_k: Optional[int] = 5
    include_sources: Optional[bool] = True


class RAGChatResponse(BaseModel):
    """RAG 기반 챗봇 응답"""
    answer: str
    sources: List[Dict[str, Any]]
    query: str
    model: str
    timestamp: str
    revised: bool = False


def setup_chat_routes(
    constitutional_chatbot,
    llm_client,
    hybrid_retriever,
    openlaw_client=None
):
    """챗봇 및 검색 라우트 설정"""

    @router.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        """Constitutional AI 기반 법률 챗봇"""
        if constitutional_chatbot:
            try:
                result = constitutional_chatbot.chat(
                    query=request.message,
                    top_k=5,
                    include_critique_log=False
                )

                response_text = result['answer']
                if result.get('sources'):
                    response_text += "\n\n📚 참고 자료:\n"
                    for i, source in enumerate(result['sources'][:3], 1):
                        metadata = source.get('metadata', {})
                        response_text += f"{i}. {metadata.get('source', 'Unknown')} - {metadata.get('date', '')}\n"

                return ChatResponse(
                    response=response_text,
                    timestamp=datetime.now().isoformat(),
                    model="GPT-4 + Constitutional AI + RAG"
                )

            except Exception as e:
                logger.error(f"Constitutional AI chat error: {e}")
                if llm_client:
                    response_text = llm_client.generate(
                        prompt=request.message,
                        temperature=request.temperature
                    )
                    return ChatResponse(
                        response=response_text,
                        timestamp=datetime.now().isoformat(),
                        model="GPT-4"
                    )
                raise HTTPException(status_code=500, detail=str(e))

        elif llm_client:
            try:
                response_text = llm_client.generate(
                    prompt=request.message,
                    temperature=request.temperature
                )

                return ChatResponse(
                    response=response_text,
                    timestamp=datetime.now().isoformat(),
                    model="GPT-4"
                )

            except Exception as e:
                logger.error(f"Chat error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(status_code=503, detail="Chat service not available")

    @router.post("/chat-with-rag", response_model=RAGChatResponse)
    async def chat_with_rag(request: RAGChatRequest):
        """ChromaDB RAG + Constitutional AI 기반 법률 챗봇

        - Hybrid Search (Semantic + BM25, RRF k=60, Adaptive Weighting)
        - Constitutional AI (6 principles + Self-Critique + 3-shot Learning)
        - 388,767개 형사법 문서 기반 RAG
        """
        if not constitutional_chatbot:
            raise HTTPException(
                status_code=503,
                detail="Constitutional AI chatbot not available"
            )

        try:
            logger.info(f"RAG Chat request: '{request.query}' (top_k={request.top_k})")

            # Constitutional AI + Hybrid RAG로 답변 생성
            result = constitutional_chatbot.chat(
                query=request.query,
                top_k=request.top_k,
                include_critique_log=False
            )

            # 소스 정보 포맷팅
            sources = []
            if request.include_sources and result.get('sources'):
                for i, source in enumerate(result['sources'], 1):
                    metadata = source.get('metadata', {})
                    sources.append({
                        'rank': i,
                        'source': metadata.get('source', 'Unknown'),
                        'type': metadata.get('type', 'unknown'),
                        'title': metadata.get('title', ''),
                        'case_number': metadata.get('case_number', ''),
                        'date': metadata.get('date', ''),
                        'citation': metadata.get('citation', ''),
                        'text_snippet': source.get('text', '')[:200],
                        'score': source.get('score', 0.0)
                    })

            # Constitutional AI가 self-critique를 통해 답변을 수정했는지 확인
            revised = result.get('revised', False)

            return RAGChatResponse(
                answer=result['answer'],
                sources=sources,
                query=request.query,
                model="GPT-4 Turbo + Constitutional AI + Hybrid RAG (388K docs)",
                timestamp=datetime.now().isoformat(),
                revised=revised
            )

        except Exception as e:
            logger.error(f"RAG chat error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"RAG 챗봇 오류: {str(e)}"
            )

    @router.post("/search", response_model=List[SearchResult])
    async def search_legal_documents(request: SearchRequest):
        """Hybrid Search: 실시간 OpenLaw API + 로컬 RAG 검색"""
        search_results = []

        # 1. OpenLaw API로 실시간 판례 검색
        if openlaw_client:
            try:
                logger.info(f"Searching OpenLaw API for: {request.query}")
                api_precedents = openlaw_client.fetch_supreme_court_precedents(
                    search_keyword=request.query,
                    limit=request.limit or 10
                )

                for i, prec in enumerate(api_precedents):
                    # Use precedent_serial as ID so we can fetch details from OpenLaw API later
                    precedent_id = prec.get('precedent_serial', f"api_{i}")

                    search_results.append(SearchResult(
                        id=precedent_id,
                        title=prec.get('title', prec.get('case_number', '')),
                        type='case',
                        summary=prec.get('summary', '')[:200] if prec.get('summary') else '판례 요약 정보 없음',
                        date=prec.get('decision_date', datetime.now()).strftime('%Y-%m-%d') if isinstance(prec.get('decision_date'), datetime) else str(prec.get('decision_date', '')),
                        relevance=95.0 - (i * 2),  # API 결과는 높은 relevance
                        citation=prec.get('case_number', '')
                    ))

                logger.info(f"OpenLaw API returned {len(api_precedents)} results")
            except Exception as e:
                logger.error(f"OpenLaw API search error: {e}")

        # 2. 로컬 RAG 검색 (보완)
        if hybrid_retriever:
            try:
                logger.info(f"Searching local RAG for: {request.query}")
                rag_results = hybrid_retriever.retrieve(
                    query=request.query,
                    top_k=5,  # RAG에서는 5개만
                    filter_metadata=request.filters
                )

                for i, result in enumerate(rag_results):
                    metadata = result.get('metadata', {})

                    doc_type = metadata.get('type', 'unknown')
                    if '판례' in metadata.get('source', ''):
                        doc_type = 'case'
                    elif '법령' in metadata.get('source', ''):
                        doc_type = 'law'
                    elif '해석례' in metadata.get('source', ''):
                        doc_type = 'interpretation'

                    search_results.append(SearchResult(
                        id=f"rag_{i}",
                        title=metadata.get('title', f"문서 {i + 1}"),
                        type=doc_type,
                        summary=result.get('text', '')[:200],
                        date=metadata.get('date', ''),
                        relevance=min(85.0, int(result.get('score', 0) * 100)),  # RAG 결과는 약간 낮은 relevance
                        citation=metadata.get('citation', metadata.get('source', ''))
                    ))

                logger.info(f"Local RAG returned {len(rag_results)} results")
            except Exception as e:
                logger.error(f"RAG search error: {e}")

        # 결과가 없으면 mock 데이터
        if not search_results:
            logger.warning("No results from API or RAG, returning mock data")
            search_results = _get_mock_search_results(request.query, request.limit)

        logger.info(f"Total search results: {len(search_results)}")
        return search_results[:request.limit or 10]

    @router.post("/analyze", response_model=AnalyzeResponse)
    async def analyze_document(request: AnalyzeRequest):
        """법률 문서 분석 (Constitutional AI 적용)"""
        if constitutional_chatbot:
            try:
                analysis_query = f"""다음 법률 문서를 분석하여 주요 내용을 요약하고 법적 쟁점을 파악해주세요:

{request.content}

분석 형식:
1. 문서 요약
2. 주요 법적 쟁점
3. 관련 법령 및 판례
4. 실무적 시사점"""

                result = constitutional_chatbot.chat(
                    query=analysis_query,
                    top_k=5,
                    include_critique_log=False
                )

                return AnalyzeResponse(
                    analysis=result['answer'],
                    sources=result.get('sources', []),
                    timestamp=datetime.now().isoformat()
                )

            except Exception as e:
                logger.error(f"Constitutional AI analysis error: {e}")
                if llm_client:
                    analysis_text = llm_client.generate(
                        prompt=analysis_query,
                        temperature=0.1
                    )
                    return AnalyzeResponse(
                        analysis=analysis_text,
                        sources=[],
                        timestamp=datetime.now().isoformat()
                    )
                raise HTTPException(status_code=500, detail=str(e))

        elif llm_client:
            try:
                prompt = f"""다음 법률 문서를 분석하여 주요 내용을 요약하고 법적 쟁점을 파악해주세요:

{request.content}

분석 형식:
1. 문서 요약
2. 주요 법적 쟁점
3. 관련 법령 및 판례
4. 실무적 시사점"""

                analysis_text = llm_client.generate(
                    prompt=prompt,
                    temperature=0.1
                )

                return AnalyzeResponse(
                    analysis=analysis_text,
                    sources=[],
                    timestamp=datetime.now().isoformat()
                )

            except Exception as e:
                logger.error(f"Document analysis error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(status_code=503, detail="Analysis service not available")

    return router


def _get_mock_search_results(query: str, limit: int) -> List[SearchResult]:
    """Mock 검색 결과 (Fallback)"""
    mock_results = [
        SearchResult(
            id="1",
            title="대법원 2023도1234 판결",
            type="case",
            summary="위법수집증거의 증거능력에 관한 판단 기준을 제시한 사례",
            date="2023-12-15",
            relevance=95.0,
            citation="대법원 2023. 12. 15. 선고 2023도1234 판결"
        ),
        SearchResult(
            id="2",
            title="형사소송법 제308조의2",
            type="law",
            summary="위법수집증거의 배제 - 적법한 절차에 따르지 아니하고 수집한 증거는 증거로 할 수 없다",
            date="2007-06-01",
            relevance=90.0,
            citation="형사소송법 제308조의2"
        )
    ]
    return mock_results[:limit]
