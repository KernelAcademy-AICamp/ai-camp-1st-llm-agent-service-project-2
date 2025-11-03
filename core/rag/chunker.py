"""
Document chunking strategies for RAG pipeline.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import re


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into chunks.

        Args:
            text: Input text to chunk

        Returns:
            List of chunk dictionaries with 'content' and 'metadata'
        """
        pass


class FixedSizeChunking(ChunkingStrategy):
    """Fixed-size chunking with optional overlap."""

    def __init__(self, chunk_size: int = 512, overlap: int = 50, use_token_count: bool = False):
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

    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """Split text into fixed-size chunks."""
        chunks = []

        if self.use_token_count:
            # Token-based chunking
            tokens = self.tokenizer.encode(text)
            step_size = self.chunk_size - self.overlap

            for i in range(0, len(tokens), step_size):
                chunk_tokens = tokens[i:i + self.chunk_size]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
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
            step_size = self.chunk_size - self.overlap

            for i in range(0, len(text), step_size):
                chunk_text = text[i:i + self.chunk_size]
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        'chunk_id': len(chunks),
                        'start_char': i,
                        'end_char': min(i + self.chunk_size, len(text)),
                        'chunking_strategy': 'fixed_char'
                    }
                })

                if i + self.chunk_size >= len(text):
                    break

        return chunks


class SemanticChunking(ChunkingStrategy):
    """Semantic chunking based on sentence embeddings similarity."""

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2",
                 similarity_threshold: float = 0.5,
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 800):
        """
        Initialize semantic chunker.

        Args:
            embedding_model: Sentence embedding model name
            similarity_threshold: Similarity threshold for splitting chunks
            min_chunk_size: Minimum chunk size in characters
            max_chunk_size: Maximum chunk size in characters
        """
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            self.model = SentenceTransformer(embedding_model)
            self.np = np
        except ImportError:
            raise ImportError("sentence-transformers required for semantic chunking")

    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """Split text into semantic chunks based on sentence similarity."""
        # Split into sentences
        sentences = self._split_into_sentences(text)
        if not sentences:
            return []

        # Get embeddings for all sentences
        embeddings = self.model.encode(sentences)

        # Group sentences into chunks based on similarity
        chunks = []
        current_chunk = [sentences[0]]
        current_length = len(sentences[0])

        for i in range(1, len(sentences)):
            # Calculate similarity with previous sentence
            similarity = self.np.dot(embeddings[i-1], embeddings[i]) / (
                self.np.linalg.norm(embeddings[i-1]) * self.np.linalg.norm(embeddings[i])
            )

            # Check if we should start a new chunk
            if (similarity < self.similarity_threshold and current_length >= self.min_chunk_size) \
               or current_length + len(sentences[i]) > self.max_chunk_size:
                # Save current chunk
                chunks.append({
                    'content': ' '.join(current_chunk),
                    'metadata': {
                        'chunk_id': len(chunks),
                        'num_sentences': len(current_chunk),
                        'chunking_strategy': 'semantic'
                    }
                })
                current_chunk = [sentences[i]]
                current_length = len(sentences[i])
            else:
                current_chunk.append(sentences[i])
                current_length += len(sentences[i])

        # Add the last chunk
        if current_chunk:
            chunks.append({
                'content': ' '.join(current_chunk),
                'metadata': {
                    'chunk_id': len(chunks),
                    'num_sentences': len(current_chunk),
                    'chunking_strategy': 'semantic'
                }
            })

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting (can be improved with spaCy or NLTK)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]


