"""
OpenAI embedding model implementation.
"""

import os
from typing import List, Union
import numpy as np
from .base import BaseEmbedder


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embedding model wrapper."""

    def __init__(self, model_name: str = "text-embedding-ada-002", api_key: str = None):
        """
        Initialize OpenAI embedder.

        Args:
            model_name: OpenAI embedding model name
            api_key: OpenAI API key (if None, uses environment variable)
        """
        super().__init__(model_name)

        # Handle API key
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")

        # Lazy import to avoid dependency issues
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")

        # Set embedding dimension based on model
        self.embedding_dim = 1536 if "ada" in model_name else None

    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Embed texts using OpenAI API.

        Args:
            texts: Single text or list of texts

        Returns:
            Numpy array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]

        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts
            )
            embeddings = [item.embedding for item in response.data]
            return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            raise RuntimeError(f"Error generating embeddings: {e}")

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed texts in batches.

        Args:
            texts: List of texts
            batch_size: Batch size (OpenAI supports up to 2048 texts per request)

        Returns:
            Numpy array of embeddings
        """
        all_embeddings = []

        # OpenAI supports large batches, adjust if needed
        batch_size = min(batch_size, 2048)

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.embed(batch)
            all_embeddings.append(embeddings)

        return np.vstack(all_embeddings) if all_embeddings else np.array([])