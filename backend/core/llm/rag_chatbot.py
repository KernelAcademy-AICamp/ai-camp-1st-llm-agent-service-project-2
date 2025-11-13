from typing import List, Dict, Any, Optional
from loguru import logger
from backend.core.retrieval.retriever import LegalDocumentRetriever
from backend.core.llm.llm_client import LLMClient


class RAGChatbot:
    """RAG 기반 법률 챗봇"""

    def __init__(
        self,
        retriever: LegalDocumentRetriever,
        llm_client: LLMClient,
        system_prompt: Optional[str] = None
    ):
        """
        Args:
            retriever: 문서 검색기
            llm_client: LLM 클라이언트
            system_prompt: 시스템 프롬프트
        """
        self.retriever = retriever
        self.llm_client = llm_client
        self.system_prompt = system_prompt or self._get_default_system_prompt()

        self.conversation_history: List[Dict[str, str]] = []

        logger.info("Initialized RAG Chatbot")

    def _get_default_system_prompt(self) -> str:
        """기본 시스템 프롬프트"""
        return """당신은 형사법 전문 AI 법률 상담사입니다.

주어진 법률 문서(판례, 법령, 해석례 등)를 참고하여 사용자의 질문에 정확하고 전문적으로 답변해주세요.

답변 시 다음 원칙을 따르세요:
1. 제공된 문서의 내용을 기반으로 답변하세요.
2. 관련 법령이나 판례를 인용할 때는 출처를 명시하세요.
3. 확실하지 않은 내용은 추측하지 말고, 모른다고 말하세요.
4. 법률 용어를 사용할 때는 쉽게 설명해주세요.
5. 답변은 한국어로 작성하세요.
6. 법률 자문이 아닌 정보 제공임을 유의하세요."""

    def chat(
        self,
        query: str,
        top_k: int = 5,
        include_context: bool = True
    ) -> Dict[str, Any]:
        """
        사용자 질문에 답변

        Args:
            query: 사용자 질문
            top_k: 검색할 문서 수
            include_context: 응답에 검색된 문서 포함 여부

        Returns:
            답변 및 검색 결과를 포함한 딕셔너리
        """
        logger.info(f"User query: {query}")

        # 1. Retrieve relevant documents
        retrieved_docs = self.retriever.retrieve(query, top_k=top_k)

        if not retrieved_docs:
            logger.warning("No documents retrieved")
            return {
                'answer': "죄송합니다. 관련 법률 정보를 찾을 수 없습니다.",
                'sources': [],
                'query': query
            }

        # 2. Format context
        context = self.retriever.format_context(retrieved_docs)

        # 3. Build prompt
        prompt = self._build_prompt(query, context)

        # 4. Generate answer
        answer = self.llm_client.generate(prompt)

        logger.info(f"Generated answer: {answer[:100]}...")

        # 5. Prepare response
        response = {
            'answer': answer,
            'query': query,
            'sources': retrieved_docs if include_context else []
        }

        # Update conversation history
        self.conversation_history.append({
            'role': 'user',
            'content': query
        })
        self.conversation_history.append({
            'role': 'assistant',
            'content': answer
        })

        return response

    def chat_with_history(
        self,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        대화 히스토리를 고려한 답변

        Args:
            query: 사용자 질문
            top_k: 검색할 문서 수

        Returns:
            답변 딕셔너리
        """
        # Retrieve documents
        retrieved_docs = self.retriever.retrieve(query, top_k=top_k)
        context = self.retriever.format_context(retrieved_docs)

        # Build messages with history
        messages = [
            {'role': 'system', 'content': self.system_prompt}
        ]

        # Add conversation history (최근 5턴만)
        messages.extend(self.conversation_history[-10:])

        # Add current query with context
        current_message = f"""관련 법률 문서:
{context}

사용자 질문: {query}"""

        messages.append({
            'role': 'user',
            'content': current_message
        })

        # Generate answer
        answer = self.llm_client.chat(messages)

        # Update history
        self.conversation_history.append({
            'role': 'user',
            'content': query
        })
        self.conversation_history.append({
            'role': 'assistant',
            'content': answer
        })

        return {
            'answer': answer,
            'query': query,
            'sources': retrieved_docs
        }

    def _build_prompt(self, query: str, context: str) -> str:
        """프롬프트 생성"""
        prompt = f"""{self.system_prompt}

관련 법률 문서:
{context}

사용자 질문: {query}

답변:"""

        return prompt

    def clear_history(self) -> None:
        """대화 히스토리 초기화"""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def get_history(self) -> List[Dict[str, str]]:
        """대화 히스토리 반환"""
        return self.conversation_history.copy()

    def ask_followup(self, query: str) -> Dict[str, Any]:
        """
        후속 질문 (히스토리 기반)

        Args:
            query: 후속 질문

        Returns:
            답변 딕셔너리
        """
        return self.chat_with_history(query)


class AdvancedRAGChatbot(RAGChatbot):
    """고급 RAG 챗봇 (재순위화, 필터링 등 추가 기능)"""

    def chat_with_reranking(
        self,
        query: str,
        top_k: int = 5,
        initial_k: int = 20
    ) -> Dict[str, Any]:
        """
        재순위화를 적용한 검색

        Args:
            query: 사용자 질문
            top_k: 최종 문서 수
            initial_k: 초기 검색 문서 수

        Returns:
            답변 딕셔너리
        """
        # 1. Retrieve more documents initially
        retrieved_docs = self.retriever.get_diverse_results(
            query,
            top_k=initial_k
        )

        # 2. Take top_k after diversity filtering
        retrieved_docs = retrieved_docs[:top_k]

        # 3. Format and generate
        context = self.retriever.format_context(retrieved_docs)
        prompt = self._build_prompt(query, context)
        answer = self.llm_client.generate(prompt)

        return {
            'answer': answer,
            'query': query,
            'sources': retrieved_docs
        }

    def chat_with_source_filter(
        self,
        query: str,
        source_types: List[str],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        특정 출처 타입으로 필터링된 검색

        Args:
            query: 사용자 질문
            source_types: 출처 타입 리스트 (예: ['statute', 'court_decision'])
            top_k: 검색할 문서 수

        Returns:
            답변 딕셔너리
        """
        # Retrieve from all sources first
        all_docs = self.retriever.retrieve(query, top_k=top_k * 3)

        # Filter by source type
        filtered_docs = [
            doc for doc in all_docs
            if doc.get('metadata', {}).get('source_type') in source_types
        ][:top_k]

        if not filtered_docs:
            return {
                'answer': f"죄송합니다. 지정된 출처({', '.join(source_types)})에서 관련 정보를 찾을 수 없습니다.",
                'query': query,
                'sources': []
            }

        # Generate answer
        context = self.retriever.format_context(filtered_docs)
        prompt = self._build_prompt(query, context)
        answer = self.llm_client.generate(prompt)

        return {
            'answer': answer,
            'query': query,
            'sources': filtered_docs
        }
