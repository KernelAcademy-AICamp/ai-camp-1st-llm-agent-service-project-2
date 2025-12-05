"""
V2 Criminal Cases Router - 형사 사건 관리 API

형사 사건 CRUD 및 대시보드 API

엔드포인트:
- GET /v2/criminal/cases - 형사 사건 목록 조회
- POST /v2/criminal/cases - 형사 사건 생성
- GET /v2/criminal/cases/{case_id} - 형사 사건 상세 조회
- PATCH /v2/criminal/cases/{case_id} - 형사 사건 수정
- DELETE /v2/criminal/cases/{case_id} - 형사 사건 삭제
- POST /v2/criminal/cases/{case_id}/schedules - 일정 추가
- PATCH /v2/criminal/cases/{case_id}/schedules/{index} - 일정 상태 수정
- GET /v2/criminal/dashboard/summary - 대시보드 요약
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from apps.ai_service.middleware.auth import verify_token
from apps.ai_service.models.database import get_write_db
from apps.ai_service.models.criminal_case import (
    CriminalStage,
    CriminalCaseCreate,
    CriminalCaseUpdate,
    CriminalCaseResponse,
    CriminalCaseListItem,
    CriminalCaseWithAnalysis,
    ScheduleItemCreate,
    DashboardSummary,
)
from apps.ai_service.services.criminal_case_service import CriminalCaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/criminal", tags=["Criminal Cases"])


# ===== 형사 사건 CRUD =====

@router.get("/cases", response_model=List[CriminalCaseListItem])
async def list_criminal_cases(
    stage: Optional[CriminalStage] = Query(None, description="진행 단계 필터"),
    limit: int = Query(50, ge=1, le=100, description="조회 개수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db)
):
    """
    사용자의 형사 사건 목록 조회

    Args:
        stage: 진행 단계 필터 (선택)
        limit: 조회 개수
        offset: 오프셋
        user: 인증된 사용자
        db: DB 세션

    Returns:
        형사 사건 목록
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        service = CriminalCaseService(db)
        cases = await service.list_cases(
            user_id=user_id,
            stage=stage,
            limit=limit,
            offset=offset
        )

        return cases

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list criminal cases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list criminal cases"
        )


@router.post("/cases", response_model=CriminalCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_criminal_case(
    data: CriminalCaseCreate,
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db)
):
    """
    형사 사건 생성

    Args:
        data: 사건 생성 데이터
        user: 인증된 사용자
        db: DB 세션

    Returns:
        생성된 형사 사건
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        service = CriminalCaseService(db)
        case = await service.create_case(
            user_id=user_id,
            data=data
        )

        return case

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create criminal case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create criminal case"
        )


@router.post("/cases/with-analysis", response_model=CriminalCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_criminal_case_with_analysis(
    data: CriminalCaseWithAnalysis,
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db)
):
    """
    분석 결과와 함께 형사 사건 생성

    Args:
        data: 분석 결과가 포함된 사건 생성 데이터
        user: 인증된 사용자
        db: DB 세션

    Returns:
        생성된 형사 사건
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        service = CriminalCaseService(db)
        case = await service.create_case_with_analysis(
            user_id=user_id,
            data=data
        )

        return case

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create criminal case with analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create criminal case"
        )


