"""
MCP Server Entry Point

Phase 4 - Week 12~13: FastMCP 기반 MCP 서버

MCP 서버:
- 도구(Tools): 판례 검색, 문서 분석, 사건 분석, LLM 비교, 외부 API
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

    # --- External API Tools (Week 13) ---
    from apps.ai_service.mcp.tools.external_tools import (
        fetch_court_api,
        fetch_statute_api,
        parse_legal_document,
        validate_document_structure,
    )

    @mcp.tool()
    async def mcp_fetch_court_api(
        case_number: Optional[str] = None,
        keyword: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        court: Optional[str] = None,
        page: int = 1,
        display: int = 20,
        fetch_content: bool = True
    ):
        """대법원 판례 API를 호출합니다.

        국가법령정보센터 판례 API를 통해 판례 데이터를 조회합니다.

        Args:
            case_number: 사건번호 (예: "2020도1234")
            keyword: 검색 키워드
            start_date: 선고일자 시작 (YYYY-MM-DD)
            end_date: 선고일자 종료 (YYYY-MM-DD)
            court: 법원명 (예: "대법원")
            page: 페이지 번호 (기본값: 1)
            display: 결과 개수 (기본값: 20, 최대: 100)
            fetch_content: 본문 상세 조회 여부 (기본값: True)

        Returns:
            판례 검색 결과 (success, total_count, precedents, metadata)
        """
        return await fetch_court_api(
            case_number=case_number,
            keyword=keyword,
            start_date=start_date,
            end_date=end_date,
            court=court,
            page=page,
            display=display,
            fetch_content=fetch_content
        )

    @mcp.tool()
    async def mcp_fetch_statute_api(
        law_code: Optional[str] = None,
        keyword: Optional[str] = None,
        law_type: Optional[str] = None,
        ministry: Optional[str] = None,
        page: int = 1,
        display: int = 20,
        fetch_content: bool = False
    ):
        """법령 API를 호출합니다.

        국가법령정보센터 API를 통해 법령 데이터를 조회합니다.

        Args:
            law_code: 법령 MST 코드
            keyword: 검색 키워드
            law_type: 법령 종류 (법률, 시행령, 시행규칙 등)
            ministry: 소관부처
            page: 페이지 번호 (기본값: 1)
            display: 결과 개수 (기본값: 20, 최대: 100)
            fetch_content: 본문 상세 조회 여부 (기본값: False)

        Returns:
            법령 검색 결과 (success, total_count, statutes, metadata)
        """
        return await fetch_statute_api(
            law_code=law_code,
            keyword=keyword,
            law_type=law_type,
            ministry=ministry,
            page=page,
            display=display,
            fetch_content=fetch_content
        )

    @mcp.tool()
    async def mcp_parse_legal_document(content: str, doc_type: str = "unknown"):
        """법률 문서를 파싱합니다.

        법률 문서의 구조를 분석하고 주요 섹션을 추출합니다.

        Args:
            content: 문서 내용 (HTML 또는 텍스트)
            doc_type: 문서 타입 ("precedent", "statute", "contract", "unknown")

        Returns:
            파싱 결과 (success, doc_type, title, sections, metadata)
        """
        return await parse_legal_document(content, doc_type)

    @mcp.tool()
    async def mcp_validate_document_structure(data: dict, doc_type: str = "precedent"):
        """문서 구조를 검증합니다.

        법률 문서가 필수 필드를 포함하고 있는지 검증합니다.

        Args:
            data: 검증할 문서 데이터
            doc_type: 문서 타입 ("precedent", "statute", "contract")

        Returns:
            검증 결과 (valid, doc_type, missing_fields, warnings, metadata)
        """
        return await validate_document_structure(data, doc_type)

    # --- Database Query Tools (사용자 데이터 조회) ---
    from apps.ai_service.mcp.tools.db_tools import (
        query_user_criminal_cases,
        get_criminal_case_detail,
        get_user_case_statistics,
    )

    @mcp.tool()
    async def mcp_query_user_criminal_cases(
        user_id: str,
        order_by: str = "created_at",
        order: str = "desc",
        limit: int = 10,
        offset: int = 0,
        crime_type_filter: Optional[str] = None,
        stage_filter: Optional[str] = None,
    ):
        """사용자의 형사 사건을 유연하게 조회합니다.

        이 도구는 다양한 형사 사건 조회 질문에 대해 적절한 파라미터를 사용하여
        하나의 도구로 여러 유형의 조회를 수행할 수 있습니다.

        Args:
            user_id: 사용자 UUID (필수)
            order_by: 정렬 기준
                - "created_at": 생성일 기준 (기본값)
                - "expected_sentence_score": 예상 형량 점수 기준 (형량 심각도)
                - "case_name": 사건명 기준
                - "crime_type": 범죄 유형 기준
            order: 정렬 순서
                - "desc": 내림차순 (기본값)
                - "asc": 오름차순
            limit: 반환할 결과 수 (기본값: 10)
            offset: 건너뛸 결과 수 (페이지네이션용)
            crime_type_filter: 범죄 유형 필터 (예: "절도", "사기", "폭행")
            stage_filter: 진행 단계 필터 (COMPLAINT, INVESTIGATION, PROSECUTION, TRIAL, JUDGMENT, CLOSED)

        Returns:
            사건 목록과 조회 정보

        사용 예시:
            - "내 형사 사건 목록": order_by="created_at", order="desc"
            - "형량이 가장 적은 사건": order_by="expected_sentence_score", order="asc", limit=1
            - "형량이 가장 높은 사건": order_by="expected_sentence_score", order="desc", limit=1
            - "절도 사건만 보여줘": crime_type_filter="절도"
            - "수사 중인 사건들": stage_filter="INVESTIGATION"
        """
        return await query_user_criminal_cases(
            user_id=user_id,
            order_by=order_by,
            order=order,
            limit=limit,
            offset=offset,
            crime_type_filter=crime_type_filter,
            stage_filter=stage_filter,
        )

    @mcp.tool()
    async def mcp_get_criminal_case_detail(user_id: str, case_id: str):
        """특정 형사 사건의 상세 정보를 조회합니다.

        Args:
            user_id: 사용자 UUID
            case_id: 사건 UUID

        Returns:
            사건 상세 정보 (구성요건, 양형인자, 예상 양형, 변호 전략 등)
        """
        return await get_criminal_case_detail(user_id=user_id, case_id=case_id)

    @mcp.tool()
    async def mcp_get_user_case_statistics(user_id: str):
        """사용자의 형사 사건 통계를 조회합니다.

        전체 사건 수, 단계별/범죄유형별 분포, 양형 통계 등을 제공합니다.

        Args:
            user_id: 사용자 UUID

        Returns:
            사건 통계 정보
        """
        return await get_user_case_statistics(user_id=user_id)

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
