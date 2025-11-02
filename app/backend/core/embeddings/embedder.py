from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from loguru import logger
from tqdm import tqdm


class KoreanLegalEmbedder:
    """한국어 법률 문서 임베딩 생성기"""

    def __init__(
        self,
        model_name: str = "jhgan/ko-sroberta-multitask",
        device: str = "cpu",
        batch_size: int = 32
    ):
        """
        Args:
            model_name: 사용할 임베딩 모델 이름
                - jhgan/ko-sroberta-multitask: 한국어 특화 (추천)
                - BM-K/KoSimCSE-roberta: 한국어 SimCSE
                - snunlp/KR-SBERT-V40K-klueNLI-augSTS: 한국어 SBERT
            device: 'cpu' or 'cuda'
            batch_size: 배치 크기
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size

        logger.info(f"Loading embedding model: {model_name} on {device}")
        self.model = SentenceTransformer(model_name, device=device)
        logger.info(f"Model loaded successfully. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

    def embed_documents(self, texts: List[str], show_progress: bool = True) -> np.ndarray:
        """
        문서들을 임베딩으로 변환

        Args:
            texts: 임베딩할 텍스트 리스트
            show_progress: 진행 표시줄 표시 여부

        Returns:
            임베딩 벡터 배열 (shape: [len(texts), embedding_dim])
        """
        if not texts:
            return np.array([])

        logger.info(f"Embedding {len(texts)} documents...")

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True  # Cosine similarity를 위한 정규화
        )

        logger.info(f"Created embeddings with shape: {embeddings.shape}")
        return embeddings

    def embed_query(self, query: str) -> np.ndarray:
        """
        쿼리를 임베딩으로 변환

        Args:
            query: 검색 쿼리

        Returns:
            임베딩 벡터
        """
        embedding = self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        return embedding

    def get_embedding_dimension(self) -> int:
        """임베딩 차원 반환"""
        return self.model.get_sentence_embedding_dimension()

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        두 임베딩 간 코사인 유사도 계산

        Args:
            embedding1: 첫 번째 임베딩
            embedding2: 두 번째 임베딩

        Returns:
            코사인 유사도 (-1 ~ 1)
        """
        # Normalize if not already normalized
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 > 0 and norm2 > 0:
            embedding1 = embedding1 / norm1
            embedding2 = embedding2 / norm2

        similarity = np.dot(embedding1, embedding2)
        return float(similarity)

    def batch_embed_with_metadata(
        self,
        texts: List[str],
        metadatas: Optional[List[dict]] = None
    ) -> tuple:
        """
        텍스트와 메타데이터를 함께 처리

        Args:
            texts: 텍스트 리스트
            metadatas: 메타데이터 리스트

        Returns:
            (embeddings, metadatas) 튜플
        """
        embeddings = self.embed_documents(texts)

        if metadatas is None:
            metadatas = [{} for _ in range(len(texts))]

        return embeddings, metadatas


# Available Korean embedding models
KOREAN_EMBEDDING_MODELS = {
    "ko-sroberta-multitask": {
        "name": "jhgan/ko-sroberta-multitask",
        "description": "한국어 다중 태스크 학습 모델 (일반 목적)",
        "dimension": 768
    },
    "ko-simcse": {
        "name": "BM-K/KoSimCSE-roberta",
        "description": "한국어 SimCSE (문장 유사도 특화)",
        "dimension": 768
    },
    "kr-sbert": {
        "name": "snunlp/KR-SBERT-V40K-klueNLI-augSTS",
        "description": "한국어 SBERT (의미 유사도)",
        "dimension": 768
    },
}


def get_recommended_model(task: str = "general") -> str:
    """
    태스크에 따른 추천 모델 반환

    Args:
        task: "general", "similarity", "search"

    Returns:
        모델 이름
    """
    if task == "similarity":
        return KOREAN_EMBEDDING_MODELS["ko-simcse"]["name"]
    elif task == "search":
        return KOREAN_EMBEDDING_MODELS["ko-sroberta-multitask"]["name"]
    else:
        return KOREAN_EMBEDDING_MODELS["ko-sroberta-multitask"]["name"]
