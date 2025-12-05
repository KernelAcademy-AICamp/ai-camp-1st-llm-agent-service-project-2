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
# 형사법 분석 개별 핸들러 (Phase 1: 형사법 특화)
# =============================================================================

async def detect_crime_type_handler(
    case_content: str,
    crime_type: str = None,
) -> Dict[str, Any]:
    """
    범죄 유형 감지 핸들러

    Args:
        case_content: 사건 문서 내용
        crime_type: 사용자 지정 범죄 유형 (선택)

    Returns:
        {
            "success": bool,
            "crime_type": str,
            "crime_category": str,
            "confidence": float
        }
    """
    try:
        from apps.ai_service.workflows.criminal_workflow import detect_crime_node
        from apps.ai_service.workflows.states.criminal_state import CriminalCaseState

        # 초기 상태 생성
        state: CriminalCaseState = {
            "texts": [case_content],
            "filenames": ["input.txt"],
            "user_id": None,
            "case_name": None,
            "input_crime_type": crime_type,
            "summary": None,
            "crime_type": None,
            "crime_category": None,
            "crime_elements": None,
            "sentencing_factors": None,
            "expected_sentence": None,
            "defense_strategies": [],
            "related_precedents": [],
            "analysis_plan": [],
            "completed_tasks": [],
            "error": None,
        }

        # 노드 실행
        result = await detect_crime_node(state)

        return {
            "success": True,
            "crime_type": result.get("crime_type", "미상"),
            "crime_category": result.get("crime_category", "general"),
            "confidence": 0.8 if result.get("crime_type") else 0.3,
        }

    except Exception as e:
        logger.error(f"[detect_crime_type_handler] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "crime_type": None,
            "crime_category": None,
        }


async def analyze_crime_elements_handler(
    case_content: str,
    crime_type: str,
) -> Dict[str, Any]:
    """
    구성요건 분석 핸들러

    Args:
        case_content: 사건 문서 내용
        crime_type: 범죄 유형

    Returns:
        {
            "success": bool,
            "objective": list,
            "subjective": list
        }
    """
    try:
        from apps.ai_service.workflows.criminal_workflow import analyze_elements_node
        from apps.ai_service.workflows.states.criminal_state import (
            CriminalCaseState,
            get_crime_category,
        )

        # 초기 상태 생성
        state: CriminalCaseState = {
            "texts": [case_content],
            "filenames": ["input.txt"],
            "user_id": None,
            "case_name": None,
            "input_crime_type": crime_type,
            "summary": None,
            "crime_type": crime_type,
            "crime_category": get_crime_category(crime_type),
            "crime_elements": None,
            "sentencing_factors": None,
            "expected_sentence": None,
            "defense_strategies": [],
            "related_precedents": [],
            "analysis_plan": ["analyze_elements"],
            "completed_tasks": [],
            "error": None,
        }

        # 노드 실행
        result = await analyze_elements_node(state)
        elements = result.get("crime_elements", {"objective": [], "subjective": []})

        return {
            "success": True,
            "objective": elements.get("objective", []),
            "subjective": elements.get("subjective", []),
        }

    except Exception as e:
        logger.error(f"[analyze_crime_elements_handler] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "objective": [],
            "subjective": [],
        }


async def extract_sentencing_factors_handler(
    case_content: str,
    crime_type: str,
) -> Dict[str, Any]:
    """
    양형인자 추출 핸들러

    Args:
        case_content: 사건 문서 내용
        crime_type: 범죄 유형

    Returns:
        {
            "success": bool,
            "favorable": list,
            "unfavorable": list
        }
    """
    try:
        from apps.ai_service.workflows.criminal_workflow import extract_factors_node
        from apps.ai_service.workflows.states.criminal_state import (
            CriminalCaseState,
            get_crime_category,
        )

        # 초기 상태 생성
        state: CriminalCaseState = {
            "texts": [case_content],
            "filenames": ["input.txt"],
            "user_id": None,
            "case_name": None,
            "input_crime_type": crime_type,
            "summary": None,
            "crime_type": crime_type,
            "crime_category": get_crime_category(crime_type),
            "crime_elements": None,
            "sentencing_factors": None,
            "expected_sentence": None,
            "defense_strategies": [],
            "related_precedents": [],
            "analysis_plan": ["extract_factors"],
            "completed_tasks": [],
            "error": None,
        }

        # 노드 실행
        result = await extract_factors_node(state)
        factors = result.get("sentencing_factors", {"favorable": [], "unfavorable": []})

        return {
            "success": True,
            "favorable": factors.get("favorable", []),
            "unfavorable": factors.get("unfavorable", []),
        }

    except Exception as e:
        logger.error(f"[extract_sentencing_factors_handler] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "favorable": [],
            "unfavorable": [],
        }


async def estimate_sentence_handler(
    crime_type: str,
    sentencing_factors: Dict[str, Any] = None,
    case_content: str = None,
) -> Dict[str, Any]:
    """
    양형 예측 핸들러

    Args:
        crime_type: 범죄 유형
        sentencing_factors: 양형인자 (선택, 없으면 자동 추출)
        case_content: 사건 문서 내용 (양형인자가 없을 경우 사용)

    Returns:
        {
            "success": bool,
            "range": str,
            "suspended_probability": float,
            "reasoning": str
        }
    """
    try:
        from apps.ai_service.workflows.criminal_workflow import (
            estimate_sentence_node,
            extract_factors_node,
        )
        from apps.ai_service.workflows.states.criminal_state import (
            CriminalCaseState,
            get_crime_category,
        )

        # 양형인자가 없고 case_content가 있으면 먼저 추출
        if not sentencing_factors and case_content:
            factors_state: CriminalCaseState = {
                "texts": [case_content],
                "filenames": ["input.txt"],
                "user_id": None,
                "case_name": None,
                "input_crime_type": crime_type,
                "summary": None,
                "crime_type": crime_type,
                "crime_category": get_crime_category(crime_type),
                "crime_elements": None,
                "sentencing_factors": None,
                "expected_sentence": None,
                "defense_strategies": [],
                "related_precedents": [],
                "analysis_plan": ["extract_factors"],
                "completed_tasks": [],
                "error": None,
            }
            factors_result = await extract_factors_node(factors_state)
            sentencing_factors = factors_result.get("sentencing_factors", {"favorable": [], "unfavorable": []})

        # 기본 양형인자
        if not sentencing_factors:
            sentencing_factors = {"favorable": [], "unfavorable": []}

        # 초기 상태 생성
        state: CriminalCaseState = {
            "texts": [case_content] if case_content else [],
            "filenames": ["input.txt"],
            "user_id": None,
            "case_name": None,
            "input_crime_type": crime_type,
            "summary": None,
            "crime_type": crime_type,
            "crime_category": get_crime_category(crime_type),
            "crime_elements": None,
            "sentencing_factors": sentencing_factors,
            "expected_sentence": None,
            "defense_strategies": [],
            "related_precedents": [],
            "analysis_plan": ["estimate_sentence"],
            "completed_tasks": [],
            "error": None,
        }

        # 노드 실행
        result = await estimate_sentence_node(state)
        sentence = result.get("expected_sentence", {})

        return {
            "success": True,
            "range": sentence.get("range", "판단 필요"),
            "suspended_probability": sentence.get("suspended_probability", 0.5),
            "reasoning": sentence.get("reasoning", ""),
        }

    except Exception as e:
        logger.error(f"[estimate_sentence_handler] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "range": None,
            "suspended_probability": None,
            "reasoning": None,
        }


