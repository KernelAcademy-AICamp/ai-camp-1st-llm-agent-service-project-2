"""
Document Analysis MCP Tools

Phase 4 - Week 12: 문서 분석 MCP Tools

도구 목록:
- analyze_document: 문서 분석
- extract_clauses: 조항 추출
- summarize_document: 문서 요약
- detect_document_type: 문서 타입 감지

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


async def analyze_document(
    content: str,
    doc_type: str = "unknown"
) -> Dict[str, Any]:
    """
    문서 분석

    LLM 기반으로 문서의 핵심 정보를 분석합니다.

    Args:
        content: 분석할 문서 내용
        doc_type: 문서 타입 (contract, statute, case, precedent, other)

    Returns:
        분석 결과 딕셔너리
        - summary: 요약
        - key_points: 핵심 포인트 리스트
        - entities: 추출된 엔티티 (당사자, 날짜 등)
        - doc_type: 감지된 문서 타입
    """
    logger.info(f"Analyzing document of type: {doc_type}")

    try:
        from libs.rag_core.llm.llm_client import get_llm

        llm = get_llm()

        prompt = f"""다음 문서를 분석하세요.

문서 타입: {doc_type}

문서 내용:
{content[:5000]}  # 길이 제한

분석 결과를 JSON 형식으로 제공하세요:
{{
    "summary": "문서 요약",
    "key_points": ["핵심 포인트 1", "핵심 포인트 2", ...],
    "entities": {{
        "parties": ["당사자 1", "당사자 2"],
        "dates": ["2024-01-01"],
        "amounts": ["1,000,000원"]
    }},
    "doc_type": "계약서|법령|판례|기타"
}}"""

        result = await llm.ainvoke(prompt)

        # 결과 파싱 (실제로는 JSON 파싱 필요)
        return {
            "summary": result.content[:500] if hasattr(result, 'content') else str(result)[:500],
            "key_points": [],
            "entities": {},
            "doc_type": doc_type,
            "raw_response": result.content if hasattr(result, 'content') else str(result)
        }

    except Exception as e:
        logger.error(f"Error analyzing document: {e}")
        return {
            "error": str(e),
            "summary": "",
            "key_points": [],
            "entities": {},
            "doc_type": doc_type
        }


async def extract_clauses(
    content: str,
    clause_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    계약서/법령에서 조항 추출

    Args:
        content: 문서 내용
        clause_types: 추출할 조항 타입 필터 (예: ["의무", "권리", "책임"])

    Returns:
        조항 리스트
        - clause_number: 조항 번호
        - clause_type: 조항 타입
        - text: 조항 내용
        - importance: 중요도 (high, medium, low)
    """
    logger.info(f"Extracting clauses, types filter: {clause_types}")

    try:
        from libs.rag_core.llm.llm_client import get_llm

        llm = get_llm()

        clause_filter = ", ".join(clause_types) if clause_types else "모든 조항"

        prompt = f"""다음 문서에서 조항을 추출하세요.

추출 대상: {clause_filter}

문서 내용:
{content[:5000]}

조항을 JSON 배열 형식으로 제공하세요:
[
    {{
        "clause_number": "제1조",
        "clause_type": "의무|권리|책임|정의|기타",
        "text": "조항 내용",
        "importance": "high|medium|low"
    }},
    ...
]"""

        result = await llm.ainvoke(prompt)

        # 결과 파싱 (실제로는 JSON 파싱 필요)
        return [{
            "clause_number": "추출됨",
            "clause_type": "general",
            "text": result.content[:500] if hasattr(result, 'content') else str(result)[:500],
            "importance": "medium"
        }]

    except Exception as e:
        logger.error(f"Error extracting clauses: {e}")
        return [{
            "error": str(e),
            "clause_number": "",
            "clause_type": "",
            "text": "",
            "importance": "low"
        }]


async def summarize_document(
    content: str,
    max_length: int = 500,
    focus: Optional[str] = None
) -> Dict[str, Any]:
    """
    문서 요약

    Args:
        content: 문서 내용
        max_length: 요약 최대 길이
        focus: 집중할 부분 (예: "법적 의무", "위험 요소")

    Returns:
        요약 결과
        - summary: 요약 텍스트
        - word_count: 단어 수
        - key_terms: 핵심 용어 리스트
    """
    logger.info(f"Summarizing document, max_length: {max_length}")

    try:
        from libs.rag_core.llm.llm_client import get_llm

        llm = get_llm()

        focus_instruction = f"\n집중할 부분: {focus}" if focus else ""

        prompt = f"""다음 문서를 {max_length}자 이내로 요약하세요.{focus_instruction}

문서 내용:
{content[:8000]}

요약:"""

        result = await llm.ainvoke(prompt)
        summary = result.content if hasattr(result, 'content') else str(result)

        return {
            "summary": summary[:max_length],
            "word_count": len(summary.split()),
            "key_terms": []  # 실제로는 핵심 용어 추출 로직 필요
        }

    except Exception as e:
        logger.error(f"Error summarizing document: {e}")
        return {
            "error": str(e),
            "summary": "",
            "word_count": 0,
            "key_terms": []
        }


async def detect_document_type(content: str) -> Dict[str, Any]:
    """
    문서 타입 감지

    Args:
        content: 문서 내용

    Returns:
        타입 감지 결과
        - doc_type: 감지된 타입 (contract, statute, precedent, case, other)
        - confidence: 신뢰도 (0-1)
        - indicators: 감지 근거
    """
    logger.info("Detecting document type")

    try:
        from libs.rag_core.llm.llm_client import get_llm

        llm = get_llm()

        prompt = f"""다음 문서의 타입을 판별하세요.

문서 내용 (앞부분):
{content[:2000]}

가능한 타입:
- contract: 계약서
- statute: 법령/법률
- precedent: 판례
- case: 사건 기록
- other: 기타

JSON 형식으로 응답하세요:
{{
    "doc_type": "타입",
    "confidence": 0.95,
    "indicators": ["근거 1", "근거 2"]
}}"""

        result = await llm.ainvoke(prompt)

        # 간단한 휴리스틱 (실제로는 LLM 응답 파싱)
        content_lower = content.lower()
        if "계약" in content or "contract" in content_lower:
            doc_type = "contract"
            confidence = 0.8
        elif "대법원" in content or "판결" in content:
            doc_type = "precedent"
            confidence = 0.85
        elif "법률" in content or "시행령" in content:
            doc_type = "statute"
            confidence = 0.8
        elif "사건" in content and "원고" in content:
            doc_type = "case"
            confidence = 0.75
        else:
            doc_type = "other"
            confidence = 0.5

        return {
            "doc_type": doc_type,
            "confidence": confidence,
            "indicators": [],
            "raw_response": result.content if hasattr(result, 'content') else str(result)
        }

    except Exception as e:
        logger.error(f"Error detecting document type: {e}")
        return {
            "error": str(e),
            "doc_type": "unknown",
            "confidence": 0.0,
            "indicators": []
        }
