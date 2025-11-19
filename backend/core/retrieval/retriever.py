from typing import List, Dict, Any, Optional
from loguru import logger
from backend.core.embeddings.embedder import KoreanLegalEmbedder
from backend.core.embeddings.vectordb import VectorDB


class LegalDocumentRetriever:
    """법률 문서 검색기"""

    def __init__(
        self,
        vectordb: VectorDB,
        embedder: KoreanLegalEmbedder,
        top_k: int = 5
    ):
        """
        Args:
            vectordb: 벡터 데이터베이스
            embedder: 임베딩 모델
            top_k: 반환할 문서 수
        """
        self.vectordb = vectordb
        self.embedder = embedder
        self.top_k = top_k

        logger.info(f"Initialized retriever (top_k={top_k})")

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        쿼리와 관련된 문서 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 수 (None이면 기본값 사용)
            filter_metadata: 메타데이터 필터링 조건

        Returns:
            검색 결과 리스트
        """
        k = top_k or self.top_k

        # Generate query embedding
        logger.info(f"Searching for: '{query}'")
        query_embedding = self.embedder.embed_query(query)

        # Search in vector database
        results = self.vectordb.search(query_embedding, top_k=k)

        # Apply metadata filtering if specified
        if filter_metadata:
            results = self._filter_results(results, filter_metadata)

        logger.info(f"Retrieved {len(results)} documents")
        return results

    def retrieve_with_scores(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        스코어 임계값을 적용한 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 수
            score_threshold: 최소 유사도 점수

        Returns:
            검색 결과 리스트
        """
        results = self.retrieve(query, top_k)

        # Filter by score threshold
        filtered_results = [
            result for result in results
            if result['score'] >= score_threshold
        ]

        logger.info(f"Filtered to {len(filtered_results)} documents (threshold={score_threshold})")
        return filtered_results

    def _filter_results(
        self,
        results: List[Dict[str, Any]],
        filter_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """메타데이터 필터링"""
        filtered = []
        for result in results:
            metadata = result.get('metadata', {})
            match = all(
                metadata.get(key) == value
                for key, value in filter_metadata.items()
            )
            if match:
                filtered.append(result)

        return filtered

    def format_context(
        self,
        results: List[Dict[str, Any]],
        max_length: Optional[int] = None
    ) -> str:
        """
        검색 결과를 LLM 컨텍스트 형식으로 변환

        Args:
            results: 검색 결과
            max_length: 최대 길이 (문자 수)

        Returns:
            포맷된 컨텍스트 문자열
        """
        context_parts = []

        for i, result in enumerate(results):
            text = result['text']
            score = result.get('score', 0)
            metadata = result.get('metadata', {})

            # Format document with metadata
            doc_str = f"[문서 {i+1}] (관련도: {score:.3f})\n"

            # Add source type if available
            source_type = metadata.get('source_type', '')
            if source_type:
                source_names = {
                    'court_decision': '판례',
                    'statute': '법령',
                    'interpretation': '해석례',
                    'constitutional': '헌법재판소 결정례'
                }
                doc_str += f"출처: {source_names.get(source_type, source_type)}\n"

            doc_str += f"{text}\n"
            context_parts.append(doc_str)

        context = "\n".join(context_parts)

        # Truncate if needed
        if max_length and len(context) > max_length:
            context = context[:max_length] + "\n...(truncated)"

        return context

    def get_diverse_results(
        self,
        query: str,
        top_k: int = 10,
        diversity_threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        다양성을 고려한 검색 (유사한 문서 제거)

        Args:
            query: 검색 쿼리
            top_k: 초기 검색 문서 수
            diversity_threshold: 유사도 임계값 (이 값 이상이면 중복으로 간주)

        Returns:
            다양성이 확보된 검색 결과
        """
        # Retrieve more documents initially
        results = self.retrieve(query, top_k=top_k * 2)

        if not results:
            return []

        # Select diverse documents
        diverse_results = [results[0]]  # Always include the top result

        for result in results[1:]:
            # Check if this document is too similar to already selected ones
            is_diverse = True
            for selected in diverse_results:
                # Simple similarity check based on text overlap
                similarity = self._text_similarity(result['text'], selected['text'])
                if similarity > diversity_threshold:
                    is_diverse = False
                    break

            if is_diverse:
                diverse_results.append(result)

            if len(diverse_results) >= top_k:
                break

        logger.info(f"Selected {len(diverse_results)} diverse documents from {len(results)}")
        return diverse_results

    def _text_similarity(self, text1: str, text2: str) -> float:
        """간단한 텍스트 유사도 계산 (Jaccard similarity)"""
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)
