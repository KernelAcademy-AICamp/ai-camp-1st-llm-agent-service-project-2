"""
RAG Workflow State Definition

Phase 4 - Week 11: LangGraph 기반 RAG 상태 관리

설계 원칙:
- 기존 LegalRAGOrchestrator와 호환
- Constitutional AI (Self-Critique) 지원
- 조건부 분기를 위한 confidence score
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal
from enum import Enum


class ResponseMode(str, Enum):
    """응답 모드 (기존 response_modes.py와 호환)"""
    CONCISE = "concise"
    STANDARD = "standard"
    DETAILED = "detailed"


class RAGState(TypedDict, total=False):
    """
    RAG Workflow 상태

    워크플로우:
        1. retrieve: 문서 검색
        2. generate: 초기 답변 생성
        3. validate: 품질 검증 (confidence score)
        4. critique: Self-Critique (DETAILED 모드만)
        5. refine: 답변 개선

    상태 필드:
        - query: 사용자 질문
        - mode: 응답 모드 (CONCISE/STANDARD/DETAILED)
        - documents: 검색된 문서 목록
        - context: LLM에 전달할 컨텍스트
        - initial_answer: 초기 답변
        - confidence_score: 답변 신뢰도 (0-100)
        - critique: Self-Critique 결과
        - final_answer: 최종 답변
        - sources: 출처 정보
        - iteration_count: 재검색 횟수
        - needs_refinement: 개선 필요 여부
        - processing_time: 처리 시간 (초)
        - error: 에러 메시지
    """
    # 입력
    query: str
    mode: str  # ResponseMode.value
    top_k: int
    include_critique_log: bool

    # 검색 결과
    documents: List[Dict[str, Any]]
    context: str

    # 답변 생성
    initial_answer: str
    confidence_score: float
    needs_refinement: bool

    # Self-Critique (DETAILED 모드)
    critique: Optional[str]
    revised: bool

    # 최종 결과
    final_answer: str
    sources: List[Dict[str, Any]]
    summarized: bool

    # 메타데이터
    session_id: str
    user_id: Optional[str]
    iteration_count: int
    max_iterations: int
    processing_time: float
    error: Optional[str]
    metadata: Dict[str, Any]

    # 의존성 주입 (옵션)
    retriever: Optional[Any]  # HybridRetriever (None이면 fallback 사용)


def create_initial_rag_state(
    query: str,
    mode: str = "standard",
    top_k: int = 5,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    include_critique_log: bool = False,
    retriever: Optional[Any] = None
) -> RAGState:
    """
    RAG 상태 초기화 헬퍼 함수

    Args:
        query: 사용자 질문
        mode: 응답 모드
        top_k: 검색 문서 수
        session_id: 세션 ID (없으면 자동 생성)
        user_id: 사용자 ID
        include_critique_log: Critique 로그 포함 여부
        retriever: 미리 초기화된 HybridRetriever (optional)

    Returns:
        초기화된 RAGState
    """
    import uuid
    from datetime import datetime

    return RAGState(
        query=query,
        mode=mode,
        top_k=top_k,
        include_critique_log=include_critique_log,
        documents=[],
        context="",
        initial_answer="",
        confidence_score=0.0,
        needs_refinement=False,
        critique=None,
        revised=False,
        final_answer="",
        sources=[],
        summarized=False,
        session_id=session_id or str(uuid.uuid4()),
        user_id=user_id,
        iteration_count=0,
        max_iterations=3,
        processing_time=0.0,
        error=None,
        metadata={
            "created_at": datetime.utcnow().isoformat(),
            "workflow_version": "2.0.0"
        },
        retriever=retriever
    )
