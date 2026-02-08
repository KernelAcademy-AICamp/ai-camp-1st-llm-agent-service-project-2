"""
RAG Workflow Node Functions

Phase 4 - Week 11: RAG 워크플로우 노드 함수

노드 함수 목록:
- retrieve_node: 문서 검색 (HybridRetriever)
- generate_node: 답변 생성 (LLMClient)
- check_confidence_node: 신뢰도 평가
- critique_node: Self-Critique
- refine_node: 답변 개선
- finalize_node: 최종 처리

라우팅 함수:
- route_after_confidence: 신뢰도 기반 조건부 분기

헬퍼 함수:
- extract_sources: 문서에서 출처 추출

성능 최적화:
- 글로벌 싱글톤 패턴으로 BM25/Retriever 재사용
- 매 요청마다 BM25 로드하지 않음 (~40초 절약)
"""

import time
import json
from typing import Dict, Any, List, Literal, Optional
from loguru import logger

from apps.ai_service.states.rag_state import RAGState


# ===== Global Component Cache (Singleton Pattern) =====
# 매 요청마다 BM25 인덱스를 로드하지 않도록 캐싱
_global_retriever: Optional["HybridRetriever"] = None
_global_bm25: Optional["BM25Index"] = None


def set_global_retriever(retriever) -> None:
    """
    전역 retriever 설정 (main.py 시작 시 호출)

    main.py에서 app.state.retriever 초기화 후 호출:
        from apps.ai_service.workflows.nodes.rag_nodes import set_global_retriever
        set_global_retriever(retriever)

    이렇게 하면 RAGState에 retriever를 포함하지 않아도 됨
    (LangGraph checkpointing msgpack 직렬화 에러 방지)
    """
    global _global_retriever
    _global_retriever = retriever
    logger.info(f"[rag_nodes] Global retriever set: {type(retriever).__name__}")


# ===== Node Functions =====

def _get_global_retriever(state_retriever=None):
    """
    글로벌 HybridRetriever 인스턴스 반환

    우선순위:
    1. state에서 전달된 retriever (라우터 → workflow → state)
    2. 글로벌 캐시된 인스턴스
    3. 싱글톤 패턴으로 직접 초기화 (fallback)

    성능: state.retriever 사용 시 BM25 재로드 없음 → 첫 요청도 ~15초
    """
    global _global_retriever, _global_bm25

    # 1. state에서 전달된 retriever 사용 (권장)
    if state_retriever is not None:
        _global_retriever = state_retriever
        logger.info("[retrieve_node] Using state.retriever (injected from app.state)")
        return _global_retriever

    # 2. 이미 캐시된 인스턴스가 있으면 반환
    if _global_retriever is not None:
        logger.debug("[retrieve_node] Using cached HybridRetriever")
        return _global_retriever

    # 3. Fallback: 직접 초기화 (state.retriever 없는 경우)
    logger.info("[retrieve_node] Fallback: Initializing HybridRetriever...")

    from libs.rag_core.retrieval.hybrid_retriever import HybridRetriever
    from libs.rag_core.retrieval.retriever import LegalDocumentRetriever
    from libs.rag_core.retrieval.bm25_index import BM25Index
    from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB
    from apps.ai_service.config.settings import settings

    # EMBED_MODE에 따라 로컬/원격 임베더 선택
    if settings.EMBED_MODE == "local":
        from libs.rag_core.embeddings.embedder import KoreanLegalEmbedder
        embedder = KoreanLegalEmbedder()
        embedding_dim = 768
    else:
        from libs.rag_core.embeddings.remote_embedder import RemoteEmbedder
        embedder = RemoteEmbedder(
            base_url=settings.REMOTE_EMBED_BASE_URL,
            api_key=settings.REMOTE_EMBED_API_KEY,
            model=settings.EMBED_MODEL
        )
        embedding_dim = 1024

    vectordb = QdrantVectorDB(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        collection_name=settings.QDRANT_COLLECTION,
        embedding_dim=embedding_dim
    )

    semantic_retriever = LegalDocumentRetriever(
        vectordb=vectordb,
        embedder=embedder
    )

    _global_bm25 = BM25Index()
    _global_bm25.load(str(settings.BM25_DIR))
    logger.info(f"[retrieve_node] BM25 index loaded: {_global_bm25.get_count()} documents")

    _global_retriever = HybridRetriever(
        semantic_retriever=semantic_retriever,
        bm25_index=_global_bm25,
        fusion_method='rrf',
        semantic_weight=0.5,
        rrf_k=60,
        enable_adaptive_weighting=True
    )

    logger.info("[retrieve_node] HybridRetriever initialized (fallback)")
    return _global_retriever


