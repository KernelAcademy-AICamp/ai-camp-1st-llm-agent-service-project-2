"""
Query Decomposer - 복잡한 질문 분해

복합 질문을 단일 질문으로 분해하여
각각 처리 후 종합합니다.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import json

from libs.rag_core.llm.llm_client import get_llm_client

logger = logging.getLogger(__name__)


@dataclass
class DecomposedQuery:
    """분해된 쿼리"""
    original_query: str
    is_complex: bool
    sub_queries: List[str]
    reasoning: str


DECOMPOSITION_PROMPT = """당신은 질문 분석 전문가입니다.

## 질문
{query}

## 작업
이 질문이 복합 질문인지 분석하고, 복합 질문이면 하위 질문으로 분해하세요.

## 복합 질문 판단 기준
- "A와 B를 비교해줘" → 복합 (A 조사, B 조사, 비교)
- "~하고 나서 ~해줘" → 복합 (순차 작업)
- "~에 대해 알려주고 관련 판례도 찾아줘" → 복합 (설명, 판례 검색)
- "~의 법적 근거와 예외 사항" → 복합 (법적 근거, 예외)

## 단일 질문 예시
- "민법 제750조가 뭐야?" → 단일
- "절도죄의 법정형은?" → 단일
- "이 계약서 분석해줘" → 단일

## 출력 형식 (JSON)

```json
{{
    "is_complex": true/false,
    "sub_queries": ["하위 질문 1", "하위 질문 2"],
    "reasoning": "판단 근거"
}}
```

하위 질문이 없으면 `sub_queries`는 빈 배열로 반환하세요.
"""


async def decompose_query(
    query: str,
    llm_client=None,
    model_name: str = "gpt-4o-mini",
) -> DecomposedQuery:
    """
    복잡한 질문을 하위 질문으로 분해

    Args:
        query: 원래 질문
        llm_client: LLM 클라이언트 (없으면 새로 생성)
        model_name: 분해에 사용할 모델

    Returns:
        DecomposedQuery
    """
    # 짧은 질문은 바로 단일로 처리
    if len(query) < 20:
        return DecomposedQuery(
            original_query=query,
            is_complex=False,
            sub_queries=[],
            reasoning="짧은 질문",
        )

    # 빠른 사전 검사
    if not should_decompose(query):
        return DecomposedQuery(
            original_query=query,
            is_complex=False,
            sub_queries=[],
            reasoning="복합 질문 키워드 없음",
        )

    try:
        if llm_client is None:
            llm_client = get_llm_client(model_name=model_name)

        prompt = DECOMPOSITION_PROMPT.format(query=query)

        response = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        result = json.loads(response)

        sub_queries = result.get("sub_queries", [])

        # 하위 질문이 너무 많으면 제한
        if len(sub_queries) > 4:
            sub_queries = sub_queries[:4]

        return DecomposedQuery(
            original_query=query,
            is_complex=result.get("is_complex", False),
            sub_queries=sub_queries,
            reasoning=result.get("reasoning", ""),
        )

    except Exception as e:
        logger.error(f"[decompose_query] Error: {e}")
        return DecomposedQuery(
            original_query=query,
            is_complex=False,
            sub_queries=[],
            reasoning=f"분해 실패: {e}",
        )


def should_decompose(query: str) -> bool:
    """
    분해가 필요한 질문인지 빠르게 판단 (LLM 호출 전)

    규칙 기반으로 빠르게 필터링
    """
    # 짧은 질문은 분해 불필요
    if len(query) < 20:
        return False

    # 복합 질문 키워드 (한글은 대소문자 구분 없음)
    complex_keywords = [
        # 비교/대조
        "비교", "차이", "다른점", "같은점", "versus", "vs",
        # 접속
        "그리고", "또한", "함께", "더불어", "아울러",
        # 순차
        "한 후", "한 다음", "그 다음", "후에",
        # 나열 (공백 포함/미포함 둘 다)
        "와 ", "과 ", " 및 ", "둘 다", "각각", "모두",
        # 복합 요청 (공백 없이도 매칭)
        "알려주고", "찾아주고", "설명하고", "분석하고",
        "해주고", "주고 ", "줘 그리고",
    ]

    for keyword in complex_keywords:
        if keyword in query:
            return True

    # 패턴 기반 체크
    # "A과/와 B" 패턴 (법률 용어가 2개 이상 언급)
    legal_terms = ["민법", "형법", "상법", "헌법", "행정법", "근로기준법", "법", "법률"]
    term_count = sum(1 for term in legal_terms if term in query)
    if term_count >= 2 and ("과 " in query or "와 " in query or " 및 " in query):
        return True

    # "~하고 ~해줘/찾아줘" 패턴
    action_pairs = [
        ("분석", "판례"),
        ("분석", "찾아"),
        ("설명", "판례"),
        ("설명", "찾아"),
        ("알려", "판례"),
        ("알려", "찾아"),
    ]

    for p1, p2 in action_pairs:
        if p1 in query and p2 in query:
            return True

    # "~고 " 접속 패턴 (동사 뒤에 "고"가 오는 경우)
    if "고 " in query and len(query) > 30:
        # "~하고", "~주고" 등
        go_patterns = ["하고 ", "주고 ", "보고 "]
        for pattern in go_patterns:
            if pattern in query:
                return True

    return False


def format_decomposition_for_prompt(decomposed: DecomposedQuery) -> str:
    """
    분해 결과를 시스템 프롬프트에 추가할 형식으로 변환

    Args:
        decomposed: 분해된 쿼리

    Returns:
        포맷팅된 문자열
    """
    if not decomposed.is_complex or not decomposed.sub_queries:
        return ""

    lines = [
        "",
        "## 질문 분해",
        "원래 질문이 다음 하위 질문으로 분해되었습니다:",
    ]

    for i, sub_q in enumerate(decomposed.sub_queries, 1):
        lines.append(f"{i}. {sub_q}")

    lines.append("")
    lines.append("각 하위 질문에 대해 순차적으로 도구를 사용하고, 마지막에 종합하세요.")

    return "\n".join(lines)


def extract_sub_query_keywords(sub_queries: List[str]) -> List[str]:
    """
    하위 질문들에서 핵심 키워드 추출

    Args:
        sub_queries: 하위 질문 목록

    Returns:
        키워드 목록
    """
    keywords = []

    legal_terms = [
        "민법", "형법", "상법", "헌법", "행정법",
        "근로기준법", "민사소송법", "형사소송법",
        "손해배상", "불법행위", "계약", "채무불이행",
        "판례", "판결", "조문", "조항", "규정",
    ]

    for query in sub_queries:
        for term in legal_terms:
            if term in query and term not in keywords:
                keywords.append(term)

    return keywords
