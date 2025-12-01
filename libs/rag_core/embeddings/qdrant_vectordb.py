"""
Qdrant Vector Database implementation
기존 VectorDB 인터페이스와 호환

qdrant-client >= 1.16.0 호환
"""

import numpy as np
from typing import List, Dict, Any, Optional
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import hashlib

from .vectordb import VectorDB


class QdrantVectorDB(VectorDB):
    """Qdrant Vector Database - 기존 VectorDB 인터페이스 호환"""

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
        collection_name: str = "law_documents",
        embedding_dim: int = 1024,  # snowflake-arctic-embed-l-v2.0-ko 기본값
        distance: str = "cosine"
    ):
        """
        Args:
            url: Qdrant 서버 URL
            api_key: API 키 (클라우드 사용 시)
            collection_name: 컬렉션 이름
            embedding_dim: 임베딩 차원
            distance: 거리 메트릭 (cosine, euclid, dot)
        """
        self.url = url
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

        # Distance 설정
        distance_map = {
            "cosine": Distance.COSINE,
            "euclid": Distance.EUCLID,
            "dot": Distance.DOT
        }
        self.distance = distance_map.get(distance.lower(), Distance.COSINE)

        # Qdrant 클라이언트 초기화
        logger.info(f"Connecting to Qdrant: {url}")
        self.client = QdrantClient(url=url, api_key=api_key)

        # 컬렉션 생성 (없으면)
        self._ensure_collection()

    def _ensure_collection(self):
        """컬렉션 존재 확인 및 생성"""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=self.distance
                    )
                )
                logger.info(f"Collection created: {self.collection_name}")
            else:
                logger.info(f"Collection exists: {self.collection_name}")

        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise

    def add_documents(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """
        문서 추가 (기존 VectorDB 인터페이스 호환)

        Args:
            texts: 텍스트 리스트
            embeddings: 임베딩 배열 [N, dim]
            metadatas: 메타데이터 리스트
        """
        if len(embeddings) != len(texts) or len(embeddings) != len(metadatas):
            raise ValueError("texts, embeddings, metadatas 길이 불일치")

        logger.info(f"Adding {len(embeddings)} documents to Qdrant...")

        # PointStruct 생성 (text와 document_id를 payload에 포함)
        points = []
        for i, (text, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas)):
            # document_id 생성: metadata에 있으면 사용, 없으면 source+chunk_id로 생성
            if 'document_id' in metadata:
                doc_id = metadata['document_id']
            else:
                source = metadata.get('source', 'unknown')
                chunk_id = metadata.get('chunk_id', i)
                doc_id = f"{source}_{chunk_id}"

            # 메타데이터 정리 (nested dict 처리)
            cleaned_meta = {}
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    cleaned_meta[key] = value
                elif value is not None:
                    cleaned_meta[key] = str(value)

            # text와 document_id를 payload에 포함
            cleaned_meta['text'] = text
            cleaned_meta['document_id'] = doc_id

            # 결정적 ID 생성 (해시 기반 - 재실행 시 동일 문서는 덮어쓰기)
            numeric_id = int(hashlib.md5(doc_id.encode()).hexdigest()[:16], 16)

            point = PointStruct(
                id=numeric_id,
                vector=embedding.tolist(),
                payload=cleaned_meta
            )
            points.append(point)

        # 배치 업로드 (진행 로그 포함)
        batch_size = 100
        total_batches = (len(points) - 1) // batch_size + 1
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
            logger.info(f"  Uploaded batch {i//batch_size + 1}/{total_batches} ({len(batch)} points)")

        logger.info(f"Added {len(points)} points to {self.collection_name}")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        벡터 검색 (기존 VectorDB 인터페이스 호환)

        Args:
            query_embedding: 쿼리 임베딩 벡터
            top_k: 반환할 결과 수

        Returns:
            검색 결과 리스트 [{id, text, metadata, score}, ...]
        """
        try:
            # qdrant-client >= 1.16.0 uses query_points instead of search
            from qdrant_client.models import QueryRequest

            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding.tolist(),
                limit=top_k,
                with_payload=True
            )

            formatted_results = []
            for point in results.points:
                payload = dict(point.payload) if point.payload else {}
                text = payload.pop('text', '')  # text를 별도 추출

                formatted_results.append({
                    "id": point.id,
                    "text": text,
                    "metadata": payload,
                    "score": point.score
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Search error: {e}")
            raise

    def save(self) -> None:
        """데이터베이스 저장 (Qdrant는 자동 저장)"""
        logger.info("Qdrant auto-persisted")

    def load(self) -> None:
        """데이터베이스 로드 (Qdrant는 자동 로드)"""
        logger.info(f"Qdrant loaded from {self.url}")

    def get_count(self) -> int:
        """문서 개수 반환"""
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """컬렉션 통계"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "points_count": info.points_count,
                "status": str(info.status)
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def delete_collection(self) -> None:
        """컬렉션 삭제"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Collection deleted: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise

    def get_full_document(
        self,
        filter_field: str,
        filter_value: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        메타데이터 필터로 같은 문서의 모든 청크를 가져와서 합침

        Args:
            filter_field: 필터링할 메타데이터 필드 (예: 'case_number', 'title', 'source')
            filter_value: 필터 값
            limit: 최대 청크 수

        Returns:
            청크 리스트 (chunk_id 순 정렬)
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        try:
            # 필터 조건으로 모든 청크 검색
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key=filter_field,
                            match=MatchValue(value=filter_value)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False  # 벡터 불필요
            )

            points = results[0]  # (points, next_page_offset)

            if not points:
                logger.warning(f"No chunks found for {filter_field}={filter_value}")
                return []

            # 청크 추출 및 정렬
            chunks = []
            for point in points:
                payload = dict(point.payload) if point.payload else {}
                text = payload.get('text', '')
                chunk_id = payload.get('chunk_id', 0)

                # chunk_id가 문자열일 수 있음 (예: "0_1")
                if isinstance(chunk_id, str):
                    try:
                        # "0_1" -> 0.1로 변환하여 정렬 가능하게
                        parts = chunk_id.split('_')
                        sort_key = float(parts[0]) + float(parts[1]) / 1000 if len(parts) > 1 else float(parts[0])
                    except:
                        sort_key = 0
                else:
                    sort_key = float(chunk_id)

                chunks.append({
                    "text": text,
                    "chunk_id": chunk_id,
                    "sort_key": sort_key,
                    "metadata": payload
                })

            # chunk_id 순으로 정렬
            chunks.sort(key=lambda x: x['sort_key'])

            logger.info(f"Found {len(chunks)} chunks for {filter_field}={filter_value}")
            return chunks

        except Exception as e:
            logger.error(f"Error getting full document: {e}")
            return []

    def get_full_document_text(
        self,
        filter_field: str,
        filter_value: str,
        limit: int = 100
    ) -> str:
        """
        같은 문서의 모든 청크를 가져와서 전체 텍스트로 합침

        Args:
            filter_field: 필터링할 메타데이터 필드
            filter_value: 필터 값
            limit: 최대 청크 수

        Returns:
            합쳐진 전체 텍스트
        """
        chunks = self.get_full_document(filter_field, filter_value, limit)

        if not chunks:
            return ""

        # 텍스트 합치기 (중복 제거를 위해 overlap 부분 처리 가능)
        texts = [chunk['text'] for chunk in chunks]
        full_text = '\n\n'.join(texts)

        return full_text
