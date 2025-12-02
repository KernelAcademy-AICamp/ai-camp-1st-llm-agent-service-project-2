"""
Case Analysis MCP Tools

Phase 4 - Week 12: 사건 분석 MCP Tools

도구 목록:
- analyze_case: 사건 분석
- extract_parties: 당사자 추출
- identify_issues: 쟁점 식별
- search_related_cases: 관련 사건 검색

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


async def analyze_case(
    case_content: str,
    case_type: str = "unknown"
) -> Dict[str, Any]:
    """
    사건 분석

    사건 기록을 분석하여 핵심 정보를 추출합니다.

    Args:
        case_content: 사건 내용
        case_type: 사건 유형 (civil, criminal, administrative, family, other)

    Returns:
        분석 결과
        - case_type: 사건 유형
        - summary: 사건 요약
        - parties: 당사자 정보
        - issues: 쟁점 리스트
        - legal_basis: 법적 근거
    """
    logger.info(f"Analyzing case of type: {case_type}")

    try:
        from libs.rag_core.llm.llm_client import get_llm

        llm = get_llm()

        prompt = f"""다음 사건을 분석하세요.

사건 유형: {case_type}

사건 내용:
{case_content[:5000]}

분석 결과를 JSON 형식으로 제공하세요:
{{
    "case_type": "민사|형사|행정|가사|기타",
    "summary": "사건 요약",
    "parties": [
        {{"role": "원고|피고|검사|피고인", "name": "이름", "description": "설명"}}
    ],
    "issues": [
        {{"issue_type": "쟁점 유형", "description": "설명", "legal_basis": "관련 법조항"}}
    ],
    "legal_basis": ["관련 법률 1", "관련 법률 2"]
}}"""

        result = await llm.ainvoke(prompt)

        return {
            "case_type": case_type,
            "summary": result.content[:500] if hasattr(result, 'content') else str(result)[:500],
            "parties": [],
            "issues": [],
            "legal_basis": [],
            "raw_response": result.content if hasattr(result, 'content') else str(result)
        }

    except Exception as e:
        logger.error(f"Error analyzing case: {e}")
        return {
            "error": str(e),
            "case_type": case_type,
            "summary": "",
            "parties": [],
            "issues": [],
            "legal_basis": []
        }


async def extract_parties(case_content: str) -> List[Dict[str, Any]]:
    """
    당사자 정보 추출

    Args:
        case_content: 사건 내용

    Returns:
        당사자 리스트
        - role: 역할 (plaintiff, defendant, third_party 등)
        - name: 이름
        - description: 설명
    """
    logger.info("Extracting parties from case")

    try:
        from libs.rag_core.llm.llm_client import get_llm

        llm = get_llm()

        prompt = f"""다음 사건에서 당사자 정보를 추출하세요.

사건 내용:
{case_content[:3000]}

당사자를 JSON 배열 형식으로 제공하세요:
[
    {{
        "role": "원고|피고|검사|피고인|참가인|제3자",
        "name": "당사자 이름",
        "description": "당사자 설명"
    }},
    ...
]"""

        result = await llm.ainvoke(prompt)

        # 간단한 파싱 (실제로는 JSON 파싱 필요)
        parties = []

        # 휴리스틱 기반 추출
        if "원고" in case_content:
            parties.append({
                "role": "plaintiff",
                "name": "원고",
                "description": "제소한 당사자"
            })
        if "피고" in case_content:
            parties.append({
                "role": "defendant",
                "name": "피고",
                "description": "피소된 당사자"
            })
        if "검사" in case_content or "검찰" in case_content:
            parties.append({
                "role": "prosecutor",
                "name": "검사",
                "description": "공소 제기자"
            })
        if "피고인" in case_content:
            parties.append({
                "role": "accused",
                "name": "피고인",
                "description": "형사 피의자"
            })

        return parties if parties else [{
            "role": "unknown",
            "name": "당사자 미상",
            "description": "추출 실패"
        }]

    except Exception as e:
        logger.error(f"Error extracting parties: {e}")
        return [{
            "error": str(e),
            "role": "unknown",
            "name": "",
            "description": ""
        }]


async def identify_issues(case_content: str) -> List[Dict[str, Any]]:
    """
    쟁점 식별

    Args:
        case_content: 사건 내용

    Returns:
        쟁점 리스트
        - issue_type: 쟁점 유형
        - description: 설명
        - legal_basis: 법적 근거
    """
    logger.info("Identifying issues in case")

    try:
        from libs.rag_core.llm.llm_client import get_llm

        llm = get_llm()

        prompt = f"""다음 사건에서 주요 쟁점을 식별하세요.

