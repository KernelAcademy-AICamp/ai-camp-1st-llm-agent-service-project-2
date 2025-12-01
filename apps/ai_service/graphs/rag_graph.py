"""
RAG Workflow Graph

Phase 4 - Week 11: LangGraph 기반 RAG Workflow

설계 원칙:
- 기존 서비스(ConstitutionalLawChatbot, HybridRetriever)를 직접 호출
- MCP Tools 사용 안 함 (Week 12에서 MCP Resources 추가 예정)
- Checkpointing 불필요 (빠른 응답, 재실행 비용 낮음)
- 조건부 분기: confidence 기반 재검색

워크플로우:
    START → retrieve → generate → check_confidence
                                      ↓
                          [high] → critique → refine → END
                          [low]  → retrieve (재검색, max 3회)
                          [max]  → END

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""

import time
import json
import uuid
from typing import Dict, Any, Optional, List, Literal
from loguru import logger

from langgraph.graph import StateGraph, START, END

from apps.ai_service.states.rag_state import RAGState, create_initial_rag_state


# ===== Node Functions (일반 Python 함수) =====

def retrieve_node(state: RAGState) -> Dict[str, Any]:
    """
    문서 검색 노드

    기존 서비스 직접 호출:
    - libs/rag_core/retrieval/retriever.py (LegalDocumentRetriever)
    - libs/rag_core/retrieval/hybrid_retriever.py (HybridRetriever)

    Returns:
        업데이트된 상태 필드 (documents, context, iteration_count)
    """
    query = state["query"]
    top_k = state.get("top_k", 5)
    iteration_count = state.get("iteration_count", 0)

    logger.info(f"[retrieve_node] query='{query}', top_k={top_k}, iteration={iteration_count}")

    start_time = time.time()

    try:
        # 기존 서비스 import 및 호출
        from libs.rag_core.retrieval.retriever import LegalDocumentRetriever
        from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB
        from libs.rag_core.embeddings.remote_embedder import RemoteEmbedder
        from apps.ai_service.config.settings import settings

        # Retriever 초기화
        embedder = RemoteEmbedder()
        vectordb = QdrantVectorDB(
            collection_name="criminal_law",
            embedder=embedder
        )
        retriever = LegalDocumentRetriever(vectordb=vectordb)

        # 검색 수행
        documents = retriever.retrieve(query, top_k=top_k)

        # 컨텍스트 생성
        context = retriever.format_context(documents)

        elapsed = time.time() - start_time
        logger.info(f"[retrieve_node] Retrieved {len(documents)} documents in {elapsed:.2f}s")

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

    logger.info(f"[check_confidence_node] Evaluating confidence")

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

        logger.info(f"[critique_node] Critique completed")

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
        sources = _extract_sources(documents)
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
        sources = _extract_sources(documents)

        logger.info("[refine_node] Answer refined")

        return {
            "final_answer": refined_answer,
            "revised": True,
            "sources": sources,
        }

    except Exception as e:
        logger.error(f"[refine_node] Error: {e}")
        sources = _extract_sources(documents)
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
    processing_time 계산

    Returns:
        업데이트된 상태 필드
    """
    initial_answer = state.get("initial_answer", "")
    final_answer = state.get("final_answer")
    documents = state.get("documents", [])

    if not final_answer:
        final_answer = initial_answer

    sources = state.get("sources") or _extract_sources(documents)

    logger.info("[finalize_node] Finalizing response")

    return {
        "final_answer": final_answer,
        "sources": sources,
    }


# ===== Helper Functions =====

