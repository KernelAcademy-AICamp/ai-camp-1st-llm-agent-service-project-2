"""
Domain models for legal document service.
공통 도메인 모델 정의 (Django, FastAPI에서 공유)
"""

from .models import (
    # Legal entities
    Law,
    LawArticle,
    Precedent,
    PrecedentSection,
    TrafficCase,

    # RAG entities
    Document,
    Chunk,
    EvidenceChunk,

    # API DTOs
    ChatRequest,
    ChatResponse,
    SearchRequest,
    SearchResponse,
    RiskSummary,
)

__all__ = [
    # Legal entities
    'Law',
    'LawArticle',
    'Precedent',
    'PrecedentSection',
    'TrafficCase',

    # RAG entities
    'Document',
    'Chunk',
    'EvidenceChunk',

    # API DTOs
    'ChatRequest',
    'ChatResponse',
    'SearchRequest',
    'SearchResponse',
    'RiskSummary',
]
