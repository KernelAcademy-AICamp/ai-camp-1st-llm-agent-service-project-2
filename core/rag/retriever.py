"""
Retrieval strategies for RAG pipeline.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
import numpy as np


class BaseRetriever(ABC):
    """Abstract base class for retrievers."""

    @abstractmethod
    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Query string
            k: Number of documents to retrieve

        Returns:
            List of retrieved documents with metadata
        """
        pass


class SimilarityRetriever(BaseRetriever):
    """Basic similarity-based retriever."""

    def __init__(self, vector_store, embedder):
        """
        Initialize similarity retriever.

        Args:
            vector_store: Vector store instance
            embedder: Embedder instance for query encoding
        """
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve documents using cosine similarity."""
        # Encode query
        query_embedding = self.embedder.embed(query)

        # Search in vector store
        results = self.vector_store.search(query_embedding, k=k)

        # Format results
        documents = []
        for text, score, metadata in results:
            documents.append({
                'content': text,
                'score': score,
                'metadata': metadata
            })

        return documents


class MMRRetriever(BaseRetriever):
    """Maximal Marginal Relevance retriever for diversity."""

    def __init__(self, vector_store, embedder, lambda_mult: float = 0.5):
        """
        Initialize MMR retriever.

        Args:
            vector_store: Vector store instance
            embedder: Embedder instance
            lambda_mult: Balance between relevance and diversity (0-1)
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.lambda_mult = lambda_mult

    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve documents using MMR algorithm."""
        # Get initial candidates (2x k for better diversity)
        query_embedding = self.embedder.embed(query)
        candidates = self.vector_store.search(query_embedding, k=k*2)

        if not candidates:
            return []

        # MMR selection
        selected = []
        selected_embeddings = []
        candidate_embeddings = {}

        # Get embeddings for all candidates
        for text, score, metadata in candidates:
            embedding = self.embedder.embed(text)
            candidate_embeddings[text] = (embedding, score, metadata)

        # Iteratively select documents
        while len(selected) < k and candidate_embeddings:
            best_score = -float('inf')
            best_doc = None

            for text, (embedding, rel_score, metadata) in candidate_embeddings.items():
                # Calculate relevance to query
                relevance = 1 / (1 + rel_score)  # Convert distance to similarity

                # Calculate max similarity to already selected docs
                max_sim = 0
                for sel_embedding in selected_embeddings:
                    sim = np.dot(embedding.squeeze(), sel_embedding.squeeze()) / (
                        np.linalg.norm(embedding) * np.linalg.norm(sel_embedding)
                    )
                    max_sim = max(max_sim, sim)

                # MMR score
                mmr_score = self.lambda_mult * relevance - (1 - self.lambda_mult) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_doc = text

            if best_doc:
                embedding, score, metadata = candidate_embeddings[best_doc]
                selected.append({
                    'content': best_doc,
                    'score': score,
                    'metadata': metadata
                })
                selected_embeddings.append(embedding)
                del candidate_embeddings[best_doc]

        return selected


class HybridRetriever(BaseRetriever):
    """Hybrid retriever combining vector search with keyword search."""

    def __init__(self, vector_store, embedder, bm25_weight: float = 0.3):
        """
        Initialize hybrid retriever.

        Args:
            vector_store: Vector store instance
            embedder: Embedder instance
            bm25_weight: Weight for BM25 scores (0-1)
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.bm25_weight = bm25_weight
        self.documents = []

        try:
            from rank_bm25 import BM25Okapi
            self.BM25 = BM25Okapi
            self.bm25_index = None
        except ImportError:
            print("Warning: rank-bm25 not installed. Falling back to vector-only search.")
            self.BM25 = None

    def add_documents(self, documents: List[str]):
        """Add documents for BM25 indexing."""
        self.documents = documents
        if self.BM25:
            # Tokenize documents for BM25
            tokenized_docs = [doc.lower().split() for doc in documents]
            self.bm25_index = self.BM25(tokenized_docs)

    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve using hybrid approach."""
        # Vector search
        query_embedding = self.embedder.embed(query)
        vector_results = self.vector_store.search(query_embedding, k=k*2)

        if not self.BM25 or not self.bm25_index:
            # Fallback to vector-only
            return [
                {
                    'content': text,
                    'score': score,
                    'metadata': metadata
                }
                for text, score, metadata in vector_results[:k]
            ]

        # BM25 search
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25_index.get_scores(tokenized_query)

        # Combine scores
        combined_scores = {}

        # Add vector search scores
        for text, score, metadata in vector_results:
            # Normalize vector score (lower is better for L2 distance)
            normalized_score = 1 / (1 + score)
            combined_scores[text] = {
                'vector_score': normalized_score * (1 - self.bm25_weight),
                'bm25_score': 0,
                'metadata': metadata
            }

        # Add BM25 scores
        for i, doc in enumerate(self.documents):
            if doc in combined_scores:
                combined_scores[doc]['bm25_score'] = bm25_scores[i] * self.bm25_weight
            else:
                combined_scores[doc] = {
                    'vector_score': 0,
                    'bm25_score': bm25_scores[i] * self.bm25_weight,
                    'metadata': {}
                }

        # Calculate final scores and sort
        final_results = []
        for text, scores in combined_scores.items():
            total_score = scores['vector_score'] + scores['bm25_score']
            final_results.append((text, total_score, scores['metadata']))

        # Sort by total score (higher is better)
        final_results.sort(key=lambda x: x[1], reverse=True)

        # Format and return top k
        return [
            {
                'content': text,
                'score': score,
                'metadata': metadata
            }
            for text, score, metadata in final_results[:k]
        ]


def create_retriever(config: dict, vector_store=None, embedder=None) -> BaseRetriever:
    """
    Factory function to create retriever based on config.

    Args:
        config: Retriever configuration
        vector_store: Vector store instance
        embedder: Embedder instance

    Returns:
        BaseRetriever instance
    """
    method = config.get('method', 'similarity')

    if method == 'similarity':
        return SimilarityRetriever(vector_store, embedder)
    elif method == 'mmr':
        return MMRRetriever(
            vector_store,
            embedder,
            lambda_mult=config.get('lambda_mult', 0.5)
        )
    elif method == 'hybrid':
        return HybridRetriever(
            vector_store,
            embedder,
            bm25_weight=config.get('bm25_weight', 0.3)
        )
    else:
        raise ValueError(f"Unknown retrieval method: {method}")