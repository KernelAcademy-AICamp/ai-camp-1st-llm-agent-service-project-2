"""
외부 임베딩 API (OpenAI 호환) 클라이언트

OpenAI 표준 /v1/embeddings 엔드포인트를 사용하여
외부 GPU 서버에서 임베딩을 생성합니다.
"""

import httpx
import numpy as np
from typing import List, Optional
from loguru import logger
import os
import time

# .env 파일 로드 (환경변수 설정)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class RemoteEmbedder:
    """OpenAI 호환 임베딩 API 클라이언트"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "dragonkue/snowflake-arctic-embed-l-v2.0-ko",
        batch_size: int = 96,
        timeout: int = 600
    ):
        """
        Args:
            base_url: API 서버 URL (기본: 환경변수 REMOTE_EMBED_BASE_URL)
            api_key: API 키 (기본: 환경변수 REMOTE_EMBED_API_KEY)
            model: 임베딩 모델명
            batch_size: 배치 크기
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = (base_url or os.getenv("REMOTE_EMBED_BASE_URL", "https://llm.wonllmapi.uk")).rstrip('/')
        self.api_key = api_key or os.getenv("REMOTE_EMBED_API_KEY", "")
        self.model = model
        self.batch_size = batch_size
        self.timeout = timeout

        # 모델별 차원 정보
        self.model_dimensions = {
            "dragonkue/snowflake-arctic-embed-l-v2.0-ko": 1024,
            "jhgan/ko-sroberta-multitask": 768,
        }
        self.dimension = self.model_dimensions.get(model, 1024)

        # httpx 클라이언트 (connection pooling 설정)
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.client = httpx.Client(
            timeout=timeout,
            headers=headers,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )

        # 재시도 설정
        self.max_retries = 3

        self.model_name = model
        logger.info(f"RemoteEmbedder initialized:")
        logger.info(f"  Base URL: {self.base_url}")
        logger.info(f"  Model: {self.model}")
        logger.info(f"  Dimension: {self.dimension}")

    def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """OpenAI 호환 /v1/embeddings API 호출"""
        url = f"{self.base_url}/v1/embeddings"

        payload = {
            "input": texts,
            "model": self.model
        }

        response = self.client.post(url, json=payload)
        response.raise_for_status()

        result = response.json()

        # OpenAI 형식: {"data": [{"embedding": [...], "index": 0}, ...]}
        embeddings = [item["embedding"] for item in sorted(result["data"], key=lambda x: x["index"])]

        return embeddings

    def embed_documents(
        self,
        texts: List[str],
        normalize: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        문서들을 임베딩으로 변환

        Args:
            texts: 임베딩할 텍스트 리스트
            normalize: 정규화 여부 (API에서 처리됨)
            show_progress: 진행 표시

        Returns:
            임베딩 벡터 배열 (N, dimension)
        """
        if not texts:
            return np.array([])

        logger.info(f"Requesting embeddings for {len(texts)} documents...")

        all_embeddings = []

        # 배치 처리 (재시도 로직 포함)
        total_batches = (len(texts) - 1) // self.batch_size + 1
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            if show_progress:
                logger.info(f"  Processing batch {batch_num}/{total_batches}")

            # 재시도 로직
            for attempt in range(self.max_retries):
                try:
                    embeddings = self._call_embedding_api(batch)
                    all_embeddings.extend(embeddings)
                    break
                except httpx.HTTPError as e:
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # exponential backoff
                        logger.warning(f"  Retry {attempt + 1}/{self.max_retries} for batch {batch_num} (waiting {wait_time}s)")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Failed after {self.max_retries} retries for batch {batch_num}: {e}")
                        raise
                except Exception as e:
                    logger.error(f"Error during embedding batch {batch_num}: {e}")
                    raise

        result = np.array(all_embeddings, dtype=np.float32)
        logger.info(f"Received embeddings with shape: {result.shape}")

        return result

    def embed_query(self, query: str, normalize: bool = True) -> np.ndarray:
        """
        쿼리를 임베딩으로 변환

        Args:
            query: 검색 쿼리
            normalize: 정규화 여부

        Returns:
            임베딩 벡터 (dimension,)
        """
        try:
            embeddings = self._call_embedding_api([query])
            return np.array(embeddings[0], dtype=np.float32)
        except Exception as e:
            logger.error(f"Error during query embedding: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """임베딩 차원 반환"""
        return self.dimension

    def close(self):
        """클라이언트 종료"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
