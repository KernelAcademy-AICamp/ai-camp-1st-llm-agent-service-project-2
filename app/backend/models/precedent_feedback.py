"""
Precedent Feedback model for user ratings on precedents
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.backend.database import Base


class PrecedentFeedback(Base):
    """
    판례 피드백 모델 - 사용자의 좋아요/싫어요 피드백 저장

    Attributes:
        id: Unique feedback identifier (UUID)
        precedent_id: 판례 문서 ID (vector DB의 document ID)
        user_id: 피드백을 남긴 사용자 ID (선택적, 익명 가능)
        query: 검색 쿼리 (어떤 질문에 대한 결과인지)
        feedback_type: 피드백 타입 ("like" or "dislike")
        is_helpful: True=좋아요, False=싫어요
        relevance_score: 관련성 점수 (1-5, 선택적)
        comment: 피드백 코멘트 (선택적)
        session_id: 세션 ID (익명 사용자 추적용)
        created_at: 피드백 생성 시각
    """

    __tablename__ = "precedent_feedback"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Precedent reference (document ID from vector DB)
    precedent_id = Column(String(200), nullable=False, index=True)

    # User reference (optional, can be anonymous)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)

    # Query context
    query = Column(String(1000), nullable=False)  # 어떤 질문에 대한 결과인지

    # Feedback data
    feedback_type = Column(String(20), nullable=False)  # "like" or "dislike"
    is_helpful = Column(Boolean, nullable=False)  # True=좋아요, False=싫어요
    relevance_score = Column(Integer, nullable=True)  # 1-5 점수 (선택적)
    comment = Column(String(500), nullable=True)  # 피드백 코멘트

    # Session tracking for anonymous users
    session_id = Column(String(100), nullable=True, index=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_precedent_feedback', precedent_id, is_helpful),
        Index('idx_precedent_created', precedent_id, created_at.desc()),
        Index('idx_user_feedback', user_id, created_at.desc()),
    )

    def __repr__(self):
        return f"<PrecedentFeedback(precedent_id='{self.precedent_id}', is_helpful={self.is_helpful})>"

    def to_dict(self):
        """Convert feedback to dictionary"""
        return {
            "id": str(self.id),
            "precedent_id": self.precedent_id,
            "user_id": str(self.user_id) if self.user_id else None,
            "query": self.query,
            "feedback_type": self.feedback_type,
            "is_helpful": self.is_helpful,
            "relevance_score": self.relevance_score,
            "comment": self.comment,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PrecedentFeedbackStats(Base):
    """
    판례 피드백 통계 - 집계된 피드백 정보 (성능 최적화용)

    Attributes:
        precedent_id: 판례 문서 ID (Primary Key)
        total_likes: 총 좋아요 수
        total_dislikes: 총 싫어요 수
        like_ratio: 좋아요 비율 (0.0 ~ 1.0)
        total_feedback_count: 총 피드백 수
        avg_relevance_score: 평균 관련성 점수
        should_exclude: RAG에서 제외할지 여부 (싫어요가 많은 경우)
        exclusion_threshold: 제외 임계값 도달 여부
        last_updated: 마지막 업데이트 시각
    """

    __tablename__ = "precedent_feedback_stats"

    # Primary key (precedent_id)
    precedent_id = Column(String(200), primary_key=True, index=True)

    # Aggregated stats
    total_likes = Column(Integer, default=0, nullable=False)
    total_dislikes = Column(Integer, default=0, nullable=False)
    like_ratio = Column(Float, default=0.0, nullable=False)  # likes / (likes + dislikes)
    total_feedback_count = Column(Integer, default=0, nullable=False)
    avg_relevance_score = Column(Float, nullable=True)

    # Exclusion flags
    should_exclude = Column(Boolean, default=False, nullable=False, index=True)
    exclusion_threshold = Column(Float, default=0.3, nullable=False)  # 좋아요 비율이 이 값 이하면 제외

    # Timestamp
    last_updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<PrecedentFeedbackStats(precedent_id='{self.precedent_id}', like_ratio={self.like_ratio:.2f})>"

    def to_dict(self):
        """Convert stats to dictionary"""
        return {
            "precedent_id": self.precedent_id,
            "total_likes": self.total_likes,
            "total_dislikes": self.total_dislikes,
            "like_ratio": self.like_ratio,
            "total_feedback_count": self.total_feedback_count,
            "avg_relevance_score": self.avg_relevance_score,
            "should_exclude": self.should_exclude,
            "exclusion_threshold": self.exclusion_threshold,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    def update_stats(self, likes: int, dislikes: int, avg_score: float = None):
        """
        통계 업데이트

        Args:
            likes: 좋아요 수
            dislikes: 싫어요 수
            avg_score: 평균 점수
        """
        self.total_likes = likes
        self.total_dislikes = dislikes
        self.total_feedback_count = likes + dislikes

        if self.total_feedback_count > 0:
            self.like_ratio = likes / self.total_feedback_count
        else:
            self.like_ratio = 0.0

        if avg_score is not None:
            self.avg_relevance_score = avg_score

        # 싫어요가 많으면 제외 플래그 설정
        # 최소 5개 이상의 피드백이 있고, 좋아요 비율이 임계값 이하인 경우
        if self.total_feedback_count >= 5 and self.like_ratio <= self.exclusion_threshold:
            self.should_exclude = True
        else:
            self.should_exclude = False

        self.last_updated = datetime.utcnow()