async def suggest_defense_strategies_handler(
    crime_type: str,
    crime_elements: Dict[str, Any] = None,
    sentencing_factors: Dict[str, Any] = None,
    case_content: str = None,
) -> Dict[str, Any]:
    """
    변호 전략 제안 핸들러

    Args:
        crime_type: 범죄 유형
        crime_elements: 구성요건 분석 결과 (선택)
        sentencing_factors: 양형인자 (선택)
        case_content: 사건 문서 내용 (선택, 자동 분석용)

    Returns:
        {
            "success": bool,
            "strategies": list
        }
    """
    try:
        from apps.ai_service.workflows.criminal_workflow import (
            suggest_defense_node,
            analyze_elements_node,
            extract_factors_node,
        )
        from apps.ai_service.workflows.states.criminal_state import (
            CriminalCaseState,
            get_crime_category,
        )

        # 구성요건이나 양형인자가 없고 case_content가 있으면 먼저 분석
        if case_content and (not crime_elements or not sentencing_factors):
            base_state: CriminalCaseState = {
                "texts": [case_content],
                "filenames": ["input.txt"],
                "user_id": None,
                "case_name": None,
                "input_crime_type": crime_type,
                "summary": None,
                "crime_type": crime_type,
                "crime_category": get_crime_category(crime_type),
                "crime_elements": None,
                "sentencing_factors": None,
                "expected_sentence": None,
                "defense_strategies": [],
                "related_precedents": [],
                "analysis_plan": [],
                "completed_tasks": [],
                "error": None,
            }

            if not crime_elements:
                elements_result = await analyze_elements_node(base_state)
                crime_elements = elements_result.get("crime_elements", {"objective": [], "subjective": []})

            if not sentencing_factors:
                factors_result = await extract_factors_node(base_state)
                sentencing_factors = factors_result.get("sentencing_factors", {"favorable": [], "unfavorable": []})

        # 기본값 설정
        if not crime_elements:
            crime_elements = {"objective": [], "subjective": []}
        if not sentencing_factors:
            sentencing_factors = {"favorable": [], "unfavorable": []}

        # 초기 상태 생성
        state: CriminalCaseState = {
            "texts": [case_content] if case_content else [],
            "filenames": ["input.txt"],
            "user_id": None,
            "case_name": None,
            "input_crime_type": crime_type,
            "summary": None,
            "crime_type": crime_type,
            "crime_category": get_crime_category(crime_type),
            "crime_elements": crime_elements,
            "sentencing_factors": sentencing_factors,
            "expected_sentence": None,
            "defense_strategies": [],
            "related_precedents": [],
            "analysis_plan": ["suggest_defense"],
            "completed_tasks": [],
            "error": None,
        }

        # 노드 실행
        result = await suggest_defense_node(state)

        return {
            "success": True,
            "strategies": result.get("defense_strategies", []),
        }

    except Exception as e:
        logger.error(f"[suggest_defense_strategies_handler] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "strategies": [],
        }


async def search_criminal_precedents_handler(
    crime_type: str,
    keywords: List[str] = None,
    case_content: str = None,
) -> Dict[str, Any]:
    """
    형사 판례 검색 핸들러

    Args:
        crime_type: 범죄 유형
        keywords: 검색 키워드 (선택)
        case_content: 사건 문서 내용 (선택, 자동 키워드 추출용)

    Returns:
        {
            "success": bool,
            "precedents": list,
            "total_count": int
        }
    """
    try:
        from apps.ai_service.workflows.criminal_workflow import search_precedents_node
        from apps.ai_service.workflows.states.criminal_state import (
            CriminalCaseState,
            get_crime_category,
        )

        # 키워드가 없으면 범죄 유형 기반으로 생성
        if not keywords:
            keywords = [crime_type]

        # 구성요건 정보 (키워드에서 생성)
        crime_elements = {
            "objective": [{"element": kw, "description": "", "fulfilled": True} for kw in keywords],
            "subjective": [],
        }

        # 초기 상태 생성
        state: CriminalCaseState = {
            "texts": [case_content] if case_content else [],
            "filenames": ["input.txt"],
            "user_id": None,
            "case_name": None,
            "input_crime_type": crime_type,
            "summary": None,
            "crime_type": crime_type,
            "crime_category": get_crime_category(crime_type),
            "crime_elements": crime_elements,
            "sentencing_factors": None,
            "expected_sentence": None,
            "defense_strategies": [],
            "related_precedents": [],
            "analysis_plan": ["search_precedents"],
            "completed_tasks": [],
            "error": None,
        }

        # 노드 실행
        result = await search_precedents_node(state)
        precedents = result.get("related_precedents", [])

        return {
            "success": True,
            "precedents": precedents,
            "total_count": len(precedents),
        }

    except Exception as e:
        logger.error(f"[search_criminal_precedents_handler] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "precedents": [],
            "total_count": 0,
        }


# =============================================================================
# 사용자 문서 검색 핸들러
# =============================================================================

