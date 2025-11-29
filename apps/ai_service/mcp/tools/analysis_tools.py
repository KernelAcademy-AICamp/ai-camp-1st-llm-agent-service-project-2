"""
Analysis MCP Tools

Phase 4 - Week 12: 분석 관련 MCP Tools

도구 목록:
- analyze_risks: 리스크 분석
- calculate_metrics: 메트릭 계산
- compare_documents: 문서 비교
- generate_report: 보고서 생성

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


async def analyze_risks(
    content: str,
    doc_type: str = "contract"
) -> List[Dict[str, Any]]:
    """
    리스크 분석

    문서에서 법적/비즈니스 리스크를 식별합니다.

    Args:
        content: 분석할 문서 내용
        doc_type: 문서 타입 (contract, statute, case 등)

    Returns:
        리스크 리스트
        - risk_type: 리스크 유형
        - description: 설명
        - severity: 심각도 (CRITICAL, HIGH, MEDIUM, LOW, INFO)
        - recommendation: 권장 조치
        - clause_reference: 관련 조항
    """
    logger.info(f"Analyzing risks for document type: {doc_type}")

    try:
        from libs.rag_core.llm.llm_client import get_llm

        llm = get_llm()

        prompt = f"""다음 {doc_type} 문서에서 법적/비즈니스 리스크를 분석하세요.

문서 내용:
{content[:5000]}

리스크를 JSON 배열 형식으로 제공하세요:
[
    {{
        "risk_type": "법적|계약|재무|운영|규정|기타",
        "description": "리스크 설명",
        "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
        "recommendation": "권장 조치",
        "clause_reference": "관련 조항 (예: 제5조 3항)"
    }},
    ...
]

심각도 기준:
- CRITICAL: 즉시 조치 필요 (법적 책임, 중대 손해)
- HIGH: 높은 주의 필요 (상당한 위험)
- MEDIUM: 검토 권장 (일반적 위험)
- LOW: 참고 수준 (경미한 위험)
- INFO: 정보성 (개선 가능)"""

        result = await llm.ainvoke(prompt)

        # 기본 리스크 분석 (실제로는 LLM 응답 파싱)
        risks = []

        # 휴리스틱 기반 리스크 감지
        content_lower = content.lower()

        if "책임" in content and "면제" in content:
            risks.append({
                "risk_type": "법적",
                "description": "책임 면제 조항 발견",
                "severity": "MEDIUM",
                "recommendation": "면제 조항의 범위와 유효성 검토 필요",
                "clause_reference": ""
            })

        if "위약금" in content or "손해배상" in content:
            risks.append({
                "risk_type": "재무",
                "description": "위약금/손해배상 조항 존재",
                "severity": "HIGH",
                "recommendation": "배상 한도 및 조건 검토 권장",
                "clause_reference": ""
            })

        if "종료" in content or "해지" in content:
            risks.append({
                "risk_type": "계약",
                "description": "계약 종료/해지 조항 발견",
                "severity": "MEDIUM",
                "recommendation": "종료 조건 및 절차 확인 필요",
                "clause_reference": ""
            })

        if not risks:
            risks.append({
                "risk_type": "INFO",
                "description": "특별한 리스크가 감지되지 않음",
                "severity": "INFO",
                "recommendation": "전문가 검토 권장",
                "clause_reference": ""
            })

        return risks

    except Exception as e:
        logger.error(f"Error analyzing risks: {e}")
        return [{
            "error": str(e),
            "risk_type": "error",
            "description": "분석 실패",
            "severity": "INFO",
            "recommendation": "",
            "clause_reference": ""
        }]


async def calculate_metrics(
    task: str,
    result: Dict[str, Any],
    ground_truth: Optional[str] = None
) -> Dict[str, Any]:
    """
    결과 평가 메트릭 계산

    Args:
        task: 작업 유형 (summarize, analyze, extract 등)
        result: 평가할 결과
        ground_truth: 정답 (있는 경우)

    Returns:
        메트릭 결과
        - quality: 품질 점수 (0-1)
        - latency_normalized: 정규화된 지연 시간
        - cost_normalized: 정규화된 비용
        - coverage: 커버리지 (있는 경우)
    """
    logger.info(f"Calculating metrics for task: {task}")

    try:
        result_text = str(result.get("result", result))

        # 기본 메트릭 계산
        word_count = len(result_text.split())

        # 품질 점수 (휴리스틱)
        quality = 0.7  # 기본값

        if word_count > 50:
            quality += 0.1
        if word_count > 200:
            quality += 0.1

        # ground_truth가 있으면 비교
        if ground_truth:
            # 간단한 유사도 계산 (Jaccard)
            result_words = set(result_text.split())
            truth_words = set(ground_truth.split())

            if truth_words:
                overlap = len(result_words & truth_words)
                union = len(result_words | truth_words)
                similarity = overlap / union if union > 0 else 0
                quality = min(1.0, quality * 0.5 + similarity * 0.5)

        return {
            "quality": round(quality, 3),
            "latency_normalized": 0.5,  # 실제로는 측정값 사용
            "cost_normalized": 0.5,  # 실제로는 계산값 사용
            "word_count": word_count,
            "has_ground_truth": ground_truth is not None
        }

    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        return {
            "error": str(e),
            "quality": 0.0,
            "latency_normalized": 0.0,
            "cost_normalized": 0.0
        }


async def compare_documents(
    doc1: str,
    doc2: str,
    comparison_type: str = "similarity"
) -> Dict[str, Any]:
    """
    문서 비교

    Args:
        doc1: 첫 번째 문서
        doc2: 두 번째 문서
        comparison_type: 비교 유형 (similarity, diff, clause)

    Returns:
        비교 결과
        - similarity_score: 유사도 점수 (0-1)
        - differences: 차이점 리스트
        - common_elements: 공통 요소 리스트
    """
    logger.info(f"Comparing documents, type: {comparison_type}")

    try:
        # 단어 기반 비교
        words1 = set(doc1.split())
        words2 = set(doc2.split())

        intersection = words1 & words2
        union = words1 | words2

        similarity = len(intersection) / len(union) if union else 0

        # 차이점 계산
        only_in_doc1 = words1 - words2
        only_in_doc2 = words2 - words1

        return {
            "similarity_score": round(similarity, 3),
            "differences": {
                "only_in_doc1": list(only_in_doc1)[:20],  # 상위 20개만
                "only_in_doc2": list(only_in_doc2)[:20]
            },
            "common_elements": list(intersection)[:20],
            "doc1_word_count": len(words1),
            "doc2_word_count": len(words2)
        }

    except Exception as e:
        logger.error(f"Error comparing documents: {e}")
        return {
            "error": str(e),
            "similarity_score": 0.0,
            "differences": {},
            "common_elements": []
        }


async def generate_report(
    analysis_results: Dict[str, Any],
    report_type: str = "summary",
    format: str = "markdown"
) -> Dict[str, Any]:
    """
    보고서 생성

    Args:
        analysis_results: 분석 결과
        report_type: 보고서 유형 (summary, detailed, executive)
        format: 출력 형식 (markdown, html, plain)

    Returns:
        보고서
        - content: 보고서 내용
        - format: 형식
        - sections: 섹션 목록
    """
    logger.info(f"Generating report, type: {report_type}, format: {format}")

    try:
        from libs.rag_core.llm.llm_client import get_llm

        llm = get_llm()

        prompt = f"""다음 분석 결과를 바탕으로 {report_type} 보고서를 작성하세요.

