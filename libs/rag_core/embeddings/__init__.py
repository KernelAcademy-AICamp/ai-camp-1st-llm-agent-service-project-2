"""
RAG Core Embeddings Module
임베딩 모델 및 VectorDB 인터페이스 (DB 비의존)
"""

from .embedder import KoreanLegalEmbedder
from .vectordb import (
    VectorDB,
    ChromaVectorDB,
    FAISSVectorDB,
    create_vector_db
)

__all__ = [
    'KoreanLegalEmbedder',
    'VectorDB',
    'ChromaVectorDB',
    'FAISSVectorDB',
    'create_vector_db'
]
