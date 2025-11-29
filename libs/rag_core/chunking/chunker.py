"""
Document chunking strategies for RAG pipeline.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import re


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Split text into chunks.

        Args:
            text: Input text to chunk
            metadata: Optional metadata for the document

        Returns:
            List of chunk dictionaries with 'content' and 'metadata'
        """
        pass


class FixedSizeChunking(ChunkingStrategy):
    """Fixed-size chunking with optional overlap."""

    def __init__(self, chunk_size: int = 512, overlap: int = 100, use_token_count: bool = False):  # ✅ overlap 50 → 100
        """
        Initialize fixed-size chunker.

        Args:
            chunk_size: Size of each chunk (in tokens or characters)
            overlap: Number of tokens/characters to overlap between chunks
            use_token_count: If True, use token count; if False, use character count
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.use_token_count = use_token_count

        if use_token_count:
            try:
                import tiktoken
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                print("tiktoken not installed. Using character count instead.")
                self.use_token_count = False

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into fixed-size chunks."""
        if metadata is None:
            metadata = {}

        chunks = []

        if self.use_token_count:
            # Token-based chunking
            tokens = self.tokenizer.encode(text)
            step_size = max(1, self.chunk_size - self.overlap)

            for i in range(0, len(tokens), step_size):
                chunk_tokens = tokens[i:i + self.chunk_size]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        **metadata,
                        'chunk_id': len(chunks),
                        'start_token': i,
                        'end_token': min(i + self.chunk_size, len(tokens)),
                        'chunking_strategy': 'fixed_token'
                    }
                })

                if i + self.chunk_size >= len(tokens):
                    break
        else:
            # Character-based chunking
            step_size = max(1, self.chunk_size - self.overlap)

            for i in range(0, len(text), step_size):
                chunk_text = text[i:i + self.chunk_size]
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        **metadata,
                        'chunk_id': len(chunks),
                        'start_char': i,
                        'end_char': min(i + self.chunk_size, len(text)),
                        'chunking_strategy': 'fixed_char'
                    }
                })

                if i + self.chunk_size >= len(text):
                    break

        return chunks


class SlidingWindowChunking(ChunkingStrategy):
    """Sliding window chunking with configurable step size."""

    def __init__(self, window_size: int = 512, step_size: int = 256):
        """
        Initialize sliding window chunker.

        Args:
            window_size: Size of the sliding window
            step_size: Step size for sliding (smaller = more overlap)
        """
        self.window_size = window_size
        self.step_size = step_size

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text using sliding window approach."""
        if metadata is None:
            metadata = {}

        chunks = []
        text_length = len(text)

        for i in range(0, text_length, self.step_size):
            end_pos = min(i + self.window_size, text_length)
            chunk_text = text[i:end_pos]

            if chunk_text.strip():
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        **metadata,
                        'chunk_id': len(chunks),
                        'start_pos': i,
                        'end_pos': end_pos,
                        'overlap_ratio': 1 - (self.step_size / self.window_size),
                        'chunking_strategy': 'sliding_window'
                    }
                })

            if end_pos >= text_length:
                break

        return chunks


class RecursiveChunking(ChunkingStrategy):
    """Recursive chunking with hierarchical separators."""

    def __init__(self, separators: List[str] = None,
                 chunk_size: int = 512,
                 overlap: int = 100):  # ✅ overlap 50 → 100
        """
        Initialize recursive chunker.

        Args:
            separators: List of separators in order of preference
            chunk_size: Target chunk size
            overlap: Overlap between chunks
        """
        self.separators = separators or ["\n\n", "\n", ". ", " "]
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text recursively using hierarchical separators."""
        if metadata is None:
            metadata = {}

        chunks = []
        self._recursive_split(text, chunks, metadata, depth=0)
        return chunks

    def _recursive_split(self, text: str, chunks: List[Dict[str, Any]], metadata: Dict[str, Any], depth: int = 0):
        """Recursively split text."""
        if len(text) <= self.chunk_size:
            if text.strip():
                chunks.append({
                    'content': text.strip(),
                    'metadata': {
                        **metadata,
                        'chunk_id': len(chunks),
                        'depth': depth,
                        'chunking_strategy': 'recursive'
                    }
                })
            return

        if depth < len(self.separators):
            separator = self.separators[depth]
            parts = text.split(separator)

            current_chunk = []
            current_length = 0

            for part in parts:
                part_length = len(part)

                if current_length + part_length > self.chunk_size and current_chunk:
                    combined_text = separator.join(current_chunk)
                    if len(combined_text) > self.chunk_size:
                        self._recursive_split(combined_text, chunks, metadata, depth + 1)
                    else:
                        chunks.append({
                            'content': combined_text,
                            'metadata': {
                                **metadata,
                                'chunk_id': len(chunks),
                                'depth': depth,
                                'chunking_strategy': 'recursive'
                            }
                        })
                    current_chunk = [part]
                    current_length = part_length
                else:
                    current_chunk.append(part)
                    current_length += part_length + len(separator)

            if current_chunk:
                combined_text = separator.join(current_chunk)
                if len(combined_text) > self.chunk_size and depth < len(self.separators) - 1:
                    self._recursive_split(combined_text, chunks, metadata, depth + 1)
                elif combined_text.strip():
                    chunks.append({
                        'content': combined_text,
                        'metadata': {
                            **metadata,
                            'chunk_id': len(chunks),
                            'depth': depth,
                            'chunking_strategy': 'recursive'
                        }
                    })
        else:
            fixed_chunker = FixedSizeChunking(self.chunk_size, self.overlap)
            fallback_chunks = fixed_chunker.chunk(text, metadata)
            for chunk in fallback_chunks:
                chunk['metadata']['depth'] = depth
                chunk['metadata']['chunking_strategy'] = 'recursive_fallback'
            chunks.extend(fallback_chunks)