def _extract_sources(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """문서에서 출처 정보 추출"""
    sources = []
    for doc in documents:
        metadata = doc.get("metadata", {})
        source = {
            "case_number": metadata.get("case_number", ""),
            "title": metadata.get("title", ""),
            "court": metadata.get("court", ""),
            "date": metadata.get("date", ""),
            "relevance_score": doc.get("score", 0),
        }
        sources.append(source)
    return sources


# ===== Routing Functions =====

def route_after_confidence(state: RAGState) -> Literal["critique", "retrieve", "finalize"]:
    """
    신뢰도 평가 후 라우팅

    Returns:
        - "critique": 신뢰도 높음 → Self-Critique
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


# ===== Workflow Builder =====

def create_rag_workflow() -> StateGraph:
    """
    RAG Workflow StateGraph 생성

    워크플로우:
        START → retrieve → generate → check_confidence
                                          ↓
                              [high] → critique → refine → finalize → END
                              [low]  → retrieve (재검색)
                              [max]  → finalize → END

    Returns:
        Compiled StateGraph
    """
    # StateGraph 정의
    workflow = StateGraph(RAGState)

    # 노드 추가
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("check_confidence", check_confidence_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("refine", refine_node)
    workflow.add_node("finalize", finalize_node)

    # 엣지 정의
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "check_confidence")

    # 조건부 분기
    workflow.add_conditional_edges(
        "check_confidence",
        route_after_confidence,
        {
            "critique": "critique",
            "retrieve": "retrieve",
            "finalize": "finalize",
        }
    )

    workflow.add_edge("critique", "refine")
    workflow.add_edge("refine", "finalize")
    workflow.add_edge("finalize", END)

    # RAG Chatbot: Checkpointing 불필요 (빠른 응답, 재실행 비용 낮음)
    return workflow.compile()


# ===== RAGWorkflow Class =====

class RAGWorkflow:
    """
    RAG Workflow 실행 클래스

    사용 예:
        workflow = RAGWorkflow()
        result = workflow.run("절도죄란?", mode="standard")
    """

    def __init__(self):
        self.graph = create_rag_workflow()
        logger.info("RAGWorkflow initialized")

    def run(
        self,
        query: str,
        mode: str = "standard",
        top_k: int = 5,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        include_critique_log: bool = False
    ) -> Dict[str, Any]:
        """
        RAG Workflow 실행

        Args:
            query: 사용자 질문
            mode: 응답 모드 (concise, standard, detailed)
            top_k: 검색 문서 수
            session_id: 세션 ID
            user_id: 사용자 ID
            include_critique_log: Critique 로그 포함 여부

        Returns:
            Workflow 실행 결과
        """
        start_time = time.time()

        # 초기 상태 생성
        initial_state = create_initial_rag_state(
            query=query,
            mode=mode,
            top_k=top_k,
            session_id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            include_critique_log=include_critique_log
        )

        logger.info(f"[RAGWorkflow] Starting: query='{query}', mode={mode}")

        # Workflow 실행
        try:
            result = self.graph.invoke(initial_state)

            processing_time = time.time() - start_time
            result["processing_time"] = processing_time

            logger.info(f"[RAGWorkflow] Completed in {processing_time:.2f}s")

            return {
                "answer": result.get("final_answer", ""),
                "sources": result.get("sources", []),
                "confidence": result.get("confidence_score", 0),
                "revised": result.get("revised", False),
                "critique_log": result.get("critique") if include_critique_log else None,
                "processing_time": processing_time,
                "session_id": result.get("session_id"),
                "iteration_count": result.get("iteration_count", 0),
            }

        except Exception as e:
            logger.error(f"[RAGWorkflow] Error: {e}")
            processing_time = time.time() - start_time
            return {
                "answer": f"워크플로우 실행 중 오류가 발생했습니다: {str(e)}",
                "sources": [],
                "confidence": 0,
                "revised": False,
                "error": str(e),
                "processing_time": processing_time,
            }

    async def arun(
        self,
        query: str,
        mode: str = "standard",
        top_k: int = 5,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        include_critique_log: bool = False
    ) -> Dict[str, Any]:
        """
        RAG Workflow 비동기 실행

        Args:
            query: 사용자 질문
            mode: 응답 모드 (concise, standard, detailed)
            top_k: 검색 문서 수
            session_id: 세션 ID
            user_id: 사용자 ID
            include_critique_log: Critique 로그 포함 여부

        Returns:
            Workflow 실행 결과
        """
        start_time = time.time()

        # 초기 상태 생성
        initial_state = create_initial_rag_state(
            query=query,
            mode=mode,
            top_k=top_k,
            session_id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            include_critique_log=include_critique_log
        )

        logger.info(f"[RAGWorkflow] Starting async: query='{query}', mode={mode}")

        # Workflow 비동기 실행
        try:
            result = await self.graph.ainvoke(initial_state)

            processing_time = time.time() - start_time
            result["processing_time"] = processing_time

            logger.info(f"[RAGWorkflow] Completed in {processing_time:.2f}s")

            return {
                "answer": result.get("final_answer", ""),
                "sources": result.get("sources", []),
                "confidence": result.get("confidence_score", 0),
                "revised": result.get("revised", False),
                "critique_log": result.get("critique") if include_critique_log else None,
                "processing_time": processing_time,
                "session_id": result.get("session_id"),
                "iteration_count": result.get("iteration_count", 0),
            }

        except Exception as e:
            logger.error(f"[RAGWorkflow] Error: {e}")
            processing_time = time.time() - start_time
            return {
                "answer": f"워크플로우 실행 중 오류가 발생했습니다: {str(e)}",
                "sources": [],
                "confidence": 0,
                "revised": False,
                "error": str(e),
                "processing_time": processing_time,
            }
