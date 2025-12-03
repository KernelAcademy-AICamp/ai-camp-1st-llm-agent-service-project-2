"""
OCR 후처리 모듈
OCR 오인식 단어를 자동으로 교정
"""

import re
from typing import Dict


class OCRPostProcessor:
    """OCR 텍스트 후처리기"""

    # 자주 오인식되는 단어 사전 (한국어 법률 문서 특화)
    COMMON_CORRECTIONS = {
        # 청구 관련
        '정구취지': '청구취지',
        '정구쥐지': '청구취지',
        '정구 취지': '청구취지',
        '정구원인': '청구원인',
        '정구 원인': '청구원인',
        '정구': '청구',

        # 법률 용어
        '판결올': '판결을',
        '조지': '조치',

        # 영문자 오인식
        'HAS': '판결을',
        'SS': '항',
        'DAS': '과실로',
        'AAS': '조치를',
        'ODE': '원고는',
        'DDS': '피고를',
    }

    # 패턴 기반 교정 (정규표현식)
    PATTERN_CORRECTIONS = [
        # "제 1 SS" -> "제1항"
        (r'제\s*(\d+)\s*SS', r'제\1항'),

        # "ODE DDS" -> "원고는 피고를"
        (r'ODE\s+DDS', '원고는 피고를'),

        # "갖는 날" -> "갚는 날"
        (r'갖는\s+날', '갚는 날'),

        # 공백이 너무 많은 경우 정리
        (r'\s{3,}', ' '),
    ]

    @classmethod
    def post_process(cls, text: str, verbose: bool = False) -> str:
        """
        OCR 텍스트 후처리

        Args:
            text: OCR로 추출된 원본 텍스트
            verbose: 교정 내역 출력 여부

        Returns:
            교정된 텍스트
        """
        corrections_made = []

        # 1단계: 단어 단위 교정
        for wrong, correct in cls.COMMON_CORRECTIONS.items():
            if wrong in text:
                count = text.count(wrong)
                text = text.replace(wrong, correct)
                if count > 0:
                    corrections_made.append(f'"{wrong}" -> "{correct}" ({count})')

        # 2단계: 패턴 기반 교정
        for pattern, replacement in cls.PATTERN_CORRECTIONS:
            matches = re.findall(pattern, text)
            if matches:
                text = re.sub(pattern, replacement, text)
                corrections_made.append(f'pattern "{pattern}" ({len(matches)})')

        if verbose and corrections_made:
            print(f'[OCR Post-processing] {len(corrections_made)} corrections made')
            for correction in corrections_made:
                print(f'  - {correction}')

        return text

    @classmethod
    def validate_corrections(cls, text: str) -> Dict[str, int]:
        """
        교정 가능한 오인식 단어 통계

        Args:
            text: OCR 텍스트

        Returns:
            오인식 단어별 발견 횟수
        """
        found = {}

        for wrong in cls.COMMON_CORRECTIONS.keys():
            count = text.count(wrong)
            if count > 0:
                found[wrong] = count

        return found


def apply_ocr_postprocessing(text: str, verbose: bool = False) -> str:
    """
    OCR 후처리 적용 (편의 함수)

    Args:
        text: OCR 텍스트
        verbose: 교정 내역 출력 여부

    Returns:
        교정된 텍스트
    """
    return OCRPostProcessor.post_process(text, verbose=verbose)