def retrieve_node(state: RAGState) -> Dict[str, Any]:
    """
    문서 검색 노드 (v2 - HybridRetriever)

    v2 핵심 구성:
    - HybridRetriever: Semantic + BM25 RRF Fusion
    - QdrantVectorDB: 벡터 검색
    - RemoteEmbedder: 원격 임베딩 API
    - BM25Index: 키워드 검색 (싱글톤 캐싱으로 재사용)

    성능 최적화:
    - 글로벌 싱글톤 패턴으로 BM25/Retriever 재사용
    - 첫 요청에만 ~40초, 이후 요청은 즉시 검색

    Returns:
        업데이트된 상태 필드 (documents, context, iteration_count)
    """
    query = state["query"]
    top_k = state.get("top_k", 5)
    iteration_count = state.get("iteration_count", 0)

    logger.info(f"[retrieve_node] query='{query}', top_k={top_k}, iteration={iteration_count}")

    start_time = time.time()

    try:
        # 전역 retriever 사용 (main.py 시작 시 set_global_retriever()로 설정됨)
        # NOTE: state에 retriever를 포함하면 LangGraph checkpointing에서 직렬화 에러 발생
        retriever = _get_global_retriever()

        # 검색 수행 (Semantic + BM25 융합)
        documents = retriever.retrieve(query, top_k=top_k)

        # 컨텍스트 생성
        context = retriever.format_context(documents)

        elapsed = time.time() - start_time
        logger.info(f"[retrieve_node] Retrieved {len(documents)} documents in {elapsed:.2f}s (Hybrid Search)")

        return {
            "documents": documents,
            "context": context,
            "iteration_count": iteration_count + 1,
        }

    except Exception as e:
        logger.error(f"[retrieve_node] Error: {e}")
        return {
            "documents": [],
            "context": "",
            "iteration_count": iteration_count + 1,
            "error": str(e),
        }


def generate_node(state: RAGState) -> Dict[str, Any]:
    """
    답변 생성 노드

    기존 서비스 직접 호출:
    - libs/rag_core/llm/llm_client.py (LLMClient)

    Returns:
        업데이트된 상태 필드 (initial_answer)
    """
    query = state["query"]
    context = state.get("context", "")
    mode = state.get("mode", "standard")

    logger.info(f"[generate_node] Generating answer for query='{query}', mode={mode}")

    if not context:
        logger.warning("[generate_node] No context available")
        return {
            "initial_answer": "검색된 문서가 없어 답변을 생성할 수 없습니다.",
            "confidence_score": 0.0,
        }

    start_time = time.time()

    try:
        from libs.rag_core.llm.llm_client import create_llm_client
        from apps.ai_service.config.settings import settings

        # LLM 클라이언트 생성
        llm_client = create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL or None,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )

        # 모드별 지시사항
        mode_instructions = {
            "concise": "답변은 100자 이내로 핵심만 간결하게 작성하세요.",
            "standard": "답변은 150-200자로 적절한 상세도로 작성하세요.",
            "detailed": "답변은 300-400자로 상세하게 작성하세요. 관련 조문과 판례를 충분히 인용하세요."
        }

        instruction = mode_instructions.get(mode, mode_instructions["standard"])

        # 프롬프트 구성
        system_prompt = """당신은 형사법 전문 법률 AI 어시스턴트입니다.
검색된 판례와 법령을 기반으로 정확하고 신뢰할 수 있는 답변을 제공합니다.

핵심 원칙:
1. 검색된 문서만을 기반으로 답변 (Hallucination 금지)
2. 모든 주장에 출처 명시 (예: [판례: 2020도1234])
3. 법률 자문이 아닌 정보 제공임을 명시
4. 불확실한 경우 솔직히 인정"""

        user_prompt = f"""다음 판례/법령을 참고하여 질문에 답변하세요.

{instruction}

=== 검색된 자료 ===
{context}

=== 질문 ===
{query}

=== 답변 ==="""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # LLM 호출
        answer = llm_client.chat(messages, temperature=0.1)

        elapsed = time.time() - start_time
        logger.info(f"[generate_node] Generated answer in {elapsed:.2f}s, length={len(answer)}")

        return {
            "initial_answer": answer,
        }

    except Exception as e:
        logger.error(f"[generate_node] Error: {e}")
        return {
            "initial_answer": f"답변 생성 중 오류가 발생했습니다: {str(e)}",
            "error": str(e),
        }


