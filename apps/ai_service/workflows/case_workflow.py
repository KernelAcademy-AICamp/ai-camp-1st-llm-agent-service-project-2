"""
Case Analysis Workflow

Phase 4 - Week 12: 사건 분석 LangGraph 워크플로우

워크플로우 흐름:
1. extract_info_node: 사건 정보 추출 (당사자, 청구 등)
2. analyze_issues_node: 쟁점 분석
3. search_precedents_node: 관련 판례 검색
4. generate_analysis_node: 종합 분석 생성

Checkpointing: 불필요 (빠른 실행, 10-15초)

사용:
    from apps.ai_service.workflows.case_workflow import (
        create_case_workflow,
        CaseWorkflow
    )

    # 방법 1: Workflow 클래스 사용
    workflow = CaseWorkflow()
    result = await workflow.arun(case_content="사건 내용...")

    # 방법 2: 직접 그래프 생성
    graph = create_case_workflow()
    result = await graph.ainvoke(initial_state)
"""

from typing import Dict, Any, Optional, List
import logging
import json
import re

from langgraph.graph import StateGraph, START, END

from apps.ai_service.workflows.base import BaseWorkflow
from apps.ai_service.workflows.states.case_state import (
    CaseAnalysisState,
    PartyInfo,
    IssueInfo,
    PrecedentResult,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Node Functions (일반 Python 함수로 구현 - MCP 불필요)
# ============================================================================

async def extract_info_node(state: CaseAnalysisState) -> Dict[str, Any]:
    """
    사건 정보 추출 노드: 당사자, 사건 유형 등 추출

    LLM을 사용하여 구조화된 정보 추출
    """
    logger.info("[extract_info_node] Extracting case information")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client

        llm_client = get_llm_client()
        case_content = state.get("case_content", "")

        if not case_content:
            return {
                "error": "No case content provided",
                "completed_tasks": state.get("completed_tasks", []) + ["extract_info_failed"]
            }

        # 당사자 및 사건 정보 추출 프롬프트
        prompt = f"""다음 사건 내용을 분석하여 당사자 정보와 사건 유형을 JSON 형식으로 추출해주세요.

사건 내용:
{case_content[:5000]}

다음 형식으로 JSON을 반환해주세요:
{{
  "case_type": "민사|형사|행정|가사|기타 중 하나",
  "parties": [
    {{
      "role": "plaintiff|defendant|third_party 중 하나",
      "name": "당사자 이름",
      "description": "당사자에 대한 간단한 설명"
    }}
  ],
  "case_summary": "사건의 간략한 요약 (2-3문장)"
}}

반드시 유효한 JSON 형식으로만 응답해주세요."""

        response = llm_client.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=1500
        )

        # JSON 파싱
        parties: List[PartyInfo] = []
        case_type = "기타"

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                case_type = data.get("case_type", "기타")

                for party_data in data.get("parties", []):
                    parties.append({
                        "role": party_data.get("role", "unknown"),
                        "name": party_data.get("name", ""),
                        "description": party_data.get("description"),
                    })
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse party info: {e}")

        # case_type 매핑
        case_type_mapping = {
            "민사": "civil",
            "형사": "criminal",
            "행정": "administrative",
            "가사": "family",
        }
        case_type_english = case_type_mapping.get(case_type, "other")

        logger.info(f"[extract_info_node] Extracted {len(parties)} parties, type={case_type}")

        return {
            "parties": parties,
            "case_type": case_type_english,
            "completed_tasks": state.get("completed_tasks", []) + ["extract_info"]
        }

    except Exception as e:
        logger.error(f"[extract_info_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["extract_info_failed"]
        }


async def analyze_issues_node(state: CaseAnalysisState) -> Dict[str, Any]:
    """
    쟁점 분석 노드: 법적 쟁점 식별

    LLM을 사용하여 주요 쟁점 추출
    """
    logger.info("[analyze_issues_node] Analyzing legal issues")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client

        llm_client = get_llm_client()
        case_content = state.get("case_content", "")
        case_type = state.get("case_type", "other")

        if not case_content:
            return {
                "error": "No case content provided",
                "completed_tasks": state.get("completed_tasks", []) + ["analyze_issues_failed"]
            }

        # 쟁점 분석 프롬프트
        prompt = f"""다음 {case_type} 사건의 법적 쟁점을 분석하여 JSON 형식으로 추출해주세요.

사건 내용:
{case_content[:5000]}

다음 형식으로 JSON 배열을 반환해주세요:
[
  {{
    "issue_type": "쟁점 유형 (예: 손해배상, 계약해지, 재산분할 등)",
    "description": "쟁점에 대한 상세 설명",
    "legal_basis": "관련 법조항 또는 판례 (알 수 있는 경우)"
  }}
]

최대 5개의 주요 쟁점을 추출하세요. 반드시 유효한 JSON 형식으로만 응답해주세요."""

        response = llm_client.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=1500
        )

        # JSON 파싱
        issues: List[IssueInfo] = []

        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))

                for issue_data in data:
                    issues.append({
                        "issue_type": issue_data.get("issue_type", ""),
                        "description": issue_data.get("description", ""),
                        "legal_basis": issue_data.get("legal_basis"),
                    })
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse issues: {e}")

        logger.info(f"[analyze_issues_node] Identified {len(issues)} issues")

        return {
            "issues": issues,
            "completed_tasks": state.get("completed_tasks", []) + ["analyze_issues"]
        }

    except Exception as e:
        logger.error(f"[analyze_issues_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["analyze_issues_failed"]
        }


