"""
WorkflowExecutor Tests

Phase 4.5: Agent Hub - WorkflowExecutor 단위 테스트

테스트 항목:
1. WorkflowInput/WorkflowOutput 데이터 클래스
2. 워크플로우별 파라미터 매핑 (_map_input_params)
3. 결과 정규화 (_normalize_output)
4. 워크플로우 동적 로딩 및 캐싱
5. execute_with_input 통합 테스트
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import asdict


# =============================================================================
# WorkflowInput/WorkflowOutput 테스트
# =============================================================================

class TestWorkflowInput:
    """WorkflowInput 데이터 클래스 테스트"""

    def test_create_minimal_input(self):
        """최소 필수 파라미터로 생성"""
        from apps.ai_service.agents.workflow_executor import WorkflowInput

        workflow_input = WorkflowInput(query="절도죄란?")

        assert workflow_input.query == "절도죄란?"
        assert workflow_input.mode == "standard"
        assert workflow_input.top_k == 5
        assert workflow_input.session_id is None
        assert workflow_input.user_id is None
        assert workflow_input.content is None
        assert workflow_input.doc_type is None
        assert workflow_input.extra == {}

    def test_create_full_input(self):
        """모든 파라미터로 생성"""
        from apps.ai_service.agents.workflow_executor import WorkflowInput

        workflow_input = WorkflowInput(
            query="계약서 분석해줘",
            mode="detailed",
            top_k=10,
            session_id="session-123",
            user_id="user-456",
            content="계약서 내용...",
            doc_type="CONTRACT",
            extra={"include_critique_log": True, "custom_param": "value"}
        )

        assert workflow_input.query == "계약서 분석해줘"
        assert workflow_input.mode == "detailed"
        assert workflow_input.top_k == 10
        assert workflow_input.session_id == "session-123"
        assert workflow_input.user_id == "user-456"
        assert workflow_input.content == "계약서 내용..."
        assert workflow_input.doc_type == "CONTRACT"
        assert workflow_input.extra["include_critique_log"] is True
        assert workflow_input.extra["custom_param"] == "value"


class TestWorkflowOutput:
    """WorkflowOutput 데이터 클래스 테스트"""

    def test_create_success_output(self):
        """성공 출력 생성"""
        from apps.ai_service.agents.workflow_executor import WorkflowOutput

        output = WorkflowOutput(
            success=True,
            answer="절도죄는 타인의 재물을 절취하는 범죄입니다.",
            sources=[{"case_number": "2020도1234"}],
            confidence=0.95,
            metadata={"revised": False, "iteration_count": 1},
            processing_time=2.5
        )

        assert output.success is True
        assert output.answer == "절도죄는 타인의 재물을 절취하는 범죄입니다."
        assert len(output.sources) == 1
        assert output.confidence == 0.95
        assert output.error is None
        assert output.processing_time == 2.5

    def test_create_error_output(self):
        """에러 출력 생성"""
        from apps.ai_service.agents.workflow_executor import WorkflowOutput

        output = WorkflowOutput(
            success=False,
            answer="워크플로우 실행 중 오류가 발생했습니다.",
            sources=[],
            confidence=0.0,
            metadata={},
            error="Connection timeout",
            processing_time=30.0
        )

        assert output.success is False
        assert output.error == "Connection timeout"
        assert output.confidence == 0.0


# =============================================================================
# 파라미터 매핑 테스트
# =============================================================================

class TestParamMapping:
    """워크플로우별 파라미터 매핑 테스트"""

    def test_rag_workflow_param_mapping(self):
        """RAG 워크플로우 파라미터 매핑"""
        from apps.ai_service.agents.workflow_executor import (
            WorkflowExecutor,
            WorkflowInput
        )

        executor = WorkflowExecutor()
        workflow_input = WorkflowInput(
            query="형법이란?",
            mode="detailed",
            top_k=10,
            session_id="session-123",
            user_id="user-456",
            extra={"include_critique_log": True}
        )

        params = executor._map_input_params("rag_workflow", workflow_input)

        assert params["query"] == "형법이란?"
        assert params["mode"] == "detailed"
        assert params["top_k"] == 10
        assert params["session_id"] == "session-123"
        assert params["user_id"] == "user-456"
        assert params["include_critique_log"] is True

    def test_document_workflow_param_mapping(self):
        """문서 분석 워크플로우 파라미터 매핑"""
        from apps.ai_service.agents.workflow_executor import (
            WorkflowExecutor,
            WorkflowInput
        )

        executor = WorkflowExecutor()
        workflow_input = WorkflowInput(
            query="계약서 분석해줘",
            content="계약서 내용...",
            doc_type="CONTRACT",
            extra={"file_path": "/path/to/doc.pdf", "document_id": "doc-123"}
        )

        params = executor._map_input_params("document_workflow", workflow_input)

        assert params["text"] == "계약서 내용..."
        assert params["doc_type"] == "CONTRACT"
        assert params["file_path"] == "/path/to/doc.pdf"
        assert params["document_id"] == "doc-123"

    def test_case_workflow_param_mapping(self):
        """사건 분석 워크플로우 파라미터 매핑"""
        from apps.ai_service.agents.workflow_executor import (
            WorkflowExecutor,
            WorkflowInput
        )

        executor = WorkflowExecutor()
        workflow_input = WorkflowInput(
            query="사건 분석",
            content="사건 내용...",
            extra={"case_type": "criminal"}
        )

        params = executor._map_input_params("case_workflow", workflow_input)

        assert params["case_content"] == "사건 내용..."
        assert params["case_type"] == "criminal"

    def test_risk_workflow_param_mapping(self):
        """리스크 분석 워크플로우 파라미터 매핑"""
        from apps.ai_service.agents.workflow_executor import (
            WorkflowExecutor,
            WorkflowInput
        )

        executor = WorkflowExecutor()
        workflow_input = WorkflowInput(
            query="리스크 분석",
            content="계약 내용...",
            session_id="session-123",
            user_id="user-456"
        )

        params = executor._map_input_params("risk_workflow", workflow_input)

        assert params["contract_text"] == "계약 내용..."
        assert params["session_id"] == "session-123"
        assert params["user_id"] == "user-456"

    def test_unknown_workflow_default_mapping(self):
        """알 수 없는 워크플로우 기본 매핑"""
        from apps.ai_service.agents.workflow_executor import (
            WorkflowExecutor,
            WorkflowInput
        )

        executor = WorkflowExecutor()
        workflow_input = WorkflowInput(
            query="테스트",
            mode="standard",
            extra={"custom_param": "value"}
        )

        params = executor._map_input_params("unknown_workflow", workflow_input)

        assert params["query"] == "테스트"
        assert params["mode"] == "standard"
        assert params["custom_param"] == "value"


# =============================================================================
# 결과 정규화 테스트
# =============================================================================

class TestOutputNormalization:
    """워크플로우 결과 정규화 테스트"""

    def test_normalize_rag_workflow_output(self):
        """RAG 워크플로우 결과 정규화"""
        from apps.ai_service.agents.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor()
        result = {
            "answer": "절도죄는...",
            "sources": [{"case_number": "2020도1234"}],
            "confidence": 0.95,
            "revised": True,
            "iteration_count": 2,
            "critique_log": {"issues": []},
            "session_id": "session-123"
        }

        output = executor._normalize_output("rag_workflow", result, 2.5)

        assert output.success is True
        assert output.answer == "절도죄는..."
        assert len(output.sources) == 1
        assert output.confidence == 0.95
        assert output.metadata["revised"] is True
        assert output.metadata["iteration_count"] == 2
        assert output.processing_time == 2.5

    def test_normalize_error_result(self):
        """에러 결과 정규화"""
        from apps.ai_service.agents.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor()
        result = {
            "error": "Connection failed",
            "answer": "실패"
        }

        output = executor._normalize_output("rag_workflow", result, 1.0)

        assert output.success is False
        assert output.error == "Connection failed"
        assert output.confidence == 0.0

    def test_normalize_document_workflow_output(self):
        """문서 분석 워크플로우 결과 정규화"""
        from apps.ai_service.agents.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor()
        result = {
            "analysis": "문서 분석 결과...",
            "doc_type": "CONTRACT",
            "clauses": [{"id": 1, "text": "조항1"}],
            "confidence": 0.85
        }

        output = executor._normalize_output("document_workflow", result, 5.0)

        assert output.success is True
        assert output.answer == "문서 분석 결과..."
        assert output.metadata["doc_type"] == "CONTRACT"
        assert len(output.metadata["clauses"]) == 1


# =============================================================================
# 워크플로우 로딩 및 캐싱 테스트
# =============================================================================

class TestWorkflowLoading:
    """워크플로우 동적 로딩 테스트"""

    def test_workflow_caching(self):
        """워크플로우 캐싱 테스트"""
        from apps.ai_service.agents.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor()

        # 초기 캐시는 비어있음
        assert len(executor.get_cached_workflows()) == 0

        # 캐시 클리어 테스트
        executor._workflow_cache["test_workflow"] = MagicMock()
        assert "test_workflow" in executor.get_cached_workflows()

        executor.clear_cache("test_workflow")
        assert "test_workflow" not in executor.get_cached_workflows()

    def test_clear_all_cache(self):
        """전체 캐시 클리어 테스트"""
        from apps.ai_service.agents.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor()

        executor._workflow_cache["wf1"] = MagicMock()
        executor._workflow_cache["wf2"] = MagicMock()
        executor._factory_cache["wf1"] = MagicMock()

        executor.clear_cache()

        assert len(executor._workflow_cache) == 0
        assert len(executor._factory_cache) == 0

    def test_update_retriever(self):
        """retriever 업데이트 테스트"""
        from apps.ai_service.agents.workflow_executor import WorkflowExecutor

        mock_retriever_old = MagicMock()
        mock_retriever_new = MagicMock()

        executor = WorkflowExecutor(retriever=mock_retriever_old)
        executor._workflow_cache["rag_workflow"] = MagicMock()

        executor.update_retriever(mock_retriever_new)

        assert executor._retriever == mock_retriever_new
        assert "rag_workflow" not in executor._workflow_cache

    def test_is_workflow_available(self):
        """워크플로우 사용 가능 여부 확인 테스트"""
        from apps.ai_service.agents.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor()

        assert executor.is_workflow_available("rag_workflow") is True
        assert executor.is_workflow_available("document_workflow") is True
        assert executor.is_workflow_available("nonexistent_workflow") is False

    def test_get_available_workflows(self):
        """사용 가능한 워크플로우 목록 테스트"""
        from apps.ai_service.agents.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor()
        available = executor.get_available_workflows()

        assert "rag_workflow" in available
        assert "document_workflow" in available
        assert "case_workflow" in available
        assert "risk_workflow" in available

        # 각 워크플로우 정보 확인
        rag_info = available["rag_workflow"]
        assert "name" in rag_info
        assert "description" in rag_info
        assert "estimated_time" in rag_info


# =============================================================================
# 통합 실행 테스트
# =============================================================================

class TestWorkflowExecution:
    """워크플로우 실행 통합 테스트"""

    @pytest.mark.asyncio
    @patch("apps.ai_service.agents.workflow_executor.importlib")
    async def test_execute_with_input_success(self, mock_importlib):
        """execute_with_input 성공 테스트"""
        from apps.ai_service.agents.workflow_executor import (
            WorkflowExecutor,
            WorkflowInput
        )

        # Mock 워크플로우 설정
        mock_workflow = MagicMock()
        mock_workflow.arun = AsyncMock(return_value={
            "answer": "테스트 응답",
            "sources": [],
            "confidence": 0.9
        })

        mock_module = MagicMock()
        mock_module.get_rag_workflow = MagicMock(return_value=mock_workflow)
        mock_importlib.import_module.return_value = mock_module

        executor = WorkflowExecutor()
        workflow_input = WorkflowInput(query="테스트 질문")

        output = await executor.execute_with_input("rag_workflow", workflow_input)

        assert output.success is True
        assert output.answer == "테스트 응답"
        assert output.confidence == 0.9
        assert output.processing_time > 0

    @pytest.mark.asyncio
    async def test_execute_with_input_workflow_not_found(self):
        """존재하지 않는 워크플로우 실행 테스트"""
        from apps.ai_service.agents.workflow_executor import (
            WorkflowExecutor,
            WorkflowInput
        )

        executor = WorkflowExecutor()
        workflow_input = WorkflowInput(query="테스트")

        output = await executor.execute_with_input("nonexistent_workflow", workflow_input)

        assert output.success is False
        assert output.error is not None
        assert "not found" in output.error.lower() or "not found" in output.answer.lower()

    @pytest.mark.asyncio
    @patch("apps.ai_service.agents.workflow_executor.importlib")
    async def test_execute_with_input_exception(self, mock_importlib):
        """워크플로우 실행 중 예외 테스트"""
        from apps.ai_service.agents.workflow_executor import (
            WorkflowExecutor,
            WorkflowInput
        )

        # Mock 워크플로우가 예외 발생
        mock_workflow = MagicMock()
        mock_workflow.arun = AsyncMock(side_effect=RuntimeError("Test error"))

        mock_module = MagicMock()
        mock_module.get_rag_workflow = MagicMock(return_value=mock_workflow)
        mock_importlib.import_module.return_value = mock_module

        executor = WorkflowExecutor()
        workflow_input = WorkflowInput(query="테스트 질문")

        output = await executor.execute_with_input("rag_workflow", workflow_input)

        assert output.success is False
        assert output.error is not None
        assert "Test error" in output.error or "Test error" in output.answer


# =============================================================================
# 레거시 호환성 테스트
# =============================================================================

class TestLegacyCompatibility:
    """레거시 API 호환성 테스트"""

    @pytest.mark.asyncio
    @patch("apps.ai_service.agents.workflow_executor.importlib")
    async def test_legacy_execute_method(self, mock_importlib):
        """레거시 execute() 메서드 테스트"""
        from apps.ai_service.agents.workflow_executor import WorkflowExecutor

        # Mock 워크플로우 설정
        mock_workflow = MagicMock()
        mock_workflow.arun = AsyncMock(return_value={
            "answer": "레거시 응답",
            "sources": []
        })

        mock_module = MagicMock()
        mock_module.get_rag_workflow = MagicMock(return_value=mock_workflow)
        mock_importlib.import_module.return_value = mock_module

        executor = WorkflowExecutor()

        # 레거시 API 사용
        result = await executor.execute(
            workflow_name="rag_workflow",
            inputs={"query": "테스트"}
        )

        assert result.success is True
        assert result.data["answer"] == "레거시 응답"

    def test_workflow_result_dataclass(self):
        """WorkflowResult 데이터 클래스 테스트"""
        from apps.ai_service.agents.workflow_executor import WorkflowResult

        result = WorkflowResult(
            success=True,
            data={"answer": "테스트"},
            workflow_name="rag_workflow",
            execution_time=1.5
        )

        assert result.success is True
        assert result.data["answer"] == "테스트"
        assert result.workflow_name == "rag_workflow"
        assert result.execution_time == 1.5
        assert result.error is None


# =============================================================================
# 싱글톤 및 편의 함수 테스트
# =============================================================================

class TestSingletonAndConvenience:
    """싱글톤 및 편의 함수 테스트"""

    def test_get_workflow_executor_singleton(self):
        """get_workflow_executor 싱글톤 테스트"""
        from apps.ai_service.agents.workflow_executor import (
            get_workflow_executor,
            _executor_instance
        )

        # 싱글톤 인스턴스 리셋 (테스트 격리)
        import apps.ai_service.agents.workflow_executor as module
        module._executor_instance = None

        executor1 = get_workflow_executor()
        executor2 = get_workflow_executor()

        assert executor1 is executor2

    @pytest.mark.asyncio
    @patch("apps.ai_service.agents.workflow_executor.importlib")
    async def test_execute_workflow_convenience_function(self, mock_importlib):
        """execute_workflow 편의 함수 테스트"""
        from apps.ai_service.agents.workflow_executor import execute_workflow

        # Mock 워크플로우 설정
        mock_workflow = MagicMock()
        mock_workflow.arun = AsyncMock(return_value={
            "answer": "편의 함수 응답",
            "sources": []
        })

        mock_module = MagicMock()
        mock_module.get_rag_workflow = MagicMock(return_value=mock_workflow)
        mock_importlib.import_module.return_value = mock_module

        # 싱글톤 리셋
        import apps.ai_service.agents.workflow_executor as module
        module._executor_instance = None

        result = await execute_workflow(
            workflow_name="rag_workflow",
            inputs={"query": "테스트"}
        )

        assert result.success is True
