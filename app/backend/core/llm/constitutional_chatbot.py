"""
Constitutional AI 적용 형사법 챗봇

이 모듈은 Anthropic의 Constitutional AI 방법론을 적용하여
법률 정보의 정확성과 안전성을 보장합니다.

주요 기능:
1. Constitutional Principles 기반 답변 생성
2. 3-Shot Learning으로 패턴 학습
3. 자기 검증 (Self-Critique) 메커니즘
4. 출처 기반 답변으로 Hallucination 방지
"""

from typing import Dict, List, Any, Optional
import json
from loguru import logger

from app.backend.core.retrieval.retriever import LegalDocumentRetriever
from app.backend.core.llm.llm_client import LLMClient
from app.backend.core.llm.constitutional_prompts import (
    ConstitutionalPromptBuilder,
    ConstitutionalPrinciples,
    FewShotExamples
)


class ConstitutionalLawChatbot:
    """
    Constitutional AI를 적용한 형사법 챗봇

    설계 원칙:
    1. 검색된 문서만을 기반으로 답변 (No Hallucination)
    2. 모든 주장에 출처 명시 (Transparency)
    3. 자기 검증으로 품질 보장 (Self-Critique)
    4. 법률 자문이 아닌 정보 제공임을 명시 (Disclaimer)
    """

    def __init__(
        self,
        retriever: LegalDocumentRetriever,
        llm_client: LLMClient,
        enable_self_critique: bool = True,
        critique_threshold: float = 0.5
    ):
        """
        Args:
            retriever: 문서 검색기
            llm_client: LLM 클라이언트 (GPT-4 또는 Claude)
            enable_self_critique: 자기 검증 활성화 여부
                - True: 2단계 생성 (초기 답변 → 검증 → 수정)
                - False: 1단계 생성 (빠르지만 품질 낮음)
            critique_threshold: 재생성 임계값 (0-1)
                - 위반 비율이 이 값을 초과하면 답변 재생성
        """
        self.retriever = retriever
        self.llm_client = llm_client
        self.enable_self_critique = enable_self_critique
        self.critique_threshold = critique_threshold
        self.prompt_builder = ConstitutionalPromptBuilder()

        # 대화 히스토리
        self.conversation_history: List[Dict[str, str]] = []

        # 시스템 프롬프트 설정
        self.system_prompt = self.prompt_builder.build_system_prompt()

        logger.info(
            f"Constitutional Chatbot 초기화 "
            f"(Self-Critique: {enable_self_critique}, "
            f"Few-Shot: {FewShotExamples.get_example_count()}개)"
        )

    def chat(
        self,
        query: str,
        top_k: int = 5,
        include_critique_log: bool = False
    ) -> Dict[str, Any]:
        """
        사용자 질문에 답변 (Constitutional AI 적용)

        프로세스:
        1. 관련 문서 검색 (RAG)
        2. 초기 답변 생성 (Few-Shot + Constitutional Prompting)
        3. 자기 검증 (선택적)
        4. 답변 수정 (필요시)

        Args:
            query: 사용자 질문
            top_k: 검색할 문서 수
            include_critique_log: 검증 로그 포함 여부 (디버깅용)

        Returns:
            {
                'answer': 최종 답변,
                'sources': 검색된 문서,
                'query': 원본 질문,
                'critique': 검증 결과 (선택적),
                'revised': 수정 여부
            }
        """
        logger.info(f"User query: {query}")

        # Step 1: 문서 검색 (RAG)
        # 왜 RAG를 사용하는가?
        # - LLM만으로는 최신 판례/법령을 알 수 없음
        # - 검색된 문서 기반 답변으로 Hallucination 방지
        retrieved_docs = self.retriever.retrieve(query, top_k=top_k)

        if not retrieved_docs:
            logger.warning("No documents retrieved")
            return self._handle_no_documents(query)

        # 검색된 문서를 컨텍스트로 포맷
        context = self.retriever.format_context(retrieved_docs)

        # Step 2: 초기 답변 생성
        # Constitutional Principles + Few-Shot Learning 적용
        initial_answer = self._generate_initial_answer(query, context)

        response = {
            'query': query,
            'sources': retrieved_docs,
            'answer': initial_answer,
            'revised': False
        }

        # Step 3 & 4: 자기 검증 및 수정 (선택적)
        if self.enable_self_critique:
            critique_result = self._critique_answer(query, initial_answer, context)

            if include_critique_log:
                response['critique'] = critique_result

            # 위반 사항이 임계값을 초과하면 답변 수정
            if self._should_revise(critique_result):
                logger.info("Revising answer due to violations")
                revised_answer = self._revise_answer(initial_answer, critique_result)
                response['answer'] = revised_answer
                response['revised'] = True

        # 대화 히스토리 업데이트
        self.conversation_history.append({
            'role': 'user',
            'content': query
        })
        self.conversation_history.append({
            'role': 'assistant',
            'content': response['answer']
        })

        logger.info(f"Response generated (revised: {response['revised']})")
        return response

    def _generate_initial_answer(self, query: str, context: str) -> str:
        """
        초기 답변 생성

        적용 기법:
        1. Constitutional Principles: 6가지 원칙 명시
        2. Few-Shot Learning: 3개 예시로 패턴 학습
        3. 구조화된 프롬프트: 단계별 지시사항
        """
        # Constitutional AI 프롬프트 생성
        user_prompt = self.prompt_builder.build_user_prompt(query, context)

        # LLM 호출
        # 왜 temperature=0.1?
        # - 법률 정보는 일관성이 중요
        # - 창의성보다 정확성 우선
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]

        answer = self.llm_client.chat(messages, temperature=0.1)

        return answer

    def _critique_answer(
        self,
        query: str,
        answer: str,
        context: str
    ) -> Dict[str, Any]:
        """
        답변 자기 검증

        Constitutional AI의 핵심:
        - AI가 자신의 답변을 원칙에 따라 검토
        - 위반 사항을 스스로 찾아냄
        - 개선 방향 제시

        Returns:
            {
                'violations': [...],
                'needs_revision': bool,
                'revision_suggestions': [...]
            }
        """
        critique_prompt = self.prompt_builder.build_critique_prompt(
            query, answer, context
        )

        messages = [
            {'role': 'system', 'content': '당신은 법률 답변 품질 검토자입니다.'},
            {'role': 'user', 'content': critique_prompt}
        ]

        try:
            # LLM에게 자기 답변 검증 요청
            critique_response = self.llm_client.chat(messages, temperature=0.0)

            # JSON 파싱
            critique_result = json.loads(critique_response)

            logger.info(f"Critique completed: {critique_result.get('needs_revision', False)}")
            return critique_result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse critique response: {e}")
            # 파싱 실패 시 안전하게 처리
            return {
                'violations': [],
                'needs_revision': False,
                'revision_suggestions': []
            }

    def _should_revise(self, critique_result: Dict[str, Any]) -> bool:
        """
        답변 수정 필요 여부 판단

        기준:
        1. needs_revision 플래그
        2. 위반 비율이 임계값 초과
        """
        if critique_result.get('needs_revision', False):
            return True

        violations = critique_result.get('violations', [])
        if not violations:
            return False

        # 위반 비율 계산
        violated_count = sum(1 for v in violations if v.get('violated', False))
        violation_rate = violated_count / len(violations)

        return violation_rate > self.critique_threshold

    def _revise_answer(
        self,
        original_answer: str,
        critique_result: Dict[str, Any]
    ) -> str:
        """
        위반 사항을 수정하여 개선된 답변 생성

        목표:
        - 모든 Constitutional Principles 준수
        - 핵심 내용은 유지
        - 출처와 면책 조항 명확화
        """
        revision_prompt = self.prompt_builder.build_revision_prompt(
            original_answer, critique_result
        )

        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': revision_prompt}
        ]

        revised_answer = self.llm_client.chat(messages, temperature=0.1)

        logger.info("Answer revised successfully")
        return revised_answer

    def _handle_no_documents(self, query: str) -> Dict[str, Any]:
        """
        검색 결과가 없을 때 처리

        Constitutional Principle: No Hallucination
        - 정보가 없으면 솔직하게 인정
        - 추측하거나 일반 지식으로 답변하지 않음
        """
        answer = f"""죄송합니다. '{query}'에 대한 관련 법률 정보를 데이터베이스에서 찾을 수 없습니다.

다음과 같이 시도해보세요:
1. 질문을 더 구체적으로 표현
2. 법률 용어를 사용 (예: "돈을 훔쳤어요" → "절도죄")
3. 관련 법령이나 판례 번호 제시

⚠️ 구체적인 법률 문제는 변호사와 상담하시기 바랍니다."""

        return {
            'query': query,
            'answer': answer,
            'sources': [],
            'revised': False
        }

    def clear_history(self) -> None:
        """대화 히스토리 초기화"""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """챗봇 통계 정보"""
        return {
            'conversation_turns': len(self.conversation_history) // 2,
            'self_critique_enabled': self.enable_self_critique,
            'few_shot_examples': FewShotExamples.get_example_count(),
            'constitutional_principles': len(ConstitutionalPrinciples.PRINCIPLES),
            'system_prompt_tokens': len(self.system_prompt.split())
        }


