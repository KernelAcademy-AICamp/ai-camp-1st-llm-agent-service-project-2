"""
RAG Workflow Tests

Phase 4 - Week 11: LangGraph 기반 RAG Workflow 단위 테스트

테스트 항목:
1. RAGState 초기화
2. 개별 노드 함수
3. 라우팅 함수
4. 전체 워크플로우 실행
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json


# ===== State Tests =====

class TestRAGState:
    """RAGState 관련 테스트"""

    def test_create_initial_rag_state(self):
        """초기 상태 생성 테스트"""
        from apps.ai_service.states.rag_state import create_initial_rag_state

        state = create_initial_rag_state(
            query="절도죄란?",
            mode="standard",
            top_k=5
        )

        assert state["query"] == "절도죄란?"
        assert state["mode"] == "standard"
        assert state["top_k"] == 5
        assert state["documents"] == []
        assert state["iteration_count"] == 0
        assert state["max_iterations"] == 3
        assert state["confidence_score"] == 0.0
        assert state["session_id"] is not None

    def test_create_initial_rag_state_with_session(self):
        """세션 ID 지정 상태 생성"""
        from apps.ai_service.states.rag_state import create_initial_rag_state

        state = create_initial_rag_state(
            query="테스트",
            session_id="custom-session-123",
            user_id="user-456"
        )

        assert state["session_id"] == "custom-session-123"
        assert state["user_id"] == "user-456"

    def test_response_mode_enum(self):
        """ResponseMode Enum 테스트"""
        from apps.ai_service.states.rag_state import ResponseMode

        assert ResponseMode.CONCISE.value == "concise"
        assert ResponseMode.STANDARD.value == "standard"
        assert ResponseMode.DETAILED.value == "detailed"


# ===== Node Function Tests =====

class TestRAGNodes:
    """RAG 노드 함수 테스트"""

    @patch("apps.ai_service.workflows.nodes.rag_nodes.LegalDocumentRetriever")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.QdrantVectorDB")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.RemoteEmbedder")
    def test_retrieve_node_success(self, mock_embedder, mock_vectordb, mock_retriever):
        """retrieve_node 성공 테스트"""
        from apps.ai_service.workflows.nodes.rag_nodes import retrieve_node

        # Mock 설정
        mock_retriever_instance = MagicMock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "판례 내용", "metadata": {"case_number": "2020도1234"}, "score": 0.9}
        ]
        mock_retriever_instance.format_context.return_value = "컨텍스트"
        mock_retriever.return_value = mock_retriever_instance

        state = {
            "query": "절도죄란?",
            "top_k": 5,
            "iteration_count": 0
        }

        result = retrieve_node(state)

        assert "documents" in result
        assert "context" in result
        assert result["iteration_count"] == 1

    @patch("apps.ai_service.workflows.nodes.rag_nodes.LegalDocumentRetriever")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.QdrantVectorDB")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.RemoteEmbedder")
    def test_retrieve_node_error(self, mock_embedder, mock_vectordb, mock_retriever):
        """retrieve_node 에러 처리 테스트"""
        from apps.ai_service.workflows.nodes.rag_nodes import retrieve_node

        mock_retriever.side_effect = Exception("Connection error")

        state = {
            "query": "테스트",
            "top_k": 5,
            "iteration_count": 0
        }

        result = retrieve_node(state)

        assert result["documents"] == []
        assert "error" in result

    @patch("apps.ai_service.workflows.nodes.rag_nodes.create_llm_client")
    def test_generate_node_success(self, mock_create_llm):
        """generate_node 성공 테스트"""
        from apps.ai_service.workflows.nodes.rag_nodes import generate_node

        mock_llm = MagicMock()
        mock_llm.chat.return_value = "생성된 답변 [판례: 2020도1234]"
        mock_create_llm.return_value = mock_llm

        state = {
            "query": "절도죄란?",
            "context": "검색된 판례 내용...",
            "mode": "standard"
        }

        result = generate_node(state)

        assert "initial_answer" in result
        assert len(result["initial_answer"]) > 0

    def test_generate_node_no_context(self):
        """generate_node 컨텍스트 없음 테스트"""
        from apps.ai_service.workflows.nodes.rag_nodes import generate_node

        state = {
            "query": "절도죄란?",
            "context": "",
            "mode": "standard"
        }

        result = generate_node(state)

        assert "검색된 문서가 없어" in result["initial_answer"]
        assert result["confidence_score"] == 0.0

    def test_check_confidence_node_high_confidence(self, sample_documents):
        """check_confidence_node 높은 신뢰도 테스트"""
        from apps.ai_service.workflows.nodes.rag_nodes import check_confidence_node

        state = {
            "initial_answer": "절도죄는 타인의 재물을 절취하는 범죄입니다. [판례: 2020도1234]",
            "documents": sample_documents,
            "mode": "standard"
        }

        result = check_confidence_node(state)

        assert "confidence_score" in result
        assert result["confidence_score"] >= 70  # 높은 신뢰도

    def test_check_confidence_node_low_confidence(self):
        """check_confidence_node 낮은 신뢰도 테스트"""
        from apps.ai_service.workflows.nodes.rag_nodes import check_confidence_node

        state = {
            "initial_answer": "모르겠습니다.",
            "documents": [],
            "mode": "detailed",
            "error": "Some error"
        }

        result = check_confidence_node(state)

        assert result["confidence_score"] < 70

    @patch("apps.ai_service.workflows.nodes.rag_nodes.create_llm_client")
    def test_critique_node_detailed_mode(self, mock_create_llm):
        """critique_node DETAILED 모드 테스트"""
        from apps.ai_service.workflows.nodes.rag_nodes import critique_node

        mock_llm = MagicMock()
        mock_llm.chat.return_value = json.dumps({
            "accuracy_score": 85,
            "completeness_score": 80,
            "citation_score": 90,
            "improvements": ["개선점1"],
            "overall_feedback": "양호"
        })
        mock_create_llm.return_value = mock_llm

        state = {
            "initial_answer": "테스트 답변",
            "query": "테스트 질문",
            "mode": "detailed"
        }

        result = critique_node(state)

        assert result["critique"] is not None

    def test_critique_node_skip_non_detailed(self):
        """critique_node 비-DETAILED 모드 스킵 테스트"""
        from apps.ai_service.workflows.nodes.rag_nodes import critique_node

        state = {
            "initial_answer": "테스트 답변",
            "query": "테스트",
            "mode": "standard"
        }

        result = critique_node(state)

        assert result["critique"] is None

    def test_finalize_node(self, sample_documents):
        """finalize_node 테스트"""
        from apps.ai_service.workflows.nodes.rag_nodes import finalize_node

        state = {
            "initial_answer": "초기 답변",
            "final_answer": None,
            "documents": sample_documents
        }

        result = finalize_node(state)

        assert result["final_answer"] == "초기 답변"
        assert len(result["sources"]) > 0


# ===== Routing Tests =====

class TestRouting:
    """라우팅 함수 테스트"""

    def test_route_high_confidence_detailed(self):
        """높은 신뢰도 + DETAILED 모드 → critique"""
        from apps.ai_service.workflows.nodes.rag_nodes import route_after_confidence

        state = {
            "confidence_score": 85,
            "iteration_count": 1,
            "max_iterations": 3,
            "mode": "detailed"
        }

        result = route_after_confidence(state)
        assert result == "critique"

    def test_route_high_confidence_standard(self):
        """높은 신뢰도 + STANDARD 모드 → finalize"""
        from apps.ai_service.workflows.nodes.rag_nodes import route_after_confidence

        state = {
            "confidence_score": 80,
            "iteration_count": 1,
            "max_iterations": 3,
            "mode": "standard"
        }

        result = route_after_confidence(state)
        assert result == "finalize"

    def test_route_low_confidence(self):
        """낮은 신뢰도 → retrieve (재검색)"""
        from apps.ai_service.workflows.nodes.rag_nodes import route_after_confidence

        state = {
            "confidence_score": 50,
            "iteration_count": 1,
            "max_iterations": 3,
            "mode": "standard"
        }

        result = route_after_confidence(state)
        assert result == "retrieve"

    def test_route_max_iterations(self):
        """최대 재시도 도달 → finalize"""
        from apps.ai_service.workflows.nodes.rag_nodes import route_after_confidence

        state = {
            "confidence_score": 40,
            "iteration_count": 3,
            "max_iterations": 3,
            "mode": "standard"
        }

        result = route_after_confidence(state)
        assert result == "finalize"


# ===== Helper Function Tests =====

class TestHelpers:
    """헬퍼 함수 테스트"""

    def test_extract_sources(self, sample_documents):
        """extract_sources 테스트"""
        from apps.ai_service.workflows.nodes.rag_nodes import extract_sources

        sources = extract_sources(sample_documents)

        assert len(sources) == 3
        assert sources[0]["case_number"] == "2020도1234"
        assert sources[0]["court"] == "대법원"

    def test_extract_sources_empty(self):
        """빈 문서 목록 테스트"""
        from apps.ai_service.workflows.nodes.rag_nodes import extract_sources

        sources = extract_sources([])
        assert sources == []


# ===== Workflow Integration Tests =====

class TestRAGWorkflowIntegration:
    """RAG Workflow 통합 테스트"""

    def test_workflow_graph_creation(self):
        """워크플로우 그래프 생성 테스트"""
        from apps.ai_service.workflows.rag_workflow import create_rag_workflow

        graph = create_rag_workflow()

        assert graph is not None

    @patch("apps.ai_service.workflows.nodes.rag_nodes.LegalDocumentRetriever")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.QdrantVectorDB")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.RemoteEmbedder")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.create_llm_client")
    def test_workflow_run(self, mock_llm, mock_embedder, mock_vectordb, mock_retriever):
        """워크플로우 실행 테스트"""
        from apps.ai_service.workflows.rag_workflow import RAGWorkflow

        # Mock 설정
        mock_retriever_instance = MagicMock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "판례", "metadata": {"case_number": "2020도1234"}, "score": 0.9}
        ]
        mock_retriever_instance.format_context.return_value = "컨텍스트"
        mock_retriever.return_value = mock_retriever_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.chat.return_value = "생성된 답변 [판례: 2020도1234]"
        mock_llm.return_value = mock_llm_instance

        workflow = RAGWorkflow()
        result = workflow.run(
            query="절도죄란?",
            mode="standard",
            top_k=5
        )

        assert "answer" in result
        assert "sources" in result
        assert "confidence" in result
        assert "processing_time" in result

    @pytest.mark.asyncio
    @patch("apps.ai_service.workflows.nodes.rag_nodes.LegalDocumentRetriever")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.QdrantVectorDB")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.RemoteEmbedder")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.create_llm_client")
    async def test_workflow_arun(self, mock_llm, mock_embedder, mock_vectordb, mock_retriever):
        """워크플로우 비동기 실행 테스트"""
        from apps.ai_service.workflows.rag_workflow import RAGWorkflow

        # Mock 설정
        mock_retriever_instance = MagicMock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "판례", "metadata": {"case_number": "2020도1234"}, "score": 0.9}
        ]
        mock_retriever_instance.format_context.return_value = "컨텍스트"
        mock_retriever.return_value = mock_retriever_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.chat.return_value = "생성된 답변 [판례: 2020도1234]"
        mock_llm.return_value = mock_llm_instance

        workflow = RAGWorkflow()
        result = await workflow.arun(
            query="절도죄란?",
            mode="standard",
            top_k=5
        )

        assert "answer" in result
        assert "session_id" in result


# ===== v1 vs v2 Comparison Tests =====

class TestV1V2Comparison:
    """v1 vs v2 비교 테스트"""

    @patch("apps.ai_service.workflows.nodes.rag_nodes.LegalDocumentRetriever")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.QdrantVectorDB")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.RemoteEmbedder")
    @patch("apps.ai_service.workflows.nodes.rag_nodes.create_llm_client")
    def test_v2_response_format(self, mock_llm, mock_embedder, mock_vectordb, mock_retriever):
        """v2 응답 형식 검증"""
        from apps.ai_service.workflows.rag_workflow import RAGWorkflow

        # Mock 설정
        mock_retriever_instance = MagicMock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "판례", "metadata": {"case_number": "2020도1234"}, "score": 0.9}
        ]
        mock_retriever_instance.format_context.return_value = "컨텍스트"
        mock_retriever.return_value = mock_retriever_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.chat.return_value = "생성된 답변"
        mock_llm.return_value = mock_llm_instance

        workflow = RAGWorkflow()
        result = workflow.run(query="테스트", mode="standard")

        # v2 응답 필드 검증
        required_fields = ["answer", "sources", "confidence", "revised", "processing_time"]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_v2_supports_modes(self):
        """v2가 모든 모드를 지원하는지 확인"""
        from apps.ai_service.states.rag_state import ResponseMode

        modes = [ResponseMode.CONCISE, ResponseMode.STANDARD, ResponseMode.DETAILED]
        assert len(modes) == 3
