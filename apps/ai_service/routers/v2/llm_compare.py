"""
V2 LLM Compare Router - LangGraph Based

Phase 4 - Week 12: LangGraph 기반 LLM 비교 API

특징:
- LangGraph StateGraph 기반 워크플로우
- Checkpointing 필수 (Human-in-the-Loop)
- 모델 결과 불일치 시 사용자 선택 요청
- TTL: 1시간

엔드포인트:
- POST /v2/llm/compare - LLM 비교 시작
- POST /v2/llm/select - 사용자 모델 선택 후 재개
- GET /v2/llm/status/{session_id} - 비교 상태 조회
- GET /v2/llm/models - 지원 모델 목록 조회
- GET /v2/llm/health - 헬스체크
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uuid

from apps.ai_service.workflows.llm_comparison_workflow import (
    create_llm_comparison_workflow,
    run_llm_comparison,
    resume_llm_comparison,
    AGREEMENT_THRESHOLD,
)
from apps.ai_service.workflows.states.llm_comparison_state import (
    LLMComparisonState,
    LLMModelConfig,
    ModelMetrics,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/llm", tags=["llm-compare-v2"])


# ===== Request/Response Models =====

class ModelConfigRequest(BaseModel):
    """모델 설정 요청"""
    model_name: str = Field(..., description="모델 이름 (gpt-4, claude-3 등)")
    provider: Optional[str] = Field(None, description="제공자 (openai, anthropic 등)")
    temperature: Optional[float] = Field(0.7, description="생성 온도", ge=0, le=2)
    max_tokens: Optional[int] = Field(None, description="최대 토큰 수")


class LLMCompareRequest(BaseModel):
    """LLM 비교 요청"""
    task: str = Field(
        ...,
        description="작업 유형 (summarize, analyze, extract_clauses 등)"
    )
    input_data: Dict[str, Any] = Field(
        ...,
        description="입력 데이터 (text, prompt 등)"
    )
    models: List[ModelConfigRequest] = Field(
        ...,
        description="비교할 모델 리스트",
        min_length=2,
        max_length=5
    )
    session_id: Optional[str] = Field(None, description="세션 ID (재개 시 사용)")


class ModelSelectRequest(BaseModel):
    """모델 선택 요청 (Human-in-the-Loop)"""
    session_id: str = Field(..., description="세션 ID")
    selected_model: str = Field(..., description="선택한 모델 이름")


class ModelResultResponse(BaseModel):
    """모델 결과"""
    model_name: str
    result: Optional[str] = None
    latency: float = 0.0
    tokens: int = 0
    cost: float = 0.0
    error: Optional[str] = None


class ModelMetricsResponse(BaseModel):
    """모델 메트릭"""
    model_name: str
    quality: float = 0.0
    latency: float = 0.0
    latency_normalized: float = 0.0
    cost: float = 0.0
    cost_normalized: float = 0.0
    tokens: int = 0
    error: Optional[str] = None


class LLMCompareResponse(BaseModel):
    """LLM 비교 응답"""
    success: bool
    task: str
    results: Dict[str, ModelResultResponse] = {}
    metrics: Dict[str, ModelMetricsResponse] = {}
    agreement_score: float = 0.0
    best_model: Optional[str] = None
    user_selected: bool = False
    awaiting_selection: bool = False
    completed_tasks: List[str] = []
    processing_time: float = 0.0
    session_id: str
    error: Optional[str] = None
    timestamp: str
    version: str = "v2"


# ===== API Endpoints =====

@router.post("/compare", response_model=LLMCompareResponse)
async def compare_llm_models(request: LLMCompareRequest):
    """
    LLM 모델 비교 시작 (v2)

    워크플로우:
    1. dispatch_to_models: 여러 모델에 병렬로 작업 전송
    2. evaluate_results: 각 모델 결과 평가
    3. check_agreement: 모델 간 결과 일치도 확인
    4. [조건부] user_choice: 결과 불일치 시 사용자 선택 (Human-in-the-Loop)
    5. select_best_model: 최적 모델 선택

    Args:
        request: LLM 비교 요청

    Returns:
        비교 결과
        - awaiting_selection=True: 사용자 선택 대기 중 (select 필요)
        - awaiting_selection=False: 비교 완료
    """
    start_time = datetime.now()

    try:
        logger.info(f"[v2/llm/compare] task={request.task}, models={[m.model_name for m in request.models]}")

        # 모델 설정 변환
        model_configs = [
            {
                "model_name": m.model_name,
                "provider": m.provider,
                "temperature": m.temperature,
                "max_tokens": m.max_tokens,
            }
            for m in request.models
        ]

        # 세션 ID 생성
        session_id = request.session_id or str(uuid.uuid4())

        # 워크플로우 실행
        try:
            result = await run_llm_comparison(
                task=request.task,
                input_data=request.input_data,
                model_configs=model_configs,
                thread_id=session_id,
            )
        except Exception as workflow_error:
            # interrupt로 중단된 경우 처리
            if "interrupt" in str(workflow_error).lower():
                # 워크플로우가 중단됨 - 사용자 선택 대기
                return LLMCompareResponse(
                    success=True,
                    task=request.task,
                    results={},
                    metrics={},
                    agreement_score=0.0,
                    best_model=None,
                    user_selected=False,
                    awaiting_selection=True,
                    completed_tasks=["dispatch_to_models", "evaluate_results", "check_agreement"],
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    session_id=session_id,
                    error=None,
                    timestamp=datetime.now().isoformat()
                )
            raise

        # 응답 생성
        processing_time = (datetime.now() - start_time).total_seconds()
        return _build_response(result, request.task, session_id, processing_time)

    except Exception as e:
        logger.error(f"[v2/llm/compare] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/select", response_model=LLMCompareResponse)
async def select_best_model(request: ModelSelectRequest):
    """
    사용자 모델 선택 후 비교 재개 (v2)

    Human-in-the-Loop 패턴:
    1. /compare에서 awaiting_selection=True 반환
    2. 사용자가 결과 확인 후 모델 선택
    3. /select로 선택 결과 제출
    4. 워크플로우 재개 -> 최종 결과 반환

    Args:
        request: 모델 선택 요청 (session_id + selected_model)

    Returns:
        최종 비교 결과
    """
    start_time = datetime.now()

    try:
        logger.info(f"[v2/llm/select] session_id={request.session_id}, model={request.selected_model}")

        # 워크플로우 재개
        workflow = create_llm_comparison_workflow()

        result = await resume_llm_comparison(
            workflow=workflow,
            thread_id=request.session_id,
            user_choice=request.selected_model,
        )

        # 응답 생성
        processing_time = (datetime.now() - start_time).total_seconds()

        # result에서 task 추출 (없으면 기본값)
        task = result.get("task", "compare")

        return _build_response(result, task, request.session_id, processing_time)

    except Exception as e:
        logger.error(f"[v2/llm/select] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/status/{session_id}")
async def get_compare_status(session_id: str):
    """
    LLM 비교 상태 조회

    Checkpointing된 워크플로우 상태 조회

    Args:
        session_id: 세션 ID

    Returns:
        현재 비교 상태
    """
    try:
        logger.info(f"[v2/llm/status] session_id={session_id}")

        # 워크플로우 인스턴스 생성
        workflow = create_llm_comparison_workflow()

        # 상태 조회 (Checkpointer에서)
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }

        try:
            state = await workflow.aget_state(config)

            if state and state.values:
                return {
                    "session_id": session_id,
                    "status": "found",
                    "task": state.values.get("task", ""),
                    "completed_tasks": state.values.get("completed_tasks", []),
                    "agreement_score": state.values.get("agreement_score", 0.0),
                    "best_model": state.values.get("best_model"),
                    "user_preference": state.values.get("user_preference"),
                    "has_results": bool(state.values.get("results")),
                    "error": state.values.get("error"),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "session_id": session_id,
                    "status": "not_found",
                    "message": "No checkpoint found for this session",
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.warning(f"Failed to get state: {e}")
            return {
                "session_id": session_id,
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"[v2/llm/status] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/models")
async def get_supported_models():
    """
    지원 모델 목록 조회

    Returns:
        지원 모델 목록 및 메타데이터
    """
    from apps.ai_service.mcp.tools.llm_tools import get_model_metadata

    models = [
        "gpt-4",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku",
        "gemini-pro",
    ]

    model_info = []
    for model in models:
        try:
            metadata = await get_model_metadata(model)
            model_info.append(metadata)
        except Exception as e:
            model_info.append({
                "model_name": model,
                "provider": "unknown",
                "error": str(e)
            })

    return {
        "models": model_info,
        "default_models": ["gpt-4", "claude-3-sonnet"],
        "agreement_threshold": AGREEMENT_THRESHOLD,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health")
async def llm_compare_v2_health():
    """
    LLM Compare v2 헬스체크

    Returns:
        상태 정보
    """
    try:
        # 워크플로우 초기화 테스트
        workflow = create_llm_comparison_workflow()

        return {
            "status": "healthy",
            "version": "v2",
            "engine": "LangGraph",
            "workflow": "llm_comparison_workflow",
            "features": [
                "parallel_execution",
                "checkpointing",
                "human_in_the_loop",
                "metrics_evaluation",
                "auto_selection",
            ],
            "checkpointing": True,
            "checkpoint_ttl": "1 hour",
            "agreement_threshold": AGREEMENT_THRESHOLD,
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
    task: str,
    session_id: str,
    processing_time: float
) -> LLMCompareResponse:
    """
    워크플로우 결과를 응답 모델로 변환
    """
    # Results 변환
    results = {}
    for model_name, model_result in result.get("results", {}).items():
        if isinstance(model_result, dict):
            results[model_name] = ModelResultResponse(
                model_name=model_name,
                result=model_result.get("result"),
                latency=model_result.get("latency", 0.0),
                tokens=model_result.get("tokens", 0),
                cost=model_result.get("cost", 0.0),
                error=model_result.get("error"),
            )
        else:
            results[model_name] = ModelResultResponse(
                model_name=model_name,
                result=str(model_result) if model_result else None,
            )

    # Metrics 변환
    metrics = {}
    for model_name, metric in result.get("evaluation_metrics", {}).items():
        metrics[model_name] = ModelMetricsResponse(
            model_name=model_name,
            quality=metric.get("quality", 0.0),
            latency=metric.get("latency", 0.0),
            latency_normalized=metric.get("latency_normalized", 0.0),
            cost=metric.get("cost", 0.0),
            cost_normalized=metric.get("cost_normalized", 0.0),
            tokens=metric.get("tokens", 0),
            error=metric.get("error"),
        )

    # 사용자 선택 여부
    user_selected = result.get("user_preference") is not None

    # 대기 여부 (agreement_score가 threshold 미만이고 best_model이 없는 경우)
    agreement_score = result.get("agreement_score", 0.0)
    awaiting_selection = (
        agreement_score < AGREEMENT_THRESHOLD and
        result.get("best_model") is None and
        not user_selected
    )

    return LLMCompareResponse(
        success=result.get("error") is None,
        task=task,
        results=results,
        metrics=metrics,
        agreement_score=agreement_score,
        best_model=result.get("best_model"),
        user_selected=user_selected,
        awaiting_selection=awaiting_selection,
        completed_tasks=result.get("completed_tasks", []),
        processing_time=processing_time,
        session_id=session_id,
        error=result.get("error"),
        timestamp=datetime.now().isoformat()
    )
