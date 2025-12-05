"""
형사법 분석 Pydantic 모델

Phase 1: CaseManagement 형사법 특화
- 구성요건 분석
- 양형인자 추출
- 양형 예측
- 변호 전략 제안
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class CriminalStage(str, Enum):
    """형사 절차 단계"""
    COMPLAINT = "COMPLAINT"  # 고소/고발/인지
    INVESTIGATION = "INVESTIGATION"  # 수사 진행
    PROSECUTION = "PROSECUTION"  # 기소
    TRIAL = "TRIAL"  # 공판
    JUDGMENT = "JUDGMENT"  # 판결
    CLOSED = "CLOSED"  # 종결


class ScheduleType(str, Enum):
    """일정 유형"""
    HEARING = "HEARING"  # 공판 기일
    SUBMISSION = "SUBMISSION"  # 서류 제출
    MEETING = "MEETING"  # 상담/회의
    DEADLINE = "DEADLINE"  # 기한
    POLICE = "POLICE"  # 경찰 출석
    PROSECUTOR = "PROSECUTOR"  # 검찰 출석


# =============================================================================
# 구성요건 분석
# =============================================================================

class CrimeElement(BaseModel):
    """범죄 구성요건 요소"""
    element: str = Field(..., description="구성요건 요소명")
    description: str = Field(..., description="구체적 설명")
    fulfilled: bool = Field(..., description="충족 여부")


class CrimeElements(BaseModel):
    """범죄 구성요건 전체"""
    objective: List[CrimeElement] = Field(
        default_factory=list,
        description="객관적 구성요건 (행위, 객체, 결과)"
    )
    subjective: List[CrimeElement] = Field(
        default_factory=list,
        description="주관적 구성요건 (고의, 과실, 목적)"
    )


# =============================================================================
# 양형인자
# =============================================================================

class SentencingFactors(BaseModel):
    """양형인자"""
    favorable: List[str] = Field(
        default_factory=list,
        description="유리한 정상 (초범, 반성, 피해회복 등)"
    )
    unfavorable: List[str] = Field(
        default_factory=list,
        description="불리한 정상 (동종전과, 계획적 범행 등)"
    )


# =============================================================================
# 양형 예측
# =============================================================================

class ExpectedSentence(BaseModel):
    """예상 양형"""
    range: str = Field(..., description="예상 형량 범위 (예: '징역 6월 ~ 1년')")
    suspended_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="집행유예 가능성 (0.0 ~ 1.0)"
    )
    reasoning: Optional[str] = Field(
        None,
        description="양형 산정 근거"
    )


# =============================================================================
# 판례
# =============================================================================

class CriminalPrecedent(BaseModel):
    """형사 판례"""
    case_number: str = Field(..., description="사건번호 (예: '2023도1234')")
    court: str = Field(..., description="법원 (예: '대법원')")
    date: str = Field(..., description="선고일")
    crime_type: str = Field(..., description="범죄 유형")
    sentence: str = Field(..., description="선고 형량")
    summary: str = Field(..., description="판례 요약")
    relevance: float = Field(..., ge=0.0, le=100.0, description="관련도 (%)")


# =============================================================================
# 분석 결과
# =============================================================================

class CriminalAnalysisResult(BaseModel):
    """형사 사건 분석 결과"""
    summary: str = Field(..., description="사건 요약")
    crime_type: str = Field(..., description="범죄 유형")
    crime_elements: CrimeElements = Field(
        default_factory=CrimeElements,
        description="구성요건 분석"
    )
    sentencing_factors: SentencingFactors = Field(
        default_factory=SentencingFactors,
        description="양형인자"
    )
    expected_sentence: ExpectedSentence = Field(..., description="예상 양형")
    defense_strategies: List[str] = Field(
        default_factory=list,
        description="변호 전략 제안"
    )
    related_precedents: List[CriminalPrecedent] = Field(
        default_factory=list,
        description="관련 판례"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "summary": "2024년 3월 서울 강남구 편의점에서 현금 50만원을 절취한 사건",
                "crime_type": "절도",
                "crime_elements": {
                    "objective": [
                        {
                            "element": "타인의 재물",
                            "description": "편의점 현금 50만원",
                            "fulfilled": True
                        },
                        {
                            "element": "절취행위",
                            "description": "야간에 점원 부재 시 금전함에서 절취",
                            "fulfilled": True
                        }
                    ],
                    "subjective": [
                        {
                            "element": "절취의 고의",
                            "description": "계획적 범행",
                            "fulfilled": True
                        }
                    ]
                },
                "sentencing_factors": {
                    "favorable": ["초범", "피해회복", "반성"],
                    "unfavorable": ["계획적 범행"]
                },
                "expected_sentence": {
                    "range": "징역 6월 ~ 1년",
                    "suspended_probability": 0.7,
                    "reasoning": "초범 + 피해회복으로 집행유예 가능성 높음"
                },
                "defense_strategies": [
                    "양형 감경 주장",
                    "피해회복 강조",
                    "반성 및 재범방지 의지 표명"
                ],
                "related_precedents": [
                    {
                        "case_number": "2023도1234",
                        "court": "대법원",
                        "date": "2023-11-15",
                        "crime_type": "절도",
                        "sentence": "징역 8월, 집행유예 2년",
                        "summary": "유사 절도 사건",
                        "relevance": 92.0
                    }
                ]
            }
        }


# =============================================================================
# API 요청/응답 스키마
# =============================================================================

class CriminalAnalyzeRequest(BaseModel):
    """형사 분석 요청"""
    crime_type: Optional[str] = Field(
        None,
        description="범죄 유형 (선택, 미지정시 자동 감지)"
    )


class CriminalAnalyzeResponse(BaseModel):
    """형사 분석 응답"""
    success: bool
    case_id: Optional[str] = None
    analysis: Optional[CriminalAnalysisResult] = None
    error: Optional[str] = None


# =============================================================================
# 일정 관리
# =============================================================================

class ScheduleItem(BaseModel):
    """일정 항목"""
    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    title: str = Field(..., description="일정 제목")
    schedule_type: ScheduleType = Field(..., description="일정 유형")
    description: Optional[str] = Field(None, description="상세 설명")
    is_completed: bool = Field(False, description="완료 여부")


# =============================================================================
# 사건 CRUD 스키마
# =============================================================================

class CriminalCaseCreate(BaseModel):
    """형사 사건 생성 요청"""
    case_name: str = Field(..., description="사건명")
    summary: Optional[str] = Field(None, description="사건 요약")
    crime_type: str = Field(..., description="범죄 유형")
    stage: CriminalStage = Field(
        CriminalStage.COMPLAINT,
        description="절차 단계"
    )
    conditions: List[str] = Field(
        default_factory=list,
        description="조건 태그 (초범, 피해회복 등)"
    )
    schedules: List[ScheduleItem] = Field(
        default_factory=list,
        description="일정 목록"
    )


class CriminalCaseUpdate(BaseModel):
    """형사 사건 수정 요청"""
    case_name: Optional[str] = None
    summary: Optional[str] = None
    stage: Optional[CriminalStage] = None
    conditions: Optional[List[str]] = None
    schedules: Optional[List[ScheduleItem]] = None


class CriminalCaseResponse(BaseModel):
    """형사 사건 응답"""
    id: str
    user_id: str
    case_name: str
    summary: str
    crime_type: str
    crime_elements: Dict[str, Any]
    sentencing_factors: Dict[str, Any]
    expected_sentence: Dict[str, Any]
    defense_strategies: List[str]
    related_precedents: List[Dict[str, Any]]
    stage: CriminalStage
    schedules: List[ScheduleItem]
    conditions: List[str]
    uploaded_files: List[Dict[str, Any]]
    created_at: str
    updated_at: str


class CriminalCaseListItem(BaseModel):
    """형사 사건 목록 아이템"""
    id: str
    case_name: str
    crime_type: str
    stage: CriminalStage
    next_schedule: Optional[ScheduleItem] = None
    created_at: str
