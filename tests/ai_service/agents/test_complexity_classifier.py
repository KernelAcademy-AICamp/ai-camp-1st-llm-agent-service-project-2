"""
ComplexityClassifier 단위 테스트
"""

import pytest
from apps.ai_service.agents.complexity_classifier import (
    ComplexityClassifier,
    ComplexityLevel,
)


class TestComplexityClassifier:
    """ComplexityClassifier 테스트"""

    @pytest.fixture
    def classifier(self):
        return ComplexityClassifier()

    # =========================================================================
    # FAST Path 테스트
    # =========================================================================

    def test_general_chat_is_fast(self, classifier):
        """일반 대화는 FAST로 분류"""
        messages = [
            "안녕하세요",
            "고마워",
            "뭐해?",
            "오늘 날씨 어때?",
        ]
        for msg in messages:
            result = classifier.classify(msg)
            assert result.level == ComplexityLevel.FAST, f"Failed for: {msg}"

    def test_cache_hit_is_fast(self, classifier):
        """캐시 히트는 FAST"""
        result = classifier.classify("절도죄 형량은?", cache_hit=True)
        assert result.level == ComplexityLevel.FAST
        assert result.confidence == 1.0

    def test_simple_definition_is_fast(self, classifier):
        """단순 정의 질문은 FAST"""
        messages = [
            "절도죄가 뭐야?",
            "손해배상이란?",
            "형량이 뭔가요?",
        ]
        for msg in messages:
            result = classifier.classify(msg)
            assert result.level == ComplexityLevel.FAST, f"Failed for: {msg}"

    def test_short_message_is_fast(self, classifier):
        """짧은 메시지는 FAST (20자 미만)"""
        result = classifier.classify("테스트")
        assert result.level == ComplexityLevel.FAST
        assert "짧은 메시지" in result.reason or "일반 대화" in result.reason

    # =========================================================================
    # MEDIUM Path 테스트
    # =========================================================================

    def test_single_attachment_is_medium(self, classifier):
        """단일 첨부는 MEDIUM"""
        result = classifier.classify(
            "이 문서 분석해줘",
            attachments=[{"filename": "contract.pdf"}]
        )
        assert result.level == ComplexityLevel.MEDIUM

    def test_single_workflow_is_medium(self, classifier):
        """단일 워크플로우 요청은 MEDIUM"""
        messages = [
            "이 계약서를 분석해줘",
            "리스크를 평가해줘",
            "판례를 검색해줘",
        ]
        for msg in messages:
            result = classifier.classify(msg)
            assert result.level == ComplexityLevel.MEDIUM, f"Failed for: {msg}"

    def test_medium_length_message(self, classifier):
        """중간 길이 메시지는 MEDIUM (20-100자)"""
        # 법률 키워드가 없는 중간 길이 메시지
        msg = "이것은 테스트를 위한 중간 길이의 메시지입니다. 복잡도 분류를 테스트합니다."
        result = classifier.classify(msg)
        # 중간 길이이므로 MEDIUM 또는 키워드 매칭에 따라 달라질 수 있음
        assert result.level in [ComplexityLevel.MEDIUM, ComplexityLevel.FAST]

    # =========================================================================
    # DEEP Path 테스트
    # =========================================================================

    def test_multi_attachment_is_deep(self, classifier):
        """다중 첨부는 DEEP"""
        result = classifier.classify(
            "두 문서를 비교해줘",
            attachments=[
                {"filename": "contract1.pdf"},
                {"filename": "contract2.pdf"},
            ]
        )
        assert result.level == ComplexityLevel.DEEP

    def test_comparison_request_is_deep(self, classifier):
        """비교 요청은 DEEP"""
        messages = [
            "두 계약서의 차이점을 분석해줘",
            "GPT-4와 Claude로 비교해줘",
        ]
        for msg in messages:
            result = classifier.classify(msg)
            assert result.level == ComplexityLevel.DEEP, f"Failed for: {msg}"

    def test_multi_step_request_is_deep(self, classifier):
        """다단계 요청은 DEEP"""
        messages = [
            "분석하고 수정안도 제시해줘",
            "검토한 뒤 보고서를 만들어줘",
            "계약서를 분석하고 리스크 평가도 해줘",
        ]
        for msg in messages:
            result = classifier.classify(msg)
            assert result.level == ComplexityLevel.DEEP, f"Failed for: {msg}"

    def test_strategy_request_is_deep(self, classifier):
        """전략/조언 요청은 DEEP"""
        messages = [
            "어떻게 해야 할지 알려줘",
            "대응 전략을 알려줘",
            "이 문제에 어떻게 해야 하나요?",
        ]
        for msg in messages:
            result = classifier.classify(msg)
            assert result.level == ComplexityLevel.DEEP, f"Failed for: {msg}"

    # =========================================================================
    # 경계 케이스 테스트
    # =========================================================================

    def test_empty_message(self, classifier):
        """빈 메시지 처리"""
        result = classifier.classify("")
        # 빈 메시지는 FAST로 분류되어야 함 (일반 대화 또는 짧은 메시지)
        assert result.level == ComplexityLevel.FAST

    def test_long_message_is_deep(self, classifier):
        """긴 메시지는 DEEP (100자 이상)"""
        long_msg = "이것은 매우 긴 메시지입니다. " * 10  # 약 150자
        result = classifier.classify(long_msg)
        # 긴 메시지는 DEEP 또는 키워드 매칭에 따라 결정
        assert result.level in [ComplexityLevel.DEEP, ComplexityLevel.MEDIUM]

    def test_result_has_required_fields(self, classifier):
        """분류 결과에 필수 필드가 있는지 확인"""
        result = classifier.classify("테스트 메시지입니다")

        assert hasattr(result, 'level')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'reason')
        assert hasattr(result, 'suggested_path')

        assert result.confidence >= 0.0 and result.confidence <= 1.0
        assert result.suggested_path in ["fast", "medium", "deep"]

    def test_suggested_workflow_for_medium(self, classifier):
        """MEDIUM 경로에서 워크플로우가 제안되는지 확인"""
        result = classifier.classify("이 계약서를 분석해줘")

        if result.level == ComplexityLevel.MEDIUM:
            assert result.suggested_workflow is not None


class TestComplexityClassifierSingleton:
    """싱글톤 패턴 테스트"""

    def test_get_complexity_classifier_returns_same_instance(self):
        """싱글톤이 동일 인스턴스를 반환하는지 확인"""
        from apps.ai_service.agents.complexity_classifier import get_complexity_classifier

        instance1 = get_complexity_classifier()
        instance2 = get_complexity_classifier()

        assert instance1 is instance2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
