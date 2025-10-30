"""
LLM models for generation.
"""

from .base import BaseLLM
from .openai_llm import OpenAILLM
from .gemini_llm import GeminiLLM

def get_llm(config: dict) -> BaseLLM:
    """
    Factory function to create LLM based on config.

    Args:
        config: LLM configuration

    Returns:
        BaseLLM instance
    """
    provider = config.get('provider', 'openai')

    if provider == 'openai':
        return OpenAILLM(
            model_name=config.get('model', 'gpt-3.5-turbo'),
            api_key=config.get('api_key'),
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens', 500),
            system_prompt=config.get('system_prompt')
        )
    elif provider == 'gemini':
        return GeminiLLM(
            model_name=config.get('model', 'gemini-pro'),
            api_key=config.get('api_key'),
            temperature=config.get('temperature', 0.7),
            max_tokens=config.get('max_tokens', 500),
            system_prompt=config.get('system_prompt')
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

__all__ = ['BaseLLM', 'OpenAILLM', 'GeminiLLM', 'get_llm']