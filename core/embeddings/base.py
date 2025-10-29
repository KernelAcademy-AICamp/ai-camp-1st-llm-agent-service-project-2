"""
Base class for all embedding models.
"""

from abc import ABC, abstractmethod
from typing import List, Union
import numpy as np


class BaseEmbedder(ABC):
    """Abstract base class for embedding models."""

    def __init__(self, model_name: str, **kwargs):
        """
        Initialize embedder.

        Args:
            model_name: Name of the embedding model
            **kwargs: Additional model-specific parameters
        """
        self.model_name = model_name
        self.embedding_dim = None

    @abstractmethod
    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Embed texts into vectors.

        Args:
            texts: Single text or list of texts to embed

        Returns:
            Numpy array of embeddings (n_texts, embedding_dim)
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed texts in batches for efficiency.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            Numpy array of embeddings
        """
        pass

    def get_embedding_dim(self) -> int:
        """Get the dimensionality of embeddings."""
        if self.embedding_dim is None:
            # Get dimension by embedding a sample text
            sample_embedding = self.embed("sample text")
            self.embedding_dim = sample_embedding.shape[-1]
        return self.embedding_dim