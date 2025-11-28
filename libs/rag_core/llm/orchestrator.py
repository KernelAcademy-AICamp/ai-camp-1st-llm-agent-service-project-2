"""
멀티 에이전트 RAG 오케스트레이터

설계 원칙:
- 기존 ConstitutionalLawChatbot을 감싸는 Decorator/Strategy 패턴
- 단일 파일로 모든 에이전트 로직 통합
- Phase 2의 ResponseMode와 연동

사용 예:
    # 방법 1: 기존 chatbot 래핑
    orchestrator = LegalRAGOrchestrator(chatbot=existing_chatbot)

    # 방법 2: 새로 생성
    orchestrator = LegalRAGOrchestrator(
        retriever=retriever,
        llm_client=llm_client
    )

    # 질문 처리
    result = orchestrator.chat("절도죄란?")
    result = orchestrator.chat("절도죄와 강도죄 비교", mode=ResponseMode.DETAILED)
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
import time
import logging

from libs.rag_core.llm.response_modes import ResponseMode, ResponseModeConfig, QueryClassifier

if TYPE_CHECKING:
    from libs.rag_core.llm.constitutional_chatbot import ConstitutionalLawChatbot
    from libs.rag_core.retrieval.retriever import LegalDocumentRetriever
    from libs.rag_core.llm.llm_client import LLMClient

logger = logging.getLogger(__name__)


# ===== 데이터 클래스 =====

@dataclass
class OrchestratorResult:
    """Orchestrator 실행 결과"""
    answer: str
    sources: list
    query: str
    mode: str
    strategy_used: str
    processing_time: float
    revised: bool = False
    summarized: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


# ===== 전략 클래스 (내부용) =====

class _QuickStrategy:
    """CONCISE 모드용 빠른 응답 전략"""

    QUICK_INSTRUCTION = """
**답변은 100자 이내로 핵심만 간결하게 작성하세요.**
- 불필요한 부연 설명 생략
- 핵심 정보와 출처만 포함
"""

    @staticmethod
    def get_config() -> Dict[str, Any]:
        return {
            "top_k": 2,
            "enable_critique": False,
            "extra_instruction": _QuickStrategy.QUICK_INSTRUCTION
        }


class _DeepStrategy:
    """DETAILED 모드용 상세 응답 전략"""

    DEEP_INSTRUCTION = """
**답변은 300-400자로 상세하게 작성하세요.**
- 관련 조문과 판례를 충분히 인용
- 구조화된 형식(번호, 목록) 사용
- 비교/분석이 필요하면 표 사용
"""

    @staticmethod
    def get_config() -> Dict[str, Any]:
        return {
            "top_k": 5,
            "enable_critique": True,
            "extra_instruction": _DeepStrategy.DEEP_INSTRUCTION
        }


class _StandardStrategy:
    """STANDARD 모드용 표준 응답 전략"""

    STANDARD_INSTRUCTION = """
**답변은 150-200자로 적절한 상세도로 작성하세요.**
- 핵심 정보와 간단한 설명 포함
- 주요 출처 명시
"""

    @staticmethod
    def get_config() -> Dict[str, Any]:
        return {
            "top_k": 3,
            "enable_critique": False,
            "extra_instruction": _StandardStrategy.STANDARD_INSTRUCTION
        }


class _Summarizer:
    """긴 답변을 요약하는 내부 유틸리티"""

    SUMMARIZE_PROMPT = """다음 법률 답변을 {target_length}자 이내로 요약하세요.

원본 질문: {question}

원본 답변:
{answer}

요약 규칙:
1. 핵심 정보만 유지
2. 출처 표시 유지 ([법령: ...], [판례: ...])
3. 면책 조항 유지
4. 불필요한 부연 설명 제거

