"""
Database Query MCP Tools

MCP 기반 사용자 데이터베이스 조회 도구

도구 목록:
- query_user_criminal_cases: 범용 형사 사건 조회 (정렬, 필터, 제한)
- get_criminal_case_detail: 특정 사건 상세 조회
- get_user_case_statistics: 사용자 사건 통계 조회

이 도구를 사용하면 LLM이 다양한 질문에 대해 적절한 파라미터를 생성하여
하나의 도구로 여러 유형의 조회를 수행할 수 있습니다.

예시:
- "형량이 가장 적은 사건" → order_by="expected_sentence_score", order="asc", limit=1
- "형량이 가장 높은 사건" → order_by="expected_sentence_score", order="desc", limit=1
- "절도 사건만 보여줘" → crime_type_filter="절도"
- "최근 등록한 사건 3개" → order_by="created_at", order="desc", limit=3
"""

from typing import Dict, Any, Optional, List
import logging
import re

logger = logging.getLogger(__name__)


def _calculate_sentence_score(expected_sentence: Dict) -> float:
    """
    예상 양형 점수 계산

    점수가 높을수록 형량이 무거움
    - 집행유예 확률이 낮을수록 높은 점수
    - 형량 범위의 숫자가 클수록 높은 점수
    """
    if not expected_sentence:
        return 0.0

    score = 0.0

    # 집행유예 확률 반영 (낮을수록 심각)
    prob = expected_sentence.get("suspended_probability", 0.5)
    if isinstance(prob, (int, float)):
        score += (1 - prob) * 50

    # 형량 범위에서 숫자 추출
    range_str = expected_sentence.get("range", "")
    if range_str:
        numbers = re.findall(r'\d+', str(range_str))
        if numbers:
            # 평균값 사용
            avg_num = sum(int(n) for n in numbers) / len(numbers)
            score += avg_num

    return score


