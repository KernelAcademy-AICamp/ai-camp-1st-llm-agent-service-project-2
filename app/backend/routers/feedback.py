"""
Precedent Feedback API Router
판례 피드백 관련 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import uuid

from app.backend.database import get_db
from app.backend.models.precedent_feedback import PrecedentFeedback, PrecedentFeedbackStats


# ============================================
# Request/Response Models
# ============================================

class FeedbackRequest(BaseModel):
    """피드백 제출 요청"""
    precedent_id: str = Field(..., description="판례 문서 ID (vector DB document ID)")
    query: str = Field(..., description="검색 쿼리")
    feedback_type: str = Field(..., description="피드백 타입 (like/dislike)")
    is_helpful: bool = Field(..., description="도움이 되었는지 (True=좋아요, False=싫어요)")
    relevance_score: Optional[int] = Field(None, ge=1, le=5, description="관련성 점수 (1-5)")
    comment: Optional[str] = Field(None, max_length=500, description="피드백 코멘트")
    user_id: Optional[str] = Field(None, description="사용자 ID (로그인한 경우)")
    session_id: Optional[str] = Field(None, description="세션 ID (익명 사용자)")


class FeedbackResponse(BaseModel):
    """피드백 응답"""
    id: str
    precedent_id: str
    feedback_type: str
    is_helpful: bool
    created_at: str
    message: str


class FeedbackStatsResponse(BaseModel):
    """피드백 통계 응답"""
    precedent_id: str
    total_likes: int
    total_dislikes: int
    like_ratio: float
    total_feedback_count: int
    avg_relevance_score: Optional[float]
    should_exclude: bool


class PrecedentWithFeedback(BaseModel):
    """피드백 포함 판례 정보"""
    precedent_id: str
    title: Optional[str]
    feedback_stats: Optional[FeedbackStatsResponse]


# ============================================
# Router Setup
# ============================================

def setup_feedback_routes() -> APIRouter:
    """피드백 라우터 설정"""
    router = APIRouter(prefix="/api/feedback", tags=["feedback"])

    @router.post("/submit", response_model=FeedbackResponse)
    async def submit_feedback(
        feedback: FeedbackRequest,
        db: AsyncSession = Depends(get_db)
    ):
        """
        판례에 대한 피드백 제출

        - **precedent_id**: 판례 문서 ID
        - **query**: 검색 쿼리
        - **feedback_type**: "like" 또는 "dislike"
        - **is_helpful**: True(좋아요) 또는 False(싫어요)
        - **relevance_score**: 선택적, 1-5점
        - **comment**: 선택적 코멘트
        """
        try:
            # 피드백 타입 검증
            if feedback.feedback_type not in ["like", "dislike"]:
                raise HTTPException(status_code=400, detail="Invalid feedback_type. Must be 'like' or 'dislike'")

            # 사용자 ID 변환 (문자열 -> UUID)
            user_uuid = None
            if feedback.user_id:
                try:
                    user_uuid = uuid.UUID(feedback.user_id)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid user_id format")

            # 피드백 생성
            new_feedback = PrecedentFeedback(
                precedent_id=feedback.precedent_id,
                user_id=user_uuid,
                query=feedback.query,
                feedback_type=feedback.feedback_type,
                is_helpful=feedback.is_helpful,
                relevance_score=feedback.relevance_score,
                comment=feedback.comment,
                session_id=feedback.session_id
            )

            db.add(new_feedback)
            await db.commit()
            await db.refresh(new_feedback)

            # 통계 업데이트 (비동기 태스크)
            await update_feedback_stats(db, feedback.precedent_id)

            return FeedbackResponse(
                id=str(new_feedback.id),
                precedent_id=new_feedback.precedent_id,
                feedback_type=new_feedback.feedback_type,
                is_helpful=new_feedback.is_helpful,
                created_at=new_feedback.created_at.isoformat(),
                message="피드백이 성공적으로 제출되었습니다."
            )

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"피드백 제출 실패: {str(e)}")

    @router.get("/stats/{precedent_id}", response_model=FeedbackStatsResponse)
    async def get_feedback_stats(
        precedent_id: str,
        db: AsyncSession = Depends(get_db)
    ):
        """
        특정 판례의 피드백 통계 조회

        - **precedent_id**: 판례 문서 ID
        """
        try:
            # 통계 조회
            result = await db.execute(
                select(PrecedentFeedbackStats).where(
                    PrecedentFeedbackStats.precedent_id == precedent_id
                )
            )
            stats = result.scalar_one_or_none()

            if not stats:
                # 통계가 없으면 빈 통계 반환
                return FeedbackStatsResponse(
                    precedent_id=precedent_id,
                    total_likes=0,
                    total_dislikes=0,
                    like_ratio=0.0,
                    total_feedback_count=0,
                    avg_relevance_score=None,
                    should_exclude=False
                )

            return FeedbackStatsResponse(
                precedent_id=stats.precedent_id,
                total_likes=stats.total_likes,
                total_dislikes=stats.total_dislikes,
                like_ratio=stats.like_ratio,
                total_feedback_count=stats.total_feedback_count,
                avg_relevance_score=stats.avg_relevance_score,
                should_exclude=stats.should_exclude
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

    @router.get("/excluded", response_model=List[str])
    async def get_excluded_precedents(
        db: AsyncSession = Depends(get_db),
        limit: int = Query(100, ge=1, le=1000)
    ):
        """
        RAG에서 제외해야 할 판례 목록 조회 (싫어요가 많은 판례)

        - **limit**: 최대 반환 개수
        """
        try:
            result = await db.execute(
                select(PrecedentFeedbackStats.precedent_id)
                .where(PrecedentFeedbackStats.should_exclude == True)
                .limit(limit)
            )
            excluded_ids = result.scalars().all()
            return list(excluded_ids)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"제외 목록 조회 실패: {str(e)}")

    @router.get("/user/{user_id}", response_model=List[dict])
    async def get_user_feedback(
        user_id: str,
        db: AsyncSession = Depends(get_db),
        limit: int = Query(50, ge=1, le=200)
    ):
        """
        사용자의 피드백 이력 조회

        - **user_id**: 사용자 ID
        - **limit**: 최대 반환 개수
        """
        try:
            # UUID 변환
            user_uuid = uuid.UUID(user_id)

            result = await db.execute(
                select(PrecedentFeedback)
                .where(PrecedentFeedback.user_id == user_uuid)
                .order_by(PrecedentFeedback.created_at.desc())
                .limit(limit)
            )
            feedbacks = result.scalars().all()

            return [feedback.to_dict() for feedback in feedbacks]

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"피드백 이력 조회 실패: {str(e)}")

    @router.delete("/{feedback_id}")
    async def delete_feedback(
        feedback_id: str,
        db: AsyncSession = Depends(get_db)
    ):
        """
        피드백 삭제 (사용자가 자신의 피드백을 취소하는 경우)

        - **feedback_id**: 피드백 ID
        """
        try:
            # UUID 변환
            fb_uuid = uuid.UUID(feedback_id)

            result = await db.execute(
                select(PrecedentFeedback).where(PrecedentFeedback.id == fb_uuid)
            )
            feedback = result.scalar_one_or_none()

            if not feedback:
                raise HTTPException(status_code=404, detail="피드백을 찾을 수 없습니다.")

            precedent_id = feedback.precedent_id
            await db.delete(feedback)
            await db.commit()

            # 통계 업데이트
            await update_feedback_stats(db, precedent_id)

            return {"message": "피드백이 삭제되었습니다.", "feedback_id": feedback_id}

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid feedback_id format")
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"피드백 삭제 실패: {str(e)}")

    return router


# ============================================
# Helper Functions
# ============================================

async def update_feedback_stats(db: AsyncSession, precedent_id: str):
    """
    판례의 피드백 통계 업데이트

    Args:
        db: 데이터베이스 세션
        precedent_id: 판례 문서 ID
    """
    try:
        # 좋아요/싫어요 개수 집계
        likes_result = await db.execute(
            select(func.count(PrecedentFeedback.id))
            .where(
                and_(
                    PrecedentFeedback.precedent_id == precedent_id,
                    PrecedentFeedback.is_helpful == True
                )
            )
        )
        total_likes = likes_result.scalar() or 0

        dislikes_result = await db.execute(
            select(func.count(PrecedentFeedback.id))
            .where(
                and_(
                    PrecedentFeedback.precedent_id == precedent_id,
                    PrecedentFeedback.is_helpful == False
                )
            )
        )
        total_dislikes = dislikes_result.scalar() or 0

        # 평균 점수 계산
        avg_score_result = await db.execute(
            select(func.avg(PrecedentFeedback.relevance_score))
            .where(
                and_(
                    PrecedentFeedback.precedent_id == precedent_id,
                    PrecedentFeedback.relevance_score.isnot(None)
                )
            )
        )
        avg_score = avg_score_result.scalar()

        # 통계 레코드 조회 또는 생성
        stats_result = await db.execute(
            select(PrecedentFeedbackStats).where(
                PrecedentFeedbackStats.precedent_id == precedent_id
            )
        )
        stats = stats_result.scalar_one_or_none()

        if stats:
            # 기존 통계 업데이트
            stats.update_stats(total_likes, total_dislikes, avg_score)
        else:
            # 새 통계 생성
            stats = PrecedentFeedbackStats(precedent_id=precedent_id)
            stats.update_stats(total_likes, total_dislikes, avg_score)
            db.add(stats)

        await db.commit()

    except Exception as e:
        await db.rollback()
        # 통계 업데이트 실패는 피드백 제출 자체를 실패시키지 않음
        print(f"Warning: Failed to update feedback stats for {precedent_id}: {e}")
