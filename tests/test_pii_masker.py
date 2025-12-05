"""
PII Masker 테스트

테스트 항목:
1. Fast 모드: Presidio 패턴 기반 마스킹
2. Balanced 모드: Presidio + LLM (로컬 LLM 없으면 건너뜀)
3. 복원 기능 테스트
4. 다양한 형식의 한국어 PII 테스트

실행:
    pytest tests/test_pii_masker.py -v -s
"""

import pytest
import os
from dotenv import load_dotenv

load_dotenv()

# 테스트용 샘플 문서
SAMPLE_CONTRACT = """
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

제2조 (보증금)
보증금: 금 일억원정(₩100,000,000)
계좌번호: 국민은행 123-45-678901 (예금주: 김철수)

2025년 1월 1일
임대인: 김철수 (서명)
임차인: 박영희 (서명)
"""

SAMPLE_CRIMINAL_CASE = """
형사사건 기록

피고인: 이민호 (주민번호: 9201151234567)
주소: 경기도 성남시 분당구 판교역로 100
전화: 01088889999

피해자: 정수아 (주민번호: 880512-2345678)
연락처: 010-2222-3333

사건개요:
2024년 11월 15일 피고인 이민호는 피해자 정수아에게
금 오천만원을 투자금 명목으로 편취하였다.
"""


class TestPIIMaskerFastMode:
    """Fast 모드 테스트 (Presidio만 사용)"""

    def test_mask_rrn_with_hyphen(self):
        """주민번호 마스킹 (하이픈 있음)"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        text = "주민번호: 760815-1234567"

        masked_text, mapping = masker.mask(text)

        # 마스킹 확인
        assert "760815-1234567" not in masked_text
        assert "[RRN_" in masked_text

        # 매핑 확인
        assert len(mapping) == 1
        assert "760815-1234567" in mapping.values()

        # 복원 확인
        restored = masker.restore(masked_text, mapping)
        assert restored == text

    def test_mask_rrn_without_hyphen(self):
        """주민번호 마스킹 (하이픈 없음)"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        text = "주민번호 9201151234567 입니다"

        masked_text, mapping = masker.mask(text)

        # 13자리 숫자도 마스킹되어야 함
        assert "9201151234567" not in masked_text

        # 복원 확인
        restored = masker.restore(masked_text, mapping)
        assert restored == text

    def test_mask_phone_various_formats(self):
        """전화번호 마스킹 (다양한 형식)"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")

        # 하이픈 있음
        text1 = "연락처: 010-1234-5678"
        masked1, mapping1 = masker.mask(text1)
        assert "010-1234-5678" not in masked1
        assert masker.restore(masked1, mapping1) == text1

        # 공백 있음
        text2 = "연락처: 010 1234 5678"
        masked2, mapping2 = masker.mask(text2)
        assert "010 1234 5678" not in masked2
        assert masker.restore(masked2, mapping2) == text2

        # 하이픈/공백 없음
        text3 = "연락처: 01012345678"
        masked3, mapping3 = masker.mask(text3)
        assert "01012345678" not in masked3
        assert masker.restore(masked3, mapping3) == text3

    def test_mask_email(self):
        """이메일 마스킹"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        text = "이메일: test@example.com"

        masked_text, mapping = masker.mask(text)

        assert "test@example.com" not in masked_text
        assert "[EMAIL_" in masked_text

        restored = masker.restore(masked_text, mapping)
        assert restored == text

    def test_mask_account_number(self):
        """계좌번호 마스킹"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        text = "계좌: 123-45-678901"

        masked_text, mapping = masker.mask(text)

        assert "123-45-678901" not in masked_text

        restored = masker.restore(masked_text, mapping)
        assert restored == text

    def test_mask_business_registration_number(self):
        """사업자등록번호 마스킹"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        text = "사업자번호: 123-45-67890"

        masked_text, mapping = masker.mask(text)

        assert "123-45-67890" not in masked_text

        restored = masker.restore(masked_text, mapping)
        assert restored == text

    def test_mask_full_contract(self):
        """전체 계약서 마스킹 테스트"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        masked_text, mapping = masker.mask(SAMPLE_CONTRACT)

        # 주민번호 마스킹 확인
        assert "760815-1234567" not in masked_text
        assert "850320-2345678" not in masked_text

        # 전화번호 마스킹 확인
        assert "010-1234-5678" not in masked_text
        assert "010-9876-5432" not in masked_text

        # 이메일 마스킹 확인
        assert "kim.cs@example.com" not in masked_text
        assert "park.yh@naver.com" not in masked_text

        # 계좌번호 마스킹 확인
        assert "123-45-678901" not in masked_text

        # 복원 확인 - 핵심 개인정보가 복원되었는지 확인
        restored = masker.restore(masked_text, mapping)
        assert "760815-1234567" in restored
        assert "850320-2345678" in restored
        assert "010-1234-5678" in restored
        assert "010-9876-5432" in restored
        assert "kim.cs@example.com" in restored
        assert "park.yh@naver.com" in restored
        assert "123-45-678901" in restored

    def test_mask_with_result(self):
        """MaskingResult 반환 테스트"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        result = masker.mask_with_result(SAMPLE_CONTRACT)

        assert result.mode == "fast"
        assert len(result.mapping) > 0
        assert result.processing_time > 0

        # 엔티티 타입 확인
        assert "RRN" in result.detected_entities or "PHONE" in result.detected_entities