분석 결과:
{str(analysis_results)[:3000]}

보고서 형식: {format}
보고서 유형: {report_type}

{format} 형식으로 보고서를 작성하세요."""

        result = await llm.ainvoke(prompt)
        content = result.content if hasattr(result, 'content') else str(result)

        # 섹션 추출 (마크다운 헤더 기반)
        sections = []
        for line in content.split('\n'):
            if line.startswith('#'):
                sections.append(line.strip('# ').strip())

        return {
            "content": content,
            "format": format,
            "report_type": report_type,
            "sections": sections,
            "word_count": len(content.split())
        }

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return {
            "error": str(e),
            "content": "",
            "format": format,
            "sections": []
        }


async def aggregate_statistics(
    data: List[Dict[str, Any]],
    group_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    통계 집계

    Args:
        data: 집계할 데이터 리스트
        group_by: 그룹화 기준 필드

    Returns:
        통계 결과
        - total_count: 총 개수
        - groups: 그룹별 통계 (있는 경우)
        - averages: 평균값들
    """
    logger.info(f"Aggregating statistics, group_by: {group_by}")

    try:
        total_count = len(data)

        if not data:
            return {
                "total_count": 0,
                "groups": {},
                "averages": {}
            }

        # 그룹별 집계
        groups = {}
        if group_by:
            for item in data:
                key = item.get(group_by, "unknown")
                if key not in groups:
                    groups[key] = []
                groups[key].append(item)

            # 그룹 카운트로 변환
            groups = {k: len(v) for k, v in groups.items()}

        # 숫자 필드 평균 계산
        averages = {}
        numeric_fields = set()

        for item in data:
            for key, value in item.items():
                if isinstance(value, (int, float)):
                    numeric_fields.add(key)

        for field in numeric_fields:
            values = [item.get(field, 0) for item in data if isinstance(item.get(field), (int, float))]
            if values:
                averages[field] = sum(values) / len(values)

        return {
            "total_count": total_count,
            "groups": groups,
            "averages": averages
        }

    except Exception as e:
        logger.error(f"Error aggregating statistics: {e}")
        return {
            "error": str(e),
            "total_count": 0,
            "groups": {},
            "averages": {}
        }