class ExperimentalChatbot(ConstitutionalLawChatbot):
    """
    실험용 챗봇 (A/B 테스트, 파라미터 조정 등)

    학습 목적:
    - 다양한 설정 비교
    - 성능 메트릭 수집
    - 프롬프트 엔지니어링 실험
    """

    def __init__(
        self,
        retriever: LegalDocumentRetriever,
        llm_client: LLMClient,
        experiment_config: Optional[Dict[str, Any]] = None
    ):
        """
        실험 설정을 받아서 초기화

        예시 설정:
        {
            'few_shot_count': 3,  # 0, 1, 3, 5
            'enable_self_critique': True,
            'critique_threshold': 0.5,
            'use_hybrid_search': False,  # Semantic + BM25
            'rerank_method': 'mmr'  # None, 'mmr', 'cross-encoder'
        }
        """
        self.experiment_config = experiment_config or {}

        super().__init__(
            retriever=retriever,
            llm_client=llm_client,
            enable_self_critique=self.experiment_config.get('enable_self_critique', True),
            critique_threshold=self.experiment_config.get('critique_threshold', 0.5)
        )

        self.metrics = {
            'total_queries': 0,
            'revisions': 0,
            'avg_response_time': 0,
            'avg_sources_used': 0
        }

    def chat(self, query: str, **kwargs) -> Dict[str, Any]:
        """실험 메트릭 수집하면서 답변 생성"""
        import time

        start_time = time.time()

        response = super().chat(query, **kwargs)

        # 메트릭 수집
        self.metrics['total_queries'] += 1
        if response.get('revised', False):
            self.metrics['revisions'] += 1

        response_time = time.time() - start_time
        self.metrics['avg_response_time'] = (
            (self.metrics['avg_response_time'] * (self.metrics['total_queries'] - 1) + response_time)
            / self.metrics['total_queries']
        )

        self.metrics['avg_sources_used'] = (
            (self.metrics['avg_sources_used'] * (self.metrics['total_queries'] - 1) + len(response['sources']))
            / self.metrics['total_queries']
        )

        return response

    def get_experiment_results(self) -> Dict[str, Any]:
        """실험 결과 요약"""
        return {
            'config': self.experiment_config,
            'metrics': self.metrics,
            'revision_rate': self.metrics['revisions'] / max(self.metrics['total_queries'], 1)
        }


# 사용 예시
if __name__ == "__main__":
    """
    사용 예시 및 테스트 코드

    실제 사용 시:
    1. retriever와 llm_client를 먼저 초기화
    2. ConstitutionalLawChatbot 인스턴스 생성
    3. chat() 메서드로 질문
    """

    # 예시: 기본 사용
    print("=== Constitutional Law Chatbot 예시 ===\n")
    print("기능:")
    print("1. Constitutional AI: 6가지 원칙 준수")
    print("2. Few-Shot Learning: 3개 예시로 패턴 학습")
    print("3. Self-Critique: 자기 검증으로 품질 보장")
    print("4. 출처 기반 답변: Hallucination 방지")

    print("\n실험 가능한 파라미터:")
    print("- few_shot_count: 0, 1, 3, 5")
    print("- enable_self_critique: True/False")
    print("- critique_threshold: 0.0 ~ 1.0")
    print("- top_k (retrieval): 3, 5, 10")
