"""
V2 Crawler Router - LangGraph Based

Phase 4 - Week 13: LangGraph 기반 크롤러 API

특징:
- LangGraph StateGraph 기반 워크플로우
- Checkpointing 필수 (장시간 실행, 서버 재시작 복구)
- MCP Tools 활용 (fetch_court_api, parse_legal_document, validate_document_structure)
- Cyclic Retry 패턴 (최대 3회)
- TTL: 24시간

엔드포인트:
- POST /v2/crawler/start - 크롤링 시작
- POST /v2/crawler/resume - 중단된 크롤링 재개
- GET /v2/crawler/status/{job_id} - 크롤링 상태 조회
- GET /v2/crawler/health - 헬스체크
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uuid

from apps.ai_service.graphs.crawler_graph import CrawlerWorkflow
from apps.ai_service.workflows.states.crawl_state import DataSource, CrawlStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/crawler", tags=["crawler-v2"])


# ===== Request/Response Models =====

class CrawlStartRequest(BaseModel):
    """크롤링 시작 요청"""
    source: str = Field(
        ...,
        description="데이터 소스 (court_precedent, statute, web)"
    )
    keywords: List[str] = Field(
        ...,
        description="크롤링할 키워드 목록",
        min_items=1,
        max_items=100
    )
    crawl_job_id: Optional[str] = Field(
        None,
        description="크롤링 작업 ID (자동 생성)"
    )


class CrawlResumeRequest(BaseModel):
    """크롤링 재개 요청"""
    thread_id: str = Field(..., description="Checkpoint thread ID")


class CrawledDocumentV2(BaseModel):
    """크롤링된 문서 (v2)"""
    url: str
    raw_content: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None
    stored: bool = False
    error: Optional[str] = None


class CrawlMetricsV2(BaseModel):
    """크롤링 메트릭스 (v2)"""
    total_urls: int
    processed_urls: int
    successful_urls: int
    failed_urls: int
    processing_time: Optional[float] = None


class CrawlStartResponse(BaseModel):
    """크롤링 시작 응답"""
    success: bool
    crawl_job_id: str
    thread_id: str
    source: str
    status: str
    crawled_data: List[CrawledDocumentV2] = []
    metrics: CrawlMetricsV2
    errors: Optional[List[str]] = None
    timestamp: str
    version: str = "v2"


class CrawlStatusResponse(BaseModel):
    """크롤링 상태 응답"""
    thread_id: str
    status: str
    processing_status: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    error: Optional[str] = None
    timestamp: str


# ===== API Endpoints =====

@router.post("/start", response_model=CrawlStartResponse)
async def start_crawl(request: CrawlStartRequest):
    """
    크롤링 시작 (v2)

    워크플로우:
    1. fetch_node: 외부 API로부터 데이터 수집
    2. parse_node: 수집된 데이터 파싱
    3. validate_node: 데이터 구조 검증
    4. store_node: 검증된 데이터 저장
    (실패 시 retry_node로 cyclic retry, 최대 3회)

    Args:
        request: 크롤링 시작 요청

    Returns:
        크롤링 결과
    """
    try:
        logger.info(f"[v2/crawler/start] source={request.source}, keywords={len(request.keywords)}")

        # 소스 유효성 검사
        source_map = {
            "court_precedent": DataSource.COURT_PRECEDENT,
            "statute": DataSource.STATUTE,
            "web": DataSource.WEB,
        }

        if request.source not in source_map:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source. Must be one of: {list(source_map.keys())}"
            )

        source = source_map[request.source]

        # 워크플로우 실행
        workflow = CrawlerWorkflow()
        result = await workflow.run(
            source=source,
            urls=request.keywords,
            crawl_job_id=request.crawl_job_id,
        )

        # 응답 생성
        crawled_docs = [
            CrawledDocumentV2(
                url=doc.get("url", ""),
                raw_content=doc.get("raw_content"),
                parsed_data=doc.get("parsed_data"),
                validation_result=doc.get("validation_result"),
                stored=doc.get("stored", False),
                error=doc.get("error"),
            )
            for doc in result.get("crawled_data", [])
        ]

        metrics = result.get("metrics", {})
        return CrawlStartResponse(
            success=result.get("status") == CrawlStatus.COMPLETED.value,
            crawl_job_id=result.get("crawl_job_id", ""),
            thread_id=result.get("thread_id", ""),
            source=request.source,
            status=result.get("status", CrawlStatus.PENDING.value),
            crawled_data=crawled_docs,
            metrics=CrawlMetricsV2(
                total_urls=metrics.get("total_urls", 0),
                processed_urls=metrics.get("processed_urls", 0) or metrics.get("successful_urls", 0) + metrics.get("failed_urls", 0),
                successful_urls=metrics.get("successful_urls", 0),
                failed_urls=metrics.get("failed_urls", 0),
                processing_time=metrics.get("processing_time"),
            ),
            errors=result.get("errors"),
            timestamp=datetime.now().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[v2/crawler/start] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/resume")
async def resume_crawl(request: CrawlResumeRequest):
    """
    중단된 크롤링 재개 (v2)

    Checkpointing을 통해 중단된 지점부터 재개합니다.
    장시간 실행 또는 서버 재시작 후 복구에 사용.

    Args:
        request: 재개 요청 (thread_id)

    Returns:
        크롤링 결과
    """
    try:
        logger.info(f"[v2/crawler/resume] thread_id={request.thread_id}")

        # 워크플로우 재개
        workflow = CrawlerWorkflow()
        result = await workflow.resume(thread_id=request.thread_id)

        # 응답 생성
        crawled_docs = [
            CrawledDocumentV2(
                url=doc.get("url", ""),
                raw_content=doc.get("raw_content"),
                parsed_data=doc.get("parsed_data"),
                validation_result=doc.get("validation_result"),
                stored=doc.get("stored", False),
                error=doc.get("error"),
            )
            for doc in result.get("crawled_data", [])
        ]

        metrics = result.get("metrics", {})

        return {
            "success": result.get("status") != CrawlStatus.FAILED.value,
            "thread_id": result.get("thread_id", request.thread_id),
            "status": result.get("status", CrawlStatus.PENDING.value),
            "crawled_data": [doc.dict() for doc in crawled_docs],
            "metrics": {
                "total_urls": metrics.get("total_urls", 0),
                "successful_urls": metrics.get("successful_urls", 0),
                "failed_urls": metrics.get("failed_urls", 0),
            },
            "error": result.get("error"),
            "timestamp": datetime.now().isoformat(),
            "version": "v2",
        }

    except Exception as e:
        logger.error(f"[v2/crawler/resume] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/status/{job_id}", response_model=CrawlStatusResponse)
async def get_crawl_status(job_id: str):
    """
    크롤링 상태 조회 (v2)

    Checkpointing된 워크플로우 상태 조회

    Args:
        job_id: 크롤링 작업 ID 또는 thread_id

    Returns:
        현재 크롤링 상태
    """
    try:
        logger.info(f"[v2/crawler/status] job_id={job_id}")

        # 워크플로우 인스턴스 생성
        workflow = CrawlerWorkflow()

        # thread_id로 상태 조회
        # job_id가 thread_id의 일부일 수 있으므로 여러 방식으로 시도
        thread_ids_to_try = [
            job_id,
            f"crawler-{job_id}",
            f"crawler-{job_id}-0",
        ]

        for thread_id in thread_ids_to_try:
            status = await workflow.get_status(thread_id)
            if status.get("status") != "not_found":
                return CrawlStatusResponse(
                    thread_id=thread_id,
                    status=status.get("status", "unknown"),
                    processing_status=status.get("processing_status"),
                    metrics=status.get("metrics"),
                    retry_count=status.get("retry_count", 0),
                    error=status.get("error"),
                    timestamp=datetime.now().isoformat(),
                )

        # 찾지 못한 경우
        return CrawlStatusResponse(
            thread_id=job_id,
            status="not_found",
            processing_status=None,
            metrics=None,
            retry_count=0,
            error="No checkpoint found for this job",
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"[v2/crawler/status] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/health")
async def crawler_v2_health():
    """
    Crawler v2 헬스체크

    Returns:
        상태 정보
    """
    try:
        # 워크플로우 초기화 테스트
        workflow = CrawlerWorkflow()

        return {
            "status": "healthy",
            "version": "v2",
            "engine": "LangGraph",
            "workflow": "crawler_workflow",
            "features": [
                "checkpointing",
                "mcp_tools",
                "cyclic_retry",
                "parallel_processing",
            ],
            "supported_sources": [
                "court_precedent",
                "statute",
                "web",
            ],
            "checkpointing": True,
            "checkpoint_ttl": "24 hours",
            "max_retry": 3,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"[health] Error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ===== Background Task Support =====

async def run_crawl_background(
    workflow: CrawlerWorkflow,
    source: DataSource,
    urls: List[str],
    crawl_job_id: str,
):
    """
    백그라운드에서 크롤링 실행

    대량 크롤링 시 사용 (TODO: Week 14에서 구현)
    """
    try:
        logger.info(f"[background] Starting crawl: job_id={crawl_job_id}")
        result = await workflow.run(
            source=source,
            urls=urls,
            crawl_job_id=crawl_job_id,
        )
        logger.info(f"[background] Completed: job_id={crawl_job_id}, status={result.get('status')}")
    except Exception as e:
        logger.error(f"[background] Error: job_id={crawl_job_id}, error={e}")