class RecursiveChunking(ChunkingStrategy):
    """Recursive chunking with hierarchical separators."""

    def __init__(self, separators: List[str] = None,
                 chunk_size: int = 512,
                 overlap: int = 50):
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

    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """Split text recursively using hierarchical separators."""
        chunks = []
        self._recursive_split(text, chunks)
        return chunks

    def _recursive_split(self, text: str, chunks: List[Dict[str, Any]], depth: int = 0):
        """Recursively split text."""
        # If text is small enough, add it as a chunk
        if len(text) <= self.chunk_size:
            if text.strip():
                chunks.append({
                    'content': text.strip(),
                    'metadata': {
                        'chunk_id': len(chunks),
                        'depth': depth,
                        'chunking_strategy': 'recursive'
                    }
                })
            return

        # Try to split with separators at current depth
        if depth < len(self.separators):
            separator = self.separators[depth]
            parts = text.split(separator)

            current_chunk = []
            current_length = 0

            for part in parts:
                part_length = len(part)

                if current_length + part_length > self.chunk_size and current_chunk:
                    # Save current chunk and start new one
                    combined_text = separator.join(current_chunk)
                    if len(combined_text) > self.chunk_size:
                        # Still too large, recurse with next separator
                        self._recursive_split(combined_text, chunks, depth + 1)
                    else:
                        chunks.append({
                            'content': combined_text,
                            'metadata': {
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

            # Handle remaining content
            if current_chunk:
                combined_text = separator.join(current_chunk)
                if len(combined_text) > self.chunk_size and depth < len(self.separators) - 1:
                    self._recursive_split(combined_text, chunks, depth + 1)
                elif combined_text.strip():
                    chunks.append({
                        'content': combined_text,
                        'metadata': {
                            'chunk_id': len(chunks),
                            'depth': depth,
                            'chunking_strategy': 'recursive'
                        }
                    })
        else:
            # No more separators, use fixed-size chunking as fallback
            fixed_chunker = FixedSizeChunking(self.chunk_size, self.overlap)
            fallback_chunks = fixed_chunker.chunk(text)
            for chunk in fallback_chunks:
                chunk['metadata']['depth'] = depth
                chunk['metadata']['chunking_strategy'] = 'recursive_fallback'
            chunks.extend(fallback_chunks)


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

    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """Split text using sliding window approach."""
        chunks = []
        text_length = len(text)

        for i in range(0, text_length, self.step_size):
            end_pos = min(i + self.window_size, text_length)
            chunk_text = text[i:end_pos]

            if chunk_text.strip():
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        'chunk_id': len(chunks),
                        'start_pos': i,
                        'end_pos': end_pos,
                        'overlap_ratio': 1 - (self.step_size / self.window_size),
                        'chunking_strategy': 'sliding_window'
                    }
                })

            # Stop if we've reached the end
            if end_pos >= text_length:
                break

        return chunks


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
            overlap=config.get('overlap', 50),
            use_token_count=config.get('use_token_count', False)
        )
    elif strategy == 'semantic':
        return SemanticChunking(
            embedding_model=config.get('embedding_model', 'all-MiniLM-L6-v2'),
            similarity_threshold=config.get('similarity_threshold', 0.5),
            min_chunk_size=config.get('min_chunk_size', 100),
            max_chunk_size=config.get('max_chunk_size', 800)
        )
    elif strategy == 'recursive':
        return RecursiveChunking(
            separators=config.get('separators', ["\n\n", "\n", ". ", " "]),
            chunk_size=config.get('chunk_size', 512),
            overlap=config.get('overlap', 50)
        )
    elif strategy == 'sliding_window':
        return SlidingWindowChunking(
            window_size=config.get('window_size', 512),
            step_size=config.get('step_size', 256)
        )
    # ========== [NEW] Legal Document Chunking Strategies ==========
    elif strategy == 'legal_article':
        from .legal_chunker import LegalArticleChunking
        return LegalArticleChunking(
            chunk_size=config.get('chunk_size', 512),
            max_chunk_size=config.get('max_chunk_size', 1000),
            include_header=config.get('include_header', True)
        )
    elif strategy == 'precedent_section':
        from .legal_chunker import PrecedentSectionChunking
        return PrecedentSectionChunking(
            chunk_size=config.get('chunk_size', 600),
            overlap=config.get('overlap', 50),
            include_header=config.get('include_header', True)
        )
    elif strategy == 'qa_context':
        from .legal_chunker import QAContextEnrichmentChunking
        return QAContextEnrichmentChunking(
            db_client=config.get('db_client'),
            include_context=config.get('include_context', True),
            context_length=config.get('context_length', 300)
        )
    # ===============================================================
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")