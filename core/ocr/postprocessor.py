"""
OCR 후처리 모듈
OCR 오인식 단어를 자동으로 교정
"""

import re
from typing import Dict


class OCRPostProcessor:
    """OCR 텍스트 후처리기"""

    # 자주 오인식되는 단어 사전
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
        '판결을': '판결을',  # 정상 케이스도 포함
        '소송비용은': '소송비용은',
        '항은': '항은',
        '조지': '조치',
        '조치': '조치',  # 정상 케이스

        # 영문자 오인식
        'HAS': '판결을',
        'SS': '항',
        'DAS': '과실로',
        'AAS': '조치를',
        'ODE': '원고는',
        'DDS': '피고를',

        # 기타
        '갖는': '갚는',
        '입은': '입은',  # 정상 케이스
    }

    # 패턴 기반 교정 (정규표현식)
    PATTERN_CORRECTIONS = [
        # "제 1 SS" → "제1항"
        (r'제\s*(\d+)\s*SS', r'제\1항'),

        # "ODE DDS" → "원고는 피고를"
        (r'ODE\s+DDS', '원고는 피고를'),

        # "갖는 날" → "갚는 날"
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
        if verbose:
            print('[OCR 후처리 시작]')
            print(f'원본 길이: {len(text)}자')

        original_text = text
        corrections_made = []

        # 1단계: 단어 단위 교정
        for wrong, correct in cls.COMMON_CORRECTIONS.items():
            if wrong in text:
                count = text.count(wrong)
                text = text.replace(wrong, correct)
                if count > 0:
                    corrections_made.append(f'"{wrong}" → "{correct}" ({count}회)')

        # 2단계: 패턴 기반 교정
        for pattern, replacement in cls.PATTERN_CORRECTIONS:
            matches = re.findall(pattern, text)
            if matches:
                text = re.sub(pattern, replacement, text)
                corrections_made.append(f'패턴 "{pattern}" 교정 ({len(matches)}회)')

        if verbose:
            print(f'\n교정 완료:')
            print(f'  총 {len(corrections_made)}가지 교정')
            for correction in corrections_made:
                print(f'  - {correction}')
            print(f'교정 후 길이: {len(text)}자')
            print()

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


if __name__ == "__main__":
    # 테스트
    test_text = """
    원 고 _ 김부상 (850315-1******)
    피 고 이가해 (781120-2******)

    손해배상(자) 정구의 소
    정구쥐지
    1. 피고는 원고에게 금 35,800,000 원 및 이에 대하여 2025 년 6 월 15 일부터
    이 사건 소장 부본 송달일까지는 연 5%의, 그 다음날부터 다 갖는 날까지는
    연 12%의 각 비율로 계산한 돈을 지급하라.
    2. 소송비용은 피고가 부담한다.
    3. 제 1 SS 가집행할 수 있다.
    라는 HAS 구합니다.

    정구원인
    1. 사고의 발생
    피고는 2025 년 6 월 15 일 11 시 30 분경 서울특별시 마포구 월드컵로
    100 번길 교차로 부근에서 피고 소유의 차량(20 가 1234)을 운전하여
    전방주시의무를 게을리하고 과속 운전한 DAS 원고 운전의 차량을 충격하였습니다.
    """

    print('='*70)
    print('OCR 후처리 테스트')
    print('='*70)
    print()

    # 교정 전 오인식 단어 확인
    print('[교정 전 오인식 단어]')
    found = OCRPostProcessor.validate_corrections(test_text)
    for word, count in found.items():
        print(f'  "{word}": {count}회')
    print()

    # 후처리 적용
    corrected = apply_ocr_postprocessing(test_text, verbose=True)

    # 결과 출력
    print('[교정 후 텍스트]')
    print('-'*70)
    print(corrected[:500])
    print('-'*70)
