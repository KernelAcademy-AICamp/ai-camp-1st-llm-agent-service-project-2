"""
V2 Sentencing Router - Phase 3

양형기준 조회 및 예측 API

특징:
- 대법원 양형기준에 따른 형량 예측
- 범죄 유형별 기본 형량 범위 제공
- 양형인자 (유리/불리) 기반 조정
- 집행유예 가능성 계산

엔드포인트:
- POST /v2/sentencing/estimate - 양형 예측
- GET /v2/sentencing/guidelines/{crime_type} - 양형기준 조회
- GET /v2/sentencing/factors - 양형인자 목록 조회
- GET /v2/sentencing/health - 헬스체크
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/sentencing", tags=["sentencing-v2"])


# ===== Request/Response Models =====

class SentencingFactors(BaseModel):
    """양형인자"""
    favorable: List[str] = Field(default_factory=list, description="유리한 정상 (감경 요소)")
    unfavorable: List[str] = Field(default_factory=list, description="불리한 정상 (가중 요소)")


class EstimateSentenceRequest(BaseModel):
    """양형 예측 요청"""
    crime_type: str = Field(..., description="범죄 유형 코드")
    sentencing_factors: SentencingFactors = Field(
        default_factory=SentencingFactors,
        description="양형인자"
    )


class EstimateSentenceResponse(BaseModel):
    """양형 예측 응답"""
    range: str = Field(..., description="예상 형량 범위 (예: '6개월 ~ 2년')")
    suspended_probability: float = Field(..., description="집행유예 가능성 (0.0 ~ 1.0)")
    reasoning: Optional[str] = Field(None, description="산정 근거")
    crime_type: str = Field(..., description="범죄 유형")
    factors_applied: SentencingFactors = Field(..., description="적용된 양형인자")
    timestamp: str = Field(..., description="처리 시간")


class SentencingGuideline(BaseModel):
    """양형기준"""
    crime_type: str = Field(..., description="범죄 유형 코드")
    crime_label: str = Field(..., description="범죄 유형 명칭")
    base_range_min: int = Field(..., description="기본 형량 최소 (개월)")
    base_range_max: int = Field(..., description="기본 형량 최대 (개월)")
    suspended_eligible: bool = Field(..., description="집행유예 가능 여부")
    description: str = Field(..., description="설명")


class FactorOptions(BaseModel):
    """양형인자 옵션"""
    favorable: List[str] = Field(..., description="유리한 정상 목록")
    unfavorable: List[str] = Field(..., description="불리한 정상 목록")


# ===== 양형기준 데이터 =====

# 범죄 유형별 기본 형량 범위 (개월 단위)
CRIME_BASE_RANGES: Dict[str, Dict] = {
    "theft": {
        "label": "절도",
        "min": 6,
        "max": 36,
        "suspended_eligible": True,
        "description": "타인의 재물을 절취하는 범죄"
    },
    "fraud": {
        "label": "사기",
        "min": 12,
        "max": 60,
        "suspended_eligible": True,
        "description": "사람을 기망하여 재물을 편취하는 범죄"
    },
    "assault": {
        "label": "폭행/상해",
        "min": 6,
        "max": 24,
        "suspended_eligible": True,
        "description": "타인의 신체에 폭행 또는 상해를 가하는 범죄"
    },
    "embezzlement": {
        "label": "횡령/배임",
        "min": 12,
        "max": 60,
        "suspended_eligible": True,
        "description": "타인의 재물을 보관하는 자가 그 재물을 횡령하거나 반환을 거부하는 범죄"
    },
    "drug": {
        "label": "마약",
        "min": 12,
        "max": 60,
        "suspended_eligible": True,
        "description": "마약류 관리에 관한 법률 위반 범죄"
    },
    "dui": {
        "label": "음주운전",
        "min": 6,
        "max": 24,
        "suspended_eligible": True,
        "description": "도로교통법상 음주운전 범죄"
    },
    "sex_crime": {
        "label": "성범죄",
        "min": 24,
        "max": 120,
        "suspended_eligible": False,
        "description": "성폭력 범죄의 처벌 등에 관한 특례법 위반 범죄"
    },
    "murder": {
        "label": "살인",
        "min": 60,
        "max": 180,
        "suspended_eligible": False,
        "description": "사람을 살해하는 범죄"
    },
}

# 양형인자 옵션
FACTOR_OPTIONS = {
    "favorable": [
        "초범",
        "반성",
        "피해회복",
        "합의",
        "자수",
        "생계형 범죄",
        "우발적 범행",
        "심신미약",
        "형사처벌 불원",
        "선처 탄원",
    ],
    "unfavorable": [
        "동종전과",
        "계획적 범행",
        "피해 중대",
        "도주 시도",
        "증거 인멸",
        "범행 후 태도 불량",
        "특수관계 이용",
        "다수 피해자",
        "범행 수법 불량",
        "반성 없음",
    ],
}


# ===== Helper Functions =====

def calculate_sentence_estimate(
    crime_type: str,
    factors: SentencingFactors
) -> Dict:
    """양형 예측 계산"""
    # 기본 범위 조회
    base = CRIME_BASE_RANGES.get(crime_type)
    if not base:
        base = {"min": 6, "max": 36, "suspended_eligible": True, "label": crime_type}

    base_min = base["min"]
    base_max = base["max"]

    # 양형인자 개수
    favorable_count = len(factors.favorable)
    unfavorable_count = len(factors.unfavorable)

    # 조정 계수 계산 (유리한 인자가 많으면 감형)
    adjustment = (favorable_count - unfavorable_count) * 0.1

    # 형량 조정
    adjusted_min = max(base_min * (1 - adjustment), 1)
    adjusted_max = max(base_max * (1 - adjustment), adjusted_min + 6)

    # 집행유예 확률 계산
    suspended_prob = 0.5
    if base.get("suspended_eligible", True):
        if favorable_count > unfavorable_count:
            suspended_prob = min(0.9, 0.5 + favorable_count * 0.1)
        elif unfavorable_count > favorable_count:
            suspended_prob = max(0.1, 0.5 - unfavorable_count * 0.1)

        # 형량이 3년 이상이면 집행유예 불가능성 증가
        if adjusted_max > 36:
            suspended_prob = min(suspended_prob, 0.3)
    else:
        # 집행유예 불가 범죄
        suspended_prob = 0.0

    # 형량 범위 문자열 생성
    range_str = format_sentence_range(adjusted_min, adjusted_max)

    # 산정 근거 생성
    crime_label = base.get("label", crime_type)
    reasoning = (
        f"{crime_label} 범죄에 대해 대법원 양형기준을 적용하였습니다. "
        f"유리한 정상 {favorable_count}개, 불리한 정상 {unfavorable_count}개를 고려하여 "
        f"예상 형량을 산정하였습니다."
    )

    if not base.get("suspended_eligible", True):
        reasoning += " 해당 범죄는 집행유예 선고가 제한되는 범죄입니다."

    return {
        "range": range_str,
        "suspended_probability": round(suspended_prob, 2),
        "reasoning": reasoning,
        "crime_type": crime_type,
        "adjusted_min": adjusted_min,
        "adjusted_max": adjusted_max,
    }


def format_sentence_range(min_months: float, max_months: float) -> str:
    """형량 범위를 문자열로 포맷"""
    def format_months(months: float) -> str:
        months = round(months)
        if months >= 12:
            years = months // 12
            remaining = months % 12
            if remaining > 0:
                return f"{years}년 {remaining}개월"
            return f"{years}년"
        return f"{months}개월"

    return f"{format_months(min_months)} ~ {format_months(max_months)}"


# ===== API Endpoints =====

@router.post("/estimate", response_model=EstimateSentenceResponse)
async def estimate_sentence(request: EstimateSentenceRequest):
    """
    양형 예측

    범죄 유형과 양형인자를 기반으로 예상 형량을 계산합니다.
    대법원 양형기준을 참고하여 산정됩니다.

    Args:
        request: 양형 예측 요청 (범죄 유형, 양형인자)

    Returns:
        예상 형량 범위 및 집행유예 가능성
    """
    try:
        logger.info(f"[v2/sentencing/estimate] crime_type={request.crime_type}")

        # 양형 예측 계산
        result = calculate_sentence_estimate(
            crime_type=request.crime_type,
            factors=request.sentencing_factors
        )

        return EstimateSentenceResponse(
            range=result["range"],
            suspended_probability=result["suspended_probability"],
            reasoning=result["reasoning"],
            crime_type=request.crime_type,
            factors_applied=request.sentencing_factors,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"[v2/sentencing/estimate] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/guidelines/{crime_type}", response_model=SentencingGuideline)
async def get_sentencing_guideline(crime_type: str):
    """
    양형기준 조회

    특정 범죄 유형에 대한 양형기준을 조회합니다.

    Args:
        crime_type: 범죄 유형 코드

    Returns:
        해당 범죄의 양형기준 정보
    """
    try:
        logger.info(f"[v2/sentencing/guidelines] crime_type={crime_type}")

        base = CRIME_BASE_RANGES.get(crime_type)
        if not base:
            raise HTTPException(
                status_code=404,
                detail=f"양형기준을 찾을 수 없습니다: {crime_type}"
            )

        return SentencingGuideline(
            crime_type=crime_type,
            crime_label=base["label"],
            base_range_min=base["min"],
            base_range_max=base["max"],
            suspended_eligible=base.get("suspended_eligible", True),
            description=base.get("description", "")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[v2/sentencing/guidelines] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/guidelines")
async def list_sentencing_guidelines():
    """
    전체 양형기준 목록 조회

    지원되는 모든 범죄 유형과 양형기준을 조회합니다.

    Returns:
        전체 양형기준 목록
    """
    try:
        logger.info("[v2/sentencing/guidelines] Listing all guidelines")

        guidelines = []
        for crime_type, base in CRIME_BASE_RANGES.items():
            guidelines.append({
                "crime_type": crime_type,
                "crime_label": base["label"],
                "base_range_min": base["min"],
                "base_range_max": base["max"],
                "suspended_eligible": base.get("suspended_eligible", True),
                "description": base.get("description", "")
            })

        return {
            "count": len(guidelines),
            "guidelines": guidelines,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"[v2/sentencing/guidelines] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/factors", response_model=FactorOptions)
async def get_factor_options():
    """
    양형인자 목록 조회

    유리한 정상 및 불리한 정상 양형인자 옵션을 조회합니다.

    Returns:
        양형인자 옵션 목록
    """
    try:
        logger.info("[v2/sentencing/factors] Getting factor options")

        return FactorOptions(
            favorable=FACTOR_OPTIONS["favorable"],
            unfavorable=FACTOR_OPTIONS["unfavorable"]
        )

    except Exception as e:
        logger.error(f"[v2/sentencing/factors] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/health")
async def sentencing_health():
    """
    Sentencing v2 헬스체크

    Returns:
        상태 정보
    """
    return {
        "status": "healthy",
        "version": "v2",
        "engine": "Rule-based + Supreme Court Guidelines",
        "features": [
            "sentence_estimation",
            "suspended_probability",
            "factor_adjustment",
            "guideline_lookup"
        ],
        "supported_crimes": list(CRIME_BASE_RANGES.keys()),
        "factor_count": {
            "favorable": len(FACTOR_OPTIONS["favorable"]),
            "unfavorable": len(FACTOR_OPTIONS["unfavorable"])
        },
        "timestamp": datetime.now().isoformat()
    }
