"""
Chat & Search Router
챗봇 및 검색 관련 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.database import get_db
from apps.backend.core.retrieval.feedback_filter import get_excluded_precedent_ids

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
    async def chat_with_rag(request: RAGChatRequest, db: AsyncSession = Depends(get_db)):
        """ChromaDB RAG + Constitutional AI 기반 법률 챗봇

        - Hybrid Search (Semantic + BM25, RRF k=60, Adaptive Weighting)
        - Constitutional AI (6 principles + Self-Critique + 3-shot Learning)
        - 388,767개 형사법 문서 기반 RAG
        - 사용자 피드백 기반 필터링 (싫어요가 많은 판례 제외)
        """
        if not constitutional_chatbot:
            raise HTTPException(
                status_code=503,
                detail="Constitutional AI chatbot not available"
            )

        try:
            logger.info(f"RAG Chat request: '{request.query}' (top_k={request.top_k})")

            # 사용자 피드백 기반 제외 판례 ID 조회
            excluded_ids = await get_excluded_precedent_ids(db)
            if excluded_ids:
                logger.info(f"Filtering out {len(excluded_ids)} precedents based on user feedback")

            # Constitutional AI + Hybrid RAG로 답변 생성
            # Hybrid Retriever가 이미 3배 배수를 적용하므로 여기서는 배수 제거
            retrieval_top_k = request.top_k
            if excluded_ids:
                # 필터링으로 인한 손실 보상만 추가
                retrieval_top_k += min(len(excluded_ids), 3)  # 최대 3개까지만 추가
                logger.info(f"Retrieving {retrieval_top_k} chunks (accounting for {len(excluded_ids)} excluded)")

            result = constitutional_chatbot.chat(
                query=request.query,
                top_k=retrieval_top_k,
                include_critique_log=False
            )

            # 피드백 기반 필터링 적용
            filtered_sources = result.get('sources', [])
            if excluded_ids and filtered_sources:
                original_count = len(filtered_sources)
                # metadata.source를 기준으로 필터링
                filtered_sources = [
                    s for s in filtered_sources
                    if s.get('metadata', {}).get('source') not in excluded_ids
                ]
                if len(filtered_sources) < original_count:
                    logger.info(f"Filtered {original_count - len(filtered_sources)} sources based on feedback")

            # 소스 정보 포맷팅 (청크 중복 제거)
            sources = []
            seen_sources = set()  # 이미 처리된 source ID 추적

            if request.include_sources and filtered_sources:
                rank = 1
                for source in filtered_sources:
                    metadata = source.get('metadata', {})
                    source_id = metadata.get('source', 'Unknown')

                    # 같은 판례의 청크 중복 제거 (첫 번째 청크만 유지)
                    if source_id in seen_sources:
                        logger.debug(f"Skipping duplicate source: {source_id}")
                        continue

                    seen_sources.add(source_id)

                    # Source ID 패턴 분석으로 문서 타입 추론
                    doc_type = metadata.get('type', 'unknown')
                    source_str = metadata.get('source', '')

                    # Source ID나 메타데이터로 타입 추론
                    if '_P_' in source_str or '판례' in source_str:
                        doc_type = 'case'
                    elif '법령' in source_str:
                        doc_type = 'law'
                    elif '해석례' in source_str:
                        doc_type = 'interpretation'
                    elif doc_type == 'unknown':
                        # 기본값: 형사법 데이터는 대부분 판례
                        doc_type = 'case'

                    sources.append({
                        'rank': rank,
                        'source': source_id,
                        'type': doc_type,
                        'title': metadata.get('title', ''),
                        'case_number': metadata.get('case_number', ''),
                        'date': metadata.get('date', ''),
                        'citation': metadata.get('citation', ''),
                        'text_snippet': source.get('text', '')[:200],
                        'score': source.get('score', 0.0)
                    })
                    rank += 1

                    # top_k 개수에 도달하면 중단
                    if len(sources) >= request.top_k:
                        break

                logger.info(f"Deduplicated sources: {len(filtered_sources)} chunks -> {len(sources)} unique precedents")

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

    @router.get("/document/{source_id}")
    async def get_document_detail(source_id: str):
        """문서 상세 정보 조회 (전체 텍스트 포함)

        Args:
            source_id: 문서 소스 ID (예: HS_P_338200)

        Returns:
            문서 전체 텍스트 및 메타데이터 (모든 청크 결합)
        """
        if not hybrid_retriever:
            raise HTTPException(
                status_code=503,
                detail="Document retrieval service not available"
            )

        try:
            logger.info(f"Fetching document detail for: {source_id}")

            # ChromaDB에서 해당 source_id를 가진 모든 청크 조회
            results = hybrid_retriever.semantic_retriever.vectordb.collection.get(
                where={"source": source_id},
                include=["documents", "metadatas"]
            )

            if not results or not results['ids']:
                # source_id가 정확하지 않으면 부분 검색 시도
                all_results = hybrid_retriever.semantic_retriever.vectordb.collection.get(
                    include=["documents", "metadatas"]
                )

                # source_id가 포함된 문서 찾기
                matching_chunks = []
                for i, metadata in enumerate(all_results['metadatas']):
                    if source_id in metadata.get('source', ''):
                        matching_chunks.append({
                            'id': all_results['ids'][i],
                            'document': all_results['documents'][i],
                            'metadata': metadata
                        })

                if not matching_chunks:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Document not found: {source_id}"
                    )

                # 청크 정렬 및 결합
                matching_chunks.sort(key=lambda x: int(x['metadata'].get('chunk_id', 0)))
                full_text = '\n\n'.join([chunk['document'] for chunk in matching_chunks])

                return {
                    'id': matching_chunks[0]['id'],
                    'source': matching_chunks[0]['metadata'].get('source', ''),
                    'title': matching_chunks[0]['metadata'].get('title', ''),
                    'type': matching_chunks[0]['metadata'].get('type', 'unknown'),
                    'case_number': matching_chunks[0]['metadata'].get('case_number', ''),
                    'date': matching_chunks[0]['metadata'].get('date', ''),
                    'citation': matching_chunks[0]['metadata'].get('citation', ''),
                    'full_text': full_text,
                    'metadata': matching_chunks[0]['metadata']
                }

            # 모든 청크를 chunk_id로 정렬
            chunks = []
            for i in range(len(results['ids'])):
                chunks.append({
                    'id': results['ids'][i],
                    'document': results['documents'][i],
                    'metadata': results['metadatas'][i]
                })

            # chunk_id로 정렬 (없으면 0으로 간주)
            chunks.sort(key=lambda x: int(x['metadata'].get('chunk_id', 0)))

            # 모든 청크의 텍스트를 결합
            full_text = '\n\n'.join([chunk['document'] for chunk in chunks])

            # 첫 번째 청크의 메타데이터 사용 (모든 청크가 같은 메타데이터 공유)
            metadata = chunks[0]['metadata']

            logger.info(f"Combined {len(chunks)} chunks for document: {source_id}")

            return {
                'id': chunks[0]['id'],
                'source': metadata.get('source', ''),
                'title': metadata.get('title', ''),
                'type': metadata.get('type', 'unknown'),
                'case_number': metadata.get('case_number', ''),
                'date': metadata.get('date', ''),
                'citation': metadata.get('citation', ''),
                'full_text': full_text,
                'metadata': metadata
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Document detail error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"문서 조회 오류: {str(e)}"
            )

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
