"""
Base Workflow Definitions

Phase 4 - Week 11: 워크플로우 공통 기반 클래스

BaseWorkflow:
- 모든 LangGraph 워크플로우의 공통 인터페이스
- 로깅, 에러 핸들링, 메트릭 수집 표준화
- Checkpointing 설정 관리 (Week 12)

사용:
    from apps.ai_service.workflows.base import BaseWorkflow

    class RAGWorkflow(BaseWorkflow):
        def create_graph(self) -> StateGraph:
            ...
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TypeVar, Generic
from loguru import logger
import time
import uuid

from langgraph.graph import StateGraph


StateType = TypeVar("StateType", bound=Dict[str, Any])


class BaseWorkflow(ABC, Generic[StateType]):
    """
    워크플로우 기본 클래스

    모든 LangGraph 기반 워크플로우의 공통 인터페이스를 정의합니다.

    Attributes:
        name: 워크플로우 이름
        graph: 컴파일된 StateGraph
        use_checkpointing: Checkpointing 사용 여부 (Week 12)
    """

    def __init__(
        self,
        name: str = "base_workflow",
        use_checkpointing: bool = False
    ):
        self.name = name
        self.use_checkpointing = use_checkpointing
        self.graph = self._build_and_compile()
        logger.info(f"{self.name} initialized (checkpointing={use_checkpointing})")

    @abstractmethod
    def create_graph(self) -> StateGraph:
        """
        StateGraph 생성 (서브클래스에서 구현)

        Returns:
            노드와 엣지가 정의된 StateGraph
        """
        pass

    @abstractmethod
    def create_initial_state(self, **kwargs) -> StateType:
        """
        초기 상태 생성 (서브클래스에서 구현)

        Returns:
            워크플로우 초기 상태
        """
        pass

    def _build_and_compile(self) -> StateGraph:
        """
        그래프 생성 및 컴파일

        Returns:
            컴파일된 StateGraph
        """
        graph = self.create_graph()

        # Week 12: Checkpointing 설정 추가 예정
        # if self.use_checkpointing:
        #     from langgraph.checkpoint.memory import MemorySaver
        #     return graph.compile(checkpointer=MemorySaver())

        return graph.compile()

    def run(self, **kwargs) -> Dict[str, Any]:
        """
        워크플로우 동기 실행

        Args:
            **kwargs: 초기 상태 생성 인자

        Returns:
            워크플로우 실행 결과
        """
        start_time = time.time()
        session_id = kwargs.get("session_id") or str(uuid.uuid4())

        logger.info(f"[{self.name}] Starting run, session={session_id}")

        try:
            initial_state = self.create_initial_state(**kwargs)
            result = self.graph.invoke(initial_state)

            processing_time = time.time() - start_time
            logger.info(f"[{self.name}] Completed in {processing_time:.2f}s")

            return self._format_result(result, processing_time, session_id)

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"[{self.name}] Error: {e}")
            return self._format_error(e, processing_time, session_id)

    async def arun(self, **kwargs) -> Dict[str, Any]:
        """
        워크플로우 비동기 실행

        Args:
            **kwargs: 초기 상태 생성 인자

        Returns:
            워크플로우 실행 결과
        """
        start_time = time.time()
        session_id = kwargs.get("session_id") or str(uuid.uuid4())

        logger.info(f"[{self.name}] Starting async run, session={session_id}")

        try:
            initial_state = self.create_initial_state(**kwargs)
            result = await self.graph.ainvoke(initial_state)

            processing_time = time.time() - start_time
            logger.info(f"[{self.name}] Completed in {processing_time:.2f}s")

            return self._format_result(result, processing_time, session_id)

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"[{self.name}] Error: {e}")
            return self._format_error(e, processing_time, session_id)

    def _format_result(
        self,
        result: Dict[str, Any],
        processing_time: float,
        session_id: str
    ) -> Dict[str, Any]:
        """
        결과 포맷팅 (서브클래스에서 오버라이드 가능)

        Args:
            result: 원시 실행 결과
            processing_time: 처리 시간
            session_id: 세션 ID

        Returns:
            포맷팅된 결과
        """
        return {
            **result,
            "processing_time": processing_time,
            "session_id": session_id,
        }

    def _format_error(
        self,
        error: Exception,
        processing_time: float,
        session_id: str
    ) -> Dict[str, Any]:
        """
        에러 포맷팅

        Args:
            error: 발생한 예외
            processing_time: 처리 시간
            session_id: 세션 ID

        Returns:
            에러 응답
        """
        return {
            "error": str(error),
            "processing_time": processing_time,
            "session_id": session_id,
        }


class WorkflowMetrics:
    """
    워크플로우 메트릭 수집 (Week 12)

    수집 항목:
    - 실행 횟수
    - 평균 처리 시간
    - 에러율
    - 노드별 실행 시간
    """

    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.total_runs = 0
        self.total_time = 0.0
        self.error_count = 0
        self.node_times: Dict[str, float] = {}

    def record_run(self, processing_time: float, success: bool = True):
        """실행 기록"""
        self.total_runs += 1
        self.total_time += processing_time
        if not success:
            self.error_count += 1

    def record_node_time(self, node_name: str, elapsed: float):
        """노드 실행 시간 기록"""
        if node_name not in self.node_times:
            self.node_times[node_name] = 0.0
        self.node_times[node_name] += elapsed

    @property
    def avg_time(self) -> float:
        """평균 처리 시간"""
        if self.total_runs == 0:
            return 0.0
        return self.total_time / self.total_runs

    @property
    def error_rate(self) -> float:
        """에러율"""
        if self.total_runs == 0:
            return 0.0
        return self.error_count / self.total_runs

    def to_dict(self) -> Dict[str, Any]:
        """메트릭 딕셔너리 반환"""
        return {
            "workflow": self.workflow_name,
            "total_runs": self.total_runs,
            "avg_processing_time": round(self.avg_time, 3),
            "error_rate": round(self.error_rate, 3),
            "node_times": self.node_times,
        }
