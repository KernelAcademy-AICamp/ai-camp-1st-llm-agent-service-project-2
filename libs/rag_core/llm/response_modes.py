"""
응답 모드 시스템

질문 유형과 사용자 선택에 따라 답변 길이/상세도 조절
"""

from enum import Enum
from typing import Dict, Any
import re


class ResponseMode(Enum):
    """응답 모드"""
    CONCISE = "concise"      # 핵심만 (50-100단어)
    STANDARD = "standard"    # 표준 (100-150단어)
    DETAILED = "detailed"    # 상세 (200-300단어)


class ResponseModeConfig:
    """각 모드별 설정"""

    CONFIGS: Dict[ResponseMode, Dict[str, Any]] = {
        ResponseMode.CONCISE: {
            "max_length": 100,
            "top_k": 2,
            "few_shot_count": 1,
            "enable_critique": False,
            "instruction": "핵심만 간결하게 답변하세요. 부가 설명은 생략합니다."
        },
        ResponseMode.STANDARD: {
            "max_length": 200,
            "top_k": 3,
            "few_shot_count": 1,
            "enable_critique": False,
            "instruction": "핵심 정보와 간단한 설명을 포함하여 답변하세요."
        },
        ResponseMode.DETAILED: {
            "max_length": 400,
            "top_k": 5,
            "few_shot_count": 2,
            "enable_critique": True,
            "instruction": "상세한 설명과 예시를 포함하여 답변하세요."
        }
    }

    @classmethod
    def get_config(cls, mode: ResponseMode) -> Dict[str, Any]:
        return cls.CONFIGS.get(mode, cls.CONFIGS[ResponseMode.STANDARD])


class QueryClassifier:
    """
    질문 복잡도 자동 분류

    사용자가 모드를 선택하지 않았을 때 자동 결정
    """

    # 단순 질문 패턴
    SIMPLE_PATTERNS = [
        r'(란|이란)\s*\??$',           # "~란?", "~이란?"
        r'(은|는)\s*무엇',              # "~은 무엇"
        r'(의\s*)?정의',                # "~의 정의"
        r'(의\s*)?뜻',                  # "~의 뜻"
        r'(의\s*)?의미',                # "~의 의미"
    ]

    # 복잡한 질문 패턴
    COMPLEX_PATTERNS = [
        r'(그리고|또한|아울러)',        # 복합 질문
        r'(비교|차이|다른\s*점)',       # 비교 분석
        r'(경우|상황|사례)',            # 사례 적용
        r'(판례|선례)',                 # 판례 요청
        r'(어떻게|어떤\s*방법)',        # 절차 질문
        r'상세|자세|구체적',            # 상세 설명 요청
    ]

    @classmethod
    def classify(cls, query: str) -> ResponseMode:
        """질문을 분석하여 적절한 응답 모드 반환"""

        query_length = len(query.split())

        # 1. 매우 짧은 질문 (5단어 미만) → CONCISE
        if query_length < 5:
            return ResponseMode.CONCISE

        # 2. 단순 패턴 매칭 → CONCISE
        for pattern in cls.SIMPLE_PATTERNS:
            if re.search(pattern, query):
                return ResponseMode.CONCISE

        # 3. 복잡한 패턴 매칭 → DETAILED
        for pattern in cls.COMPLEX_PATTERNS:
            if re.search(pattern, query):
                return ResponseMode.DETAILED

        # 4. 긴 질문 (15단어 이상) → DETAILED
        if query_length >= 15:
            return ResponseMode.DETAILED

        # 5. 기본 → STANDARD
        return ResponseMode.STANDARD

    @classmethod
    def get_mode_description(cls, mode: ResponseMode) -> str:
        """모드 설명 (UI 표시용)"""
        descriptions = {
            ResponseMode.CONCISE: "간결 모드: 핵심만 빠르게",
            ResponseMode.STANDARD: "표준 모드: 적절한 설명 포함",
            ResponseMode.DETAILED: "상세 모드: 자세한 분석과 예시"
        }
        return descriptions.get(mode, "")


class DynamicFewShotSelector:
    """질문 유형에 맞는 Few-Shot 예시 동적 선택"""

    EXAMPLES_BY_TYPE = {
        "definition": {
            "question": "절도죄란?",
            "answer": "**절도죄**(형법 제329조): 타인의 재물을 절취하는 죄. 6년↓ 징역 또는 1천만원↓ 벌금. ⚠️ 법률 정보 제공입니다."
        },
        "comparison": {
            "question": "절도죄와 강도죄 차이?",
            "answer": "**핵심 차이**: 폭행·협박 유무\n- 절도: 몰래 (6년↓)\n- 강도: 폭행·협박 (3년↑)\n⚠️ 법률 정보 제공입니다."
        },
        "requirements": {
            "question": "정당방위 요건?",
            "answer": "**정당방위**(형법 제21조) 요건:\n1. 현재의 부당한 침해\n2. 방위 목적\n3. 상당성\n[판례: 대법원 2018도34567] ⚠️ 법률 정보 제공입니다."
        }
    }

    @classmethod
    def select(cls, query: str) -> dict:
        """질문 유형에 맞는 예시 선택"""

        # 정의형
        if re.search(r'(란|이란|은\s*무엇|정의|뜻)', query):
            return cls.EXAMPLES_BY_TYPE["definition"]

        # 비교형
        if re.search(r'(차이|비교|다른)', query):
            return cls.EXAMPLES_BY_TYPE["comparison"]

        # 요건형
        if re.search(r'(요건|성립|조건)', query):
            return cls.EXAMPLES_BY_TYPE["requirements"]

        # 기본
        return cls.EXAMPLES_BY_TYPE["definition"]

    @classmethod
    def format_example(cls, query: str) -> str:
        """선택된 예시를 프롬프트 형식으로"""
        example = cls.select(query)
        return f"""<Example>
Q: {example['question']}
A: {example['answer']}
</Example>"""
