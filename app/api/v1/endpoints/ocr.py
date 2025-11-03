"""
OCR 작업 관리 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Path as PathParam
from typing import Dict
import logging
from datetime import datetime

from app.schemas import OCRJobStatus, OCRStatus, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# 임시 작업 저장소 (실제로는 Redis나 데이터베이스 사용)
JOB_STORAGE: Dict[str, OCRJobStatus] = {}


@router.get(
    "/ocr/jobs/{job_id}",
    response_model=OCRJobStatus,
    summary="OCR 작업 상태 조회",
    description="OCR 작업의 현재 상태를 조회합니다.",
    responses={
        200: {"description": "조회 성공"},
        404: {"model": ErrorResponse, "description": "작업을 찾을 수 없음"}
    }
)
async def get_ocr_job_status(
    job_id: str = PathParam(..., description="OCR 작업 ID")
):
    """
    OCR 작업 상태 조회

    - **job_id**: OCR 작업 ID
    - 실시간으로 작업 진행 상황을 확인할 수 있습니다
    """

    # TODO: Celery task 상태 조회
    # from celery.result import AsyncResult
    # task = AsyncResult(job_id)
    # return task.state, task.info

    if job_id in JOB_STORAGE:
        return JOB_STORAGE[job_id]

    # 임시: 완료된 작업으로 가정
    return OCRJobStatus(
        job_id=job_id,
        document_id="unknown",
        status=OCRStatus.COMPLETED,
        progress=100.0,
        total_pages=None,
        processed_pages=0,
        current_page=None,
        average_confidence=None,
        error_message=None,
        started_at=None,
        completed_at=datetime.now()
    )


@router.post(
    "/ocr/jobs/{job_id}/cancel",
    summary="OCR 작업 취소",
    description="진행 중인 OCR 작업을 취소합니다.",
    responses={
        200: {"description": "취소 성공"},
        404: {"model": ErrorResponse, "description": "작업을 찾을 수 없음"},
        400: {"model": ErrorResponse, "description": "취소할 수 없는 상태"}
    }
)
async def cancel_ocr_job(
    job_id: str = PathParam(..., description="OCR 작업 ID")
):
    """
    OCR 작업 취소

    - **job_id**: OCR 작업 ID
    - pending 또는 processing 상태의 작업만 취소 가능합니다
    """

    # TODO: Celery task 취소
    # from celery.result import AsyncResult
    # task = AsyncResult(job_id)
    # task.revoke(terminate=True)

    if job_id in JOB_STORAGE:
        job = JOB_STORAGE[job_id]

        if job.status in [OCRStatus.COMPLETED, OCRStatus.FAILED, OCRStatus.CANCELLED]:
            raise HTTPException(
                status_code=400,
                detail=f"작업이 이미 {job.status} 상태입니다"
            )

        job.status = OCRStatus.CANCELLED
        logger.info(f"OCR 작업 취소: {job_id}")

        return {
            "message": "작업이 취소되었습니다",
            "job_id": job_id,
            "status": OCRStatus.CANCELLED
        }

    raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")


@router.post(
    "/ocr/jobs/{job_id}/retry",
    summary="OCR 작업 재시도",
    description="실패한 OCR 작업을 재시도합니다.",
    responses={
        200: {"description": "재시도 시작"},
        404: {"model": ErrorResponse, "description": "작업을 찾을 수 없음"},
        400: {"model": ErrorResponse, "description": "재시도할 수 없는 상태"}
    }
)
async def retry_ocr_job(
    job_id: str = PathParam(..., description="OCR 작업 ID")
):
    """
    OCR 작업 재시도

    - **job_id**: OCR 작업 ID
    - failed 상태의 작업만 재시도 가능합니다
    """

    # TODO: 실패한 작업을 다시 큐에 등록
    if job_id in JOB_STORAGE:
        job = JOB_STORAGE[job_id]

        if job.status != OCRStatus.FAILED:
            raise HTTPException(
                status_code=400,
                detail=f"재시도할 수 없는 상태입니다: {job.status}"
            )

        # 새로운 작업 ID 생성
        import uuid
        new_job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        logger.info(f"OCR 작업 재시도: {job_id} -> {new_job_id}")

        return {
            "message": "작업이 재시도되었습니다",
            "old_job_id": job_id,
            "new_job_id": new_job_id,
            "status": OCRStatus.PENDING
        }

    raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")


@router.get(
    "/ocr/jobs",
    summary="OCR 작업 목록 조회",
    description="모든 OCR 작업 목록을 조회합니다."
)
async def list_ocr_jobs(
    status: OCRStatus = None,
    limit: int = 50
):
    """
    OCR 작업 목록 조회

    - **status**: 상태 필터 (선택사항)
    - **limit**: 최대 조회 개수 (기본 50)
    """

    # TODO: Redis나 데이터베이스에서 작업 목록 조회
    jobs = list(JOB_STORAGE.values())

    if status:
        jobs = [job for job in jobs if job.status == status]

    jobs = jobs[:limit]

    return {
        "total": len(jobs),
        "jobs": jobs
    }


@router.get(
    "/ocr/statistics",
    summary="OCR 작업 통계",
    description="OCR 작업 통계를 조회합니다."
)
async def get_ocr_statistics():
    """
    OCR 작업 통계

    - 전체 작업 수
    - 상태별 작업 수
    - 평균 처리 시간
    - 성공률
    """

    # TODO: 데이터베이스에서 통계 조회
    total_jobs = len(JOB_STORAGE)

    if total_jobs == 0:
        return {
            "total_jobs": 0,
            "by_status": {},
            "success_rate": 0.0,
            "average_processing_time": None
        }

    jobs = list(JOB_STORAGE.values())

    by_status = {}
    for status in OCRStatus:
        count = len([job for job in jobs if job.status == status])
        if count > 0:
            by_status[status.value] = count

    completed = len([job for job in jobs if job.status == OCRStatus.COMPLETED])
    success_rate = (completed / total_jobs * 100) if total_jobs > 0 else 0.0

    return {
        "total_jobs": total_jobs,
        "by_status": by_status,
        "success_rate": success_rate,
        "average_processing_time": None
    }
