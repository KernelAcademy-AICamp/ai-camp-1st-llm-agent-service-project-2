"""
Tool Registry - 도구 등록 및 실행 (Phase 7 확장)

기존 WorkflowExecutor를 래핑하여 도구로 사용할 수 있게 합니다.
Phase 7: 도구 확장 및 카테고리 분류, 병렬 실행, 폴백 체인 지원
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
import time

from apps.ai_service.agents.workflow_executor import (
    WorkflowExecutor,
    get_workflow_executor,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 도구 카테고리 정의 (Phase 7)
# =============================================================================

class ToolCategory(Enum):
    """도구 카테고리"""
    SEARCH = "search"           # 검색 도구
    ANALYSIS = "analysis"       # 분석 도구
    DOCUMENT = "document"       # 문서 처리
    EXTERNAL_API = "external"   # 외부 API
    UTILITY = "utility"         # 유틸리티


# =============================================================================
# 도구 정의 (확장)
# =============================================================================

@dataclass
class ToolDefinition:
    """도구 정의 (Phase 7 확장)"""
    name: str
    description: str
    workflow_name: Optional[str]  # 연결된 워크플로우
    input_schema: Dict[str, Any]  # 입력 스키마
    output_schema: Dict[str, Any]  # 출력 스키마
    # Phase 7 추가 필드
    category: ToolCategory = ToolCategory.UTILITY
    estimated_tokens: int = 500  # 예상 토큰 사용량
    timeout: float = 30.0  # 타임아웃 (초)
    requires_context: bool = False  # 컨텍스트 필요 여부
    fallback_tool: Optional[str] = None  # 폴백 도구
    is_external_api: bool = False  # 외부 API 여부
    external_handler: Optional[Callable] = None  # 외부 API 핸들러


@dataclass
class ToolResult:
    """도구 실행 결과 (Phase 7 확장)"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tokens_used: int = 0  # Phase 7: 토큰 사용량 추적
    execution_time: float = 0.0  # Phase 7: 실행 시간


# =============================================================================
# 도구 → 워크플로우 매핑 (확장)
# =============================================================================

TOOL_WORKFLOW_MAP: Dict[str, str] = {
    # 검색 도구
    "search_legal": "rag_workflow",
    "search_cases": "rag_workflow",
    "search_statutes": "rag_workflow",
    "search_precedents": "rag_workflow",

    # 분석 도구
    "analyze_document": "document_workflow",
    "analyze_case": "case_workflow",
    "assess_risk": "risk_workflow",
    "analyze_contract": "document_workflow",

    # 비교 도구
    "compare_documents": "document_workflow",
    "compare_models": "llm_comparison_workflow",
}


# =============================================================================
# 폴백 체인 정의 (Phase 7)
# =============================================================================

TOOL_FALLBACK_CHAIN: Dict[str, List[str]] = {
    "search_legal": ["search_precedents", "fetch_statute_api"],
    "search_precedents": ["fetch_court_api", "search_legal"],
    "search_statutes": ["fetch_statute_api", "search_legal"],
    "analyze_document": ["analyze_contract"],
    "fetch_court_api": ["search_precedents"],
    "fetch_statute_api": ["search_statutes"],
}


# =============================================================================
# ToolRegistry 클래스 (Phase 7 확장)
# =============================================================================

