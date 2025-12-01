"""
V2 Analytics Router - LangGraph Based

Phase 4 - Week 13: LangGraph 기반 Analytics API

특징:
- LangGraph StateGraph 기반 워크플로우
- Checkpointing 불필요 (즉시 실행, 상태 저장 불필요)
- MCP Tools 불필요 (Simple CRUD 작업, 내부 로직)
- 직접 Python 함수 호출 (Django ORM)

엔드포인트:
- POST /v2/analytics/generate - 분석 리포트 생성
- GET /v2/analytics/overview - 대시보드 개요
- GET /v2/analytics/trends - 트렌드 데이터
- GET /v2/analytics/health - 헬스체크
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from apps.ai_service.graphs.analytics_graph import AnalyticsWorkflow
from apps.ai_service.workflows.states.dashboard_state import (
    TimeRange,
    AnomalySeverity,
    AnomalyType,
    InsightCategory,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/analytics", tags=["analytics-v2"])


# ===== Request/Response Models =====

class AnalyticsGenerateRequest(BaseModel):
    """분석 리포트 생성 요청"""
    time_range: str = Field(
        default=TimeRange.DAY.value,
        description="분석 시간 범위 (1h, 1d, 7d, 30d, 90d)"
    )
    user_id: Optional[str] = Field(
        None,
        description="사용자 ID (선택)"
    )
    organization_id: Optional[str] = Field(
        None,
        description="조직 ID (선택)"
    )


class AnomalyResponse(BaseModel):
    """이상 탐지 결과"""
    type: str
    metric: str
    severity: str
    message: str
    current_value: float
    expected_value: float
    deviation_percent: float
    detected_at: str


class InsightResponse(BaseModel):
    """인사이트"""
    category: str
    title: str
    description: str
    action_items: List[str]
    priority: int


class TrendResponse(BaseModel):
    """트렌드 데이터"""
    metric: str
    direction: str
    change_percent: float
    period: str


class SummaryResponse(BaseModel):
    """요약 데이터"""
    total_documents: int = 0
    active_users: int = 0
    risk_analyzed_documents: int = 0
    high_risk_documents: int = 0
    estimated_cost: float = 0.0


class AnalyticsGenerateResponse(BaseModel):
    """분석 리포트 응답"""
    success: bool
    summary: SummaryResponse
    analyzed_data: Optional[Dict[str, Any]] = None
    anomalies: List[AnomalyResponse] = []
    insights: List[InsightResponse] = []
    recommendations: List[str] = []
    trends: Dict[str, TrendResponse] = {}
    errors: List[str] = []
    completed_steps: List[str] = []
    timestamp: str
    version: str = "v2"


class OverviewResponse(BaseModel):
    """대시보드 개요 응답"""
    total_documents: int
    active_users: int
    high_risk_documents: int
    anomaly_count: int
    time_range: str
    timestamp: str
    version: str = "v2"


class TrendsResponse(BaseModel):
    """트렌드 데이터 응답"""
    trends: Dict[str, Any]
    time_range: str
    timestamp: str
    version: str = "v2"


# ===== API Endpoints =====

@router.post("/generate", response_model=AnalyticsGenerateResponse)
async def generate_analytics_report(request: AnalyticsGenerateRequest):
    """
    분석 리포트 생성 (v2)

    워크플로우:
    1. collect_metrics_node: 메트릭 수집 (Django ORM)
    2. analyze_node: 데이터 분석
    3. detect_anomalies_node: 이상 탐지
    4. alert_node: 알림 발송 (HIGH/CRITICAL 이상 시)
    5. generate_insights_node: 인사이트 생성

    **Checkpointing 불필요**: 즉시 실행, 상태 저장 불필요

    Args:
        request: 분석 요청

    Returns:
        분석 리포트
    """
    try:
        logger.info(f"[v2/analytics/generate] time_range={request.time_range}")

        # 시간 범위 유효성 검사
        valid_ranges = [tr.value for tr in TimeRange]
        if request.time_range not in valid_ranges:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time_range. Must be one of: {valid_ranges}"
            )

        # 워크플로우 실행
        workflow = AnalyticsWorkflow()
        result = await workflow.generate_report(
            time_range=request.time_range,
            user_id=request.user_id,
            organization_id=request.organization_id,
        )

        # 응답 변환
        summary_data = result.get("summary", {})
        summary = SummaryResponse(
            total_documents=summary_data.get("total_documents", 0),
            active_users=summary_data.get("active_users", 0),
            risk_analyzed_documents=summary_data.get("risk_analyzed_documents", 0),
            high_risk_documents=summary_data.get("high_risk_documents", 0),
            estimated_cost=summary_data.get("estimated_cost", 0.0),
        )

        # 이상 탐지 결과 변환
        anomalies = [
            AnomalyResponse(
                type=a.get("type", ""),
                metric=a.get("metric", ""),
                severity=a.get("severity", ""),
                message=a.get("message", ""),
                current_value=a.get("current_value", 0.0),
                expected_value=a.get("expected_value", 0.0),
                deviation_percent=a.get("deviation_percent", 0.0),
                detected_at=a.get("detected_at", ""),
            )
            for a in result.get("anomalies", [])
        ]

        # 인사이트 변환
        insights = [
            InsightResponse(
                category=i.get("category", ""),
                title=i.get("title", ""),
                description=i.get("description", ""),
                action_items=i.get("action_items", []),
                priority=i.get("priority", 5),
            )
            for i in result.get("insights", [])
        ]

        # 트렌드 변환
        trends_data = result.get("trends", {})
        trends = {}
        for key, trend in trends_data.items():
            if isinstance(trend, dict):
                trends[key] = TrendResponse(
                    metric=trend.get("metric", key),
                    direction=trend.get("direction", "stable"),
                    change_percent=trend.get("change_percent", 0.0),
                    period=trend.get("period", request.time_range),
                )

        return AnalyticsGenerateResponse(
            success=result.get("success", False),
            summary=summary,
            analyzed_data=result.get("analyzed_data"),
            anomalies=anomalies,
            insights=insights,
            recommendations=result.get("recommendations", []),
            trends=trends,
            errors=result.get("errors", []),
            completed_steps=result.get("completed_steps", []),
            timestamp=datetime.now().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[v2/analytics/generate] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/overview", response_model=OverviewResponse)
async def get_analytics_overview(
    time_range: str = Query(
        default=TimeRange.DAY.value,
        description="분석 시간 범위 (1h, 1d, 7d, 30d, 90d)"
    ),
    organization_id: Optional[str] = Query(
        default=None,
        description="조직 ID (선택)"
    ),
):
    """
    대시보드 개요 조회 (v2)

    요약 정보만 빠르게 조회합니다.

    Args:
        time_range: 분석 시간 범위
        organization_id: 조직 ID (선택)

    Returns:
        대시보드 개요
    """
    try:
        logger.info(f"[v2/analytics/overview] time_range={time_range}")

        # 시간 범위 유효성 검사
        valid_ranges = [tr.value for tr in TimeRange]
        if time_range not in valid_ranges:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time_range. Must be one of: {valid_ranges}"
            )

        # 워크플로우 실행
        workflow = AnalyticsWorkflow()
        result = await workflow.get_overview(
            time_range=time_range,
            organization_id=organization_id,
        )

        return OverviewResponse(
            total_documents=result.get("total_documents", 0),
            active_users=result.get("active_users", 0),
            high_risk_documents=result.get("high_risk_documents", 0),
            anomaly_count=result.get("anomaly_count", 0),
            time_range=result.get("time_range", time_range),
            timestamp=datetime.now().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[v2/analytics/overview] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/trends", response_model=TrendsResponse)
async def get_analytics_trends(
    time_range: str = Query(
        default=TimeRange.WEEK.value,
        description="분석 시간 범위 (1h, 1d, 7d, 30d, 90d)"
    ),
    organization_id: Optional[str] = Query(
        default=None,
        description="조직 ID (선택)"
    ),
):
    """
    트렌드 데이터 조회 (v2)

    시간에 따른 변화 트렌드를 조회합니다.

    Args:
        time_range: 분석 시간 범위
        organization_id: 조직 ID (선택)

    Returns:
        트렌드 데이터
    """
    try:
        logger.info(f"[v2/analytics/trends] time_range={time_range}")

        # 시간 범위 유효성 검사
        valid_ranges = [tr.value for tr in TimeRange]
        if time_range not in valid_ranges:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time_range. Must be one of: {valid_ranges}"
            )

        # 워크플로우 실행
        workflow = AnalyticsWorkflow()
        result = await workflow.get_trends(
            time_range=time_range,
            organization_id=organization_id,
        )

        # 트렌드 데이터 변환
        trends = {}
        for key, trend in result.get("trends", {}).items():
            if isinstance(trend, dict):
                trends[key] = {
                    "metric": trend.get("metric", key),
                    "direction": trend.get("direction", "stable"),
                    "change_percent": trend.get("change_percent", 0.0),
                    "period": trend.get("period", time_range),
                    "data_points": trend.get("data_points", []),
                }

        return TrendsResponse(
            trends=trends,
            time_range=result.get("time_range", time_range),
            timestamp=datetime.now().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[v2/analytics/trends] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/health")
async def analytics_v2_health():
    """
    Analytics v2 헬스체크

    Returns:
        상태 정보
    """
    try:
        # 워크플로우 초기화 테스트
        workflow = AnalyticsWorkflow()

        return {
            "status": "healthy",
            "version": "v2",
            "engine": "LangGraph",
            "workflow": "analytics_workflow",
            "features": [
                "anomaly_detection",
                "insight_generation",
                "trend_analysis",
                "auto_alerting",
            ],
            "supported_time_ranges": [tr.value for tr in TimeRange],
            "checkpointing": False,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"[health] Error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ===== Additional Utility Endpoints =====

@router.get("/anomaly-types")
async def get_anomaly_types():
    """
    지원되는 이상 유형 목록

    Returns:
        이상 유형 목록
    """
    return {
        "anomaly_types": [at.value for at in AnomalyType],
        "severity_levels": [s.value for s in AnomalySeverity],
        "descriptions": {
            AnomalyType.SPIKE.value: "급격한 증가 감지",
            AnomalyType.DROP.value: "급격한 감소 감지",
            AnomalyType.TREND_CHANGE.value: "트렌드 변화 감지",
            AnomalyType.OUTLIER.value: "이상치 감지",
            AnomalyType.THRESHOLD.value: "임계값 초과 감지",
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/insight-categories")
async def get_insight_categories():
    """
    지원되는 인사이트 카테고리 목록

    Returns:
        인사이트 카테고리 목록
    """
    return {
        "categories": [ic.value for ic in InsightCategory],
        "descriptions": {
            InsightCategory.USAGE.value: "사용량 관련 인사이트",
            InsightCategory.PERFORMANCE.value: "성능 관련 인사이트",
            InsightCategory.COST.value: "비용 관련 인사이트",
            InsightCategory.RISK.value: "리스크 관련 인사이트",
            InsightCategory.RECOMMENDATION.value: "권장사항 인사이트",
        },
        "timestamp": datetime.now().isoformat()
    }
