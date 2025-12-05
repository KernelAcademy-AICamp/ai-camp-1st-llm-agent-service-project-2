"""
Retrieval Evaluator - 검색 결과 품질 평가

검색 결과가 질문에 적합한지 평가하고,
부족하면 재검색을 권장합니다.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
import json

from libs.rag_core.llm.llm_client import get_llm_client

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """검색 결과 평가 결과"""
    is_relevant: bool           # 관련성 있는지
    is_sufficient: bool         # 충분한지
    relevance_score: float      # 관련성 점수 (0.0 ~ 1.0)
    completeness_score: float   # 완전성 점수 (0.0 ~ 1.0)
    reasoning: str              # 평가 근거
    suggested_action: str       # 권장 행동 ("use", "retry", "expand", "different_tool")
    suggested_query: Optional[str] = None  # 재검색 시 제안 쿼리


EVALUATION_PROMPT = """당신은 검색 결과 품질 평가 전문가입니다.

## 원래 질문
{query}

## 검색 결과
{results}

## 평가 기준

1. **관련성 (Relevance)**: 검색 결과가 질문과 직접 관련이 있는가?
   - 1.0: 매우 관련있음 (질문에 직접 답변 가능)
   - 0.7: 관련있음 (부분적으로 답변 가능)
   - 0.4: 약간 관련 (배경 정보로 사용 가능)
   - 0.0: 관련없음

2. **완전성 (Completeness)**: 질문에 답하기에 정보가 충분한가?
   - 1.0: 매우 충분 (추가 검색 불필요)
   - 0.7: 충분 (약간의 추가 정보 있으면 좋음)
   - 0.4: 부분적 (추가 검색 필요)
   - 0.0: 불충분 (다시 검색 필요)

## 출력 형식 (JSON)

```json
{{
    "relevance_score": 0.0~1.0,
    "completeness_score": 0.0~1.0,
    "reasoning": "평가 근거 설명",
    "suggested_action": "use|retry|expand|different_tool",
    "suggested_query": "재검색 시 제안 쿼리 (optional)"
}}
```

- `use`: 현재 결과로 답변 생성
- `retry`: 다른 검색어로 재검색
- `expand`: 추가 검색으로 정보 보완
- `different_tool`: 다른 도구 사용 권장
"""


async def evaluate_retrieval(
    query: str,
    results: List[Dict[str, Any]],
    llm_client=None,
    model_name: str = "gpt-4o-mini",
) -> EvaluationResult:
    """
    검색 결과 품질 평가

    Args:
        query: 원래 질문
        results: 검색 결과 목록
        llm_client: LLM 클라이언트 (없으면 새로 생성)
        model_name: 평가에 사용할 모델

    Returns:
        EvaluationResult
    """
    # 결과가 없으면 바로 retry 권장
    if not results:
        return EvaluationResult(
            is_relevant=False,
            is_sufficient=False,
            relevance_score=0.0,
            completeness_score=0.0,
            reasoning="검색 결과가 없습니다.",
            suggested_action="retry",
            suggested_query=_generate_alternative_query(query),
        )

    # 결과 텍스트 포맷팅
    results_text = _format_results(results)

    # LLM으로 평가
    try:
        if llm_client is None:
            llm_client = get_llm_client(model_name=model_name)

        prompt = EVALUATION_PROMPT.format(
            query=query,
            results=results_text,
        )

        response = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        # JSON 파싱
        evaluation = json.loads(response)

        relevance = evaluation.get("relevance_score", 0.5)
        completeness = evaluation.get("completeness_score", 0.5)

        return EvaluationResult(
            is_relevant=relevance >= 0.5,
            is_sufficient=completeness >= 0.6,
            relevance_score=relevance,
            completeness_score=completeness,
            reasoning=evaluation.get("reasoning", ""),
            suggested_action=evaluation.get("suggested_action", "use"),
            suggested_query=evaluation.get("suggested_query"),
        )

    except Exception as e:
        logger.error(f"[evaluate_retrieval] Error: {e}")
        # 평가 실패 시 결과 사용
        return EvaluationResult(
            is_relevant=True,
            is_sufficient=True,
            relevance_score=0.6,
            completeness_score=0.6,
            reasoning=f"평가 실패: {e}",
            suggested_action="use",
        )


def _format_results(results: List[Dict[str, Any]], max_chars: int = 2000) -> str:
    """검색 결과 포맷팅"""
    formatted = []
    total_chars = 0

    for i, result in enumerate(results, 1):
        # 다양한 키에서 텍스트 추출
        text = (
            result.get("text") or
            result.get("content") or
            result.get("summary") or
            str(result)
        )[:500]

        # 점수 추출
        score = result.get("score", result.get("relevance_score", "N/A"))

        # 제목 추출
        title = result.get("title", result.get("name", f"결과 {i}"))

        entry = f"[{title}] (점수: {score})\n{text}\n"

        if total_chars + len(entry) > max_chars:
            break

        formatted.append(entry)
        total_chars += len(entry)

    return "\n".join(formatted) if formatted else "검색 결과 없음"


def _generate_alternative_query(query: str) -> str:
    """대안 검색어 생성 (간단한 규칙 기반)"""
    # 너무 긴 쿼리는 핵심만
    if len(query) > 50:
        # 첫 문장만 사용
        return query.split(".")[0].split("?")[0][:50]

    # 짧은 쿼리는 키워드 확장 시도
    legal_keywords = ["법", "조", "규정", "판례", "조항"]
    has_legal_keyword = any(k in query for k in legal_keywords)

    if not has_legal_keyword and len(query) < 20:
        return query + " 법률"

    return query


def quick_evaluate(results: List[Dict[str, Any]], min_score: float = 0.5) -> bool:
    """
    빠른 결과 평가 (LLM 호출 없이)

    점수 기반으로 결과가 유용한지 빠르게 판단

    Args:
        results: 검색 결과 목록
        min_score: 최소 허용 점수

    Returns:
        결과가 유용한지 여부
    """
    if not results:
        return False

    # 평균 점수 계산
    scores = []
    for result in results:
        score = result.get("score", result.get("relevance_score"))
        if isinstance(score, (int, float)):
            scores.append(float(score))

    if not scores:
        return True  # 점수 정보가 없으면 일단 사용

    avg_score = sum(scores) / len(scores)
    return avg_score >= min_score
