"""
HuggingFace embedding model implementation.
"""

from typing import List, Union
import numpy as np
from .base import BaseEmbedder


class HuggingFaceEmbedder(BaseEmbedder):
    """HuggingFace transformer-based embedding model wrapper."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-large", device: str = "cpu"):
        """
        Initialize HuggingFace embedder.

        Args:
            model_name: HuggingFace model name
            device: Device to run model on ('cpu', 'cuda', 'mps')
        """
        super().__init__(model_name)
        self.device = device

        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model.to(device)
        except ImportError:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")

        # Get embedding dimension
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Embed texts using HuggingFace model.

        Args:
            texts: Single text or list of texts

        Returns:
            Numpy array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]

        # Add prefix for E5 models if needed
        if "e5" in self.model_name.lower():
            texts = [f"query: {text}" for text in texts]

        # BGE-M3 특별 처리
        if "bge-m3" in self.model_name.lower():
            # BGE-M3는 최대 8192 토큰 지원
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
                # max_length 파라미터는 모델이 지원하지 않을 수 있음
            )
        else:
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,  # L2 normalization for cosine similarity
                show_progress_bar=False
            )

        return embeddings.astype(np.float32)

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed texts in batches.

        Args:
            texts: List of texts
            batch_size: Batch size for processing

        Returns:
            Numpy array of embeddings
        """
        # Add prefix for E5 models if needed
        if "e5" in self.model_name.lower():
            texts = [f"query: {text}" for text in texts]

        # BGE-M3 특별 처리
        if "bge-m3" in self.model_name.lower():
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 100  # Show progress for large batches
                # max_length 파라미터는 모델이 지원하지 않을 수 있음
            )
        else:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 100  # Show progress for large batches
            )

        return embeddings.astype(np.float32)