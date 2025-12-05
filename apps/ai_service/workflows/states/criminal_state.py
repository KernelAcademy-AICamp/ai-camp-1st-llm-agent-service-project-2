"""
Criminal Case Analysis State

형사 사건 분석 워크플로우 상태 정의

워크플로우 흐름:
1. detect_crime_node: 범죄 유형 감지
2. analyze_elements_node: 구성요건 분석
3. extract_factors_node: 양형인자 추출
4. estimate_sentence_node: 양형 예측
5. suggest_defense_node: 변호 전략 제안
6. search_precedents_node: 형사 판례 검색

조건부 분기:
- 범죄 유형별 특화 분석 경로
- 재산범죄: 피해액 중심 분석
- 폭력범죄: 상해 정도 분석
- 교통범죄: 혈중농도, 전과 분석
"""

from typing import TypedDict, List, Dict, Any, Optional


class CrimeElementResult(TypedDict):
    """범죄 구성요건 요소"""
    element: str
    description: str
    fulfilled: bool


class CrimeElementsResult(TypedDict):
    """구성요건 분석 결과"""
    objective: List[CrimeElementResult]
    subjective: List[CrimeElementResult]


class SentencingFactorsResult(TypedDict):
    """양형인자 결과"""
    favorable: List[str]
    unfavorable: List[str]


class ExpectedSentenceResult(TypedDict):
    """예상 양형 결과"""
    range: str
    suspended_probability: float
    reasoning: Optional[str]


class CriminalPrecedentResult(TypedDict):
    """형사 판례 결과"""
    case_number: str
    court: str
    date: str
    crime_type: str
    sentence: str
    summary: str
    relevance: float


class CriminalCaseState(TypedDict):
    """
    형사 사건 분석 워크플로우 상태

    Attributes:
        # 입력
        texts: 문서 텍스트 리스트
        filenames: 파일명 리스트
        user_id: 사용자 ID
        case_name: 사건명 (선택)
        input_crime_type: 사용자 지정 범죄 유형 (선택)

        # 분석 결과
        summary: 사건 요약
        crime_type: 감지된/확정된 범죄 유형
        crime_category: 범죄 카테고리 (property/violent/traffic/sexual/drug/general)
        criminal_stage: 형사 절차 단계 (COMPLAINT/INVESTIGATION/PROSECUTION/TRIAL/JUDGMENT/CLOSED)
        crime_elements: 구성요건 분석 결과
        sentencing_factors: 양형인자
        expected_sentence: 예상 양형
        defense_strategies: 변호 전략 리스트
        related_precedents: 관련 판례 리스트

        # 워크플로우 제어
        analysis_plan: 분석 계획 (실행할 노드 목록)
        completed_tasks: 완료된 작업 목록
        error: 에러 메시지
    """
    # 입력
    texts: List[str]
    filenames: List[str]
    user_id: Optional[str]
    case_name: Optional[str]
    input_crime_type: Optional[str]

    # 분석 결과
    summary: Optional[str]
    crime_type: Optional[str]
    crime_category: Optional[str]  # property, violent, traffic, sexual, drug, general
    criminal_stage: Optional[str]  # COMPLAINT, INVESTIGATION, PROSECUTION, TRIAL, JUDGMENT, CLOSED
    crime_elements: Optional[CrimeElementsResult]
    sentencing_factors: Optional[SentencingFactorsResult]
    expected_sentence: Optional[ExpectedSentenceResult]
    defense_strategies: List[str]
    related_precedents: List[CriminalPrecedentResult]

    # 워크플로우 제어
    analysis_plan: List[str]
    completed_tasks: List[str]
    error: Optional[str]

    # 판례 검색 비동기 처리
    skip_precedents: Optional[bool]  # True면 판례 검색 스킵 (나중에 별도 API로 검색)
    precedents_status: Optional[str]  # 'pending', 'searching', 'completed', 'failed'


