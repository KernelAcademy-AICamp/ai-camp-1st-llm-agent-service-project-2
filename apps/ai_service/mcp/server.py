"""
MCP Server Entry Point

Phase 4 - Week 12: FastMCP 기반 MCP 서버

MCP 서버:
- 도구(Tools): 판례 검색, 문서 분석, 사건 분석, LLM 비교
- 리소스(Resources): document://, precedent://

사용법:
    from apps.ai_service.mcp.server import create_mcp_server

    mcp = create_mcp_server()
    mcp.run()

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


def create_mcp_server(name: str = "CriminalLaw MCP Server"):
    """
    MCP 서버 생성

    Args:
        name: 서버 이름

    Returns:
        FastMCP 인스턴스
    """
    try:
        from fastmcp import FastMCP
    except ImportError:
        logger.warning("fastmcp not installed. MCP server will not be available.")
        return None

    mcp = FastMCP(
        name=name,
        version="1.0.0",
        description="형사법 판례/법령 검색 및 분석 MCP 서버"
    )

    # ==========================================================================
    # Tools 등록
    # ==========================================================================

    # --- Precedent Tools ---
    from apps.ai_service.mcp.tools.precedent_tools import (
        search_precedents,
        get_precedent_details,
        search_with_feedback_filtering,
    )

    @mcp.tool()
    def mcp_search_precedents(query: str, top_k: int = 5, court_filter: Optional[str] = None):
        """판례를 검색합니다.

        Args:
            query: 검색 질의
            top_k: 반환할 결과 수
            court_filter: 법원 필터 (예: "대법원", "헌법재판소")

        Returns:
            검색된 판례 목록
        """
        return search_precedents(query, top_k, court_filter)

    @mcp.tool()
    def mcp_get_precedent_details(case_number: str):
        """판례 상세 정보를 조회합니다.

        Args:
            case_number: 사건번호 (예: "2020도1234")

        Returns:
            판례 상세 정보
        """
        return get_precedent_details(case_number)

    # --- Document Tools ---
    from apps.ai_service.mcp.tools.document_tools import (
        analyze_document,
        extract_clauses,
        summarize_document,
        detect_document_type,
    )

    @mcp.tool()
    async def mcp_analyze_document(content: str, doc_type: str = "unknown"):
        """문서를 분석합니다.

        Args:
            content: 분석할 문서 내용
            doc_type: 문서 타입

        Returns:
            분석 결과
        """
        return await analyze_document(content, doc_type)

    @mcp.tool()
    async def mcp_extract_clauses(content: str):
        """문서에서 조항을 추출합니다.

        Args:
            content: 문서 내용

        Returns:
            추출된 조항 목록
        """
        return await extract_clauses(content)

    @mcp.tool()
    async def mcp_summarize_document(content: str, max_length: int = 500):
        """문서를 요약합니다.

        Args:
            content: 문서 내용
            max_length: 요약 최대 길이

        Returns:
            요약 결과
        """
        return await summarize_document(content, max_length)

    @mcp.tool()
    async def mcp_detect_document_type(content: str):
        """문서 타입을 감지합니다.

        Args:
            content: 문서 내용

        Returns:
            감지된 문서 타입
        """
        return await detect_document_type(content)

    # --- Case Tools ---
    from apps.ai_service.mcp.tools.case_tools import (
        analyze_case,
        extract_parties,
        identify_issues,
        search_related_cases,
        assess_case_complexity,
    )

    @mcp.tool()
    async def mcp_analyze_case(case_content: str, case_type: str = "unknown"):
        """사건을 분석합니다.

        Args:
            case_content: 사건 내용
            case_type: 사건 유형

        Returns:
            사건 분석 결과
        """
        return await analyze_case(case_content, case_type)

    @mcp.tool()
    async def mcp_extract_parties(case_content: str):
        """사건에서 당사자를 추출합니다.

        Args:
            case_content: 사건 내용

        Returns:
            당사자 목록
        """
        return await extract_parties(case_content)

    @mcp.tool()
    async def mcp_identify_issues(case_content: str):
        """사건의 쟁점을 식별합니다.

        Args:
            case_content: 사건 내용

        Returns:
            쟁점 목록
        """
        return await identify_issues(case_content)

    @mcp.tool()
    async def mcp_search_related_cases(query: str, case_type: Optional[str] = None, top_k: int = 5):
        """관련 사건을 검색합니다.

        Args:
            query: 검색 질의
            case_type: 사건 유형 필터
            top_k: 반환할 결과 수

        Returns:
            관련 사건 목록
        """
        return await search_related_cases(query, case_type, top_k)

    @mcp.tool()
    async def mcp_assess_case_complexity(case_content: str):
        """사건 복잡도를 평가합니다.

        Args:
            case_content: 사건 내용

        Returns:
            복잡도 평가 결과
        """
        return await assess_case_complexity(case_content)

    # --- Analysis Tools ---
    from apps.ai_service.mcp.tools.analysis_tools import (
        analyze_risks,
        compare_documents,
        generate_report,
    )

    @mcp.tool()
    async def mcp_analyze_risks(content: str, doc_type: str = "contract"):
        """문서의 리스크를 분석합니다.

        Args:
            content: 문서 내용
            doc_type: 문서 타입

        Returns:
            리스크 목록
        """
        return await analyze_risks(content, doc_type)

    @mcp.tool()
    async def mcp_compare_documents(doc1: str, doc2: str, comparison_type: str = "similarity"):
        """두 문서를 비교합니다.

        Args:
            doc1: 첫 번째 문서
            doc2: 두 번째 문서
            comparison_type: 비교 유형

        Returns:
            비교 결과
        """
        return await compare_documents(doc1, doc2, comparison_type)

    @mcp.tool()
    async def mcp_generate_report(analysis_results: dict, report_type: str = "summary"):
        """분석 결과로 보고서를 생성합니다.

        Args:
            analysis_results: 분석 결과
            report_type: 보고서 유형

        Returns:
            생성된 보고서
        """
        return await generate_report(analysis_results, report_type)

    # --- LLM Tools ---
    from apps.ai_service.mcp.tools.llm_tools import (
        execute_on_model,
        get_model_metadata,
        select_best_model,
    )

    @mcp.tool()
    async def mcp_execute_on_model(model_name: str, task: str, input_data: dict):
        """특정 LLM 모델에서 작업을 실행합니다.

        Args:
            model_name: 모델 이름
            task: 작업 유형
            input_data: 입력 데이터

        Returns:
            실행 결과
        """
        return await execute_on_model(model_name, task, input_data)

    @mcp.tool()
    async def mcp_get_model_metadata(model_name: str):
        """모델 메타데이터를 조회합니다.

        Args:
            model_name: 모델 이름

        Returns:
            모델 메타데이터
        """
        return await get_model_metadata(model_name)

    @mcp.tool()
    async def mcp_select_best_model(metrics: dict, criteria: Optional[dict] = None):
        """최적 모델을 선택합니다.

        Args:
            metrics: 모델별 메트릭
            criteria: 가중치 기준

        Returns:
            선택 결과
        """
        return await select_best_model(metrics, criteria)

    # ==========================================================================
    # Resources 등록
    # ==========================================================================

    from apps.ai_service.mcp.resources.document_resources import (
        get_document_text,
        get_document_metadata,
    )

    @mcp.resource("document://{doc_id}/text")
    def resource_document_text(doc_id: str) -> str:
        """문서 원문을 조회합니다."""
        return get_document_text(doc_id)

    @mcp.resource("document://{doc_id}/metadata")
    def resource_document_metadata(doc_id: str) -> dict:
        """문서 메타데이터를 조회합니다."""
        return get_document_metadata(doc_id)

    @mcp.resource("precedent://{case_number}")
    def resource_precedent(case_number: str) -> str:
        """판례 원문을 조회합니다."""
        return get_precedent_details(case_number)

    logger.info(f"MCP Server '{name}' created with tools and resources")

    return mcp


if __name__ == "__main__":
    server = create_mcp_server()
    if server:
        server.run()
    else:
        print("MCP Server could not be created. Please install fastmcp: pip install fastmcp")
