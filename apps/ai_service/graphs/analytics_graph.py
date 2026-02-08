"""
Analytics Workflow Graph

Phase 4 - Week 13: LangGraph 기반 Analytics Workflow

설계 원칙:
- Checkpointing 불필요 (즉시 실행, 상태 저장 불필요)
- MCP Tools 불필요 (Simple CRUD 작업, 내부 로직)
- 직접 Python 함수 호출 (Django ORM, 데이터 분석)

워크플로우:
    START → collect_metrics → analyze → detect_anomalies → [alert if needed] → generate_insights → END

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""

import asyncio
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime, timedelta
from loguru import logger

from langgraph.graph import StateGraph, START, END

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


# =============================================================================
# Helper Functions (DB Query Helpers)
# =============================================================================

async def query_document_stats(
    organization_id: Optional[str],
    time_range: str
) -> Dict[str, Any]:
    """
    문서 통계 조회 (Django ORM 직접 호출)

    Simple CRUD 작업으로 MCP Tool 불필요
    """
    # Django ORM에서 동기 함수이므로 run_in_executor 사용
    import asyncio
    from functools import partial

    def _query():
        try:
            # Django 설정이 필요한 경우
            import django
            import os
            if not os.environ.get('DJANGO_SETTINGS_MODULE'):
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_api.settings')
                django.setup()

            from django.db.models import Count
            from django.utils import timezone

            # Document 모델 import (실제 경로에 맞게 조정)
            try:
                from documents.models import Document, Summary, RiskAnalysisResult
            except ImportError:
                # 모델이 없는 경우 더미 데이터 반환
                logger.warning("[query_document_stats] Document model not found, returning dummy data")
                return {
                    "total_count": 0,
                    "by_status": {},
                    "by_type": {},
                    "daily_uploads": 0,
                    "weekly_uploads": 0,
                    "historical_avg": 0.0,
                }

            # 시간 범위 계산
            now = timezone.now()
            if time_range == TimeRange.HOUR.value:
                start_date = now - timedelta(hours=1)
            elif time_range == TimeRange.DAY.value:
                start_date = now - timedelta(days=1)
            elif time_range == TimeRange.WEEK.value:
                start_date = now - timedelta(days=7)
            elif time_range == TimeRange.MONTH.value:
                start_date = now - timedelta(days=30)
            else:
                start_date = now - timedelta(days=90)

            # 기본 queryset
            qs = Document.objects.all()
            if organization_id:
                # organization_id 필터가 있으면 적용 (실제 필드명에 맞게 조정)
                pass

            # 전체 문서 수
            total_count = qs.count()

            # 상태별 집계
            by_status = dict(qs.values('status').annotate(count=Count('id')).values_list('status', 'count'))

            # 타입별 집계
            by_type = dict(qs.values('doc_type').annotate(count=Count('id')).values_list('doc_type', 'count'))

            # 일일 업로드
            daily_uploads = qs.filter(created_at__gte=now - timedelta(days=1)).count()

            # 주간 업로드
            weekly_uploads = qs.filter(created_at__gte=now - timedelta(days=7)).count()

            # 과거 평균 (90일 기준)
            past_90_days = qs.filter(created_at__gte=now - timedelta(days=90)).count()
            historical_avg = past_90_days / 90 if past_90_days > 0 else 0.0

            return {
                "total_count": total_count,
                "by_status": by_status,
                "by_type": by_type,
                "daily_uploads": daily_uploads,
                "weekly_uploads": weekly_uploads,
                "historical_avg": historical_avg,
            }

        except Exception as e:
            logger.error(f"[query_document_stats] Error: {e}")
            return {
                "total_count": 0,
                "by_status": {},
                "by_type": {},
                "daily_uploads": 0,
                "weekly_uploads": 0,
                "historical_avg": 0.0,
            }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _query)


async def query_user_activity(
    user_id: Optional[str],
    time_range: str
) -> Dict[str, Any]:
    """
    사용자 활동 통계 조회

    Simple CRUD 작업으로 MCP Tool 불필요
    """
    def _query():
        try:
            import django
            import os
            if not os.environ.get('DJANGO_SETTINGS_MODULE'):
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_api.settings')
                django.setup()

            from django.db.models import Count
            from django.utils import timezone

            try:
                from cases.models import ChatHistory
                from users.models import User
            except ImportError:
                logger.warning("[query_user_activity] Models not found, returning dummy data")
                return {
                    "active_users": 0,
                    "total_queries": 0,
                    "avg_queries_per_user": 0.0,
                    "chat_sessions": 0,
                }

            # 시간 범위 계산
            now = timezone.now()
            if time_range == TimeRange.HOUR.value:
                start_date = now - timedelta(hours=1)
            elif time_range == TimeRange.DAY.value:
                start_date = now - timedelta(days=1)
            elif time_range == TimeRange.WEEK.value:
                start_date = now - timedelta(days=7)
            elif time_range == TimeRange.MONTH.value:
                start_date = now - timedelta(days=30)
            else:
                start_date = now - timedelta(days=90)

            # 채팅 이력 조회
            chat_qs = ChatHistory.objects.filter(created_at__gte=start_date)

            # 총 쿼리 수
            total_queries = chat_qs.count()

            # 활성 사용자 수
            active_users = chat_qs.values('user_id').distinct().count()

            # 평균 쿼리 수
            avg_queries = total_queries / active_users if active_users > 0 else 0.0

            # 세션 수 (case별로 그룹)
            chat_sessions = chat_qs.values('case_id').distinct().count()

            return {
                "active_users": active_users,
                "total_queries": total_queries,
                "avg_queries_per_user": avg_queries,
                "chat_sessions": chat_sessions,
            }

        except Exception as e:
            logger.error(f"[query_user_activity] Error: {e}")
            return {
                "active_users": 0,
                "total_queries": 0,
                "avg_queries_per_user": 0.0,
                "chat_sessions": 0,
            }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _query)


async def query_risk_trends(
    organization_id: Optional[str]
) -> Dict[str, Any]:
    """
    리스크 트렌드 통계 조회

    Simple CRUD 작업으로 MCP Tool 불필요
    """
    def _query():
        try:
            import django
            import os
            if not os.environ.get('DJANGO_SETTINGS_MODULE'):
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_api.settings')
                django.setup()

            from django.db.models import Count, Avg
            from django.utils import timezone

            try:
                from documents.models import RiskAnalysisResult
            except ImportError:
                logger.warning("[query_risk_trends] RiskAnalysisResult model not found, returning dummy data")
                return {
                    "analyzed_count": 0,
                    "avg_score": 0.0,
                    "by_severity": {},
                    "high_risk_count": 0,
                }

            now = timezone.now()
            start_date = now - timedelta(days=30)

            qs = RiskAnalysisResult.objects.filter(created_at__gte=start_date)

            # 분석된 문서 수
            analyzed_count = qs.count()

            # 평균 점수
            avg_data = qs.aggregate(avg_score=Avg('overall_risk_score'))
            avg_score = avg_data.get('avg_score') or 0.0

            # 심각도별 집계 (risk_items JSON 필드에서)
            # 실제 구현은 DB 구조에 따라 달라짐
            by_severity = {
                "CRITICAL": 0,
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
                "INFO": 0,
            }

            # 고위험 문서 수 (점수 70 이상)
            high_risk_count = qs.filter(overall_risk_score__gte=70).count()

            return {
                "analyzed_count": analyzed_count,
                "avg_score": float(avg_score),
                "by_severity": by_severity,
                "high_risk_count": high_risk_count,
            }

        except Exception as e:
            logger.error(f"[query_risk_trends] Error: {e}")
            return {
                "analyzed_count": 0,
                "avg_score": 0.0,
                "by_severity": {},
                "high_risk_count": 0,
            }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _query)


async def calculate_cost_metrics(
    organization_id: Optional[str]
) -> Dict[str, Any]:
    """
    비용 메트릭 계산

    LLM 호출 로그를 기반으로 비용 추정 (실제 구현은 로깅 방식에 따라 달라짐)
    """
    # 실제 구현에서는 LLM 호출 로그 테이블에서 집계
    # 현재는 더미 데이터 반환
    return {
        "total_tokens": 0,
        "estimated_cost": 0.0,
        "by_model": {
            "gpt-4": 0.0,
            "gpt-3.5-turbo": 0.0,
            "claude-3": 0.0,
        },
    }


# =============================================================================
# Node Functions (async)
# =============================================================================

async def collect_metrics_node(state: DashboardState) -> Dict[str, Any]:
    """
    메트릭 수집 노드

    Django ORM을 직접 호출하여 메트릭을 수집합니다.
    MCP Tools 불필요: Simple CRUD 작업

    Returns:
        업데이트된 상태 필드 (raw_metrics, completed_steps)
    """
    time_range = state.get("time_range", TimeRange.DAY.value)
    user_id = state.get("user_id")
    organization_id = state.get("organization_id")

    logger.info(f"[collect_metrics_node] time_range={time_range}")

    completed_steps = list(state.get("completed_steps", []))

    try:
        # 병렬로 여러 메트릭 수집
        doc_stats, user_activity, risk_trends, cost_metrics = await asyncio.gather(
            query_document_stats(organization_id, time_range),
            query_user_activity(user_id, time_range),
            query_risk_trends(organization_id),
            calculate_cost_metrics(organization_id),
        )

        raw_metrics = {
            "documents": doc_stats,
            "activity": user_activity,
            "risks": risk_trends,
            "costs": cost_metrics,
            "collected_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"[collect_metrics_node] Collected metrics: docs={doc_stats.get('total_count', 0)}, "
                   f"users={user_activity.get('active_users', 0)}")

        completed_steps.append("collect_metrics")

        return {
            "raw_metrics": raw_metrics,
            "completed_steps": completed_steps,
        }

    except Exception as e:
        logger.error(f"[collect_metrics_node] Error: {e}")
        processing_errors = list(state.get("processing_errors", []))
        processing_errors.append(f"collect_metrics: {str(e)}")
        return {
            "raw_metrics": None,
            "processing_errors": processing_errors,
        }


async def analyze_node(state: DashboardState) -> Dict[str, Any]:
    """
    데이터 분석 노드

    수집된 메트릭을 기반으로 분석 데이터를 생성합니다.

    Returns:
        업데이트된 상태 필드 (analyzed_data, trends, completed_steps)
    """
    raw_metrics = state.get("raw_metrics")

    logger.info("[analyze_node] Analyzing metrics")

    completed_steps = list(state.get("completed_steps", []))

    if not raw_metrics:
        logger.warning("[analyze_node] No raw metrics to analyze")
        processing_errors = list(state.get("processing_errors", []))
        processing_errors.append("analyze: No raw metrics")
        return {
            "analyzed_data": None,
            "processing_errors": processing_errors,
        }

    try:
        documents = raw_metrics.get("documents", {})
        activity = raw_metrics.get("activity", {})
        risks = raw_metrics.get("risks", {})
        costs = raw_metrics.get("costs", {})

        # 분석 데이터 생성
        analyzed_data = {
            "summary": {
                "total_documents": documents.get("total_count", 0),
                "active_users": activity.get("active_users", 0),
                "risk_analyzed_documents": risks.get("analyzed_count", 0),
                "high_risk_documents": risks.get("high_risk_count", 0),
                "estimated_cost": costs.get("estimated_cost", 0.0),
            },
            "document_analysis": {
                "status_distribution": documents.get("by_status", {}),
                "type_distribution": documents.get("by_type", {}),
                "upload_rate": {
                    "daily": documents.get("daily_uploads", 0),
                    "weekly": documents.get("weekly_uploads", 0),
                    "historical_avg": documents.get("historical_avg", 0.0),
                },
            },
            "user_analysis": {
                "engagement_rate": (
                    activity.get("avg_queries_per_user", 0) / 10
                    if activity.get("avg_queries_per_user", 0) > 0
                    else 0.0
                ),
                "session_count": activity.get("chat_sessions", 0),
            },
            "risk_analysis": {
                "avg_risk_score": risks.get("avg_score", 0.0),
                "severity_distribution": risks.get("by_severity", {}),
                "high_risk_ratio": (
                    risks.get("high_risk_count", 0) / max(risks.get("analyzed_count", 1), 1)
                ),
            },
        }

        # 트렌드 생성
        trends = {}

        # 문서 업로드 트렌드
        daily = documents.get("daily_uploads", 0)
        historical = documents.get("historical_avg", 0.0)
        if historical > 0:
            change_percent = ((daily - historical) / historical) * 100
            direction = "up" if change_percent > 5 else ("down" if change_percent < -5 else "stable")
        else:
            change_percent = 0.0
            direction = "stable"

        trends["document_uploads"] = Trend(
            metric="document_uploads",
            direction=direction,
            change_percent=round(change_percent, 2),
            period=state.get("time_range", TimeRange.DAY.value),
            data_points=[],
        )

        # 리스크 트렌드
        avg_risk = risks.get("avg_score", 0.0)
        if avg_risk >= 70:
            risk_direction = "up"
        elif avg_risk <= 30:
            risk_direction = "down"
        else:
            risk_direction = "stable"

        trends["risk_score"] = Trend(
            metric="risk_score",
            direction=risk_direction,
            change_percent=0.0,  # 실제로는 이전 기간과 비교 필요
            period=state.get("time_range", TimeRange.DAY.value),
            data_points=[],
        )

        logger.info(f"[analyze_node] Analysis complete: docs={analyzed_data['summary']['total_documents']}")

        completed_steps.append("analyze")

        return {
            "analyzed_data": analyzed_data,
            "trends": trends,
            "completed_steps": completed_steps,
        }

    except Exception as e:
        logger.error(f"[analyze_node] Error: {e}")
        processing_errors = list(state.get("processing_errors", []))
        processing_errors.append(f"analyze: {str(e)}")
        return {
            "analyzed_data": None,
            "processing_errors": processing_errors,
        }


async def detect_anomalies_node(state: DashboardState) -> Dict[str, Any]:
    """
    이상 탐지 노드

    분석된 데이터에서 이상 징후를 탐지합니다.

    Returns:
        업데이트된 상태 필드 (anomalies, alert_triggered, completed_steps)
    """
    raw_metrics = state.get("raw_metrics")
    analyzed_data = state.get("analyzed_data")

    logger.info("[detect_anomalies_node] Detecting anomalies")

    completed_steps = list(state.get("completed_steps", []))
    anomalies: List[Anomaly] = []
    alert_triggered = False

    if not raw_metrics or not analyzed_data:
        logger.warning("[detect_anomalies_node] No data for anomaly detection")
        completed_steps.append("detect_anomalies")
        return {
            "anomalies": [],
            "alert_triggered": False,
            "completed_steps": completed_steps,
        }

    try:
        documents = raw_metrics.get("documents", {})
        activity = raw_metrics.get("activity", {})
        risks = raw_metrics.get("risks", {})

        # 이상 탐지 규칙

        # 1. 문서 업로드 급증 탐지
        daily_uploads = documents.get("daily_uploads", 0)
        historical_avg = documents.get("historical_avg", 0.0)

        if historical_avg > 0 and daily_uploads > historical_avg * 2:
            deviation = ((daily_uploads - historical_avg) / historical_avg) * 100
            anomalies.append(Anomaly(
                type=AnomalyType.SPIKE.value,
                metric="document_uploads",
                severity=AnomalySeverity.MEDIUM.value,
                message=f"문서 업로드가 평소({historical_avg:.1f})보다 {deviation:.0f}% 증가했습니다.",
                current_value=float(daily_uploads),
                expected_value=historical_avg,
                deviation_percent=deviation,
                detected_at=datetime.utcnow().isoformat(),
            ))

        # 2. 문서 업로드 급감 탐지
        if historical_avg > 0 and daily_uploads < historical_avg * 0.5:
            deviation = ((historical_avg - daily_uploads) / historical_avg) * 100
            anomalies.append(Anomaly(
                type=AnomalyType.DROP.value,
                metric="document_uploads",
                severity=AnomalySeverity.LOW.value,
                message=f"문서 업로드가 평소({historical_avg:.1f})보다 {deviation:.0f}% 감소했습니다.",
                current_value=float(daily_uploads),
                expected_value=historical_avg,
                deviation_percent=-deviation,
                detected_at=datetime.utcnow().isoformat(),
            ))

        # 3. 고위험 문서 비율 임계값 초과
        high_risk_ratio = analyzed_data.get("risk_analysis", {}).get("high_risk_ratio", 0)
        if high_risk_ratio > 0.3:  # 30% 초과
            anomalies.append(Anomaly(
                type=AnomalyType.THRESHOLD.value,
                metric="high_risk_ratio",
                severity=AnomalySeverity.HIGH.value,
                message=f"고위험 문서 비율({high_risk_ratio*100:.1f}%)이 30% 임계값을 초과했습니다.",
                current_value=high_risk_ratio,
                expected_value=0.3,
                deviation_percent=((high_risk_ratio - 0.3) / 0.3) * 100,
                detected_at=datetime.utcnow().isoformat(),
            ))
            alert_triggered = True  # HIGH 이상 심각도 → 알림

        # 4. 사용자 활동 급감 탐지
        active_users = activity.get("active_users", 0)
        if active_users == 0 and activity.get("total_queries", 0) == 0:
            anomalies.append(Anomaly(
                type=AnomalyType.DROP.value,
                metric="user_activity",
                severity=AnomalySeverity.MEDIUM.value,
                message="사용자 활동이 없습니다. 시스템 점검이 필요할 수 있습니다.",
                current_value=0.0,
                expected_value=1.0,
                deviation_percent=-100.0,
                detected_at=datetime.utcnow().isoformat(),
            ))

        # 5. 평균 리스크 점수 급등
        avg_risk_score = risks.get("avg_score", 0.0)
        if avg_risk_score >= 80:
            anomalies.append(Anomaly(
                type=AnomalyType.THRESHOLD.value,
                metric="avg_risk_score",
                severity=AnomalySeverity.CRITICAL.value,
                message=f"평균 리스크 점수({avg_risk_score:.1f})가 위험 수준(80)을 초과했습니다.",
                current_value=avg_risk_score,
                expected_value=50.0,
                deviation_percent=((avg_risk_score - 50) / 50) * 100,
                detected_at=datetime.utcnow().isoformat(),
            ))
            alert_triggered = True  # CRITICAL 심각도 → 알림

        logger.info(f"[detect_anomalies_node] Found {len(anomalies)} anomalies, alert={alert_triggered}")

        completed_steps.append("detect_anomalies")

        return {
            "anomalies": anomalies,
            "alert_triggered": alert_triggered,
            "completed_steps": completed_steps,
        }

    except Exception as e:
        logger.error(f"[detect_anomalies_node] Error: {e}")
        processing_errors = list(state.get("processing_errors", []))
        processing_errors.append(f"detect_anomalies: {str(e)}")
        return {
            "anomalies": [],
            "alert_triggered": False,
            "processing_errors": processing_errors,
        }


async def alert_node(state: DashboardState) -> Dict[str, Any]:
    """
    알림 노드

    HIGH/CRITICAL 이상 탐지 시 알림을 발송합니다.

    Returns:
        업데이트된 상태 필드 (completed_steps)
    """
    anomalies = state.get("anomalies", [])

    logger.info(f"[alert_node] Processing {len(anomalies)} anomalies")

    completed_steps = list(state.get("completed_steps", []))

    # HIGH/CRITICAL 이상만 필터링
    critical_anomalies = [
        a for a in anomalies
        if a.get("severity") in [AnomalySeverity.HIGH.value, AnomalySeverity.CRITICAL.value]
    ]

    if critical_anomalies:
        # TODO: 실제 알림 발송 로직 구현
        # - 이메일 알림
        # - Slack 웹훅
        # - 내부 알림 시스템
        for anomaly in critical_anomalies:
            logger.warning(
                f"[ALERT] {anomaly['severity']}: {anomaly['metric']} - {anomaly['message']}"
            )

    completed_steps.append("alert")

    return {
        "completed_steps": completed_steps,
    }


async def generate_insights_node(state: DashboardState) -> Dict[str, Any]:
    """
    인사이트 생성 노드

    분석 결과와 이상 탐지 결과를 바탕으로 인사이트와 권장사항을 생성합니다.

    Returns:
        업데이트된 상태 필드 (insights, recommendations, completed_steps)
    """
    analyzed_data = state.get("analyzed_data")
    anomalies = state.get("anomalies", [])
    trends = state.get("trends", {})

    logger.info("[generate_insights_node] Generating insights")

    completed_steps = list(state.get("completed_steps", []))
    insights: List[Insight] = []
    recommendations: List[str] = []

    if not analyzed_data:
        logger.warning("[generate_insights_node] No analyzed data for insights")
        completed_steps.append("generate_insights")
        return {
            "insights": [],
            "recommendations": [],
            "completed_steps": completed_steps,
        }

    try:
        summary = analyzed_data.get("summary", {})
        doc_analysis = analyzed_data.get("document_analysis", {})
        risk_analysis = analyzed_data.get("risk_analysis", {})

        # 1. 사용량 인사이트
        total_docs = summary.get("total_documents", 0)
        active_users = summary.get("active_users", 0)

        if total_docs > 0:
            insights.append(Insight(
                category=InsightCategory.USAGE.value,
                title="문서 관리 현황",
                description=f"현재 {total_docs}개의 문서가 관리되고 있으며, {active_users}명의 사용자가 활동 중입니다.",
                action_items=[
                    "정기적인 문서 정리 및 아카이빙 검토",
                    "사용자 피드백 수집을 통한 서비스 개선",
                ],
                priority=3,
            ))

        # 2. 리스크 인사이트
        high_risk_count = summary.get("high_risk_documents", 0)
        avg_risk = risk_analysis.get("avg_risk_score", 0.0)

        if high_risk_count > 0:
            insights.append(Insight(
                category=InsightCategory.RISK.value,
                title="고위험 문서 검토 필요",
                description=f"{high_risk_count}개의 고위험 문서가 발견되었습니다. 평균 리스크 점수: {avg_risk:.1f}",
                action_items=[
                    "고위험 문서 우선 검토",
                    "리스크 완화 조치 계획 수립",
                    "관련 담당자에게 알림",
                ],
                priority=1,
            ))
            recommendations.append(f"⚠️ {high_risk_count}개의 고위험 문서를 즉시 검토하세요.")

        # 3. 트렌드 기반 인사이트
        doc_trend = trends.get("document_uploads", {})
        if doc_trend:
            direction = doc_trend.get("direction", "stable")
            change = doc_trend.get("change_percent", 0)

            if direction == "up" and change > 50:
                insights.append(Insight(
                    category=InsightCategory.USAGE.value,
                    title="문서 업로드 급증",
                    description=f"문서 업로드가 {change:.0f}% 증가했습니다. 용량 및 처리 성능을 확인하세요.",
                    action_items=[
                        "스토리지 용량 확인",
                        "처리 대기열 모니터링",
                        "필요시 리소스 확장",
                    ],
                    priority=2,
                ))
                recommendations.append("📈 문서 업로드 증가에 대비한 리소스 확인을 권장합니다.")

            elif direction == "down" and change > 30:
                insights.append(Insight(
                    category=InsightCategory.USAGE.value,
                    title="문서 업로드 감소",
                    description=f"문서 업로드가 {abs(change):.0f}% 감소했습니다.",
                    action_items=[
                        "사용자 피드백 확인",
                        "시스템 접근성 점검",
                    ],
                    priority=4,
                ))

        # 4. 이상 탐지 기반 인사이트
        critical_anomalies = [
            a for a in anomalies
            if a.get("severity") in [AnomalySeverity.CRITICAL.value, AnomalySeverity.HIGH.value]
        ]

        if critical_anomalies:
            anomaly_msgs = [a.get("message", "") for a in critical_anomalies]
            insights.append(Insight(
                category=InsightCategory.RISK.value,
                title="긴급 주의 필요",
                description=f"{len(critical_anomalies)}개의 심각한 이상이 탐지되었습니다.",
                action_items=[
                    "탐지된 이상 즉시 확인",
                    "관련 시스템 점검",
                    "필요시 긴급 대응",
                ],
                priority=1,
            ))
            for msg in anomaly_msgs[:3]:
                recommendations.append(f"🚨 {msg}")

        # 5. 비용 인사이트 (비용 데이터가 있는 경우)
        estimated_cost = summary.get("estimated_cost", 0.0)
        if estimated_cost > 0:
            insights.append(Insight(
                category=InsightCategory.COST.value,
                title="비용 현황",
                description=f"현재 예상 비용: ${estimated_cost:.2f}",
                action_items=[
                    "비용 효율화 방안 검토",
                    "모델 선택 최적화",
                ],
                priority=4,
            ))

        # 기본 권장사항 추가
        if not recommendations:
            recommendations.append("✅ 현재 시스템이 정상적으로 운영되고 있습니다.")

        # 우선순위 정렬
        insights.sort(key=lambda x: x.get("priority", 5))

        logger.info(f"[generate_insights_node] Generated {len(insights)} insights, {len(recommendations)} recommendations")

        completed_steps.append("generate_insights")

        return {
            "insights": insights,
            "recommendations": recommendations,
            "completed_steps": completed_steps,
        }

    except Exception as e:
        logger.error(f"[generate_insights_node] Error: {e}")
        processing_errors = list(state.get("processing_errors", []))
        processing_errors.append(f"generate_insights: {str(e)}")
        return {
            "insights": [],
            "recommendations": [],
            "processing_errors": processing_errors,
        }


# =============================================================================
# Routing Functions
# =============================================================================

def has_anomalies(state: DashboardState) -> bool:
    """
    이상 탐지 여부 확인

    Returns:
        True: HIGH/CRITICAL 이상이 있어 알림 필요
        False: 알림 불필요
    """
    return state.get("alert_triggered", False)


# =============================================================================
# Workflow Builder
# =============================================================================

def create_analytics_workflow() -> StateGraph:
    """
    Analytics Workflow StateGraph 생성

    워크플로우:
        START → collect_metrics → analyze → detect_anomalies
                                                    ↓
                                    [alert if needed] → generate_insights → END

    Checkpointing 불필요: 즉시 실행, 상태 저장 불필요

    Returns:
        Compiled StateGraph (checkpointer 없음)
    """
    workflow = StateGraph(DashboardState)

    # 노드 추가
    workflow.add_node("collect_metrics", collect_metrics_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("detect_anomalies", detect_anomalies_node)
    workflow.add_node("alert", alert_node)
    workflow.add_node("generate_insights", generate_insights_node)

    # 엣지 정의
    workflow.add_edge(START, "collect_metrics")
    workflow.add_edge("collect_metrics", "analyze")
    workflow.add_edge("analyze", "detect_anomalies")

    # 조건부 분기: 이상 탐지 시 알림
    workflow.add_conditional_edges(
        "detect_anomalies",
        has_anomalies,
        {
            True: "alert",
            False: "generate_insights",
        }
    )

    # alert 후 인사이트 생성
    workflow.add_edge("alert", "generate_insights")

    # 종료
    workflow.add_edge("generate_insights", END)

    # Checkpointing 불필요 - workflow.compile() 사용 (checkpointer 없음)
    return workflow.compile()


# =============================================================================
# AnalyticsWorkflow Class
# =============================================================================

class AnalyticsWorkflow:
    """
    Analytics Workflow 실행 클래스

    Checkpointing 불필요 워크플로우:
    - 즉시 실행 (수 초 이내)
    - 상태 저장 불필요
    - 재실행 용이

    사용 예:
        workflow = AnalyticsWorkflow()
        result = await workflow.generate_report(
            time_range=TimeRange.DAY.value,
            user_id="user-123",
        )
    """

    def __init__(self):
        """Analytics Workflow 초기화"""
        self.graph = create_analytics_workflow()
        logger.info("[AnalyticsWorkflow] Initialized (no checkpointing)")

    async def generate_report(
        self,
        time_range: str = TimeRange.DAY.value,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        분석 리포트 생성

        Args:
            time_range: 분석 시간 범위 (1h, 1d, 7d, 30d, 90d)
            user_id: 사용자 ID (선택)
            organization_id: 조직 ID (선택)

        Returns:
            {
                "success": bool,
                "summary": {...},
                "analyzed_data": {...},
                "anomalies": [...],
                "insights": [...],
                "recommendations": [...],
                "trends": {...},
                "errors": [...],
            }
        """
        logger.info(f"[AnalyticsWorkflow] Generating report: time_range={time_range}")

        # 초기 상태 생성
        initial_state = create_initial_dashboard_state(
            time_range=time_range,
            user_id=user_id,
            organization_id=organization_id,
        )

        try:
            # 워크플로우 실행
            result = await self.graph.ainvoke(initial_state)

            success = len(result.get("processing_errors", [])) == 0

            return {
                "success": success,
                "summary": result.get("analyzed_data", {}).get("summary", {}),
                "analyzed_data": result.get("analyzed_data"),
                "anomalies": result.get("anomalies", []),
                "insights": result.get("insights", []),
                "recommendations": result.get("recommendations", []),
                "trends": result.get("trends", {}),
                "errors": result.get("processing_errors", []),
                "completed_steps": result.get("completed_steps", []),
            }

        except Exception as e:
            logger.error(f"[AnalyticsWorkflow] Error: {e}")
            return {
                "success": False,
                "summary": {},
                "analyzed_data": None,
                "anomalies": [],
                "insights": [],
                "recommendations": [],
                "trends": {},
                "errors": [str(e)],
                "completed_steps": [],
            }

    async def get_overview(
        self,
        time_range: str = TimeRange.DAY.value,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        대시보드 개요 조회 (요약 정보만)

        Args:
            time_range: 분석 시간 범위
            organization_id: 조직 ID (선택)

        Returns:
            {
                "total_documents": int,
                "active_users": int,
                "high_risk_documents": int,
                "anomaly_count": int,
            }
        """
        result = await self.generate_report(
            time_range=time_range,
            organization_id=organization_id,
        )

        summary = result.get("summary", {})
        anomalies = result.get("anomalies", [])

        return {
            "total_documents": summary.get("total_documents", 0),
            "active_users": summary.get("active_users", 0),
            "high_risk_documents": summary.get("high_risk_documents", 0),
            "anomaly_count": len(anomalies),
            "time_range": time_range,
        }

    async def get_trends(
        self,
        time_range: str = TimeRange.WEEK.value,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        트렌드 데이터 조회

        Args:
            time_range: 분석 시간 범위
            organization_id: 조직 ID (선택)

        Returns:
            트렌드 데이터 딕셔너리
        """
        result = await self.generate_report(
            time_range=time_range,
            organization_id=organization_id,
        )

        return {
            "trends": result.get("trends", {}),
            "time_range": time_range,
        }


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "AnalyticsWorkflow",
    "create_analytics_workflow",
    "collect_metrics_node",
    "analyze_node",
    "detect_anomalies_node",
    "alert_node",
    "generate_insights_node",
]
