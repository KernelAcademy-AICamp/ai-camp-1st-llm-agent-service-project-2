"""
Document Analysis Workflow

Phase 4 - Week 12: 문서 분석 LangGraph 워크플로우

워크플로우 흐름:
1. preprocess_node: 문서 텍스트 추출 (document_processor 사용)
2. chunk_node: 텍스트 청킹
3. parallel: summarize_node + extract_clauses_node (병렬 실행)
4. aggregate_node: 결과 집계

Checkpointing: 불필요 (빠른 실행, 10-20초)

사용:
    from apps.ai_service.workflows.document_workflow import (
        create_document_workflow,
        DocumentWorkflow
    )

    # 방법 1: Workflow 클래스 사용
    workflow = DocumentWorkflow()
    result = await workflow.arun(file_path="/path/to/file.pdf")

    # 방법 2: 직접 그래프 생성
    graph = create_document_workflow()
    result = await graph.ainvoke(initial_state)
"""

from typing import Dict, Any, Optional, List
import logging
import asyncio

from langgraph.graph import StateGraph, START, END

from apps.ai_service.workflows.base import BaseWorkflow
from apps.ai_service.workflows.states.document_state import (
    DocumentAnalysisState,
    SummaryResult,
    ClauseResult,
    ChunkData,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Node Functions (일반 Python 함수로 구현 - MCP 불필요)
# ============================================================================

async def preprocess_node(state: DocumentAnalysisState) -> Dict[str, Any]:
    """
    문서 전처리 노드: 텍스트 추출

    기존 services/document_processor.py 직접 호출
    """
    logger.info(f"[preprocess_node] Processing document: {state.get('file_path')}")

    try:
        from apps.ai_service.services.document_processor import DocumentProcessor

        processor = DocumentProcessor(
            chunk_size=1000,
            chunk_overlap=200
        )

        file_path = state.get("file_path")
        document_id = state.get("document_id")

        if file_path:
            # 파일에서 텍스트 추출
            result = processor.process_document(file_path)

            if not result.get("success"):
                return {
                    "error": result.get("error", "Failed to process document"),
                    "completed_tasks": state.get("completed_tasks", []) + ["preprocess_failed"]
                }

            return {
                "text": result.get("text", ""),
                "chunks": [],  # chunk_node에서 처리
                "doc_type": state.get("doc_type", "OTHER"),
                "completed_tasks": state.get("completed_tasks", []) + ["preprocess"]
            }
        elif document_id:
            # DB에서 텍스트 조회 (Django ORM)
            # Django 설정이 필요하므로 동적 import
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
                    "completed_tasks": state.get("completed_tasks", []) + ["preprocess"]
                }
            except Exception as e:
                logger.warning(f"Django model access failed: {e}")
                return {
                    "error": f"Failed to load document {document_id}: {str(e)}",
                    "completed_tasks": state.get("completed_tasks", []) + ["preprocess_failed"]
                }
        else:
            # 이미 텍스트가 있는 경우
            if state.get("text"):
                return {
                    "completed_tasks": state.get("completed_tasks", []) + ["preprocess"]
                }
            return {
                "error": "No file_path, document_id, or text provided",
                "completed_tasks": state.get("completed_tasks", []) + ["preprocess_failed"]
            }

    except Exception as e:
        logger.error(f"[preprocess_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["preprocess_failed"]
        }


async def chunk_node(state: DocumentAnalysisState) -> Dict[str, Any]:
    """
    청킹 노드: 텍스트를 청크로 분할

    기존 services/document_processor.py의 chunk_text 직접 호출
    """
    logger.info(f"[chunk_node] Chunking text (length: {len(state.get('text', ''))})")

    try:
        from apps.ai_service.services.document_processor import DocumentProcessor

        processor = DocumentProcessor(
            chunk_size=1000,
            chunk_overlap=200
        )

        text = state.get("text", "")
        if not text:
            return {
                "error": "No text to chunk",
                "completed_tasks": state.get("completed_tasks", []) + ["chunk_failed"]
            }

        chunks_raw = processor.chunk_text(text)

        # ChunkData 형식으로 변환
        chunks: List[ChunkData] = []
        for chunk in chunks_raw:
            chunks.append({
                "chunk_index": chunk.get("chunk_index", 0),
                "text": chunk.get("text", ""),
                "start_offset": chunk.get("start_offset", 0),
                "end_offset": chunk.get("end_offset", 0),
                "token_count": chunk.get("token_count", 0),
            })

        logger.info(f"[chunk_node] Created {len(chunks)} chunks")

        return {
            "chunks": chunks,
            "completed_tasks": state.get("completed_tasks", []) + ["chunk"]
        }

    except Exception as e:
        logger.error(f"[chunk_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["chunk_failed"]
        }


