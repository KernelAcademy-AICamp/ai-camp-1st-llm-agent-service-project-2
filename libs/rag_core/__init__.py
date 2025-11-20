"""
RAG Core Library
공통 RAG 로직: 임베딩, LLM, 검색 (DB 비의존)

이 라이브러리는 apps/backend, apps/ai-service, apps/data-pipeline에서
공통으로 사용하는 RAG 핵심 로직을 포함합니다.

Note:
    - feedback_filter.py는 DB 의존적이므로 apps/backend/core/retrieval/에 유지됨
    - 피드백 필터링은 apps.backend.core.retrieval.feedback_filter에서 import

Usage:
    from libs.rag_core import (
        KoreanLegalEmbedder,
        ChromaVectorDB,
        create_llm_client,
        HybridRetriever
    )
"""

# Embeddings
from .embeddings import (
    KoreanLegalEmbedder,
    VectorDB,
    ChromaVectorDB,
    FAISSVectorDB,
    create_vector_db
)

# LLM
from .llm import (
    LLMClient,
    OpenAIClient,
    OllamaClient,
    AnthropicClient,
    create_llm_client,
    RAGChatbot,
    AdvancedRAGChatbot,
    ConstitutionalLawChatbot,
    AdapterChatbot,
    ConstitutionalPrinciples
)

# Retrieval
from .retrieval import (
    LegalDocumentRetriever,
    BM25Index,
    HybridRetriever,
    filter_results
)

__version__ = '1.0.0'

__all__ = [
    # Embeddings
    'KoreanLegalEmbedder',
    'VectorDB',
    'ChromaVectorDB',
    'FAISSVectorDB',
    'create_vector_db',

    # LLM
    'LLMClient',
    'OpenAIClient',
    'OllamaClient',
    'AnthropicClient',
    'create_llm_client',
    'RAGChatbot',
    'AdvancedRAGChatbot',
    'ConstitutionalLawChatbot',
    'AdapterChatbot',
    'ConstitutionalPrinciples',

    # Retrieval
    'LegalDocumentRetriever',
    'BM25Index',
    'HybridRetriever',
    'filter_results'
]
