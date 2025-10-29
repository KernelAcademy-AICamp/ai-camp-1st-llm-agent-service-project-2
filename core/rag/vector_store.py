"""
Vector store implementations for RAG pipeline.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import os
import json


class BaseVectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add(self, texts: List[str], embeddings: np.ndarray, metadata: List[Dict[str, Any]] = None):
        """
        Add texts and their embeddings to the store.

        Args:
            texts: List of text chunks
            embeddings: Numpy array of embeddings
            metadata: Optional metadata for each chunk
        """
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Search for similar vectors.

        Args:
            query_embedding: Query vector
            k: Number of results to return

        Returns:
            List of (text, score, metadata) tuples
        """
        pass

    @abstractmethod
    def save(self, path: str):
        """Save vector store to disk."""
        pass

    @abstractmethod
    def load(self, path: str):
        """Load vector store from disk."""
        pass


class FAISSVectorStore(BaseVectorStore):
    """FAISS-based vector store implementation."""

    def __init__(self, index_type: str = "flat", dimension: int = None):
        """
        Initialize FAISS vector store.

        Args:
            index_type: Type of FAISS index ('flat', 'ivf')
            dimension: Embedding dimension
        """
        self.index_type = index_type
        self.dimension = dimension
        self.index = None
        self.texts = []
        self.metadata = []

        try:
            import faiss
            self.faiss = faiss
        except ImportError:
            raise ImportError("faiss-cpu not installed. Run: pip install faiss-cpu")

    def _create_index(self, dimension: int):
        """Create FAISS index."""
        if self.index_type == "flat":
            self.index = self.faiss.IndexFlatL2(dimension)
        elif self.index_type == "ivf":
            # IVF index for faster search with some accuracy loss
            nlist = 100  # number of clusters
            quantizer = self.faiss.IndexFlatL2(dimension)
            self.index = self.faiss.IndexIVFFlat(quantizer, dimension, nlist)
            # Train with some initial vectors if needed
            self.needs_training = True
        else:
            raise ValueError(f"Unknown index type: {self.index_type}")

        self.dimension = dimension

    def add(self, texts: List[str], embeddings: np.ndarray, metadata: List[Dict[str, Any]] = None):
        """Add texts and embeddings to FAISS index."""
        if self.index is None:
            self._create_index(embeddings.shape[1])

        # Ensure embeddings are float32
        embeddings = embeddings.astype(np.float32)

        # Train IVF index if needed
        if self.index_type == "ivf" and hasattr(self, 'needs_training') and self.needs_training:
            if embeddings.shape[0] >= 100:  # Need enough data to train
                self.index.train(embeddings)
                self.needs_training = False
            else:
                # Not enough data, fall back to flat index temporarily
                print(f"Warning: Not enough data to train IVF index ({embeddings.shape[0]} < 100)")

        # Add to index
        self.index.add(embeddings)

        # Store texts and metadata
        self.texts.extend(texts)
        if metadata:
            self.metadata.extend(metadata)
        else:
            self.metadata.extend([{} for _ in texts])

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar vectors in FAISS index."""
        if self.index is None or self.index.ntotal == 0:
            return []

        # Ensure query is 2D and float32
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        query_embedding = query_embedding.astype(np.float32)

        # Search
        k = min(k, self.index.ntotal)  # Don't search for more than we have
        distances, indices = self.index.search(query_embedding, k)

        # Prepare results
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx != -1:  # Valid index
                results.append((
                    self.texts[idx],
                    float(dist),  # Lower is better for L2 distance
                    self.metadata[idx] if idx < len(self.metadata) else {}
                ))

        return results

    def save(self, path: str):
        """Save FAISS index and metadata to disk."""
        os.makedirs(path, exist_ok=True)

        # Save FAISS index
        if self.index is not None:
            self.faiss.write_index(self.index, os.path.join(path, "index.faiss"))

        # Save texts and metadata
        data = {
            'texts': self.texts,
            'metadata': self.metadata,
            'index_type': self.index_type,
            'dimension': self.dimension
        }
        with open(os.path.join(path, "data.json"), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str):
        """Load FAISS index and metadata from disk."""
        # Load FAISS index
        index_path = os.path.join(path, "index.faiss")
        if os.path.exists(index_path):
            self.index = self.faiss.read_index(index_path)

        # Load texts and metadata
        data_path = os.path.join(path, "data.json")
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.texts = data['texts']
                self.metadata = data['metadata']
                self.index_type = data.get('index_type', 'flat')
                self.dimension = data.get('dimension')


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB-based vector store implementation."""

    def __init__(self, collection_name: str = "legal_docs", persist_directory: str = None):
        """
        Initialize Chroma vector store.

        Args:
            collection_name: Name of the collection
            persist_directory: Directory to persist the database
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        try:
            import chromadb
            from chromadb.config import Settings

            if persist_directory:
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(anonymized_telemetry=False)
                )
            else:
                self.client = chromadb.Client(
                    Settings(anonymized_telemetry=False)
                )

            self.collection = self.client.get_or_create_collection(name=collection_name)
        except ImportError:
            raise ImportError("chromadb not installed. Run: pip install chromadb")

    def add(self, texts: List[str], embeddings: np.ndarray, metadata: List[Dict[str, Any]] = None):
        """Add texts and embeddings to Chroma collection."""
        # Prepare IDs
        start_id = self.collection.count()
        ids = [f"doc_{start_id + i}" for i in range(len(texts))]

        # Convert embeddings to list format
        embeddings_list = embeddings.tolist()

        # Add to collection
        if metadata:
            self.collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings_list,
                metadatas=metadata
            )
        else:
            self.collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings_list
            )

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar vectors in Chroma collection."""
        # Ensure query is 1D list
        if query_embedding.ndim > 1:
            query_embedding = query_embedding.squeeze()
        query_embedding_list = query_embedding.tolist()

        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding_list],
            n_results=k
        )

        # Format results
        output = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                output.append((
                    results['documents'][0][i],
                    results['distances'][0][i] if results['distances'] else 0.0,
                    results['metadatas'][0][i] if results['metadatas'] else {}
                ))

        return output

    def save(self, path: str):
        """Save is handled by persist_directory in Chroma."""
        if self.persist_directory:
            print(f"Chroma database is automatically persisted to {self.persist_directory}")
        else:
            print("Warning: No persist_directory set. Database is in-memory only.")

    def load(self, path: str):
        """Load is handled by persist_directory in Chroma."""
        if self.persist_directory:
            print(f"Chroma database loaded from {self.persist_directory}")
        else:
            print("Warning: No persist_directory set. Cannot load from disk.")


def get_vector_store(config: dict) -> BaseVectorStore:
    """
    Factory function to create vector store based on config.

    Args:
        config: Vector store configuration

    Returns:
        BaseVectorStore instance
    """
    store_type = config.get('type', 'faiss')

    if store_type == 'faiss':
        return FAISSVectorStore(
            index_type=config.get('index_type', 'flat'),
            dimension=config.get('dimension')
        )
    elif store_type == 'chroma':
        return ChromaVectorStore(
            collection_name=config.get('collection_name', 'legal_docs'),
            persist_directory=config.get('persist_directory')
        )
    else:
        raise ValueError(f"Unknown vector store type: {store_type}")