"""
V2 Case Router - LangGraph Based

Phase 4 - Week 12: LangGraph 기반 사건 분석 API

특징:
- LangGraph StateGraph 기반 워크플로우
- 병렬 실행 (analyze_issues + search_precedents)
- Checkpointing 불필요 (빠른 실행)
- 기존 v1 API와 호환성 유지

엔드포인트:
- POST /v2/cases/analyze - 사건 분석
- GET /v2/cases/health - 헬스체크
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from apps.ai_service.workflows.case_workflow import CaseWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/cases", tags=["cases-v2"])


# ===== Request/Response Models =====

class PartyV2(BaseModel):
    """당사자 정보 (v2)"""
    role: str = Field(..., description="역할 (plaintiff, defendant, third_party)")
    name: str = Field(..., description="이름")
    description: Optional[str] = Field(None, description="설명")


class IssueV2(BaseModel):
    """법적 쟁점 (v2)"""
    issue_type: str = Field(..., description="쟁점 유형")
    description: str = Field(..., description="쟁점 설명")
    legal_basis: Optional[str] = Field(None, description="관련 법조항")


class PrecedentV2(BaseModel):
    """관련 판례 (v2)"""
    case_number: str = Field("", description="사건번호")
    title: str = Field(..., description="제목")
    summary: str = Field(..., description="요약")
    relevance_score: float = Field(0.0, description="관련도 점수")


class CaseAnalyzeRequest(BaseModel):
    """사건 분석 요청"""
    case_content: str = Field(..., description="사건 내용", min_length=50)
    case_type: str = Field(
        "other",
        description="사건 유형 (civil, criminal, administrative, family, other)"
    )
    session_id: Optional[str] = Field(None, description="세션 ID")


class CaseAnalyzeResponse(BaseModel):
    """사건 분석 응답"""
    success: bool
    case_type: str
    parties: List[PartyV2] = []
    issues: List[IssueV2] = []
    related_precedents: List[PrecedentV2] = []
    analysis: Optional[str] = None
    completed_tasks: List[str] = []
    processing_time: float
    session_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: str
    version: str = "v2"


# ===== API Endpoints =====

@router.post("/analyze", response_model=CaseAnalyzeResponse)
async def analyze_case(request: CaseAnalyzeRequest):
    """
    사건 분석 (v2)

    워크플로우:
    1. extract_info: 당사자 및 사건 정보 추출
    2. analyze_issues + search_precedents: 병렬 실행
    3. generate_analysis: 종합 분석 생성

    Args:
        request: 사건 분석 요청

    Returns:
        사건 분석 결과
    """
    try:
        logger.info(f"[v2/cases/analyze] content_len={len(request.case_content)}, type={request.case_type}")

        # 워크플로우 실행
        workflow = CaseWorkflow()
        result = await workflow.arun(
            case_content=request.case_content,
            case_type=request.case_type,
            session_id=request.session_id
        )

        # 응답 생성
        return _build_response(result)

    except Exception as e:
        logger.error(f"[v2/cases/analyze] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/health")
async def case_v2_health():
    """
    Case v2 헬스체크

    Returns:
        상태 정보
    """
    try:
        # 워크플로우 초기화 테스트
        workflow = CaseWorkflow()

        return {
            "status": "healthy",
            "version": "v2",
            "engine": "LangGraph",
            "workflow": "case_analysis_workflow",
            "features": [
                "parallel_execution",
                "party_extraction",
                "issue_analysis",
                "precedent_search",
                "comprehensive_analysis"
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

def _build_response(result: Dict[str, Any]) -> CaseAnalyzeResponse:
    """
    워크플로우 결과를 응답 모델로 변환
    """
    # Parties 변환
    parties = []
    for party_data in result.get("parties", []):
        parties.append(PartyV2(
            role=party_data.get("role", "unknown"),
            name=party_data.get("name", ""),
            description=party_data.get("description")
        ))

    # Issues 변환
    issues = []
    for issue_data in result.get("issues", []):
        issues.append(IssueV2(
            issue_type=issue_data.get("issue_type", ""),
            description=issue_data.get("description", ""),
            legal_basis=issue_data.get("legal_basis")
        ))

    # Precedents 변환
    precedents = []
    for prec_data in result.get("related_precedents", []):
        precedents.append(PrecedentV2(
            case_number=prec_data.get("case_number", ""),
            title=prec_data.get("title", ""),
            summary=prec_data.get("summary", ""),
            relevance_score=prec_data.get("relevance_score", 0.0)
        ))

    return CaseAnalyzeResponse(
        success=result.get("success", False),
        case_type=result.get("case_type", "other"),
        parties=parties,
        issues=issues,
        related_precedents=precedents,
        analysis=result.get("analysis"),
        completed_tasks=result.get("completed_tasks", []),
        processing_time=result.get("processing_time", 0),
        session_id=result.get("session_id"),
        error=result.get("error"),
        timestamp=datetime.now().isoformat()
    )
