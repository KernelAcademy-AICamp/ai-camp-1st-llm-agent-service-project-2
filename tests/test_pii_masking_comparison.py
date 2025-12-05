"""
PII Masking 비교 테스트
커스텀 Regex+LLM vs Presidio+한국어모델

테스트 목적:
1. 한국어 법률 문서에서 개인정보 마스킹 정확도 비교
2. 처리 속도 비교
3. 각 방식의 장단점 파악

실행 방법:
    pytest tests/test_pii_masking_comparison.py -v -s
"""

import re
import time
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass
import pytest

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# OpenAI API 사용 (테스트용)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Presidio 사용 (설치된 경우)
try:
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer, Pattern
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False


# ============================================================================
# 테스트용 한국어 법률 문서 샘플
# ============================================================================

SAMPLE_DOCUMENTS = {
    "임대차계약서": """
임대차계약서

제1조 (당사자)
임대인: 김철수 (주민등록번호: 760815-1234567)
주소: 서울특별시 강남구 테헤란로 123, 456호
연락처: 010-1234-5678
이메일: kim.cs@example.com

임차인: 박영희 (주민등록번호: 850320-2345678)
주소: 서울특별시 마포구 월드컵로 789
연락처: 010-9876-5432
이메일: park.yh@naver.com

제2조 (목적물)
부동산 소재지: 서울특별시 강남구 역삼동 111-22
건물 종류: 아파트
전용면적: 84.5㎡

제3조 (보증금 및 차임)
보증금: 금 일억원정(₩100,000,000)
월 차임: 금 이백만원정(₩2,000,000)

제4조 (계약기간)
계약 시작일: 2025년 1월 1일
계약 종료일: 2027년 12월 31일

제5조 (특약사항)
1. 임차인은 계약금으로 금 천만원(₩10,000,000)을 계약 체결 시 지급한다.
2. 임대인의 계좌번호: 국민은행 123-45-678901 (예금주: 김철수)
3. 긴급 연락처: 부동산 ABC (대표: 이상호, 전화: 02-1234-5678)

2025년 1월 1일
임대인: 김철수 (서명)
임차인: 박영희 (서명)
    """,

    "임대차계약서_실제형식": """
임대차 계약서

당사자
임대인 김민수
주민번호 8503201234567(하이픈없음)
주소 서울시 송파구 올림픽로300 102동 1503호
핸드폰 010 8888 9999
이메일:kim_minsu@daum.net

임차인 윤지혜
주 민번호:920715-2234567
거주지:경기도성남시분당구정자일로50, 202호
연락처:01077778888(하이픈없음)
e-mail:yoon.jihye99@naver.com

목적물
대상부동산:서울시강남구삼성동111-22번지 아파트
전용 면적:84m2

보증금및월세
보증금 5천만원
월임대료 150만원
계좌번호  국민은행 012345678901

계약일:2025.1.15
임대인:김민수(인)
임차인:윤지혜(인)
    """,

    "고소장": """
고소장

고소인: 최민준 (주민번호: 920514-1234567)
주소: 경기도 성남시 분당구 판교역로 100
직업: 회사원
전화번호: 010-2222-3333
이메일: choi.mj@gmail.com

피고소인: 정수진 (주민번호: 881205-2345678)
주소: 서울특별시 송파구 올림픽로 200
직업: 자영업
전화번호: 010-4444-5555

고소취지
피고소인을 사기죄로 고소하오니 엄벌에 처하여 주시기 바랍니다.

범죄사실
1. 피고소인은 2024년 11월 15일 고소인을 만나 "확실한 투자처가 있다"며
   금 오천만원(₩50,000,000)을 투자하면 30% 수익을 보장하겠다고 제안하였습니다.

2. 고소인은 이를 믿고 2024년 11월 20일 피고소인의 계좌(신한은행 110-123-456789)로
   금 오천만원을 송금하였습니다.

3. 피고소인은 그 후 연락을 끊고 잠적하였으며, 해당 계좌도 폐쇄된 상태입니다.

4. 증거자료:
   - 계좌이체 영수증 (거래번호: 2024112012345678)
   - 카카오톡 대화내역 (피고소인 카카오ID: jung_sj_88)
   - 통화녹음 파일 (녹음일시: 2024.11.15 14:30)

입증방법
1. 계좌이체 증명서
2. 카카오톡 대화내역
3. 녹음파일
4. 목격자 진술서 (이동욱, 전화: 010-6666-7777)

2025년 1월 10일
고소인: 최민준 (서명)
    """,

    "근로계약서": """
근로계약서

사용자
상호: 주식회사 테크혁신
대표이사: 홍길동
사업자등록번호: 123-45-67890
소재지: 서울특별시 강남구 테헤란로 500
전화번호: 02-9999-8888

근로자
성명: 이지은 (주민번호: 940223-2345678)
주소: 서울특별시 관악구 봉천동 333-44
전화번호: 010-7777-8888
이메일: lee.jieun@company.com
긴급연락처: 이은정 (모친, 010-7777-9999)

제1조 (근무장소)
서울특별시 강남구 테헤란로 500, 주식회사 테크혁신 본사

제2조 (업무내용)
직무: 소프트웨어 개발 (백엔드 엔지니어)
부서: 개발1팀
직급: 주임

제3조 (근무시간)
평일: 오전 9시 ~ 오후 6시 (점심시간 12-13시)
주 40시간 근무

제4조 (임금)
월 기본급: 금 사백만원정(₩4,000,000)
급여지급일: 매월 25일
급여계좌: 우리은행 1002-123-456789 (예금주: 이지은)

제5조 (계약기간)
시작일: 2025년 2월 1일
종료일: 정년 (만 60세)
수습기간: 3개월 (2025.2.1 ~ 2025.4.30)

제6조 (4대 보험)
- 국민연금: 가입
- 건강보험: 가입
- 고용보험: 가입
- 산재보험: 가입

2025년 1월 15일
사용자: 홍길동 (날인)
근로자: 이지은 (서명)
    """
}


