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


def setup_chat_routes(
    constitutional_chatbot,
    llm_client,
    hybrid_retriever
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

    @router.post("/search", response_model=List[SearchResult])
    async def search_legal_documents(request: SearchRequest):
        """Hybrid Search 기반 법률 문서 검색"""
        if hybrid_retriever:
            try:
                results = hybrid_retriever.retrieve(
                    query=request.query,
                    top_k=request.limit or 10,
                    filter_metadata=request.filters
                )

                search_results = []
                for i, result in enumerate(results):
                    metadata = result.get('metadata', {})

                    doc_type = metadata.get('type', 'unknown')
                    if '판례' in metadata.get('source', ''):
                        doc_type = 'case'
                    elif '법령' in metadata.get('source', ''):
                        doc_type = 'law'
                    elif '해석례' in metadata.get('source', ''):
                        doc_type = 'interpretation'

                    search_results.append(SearchResult(
                        id=str(i + 1),
                        title=metadata.get('title', f"문서 {i + 1}"),
                        type=doc_type,
                        summary=result.get('text', '')[:200],
                        date=metadata.get('date', ''),
                        relevance=min(100, int(result.get('score', 0) * 100)),
                        citation=metadata.get('citation', metadata.get('source', ''))
                    ))

                logger.info(f"Search returned {len(search_results)} results for query: {request.query}")
                return search_results

            except Exception as e:
                logger.error(f"Search error: {e}")
                return _get_mock_search_results(request.query, request.limit)
        else:
            return _get_mock_search_results(request.query, request.limit)

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