async def query_user_criminal_cases(
    user_id: str,
    order_by: str = "created_at",
    order: str = "desc",
    limit: int = 10,
    offset: int = 0,
    crime_type_filter: Optional[str] = None,
    stage_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    사용자의 형사 사건을 유연하게 조회합니다.

    LLM이 사용자 질문을 분석하여 적절한 파라미터를 생성합니다.

    Args:
        user_id: 사용자 UUID (필수)
        order_by: 정렬 기준 (created_at, expected_sentence_score, case_name, crime_type)
            - created_at: 생성일 기준
            - expected_sentence_score: 예상 형량 점수 기준 (형량 심각도)
            - case_name: 사건명 기준
            - crime_type: 범죄 유형 기준
        order: 정렬 순서 (asc: 오름차순, desc: 내림차순)
            - 형량이 가장 적은 사건: order_by="expected_sentence_score", order="asc"
            - 형량이 가장 높은 사건: order_by="expected_sentence_score", order="desc"
        limit: 반환할 결과 수 (기본값: 10)
        offset: 건너뛸 결과 수 (페이지네이션용)
        crime_type_filter: 범죄 유형 필터 (예: "절도", "사기", "폭행")
        stage_filter: 진행 단계 필터 (COMPLAINT, INVESTIGATION, PROSECUTION, TRIAL, JUDGMENT, CLOSED)

    Returns:
        {
            "success": True,
            "count": int,
            "total": int,
            "cases": [
                {
                    "id": str,
                    "case_name": str,
                    "crime_type": str,
                    "summary": str,
                    "stage": str,
                    "expected_sentence": dict,
                    "expected_sentence_score": float,
                    "created_at": str
                }
            ],
            "query_info": {
                "order_by": str,
                "order": str,
                "filters_applied": list
            }
        }

    사용 예시:
        - "내 형사 사건 목록 보여줘"
          → query_user_criminal_cases(user_id, order_by="created_at", order="desc")

        - "형량이 가장 적은 사건은?"
          → query_user_criminal_cases(user_id, order_by="expected_sentence_score", order="asc", limit=1)

        - "형량이 가장 높은 사건은?"
          → query_user_criminal_cases(user_id, order_by="expected_sentence_score", order="desc", limit=1)

        - "절도 사건만 보여줘"
          → query_user_criminal_cases(user_id, crime_type_filter="절도")

        - "수사 중인 사건들"
          → query_user_criminal_cases(user_id, stage_filter="INVESTIGATION")
    """
    try:
        from apps.ai_service.services.criminal_case_service import CriminalCaseService
        from apps.ai_service.models.database import get_db

        async for db in get_db():
            service = CriminalCaseService(db)

            # 전체 사건 조회 (필터링을 위해)
            all_cases = await service.list_cases_full(user_id, limit=500)

            if not all_cases:
                return {
                    "success": True,
                    "count": 0,
                    "total": 0,
                    "cases": [],
                    "message": "저장된 형사 사건이 없습니다.",
                    "query_info": {
                        "order_by": order_by,
                        "order": order,
                        "filters_applied": []
                    }
                }

            # 필터 적용
            filtered_cases = all_cases
            filters_applied = []

            if crime_type_filter:
                filtered_cases = [
                    c for c in filtered_cases
                    if crime_type_filter.lower() in (c.crime_type or "").lower()
                ]
                filters_applied.append(f"crime_type={crime_type_filter}")

            if stage_filter:
                filtered_cases = [
                    c for c in filtered_cases
                    if c.stage.value == stage_filter
                ]
                filters_applied.append(f"stage={stage_filter}")

            # 점수 계산 및 변환
            cases_with_score = []
            for case in filtered_cases:
                sentence_score = _calculate_sentence_score(case.expected_sentence)
                cases_with_score.append({
                    "id": case.id,
                    "case_name": case.case_name,
                    "crime_type": case.crime_type,
                    "summary": case.summary[:200] if case.summary else "",
                    "stage": case.stage.value,
                    "expected_sentence": case.expected_sentence,
                    "expected_sentence_score": sentence_score,
                    "sentencing_factors": case.sentencing_factors,
                    "defense_strategies": case.defense_strategies[:3] if case.defense_strategies else [],
                    "created_at": case.created_at.isoformat() if case.created_at else None,
                })

            # 정렬
            reverse = (order.lower() == "desc")

            if order_by == "expected_sentence_score":
                cases_with_score.sort(
                    key=lambda x: x.get("expected_sentence_score", 0),
                    reverse=reverse
                )
            elif order_by == "created_at":
                cases_with_score.sort(
                    key=lambda x: x.get("created_at") or "",
                    reverse=reverse
                )
            elif order_by == "case_name":
                cases_with_score.sort(
                    key=lambda x: x.get("case_name") or "",
                    reverse=reverse
                )
            elif order_by == "crime_type":
                cases_with_score.sort(
                    key=lambda x: x.get("crime_type") or "",
                    reverse=reverse
                )

            # 페이지네이션 적용
            total = len(cases_with_score)
            paginated = cases_with_score[offset:offset + limit]

            return {
                "success": True,
                "count": len(paginated),
                "total": total,
                "cases": paginated,
                "query_info": {
                    "order_by": order_by,
                    "order": order,
                    "limit": limit,
                    "offset": offset,
                    "filters_applied": filters_applied
                }
            }

    except Exception as e:
        logger.error(f"query_user_criminal_cases error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "total": 0,
            "cases": []
        }


async def get_criminal_case_detail(
    user_id: str,
    case_id: str,
) -> Dict[str, Any]:
    """
    특정 형사 사건의 상세 정보를 조회합니다.

    Args:
        user_id: 사용자 UUID
        case_id: 사건 UUID

    Returns:
        {
            "success": True,
            "case": {
                "id": str,
                "case_name": str,
                "crime_type": str,
                "summary": str,
                "stage": str,
                "crime_elements": dict,
                "sentencing_factors": dict,
                "expected_sentence": dict,
                "defense_strategies": list,
                "related_precedents": list,
                "schedules": list,
                "conditions": list,
                "uploaded_files": list,
                "created_at": str,
                "updated_at": str
            }
        }
    """
    try:
        from apps.ai_service.services.criminal_case_service import CriminalCaseService
        from apps.ai_service.models.database import get_db

        async for db in get_db():
            service = CriminalCaseService(db)
            case = await service.get_case(case_id, user_id)

            if not case:
                return {
                    "success": False,
                    "error": "사건을 찾을 수 없습니다.",
                    "case": None
                }

            return {
                "success": True,
                "case": {
                    "id": case.id,
                    "case_name": case.case_name,
                    "crime_type": case.crime_type,
                    "summary": case.summary,
                    "stage": case.stage.value,
                    "crime_elements": case.crime_elements,
                    "sentencing_factors": case.sentencing_factors,
                    "expected_sentence": case.expected_sentence,
                    "defense_strategies": case.defense_strategies,
                    "related_precedents": case.related_precedents,
                    "schedules": case.schedules,
                    "conditions": case.conditions,
                    "uploaded_files": case.uploaded_files,
                    "created_at": case.created_at.isoformat() if case.created_at else None,
                    "updated_at": case.updated_at.isoformat() if case.updated_at else None,
                }
            }

    except Exception as e:
        logger.error(f"get_criminal_case_detail error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "case": None
        }


async def get_user_case_statistics(
    user_id: str,
) -> Dict[str, Any]:
    """
    사용자의 형사 사건 통계를 조회합니다.

    Args:
        user_id: 사용자 UUID

    Returns:
        {
            "success": True,
            "statistics": {
                "total_cases": int,
                "by_stage": {"COMPLAINT": 2, "INVESTIGATION": 1, ...},
                "by_crime_type": {"절도": 2, "사기": 1, ...},
                "sentence_summary": {
                    "highest": {"case_name": str, "score": float, "range": str},
                    "lowest": {"case_name": str, "score": float, "range": str},
                    "average_score": float
                }
            }
        }
    """
    try:
        from apps.ai_service.services.criminal_case_service import CriminalCaseService
        from apps.ai_service.models.database import get_db

        async for db in get_db():
            service = CriminalCaseService(db)

            # 전체 사건 조회
            all_cases = await service.list_cases_full(user_id, limit=500)

            if not all_cases:
                return {
                    "success": True,
                    "statistics": {
                        "total_cases": 0,
                        "by_stage": {},
                        "by_crime_type": {},
                        "sentence_summary": None
                    },
                    "message": "저장된 형사 사건이 없습니다."
                }

            # 단계별 집계
            by_stage = {}
            for case in all_cases:
                stage = case.stage.value
                by_stage[stage] = by_stage.get(stage, 0) + 1

            # 범죄 유형별 집계
            by_crime_type = {}
            for case in all_cases:
                crime_type = case.crime_type or "미분류"
                by_crime_type[crime_type] = by_crime_type.get(crime_type, 0) + 1

            # 양형 통계
            cases_with_sentence = []
            for case in all_cases:
                if case.expected_sentence:
                    score = _calculate_sentence_score(case.expected_sentence)
                    cases_with_sentence.append({
                        "case_name": case.case_name,
                        "score": score,
                        "range": case.expected_sentence.get("range", ""),
                        "suspended_probability": case.expected_sentence.get("suspended_probability", 0)
                    })

            sentence_summary = None
            if cases_with_sentence:
                sorted_by_score = sorted(cases_with_sentence, key=lambda x: x["score"])
                scores = [c["score"] for c in cases_with_sentence]

                sentence_summary = {
                    "highest": sorted_by_score[-1] if sorted_by_score else None,
                    "lowest": sorted_by_score[0] if sorted_by_score else None,
                    "average_score": sum(scores) / len(scores) if scores else 0
                }

            return {
                "success": True,
                "statistics": {
                    "total_cases": len(all_cases),
                    "by_stage": by_stage,
                    "by_crime_type": by_crime_type,
                    "sentence_summary": sentence_summary
                }
            }

    except Exception as e:
        logger.error(f"get_user_case_statistics error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "statistics": None
        }