@router.get("/cases/{case_id}", response_model=CriminalCaseResponse)
async def get_criminal_case(
    case_id: str,
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db)
):
    """
    형사 사건 상세 조회

    Args:
        case_id: 사건 ID
        user: 인증된 사용자
        db: DB 세션

    Returns:
        형사 사건 상세 정보
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        service = CriminalCaseService(db)
        case = await service.get_case(
            case_id=case_id,
            user_id=user_id
        )

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Criminal case not found"
            )

        return case

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get criminal case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get criminal case"
        )


@router.patch("/cases/{case_id}", response_model=CriminalCaseResponse)
async def update_criminal_case(
    case_id: str,
    data: CriminalCaseUpdate,
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db)
):
    """
    형사 사건 수정

    Args:
        case_id: 사건 ID
        data: 수정 데이터
        user: 인증된 사용자
        db: DB 세션

    Returns:
        수정된 형사 사건
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        service = CriminalCaseService(db)
        case = await service.update_case(
            case_id=case_id,
            user_id=user_id,
            data=data
        )

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Criminal case not found"
            )

        return case

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update criminal case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update criminal case"
        )


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_criminal_case(
    case_id: str,
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db)
):
    """
    형사 사건 삭제

    Args:
        case_id: 사건 ID
        user: 인증된 사용자
        db: DB 세션
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        service = CriminalCaseService(db)
        deleted = await service.delete_case(
            case_id=case_id,
            user_id=user_id
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Criminal case not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete criminal case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete criminal case"
        )


# ===== 일정 관리 =====

@router.post("/cases/{case_id}/schedules", response_model=CriminalCaseResponse)
async def add_schedule(
    case_id: str,
    schedule: ScheduleItemCreate,
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db)
):
    """
    일정 추가

    Args:
        case_id: 사건 ID
        schedule: 일정 데이터
        user: 인증된 사용자
        db: DB 세션

    Returns:
        업데이트된 형사 사건
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        service = CriminalCaseService(db)
        case = await service.add_schedule(
            case_id=case_id,
            user_id=user_id,
            schedule=schedule
        )

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Criminal case not found"
            )

        return case

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add schedule to case {case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add schedule"
        )


@router.patch("/cases/{case_id}/schedules/{schedule_index}")
async def update_schedule_status(
    case_id: str,
    schedule_index: int,
    is_completed: bool = Query(..., description="완료 여부"),
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db)
):
    """
    일정 완료 상태 수정

    Args:
        case_id: 사건 ID
        schedule_index: 일정 인덱스
        is_completed: 완료 여부
        user: 인증된 사용자
        db: DB 세션

    Returns:
        업데이트된 형사 사건
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        service = CriminalCaseService(db)
        case = await service.update_schedule_status(
            case_id=case_id,
            user_id=user_id,
            schedule_index=schedule_index,
            is_completed=is_completed
        )

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Criminal case not found"
            )

        return case

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update schedule status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update schedule status"
        )


# ===== 대시보드 =====

@router.get("/dashboard")
async def get_dashboard_cases(
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db)
):
    """
    대시보드용 형사 사건 목록 조회 (전체 상세 정보 포함)

    Args:
        user: 인증된 사용자
        db: DB 세션

    Returns:
        형사 사건 목록 (전체 상세 정보)
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        service = CriminalCaseService(db)
        cases = await service.list_cases_full(
            user_id=user_id,
            limit=100
        )

        return {"cases": cases}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard cases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard cases"
        )


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db)
):
    """
    형사 사건 대시보드 요약

    Args:
        user: 인증된 사용자
        db: DB 세션

    Returns:
        대시보드 요약 데이터
    """
    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        # 대시보드 서비스 사용
        from apps.ai_service.services.criminal_dashboard_service import CriminalDashboardService

        dashboard_service = CriminalDashboardService(db)
        summary = await dashboard_service.get_dashboard_summary(user_id)

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard"
        )


@router.get("/statistics/similar-cases")
async def get_similar_case_statistics(
    crime_type: str = Query(..., description="범죄 유형"),
    conditions: List[str] = Query(default=[], description="조건 태그"),
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db)
):
    """
    유사 사건 통계 조회

    Args:
        crime_type: 범죄 유형
        conditions: 조건 태그 목록
        user: 인증된 사용자
        db: DB 세션

    Returns:
        유사 사건 통계
    """
    try:
        from apps.ai_service.services.criminal_dashboard_service import CriminalDashboardService

        dashboard_service = CriminalDashboardService(db)
        statistics = await dashboard_service.get_similar_case_statistics(
            crime_type=crime_type,
            conditions=conditions
        )

        return statistics

    except Exception as e:
        logger.error(f"Failed to get similar case statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get similar case statistics"
        )