# ============================================================================
# 정답 데이터 (Ground Truth)
# ============================================================================

GROUND_TRUTH = {
    "임대차계약서": {
        "이름": ["김철수", "박영희", "이상호"],
        "주민번호": ["760815-1234567", "850320-2345678"],
        "전화번호": ["010-1234-5678", "010-9876-5432", "02-1234-5678"],
        "이메일": ["kim.cs@example.com", "park.yh@naver.com"],
        "주소": [
            "서울특별시 강남구 테헤란로 123, 456호",
            "서울특별시 마포구 월드컵로 789",
            "서울특별시 강남구 역삼동 111-22"
        ],
        "계좌번호": ["123-45-678901"],
    },
    "임대차계약서_실제형식": {
        "이름": ["김민수", "윤지혜"],
        "주민번호": ["8503201234567", "920715-2234567"],  # 하이픈 있는것/없는것 모두
        "전화번호": ["010 8888 9999", "01077778888"],  # 공백/하이픈 없는 것
        "이메일": ["kim_minsu@daum.net", "yoon.jihye99@naver.com"],
        "주소": [
            "서울시 송파구 올림픽로300 102동 1503호",
            "경기도성남시분당구정자일로50, 202호",
            "서울시강남구삼성동111-22번지"
        ],
        "계좌번호": ["012345678901"],
    },
    "고소장": {
        "이름": ["최민준", "정수진", "이동욱"],
        "주민번호": ["920514-1234567", "881205-2345678"],
        "전화번호": ["010-2222-3333", "010-4444-5555", "010-6666-7777"],
        "이메일": ["choi.mj@gmail.com"],
        "주소": [
            "경기도 성남시 분당구 판교역로 100",
            "서울특별시 송파구 올림픽로 200"
        ],
        "계좌번호": ["110-123-456789"],
        "기타_ID": ["jung_sj_88", "2024112012345678"],
    },
    "근로계약서": {
        "이름": ["홍길동", "이지은", "이은정"],
        "주민번호": ["940223-2345678"],
        "전화번호": ["02-9999-8888", "010-7777-8888", "010-7777-9999"],
        "이메일": ["lee.jieun@company.com"],
        "주소": [
            "서울특별시 강남구 테헤란로 500",
            "서울특별시 관악구 봉천동 333-44"
        ],
        "사업자번호": ["123-45-67890"],
        "계좌번호": ["1002-123-456789"],
    }
}


# ============================================================================
# 데이터 클래스
# ============================================================================

@dataclass
class MaskingResult:
    """마스킹 결과"""
    method: str  # "custom_regex_llm" or "presidio"
    masked_text: str
    detected_entities: Dict[str, List[str]]
    processing_time: float

    def to_dict(self):
        return {
            "method": self.method,
            "masked_text": self.masked_text,
            "detected_entities": self.detected_entities,
            "processing_time": self.processing_time
        }


@dataclass
class ComparisonMetrics:
    """비교 메트릭"""
    precision: float
    recall: float
    f1_score: float
    speed: float

    def to_dict(self):
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "speed": self.speed
        }