def check_confidence_node(state: RAGState) -> Dict[str, Any]:
    """
    답변 신뢰도 평가 노드

    간단한 휴리스틱 기반 신뢰도 평가:
    - 출처 인용 여부
    - 답변 길이
    - 검색된 문서 수

    Returns:
        업데이트된 상태 필드 (confidence_score, needs_refinement)
    """
    initial_answer = state.get("initial_answer", "")
    documents = state.get("documents", [])
    mode = state.get("mode", "standard")

    logger.info("[check_confidence_node] Evaluating confidence")

    # 휴리스틱 기반 신뢰도 계산
    score = 50.0  # 기본 점수

    # 1. 문서 검색 결과
    doc_count = len(documents)
    if doc_count >= 3:
        score += 20
    elif doc_count >= 1:
        score += 10

    # 2. 출처 인용 여부
    has_citation = any(marker in initial_answer for marker in ["[판례:", "[법령:", "[출처:"])
    if has_citation:
        score += 15

    # 3. 답변 길이 (모드별 적절성)
    answer_length = len(initial_answer)
    if mode == "concise" and 50 <= answer_length <= 150:
        score += 10
    elif mode == "standard" and 100 <= answer_length <= 300:
        score += 10
    elif mode == "detailed" and answer_length >= 200:
        score += 10

    # 4. 에러 체크
    if state.get("error"):
        score -= 30

    # 점수 범위 제한
    confidence_score = max(0.0, min(100.0, score))

    # 개선 필요 여부
    needs_refinement = confidence_score < 70 and mode == "detailed"

    logger.info(f"[check_confidence_node] confidence={confidence_score}, needs_refinement={needs_refinement}")

    return {
        "confidence_score": confidence_score,
        "needs_refinement": needs_refinement,
    }


def critique_node(state: RAGState) -> Dict[str, Any]:
    """
    Self-Critique 노드 (DETAILED 모드만)

    Constitutional AI의 자기 검증 단계:
    - 법률적 정확성
    - 판례 인용 적절성
    - 논리적 일관성

    Returns:
        업데이트된 상태 필드 (critique)
    """
    initial_answer = state.get("initial_answer", "")
    query = state.get("query", "")
    mode = state.get("mode", "standard")

    # DETAILED 모드가 아니면 스킵
    if mode != "detailed":
        logger.info("[critique_node] Skipped (not detailed mode)")
        return {"critique": None}

    logger.info("[critique_node] Running self-critique")

    try:
        from libs.rag_core.llm.llm_client import create_llm_client
        from apps.ai_service.config.settings import settings

        llm_client = create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL or None,
            temperature=0.0,
            max_tokens=1000
        )

        critique_prompt = f"""다음 법률 답변을 검토하고 개선점을 제시하세요.

질문: {query}

답변:
{initial_answer}

검토 항목:
1. 법률적 정확성: 법령/판례 인용이 정확한가?
2. 완전성: 질문에 충분히 답변했는가?
3. 출처 명시: 근거가 명확히 제시되었는가?
4. 면책 조항: 법률 자문 아님이 명시되었는가?

JSON 형식으로 응답:
{{
    "accuracy_score": 0-100,
    "completeness_score": 0-100,
    "citation_score": 0-100,
    "improvements": ["개선점1", "개선점2"],
    "overall_feedback": "전체 평가 요약"
}}"""

        messages = [
            {"role": "system", "content": "법률 답변 품질 검토자입니다."},
            {"role": "user", "content": critique_prompt}
        ]

        critique_response = llm_client.chat(messages, temperature=0.0)

        # JSON 파싱 시도
        try:
            critique = json.loads(critique_response)
        except json.JSONDecodeError:
            critique = {"raw_feedback": critique_response}

        logger.info("[critique_node] Critique completed")

        return {"critique": json.dumps(critique, ensure_ascii=False)}

    except Exception as e:
        logger.error(f"[critique_node] Error: {e}")
        return {"critique": None}