async def search_precedents_node(state: CaseAnalysisState) -> Dict[str, Any]:
    """
    관련 판례 검색 노드: RAG 기반 판례 검색

    기존 case_analyzer._search_related_cases 로직 활용
    """
    logger.info("[search_precedents_node] Searching related precedents")

    try:
        # 검색 쿼리 구성: 쟁점 기반
        issues = state.get("issues", [])
        case_content = state.get("case_content", "")

        if issues:
            query = " ".join([issue.get("description", "")[:100] for issue in issues[:3]])
        else:
            query = case_content[:500] if case_content else ""

        if not query:
            return {
                "related_precedents": [],
                "completed_tasks": state.get("completed_tasks", []) + ["search_precedents"]
            }

        # Retriever 가져오기 (app.state에서 또는 직접 생성)
        precedents: List[PrecedentResult] = []

        try:
            from libs.rag_core.retrieval.retriever import LegalDocumentRetriever
            from libs.rag_core.embeddings.embedder import KoreanLegalEmbedder
            from libs.rag_core.vectordb.chromadb import ChromaVectorDB
            from config.settings import settings

            embedder = KoreanLegalEmbedder()
            vectordb = ChromaVectorDB(
                collection_name="criminal_law_docs",
                persist_directory=str(settings.CHROMA_DIR)
            )
            retriever = LegalDocumentRetriever(vectordb=vectordb, embedder=embedder)

            # 판례 검색
            results = retriever.retrieve(
                query=query,
                top_k=5,
                filter_metadata={"type": "precedent"}
            )

            for result in results:
                metadata = result.get("metadata", {})
                case_number = metadata.get("case_number", "")
                court = metadata.get("court", "")

                # Title 생성
                if case_number and court:
                    title = f"{court} {case_number}"
                elif case_number:
                    title = f"판례 {case_number}"
                else:
                    title = "관련 판례"

                # Summary
                text = result.get("text", "")[:350]

                precedents.append({
                    "case_number": case_number,
                    "title": title,
                    "summary": text,
                    "relevance_score": result.get("score", 0.0),
                })

        except Exception as e:
            logger.warning(f"Retriever not available: {e}")
            # 검색 실패 시 빈 리스트 반환

        logger.info(f"[search_precedents_node] Found {len(precedents)} precedents")

        return {
            "related_precedents": precedents,
            "completed_tasks": state.get("completed_tasks", []) + ["search_precedents"]
        }

    except Exception as e:
        logger.error(f"[search_precedents_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["search_precedents_failed"]
        }


async def generate_analysis_node(state: CaseAnalysisState) -> Dict[str, Any]:
    """
    종합 분석 생성 노드: 최종 분석 보고서 생성

    모든 정보를 종합하여 분석 결과 생성
    """
    logger.info("[generate_analysis_node] Generating final analysis")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client

        llm_client = get_llm_client()

        # 수집된 정보 종합
        case_type = state.get("case_type", "other")
        parties = state.get("parties", [])
        issues = state.get("issues", [])
        precedents = state.get("related_precedents", [])
        case_content = state.get("case_content", "")[:2000]

        # 분석 프롬프트
        prompt = f"""다음 정보를 바탕으로 사건 종합 분석을 작성해주세요.

사건 유형: {case_type}

당사자 정보:
{json.dumps(parties, ensure_ascii=False, indent=2) if parties else "정보 없음"}

법적 쟁점:
{json.dumps(issues, ensure_ascii=False, indent=2) if issues else "정보 없음"}

관련 판례:
{json.dumps([p.get('title', '') for p in precedents[:3]], ensure_ascii=False) if precedents else "없음"}

사건 요약:
{case_content}

다음 내용을 포함한 종합 분석을 작성해주세요:
1. 사건 개요
2. 주요 쟁점 분석
3. 관련 판례 참고
4. 법적 검토 의견
5. 향후 대응 방향

분석 결과:"""

        analysis = llm_client.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=2000
        )

        logger.info(f"[generate_analysis_node] Generated analysis: {len(analysis)} chars")

        return {
            "analysis": analysis,
            "completed_tasks": state.get("completed_tasks", []) + ["generate_analysis"]
        }

    except Exception as e:
        logger.error(f"[generate_analysis_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["generate_analysis_failed"]
        }


