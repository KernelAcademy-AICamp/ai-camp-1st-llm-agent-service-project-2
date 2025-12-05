"""
Complexity Classifier - 질문 복잡도 분류기

Phase 6-3: 법률 서비스 최적화 재설계

핵심 원칙:
1. "법률 질문 vs 일반 대화" 먼저 구분 (글자 수 X)
2. 법률 질문 → 항상 적절한 도구 사용 (RAG/MCP/법령 API)
3. 일반 대화 → FAST (LLM 직접 응답)
4. 사용자가 특별한 프롬프트를 사용할 필요 없음

분류 우선순위:
1. 캐시 히트 → FAST
2. 일반 대화 (법률 무관) → FAST
3. 법률 질문 → MEDIUM/DEEP/THINKING (복잡도에 따라)
"""

from typing import List, Dict, Any, Optional
import logging
import re

from apps.ai_service.agents.states.master_agent_state import (
    ComplexityLevel,
    ComplexityResult,
)
from apps.ai_service.agents.intent_classifier import (
    IntentClassifier,
    is_general_chat,
    LEGAL_KEYWORDS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 법률 질문 감지 (핵심!)
# =============================================================================

def is_legal_question(message: str) -> bool:
    """
    법률 관련 질문인지 판단

    LEGAL_KEYWORDS가 하나라도 포함되면 법률 질문으로 판단

    Args:
        message: 사용자 메시지

    Returns:
        법률 질문 여부
    """
    normalized = message.lower().strip()

    for keyword in LEGAL_KEYWORDS:
        if keyword in normalized:
            return True

    return False


# =============================================================================
# 복잡도 분류 규칙
# =============================================================================

DEEP_KEYWORDS = {
    # 복합 요청 (순차적 작업)
    "multi_request": [
        "그리고", "한 뒤", "한뒤", "다음에", "후에", "또한", "추가로",
        "~하고", "한 다음", "한다음",
    ],
    # 비교 요청
    "comparison": ["비교", "차이점", "다른 점", "다른점", "vs", "versus"],
    # 전략/조언
    "strategy": [
        "어떻게 해야", "어떻게해야", "어떻게 할", "어떻게할",
        "전략", "방안", "대응", "조언",
    ],
    # 분석 + 생성
    "analysis_gen": [
        "분석하고", "검토하고", "평가하고",
        "검토한 뒤", "검토한뒤", "분석한 뒤", "분석한뒤",
        "보고서를 만들어", "보고서 만들어", "작성해줘",
    ],
    # 형사법 관련 (Phase 1: 형사법 특화)
    "criminal_law": [
        "구성요건", "고의", "과실", "위법성", "책임",
        "양형", "형량", "집행유예", "선고유예",
        "변호 전략", "변호전략", "무죄 주장", "무죄주장",
        "유리한 정상", "불리한 정상", "양형인자",
        "기소 가능성", "기소가능성", "처벌 수위", "처벌수위",
    ],
}

# MEDIUM Path 워크플로우 매핑
MEDIUM_WORKFLOW_MAP = {
    "document_workflow": ["분석해", "검토해", "요약해", "정리해"],
    "risk_workflow": ["리스크", "위험", "문제점"],
    "case_workflow": ["판례", "사건", "판결"],
    "rag_workflow": ["법률", "법적", "조문", "조항"],
    # 형사법 워크플로우 (Phase 1: 형사법 특화)
    "criminal_workflow": [
        "절도", "강도", "사기", "횡령", "배임", "폭행", "상해",
        "살인", "협박", "강간", "추행", "음주운전", "뺑소니",
        "마약", "도박", "명예훼손", "모욕", "무고", "위증",
        "형사", "범죄", "기소", "공소", "수사",
    ],
}


# =============================================================================
# ComplexityClassifier 클래스
# =============================================================================

class ComplexityClassifier:
    """
    질문 복잡도 분류기

    휴리스틱 우선 + LLM 보조 방식으로 복잡도를 분류합니다.

    Attributes:
        intent_classifier: 의도 분류기 (재사용)
    """

    def __init__(self, intent_classifier: Optional[IntentClassifier] = None):
        """
        ComplexityClassifier 초기화

        Args:
            intent_classifier: IntentClassifier 인스턴스 (공유 가능)
        """
        self.intent_classifier = intent_classifier
        logger.info("ComplexityClassifier initialized")

    def classify(
        self,
        user_message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        cache_hit: bool = False,
    ) -> ComplexityResult:
        """
        복잡도 분류 실행

        핵심 원칙:
        - 법률 질문 vs 일반 대화를 먼저 구분 (글자 수 X)
        - 법률 질문 → 항상 적절한 도구 사용
        - 일반 대화 → FAST

        분류 우선순위:
        1. 캐시 히트 → FAST
        2. 일반 대화 (법률 무관) → FAST
        3. 첨부 파일 있음 → MEDIUM 이상
        4. 법률 질문 → MEDIUM (RAG 사용)
        5. 복잡한 요청 (비교/분석/전략) → DEEP
        6. 고도 추론 필요 → THINKING

        Args:
            user_message: 사용자 메시지
            attachments: 첨부 파일 목록
            conversation_history: 대화 기록
            cache_hit: 캐시 히트 여부

        Returns:
            ComplexityResult 객체
        """
        logger.debug(f"Classifying complexity for: {user_message[:50]}...")

        # 1. 캐시 히트 → FAST
        if cache_hit:
            return ComplexityResult(
                level=ComplexityLevel.FAST,
                confidence=1.0,
                reason="캐시 히트",
                suggested_path="fast",
            )

        # 2. 첨부 파일 기반 분류 (가장 명확한 시그널)
        attachment_result = self._classify_by_attachments(attachments)
        if attachment_result:
            return attachment_result

        # 3. THINKING 체크 먼저! (전략적/판단 요청)
        #    ⚠️ 일반 대화 체크보다 먼저 - "어떻게 해야 할까?"는 THINKING
        num_attachments = len(attachments) if attachments else 0
        thinking_result = self._is_thinking_path(user_message.lower(), num_attachments)
        if thinking_result:
            return thinking_result

        # 4. DEEP 키워드 체크 (복합 요청, 비교, 분석)
        deep_result = self._check_deep_keywords(user_message)
        if deep_result:
            return deep_result

        # 5. 일반 대화 → FAST (법률 키워드 없고, 일반 대화 패턴)
        #    THINKING/DEEP 체크 후에! 전략적 질문은 THINKING으로 먼저 잡힘
        if not attachments and is_general_chat(user_message):
            return ComplexityResult(
                level=ComplexityLevel.FAST,
                confidence=0.95,
                reason="일반 대화 (법률 무관)",
                suggested_path="fast",
            )

        # 6. 법률 질문 → MEDIUM (RAG 사용)
        #    ⚠️ 핵심! 글자 수와 관계없이 법률 질문은 MEDIUM
        if is_legal_question(user_message):
            return ComplexityResult(
                level=ComplexityLevel.MEDIUM,
                confidence=0.85,
                reason="법률 질문 (RAG 검색 필요)",
                suggested_path="medium",
                suggested_workflow="rag_workflow",
            )

        # 7. MEDIUM 워크플로우 매핑 (분석해, 검토해 등)
        medium_result = self._check_medium_workflow(user_message)
        if medium_result:
            return medium_result

        # 8. 그 외 → MEDIUM (기본값)
        #    글자 수 기반 분류 제거! 불확실하면 MEDIUM
        return ComplexityResult(
            level=ComplexityLevel.MEDIUM,
            confidence=0.6,
            reason="기본 분류 (MEDIUM)",
            suggested_path="medium",
        )

    def _classify_by_attachments(
        self,
        attachments: Optional[List[Dict[str, Any]]]
    ) -> Optional[ComplexityResult]:
        """첨부 파일 수 기반 분류"""
        if not attachments:
            return None

        count = len(attachments)

        if count >= 2:
            # 2개 이상 → DEEP (비교 분석 가능성)
            return ComplexityResult(
                level=ComplexityLevel.DEEP,
                confidence=0.85,
                reason=f"다중 첨부 파일 ({count}개)",
                suggested_path="deep",
                requires_planning=True,
            )
        elif count == 1:
            # 1개 → MEDIUM
            return ComplexityResult(
                level=ComplexityLevel.MEDIUM,
                confidence=0.8,
                reason="단일 첨부 파일",
                suggested_path="medium",
                suggested_workflow="document_workflow",
            )

        return None

    def _check_deep_keywords(self, message: str) -> Optional[ComplexityResult]:
        """DEEP 키워드 체크"""
        message_lower = message.lower()

        for category, keywords in DEEP_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return ComplexityResult(
                        level=ComplexityLevel.DEEP,
                        confidence=0.85,
                        reason=f"복합 요청 키워드: {keyword}",
                        suggested_path="deep",
                        requires_planning=True,
                    )

        return None

    def _check_medium_workflow(self, message: str) -> Optional[ComplexityResult]:
        """MEDIUM 워크플로우 매핑 체크"""
        message_lower = message.lower()

        for workflow, keywords in MEDIUM_WORKFLOW_MAP.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return ComplexityResult(
                        level=ComplexityLevel.MEDIUM,
                        confidence=0.8,
                        reason=f"단일 워크플로우 매핑: {workflow}",
                        suggested_path="medium",
                        suggested_workflow=workflow,
                    )

        return None

    def _is_thinking_path(
        self,
        message_lower: str,
        num_attachments: int,
    ) -> Optional[ComplexityResult]:
        """
        THINKING 경로가 필요한지 판단

        기준 (Phase 6-3 개선):
        - 전략적 질문 → 바로 THINKING
        - 판단/추천 요청 → 바로 THINKING
        - 법률 + 종합분석 → THINKING
        - 복합 조건 (점수 2점 이상) → THINKING

        핵심 원칙: 사용자가 "어떻게 하면 좋을까?"와 같은
        전략적 조언을 요청하면 단순 검색이 아닌 깊은 사고 필요
        """
        reasons = []

        # 전략적 질문 → 바로 THINKING
        strategic_keywords = [
            "어떻게 하면", "어떻게 해야", "최선의 방법", "최적의",
            "전략을", "전략적으로", "접근 방법", "가장 좋은",
            "유리한 조건", "유리하게", "효과적으로",
        ]
        for kw in strategic_keywords:
            if kw in message_lower:
                reasons.append(f"전략적 질문: '{kw}'")
                return ComplexityResult(
                    level=ComplexityLevel.THINKING,
                    confidence=0.9,
                    reason=", ".join(reasons),
                    suggested_path="thinking",
                    requires_planning=True,
                )

        # 판단/추천 요청 → 바로 THINKING
        judgment_keywords = [
            "판단해", "결정해", "어떤 것이 더", "무엇이 더",
            "추천해", "권장해", "제안해", "조언해",
            "어떻게 해야 할까", "뭐가 나을까", "좋을까요",
        ]
        for kw in judgment_keywords:
            if kw in message_lower:
                reasons.append(f"판단 요청: '{kw}'")
                return ComplexityResult(
                    level=ComplexityLevel.THINKING,
                    confidence=0.9,
                    reason=", ".join(reasons),
                    suggested_path="thinking",
                    requires_planning=True,
                )

        # 종합 분석 키워드
        comprehensive_keywords = [
            "여러 측면", "종합적", "전반적", "다각도",
            "모든 가능성", "전체적으로", "깊이 분석",
        ]

        # 복잡한 추론 키워드
        reasoning_keywords = [
            "왜냐하면", "따라서", "결론적으로", "고려할 때",
            "리스크를 분석", "위험을 평가",
        ]

        score = 0

        for kw in comprehensive_keywords:
            if kw in message_lower:
                score += 1
                reasons.append(f"종합분석: '{kw}'")
                break

        for kw in reasoning_keywords:
            if kw in message_lower:
                score += 1
                reasons.append(f"추론: '{kw}'")
                break

        # 긴 질문 추가 점수
        if len(message_lower) > 200:
            score += 1
            reasons.append("긴 질문")

        # 다중 첨부 추가 점수
        if num_attachments >= 2:
            score += 1
            reasons.append("다중 첨부")

        # 2점 이상이면 THINKING
        if score >= 2:
            return ComplexityResult(
                level=ComplexityLevel.THINKING,
                confidence=min(0.7 + score * 0.1, 0.95),
                reason=", ".join(reasons),
                suggested_path="thinking",
                requires_planning=True,
            )

        return None


# =============================================================================
# 싱글톤/팩토리
# =============================================================================

_classifier_instance: Optional[ComplexityClassifier] = None


def get_complexity_classifier() -> ComplexityClassifier:
    """
    ComplexityClassifier 인스턴스 반환 (싱글톤)
    """
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ComplexityClassifier()
    return _classifier_instance
