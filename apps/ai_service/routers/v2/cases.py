"""
V2 Case Router - LangGraph Based

Phase 4 - Week 12: LangGraph 기반 사건 분석 API
Phase 1 - 형사법 특화: 구성요건 분석, 양형인자, 양형 예측, 변호 전략

특징:
- LangGraph StateGraph 기반 워크플로우
- 병렬 실행 (analyze_issues + search_precedents)
- Checkpointing 불필요 (빠른 실행)
- 기존 v1 API와 호환성 유지
- 형사 사건 전문 분석 기능 추가

엔드포인트:
- POST /v2/cases/analyze - 사건 분석
- POST /v2/cases/criminal/analyze - 형사 사건 분석
- POST /v2/cases/criminal/analyze-files - 형사 사건 파일 분석
- POST /v2/cases/criminal/analyze-and-save - 형사 사건 분석 + DB 저장
- GET /v2/cases/health - 헬스체크
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import io

from apps.ai_service.workflows.case_workflow import CaseWorkflow
from apps.ai_service.workflows.criminal_workflow import CriminalCaseWorkflow
from apps.ai_service.services.case_analyzer import CaseAnalyzer
from apps.ai_service.models.database import get_write_db
from apps.ai_service.middleware.auth import verify_token
from apps.ai_service.models.criminal_analysis import (
    CriminalAnalysisResult,
    CriminalAnalyzeRequest,
    CriminalAnalyzeResponse,
    CrimeElements,
    SentencingFactors,
    ExpectedSentence,
    CriminalPrecedent,
)
from apps.ai_service.models.criminal_case import (
    CriminalCaseResponse,
    CriminalCaseUpdate,
    CriminalCaseWithAnalysis,
    CriminalStage,
)
from apps.ai_service.services.criminal_case_service import CriminalCaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/cases", tags=["cases-v2"])


# ===== Helper: Crime Type Translation =====

# 영어 → 한국어 범죄 유형 매핑
ENGLISH_TO_KOREAN_CRIME_TYPES = {
    "theft": "절도",
    "robbery": "강도",
    "fraud": "사기",
    "embezzlement": "횡령",
    "breach of trust": "배임",
    "assault": "폭행",
    "battery": "상해",
    "murder": "살인",
    "homicide": "살인",
    "rape": "강간",
    "sexual assault": "성추행",
    "sexual harassment": "성추행",
    "drugs": "마약",
    "drug": "마약",
    "dui": "음주운전",
    "drunk driving": "음주운전",
    "traffic accident": "교통사고",
    "traffic": "교통사고",
    "defamation": "명예훼손",
    "insult": "모욕",
    "threat": "협박",
    "blackmail": "협박",
    "bribery": "뇌물",
    "dereliction of duty": "직무유기",
    "perjury": "위증",
    "forgery": "위조",
    "arson": "방화",
    "kidnapping": "납치",
}


def ensure_korean_crime_type(crime_type: Optional[str]) -> str:
    """
    범죄 유형을 한국어로 변환

    Args:
        crime_type: 범죄 유형 (한국어 또는 영어)

    Returns:
        한국어 범죄 유형
    """
    if not crime_type:
        return "형사"

    # 이미 한국어인 경우 그대로 반환
    korean_crime_types = [
        "절도", "강도", "사기", "횡령", "배임",
        "폭행", "상해", "살인", "강간", "성추행",
        "마약", "음주운전", "교통사고",
        "명예훼손", "모욕", "협박",
        "뇌물", "직무유기", "위증",
    ]

    for korean in korean_crime_types:
        if korean in crime_type:
            return korean

    # 영어를 한국어로 변환
    crime_lower = crime_type.lower().strip()
    for eng, kor in ENGLISH_TO_KOREAN_CRIME_TYPES.items():
        if eng in crime_lower:
            return kor

    # 매핑되지 않으면 "형사" 반환
    return "형사"


# ===== Helper: Document Indexing =====

async def index_criminal_case_documents(
    texts: List[str],
    case_id: str,
    crime_type: str,
) -> Dict[str, Any]:
    """
    형사 사건 문서를 벡터DB에 인덱싱

    Args:
        texts: 문서 텍스트 목록
        case_id: 사건 ID
        crime_type: 범죄 유형

    Returns:
        인덱싱 결과
    """
    try:
        from main import app
        from apps.ai_service.services.document_processor import DocumentProcessor

        document_indexer = getattr(app.state, 'document_indexer', None)
        if not document_indexer:
            logger.warning("[index_criminal_case_documents] DocumentIndexer not available")
            return {"success": False, "error": "DocumentIndexer not initialized"}

        # 모든 텍스트를 합쳐서 청킹
        combined_text = "\n\n".join(texts)

        # 청킹
        processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
        chunks = processor.chunk_text(combined_text)

        if not chunks:
            logger.warning(f"[index_criminal_case_documents] No chunks generated for case {case_id}")
            return {"success": False, "error": "No chunks generated"}

        # 인덱싱
        result = document_indexer.index_chunks(
            chunks=chunks,
            document_id=f"criminal_case_{case_id}",
            document_metadata={
                "doc_type": "CRIMINAL_CASE",
                "crime_type": crime_type,
                "case_id": case_id,
            }
        )

        logger.info(f"[index_criminal_case_documents] Indexed {result.get('indexed_count', 0)} chunks for case {case_id}")
        return result

    except Exception as e:
        logger.error(f"[index_criminal_case_documents] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def get_llm_client_from_app(app_state) -> Any:
    """앱 상태에서 LLM 클라이언트 가져오기 (없으면 생성)"""
    llm_client = getattr(app_state, 'llm_client', None)
    if llm_client is None:
        from libs.rag_core.llm.llm_client import create_llm_client
        import os
        llm_client = create_llm_client(
            model_name=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            provider=os.getenv("LLM_PROVIDER", "openai"),
        )
    return llm_client


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
                "comprehensive_analysis",
                "criminal_analysis",  # Phase 1: 형사법 특화
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


# ===== 형사 사건 분석 API (Phase 1: 형사법 특화) =====

class CriminalCaseAnalyzeRequest(BaseModel):
    """형사 사건 분석 요청"""
    case_content: str = Field(..., description="사건 내용", min_length=30)
    crime_type: Optional[str] = Field(
        None,
        description="범죄 유형 (선택, 미지정시 자동 감지)"
    )
    session_id: Optional[str] = Field(None, description="세션 ID")


class CriminalCaseAnalyzeResponse(BaseModel):
    """형사 사건 분석 응답"""
    success: bool
    case_id: Optional[str] = None
    summary: str = ""
    crime_type: str = ""
    crime_elements: Dict[str, Any] = {}
    sentencing_factors: Dict[str, Any] = {}
    expected_sentence: Dict[str, Any] = {}
    defense_strategies: List[str] = []
    related_precedents: List[Dict[str, Any]] = []
    processing_time: float = 0.0
    error: Optional[str] = None
    timestamp: str = ""
    version: str = "v2"


@router.post("/criminal/analyze", response_model=CriminalCaseAnalyzeResponse)
async def analyze_criminal_case(http_request: Request, request: CriminalCaseAnalyzeRequest):
    """
    형사 사건 분석 (Phase 1: 형사법 특화) - LangGraph Workflow

    워크플로우:
    1. detect_crime_node: 범죄 유형 자동 감지
    2. plan_analysis_node: 범죄 카테고리별 분석 계획 수립
    3. [조건부 분기] route_by_category:
       - property: 재산범죄 분석 (피해액 중심)
       - violent: 폭력범죄 분석 (상해정도 중심)
       - traffic: 교통범죄 분석 (혈중농도, 전과)
       - general: 공통 분석
    4. analyze_elements_node: 구성요건 분석 (객관적/주관적)
    5. extract_factors_node: 양형인자 추출 (유리/불리)
    6. estimate_sentence_node: 예상 양형 산정
    7. suggest_defense_node: 변호 전략 제안
    8. search_precedents_node: 관련 판례 검색

    Args:
        request: 형사 사건 분석 요청

    Returns:
        형사 사건 분석 결과
    """
    import time
    start_time = time.time()

    try:
        logger.info(f"[v2/cases/criminal/analyze] content_len={len(request.case_content)}, crime_type={request.crime_type}")

        # CriminalCaseWorkflow 사용 (LangGraph 기반)
        workflow = CriminalCaseWorkflow()
        result = await workflow.arun(
            texts=[request.case_content],
            filenames=["user_input.txt"],
            crime_type=request.crime_type,
        )

        processing_time = time.time() - start_time

        # 응답 생성
        return CriminalCaseAnalyzeResponse(
            success=result.get("success", True),
            case_id=request.session_id,
            summary=result.get("summary", ""),
            crime_type=result.get("crime_type", ""),
            crime_elements=result.get("crime_elements") or {},
            sentencing_factors=result.get("sentencing_factors") or {},
            expected_sentence=result.get("expected_sentence") or {},
            defense_strategies=result.get("defense_strategies", []),
            related_precedents=result.get("related_precedents", []),
            processing_time=processing_time,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"[v2/cases/criminal/analyze] Error: {e}", exc_info=True)
        return CriminalCaseAnalyzeResponse(
            success=False,
            error=str(e),
            processing_time=time.time() - start_time,
            timestamp=datetime.now().isoformat(),
        )


@router.post("/criminal/analyze-files")
async def analyze_criminal_case_files(
    request: Request,
    files: List[UploadFile] = File(..., description="분석할 파일들"),
    crime_type: Optional[str] = Form(None, description="범죄 유형 (선택)"),
    session_id: Optional[str] = Form(None, description="세션 ID"),
):
    """
    형사 사건 파일 분석 (Phase 1: 형사법 특화) - LangGraph Workflow

    여러 파일을 업로드하여 형사 사건을 분석합니다.
    지원 형식: txt, pdf, docx

    워크플로우:
    1. detect_crime_node: 범죄 유형 자동 감지
    2. plan_analysis_node: 범죄 카테고리별 분석 계획 수립
    3. [조건부 분기] route_by_category
    4. common_analysis: 구성요건/양형인자/양형예측
    5. suggest_defense_node: 변호 전략 제안
    6. search_precedents_node: 관련 판례 검색

    Args:
        files: 분석할 파일들
        crime_type: 범죄 유형 (선택)
        session_id: 세션 ID

    Returns:
        형사 사건 분석 결과
    """
    import time
    start_time = time.time()

    try:
        logger.info(f"[v2/cases/criminal/analyze-files] files={len(files)}, crime_type={crime_type}")

        texts = []
        filenames = []

        for file in files:
            content = await file.read()

            # 파일 형식에 따른 텍스트 추출
            if file.filename.endswith('.txt'):
                text = content.decode('utf-8', errors='ignore')
            elif file.filename.endswith('.pdf'):
                # PDF 처리 (간단한 구현)
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                    text = "\n".join([page.extract_text() or "" for page in pdf_reader.pages])
                except ImportError:
                    text = content.decode('utf-8', errors='ignore')
            else:
                text = content.decode('utf-8', errors='ignore')

            texts.append(text)
            filenames.append(file.filename)

        # CriminalCaseWorkflow 사용 (LangGraph 기반)
        workflow = CriminalCaseWorkflow()
        result = await workflow.arun(
            texts=texts,
            filenames=filenames,
            crime_type=crime_type,
        )

        processing_time = time.time() - start_time

        return {
            "success": result.get("success", True),
            "case_id": session_id,
            "files_analyzed": len(files),
            "summary": result.get("summary", ""),
            "crime_type": result.get("crime_type", ""),
            "crime_elements": result.get("crime_elements") or {},
            "sentencing_factors": result.get("sentencing_factors") or {},
            "expected_sentence": result.get("expected_sentence") or {},
            "defense_strategies": result.get("defense_strategies", []),
            "related_precedents": result.get("related_precedents", []),
            "completed_tasks": result.get("completed_tasks", []),
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat(),
            "version": "v2",
        }

    except Exception as e:
        logger.error(f"[v2/cases/criminal/analyze-files] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "processing_time": time.time() - start_time,
            "timestamp": datetime.now().isoformat(),
            "version": "v2",
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


# ===== 형사 사건 분석 + 저장 API (Phase 1: 형사법 특화) =====

@router.post("/criminal/analyze-and-save", response_model=CriminalCaseResponse, status_code=status.HTTP_201_CREATED)
async def analyze_and_save_criminal_case(
    http_request: Request,
    files: List[UploadFile] = File(..., description="분석할 파일들"),
    case_name: Optional[str] = Form(None, description="사건명 (선택, 미입력시 자동 생성)"),
    crime_type: Optional[str] = Form(None, description="범죄 유형 (선택, 미지정시 자동 감지)"),
    confirmed_texts: Optional[str] = Form(None, description="OCR로 추출된 텍스트 (JSON 형식, 파일명 -> 텍스트)"),
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db),
):
    """
    형사 사건 분석 + DB 저장 (Phase 1: 형사법 특화) - LangGraph Workflow

    파일을 업로드하여 형사 사건을 분석하고, 결과를 DB에 저장합니다.
    CaseManagementV2에서 사용하는 핵심 API입니다.

    워크플로우 기반 처리 흐름:
    1. 파일 텍스트 추출
    2. CriminalCaseWorkflow 실행:
       - detect_crime_node: 범죄 유형 자동 감지
       - plan_analysis_node: 범죄 카테고리별 분석 계획
       - [조건부 분기]: 재산/폭력/교통 범죄 특화 분석
       - analyze_elements_node: 구성요건 분석
       - extract_factors_node: 양형인자 추출
       - estimate_sentence_node: 양형 예측
       - suggest_defense_node: 변호 전략
       - search_precedents_node: 판례 검색
    3. CriminalCaseService로 DB 저장

    Args:
        files: 분석할 파일들 (txt, pdf, docx)
        case_name: 사건명 (선택)
        crime_type: 범죄 유형 (선택)
        user: 인증된 사용자 (JWT 토큰)
        db: DB 세션 (Write)

    Returns:
        저장된 형사 사건 정보 (CriminalCaseResponse)
    """
    import time
    start_time = time.time()

    try:
        # 사용자 ID 검증
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        logger.info(f"[v2/cases/criminal/analyze-and-save] files={len(files)}, user={user_id}, crime_type={crime_type}")

        # OCR로 추출된 텍스트 파싱 (프론트엔드에서 전달)
        confirmed_texts_map: Dict[str, str] = {}
        if confirmed_texts:
            try:
                import json
                confirmed_texts_map = json.loads(confirmed_texts)
                logger.info(f"[v2/cases/criminal/analyze-and-save] Using OCR confirmed texts for {len(confirmed_texts_map)} files")
            except json.JSONDecodeError as e:
                logger.warning(f"[v2/cases/criminal/analyze-and-save] Failed to parse confirmed_texts: {e}")

        # 파일 텍스트 추출
        texts = []
        filenames = []
        file_sizes = []

        for file in files:
            content = await file.read()
            file_sizes.append(len(content))  # 파일 크기 저장

            # OCR로 추출된 텍스트가 있으면 사용 (재추출 스킵)
            if file.filename in confirmed_texts_map:
                text = confirmed_texts_map[file.filename]
                logger.info(f"[v2/cases/criminal/analyze-and-save] Using OCR text for {file.filename} (len={len(text)})")
            else:
                # 파일 형식에 따른 텍스트 추출
                if file.filename.endswith('.txt'):
                    text = content.decode('utf-8', errors='ignore')
                elif file.filename.endswith('.pdf'):
                    try:
                        import PyPDF2
                        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                        text = "\n".join([page.extract_text() or "" for page in pdf_reader.pages])
                    except ImportError:
                        text = content.decode('utf-8', errors='ignore')
                else:
                    text = content.decode('utf-8', errors='ignore')

            texts.append(text)
            filenames.append(file.filename)

        # CriminalCaseWorkflow로 분석 (LangGraph 기반)
        # skip_precedents=True: 판례 검색은 나중에 별도 API로 비동기 처리
        workflow = CriminalCaseWorkflow()
        analysis_result = await workflow.arun(
            texts=texts,
            filenames=filenames,
            user_id=user_id,
            case_name=case_name,
            crime_type=crime_type,
            skip_precedents=True,  # 판례 검색 스킵 (상세 페이지에서 비동기 검색)
        )

        # 사건명 자동 생성 (미입력시)
        korean_crime_type = ensure_korean_crime_type(analysis_result.get('crime_type'))
        final_case_name = case_name or f"{korean_crime_type} 사건"

        # 업로드된 파일 정보 준비 (파일명, 크기, 원문 텍스트 포함)
        uploaded_files = [
            {
                "filename": fn,
                "size": size,
                "content": text,  # 원문 텍스트 저장
                "uploaded_at": datetime.now().isoformat()
            }
            for fn, size, text in zip(filenames, file_sizes, texts)
        ]

        # 형사 절차 단계 결정 (워크플로우에서 감지된 값 사용)
        detected_stage_str = analysis_result.get("criminal_stage", "COMPLAINT")
        try:
            detected_stage = CriminalStage(detected_stage_str)
        except ValueError:
            detected_stage = CriminalStage.COMPLAINT
        logger.info(f"[v2/cases/criminal/analyze-and-save] Detected stage: {detected_stage.value}")

        # CriminalCaseWithAnalysis 객체 생성
        case_data = CriminalCaseWithAnalysis(
            case_name=final_case_name,
            summary=analysis_result.get("summary", ""),
            crime_type=korean_crime_type,  # 한국어로 변환된 범죄 유형 사용
            stage=detected_stage,  # 워크플로우에서 감지된 단계 사용
            crime_elements=analysis_result.get("crime_elements") or {},
            sentencing_factors=analysis_result.get("sentencing_factors") or {},
            expected_sentence=analysis_result.get("expected_sentence") or {},
            defense_strategies=analysis_result.get("defense_strategies", []),
            related_precedents=analysis_result.get("related_precedents", []),
            uploaded_files=uploaded_files,
        )

        # CriminalCaseService로 DB 저장
        case_service = CriminalCaseService(db)
        result = await case_service.create_case_with_analysis(user_id, case_data)

        processing_time = time.time() - start_time
        logger.info(f"[v2/cases/criminal/analyze-and-save] Completed in {processing_time:.2f}s, case_id={result.id}, stage={detected_stage.value}")

        # 문서 인덱싱 (벡터DB에 저장)
        if result and result.id:
            indexing_result = await index_criminal_case_documents(
                texts=texts,
                case_id=str(result.id),
                crime_type=result.crime_type or crime_type or "unknown"
            )
            if indexing_result.get("success"):
                logger.info(f"[v2/cases/criminal/analyze-and-save] Document indexed: {indexing_result.get('indexed_count', 0)} chunks")
            else:
                logger.warning(f"[v2/cases/criminal/analyze-and-save] Document indexing failed: {indexing_result.get('error')}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[v2/cases/criminal/analyze-and-save] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze and save criminal case: {str(e)}"
        )


@router.post("/criminal/analyze-text-and-save", response_model=CriminalCaseResponse, status_code=status.HTTP_201_CREATED)
async def analyze_text_and_save_criminal_case(
    http_request: Request,
    case_content: str = Form(..., description="사건 내용", min_length=30),
    case_name: Optional[str] = Form(None, description="사건명 (선택, 미입력시 자동 생성)"),
    crime_type: Optional[str] = Form(None, description="범죄 유형 (선택, 미지정시 자동 감지)"),
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db),
):
    """
    형사 사건 텍스트 분석 + DB 저장 (Phase 1: 형사법 특화) - LangGraph Workflow

    텍스트를 직접 입력하여 형사 사건을 분석하고, 결과를 DB에 저장합니다.

    워크플로우 기반 처리 흐름:
    1. CriminalCaseWorkflow로 분석
    2. CriminalCaseService로 DB 저장

    Args:
        case_content: 사건 내용 (텍스트)
        case_name: 사건명 (선택)
        crime_type: 범죄 유형 (선택)
        user: 인증된 사용자 (JWT 토큰)
        db: DB 세션 (Write)

    Returns:
        저장된 형사 사건 정보 (CriminalCaseResponse)
    """
    import time
    start_time = time.time()

    try:
        # 사용자 ID 검증
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        logger.info(f"[v2/cases/criminal/analyze-text-and-save] content_len={len(case_content)}, user={user_id}")

        # CriminalCaseWorkflow로 분석 (LangGraph 기반)
        workflow = CriminalCaseWorkflow()
        analysis_result = await workflow.arun(
            texts=[case_content],
            filenames=["user_input.txt"],
            user_id=user_id,
            case_name=case_name,
            crime_type=crime_type,
        )

        # 사건명 자동 생성 (미입력시)
        korean_crime_type = ensure_korean_crime_type(analysis_result.get('crime_type'))
        final_case_name = case_name or f"{korean_crime_type} 사건"

        # 형사 절차 단계 결정 (워크플로우에서 감지된 값 사용)
        detected_stage_str = analysis_result.get("criminal_stage", "COMPLAINT")
        try:
            detected_stage = CriminalStage(detected_stage_str)
        except ValueError:
            detected_stage = CriminalStage.COMPLAINT
        logger.info(f"[v2/cases/criminal/analyze-text-and-save] Detected stage: {detected_stage.value}")

        # CriminalCaseWithAnalysis 객체 생성
        case_data = CriminalCaseWithAnalysis(
            case_name=final_case_name,
            summary=analysis_result.get("summary", ""),
            crime_type=korean_crime_type,  # 한국어로 변환된 범죄 유형 사용
            stage=detected_stage,  # 워크플로우에서 감지된 단계 사용
            crime_elements=analysis_result.get("crime_elements") or {},
            sentencing_factors=analysis_result.get("sentencing_factors") or {},
            expected_sentence=analysis_result.get("expected_sentence") or {},
            defense_strategies=analysis_result.get("defense_strategies", []),
            related_precedents=analysis_result.get("related_precedents", []),
            uploaded_files=[{
                "filename": "user_input.txt",
                "size": len(case_content.encode('utf-8')),
                "content": case_content,
                "uploaded_at": datetime.now().isoformat()
            }],
        )

        # CriminalCaseService로 DB 저장
        case_service = CriminalCaseService(db)
        result = await case_service.create_case_with_analysis(user_id, case_data)

        processing_time = time.time() - start_time
        logger.info(f"[v2/cases/criminal/analyze-text-and-save] Completed in {processing_time:.2f}s, case_id={result.id}, stage={detected_stage.value}")

        # 문서 인덱싱 (벡터DB에 저장)
        if result and result.id:
            indexing_result = await index_criminal_case_documents(
                texts=[case_content],
                case_id=str(result.id),
                crime_type=result.crime_type or crime_type or "unknown"
            )
            if indexing_result.get("success"):
                logger.info(f"[v2/cases/criminal/analyze-text-and-save] Document indexed: {indexing_result.get('indexed_count', 0)} chunks")
            else:
                logger.warning(f"[v2/cases/criminal/analyze-text-and-save] Document indexing failed: {indexing_result.get('error')}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[v2/cases/criminal/analyze-text-and-save] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze and save criminal case: {str(e)}"
        )


# ===== 판례 검색 전용 API (비동기 처리) =====

class SearchPrecedentsRequest(BaseModel):
    """판례 검색 요청"""
    query: Optional[str] = Field(None, description="검색 쿼리 (미입력시 사건 내용 기반 자동 생성)")
    top_k: int = Field(5, ge=1, le=20, description="검색할 판례 수")


class SearchPrecedentsResponse(BaseModel):
    """판례 검색 응답"""
    success: bool
    case_id: str
    precedents: List[Dict[str, Any]] = []
    precedents_status: str = "completed"  # 'pending', 'searching', 'completed', 'failed'
    processing_time: float = 0.0
    error: Optional[str] = None


@router.post("/criminal/cases/{case_id}/search-precedents", response_model=SearchPrecedentsResponse)
async def search_precedents_for_case(
    case_id: str,
    request: SearchPrecedentsRequest = None,
    user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_write_db),
):
    """
    형사 사건에 대한 관련 판례 검색 (비동기 처리용)

    분석 완료 후 상세 페이지에서 호출하여 판례를 검색합니다.
    검색 결과는 DB에 저장되어 다음 조회 시 캐시됩니다.

    Args:
        case_id: 사건 ID
        request: 판례 검색 요청 (선택)
        user: 인증된 사용자
        db: DB 세션

    Returns:
        검색된 판례 목록
    """
    import time
    from apps.ai_service.workflows.criminal_workflow import search_precedents_node

    start_time = time.time()

    try:
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token"
            )

        logger.info(f"[v2/cases/criminal/search-precedents] case_id={case_id}, user={user_id}")

        # 사건 정보 조회
        case_service = CriminalCaseService(db)
        case_data = await case_service.get_case(case_id, user_id)

        if not case_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )

        # 이미 판례가 있으면 반환
        if case_data.related_precedents and len(case_data.related_precedents) > 0:
            return SearchPrecedentsResponse(
                success=True,
                case_id=case_id,
                precedents=case_data.related_precedents,
                precedents_status="completed",
                processing_time=time.time() - start_time,
            )

        # 검색 쿼리 생성 (사건 내용 기반)
        query = request.query if request and request.query else None
        if not query:
            # 사건 요약과 범죄 유형으로 쿼리 생성
            query_parts = []
            if case_data.crime_type:
                query_parts.append(case_data.crime_type)
            if case_data.summary:
                query_parts.append(case_data.summary[:200])
            query = " ".join(query_parts) if query_parts else "형사 판례"

        top_k = request.top_k if request else 5

        # search_precedents_node 호출을 위한 상태 준비
        state = {
            "crime_type": case_data.crime_type or "미상",
            "crime_elements": case_data.crime_elements or {},
            "summary": case_data.summary or "",
            "analysis_plan": [],
            "completed_tasks": [],
        }

        # 판례 검색 실행
        result = await search_precedents_node(state)
        precedents = result.get("related_precedents", [])

        # DB에 판례 정보 업데이트
        if precedents:
            await case_service.update_case(
                case_id=case_id,
                user_id=user_id,
                data=CriminalCaseUpdate(related_precedents=precedents)
            )

        processing_time = time.time() - start_time
        logger.info(f"[v2/cases/criminal/search-precedents] Found {len(precedents)} precedents in {processing_time:.2f}s")

        return SearchPrecedentsResponse(
            success=True,
            case_id=case_id,
            precedents=precedents,
            precedents_status="completed",
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[v2/cases/criminal/search-precedents] Error: {e}", exc_info=True)
        return SearchPrecedentsResponse(
            success=False,
            case_id=case_id,
            precedents=[],
            precedents_status="failed",
            processing_time=time.time() - start_time,
            error=str(e),
        )