# ============================================================================
# 커스텀 Regex + LLM 마스킹
# ============================================================================

class CustomRegexLLMMasker:
    """커스텀 정규식 + LLM 기반 마스킹"""

    # 한국어 개인정보 정규식 패턴 (엄격한 형식만 매칭 - 실제로는 못 잡는 것 많음)
    PATTERNS = {
        "주민번호": r"\d{6}-\d{7}",  # 하이픈 있는 것만
        "전화번호": r"0\d{1,2}-\d{3,4}-\d{4}",  # 하이픈 있는 것만
        "이메일": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "계좌번호": r"\d{3,4}-\d{2,6}-\d{3,10}",  # 하이픈 있는 것만
        "사업자번호": r"\d{3}-\d{2}-\d{5}",  # 하이픈 있는 것만
    }

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        if use_llm and OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            if not api_key:
                print("⚠️  Warning: OpenAI API key not found. LLM masking disabled.")
                self.use_llm = False
            else:
                self.client = OpenAI(api_key=api_key)
        else:
            self.use_llm = False

    def mask(self, text: str) -> MaskingResult:
        """마스킹 수행"""
        start_time = time.time()

        # 1단계: 정규식 기반 마스킹
        regex_masked, regex_entities = self._regex_masking(text)

        # 2단계: LLM 기반 문맥 마스킹 (옵션)
        if self.use_llm:
            llm_masked, llm_entities = self._llm_masking(regex_masked)
            final_text = llm_masked
            all_entities = {**regex_entities, **llm_entities}
        else:
            final_text = regex_masked
            all_entities = regex_entities

        processing_time = time.time() - start_time

        return MaskingResult(
            method="custom_regex_llm" if self.use_llm else "custom_regex_only",
            masked_text=final_text,
            detected_entities=all_entities,
            processing_time=processing_time
        )

    def _regex_masking(self, text: str) -> Tuple[str, Dict[str, List[str]]]:
        """정규식 기반 1차 마스킹"""
        masked_text = text
        detected = {}

        for entity_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                detected[entity_type] = list(set(matches))

                # 마스킹 적용
                for i, match in enumerate(set(matches), 1):
                    masked_text = masked_text.replace(match, f"[{entity_type}_{i}]")

        return masked_text, detected

    def _llm_masking(self, text: str) -> Tuple[str, Dict[str, List[str]]]:
        """LLM 기반 문맥 마스킹 (이름, 주소 등)"""
        if not self.use_llm:
            return text, {}

        prompt = f"""다음 한국어 법률 문서에서 아직 마스킹되지 않은 개인정보를 찾아서 마스킹해주세요.

이미 정규식으로 마스킹된 패턴: [주민번호_N], [전화번호_N], [이메일_N] 등

추가로 마스킹해야 할 정보:
1. 사람 이름 → [이름_1], [이름_2], ...
2. 주소 → [주소_1], [주소_2], ...
3. 기타 식별 가능한 정보

규칙:
- 직책/직업은 마스킹하지 않음 (예: "변호사", "대표이사")
- 일반 명사는 마스킹하지 않음 (예: "국민은행", "카카오톡")
- 법률 용어는 유지 (예: "임대인", "피고소인")

원본 문서:
{text[:2000]}

마스킹된 결과만 출력하세요 (설명 없이):"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 한국어 개인정보 마스킹 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=3000
            )

            llm_masked = response.choices[0].message.content.strip()

            # LLM이 추가로 마스킹한 항목 추출
            llm_entities = self._extract_llm_entities(text, llm_masked)

            return llm_masked, llm_entities

        except Exception as e:
            print(f"⚠️  LLM masking failed: {e}")
            return text, {}

    def _extract_llm_entities(self, original: str, masked: str) -> Dict[str, List[str]]:
        """LLM이 추가로 마스킹한 엔티티 추출"""
        # 간단한 휴리스틱: [이름_N], [주소_N] 패턴 찾기
        entities = {}

        name_matches = re.findall(r'\[이름_\d+\]', masked)
        if name_matches:
            entities["이름"] = [f"감지됨({len(name_matches)}개)"]

        address_matches = re.findall(r'\[주소_\d+\]', masked)
        if address_matches:
            entities["주소"] = [f"감지됨({len(address_matches)}개)"]

        return entities


# ============================================================================
# Presidio 기반 마스킹 (한국어 패턴 추가)
# ============================================================================

class PresidioKoreanMasker:
    """Presidio + 한국어 패턴 Recognizer"""

    def __init__(self, use_llm: bool = False):
        if not PRESIDIO_AVAILABLE:
            raise ImportError("presidio-analyzer and presidio-anonymizer required")

        self.use_llm = use_llm

        # LLM 설정 (하이브리드 모드)
        if use_llm and OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            if api_key:
                self.llm_client = OpenAI(api_key=api_key)
            else:
                print("⚠️  Warning: OpenAI API key not found. Hybrid mode disabled.")
                self.use_llm = False

        # Analyzer 생성 (기본 영어 지원)
        self.analyzer = AnalyzerEngine()

        # 한국어 패턴 Recognizer 추가
        self._add_korean_recognizers()

        # Anonymizer 생성
        self.anonymizer = AnonymizerEngine()

    def _add_korean_recognizers(self):
        """한국어 개인정보 Recognizer 추가"""

        # 주민등록번호 (다양한 형식 지원)
        korean_ssn = PatternRecognizer(
            supported_entity="KR_RRN",
            patterns=[
                Pattern(name="Korean RRN with hyphen", regex=r"\d{6}-\d{7}", score=0.9),
                Pattern(name="Korean RRN no hyphen", regex=r"\d{13}(?!\d)", score=0.85),  # 13자리 숫자
                Pattern(name="Korean RRN with space", regex=r"\d{6}\s+-?\s*\d{7}", score=0.8),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_ssn)

        # 한국 전화번호 (다양한 형식 지원)
        korean_phone = PatternRecognizer(
            supported_entity="KR_PHONE",
            patterns=[
                Pattern(name="Phone with hyphen", regex=r"0\d{1,2}-\d{3,4}-\d{4}", score=0.9),
                Pattern(name="Phone with space", regex=r"0\d{1,2}\s+\d{3,4}\s+\d{4}", score=0.85),
                Pattern(name="Phone no separator", regex=r"0\d{9,10}(?!\d)", score=0.75),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_phone)

        # 한국 계좌번호 (다양한 형식)
        korean_account = PatternRecognizer(
            supported_entity="KR_ACCOUNT",
            patterns=[
                Pattern(name="Account with hyphen", regex=r"\d{3,4}-\d{2,6}-\d{3,10}", score=0.8),
                Pattern(name="Account no hyphen", regex=r"\d{10,14}(?!\d)", score=0.6),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_account)

        # 사업자등록번호
        korean_business = PatternRecognizer(
            supported_entity="KR_BRN",
            patterns=[
                Pattern(name="BRN with hyphen", regex=r"\d{3}-\d{2}-\d{5}", score=0.9),
                Pattern(name="BRN no hyphen", regex=r"\d{10}(?!\d)", score=0.7),
            ]
        )
        self.analyzer.registry.add_recognizer(korean_business)

    def mask(self, text: str) -> MaskingResult:
        """마스킹 수행"""
        start_time = time.time()

        # 1단계: Presidio 기반 패턴 마스킹
        # Note: language='en' 사용. PatternRecognizer는 정규식 기반이므로 한국어 텍스트에서도 작동
        analyzer_results = self.analyzer.analyze(
            text=text,
            language="en",
            entities=["KR_RRN", "KR_PHONE", "EMAIL_ADDRESS", "KR_ACCOUNT", "KR_BRN"]
        )

        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results
        )

        # 검출된 엔티티 정리
        detected_entities = {}
        for result in analyzer_results:
            entity_type = result.entity_type
            if entity_type not in detected_entities:
                detected_entities[entity_type] = []
            detected_entities[entity_type].append(
                text[result.start:result.end]
            )

        # 2단계: LLM 기반 추가 마스킹 (하이브리드 모드)
        final_text = anonymized_result.text
        if self.use_llm:
            llm_masked, llm_entities = self._llm_enhance_masking(final_text)
            final_text = llm_masked
            # LLM이 추가로 감지한 엔티티 병합
            for entity_type, items in llm_entities.items():
                if entity_type not in detected_entities:
                    detected_entities[entity_type] = []
                detected_entities[entity_type].extend(items)

        processing_time = time.time() - start_time

        return MaskingResult(
            method="presidio_llm_hybrid" if self.use_llm else "presidio_korean",
            masked_text=final_text,
            detected_entities=detected_entities,
            processing_time=processing_time
        )

    def _llm_enhance_masking(self, presidio_masked_text: str) -> Tuple[str, Dict[str, List[str]]]:
        """LLM을 사용한 추가 마스킹 (이름, 주소 등 Presidio가 놓친 정보)"""
        if not self.use_llm:
            return presidio_masked_text, {}

        prompt = f"""당신은 한국어 법률 문서의 개인정보 마스킹 전문가입니다.