def refine_node(state: RAGState) -> Dict[str, Any]:
    """
    답변 개선 노드

    Critique 결과를 반영하여 답변 개선

    Returns:
        업데이트된 상태 필드 (final_answer, revised, sources)
    """
    initial_answer = state.get("initial_answer", "")
    critique = state.get("critique")
    documents = state.get("documents", [])
    query = state.get("query", "")

    # Critique가 없으면 초기 답변 사용
    if not critique:
        logger.info("[refine_node] No critique, using initial answer")
        sources = extract_sources(documents)
        return {
            "final_answer": initial_answer,
            "revised": False,
            "sources": sources,
        }

    logger.info("[refine_node] Refining answer based on critique")

    try:
        from libs.rag_core.llm.llm_client import create_llm_client
        from apps.ai_service.config.settings import settings

        llm_client = create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL or None,
            temperature=0.1,
            max_tokens=settings.LLM_MAX_TOKENS
        )

        revision_prompt = f"""다음 검토 의견을 반영하여 답변을 개선하세요.

원본 질문: {query}

원본 답변:
{initial_answer}

검토 의견:
{critique}

개선 규칙:
1. 핵심 내용 유지
2. 지적된 문제점 수정
3. 출처 명확히 표시
4. 면책 조항 포함

개선된 답변:"""

        messages = [
            {"role": "system", "content": "법률 답변을 개선하는 전문가입니다."},
            {"role": "user", "content": revision_prompt}
        ]

        refined_answer = llm_client.chat(messages, temperature=0.1)
        sources = extract_sources(documents)

        logger.info("[refine_node] Answer refined")

        return {
            "final_answer": refined_answer,
            "revised": True,
            "sources": sources,
        }

    except Exception as e:
        logger.error(f"[refine_node] Error: {e}")
        sources = extract_sources(documents)
        return {
            "final_answer": initial_answer,
            "revised": False,
            "sources": sources,
            "error": str(e),
        }


def finalize_node(state: RAGState) -> Dict[str, Any]:
    """
    최종 처리 노드

    final_answer가 없으면 initial_answer 사용
    sources 정리

    Returns:
        업데이트된 상태 필드
    """
    initial_answer = state.get("initial_answer", "")
    final_answer = state.get("final_answer")
    documents = state.get("documents", [])

    if not final_answer:
        final_answer = initial_answer

    sources = state.get("sources") or extract_sources(documents)

    logger.info("[finalize_node] Finalizing response")
    logger.debug(f"[finalize_node] Documents count: {len(documents)}")
    for i, doc in enumerate(documents[:5]):
        metadata = doc.get("metadata", {})
        logger.debug(f"[finalize_node] Doc {i}: doc_type={metadata.get('doc_type')}, keys={list(metadata.keys())[:10]}")

    return {
        "final_answer": final_answer,
        "sources": sources,
    }


# ===== Routing Functions =====

def route_after_confidence(state: RAGState) -> Literal["critique", "retrieve", "finalize"]:
    """
    신뢰도 평가 후 라우팅

    Returns:
        - "critique": 신뢰도 높음 + DETAILED 모드 → Self-Critique
        - "retrieve": 신뢰도 낮음 + iteration < max → 재검색
        - "finalize": 최대 재시도 도달 또는 충분한 신뢰도
    """
    confidence_score = state.get("confidence_score", 0)
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    mode = state.get("mode", "standard")

    # 최대 재시도 도달
    if iteration_count >= max_iterations:
        logger.info(f"[route] Max iterations reached ({iteration_count})")
        return "finalize"

    # 신뢰도 기반 라우팅
    if confidence_score >= 70:
        # DETAILED 모드면 critique, 아니면 바로 finalize
        if mode == "detailed":
            logger.info(f"[route] High confidence ({confidence_score}) → critique")
            return "critique"
        else:
            logger.info(f"[route] High confidence ({confidence_score}) → finalize")
            return "finalize"
    else:
        # 신뢰도 낮음 → 재검색
        logger.info(f"[route] Low confidence ({confidence_score}) → retrieve")
        return "retrieve"


# ===== Helper Functions =====

