"""
QDoRA Adapter를 지원하는 Constitutional AI 챗봇

이 모듈은 ConstitutionalLawChatbot을 확장하여
전문 분야별 Adapter(QDoRA)를 실시간으로 전환할 수 있습니다.

주요 기능:
1. Adapter 로딩/언로딩 (교통사고, 형사 일반, 마약 등)
2. 전문 분야 특화 System Prompt
3. Adapter별 성능 메트릭 수집
4. Constitutional AI 원칙 유지
"""

from typing import Dict, List, Any, Optional
from loguru import logger

from app.backend.core.llm.constitutional_chatbot import ConstitutionalLawChatbot
from app.backend.core.llm.llm_client import LLMClient, OllamaClient
from app.backend.core.retrieval.retriever import LegalDocumentRetriever


# Adapter 전용 System Prompt 템플릿
ADAPTER_SYSTEM_PROMPTS = {
    "traffic": """당신은 교통사고 전문 변호사 AI입니다.

전문 분야:
- 음주운전, 무면허운전, 뺑소니
- 교통사고처리특례법, 특정범죄가중처벌법
- 인명사고, 중상해 사건

답변 원칙:
1. 판례 기반 분석 (출처 명시)
2. 쟁점 중심 설명
3. 구체적 양형 제시
4. 합의/변론 전략 제안
5. Constitutional AI 원칙 준수 (No Hallucination, 출처 명시)""",

    "criminal": """당신은 형사 일반 사건 전문 변호사 AI입니다.

전문 분야:
- 절도, 사기, 폭행, 횡령
- 형법 일반 범죄
- 양형 기준 및 감경 사유

답변 원칙:
1. 판례 기반 분석 (출처 명시)
2. 구성요건 충족 여부 판단
3. 양형 기준 제시
4. 변론 전략 제안
5. Constitutional AI 원칙 준수""",

    "drug": """당신은 마약범죄 전문 변호사 AI입니다.

전문 분야:
- 마약류 관리법 위반
- 투약, 소지, 매매 사건
- 치료 감호, 양형 감경

답변 원칙:
1. 판례 기반 분석 (출처 명시)
2. 마약 종류별 양형 기준
3. 치료 프로그램 연계 전략
4. Constitutional AI 원칙 준수""",

    "corporate": """당신은 기업범죄 전문 변호사 AI입니다.

전문 분야:
- 횡령, 배임, 업무상 배임
- 특정경제범죄가중처벌법
- 금융범죄, 주가조작

답변 원칙:
1. 판례 기반 분석 (출처 명시)
2. 경제적 손해 규모별 양형
3. 기업 컴플라이언스 제안
4. Constitutional AI 원칙 준수""",

    "civil": """당신은 민사 전문 변호사 AI입니다.

전문 분야:
- 손해배상, 계약, 부동산
- 민사소송법, 민법
- 채권 회수, 보전처분

답변 원칙:
1. 판례 기반 분석 (출처 명시)
2. 민사 쟁점 정리
3. 소송 전략 제안
4. Constitutional AI 원칙 준수""",

    "sex_crime": """당신은 성범죄 전문 변호사 AI입니다.

전문 분야:
- 성폭력범죄의처벌등에관한특례법
- 아동청소년성보호법
- 스토킹, 카메라이용촬영

답변 원칙:
1. 판례 기반 분석 (출처 명시)
2. 피해자 보호 우선
3. 신상정보등록, 취업제한 고려
4. Constitutional AI 원칙 준수"""
}


