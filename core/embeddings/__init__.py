"""
Embedding modules for text vectorization.
"""

from .base import BaseEmbedder
from .openai_embedder import OpenAIEmbedder
from .huggingface_embedder import HuggingFaceEmbedder

def get_embedder(config: dict) -> BaseEmbedder:
    """
    Factory function to create embedder based on config.

    Args:
        config: Embedding configuration

    Returns:
        BaseEmbedder instance
    """
    embedder_type = config.get('type', 'openai')

    if embedder_type == 'openai':
        return OpenAIEmbedder(
            model_name=config.get('model', 'text-embedding-ada-002'),
            api_key=config.get('api_key')
        )
    elif embedder_type == 'huggingface':
        return HuggingFaceEmbedder(
            model_name=config.get('model', 'intfloat/multilingual-e5-large'),
            device=config.get('device', 'cpu')
        )
    else:
        raise ValueError(f"Unknown embedder type: {embedder_type}")

__all__ = ['BaseEmbedder', 'OpenAIEmbedder', 'HuggingFaceEmbedder', 'get_embedder']