사건 내용:
{case_content[:4000]}

쟁점을 JSON 배열 형식으로 제공하세요:
[
    {{
        "issue_type": "사실관계|법률해석|손해배상|책임유무|기타",
        "description": "쟁점 설명",
        "legal_basis": "관련 법조항"
    }},
    ...
]"""

        result = await llm.ainvoke(prompt)

        return [{
            "issue_type": "general",
            "description": result.content[:500] if hasattr(result, 'content') else str(result)[:500],
            "legal_basis": ""
        }]

    except Exception as e:
        logger.error(f"Error identifying issues: {e}")
        return [{
            "error": str(e),
            "issue_type": "unknown",
            "description": "",
            "legal_basis": ""
        }]


async def search_related_cases(
    query: str,
    case_type: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    관련 사건 검색

    Args:
        query: 검색 질의
        case_type: 사건 유형 필터
        top_k: 반환할 결과 수

    Returns:
        관련 사건 리스트
        - case_number: 사건번호
        - title: 제목
        - summary: 요약
        - relevance_score: 관련도 점수
    """
    logger.info(f"Searching related cases: {query}, type={case_type}, top_k={top_k}")

    try:
        from libs.rag_core.retrieval.retriever import LegalDocumentRetriever
        from libs.rag_core.embeddings.remote_embedder import RemoteEmbedder
        from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB
        from apps.ai_service.config.settings import settings

        # embedder 및 vectordb 초기화
        embedder = RemoteEmbedder(
            base_url=settings.REMOTE_EMBED_BASE_URL,
            timeout=30
        )
        vectordb = QdrantVectorDB(
            collection_name=settings.QDRANT_COLLECTION,
            url=settings.QDRANT_URL,
            embedding_dim=embedder.get_embedding_dimension()
        )

        retriever = LegalDocumentRetriever(
            vectordb=vectordb,
            embedder=embedder
        )

        # 검색 실행 (동기 메서드 사용)
        results = retriever.retrieve(
            query=query,
            top_k=top_k
        )

        # 결과 포맷팅
        related_cases = []
        for i, doc in enumerate(results):
            related_cases.append({
                "case_number": doc.get("case_number", doc.get("metadata", {}).get("case_number", f"unknown-{i}")),
                "title": doc.get("title", doc.get("metadata", {}).get("title", "제목 없음")),
                "summary": doc.get("text", doc.get("content", ""))[:200],
                "relevance_score": doc.get("score", 0.5)
            })

        return related_cases

    except Exception as e:
        logger.error(f"Error searching related cases: {e}")
        return [{
            "error": str(e),
            "case_number": "",
            "title": "",
            "summary": "",
            "relevance_score": 0.0
        }]


async def assess_case_complexity(case_content: str) -> Dict[str, Any]:
    """
    사건 복잡도 평가

    Args:
        case_content: 사건 내용

    Returns:
        복잡도 평가 결과
        - complexity_score: 복잡도 점수 (0-100)
        - factors: 복잡도 요인 리스트
        - recommendation: 처리 권장사항
    """
    logger.info("Assessing case complexity")

    try:
        from libs.rag_core.llm.llm_client import get_llm

        llm = get_llm()

        prompt = f"""다음 사건의 복잡도를 평가하세요.

사건 내용:
{case_content[:4000]}

복잡도를 JSON 형식으로 평가하세요:
{{
    "complexity_score": 0-100 사이의 점수,
    "factors": ["복잡도 요인 1", "복잡도 요인 2", ...],
    "recommendation": "단순|전문가 검토 권장|긴급 검토 필요"
}}

평가 기준:
- 당사자 수
- 쟁점 복잡성
- 관련 법률 범위
- 증거/자료 양
- 전문 지식 필요도"""

        result = await llm.ainvoke(prompt)

        # 간단한 휴리스틱 기반 복잡도 계산
        content_length = len(case_content)
        party_count = sum(1 for word in ["원고", "피고", "피고인", "제3자"] if word in case_content)

        complexity_score = min(100, max(0,
            (content_length // 1000) * 10 +  # 길이 기반
            party_count * 15 +  # 당사자 수 기반
            20  # 기본 점수
        ))

        return {
            "complexity_score": complexity_score,
            "factors": [
                f"문서 길이: {content_length}자",
                f"당사자 수: {party_count}명"
            ],
            "recommendation": "전문가 검토 권장" if complexity_score >= 70 else "단순"
        }

    except Exception as e:
        logger.error(f"Error assessing complexity: {e}")
        return {
            "error": str(e),
            "complexity_score": 50,
            "factors": [],
            "recommendation": "평가 실패"
        }
