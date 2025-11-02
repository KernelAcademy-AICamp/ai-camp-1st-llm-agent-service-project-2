"""
Hybrid Retriever: Semantic Search + BM25 융합

학습 목적:
- Hybrid Search: Dense(Semantic) + Sparse(BM25) 검색 결합
- RRF (Reciprocal Rank Fusion): 서로 다른 검색 결과 융합 알고리즘
- Adaptive Weighting: 쿼리 타입에 따라 가중치 자동 조정
- 장점: Semantic의 의미 이해 + BM25의 정확한 키워드 매칭
"""

from typing import List, Dict, Any, Optional, Literal
from loguru import logger
import re
from app.backend.core.retrieval.retriever import LegalDocumentRetriever
from app.backend.core.retrieval.bm25_index import BM25Index


class HybridRetriever:
    """Semantic Search + BM25 Hybrid Retriever"""

    def __init__(
        self,
        semantic_retriever: LegalDocumentRetriever,
        bm25_index: BM25Index,
        fusion_method: Literal['rrf', 'weighted_sum'] = 'rrf',
        semantic_weight: float = 0.5,
        rrf_k: int = 60,
        enable_adaptive_weighting: bool = True
    ):
        """
        Args:
            semantic_retriever: Semantic search retriever (Vector DB 기반)
            bm25_index: BM25 검색 인덱스
            fusion_method: 융합 방법 ('rrf' 또는 'weighted_sum')
            semantic_weight: Semantic 검색 가중치 (0.0~1.0, BM25 = 1 - semantic_weight)
            rrf_k: RRF 파라미터 (일반적으로 60)
            enable_adaptive_weighting: 쿼리 타입별 자동 가중치 조정 활성화

        학습 노트:
            - RRF: score = Σ 1/(k + rank_i) - 순위 기반 융합
            - Weighted Sum: score = w1*score1 + w2*score2 - 점수 기반 융합
            - Adaptive: 쿼리 타입 분석 후 가중치 자동 조정
        """
        self.semantic_retriever = semantic_retriever
        self.bm25_index = bm25_index
        self.fusion_method = fusion_method
        self.semantic_weight = semantic_weight
        self.rrf_k = rrf_k
        self.enable_adaptive_weighting = enable_adaptive_weighting

        logger.info(
            f"Initialized HybridRetriever ("
            f"fusion={fusion_method}, "
            f"semantic_weight={semantic_weight}, "
            f"adaptive={enable_adaptive_weighting})"
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: Optional[float] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid 검색 수행

        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 수
            semantic_weight: Semantic 가중치 (None이면 기본값 사용)
            filter_metadata: 메타데이터 필터링

        Returns:
            융합된 검색 결과 리스트
        """
        # Adaptive weighting (쿼리 타입별 가중치 조정)
        if self.enable_adaptive_weighting and semantic_weight is None:
            semantic_weight = self._get_adaptive_weight(query)
        elif semantic_weight is None:
            semantic_weight = self.semantic_weight

        bm25_weight = 1.0 - semantic_weight

        logger.info(
            f"Hybrid search: '{query}' "
            f"(semantic={semantic_weight:.2f}, bm25={bm25_weight:.2f})"
        )

        # 1. Semantic Search
        # 더 많은 문서를 가져와서 융합 시 다양성 확보
        semantic_results = self.semantic_retriever.retrieve(
            query,
            top_k=top_k * 3,
            filter_metadata=filter_metadata
        )

        # 2. BM25 Search
        bm25_results = self.bm25_index.search(
            query,
            top_k=top_k * 3
        )

        # 3. Fusion
        if self.fusion_method == 'rrf':
            fused_results = self._reciprocal_rank_fusion(
                semantic_results,
                bm25_results,
                semantic_weight,
                bm25_weight
            )
        else:  # weighted_sum
            fused_results = self._weighted_sum_fusion(
                semantic_results,
                bm25_results,
                semantic_weight,
                bm25_weight
            )

        # Top-K만 반환
        final_results = fused_results[:top_k]

        logger.info(
            f"Retrieved {len(final_results)} documents "
            f"(semantic: {len(semantic_results)}, bm25: {len(bm25_results)})"
        )

        return final_results

    def _reciprocal_rank_fusion(
        self,
        semantic_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        semantic_weight: float,
        bm25_weight: float
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF)

        학습 목적:
            RRF는 서로 다른 검색 시스템의 결과를 융합하는 효과적인 방법

            공식: RRF_score = Σ weight_i / (k + rank_i)
            - k: 일반적으로 60 (상위 결과에 너무 큰 가중치 방지)
            - rank_i: 각 검색 시스템에서의 순위 (1부터 시작)
            - weight_i: 검색 시스템별 가중치

            장점:
            - 점수 범위가 다른 시스템 융합에 강건함
            - 순위 정보만 사용하여 정규화 불필요
            - 구현 간단하고 효과적

        Args:
            semantic_results: Semantic 검색 결과
            bm25_results: BM25 검색 결과
            semantic_weight: Semantic 가중치
            bm25_weight: BM25 가중치

        Returns:
            융합된 결과 (RRF 점수 기준 정렬)
        """
        # 문서별 점수 집계
        doc_scores: Dict[str, Dict[str, Any]] = {}

        # Semantic 결과 처리
        for rank, result in enumerate(semantic_results, start=1):
            text = result['text']
            rrf_score = semantic_weight / (self.rrf_k + rank)

            if text not in doc_scores:
                doc_scores[text] = {
                    'text': text,
                    'metadata': result['metadata'],
                    'score': 0.0,
                    'semantic_rank': rank,
                    'bm25_rank': None,
                    'semantic_score': result.get('score', 0),
                    'bm25_score': 0,
                    'fusion_method': 'rrf'
                }

            doc_scores[text]['score'] += rrf_score

        # BM25 결과 처리
        for rank, result in enumerate(bm25_results, start=1):
            text = result['text']
            rrf_score = bm25_weight / (self.rrf_k + rank)

            if text not in doc_scores:
                doc_scores[text] = {
                    'text': text,
                    'metadata': result['metadata'],
                    'score': 0.0,
                    'semantic_rank': None,
                    'bm25_rank': rank,
                    'semantic_score': 0,
                    'bm25_score': result.get('score', 0),
                    'fusion_method': 'rrf'
                }
            else:
                doc_scores[text]['bm25_rank'] = rank
                doc_scores[text]['bm25_score'] = result.get('score', 0)

            doc_scores[text]['score'] += rrf_score

        # 점수 기준 정렬
        sorted_results = sorted(
            doc_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )

        return sorted_results

    def _weighted_sum_fusion(
        self,
        semantic_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        semantic_weight: float,
        bm25_weight: float
    ) -> List[Dict[str, Any]]:
        """
        Weighted Sum Fusion

        학습 목적:
            점수 기반 융합 방법 (정규화 필요)

            공식: score = w1 * norm(score1) + w2 * norm(score2)

            장점: 직관적이고 간단
            단점: 점수 범위가 다르면 정규화 필요

        Args:
            semantic_results: Semantic 검색 결과
            bm25_results: BM25 검색 결과
            semantic_weight: Semantic 가중치
            bm25_weight: BM25 가중치

        Returns:
            융합된 결과
        """
        # 점수 정규화 (min-max scaling)
        def normalize_scores(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            if not results:
                return []

            scores = [r['score'] for r in results]
            min_score = min(scores)
            max_score = max(scores)

            if max_score == min_score:
                # 모든 점수가 같으면 1로 정규화
                for r in results:
                    r['normalized_score'] = 1.0
            else:
                for r in results:
                    r['normalized_score'] = (r['score'] - min_score) / (max_score - min_score)

            return results

        # 정규화
        semantic_results = normalize_scores(semantic_results)
        bm25_results = normalize_scores(bm25_results)

        # 문서별 점수 집계
        doc_scores: Dict[str, Dict[str, Any]] = {}

        # Semantic 결과
        for result in semantic_results:
            text = result['text']
            doc_scores[text] = {
                'text': text,
                'metadata': result['metadata'],
                'score': semantic_weight * result['normalized_score'],
                'semantic_score': result['score'],
                'bm25_score': 0,
                'fusion_method': 'weighted_sum'
            }

        # BM25 결과
        for result in bm25_results:
            text = result['text']
            if text in doc_scores:
                doc_scores[text]['score'] += bm25_weight * result['normalized_score']
                doc_scores[text]['bm25_score'] = result['score']
            else:
                doc_scores[text] = {
                    'text': text,
                    'metadata': result['metadata'],
                    'score': bm25_weight * result['normalized_score'],
                    'semantic_score': 0,
                    'bm25_score': result['score'],
                    'fusion_method': 'weighted_sum'
                }

        # 정렬
        sorted_results = sorted(
            doc_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )

        return sorted_results

    def _get_adaptive_weight(self, query: str) -> float:
        """
        쿼리 타입 분석 후 적응형 가중치 결정

        학습 목적:
            쿼리 특성에 따라 Semantic vs BM25 가중치를 자동 조정

            쿼리 타입별 전략:
            1. 조항 번호 (예: "형법 제329조") → BM25 우선 (0.2)
            2. 판례 번호 (예: "2023도1234") → BM25 우선 (0.3)
            3. 의미 질문 (예: "절도죄란?") → Semantic 우선 (0.7)
            4. 복합 질문 (예: "절도죄 제329조") → 균형 (0.5)

        Args:
            query: 검색 쿼리

        Returns:
            Semantic weight (0.0 ~ 1.0)
        """
        # 조항 번호 패턴 (예: 제329조, 제10조의2)
        statute_pattern = re.compile(r'제\s*\d+\s*조')

        # 판례 번호 패턴 (예: 2023도1234, 대법원 2020도5678)
        case_pattern = re.compile(r'\d{4}도\d+')

        # 키워드 패턴 (정확한 법률 용어)
        exact_keywords = ['형법', '형사소송법', '특정범죄가중처벌법', '성폭력처벌법']

        has_statute = bool(statute_pattern.search(query))
        has_case = bool(case_pattern.search(query))
        has_exact_keyword = any(keyword in query for keyword in exact_keywords)

        # 쿼리 길이 (짧은 쿼리 = 키워드 검색에 적합)
        query_length = len(query.split())

        # 가중치 결정
        if has_statute:
            # 조항 번호 → BM25 강화
            semantic_weight = 0.2
            logger.debug(f"Query has statute reference → semantic_weight={semantic_weight}")
        elif has_case:
            # 판례 번호 → BM25 강화
            semantic_weight = 0.3
            logger.debug(f"Query has case reference → semantic_weight={semantic_weight}")
        elif query_length <= 3 and has_exact_keyword:
            # 짧은 키워드 쿼리 → BM25 강화
            semantic_weight = 0.3
            logger.debug(f"Short keyword query → semantic_weight={semantic_weight}")
        elif query_length <= 5:
            # 짧은 쿼리 → 균형
            semantic_weight = 0.4
            logger.debug(f"Short query → semantic_weight={semantic_weight}")
        else:
            # 긴 의미 질문 → Semantic 강화
            semantic_weight = 0.7
            logger.debug(f"Long semantic query → semantic_weight={semantic_weight}")

        return semantic_weight

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        쿼리 분석 (디버깅 및 학습용)

        Returns:
            쿼리 분석 결과 (타입, 가중치, 키워드 등)
        """
        adaptive_weight = self._get_adaptive_weight(query)
        bm25_analysis = self.bm25_index.analyze_query(query)

        return {
            'query': query,
            'adaptive_semantic_weight': adaptive_weight,
            'adaptive_bm25_weight': 1.0 - adaptive_weight,
            'bm25_analysis': bm25_analysis,
            'fusion_method': self.fusion_method,
            'rrf_k': self.rrf_k if self.fusion_method == 'rrf' else None
        }

    def format_context(
        self,
        results: List[Dict[str, Any]],
        max_length: Optional[int] = None
    ) -> str:
        """
        검색 결과를 LLM 컨텍스트 형식으로 변환
        (LegalDocumentRetriever와 호환성 유지)

        Args:
            results: 검색 결과
            max_length: 최대 길이

        Returns:
            포맷된 컨텍스트 문자열
        """
        # 기존 retriever의 format_context 재사용
        return self.semantic_retriever.format_context(results, max_length)

    def get_search_stats(self) -> Dict[str, Any]:
        """검색 시스템 통계"""
        return {
            'semantic_db_count': self.semantic_retriever.vectordb.get_count(),
            'bm25_index_count': self.bm25_index.get_count(),
            'fusion_method': self.fusion_method,
            'default_semantic_weight': self.semantic_weight,
            'adaptive_weighting_enabled': self.enable_adaptive_weighting
        }
