"""
Workflow State Definitions

Phase 4 - Week 12~13: 워크플로우 상태 정의

상태 정의:
- DocumentAnalysisState: 문서 분석 상태
- CaseAnalysisState: 사건 분석 상태
- CriminalCaseState: 형사 사건 분석 상태
- RiskAnalysisState: 리스크 분석 상태
- LLMComparisonState: LLM 비교 상태
- CrawlState: 크롤러 상태 (Week 13, Checkpointing 필수)
- DashboardState: 대시보드 분석 상태 (Week 13, Checkpointing 불필요)

사용:
    from apps.ai_service.workflows.states import DocumentAnalysisState
    from apps.ai_service.workflows.states import CriminalCaseState
    from apps.ai_service.workflows.states import CrawlState
    from apps.ai_service.workflows.states import DashboardState
"""

from apps.ai_service.workflows.states.document_state import DocumentAnalysisState
from apps.ai_service.workflows.states.case_state import CaseAnalysisState
from apps.ai_service.workflows.states.criminal_state import (
    CriminalCaseState,
    CrimeElementResult,
    CrimeElementsResult,
    SentencingFactorsResult,
    ExpectedSentenceResult,
    CriminalPrecedentResult,
    get_crime_category,
    CRIME_CATEGORY_MAP,
)
from apps.ai_service.workflows.states.risk_state import RiskAnalysisState
from apps.ai_service.workflows.states.llm_comparison_state import (
    LLMComparisonState,
    LLMModelConfig,
    ModelMetrics,
)
from apps.ai_service.workflows.states.crawl_state import (
    CrawlState,
    CrawlStatus,
    DataSource,
    CrawlMetrics,
    CrawledDocument,
    ProcessingStatus,
    QualityCheck,
    create_initial_crawl_state,
)
from apps.ai_service.workflows.states.dashboard_state import (
    DashboardState,
    TimeRange,
    AnomalySeverity,
    AnomalyType,
    InsightCategory,
    Anomaly,
    Insight,
    Trend,
    create_initial_dashboard_state,
)

__all__ = [
    "DocumentAnalysisState",
    "CaseAnalysisState",
    # Criminal Case State
    "CriminalCaseState",
    "CrimeElementResult",
    "CrimeElementsResult",
    "SentencingFactorsResult",
    "ExpectedSentenceResult",
    "CriminalPrecedentResult",
    "get_crime_category",
    "CRIME_CATEGORY_MAP",
    # Risk & LLM Comparison
    "RiskAnalysisState",
    "LLMComparisonState",
    "LLMModelConfig",
    "ModelMetrics",
    # Week 13: Crawler State
    "CrawlState",
    "CrawlStatus",
    "DataSource",
    "CrawlMetrics",
    "CrawledDocument",
    "ProcessingStatus",
    "QualityCheck",
    "create_initial_crawl_state",
    # Week 13: Dashboard State
    "DashboardState",
    "TimeRange",
    "AnomalySeverity",
    "AnomalyType",
    "InsightCategory",
    "Anomaly",
    "Insight",
    "Trend",
    "create_initial_dashboard_state",
]
