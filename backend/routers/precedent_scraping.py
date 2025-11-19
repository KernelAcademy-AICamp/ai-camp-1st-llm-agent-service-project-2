"""
Precedent Scraping API Router
대법원 포털 스크래핑 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel, Field
import logging

from backend.database import get_db
from backend.models.precedent import Precedent
from backend.services.scourt_playwright_client import ScourtPlaywrightClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/precedents", tags=["precedent-scraping"])


# ============================================
# Pydantic Models
# ============================================

class FetchLatestRequest(BaseModel):
    """최신 판례 가져오기 요청"""
    limit: int = Field(default=10, ge=1, le=10, description="최대 10건")


class SearchKeywordRequest(BaseModel):
    """키워드 검색 요청"""
    keyword: str = Field(..., min_length=1, description="검색 키워드")
    limit: int = Field(default=10, ge=1, le=10, description="최대 10건")


class FetchLatestResponse(BaseModel):
    """최신 판례 가져오기 응답"""
    success: bool
    message: str
    fetched_count: int
    stored_count: int
    precedents: list


# ============================================
# API Endpoints
# ============================================

@router.post("/fetch-latest", response_model=FetchLatestResponse)
async def fetch_latest_precedents(
    request: FetchLatestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    대법원 포털에서 최신 판례 가져오기 (최대 10건)

    Features:
    - Rate limited (1 request per second)
    - Maximum 10 precedents per request
    - Automatic deduplication
    - Timeout protection

    Args:
        request: FetchLatestRequest with keyword and limit
        db: Database session

    Returns:
        FetchLatestResponse with fetched precedents
    """
    try:
        logger.info(f"Fetching latest precedents, limit: {request.limit}")

        # Hard limit enforcement
        if request.limit > 10:
            request.limit = 10
            logger.warning("Limit exceeded 10, capping at 10")

        # Initialize Playwright client
        async with ScourtPlaywrightClient() as client:
            # Fetch precedents from Supreme Court portal
            precedents_data = await client.fetch_latest_precedents(
                max_count=request.limit
            )

            if not precedents_data:
                return FetchLatestResponse(
                    success=False,
                    message="No precedents found",
                    fetched_count=0,
                    stored_count=0,
                    precedents=[]
                )

            stored_count = 0
            stored_precedents = []

            # Store precedents in database
            for prec_data in precedents_data:
                try:
                    # Check for duplicates
                    existing = await db.execute(
                        select(Precedent).where(
                            Precedent.case_number == prec_data["case_number"]
                        )
                    )
                    if existing.scalars().first():
                        logger.debug(f"Precedent {prec_data['case_number']} already exists, skipping")
                        continue

                    # Create new precedent
                    precedent = Precedent(
                        case_number=prec_data["case_number"],
                        title=prec_data["title"],
                        summary=prec_data.get("summary", ""),
                        full_text=None,  # Will be fetched on demand
                        judgment_summary=None,
                        reference_statutes=[],
                        reference_precedents=[],
                        precedent_id=prec_data.get("precedent_id", ""),
                        court=prec_data.get("court", "대법원"),
                        decision_date=prec_data["decision_date"],
                        case_type="형사",
                        specialization_tags=["형사일반"],
                        case_link=f"https://portal.scourt.go.kr/pgp/main.on?jisCntntsSrno={prec_data.get('precedent_id', '')}" if prec_data.get('precedent_id') else None,
                    )

                    db.add(precedent)
                    stored_count += 1
                    stored_precedents.append({
                        "case_number": precedent.case_number,
                        "title": precedent.title,
                        "court": precedent.court,
                        "decision_date": precedent.decision_date.isoformat(),
                    })

                except Exception as e:
                    logger.error(f"Error storing precedent {prec_data.get('case_number')}: {e}")
                    continue

            # Commit all changes
            await db.commit()

            logger.info(f"Successfully fetched {len(precedents_data)} and stored {stored_count} precedents")

            return FetchLatestResponse(
                success=True,
                message=f"Successfully fetched {len(precedents_data)} precedents, stored {stored_count} new ones",
                fetched_count=len(precedents_data),
                stored_count=stored_count,
                precedents=stored_precedents
            )

    except Exception as e:
        logger.error(f"Error in fetch_latest_precedents: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch precedents: {str(e)}"
        )


