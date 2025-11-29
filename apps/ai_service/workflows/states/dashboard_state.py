"""
Dashboard State

Phase 4 - Week 13: Analytics 워크플로우 상태 정의

Analytics 워크플로우:
1. collect_metrics_node: 메트릭 수집 (DB 쿼리)
2. analyze_node: 데이터 분석
3. detect_anomalies_node: 이상 탐지
4. generate_insights_node: 인사이트 생성

Checkpointing: 불필요 (즉시 실행, 상태 저장 불필요)
MCP Tools: 불필요 (Simple CRUD 작업, 내부 로직)
"""

from typing import TypedDict, List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class TimeRange(str, Enum):
    """시간 범위"""
    HOUR = "1h"         # 최근 1시간
    DAY = "1d"          # 최근 1일
    WEEK = "7d"         # 최근 7일
    MONTH = "30d"       # 최근 30일
    QUARTER = "90d"     # 최근 90일


class AnomalySeverity(str, Enum):
    """이상 심각도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    """이상 유형"""
    SPIKE = "spike"           # 급증
    DROP = "drop"             # 급감
    TREND_CHANGE = "trend_change"  # 트렌드 변화
    OUTLIER = "outlier"       # 이상치
    THRESHOLD = "threshold"   # 임계값 초과


class InsightCategory(str, Enum):
    """인사이트 카테고리"""
    USAGE = "usage"               # 사용량 관련
    PERFORMANCE = "performance"   # 성능 관련
    COST = "cost"                 # 비용 관련
    RISK = "risk"                 # 리스크 관련
    RECOMMENDATION = "recommendation"  # 권장사항


class DocumentMetrics(TypedDict):
    """문서 관련 메트릭"""
    total_count: int
    by_status: Dict[str, int]  # UPLOADED, PREPROCESSED, EMBEDDED
    by_type: Dict[str, int]    # CONTRACT, CASE, STATUTE, PRECEDENT
    daily_uploads: int
    weekly_uploads: int
    historical_avg: float


class RiskMetrics(TypedDict):
    """리스크 관련 메트릭"""
    analyzed_count: int
    avg_score: float
    by_severity: Dict[str, int]  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    high_risk_count: int


class UserActivityMetrics(TypedDict):
    """사용자 활동 메트릭"""
    active_users: int
    total_queries: int
    avg_queries_per_user: float
    chat_sessions: int


class CostMetrics(TypedDict):
    """비용 메트릭"""
    total_tokens: int
    estimated_cost: float
    by_model: Dict[str, float]


class PerformanceMetrics(TypedDict):
    """성능 메트릭"""
    avg_response_time: float  # seconds
    p95_response_time: float
    error_rate: float
    throughput: float  # requests per second


class Anomaly(TypedDict):
    """이상 탐지 결과"""
    type: str           # AnomalyType value
    metric: str         # 관련 메트릭 이름
    severity: str       # AnomalySeverity value
    message: str        # 설명 메시지
    current_value: float
    expected_value: float
    deviation_percent: float
    detected_at: str    # ISO format datetime


class Insight(TypedDict):
    """인사이트"""
    category: str       # InsightCategory value
    title: str          # 인사이트 제목
    description: str    # 상세 설명
    action_items: List[str]  # 권장 조치
    priority: int       # 우선순위 (1-5, 1이 가장 높음)


class Trend(TypedDict):
    """트렌드 데이터"""
    metric: str
    direction: str      # up, down, stable
    change_percent: float
    period: str
    data_points: List[Dict[str, Any]]


class DashboardState(TypedDict):
    """
    Analytics 워크플로우 상태 (Checkpointing 불필요)

    간단한 집계 및 분석 작업으로, 즉시 실행되며 상태 저장이 불필요.

    Attributes:
        user_id: 사용자 ID (Optional)
        organization_id: 조직 ID (Optional)
        time_range: 분석 시간 범위
        raw_metrics: 수집된 원시 메트릭
        analyzed_data: 분석된 데이터
        anomalies: 탐지된 이상 목록
        insights: 생성된 인사이트 목록
        trends: 트렌드 데이터
        recommendations: 권장사항 목록
        alert_triggered: 알림 발생 여부
        processing_errors: 처리 중 발생한 에러 목록
        completed_steps: 완료된 단계 목록
    """
    # Context
    user_id: Optional[str]
    organization_id: Optional[str]
    time_range: str  # TimeRange value

    # Raw data
    raw_metrics: Optional[Dict[str, Any]]

    # Analyzed results
    analyzed_data: Optional[Dict[str, Any]]
    anomalies: Optional[List[Anomaly]]
    insights: Optional[List[Insight]]
    trends: Optional[Dict[str, Trend]]
    recommendations: Optional[List[str]]

    # Alert management
    alert_triggered: bool

    # Processing status
    processing_errors: List[str]
    completed_steps: List[str]


def create_initial_dashboard_state(
    time_range: str = TimeRange.DAY.value,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> DashboardState:
    """
    초기 대시보드 상태 생성

    Args:
        time_range: 분석 시간 범위 (기본: 1일)
        user_id: 사용자 ID (선택)
        organization_id: 조직 ID (선택)

    Returns:
        초기화된 DashboardState
    """
    return DashboardState(
        user_id=user_id,
        organization_id=organization_id,
        time_range=time_range,
        raw_metrics=None,
        analyzed_data=None,
        anomalies=None,
        insights=None,
        trends=None,
        recommendations=None,
        alert_triggered=False,
        processing_errors=[],
        completed_steps=[],
    )
