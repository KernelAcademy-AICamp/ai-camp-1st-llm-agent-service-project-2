"""
Workflow Router - 워크플로우 라우터

Phase 5: Agent Hub - 워크플로우 라우팅 컴포넌트

설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.2

역할:
- 분류된 의도에 따라 적절한 워크플로우와 도구를 선택
- 실행 계획 수립 (실행 순서, 병렬 실행 그룹 결정)
- 예상 실행 시간 계산

매핑된 워크플로우:
- RAGWorkflow: RAG 기반 질의응답 (apps/ai_service/workflows/rag_workflow.py)
- DocumentWorkflow: 문서 분석 (apps/ai_service/workflows/document_workflow.py)
- CaseWorkflow: 사건 분석 (apps/ai_service/workflows/case_workflow.py)
- RiskWorkflow: 리스크 분석 (apps/ai_service/workflows/risk_workflow.py)
- LLMComparisonWorkflow: LLM 비교 (apps/ai_service/workflows/llm_comparison_workflow.py)
- CrawlerWorkflow: 크롤러 (apps/ai_service/graphs/crawler_graph.py)
- AnalyticsWorkflow: 분석 대시보드 (apps/ai_service/graphs/analytics_graph.py)
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import logging
import uuid

from apps.ai_service.agents.states.master_agent_state import (
    Intent,
    IntentCategory,
    ExecutionPlan,
    WorkflowStep,
    ToolCall,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 실행 우선순위 열거형
# =============================================================================

class ExecutionPriority(str, Enum):
    """실행 우선순위"""
    HIGH_SPEED = "high_speed"    # 빠른 응답 우선
    ACCURACY = "accuracy"        # 정확도 우선
    QUALITY = "quality"          # 품질 우선 (느리지만 상세함)


# =============================================================================
# 워크플로우 설정 정보
# =============================================================================

class WorkflowConfig:
    """워크플로우 설정 정보"""
    def __init__(
        self,
        name: str,
        module_path: str,
        factory_function: str,
        estimated_time: float,
        requires_checkpointing: bool = False,
        supports_streaming: bool = True,
        required_inputs: Optional[List[str]] = None,
        description: str = "",
    ):
        self.name = name
        self.module_path = module_path
        self.factory_function = factory_function
        self.estimated_time = estimated_time
        self.requires_checkpointing = requires_checkpointing
        self.supports_streaming = supports_streaming
        self.required_inputs = required_inputs or []
        self.description = description


# =============================================================================
# 워크플로우 레지스트리
# =============================================================================

WORKFLOW_REGISTRY: Dict[str, WorkflowConfig] = {
    "rag_workflow": WorkflowConfig(
        name="rag_workflow",
        module_path="apps.ai_service.workflows.rag_workflow",
        factory_function="get_rag_workflow",
        estimated_time=20.0,  # Hybrid Search + LLM 생성 시간 고려 (기존 3.0 → 20.0)
        requires_checkpointing=False,
        supports_streaming=True,
        required_inputs=["query"],
        description="RAG 기반 법률 질의응답",
    ),
    "document_workflow": WorkflowConfig(
        name="document_workflow",
        module_path="apps.ai_service.workflows.document_workflow",
        factory_function="get_document_workflow",
        estimated_time=25.0,  # 문서 분석 3단계(요약/조항/리스크)에 각 10-15초 소요 (기존 10.0 → 25.0)
        requires_checkpointing=False,
        supports_streaming=True,
        required_inputs=["content"],
        description="문서 분석 (계약서, 소장, 판결문 등)",
    ),
    "case_workflow": WorkflowConfig(
        name="case_workflow",
        module_path="apps.ai_service.workflows.case_workflow",
        factory_function="get_case_workflow",
        estimated_time=8.0,
        requires_checkpointing=False,
        supports_streaming=True,
        required_inputs=["content"],
        description="사건/판례 분석",
    ),
    "risk_workflow": WorkflowConfig(
        name="risk_workflow",
        module_path="apps.ai_service.workflows.risk_workflow",
        factory_function="get_risk_workflow",
        estimated_time=15.0,
        requires_checkpointing=True,  # Human-in-the-Loop
        supports_streaming=True,
        required_inputs=["content"],
        description="리스크 평가 (계약서, 거래 등)",
    ),
    "llm_comparison_workflow": WorkflowConfig(
        name="llm_comparison_workflow",
        module_path="apps.ai_service.workflows.llm_comparison_workflow",
        factory_function="create_llm_comparison_workflow",
        estimated_time=30.0,
        requires_checkpointing=True,  # Human-in-the-Loop
        supports_streaming=True,
        required_inputs=["task", "input_data", "model_configs"],
        description="LLM 모델 비교 분석",
    ),
    "crawler_workflow": WorkflowConfig(
        name="crawler_workflow",
        module_path="apps.ai_service.graphs.crawler_graph",
        factory_function="create_crawler_workflow",
        estimated_time=20.0,
        requires_checkpointing=True,
        supports_streaming=False,
        required_inputs=["urls"],
        description="웹 크롤링 및 데이터 수집",
    ),
    "analytics_workflow": WorkflowConfig(
        name="analytics_workflow",
        module_path="apps.ai_service.graphs.analytics_graph",
        factory_function="create_analytics_workflow",
        estimated_time=5.0,
        requires_checkpointing=False,
        supports_streaming=True,
        required_inputs=[],
        description="통계 분석 및 대시보드",
    ),
}


# =============================================================================
# 의도-워크플로우 매핑
# =============================================================================

INTENT_WORKFLOW_MAP: Dict[IntentCategory, Dict[str, Any]] = {
    IntentCategory.GENERAL_CHAT: {
        "workflows": [],  # 워크플로우 없음 - LLM 직접 응답
        "tools": [],
        "priority": ExecutionPriority.HIGH_SPEED,
        "requires_checkpointing": False,
        "description": "일반 대화 (법률과 무관)",
    },
    IntentCategory.QUERY: {
        "workflows": ["rag_workflow"],
        "tools": [],
        "priority": ExecutionPriority.HIGH_SPEED,
        "requires_checkpointing": False,
        "description": "RAG 기반 빠른 법률 질의응답",
    },
    IntentCategory.DOCUMENT_ANALYSIS: {
        "workflows": ["document_workflow"],
        "tools": [
            "detect_document_type",
            "analyze_document",
            "extract_clauses",
            "summarize_document",
        ],
        "priority": ExecutionPriority.ACCURACY,
        "requires_checkpointing": False,
        "description": "문서 분석 (계약서, 소장, 판결문)",
    },
    IntentCategory.CASE_ANALYSIS: {
        "workflows": ["case_workflow"],
        "tools": [
            "analyze_case",
            "extract_parties",
            "identify_issues",
            "assess_case_complexity",
        ],
        "priority": ExecutionPriority.ACCURACY,
        "requires_checkpointing": False,
        "description": "사건/판례 분석",
    },
    IntentCategory.RISK_ASSESSMENT: {
        "workflows": ["risk_workflow"],
        "tools": ["analyze_risks"],
        "priority": ExecutionPriority.ACCURACY,
        "requires_checkpointing": True,  # Human-in-the-Loop
        "description": "리스크 평가",
    },
    IntentCategory.COMPARISON: {
        "workflows": ["llm_comparison_workflow"],
        "tools": [
            "execute_on_model",
            "calculate_llm_metrics",
            "select_best_model",
        ],
        "priority": ExecutionPriority.QUALITY,
        "requires_checkpointing": True,  # Human-in-the-Loop
        "description": "LLM 모델 비교 분석",
    },
    IntentCategory.SEARCH: {
        "workflows": [],  # 도구만 사용
        "tools": [
            "fetch_court_api",
            "fetch_statute_api",
            "search_related_cases",
            "mcp_search_precedents",
        ],
        "priority": ExecutionPriority.HIGH_SPEED,
        "requires_checkpointing": False,
        "description": "판례/법령 검색",
    },
    IntentCategory.GENERATION: {
        "workflows": [],  # 도구만 사용
        "tools": [
            "generate_report",
            "aggregate_statistics",
        ],
        "priority": ExecutionPriority.QUALITY,
        "requires_checkpointing": False,
        "description": "문서/보고서 생성",
    },
    IntentCategory.ANALYTICS: {
        "workflows": ["analytics_workflow"],
        "tools": [
            "aggregate_statistics",
            "calculate_metrics",
        ],
        "priority": ExecutionPriority.ACCURACY,
        "requires_checkpointing": False,
        "description": "통계 분석 및 대시보드",
    },
    IntentCategory.MULTI_TASK: {
        "workflows": [],  # 동적으로 결정
        "tools": [],      # 동적으로 결정
        "priority": ExecutionPriority.QUALITY,
        "requires_checkpointing": False,  # 개별 워크플로우에 따라 결정
        "description": "복합 작업 (여러 기능 조합)",
    },
    IntentCategory.UNKNOWN: {
        "workflows": ["rag_workflow"],  # 기본값: RAG
        "tools": [],
        "priority": ExecutionPriority.HIGH_SPEED,
        "requires_checkpointing": False,
        "description": "기본 질의응답 (분류 불가)",
    },
}


# =============================================================================
# 도구 메타데이터
# =============================================================================

TOOL_METADATA: Dict[str, Dict[str, Any]] = {
    # Document Tools
    "detect_document_type": {
        "estimated_time": 1.0,
        "category": "document",
        "description": "문서 타입 감지",
    },
    "analyze_document": {
        "estimated_time": 5.0,
        "category": "document",
        "description": "문서 분석",
    },
    "extract_clauses": {
        "estimated_time": 3.0,
        "category": "document",
        "description": "조항 추출",
    },
    "summarize_document": {
        "estimated_time": 4.0,
        "category": "document",
        "description": "문서 요약",
    },
    # Case Tools
    "analyze_case": {
        "estimated_time": 5.0,
        "category": "case",
        "description": "사건 분석",
    },
    "extract_parties": {
        "estimated_time": 2.0,
        "category": "case",
        "description": "당사자 추출",
    },
    "identify_issues": {
        "estimated_time": 3.0,
        "category": "case",
        "description": "쟁점 식별",
    },
    "assess_case_complexity": {
        "estimated_time": 2.0,
        "category": "case",
        "description": "사건 복잡도 평가",
    },
    # Risk Tools
    "analyze_risks": {
        "estimated_time": 8.0,
        "category": "risk",
        "description": "리스크 분석",
    },
    # LLM Tools
    "execute_on_model": {
        "estimated_time": 10.0,
        "category": "llm",
        "description": "특정 LLM 모델 실행",
    },
    "calculate_llm_metrics": {
        "estimated_time": 2.0,
        "category": "llm",
        "description": "LLM 메트릭 계산",
    },
    "select_best_model": {
        "estimated_time": 1.0,
        "category": "llm",
        "description": "최적 모델 선택",
    },
    # Search Tools
    "fetch_court_api": {
        "estimated_time": 3.0,
        "category": "external",
        "description": "대법원 판례 API 조회",
    },
    "fetch_statute_api": {
        "estimated_time": 2.0,
        "category": "external",
        "description": "법령 API 조회",
    },
    "search_related_cases": {
        "estimated_time": 3.0,
        "category": "search",
        "description": "관련 판례 검색",
    },
    "mcp_search_precedents": {
        "estimated_time": 2.0,
        "category": "search",
        "description": "MCP 판례 검색",
    },
    # Generation Tools
    "generate_report": {
        "estimated_time": 10.0,
        "category": "generation",
        "description": "보고서 생성",
    },
    "aggregate_statistics": {
        "estimated_time": 3.0,
        "category": "analytics",
        "description": "통계 집계",
    },
    "calculate_metrics": {
        "estimated_time": 2.0,
        "category": "analytics",
        "description": "메트릭 계산",
    },
}


# =============================================================================
# WorkflowRouter 클래스
# =============================================================================

class WorkflowRouter:
    """
    워크플로우 라우터

    분류된 의도에 따라 적절한 워크플로우와 도구를 선택하고
    실행 계획을 수립합니다.

    Attributes:
        intent_map: 의도-워크플로우 매핑
        workflow_registry: 워크플로우 레지스트리
        tool_metadata: 도구 메타데이터
    """

    def __init__(self):
        self.intent_map = INTENT_WORKFLOW_MAP
        self.workflow_registry = WORKFLOW_REGISTRY
        self.tool_metadata = TOOL_METADATA

        logger.info("WorkflowRouter initialized")

    def route(
        self,
        intent: Intent,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """
        실행 계획 생성

        Args:
            intent: 분류된 의도
            context: 실행 컨텍스트 (첨부파일, 대화기록, 사용자 정보 등)

        Returns:
            ExecutionPlan 객체
        """
        context = context or {}

        # intent.category는 use_enum_values=True로 인해 문자열일 수 있음
        category_value = intent.category.value if hasattr(intent.category, 'value') else intent.category
        logger.info(f"Routing intent: {category_value}")

        # 1. 의도에 맞는 워크플로우/도구 선택
        selected = self._select_workflows_and_tools(intent, context)

        # 2. 실행 순서 결정
        execution_order = self._determine_execution_order(
            selected["workflows"],
            selected["tools"],
            intent,
        )

        # 3. 병렬 실행 그룹 식별
        parallel_groups = self._identify_parallel_groups(
            selected["workflows"],
            selected["tools"],
        )

        # 4. 예상 실행 시간 계산
        estimated_time = self._estimate_time(
            selected["workflows"],
            selected["tools"],
        )

        # 5. 실행 계획 생성
        plan = ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            workflows=selected["workflows"],
            tools=selected["tools"],
            execution_order=execution_order,
            estimated_total_time=estimated_time,
            can_parallelize=len(parallel_groups) > 1,
            parallel_groups=parallel_groups,
        )

        logger.info(
            f"Execution plan created: {len(plan.workflows)} workflows, "
            f"{len(plan.tools)} tools, estimated_time={estimated_time:.1f}s"
        )

        return plan

    def _select_workflows_and_tools(
        self,
        intent: Intent,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        워크플로우/도구 선택

        Args:
            intent: 분류된 의도
            context: 실행 컨텍스트

        Returns:
            {"workflows": [...], "tools": [...]}
        """
        # intent.category는 use_enum_values=True로 인해 문자열일 수 있음
        category_value = intent.category.value if hasattr(intent.category, 'value') else intent.category

        # 문자열을 enum으로 변환하여 매핑 조회
        try:
            category_enum = IntentCategory(category_value)
        except ValueError:
            category_enum = IntentCategory.UNKNOWN

        mapping = self.intent_map.get(category_enum, self.intent_map[IntentCategory.UNKNOWN])

        workflows: List[WorkflowStep] = []
        tools: List[ToolCall] = []

        # MULTI_TASK 처리: 추천된 워크플로우 또는 extracted_params 활용
        if category_enum == IntentCategory.MULTI_TASK:
            # 1. intent.suggested_workflows 사용
            workflow_names = intent.suggested_workflows or []

            # 2. extracted_params에서 sub_tasks 추출
            sub_tasks = intent.extracted_params.get("sub_tasks", [])
            for sub_task in sub_tasks:
                try:
                    sub_category = IntentCategory(sub_task.upper())
                    sub_mapping = self.intent_map.get(sub_category, {})
                    workflow_names.extend(sub_mapping.get("workflows", []))
                except ValueError:
                    pass

            # 중복 제거
            workflow_names = list(dict.fromkeys(workflow_names))
        else:
            workflow_names = mapping.get("workflows", [])

        # 워크플로우 생성
        for idx, wf_name in enumerate(workflow_names):
            if wf_name in self.workflow_registry:
                config = self.workflow_registry[wf_name]
                step = WorkflowStep(
                    step_id=f"wf_{idx}_{wf_name[:8]}",
                    workflow_name=wf_name,
                    inputs=self._extract_workflow_inputs(wf_name, intent, context),
                    depends_on=[],  # 기본적으로 독립 실행
                    estimated_time=config.estimated_time,
                    priority=idx,
                )
                workflows.append(step)

        # 도구 선택 (필요한 경우만)
        tool_names = mapping.get("tools", [])

        # 워크플로우가 없는 경우에만 도구 직접 사용
        if not workflows and tool_names:
            for idx, tool_name in enumerate(tool_names):
                if tool_name in self.tool_metadata:
                    metadata = self.tool_metadata[tool_name]
                    tool_call = ToolCall(
                        tool_id=f"tool_{idx}_{tool_name[:8]}",
                        tool_name=tool_name,
                        inputs=self._extract_tool_inputs(tool_name, intent, context),
                        depends_on=[],
                    )
                    tools.append(tool_call)

        return {
            "workflows": workflows,
            "tools": tools,
            "priority": mapping.get("priority", ExecutionPriority.HIGH_SPEED),
            "requires_checkpointing": mapping.get("requires_checkpointing", False),
        }

    def _extract_workflow_inputs(
        self,
        workflow_name: str,
        intent: Intent,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        워크플로우 입력 파라미터 추출

        Args:
            workflow_name: 워크플로우 이름
            intent: 분류된 의도
            context: 실행 컨텍스트

        Returns:
            워크플로우 입력 파라미터
        """
        inputs = {}

        # 공통 파라미터
        if "query" in context or "user_message" in context:
            inputs["query"] = context.get("query") or context.get("user_message", "")

        # 첨부 파일에서 content 추출
        attachments = context.get("attachments", [])
        if attachments:
            # 첫 번째 첨부 파일의 내용 사용
            inputs["content"] = attachments[0].get("content", "")
            inputs["doc_type"] = attachments[0].get("type", "unknown")

        # intent에서 추출된 파라미터 병합
        inputs.update(intent.extracted_params)

        # 워크플로우별 특수 파라미터
        if workflow_name == "llm_comparison_workflow":
            inputs["task"] = context.get("task", "compare")
            inputs["input_data"] = context.get("input_data", {})
            inputs["model_configs"] = context.get("model_configs", [])

        return inputs

    def _extract_tool_inputs(
        self,
        tool_name: str,
        intent: Intent,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        도구 입력 파라미터 추출

        Args:
            tool_name: 도구 이름
            intent: 분류된 의도
            context: 실행 컨텍스트

        Returns:
            도구 입력 파라미터
        """
        inputs = {}

        # 공통 파라미터
        query = context.get("query") or context.get("user_message", "")

        # 도구별 입력 매핑
        if tool_name in ["fetch_court_api", "mcp_search_precedents", "search_related_cases"]:
            inputs["query"] = query
            inputs["top_k"] = intent.extracted_params.get("top_k", 5)

        elif tool_name == "fetch_statute_api":
            inputs["query"] = query

        elif tool_name in ["analyze_document", "extract_clauses", "summarize_document"]:
            attachments = context.get("attachments", [])
            if attachments:
                inputs["content"] = attachments[0].get("content", "")
                inputs["doc_type"] = attachments[0].get("type", "unknown")

        elif tool_name == "generate_report":
            inputs["data"] = context.get("data", {})
            inputs["format"] = intent.extracted_params.get("format", "markdown")

        return inputs

    def _determine_execution_order(
        self,
        workflows: List[WorkflowStep],
        tools: List[ToolCall],
        intent: Intent,
    ) -> List[str]:
        """
        실행 순서 결정

        Args:
            workflows: 워크플로우 목록
            tools: 도구 목록
            intent: 분류된 의도

        Returns:
            실행 순서 (step_id/tool_id 목록)
        """
        order = []

        # 1. 우선순위에 따라 워크플로우 정렬
        sorted_workflows = sorted(workflows, key=lambda w: w.priority)

        # 2. 도구는 카테고리별로 그룹화하여 순서 결정
        # - document 도구: detect -> analyze -> extract -> summarize
        # - case 도구: analyze -> extract -> identify -> assess
        # - search 도구: 병렬 실행 가능

        # 워크플로우 먼저 실행
        for wf in sorted_workflows:
            order.append(wf.step_id)

        # 도구 실행
        for tool in tools:
            order.append(tool.tool_id)

        return order

    def _identify_parallel_groups(
        self,
        workflows: List[WorkflowStep],
        tools: List[ToolCall],
    ) -> List[List[str]]:
        """
        병렬 실행 가능한 그룹 식별

        의존성이 없는 워크플로우/도구는 병렬 실행 가능

        Args:
            workflows: 워크플로우 목록
            tools: 도구 목록

        Returns:
            병렬 실행 그룹 목록
        """
        groups = []

        # 의존성이 없는 워크플로우는 모두 병렬 실행 가능
        independent_workflows = [
            wf.step_id for wf in workflows if not wf.depends_on
        ]
        if independent_workflows:
            groups.append(independent_workflows)

        # 의존성이 있는 워크플로우는 순차 실행
        dependent_workflows = [
            wf.step_id for wf in workflows if wf.depends_on
        ]
        for wf_id in dependent_workflows:
            groups.append([wf_id])

        # 도구는 카테고리별로 병렬 실행 가능
        tool_categories: Dict[str, List[str]] = {}
        for tool in tools:
            metadata = self.tool_metadata.get(tool.tool_name, {})
            category = metadata.get("category", "unknown")
            if category not in tool_categories:
                tool_categories[category] = []
            tool_categories[category].append(tool.tool_id)

        # 같은 카테고리 도구는 순차, 다른 카테고리는 병렬
        for category, tool_ids in tool_categories.items():
            if len(tool_ids) > 1:
                # 같은 카테고리 내에서는 순차 실행
                for tool_id in tool_ids:
                    groups.append([tool_id])
            else:
                groups.append(tool_ids)

        return groups if groups else [[]]

    def _estimate_time(
        self,
        workflows: List[WorkflowStep],
        tools: List[ToolCall],
    ) -> float:
        """
        예상 실행 시간 계산

        병렬 실행 가능한 경우 최대 시간 기준

        Args:
            workflows: 워크플로우 목록
            tools: 도구 목록

        Returns:
            예상 총 실행 시간 (초)
        """
        total_time = 0.0

        # 워크플로우 시간
        workflow_times = [wf.estimated_time for wf in workflows]
        if workflow_times:
            # 병렬 실행 가능하면 최대값, 아니면 합계
            # 간단하게 최대값 + 나머지의 30% (부분 병렬화 가정)
            if len(workflow_times) > 1:
                total_time += max(workflow_times) + sum(sorted(workflow_times)[:-1]) * 0.3
            else:
                total_time += sum(workflow_times)

        # 도구 시간
        for tool in tools:
            metadata = self.tool_metadata.get(tool.tool_name, {})
            total_time += metadata.get("estimated_time", 2.0)

        return round(total_time, 1)

    def get_workflow_config(self, workflow_name: str) -> Optional[WorkflowConfig]:
        """
        워크플로우 설정 조회

        Args:
            workflow_name: 워크플로우 이름

        Returns:
            WorkflowConfig 또는 None
        """
        return self.workflow_registry.get(workflow_name)

    def get_available_workflows(self) -> List[str]:
        """사용 가능한 워크플로우 목록 반환"""
        return list(self.workflow_registry.keys())

    def get_available_tools(self) -> List[str]:
        """사용 가능한 도구 목록 반환"""
        return list(self.tool_metadata.keys())


# =============================================================================
# 편의 함수
# =============================================================================

def get_workflow_router() -> WorkflowRouter:
    """
    WorkflowRouter 인스턴스 생성

    Returns:
        WorkflowRouter 인스턴스
    """
    return WorkflowRouter()
