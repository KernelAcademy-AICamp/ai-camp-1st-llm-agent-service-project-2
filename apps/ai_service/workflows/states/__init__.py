"""
Workflow State Definitions

Phase 4 - Week 12: 워크플로우 상태 정의

상태 정의:
- DocumentAnalysisState: 문서 분석 상태
- CaseAnalysisState: 사건 분석 상태
- RiskAnalysisState: 리스크 분석 상태
- LLMComparisonState: LLM 비교 상태

사용:
    from apps.ai_service.workflows.states import DocumentAnalysisState
"""

from apps.ai_service.workflows.states.document_state import DocumentAnalysisState
from apps.ai_service.workflows.states.case_state import CaseAnalysisState
from apps.ai_service.workflows.states.risk_state import RiskAnalysisState
from apps.ai_service.workflows.states.llm_comparison_state import (
    LLMComparisonState,
    LLMModelConfig,
    ModelMetrics,
)

__all__ = [
    "DocumentAnalysisState",
    "CaseAnalysisState",
    "RiskAnalysisState",
    "LLMComparisonState",
    "LLMModelConfig",
    "ModelMetrics",
]
