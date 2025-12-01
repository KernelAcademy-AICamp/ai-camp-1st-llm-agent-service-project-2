"""
Risk Analysis State

Phase 4 - Week 12: 리스크 분석 워크플로우 상태 정의

리스크 분석 워크플로우:
1. identify_risks_node: 리스크 식별
2. assess_severity_node: 심각도 평가
3. human_review_node: 전문가 검토 (Human-in-the-Loop)
4. generate_report_node: 보고서 생성

Checkpointing: 필수 (Human-in-the-Loop, TTL: 7일)
"""

from typing import TypedDict, List, Dict, Any, Optional
from enum import Enum


class RiskSeverity(str, Enum):
    """리스크 심각도"""
    CRITICAL = "CRITICAL"  # 즉시 조치 필요
    HIGH = "HIGH"          # 높은 주의 필요
    MEDIUM = "MEDIUM"      # 검토 권장
    LOW = "LOW"            # 참고 수준
    INFO = "INFO"          # 정보성


class RiskItem(TypedDict):
    """리스크 항목"""
    risk_type: str
    description: str
    severity: str  # RiskSeverity value
    recommendation: Optional[str]
    clause_reference: Optional[str]


class HumanReviewResult(TypedDict):
    """전문가 검토 결과"""
    reviewer_id: Optional[str]
    approved: bool
    comments: Optional[str]
    modified_risks: Optional[List[RiskItem]]


class SeverityAssessment(TypedDict):
    """심각도 평가 결과"""
    overall_score: float
    critical_count: int
    high_count: int


class RiskAnalysisState(TypedDict):
    """
    리스크 분석 워크플로우 상태 (Iterative Refinement 패턴)

    Attributes:
        document_id: 문서 ID
        text: 분석 대상 텍스트
        doc_type: 문서 타입
        identified_risks: 식별된 리스크 리스트
        severity_assessment: 심각도 평가 결과
        mitigation_strategies: 완화 전략 리스트
        requires_human_review: 전문가 검토 필요 여부
        human_review: 전문가 검토 결과
        review_feedback: 리뷰 피드백 (refine 포함 시 재분석)
        refinement_iteration: 재분석 반복 횟수 (최대 3회)
        summary: 간결한 요약 (프론트엔드 표시용)
        report: 최종 보고서 (상세 분석)
        completed_tasks: 완료된 작업 목록
        iteration_count: 총 반복 횟수
        skip_human_review: Human-in-the-Loop 스킵 여부 (기본: True)
        error: 에러 메시지 (있는 경우)
    """
    document_id: Optional[str]
    text: str
    doc_type: str
    identified_risks: List[RiskItem]
    severity_assessment: Optional[SeverityAssessment]
    mitigation_strategies: List[str]
    requires_human_review: bool
    human_review: Optional[HumanReviewResult]
    review_feedback: Optional[str]
    refinement_iteration: int
    summary: Optional[str]
    report: Optional[str]
    completed_tasks: List[str]
    iteration_count: int
    skip_human_review: bool
    error: Optional[str]