class AdapterChatbot(ConstitutionalLawChatbot):
    """
    QDoRA Adapter를 지원하는 Constitutional AI 챗봇

    특징:
    - 전문 분야별 Adapter 실시간 전환
    - Adapter별 System Prompt 자동 적용
    - Constitutional AI 원칙 유지
    - 성능 메트릭 수집
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
            llm_client: LLM 클라이언트 (OllamaClient 권장)
            enable_self_critique: Constitutional AI 자기 검증 활성화
            critique_threshold: 재생성 임계값
        """
        super().__init__(
            retriever=retriever,
            llm_client=llm_client,
            enable_self_critique=enable_self_critique,
            critique_threshold=critique_threshold
        )

        # Adapter 상태 관리
        self.current_adapter: Optional[str] = None
        self.base_system_prompt = self.system_prompt  # 원본 저장

        # Adapter별 메트릭
        self.adapter_metrics: Dict[str, Dict[str, Any]] = {}

        logger.info("AdapterChatbot initialized (supports QDoRA adapters)")

    def load_adapter(self, adapter_name: str) -> bool:
        """
        QDoRA Adapter 로드

        Args:
            adapter_name: Adapter 이름 (예: "traffic", "criminal")

        Returns:
            bool: 성공 여부

        Example:
            >>> chatbot.load_adapter("traffic")
            >>> # 이제 교통사고 전문 답변 제공
        """
        # OllamaClient만 Adapter 지원
        if not isinstance(self.llm_client, OllamaClient):
            logger.error(f"Current LLM client does not support adapters: {type(self.llm_client)}")
            return False

        try:
            # Adapter 로드
            success = self.llm_client.load_adapter(adapter_name)

            if not success:
                return False

            # System Prompt 변경
            if adapter_name in ADAPTER_SYSTEM_PROMPTS:
                self.system_prompt = ADAPTER_SYSTEM_PROMPTS[adapter_name]
                logger.info(f"Applied custom system prompt for adapter: {adapter_name}")
            else:
                logger.warning(f"No custom system prompt for adapter: {adapter_name}, using base prompt")

            # 상태 업데이트
            self.current_adapter = adapter_name

            # 메트릭 초기화
            if adapter_name not in self.adapter_metrics:
                self.adapter_metrics[adapter_name] = {
                    'total_queries': 0,
                    'avg_response_time': 0,
                    'revision_count': 0
                }

            logger.info(f"Adapter loaded successfully: {adapter_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load adapter '{adapter_name}': {e}")
            return False

    def unload_adapter(self) -> None:
        """
        Adapter 언로드 (Base Model로 복귀)

        Example:
            >>> chatbot.unload_adapter()
            >>> # Base Kosaul 모델로 복귀
        """
        if not isinstance(self.llm_client, OllamaClient):
            logger.warning("Current LLM client does not support adapters")
            return

        try:
            # Ollama Client에서 Adapter 언로드
            self.llm_client.unload_adapter()

            # System Prompt 복원
            self.system_prompt = self.base_system_prompt

            # 상태 초기화
            old_adapter = self.current_adapter
            self.current_adapter = None

            logger.info(f"Adapter unloaded: {old_adapter} → Base Model")

        except Exception as e:
            logger.error(f"Failed to unload adapter: {e}")

    def list_available_adapters(self) -> List[str]:
        """
        사용 가능한 Adapter 목록 조회

        Returns:
            List[str]: Adapter 이름 목록

        Example:
            >>> chatbot.list_available_adapters()
            ['traffic', 'criminal', 'drug']
        """
        if not isinstance(self.llm_client, OllamaClient):
            return []

        return self.llm_client.list_adapters()

    def get_adapter_info(self) -> Dict[str, Any]:
        """
        현재 Adapter 정보 반환

        Returns:
            {
                'current_adapter': str | None,
                'is_adapter_loaded': bool,
                'available_adapters': List[str],
                'metrics': Dict (Adapter별)
            }
        """
        return {
            'current_adapter': self.current_adapter,
            'is_adapter_loaded': self.current_adapter is not None,
            'available_adapters': self.list_available_adapters(),
            'metrics': self.adapter_metrics.get(self.current_adapter, {}) if self.current_adapter else {}
        }

    def chat(
        self,
        query: str,
        top_k: int = 5,
        include_critique_log: bool = False
    ) -> Dict[str, Any]:
        """
        Constitutional AI + Adapter 답변 생성

        오버라이드: 메트릭 수집 추가

        Args:
            query: 사용자 질문
            top_k: 검색할 문서 수
            include_critique_log: 검증 로그 포함 여부

        Returns:
            {
                'answer': 최종 답변,
                'sources': 검색된 문서,
                'query': 원본 질문,
                'critique': 검증 결과 (선택적),
                'revised': 수정 여부,
                'adapter': 현재 Adapter 이름
            }
        """
        import time

        start_time = time.time()

        # 부모 클래스의 chat 호출 (Constitutional AI)
        response = super().chat(query, top_k, include_critique_log)

        # Adapter 정보 추가
        response['adapter'] = self.current_adapter

        # 메트릭 수집 (Adapter 사용 중일 때만)
        if self.current_adapter:
            response_time = time.time() - start_time

            metrics = self.adapter_metrics[self.current_adapter]
            metrics['total_queries'] += 1

            # 평균 응답 시간 업데이트
            total = metrics['total_queries']
            metrics['avg_response_time'] = (
                (metrics['avg_response_time'] * (total - 1) + response_time) / total
            )

            # 수정 횟수
            if response.get('revised', False):
                metrics['revision_count'] += 1

        return response


# 사용 예시
if __name__ == "__main__":
    """
    AdapterChatbot 사용 예시

    1. 기본 사용 (Base Model)
    2. Adapter 로드 (교통사고 전문)
    3. 답변 생성
    4. Adapter 언로드
    """

    print("=== AdapterChatbot 사용 예시 ===\n")

    print("1. 초기화:")
    print("   chatbot = AdapterChatbot(retriever, llm_client)")
    print("")

    print("2. Adapter 로드 (교통사고 전문):")
    print("   chatbot.load_adapter('traffic')")
    print("")

    print("3. 질문:")
    print("   response = chatbot.chat('음주운전 3회, 무면허, 중상해 사건의 양형은?')")
    print("")

    print("4. Adapter 정보:")
    print("   info = chatbot.get_adapter_info()")
    print("   {")
    print("     'current_adapter': 'traffic',")
    print("     'is_adapter_loaded': True,")
    print("     'available_adapters': ['traffic', 'criminal', 'drug'],")
    print("     'metrics': {'total_queries': 15, 'avg_response_time': 2.3}")
    print("   }")
    print("")

    print("5. Adapter 언로드:")
    print("   chatbot.unload_adapter()  # Base Model로 복귀")
    print("")

    print("주요 특징:")
    print("- Constitutional AI 원칙 유지")
    print("- Adapter별 전문 System Prompt")
    print("- 실시간 Adapter 전환 (재시작 불필요)")
    print("- 성능 메트릭 자동 수집")
