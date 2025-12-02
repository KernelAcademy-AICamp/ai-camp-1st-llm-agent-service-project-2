"""
Workflow Executor - 워크플로우 실행기

Phase 4.5: Agent Hub - 워크플로우 동적 로딩 및 실행

설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.2

역할:
- WORKFLOW_REGISTRY 설정을 기반으로 워크플로우 동적 로드
- 워크플로우 인스턴스 캐싱 (매 요청마다 import하지 않음)
- 입력 파라미터 매핑 (WorkflowInput → 워크플로우별 파라미터)
- 출력 정규화 (워크플로우 결과 → WorkflowOutput)
- 에러 핸들링 및 로깅

개선점 (기존 execute_workflows_node._run_workflow 대비):
- inspect.signature() 런타임 호출 제거
- 워크플로우별 파라미터 매핑 명시적 정의
- 표준화된 입력/출력 형식 (WorkflowInput/WorkflowOutput)
- 캐싱으로 반복 import 방지
"""

import importlib
import asyncio
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
import logging

from apps.ai_service.agents.workflow_router import (
    WORKFLOW_REGISTRY,
    WorkflowConfig,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 워크플로우 입력/출력 데이터 클래스
# =============================================================================

@dataclass
class WorkflowInput:
    """
    워크플로우 공통 입력 구조

    모든 워크플로우가 받을 수 있는 표준 입력 형식.
    워크플로우별로 필요한 필드만 사용됨.
    """
    query: str
    mode: str = "standard"
    top_k: int = 5
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    content: Optional[str] = None  # 첨부파일 내용 (문서 분석용)
    doc_type: Optional[str] = None  # 문서 타입
    extra: Dict[str, Any] = field(default_factory=dict)  # 워크플로우별 추가 파라미터


@dataclass
class WorkflowOutput:
    """
    워크플로우 공통 출력 구조

    모든 워크플로우 결과를 표준화된 형식으로 반환.
    """
    success: bool
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    metadata: Dict[str, Any]
    error: Optional[str] = None
    processing_time: float = 0.0


@dataclass
class WorkflowResult:
    """워크플로우 실행 결과 (레거시 호환용)"""
    success: bool
    data: Dict[str, Any]
    workflow_name: str
    execution_time: float
    error: Optional[str] = None


# =============================================================================
# WorkflowExecutor 클래스
# =============================================================================

class WorkflowExecutor:
    """
    워크플로우 실행기

    WORKFLOW_REGISTRY에 정의된 워크플로우를 동적으로 로드하고 실행합니다.

    기능:
    1. 동적 모듈 로딩 (importlib 사용)
    2. 워크플로우 캐싱
    3. 입력 파라미터 매핑 (WorkflowInput → 워크플로우별 파라미터)
    4. 출력 정규화 (워크플로우 결과 → WorkflowOutput)
    5. 에러 핸들링

    Usage (레거시):
        executor = WorkflowExecutor()
        result = await executor.execute("rag_workflow", {"query": "형법이란?"})

    Usage (신규 - 권장):
        executor = WorkflowExecutor(retriever=app.state.retriever)
        result = await executor.execute_with_input(
            "rag_workflow",
            WorkflowInput(query="형법이란?", mode="standard")
        )
    """

    def __init__(self, retriever=None):
        """
        WorkflowExecutor 초기화

        Args:
            retriever: HybridRetriever 인스턴스 (RAG 워크플로우용)
        """
        self._workflow_cache: Dict[str, Any] = {}
        self._factory_cache: Dict[str, Callable] = {}
        self._retriever = retriever
        logger.info("WorkflowExecutor initialized")

    # =========================================================================
    # 동적 모듈 로딩
    # =========================================================================

    def _load_factory_function(self, workflow_name: str) -> Optional[Callable]:
        """
        워크플로우 팩토리 함수 로드

        Args:
            workflow_name: 워크플로우 이름 (WORKFLOW_REGISTRY 키)

        Returns:
            팩토리 함수 또는 None

        Raises:
            WorkflowLoadError: 모듈/함수 로드 실패 시
        """
        # 캐시 확인
        if workflow_name in self._factory_cache:
            logger.debug(f"Factory cache hit: {workflow_name}")
            return self._factory_cache[workflow_name]

        # 레지스트리에서 설정 조회
        config = WORKFLOW_REGISTRY.get(workflow_name)
        if not config:
            raise WorkflowLoadError(f"Workflow not found in registry: {workflow_name}")

        logger.info(f"Loading workflow: {workflow_name} from {config.module_path}")

        try:
            # 모듈 동적 import
            module = importlib.import_module(config.module_path)

            # 팩토리 함수 가져오기
            factory_function = getattr(module, config.factory_function, None)
            if factory_function is None:
                raise WorkflowLoadError(
                    f"Factory function not found: {config.factory_function} "
                    f"in module {config.module_path}"
                )

            # 캐시에 저장
            self._factory_cache[workflow_name] = factory_function
            logger.info(f"Loaded factory function: {config.factory_function}")

            return factory_function

        except ImportError as e:
            raise WorkflowLoadError(
                f"Failed to import module: {config.module_path}. Error: {e}"
            )
        except Exception as e:
            raise WorkflowLoadError(
                f"Failed to load workflow {workflow_name}: {e}"
            )

    def _get_workflow_instance(
        self,
        workflow_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        워크플로우 인스턴스 가져오기

        캐시에 있으면 캐시 사용, 없으면 새로 생성

        Args:
            workflow_name: 워크플로우 이름
            context: 워크플로우 초기화 컨텍스트 (retriever 등)

        Returns:
            워크플로우 인스턴스
        """
        context = context or {}

        # retriever 우선순위: context > self._retriever
        retriever = context.get("retriever") or self._retriever

        # RAG 워크플로우이고 retriever가 있으면 캐시 사용 안 함
        # (retriever가 변경될 수 있으므로)
        use_cache = not (workflow_name == "rag_workflow" and retriever)

        if use_cache and workflow_name in self._workflow_cache:
            logger.debug(f"Workflow cache hit: {workflow_name}")
            return self._workflow_cache[workflow_name]

        # 팩토리 함수 로드
        factory = self._load_factory_function(workflow_name)

        # 워크플로우 인스턴스 생성
        try:
            # 특수 케이스: RAGWorkflow는 retriever 인자 필요
            if workflow_name == "rag_workflow" and retriever:
                instance = factory(retriever=retriever)
            else:
                instance = factory()

            # 캐시에 저장
            if use_cache:
                self._workflow_cache[workflow_name] = instance

            logger.info(f"Created workflow instance: {workflow_name}")
            return instance

        except Exception as e:
            raise WorkflowLoadError(
                f"Failed to create workflow instance {workflow_name}: {e}"
            )

    # =========================================================================
    # 워크플로우 실행
    # =========================================================================

    async def execute(
        self,
        workflow_name: str,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> WorkflowResult:
        """
        워크플로우 실행

        Args:
            workflow_name: 워크플로우 이름
            inputs: 워크플로우 입력 파라미터
            context: 실행 컨텍스트 (retriever, session_id 등)
            timeout: 타임아웃 (초)

        Returns:
            WorkflowResult
        """
        context = context or {}
        start_time = time.time()

        logger.info(f"Executing workflow: {workflow_name}")
        logger.debug(f"Inputs: {list(inputs.keys())}")

        try:
            # 1. 워크플로우 인스턴스 가져오기
            workflow = self._get_workflow_instance(workflow_name, context)

            # 2. 워크플로우 설정 조회
            config = WORKFLOW_REGISTRY.get(workflow_name)

            # 3. 타임아웃 설정
            effective_timeout = timeout or (config.estimated_time * 3 if config else 60.0)

            # 4. 워크플로우 실행
            result = await self._invoke_workflow(
                workflow=workflow,
                workflow_name=workflow_name,
                inputs=inputs,
                context=context,
                timeout=effective_timeout,
            )

            execution_time = time.time() - start_time
            logger.info(f"Workflow {workflow_name} completed in {execution_time:.2f}s")

            return WorkflowResult(
                success=True,
                data=result,
                workflow_name=workflow_name,
                execution_time=execution_time,
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error_msg = f"Workflow {workflow_name} timed out after {execution_time:.2f}s"
            logger.error(error_msg)

            return WorkflowResult(
                success=False,
                data={},
                workflow_name=workflow_name,
                execution_time=execution_time,
                error=error_msg,
            )

        except WorkflowLoadError as e:
            execution_time = time.time() - start_time
            logger.error(f"Workflow load error: {e}")

            return WorkflowResult(
                success=False,
                data={},
                workflow_name=workflow_name,
                execution_time=execution_time,
                error=str(e),
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Workflow execution error: {e}"
            logger.error(error_msg, exc_info=True)

            return WorkflowResult(
                success=False,
                data={},
                workflow_name=workflow_name,
                execution_time=execution_time,
                error=error_msg,
            )

    async def _invoke_workflow(
        self,
        workflow: Any,
        workflow_name: str,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
        timeout: float,
    ) -> Dict[str, Any]:
        """
        워크플로우 실제 실행

        워크플로우 타입에 따라 적절한 메서드 호출:
        - RAGWorkflow: arun() 메서드
        - BaseWorkflow 상속 (DocumentWorkflow, CaseWorkflow): arun() 메서드
        - LangGraph CompiledGraph: ainvoke() 메서드
        - 일반 함수: await 호출

        Args:
            workflow: 워크플로우 인스턴스
            workflow_name: 워크플로우 이름
            inputs: 입력 파라미터
            context: 실행 컨텍스트
            timeout: 타임아웃

        Returns:
            실행 결과 (Dict)
        """
        # 세션 ID 추출
        session_id = context.get("session_id") or inputs.get("session_id")
        user_id = context.get("user_id") or inputs.get("user_id")

        # 워크플로우별 실행 방식 결정
        if workflow_name == "rag_workflow":
            # RAGWorkflow: arun(query, mode, top_k, session_id, user_id)
            coro = workflow.arun(
                query=inputs.get("query", ""),
                mode=inputs.get("mode", "standard"),
                top_k=inputs.get("top_k", 5),
                session_id=session_id,
                user_id=user_id,
                include_critique_log=inputs.get("include_critique_log", False),
            )

        elif workflow_name == "document_workflow":
            # DocumentWorkflow: arun(file_path, document_id, text, doc_type, query)
            coro = workflow.arun(
                file_path=inputs.get("file_path"),
                document_id=inputs.get("document_id"),
                text=inputs.get("content") or inputs.get("text"),
                doc_type=inputs.get("doc_type", "OTHER"),
                query=inputs.get("query"),  # 사용자 질문 전달
            )

        elif workflow_name == "case_workflow":
            # CaseWorkflow: arun(case_content, case_type)
            coro = workflow.arun(
                case_content=inputs.get("content") or inputs.get("case_content", ""),
                case_type=inputs.get("case_type", "other"),
            )

        elif workflow_name == "risk_workflow":
            # RiskWorkflow: arun(**inputs)
            # 별도 구현 필요 시 추가
            if hasattr(workflow, "arun"):
                coro = workflow.arun(**inputs)
            elif hasattr(workflow, "ainvoke"):
                coro = workflow.ainvoke(inputs)
            else:
                raise WorkflowExecutionError(
                    f"Workflow {workflow_name} has no arun or ainvoke method"
                )

        elif workflow_name == "llm_comparison_workflow":
            # LLMComparisonWorkflow
            if hasattr(workflow, "arun"):
                coro = workflow.arun(**inputs)
            elif hasattr(workflow, "ainvoke"):
                coro = workflow.ainvoke(inputs)
            else:
                raise WorkflowExecutionError(
                    f"Workflow {workflow_name} has no arun or ainvoke method"
                )

        else:
            # 기타 워크플로우: arun > ainvoke > invoke 순으로 시도
            if hasattr(workflow, "arun"):
                coro = workflow.arun(**inputs)
            elif hasattr(workflow, "ainvoke"):
                coro = workflow.ainvoke(inputs)
            elif callable(workflow):
                # 일반 함수인 경우
                result = workflow(**inputs)
                if asyncio.iscoroutine(result):
                    coro = result
                else:
                    return self._normalize_result(result)
            else:
                raise WorkflowExecutionError(
                    f"Workflow {workflow_name} is not callable"
                )

        # 타임아웃 적용하여 실행
        result = await asyncio.wait_for(coro, timeout=timeout)

        return self._normalize_result(result)

    def _normalize_result(self, result: Any) -> Dict[str, Any]:
        """
        결과 정규화

        다양한 워크플로우 반환 형식을 Dict[str, Any]로 통일

        Args:
            result: 워크플로우 실행 결과

        Returns:
            정규화된 결과 (Dict)
        """
        if result is None:
            return {"success": True, "data": None}

        if isinstance(result, dict):
            return result

        # dataclass인 경우
        if hasattr(result, "__dataclass_fields__"):
            from dataclasses import asdict
            return asdict(result)

        # Pydantic 모델인 경우
        if hasattr(result, "model_dump"):
            return result.model_dump()
        elif hasattr(result, "dict"):
            return result.dict()

        # 기타: 문자열로 변환
        return {"result": str(result)}

    # =========================================================================
    # 유틸리티 메서드
    # =========================================================================

    def clear_cache(self, workflow_name: Optional[str] = None):
        """
        캐시 클리어

        Args:
            workflow_name: 특정 워크플로우만 클리어 (None이면 전체)
        """
        if workflow_name:
            self._workflow_cache.pop(workflow_name, None)
            self._factory_cache.pop(workflow_name, None)
            logger.info(f"Cleared cache for workflow: {workflow_name}")
        else:
            self._workflow_cache.clear()
            self._factory_cache.clear()
            logger.info("Cleared all workflow caches")

    def get_available_workflows(self) -> Dict[str, Dict[str, Any]]:
        """
        사용 가능한 워크플로우 목록 반환

        Returns:
            워크플로우 정보 딕셔너리
        """
        return {
            name: {
                "name": config.name,
                "description": config.description,
                "estimated_time": config.estimated_time,
                "requires_checkpointing": config.requires_checkpointing,
                "supports_streaming": config.supports_streaming,
                "required_inputs": config.required_inputs,
            }
            for name, config in WORKFLOW_REGISTRY.items()
        }

    def is_workflow_available(self, workflow_name: str) -> bool:
        """
        워크플로우 사용 가능 여부 확인

        Args:
            workflow_name: 워크플로우 이름

        Returns:
            사용 가능 여부
        """
        return workflow_name in WORKFLOW_REGISTRY

    # =========================================================================
    # WorkflowInput 기반 실행 (권장 방식)
    # =========================================================================

    async def execute_with_input(
        self,
        workflow_name: str,
        workflow_input: WorkflowInput
    ) -> WorkflowOutput:
        """
        WorkflowInput 기반 워크플로우 실행 (권장 방식)

        런타임 inspect.signature() 호출 없이 명시적 파라미터 매핑 사용.

        Args:
            workflow_name: 실행할 워크플로우 이름
            workflow_input: WorkflowInput 객체

        Returns:
            WorkflowOutput: 정규화된 실행 결과

        Usage:
            executor = WorkflowExecutor(retriever=app.state.retriever)
            result = await executor.execute_with_input(
                "rag_workflow",
                WorkflowInput(query="형법이란?", mode="standard")
            )
        """
        start_time = time.time()

        logger.info(f"[WorkflowExecutor] Executing: {workflow_name}")
        logger.debug(f"[WorkflowExecutor] Input: query='{workflow_input.query[:50] if len(workflow_input.query) > 50 else workflow_input.query}...'")

        try:
            # 1. 워크플로우 인스턴스 가져오기
            workflow = self._get_workflow_instance(workflow_name)

            # 2. 입력 파라미터 매핑 (명시적 - inspect 불필요)
            params = self._map_input_params(workflow_name, workflow_input)
            logger.debug(f"[WorkflowExecutor] Params: {list(params.keys())}")

            # 3. 워크플로우 실행
            result = await self._execute_workflow_internal(workflow, params)

            processing_time = time.time() - start_time

            # 4. 결과 정규화
            output = self._normalize_output(workflow_name, result, processing_time)

            logger.info(
                f"[WorkflowExecutor] Completed: {workflow_name} "
                f"in {processing_time:.2f}s, success={output.success}"
            )

            return output

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"[WorkflowExecutor] Error in {workflow_name}: {e}")

            return WorkflowOutput(
                success=False,
                answer=f"워크플로우 실행 중 오류가 발생했습니다: {str(e)}",
                sources=[],
                confidence=0.0,
                metadata={"workflow_name": workflow_name},
                error=str(e),
                processing_time=processing_time,
            )

    def _map_input_params(
        self,
        workflow_name: str,
        workflow_input: WorkflowInput
    ) -> Dict[str, Any]:
        """
        워크플로우별 입력 파라미터 매핑 (명시적 정의)

        런타임 inspect.signature() 대신 워크플로우별 파라미터를 명시적으로 매핑.

        Args:
            workflow_name: 워크플로우 이름
            workflow_input: 입력 데이터

        Returns:
            워크플로우에 전달할 파라미터 딕셔너리
        """
        if workflow_name == "rag_workflow":
            # RAGWorkflow.arun(query, mode, top_k, session_id, user_id, include_critique_log)
            params = {
                "query": workflow_input.query,
                "mode": workflow_input.mode,
                "top_k": workflow_input.top_k,
            }
            if workflow_input.session_id:
                params["session_id"] = workflow_input.session_id
            if workflow_input.user_id:
                params["user_id"] = workflow_input.user_id
            params["include_critique_log"] = workflow_input.extra.get(
                "include_critique_log", False
            )
            return params

        elif workflow_name == "document_workflow":
            # DocumentWorkflow: arun(file_path, document_id, text, doc_type, query)
            return {
                "text": workflow_input.content,
                "doc_type": workflow_input.doc_type or "OTHER",
                "file_path": workflow_input.extra.get("file_path"),
                "document_id": workflow_input.extra.get("document_id"),
                "query": workflow_input.query,  # 사용자 질문 전달
            }

        elif workflow_name == "case_workflow":
            # CaseWorkflow: arun(case_content, case_type)
            return {
                "case_content": workflow_input.content or workflow_input.query,
                "case_type": workflow_input.extra.get("case_type", "other"),
            }

        elif workflow_name == "risk_workflow":
            # RiskWorkflow 파라미터
            return {
                "contract_text": workflow_input.content or workflow_input.query,
                "session_id": workflow_input.session_id,
                "user_id": workflow_input.user_id,
            }

        elif workflow_name == "llm_comparison_workflow":
            # LLMComparisonWorkflow 파라미터
            return {
                "task": workflow_input.extra.get("task", "compare"),
                "input_data": {
                    "query": workflow_input.query,
                    "content": workflow_input.content,
                },
                "model_configs": workflow_input.extra.get("model_configs", []),
            }

        elif workflow_name == "crawler_workflow":
            # CrawlerWorkflow 파라미터
            return {
                "urls": workflow_input.extra.get("urls", []),
                "max_depth": workflow_input.extra.get("max_depth", 2),
                "output_format": workflow_input.extra.get("output_format", "json"),
            }

        elif workflow_name == "analytics_workflow":
            # AnalyticsWorkflow 파라미터
            return {
                "query": workflow_input.query,
                "date_range": workflow_input.extra.get("date_range"),
                "metrics": workflow_input.extra.get("metrics", []),
            }

        # 기본: 모든 기본 파라미터 전달
        return {
            "query": workflow_input.query,
            "mode": workflow_input.mode,
            "top_k": workflow_input.top_k,
            "session_id": workflow_input.session_id,
            "user_id": workflow_input.user_id,
            "content": workflow_input.content,
            "doc_type": workflow_input.doc_type,
            **workflow_input.extra,
        }

    async def _execute_workflow_internal(
        self,
        workflow: Any,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        워크플로우 실행 (다양한 인터페이스 지원)

        Args:
            workflow: 워크플로우 인스턴스
            params: 실행 파라미터

        Returns:
            실행 결과 딕셔너리
        """
        # 우선순위: arun > run > ainvoke > invoke > callable
        if hasattr(workflow, "arun"):
            result = await workflow.arun(**params)
        elif hasattr(workflow, "run"):
            if asyncio.iscoroutinefunction(workflow.run):
                result = await workflow.run(**params)
            else:
                result = workflow.run(**params)
        elif hasattr(workflow, "ainvoke"):
            # LangGraph StateGraph (dict 입력)
            result = await workflow.ainvoke(params)
        elif hasattr(workflow, "invoke"):
            if asyncio.iscoroutinefunction(workflow.invoke):
                result = await workflow.invoke(params)
            else:
                result = workflow.invoke(params)
        elif callable(workflow):
            if asyncio.iscoroutinefunction(workflow):
                result = await workflow(params)
            else:
                result = workflow(params)
        else:
            raise WorkflowExecutionError("Workflow has no executable method")

        # dict가 아닌 경우 래핑
        return result if isinstance(result, dict) else {"result": result}

    def _normalize_output(
        self,
        workflow_name: str,
        result: Dict[str, Any],
        processing_time: float
    ) -> WorkflowOutput:
        """
        워크플로우 결과를 WorkflowOutput으로 정규화

        Args:
            workflow_name: 워크플로우 이름
            result: 워크플로우 실행 결과
            processing_time: 처리 시간

        Returns:
            WorkflowOutput: 정규화된 출력
        """
        # 에러 체크
        if result.get("error"):
            return WorkflowOutput(
                success=False,
                answer=result.get("answer", f"오류 발생: {result.get('error')}"),
                sources=[],
                confidence=0.0,
                metadata=result,
                error=result.get("error"),
                processing_time=processing_time,
            )

        # RAGWorkflow 결과 형식
        if workflow_name == "rag_workflow":
            return WorkflowOutput(
                success=True,
                answer=result.get("answer", ""),
                sources=result.get("sources", []),
                confidence=result.get("confidence", 0.0),
                metadata={
                    "revised": result.get("revised", False),
                    "iteration_count": result.get("iteration_count", 0),
                    "critique_log": result.get("critique_log"),
                    "session_id": result.get("session_id"),
                },
                processing_time=processing_time,
            )

        # DocumentWorkflow 결과 형식
        elif workflow_name == "document_workflow":
            return WorkflowOutput(
                success=True,
                answer=result.get("analysis", result.get("summary", str(result))),
                sources=result.get("references", []),
                confidence=result.get("confidence", 0.7),
                metadata={
                    "doc_type": result.get("doc_type"),
                    "clauses": result.get("clauses", []),
                    "entities": result.get("entities", []),
                },
                processing_time=processing_time,
            )

        # CaseWorkflow 결과 형식
        elif workflow_name == "case_workflow":
            return WorkflowOutput(
                success=True,
                answer=result.get("analysis", str(result)),
                sources=result.get("related_cases", []),
                confidence=result.get("confidence", 0.7),
                metadata={
                    "parties": result.get("parties", []),
                    "issues": result.get("issues", []),
                    "complexity": result.get("complexity"),
                },
                processing_time=processing_time,
            )

        # RiskWorkflow 결과 형식
        elif workflow_name == "risk_workflow":
            return WorkflowOutput(
                success=True,
                answer=result.get("summary", result.get("analysis", str(result))),
                sources=[],
                confidence=result.get("confidence", 0.7),
                metadata={
                    "risks": result.get("risks", []),
                    "risk_level": result.get("risk_level"),
                    "recommendations": result.get("recommendations", []),
                },
                processing_time=processing_time,
            )

        # 기본 형식
        return WorkflowOutput(
            success=True,
            answer=result.get("answer", result.get("result", str(result))),
            sources=result.get("sources", []),
            confidence=result.get("confidence", 0.5),
            metadata=result,
            processing_time=processing_time,
        )

    def execute_with_input_sync(
        self,
        workflow_name: str,
        workflow_input: WorkflowInput
    ) -> WorkflowOutput:
        """
        WorkflowInput 기반 동기 실행

        Args:
            workflow_name: 실행할 워크플로우 이름
            workflow_input: WorkflowInput 객체

        Returns:
            WorkflowOutput: 정규화된 실행 결과
        """
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.execute_with_input(workflow_name, workflow_input)
                )
                return future.result()
        except RuntimeError:
            return asyncio.run(self.execute_with_input(workflow_name, workflow_input))

    def update_retriever(self, retriever):
        """
        retriever 업데이트 (캐시된 rag_workflow도 갱신)

        Args:
            retriever: 새 HybridRetriever 인스턴스
        """
        self._retriever = retriever
        # rag_workflow 캐시 무효화
        self.clear_cache("rag_workflow")
        logger.info("Retriever updated, rag_workflow cache invalidated")

    def get_cached_workflows(self) -> List[str]:
        """캐시된 워크플로우 목록 반환"""
        return list(self._workflow_cache.keys())


# =============================================================================
# 예외 클래스
# =============================================================================

class WorkflowLoadError(Exception):
    """워크플로우 로드 실패 예외"""
    pass


class WorkflowExecutionError(Exception):
    """워크플로우 실행 실패 예외"""
    pass


# =============================================================================
# 편의 함수
# =============================================================================

# 싱글톤 인스턴스
_executor_instance: Optional[WorkflowExecutor] = None


def get_workflow_executor(retriever=None) -> WorkflowExecutor:
    """
    WorkflowExecutor 싱글톤 인스턴스 반환

    Args:
        retriever: HybridRetriever 인스턴스 (optional)
                   - 최초 호출 시: 이 값으로 초기화
                   - 이후 호출 시: 기존 인스턴스의 retriever가 None이면 업데이트

    Returns:
        WorkflowExecutor 인스턴스

    Usage:
        # main.py startup에서 retriever 주입
        executor = get_workflow_executor(retriever=app.state.retriever)

        # 이후 다른 곳에서는 인자 없이 호출
        executor = get_workflow_executor()
    """
    global _executor_instance

    if _executor_instance is None:
        # 최초 생성
        _executor_instance = WorkflowExecutor(retriever=retriever)
        if retriever:
            logger.info("WorkflowExecutor initialized with retriever")
    elif retriever is not None and _executor_instance._retriever is None:
        # 기존 인스턴스에 retriever가 없으면 업데이트
        _executor_instance.update_retriever(retriever)
        logger.info("WorkflowExecutor retriever updated")

    return _executor_instance


def init_workflow_executor(retriever=None) -> WorkflowExecutor:
    """
    WorkflowExecutor 명시적 초기화 (main.py startup에서 사용)

    기존 인스턴스가 있어도 새로 생성합니다.

    Args:
        retriever: HybridRetriever 인스턴스

    Returns:
        새로 생성된 WorkflowExecutor 인스턴스
    """
    global _executor_instance
    _executor_instance = WorkflowExecutor(retriever=retriever)
    logger.info(f"WorkflowExecutor initialized (retriever={'yes' if retriever else 'no'})")
    return _executor_instance


async def execute_workflow(
    workflow_name: str,
    inputs: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
) -> WorkflowResult:
    """
    워크플로우 실행 편의 함수

    Args:
        workflow_name: 워크플로우 이름
        inputs: 입력 파라미터
        context: 실행 컨텍스트
        timeout: 타임아웃

    Returns:
        WorkflowResult
    """
    executor = get_workflow_executor()
    return await executor.execute(
        workflow_name=workflow_name,
        inputs=inputs,
        context=context,
        timeout=timeout,
    )
