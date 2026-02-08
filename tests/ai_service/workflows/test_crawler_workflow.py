"""
Crawler Workflow Tests

Phase 4 - Week 13: LangGraph 기반 Crawler Workflow 단위 테스트

테스트 항목:
1. CrawlState 초기화
2. 개별 노드 함수
3. 라우팅 함수
4. 전체 워크플로우 실행
5. Checkpointing 동작
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime


# ===== State Tests =====

class TestCrawlState:
    """CrawlState 관련 테스트"""

    def test_create_initial_crawl_state(self):
        """초기 상태 생성 테스트"""
        from apps.ai_service.workflows.states.crawl_state import (
            create_initial_crawl_state,
            DataSource,
            CrawlStatus,
        )

        state = create_initial_crawl_state(
            crawl_job_id="test-job-123",
            source=DataSource.COURT_PRECEDENT,
            urls_to_crawl=["절도죄", "사기죄"],
        )

        assert state["crawl_job_id"] == "test-job-123"
        assert state["source"] == DataSource.COURT_PRECEDENT.value
        assert state["urls_to_crawl"] == ["절도죄", "사기죄"]
        assert state["source_url"] == "절도죄"
        assert state["status"] == CrawlStatus.PENDING.value
        assert state["retry_count"] == 0
        assert state["crawled_data"] == []
        assert state["failed_urls"] == []
        assert state["metrics"]["total_urls"] == 2

    def test_create_initial_crawl_state_empty_urls(self):
        """빈 URL 목록으로 상태 생성 테스트"""
        from apps.ai_service.workflows.states.crawl_state import (
            create_initial_crawl_state,
            DataSource,
        )

        state = create_initial_crawl_state(
            crawl_job_id="test-job-456",
            source=DataSource.STATUTE,
            urls_to_crawl=[],
        )

        assert state["source_url"] is None
        assert state["urls_to_crawl"] == []
        assert state["metrics"]["total_urls"] == 0

    def test_data_source_enum(self):
        """DataSource Enum 테스트"""
        from apps.ai_service.workflows.states.crawl_state import DataSource

        assert DataSource.COURT_PRECEDENT.value == "court_precedent"
        assert DataSource.STATUTE.value == "statute"
        assert DataSource.WEB.value == "web"

    def test_crawl_status_enum(self):
        """CrawlStatus Enum 테스트"""
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        assert CrawlStatus.PENDING.value == "pending"
        assert CrawlStatus.FETCHING.value == "fetching"
        assert CrawlStatus.COMPLETED.value == "completed"
        assert CrawlStatus.FAILED.value == "failed"
        assert CrawlStatus.RETRYING.value == "retrying"


# ===== Node Function Tests =====

class TestCrawlerNodes:
    """Crawler 노드 함수 테스트"""

    @pytest.fixture
    def sample_state(self):
        """테스트용 샘플 상태"""
        from apps.ai_service.workflows.states.crawl_state import (
            create_initial_crawl_state,
            DataSource,
        )

        return create_initial_crawl_state(
            crawl_job_id="test-job-001",
            source=DataSource.COURT_PRECEDENT,
            urls_to_crawl=["절도죄"],
        )

    @pytest.mark.asyncio
    @patch("apps.ai_service.graphs.crawler_graph.fetch_court_api")
    async def test_fetch_node_success(self, mock_fetch_api, sample_state):
        """fetch_node 성공 테스트"""
        from apps.ai_service.graphs.crawler_graph import fetch_node

        # Mock 설정
        mock_fetch_api.return_value = {
            "success": True,
            "precedents": [
                {
                    "case_number": "2020도1234",
                    "case_name": "절도 사건",
                    "court": "대법원",
                    "decision_date": "2020-05-15",
                    "content": "판례 내용..."
                }
            ],
            "total_count": 1
        }

        result = await fetch_node(sample_state)

        assert result["raw_content"] is not None
        assert "2020도1234" in result["raw_content"]
        assert "fetch" in result["completed_tasks"]
        assert result["error"] is None

    @pytest.mark.asyncio
    @patch("apps.ai_service.graphs.crawler_graph.fetch_court_api")
    async def test_fetch_node_failure(self, mock_fetch_api, sample_state):
        """fetch_node 실패 테스트"""
        from apps.ai_service.graphs.crawler_graph import fetch_node
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        mock_fetch_api.return_value = {
            "success": False,
            "error": "API connection failed",
            "precedents": [],
            "total_count": 0
        }

        result = await fetch_node(sample_state)

        assert result["status"] == CrawlStatus.FAILED.value
        assert result["error"] is not None

    @pytest.mark.asyncio
    @patch("apps.ai_service.graphs.crawler_graph.parse_legal_document")
    async def test_parse_node_success(self, mock_parse):
        """parse_node 성공 테스트"""
        from apps.ai_service.graphs.crawler_graph import parse_node
        from apps.ai_service.workflows.states.crawl_state import DataSource

        mock_parse.return_value = {
            "success": True,
            "title": "2020도1234 판례",
            "doc_type": "precedent",
            "sections": [
                {"name": "판시사항", "content": "내용...", "order": 0}
            ],
            "metadata": {}
        }

        state = {
            "crawl_job_id": "test",
            "source": DataSource.COURT_PRECEDENT.value,
            "source_url": "절도죄",
            "raw_content": "판례 원본 내용...",
            "completed_tasks": ["fetch"],
        }

        result = await parse_node(state)

        assert result["parsed_data"] is not None
        assert result["parsed_data"]["title"] == "2020도1234 판례"
        assert "parse" in result["completed_tasks"]

    @pytest.mark.asyncio
    async def test_parse_node_no_content(self):
        """parse_node 콘텐츠 없음 테스트"""
        from apps.ai_service.graphs.crawler_graph import parse_node
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        state = {
            "crawl_job_id": "test",
            "source": "court_precedent",
            "source_url": "테스트",
            "raw_content": None,
            "completed_tasks": [],
        }

        result = await parse_node(state)

        assert result["status"] == CrawlStatus.FAILED.value
        assert "No raw content" in result["error"]

    @pytest.mark.asyncio
    @patch("apps.ai_service.graphs.crawler_graph.validate_document_structure")
    async def test_validate_node_success(self, mock_validate):
        """validate_node 성공 테스트"""
        from apps.ai_service.graphs.crawler_graph import validate_node
        from apps.ai_service.workflows.states.crawl_state import DataSource

        mock_validate.return_value = {
            "valid": True,
            "missing_fields": [],
            "warnings": [],
            "metadata": {}
        }

        state = {
            "crawl_job_id": "test",
            "source": DataSource.COURT_PRECEDENT.value,
            "source_url": "절도죄",
            "parsed_data": {
                "title": "테스트 판례",
                "sections": [{"content": "내용", "name": "판시사항", "order": 0}]
            },
            "completed_tasks": ["fetch", "parse"],
        }

        result = await validate_node(state)

        assert result["validation_result"] is not None
        assert result["validation_result"]["valid"] is True
        assert result["quality_check"]["is_valid"] is True
        assert "validate" in result["completed_tasks"]

    @pytest.mark.asyncio
    async def test_store_node_success(self):
        """store_node 성공 테스트"""
        from apps.ai_service.graphs.crawler_graph import store_node
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        state = {
            "crawl_job_id": "test",
            "source_url": "절도죄",
            "raw_content": "원본 내용",
            "parsed_data": {"title": "테스트"},
            "validation_result": {"valid": True},
            "crawled_data": [],
            "completed_tasks": ["fetch", "parse", "validate"],
            "metrics": {
                "total_urls": 1,
                "processed_urls": 0,
                "successful_urls": 0,
                "failed_urls": 0,
                "start_time": datetime.utcnow().isoformat(),
                "end_time": None,
            }
        }

        result = await store_node(state)

        assert len(result["crawled_data"]) == 1
        assert result["crawled_data"][0]["stored"] is True
        assert result["status"] == CrawlStatus.COMPLETED.value
        assert result["metrics"]["successful_urls"] == 1
        assert "store" in result["completed_tasks"]

    @pytest.mark.asyncio
    async def test_retry_node_under_limit(self):
        """retry_node 재시도 가능 테스트"""
        from apps.ai_service.graphs.crawler_graph import retry_node
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        state = {
            "crawl_job_id": "test",
            "source_url": "절도죄",
            "retry_count": 1,
            "failed_urls": [],
            "needs_retry": [],
            "metrics": {"total_urls": 1, "failed_urls": 0, "start_time": None},
        }

        result = await retry_node(state)

        assert result["retry_count"] == 2
        assert result["status"] == CrawlStatus.RETRYING.value
        assert result["raw_content"] is None  # 이전 결과 초기화

    @pytest.mark.asyncio
    async def test_retry_node_max_exceeded(self):
        """retry_node 최대 재시도 초과 테스트"""
        from apps.ai_service.graphs.crawler_graph import retry_node
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        state = {
            "crawl_job_id": "test",
            "source_url": "절도죄",
            "retry_count": 3,  # MAX_RETRY_COUNT = 3
            "failed_urls": [],
            "needs_retry": [],
            "metrics": {"total_urls": 1, "failed_urls": 0, "start_time": None},
        }

        result = await retry_node(state)

        assert result["retry_count"] == 4
        assert result["status"] == CrawlStatus.FAILED.value
        assert "절도죄" in result["failed_urls"]


# ===== Routing Tests =====

class TestRouting:
    """라우팅 함수 테스트"""

    def test_route_after_fetch_success(self):
        """fetch 성공 후 parse로 라우팅"""
        from apps.ai_service.graphs.crawler_graph import route_after_fetch
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        state = {
            "status": CrawlStatus.FETCHING.value,
            "raw_content": "판례 내용..."
        }

        result = route_after_fetch(state)
        assert result == "parse"

    def test_route_after_fetch_failure(self):
        """fetch 실패 후 retry로 라우팅"""
        from apps.ai_service.graphs.crawler_graph import route_after_fetch
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        state = {
            "status": CrawlStatus.FAILED.value,
            "raw_content": None
        }

        result = route_after_fetch(state)
        assert result == "retry"

    def test_route_after_parse_success(self):
        """parse 성공 후 validate로 라우팅"""
        from apps.ai_service.graphs.crawler_graph import route_after_parse
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        state = {
            "status": CrawlStatus.PARSING.value,
            "parsed_data": {"title": "테스트"}
        }

        result = route_after_parse(state)
        assert result == "validate"

    def test_route_after_parse_failure(self):
        """parse 실패 후 retry로 라우팅"""
        from apps.ai_service.graphs.crawler_graph import route_after_parse
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        state = {
            "status": CrawlStatus.FAILED.value,
            "parsed_data": None
        }

        result = route_after_parse(state)
        assert result == "retry"

    def test_route_after_validate_success(self):
        """validate 성공 후 store로 라우팅"""
        from apps.ai_service.graphs.crawler_graph import route_after_validate
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        state = {
            "status": CrawlStatus.VALIDATING.value,
            "validation_result": {"valid": True},
            "quality_check": {"is_valid": True}
        }

        result = route_after_validate(state)
        assert result == "store"

    def test_route_after_retry_continue(self):
        """retry 후 fetch로 계속"""
        from apps.ai_service.graphs.crawler_graph import route_after_retry
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        state = {
            "retry_count": 1,
            "status": CrawlStatus.RETRYING.value
        }

        result = route_after_retry(state)
        assert result == "fetch"

    def test_route_after_retry_end(self):
        """retry 최대 횟수 후 종료"""
        from apps.ai_service.graphs.crawler_graph import route_after_retry
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        state = {
            "retry_count": 3,
            "status": CrawlStatus.FAILED.value
        }

        result = route_after_retry(state)
        assert result == "end"


# ===== Workflow Integration Tests =====

class TestCrawlerWorkflowIntegration:
    """Crawler Workflow 통합 테스트"""

    def test_workflow_graph_creation(self):
        """워크플로우 그래프 생성 테스트"""
        from apps.ai_service.graphs.crawler_graph import create_crawler_workflow

        graph = create_crawler_workflow()

        assert graph is not None

    def test_workflow_with_checkpointing(self):
        """Checkpointing 포함 워크플로우 생성"""
        from apps.ai_service.graphs.crawler_graph import create_crawler_workflow
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        graph = create_crawler_workflow(checkpointer=checkpointer)

        assert graph is not None

    @pytest.mark.asyncio
    @patch("apps.ai_service.graphs.crawler_graph.fetch_court_api")
    @patch("apps.ai_service.graphs.crawler_graph.parse_legal_document")
    @patch("apps.ai_service.graphs.crawler_graph.validate_document_structure")
    async def test_workflow_run(self, mock_validate, mock_parse, mock_fetch):
        """워크플로우 실행 테스트"""
        from apps.ai_service.graphs.crawler_graph import CrawlerWorkflow
        from apps.ai_service.workflows.states.crawl_state import DataSource, CrawlStatus

        # Mock 설정
        mock_fetch.return_value = {
            "success": True,
            "precedents": [
                {"case_number": "2020도1234", "content": "판례 내용", "case_name": "", "court": "", "decision_date": ""}
            ],
            "total_count": 1
        }

        mock_parse.return_value = {
            "success": True,
            "title": "테스트 판례",
            "sections": [],
            "metadata": {}
        }

        mock_validate.return_value = {
            "valid": True,
            "missing_fields": [],
            "warnings": [],
            "metadata": {}
        }

        workflow = CrawlerWorkflow()
        result = await workflow.run(
            source=DataSource.COURT_PRECEDENT,
            urls=["절도죄"],
        )

        assert "crawl_job_id" in result
        assert "thread_id" in result
        assert "status" in result
        assert "crawled_data" in result
        assert "metrics" in result

    @pytest.mark.asyncio
    async def test_workflow_get_status(self):
        """워크플로우 상태 조회 테스트"""
        from apps.ai_service.graphs.crawler_graph import CrawlerWorkflow

        workflow = CrawlerWorkflow()
        status = await workflow.get_status("non-existent-thread")

        assert status["status"] == "not_found"


# ===== v2 API Router Tests =====

class TestCrawlerV2Router:
    """Crawler v2 API 라우터 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI

        app = FastAPI()
        from apps.ai_service.routers.v2.crawler import router
        app.include_router(router)

        return TestClient(app)

    def test_health_endpoint(self, client):
        """헬스체크 엔드포인트 테스트"""
        response = client.get("/v2/crawler/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "v2"
        assert data["checkpointing"] is True
        assert "court_precedent" in data["supported_sources"]

    @patch("apps.ai_service.routers.v2.crawler.CrawlerWorkflow")
    def test_start_endpoint(self, mock_workflow_class, client):
        """크롤링 시작 엔드포인트 테스트"""
        from apps.ai_service.workflows.states.crawl_state import CrawlStatus

        mock_workflow = MagicMock()
        mock_workflow.run = AsyncMock(return_value={
            "crawl_job_id": "test-123",
            "thread_id": "crawler-test-123",
            "status": CrawlStatus.COMPLETED.value,
            "crawled_data": [],
            "metrics": {
                "total_urls": 1,
                "successful_urls": 1,
                "failed_urls": 0,
            },
            "errors": None
        })
        mock_workflow_class.return_value = mock_workflow

        response = client.post(
            "/v2/crawler/start",
            json={
                "source": "court_precedent",
                "keywords": ["절도죄"],
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["version"] == "v2"

    def test_start_endpoint_invalid_source(self, client):
        """잘못된 소스로 시작 요청 테스트"""
        response = client.post(
            "/v2/crawler/start",
            json={
                "source": "invalid_source",
                "keywords": ["테스트"],
            }
        )

        assert response.status_code == 400


# ===== Export Tests =====

class TestExports:
    """모듈 export 테스트"""

    def test_graphs_exports(self):
        """graphs 모듈 export 테스트"""
        from apps.ai_service.graphs import (
            CrawlerWorkflow,
            create_crawler_workflow,
            fetch_node,
            parse_node,
            validate_node,
            store_node,
            retry_node,
        )

        assert CrawlerWorkflow is not None
        assert create_crawler_workflow is not None
        assert fetch_node is not None
        assert parse_node is not None
        assert validate_node is not None
        assert store_node is not None
        assert retry_node is not None

    def test_states_exports(self):
        """states 모듈 export 테스트"""
        from apps.ai_service.workflows.states import (
            CrawlState,
            CrawlStatus,
            DataSource,
            CrawlMetrics,
            CrawledDocument,
            ProcessingStatus,
            QualityCheck,
            create_initial_crawl_state,
        )

        assert CrawlState is not None
        assert CrawlStatus is not None
        assert DataSource is not None
        assert create_initial_crawl_state is not None

    def test_router_exports(self):
        """router 모듈 export 테스트"""
        from apps.ai_service.routers.v2 import crawler_router

        assert crawler_router is not None
