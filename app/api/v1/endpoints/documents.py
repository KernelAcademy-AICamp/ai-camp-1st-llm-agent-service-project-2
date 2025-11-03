"""
문서 관리 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Query, Path as PathParam
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional
import os
from pathlib import Path
from datetime import datetime
import logging
import json
import csv
from io import StringIO

from app.schemas import (
    DocumentListResponse,
    DocumentListItem,
    DocumentDetailResponse,
    OCRStatus,
    DocumentType,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


# 임시 데이터 (실제로는 데이터베이스에서 가져와야 함)
MOCK_DOCUMENTS = {}


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="문서 목록 조회",
    description="업로드된 문서 목록을 조회합니다.",
)
async def list_documents(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    status: Optional[OCRStatus] = Query(None, description="상태 필터"),
    document_type: Optional[DocumentType] = Query(None, description="문서 타입 필터"),
):
    """
    문서 목록 조회

    - **page**: 페이지 번호 (1부터 시작)
    - **page_size**: 페이지당 문서 수 (1-100)
    - **status**: 상태 필터 (pending, processing, completed, failed, cancelled)
    - **document_type**: 문서 타입 필터 (case_law, interpretation, contract, other)
    """

    # TODO: 데이터베이스에서 문서 목록 조회
    # 현재는 uploads 디렉토리에서 파일 목록 읽기
    upload_dir = Path("uploads")

    if not upload_dir.exists():
        return DocumentListResponse(
            total=0,
            page=page,
            page_size=page_size,
            documents=[]
        )

    # 간단한 목 데이터
    documents = []
    for file_path in upload_dir.glob("*.pdf"):
        doc_id = file_path.stem
        file_stat = file_path.stat()

        documents.append(DocumentListItem(
            document_id=doc_id,
            filename=file_path.name,
            document_type=DocumentType.OTHER,
            total_pages=None,
            status=OCRStatus.COMPLETED,
            average_confidence=None,
            created_at=datetime.fromtimestamp(file_stat.st_ctime),
            updated_at=datetime.fromtimestamp(file_stat.st_mtime)
        ))

    # 필터링
    if status:
        documents = [doc for doc in documents if doc.status == status]
    if document_type:
        documents = [doc for doc in documents if doc.document_type == document_type]

    # 페이지네이션
    total = len(documents)
    start = (page - 1) * page_size
    end = start + page_size
    page_documents = documents[start:end]

    return DocumentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        documents=page_documents
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    summary="문서 상세 조회",
    description="특정 문서의 상세 정보를 조회합니다.",
    responses={
        200: {"description": "조회 성공"},
        404: {"model": ErrorResponse, "description": "문서를 찾을 수 없음"}
    }
)
async def get_document(
    document_id: str = PathParam(..., description="문서 ID")
):
    """
    문서 상세 정보 조회

    - **document_id**: 문서 ID
    """

    # TODO: 데이터베이스에서 문서 정보 조회
    file_path = Path("uploads") / f"{document_id}.pdf"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

    file_stat = file_path.stat()

    return DocumentDetailResponse(
        document_id=document_id,
        filename=file_path.name,
        document_type=DocumentType.OTHER,
        file_size=file_stat.st_size,
        total_pages=0,
        processed_pages=0,
        status=OCRStatus.COMPLETED,
        average_confidence=None,
        total_word_count=None,
        processing_time=None,
        created_at=datetime.fromtimestamp(file_stat.st_ctime),
        updated_at=datetime.fromtimestamp(file_stat.st_mtime),
        error_message=None
    )


@router.delete(
    "/documents/{document_id}",
    summary="문서 삭제",
    description="특정 문서를 삭제합니다.",
    responses={
        200: {"description": "삭제 성공"},
        404: {"model": ErrorResponse, "description": "문서를 찾을 수 없음"},
        500: {"model": ErrorResponse, "description": "서버 오류"}
    }
)
async def delete_document(
    document_id: str = PathParam(..., description="문서 ID")
):
    """
    문서 삭제

    - **document_id**: 문서 ID
    - 원본 PDF 파일과 모든 관련 데이터가 삭제됩니다
    """

    try:
        # TODO: 데이터베이스에서 문서 정보 삭제
        # TODO: MinIO/S3에서 파일 삭제

        file_path = Path("uploads") / f"{document_id}.pdf"

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")

        # 파일 삭제
        file_path.unlink()

        logger.info(f"문서 삭제 완료: {document_id}")

        return {
            "message": "문서가 성공적으로 삭제되었습니다",
            "document_id": document_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 삭제 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"문서 삭제 중 오류가 발생했습니다: {str(e)}")


@router.get(
    "/documents/{document_id}/download",
    summary="문서 결과 다운로드",
    description="OCR 처리된 문서 결과를 다운로드합니다.",
    responses={
        200: {"description": "다운로드 성공"},
        404: {"model": ErrorResponse, "description": "문서를 찾을 수 없음"},
        400: {"model": ErrorResponse, "description": "잘못된 요청"}
    }
)
async def download_document_result(
    document_id: str = PathParam(..., description="문서 ID"),
    format: str = Query("json", description="출력 형식 (json, csv, txt)")
):
    """
    문서 결과 다운로드

    - **document_id**: 문서 ID
    - **format**: 출력 형식
        - `json`: JSON 형식 (메타데이터 포함)
        - `csv`: CSV 형식 (구조화 데이터)
        - `txt`: 텍스트만 추출
    """

    if format not in ["json", "csv", "txt"]:
        raise HTTPException(status_code=400, detail="지원하지 않는 형식입니다")

    # TODO: 데이터베이스에서 OCR 결과 조회

    # 임시: 생성된 파일이 있는지 확인
    if format == "json":
        result_file = Path(f"{document_id}_document.json")
        if result_file.exists():
            return FileResponse(
                result_file,
                media_type="application/json",
                filename=f"{document_id}.json"
            )
    elif format == "csv":
        result_file = Path(f"{document_id}_structured.csv")
        if result_file.exists():
            return FileResponse(
                result_file,
                media_type="text/csv",
                filename=f"{document_id}.csv"
            )

    raise HTTPException(status_code=404, detail="문서 결과를 찾을 수 없습니다")


@router.get(
    "/documents/{document_id}/text",
    summary="문서 텍스트 조회",
    description="OCR로 추출된 텍스트를 조회합니다.",
    responses={
        200: {"description": "조회 성공"},
        404: {"model": ErrorResponse, "description": "문서를 찾을 수 없음"}
    }
)
async def get_document_text(
    document_id: str = PathParam(..., description="문서 ID"),
    page: Optional[int] = Query(None, ge=1, description="특정 페이지만 조회")
):
    """
    문서 텍스트 조회

    - **document_id**: 문서 ID
    - **page**: 특정 페이지 번호 (선택사항)
    """

    # TODO: 데이터베이스에서 텍스트 조회
    raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")


@router.get(
    "/documents/statistics/summary",
    summary="문서 통계",
    description="전체 문서 통계를 조회합니다."
)
async def get_documents_statistics():
    """
    문서 통계 조회

    - 전체 문서 수
    - 상태별 문서 수
    - 평균 처리 시간
    - 평균 신뢰도
    """

    # TODO: 데이터베이스에서 통계 조회
    upload_dir = Path("uploads")

    if not upload_dir.exists():
        return {
            "total_documents": 0,
            "by_status": {},
            "by_type": {},
            "average_confidence": None,
            "average_processing_time": None
        }

    total = len(list(upload_dir.glob("*.pdf")))

    return {
        "total_documents": total,
        "by_status": {
            "completed": total,
            "pending": 0,
            "processing": 0,
            "failed": 0
        },
        "by_type": {
            "other": total
        },
        "average_confidence": None,
        "average_processing_time": None
    }
