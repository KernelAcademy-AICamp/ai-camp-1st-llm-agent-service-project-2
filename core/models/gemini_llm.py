"""
Google Gemini LLM implementation.
"""

import os
from typing import List, Optional
from .base import BaseLLM


class GeminiLLM(BaseLLM):
    """Google Gemini model wrapper."""

    def __init__(self,
                 model_name: str = "gemini-pro",
                 api_key: str = None,
                 temperature: float = 0.7,
                 max_tokens: int = 500):
        """
        Initialize Gemini LLM.

        Args:
            model_name: Gemini model name
            api_key: Google API key
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        super().__init__(model_name, temperature, max_tokens)

        # Handle API key
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key not provided. Set GOOGLE_API_KEY environment variable.")

        # Initialize client
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name)
        except ImportError:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text using Gemini API.

        Args:
            prompt: Input prompt
            system_prompt: Optional system prompt

        Returns:
            Generated text
        """
        # Combine system prompt and user prompt if needed
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        try:
            # Configure generation parameters
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }

            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            return response.text
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