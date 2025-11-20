"""
Feedback Adapter
데이터베이스 기반 피드백 제공자 (Read-Only)
"""

from typing import Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from models.precedent_feedback import PrecedentFeedbackStats

logger = logging.getLogger(__name__)

class DatabaseFeedbackProvider:
    """
    데이터베이스 기반 피드백 제공자

    Django에서 관리하는 precedent_feedback_stats 테이블을 읽어서
    제외할 판례 ID 목록을 제공합니다.

    Usage:
        provider = DatabaseFeedbackProvider(db)
        excluded_ids = await provider.get_excluded_ids()
        # excluded_ids: {"precedent_id_1", "precedent_id_2", ...}
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_excluded_ids(self) -> Set[str]:
        """
        제외할 판례 ID 조회

        should_exclude=True인 판례 ID를 반환합니다.
        이 판례들은 RAG 검색 결과에서 필터링됩니다.

        Returns:
            제외할 판례 ID 집합
        """
        try:
            result = await self.db.execute(
                select(PrecedentFeedbackStats.precedent_id)
                .where(PrecedentFeedbackStats.should_exclude == True)
            )
            excluded_ids = result.scalars().all()

            if excluded_ids:
                logger.info(f"📊 Loaded {len(excluded_ids)} excluded precedents from DB")
            else:
                logger.debug("📊 No excluded precedents found in DB")

            return set(excluded_ids)

        except Exception as e:
            logger.warning(f"⚠️  Failed to get excluded IDs from DB: {e}")
            logger.info("Continuing without feedback filtering")
            return set()

    async def get_feedback_stats(self, precedent_id: str) -> dict:
        """
        특정 판례의 피드백 통계 조회

        Args:
            precedent_id: 판례 ID

        Returns:
            피드백 통계 dict 또는 None
        """
        try:
            result = await self.db.execute(
                select(PrecedentFeedbackStats)
                .where(PrecedentFeedbackStats.precedent_id == precedent_id)
            )
            stats = result.scalar_one_or_none()

            if stats:
                return {
                    "precedent_id": stats.precedent_id,
                    "total_likes": stats.total_likes,
                    "total_dislikes": stats.total_dislikes,
                    "total_feedback_count": stats.total_feedback_count,
                    "like_ratio": stats.like_ratio,
                    "avg_relevance_score": stats.avg_relevance_score,
                    "should_exclude": stats.should_exclude,
                    "exclusion_threshold": stats.exclusion_threshold,
                    "last_updated": stats.last_updated.isoformat() if stats.last_updated else None
                }
            else:
                return None

        except Exception as e:
            logger.warning(f"⚠️  Failed to get feedback stats for {precedent_id}: {e}")
            return None
