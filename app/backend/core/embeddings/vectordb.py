from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import numpy as np
from pathlib import Path
import pickle
from loguru import logger

import chromadb
from chromadb.config import Settings
import faiss


class VectorDB(ABC):
    """벡터 데이터베이스 인터페이스"""

    @abstractmethod
    def add_documents(self, texts: List[str], embeddings: np.ndarray, metadatas: List[Dict]) -> None:
        """문서 추가"""
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """유사 문서 검색"""
        pass

    @abstractmethod
    def save(self) -> None:
        """데이터베이스 저장"""
        pass

    @abstractmethod
    def load(self) -> None:
        """데이터베이스 로드"""
        pass


class ChromaVectorDB(VectorDB):
    """ChromaDB 기반 벡터 데이터베이스"""

    def __init__(self, persist_directory: str, collection_name: str = "law_documents"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name

        logger.info(f"Initializing ChromaDB at {self.persist_directory}")

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

        logger.info(f"ChromaDB initialized. Collection: {self.collection_name}")

    def add_documents(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """
        문서 추가

        Args:
            texts: 텍스트 리스트
            embeddings: 임베딩 배열
            metadatas: 메타데이터 리스트
        """
        # Convert numpy array to list
        embeddings_list = embeddings.tolist()

        # Generate IDs
        start_id = self.collection.count()
        ids = [f"doc_{start_id + i}" for i in range(len(texts))]

        # Clean metadatas (Chroma doesn't support nested dicts)
        cleaned_metadatas = []
        for meta in metadatas:
            cleaned_meta = {}
            for key, value in meta.items():
                if isinstance(value, (str, int, float, bool)):
                    cleaned_meta[key] = value
                elif value is not None:
                    cleaned_meta[key] = str(value)
            cleaned_metadatas.append(cleaned_meta)

        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings_list,
            documents=texts,
            metadatas=cleaned_metadatas
        )

        logger.info(f"Added {len(texts)} documents to ChromaDB")

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        유사 문서 검색

        Args:
            query_embedding: 쿼리 임베딩
            top_k: 반환할 문서 수

        Returns:
            검색 결과 리스트
        """
        query_embedding_list = query_embedding.tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding_list],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'score': 1 - results['distances'][0][i]  # Convert distance to similarity
            })

        return formatted_results

    def save(self) -> None:
        """데이터베이스 저장 (자동 저장됨)"""
        logger.info("ChromaDB auto-persisted")

    def load(self) -> None:
        """데이터베이스 로드 (자동 로드됨)"""
        logger.info(f"ChromaDB loaded from {self.persist_directory}")

    def get_count(self) -> int:
        """문서 개수 반환"""
        return self.collection.count()

    def delete_collection(self) -> None:
        """컬렉션 삭제"""
        self.client.delete_collection(self.collection_name)
        logger.info(f"Deleted collection: {self.collection_name}")


class FAISSVectorDB(VectorDB):
    """FAISS 기반 벡터 데이터베이스"""

    def __init__(self, index_path: str, dimension: int = 768):
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension

        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product (for normalized vectors = cosine)

        # Store documents and metadatas separately
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []

        logger.info(f"Initialized FAISS index (dimension={dimension})")

    def add_documents(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """
        문서 추가

        Args:
            texts: 텍스트 리스트
            embeddings: 임베딩 배열 (must be normalized)
            metadatas: 메타데이터 리스트
        """
        # Ensure embeddings are float32
        embeddings = embeddings.astype(np.float32)

        # Add to FAISS index
        self.index.add(embeddings)

        # Store documents and metadatas
        self.documents.extend(texts)
        self.metadatas.extend(metadatas)

        logger.info(f"Added {len(texts)} documents to FAISS. Total: {self.index.ntotal}")

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        유사 문서 검색

        Args:
            query_embedding: 쿼리 임베딩 (must be normalized)
            top_k: 반환할 문서 수

        Returns:
            검색 결과 리스트
        """
        # Ensure query is 2D and float32
        query_embedding = query_embedding.astype(np.float32).reshape(1, -1)

        # Search
        scores, indices = self.index.search(query_embedding, top_k)

        # Format results
        formatted_results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):  # Valid index
                formatted_results.append({
                    'id': f"doc_{idx}",
                    'text': self.documents[idx],
                    'metadata': self.metadatas[idx],
                    'score': float(scores[0][i])
                })

        return formatted_results

    def save(self) -> None:
        """데이터베이스 저장"""
        # Save FAISS index
        faiss.write_index(self.index, str(self.index_path / "index.faiss"))

        # Save documents and metadatas
        with open(self.index_path / "documents.pkl", "wb") as f:
            pickle.dump(self.documents, f)

        with open(self.index_path / "metadatas.pkl", "wb") as f:
            pickle.dump(self.metadatas, f)

        logger.info(f"Saved FAISS index to {self.index_path}")

    def load(self) -> None:
        """데이터베이스 로드"""
        # Load FAISS index
        index_file = self.index_path / "index.faiss"
        if index_file.exists():
            self.index = faiss.read_index(str(index_file))
            logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")

            # Load documents and metadatas
            with open(self.index_path / "documents.pkl", "rb") as f:
                self.documents = pickle.load(f)

            with open(self.index_path / "metadatas.pkl", "rb") as f:
                self.metadatas = pickle.load(f)

            logger.info(f"Loaded {len(self.documents)} documents")
        else:
            logger.warning(f"No index found at {index_file}")

    def get_count(self) -> int:
        """문서 개수 반환"""
        return self.index.ntotal


def create_vector_db(db_type: str, **kwargs) -> VectorDB:
    """
    벡터 데이터베이스 팩토리 함수

    Args:
        db_type: 'chroma' or 'faiss'
        **kwargs: 데이터베이스별 파라미터

    Returns:
        VectorDB 인스턴스
    """
    if db_type.lower() == "chroma":
        return ChromaVectorDB(
            persist_directory=kwargs.get("persist_directory", "./data/vectordb/chroma"),
            collection_name=kwargs.get("collection_name", "law_documents")
        )
    elif db_type.lower() == "faiss":
        return FAISSVectorDB(
            index_path=kwargs.get("index_path", "./data/vectordb/faiss"),
            dimension=kwargs.get("dimension", 768)
        )
    else:
        raise ValueError(f"Unknown vector DB type: {db_type}")
