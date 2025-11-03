"""
Precedents Router
대법원 판례 관련 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.backend.database import get_db
from app.backend.models.precedent import Precedent
from app.backend.services.precedent_crawler import PrecedentCrawler

import logging

logger = logging.getLogger(__name__)


# ============================================
# Pydantic Models
# ============================================

class PrecedentResponse(BaseModel):
    """판례 응답 모델"""
    id: str
    case_number: str
    title: str
    summary: Optional[str]
    court: str
    decision_date: str
    case_type: str
    specialization_tags: List[str]
    case_link: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class PrecedentDetailResponse(PrecedentResponse):
    """판례 상세 응답 모델"""
    full_text: Optional[str]
    citation: Optional[str]
    updated_at: str


class PrecedentListResponse(BaseModel):
    """판례 목록 응답 모델"""
    total: int
    precedents: List[PrecedentResponse]


# ============================================
# Router Setup Function
# ============================================

def setup_precedent_routes(crawler: Optional[PrecedentCrawler] = None) -> APIRouter:
    """
    Setup precedent-related routes

    Args:
        crawler: PrecedentCrawler instance (optional)

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/precedents", tags=["precedents"])

    @router.get("/recent", response_model=PrecedentListResponse)
    async def get_recent_precedents(
        limit: int = Query(default=10, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        case_type: Optional[str] = Query(default=None),
        db: AsyncSession = Depends(get_db)
    ):
        """
        최근 판례 조회

        Args:
            limit: 조회할 판례 수 (1-100)
            offset: 오프셋
            case_type: 사건 종류 필터 (형사, 민사 등)
            db: Database session

        Returns:
            PrecedentListResponse with recent precedents
        """
        try:
            # 쿼리 구성
            query = select(Precedent).order_by(desc(Precedent.decision_date))

            if case_type:
                query = query.where(Precedent.case_type == case_type)

            # Count 쿼리
            count_result = await db.execute(
                select(Precedent)
            )
            total = len(count_result.scalars().all())

            # 페이지네이션 적용
            query = query.limit(limit).offset(offset)

            result = await db.execute(query)
            precedents = result.scalars().all()

            # 응답 생성
            precedent_responses = [
                PrecedentResponse(
                    id=str(prec.id),
                    case_number=prec.case_number,
                    title=prec.title,
                    summary=prec.summary,
                    court=prec.court,
                    decision_date=prec.decision_date.isoformat(),
                    case_type=prec.case_type,
                    specialization_tags=prec.specialization_tags,
                    case_link=prec.case_link,
                    created_at=prec.created_at.isoformat()
                )
                for prec in precedents
            ]

            return PrecedentListResponse(
                total=total,
                precedents=precedent_responses
            )

        except Exception as e:
            logger.error(f"Error fetching recent precedents: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch precedents")

    @router.get("/{precedent_id}", response_model=PrecedentDetailResponse)
    async def get_precedent_detail(
        precedent_id: str,
        db: AsyncSession = Depends(get_db)
    ):
        """
        판례 상세 조회

        Args:
            precedent_id: Precedent UUID
            db: Database session

        Returns:
            PrecedentDetailResponse with full precedent details
        """
        try:
            result = await db.execute(
                select(Precedent).where(Precedent.id == precedent_id)
            )
            precedent = result.scalars().first()

            if not precedent:
                raise HTTPException(status_code=404, detail="Precedent not found")

            return PrecedentDetailResponse(
                id=str(precedent.id),
                case_number=precedent.case_number,
                title=precedent.title,
                summary=precedent.summary,
                full_text=precedent.full_text,
                court=precedent.court,
                decision_date=precedent.decision_date.isoformat(),
                case_type=precedent.case_type,
                specialization_tags=precedent.specialization_tags,
                citation=precedent.citation,
                case_link=precedent.case_link,
                created_at=precedent.created_at.isoformat(),
                updated_at=precedent.updated_at.isoformat()
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching precedent detail: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch precedent detail")

    @router.get("/search/by-specialization", response_model=PrecedentListResponse)
    async def search_by_specialization(
        specialization: str = Query(..., description="전문분야 (e.g., 형사일반, 성범죄)"),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        db: AsyncSession = Depends(get_db)
    ):
        """
        전문분야별 판례 검색

        Args:
            specialization: 전문분야 태그
            limit: 조회할 판례 수
            offset: 오프셋
            db: Database session

        Returns:
            PrecedentListResponse with matching precedents
        """
        try:
            # SQLite-compatible JSON search using LIKE
            # specialization_tags is stored as JSON string
            query = select(Precedent).where(
                Precedent.specialization_tags.like(f'%"{specialization}"%')
            ).order_by(desc(Precedent.decision_date))

            # Count
            count_result = await db.execute(query)
            total = len(count_result.scalars().all())

            # 페이지네이션
            query = query.limit(limit).offset(offset)

            result = await db.execute(query)
            precedents = result.scalars().all()

            precedent_responses = [
                PrecedentResponse(
                    id=str(prec.id),
                    case_number=prec.case_number,
                    title=prec.title,
                    summary=prec.summary,
                    court=prec.court,
                    decision_date=prec.decision_date.isoformat(),
                    case_type=prec.case_type,
                    specialization_tags=prec.specialization_tags,
                    case_link=prec.case_link,
                    created_at=prec.created_at.isoformat()
                )
                for prec in precedents
            ]

            return PrecedentListResponse(
                total=total,
                precedents=precedent_responses
            )

        except Exception as e:
            logger.error(f"Error searching precedents by specialization: {e}")
            raise HTTPException(status_code=500, detail="Failed to search precedents")

    @router.post("/refresh")
    async def refresh_precedents(
        limit: int = Query(default=10, ge=1, le=100),
        db: AsyncSession = Depends(get_db)
    ):
        """
        판례 수동 갱신 (관리자용)

        Args:
            limit: 조회할 판례 수
            db: Database session

        Returns:
            Success message with count
        """
        if not crawler:
            raise HTTPException(
                status_code=503,
                detail="Crawler service not available"
            )

        try:
            stored_count = await crawler.fetch_and_store_latest(
                db=db,
                limit=limit,
                case_type="형사"
            )

            return JSONResponse(
                content={
                    "message": "Precedents refreshed successfully",
                    "stored_count": stored_count
                }
            )

        except Exception as e:
            logger.error(f"Error refreshing precedents: {e}")
            raise HTTPException(status_code=500, detail="Failed to refresh precedents")

    return router
