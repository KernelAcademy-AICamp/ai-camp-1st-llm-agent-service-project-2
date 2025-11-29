"""
V2 Risk Router - LangGraph Based

Phase 4 - Week 12: LangGraph 기반 리스크 분석 API

특징:
- LangGraph StateGraph 기반 워크플로우
- Checkpointing 필수 (Human-in-the-Loop)
- 고위험 리스크 발견 시 전문가 검토 요청
- TTL: 7일

엔드포인트:
- POST /v2/risk/analyze - 리스크 분석 시작
- POST /v2/risk/resume - 전문가 검토 후 재개
- GET /v2/risk/status/{session_id} - 분석 상태 조회
- GET /v2/risk/health - 헬스체크
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from apps.ai_service.workflows.risk_workflow import RiskWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/risk", tags=["risk-v2"])


# ===== Request/Response Models =====

class RiskItemV2(BaseModel):
    """리스크 항목 (v2)"""
    risk_type: str = Field(..., description="리스크 유형")
    description: str = Field(..., description="리스크 설명")
    severity: str = Field(..., description="심각도 (CRITICAL/HIGH/MEDIUM/LOW/INFO)")
    recommendation: Optional[str] = Field(None, description="권장 조치")
    clause_reference: Optional[str] = Field(None, description="관련 조항")


class HumanReviewV2(BaseModel):
    """전문가 검토 결과 (v2)"""
    approved: bool = Field(..., description="승인 여부")
    comments: Optional[str] = Field(None, description="검토 의견")
    modified_risks: Optional[List[RiskItemV2]] = Field(None, description="수정된 리스크 목록")


class RiskAnalyzeRequest(BaseModel):
    """리스크 분석 요청"""
    text: str = Field(..., description="분석할 텍스트", min_length=50)
    doc_type: str = Field(
        "CONTRACT",
        description="문서 유형 (CONTRACT, STATUTE, PRECEDENT, OTHER)"
    )
    document_id: Optional[str] = Field(None, description="문서 ID")
    session_id: Optional[str] = Field(None, description="세션 ID (재개 시 사용)")


class RiskResumeRequest(BaseModel):
    """전문가 검토 후 재개 요청"""
    session_id: str = Field(..., description="세션 ID (thread_id)")
    human_review: HumanReviewV2 = Field(..., description="전문가 검토 결과")


class RiskAnalyzeResponse(BaseModel):
    """리스크 분석 응답"""
    success: bool
    document_id: Optional[str] = None
    doc_type: str
    identified_risks: List[RiskItemV2] = []
    requires_human_review: bool = False
    awaiting_review: bool = False
    human_review: Optional[HumanReviewV2] = None
    report: Optional[str] = None
    completed_tasks: List[str] = []
    processing_time: float
    session_id: str
    error: Optional[str] = None
    timestamp: str
    version: str = "v2"


# ===== API Endpoints =====

@router.post("/analyze", response_model=RiskAnalyzeResponse)
async def analyze_risk(request: RiskAnalyzeRequest):
    """
    리스크 분석 시작 (v2)

    워크플로우:
    1. identify_risks: 리스크 식별
    2. assess_severity: 심각도 평가
    3. [조건부] human_review: 전문가 검토 (CRITICAL/HIGH 리스크 시)
    4. generate_report: 보고서 생성

    Args:
        request: 리스크 분석 요청

    Returns:
        리스크 분석 결과
        - awaiting_review=True: 전문가 검토 대기 중 (resume 필요)
        - awaiting_review=False: 분석 완료
    """
    try:
        logger.info(f"[v2/risk/analyze] text_len={len(request.text)}, type={request.doc_type}")

        # 워크플로우 실행
        workflow = RiskWorkflow(use_checkpointing=True)
        result = await workflow.arun(
            text=request.text,
            doc_type=request.doc_type,
            document_id=request.document_id,
            session_id=request.session_id
        )

        # 응답 생성
        return _build_response(result)

    except Exception as e:
        logger.error(f"[v2/risk/analyze] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/resume", response_model=RiskAnalyzeResponse)
async def resume_risk_analysis(request: RiskResumeRequest):
    """
    전문가 검토 후 리스크 분석 재개 (v2)

    Human-in-the-Loop 패턴:
    1. /analyze에서 awaiting_review=True 반환
    2. 전문가가 리스크 검토
    3. /resume으로 검토 결과 제출
    4. 워크플로우 재개 -> 보고서 생성

    Args:
        request: 재개 요청 (session_id + human_review)

    Returns:
        최종 리스크 분석 결과
    """
    try:
        logger.info(f"[v2/risk/resume] session_id={request.session_id}")

        # 워크플로우 재개
        workflow = RiskWorkflow(use_checkpointing=True)

        # HumanReviewV2 -> dict 변환
        human_review_dict = {
            "approved": request.human_review.approved,
            "comments": request.human_review.comments,
        }
        if request.human_review.modified_risks:
            human_review_dict["modified_risks"] = [
                {
                    "risk_type": r.risk_type,
                    "description": r.description,
                    "severity": r.severity,
                    "recommendation": r.recommendation,
                    "clause_reference": r.clause_reference,
                }
                for r in request.human_review.modified_risks
            ]

        result = await workflow.resume(
            thread_id=request.session_id,
            human_review=human_review_dict
        )

        # 응답 생성
        return _build_response(result)

    except Exception as e:
        logger.error(f"[v2/risk/resume] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/status/{session_id}")
async def get_risk_status(session_id: str):
    """
    리스크 분석 상태 조회

    Checkpointing된 워크플로우 상태 조회

    Args:
        session_id: 세션 ID

    Returns:
        현재 분석 상태
    """
    try:
        logger.info(f"[v2/risk/status] session_id={session_id}")

        # 워크플로우 인스턴스 생성
        workflow = RiskWorkflow(use_checkpointing=True)

        # 상태 조회 (Checkpointer에서)
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }

        try:
            state = await workflow.graph.aget_state(config)

            if state and state.values:
                return {
                    "session_id": session_id,
                    "status": "found",
                    "completed_tasks": state.values.get("completed_tasks", []),
                    "requires_human_review": state.values.get("requires_human_review", False),
                    "has_report": state.values.get("report") is not None,
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
        logger.error(f"[v2/risk/status] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/health")
async def risk_v2_health():
    """
    Risk v2 헬스체크

    Returns:
        상태 정보
    """
    try:
        # 워크플로우 초기화 테스트
        workflow = RiskWorkflow(use_checkpointing=True)

        return {
            "status": "healthy",
            "version": "v2",
            "engine": "LangGraph",
            "workflow": "risk_analysis_workflow",
            "features": [
                "checkpointing",
                "human_in_the_loop",
                "risk_identification",
                "severity_assessment",
                "report_generation"
            ],
            "checkpointing": True,
            "checkpoint_ttl": "7 days",
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

def _build_response(result: Dict[str, Any]) -> RiskAnalyzeResponse:
    """
    워크플로우 결과를 응답 모델로 변환
    """
    # Risks 변환
    risks = []
    for risk_data in result.get("identified_risks", []):
        risks.append(RiskItemV2(
            risk_type=risk_data.get("risk_type", "OTHER"),
            description=risk_data.get("description", ""),
            severity=risk_data.get("severity", "MEDIUM"),
            recommendation=risk_data.get("recommendation"),
            clause_reference=risk_data.get("clause_reference")
        ))

    # Human review 변환
    human_review = None
    if result.get("human_review"):
        hr_data = result["human_review"]
        human_review = HumanReviewV2(
            approved=hr_data.get("approved", False),
            comments=hr_data.get("comments"),
            modified_risks=None  # 간소화
        )

    return RiskAnalyzeResponse(
        success=result.get("success", False),
        document_id=result.get("document_id"),
        doc_type=result.get("doc_type", "CONTRACT"),
        identified_risks=risks,
        requires_human_review=result.get("requires_human_review", False),
        awaiting_review=result.get("awaiting_review", False),
        human_review=human_review,
        report=result.get("report"),
        completed_tasks=result.get("completed_tasks", []),
        processing_time=result.get("processing_time", 0),
        session_id=result.get("session_id", ""),
        error=result.get("error"),
        timestamp=datetime.now().isoformat()
    )