요약:"""

    def __init__(self, llm_client: "LLMClient"):
        self.llm_client = llm_client

    def condense(self, answer: str, question: str, target_length: int = 150) -> str:
        """답변 요약 (동기)"""
        prompt = self.SUMMARIZE_PROMPT.format(
            target_length=target_length,
            question=question,
            answer=answer
        )

        messages = [
            {"role": "system", "content": "법률 답변을 간결하게 요약합니다."},
            {"role": "user", "content": prompt}
        ]

        summarized = self.llm_client.chat(messages, temperature=0.1)
        logger.info(f"Summarized: {len(answer)} → {len(summarized)} chars")

        return summarized


# ===== 메인 Orchestrator =====

class LegalRAGOrchestrator:
    """
    법률 RAG 멀티 에이전트 오케스트레이터

    기존 ConstitutionalLawChatbot을 감싸고 ResponseMode에 따라
    적절한 전략을 선택하여 답변을 최적화합니다.

    사용 예:
        # 방법 1: 기존 chatbot 래핑
        orchestrator = LegalRAGOrchestrator(chatbot=existing_chatbot)

        # 방법 2: 새로 생성
        orchestrator = LegalRAGOrchestrator(
            retriever=retriever,
            llm_client=llm_client
        )

        # 질문 처리
        result = orchestrator.chat("절도죄란?")
        result = orchestrator.chat("절도죄와 강도죄 비교", mode=ResponseMode.DETAILED)
    """

    # 전략 매핑
    STRATEGIES = {
        ResponseMode.CONCISE: _QuickStrategy,
        ResponseMode.STANDARD: _StandardStrategy,
        ResponseMode.DETAILED: _DeepStrategy,
    }

    def __init__(
        self,
        chatbot: Optional["ConstitutionalLawChatbot"] = None,
        retriever: Optional["LegalDocumentRetriever"] = None,
        llm_client: Optional["LLMClient"] = None,
        enable_summarization: bool = True,
        summarize_threshold: int = 800  # 이 글자 수 초과 시 요약
    ):
        """
        Args:
            chatbot: 기존 ConstitutionalLawChatbot 인스턴스 (있으면 재사용)
            retriever: 문서 검색기 (chatbot이 없을 때 필요)
            llm_client: LLM 클라이언트 (chatbot이 없을 때 필요)
            enable_summarization: 요약 기능 활성화
            summarize_threshold: 요약 트리거 글자 수
        """
        # 지연 임포트 (순환 참조 방지)
        from libs.rag_core.llm.constitutional_chatbot import ConstitutionalLawChatbot

        # 기존 chatbot 사용 또는 새로 생성
        if chatbot:
            self.chatbot = chatbot
            self.llm_client = chatbot.llm_client
        elif retriever and llm_client:
            self.chatbot = ConstitutionalLawChatbot(
                retriever=retriever,
                llm_client=llm_client,
                enable_self_critique=False  # Orchestrator가 제어
            )
            self.llm_client = llm_client
        else:
            raise ValueError("chatbot 또는 (retriever, llm_client) 필요")

        self.enable_summarization = enable_summarization
        self.summarize_threshold = summarize_threshold
        self.summarizer = _Summarizer(self.llm_client)

        # 메트릭
        self.metrics = {
            "total_queries": 0,
            "concise_count": 0,
            "standard_count": 0,
            "detailed_count": 0,
            "summarized_count": 0,
            "avg_response_time": 0.0
        }

        logger.info("LegalRAGOrchestrator initialized")

    def chat(
        self,
        query: str,
        mode: Optional[ResponseMode] = None,
        top_k: Optional[int] = None,
        include_critique_log: bool = False
    ) -> OrchestratorResult:
        """
        질문 처리 메인 메서드

        Args:
            query: 사용자 질문
            mode: 응답 모드 (None이면 자동 분류)
            top_k: 검색 문서 수 (None이면 모드에 따라 자동)
            include_critique_log: 검증 로그 포함 여부

        Returns:
            OrchestratorResult: 처리 결과
        """
        start_time = time.time()

        # 1. 모드 결정
        if mode is None:
            mode = QueryClassifier.classify(query)
        logger.info(f"Query mode: {mode.value}")

        # 2. 전략 선택
        strategy = self.STRATEGIES.get(mode, _StandardStrategy)
        config = strategy.get_config()

        # 3. top_k 결정 (명시적 > 전략 기본값)
        effective_top_k = top_k or config["top_k"]

        # 4. 기존 chatbot으로 답변 생성
        # Self-Critique는 DETAILED 모드에서만
        self.chatbot.enable_self_critique = config["enable_critique"]

        chatbot_result = self.chatbot.chat(
            query=query,
            top_k=effective_top_k,
            include_critique_log=include_critique_log and config["enable_critique"]
        )

        answer = chatbot_result['answer']
        sources = chatbot_result['sources']
        revised = chatbot_result.get('revised', False)

        # 5. 필요시 요약 (DETAILED 모드 제외)
        summarized = False
        if (self.enable_summarization and
            mode != ResponseMode.DETAILED and
            len(answer) > self.summarize_threshold):

            logger.info(f"Answer too long ({len(answer)}), summarizing...")
            answer = self.summarizer.condense(answer, query, target_length=400)
            summarized = True
            self.metrics["summarized_count"] += 1

        # 6. 메트릭 업데이트
        processing_time = time.time() - start_time
        self._update_metrics(mode, processing_time)

        # 7. 결과 반환
        return OrchestratorResult(
            answer=answer,
            sources=sources,
            query=query,
            mode=mode.value,
            strategy_used=strategy.__name__,
            processing_time=processing_time,
            revised=revised,
            summarized=summarized,
            metadata={
                "top_k": effective_top_k,
                "critique_enabled": config["enable_critique"],
                "critique_log": chatbot_result.get('critique') if include_critique_log else None
            }
        )

    def _update_metrics(self, mode: ResponseMode, response_time: float):
        """메트릭 업데이트"""
        self.metrics["total_queries"] += 1

        mode_key = f"{mode.value}_count"
        if mode_key in self.metrics:
            self.metrics[mode_key] += 1

        n = self.metrics["total_queries"]
        self.metrics["avg_response_time"] = (
            (self.metrics["avg_response_time"] * (n - 1) + response_time) / n
        )

    def get_metrics(self) -> Dict[str, Any]:
        """현재 메트릭 반환"""
        total = max(self.metrics["total_queries"], 1)
        return {
            **self.metrics,
            "concise_ratio": self.metrics["concise_count"] / total,
            "standard_ratio": self.metrics["standard_count"] / total,
            "detailed_ratio": self.metrics["detailed_count"] / total,
            "summarize_ratio": self.metrics["summarized_count"] / total
        }

    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 (chatbot 통계 포함)"""
        return {
            "orchestrator_metrics": self.get_metrics(),
            "chatbot_statistics": self.chatbot.get_statistics() if hasattr(self.chatbot, 'get_statistics') else {}
        }
