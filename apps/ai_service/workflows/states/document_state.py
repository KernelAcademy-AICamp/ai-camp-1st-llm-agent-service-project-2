"""
Document Analysis State

Phase 4 - Week 12: 문서 분석 워크플로우 상태 정의

문서 분석 워크플로우:
1. preprocess_node: 문서 텍스트 추출 (document_processor 사용)
2. chunk_node: 텍스트 청킹
3. summarize_node: 요약 생성 (summarizer 사용)
4. extract_clauses_node: 핵심 조항 추출 (clause_extractor 사용)

Checkpointing: 불필요 (빠른 실행, 10-20초)
"""

from typing import TypedDict, List, Dict, Any, Optional


class SummaryResult(TypedDict):
    """요약 결과"""
    summary: str
    token_count: int
    model_version: str


class ClauseResult(TypedDict):
    """조항 추출 결과"""
    clause_type: str
    title: str
    content: str
    importance_score: int


class ChunkData(TypedDict):
    """청크 데이터"""
    chunk_index: int
    text: str
    start_offset: int
    end_offset: int
    token_count: int


class RiskAnalysisResult(TypedDict):
    """리스크 분석 결과 (문서 분석용)"""
    risk_type: str
    description: str
    severity: str
    recommendation: Optional[str]


class DocumentAnalysisState(TypedDict):
    """
    문서 분석 워크플로우 상태

    Attributes:
        document_id: 문서 ID (DB 저장용)
        file_path: 파일 경로 (파일 처리용)
        doc_type: 문서 타입 (CONTRACT, STATUTE, PRECEDENT, OTHER)
        text: 추출된 전체 텍스트
        chunks: 청킹된 텍스트 리스트
        summary: 요약 결과
        clauses: 추출된 핵심 조항 리스트
        risks: 리스크 분석 결과 (문서 타입이 CONTRACT인 경우)
        analysis_plan: LLM이 결정한 분석 작업 목록
        needs_expert_review: 전문가 검토 필요 여부
        completed_tasks: 완료된 작업 목록
        error: 에러 메시지 (있는 경우)
    """
    document_id: Optional[str]
    file_path: Optional[str]
    doc_type: str
    text: str
    chunks: List[ChunkData]
    summary: Optional[SummaryResult]
    clauses: List[ClauseResult]
    risks: Optional[List[RiskAnalysisResult]]
    analysis_plan: List[str]
    needs_expert_review: bool
    completed_tasks: List[str]
    error: Optional[str]
