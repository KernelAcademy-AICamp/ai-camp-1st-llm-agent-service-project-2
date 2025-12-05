"""
Qdrant Native Hybrid Retriever

Qdrant의 네이티브 하이브리드 검색 기능을 활용하여
Dense (Semantic) + Sparse (SPLADE) 검색을 수행합니다.

특징:
- Qdrant Prefetch + RRF Fusion 사용
- BM25 별도 인덱스 불필요 (시작 시간 40초 절약)
- SPLADE 기반 의미 있는 sparse 검색
"""

from typing import List, Dict, Any, Optional, Literal
from loguru import logger

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Prefetch, FusionQuery, Fusion, SparseVector,
    Filter, FieldCondition, MatchValue, MatchAny
)


class QdrantHybridRetriever:
    """
    Qdrant Native Hybrid Retriever

    Dense (snowflake-arctic-embed) + Sparse (SPLADE) 하이브리드 검색
    Qdrant의 Prefetch + RRF Fusion 기능 사용
    """

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        qdrant_api_key: Optional[str] = None,
        collection_name: str = "law_documents_hybrid",
        dense_embedder: Any = None,
        splade_encoder: Any = None,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        prefetch_limit: int = 100,
        timeout: int = 300
    ):
        """
        Args:
            qdrant_url: Qdrant 서버 URL
            qdrant_api_key: Qdrant API 키
            collection_name: 하이브리드 컬렉션 이름
            dense_embedder: Dense 임베더 (RemoteEmbedder 등)
            splade_encoder: SPLADE 인코더
            dense_weight: Dense 검색 가중치 (RRF에서는 prefetch limit으로 조절)
            sparse_weight: Sparse 검색 가중치
            prefetch_limit: Prefetch 단계에서 가져올 문서 수
            timeout: HTTP 타임아웃 (초)
        """
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.dense_embedder = dense_embedder
        self.splade_encoder = splade_encoder
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.prefetch_limit = prefetch_limit

        # Qdrant 클라이언트
        self.client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=timeout
        )

        logger.info(
            f"Initialized QdrantHybridRetriever "
            f"(collection={collection_name}, "
            f"dense_weight={dense_weight}, sparse_weight={sparse_weight})"
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        search_mode: Literal["hybrid", "dense", "sparse"] = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 수행

        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 수
            filter_metadata: 메타데이터 필터 (예: {"doc_type": "판결문"})
            search_mode: 검색 모드 ("hybrid", "dense", "sparse")

        Returns:
            검색 결과 리스트 [{text, metadata, score}, ...]
        """
        logger.info(f"Hybrid search: '{query}' (mode={search_mode}, top_k={top_k})")

        # 필터 구성
        qdrant_filter = None
        if filter_metadata:
            conditions = []
            for key, value in filter_metadata.items():
                if isinstance(value, list):
                    conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
                else:
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            qdrant_filter = Filter(must=conditions)

        try:
            if search_mode == "hybrid":
                results = self._hybrid_search(query, top_k, qdrant_filter)
            elif search_mode == "dense":
                results = self._dense_search(query, top_k, qdrant_filter)
            else:  # sparse
                results = self._sparse_search(query, top_k, qdrant_filter)

            logger.info(f"Retrieved {len(results)} documents")
            return results

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def _get_dense_vector(self, query: str) -> list:
        """Dense 임베딩 생성 (다양한 embedder 인터페이스 지원)"""
        # embed_query 메서드 우선 사용 (RemoteEmbedder 등)
        if hasattr(self.dense_embedder, 'embed_query'):
            dense_vector = self.dense_embedder.embed_query(query)
        elif hasattr(self.dense_embedder, 'embed'):
            dense_vector = self.dense_embedder.embed(query)
        else:
            raise ValueError("dense_embedder must have 'embed_query' or 'embed' method")

        if hasattr(dense_vector, 'tolist'):
            dense_vector = dense_vector.tolist()
        return dense_vector

    def _hybrid_search(
        self,
        query: str,
        top_k: int,
        qdrant_filter: Optional[Filter]
    ) -> List[Dict[str, Any]]:
        """
        Qdrant 네이티브 하이브리드 검색 (Prefetch + RRF)
        """
        # 1. Dense 임베딩 생성
        dense_vector = self._get_dense_vector(query)

        # 2. Sparse 임베딩 생성 (SPLADE)
        sparse_indices, sparse_values = self.splade_encoder.encode(query)

        # 3. Qdrant Prefetch + Fusion 검색
        results = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                # Dense 검색
                Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=self.prefetch_limit,
                    filter=qdrant_filter
                ),
                # Sparse 검색 (SPLADE)
                Prefetch(
                    query=SparseVector(
                        indices=sparse_indices,
                        values=sparse_values
                    ),
                    using="splade",
                    limit=self.prefetch_limit,
                    filter=qdrant_filter
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k,
            with_payload=True
        )

        return self._format_results(results.points)

    def _dense_search(
        self,
        query: str,
        top_k: int,
        qdrant_filter: Optional[Filter]
    ) -> List[Dict[str, Any]]:
        """
        Dense 전용 검색
        """
        dense_vector = self._get_dense_vector(query)

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=dense_vector,
            using="dense",
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True
        )

        return self._format_results(results.points)

    def _sparse_search(
        self,
        query: str,
        top_k: int,
        qdrant_filter: Optional[Filter]
    ) -> List[Dict[str, Any]]:
        """
        Sparse (SPLADE) 전용 검색
        """
        sparse_indices, sparse_values = self.splade_encoder.encode(query)

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=SparseVector(
                indices=sparse_indices,
                values=sparse_values
            ),
            using="splade",
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True
        )

        return self._format_results(results.points)

    def _format_results(self, points: list) -> List[Dict[str, Any]]:
        """
        Qdrant 결과를 통일된 형식으로 변환
        """
        formatted = []
        for point in points:
            payload = dict(point.payload) if point.payload else {}
            text = payload.pop('text', '')

            formatted.append({
                "id": point.id,
                "text": text,
                "metadata": payload,
                "score": point.score
            })

        return formatted

    def format_context(
        self,
        results: List[Dict[str, Any]],
        max_length: Optional[int] = None
    ) -> str:
        """
        검색 결과를 LLM 컨텍스트 형식으로 변환

        Args:
            results: 검색 결과 리스트
            max_length: 최대 컨텍스트 길이

        Returns:
            포맷된 컨텍스트 문자열
        """
        if not results:
            return ""

        context_parts = []
        total_length = 0

        for i, result in enumerate(results, 1):
            text = result.get('text', '')
            metadata = result.get('metadata', {})
            score = result.get('score', 0)

            # 문서 타입별 출처 정보
            doc_type = metadata.get('doc_type', '')
            source_info = self._format_source_info(metadata, doc_type)

            # 컨텍스트 포맷
            context_entry = f"[문서 {i}] {source_info}\n{text}\n"

            # 최대 길이 체크
            if max_length and total_length + len(context_entry) > max_length:
                break

            context_parts.append(context_entry)
            total_length += len(context_entry)

        return "\n".join(context_parts)

    def _format_source_info(self, metadata: Dict[str, Any], doc_type: str) -> str:
        """
        문서 타입별 출처 정보 포맷
        """
        if doc_type == "판결문":
            case_num = metadata.get('case_num', '')
            court = metadata.get('court_name', '')
            return f"[판례: {case_num}] ({court})"
        elif doc_type == "결정례":
            case_num = metadata.get('case_num', '')
            return f"[결정례: {case_num}]"
        elif doc_type == "법령":
            law_title = metadata.get('law_title', metadata.get('title', ''))
            article = metadata.get('article_num', '')
            return f"[법령: {law_title} {article}]"
        elif doc_type == "해석례":
            agenda = metadata.get('agenda', '')
            return f"[해석례: {agenda}]"
        else:
            return f"[{doc_type or '문서'}]"

    def get_count(self) -> int:
        """컬렉션 문서 개수 반환"""
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 반환"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "points_count": info.points_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": str(info.status),
                "search_mode": "hybrid (dense + splade)"
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