async def search_user_documents_handler(
    query: str,
    document_id: str = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    사용자가 업로드한 문서에서 검색

    Args:
        query: 검색 쿼리
        document_id: 특정 문서 ID로 필터링 (선택)
        top_k: 반환할 결과 수

    Returns:
        {
            "success": bool,
            "chunks": [{"text": str, "score": float, "metadata": dict}, ...],
            "total_count": int
        }
    """
    try:
        from main import app

        document_indexer = getattr(app.state, 'document_indexer', None)
        if not document_indexer:
            logger.warning("[search_user_documents] DocumentIndexer not available")
            return {
                "success": False,
                "error": "DocumentIndexer not initialized",
                "chunks": [],
                "total_count": 0
            }

        # 검색 수행
        results = document_indexer.search_similar_chunks(
            query=query,
            top_k=top_k,
            document_id=document_id
        )

        # 결과 포맷팅
        chunks = []
        for result in results:
            chunks.append({
                "text": result.get("text", ""),
                "score": result.get("score", 0.0),
                "metadata": result.get("metadata", {}),
            })

        logger.info(f"[search_user_documents] Found {len(chunks)} chunks for query: {query[:50]}...")
        return {
            "success": True,
            "chunks": chunks,
            "total_count": len(chunks)
        }

    except Exception as e:
        logger.error(f"[search_user_documents] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "chunks": [],
            "total_count": 0
        }


# =============================================================================
# 사용자 문서 목록 조회 핸들러 (Agent Hub 연동)
# =============================================================================

async def list_user_documents_handler(
    user_id: str,
    doc_type: str = None,
    search: str = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    사용자가 업로드한 문서 목록 조회

    Args:
        user_id: 사용자 UUID
        doc_type: 문서 유형 필터 (CASE, CONTRACT, STATUTE, PRECEDENT, OTHER)
        search: 제목 검색어
        limit: 반환할 결과 수

    Returns:
        {
            "success": bool,
            "count": int,
            "documents": [
                {
                    "id": str,
                    "title": str,
                    "doc_type": str,
                    "status": str,
                    "analysis_status": str,
                    "created_at": str
                }
            ]
        }
    """
    try:
        from apps.ai_service.clients.django_client import get_django_client

        client = get_django_client()
        result = await client.list_documents(
            user_id=user_id,
            doc_type=doc_type,
            search=search,
            limit=limit,
        )

        if result["success"]:
            # 문서 정보 간략화
            documents = []
            for doc in result.get("documents", []):
                documents.append({
                    "id": doc.get("id"),
                    "title": doc.get("title"),
                    "doc_type": doc.get("doc_type"),
                    "doc_type_display": doc.get("doc_type_display", doc.get("doc_type")),
                    "status": doc.get("status"),
                    "analysis_status": doc.get("analysis_status"),
                    "created_at": doc.get("created_at"),
                })

            logger.info(f"[list_user_documents] Found {len(documents)} documents for user {user_id}")
            return {
                "success": True,
                "count": result.get("count", len(documents)),
                "documents": documents,
            }
        else:
            return result

    except Exception as e:
        logger.error(f"[list_user_documents] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "documents": [],
        }


async def get_document_analysis_handler(
    document_id: str,
    user_id: str,
    analysis_type: str = "all",
) -> Dict[str, Any]:
    """
    문서 분석 결과 조회

    Args:
        document_id: 문서 UUID
        user_id: 사용자 UUID
        analysis_type: 조회할 분석 유형 (summary, risk, case, all)

    Returns:
        {
            "success": bool,
            "document_title": str,
            "summary": {...},
            "risk_analysis": {...},
            "case_analysis": {...}
        }
    """
    try:
        from apps.ai_service.clients.django_client import get_django_client

        client = get_django_client()
        result = {
            "success": True,
            "document_id": document_id,
        }

        # 문서 기본 정보 조회
        doc_result = await client.get_document(document_id, user_id)
        if doc_result["success"]:
            result["document_title"] = doc_result["document"].get("title")
            result["doc_type"] = doc_result["document"].get("doc_type")
        else:
            return {
                "success": False,
                "error": doc_result.get("error", "문서를 찾을 수 없습니다"),
            }

        # 요약 조회
        if analysis_type in ["summary", "all"]:
            summary_result = await client.get_document_summary(document_id, user_id)
            result["summary"] = summary_result.get("summary")

        # 리스크 분석 조회
        if analysis_type in ["risk", "all"]:
            risk_result = await client.get_document_risk_analysis(document_id, user_id)
            result["risk_analysis"] = risk_result.get("risk_analysis")

        # 사건 분석 조회
        if analysis_type in ["case", "all"]:
            case_result = await client.get_document_case_analysis(document_id, user_id)
            result["case_analysis"] = case_result.get("case_analysis")

        logger.info(f"[get_document_analysis] Retrieved analysis for document {document_id}")
        return result

    except Exception as e:
        logger.error(f"[get_document_analysis] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def list_documents_with_risk_handler(
    user_id: str,
    severity: str = None,
    sort_by: str = "risk_score",
    order: str = "desc",
    limit: int = 10,
) -> Dict[str, Any]:
    """
    리스크 분석이 있는 문서 목록 조회 (정렬 가능)

    Args:
        user_id: 사용자 UUID
        severity: 심각도 필터 (CRITICAL, HIGH, MEDIUM, LOW, INFO)
        sort_by: 정렬 기준 (risk_score, created_at, title)
        order: 정렬 순서 (asc, desc)
        limit: 결과 수 제한

    Returns:
        {
            "success": bool,
            "count": int,
            "documents": [
                {
                    "document": {...},
                    "risk_analysis": {...}
                }
            ]
        }
    """
    try:
        from apps.ai_service.clients.django_client import get_django_client

        client = get_django_client()
        result = await client.list_documents_with_risk(
            user_id=user_id,
            severity=severity,
            sort_by=sort_by,
            order=order,
            limit=limit,
        )

        if result["success"]:
            logger.info(f"[list_documents_with_risk] Found {result.get('count', 0)} documents with risk for user {user_id}")

        return result

    except Exception as e:
        logger.error(f"[list_documents_with_risk] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "documents": [],
        }


async def get_risk_overview_handler(
    user_id: str,
) -> Dict[str, Any]:
    """
    사용자의 리스크 분석 통계 개요 조회

    Args:
        user_id: 사용자 UUID

    Returns:
        {
            "success": bool,
            "total_documents": int,
            "documents_with_risk": int,
            "avg_risk_score": float,
            "high_risk_count": int,
            "severity_distribution": {...}
        }
    """
    try:
        from apps.ai_service.clients.django_client import get_django_client

        client = get_django_client()
        result = await client.get_risk_overview(user_id)

        if result["success"]:
            logger.info(f"[get_risk_overview] Retrieved risk overview for user {user_id}")

        return result

    except Exception as e:
        logger.error(f"[get_risk_overview] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def list_user_criminal_cases_handler(
    user_id: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    사용자의 형사 사건 목록 조회

    Args:
        user_id: 사용자 UUID
        limit: 결과 수 제한

    Returns:
        {
            "success": bool,
            "count": int,
            "cases": [
                {
                    "id": str,
                    "case_name": str,
                    "crime_type": str,
                    "summary": str,
                    "expected_sentence": {...},
                    "created_at": str
                }
            ]
        }
    """
    try:
        from apps.ai_service.clients.django_client import get_django_client

        client = get_django_client()
        result = await client.list_criminal_cases(user_id=user_id, limit=limit)

        if result["success"]:
            logger.info(f"[list_user_criminal_cases] Found {result.get('count', 0)} cases for user {user_id}")

        return result

    except Exception as e:
        logger.error(f"[list_user_criminal_cases] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "cases": [],
        }


async def get_criminal_case_highest_sentence_handler(
    user_id: str,
) -> Dict[str, Any]:
    """
    예상 양형이 가장 높은 형사 사건 조회

    Args:
        user_id: 사용자 UUID

    Returns:
        {
            "success": bool,
            "case": {...},
            "reason": str
        }
    """
    try:
        from apps.ai_service.clients.django_client import get_django_client

        client = get_django_client()
        result = await client.get_criminal_case_with_highest_sentence(user_id)

        if result["success"]:
            logger.info(f"[get_criminal_case_highest_sentence] Found case for user {user_id}")

        return result

    except Exception as e:
        logger.error(f"[get_criminal_case_highest_sentence] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "case": None,
        }


async def query_user_criminal_cases_handler(
    user_id: str,
    order_by: str = "created_at",
    order: str = "desc",
    limit: int = 10,
    offset: int = 0,
    crime_type_filter: Optional[str] = None,
    stage_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    사용자의 형사 사건을 유연하게 조회하는 범용 핸들러

    이 핸들러를 통해 다양한 질문에 대응할 수 있습니다:
    - "내 사건 목록 보여줘" → order_by="created_at"
    - "형량이 가장 적은 사건" → order_by="expected_sentence_score", order="asc", limit=1
    - "형량이 가장 높은 사건" → order_by="expected_sentence_score", order="desc", limit=1
    - "절도 사건만 보여줘" → crime_type_filter="절도"
    """
    try:
        from apps.ai_service.mcp.tools.db_tools import query_user_criminal_cases

        result = await query_user_criminal_cases(
            user_id=user_id,
            order_by=order_by,
            order=order,
            limit=limit,
            offset=offset,
            crime_type_filter=crime_type_filter,
            stage_filter=stage_filter,
        )

        if result["success"]:
            logger.info(f"[query_user_criminal_cases] Found {result.get('count', 0)} cases for user {user_id}")

        return result

    except Exception as e:
        logger.error(f"[query_user_criminal_cases] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "cases": [],
        }


async def get_criminal_case_detail_handler(
    user_id: str,
    case_id: str,
) -> Dict[str, Any]:
    """특정 형사 사건의 상세 정보 조회 핸들러"""
    try:
        from apps.ai_service.mcp.tools.db_tools import get_criminal_case_detail

        result = await get_criminal_case_detail(user_id=user_id, case_id=case_id)

        if result["success"]:
            logger.info(f"[get_criminal_case_detail] Found case {case_id} for user {user_id}")

        return result

    except Exception as e:
        logger.error(f"[get_criminal_case_detail] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "case": None,
        }


async def get_user_case_statistics_handler(
    user_id: str,
) -> Dict[str, Any]:
    """사용자 사건 통계 조회 핸들러"""
    try:
        from apps.ai_service.mcp.tools.db_tools import get_user_case_statistics

        result = await get_user_case_statistics(user_id=user_id)

        if result["success"]:
            logger.info(f"[get_user_case_statistics] Got statistics for user {user_id}")

        return result

    except Exception as e:
        logger.error(f"[get_user_case_statistics] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "statistics": None,
        }


# =============================================================================
# MCP 도구 핸들러 (Phase 7: LLM Native Tool Use 확장)
# =============================================================================

async def get_precedent_details_handler(
    case_number: str,
) -> Dict[str, Any]:
    """판례 상세 조회 핸들러"""
    try:
        from apps.ai_service.mcp.tools.precedent_tools import get_precedent_details

        result = get_precedent_details(case_number)

        if result.get("success", True):
            logger.info(f"[get_precedent_details] Found precedent: {case_number}")

        return result

    except Exception as e:
        logger.error(f"[get_precedent_details] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def extract_clauses_handler(
    content: str,
) -> Dict[str, Any]:
    """조항 추출 핸들러"""
    try:
        from apps.ai_service.mcp.tools.document_tools import extract_clauses

        result = await extract_clauses(content)

        logger.info(f"[extract_clauses] Extracted clauses from document")
        return result

    except Exception as e:
        logger.error(f"[extract_clauses] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "clauses": [],
        }


async def summarize_document_handler(
    content: str,
    max_length: int = 500,
) -> Dict[str, Any]:
    """문서 요약 핸들러"""
    try:
        from apps.ai_service.mcp.tools.document_tools import summarize_document

        result = await summarize_document(content, max_length)

        logger.info(f"[summarize_document] Summarized document")
        return result

    except Exception as e:
        logger.error(f"[summarize_document] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "summary": None,
        }


async def detect_document_type_handler(
    content: str,
) -> Dict[str, Any]:
    """문서 타입 감지 핸들러"""
    try:
        from apps.ai_service.mcp.tools.document_tools import detect_document_type

        result = await detect_document_type(content)

        logger.info(f"[detect_document_type] Detected type: {result.get('doc_type', 'unknown')}")
        return result

    except Exception as e:
        logger.error(f"[detect_document_type] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "doc_type": "unknown",
        }


async def extract_parties_handler(
    case_content: str,
) -> Dict[str, Any]:
    """당사자 추출 핸들러"""
    try:
        from apps.ai_service.mcp.tools.case_tools import extract_parties

        result = await extract_parties(case_content)

        logger.info(f"[extract_parties] Extracted parties")
        return result

    except Exception as e:
        logger.error(f"[extract_parties] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "parties": [],
        }


async def identify_issues_handler(
    case_content: str,
) -> Dict[str, Any]:
    """쟁점 식별 핸들러"""
    try:
        from apps.ai_service.mcp.tools.case_tools import identify_issues

        result = await identify_issues(case_content)

        logger.info(f"[identify_issues] Identified issues")
        return result

    except Exception as e:
        logger.error(f"[identify_issues] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "issues": [],
        }


async def search_related_cases_handler(
    query: str,
    case_type: Optional[str] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """관련 사건 검색 핸들러"""
    try:
        from apps.ai_service.mcp.tools.case_tools import search_related_cases

        result = await search_related_cases(query, case_type, top_k)

        logger.info(f"[search_related_cases] Found {len(result.get('cases', []))} related cases")
        return result

    except Exception as e:
        logger.error(f"[search_related_cases] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "cases": [],
        }


async def assess_case_complexity_handler(
    case_content: str,
) -> Dict[str, Any]:
    """사건 복잡도 평가 핸들러"""
    try:
        from apps.ai_service.mcp.tools.case_tools import assess_case_complexity

        result = await assess_case_complexity(case_content)

        logger.info(f"[assess_case_complexity] Assessed complexity: {result.get('complexity_level', 'unknown')}")
        return result

    except Exception as e:
        logger.error(f"[assess_case_complexity] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "complexity_level": "unknown",
        }


async def analyze_risks_handler(
    content: str,
    doc_type: str = "contract",
) -> Dict[str, Any]:
    """리스크 분석 핸들러"""
    try:
        from apps.ai_service.mcp.tools.analysis_tools import analyze_risks

        result = await analyze_risks(content, doc_type)

        logger.info(f"[analyze_risks] Analyzed risks")
        return result

    except Exception as e:
        logger.error(f"[analyze_risks] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "risks": [],
        }


async def compare_documents_handler(
    doc1: str,
    doc2: str,
    comparison_type: str = "similarity",
) -> Dict[str, Any]:
    """문서 비교 핸들러"""
    try:
        from apps.ai_service.mcp.tools.analysis_tools import compare_documents

        result = await compare_documents(doc1, doc2, comparison_type)

        logger.info(f"[compare_documents] Compared documents")
        return result

    except Exception as e:
        logger.error(f"[compare_documents] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def generate_report_handler(
    analysis_results: Dict[str, Any],
    report_type: str = "summary",
) -> Dict[str, Any]:
    """보고서 생성 핸들러"""
    try:
        from apps.ai_service.mcp.tools.analysis_tools import generate_report

        result = await generate_report(analysis_results, report_type)

        logger.info(f"[generate_report] Generated {report_type} report")
        return result

    except Exception as e:
        logger.error(f"[generate_report] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "report": None,
        }


async def fetch_court_api_handler(
    case_number: Optional[str] = None,
    keyword: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    court: Optional[str] = None,
    page: int = 1,
    display: int = 20,
) -> Dict[str, Any]:
    """대법원 판례 API 호출 핸들러"""
    try:
        from apps.ai_service.mcp.tools.external_tools import fetch_court_api

        result = await fetch_court_api(
            case_number=case_number,
            keyword=keyword,
            start_date=start_date,
            end_date=end_date,
            court=court,
            page=page,
            display=display,
        )

        logger.info(f"[fetch_court_api] Fetched {result.get('total_count', 0)} precedents")
        return result

    except Exception as e:
        logger.error(f"[fetch_court_api] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "precedents": [],
        }


async def fetch_statute_api_handler(
    law_code: Optional[str] = None,
    keyword: Optional[str] = None,
    law_type: Optional[str] = None,
    ministry: Optional[str] = None,
    page: int = 1,
    display: int = 20,
) -> Dict[str, Any]:
    """법령 API 호출 핸들러"""
    try:
        from apps.ai_service.mcp.tools.external_tools import fetch_statute_api

        result = await fetch_statute_api(
            law_code=law_code,
            keyword=keyword,
            law_type=law_type,
            ministry=ministry,
            page=page,
            display=display,
        )

        logger.info(f"[fetch_statute_api] Fetched {result.get('total_count', 0)} statutes")
        return result

    except Exception as e:
        logger.error(f"[fetch_statute_api] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "statutes": [],
        }


async def parse_legal_document_handler(
    content: str,
    doc_type: str = "unknown",
) -> Dict[str, Any]:
    """법률 문서 파싱 핸들러"""
    try:
        from apps.ai_service.mcp.tools.external_tools import parse_legal_document

        result = await parse_legal_document(content, doc_type)

        logger.info(f"[parse_legal_document] Parsed document")
        return result

    except Exception as e:
        logger.error(f"[parse_legal_document] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def validate_document_structure_handler(
    data: Dict[str, Any],
    doc_type: str = "precedent",
) -> Dict[str, Any]:
    """문서 구조 검증 핸들러"""
    try:
        from apps.ai_service.mcp.tools.external_tools import validate_document_structure

        result = await validate_document_structure(data, doc_type)

        logger.info(f"[validate_document_structure] Validated: {result.get('valid', False)}")
        return result

    except Exception as e:
        logger.error(f"[validate_document_structure] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "valid": False,
        }


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
    "search_criminal_precedents": "rag_workflow",  # Phase 1: 형사법 특화
    "search_user_documents": None,  # 사용자 문서 검색 (외부 핸들러 사용)

    # 분석 도구
    "analyze_document": "document_workflow",
    "analyze_case": "case_workflow",
    "assess_risk": "risk_workflow",
    "analyze_contract": "document_workflow",

    # 형사법 분석 도구 (Phase 1: 형사법 특화)
    "analyze_criminal_case": "criminal_workflow",
    "detect_crime_type": "criminal_workflow",
    "analyze_crime_elements": "criminal_workflow",
    "extract_sentencing_factors": "criminal_workflow",
    "estimate_sentence": "criminal_workflow",
    "suggest_defense_strategies": "criminal_workflow",

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
            ToolDefinition(
                name="search_user_documents",
                description="내 문서 검색. 사용자가 업로드한 문서에서 관련 내용을 검색합니다.",
                workflow_name=None,  # 외부 핸들러 사용
                input_schema={"query": "str", "document_id": "str (optional)", "top_k": "int"},
                output_schema={"chunks": "list", "scores": "list"},
                category=ToolCategory.SEARCH,
                estimated_tokens=300,
                timeout=30.0,
                is_external_api=True,  # 외부 핸들러로 처리
                external_handler=search_user_documents_handler,
            ),
            # 사용자 문서 목록 및 분석 조회 도구 (Django 백엔드 연동)
            ToolDefinition(
                name="list_user_documents",
                description="내 문서 목록 조회. 사용자가 업로드한 문서 목록을 조회합니다. '내 문서 목록이 뭐야?', '업로드한 문서 보여줘' 등의 질문에 사용합니다.",
                workflow_name=None,
                input_schema={
                    "user_id": "str (사용자 UUID, 필수)",
                    "doc_type": "str (optional, CASE/CONTRACT/STATUTE/PRECEDENT/OTHER)",
                    "search": "str (optional, 제목 검색어)",
                    "limit": "int (default: 10)",
                },
                output_schema={
                    "success": "bool",
                    "count": "int",
                    "documents": "list (id, title, doc_type, status, analysis_status, created_at)",
                },
                category=ToolCategory.SEARCH,
                estimated_tokens=200,
                timeout=30.0,
                is_external_api=True,
                external_handler=list_user_documents_handler,
            ),
            ToolDefinition(
                name="get_document_analysis",
                description="문서 분석 결과 조회. 특정 문서의 요약, 리스크 분석, 사건 분석 결과를 조회합니다. '이 문서 분석해줘', '문서 요약 보여줘' 등의 질문에 사용합니다.",
                workflow_name=None,
                input_schema={
                    "document_id": "str (문서 UUID, 필수)",
                    "user_id": "str (사용자 UUID, 필수)",
                    "analysis_type": "str (optional, summary/risk/case/all, default: all)",
                },
                output_schema={
                    "success": "bool",
                    "document_title": "str",
                    "summary": "dict (요약 정보)",
                    "risk_analysis": "dict (리스크 분석)",
                    "case_analysis": "dict (사건 분석)",
                },
                category=ToolCategory.ANALYSIS,
                estimated_tokens=500,
                timeout=45.0,
                is_external_api=True,
                external_handler=get_document_analysis_handler,
            ),
            ToolDefinition(
                name="list_documents_with_risk",
                description="리스크가 있는 문서 목록 조회. 리스크 분석이 완료된 문서를 리스크 점수순으로 조회합니다. '위험한 문서 보여줘', '리스크 높은 문서는?' 등의 질문에 사용합니다.",
                workflow_name=None,
                input_schema={
                    "user_id": "str (사용자 UUID, 필수)",
                    "severity": "str (optional, CRITICAL/HIGH/MEDIUM/LOW/INFO)",
                    "sort_by": "str (optional, risk_score/created_at/title, default: risk_score)",
                    "order": "str (optional, asc/desc, default: desc)",
                    "limit": "int (default: 10)",
                },
                output_schema={
                    "success": "bool",
                    "count": "int",
                    "documents": "list (document + risk_analysis)",
                },
                category=ToolCategory.SEARCH,
                estimated_tokens=300,
                timeout=30.0,
                is_external_api=True,
                external_handler=list_documents_with_risk_handler,
            ),
            ToolDefinition(
                name="get_risk_overview",
                description="리스크 통계 개요 조회. 사용자의 전체 문서에 대한 리스크 통계를 조회합니다. '내 문서들의 리스크 현황은?', '위험도 분포 보여줘' 등의 질문에 사용합니다.",
                workflow_name=None,
                input_schema={
                    "user_id": "str (사용자 UUID, 필수)",
                },
                output_schema={
                    "success": "bool",
                    "total_documents": "int",
                    "documents_with_risk": "int",
                    "avg_risk_score": "float",
                    "high_risk_count": "int",
                    "severity_distribution": "dict",
                },
                category=ToolCategory.ANALYSIS,
                estimated_tokens=200,
                timeout=30.0,
                is_external_api=True,
                external_handler=get_risk_overview_handler,
            ),
            # ================================================================
            # 범용 사건 조회 도구 (MCP DB Tool)
            # 하나의 도구로 다양한 사건 조회 질문을 처리합니다.
            # ================================================================
            ToolDefinition(
                name="query_user_criminal_cases",
                description="""사용자의 형사 사건을 유연하게 조회합니다. 이 도구 하나로 다양한 질문에 대응할 수 있습니다.

사용 예시:
- "내 형사 사건 목록" → order_by="created_at", order="desc"
- "형량이 가장 적은 사건" → order_by="expected_sentence_score", order="asc", limit=1
- "형량이 가장 높은 사건" → order_by="expected_sentence_score", order="desc", limit=1
- "절도 사건만 보여줘" → crime_type_filter="절도"
- "수사 중인 사건들" → stage_filter="INVESTIGATION"
- "가장 최근 사건" → order_by="created_at", order="desc", limit=1

정렬 기준(order_by):
- created_at: 생성일 기준
- expected_sentence_score: 예상 형량 점수 (높을수록 심각)
- case_name: 사건명
- crime_type: 범죄 유형

진행 단계(stage_filter): COMPLAINT, INVESTIGATION, PROSECUTION, TRIAL, JUDGMENT, CLOSED""",
                workflow_name=None,
                input_schema={
                    "user_id": "str (사용자 UUID, 필수)",
                    "order_by": "str (정렬 기준: created_at|expected_sentence_score|case_name|crime_type, 기본값: created_at)",
                    "order": "str (정렬 순서: asc|desc, 기본값: desc)",
                    "limit": "int (결과 수 제한, 기본값: 10)",
                    "offset": "int (건너뛸 결과 수, 기본값: 0)",
                    "crime_type_filter": "str (범죄 유형 필터, 선택)",
                    "stage_filter": "str (진행 단계 필터, 선택)",
                },
                output_schema={
                    "success": "bool",
                    "count": "int (반환된 결과 수)",
                    "total": "int (전체 결과 수)",
                    "cases": "list (id, case_name, crime_type, summary, stage, expected_sentence, expected_sentence_score, created_at)",
                    "query_info": "dict (적용된 정렬/필터 정보)",
                },
                category=ToolCategory.SEARCH,
                estimated_tokens=400,
                timeout=30.0,
                is_external_api=True,
                external_handler=query_user_criminal_cases_handler,
            ),
            ToolDefinition(
                name="get_criminal_case_detail",
                description="특정 형사 사건의 상세 정보를 조회합니다. 사건 ID를 알고 있을 때 구성요건, 양형인자, 예상 양형, 변호 전략 등 전체 정보를 가져옵니다.",
                workflow_name=None,
                input_schema={
                    "user_id": "str (사용자 UUID, 필수)",
                    "case_id": "str (사건 UUID, 필수)",
                },
                output_schema={
                    "success": "bool",
                    "case": "dict (전체 사건 정보)",
                },
                category=ToolCategory.SEARCH,
                estimated_tokens=500,
                timeout=30.0,
                is_external_api=True,
                external_handler=get_criminal_case_detail_handler,
            ),
            ToolDefinition(
                name="get_user_case_statistics",
                description="사용자의 형사 사건 통계를 조회합니다. 전체 사건 수, 단계별/범죄유형별 분포, 양형 통계 (가장 높은/낮은 형량 사건) 등을 제공합니다. '내 사건들 통계', '사건 현황 요약' 등의 질문에 사용합니다.",
                workflow_name=None,
                input_schema={
                    "user_id": "str (사용자 UUID, 필수)",
                },
                output_schema={
                    "success": "bool",
                    "statistics": "dict (total_cases, by_stage, by_crime_type, sentence_summary)",
                },
                category=ToolCategory.ANALYSIS,
                estimated_tokens=300,
                timeout=30.0,
                is_external_api=True,
                external_handler=get_user_case_statistics_handler,
            ),
            # 기존 도구 유지 (하위 호환성)
            ToolDefinition(
                name="list_user_criminal_cases",
                description="[레거시] 내 형사 사건 목록 조회. query_user_criminal_cases를 사용하세요.",
                workflow_name=None,
                input_schema={
                    "user_id": "str (사용자 UUID, 필수)",
                    "limit": "int (default: 10)",
                },
                output_schema={
                    "success": "bool",
                    "count": "int",
                    "cases": "list",
                },
                category=ToolCategory.SEARCH,
                estimated_tokens=300,
                timeout=30.0,
                is_external_api=True,
                external_handler=list_user_criminal_cases_handler,
            ),
            ToolDefinition(
                name="get_criminal_case_highest_sentence",
                description="[레거시] 예상 양형이 가장 높은 형사 사건 조회. query_user_criminal_cases(order_by='expected_sentence_score', order='desc', limit=1)를 사용하세요.",
                workflow_name=None,
                input_schema={
                    "user_id": "str (사용자 UUID, 필수)",
                },
                output_schema={
                    "success": "bool",
                    "case": "dict",
                    "reason": "str",
                },
                category=ToolCategory.ANALYSIS,
                estimated_tokens=300,
                timeout=30.0,
                is_external_api=True,
                external_handler=get_criminal_case_highest_sentence_handler,
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

            # 형사법 분석 도구 (Phase 1: 형사법 특화)
            # 전체 워크플로우 실행 (모든 분석 단계 수행)
            ToolDefinition(
                name="analyze_criminal_case",
                description="형사 사건 종합 분석. 범죄 유형 감지, 구성요건 분석, 양형인자 추출, 양형 예측, 변호 전략 제안을 모두 수행합니다. 전체 분석이 필요할 때 사용하세요.",
                workflow_name="criminal_workflow",
                input_schema={
                    "case_content": "str",
                    "crime_type": "str (optional)",
                },
                output_schema={
                    "summary": "str",
                    "crime_type": "str",
                    "crime_elements": "dict",
                    "sentencing_factors": "dict",
                    "expected_sentence": "dict",
                    "defense_strategies": "list",
                    "related_precedents": "list",
                },
                category=ToolCategory.ANALYSIS,
                estimated_tokens=2000,
                timeout=120.0,
                requires_context=True,
            ),
            # 개별 분석 도구들 (external_handler 사용)
            ToolDefinition(
                name="detect_crime_type",
                description="범죄 유형 감지. 사건 내용에서 범죄 유형(절도, 사기, 폭행 등)을 자동으로 감지합니다. 범죄 유형만 알고 싶을 때 사용하세요.",
                workflow_name=None,  # 개별 핸들러 사용
                input_schema={
                    "case_content": "str (사건 문서 내용)",
                    "crime_type": "str (optional, 사용자 지정 범죄 유형)",
                },
                output_schema={
                    "crime_type": "str",
                    "crime_category": "str",
                    "confidence": "float",
                },
                category=ToolCategory.ANALYSIS,
                estimated_tokens=500,
                timeout=30.0,
                is_external_api=True,
                external_handler=detect_crime_type_handler,
            ),
            ToolDefinition(
                name="analyze_crime_elements",
                description="구성요건 분석. 범죄의 객관적 구성요건(행위, 객체, 결과)과 주관적 구성요건(고의/과실)을 분석합니다.",
                workflow_name=None,  # 개별 핸들러 사용
                input_schema={
                    "case_content": "str (사건 문서 내용)",
                    "crime_type": "str (범죄 유형)",
                },
                output_schema={
                    "objective": "list (객관적 구성요건)",
                    "subjective": "list (주관적 구성요건)",
                },
                category=ToolCategory.ANALYSIS,
                estimated_tokens=1000,
                timeout=60.0,
                is_external_api=True,
                external_handler=analyze_crime_elements_handler,
            ),
            ToolDefinition(
                name="extract_sentencing_factors",
                description="양형인자 추출. 유리한 정상(초범, 반성, 피해회복 등)과 불리한 정상(동종전과, 계획적 범행 등)을 추출합니다.",
                workflow_name=None,  # 개별 핸들러 사용
                input_schema={
                    "case_content": "str (사건 문서 내용)",
                    "crime_type": "str (범죄 유형)",
                },
                output_schema={
                    "favorable": "list (유리한 정상)",
                    "unfavorable": "list (불리한 정상)",
                },
                category=ToolCategory.ANALYSIS,
                estimated_tokens=800,
                timeout=45.0,
                is_external_api=True,
                external_handler=extract_sentencing_factors_handler,
            ),
            ToolDefinition(
                name="estimate_sentence",
                description="양형 예측. 예상 형량 범위와 집행유예 가능성을 예측합니다. 양형인자가 없으면 자동으로 추출합니다.",
                workflow_name=None,  # 개별 핸들러 사용
                input_schema={
                    "crime_type": "str (범죄 유형)",
                    "sentencing_factors": "dict (optional, 양형인자)",
                    "case_content": "str (optional, 양형인자가 없을 경우 사용)",
                },
                output_schema={
                    "range": "str (예상 형량 범위)",
                    "suspended_probability": "float (집행유예 가능성 0.0~1.0)",
                    "reasoning": "str (산정 근거)",
                },
                category=ToolCategory.ANALYSIS,
                estimated_tokens=600,
                timeout=30.0,
                is_external_api=True,
                external_handler=estimate_sentence_handler,
            ),
            ToolDefinition(
                name="suggest_defense_strategies",
                description="변호 전략 제안. 형사 사건에 대한 변호 전략을 제안합니다. 구성요건/양형인자가 없으면 자동으로 분석합니다.",
                workflow_name=None,  # 개별 핸들러 사용
                input_schema={
                    "crime_type": "str (범죄 유형)",
                    "crime_elements": "dict (optional, 구성요건)",
                    "sentencing_factors": "dict (optional, 양형인자)",
                    "case_content": "str (optional, 자동 분석용)",
                },
                output_schema={"strategies": "list (변호 전략 목록)"},
                category=ToolCategory.ANALYSIS,
                estimated_tokens=800,
                timeout=45.0,
                is_external_api=True,
                external_handler=suggest_defense_strategies_handler,
            ),
            ToolDefinition(
                name="search_criminal_precedents",
                description="형사 판례 검색. 유사한 형사 사건 판례를 검색합니다.",
                workflow_name=None,  # 개별 핸들러 사용
                input_schema={
                    "crime_type": "str (범죄 유형)",
                    "keywords": "list (optional, 검색 키워드)",
                    "case_content": "str (optional, 자동 키워드 추출용)",
                },
                output_schema={
                    "precedents": "list (판례 목록)",
                    "total_count": "int",
                },
                category=ToolCategory.SEARCH,
                estimated_tokens=700,
                timeout=45.0,
                is_external_api=True,
                external_handler=search_criminal_precedents_handler,
                fallback_tool="fetch_court_api",
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
            # 외부 핸들러가 있으면 등록
            if tool.external_handler:
                self._external_handlers[tool.name] = tool.external_handler

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

        # ================================================================
        # 추가 MCP 도구 등록 (Phase 7: LLM Native Tool Use 확장)
        # ================================================================
        try:
            additional_mcp_tools = [
                # 판례 상세 조회
                ToolDefinition(
                    name="get_precedent_details",
                    description="특정 판례의 상세 정보를 조회합니다. 사건번호로 판결문 전문, 주요 판시사항, 참조조문 등을 가져옵니다.",
                    workflow_name=None,
                    input_schema={"case_number": "str"},
                    output_schema={"precedent": "dict"},
                    category=ToolCategory.SEARCH,
                    estimated_tokens=100,
                    timeout=30.0,
                    is_external_api=True,
                    external_handler=get_precedent_details_handler,
                ),
                # 문서 분석 도구
                ToolDefinition(
                    name="extract_clauses",
                    description="문서에서 조항을 추출합니다. 계약서, 약관, 법령 등에서 개별 조항을 분리합니다.",
                    workflow_name=None,
                    input_schema={"content": "str"},
                    output_schema={"clauses": "list"},
                    category=ToolCategory.ANALYSIS,
                    estimated_tokens=500,
                    timeout=60.0,
                    is_external_api=True,
                    external_handler=extract_clauses_handler,
                ),
                ToolDefinition(
                    name="summarize_document",
                    description="문서를 요약합니다. 긴 법률 문서, 판결문, 계약서 등의 핵심 내용을 간결하게 정리합니다.",
                    workflow_name=None,
                    input_schema={"content": "str", "max_length": "int"},
                    output_schema={"summary": "str"},
                    category=ToolCategory.ANALYSIS,
                    estimated_tokens=800,
                    timeout=60.0,
                    is_external_api=True,
                    external_handler=summarize_document_handler,
                ),
                ToolDefinition(
                    name="detect_document_type",
                    description="문서 타입을 자동 감지합니다. 계약서, 판결문, 소장, 법령 등 문서 유형을 판별합니다.",
                    workflow_name=None,
                    input_schema={"content": "str"},
                    output_schema={"doc_type": "str", "confidence": "float"},
                    category=ToolCategory.ANALYSIS,
                    estimated_tokens=300,
                    timeout=30.0,
                    is_external_api=True,
                    external_handler=detect_document_type_handler,
                ),
                # 사건 분석 도구
                ToolDefinition(
                    name="extract_parties",
                    description="사건에서 당사자를 추출합니다. 원고, 피고, 피해자, 피의자 등 관련자 정보를 식별합니다.",
                    workflow_name=None,
                    input_schema={"case_content": "str"},
                    output_schema={"parties": "list"},
                    category=ToolCategory.ANALYSIS,
                    estimated_tokens=400,
                    timeout=45.0,
                    is_external_api=True,
                    external_handler=extract_parties_handler,
                ),
                ToolDefinition(
                    name="identify_issues",
                    description="사건의 법적 쟁점을 식별합니다. 사실관계와 법률적 쟁점을 분류하여 제시합니다.",
                    workflow_name=None,
                    input_schema={"case_content": "str"},
                    output_schema={"issues": "list"},
                    category=ToolCategory.ANALYSIS,
                    estimated_tokens=600,
                    timeout=60.0,
                    is_external_api=True,
                    external_handler=identify_issues_handler,
                ),
                ToolDefinition(
                    name="search_related_cases",
                    description="관련 사건을 검색합니다. 유사한 쟁점이나 사실관계를 가진 선례를 찾습니다.",
                    workflow_name=None,
                    input_schema={"query": "str", "case_type": "str", "top_k": "int"},
                    output_schema={"cases": "list"},
                    category=ToolCategory.SEARCH,
                    estimated_tokens=500,
                    timeout=45.0,
                    is_external_api=True,
                    external_handler=search_related_cases_handler,
                ),
                ToolDefinition(
                    name="assess_case_complexity",
                    description="사건 복잡도를 평가합니다. 쟁점 수, 증거 복잡성, 법적 난이도 등을 분석합니다.",
                    workflow_name=None,
                    input_schema={"case_content": "str"},
                    output_schema={"complexity_level": "str", "factors": "list"},
                    category=ToolCategory.ANALYSIS,
                    estimated_tokens=400,
                    timeout=45.0,
                    is_external_api=True,
                    external_handler=assess_case_complexity_handler,
                ),
                # 분석 도구
                ToolDefinition(
                    name="analyze_risks",
                    description="문서의 리스크를 분석합니다. 계약 조건의 위험성, 법적 취약점 등을 평가합니다.",
                    workflow_name=None,
                    input_schema={"content": "str", "doc_type": "str"},
                    output_schema={"risks": "list", "risk_score": "float"},
                    category=ToolCategory.ANALYSIS,
                    estimated_tokens=700,
                    timeout=60.0,
                    is_external_api=True,
                    external_handler=analyze_risks_handler,
                ),
                ToolDefinition(
                    name="compare_documents",
                    description="두 문서를 비교합니다. 조항 차이, 누락 사항, 변경점 등을 분석합니다.",
                    workflow_name=None,
                    input_schema={"doc1": "str", "doc2": "str", "comparison_type": "str"},
                    output_schema={"differences": "list", "similarities": "list"},
                    category=ToolCategory.ANALYSIS,
                    estimated_tokens=1000,
                    timeout=90.0,
                    is_external_api=True,
                    external_handler=compare_documents_handler,
                ),
                ToolDefinition(
                    name="generate_report",
                    description="분석 결과로 보고서를 생성합니다. 분석 내용을 정리된 형태로 출력합니다.",
                    workflow_name=None,
                    input_schema={"analysis_results": "dict", "report_type": "str"},
                    output_schema={"report": "str"},
                    category=ToolCategory.ANALYSIS,
                    estimated_tokens=800,
                    timeout=60.0,
                    is_external_api=True,
                    external_handler=generate_report_handler,
                ),
                # 외부 API 도구 핸들러 등록
                ToolDefinition(
                    name="fetch_court_api",
                    description="대법원 판례 API를 호출합니다. 국가법령정보센터에서 실시간 판례 데이터를 조회합니다.",
                    workflow_name=None,
                    input_schema={
                        "case_number": "str (optional)",
                        "keyword": "str (optional)",
                        "start_date": "str (optional)",
                        "end_date": "str (optional)",
                        "court": "str (optional)",
                    },
                    output_schema={"precedents": "list", "total_count": "int"},
                    category=ToolCategory.EXTERNAL_API,
                    estimated_tokens=100,
                    timeout=30.0,
                    is_external_api=True,
                    external_handler=fetch_court_api_handler,
                ),
                ToolDefinition(
                    name="fetch_statute_api",
                    description="법령 API를 호출합니다. 국가법령정보센터에서 최신 법령 정보를 조회합니다.",
                    workflow_name=None,
                    input_schema={
                        "law_code": "str (optional)",
                        "keyword": "str (optional)",
                        "law_type": "str (optional)",
                        "ministry": "str (optional)",
                    },
                    output_schema={"statutes": "list", "total_count": "int"},
                    category=ToolCategory.EXTERNAL_API,
                    estimated_tokens=100,
                    timeout=30.0,
                    is_external_api=True,
                    external_handler=fetch_statute_api_handler,
                ),
                ToolDefinition(
                    name="parse_legal_document",
                    description="법률 문서를 파싱합니다. 문서 구조를 분석하고 주요 섹션을 추출합니다.",
                    workflow_name=None,
                    input_schema={"content": "str", "doc_type": "str"},
                    output_schema={"sections": "list", "title": "str"},
                    category=ToolCategory.UTILITY,
                    estimated_tokens=200,
                    timeout=30.0,
                    is_external_api=True,
                    external_handler=parse_legal_document_handler,
                ),
                ToolDefinition(
                    name="validate_document_structure",
                    description="문서 구조를 검증합니다. 필수 필드 존재 여부를 확인합니다.",
                    workflow_name=None,
                    input_schema={"data": "dict", "doc_type": "str"},
                    output_schema={"valid": "bool", "missing_fields": "list"},
                    category=ToolCategory.UTILITY,
                    estimated_tokens=50,
                    timeout=10.0,
                    is_external_api=True,
                    external_handler=validate_document_structure_handler,
                ),
            ]

            for tool in additional_mcp_tools:
                self._tools[tool.name] = tool
                if tool.external_handler:
                    self._external_handlers[tool.name] = tool.external_handler

            logger.info(f"Registered {len(additional_mcp_tools)} additional MCP tools")

        except Exception as e:
            logger.warning(f"Failed to register additional MCP tools: {e}")

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
            "문서": [ToolCategory.DOCUMENT, ToolCategory.SEARCH],
            "내 문서": [ToolCategory.SEARCH],
            "업로드": [ToolCategory.SEARCH],
            "비교": [ToolCategory.DOCUMENT],
            "리스크": [ToolCategory.ANALYSIS],
            "위험": [ToolCategory.ANALYSIS],
            "사건": [ToolCategory.SEARCH, ToolCategory.ANALYSIS],
            # Phase 1: 형사법 특화 키워드
            "형사": [ToolCategory.ANALYSIS],
            "범죄": [ToolCategory.ANALYSIS],
            "절도": [ToolCategory.ANALYSIS],
            "사기": [ToolCategory.ANALYSIS],
            "폭행": [ToolCategory.ANALYSIS],
            "상해": [ToolCategory.ANALYSIS],
            "구성요건": [ToolCategory.ANALYSIS],
            "양형": [ToolCategory.ANALYSIS],
            "형량": [ToolCategory.ANALYSIS],
            "집행유예": [ToolCategory.ANALYSIS],
            "변호": [ToolCategory.ANALYSIS],
            "기소": [ToolCategory.ANALYSIS, ToolCategory.SEARCH],
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
