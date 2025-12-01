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
import uuid
from typing import Dict, Any, Optional
from loguru import logger

from langgraph.graph import StateGraph, START, END

from apps.ai_service.states.rag_state import RAGState, create_initial_rag_state
from apps.ai_service.workflows.nodes import (
    retrieve_node,
    generate_node,
    check_confidence_node,
    critique_node,
    refine_node,
    finalize_node,
    route_after_confidence,
)


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

    또는 (pre-initialized retriever 사용):
        workflow = RAGWorkflow(retriever=app.state.retriever)
        result = workflow.run("절도죄란?", mode="standard")
    """

    def __init__(self, retriever=None):
        """
        Args:
            retriever: 미리 초기화된 HybridRetriever (optional)
                       제공되면 BM25 재로드 없이 바로 사용
                       None이면 nodes에서 fallback으로 새로 생성
        """
        self.graph = create_rag_workflow()
        self.retriever = retriever  # app.state.retriever 전달받음
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

        # 초기 상태 생성 (retriever 주입)
        initial_state = create_initial_rag_state(
            query=query,
            mode=mode,
            top_k=top_k,
            session_id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            include_critique_log=include_critique_log,
            retriever=self.retriever  # app.state.retriever 전달
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

        # 초기 상태 생성 (retriever 주입)
        initial_state = create_initial_rag_state(
            query=query,
            mode=mode,
            top_k=top_k,
            session_id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            include_critique_log=include_critique_log,
            retriever=self.retriever  # app.state.retriever 전달
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