# ============================================================================
# Workflow Graph Creation
# ============================================================================

def create_case_workflow() -> StateGraph:
    """
    Case Analysis Workflow 생성

    그래프 구조:
        START
          |
          v
        extract_info
          |
          v
    +-----+-----+
    |           |
    v           v
analyze_issues  search_precedents  (병렬 실행)
    |           |
    +-----+-----+
          |
          v
    generate_analysis
          |
          v
        END

    Checkpointing: 불필요 (compile() 시 checkpointer 없이)

    Returns:
        컴파일된 StateGraph
    """
    # StateGraph 생성
    workflow = StateGraph(CaseAnalysisState)

    # 노드 추가
    workflow.add_node("extract_info", extract_info_node)
    workflow.add_node("analyze_issues", analyze_issues_node)
    workflow.add_node("search_precedents", search_precedents_node)
    workflow.add_node("generate_analysis", generate_analysis_node)

    # 엣지 정의
    # START -> extract_info
    workflow.add_edge(START, "extract_info")

    # extract_info -> analyze_issues, search_precedents (fan-out, 병렬)
    workflow.add_edge("extract_info", "analyze_issues")
    workflow.add_edge("extract_info", "search_precedents")

    # analyze_issues, search_precedents -> generate_analysis (fan-in)
    workflow.add_edge("analyze_issues", "generate_analysis")
    workflow.add_edge("search_precedents", "generate_analysis")

    # generate_analysis -> END
    workflow.add_edge("generate_analysis", END)

    # 컴파일 (Checkpointing 없음)
    return workflow.compile()


# ============================================================================
# Workflow Class (BaseWorkflow 상속)
# ============================================================================

class CaseWorkflow(BaseWorkflow[CaseAnalysisState]):
    """
    Case Analysis Workflow 클래스

    BaseWorkflow를 상속하여 표준화된 인터페이스 제공

    사용:
        workflow = CaseWorkflow()
        result = await workflow.arun(
            case_content="사건 내용...",
            case_type="civil"
        )
    """

    def __init__(self):
        super().__init__(
            name="case_analysis_workflow",
            use_checkpointing=False  # Checkpointing 불필요
        )

    def create_graph(self) -> StateGraph:
        """StateGraph 생성"""
        workflow = StateGraph(CaseAnalysisState)

        # 노드 추가
        workflow.add_node("extract_info", extract_info_node)
        workflow.add_node("analyze_issues", analyze_issues_node)
        workflow.add_node("search_precedents", search_precedents_node)
        workflow.add_node("generate_analysis", generate_analysis_node)

        # 엣지 정의
        workflow.add_edge(START, "extract_info")
        workflow.add_edge("extract_info", "analyze_issues")
        workflow.add_edge("extract_info", "search_precedents")
        workflow.add_edge("analyze_issues", "generate_analysis")
        workflow.add_edge("search_precedents", "generate_analysis")
        workflow.add_edge("generate_analysis", END)

        return workflow

    def create_initial_state(
        self,
        case_content: str,
        case_type: str = "other",
        **kwargs
    ) -> CaseAnalysisState:
        """
        초기 상태 생성

        Args:
            case_content: 사건 내용 텍스트
            case_type: 사건 유형 (civil, criminal, administrative, family, other)

        Returns:
            초기 CaseAnalysisState
        """
        return CaseAnalysisState(
            case_content=case_content,
            case_type=case_type,
            parties=[],
            issues=[],
            related_precedents=[],
            analysis=None,
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
            "case_type": result.get("case_type", "other"),
            "parties": result.get("parties", []),
            "issues": result.get("issues", []),
            "related_precedents": result.get("related_precedents", []),
            "analysis": result.get("analysis"),
            "completed_tasks": result.get("completed_tasks", []),
            "processing_time": processing_time,
            "session_id": session_id,
            "error": result.get("error"),
        }


# ============================================================================
# Factory Functions
# ============================================================================

def get_case_workflow() -> CaseWorkflow:
    """CaseWorkflow 인스턴스 반환"""
    return CaseWorkflow()
