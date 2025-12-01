"""
Document Analysis Workflow

Phase 4 - Week 12: 문서 분석 LangGraph 워크플로우 (Planning Agent 패턴)

워크플로우 흐름:
1. extract_text_node: 문서 텍스트 추출
2. plan_node: LLM이 문서 타입에 따라 분석 계획 수립
3. [조건부] summarize_node / extract_clauses_node / analyze_risk_node
4. plan_node: 다음 작업 결정 (cyclic)
5. aggregate_node: 결과 집계

Cyclic Pattern:
- plan → summarize → plan
- plan → extract_clauses → plan
- plan → analyze_risk → plan
- plan → aggregate (all_done)

Checkpointing: 불필요 (빠른 실행, 10-20초)

사용:
    from apps.ai_service.workflows.document_workflow import (
        create_document_workflow,
        DocumentWorkflow
    )

    # Workflow 클래스 사용
    workflow = DocumentWorkflow()
    result = await workflow.arun(file_path="/path/to/file.pdf")
"""

from typing import Dict, Any, Optional, List
import logging
import json
import re

from langgraph.graph import StateGraph, START, END

from apps.ai_service.workflows.base import BaseWorkflow
from apps.ai_service.workflows.states.document_state import (
    DocumentAnalysisState,
    SummaryResult,
    ClauseResult,
    ChunkData,
    RiskAnalysisResult,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Document Type → Analysis Tasks Mapping
# ============================================================================

DOC_TYPE_ANALYSIS = {
    "CONTRACT": ["summary", "clauses", "risk"],
    "STATUTE": ["summary"],
    "CASE": ["summary", "clauses"],
    "PRECEDENT": ["summary", "clauses"],
    "OTHER": ["summary"],
}


# ============================================================================
# Node Functions
# ============================================================================

async def extract_text_node(state: DocumentAnalysisState) -> Dict[str, Any]:
    """
    문서 전처리 노드: 텍스트 추출

    기존 services/document_processor.py 직접 호출
    """
    logger.info(f"[extract_text_node] Processing document: {state.get('file_path')}")

    try:
        from apps.ai_service.services.document_processor import DocumentProcessor

        processor = DocumentProcessor(
            chunk_size=1000,
            chunk_overlap=200
        )

        # 먼저 텍스트가 이미 제공되었는지 확인
        if state.get("text"):
            logger.info("[extract_text_node] Text already provided, skipping extraction")
            return {
                "completed_tasks": state.get("completed_tasks", []) + ["extract_text"]
            }

        file_path = state.get("file_path")
        document_id = state.get("document_id")

        if file_path:
            # 파일에서 텍스트 추출
            result = processor.process_document(file_path)

            if not result.get("success"):
                return {
                    "error": result.get("error", "Failed to process document"),
                    "completed_tasks": state.get("completed_tasks", []) + ["extract_text_failed"]
                }

            return {
                "text": result.get("text", ""),
                "chunks": [],  # plan_node에서 처리
                "doc_type": state.get("doc_type", "OTHER"),
                "completed_tasks": state.get("completed_tasks", []) + ["extract_text"]
            }
        elif document_id:
            # DB에서 텍스트 조회
            try:
                import django
                django.setup()
                from documents.models import Document, DocumentChunk

                doc = Document.objects.get(id=document_id)
                chunks = DocumentChunk.objects.filter(document=doc).order_by('chunk_index')
                full_text = "\n\n".join([chunk.text for chunk in chunks])

                return {
                    "text": full_text,
                    "chunks": [],
                    "doc_type": doc.doc_type if hasattr(doc, 'doc_type') else "OTHER",
                    "completed_tasks": state.get("completed_tasks", []) + ["extract_text"]
                }
            except Exception as e:
                logger.warning(f"Django model access failed: {e}")
                return {
                    "error": f"Failed to load document {document_id}: {str(e)}",
                    "completed_tasks": state.get("completed_tasks", []) + ["extract_text_failed"]
                }
        else:
            # 텍스트도 없고, file_path도 없고, document_id도 없는 경우
            return {
                "error": "No file_path, document_id, or text provided",
                "completed_tasks": state.get("completed_tasks", []) + ["extract_text_failed"]
            }

    except Exception as e:
        logger.error(f"[extract_text_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["extract_text_failed"]
        }


async def planning_agent_node(state: DocumentAnalysisState) -> Dict[str, Any]:
    """
    Planning Agent 노드: 문서 타입에 따라 분석 작업 계획

    문서 타입별 권장 분석:
    - CONTRACT: summary, clauses, risk
    - STATUTE: summary
    - CASE/PRECEDENT: summary, clauses
    - OTHER: summary

    Note: 첫 번째 호출에서만 analysis_plan을 설정합니다.
          이후 호출에서는 기존 plan을 유지합니다.
    """
    logger.info("[planning_agent_node] Planning analysis tasks")

    try:
        # 이미 완료된 작업 확인
        completed_tasks = state.get("completed_tasks", [])
        completed = set(completed_tasks)
        doc_type = state.get("doc_type", "OTHER")
        current_plan = state.get("analysis_plan", [])

        logger.info(
            f"[planning_agent_node] doc_type={doc_type}, "
            f"completed_tasks={completed_tasks}, current_plan={current_plan}"
        )

        # 첫 호출인 경우에만 권장 분석 작업 설정
        if "plan" not in completed:
            # 문서 타입별 권장 분석
            recommended = DOC_TYPE_ANALYSIS.get(doc_type, ["summary"])
            logger.info(f"[planning_agent_node] Initial plan: {recommended}")
            return {
                "analysis_plan": recommended,
                "completed_tasks": completed_tasks + ["plan"]
            }

        # 이미 plan이 완료된 경우, analysis_plan은 각 노드에서 업데이트됨
        # current_plan이 비어있으면 all_done으로 라우팅됨
        logger.info(f"[planning_agent_node] Continuing with plan: {current_plan}")
        return {}

    except Exception as e:
        logger.error(f"[planning_agent_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["plan_failed"]
        }


def route_analysis_tasks(state: DocumentAnalysisState) -> str:
    """
    다음 실행할 분석 작업 선택

    Returns:
        "summary" | "clauses" | "risk" | "all_done"
    """
    plan = state.get("analysis_plan", [])

    if not plan:
        return "all_done"

    # 첫 번째 작업 선택
    next_task = plan[0]

    if next_task == "summary":
        return "summary"
    elif next_task == "clauses":
        return "clauses"
    elif next_task == "risk":
        return "risk"
    else:
        return "all_done"


async def summarize_node(state: DocumentAnalysisState) -> Dict[str, Any]:
    """
    요약 노드: 문서 요약 생성

    기존 services/summarizer.py 직접 호출
    """
    logger.info("[summarize_node] Generating summary")

    try:
        from libs.rag_core.llm.llm_client import create_llm_client
        from apps.ai_service.services.summarizer import Summarizer
        from apps.ai_service.config.settings import settings

        llm_client = create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
        summarizer = Summarizer(llm_client)

        text = state.get("text", "")
        if not text:
            return {
                "error": "No text to summarize",
                "completed_tasks": state.get("completed_tasks", []) + ["summary_failed"]
            }

        # 요약 생성 (GLOBAL 타입)
        result = await summarizer.summarize(
            text=text,
            document_id=state.get("document_id"),
            summary_type="GLOBAL"
        )

        summary_result: SummaryResult = {
            "summary": result.get("summary", ""),
            "token_count": result.get("token_count", 0),
            "model_version": result.get("model_version", "unknown"),
        }

        logger.info(f"[summarize_node] Summary generated: {len(summary_result['summary'])} chars")

        # 완료된 작업 기록 및 analysis_plan에서 제거
        completed = state.get("completed_tasks", [])
        analysis_plan = state.get("analysis_plan", [])
        new_plan = [t for t in analysis_plan if t != "summary"]

        return {
            "summary": summary_result,
            "analysis_plan": new_plan,
            "completed_tasks": completed + ["summary"]
        }

    except Exception as e:
        logger.error(f"[summarize_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["summary_failed"]
        }


async def extract_clauses_node(state: DocumentAnalysisState) -> Dict[str, Any]:
    """
    핵심 조항 추출 노드

    기존 services/clause_extractor.py 직접 호출
    """
    logger.info("[extract_clauses_node] Extracting key clauses")

    try:
        from libs.rag_core.llm.llm_client import create_llm_client
        from apps.ai_service.services.clause_extractor import ClauseExtractor
        from apps.ai_service.config.settings import settings

        llm_client = create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
        extractor = ClauseExtractor(llm_client)

        text = state.get("text", "")
        if not text:
            return {
                "error": "No text to extract clauses from",
                "completed_tasks": state.get("completed_tasks", []) + ["clauses_failed"]
            }

        # 핵심 조항 추출
        result = await extractor.extract_clauses(
            text=text,
            document_id=state.get("document_id"),
            doc_type=state.get("doc_type", "OTHER")
        )

        clauses: List[ClauseResult] = []
        for clause in result.get("clauses", []):
            clauses.append({
                "clause_type": clause.get("clause_type", "OTHER"),
                "title": clause.get("title", ""),
                "content": clause.get("content", ""),
                "importance_score": clause.get("importance_score", 50),
            })

        logger.info(f"[extract_clauses_node] Extracted {len(clauses)} clauses")

        # 완료된 작업 기록 및 analysis_plan에서 제거
        completed = state.get("completed_tasks", [])
        analysis_plan = state.get("analysis_plan", [])
        new_plan = [t for t in analysis_plan if t != "clauses"]

        return {
            "clauses": clauses,
            "analysis_plan": new_plan,
            "completed_tasks": completed + ["clauses"]
        }

    except Exception as e:
        logger.error(f"[extract_clauses_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["clauses_failed"]
        }


async def analyze_risk_node(state: DocumentAnalysisState) -> Dict[str, Any]:
    """
    리스크 분석 노드 (CONTRACT 문서용)

    기존 services/risk_analyzer.py 직접 호출
    """
    logger.info("[analyze_risk_node] Analyzing risks")

    try:
        from libs.rag_core.llm.llm_client import create_llm_client
        from apps.ai_service.config.settings import settings

        llm_client = create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )

        text = state.get("text", "")
        doc_type = state.get("doc_type", "CONTRACT")

        if not text:
            return {
                "error": "No text to analyze risks",
                "completed_tasks": state.get("completed_tasks", []) + ["risk_failed"]
            }

        # 리스크 식별 프롬프트
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

        # JSON 파싱
        risks: List[RiskAnalysisResult] = []
        needs_review = False

        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))

                for risk_data in data:
                    severity = risk_data.get("severity", "MEDIUM").upper()
                    if severity not in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
                        severity = "MEDIUM"

                    # CRITICAL/HIGH 리스크가 있으면 전문가 검토 필요
                    if severity in ["CRITICAL", "HIGH"]:
                        needs_review = True

                    risks.append({
                        "risk_type": risk_data.get("risk_type", "OTHER"),
                        "description": risk_data.get("description", ""),
                        "severity": severity,
                        "recommendation": risk_data.get("recommendation"),
                    })
        except Exception as e:
            logger.warning(f"Failed to parse risks: {e}")

        logger.info(f"[analyze_risk_node] Identified {len(risks)} risks, needs_review={needs_review}")

        # 완료된 작업 기록 및 analysis_plan에서 제거
        completed = state.get("completed_tasks", [])
        analysis_plan = state.get("analysis_plan", [])
        new_plan = [t for t in analysis_plan if t != "risk"]

        return {
            "risks": risks,
            "needs_expert_review": needs_review,
            "analysis_plan": new_plan,
            "completed_tasks": completed + ["risk"]
        }

    except Exception as e:
        logger.error(f"[analyze_risk_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["risk_failed"]
        }


