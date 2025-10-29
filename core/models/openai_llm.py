"""
OpenAI LLM implementation.
"""

import os
from typing import List, Optional
from .base import BaseLLM


class OpenAILLM(BaseLLM):
    """OpenAI GPT model wrapper."""

    def __init__(self,
                 model_name: str = "gpt-3.5-turbo",
                 api_key: str = None,
                 base_url: str = None,
                 temperature: float = 0.7,
                 max_tokens: int = 500):
        """
        Initialize OpenAI LLM.

        Args:
            model_name: OpenAI model name (or custom model alias)
            api_key: OpenAI API key (or custom API key)
            base_url: Optional custom base URL for OpenAI-compatible APIs
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        super().__init__(model_name, temperature, max_tokens)

        # Handle API key
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")

        # Handle custom base URL (for OpenAI-compatible APIs)
        self.base_url = base_url or os.getenv('LLM_BASE_URL')

        # Initialize client
        try:
            from openai import OpenAI
            if self.base_url:
                # Custom OpenAI-compatible API
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            else:
                # Standard OpenAI API
                self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text using OpenAI API.

        Args:
            prompt: Input prompt
            system_prompt: Optional system prompt

        Returns:
            Generated text
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Error generating response: {e}")

    def generate_with_context(self,
                            query: str,
                            context: List[str],
                            system_prompt: Optional[str] = None) -> str:
        """
        Generate response with RAG context.

        Args:
            query: User query
            context: Retrieved documents
            system_prompt: Optional system prompt

        Returns:
            Generated response
        """
        # Use default system prompt if not provided
        if system_prompt is None:
            system_prompt = """당신은 법률 문서 분석을 돕는 AI 어시스턴트입니다.
제공된 문서를 바탕으로 정확하고 도움이 되는 답변을 제공하세요.
문서에 없는 내용은 추측하지 말고, 확실한 정보만 제공하세요."""

        # Create RAG prompt
        rag_prompt = self.create_rag_prompt(query, context)

        # Generate response
        return self.generate(rag_prompt, system_prompt)