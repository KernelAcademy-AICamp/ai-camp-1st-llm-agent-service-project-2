"""
Base class for language models.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLM(ABC):
    """Abstract base class for language models."""

    def __init__(self, model_name: str, temperature: float = 0.7, max_tokens: int = 500):
        """
        Initialize LLM.

        Args:
            model_name: Name of the model
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text based on prompt.

        Args:
            prompt: Input prompt
            system_prompt: Optional system prompt

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def generate_with_context(self,
                            query: str,
                            context: List[str],
                            system_prompt: Optional[str] = None) -> str:
        """
        Generate text with retrieved context.

        Args:
            query: User query
            context: List of retrieved documents
            system_prompt: Optional system prompt

        Returns:
            Generated response
        """
        pass

    def create_rag_prompt(self, query: str, context: List[str]) -> str:
        """
        Create a RAG prompt from query and context.

        Args:
            query: User query
            context: Retrieved documents

        Returns:
            Formatted prompt
        """
        context_str = "\n\n".join([f"[Document {i+1}]\n{doc}" for i, doc in enumerate(context)])

        prompt = f"""다음 문서들을 참고하여 질문에 답변해주세요. 문서에 없는 내용은 추측하지 말고, 정확한 정보만 제공하세요.

### 참고 문서:
{context_str}

### 질문:
{query}

### 답변:"""

        return prompt