"""
RAG Core Embeddings Module
임베딩 모델 및 VectorDB 인터페이스 (DB 비의존)
"""

from .embedder import KoreanLegalEmbedder, KOREAN_EMBEDDING_MODELS, get_recommended_model
from .vectordb import (
    VectorDB,
    ChromaVectorDB,
    FAISSVectorDB,
    create_vector_db
)

# Remote embedder (외부 임베딩 API용)
try:
    from .remote_embedder import RemoteEmbedder
except ImportError:
    RemoteEmbedder = None

# Qdrant VectorDB
try:
    from .qdrant_vectordb import QdrantVectorDB
except ImportError:
    QdrantVectorDB = None

__all__ = [
    'KoreanLegalEmbedder',
    'RemoteEmbedder',
    'VectorDB',
    'ChromaVectorDB',
    'FAISSVectorDB',
    'QdrantVectorDB',
    'create_vector_db',
    'KOREAN_EMBEDDING_MODELS',
    'get_recommended_model',
]