Presidio가 1차로 패턴 기반 마스킹을 완료했습니다. 이제 당신은 Presidio가 놓친 개인정보만 추가로 마스킹해야 합니다.

## 이미 마스킹된 정보 (절대 건드리지 말 것)
- <EMAIL_ADDRESS>: 이메일
- <KR_RRN>: 주민등록번호
- <KR_PHONE>: 전화번호
- <KR_ACCOUNT>: 계좌번호
- <KR_BRN>: 사업자등록번호

## 추가로 마스킹해야 할 정보 (정확히 이것만)

### ✅ 반드시 마스킹할 것
1. **실제 사람 이름**: 한국식 이름 (성+이름, 2-4글자)
   - 예시: "김철수", "박영희", "이상호", "홍길동", "이지은"
   - 형식: [이름_1], [이름_2], [이름_3] ...

2. **구체적인 주소**: 실제 위치를 식별할 수 있는 주소
   - 예시: "서울특별시 강남구 테헤란로 123, 456호"
   - 예시: "경기도 성남시 분당구 판교역로 100"
   - 형식: [주소_1], [주소_2], [주소_3] ...

### ❌ 절대 마스킹하지 말 것
1. **직책/역할/직업**: 대표이사, 임대인, 임차인, 고소인, 피고소인, 근로자, 사용자, 변호사, 검사, 판사
2. **일반 명사**: 국민은행, 신한은행, 우리은행, 카카오톡, 회사명, 부서명
3. **법률 용어**: 계약서, 고소장, 근로계약, 보증금, 월차임, 임금, 수습기간
4. **일반적인 장소**: 본사, 지점, 아파트, 오피스텔 (구체적 주소 없이 나오는 경우)
5. **이미 마스킹된 태그**: <EMAIL_ADDRESS>, <KR_RRN> 등

