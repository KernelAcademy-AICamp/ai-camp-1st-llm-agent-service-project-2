"""
LLM Router
Document summarization and clause extraction APIs
"""

from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/llm", tags=["llm"])

# Thread pool for concurrent LLM calls
_executor = ThreadPoolExecutor(max_workers=10)

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


# ===== LLM Comparison Models =====

class CompareModelConfig(BaseModel):
    """비교할 모델 설정"""
    id: str = Field(..., description="Model config ID")
    name: str = Field(..., description="Model display name")
    provider: str = Field(..., description="Provider (openai, anthropic, google, ollama)")
    model_id: str = Field(..., description="Actual model ID (e.g., gpt-4-turbo)")
    api_key_env_var: Optional[str] = Field(None, description="Environment variable for API key")
    base_url: Optional[str] = Field(None, description="Custom API endpoint URL")
    temperature: float = Field(0.1, description="Temperature setting")
    max_tokens: int = Field(2000, description="Max tokens limit")
    input_cost_per_1k: float = Field(0.0, description="Cost per 1K input tokens")
    output_cost_per_1k: float = Field(0.0, description="Cost per 1K output tokens")


class CompareRequest(BaseModel):
    """모델 비교 요청"""
    text: str = Field(..., description="Text to process")
    task_type: str = Field(..., description="Task type (summarize, clauses, risk_analysis, etc.)")
    models: List[CompareModelConfig] = Field(..., description="List of models to compare")
    session_id: str = Field(..., description="Comparison session ID")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional options")


class ModelResult(BaseModel):
    """개별 모델 결과"""
    model_id: str
    model_name: str
    provider: str
    status: str  # success, error
    response_text: Optional[str] = None
    prompt_tokens: int = 0
    response_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    estimated_cost: float = 0.0
    error_message: Optional[str] = None


class CompareResponse(BaseModel):
    """모델 비교 응답"""
    session_id: str
    results: List[ModelResult]
    fastest_model: Optional[str] = None
    cheapest_model: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)


# ===== Helper Functions =====