@router.post("/fetch-latest-background")
async def fetch_latest_precedents_background(
    background_tasks: BackgroundTasks,
    request: FetchLatestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    백그라운드에서 최신 판례 가져오기

    Args:
        background_tasks: FastAPI background tasks
        request: FetchLatestRequest
        db: Database session

    Returns:
        Immediate response with task status
    """
    background_tasks.add_task(
        _fetch_and_store_background,
        request.limit
    )

    return JSONResponse(
        content={
            "success": True,
            "message": "Precedent fetching started in background",
            "status": "processing"
        }
    )


async def _fetch_and_store_background(limit: int):
    """Background task for fetching precedents"""
    try:
        from backend.database import get_async_session

        async with get_async_session() as db:
            async with ScourtPlaywrightClient() as client:
                precedents_data = await client.fetch_latest_precedents(
                    max_count=limit
                )

                for prec_data in precedents_data:
                    try:
                        existing = await db.execute(
                            select(Precedent).where(
                                Precedent.case_number == prec_data["case_number"]
                            )
                        )
                        if existing.scalars().first():
                            continue

                        precedent = Precedent(
                            case_number=prec_data["case_number"],
                            title=prec_data["title"],
                            summary=prec_data.get("summary", ""),
                            precedent_id=prec_data.get("precedent_id", ""),
                            court=prec_data.get("court", "대법원"),
                            decision_date=prec_data["decision_date"],
                            case_type="형사",
                            specialization_tags=["형사일반"],
                            case_link=f"https://portal.scourt.go.kr/pgp/main.on?jisCntntsSrno={prec_data.get('precedent_id', '')}",
                        )

                        db.add(precedent)

                    except Exception as e:
                        logger.error(f"Error in background task: {e}")
                        continue

                await db.commit()
                logger.info(f"Background task completed: fetched {len(precedents_data)} precedents")

    except Exception as e:
        logger.error(f"Background task failed: {e}")


@router.post("/search-keyword", response_model=FetchLatestResponse)
async def search_precedents_by_keyword(
    request: SearchKeywordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    키워드로 대법원 최신 판례 10개 검색

    Features:
    - Rate limited (1 request per second)
    - Maximum 10 precedents per request
    - Automatic deduplication
    - Timeout protection

    Args:
        request: SearchKeywordRequest with keyword and limit
        db: Database session

    Returns:
        FetchLatestResponse with fetched precedents
    """
    try:
        logger.info(f"Searching precedents with keyword: {request.keyword}, limit: {request.limit}")

        # Hard limit enforcement
        if request.limit > 10:
            request.limit = 10
            logger.warning("Limit exceeded 10, capping at 10")

        # Initialize Playwright client
        async with ScourtPlaywrightClient() as client:
            # Search precedents from Supreme Court portal
            precedents_data = await client.search_precedents_by_keyword(
                keyword=request.keyword,
                max_count=request.limit
            )

            if not precedents_data:
                return FetchLatestResponse(
                    success=False,
                    message=f"'{request.keyword}' 키워드로 검색된 판례가 없습니다",
                    fetched_count=0,
                    stored_count=0,
                    precedents=[]
                )

            stored_count = 0
            stored_precedents = []

            # Store precedents in database
            for prec_data in precedents_data:
                try:
                    # Check for duplicates
                    existing = await db.execute(
                        select(Precedent).where(
                            Precedent.case_number == prec_data["case_number"]
                        )
                    )
                    if existing.scalars().first():
                        logger.debug(f"Precedent {prec_data['case_number']} already exists, skipping")
                        continue

                    # Create new precedent
                    precedent = Precedent(
                        case_number=prec_data["case_number"],
                        title=prec_data["title"],
                        summary=prec_data.get("summary", ""),
                        full_text=None,  # Will be fetched on demand
                        judgment_summary=None,
                        reference_statutes=[],
                        reference_precedents=[],
                        precedent_id=prec_data.get("precedent_id", ""),
                        court=prec_data.get("court", "대법원"),
                        decision_date=prec_data["decision_date"],
                        case_type="형사",
                        specialization_tags=["형사일반"],
                        case_link=f"https://portal.scourt.go.kr/pgp/main.on?jisCntntsSrno={prec_data.get('precedent_id', '')}" if prec_data.get('precedent_id') else None,
                    )

                    db.add(precedent)
                    stored_count += 1
                    stored_precedents.append({
                        "case_number": precedent.case_number,
                        "title": precedent.title,
                        "court": precedent.court,
                        "decision_date": precedent.decision_date.isoformat(),
                    })

                except Exception as e:
                    logger.error(f"Error storing precedent {prec_data.get('case_number')}: {e}")
                    continue

            # Commit all changes
            await db.commit()

            logger.info(f"Successfully fetched {len(precedents_data)} and stored {stored_count} precedents for keyword '{request.keyword}'")

            return FetchLatestResponse(
                success=True,
                message=f"'{request.keyword}' 키워드로 {len(precedents_data)}건 조회, {stored_count}건 저장",
                fetched_count=len(precedents_data),
                stored_count=stored_count,
                precedents=stored_precedents
            )

    except Exception as e:
        logger.error(f"Error in search_precedents_by_keyword: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search precedents: {str(e)}"
        )


@router.get("/scraping-status")
async def get_scraping_status():
    """
    스크래핑 상태 조회

    Returns:
        Current scraping status
    """
    # TODO: Implement proper status tracking with Redis or database
    return JSONResponse(
        content={
            "status": "idle",
            "message": "No active scraping tasks"
        }
    )
