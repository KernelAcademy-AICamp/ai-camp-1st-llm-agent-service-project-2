# apps/ai-service/routers/analyze.py
"""
Analyze Router
사건 분석 및 문서 생성 API
"""

from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/analyze", tags=["analyze"])

# ===== Request/Response Models =====

class AnalyzeRequest(BaseModel):
    """사건 분석 요청"""
    text: str = Field(..., description="분석할 사건 텍스트")
    include_related_cases: bool = Field(True, description="관련 판례 검색 포함")

class AnalyzeResponse(BaseModel):
    """사건 분석 응답"""
    summary: str
    document_types: List[str]
    issues: List[str]
    key_dates: Dict[str, str]
    parties: Dict[str, str]
    related_cases: List[Dict[str, Any]]
    suggested_case_name: str
    suggested_next_steps: List[str]

class GenerateRequest(BaseModel):
    """문서 생성 요청"""
    template_name: str = Field(..., description="템플릿 이름 (소장, 답변서 등)")
    case_analysis: Dict[str, Any] = Field(..., description="사건 분석 결과")
    generation_mode: str = Field("quick", description="생성 모드 (quick/custom)")
    custom_fields: Optional[Dict[str, str]] = Field(None, description="맞춤 필드")

class GenerateResponse(BaseModel):
    """문서 생성 응답"""
    title: str
    content: str
    template_used: str
    metadata: Dict[str, Any]

# ===== API Endpoints =====

@router.post("/case", response_model=AnalyzeResponse)
async def analyze_case(
    request: AnalyzeRequest,
    app_request: Request
):
    """
    사건 분석

    텍스트를 분석하여 사건 정보를 추출하고
    관련 판례를 검색합니다.
    """
    try:
        # CaseAnalyzer import (지연 import)
        from services.case_analyzer import CaseAnalyzer

        # AI 컴포넌트 가져오기
        llm_client = app_request.app.state.llm_client
        retriever = app_request.app.state.retriever

        if not llm_client:
            raise HTTPException(
                status_code=503,
                detail="LLM client is not available"
            )

        # CaseAnalyzer 초기화
        analyzer = CaseAnalyzer(
            llm_client=llm_client,
            retriever=retriever if request.include_related_cases else None
        )

        # 분석 수행 (⭐ 수정: analyze() → analyze_documents())
        result = await analyzer.analyze_documents(
            texts=[request.text],
            filenames=["uploaded_text"]
        )

        return AnalyzeResponse(
            summary=result.get('summary', ''),
            document_types=result.get('document_types', []),
            issues=result.get('issues', []),
            key_dates=result.get('key_dates', {}),
            parties=result.get('parties', {}),
            related_cases=result.get('related_cases', []),
            suggested_case_name=result.get('suggested_case_name', ''),
            suggested_next_steps=result.get('suggested_next_steps', [])
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Case analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@router.post("/generate", response_model=GenerateResponse)
async def generate_document(
    request: GenerateRequest,
    app_request: Request
):
    """
    법률 문서 생성

    사건 정보를 기반으로 법률 문서를 생성합니다.
    """
    try:
        from services.document_generator import DocumentGenerator

        llm_client = app_request.app.state.llm_client
        if not llm_client:
            raise HTTPException(
                status_code=503,
                detail="LLM client is not available"
            )

        generator = DocumentGenerator(llm_client=llm_client)

        # 문서 생성 (⭐ 수정: generate() → generate_document(), await 추가)
        result = await generator.generate_document(
            template_name=request.template_name,
            case_analysis=request.case_analysis,
            generation_mode=request.generation_mode,
            custom_fields=request.custom_fields
        )

        return GenerateResponse(
            title=result.get('title', ''),
            content=result.get('content', ''),
            template_used=result.get('template_used', ''),
            metadata=result.get('metadata', {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Document generation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}"
        )
