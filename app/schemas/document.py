"""
문서 관련 Pydantic 스키마
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class OCRStatus(str, Enum):
    """OCR 작업 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DocumentType(str, Enum):
    """문서 타입"""
    CASE_LAW = "case_law"  # 판례
    INTERPRETATION = "interpretation"  # 해석례
    CONTRACT = "contract"  # 계약서
    OTHER = "other"  # 기타


class DocumentUploadResponse(BaseModel):
    """문서 업로드 응답"""
    document_id: str = Field(..., description="문서 ID")
    filename: str = Field(..., description="파일명")
    file_size: int = Field(..., description="파일 크기 (bytes)")
    content_type: str = Field(..., description="콘텐츠 타입")
    upload_time: datetime = Field(..., description="업로드 시간")
    ocr_job_id: Optional[str] = Field(None, description="OCR 작업 ID")
    status: OCRStatus = Field(default=OCRStatus.PENDING, description="OCR 상태")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_20231031_123456",
                "filename": "contract.pdf",
                "file_size": 1048576,
                "content_type": "application/pdf",
                "upload_time": "2023-10-31T12:34:56",
                "ocr_job_id": "job_20231031_123456",
                "status": "pending"
            }
        }


class DocumentListItem(BaseModel):
    """문서 목록 아이템"""
    document_id: str
    filename: str
    document_type: Optional[DocumentType]
    total_pages: Optional[int]
    status: OCRStatus
    average_confidence: Optional[float]
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """문서 목록 응답"""
    total: int = Field(..., description="전체 문서 수")
    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지 크기")
    documents: List[DocumentListItem] = Field(..., description="문서 목록")


class DocumentDetailResponse(BaseModel):
    """문서 상세 응답"""
    document_id: str
    filename: str
    document_type: Optional[DocumentType]
    file_size: int
    total_pages: int
    processed_pages: int
    status: OCRStatus
    average_confidence: Optional[float]
    total_word_count: Optional[int]
    processing_time: Optional[float]
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None


class OCRJobStatus(BaseModel):
    """OCR 작업 상태"""
    job_id: str = Field(..., description="작업 ID")
    document_id: str = Field(..., description="문서 ID")
    status: OCRStatus = Field(..., description="작업 상태")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="진행률 (%)")
    total_pages: Optional[int] = Field(None, description="전체 페이지 수")
    processed_pages: int = Field(default=0, description="처리된 페이지 수")
    current_page: Optional[int] = Field(None, description="현재 처리 중인 페이지")
    average_confidence: Optional[float] = Field(None, description="평균 신뢰도")
    error_message: Optional[str] = Field(None, description="에러 메시지")
    started_at: Optional[datetime] = Field(None, description="시작 시간")
    completed_at: Optional[datetime] = Field(None, description="완료 시간")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_20231031_123456",
                "document_id": "doc_20231031_123456",
                "status": "processing",
                "progress": 66.67,
                "total_pages": 3,
                "processed_pages": 2,
                "current_page": 3,
                "average_confidence": 85.5,
                "error_message": None,
                "started_at": "2023-10-31T12:34:56",
                "completed_at": None
            }
        }


class DocumentDownloadOptions(BaseModel):
    """문서 다운로드 옵션"""
    format: str = Field(default="json", description="출력 형식 (json, csv, txt)")
    include_metadata: bool = Field(default=True, description="메타데이터 포함 여부")


class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 정보")
    timestamp: datetime = Field(default_factory=datetime.now, description="에러 발생 시간")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "File too large",
                "detail": "Maximum file size is 50MB",
                "timestamp": "2023-10-31T12:34:56"
            }
        }