class ToolRegistry:
    """
    도구 레지스트리 (Phase 7 확장)

    기능:
    - 워크플로우 기반 도구 실행
    - 외부 API 도구 실행
    - 폴백 체인 지원
    - 카테고리별 도구 필터링
    - 토큰 사용량 추적
    """

    def __init__(self, retriever=None):
        """ToolRegistry 초기화"""
        self._executor = get_workflow_executor(retriever=retriever)
        self._tools: Dict[str, ToolDefinition] = {}
        self._external_handlers: Dict[str, Callable] = {}
        self._register_default_tools()
        self._register_external_api_tools()
        logger.info(f"ToolRegistry initialized with {len(self._tools)} tools")

    def _register_default_tools(self):
        """기본 워크플로우 기반 도구 등록"""
        default_tools = [
            # 검색 도구
            ToolDefinition(
                name="search_legal",
                description="법률 정보 검색 (RAG). 법령, 판례, 법률 문서에서 관련 정보를 검색합니다.",
                workflow_name="rag_workflow",
                input_schema={"query": "str", "top_k": "int"},
                output_schema={"answer": "str", "sources": "list"},
                category=ToolCategory.SEARCH,
                estimated_tokens=800,
                timeout=60.0,
                fallback_tool="search_precedents",
            ),
            ToolDefinition(
                name="search_precedents",
                description="판례 검색. 유사 판례와 관련 사건을 검색합니다.",
                workflow_name="rag_workflow",
                input_schema={"query": "str", "case_type": "str", "top_k": "int"},
                output_schema={"cases": "list", "relevance_scores": "list"},
                category=ToolCategory.SEARCH,
                estimated_tokens=600,
                timeout=45.0,
                fallback_tool="fetch_court_api",
            ),
            ToolDefinition(
                name="search_statutes",
                description="법령 검색. 관련 법률 조문을 검색합니다.",
                workflow_name="rag_workflow",
                input_schema={"query": "str", "law_type": "str"},
                output_schema={"statutes": "list", "articles": "list"},
                category=ToolCategory.SEARCH,
                estimated_tokens=500,
                timeout=30.0,
                fallback_tool="fetch_statute_api",
            ),
            ToolDefinition(
                name="search_cases",
                description="사건 검색. 유사 사건과 관련 정보를 검색합니다.",
                workflow_name="rag_workflow",
                input_schema={"query": "str", "top_k": "int"},
                output_schema={"cases": "list"},
                category=ToolCategory.SEARCH,
                estimated_tokens=600,
                timeout=45.0,
            ),

            # 분석 도구
            ToolDefinition(
                name="analyze_document",
                description="문서 분석. 법률 문서의 구조, 핵심 조항, 리스크를 분석합니다.",
                workflow_name="document_workflow",
                input_schema={"document_content": "str", "analysis_type": "str"},
                output_schema={"analysis": "dict", "summary": "str"},
                category=ToolCategory.ANALYSIS,
                estimated_tokens=1500,
                timeout=90.0,
                requires_context=True,
            ),
            ToolDefinition(
                name="analyze_case",
                description="판례/사건 분석. 사건의 쟁점, 판결 요지, 시사점을 분석합니다.",
                workflow_name="case_workflow",
                input_schema={"case_content": "str"},
                output_schema={"analysis": "dict", "key_points": "list"},
                category=ToolCategory.ANALYSIS,
                estimated_tokens=1200,
                timeout=60.0,
            ),
            ToolDefinition(
                name="analyze_contract",
                description="계약서 분석. 계약 조건, 의무, 권리를 분석합니다.",
                workflow_name="document_workflow",
                input_schema={"contract_content": "str", "contract_type": "str"},
                output_schema={"clauses": "list", "risks": "list", "summary": "str"},
                category=ToolCategory.DOCUMENT,
                estimated_tokens=1800,
                timeout=120.0,
                requires_context=True,
            ),
            ToolDefinition(
                name="assess_risk",
                description="리스크 평가. 법률 문서의 잠재적 위험 요소를 평가합니다.",
                workflow_name="risk_workflow",
                input_schema={"document_content": "str"},
                output_schema={"risks": "list", "score": "float"},
                category=ToolCategory.ANALYSIS,
                estimated_tokens=1000,
                timeout=60.0,
            ),

            # 문서 처리 도구
            ToolDefinition(
                name="compare_documents",
                description="문서 비교. 두 문서의 차이점과 공통점을 분석합니다.",
                workflow_name="document_workflow",
                input_schema={"doc1": "str", "doc2": "str"},
                output_schema={"differences": "list", "similarities": "list"},
                category=ToolCategory.DOCUMENT,
                estimated_tokens=2000,
                timeout=120.0,
                requires_context=True,
            ),
            ToolDefinition(
                name="compare_models",
                description="LLM 모델 비교. 여러 모델의 응답을 비교합니다.",
                workflow_name="llm_comparison_workflow",
                input_schema={"query": "str", "models": "list"},
                output_schema={"comparisons": "list", "summary": "str"},
                category=ToolCategory.ANALYSIS,
                estimated_tokens=3000,
                timeout=180.0,
            ),
        ]

        for tool in default_tools:
            self._tools[tool.name] = tool

    def _register_external_api_tools(self):
        """외부 API 도구 등록 (Phase 7)"""
        try:
            from apps.ai_service.mcp.tools.external_tools import (
                fetch_court_api,
                fetch_statute_api,
                parse_legal_document,
                validate_document_structure,
            )

            external_tools = [
                ToolDefinition(
                    name="fetch_court_api",
                    description="대법원 판례 API 호출. 실시간 판례 데이터를 조회합니다.",
                    workflow_name=None,
                    input_schema={
                        "keyword": "str",
                        "case_number": "str",
                        "start_date": "str",
                        "end_date": "str",
                    },
                    output_schema={"precedents": "list", "total_count": "int"},
                    category=ToolCategory.EXTERNAL_API,
                    estimated_tokens=100,  # API 호출은 LLM 토큰 적음
                    timeout=30.0,
                    is_external_api=True,
                    external_handler=fetch_court_api,
                ),
                ToolDefinition(
                    name="fetch_statute_api",
                    description="법령 API 호출. 최신 법령 정보를 조회합니다.",
                    workflow_name=None,
                    input_schema={
                        "keyword": "str",
                        "law_type": "str",
                        "ministry": "str",
                    },
                    output_schema={"statutes": "list", "total_count": "int"},
                    category=ToolCategory.EXTERNAL_API,
                    estimated_tokens=100,
                    timeout=30.0,
                    is_external_api=True,
                    external_handler=fetch_statute_api,
                ),
                ToolDefinition(
                    name="parse_legal_document",
                    description="법률 문서 파싱. 문서 구조를 분석하고 섹션을 추출합니다.",
                    workflow_name=None,
                    input_schema={"content": "str", "doc_type": "str"},
                    output_schema={"sections": "list", "title": "str"},
                    category=ToolCategory.UTILITY,
                    estimated_tokens=50,
                    timeout=10.0,
                    is_external_api=True,
                    external_handler=parse_legal_document,
                ),
                ToolDefinition(
                    name="validate_document_structure",
                    description="문서 구조 검증. 필수 필드 존재 여부를 확인합니다.",
                    workflow_name=None,
                    input_schema={"data": "dict", "doc_type": "str"},
                    output_schema={"valid": "bool", "missing_fields": "list"},
                    category=ToolCategory.UTILITY,
                    estimated_tokens=30,
                    timeout=5.0,
                    is_external_api=True,
                    external_handler=validate_document_structure,
                ),
            ]

            for tool in external_tools:
                self._tools[tool.name] = tool
                if tool.external_handler:
                    self._external_handlers[tool.name] = tool.external_handler

            logger.info(f"Registered {len(external_tools)} external API tools")

        except ImportError as e:
            logger.warning(f"Failed to import external tools: {e}")

    # =================================================================
    # 도구 조회 메서드
    # =================================================================

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """도구 정의 조회"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """등록된 도구 목록"""
        return list(self._tools.keys())

    def list_tools_by_category(self, category: ToolCategory) -> List[str]:
        """카테고리별 도구 목록 (Phase 7)"""
        return [
            name for name, tool in self._tools.items()
            if tool.category == category
        ]

    def get_tools_for_context(
        self,
        query: str,
        categories: Optional[List[ToolCategory]] = None,
        max_tools: int = 10,
    ) -> List[ToolDefinition]:
        """
        컨텍스트에 적합한 도구 필터링 (Phase 7)

        THINKING 경로에서 사용. 질문에 관련된 도구만 반환합니다.

        Args:
            query: 사용자 질문
            categories: 허용할 카테고리 목록
            max_tools: 최대 도구 수

        Returns:
            필터링된 도구 정의 목록
        """
        query_lower = query.lower()

        # 키워드 기반 점수 계산
        keyword_scores = {
            "검색": [ToolCategory.SEARCH],
            "찾아": [ToolCategory.SEARCH],
            "판례": [ToolCategory.SEARCH, ToolCategory.EXTERNAL_API],
            "법령": [ToolCategory.SEARCH, ToolCategory.EXTERNAL_API],
            "법률": [ToolCategory.SEARCH],
            "조문": [ToolCategory.SEARCH],
            "분석": [ToolCategory.ANALYSIS],
            "평가": [ToolCategory.ANALYSIS],
            "계약": [ToolCategory.DOCUMENT, ToolCategory.ANALYSIS],
            "문서": [ToolCategory.DOCUMENT],
            "비교": [ToolCategory.DOCUMENT],
            "리스크": [ToolCategory.ANALYSIS],
            "위험": [ToolCategory.ANALYSIS],
            "사건": [ToolCategory.SEARCH, ToolCategory.ANALYSIS],
        }

        # 관련 카테고리 결정
        relevant_categories = set()
        for keyword, cats in keyword_scores.items():
            if keyword in query_lower:
                relevant_categories.update(cats)

        # 카테고리 필터 적용
        if categories:
            relevant_categories = relevant_categories.intersection(set(categories))

        # 카테고리 없으면 모든 카테고리 허용
        if not relevant_categories:
            relevant_categories = set(ToolCategory)

        # 도구 필터링
        filtered_tools = [
            tool for tool in self._tools.values()
            if tool.category in relevant_categories
        ]

        # 예상 토큰 기준 정렬 (적은 것 우선)
        filtered_tools.sort(key=lambda t: t.estimated_tokens)

        return filtered_tools[:max_tools]

    def get_fallback_tools(self, tool_name: str) -> List[str]:
        """폴백 도구 목록 반환 (Phase 7)"""
        return TOOL_FALLBACK_CHAIN.get(tool_name, [])

    def estimate_cost(self, tool_names: List[str]) -> Dict[str, Any]:
        """
        도구 실행 비용 추정 (Phase 7)

        Args:
            tool_names: 실행할 도구 목록

        Returns:
            {
                "total_estimated_tokens": int,
                "total_estimated_time": float,
                "per_tool": {tool_name: {"tokens": int, "time": float}}
            }
        """
        total_tokens = 0
        total_time = 0.0
        per_tool = {}

        for name in tool_names:
            tool = self._tools.get(name)
            if tool:
                total_tokens += tool.estimated_tokens
                total_time += tool.timeout * 0.5  # 평균적으로 타임아웃의 절반
                per_tool[name] = {
                    "tokens": tool.estimated_tokens,
                    "time": tool.timeout,
                }

        return {
            "total_estimated_tokens": total_tokens,
            "total_estimated_time": total_time,
            "per_tool": per_tool,
        }

    # =================================================================
    # 도구 실행 메서드
    # =================================================================

    async def execute_tool(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        use_fallback: bool = True,
        max_retries: int = 2,
    ) -> ToolResult:
        """
        도구 실행 (Phase 7: 폴백 및 재시도 지원)

        Args:
            tool_name: 도구 이름
            inputs: 입력 파라미터
            use_fallback: 실패 시 폴백 사용 여부
            max_retries: 최대 재시도 횟수

        Returns:
            ToolResult
        """
        start_time = time.time()

        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}",
            )

        # 재시도 로직
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"[ToolRegistry] Retry {attempt}/{max_retries} for {tool_name}")
                    await asyncio.sleep(1.0 * attempt)  # 지수 백오프

                result = await self._execute_single_tool(tool, inputs)
                result.execution_time = time.time() - start_time

                if result.success:
                    return result

                last_error = result.error

            except asyncio.TimeoutError:
                last_error = f"Tool {tool_name} timed out after {tool.timeout}s"
                logger.warning(last_error)
            except Exception as e:
                last_error = str(e)
                logger.error(f"[ToolRegistry] Tool {tool_name} error: {e}")

        # 폴백 시도
        if use_fallback:
            fallback_tools = self.get_fallback_tools(tool_name)
            for fallback_name in fallback_tools:
                logger.info(f"[ToolRegistry] Trying fallback: {fallback_name}")
                fallback_result = await self.execute_tool(
                    fallback_name,
                    inputs,
                    use_fallback=False,  # 폴백의 폴백은 안함
                    max_retries=1,
                )
                if fallback_result.success:
                    fallback_result.execution_time = time.time() - start_time
                    return fallback_result

        return ToolResult(
            success=False,
            error=f"Tool {tool_name} failed after {max_retries + 1} attempts: {last_error}",
            execution_time=time.time() - start_time,
        )

    async def _execute_single_tool(
        self,
        tool: ToolDefinition,
        inputs: Dict[str, Any],
    ) -> ToolResult:
        """단일 도구 실행 (내부)"""

        # 외부 API 도구인 경우
        if tool.is_external_api and tool.external_handler:
            try:
                result = await asyncio.wait_for(
                    tool.external_handler(**inputs),
                    timeout=tool.timeout,
                )
                return ToolResult(
                    success=result.get("success", True),
                    data=result,
                    tokens_used=tool.estimated_tokens,
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=str(e),
                )

        # 워크플로우 기반 도구인 경우
        if not tool.workflow_name:
            return ToolResult(
                success=False,
                error=f"Tool {tool.name} has no associated workflow",
            )

        try:
            result = await asyncio.wait_for(
                self._executor.execute(
                    workflow_name=tool.workflow_name,
                    inputs=inputs,
                ),
                timeout=tool.timeout,
            )

            if result.success:
                return ToolResult(
                    success=True,
                    data=result.data,
                    tokens_used=tool.estimated_tokens,
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.error,
                )

        except asyncio.TimeoutError:
            raise
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
            )

    async def execute_tools_parallel(
        self,
        tool_calls: List[Dict[str, Any]],
        max_concurrent: int = 3,
    ) -> List[ToolResult]:
        """
        여러 도구 병렬 실행 (Phase 7)

        Args:
            tool_calls: [{"tool_name": str, "inputs": dict}, ...]
            max_concurrent: 최대 동시 실행 수

        Returns:
            ToolResult 목록
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(call):
            async with semaphore:
                return await self.execute_tool(
                    call["tool_name"],
                    call.get("inputs", {}),
                )

        tasks = [execute_with_semaphore(call) for call in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외를 ToolResult로 변환
        converted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                converted_results.append(ToolResult(
                    success=False,
                    error=str(result),
                ))
            else:
                converted_results.append(result)

        return converted_results

    async def execute_workflow(
        self,
        workflow_name: str,
        inputs: Dict[str, Any],
    ) -> ToolResult:
        """
        워크플로우 직접 실행

        Args:
            workflow_name: 워크플로우 이름
            inputs: 입력 파라미터

        Returns:
            ToolResult
        """
        start_time = time.time()

        try:
            logger.info(f"[ToolRegistry] Executing workflow: {workflow_name}")

            result = await self._executor.execute(
                workflow_name=workflow_name,
                inputs=inputs,
            )

            execution_time = time.time() - start_time

            if result.success:
                return ToolResult(
                    success=True,
                    data=result.data,
                    execution_time=execution_time,
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.error,
                    execution_time=execution_time,
                )

        except Exception as e:
            logger.error(f"[ToolRegistry] Workflow execution failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )


# =============================================================================
# 싱글톤/팩토리
# =============================================================================

_registry_instance: Optional[ToolRegistry] = None


def get_tool_registry(retriever=None) -> ToolRegistry:
    """ToolRegistry 인스턴스 반환 (싱글톤)"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry(retriever=retriever)
    return _registry_instance


def init_tool_registry(retriever=None) -> ToolRegistry:
    """ToolRegistry 명시적 초기화 (기존 인스턴스 덮어씀)"""
    global _registry_instance
    _registry_instance = ToolRegistry(retriever=retriever)
    return _registry_instance
