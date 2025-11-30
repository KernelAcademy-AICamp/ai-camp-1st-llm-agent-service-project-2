"""
V2 RAG API Tests

Phase 4 - Week 11: LangGraph 기반 RAG API 테스트

테스트 항목:
1. POST /v2/rag/chat - RAG 질의응답
2. GET /v2/rag/health - 헬스체크
3. POST /v2/rag/compare - v1 vs v2 비교
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json


# ===== Test Setup =====

@pytest.fixture
def mock_rag_workflow():
    """RAGWorkflow Mock"""
    mock = MagicMock()
    mock.arun = AsyncMock(return_value={
        "answer": "절도죄는 타인의 재물을 절취하는 범죄입니다.",
        "sources": [
            {
                "case_number": "2020도1234",
                "title": "절도죄 판례",
                "court": "대법원",
                "date": "2020-05-15",
                "relevance_score": 0.95
            }
        ],
        "confidence": 85.0,
        "revised": False,
        "processing_time": 1.5,
        "iteration_count": 1,
        "session_id": "test-session-123",
        "critique_log": None
    })
    mock.run = MagicMock(return_value={
        "answer": "절도죄는 타인의 재물을 절취하는 범죄입니다.",
        "sources": [],
        "confidence": 85.0,
        "revised": False,
        "processing_time": 1.5,
        "iteration_count": 1,
        "session_id": "test-session-123"
    })
    return mock


@pytest.fixture
def app_with_mocks(mock_rag_workflow):
    """Mock이 적용된 FastAPI 앱"""
    with patch("apps.ai_service.routers.v2.rag.RAGWorkflow", return_value=mock_rag_workflow):
        from apps.ai_service.routers.v2.rag import router
        app = FastAPI()
        app.include_router(router)
        yield app


@pytest.fixture
def client(app_with_mocks):
    """테스트 클라이언트"""
    return TestClient(app_with_mocks)


# ===== Health Check Tests =====

class TestHealthEndpoint:
    """GET /v2/rag/health 테스트"""

    def test_health_check_success(self, client, mock_rag_workflow):
        """헬스체크 성공"""
        response = client.get("/v2/rag/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "v2"
        assert data["engine"] == "LangGraph"
        assert "features" in data
        assert "conditional_routing" in data["features"]

    @patch("apps.ai_service.routers.v2.rag.RAGWorkflow")
    def test_health_check_failure(self, mock_workflow_class, client):
        """헬스체크 실패"""
        mock_workflow_class.side_effect = Exception("Initialization error")

        # 새로운 클라이언트로 재시도 (에러 상태)
        from apps.ai_service.routers.v2.rag import router
        app = FastAPI()
        app.include_router(router)
        error_client = TestClient(app)

        response = error_client.get("/v2/rag/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"


# ===== Chat Endpoint Tests =====

class TestChatEndpoint:
    """POST /v2/rag/chat 테스트"""

    def test_chat_success(self, client):
        """채팅 성공"""
        response = client.post(
            "/v2/rag/chat",
            json={
                "query": "절도죄란 무엇인가요?",
                "mode": "standard",
                "top_k": 5,
                "include_sources": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "confidence" in data
        assert data["version"] == "v2"

    def test_chat_with_all_modes(self, client):
        """모든 모드 테스트"""
        modes = ["concise", "standard", "detailed"]

        for mode in modes:
            response = client.post(
                "/v2/rag/chat",
                json={
                    "query": "테스트 질문",
                    "mode": mode
                }
            )
            assert response.status_code == 200
            assert response.json()["mode"] == mode

    def test_chat_empty_query(self, client):
        """빈 질문 테스트"""
        response = client.post(
            "/v2/rag/chat",
            json={
                "query": "",
                "mode": "standard"
            }
        )

        assert response.status_code == 422  # Validation error

    def test_chat_with_session_id(self, client):
        """세션 ID 포함 테스트"""
        response = client.post(
            "/v2/rag/chat",
            json={
                "query": "테스트",
                "session_id": "my-custom-session"
            }
        )

        assert response.status_code == 200

    def test_chat_with_critique_log(self, client):
        """Critique 로그 포함 테스트"""
        response = client.post(
            "/v2/rag/chat",
            json={
                "query": "테스트",
                "mode": "detailed",
                "include_critique_log": True
            }
        )

        assert response.status_code == 200

    def test_chat_top_k_validation(self, client):
        """top_k 범위 검증"""
        # 유효 범위: 1-10
        response = client.post(
            "/v2/rag/chat",
            json={
                "query": "테스트",
                "top_k": 15  # 범위 초과
            }
        )
        assert response.status_code == 422

        response = client.post(
            "/v2/rag/chat",
            json={
                "query": "테스트",
                "top_k": 0  # 범위 미만
            }
        )
        assert response.status_code == 422


# ===== Compare Endpoint Tests =====

class TestCompareEndpoint:
    """POST /v2/rag/compare 테스트"""

    def test_compare_endpoint(self, client):
        """v1 vs v2 비교 엔드포인트"""
        response = client.post(
            "/v2/rag/compare",
            json={
                "query": "절도죄란?",
                "mode": "standard"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "v2" in data
        assert "answer" in data["v2"]


# ===== Response Model Tests =====

class TestResponseModels:
    """응답 모델 검증 테스트"""

    def test_rag_v2_response_structure(self, client):
        """RAGv2Response 구조 검증"""
        response = client.post(
            "/v2/rag/chat",
            json={"query": "테스트"}
        )

        data = response.json()

        # 필수 필드 검증
        required_fields = [
            "answer", "sources", "query", "mode",
            "confidence", "revised", "processing_time",
            "iteration_count", "timestamp", "version"
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_source_structure(self, client):
        """Source 구조 검증"""
        response = client.post(
            "/v2/rag/chat",
            json={"query": "테스트", "include_sources": True}
        )

        data = response.json()

        if data["sources"]:
            source = data["sources"][0]
            source_fields = ["case_number", "title", "court", "date", "relevance_score"]
            for field in source_fields:
                assert field in source, f"Missing source field: {field}"


# ===== Error Handling Tests =====

class TestErrorHandling:
    """에러 처리 테스트"""

    @patch("apps.ai_service.routers.v2.rag.RAGWorkflow")
    def test_internal_error_handling(self, mock_workflow_class):
        """내부 에러 처리"""
        mock_instance = MagicMock()
        mock_instance.arun = AsyncMock(side_effect=Exception("Internal error"))
        mock_workflow_class.return_value = mock_instance

        from apps.ai_service.routers.v2.rag import router
        app = FastAPI()
        app.include_router(router)
        error_client = TestClient(app)

        response = error_client.post(
            "/v2/rag/chat",
            json={"query": "테스트"}
        )

        assert response.status_code == 500


# ===== Streaming Tests =====

class TestStreamingEndpoint:
    """스트리밍 응답 테스트"""

    def test_streaming_request(self, client):
        """스트리밍 요청 테스트"""
        # 스트리밍은 TestClient에서 직접 테스트하기 어려움
        # 기본 요청으로 stream=True 파라미터 검증
        response = client.post(
            "/v2/rag/chat",
            json={
                "query": "테스트",
                "stream": False  # 비스트리밍
            }
        )

        assert response.status_code == 200


# ===== Integration Tests =====

class TestIntegration:
    """통합 테스트"""

    def test_full_rag_flow(self, client):
        """전체 RAG 플로우 테스트"""
        # 1. 헬스체크
        health_response = client.get("/v2/rag/health")
        assert health_response.status_code == 200

        # 2. 질문 요청
        chat_response = client.post(
            "/v2/rag/chat",
            json={
                "query": "절도죄의 구성요건은?",
                "mode": "detailed",
                "top_k": 5,
                "include_sources": True,
                "include_critique_log": True
            }
        )
        assert chat_response.status_code == 200

        data = chat_response.json()
        assert len(data["answer"]) > 0
        assert data["version"] == "v2"

    def test_multiple_requests(self, client):
        """다중 요청 테스트"""
        queries = [
            "절도죄란?",
            "사기죄의 구성요건",
            "형법 제329조"
        ]

        for query in queries:
            response = client.post(
                "/v2/rag/chat",
                json={"query": query}
            )
            assert response.status_code == 200