async def summarize_node(state: DocumentAnalysisState) -> Dict[str, Any]:
    """
    요약 노드: 문서 요약 생성

    기존 services/summarizer.py 직접 호출
    """
    logger.info("[summarize_node] Generating summary")

    try:
        # LLM 클라이언트 가져오기
        from libs.rag_core.llm.llm_client import get_llm_client
        from apps.ai_service.services.summarizer import Summarizer

        llm_client = get_llm_client()
        summarizer = Summarizer(llm_client)

        text = state.get("text", "")
        if not text:
            return {
                "error": "No text to summarize",
                "completed_tasks": state.get("completed_tasks", []) + ["summarize_failed"]
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

        return {
            "summary": summary_result,
            "completed_tasks": state.get("completed_tasks", []) + ["summarize"]
        }

    except Exception as e:
        logger.error(f"[summarize_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["summarize_failed"]
        }


async def extract_clauses_node(state: DocumentAnalysisState) -> Dict[str, Any]:
    """
    핵심 조항 추출 노드

    기존 services/clause_extractor.py 직접 호출
    """
    logger.info("[extract_clauses_node] Extracting key clauses")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client
        from apps.ai_service.services.clause_extractor import ClauseExtractor

        llm_client = get_llm_client()
        extractor = ClauseExtractor(llm_client)

        text = state.get("text", "")
        if not text:
            return {
                "error": "No text to extract clauses from",
                "completed_tasks": state.get("completed_tasks", []) + ["extract_clauses_failed"]
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

        return {
            "clauses": clauses,
            "completed_tasks": state.get("completed_tasks", []) + ["extract_clauses"]
        }

    except Exception as e:
        logger.error(f"[extract_clauses_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["extract_clauses_failed"]
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

    # 모든 작업 완료 확인
    required_tasks = {"preprocess", "chunk", "summarize", "extract_clauses"}
    completed_set = set(completed_tasks)

    missing_tasks = required_tasks - completed_set
    if missing_tasks:
        logger.warning(f"[aggregate_node] Missing tasks: {missing_tasks}")

    return {
        "completed_tasks": completed_tasks + ["aggregate"]
    }


# ============================================================================
# Workflow Graph Creation
# ============================================================================

def create_document_workflow() -> StateGraph:
    """
    Document Analysis Workflow 생성

    그래프 구조:
        START
          |
          v
        preprocess
          |
          v
        chunk
          |
          v
        +-----------+
        |           |
        v           v
    summarize  extract_clauses  (병렬 실행 - LangGraph가 자동으로 처리)
        |           |
        +-----------+
              |
              v
          aggregate
              |
              v
            END

    Checkpointing: 불필요 (compile() 시 checkpointer 없이)

    Returns:
        컴파일된 StateGraph
    """
    # StateGraph 생성
    workflow = StateGraph(DocumentAnalysisState)

    # 노드 추가
    workflow.add_node("preprocess", preprocess_node)
    workflow.add_node("chunk", chunk_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("extract_clauses", extract_clauses_node)
    workflow.add_node("aggregate", aggregate_node)

    # 엣지 정의
    # START -> preprocess
    workflow.add_edge(START, "preprocess")

    # preprocess -> chunk
    workflow.add_edge("preprocess", "chunk")

    # chunk -> summarize, extract_clauses (fan-out)
    # LangGraph에서 동일 소스에서 여러 엣지를 추가하면 병렬 실행됨
    workflow.add_edge("chunk", "summarize")
    workflow.add_edge("chunk", "extract_clauses")

    # summarize, extract_clauses -> aggregate (fan-in)
    workflow.add_edge("summarize", "aggregate")
    workflow.add_edge("extract_clauses", "aggregate")

    # aggregate -> END
    workflow.add_edge("aggregate", END)

    # 컴파일 (Checkpointing 없음)
    return workflow.compile()


# ============================================================================
# Workflow Class (BaseWorkflow 상속)
# ============================================================================

class DocumentWorkflow(BaseWorkflow[DocumentAnalysisState]):
    """
    Document Analysis Workflow 클래스

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
            use_checkpointing=False  # Checkpointing 불필요
        )

    def create_graph(self) -> StateGraph:
        """StateGraph 생성"""
        # StateGraph 생성 (compile 전)
        workflow = StateGraph(DocumentAnalysisState)

        # 노드 추가
        workflow.add_node("preprocess", preprocess_node)
        workflow.add_node("chunk", chunk_node)
        workflow.add_node("summarize", summarize_node)
        workflow.add_node("extract_clauses", extract_clauses_node)
        workflow.add_node("aggregate", aggregate_node)

        # 엣지 정의
        workflow.add_edge(START, "preprocess")
        workflow.add_edge("preprocess", "chunk")
        workflow.add_edge("chunk", "summarize")
        workflow.add_edge("chunk", "extract_clauses")
        workflow.add_edge("summarize", "aggregate")
        workflow.add_edge("extract_clauses", "aggregate")
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
