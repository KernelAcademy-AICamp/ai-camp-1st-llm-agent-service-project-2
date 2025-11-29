"""법률 문서 청킹 전략 모듈"""
from .chunker import (
    create_chunker,
    merge_small_chunks,  # ✅ 신규 추가
    ChunkingStrategy,
    FixedSizeChunking,
    RecursiveChunking,
    SlidingWindowChunking
)
from .legal_chunker import (
    LegalArticleChunking,
    PrecedentAutoChunking,
    QAPreserveChunking,
    InterpretationChunking
)

__all__ = [
    'create_chunker',
    'merge_small_chunks',  # ✅ 신규 추가
    'ChunkingStrategy',
    'FixedSizeChunking',
    'RecursiveChunking',
    'SlidingWindowChunking',
    'LegalArticleChunking',
    'PrecedentAutoChunking',
    'QAPreserveChunking',
    'InterpretationChunking',
]