def merge_small_chunks(chunks: List[Dict[str, Any]],
                      min_size: int = 100,
                      max_merged_size: int = 600) -> List[Dict[str, Any]]:
    """
    너무 작은 청크를 인접 청크와 합치는 후처리 함수

    Args:
        chunks: 청크 리스트
        min_size: 이 크기 미만의 청크는 합침 대상
        max_merged_size: 합쳐진 청크의 최대 크기

    Returns:
        합쳐진 청크 리스트
    """
    if not chunks:
        return chunks

    merged = []
    current_chunk = None

    for chunk in chunks:
        content = chunk.get('content', '')

        if current_chunk is None:
            current_chunk = chunk.copy()
            continue

        current_content = current_chunk.get('content', '')

        # 현재 청크가 너무 작으면 합침
        if len(current_content) < min_size:
            combined_length = len(current_content) + len(content)

            if combined_length <= max_merged_size:
                # 합치기
                current_chunk['content'] = current_content + '\n' + content
                current_chunk['metadata']['merged'] = True
                continue

        # 다음 청크가 너무 작으면 현재 청크에 합침
        if len(content) < min_size:
            combined_length = len(current_content) + len(content)

            if combined_length <= max_merged_size:
                current_chunk['content'] = current_content + '\n' + content
                current_chunk['metadata']['merged'] = True
                continue

        # 합치지 않음 - 현재 청크 저장하고 다음으로 이동
        merged.append(current_chunk)
        current_chunk = chunk.copy()

    # 마지막 청크 추가
    if current_chunk is not None:
        merged.append(current_chunk)

    # chunk_id 재정렬
    for idx, chunk in enumerate(merged):
        chunk['metadata']['chunk_id'] = idx

    return merged


def create_chunker(config: dict) -> ChunkingStrategy:
    """
    Factory function to create chunker based on config.

    Args:
        config: Chunking configuration

    Returns:
        ChunkingStrategy instance
    """
    strategy = config.get('strategy', 'fixed')

    if strategy == 'fixed':
        return FixedSizeChunking(
            chunk_size=config.get('chunk_size', 512),
            overlap=config.get('overlap', 100),  # ✅ 50 → 100
            use_token_count=config.get('use_token_count', False)
        )
    elif strategy == 'recursive':
        return RecursiveChunking(
            separators=config.get('separators', ["\n\n", "\n", ". ", " "]),
            chunk_size=config.get('chunk_size', 512),
            overlap=config.get('overlap', 100)  # ✅ 50 → 100
        )
    elif strategy == 'sliding_window':
        return SlidingWindowChunking(
            window_size=config.get('window_size', 512),
            step_size=config.get('step_size', 412)  # ✅ 256 → 412 (overlap 100)
        )
    # Legal Document Chunking Strategies
    elif strategy == 'legal_article':
        from .legal_chunker import LegalArticleChunking
        return LegalArticleChunking(
            chunk_size=config.get('chunk_size', 512),
            max_chunk_size=config.get('max_chunk_size', 800),  # ✅ 1000 → 800
            include_header=config.get('include_header', True)
        )
    elif strategy == 'precedent_auto':
        from .legal_chunker import PrecedentAutoChunking
        return PrecedentAutoChunking(
            chunk_size=config.get('chunk_size', 600),
            overlap=config.get('overlap', 100),  # ✅ 50 → 100
            auto_detect_sections=config.get('auto_detect_sections', True)
        )
    elif strategy == 'qa_preserve':
        from .legal_chunker import QAPreserveChunking
        return QAPreserveChunking(
            max_length=config.get('max_length', 1000),  # ✅ 2000 → 1000
            preserve_whole=config.get('preserve_whole', True),
            hard_max_size=config.get('hard_max_size', 1500),  # ⭐ 절대 최대 크기
            overlap=config.get('overlap', 100)  # ⭐ 분할 시 오버랩
        )
    # ✅ 신규 추가: interpretation 전략
    elif strategy == 'interpretation':
        from .legal_chunker import InterpretationChunking
        return InterpretationChunking(
            max_length=config.get('max_length', 1000),
            preserve_qa_structure=config.get('preserve_qa_structure', True),
            fallback_strategy=config.get('fallback_strategy', 'sliding_window')
        )
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")
