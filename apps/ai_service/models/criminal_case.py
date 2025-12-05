"""
Criminal Case Models (Pydantic)
형사 사건 Pydantic 모델
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime, date
from enum import Enum


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


class ScheduleItem(BaseModel):
    """일정 항목"""
    date: date
    title: str
    schedule_type: ScheduleType
    description: Optional[str] = None
    is_completed: bool = False


class CrimeElement(BaseModel):
    """구성요건 항목"""
    element: str  # 요건명
    description: str  # 설명
    fulfilled: bool  # 충족 여부


class CrimeElements(BaseModel):
    """구성요건 분석 결과"""
    objective: List[CrimeElement] = Field(default_factory=list)  # 객관적 구성요건
    subjective: List[CrimeElement] = Field(default_factory=list)  # 주관적 구성요건


class SentencingFactors(BaseModel):
    """양형인자"""
    favorable: List[str] = Field(default_factory=list)  # 유리한 정상
    unfavorable: List[str] = Field(default_factory=list)  # 불리한 정상


class ExpectedSentence(BaseModel):
    """예상 양형"""
    range: str  # 예상 형량 범위
    suspended_probability: float = 0.0  # 집행유예 가능성
    reasoning: Optional[str] = None  # 산정 근거


class CriminalPrecedent(BaseModel):
    """형사 판례"""
    case_number: str  # 사건번호
    court: str  # 법원
    date: str  # 판결일
    crime_type: str  # 범죄 유형
    sentence: str  # 선고 형량
    summary: str  # 요약
    relevance: float  # 관련도


class UploadedFile(BaseModel):
    """업로드된 파일 정보"""
    filename: str
    file_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None


# ============================================
# Request/Response Models
# ============================================

class CriminalCaseCreate(BaseModel):
    """사건 생성 요청"""
    case_name: str
    summary: Optional[str] = None
    crime_type: str
    stage: CriminalStage = CriminalStage.COMPLAINT
    conditions: List[str] = Field(default_factory=list)
    schedules: List[ScheduleItem] = Field(default_factory=list)


class CriminalCaseUpdate(BaseModel):
    """사건 수정 요청"""
    case_name: Optional[str] = None
    summary: Optional[str] = None
    stage: Optional[CriminalStage] = None
    conditions: Optional[List[str]] = None
    schedules: Optional[List[ScheduleItem]] = None
    crime_elements: Optional[Dict] = None
    sentencing_factors: Optional[Dict] = None
    expected_sentence: Optional[Dict] = None
    defense_strategies: Optional[List[str]] = None
    related_precedents: Optional[List[Dict]] = None


class CriminalCaseResponse(BaseModel):
    """사건 응답"""
    id: str
    user_id: str
    case_name: str
    summary: str
    crime_type: str
    crime_elements: Dict
    sentencing_factors: Dict
    expected_sentence: Dict
    defense_strategies: List[str]
    related_precedents: List[Dict]
    stage: CriminalStage
    schedules: List[Dict]
    conditions: List[str]
    uploaded_files: List[Dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CriminalCaseListItem(BaseModel):
    """사건 목록 아이템"""
    id: str
    case_name: str
    crime_type: str
    stage: CriminalStage
    next_schedule: Optional[ScheduleItem] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduleItemCreate(BaseModel):
    """일정 생성 요청"""
    date: date
    title: str
    schedule_type: ScheduleType
    description: Optional[str] = None


class ScheduleItemResponse(BaseModel):
    """일정 응답"""
    id: str
    case_id: str
    date: date
    title: str
    schedule_type: ScheduleType
    description: Optional[str] = None
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Analysis Models (분석 결과)
# ============================================

class CriminalAnalysisResult(BaseModel):
    """형사 사건 분석 결과"""
    summary: str
    crime_type: str
    crime_elements: CrimeElements
    sentencing_factors: SentencingFactors
    expected_sentence: ExpectedSentence
    defense_strategies: List[str] = Field(default_factory=list)
    related_precedents: List[CriminalPrecedent] = Field(default_factory=list)


class CriminalCaseWithAnalysis(CriminalCaseCreate):
    """분석 결과가 포함된 사건 생성 요청"""
    crime_elements: Dict = Field(default_factory=dict)
    sentencing_factors: Dict = Field(default_factory=dict)
    expected_sentence: Dict = Field(default_factory=dict)
    defense_strategies: List[str] = Field(default_factory=list)
    related_precedents: List[Dict] = Field(default_factory=list)
    uploaded_files: List[Dict] = Field(default_factory=list)


# ============================================
# Dashboard Models (대시보드)
# ============================================

class DashboardSummary(BaseModel):
    """대시보드 요약"""
    total_cases: int
    cases_by_stage: Dict[str, int]
    upcoming_schedules: List[Dict]
    recommendations: List[Dict]
    primary_case: Optional[Dict] = None
    cases: List[CriminalCaseListItem] = Field(default_factory=list)


class SimilarCaseStatistics(BaseModel):
    """유사 사건 통계"""
    crime_type: str
    conditions: List[str]
    total_similar_cases: int
    distribution: Dict[str, float]  # suspended, fine, imprisonment, acquittal