class TestPIIMaskerBalancedMode:
    """Balanced 모드 테스트 (Presidio + LLM)"""

    @pytest.mark.skipif(
        not (os.getenv("LOCAL_LLM_BASE_URL") or os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_API_KEY")),
        reason="LLM configuration not available"
    )
    def test_mask_with_llm(self):
        """LLM을 사용한 이름/주소 마스킹"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="balanced")

        # LLM이 설정되었는지 확인
        if masker.llm_client is None:
            pytest.skip("LLM client not configured")

        masked_text, mapping = masker.mask(SAMPLE_CONTRACT)

        # 패턴 기반 마스킹 확인
        assert "760815-1234567" not in masked_text
        assert "010-1234-5678" not in masked_text

        # LLM 기반 이름 마스킹 확인 (있을 수 있음)
        # 참고: LLM 응답에 따라 결과가 다를 수 있음
        print(f"\n감지된 엔티티 수: {len(mapping)}")
        print(f"마스킹된 항목: {list(mapping.keys())}")

        # 복원 확인
        restored = masker.restore(masked_text, mapping)

        # 원본의 핵심 내용이 복원되었는지 확인
        assert "주민등록번호" in restored
        assert "연락처" in restored


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    def test_mask_text_function(self):
        """mask_text 편의 함수 테스트"""
        from apps.ai_service.services.pii_masker import mask_text, restore_text

        text = "전화번호: 010-1234-5678"

        masked, mapping = mask_text(text, mode="fast")
        restored = restore_text(masked, mapping)

        assert "010-1234-5678" not in masked
        assert restored == text

    def test_get_masker_singleton(self):
        """싱글톤 패턴 테스트"""
        from apps.ai_service.services.pii_masker import get_masker

        masker1 = get_masker(mode="fast")
        masker2 = get_masker(mode="fast")

        assert masker1 is masker2


class TestRestoreFunction:
    """복원 기능 상세 테스트"""

    def test_restore_multiple_same_type(self):
        """동일 타입 여러 개 복원"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        text = """
        전화1: 010-1111-2222
        전화2: 010-3333-4444
        전화3: 010-5555-6666
        """

        masked_text, mapping = masker.mask(text)

        # 모든 전화번호가 마스킹되어야 함
        assert "010-1111-2222" not in masked_text
        assert "010-3333-4444" not in masked_text
        assert "010-5555-6666" not in masked_text

        # 복원 후 모든 전화번호가 있어야 함
        restored = masker.restore(masked_text, mapping)
        assert "010-1111-2222" in restored
        assert "010-3333-4444" in restored
        assert "010-5555-6666" in restored

    def test_restore_preserves_structure(self):
        """복원 후 문서 구조 유지"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")

        original = """제1조 (당사자)
임대인: 김철수 (주민등록번호: 760815-1234567)
주소: 서울특별시 강남구 테헤란로 123
연락처: 010-1234-5678"""

        masked_text, mapping = masker.mask(original)
        restored = masker.restore(masked_text, mapping)

        # 구조가 동일해야 함
        assert restored == original

    def test_restore_with_llm_response(self):
        """LLM 응답에서 플레이스홀더 복원"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")

        # 원본 텍스트 마스킹
        original = "김철수(010-1234-5678)에게 연락하세요."
        masked_text, mapping = masker.mask(original)

        # LLM이 플레이스홀더를 그대로 사용한 응답을 생성했다고 가정
        # 예: "[PHONE_1]에게 연락드리겠습니다"
        simulated_llm_response = f"연락처 {list(mapping.keys())[0]}(으)로 연락드리겠습니다."

        # 응답에서 복원
        restored_response = masker.restore(simulated_llm_response, mapping)

        # 실제 전화번호가 복원되어야 함
        assert "010-1234-5678" in restored_response


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_text(self):
        """빈 텍스트"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        masked_text, mapping = masker.mask("")

        assert masked_text == ""
        assert len(mapping) == 0

    def test_no_pii(self):
        """PII가 없는 텍스트"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        text = "이 문서에는 개인정보가 없습니다. 단순한 텍스트입니다."

        masked_text, mapping = masker.mask(text)

        assert masked_text == text
        assert len(mapping) == 0

    def test_overlapping_patterns(self):
        """겹치는 패턴 처리"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        # 여러 개인정보가 연속으로 있는 경우
        text = "연락처: 010-1234-5678, 이메일: test@example.com"

        masked_text, mapping = masker.mask(text)
        restored = masker.restore(masked_text, mapping)

        # 복원 후 핵심 정보가 있어야 함
        assert "010-1234-5678" in restored
        assert "test@example.com" in restored

    def test_special_characters(self):
        """특수 문자가 포함된 텍스트"""
        from apps.ai_service.services.pii_masker import PIIMasker

        masker = PIIMasker(mode="fast")
        text = "이메일: test+special@example.com, 전화: 010-1234-5678"

        masked_text, mapping = masker.mask(text)
        restored = masker.restore(masked_text, mapping)

        assert restored == text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
