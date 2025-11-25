"""
Crawler Router

크롤링 API 엔드포인트
"""
import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import date
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from services.crawler import (
    get_crawler,
    CourtPrecedentCrawler,
    StatuteCrawler,
    WebCrawler,
    CrawlResult
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/crawler", tags=["crawler"])


# Request/Response Models
class CrawlFilters(BaseModel):
    """크롤링 필터 모델"""
    start_date: Optional[str] = Field(None, description="시작 날짜 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="종료 날짜 (YYYY-MM-DD)")
    case_type: Optional[str] = Field(None, description="사건 유형 (민사, 형사 등)")
    keyword: Optional[str] = Field(None, description="검색 키워드")
    law_type: Optional[str] = Field(None, description="법령 종류")


class CrawlRequest(BaseModel):
    """크롤링 요청 모델"""
    data_source_id: str = Field(..., description="데이터 소스 ID")
    job_id: str = Field(..., description="크롤링 작업 ID")
    base_url: Optional[str] = Field(None, description="기본 URL")
    config: Dict[str, Any] = Field(default_factory=dict, description="크롤러 설정")
    filters: CrawlFilters = Field(default_factory=CrawlFilters, description="필터 조건")


class CrawlResponse(BaseModel):
    """크롤링 응답 모델"""
    job_id: str
    status: str
    documents_collected: int
    errors: List[str] = []
    message: str = ""


class JobStatusResponse(BaseModel):
    """작업 상태 응답 모델"""
    job_id: str
    status: str
    documents_collected: int
    errors: List[str] = []
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


# 진행 중인 작업 저장 (메모리 기반, 실제 환경에서는 Redis 등 사용)
_running_jobs: Dict[str, Dict[str, Any]] = {}


async def update_django_job_status(
    job_id: str,
    status: str,
    documents_collected: int = 0,
    errors: List[str] = None
):
    """Django 서버의 CrawlJob 상태 업데이트 (콜백)"""
    # 실제 구현 시 Django API 호출
    logger.info(f"Django 작업 상태 업데이트: job_id={job_id}, status={status}, docs={documents_collected}")

    # Django API 호출 예시 (실제 환경에서 활성화)
    # try:
    #     async with httpx.AsyncClient() as client:
    #         await client.patch(
    #             f"http://localhost:8000/api/v1/crawl-jobs/{job_id}/",
    #             json={
    #                 "status": status,
    #                 "documents_collected": documents_collected,
    #                 "errors": errors or []
    #             }
    #         )
    # except Exception as e:
    #     logger.error(f"Django 상태 업데이트 실패: {e}")


async def run_crawl_task(
    job_id: str,
    source_type: str,
    base_url: str,
    config: Dict[str, Any],
    filters: Dict[str, Any]
):
    """백그라운드 크롤링 작업 실행"""
    try:
        # 작업 상태 업데이트
        _running_jobs[job_id] = {
            "status": "RUNNING",
            "documents_collected": 0,
            "errors": []
        }

        # 크롤러 인스턴스 생성
        crawler = get_crawler(
            source_type=source_type,
            base_url=base_url,
            config=config
        )

        # 크롤링 실행
        result = await crawler.crawl(filters=filters)

        # 결과 저장
        _running_jobs[job_id] = {
            "status": "COMPLETED" if result.success else "FAILED",
            "documents_collected": result.documents_collected,
            "errors": result.errors
        }

        # Django 상태 업데이트
        await update_django_job_status(
            job_id=job_id,
            status="COMPLETED" if result.success else "FAILED",
            documents_collected=result.documents_collected,
            errors=result.errors
        )

        logger.info(f"크롤링 작업 완료: job_id={job_id}, docs={result.documents_collected}")

    except Exception as e:
        logger.error(f"크롤링 작업 실패: job_id={job_id}, error={e}")
        _running_jobs[job_id] = {
            "status": "FAILED",
            "documents_collected": 0,
            "errors": [str(e)]
        }
        await update_django_job_status(
            job_id=job_id,
            status="FAILED",
            documents_collected=0,
            errors=[str(e)]
        )


@router.post("/court-precedents", response_model=CrawlResponse)
async def crawl_court_precedents(
    request: CrawlRequest,
    background_tasks: BackgroundTasks
):
    """
    대법원 판례 크롤링

    대법원 판례 API를 통해 판례 데이터를 수집합니다.

    - **data_source_id**: 데이터 소스 ID
    - **job_id**: 크롤링 작업 ID
    - **filters**: 필터 조건 (start_date, end_date, case_type 등)
    """
    logger.info(f"대법원 판례 크롤링 요청: job_id={request.job_id}")

    # 백그라운드 작업 등록
    background_tasks.add_task(
        run_crawl_task,
        job_id=request.job_id,
        source_type="COURT_API",
        base_url=request.base_url,
        config=request.config,
        filters=request.filters.model_dump(exclude_none=True)
    )

    return CrawlResponse(
        job_id=request.job_id,
        status="RUNNING",
        documents_collected=0,
        message="대법원 판례 크롤링 작업이 시작되었습니다."
    )


@router.post("/statutes", response_model=CrawlResponse)
async def crawl_statutes(
    request: CrawlRequest,
    background_tasks: BackgroundTasks
):
    """
    법령 크롤링

    국가법령정보센터 API를 통해 법령 데이터를 수집합니다.

    - **data_source_id**: 데이터 소스 ID
    - **job_id**: 크롤링 작업 ID
    - **filters**: 필터 조건 (law_type, keyword 등)
    """
    logger.info(f"법령 크롤링 요청: job_id={request.job_id}")

    # 백그라운드 작업 등록
    background_tasks.add_task(
        run_crawl_task,
        job_id=request.job_id,
        source_type="STATUTE_API",
        base_url=request.base_url,
        config=request.config,
        filters=request.filters.model_dump(exclude_none=True)
    )

    return CrawlResponse(
        job_id=request.job_id,
        status="RUNNING",
        documents_collected=0,
        message="법령 크롤링 작업이 시작되었습니다."
    )


@router.post("/web", response_model=CrawlResponse)
async def crawl_web(
    request: CrawlRequest,
    background_tasks: BackgroundTasks
):
    """
    웹 크롤링

    지정된 URL에서 법률 관련 데이터를 수집합니다.

    - **data_source_id**: 데이터 소스 ID
    - **job_id**: 크롤링 작업 ID
    - **base_url**: 크롤링 대상 URL
    - **config**: 크롤러 설정
    """
    logger.info(f"웹 크롤링 요청: job_id={request.job_id}, url={request.base_url}")

    if not request.base_url:
        raise HTTPException(
            status_code=400,
            detail="웹 크롤링에는 base_url이 필요합니다."
        )

    # 백그라운드 작업 등록
    background_tasks.add_task(
        run_crawl_task,
        job_id=request.job_id,
        source_type="WEB_CRAWL",
        base_url=request.base_url,
        config=request.config,
        filters=request.filters.model_dump(exclude_none=True)
    )

    return CrawlResponse(
        job_id=request.job_id,
        status="RUNNING",
        documents_collected=0,
        message="웹 크롤링 작업이 시작되었습니다."
    )


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    크롤링 작업 상태 조회

    - **job_id**: 크롤링 작업 ID
    """
    job_status = _running_jobs.get(job_id)

    if not job_status:
        raise HTTPException(
            status_code=404,
            detail=f"작업을 찾을 수 없습니다: {job_id}"
        )

    return JobStatusResponse(
        job_id=job_id,
        status=job_status.get("status", "UNKNOWN"),
        documents_collected=job_status.get("documents_collected", 0),
        errors=job_status.get("errors", [])
    )


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    크롤링 작업 취소

    - **job_id**: 크롤링 작업 ID
    """
    job_status = _running_jobs.get(job_id)

    if not job_status:
        raise HTTPException(
            status_code=404,
            detail=f"작업을 찾을 수 없습니다: {job_id}"
        )

    if job_status.get("status") not in ["PENDING", "RUNNING"]:
        raise HTTPException(
            status_code=400,
            detail="취소할 수 없는 상태입니다."
        )

    # 상태 업데이트
    _running_jobs[job_id]["status"] = "CANCELLED"

    await update_django_job_status(
        job_id=job_id,
        status="CANCELLED",
        documents_collected=job_status.get("documents_collected", 0)
    )

    return {
        "job_id": job_id,
        "status": "CANCELLED",
        "message": "작업이 취소되었습니다."
    }


@router.get("/health")
async def crawler_health():
    """크롤러 서비스 헬스 체크"""
    return {
        "status": "healthy",
        "service": "crawler",
        "running_jobs": len(_running_jobs),
        "supported_types": ["COURT_API", "STATUTE_API", "WEB_CRAWL"]
    }