def _estimate_tokens(text: str) -> int:
    """
    간단한 토큰 추정 (실제로는 tiktoken 등을 사용하는 것이 좋음)
    한글은 대략 글자당 1.5~2 토큰, 영문은 단어당 1~1.5 토큰
    """
    # 간단한 추정: 문자열 길이 / 4 (대략적인 평균)
    return max(1, len(text) // 4)


def _call_llm_sync(
    model_config: CompareModelConfig,
    text: str,
    task_type: str,
    options: Dict[str, Any]
) -> ModelResult:
    """
    동기적으로 LLM 호출 (ThreadPool에서 실행됨)
    """
    start_time = time.time()

    try:
        # Import LLM client factory
        from libs.rag_core import create_llm_client

        # Get API key from environment
        api_key = ""
        if model_config.api_key_env_var:
            api_key = os.getenv(model_config.api_key_env_var, "")

        if not api_key and model_config.provider != "ollama":
            return ModelResult(
                model_id=model_config.id,
                model_name=model_config.name,
                provider=model_config.provider,
                status="error",
                error_message=f"API key not found: {model_config.api_key_env_var}",
                latency_ms=int((time.time() - start_time) * 1000)
            )

        # Create LLM client
        client = create_llm_client(
            provider=model_config.provider,
            api_key=api_key,
            model=model_config.model_id,
            base_url=model_config.base_url if model_config.base_url else None,
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens
        )

        # Build prompt based on task type
        prompt = _build_prompt(text, task_type, options)

        # Call LLM
        response = client.generate(prompt)

        # Calculate metrics
        latency_ms = int((time.time() - start_time) * 1000)
        prompt_tokens = _estimate_tokens(prompt)
        response_tokens = _estimate_tokens(response) if response else 0
        total_tokens = prompt_tokens + response_tokens

        # Calculate cost
        estimated_cost = (
            (prompt_tokens / 1000) * model_config.input_cost_per_1k +
            (response_tokens / 1000) * model_config.output_cost_per_1k
        )

        return ModelResult(
            model_id=model_config.id,
            model_name=model_config.name,
            provider=model_config.provider,
            status="success",
            response_text=response,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            estimated_cost=round(estimated_cost, 6)
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"LLM call error for {model_config.name}: {e}")
        return ModelResult(
            model_id=model_config.id,
            model_name=model_config.name,
            provider=model_config.provider,
            status="error",
            error_message=str(e),
            latency_ms=latency_ms
        )


def _build_prompt(text: str, task_type: str, options: Dict[str, Any]) -> str:
    """
    태스크 유형에 따른 프롬프트 생성
    """
    if task_type == "summarize":
        return f"""다음 문서를 요약해주세요. 핵심 내용을 간결하게 정리하되, 중요한 법적 사항은 빠뜨리지 마세요.

문서:
{text}

요약:"""

    elif task_type == "clauses":
        return f"""다음 문서에서 핵심 조항들을 추출해주세요. 각 조항의 유형, 제목, 내용, 중요도를 JSON 형식으로 정리해주세요.

문서:
{text}

조항 목록:"""

    elif task_type == "risk_analysis":
        return f"""다음 문서의 법적 리스크를 분석해주세요.
잠재적 위험 요소, 심각도, 권장 조치를 포함해 분석해주세요.

문서:
{text}

리스크 분석:"""

    elif task_type == "case_analysis":
        return f"""다음 문서를 법적 사건 관점에서 분석해주세요.
당사자, 쟁점, 관련 법규, 예상 결과 등을 정리해주세요.

문서:
{text}

사건 분석:"""

    elif task_type == "chat":
        user_query = options.get("user_query", "")
        return f"""다음 문서를 참고하여 질문에 답변해주세요.

문서:
{text}

질문: {user_query}

답변:"""

    else:  # default/other
        return f"""다음 문서를 분석해주세요:

{text}

분석 결과:"""


# ===== Compare API Endpoint =====

@router.post("/compare", response_model=CompareResponse)
async def compare_models(
    request: CompareRequest,
    app_request: Request,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    POST /v1/llm/compare

    여러 LLM 모델의 응답을 비교합니다.
    각 모델에 동일한 프롬프트를 전송하고 결과, 토큰 사용량, 지연 시간을 비교합니다.

    Args:
        request: CompareRequest (text, task_type, models, session_id, options)
        x_user_id: User ID from header (for logging)

    Returns:
        CompareResponse with results from each model
    """
    logger.info(f"Compare request: session={request.session_id}, task={request.task_type}, models={len(request.models)}")

    if not request.models:
        raise HTTPException(
            status_code=400,
            detail="At least one model is required for comparison"
        )

    if not request.text or len(request.text.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )

    # Run LLM calls concurrently using ThreadPoolExecutor
    loop = asyncio.get_event_loop()

    # Create tasks for each model
    tasks = [
        loop.run_in_executor(
            _executor,
            _call_llm_sync,
            model,
            request.text,
            request.task_type,
            request.options or {}
        )
        for model in request.models
    ]

    # Wait for all tasks to complete
    results: List[ModelResult] = await asyncio.gather(*tasks)

    # Calculate summary statistics
    successful_results = [r for r in results if r.status == "success"]

    fastest_model = None
    cheapest_model = None

    if successful_results:
        # Find fastest model
        fastest = min(successful_results, key=lambda r: r.latency_ms)
        fastest_model = fastest.model_name

        # Find cheapest model
        cheapest = min(successful_results, key=lambda r: r.estimated_cost)
        cheapest_model = cheapest.model_name

    # Build summary
    summary = {
        "total_models": len(results),
        "successful": len(successful_results),
        "failed": len(results) - len(successful_results),
        "avg_latency_ms": sum(r.latency_ms for r in successful_results) // len(successful_results) if successful_results else 0,
        "total_tokens": sum(r.total_tokens for r in successful_results),
        "total_cost": round(sum(r.estimated_cost for r in successful_results), 6)
    }

    logger.info(f"Compare complete: session={request.session_id}, success={len(successful_results)}/{len(results)}")

    return CompareResponse(
        session_id=request.session_id,
        results=results,
        fastest_model=fastest_model,
        cheapest_model=cheapest_model,
        summary=summary
    )