# 범죄 유형 → 카테고리 매핑
CRIME_CATEGORY_MAP: Dict[str, str] = {
    # 재산범죄
    "절도": "property",
    "강도": "property",
    "사기": "property",
    "횡령": "property",
    "배임": "property",
    # 폭력범죄
    "폭행": "violent",
    "상해": "violent",
    "살인": "violent",
    "협박": "violent",
    # 교통범죄
    "음주운전": "traffic",
    "교통사고": "traffic",
    # 성범죄
    "강간": "sexual",
    "성추행": "sexual",
    # 마약범죄
    "마약": "drug",
    # 기타
    "명예훼손": "general",
    "모욕": "general",
    "뇌물": "general",
    "직무유기": "general",
    "위증": "general",
}


def get_crime_category(crime_type: str) -> str:
    """범죄 유형에서 카테고리 반환"""
    return CRIME_CATEGORY_MAP.get(crime_type, "general")


# 형사 절차 단계 감지를 위한 키워드 매핑
STAGE_KEYWORDS: Dict[str, List[str]] = {
    "JUDGMENT": [
        "판결문", "판결", "선고", "주문", "피고인을 징역", "피고인을 벌금",
        "무죄", "집행유예", "항소심", "상고심", "확정판결"
    ],
    "TRIAL": [
        "공판", "공판조서", "공판기일", "증인소환", "변론", "증거조사",
        "법정", "재판장", "피고인 심문", "최종변론", "구형"
    ],
    "PROSECUTION": [
        "공소장", "기소", "기소결정", "약식명령 청구", "공소제기",
        "구속기소", "불구속기소", "약식기소"
    ],
    "INVESTIGATION": [
        "송치", "검찰송치", "수사결과", "검찰수사", "기소의견",
        "불기소의견", "구속영장", "피의자신문조서", "참고인조사"
    ],
    "COMPLAINT": [
        "고소장", "고발장", "인지서", "범죄신고", "피해신고",
        "고소취지", "고소이유", "고발취지"
    ],
    "CLOSED": [
        "종결", "확정", "형집행종료", "사건종결"
    ]
}


def detect_criminal_stage(text: str, filenames: List[str] = None) -> str:
    """
    문서 내용과 파일명에서 형사 절차 단계를 감지

    Args:
        text: 문서 텍스트
        filenames: 파일명 리스트

    Returns:
        감지된 형사 절차 단계 (COMPLAINT, INVESTIGATION, PROSECUTION, TRIAL, JUDGMENT, CLOSED)
    """
    # 파일명 기반 감지 (더 신뢰도 높음)
    if filenames:
        combined_filenames = " ".join(filenames).lower()
        for stage, keywords in STAGE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in combined_filenames:
                    return stage

    # 텍스트 기반 감지
    text_lower = text.lower() if text else ""

    # 판결문이 가장 명확한 키워드를 가짐 - 우선 검사
    judgment_score = sum(1 for kw in STAGE_KEYWORDS["JUDGMENT"] if kw in text_lower)
    if judgment_score >= 2:  # 판결문은 2개 이상 키워드 매치시
        return "JUDGMENT"

    # 공판 단계 키워드
    trial_score = sum(1 for kw in STAGE_KEYWORDS["TRIAL"] if kw in text_lower)
    if trial_score >= 2:
        return "TRIAL"

    # 기소 단계 키워드
    prosecution_score = sum(1 for kw in STAGE_KEYWORDS["PROSECUTION"] if kw in text_lower)
    if prosecution_score >= 1:  # 공소장은 명확함
        return "PROSECUTION"

    # 수사 단계 키워드
    investigation_score = sum(1 for kw in STAGE_KEYWORDS["INVESTIGATION"] if kw in text_lower)
    if investigation_score >= 1:
        return "INVESTIGATION"

    # 고소/고발 단계 키워드
    complaint_score = sum(1 for kw in STAGE_KEYWORDS["COMPLAINT"] if kw in text_lower)
    if complaint_score >= 1:
        return "COMPLAINT"

    # 기본값은 COMPLAINT
    return "COMPLAINT"
