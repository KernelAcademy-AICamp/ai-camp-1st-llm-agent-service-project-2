"""
V2 Document Router - LangGraph Based

Phase 4 - Week 12: LangGraph 기반 문서 분석 API

특징:
- LangGraph StateGraph 기반 워크플로우
- 병렬 실행 (summarize + extract_clauses)
- Checkpointing 불필요 (빠른 실행)
- 기존 v1 API와 호환성 유지

엔드포인트:
- POST /v2/documents/analyze - 문서 분석
- POST /v2/documents/analyze/text - 텍스트 직접 분석
- GET /v2/documents/health - 헬스체크
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import tempfile
import os

from apps.ai_service.workflows.document_workflow import DocumentWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/documents", tags=["documents-v2"])


# ===== Request/Response Models =====

class ClauseV2(BaseModel):
    """핵심 조항 (v2)"""
    clause_type: str = Field(..., description="조항 유형")
    title: str = Field(..., description="조항 제목")
    content: str = Field(..., description="조항 내용")
    importance_score: int = Field(..., description="중요도 점수 (0-100)")


class SummaryV2(BaseModel):
    """요약 정보 (v2)"""
    summary: str = Field(..., description="요약 텍스트")
    token_count: int = Field(0, description="토큰 수")
    model_version: str = Field("unknown", description="모델 버전")


class DocumentAnalyzeRequest(BaseModel):
    """문서 분석 요청 (텍스트 직접 제공)"""
    text: str = Field(..., description="분석할 텍스트", min_length=10)
    doc_type: str = Field(
        "OTHER",
        description="문서 유형 (CONTRACT, STATUTE, PRECEDENT, OTHER)"
    )
    document_id: Optional[str] = Field(None, description="문서 ID (DB 저장용)")
    session_id: Optional[str] = Field(None, description="세션 ID")


class DocumentAnalyzeResponse(BaseModel):
    """문서 분석 응답"""
    success: bool
    document_id: Optional[str] = None
    doc_type: str
    summary: Optional[SummaryV2] = None
    clauses: List[ClauseV2] = []
    chunk_count: int = 0
    completed_tasks: List[str] = []
    processing_time: float
    session_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: str
    version: str = "v2"


class DocumentErrorResponse(BaseModel):
    """에러 응답"""
    error: str
    detail: Optional[str] = None
    timestamp: str


# ===== API Endpoints =====

@router.post("/analyze", response_model=DocumentAnalyzeResponse)
async def analyze_document_file(
    file: UploadFile = File(...),
    doc_type: str = Form("OTHER"),
    document_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """
    파일 업로드 기반 문서 분석 (v2)

    워크플로우:
    1. preprocess: 파일에서 텍스트 추출
    2. chunk: 텍스트 청킹
    3. summarize + extract_clauses: 병렬 실행
    4. aggregate: 결과 집계

    Args:
        file: 업로드 파일 (PDF, DOCX, TXT)
        doc_type: 문서 유형
        document_id: 문서 ID (선택)
        session_id: 세션 ID (선택)

    Returns:
        문서 분석 결과
    """
    temp_path = None
    try:
        logger.info(f"[v2/documents/analyze] file={file.filename}, type={doc_type}")

        # 파일 확장자 검증
        filename = file.filename or "document"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".docx", ".txt"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Supported: pdf, docx, txt"
            )

        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # 워크플로우 실행
        workflow = DocumentWorkflow()
        result = await workflow.arun(
            file_path=temp_path,
            doc_type=doc_type,
            document_id=document_id,
            session_id=session_id
        )

        # 응답 생성
        return _build_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[v2/documents/analyze] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    finally:
        # 임시 파일 정리
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")


@router.post("/analyze/text", response_model=DocumentAnalyzeResponse)
async def analyze_document_text(request: DocumentAnalyzeRequest):
    """
    텍스트 직접 분석 (v2)

    워크플로우:
    1. preprocess: 텍스트 직접 사용 (추출 생략)
    2. chunk: 텍스트 청킹
    3. summarize + extract_clauses: 병렬 실행
    4. aggregate: 결과 집계

    Args:
        request: 분석 요청 (텍스트 포함)

    Returns:
        문서 분석 결과
    """
    try:
        logger.info(f"[v2/documents/analyze/text] text_len={len(request.text)}, type={request.doc_type}")

        # 워크플로우 실행
        workflow = DocumentWorkflow()
        result = await workflow.arun(
            text=request.text,
            doc_type=request.doc_type,
            document_id=request.document_id,
            session_id=request.session_id
        )

        # 응답 생성
        return _build_response(result)

    except Exception as e:
        logger.error(f"[v2/documents/analyze/text] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/health")
async def document_v2_health():
    """
    Document v2 헬스체크

    Returns:
        상태 정보
    """
    try:
        # 워크플로우 초기화 테스트
        workflow = DocumentWorkflow()

        return {
            "status": "healthy",
            "version": "v2",
            "engine": "LangGraph",
            "workflow": "document_analysis_workflow",
            "features": [
                "parallel_execution",
                "text_extraction",
                "summarization",
                "clause_extraction"
            ],
            "checkpointing": False,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"[health] Error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ===== Helper Functions =====

def _build_response(result: Dict[str, Any]) -> DocumentAnalyzeResponse:
    """
    워크플로우 결과를 응답 모델로 변환
    """
    # Summary 변환
    summary_data = result.get("summary")
    summary = None
    if summary_data:
        summary = SummaryV2(
            summary=summary_data.get("summary", ""),
            token_count=summary_data.get("token_count", 0),
            model_version=summary_data.get("model_version", "unknown")
        )

    # Clauses 변환
    clauses = []
    for clause_data in result.get("clauses", []):
        clauses.append(ClauseV2(
            clause_type=clause_data.get("clause_type", "OTHER"),
            title=clause_data.get("title", ""),
            content=clause_data.get("content", ""),
            importance_score=clause_data.get("importance_score", 50)
        ))

    return DocumentAnalyzeResponse(
        success=result.get("success", False),
        document_id=result.get("document_id"),
        doc_type=result.get("doc_type", "OTHER"),
        summary=summary,
        clauses=clauses,
        chunk_count=result.get("chunk_count", 0),
        completed_tasks=result.get("completed_tasks", []),
        processing_time=result.get("processing_time", 0),
        session_id=result.get("session_id"),
        error=result.get("error"),
        timestamp=datetime.now().isoformat()
    )
