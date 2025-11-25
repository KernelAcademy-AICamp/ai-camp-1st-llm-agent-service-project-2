"""
LLM Router
Document summarization and clause extraction APIs
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/llm", tags=["llm"])

# ===== Request/Response Models =====

class SummarizeRequest(BaseModel):
    """문서 요약 요청"""
    document_id: str = Field(..., description="Document ID")
    text: str = Field(..., description="Document text to summarize")
    llm_model: str = Field("gpt-4", description="LLM model name")
    summary_type: str = Field("GLOBAL", description="Summary type (GLOBAL, SECTION)")

class SummarizeResponse(BaseModel):
    """문서 요약 응답"""
    success: bool
    document_id: str
    summary: str
    token_count: int
    model_version: str
    error: Optional[str] = None

class ClausesRequest(BaseModel):
    """조항 추출 요청"""
    document_id: str = Field(..., description="Document ID")
    text: str = Field(..., description="Document text to analyze")
    llm_model: str = Field("gpt-4", description="LLM model name")
    doc_type: Optional[str] = Field(None, description="Document type (CONTRACT, STATUTE, PRECEDENT, etc.)")

class ClauseItem(BaseModel):
    """개별 조항 정보"""
    clause_type: str
    title: str
    content: str
    importance_score: int

class ClausesResponse(BaseModel):
    """조항 추출 응답"""
    success: bool
    document_id: str
    clauses: List[ClauseItem]
    total_count: int
    error: Optional[str] = None

class AnalyzeRiskRequest(BaseModel):
    """리스크 분석 요청"""
    document_id: str = Field(..., description="Document ID")
    text: str = Field(..., description="Document text to analyze")
    llm_model: str = Field("gpt-4", description="LLM model name")
    document_type: str = Field("CONTRACT", description="Document type (CONTRACT, STATUTE, etc.)")

class RiskItem(BaseModel):
    """개별 리스크 항목"""
    category: str
    title: str
    description: str
    severity: str
    score: int
    clause_reference: str

class AnalyzeRiskResponse(BaseModel):
    """리스크 분석 응답"""
    success: bool
    document_id: str
    overall_risk_score: int
    severity: str
    risk_items: List[RiskItem]
    recommendations: List[str]
    summary: str
    meta: Dict[str, Any]
    error: Optional[str] = None

class AnalyzeCaseRequest(BaseModel):
    """사건 분석 요청"""
    document_id: str = Field(..., description="Document ID")
    text: str = Field(..., description="Document text to analyze")
    llm_model: str = Field("gpt-4", description="LLM model name")
    scenario: Optional[str] = Field(None, description="Analysis scenario (소송 준비, 계약 검토, etc.)")

class AnalyzeCaseResponse(BaseModel):
    """사건 분석 응답"""
    success: bool
    document_id: str
    suggested_case_name: str
    document_types: List[str]
    parties: Dict[str, Any]
    key_dates: Dict[str, str]
    issues: List[str]
    related_precedents: List[str]
    suggested_next_steps: List[str]
    scenario: Optional[str] = None
    error: Optional[str] = None

# ===== API Endpoints =====

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_document(
    request: SummarizeRequest,
    app_request: Request
):
    """
    POST /v1/llm/summarize

    문서 요약 생성

    Django Backend에서 호출되며, 문서 텍스트를 입력받아 요약을 생성합니다.

    Args:
        request: SummarizeRequest (document_id, text, llm_model, summary_type)

    Returns:
        SummarizeResponse with summary text and metadata

    Raises:
        HTTPException 400: Invalid input
        HTTPException 503: LLM service not available
        HTTPException 500: Internal error
    """
    try:
        # Import service (lazy import)
        from services.summarizer import Summarizer

        # Get LLM client from app state
        llm_client = app_request.app.state.llm_client

        if not llm_client:
            raise HTTPException(
                status_code=503,
                detail="LLM client is not available"
            )

        # Validate input
        if not request.text or len(request.text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )

        if request.summary_type not in ["GLOBAL", "SECTION"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid summary_type. Must be GLOBAL or SECTION"
            )

        # Initialize Summarizer
        summarizer = Summarizer(llm_client=llm_client)

        # Generate summary
        logger.info(f"Generating {request.summary_type} summary for document {request.document_id}...")

        result = await summarizer.summarize(
            text=request.text,
            document_id=request.document_id,
            summary_type=request.summary_type,
            llm_model=request.llm_model
        )

        # Return response
        return SummarizeResponse(
            success=True,
            document_id=request.document_id,
            summary=result.get('summary', ''),
            token_count=result.get('token_count', 0),
            model_version=result.get('model_version', request.llm_model)
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in summarize: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )


@router.post("/clauses", response_model=ClausesResponse)
async def extract_clauses(
    request: ClausesRequest,
    app_request: Request
):
    """
    POST /v1/llm/clauses

    핵심 조항 추출

    Django Backend에서 호출되며, 문서 텍스트를 분석하여 핵심 조항들을 추출합니다.

    Args:
        request: ClausesRequest (document_id, text, llm_model, doc_type)

    Returns:
        ClausesResponse with list of extracted clauses

    Raises:
        HTTPException 400: Invalid input
        HTTPException 503: LLM service not available
        HTTPException 500: Internal error
    """
    try:
        # Import service (lazy import)
        from services.clause_extractor import ClauseExtractor

        # Get LLM client from app state
        llm_client = app_request.app.state.llm_client

        if not llm_client:
            raise HTTPException(
                status_code=503,
                detail="LLM client is not available"
            )

        # Validate input
        if not request.text or len(request.text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )

        # Initialize ClauseExtractor
        extractor = ClauseExtractor(llm_client=llm_client)

        # Extract clauses
        logger.info(
            f"Extracting clauses for document {request.document_id} "
            f"(type: {request.doc_type})..."
        )

        result = await extractor.extract_clauses(
            text=request.text,
            document_id=request.document_id,
            doc_type=request.doc_type,
            llm_model=request.llm_model
        )

        # Convert to response model
        clause_items = [
            ClauseItem(
                clause_type=clause['clause_type'],
                title=clause['title'],
                content=clause['content'],
                importance_score=clause['importance_score']
            )
            for clause in result.get('clauses', [])
        ]

        # Return response
        return ClausesResponse(
            success=True,
            document_id=request.document_id,
            clauses=clause_items,
            total_count=result.get('total_count', len(clause_items))
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in extract_clauses: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error extracting clauses: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract clauses: {str(e)}"
        )


@router.post("/analyze_risk", response_model=AnalyzeRiskResponse)
async def analyze_document_risk(
    request: AnalyzeRiskRequest,
    app_request: Request
):
    """
    POST /v1/llm/analyze_risk

    문서 리스크 분석

    Django Backend에서 호출되며, 문서 텍스트를 분석하여 잠재적 리스크를 식별합니다.

    Args:
        request: AnalyzeRiskRequest (document_id, text, llm_model, document_type)

    Returns:
        AnalyzeRiskResponse with risk analysis results

    Raises:
        HTTPException 400: Invalid input
        HTTPException 503: LLM service not available
        HTTPException 500: Internal error
    """
    try:
        # Import service (lazy import)
        from services.risk_analyzer import RiskAnalyzer

        # Get LLM client from app state
        llm_client = app_request.app.state.llm_client

        if not llm_client:
            raise HTTPException(
                status_code=503,
                detail="LLM client is not available"
            )

        # Validate input
        if not request.text or len(request.text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )

        # Initialize RiskAnalyzer
        analyzer = RiskAnalyzer(llm_client=llm_client)

        # Analyze risks
        logger.info(
            f"Analyzing risks for document {request.document_id} "
            f"(type: {request.document_type})..."
        )

        result = await analyzer.analyze_risk(
            text=request.text,
            document_id=request.document_id,
            document_type=request.document_type,
            llm_model=request.llm_model
        )

        # Convert risk items to response model
        risk_items = [
            RiskItem(
                category=item['category'],
                title=item['title'],
                description=item['description'],
                severity=item['severity'],
                score=item['score'],
                clause_reference=item.get('clause_reference', '')
            )
            for item in result.get('risk_items', [])
        ]

        # Return response
        return AnalyzeRiskResponse(
            success=True,
            document_id=request.document_id,
            overall_risk_score=result.get('overall_risk_score', 0),
            severity=result.get('severity', 'MEDIUM'),
            risk_items=risk_items,
            recommendations=result.get('recommendations', []),
            summary=result.get('summary', ''),
            meta=result.get('meta', {})
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in analyze_risk: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error analyzing risks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze risks: {str(e)}"
        )


@router.post("/analyze_case", response_model=AnalyzeCaseResponse)
async def analyze_case(
    request: AnalyzeCaseRequest,
    app_request: Request
):
    """
    POST /v1/llm/analyze_case

    문서 사건 분석

    Django Backend에서 호출되며, 문서 텍스트를 분석하여 사건 정보를 추출합니다.

    Args:
        request: AnalyzeCaseRequest (document_id, text, llm_model, scenario)

    Returns:
        AnalyzeCaseResponse with case analysis results

    Raises:
        HTTPException 400: Invalid input
        HTTPException 503: LLM service not available
        HTTPException 500: Internal error
    """
    try:
        # Import service (lazy import)
        from services.case_analyzer import CaseAnalyzer

        # Get LLM client from app state
        llm_client = app_request.app.state.llm_client

        if not llm_client:
            raise HTTPException(
                status_code=503,
                detail="LLM client is not available"
            )

        # Validate input
        if not request.text or len(request.text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )

        # Initialize CaseAnalyzer
        analyzer = CaseAnalyzer(llm_client=llm_client)

        # Analyze case
        logger.info(
            f"Analyzing case for document {request.document_id} "
            f"(scenario: {request.scenario})..."
        )

        # Prepare text as single document
        texts = [request.text]
        filenames = [f"document_{request.document_id}"]

        # Use the analyze_documents method
        result = await analyzer.analyze_documents(
            texts=texts,
            filenames=filenames
        )

        # Add scenario information
        if request.scenario:
            result['scenario'] = request.scenario

        # Return response
        return AnalyzeCaseResponse(
            success=True,
            document_id=request.document_id,
            suggested_case_name=result.get('suggested_case_name', ''),
            document_types=result.get('document_types', []),
            parties=result.get('parties', {}),
            key_dates=result.get('key_dates', {}),
            issues=result.get('issues', []),
            related_precedents=result.get('related_cases', []),
            suggested_next_steps=result.get('suggested_next_steps', []),
            scenario=result.get('scenario')
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in analyze_case: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error analyzing case: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze case: {str(e)}"
        )