def extract_sources(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    문서에서 출처 정보 추출

    doc_type별 메타데이터 매핑 (청킹_메타데이터_구현_명세서.md 기준):

    원천데이터:
    - 판결문: case_name, case_num, court_name, sentence_date
    - 결정례: case_name, case_num, court_code, final_date
    - 법령: law_title, article_num, ministry, promulg_date
    - 해석례: agenda, agenda_num, interp_ministry, interp_date

    라벨링 데이터 (QA/SUM):
    - 라벨링_판결문: case_name, case_num, court_name, sentence_date, label_type
    - 라벨링_결정례: case_name, case_num, court_code, final_date, label_type
    - 라벨링_법령: title, law_id, ministry, promulg_date, label_type
    - 라벨링_해석례: agenda, agenda_num, interp_ministry, interp_date, label_type

    Fallback:
    - 메타데이터가 없는 경우 text 일부를 title로 사용
    - precedent_id, decision_id 등 대체 ID 필드 시도
    """
    sources = []
    for doc in documents:
        metadata = doc.get("metadata", {})
        text = doc.get("text", "")
        doc_type = metadata.get("doc_type", "")
        source_type = metadata.get("source", "")  # 원천_판결문, 라벨링_판결문_QA 등
        label_type = metadata.get("label_type", "")  # QA 또는 SUM

        # Fallback: text에서 title 생성 (앞 50자)
        def get_text_preview(text: str, max_len: int = 50) -> str:
            if not text:
                return ""
            preview = text[:max_len].replace("\n", " ").strip()
            if len(text) > max_len:
                preview += "..."
            return preview

        # text_snippet: 문서 내용 미리보기 (앞 200자)
        text_snippet = text[:200].replace("\n", " ").strip() + "..." if len(text) > 200 else text.replace("\n", " ").strip()

        # doc_type별 필드 매핑
        if doc_type == "판결문":
            # 판결문: precedent_id도 fallback으로 시도
            case_num = metadata.get("case_num") or metadata.get("precedent_id", "")
            case_name = metadata.get("case_name", "")
            court_name = metadata.get("court_name") or metadata.get("court_code", "")

            source = {
                "case_number": case_num,
                "title": case_name or get_text_preview(text),
                "court": court_name,
                "date": metadata.get("sentence_date", ""),
                "doc_type": f"{doc_type} ({label_type})" if label_type else doc_type,
                "relevance_score": doc.get("score", 0),
                "text_snippet": text_snippet,
                "full_text": text,
            }
        elif doc_type == "결정례":
            # 결정례: decision_id도 fallback으로 시도
            case_num = metadata.get("case_num") or metadata.get("decision_id", "")
            case_name = metadata.get("case_name", "")
            court_code = metadata.get("court_code", "")

            source = {
                "case_number": case_num,
                "title": case_name or get_text_preview(text),
                "court": court_code,
                "date": metadata.get("final_date", ""),
                "doc_type": f"{doc_type} ({label_type})" if label_type else doc_type,
                "relevance_score": doc.get("score", 0),
                "text_snippet": text_snippet,
                "full_text": text,
            }
        elif doc_type == "법령":
            # 법령: law_title (원천) 또는 title (라벨링)
            title = metadata.get("law_title") or metadata.get("title", "")
            article = metadata.get("article_num") or metadata.get("sm_class", "")
            if article and title:
                title = f"{title} {article}"

            source = {
                "case_number": metadata.get("law_id", ""),  # 법령 ID
                "title": title or get_text_preview(text),
                "court": metadata.get("ministry", ""),  # 담당 부처
                "date": metadata.get("promulg_date") or metadata.get("effect_date", ""),
                "doc_type": f"{doc_type} ({label_type})" if label_type else doc_type,
                "relevance_score": doc.get("score", 0),
                "text_snippet": text_snippet,
                "full_text": text,
            }
        elif doc_type == "해석례":
            # 해석례: agenda (의제), interp_ministry (해석부처)
            agenda = metadata.get("agenda", "")
            agenda_num = metadata.get("agenda_num", "")
            title = f"{agenda} ({agenda_num})" if agenda and agenda_num else agenda or agenda_num

            source = {
                "case_number": metadata.get("interpretation_id", ""),
                "title": title or metadata.get("case_name", "") or get_text_preview(text),
                "court": metadata.get("interp_ministry") or metadata.get("question_ministry", ""),
                "date": metadata.get("interp_date", ""),
                "doc_type": f"{doc_type} ({label_type})" if label_type else doc_type,
                "relevance_score": doc.get("score", 0),
                "text_snippet": text_snippet,
                "full_text": text,
            }
        else:
            # 기타: 공통 필드 시도
            source = {
                "case_number": (
                    metadata.get("case_num") or
                    metadata.get("law_id") or
                    metadata.get("interpretation_id") or
                    metadata.get("decision_id") or
                    metadata.get("precedent_id", "")
                ),
                "title": (
                    metadata.get("case_name") or
                    metadata.get("title") or
                    metadata.get("law_title") or
                    metadata.get("agenda", "") or
                    get_text_preview(text)
                ),
                "court": (
                    metadata.get("court_name") or
                    metadata.get("court_code") or
                    metadata.get("ministry") or
                    metadata.get("interp_ministry", "")
                ),
                "date": (
                    metadata.get("sentence_date") or
                    metadata.get("final_date") or
                    metadata.get("promulg_date") or
                    metadata.get("interp_date", "")
                ),
                "doc_type": doc_type or source_type or "unknown",
                "relevance_score": doc.get("score", 0),
                "text_snippet": text_snippet,
                "full_text": text,
            }

        sources.append(source)
    return sources
