"""
Crawl State

Phase 4 - Week 13: 크롤러 워크플로우 상태 정의

크롤러 워크플로우:
1. fetch_node: 외부 API로부터 데이터 수집
2. parse_node: 수집된 데이터 파싱
3. validate_node: 데이터 구조 검증
4. store_node: 검증된 데이터 저장

Checkpointing: 필수 (장시간 실행, 서버 재시작 복구, TTL: 24시간)
Retry: 최대 3회 (cyclic retry pattern)
"""

from typing import TypedDict, List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class DataSource(str, Enum):
    """데이터 소스 유형"""
    COURT_PRECEDENT = "court_precedent"  # 대법원 판례
    STATUTE = "statute"                   # 법령
    WEB = "web"                           # 웹 크롤링


class CrawlStatus(str, Enum):
    """크롤링 상태"""
    PENDING = "pending"          # 대기 중
    FETCHING = "fetching"        # 데이터 수집 중
    PARSING = "parsing"          # 파싱 중
    VALIDATING = "validating"    # 검증 중
    STORING = "storing"          # 저장 중
    COMPLETED = "completed"      # 완료
    FAILED = "failed"            # 실패
    RETRYING = "retrying"        # 재시도 중


class CrawlMetrics(TypedDict):
    """크롤링 메트릭스"""
    total_urls: int
    processed_urls: int
    successful_urls: int
    failed_urls: int
    start_time: Optional[str]  # ISO format datetime
    end_time: Optional[str]    # ISO format datetime


class CrawledDocument(TypedDict):
    """크롤링된 문서 데이터"""
    url: str
    raw_content: Optional[str]
    parsed_data: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    stored: bool
    error: Optional[str]


class ProcessingStatus(TypedDict):
    """처리 상태 정보"""
    current_url: Optional[str]
    current_step: str  # fetch, parse, validate, store
    progress_percent: float


class QualityCheck(TypedDict):
    """품질 검사 결과"""
    is_valid: bool
    validation_errors: List[str]
    data_completeness: float  # 0.0 ~ 1.0


class CrawlState(TypedDict):
    """
    크롤러 워크플로우 상태 (Checkpointing 필수)

    장시간 실행되는 크롤링 작업을 위한 상태 관리.
    서버 재시작 시 복구 가능하도록 Checkpointing 필수.

    Attributes:
        crawl_job_id: 크롤링 작업 ID (UUID)
        source: 데이터 소스 유형
        source_url: 현재 처리 중인 URL
        urls_to_crawl: 크롤링할 URL 목록
        crawled_data: 크롤링된 문서 데이터 목록
        failed_urls: 실패한 URL 목록
        processing_status: 현재 처리 상태
        quality_check: 품질 검사 결과
        needs_retry: 재시도가 필요한 URL 목록
        retry_count: 현재 재시도 횟수 (최대 3회)
        raw_content: 현재 문서의 원본 콘텐츠
        parsed_data: 현재 문서의 파싱된 데이터
        validation_result: 현재 문서의 검증 결과
        status: 전체 크롤링 상태
        metrics: 크롤링 메트릭스
        error: 에러 메시지 (있는 경우)
        completed_tasks: 완료된 작업 목록
    """
    # Job identification
    crawl_job_id: str
    source: str  # DataSource value

    # URL management
    source_url: Optional[str]
    urls_to_crawl: List[str]
    failed_urls: List[str]
    needs_retry: List[str]

    # Document processing (current document)
    raw_content: Optional[str]
    parsed_data: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]

    # Accumulated results
    crawled_data: List[CrawledDocument]

    # Status tracking
    processing_status: ProcessingStatus
    quality_check: Optional[QualityCheck]
    status: str  # CrawlStatus value

    # Retry management (cyclic, max 3)
    retry_count: int

    # Metrics and completion
    metrics: CrawlMetrics
    completed_tasks: List[str]
    error: Optional[str]


def create_initial_crawl_state(
    crawl_job_id: str,
    source: DataSource,
    urls_to_crawl: List[str],
) -> CrawlState:
    """
    초기 크롤링 상태 생성

    Args:
        crawl_job_id: 크롤링 작업 ID
        source: 데이터 소스 유형
        urls_to_crawl: 크롤링할 URL 목록

    Returns:
        초기화된 CrawlState
    """
    return CrawlState(
        crawl_job_id=crawl_job_id,
        source=source.value,
        source_url=urls_to_crawl[0] if urls_to_crawl else None,
        urls_to_crawl=urls_to_crawl,
        failed_urls=[],
        needs_retry=[],
        raw_content=None,
        parsed_data=None,
        validation_result=None,
        crawled_data=[],
        processing_status=ProcessingStatus(
            current_url=urls_to_crawl[0] if urls_to_crawl else None,
            current_step="fetch",
            progress_percent=0.0,
        ),
        quality_check=None,
        status=CrawlStatus.PENDING.value,
        retry_count=0,
        metrics=CrawlMetrics(
            total_urls=len(urls_to_crawl),
            processed_urls=0,
            successful_urls=0,
            failed_urls=0,
            start_time=datetime.utcnow().isoformat(),
            end_time=None,
        ),
        completed_tasks=[],
        error=None,
    )
