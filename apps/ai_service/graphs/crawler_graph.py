"""
Crawler Workflow Graph

Phase 4 - Week 13: LangGraph 기반 Crawler Workflow

설계 원칙:
- MCP Tools 활용 (fetch_court_api, parse_legal_document, validate_document_structure)
- Checkpointing 필수 (장시간 실행, 서버 재시작 복구, 외부 API 의존)
- Cyclic Retry 패턴 (최대 3회)
- 병렬 처리 지원

워크플로우:
    START → fetch_node → parse_node → validate_node → store_node
                ↓ (실패 시)                              ↓
            retry_node ←─────────────────────────────────
                ↓ (max retry)
              END (failed)

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""

import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from loguru import logger

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from apps.ai_service.workflows.states.crawl_state import (
    CrawlState,
    CrawlStatus,
    DataSource,
    CrawledDocument,
    ProcessingStatus,
    QualityCheck,
    CrawlMetrics,
    create_initial_crawl_state,
)

# MCP Tools import
from apps.ai_service.mcp.tools.external_tools import (
    fetch_court_api,
    fetch_statute_api,
    parse_legal_document,
    validate_document_structure,
)


# =============================================================================
# Constants
# =============================================================================

MAX_RETRY_COUNT = 3
CHECKPOINT_TTL = 24 * 3600  # 24 hours


# =============================================================================
# Node Functions (async)
# =============================================================================

async def fetch_node(state: CrawlState) -> Dict[str, Any]:
    """
    데이터 수집 노드

    MCP Tools를 사용하여 외부 API에서 데이터를 수집합니다.
    - 판례: fetch_court_api
    - 법령: fetch_statute_api

    Returns:
        업데이트된 상태 필드 (raw_content, status, processing_status, error)
    """
    source = state["source"]
    source_url = state.get("source_url")
    crawl_job_id = state["crawl_job_id"]

    logger.info(f"[fetch_node] job_id={crawl_job_id}, source={source}, url={source_url}")

    start_time = time.time()
    completed_tasks = list(state.get("completed_tasks", []))

    try:
        # 상태 업데이트: fetching
        processing_status = ProcessingStatus(
            current_url=source_url,
            current_step="fetch",
            progress_percent=10.0,
        )

        raw_content = None

        if source == DataSource.COURT_PRECEDENT.value:
            # 대법원 판례 API 호출
            # source_url이 키워드 또는 사건번호인 경우 처리
            result = await fetch_court_api(
                keyword=source_url,
                fetch_content=True,
                display=20,
            )

            if result.get("success") and result.get("precedents"):
                # 판례 데이터를 문자열로 변환
                precedents = result["precedents"]
                raw_content = "\n---\n".join([
                    f"사건번호: {p.get('case_number', '')}\n"
                    f"사건명: {p.get('case_name', '')}\n"
                    f"법원: {p.get('court', '')}\n"
                    f"선고일자: {p.get('decision_date', '')}\n"
                    f"내용:\n{p.get('content', '')}"
                    for p in precedents
                ])
                logger.info(f"[fetch_node] Fetched {len(precedents)} precedents")
            else:
                error_msg = result.get("error", "No precedents found")
                logger.warning(f"[fetch_node] Failed to fetch precedents: {error_msg}")
                return {
                    "status": CrawlStatus.FAILED.value,
                    "error": error_msg,
                    "processing_status": processing_status,
                }

        elif source == DataSource.STATUTE.value:
            # 법령 API 호출
            result = await fetch_statute_api(
                keyword=source_url,
                fetch_content=True,
                display=20,
            )

            if result.get("success") and result.get("statutes"):
                statutes = result["statutes"]
                raw_content = "\n---\n".join([
                    f"법령명: {s.get('law_name', '')}\n"
                    f"법령종류: {s.get('law_type', '')}\n"
                    f"소관부처: {s.get('ministry', '')}\n"
                    f"시행일자: {s.get('enforcement_date', '')}\n"
                    f"내용:\n{s.get('content', '')}"
                    for s in statutes
                ])
                logger.info(f"[fetch_node] Fetched {len(statutes)} statutes")
            else:
                error_msg = result.get("error", "No statutes found")
                logger.warning(f"[fetch_node] Failed to fetch statutes: {error_msg}")
                return {
                    "status": CrawlStatus.FAILED.value,
                    "error": error_msg,
                    "processing_status": processing_status,
                }

        else:
            # 지원하지 않는 소스
            return {
                "status": CrawlStatus.FAILED.value,
                "error": f"Unsupported source type: {source}",
                "processing_status": processing_status,
            }

        elapsed = time.time() - start_time
        logger.info(f"[fetch_node] Completed in {elapsed:.2f}s, content_length={len(raw_content or '')}")

        completed_tasks.append("fetch")

        return {
            "raw_content": raw_content,
            "status": CrawlStatus.FETCHING.value,
            "processing_status": ProcessingStatus(
                current_url=source_url,
                current_step="fetch",
                progress_percent=25.0,
            ),
            "completed_tasks": completed_tasks,
            "error": None,
        }

    except Exception as e:
        logger.error(f"[fetch_node] Error: {e}")
        return {
            "status": CrawlStatus.FAILED.value,
            "error": str(e),
            "processing_status": ProcessingStatus(
                current_url=source_url,
                current_step="fetch",
                progress_percent=0.0,
            ),
        }


async def parse_node(state: CrawlState) -> Dict[str, Any]:
    """
    데이터 파싱 노드

    MCP Tool (parse_legal_document)을 사용하여 수집된 데이터를 파싱합니다.

    Returns:
        업데이트된 상태 필드 (parsed_data, status, processing_status)
    """
    raw_content = state.get("raw_content")
    source = state.get("source")
    crawl_job_id = state["crawl_job_id"]

    logger.info(f"[parse_node] job_id={crawl_job_id}")

    completed_tasks = list(state.get("completed_tasks", []))

    if not raw_content:
        logger.warning("[parse_node] No raw content to parse")
        return {
            "status": CrawlStatus.FAILED.value,
            "error": "No raw content to parse",
            "processing_status": ProcessingStatus(
                current_url=state.get("source_url"),
                current_step="parse",
                progress_percent=25.0,
            ),
        }

    try:
        # 문서 타입 결정
        doc_type = "unknown"
        if source == DataSource.COURT_PRECEDENT.value:
            doc_type = "precedent"
        elif source == DataSource.STATUTE.value:
            doc_type = "statute"

        # MCP Tool: parse_legal_document
        result = await parse_legal_document(
            content=raw_content,
            doc_type=doc_type,
        )

        if result.get("success"):
            logger.info(f"[parse_node] Parsed {len(result.get('sections', []))} sections")
            completed_tasks.append("parse")

            return {
                "parsed_data": {
                    "title": result.get("title", ""),
                    "doc_type": result.get("doc_type", doc_type),
                    "sections": result.get("sections", []),
                    "metadata": result.get("metadata", {}),
                },
                "status": CrawlStatus.PARSING.value,
                "processing_status": ProcessingStatus(
                    current_url=state.get("source_url"),
                    current_step="parse",
                    progress_percent=50.0,
                ),
                "completed_tasks": completed_tasks,
                "error": None,
            }
        else:
            error_msg = result.get("error", "Parsing failed")
            logger.warning(f"[parse_node] Parsing failed: {error_msg}")
            return {
                "status": CrawlStatus.FAILED.value,
                "error": error_msg,
                "processing_status": ProcessingStatus(
                    current_url=state.get("source_url"),
                    current_step="parse",
                    progress_percent=25.0,
                ),
            }

    except Exception as e:
        logger.error(f"[parse_node] Error: {e}")
        return {
            "status": CrawlStatus.FAILED.value,
            "error": str(e),
            "processing_status": ProcessingStatus(
                current_url=state.get("source_url"),
                current_step="parse",
                progress_percent=25.0,
            ),
        }


async def validate_node(state: CrawlState) -> Dict[str, Any]:
    """
    데이터 검증 노드

    MCP Tool (validate_document_structure)을 사용하여 파싱된 데이터를 검증합니다.

    Returns:
        업데이트된 상태 필드 (validation_result, quality_check, status)
    """
    parsed_data = state.get("parsed_data")
    source = state.get("source")
    crawl_job_id = state["crawl_job_id"]

    logger.info(f"[validate_node] job_id={crawl_job_id}")

    completed_tasks = list(state.get("completed_tasks", []))

    if not parsed_data:
        logger.warning("[validate_node] No parsed data to validate")
        return {
            "status": CrawlStatus.FAILED.value,
            "error": "No parsed data to validate",
            "processing_status": ProcessingStatus(
                current_url=state.get("source_url"),
                current_step="validate",
                progress_percent=50.0,
            ),
        }

    try:
        # 문서 타입 결정
        doc_type = "document"
        if source == DataSource.COURT_PRECEDENT.value:
            doc_type = "precedent"
        elif source == DataSource.STATUTE.value:
            doc_type = "statute"

        # 검증용 데이터 준비
        validation_data = {
            "title": parsed_data.get("title", ""),
            "content": "\n".join([
                s.get("content", "") for s in parsed_data.get("sections", [])
            ]),
            "doc_type": parsed_data.get("doc_type", doc_type),
        }

        # 판례인 경우 추가 필드
        if doc_type == "precedent":
            validation_data["case_number"] = parsed_data.get("title", "")

        # 법령인 경우 추가 필드
        if doc_type == "statute":
            validation_data["law_name"] = parsed_data.get("title", "")

        # MCP Tool: validate_document_structure
        result = await validate_document_structure(
            data=validation_data,
            doc_type=doc_type,
        )

        # 품질 검사 결과 생성
        is_valid = result.get("valid", False)
        missing_fields = result.get("missing_fields", [])
        warnings = result.get("warnings", [])

        # 데이터 완전성 계산
        total_expected = len(missing_fields) + len(validation_data)
        data_completeness = (total_expected - len(missing_fields)) / max(total_expected, 1)

        quality_check = QualityCheck(
            is_valid=is_valid,
            validation_errors=missing_fields,
            data_completeness=data_completeness,
        )

        logger.info(f"[validate_node] Validation result: valid={is_valid}, completeness={data_completeness:.2f}")

        completed_tasks.append("validate")

        return {
            "validation_result": {
                "valid": is_valid,
                "missing_fields": missing_fields,
                "warnings": warnings,
                "metadata": result.get("metadata", {}),
            },
            "quality_check": quality_check,
            "status": CrawlStatus.VALIDATING.value,
            "processing_status": ProcessingStatus(
                current_url=state.get("source_url"),
                current_step="validate",
                progress_percent=75.0,
            ),
            "completed_tasks": completed_tasks,
            "error": None,
        }

    except Exception as e:
        logger.error(f"[validate_node] Error: {e}")
        return {
            "status": CrawlStatus.FAILED.value,
            "error": str(e),
            "processing_status": ProcessingStatus(
                current_url=state.get("source_url"),
                current_step="validate",
                progress_percent=50.0,
            ),
        }


async def store_node(state: CrawlState) -> Dict[str, Any]:
    """
    데이터 저장 노드

    검증된 데이터를 저장하고 크롤링 결과를 누적합니다.

    Returns:
        업데이트된 상태 필드 (crawled_data, metrics, status)
    """
    crawl_job_id = state["crawl_job_id"]
    source_url = state.get("source_url")
    raw_content = state.get("raw_content")
    parsed_data = state.get("parsed_data")
    validation_result = state.get("validation_result")

    logger.info(f"[store_node] job_id={crawl_job_id}, url={source_url}")

    completed_tasks = list(state.get("completed_tasks", []))
    crawled_data = list(state.get("crawled_data", []))
    metrics = dict(state.get("metrics", {}))

    try:
        # 크롤링된 문서 생성
        crawled_doc = CrawledDocument(
            url=source_url or "",
            raw_content=raw_content,
            parsed_data=parsed_data,
            validation_result=validation_result,
            stored=True,
            error=None,
        )

        crawled_data.append(crawled_doc)

        # 메트릭스 업데이트
        metrics["processed_urls"] = metrics.get("processed_urls", 0) + 1
        metrics["successful_urls"] = metrics.get("successful_urls", 0) + 1
        metrics["end_time"] = datetime.utcnow().isoformat()

        # 진행률 계산
        total_urls = metrics.get("total_urls", 1)
        progress = (metrics["processed_urls"] / total_urls) * 100

        logger.info(f"[store_node] Stored document, progress={progress:.1f}%")

        completed_tasks.append("store")

        return {
            "crawled_data": crawled_data,
            "metrics": CrawlMetrics(
                total_urls=metrics.get("total_urls", 1),
                processed_urls=metrics.get("processed_urls", 1),
                successful_urls=metrics.get("successful_urls", 1),
                failed_urls=metrics.get("failed_urls", 0),
                start_time=metrics.get("start_time"),
                end_time=metrics.get("end_time"),
            ),
            "status": CrawlStatus.COMPLETED.value,
            "processing_status": ProcessingStatus(
                current_url=source_url,
                current_step="store",
                progress_percent=100.0,
            ),
            "completed_tasks": completed_tasks,
            "error": None,
        }

    except Exception as e:
        logger.error(f"[store_node] Error: {e}")
        return {
            "status": CrawlStatus.FAILED.value,
            "error": str(e),
            "processing_status": ProcessingStatus(
                current_url=source_url,
                current_step="store",
                progress_percent=75.0,
            ),
        }


async def retry_node(state: CrawlState) -> Dict[str, Any]:
    """
    재시도 노드

    실패한 작업에 대해 재시도를 수행합니다.
    최대 3회까지 재시도하며, 초과 시 실패 처리합니다.

    Returns:
        업데이트된 상태 필드 (retry_count, needs_retry, status)
    """
    crawl_job_id = state["crawl_job_id"]
    source_url = state.get("source_url")
    retry_count = state.get("retry_count", 0)
    failed_urls = list(state.get("failed_urls", []))
    needs_retry = list(state.get("needs_retry", []))
    metrics = dict(state.get("metrics", {}))

    logger.info(f"[retry_node] job_id={crawl_job_id}, retry_count={retry_count}")

    # 재시도 횟수 증가
    new_retry_count = retry_count + 1

    if new_retry_count >= MAX_RETRY_COUNT:
        # 최대 재시도 횟수 초과
        logger.warning(f"[retry_node] Max retries ({MAX_RETRY_COUNT}) exceeded for {source_url}")

        # 실패 URL 추가
        if source_url and source_url not in failed_urls:
            failed_urls.append(source_url)

        # 메트릭스 업데이트
        metrics["failed_urls"] = metrics.get("failed_urls", 0) + 1
        metrics["end_time"] = datetime.utcnow().isoformat()

        return {
            "retry_count": new_retry_count,
            "failed_urls": failed_urls,
            "needs_retry": [],
            "status": CrawlStatus.FAILED.value,
            "metrics": CrawlMetrics(
                total_urls=metrics.get("total_urls", 1),
                processed_urls=metrics.get("processed_urls", 0),
                successful_urls=metrics.get("successful_urls", 0),
                failed_urls=metrics.get("failed_urls", 1),
                start_time=metrics.get("start_time"),
                end_time=metrics.get("end_time"),
            ),
            "error": f"Max retries exceeded ({MAX_RETRY_COUNT})",
        }

    # 재시도 준비
    logger.info(f"[retry_node] Preparing retry {new_retry_count}/{MAX_RETRY_COUNT}")

    # 재시도 대기 (exponential backoff)
    await asyncio.sleep(1.0 * new_retry_count)

    return {
        "retry_count": new_retry_count,
        "status": CrawlStatus.RETRYING.value,
        "raw_content": None,  # 이전 결과 초기화
        "parsed_data": None,
        "validation_result": None,
        "error": None,
    }


# =============================================================================
# Routing Functions
# =============================================================================

def route_after_fetch(state: CrawlState) -> Literal["parse", "retry"]:
    """
    fetch 후 라우팅

    Returns:
        - "parse": 성공 → 파싱 진행
        - "retry": 실패 → 재시도
    """
    status = state.get("status", "")
    raw_content = state.get("raw_content")

    if status == CrawlStatus.FAILED.value or not raw_content:
        logger.info("[route_after_fetch] → retry")
        return "retry"

    logger.info("[route_after_fetch] → parse")
    return "parse"


def route_after_parse(state: CrawlState) -> Literal["validate", "retry"]:
    """
    parse 후 라우팅

    Returns:
        - "validate": 성공 → 검증 진행
        - "retry": 실패 → 재시도
    """
    status = state.get("status", "")
    parsed_data = state.get("parsed_data")

    if status == CrawlStatus.FAILED.value or not parsed_data:
        logger.info("[route_after_parse] → retry")
        return "retry"

    logger.info("[route_after_parse] → validate")
    return "validate"


def route_after_validate(state: CrawlState) -> Literal["store", "retry"]:
    """
    validate 후 라우팅

    Returns:
        - "store": 성공 → 저장 진행
        - "retry": 실패 → 재시도
    """
    status = state.get("status", "")
    validation_result = state.get("validation_result")
    quality_check = state.get("quality_check")

    # 검증 실패 시 재시도
    if status == CrawlStatus.FAILED.value:
        logger.info("[route_after_validate] → retry (status failed)")
        return "retry"

    # 품질 검사 실패 시에도 저장은 진행 (경고만 기록)
    if quality_check and not quality_check.get("is_valid", True):
        logger.warning("[route_after_validate] Quality check failed, but proceeding to store")

    logger.info("[route_after_validate] → store")
    return "store"


def route_after_retry(state: CrawlState) -> Literal["fetch", "end"]:
    """
    retry 후 라우팅

    Returns:
        - "fetch": 재시도 가능 → fetch로 돌아감
        - "end": 최대 재시도 초과 → 종료
    """
    retry_count = state.get("retry_count", 0)
    status = state.get("status", "")

    if retry_count >= MAX_RETRY_COUNT or status == CrawlStatus.FAILED.value:
        logger.info(f"[route_after_retry] → end (retry_count={retry_count})")
        return "end"

    logger.info(f"[route_after_retry] → fetch (retry #{retry_count})")
    return "fetch"


# =============================================================================
# Workflow Builder
# =============================================================================

def create_crawler_workflow(checkpointer: Optional[Any] = None) -> StateGraph:
    """
    Crawler Workflow StateGraph 생성

    워크플로우:
        START → fetch → parse → validate → store → END
                  ↓        ↓         ↓
                retry ←────┴─────────┘
                  ↓ (max retry)
                 END

    Args:
        checkpointer: Checkpointer 인스턴스 (필수!)

    Returns:
        Compiled StateGraph with checkpointing
    """
    # StateGraph 정의
    workflow = StateGraph(CrawlState)

    # 노드 추가
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("parse", parse_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("store", store_node)
    workflow.add_node("retry", retry_node)

    # 엣지 정의
    workflow.add_edge(START, "fetch")

    # 조건부 분기: fetch 후
    workflow.add_conditional_edges(
        "fetch",
        route_after_fetch,
        {
            "parse": "parse",
            "retry": "retry",
        }
    )

    # 조건부 분기: parse 후
    workflow.add_conditional_edges(
        "parse",
        route_after_parse,
        {
            "validate": "validate",
            "retry": "retry",
        }
    )

    # 조건부 분기: validate 후
    workflow.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "store": "store",
            "retry": "retry",
        }
    )

    # store → END
    workflow.add_edge("store", END)

    # 조건부 분기: retry 후
    workflow.add_conditional_edges(
        "retry",
        route_after_retry,
        {
            "fetch": "fetch",
            "end": END,
        }
    )

    # Checkpointing 필수! (장시간 실행, 서버 재시작 복구)
    if checkpointer is None:
        logger.warning("[create_crawler_workflow] No checkpointer provided! Using MemorySaver (dev mode)")
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


# =============================================================================
# CrawlerWorkflow Class
# =============================================================================

class CrawlerWorkflow:
    """
    Crawler Workflow 실행 클래스

    Checkpointing 필수 워크플로우:
    - 장시간 실행 (수천 개 문서, 수 시간)
    - 서버 재시작 시 복구 가능
    - 외부 API 의존으로 실패율 높음

    사용 예:
        workflow = CrawlerWorkflow()
        result = await workflow.run(
            source=DataSource.COURT_PRECEDENT,
            urls=["절도죄", "사기죄"],
        )

        # 재개 (Checkpointing)
        result = await workflow.resume(thread_id="...")
    """

    def __init__(self, checkpointer: Optional[Any] = None):
        """
        Args:
            checkpointer: Checkpointer 인스턴스
                - MemorySaver: 개발/테스트용
                - RedisSaver: 프로덕션용 (TODO: Week 14에서 구현)
        """
        if checkpointer is None:
            checkpointer = MemorySaver()
            logger.warning("[CrawlerWorkflow] Using MemorySaver (dev mode). Use RedisSaver for production!")

        self.checkpointer = checkpointer
        self.graph = create_crawler_workflow(checkpointer=checkpointer)
        logger.info("[CrawlerWorkflow] Initialized with checkpointing")

    async def run(
        self,
        source: DataSource,
        urls: List[str],
        crawl_job_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crawler Workflow 실행

        Args:
            source: 데이터 소스 타입
            urls: 크롤링할 URL/키워드 목록
            crawl_job_id: 크롤링 작업 ID (자동 생성)
            thread_id: Checkpoint thread ID (재개용)

        Returns:
            {
                "crawl_job_id": str,
                "thread_id": str,
                "status": str,
                "crawled_data": [...],
                "metrics": {...},
                "error": Optional[str],
            }
        """
        crawl_job_id = crawl_job_id or str(uuid.uuid4())
        thread_id = thread_id or f"crawler-{crawl_job_id}"

        logger.info(f"[CrawlerWorkflow] Starting: job_id={crawl_job_id}, source={source.value}, urls={len(urls)}")

        start_time = time.time()
        all_results: List[CrawledDocument] = []
        all_errors: List[str] = []

        # 각 URL에 대해 워크플로우 실행
        for i, url in enumerate(urls):
            url_thread_id = f"{thread_id}-{i}"

            # 초기 상태 생성
            initial_state = create_initial_crawl_state(
                crawl_job_id=crawl_job_id,
                source=source,
                urls_to_crawl=urls,
            )
            # 현재 URL 설정
            initial_state["source_url"] = url

            try:
                # 워크플로우 실행 (비동기)
                config = {"configurable": {"thread_id": url_thread_id}}
                result = await self.graph.ainvoke(initial_state, config=config)

                # 결과 수집
                if result.get("crawled_data"):
                    all_results.extend(result["crawled_data"])

                if result.get("error"):
                    all_errors.append(f"{url}: {result['error']}")

                logger.info(f"[CrawlerWorkflow] Processed {i+1}/{len(urls)}: {url}")

            except Exception as e:
                logger.error(f"[CrawlerWorkflow] Error processing {url}: {e}")
                all_errors.append(f"{url}: {str(e)}")

        processing_time = time.time() - start_time

        # 최종 상태 결정
        final_status = CrawlStatus.COMPLETED.value
        if all_errors and not all_results:
            final_status = CrawlStatus.FAILED.value
        elif all_errors:
            final_status = CrawlStatus.COMPLETED.value  # 부분 성공

        logger.info(f"[CrawlerWorkflow] Completed in {processing_time:.2f}s: "
                   f"success={len(all_results)}, failed={len(all_errors)}")

        return {
            "crawl_job_id": crawl_job_id,
            "thread_id": thread_id,
            "status": final_status,
            "crawled_data": all_results,
            "metrics": {
                "total_urls": len(urls),
                "successful_urls": len(all_results),
                "failed_urls": len(all_errors),
                "processing_time": processing_time,
            },
            "errors": all_errors if all_errors else None,
        }

    async def resume(
        self,
        thread_id: str,
    ) -> Dict[str, Any]:
        """
        중단된 Workflow 재개

        Checkpointing을 통해 중단된 지점부터 재개합니다.

        Args:
            thread_id: Checkpoint thread ID

        Returns:
            Workflow 실행 결과
        """
        logger.info(f"[CrawlerWorkflow] Resuming: thread_id={thread_id}")

        try:
            config = {"configurable": {"thread_id": thread_id}}

            # 마지막 상태 가져오기
            state = await self.graph.aget_state(config)

            if state and state.values:
                logger.info(f"[CrawlerWorkflow] Found checkpoint, resuming from: {state.values.get('status')}")

                # 재개
                result = await self.graph.ainvoke(None, config=config)

                return {
                    "thread_id": thread_id,
                    "status": result.get("status", CrawlStatus.COMPLETED.value),
                    "crawled_data": result.get("crawled_data", []),
                    "metrics": result.get("metrics", {}),
                    "error": result.get("error"),
                }
            else:
                logger.warning(f"[CrawlerWorkflow] No checkpoint found for thread_id={thread_id}")
                return {
                    "thread_id": thread_id,
                    "status": CrawlStatus.FAILED.value,
                    "error": "No checkpoint found",
                }

        except Exception as e:
            logger.error(f"[CrawlerWorkflow] Resume error: {e}")
            return {
                "thread_id": thread_id,
                "status": CrawlStatus.FAILED.value,
                "error": str(e),
            }

    async def get_status(self, thread_id: str) -> Dict[str, Any]:
        """
        Workflow 상태 조회

        Args:
            thread_id: Checkpoint thread ID

        Returns:
            현재 상태 정보
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = await self.graph.aget_state(config)

            if state and state.values:
                return {
                    "thread_id": thread_id,
                    "status": state.values.get("status", "unknown"),
                    "processing_status": state.values.get("processing_status", {}),
                    "metrics": state.values.get("metrics", {}),
                    "retry_count": state.values.get("retry_count", 0),
                    "error": state.values.get("error"),
                }
            else:
                return {
                    "thread_id": thread_id,
                    "status": "not_found",
                    "error": "No state found",
                }

        except Exception as e:
            return {
                "thread_id": thread_id,
                "status": "error",
                "error": str(e),
            }


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "CrawlerWorkflow",
    "create_crawler_workflow",
    "fetch_node",
    "parse_node",
    "validate_node",
    "store_node",
    "retry_node",
]
