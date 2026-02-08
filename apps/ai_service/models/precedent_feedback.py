"""
Precedent Feedback Model (Read-Only)
Django의 precedent_feedback_stats 테이블 매핑
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float
from datetime import datetime
from .database import Base

class PrecedentFeedbackStats(Base):
    """
    판례 피드백 통계 (Read-Only)

    Django 모델과 동일한 테이블 매핑
    Note: Phase 1.5에서 Raw SQL로 변경 예정
    """
    __tablename__ = "precedent_feedback_stats"

    # Primary key
    precedent_id = Column(String(200), primary_key=True, index=True)

    # Aggregated stats
    total_likes = Column(Integer, default=0, nullable=False)
    total_dislikes = Column(Integer, default=0, nullable=False)
    like_ratio = Column(Float, default=0.0, nullable=False)
    total_feedback_count = Column(Integer, default=0, nullable=False)
    avg_relevance_score = Column(Float, nullable=True)

    # Exclusion flags
    should_exclude = Column(Boolean, default=False, nullable=False, index=True)
    exclusion_threshold = Column(Float, default=0.3, nullable=False)

    # Timestamp
    last_updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<PrecedentFeedbackStats {self.precedent_id} (👍 {self.total_likes} / 👎 {self.total_dislikes})>"