async def aggregate_node(state: DocumentAnalysisState) -> Dict[str, Any]:
    """
    결과 집계 노드: 모든 분석 결과 통합
    """
    logger.info("[aggregate_node] Aggregating results")

    completed_tasks = state.get("completed_tasks", [])

    # 에러 체크
    if state.get("error"):
        logger.warning(f"[aggregate_node] Error found: {state.get('error')}")
        return {
            "completed_tasks": completed_tasks + ["aggregate_with_error"]
        }

    return {
        "completed_tasks": completed_tasks + ["aggregate"]
    }


# ============================================================================
# Workflow Graph Creation
# ============================================================================

def create_document_workflow() -> StateGraph:
    """
    Document Analysis Workflow 생성 (Planning Agent 패턴)

    그래프 구조:
        START
          |
          v
      extract_text
          |
          v
        plan  <-----------------+
          |                     |
          v                     |
    [조건부 분기]                |
    /    |    \                |
   v     v     v               |
 summary clauses risk --------+
   |     |     |
   +-----+-----+
         |
         v (all_done)
      aggregate
         |
         v
        END

    Cyclic Pattern: 각 분석 노드 완료 후 다시 plan으로

    Returns:
        컴파일된 StateGraph
    """
    workflow = StateGraph(DocumentAnalysisState)

    # 노드 추가
    workflow.add_node("extract_text", extract_text_node)
    workflow.add_node("plan", planning_agent_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("extract_clauses", extract_clauses_node)
    workflow.add_node("analyze_risk", analyze_risk_node)
    workflow.add_node("aggregate", aggregate_node)

    # 엣지 정의
    # START -> extract_text
    workflow.add_edge(START, "extract_text")

    # extract_text -> plan
    workflow.add_edge("extract_text", "plan")

    # plan -> [조건부] summarize/clauses/risk/all_done
    workflow.add_conditional_edges(
        "plan",
        route_analysis_tasks,
        {
            "summary": "summarize",
            "clauses": "extract_clauses",
            "risk": "analyze_risk",
            "all_done": "aggregate"
        }
    )

    # Cyclic: 각 분석 노드 완료 후 다시 plan으로
    workflow.add_edge("summarize", "plan")
    workflow.add_edge("extract_clauses", "plan")
    workflow.add_edge("analyze_risk", "plan")

    # aggregate -> END
    workflow.add_edge("aggregate", END)

    # 컴파일 (Checkpointing 없음)
    # recursion_limit은 invoke() 시점에 BaseWorkflow에서 전달 (LangGraph 1.0+)
    return workflow.compile()


# ============================================================================
# Workflow Class (BaseWorkflow 상속)
# ============================================================================

class DocumentWorkflow(BaseWorkflow[DocumentAnalysisState]):
    """
    Document Analysis Workflow 클래스 (Planning Agent 패턴)

    BaseWorkflow를 상속하여 표준화된 인터페이스 제공

    사용:
        workflow = DocumentWorkflow()
        result = await workflow.arun(
            file_path="/path/to/document.pdf",
            doc_type="CONTRACT"
        )
    """

    def __init__(self):
        super().__init__(
            name="document_analysis_workflow",
            use_checkpointing=False,  # Checkpointing 불필요
            recursion_limit=50  # Planning Agent 패턴 (cyclic): 충분한 recursion 허용
        )

    def create_graph(self) -> StateGraph:
        """StateGraph 생성 (compile 전) - 순차 실행 방식"""
        workflow = StateGraph(DocumentAnalysisState)

        # 노드 추가
        workflow.add_node("extract_text", extract_text_node)
        workflow.add_node("plan", planning_agent_node)
        workflow.add_node("summarize", summarize_node)
        workflow.add_node("extract_clauses", extract_clauses_node)
        workflow.add_node("analyze_risk", analyze_risk_node)
        workflow.add_node("aggregate", aggregate_node)

        # 순차 실행 방식 (Cyclic 패턴 제거)
        # START -> extract_text -> plan -> summarize -> clauses -> risk -> aggregate -> END
        workflow.add_edge(START, "extract_text")
        workflow.add_edge("extract_text", "plan")
        workflow.add_edge("plan", "summarize")
        workflow.add_edge("summarize", "extract_clauses")
        workflow.add_edge("extract_clauses", "analyze_risk")
        workflow.add_edge("analyze_risk", "aggregate")
        workflow.add_edge("aggregate", END)

        return workflow

    def create_initial_state(
        self,
        file_path: Optional[str] = None,
        document_id: Optional[str] = None,
        text: Optional[str] = None,
        doc_type: str = "OTHER",
        **kwargs
    ) -> DocumentAnalysisState:
        """
        초기 상태 생성

        Args:
            file_path: 파일 경로 (파일에서 처리)
            document_id: 문서 ID (DB에서 조회)
            text: 직접 제공된 텍스트
            doc_type: 문서 타입 (CONTRACT, STATUTE, PRECEDENT, OTHER)

        Returns:
            초기 DocumentAnalysisState
        """
        return DocumentAnalysisState(
            document_id=document_id,
            file_path=file_path,
            doc_type=doc_type,
            text=text or "",
            chunks=[],
            summary=None,
            clauses=[],
            risks=None,
            analysis_plan=[],
            needs_expert_review=False,
            completed_tasks=[],
            error=None,
        )

    def _format_result(
        self,
        result: Dict[str, Any],
        processing_time: float,
        session_id: str
    ) -> Dict[str, Any]:
        """
        결과 포맷팅 (BaseWorkflow 오버라이드)

        API 응답 형식에 맞게 변환
        """
        return {
            "success": result.get("error") is None,
            "document_id": result.get("document_id"),
            "doc_type": result.get("doc_type"),
            "summary": result.get("summary"),
            "clauses": result.get("clauses", []),
            "risks": result.get("risks"),
            "needs_expert_review": result.get("needs_expert_review", False),
            "chunk_count": len(result.get("chunks", [])),
            "completed_tasks": result.get("completed_tasks", []),
            "processing_time": processing_time,
            "session_id": session_id,
            "error": result.get("error"),
        }


# ============================================================================
# Factory Functions
# ============================================================================

def get_document_workflow() -> DocumentWorkflow:
    """DocumentWorkflow 인스턴스 반환"""
    return DocumentWorkflow()
