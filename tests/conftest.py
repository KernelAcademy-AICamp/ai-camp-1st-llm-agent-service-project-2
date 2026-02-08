"""
Pytest Configuration and Fixtures

Phase 4 - Week 11: 테스트 공통 설정
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "apps" / "ai_service"))


# ===== Mock Fixtures =====

@pytest.fixture
def mock_llm_client():
    """LLM 클라이언트 Mock"""
    mock = MagicMock()
    mock.chat.return_value = "테스트 응답입니다. [판례: 2020도1234] 절도죄는 타인의 재물을 절취하는 행위입니다."
    return mock


@pytest.fixture
def mock_retriever():
    """Retriever Mock"""
    mock = MagicMock()
    mock.retrieve.return_value = [
        {
            "content": "절도죄는 형법 제329조에 규정된 범죄로...",
            "metadata": {
                "case_number": "2020도1234",
                "title": "절도죄 판례",
                "court": "대법원",
                "date": "2020-05-15"
            },
            "score": 0.95
        },
        {
            "content": "형법 제329조 절도죄 조문 내용...",
            "metadata": {
                "case_number": "2019도5678",
                "title": "절도죄 관련 판례",
                "court": "서울고등법원",
                "date": "2019-03-20"
            },
            "score": 0.88
        }
    ]
    mock.format_context.return_value = "검색된 판례 컨텍스트..."
    return mock


@pytest.fixture
def mock_vectordb():
    """VectorDB Mock"""
    mock = MagicMock()
    mock.search.return_value = []
    return mock


@pytest.fixture
def mock_embedder():
    """Embedder Mock"""
    mock = MagicMock()
    mock.embed.return_value = [0.1] * 768
    return mock


@pytest.fixture
def sample_rag_state():
    """샘플 RAG 상태"""
    return {
        "query": "절도죄란 무엇인가요?",
        "mode": "standard",
        "top_k": 5,
        "include_critique_log": False,
        "documents": [],
        "context": "",
        "initial_answer": "",
        "confidence_score": 0.0,
        "needs_refinement": False,
        "critique": None,
        "revised": False,
        "final_answer": "",
        "sources": [],
        "summarized": False,
        "session_id": "test-session-123",
        "user_id": None,
        "iteration_count": 0,
        "max_iterations": 3,
        "processing_time": 0.0,
        "error": None,
        "metadata": {}
    }


@pytest.fixture
def sample_documents():
    """샘플 검색 문서"""
    return [
        {
            "content": "절도죄는 형법 제329조에 규정된 범죄입니다.",
            "metadata": {
                "case_number": "2020도1234",
                "title": "절도죄 판례",
                "court": "대법원",
                "date": "2020-05-15"
            },
            "score": 0.95
        },
        {
            "content": "타인의 재물을 절취하는 행위를 처벌합니다.",
            "metadata": {
                "case_number": "2019도5678",
                "title": "절도 관련",
                "court": "서울고등법원",
                "date": "2019-03-20"
            },
            "score": 0.88
        },
        {
            "content": "절취의 의미와 범위에 대한 판시...",
            "metadata": {
                "case_number": "2018도9999",
                "title": "절취 정의",
                "court": "대법원",
                "date": "2018-11-10"
            },
            "score": 0.82
        }
    ]


# ===== Test Client Fixtures =====

@pytest.fixture
def test_client():
    """FastAPI 테스트 클라이언트"""
    from fastapi.testclient import TestClient

    # Mock dependencies before importing app
    with patch("apps.ai_service.workflows.nodes.rag_nodes.LegalDocumentRetriever"), \
         patch("apps.ai_service.workflows.nodes.rag_nodes.QdrantVectorDB"), \
         patch("apps.ai_service.workflows.nodes.rag_nodes.RemoteEmbedder"), \
         patch("apps.ai_service.workflows.nodes.rag_nodes.create_llm_client"):

        from apps.ai_service.main import app
        client = TestClient(app)
        yield client


@pytest.fixture
def async_test_client():
    """비동기 테스트 클라이언트"""
    import httpx
    from apps.ai_service.main import app

    return httpx.AsyncClient(app=app, base_url="http://test")
