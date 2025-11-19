"""
Feedback-based filtering for RAG retrieval
사용자 피드백을 기반으로 RAG 검색 결과를 필터링
"""

from typing import List, Dict, Any, Set, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import asyncio

from backend.models.precedent_feedback import PrecedentFeedbackStats


class FeedbackFilter:
    """
    피드백 기반 필터링 클래스

    싫어요가 많이 누적된 판례를 RAG 검색 결과에서 제외
    """

    def __init__(
        self,
        min_feedback_count: int = 5,
        exclusion_threshold: float = 0.3,
        enable_filtering: bool = True
    ):
        """
        Args:
            min_feedback_count: 필터링을 적용할 최소 피드백 수 (기본: 5)
            exclusion_threshold: 제외 임계값 - 좋아요 비율이 이 값 이하면 제외 (기본: 0.3)
            enable_filtering: 필터링 활성화 여부 (기본: True)
        """
        self.min_feedback_count = min_feedback_count
        self.exclusion_threshold = exclusion_threshold
        self.enable_filtering = enable_filtering
        self._excluded_cache: Set[str] = set()
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5분 캐시

    async def get_excluded_precedents(self, db: AsyncSession) -> Set[str]:
        """
        제외할 판례 ID 목록 조회 (캐싱)

        Args:
            db: 데이터베이스 세션

        Returns:
            제외할 판례 ID 집합
        """
        import time
        current_time = time.time()

        # 캐시가 유효하면 캐시된 결과 반환
        if self._excluded_cache and (current_time - self._cache_timestamp) < self._cache_ttl:
            return self._excluded_cache

        try:
            # 제외 대상 판례 조회
            result = await db.execute(
                select(PrecedentFeedbackStats.precedent_id)
                .where(PrecedentFeedbackStats.should_exclude == True)
            )
            excluded_ids = result.scalars().all()

            self._excluded_cache = set(excluded_ids)
            self._cache_timestamp = current_time

            if excluded_ids:
                logger.info(f"Loaded {len(excluded_ids)} excluded precedents from feedback")

            return self._excluded_cache

        except Exception as e:
            logger.warning(f"Failed to load excluded precedents: {e}")
            return set()

    def filter_results(
        self,
        results: List[Dict[str, Any]],
        excluded_ids: Set[str]
    ) -> List[Dict[str, Any]]:
        """
        검색 결과에서 제외 대상 판례 필터링

        Args:
            results: 검색 결과 리스트 (각 항목은 'id' 또는 'source' 필드 포함)
            excluded_ids: 제외할 판례 ID 집합

        Returns:
            필터링된 검색 결과
        """
        if not self.enable_filtering or not excluded_ids:
            return results

        filtered = []
        excluded_count = 0

        for result in results:
            # 결과에서 문서 ID 추출 (여러 가능한 키 확인)
            doc_id = result.get('id') or result.get('source') or result.get('document_id')

            if doc_id and doc_id in excluded_ids:
                excluded_count += 1
                logger.debug(f"Filtered out precedent {doc_id} due to negative feedback")
                continue

            filtered.append(result)

        if excluded_count > 0:
            logger.info(f"Filtered out {excluded_count} precedents based on user feedback")

        return filtered

    async def filter_results_with_db(
        self,
        results: List[Dict[str, Any]],
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        데이터베이스를 사용하여 검색 결과 필터링

        Args:
            results: 검색 결과 리스트
            db: 데이터베이스 세션

        Returns:
            필터링된 검색 결과
        """
        if not self.enable_filtering:
            return results

        excluded_ids = await self.get_excluded_precedents(db)
        return self.filter_results(results, excluded_ids)

    def clear_cache(self):
        """캐시 초기화"""
        self._excluded_cache.clear()
        self._cache_timestamp = 0
        logger.info("Feedback filter cache cleared")


# ============================================
# Standalone Helper Functions
# ============================================

async def get_excluded_precedent_ids(db: AsyncSession) -> Set[str]:
    """
    제외할 판례 ID 목록 조회 (단독 함수)

    Args:
        db: 데이터베이스 세션

    Returns:
        제외할 판례 ID 집합
    """
    try:
        result = await db.execute(
            select(PrecedentFeedbackStats.precedent_id)
            .where(PrecedentFeedbackStats.should_exclude == True)
        )
        excluded_ids = result.scalars().all()
        return set(excluded_ids)

    except Exception as e:
        logger.warning(f"Failed to get excluded precedent IDs: {e}")
        return set()


def apply_feedback_filter(
    results: List[Dict[str, Any]],
    excluded_ids: Set[str],
    id_key: str = 'source'
) -> List[Dict[str, Any]]:
    """
    검색 결과에 피드백 필터 적용 (단독 함수)

    Args:
        results: 검색 결과 리스트
        excluded_ids: 제외할 판례 ID 집합
        id_key: 문서 ID를 가져올 키 이름 (기본: 'source')

    Returns:
        필터링된 검색 결과
    """
    if not excluded_ids:
        return results

    filtered = []
    for result in results:
        doc_id = result.get(id_key)
        if doc_id and doc_id not in excluded_ids:
            filtered.append(result)

    return filtered
