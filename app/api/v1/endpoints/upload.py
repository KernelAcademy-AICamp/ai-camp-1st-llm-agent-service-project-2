"""
파일 업로드 API 엔드포인트
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import os
import uuid
from datetime import datetime
from pathlib import Path
import logging

from app.schemas import DocumentUploadResponse, OCRStatus, ErrorResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 허용되는 파일 확장자
ALLOWED_EXTENSIONS = {".pdf"}
# 최대 파일 크기 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


def validate_file(file: UploadFile) -> tuple[bool, Optional[str]]:
    """
    파일 유효성 검증

    Args:
        file: 업로드된 파일

    Returns:
        (유효 여부, 에러 메시지)
    """
    # 파일 확장자 검증
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"허용되지 않는 파일 형식입니다. 허용 형식: {', '.join(ALLOWED_EXTENSIONS)}"

    # Content-Type 검증
    if file.content_type not in ["application/pdf"]:
        return False, f"잘못된 Content-Type입니다: {file.content_type}"

    return True, None


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="PDF 파일 업로드",
    description="PDF 파일을 업로드하고 OCR 작업을 시작합니다.",
    responses={
        200: {"description": "업로드 성공"},
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        413: {"model": ErrorResponse, "description": "파일 크기 초과"},
        500: {"model": ErrorResponse, "description": "서버 오류"}
    }
)
async def upload_document(
    file: UploadFile = File(..., description="업로드할 PDF 파일")
) -> DocumentUploadResponse:
    """
    PDF 파일 업로드 및 OCR 작업 등록

    - **file**: PDF 파일 (최대 50MB)
    - 허용 형식: .pdf
    - 업로드 후 자동으로 OCR 작업이 시작됩니다
    """

    try:
        # 1. 파일 유효성 검증
        is_valid, error_message = validate_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)

        # 2. 파일 읽기
        contents = await file.read()
        file_size = len(contents)

        # 파일 크기 검증
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"파일 크기가 너무 큽니다. 최대 크기: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            )

        if file_size == 0:
            raise HTTPException(status_code=400, detail="빈 파일입니다")

        # 3. 문서 ID 생성
        document_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 4. 임시 저장 디렉토리 생성
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        # 5. 파일 저장
        file_path = upload_dir / f"{document_id}.pdf"
        with open(file_path, "wb") as f:
            f.write(contents)

        logger.info(f"파일 업로드 완료: {document_id}, 크기: {file_size} bytes")

        # 6. OCR 작업 ID 생성 (실제로는 Celery task ID가 될 것)
        ocr_job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # TODO: Celery task 시작
        # from app.workers.ocr_worker import process_document_ocr
        # task = process_document_ocr.delay(str(file_path), document_id)
        # ocr_job_id = task.id

        logger.info(f"OCR 작업 등록: {ocr_job_id}")

        # 7. 응답 생성
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            file_size=file_size,
            content_type=file.content_type,
            upload_time=datetime.now(),
            ocr_job_id=ocr_job_id,
            status=OCRStatus.PENDING
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}")


@router.post(
    "/upload/batch",
    summary="여러 PDF 파일 일괄 업로드",
    description="여러 PDF 파일을 한 번에 업로드합니다.",
    responses={
        200: {"description": "업로드 성공"},
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        413: {"model": ErrorResponse, "description": "파일 크기 초과"},
        500: {"model": ErrorResponse, "description": "서버 오류"}
    }
)
async def upload_documents_batch(
    files: list[UploadFile] = File(..., description="업로드할 PDF 파일 목록")
):
    """
    여러 PDF 파일 일괄 업로드

    - **files**: PDF 파일 리스트 (각 최대 50MB)
    - 최대 10개 파일까지 동시 업로드 가능
    """

    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="최대 10개 파일까지 업로드 가능합니다"
        )

    results = []
    errors = []

    for file in files:
        try:
            result = await upload_document(file)
            results.append(result)
        except HTTPException as e:
            errors.append({
                "filename": file.filename,
                "error": e.detail
            })
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })

    return {
        "uploaded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.get(
    "/upload/limits",
    summary="업로드 제한 정보",
    description="파일 업로드 제한 정보를 반환합니다."
)
async def get_upload_limits():
    """
    업로드 제한 정보 조회
    """
    return {
        "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
        "max_batch_count": 10,
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "allowed_content_types": ["application/pdf"]
    }
