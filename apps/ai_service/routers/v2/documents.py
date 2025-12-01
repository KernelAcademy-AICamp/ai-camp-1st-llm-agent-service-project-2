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
    analysis_type: Optional[str] = Field(
        None,
        description="분석 유형: 'summary' | 'clauses' | 'risk' | None (전체)"
    )


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
    - analysis_type=None: 전체 분석 (summary + clauses + risk)
    - analysis_type='summary': 요약만 생성
    - analysis_type='clauses': 조항만 추출
    - analysis_type='risk': 리스크만 분석

    Args:
        request: 분석 요청 (텍스트 포함)

    Returns:
        문서 분석 결과
    """
    try:
        analysis_type = request.analysis_type
        logger.info(
            f"[v2/documents/analyze/text] text_len={len(request.text)}, "
            f"type={request.doc_type}, analysis_type={analysis_type}"
        )

        # 선택적 분석: 개별 서비스 직접 호출 (워크플로우 우회)
        if analysis_type in ('summary', 'clauses', 'risk'):
            result = await _run_single_analysis(
                text=request.text,
                doc_type=request.doc_type,
                document_id=request.document_id,
                analysis_type=analysis_type
            )
            return _build_response(result, request.session_id)

        # 전체 분석: 워크플로우 실행
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


async def _run_single_analysis(
    text: str,
    doc_type: str,
    document_id: Optional[str],
    analysis_type: str
) -> Dict[str, Any]:
    """
    개별 분석 실행 (워크플로우 우회)

    Args:
        text: 분석할 텍스트
        doc_type: 문서 유형
        document_id: 문서 ID
        analysis_type: 'summary' | 'clauses' | 'risk'

    Returns:
        분석 결과
    """
    import time
    from libs.rag_core.llm.llm_client import create_llm_client
    from apps.ai_service.config.settings import settings

    start_time = time.time()

    llm_client = create_llm_client(
        provider=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS
    )

    result = {
        "success": True,
        "document_id": document_id,
        "doc_type": doc_type,
        "summary": None,
        "clauses": [],
        "risks": None,
        "completed_tasks": [],
        "error": None,
    }

    try:
        if analysis_type == 'summary':
            from apps.ai_service.services.summarizer import Summarizer
            summarizer = Summarizer(llm_client)
            summary_result = await summarizer.summarize(
                text=text,
                document_id=document_id,
                summary_type="GLOBAL"
            )
            result["summary"] = {
                "summary": summary_result.get("summary", ""),
                "token_count": summary_result.get("token_count", 0),
                "model_version": summary_result.get("model_version", "unknown"),
            }
            result["completed_tasks"] = ["summary"]

        elif analysis_type == 'clauses':
            from apps.ai_service.services.clause_extractor import ClauseExtractor
            extractor = ClauseExtractor(llm_client)
            clauses_result = await extractor.extract_clauses(
                text=text,
                document_id=document_id,
                doc_type=doc_type
            )
            result["clauses"] = clauses_result.get("clauses", [])
            result["completed_tasks"] = ["clauses"]

        elif analysis_type == 'risk':
            # 리스크 분석은 별도 엔드포인트 사용 권장
            # 여기서는 간단히 처리
            import json
            import re

            prompt = f"""당신은 법률 리스크 분석 전문가입니다. 다음 {doc_type} 문서에서 잠재적 리스크를 식별해주세요.

문서 내용:
{text[:8000]}

다음 JSON 배열 형식으로 리스크를 식별해주세요:
[
  {{
    "risk_type": "LEGAL|FINANCIAL|COMPLIANCE|OPERATIONAL|OTHER",
    "description": "리스크에 대한 상세 설명",
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
    "recommendation": "리스크 완화 권장사항"
  }}
]

최대 5개의 리스크를 식별하세요. 반드시 유효한 JSON 형식으로만 응답해주세요."""

            response = llm_client.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )

            risks = []
            try:
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    risks = json.loads(json_match.group(0))
            except Exception as e:
                logger.warning(f"Failed to parse risks: {e}")

            result["risks"] = risks
            result["completed_tasks"] = ["risk"]

    except Exception as e:
        logger.error(f"[_run_single_analysis] Error: {e}", exc_info=True)
        result["success"] = False
        result["error"] = str(e)

    result["processing_time"] = time.time() - start_time
    return result


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

def _build_response(
    result: Dict[str, Any],
    session_id: Optional[str] = None
) -> DocumentAnalyzeResponse:
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
        session_id=session_id or result.get("session_id"),
        error=result.get("error"),
        timestamp=datetime.now().isoformat()
    )
