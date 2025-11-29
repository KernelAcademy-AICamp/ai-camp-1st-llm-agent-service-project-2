"""
Case Analysis State

Phase 4 - Week 12: 사건 분석 워크플로우 상태 정의

사건 분석 워크플로우:
1. extract_info_node: 사건 정보 추출 (당사자, 청구 등)
2. analyze_issues_node: 쟁점 분석
3. search_precedents_node: 관련 판례 검색
4. generate_analysis_node: 종합 분석 생성

Checkpointing: 불필요 (빠른 실행, 10-15초)
"""

from typing import TypedDict, List, Dict, Any, Optional


class PartyInfo(TypedDict):
    """당사자 정보"""
    role: str  # plaintiff, defendant, third_party
    name: str
    description: Optional[str]


class IssueInfo(TypedDict):
    """쟁점 정보"""
    issue_type: str
    description: str
    legal_basis: Optional[str]


class PrecedentResult(TypedDict):
    """관련 판례"""
    case_number: str
    title: str
    summary: str
    relevance_score: float


class CaseAnalysisState(TypedDict):
    """
    사건 분석 워크플로우 상태

    Attributes:
        case_content: 원본 사건 내용
        case_type: 사건 유형 (civil, criminal, administrative)
        parties: 당사자 정보 리스트
        issues: 쟁점 리스트
        related_precedents: 관련 판례 리스트
        analysis: 종합 분석 결과
        completed_tasks: 완료된 작업 목록
        error: 에러 메시지 (있는 경우)
    """
    case_content: str
    case_type: str
    parties: List[PartyInfo]
    issues: List[IssueInfo]
    related_precedents: List[PrecedentResult]
    analysis: Optional[str]
    completed_tasks: List[str]
    error: Optional[str]