## Few-Shot Examples

### Example 1
입력: "임대인: <KR_RRN> 주소: 서울특별시 강남구 테헤란로 123"
출력: "임대인: [이름_1] (주민등록번호: <KR_RRN>) 주소: [주소_1]"

### Example 2
입력: "대표이사: 홍길동 사업자등록번호: <KR_BRN>"
출력: "대표이사: [이름_1] 사업자등록번호: <KR_BRN>"

### Example 3
입력: "고소인을 만나 투자를 제안하였습니다"
출력: "고소인을 만나 투자를 제안하였습니다" (변경 없음 - "고소인"은 역할이므로 마스킹 안 함)

## 원본 문서
{presidio_masked_text[:2000]}

## 출력 지침
- 위 문서에서 **이름과 주소만** 마스킹하세요
- 다른 설명 없이 마스킹된 문서만 출력하세요
- 원본 문서의 형식(줄바꿈, 들여쓰기)을 정확히 유지하세요"""

        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 한국어 개인정보 마스킹 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=3000
            )

            llm_masked = response.choices[0].message.content.strip()

            # LLM이 추가로 마스킹한 항목 추출
            llm_entities = self._extract_llm_entities(presidio_masked_text, llm_masked)

            return llm_masked, llm_entities

        except Exception as e:
            print(f"⚠️  LLM enhancement failed: {e}")
            return presidio_masked_text, {}

    def _extract_llm_entities(self, original: str, masked: str) -> Dict[str, List[str]]:
        """LLM이 추가로 마스킹한 엔티티 추출 - 실제 값 역추적"""
        entities = {}

        # [이름_1], [이름_2] 등을 찾고, 원본에서 실제 이름 추출
        name_pattern = r'\[이름_\d+\]'
        name_placeholders = re.findall(name_pattern, masked)

        if name_placeholders:
            # 원본과 마스킹된 텍스트를 비교해서 실제 이름 찾기
            detected_names = []
            temp_masked = masked
            temp_original = original

            for placeholder in name_placeholders:
                # 마스킹된 텍스트에서 placeholder 위치 찾기
                placeholder_pos = temp_masked.find(placeholder)
                if placeholder_pos == -1:
                    continue

                # 원본에서 같은 위치 전후로 한국식 이름 패턴 찾기 (2-4글자)
                context_start = max(0, placeholder_pos - 20)
                context_end = min(len(temp_original), placeholder_pos + 20)
                context = temp_original[context_start:context_end]

                # 한국식 이름 패턴: 2-4글자 한글
                korean_name_matches = re.findall(r'[가-힣]{2,4}', context)
                if korean_name_matches:
                    # 가장 가까운 매칭 선택
                    detected_names.append(korean_name_matches[0])
                    # 사용한 부분 제거 (중복 방지)
                    temp_original = temp_original.replace(korean_name_matches[0], '', 1)
                    temp_masked = temp_masked.replace(placeholder, '', 1)

            if detected_names:
                entities["이름"] = list(set(detected_names))

        # 주소도 동일한 방식으로 추출
        address_pattern = r'\[주소_\d+\]'
        address_placeholders = re.findall(address_pattern, masked)

        if address_placeholders:
            detected_addresses = []

            # 간단한 휴리스틱: "주소:" 또는 "거주지:" 뒤의 텍스트 추출
            address_markers = ['주소:', '거주지:', '소재지:', '주소 ', '소재지 ', '부동산:']

            for marker in address_markers:
                if marker in original:
                    parts = original.split(marker)
                    for i, part in enumerate(parts[1:], 1):
                        # 다음 줄바꿈까지 또는 50자까지
                        addr_text = part.split('\n')[0].strip()[:100]
                        # 주소 패턴 (시/도로 시작)
                        addr_matches = re.findall(r'[가-힣]{2,}[시도구군][가-힣\s\d,.-]+', addr_text)
                        if addr_matches:
                            detected_addresses.extend(addr_matches)

            if detected_addresses:
                entities["주소"] = list(set([addr.strip() for addr in detected_addresses]))

        return entities


# ============================================================================
# 평가 함수
# ============================================================================

def calculate_metrics(
    detected: Dict[str, List[str]],
    ground_truth: Dict[str, List[str]]
) -> ComparisonMetrics:
    """
    Precision, Recall, F1 Score 계산

    Args:
        detected: 감지된 엔티티
        ground_truth: 정답 엔티티
    """
    # 모든 엔티티를 평탄화
    detected_items = set()
    for items in detected.values():
        detected_items.update(items)

    ground_truth_items = set()
    for items in ground_truth.values():
        ground_truth_items.update(items)

    # True Positive, False Positive, False Negative
    tp = len(detected_items & ground_truth_items)
    fp = len(detected_items - ground_truth_items)
    fn = len(ground_truth_items - detected_items)

    # Precision, Recall, F1
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return ComparisonMetrics(
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        speed=0  # Will be set separately
    )


# ============================================================================
# pytest 테스트
# ============================================================================

@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI not available")
def test_custom_regex_llm_masking():
    """커스텀 Regex+LLM 마스킹 테스트"""
    masker = CustomRegexLLMMasker(use_llm=True)

    for doc_name, doc_text in SAMPLE_DOCUMENTS.items():
        print(f"\n{'='*60}")
        print(f"📄 문서: {doc_name}")
        print(f"{'='*60}")

        result = masker.mask(doc_text)

        print(f"\n🔍 감지된 엔티티:")
        for entity_type, items in result.detected_entities.items():
            print(f"  - {entity_type}: {len(items)}개")

        print(f"\n⏱️  처리 시간: {result.processing_time:.2f}초")

        # Ground truth와 비교
        if doc_name in GROUND_TRUTH:
            metrics = calculate_metrics(
                result.detected_entities,
                GROUND_TRUTH[doc_name]
            )
            metrics.speed = result.processing_time

            print(f"\n📊 메트릭:")
            print(f"  - Precision: {metrics.precision:.2%}")
            print(f"  - Recall: {metrics.recall:.2%}")
            print(f"  - F1 Score: {metrics.f1_score:.2%}")


@pytest.mark.skipif(not PRESIDIO_AVAILABLE, reason="Presidio not available")
def test_presidio_korean_masking():
    """Presidio 한국어 마스킹 테스트"""
    masker = PresidioKoreanMasker()

    for doc_name, doc_text in SAMPLE_DOCUMENTS.items():
        print(f"\n{'='*60}")
        print(f"📄 문서: {doc_name}")
        print(f"{'='*60}")

        result = masker.mask(doc_text)

        print(f"\n🔍 감지된 엔티티:")
        for entity_type, items in result.detected_entities.items():
            print(f"  - {entity_type}: {len(items)}개")

        print(f"\n⏱️  처리 시간: {result.processing_time:.2f}초")

        # Ground truth와 비교
        if doc_name in GROUND_TRUTH:
            metrics = calculate_metrics(
                result.detected_entities,
                GROUND_TRUTH[doc_name]
            )
            metrics.speed = result.processing_time

            print(f"\n📊 메트릭:")
            print(f"  - Precision: {metrics.precision:.2%}")
            print(f"  - Recall: {metrics.recall:.2%}")
            print(f"  - F1 Score: {metrics.f1_score:.2%}")


@pytest.mark.skipif(
    not (OPENAI_AVAILABLE and PRESIDIO_AVAILABLE),
    reason="Both OpenAI and Presidio required"
)
def test_presidio_llm_hybrid():
    """Presidio + LLM 하이브리드 마스킹 테스트"""
    masker = PresidioKoreanMasker(use_llm=True)

    for doc_name, doc_text in SAMPLE_DOCUMENTS.items():
        print(f"\n{'='*60}")
        print(f"📄 문서: {doc_name}")
        print(f"{'='*60}")

        result = masker.mask(doc_text)

        print(f"\n🔍 감지된 엔티티:")
        for entity_type, items in result.detected_entities.items():
            print(f"  - {entity_type}: {len(items)}개")

        print(f"\n⏱️  처리 시간: {result.processing_time:.2f}초")

        # Ground truth와 비교
        if doc_name in GROUND_TRUTH:
            metrics = calculate_metrics(
                result.detected_entities,
                GROUND_TRUTH[doc_name]
            )
            metrics.speed = result.processing_time

            print(f"\n📊 메트릭:")
            print(f"  - Precision: {metrics.precision:.2%}")
            print(f"  - Recall: {metrics.recall:.2%}")
            print(f"  - F1 Score: {metrics.f1_score:.2%}")


@pytest.mark.skipif(
    not (OPENAI_AVAILABLE and PRESIDIO_AVAILABLE),
    reason="Both OpenAI and Presidio required"
)
def test_comparison():
    """세 방식 직접 비교: 커스텀 vs Presidio vs 하이브리드"""
    print(f"\n{'='*80}")
    print("🆚 커스텀 Regex+LLM vs Presidio vs Presidio+LLM 하이브리드 비교 테스트")
    print(f"{'='*80}\n")

    custom_masker = CustomRegexLLMMasker(use_llm=True)
    presidio_masker = PresidioKoreanMasker(use_llm=False)
    hybrid_masker = PresidioKoreanMasker(use_llm=True)

    results = {
        "custom": {},
        "presidio": {},
        "hybrid": {}
    }

    for doc_name, doc_text in SAMPLE_DOCUMENTS.items():
        print(f"\n📄 문서: {doc_name}")
        print("-" * 80)

        # 1. 커스텀 Regex+LLM
        custom_result = custom_masker.mask(doc_text)
        custom_metrics = calculate_metrics(
            custom_result.detected_entities,
            GROUND_TRUTH[doc_name]
        )
        custom_metrics.speed = custom_result.processing_time
        results["custom"][doc_name] = custom_metrics

        print(f"\n🔧 커스텀 Regex+LLM:")
        print(f"   Precision: {custom_metrics.precision:.2%}")
        print(f"   Recall: {custom_metrics.recall:.2%}")
        print(f"   F1 Score: {custom_metrics.f1_score:.2%}")
        print(f"   속도: {custom_metrics.speed:.2f}초")

        # 2. Presidio Only
        presidio_result = presidio_masker.mask(doc_text)
        presidio_metrics = calculate_metrics(
            presidio_result.detected_entities,
            GROUND_TRUTH[doc_name]
        )
        presidio_metrics.speed = presidio_result.processing_time
        results["presidio"][doc_name] = presidio_metrics

        print(f"\n🛡️  Presidio Only:")
        print(f"   Precision: {presidio_metrics.precision:.2%}")
        print(f"   Recall: {presidio_metrics.recall:.2%}")
        print(f"   F1 Score: {presidio_metrics.f1_score:.2%}")
        print(f"   속도: {presidio_metrics.speed:.2f}초")

        # 3. Presidio + LLM 하이브리드
        hybrid_result = hybrid_masker.mask(doc_text)
        hybrid_metrics = calculate_metrics(
            hybrid_result.detected_entities,
            GROUND_TRUTH[doc_name]
        )
        hybrid_metrics.speed = hybrid_result.processing_time
        results["hybrid"][doc_name] = hybrid_metrics

        print(f"\n🚀 Presidio + LLM 하이브리드:")
        print(f"   Precision: {hybrid_metrics.precision:.2%}")
        print(f"   Recall: {hybrid_metrics.recall:.2%}")
        print(f"   F1 Score: {hybrid_metrics.f1_score:.2%}")
        print(f"   속도: {hybrid_metrics.speed:.2f}초")

        # 승자 판정
        max_f1 = max(custom_metrics.f1_score, presidio_metrics.f1_score, hybrid_metrics.f1_score)
        if custom_metrics.f1_score == max_f1:
            print(f"\n🏆 이 문서 승자: 커스텀 Regex+LLM (F1: {custom_metrics.f1_score:.2%})")
        elif hybrid_metrics.f1_score == max_f1:
            print(f"\n🏆 이 문서 승자: Presidio+LLM 하이브리드 (F1: {hybrid_metrics.f1_score:.2%})")
        else:
            print(f"\n🏆 이 문서 승자: Presidio Only (F1: {presidio_metrics.f1_score:.2%})")

    # 전체 평균
    print(f"\n{'='*80}")
    print("📊 전체 평균 성능")
    print(f"{'='*80}\n")

    custom_avg_f1 = sum(m.f1_score for m in results["custom"].values()) / len(results["custom"])
    custom_avg_speed = sum(m.speed for m in results["custom"].values()) / len(results["custom"])

    presidio_avg_f1 = sum(m.f1_score for m in results["presidio"].values()) / len(results["presidio"])
    presidio_avg_speed = sum(m.speed for m in results["presidio"].values()) / len(results["presidio"])

    hybrid_avg_f1 = sum(m.f1_score for m in results["hybrid"].values()) / len(results["hybrid"])
    hybrid_avg_speed = sum(m.speed for m in results["hybrid"].values()) / len(results["hybrid"])

    print(f"1️⃣  커스텀 Regex+LLM:")
    print(f"   평균 F1 Score: {custom_avg_f1:.2%}")
    print(f"   평균 속도: {custom_avg_speed:.2f}초")

    print(f"\n2️⃣  Presidio Only:")
    print(f"   평균 F1 Score: {presidio_avg_f1:.2%}")
    print(f"   평균 속도: {presidio_avg_speed:.2f}초")

    print(f"\n3️⃣  Presidio + LLM 하이브리드:")
    print(f"   평균 F1 Score: {hybrid_avg_f1:.2%}")
    print(f"   평균 속도: {hybrid_avg_speed:.2f}초")

    # 최종 승자
    print(f"\n{'='*80}")
    max_avg_f1 = max(custom_avg_f1, presidio_avg_f1, hybrid_avg_f1)

    if custom_avg_f1 == max_avg_f1:
        print(f"🏆 최종 승자: 커스텀 Regex+LLM")
        print(f"   평균 F1 Score: {custom_avg_f1:.2%}")
        print(f"   Presidio보다: +{(custom_avg_f1 - presidio_avg_f1)*100:.1f}%p")
        print(f"   하이브리드보다: +{(custom_avg_f1 - hybrid_avg_f1)*100:.1f}%p")
    elif hybrid_avg_f1 == max_avg_f1:
        print(f"🏆 최종 승자: Presidio + LLM 하이브리드")
        print(f"   평균 F1 Score: {hybrid_avg_f1:.2%}")
        print(f"   커스텀보다: +{(hybrid_avg_f1 - custom_avg_f1)*100:.1f}%p")
        print(f"   Presidio보다: +{(hybrid_avg_f1 - presidio_avg_f1)*100:.1f}%p")
    else:
        print(f"🏆 최종 승자: Presidio Only")
        print(f"   평균 F1 Score: {presidio_avg_f1:.2%}")
        print(f"   커스텀보다: +{(presidio_avg_f1 - custom_avg_f1)*100:.1f}%p")
        print(f"   하이브리드보다: +{(presidio_avg_f1 - hybrid_avg_f1)*100:.1f}%p")

    # 속도 비교
    min_speed = min(custom_avg_speed, presidio_avg_speed, hybrid_avg_speed)
    if custom_avg_speed == min_speed:
        print(f"\n⚡ 가장 빠른 방식: 커스텀 Regex+LLM ({custom_avg_speed:.2f}초)")
    elif presidio_avg_speed == min_speed:
        print(f"\n⚡ 가장 빠른 방식: Presidio Only ({presidio_avg_speed:.2f}초)")
    else:
        print(f"\n⚡ 가장 빠른 방식: Presidio+LLM 하이브리드 ({hybrid_avg_speed:.2f}초)")

    print(f"{'='*80}\n")


if __name__ == "__main__":
    # 직접 실행 시
    print("PII 마스킹 비교 테스트")
    print("=" * 80)

    if OPENAI_AVAILABLE:
        print("✅ OpenAI 사용 가능")
    else:
        print("❌ OpenAI 사용 불가")

    if PRESIDIO_AVAILABLE:
        print("✅ Presidio 사용 가능")
    else:
        print("❌ Presidio 사용 불가")

    print("\npytest 실행:")
    print("  pytest tests/test_pii_masking_comparison.py -v -s")
