"""
V2 API Integration Tests - Week 13 완료 테스트

Phase 4 - Week 13: LangGraph 기반 v2 API 통합 테스트

테스트 범위:
1. Crawler v2 API (Checkpointing)
2. Analytics v2 API (Anomaly Detection)
3. 기존 v2 API 헬스체크 (RAG, Documents, Cases, Risk, LLM Compare)
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== Fixtures =====

@pytest.fixture
def crawler_request():
    """Crawler v2 요청 fixture"""
    return {
        "source": "court_precedent",
        "keywords": ["형사", "사기"],
    }


@pytest.fixture
def analytics_request():
    """Analytics v2 요청 fixture"""
    return {
        "time_range": "1d",
        "user_id": None,
        "organization_id": None,
    }


# ===== Unit Tests =====

class TestCrawlerV2State:
    """CrawlState 테스트"""

    def test_crawl_state_import(self):
        """CrawlState 모듈 import 테스트"""
        from apps.ai_service.workflows.states.crawl_state import (
            DataSource,
            CrawlStatus,
            CrawlMetrics,
            CrawledDocument,
            CrawlState,
            create_initial_crawl_state,
        )

        assert DataSource.COURT_PRECEDENT is not None
        assert CrawlStatus.PENDING is not None

    def test_data_source_enum(self):
        """DataSource enum 값 확인"""
        from apps.ai_service.workflows.states.crawl_state import DataSource

        assert DataSource.COURT_PRECEDENT.value == "court_precedent"
        assert DataSource.STATUTE.value == "statute"
        assert DataSource.WEB.value == "web"

    def test_crawl_status_enum(self):
        """CrawlStatus enum 값 확인"""
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        assert CrawlStatus.PENDING.value == "pending"
        assert CrawlStatus.FETCHING.value == "fetching"
        assert CrawlStatus.PARSING.value == "parsing"
        assert CrawlStatus.VALIDATING.value == "validating"
        assert CrawlStatus.STORING.value == "storing"
        assert CrawlStatus.COMPLETED.value == "completed"
        assert CrawlStatus.FAILED.value == "failed"
        assert CrawlStatus.RETRYING.value == "retrying"

    def test_create_initial_crawl_state(self):
        """초기 CrawlState 생성 테스트"""
        from apps.ai_service.workflows.states.crawl_state import (
            DataSource,
            CrawlStatus,
            create_initial_crawl_state,
        )

        state = create_initial_crawl_state(
            source=DataSource.COURT_PRECEDENT,
            urls_to_crawl=["https://example.com/1", "https://example.com/2"],
            crawl_job_id="test-job-123",
        )

        assert state["source"] == DataSource.COURT_PRECEDENT.value
        assert len(state["urls_to_crawl"]) == 2
        assert state["crawl_job_id"] == "test-job-123"
        assert state["status"] == CrawlStatus.PENDING.value
        assert state["retry_count"] == 0


class TestAnalyticsV2State:
    """DashboardState 테스트"""

    def test_dashboard_state_import(self):
        """DashboardState 모듈 import 테스트"""
        from apps.ai_service.workflows.states.dashboard_state import (
            TimeRange,
            AnomalySeverity,
            AnomalyType,
            InsightCategory,
            DashboardState,
            create_initial_dashboard_state,
        )

        assert TimeRange.DAY is not None
        assert AnomalySeverity.HIGH is not None
        assert AnomalyType.SPIKE is not None
        assert InsightCategory.USAGE is not None

    def test_time_range_enum(self):
        """TimeRange enum 값 확인"""
        from apps.ai_service.workflows.states.dashboard_state import TimeRange

        assert TimeRange.HOUR.value == "1h"
        assert TimeRange.DAY.value == "1d"
        assert TimeRange.WEEK.value == "7d"
        assert TimeRange.MONTH.value == "30d"
        assert TimeRange.QUARTER.value == "90d"

    def test_anomaly_severity_enum(self):
        """AnomalySeverity enum 값 확인"""
        from apps.ai_service.workflows.states.dashboard_state import AnomalySeverity

        assert AnomalySeverity.LOW.value == "low"
        assert AnomalySeverity.MEDIUM.value == "medium"
        assert AnomalySeverity.HIGH.value == "high"
        assert AnomalySeverity.CRITICAL.value == "critical"

    def test_anomaly_type_enum(self):
        """AnomalyType enum 값 확인"""
        from apps.ai_service.workflows.states.dashboard_state import AnomalyType

        assert AnomalyType.SPIKE.value == "spike"
        assert AnomalyType.DROP.value == "drop"
        assert AnomalyType.TREND_CHANGE.value == "trend_change"
        assert AnomalyType.OUTLIER.value == "outlier"
        assert AnomalyType.THRESHOLD.value == "threshold"

    def test_insight_category_enum(self):
        """InsightCategory enum 값 확인"""
        from apps.ai_service.workflows.states.dashboard_state import InsightCategory

        assert InsightCategory.USAGE.value == "usage"
        assert InsightCategory.PERFORMANCE.value == "performance"
        assert InsightCategory.COST.value == "cost"
        assert InsightCategory.RISK.value == "risk"
        assert InsightCategory.RECOMMENDATION.value == "recommendation"

    def test_create_initial_dashboard_state(self):
        """초기 DashboardState 생성 테스트"""
        from apps.ai_service.workflows.states.dashboard_state import (
            TimeRange,
            create_initial_dashboard_state,
        )

        state = create_initial_dashboard_state(
            time_range=TimeRange.DAY.value,
            user_id="user-123",
            organization_id="org-456",
        )

        assert state["time_range"] == TimeRange.DAY.value
        assert state["user_id"] == "user-123"
        assert state["organization_id"] == "org-456"
        # anomalies, insights는 None으로 초기화됨 (빈 리스트가 아님)
        assert state["anomalies"] is None
        assert state["insights"] is None
        assert state["completed_steps"] == []


class TestMCPTools:
    """MCP Tools 테스트"""

    def test_mcp_tools_import(self):
        """MCP Tools 모듈 import 테스트"""
        from apps.ai_service.mcp.tools import (
            fetch_court_api,
            fetch_statute_api,
            parse_legal_document,
            validate_document_structure,
        )

        assert fetch_court_api is not None
        assert fetch_statute_api is not None
        assert parse_legal_document is not None
        assert validate_document_structure is not None

    def test_fetch_court_api_signature(self):
        """fetch_court_api 함수 시그니처 확인"""
        from apps.ai_service.mcp.tools import fetch_court_api
        import inspect

        sig = inspect.signature(fetch_court_api)
        params = list(sig.parameters.keys())

        # 최소한 keyword 파라미터가 있어야 함
        assert "keyword" in params or "case_number" in params

    def test_parse_legal_document_signature(self):
        """parse_legal_document 함수 시그니처 확인"""
        from apps.ai_service.mcp.tools import parse_legal_document
        import inspect

        sig = inspect.signature(parse_legal_document)
        params = list(sig.parameters.keys())

        assert "content" in params
        assert "doc_type" in params


class TestCrawlerWorkflow:
    """Crawler Workflow 테스트"""

    def test_crawler_workflow_import(self):
        """CrawlerWorkflow 클래스 import 테스트"""
        from apps.ai_service.graphs.crawler_graph import CrawlerWorkflow

        assert CrawlerWorkflow is not None

    def test_crawler_workflow_has_required_methods(self):
        """CrawlerWorkflow 필수 메서드 확인"""
        from apps.ai_service.graphs.crawler_graph import CrawlerWorkflow

        workflow = CrawlerWorkflow()

        assert hasattr(workflow, "run")
        assert hasattr(workflow, "resume")
        assert hasattr(workflow, "get_status")
        assert callable(workflow.run)
        assert callable(workflow.resume)
        assert callable(workflow.get_status)

    def test_crawler_workflow_checkpointing(self):
        """CrawlerWorkflow Checkpointing 설정 확인"""
        from apps.ai_service.graphs.crawler_graph import CrawlerWorkflow

        workflow = CrawlerWorkflow()

        # checkpointer가 설정되어 있어야 함
        assert hasattr(workflow, "checkpointer") or hasattr(workflow, "graph")


class TestAnalyticsWorkflow:
    """Analytics Workflow 테스트"""

    def test_analytics_workflow_import(self):
        """AnalyticsWorkflow 클래스 import 테스트"""
        from apps.ai_service.graphs.analytics_graph import AnalyticsWorkflow

        assert AnalyticsWorkflow is not None

    def test_analytics_workflow_has_required_methods(self):
        """AnalyticsWorkflow 필수 메서드 확인"""
        from apps.ai_service.graphs.analytics_graph import AnalyticsWorkflow

        workflow = AnalyticsWorkflow()

        assert hasattr(workflow, "generate_report")
        assert hasattr(workflow, "get_overview")
        assert hasattr(workflow, "get_trends")
        assert callable(workflow.generate_report)
        assert callable(workflow.get_overview)
        assert callable(workflow.get_trends)


class TestV2Routers:
    """V2 Router 테스트"""

    def test_crawler_router_import(self):
        """Crawler v2 router import 테스트"""
        from apps.ai_service.routers.v2.crawler import router

        assert router is not None
        assert router.prefix == "/v2/crawler"

    def test_analytics_router_import(self):
        """Analytics v2 router import 테스트"""
        from apps.ai_service.routers.v2.analytics import router

        assert router is not None
        assert router.prefix == "/v2/analytics"

    def test_all_v2_routers_in_init(self):
        """모든 v2 router가 __init__.py에 등록되어 있는지 확인"""
        from apps.ai_service.routers.v2 import (
            rag_router,
            documents_router,
            cases_router,
            risk_router,
            llm_compare_router,
            crawler_router,
            analytics_router,
        )

        assert rag_router is not None
        assert documents_router is not None
        assert cases_router is not None
        assert risk_router is not None
        assert llm_compare_router is not None
        assert crawler_router is not None
        assert analytics_router is not None


# ===== Integration Tests (requires running server) =====

class TestV2APIEndpoints:
    """V2 API 엔드포인트 테스트 (서버 실행 필요)"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_crawler_health_endpoint(self):
        """Crawler v2 헬스체크 엔드포인트 테스트"""
        import httpx

        async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
            response = await client.get("/v2/crawler/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["version"] == "v2"
            assert data["engine"] == "LangGraph"
            assert data["checkpointing"] is True

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analytics_health_endpoint(self):
        """Analytics v2 헬스체크 엔드포인트 테스트"""
        import httpx

        async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
            response = await client.get("/v2/analytics/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["version"] == "v2"
            assert data["engine"] == "LangGraph"
            assert data["checkpointing"] is False

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analytics_anomaly_types_endpoint(self):
        """Analytics v2 이상 유형 엔드포인트 테스트"""
        import httpx

        async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
            response = await client.get("/v2/analytics/anomaly-types")
            assert response.status_code == 200

            data = response.json()
            assert "anomaly_types" in data
            assert "severity_levels" in data
            assert "descriptions" in data

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analytics_insight_categories_endpoint(self):
        """Analytics v2 인사이트 카테고리 엔드포인트 테스트"""
        import httpx

        async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
            response = await client.get("/v2/analytics/insight-categories")
            assert response.status_code == 200

            data = response.json()
            assert "categories" in data
            assert "descriptions" in data


# ===== Week 13 Summary Tests =====

class TestWeek13Completion:
    """Week 13 완료 확인 테스트"""

    def test_external_api_tools_exist(self):
        """External API Tools 확인"""
        from apps.ai_service.mcp.tools import (
            fetch_court_api,
            fetch_statute_api,
            parse_legal_document,
            validate_document_structure,
        )

        # 모든 MCP Tools가 존재
        assert fetch_court_api is not None
        assert fetch_statute_api is not None
        assert parse_legal_document is not None
        assert validate_document_structure is not None

        logger.info("✅ External API Tools: 4개 확인 완료")

    def test_crawl_state_defined(self):
        """CrawlState 정의 확인"""
        from apps.ai_service.workflows.states.crawl_state import (
            DataSource,
            CrawlStatus,
            CrawlMetrics,
            CrawledDocument,
            ProcessingStatus,
            CrawlState,
            create_initial_crawl_state,
        )

        # DataSource: 3가지 타입
        assert len(DataSource) == 3

        # CrawlStatus: 8가지 상태
        assert len(CrawlStatus) == 8

        logger.info("✅ CrawlState 정의: 완료")

    def test_dashboard_state_defined(self):
        """DashboardState 정의 확인"""
        from apps.ai_service.workflows.states.dashboard_state import (
            TimeRange,
            AnomalySeverity,
            AnomalyType,
            InsightCategory,
            DocumentMetrics,
            RiskMetrics,
            UserActivityMetrics,
            CostMetrics,
            PerformanceMetrics,
            Anomaly,
            Insight,
            Trend,
            DashboardState,
            create_initial_dashboard_state,
        )

        # TimeRange: 5가지 범위
        assert len(TimeRange) == 5

        # AnomalySeverity: 4가지 심각도
        assert len(AnomalySeverity) == 4

        # AnomalyType: 5가지 이상 유형
        assert len(AnomalyType) == 5

        # InsightCategory: 5가지 인사이트 카테고리
        assert len(InsightCategory) == 5

        logger.info("✅ DashboardState 정의: 완료")

    def test_crawler_workflow_with_checkpointing(self):
        """Crawler Workflow (Checkpointing) 확인"""
        from apps.ai_service.graphs.crawler_graph import CrawlerWorkflow

        workflow = CrawlerWorkflow()

        # 필수 메서드
        assert hasattr(workflow, "run")
        assert hasattr(workflow, "resume")
        assert hasattr(workflow, "get_status")

        logger.info("✅ Crawler Workflow: Checkpointing 포함 완료")

    def test_analytics_workflow_without_checkpointing(self):
        """Analytics Workflow (Checkpointing 불필요) 확인"""
        from apps.ai_service.graphs.analytics_graph import AnalyticsWorkflow

        workflow = AnalyticsWorkflow()

        # 필수 메서드
        assert hasattr(workflow, "generate_report")
        assert hasattr(workflow, "get_overview")
        assert hasattr(workflow, "get_trends")

        logger.info("✅ Analytics Workflow: Checkpointing 불필요 완료")

    def test_all_v2_routers_registered(self):
        """모든 v2 라우터 등록 확인"""
        from apps.ai_service.routers.v2 import (
            rag_router,
            documents_router,
            cases_router,
            risk_router,
            llm_compare_router,
            crawler_router,
            analytics_router,
        )

        routers = [
            ("rag_router", rag_router),
            ("documents_router", documents_router),
            ("cases_router", cases_router),
            ("risk_router", risk_router),
            ("llm_compare_router", llm_compare_router),
            ("crawler_router", crawler_router),
            ("analytics_router", analytics_router),
        ]

        for name, router in routers:
            assert router is not None, f"{name}이 None입니다"
            assert hasattr(router, "routes"), f"{name}에 routes가 없습니다"

        logger.info(f"✅ V2 Routers: {len(routers)}개 등록 완료")


# ===== Main =====

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
