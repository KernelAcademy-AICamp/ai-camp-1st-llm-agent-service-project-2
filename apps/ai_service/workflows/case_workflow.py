"""
Case Analysis Workflow

Phase 4 - Week 12: 사건 분석 LangGraph 워크플로우 (Complexity-based Routing)

워크플로우 흐름:
1. analyze_node: 사건 분석 (case_analyst_agent)
2. assess_complexity_node: 복잡도 평가
3. [조건부] route_by_complexity:
   - simple: research_node -> END
   - complex: strategize_node -> research_node -> END

Multi-Agent 패턴:
- case_analyst_agent: 사건 요약, 이슈, 당사자, 날짜 추출
- complexity_assessor: 복잡도 평가 (0-100)
- legal_strategist_agent: 법률 전략 수립 (복잡한 사건만)
- precedent_researcher_agent: 판례 검색

Checkpointing: 불필요 (빠른 실행, 10-15초)

사용:
    from apps.ai_service.workflows.case_workflow import (
        create_case_workflow,
        CaseWorkflow
    )

    workflow = CaseWorkflow()
    result = await workflow.arun(case_content="사건 내용...")
"""

from typing import Dict, Any, Optional, List
import logging
import json
import re

from langgraph.graph import StateGraph, START, END

from apps.ai_service.workflows.base import BaseWorkflow
from apps.ai_service.services.pii_masker import PIIMasker, get_masker
from apps.ai_service.workflows.states.case_state import (
    CaseAnalysisState,
    PartyInfo,
    IssueInfo,
    PrecedentResult,
)

logger = logging.getLogger(__name__)

# Complexity threshold
COMPLEXITY_THRESHOLD = 70


# ============================================================================
# Node Functions
# ============================================================================

async def case_analyst_agent(state: CaseAnalysisState) -> Dict[str, Any]:
    """
    사건 분석 에이전트: 사건 요약, 핵심 이슈, 당사자 추출

    직접 LLM 호출
    """
    logger.info("[case_analyst_agent] Analyzing case")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client

        llm_client = get_llm_client()
        case_content = state.get("case_content", "")

        if not case_content:
            return {
                "error": "No case content provided",
                "completed_tasks": state.get("completed_tasks", []) + ["analyze_failed"]
            }

        # 사건 분석 프롬프트 (사건 요약 + 핵심 이슈 + 당사자 + 날짜를 한 번에 추출)
        prompt = f"""다음 법률 사건을 분석하세요.

사건 내용:
{case_content[:10000]}

다음 JSON 형식으로 응답하세요:
{{
    "case_summary": "사건 요약 (2-3문장)",
    "case_type": "민사|형사|행정|가사|기타 중 하나",
    "key_issues": [
        {{
            "issue_type": "쟁점 유형",
            "description": "쟁점 설명",
            "legal_basis": "관련 법조항 (있으면)"
        }}
    ],
    "parties": [
        {{
            "role": "plaintiff|defendant|third_party",
            "name": "당사자 이름",
            "description": "당사자 설명"
        }}
    ],
    "important_dates": ["YYYY-MM-DD: 사건 설명", ...]
}}

반드시 유효한 JSON 형식으로만 응답하세요."""

        # PII 마스킹 적용 (OpenAI API에 개인정보 전송 방지)
        masker = get_masker(mode="balanced")
        masked_prompt, pii_mapping = masker.mask(prompt)
        logger.debug(f"[case_analyst_agent] PII masked: {len(pii_mapping)} entities")

        response = llm_client.generate(
            prompt=masked_prompt,
            temperature=0.1,
            max_tokens=2000
        )

        # PII 복원 (응답에서 플레이스홀더를 원본으로 복원)
        response = masker.restore(response, pii_mapping)

        # JSON 파싱
        parties: List[PartyInfo] = []
        issues: List[IssueInfo] = []
        case_type = "other"

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))

                # Case type
                case_type_kr = data.get("case_type", "기타")
                case_type_mapping = {
                    "민사": "civil",
                    "형사": "criminal",
                    "행정": "administrative",
                    "가사": "family",
                }
                case_type = case_type_mapping.get(case_type_kr, "other")

                # Parties
                for party_data in data.get("parties", []):
                    parties.append({
                        "role": party_data.get("role", "unknown"),
                        "name": party_data.get("name", ""),
                        "description": party_data.get("description"),
                    })

                # Issues
                for issue_data in data.get("key_issues", []):
                    issues.append({
                        "issue_type": issue_data.get("issue_type", ""),
                        "description": issue_data.get("description", ""),
                        "legal_basis": issue_data.get("legal_basis"),
                    })

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse case analysis: {e}")

        logger.info(f"[case_analyst_agent] Extracted {len(parties)} parties, {len(issues)} issues")

        return {
            "parties": parties,
            "issues": issues,
            "case_type": case_type,
            "completed_tasks": state.get("completed_tasks", []) + ["analyze"]
        }

    except Exception as e:
        logger.error(f"[case_analyst_agent] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["analyze_failed"]
        }


async def complexity_assessor_node(state: CaseAnalysisState) -> Dict[str, Any]:
    """
    사건 복잡도 평가 노드

    복잡도 점수 (0-100) 계산:
    - 법률 쟁점의 복잡성
    - 관련 당사자 수
    - 증거의 복잡도
    - 선례의 명확성
    """
    logger.info("[complexity_assessor_node] Assessing case complexity")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client

        llm_client = get_llm_client()

        # 사건 정보 요약
        parties = state.get("parties", [])
        issues = state.get("issues", [])
        case_content = state.get("case_content", "")[:2000]

        prompt = f"""다음 사건의 복잡도를 0-100으로 평가하세요.

사건 요약: {case_content}
당사자 수: {len(parties)}
쟁점 수: {len(issues)}
쟁점 내용: {json.dumps([i.get("description", "")[:100] for i in issues], ensure_ascii=False)}

평가 기준:
- 법률 쟁점의 복잡성 (여러 법률 영역 관련, 판례 불명확)
- 관련 당사자 수 (다수 당사자, 복잡한 이해관계)
- 증거의 복잡도 (전문 감정 필요, 기술적 증거)
- 선례의 명확성 (확립된 판례 유무)

70점 이상: 복잡한 사건 (전문 전략 수립 필요)
70점 미만: 일반 사건

복잡도 점수 (숫자만 응답):"""

        # PII 마스킹 적용 (OpenAI API에 개인정보 전송 방지)
        masker = get_masker(mode="balanced")
        masked_prompt, pii_mapping = masker.mask(prompt)
        logger.debug(f"[complexity_assessor_node] PII masked: {len(pii_mapping)} entities")

        response = llm_client.generate(
            prompt=masked_prompt,
            temperature=0.1,
            max_tokens=50
        )

        # PII 복원 (응답에서 플레이스홀더를 원본으로 복원)
        response = masker.restore(response, pii_mapping)

        # 숫자 추출
        try:
            score_match = re.search(r'\d+', response)
            complexity_score = int(score_match.group(0)) if score_match else 50
            complexity_score = min(100, max(0, complexity_score))  # 0-100 범위로 제한
        except Exception:
            complexity_score = 50

        logger.info(f"[complexity_assessor_node] Complexity score: {complexity_score}")

        return {
            "complexity_score": complexity_score,
            "completed_tasks": state.get("completed_tasks", []) + ["assess_complexity"]
        }

    except Exception as e:
        logger.error(f"[complexity_assessor_node] Error: {e}")
        return {
            "complexity_score": 50,  # 기본값
            "completed_tasks": state.get("completed_tasks", []) + ["assess_complexity_failed"]
        }


def route_by_complexity(state: CaseAnalysisState) -> str:
    """
    복잡도에 따라 라우팅

    Returns:
        "complex" if score >= 70, "simple" otherwise
    """
    complexity_score = state.get("complexity_score", 50)
    return "complex" if complexity_score >= COMPLEXITY_THRESHOLD else "simple"


async def legal_strategist_agent(state: CaseAnalysisState) -> Dict[str, Any]:
    """
    법률 전략 수립 에이전트 (복잡한 사건만)

    유사 사건 검색 후 전략 수립
    """
    logger.info("[legal_strategist_agent] Developing legal strategy")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client

        llm_client = get_llm_client()

        # 유사 사건 검색
        similar_cases = []
        try:
            from libs.rag_core.retrieval.retriever import LegalDocumentRetriever
            from libs.rag_core.embeddings.embedder import KoreanLegalEmbedder
            from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB
            from config.settings import settings

            embedder = KoreanLegalEmbedder()
            vectordb = QdrantVectorDB(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
                collection_name=settings.QDRANT_COLLECTION
            )
            retriever = LegalDocumentRetriever(vectordb=vectordb, embedder=embedder)

            # 검색 쿼리
            issues = state.get("issues", [])
            query_parts = [issue.get("description", "")[:100] for issue in issues[:3]]
            search_query = " ".join(query_parts) if query_parts else state.get("case_content", "")[:500]

            results = retriever.retrieve(query=search_query, top_k=5)
            similar_cases = [
                {
                    "case_number": r.get("metadata", {}).get("case_number", ""),
                    "summary": r.get("text", "")[:200]
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Similar case search failed: {e}")

        # 전략 수립 프롬프트
        issues = state.get("issues", [])
        parties = state.get("parties", [])

        prompt = f"""다음 복잡한 사건에 대한 법률 전략을 수립하세요.

사건 유형: {state.get("case_type", "other")}
복잡도 점수: {state.get("complexity_score", 0)}

당사자:
{json.dumps(parties, ensure_ascii=False, indent=2) if parties else "정보 없음"}

핵심 쟁점:
{json.dumps(issues, ensure_ascii=False, indent=2) if issues else "정보 없음"}

유사 사건:
{json.dumps(similar_cases, ensure_ascii=False, indent=2) if similar_cases else "없음"}

다음 내용을 포함한 전략 보고서를 작성하세요:

## 1. 핵심 주장
(주요 법률 논거 및 주장)

## 2. 증거 전략
(필요한 증거 및 수집 방안)

## 3. 예상 반론 및 대응
(상대측 주장 예상 및 반박 논거)

## 4. 승소 가능성
(예상 결과 및 근거)

전략 보고서:"""

        # PII 마스킹 적용 (OpenAI API에 개인정보 전송 방지)
        masker = get_masker(mode="balanced")
        masked_prompt, pii_mapping = masker.mask(prompt)
        logger.debug(f"[legal_strategist_agent] PII masked: {len(pii_mapping)} entities")

        strategy = llm_client.generate(
            prompt=masked_prompt,
            temperature=0.3,
            max_tokens=2000
        )

        # PII 복원 (응답에서 플레이스홀더를 원본으로 복원)
        strategy = masker.restore(strategy, pii_mapping)

        logger.info(f"[legal_strategist_agent] Strategy developed: {len(strategy)} chars")

        return {
            "legal_strategy": strategy,
            "completed_tasks": state.get("completed_tasks", []) + ["strategize"]
        }

    except Exception as e:
        logger.error(f"[legal_strategist_agent] Error: {e}")
        return {
            "legal_strategy": None,
            "completed_tasks": state.get("completed_tasks", []) + ["strategize_failed"]
        }


async def precedent_researcher_agent(state: CaseAnalysisState) -> Dict[str, Any]:
    """
    판례 조사 에이전트: 각 이슈별 판례 검색
    """
    logger.info("[precedent_researcher_agent] Researching precedents")

    try:
        issues = state.get("issues", [])
        case_content = state.get("case_content", "")

        # 검색 쿼리 구성
        if issues:
            query = " ".join([issue.get("description", "")[:100] for issue in issues[:3]])
        else:
            query = case_content[:500] if case_content else ""

        if not query:
            return {
                "related_precedents": [],
                "next_steps": ["관련 판례 상세 검토", "증거 자료 수집"],
                "completed_tasks": state.get("completed_tasks", []) + ["research"]
            }

        # 판례 검색
        precedents: List[PrecedentResult] = []

        try:
            from libs.rag_core.retrieval.retriever import LegalDocumentRetriever
            from libs.rag_core.embeddings.embedder import KoreanLegalEmbedder
            from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB
            from config.settings import settings

            embedder = KoreanLegalEmbedder()
            vectordb = QdrantVectorDB(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
                collection_name=settings.QDRANT_COLLECTION
            )
            retriever = LegalDocumentRetriever(vectordb=vectordb, embedder=embedder)

            # 각 이슈별 검색
            all_results = []
            for issue in issues[:3]:
                results = retriever.retrieve(
                    query=issue.get("description", ""),
                    top_k=3,
                    filter_metadata={"type": "precedent"}
                )
                all_results.extend(results)

            # 중복 제거
            seen = set()
            for result in all_results:
                metadata = result.get("metadata", {})
                case_number = metadata.get("case_number", "")

                if case_number and case_number in seen:
                    continue
                seen.add(case_number)

                court = metadata.get("court", "")
                if case_number and court:
                    title = f"{court} {case_number}"
                elif case_number:
                    title = f"판례 {case_number}"
                else:
                    title = "관련 판례"

                precedents.append({
                    "case_number": case_number,
                    "title": title,
                    "summary": result.get("text", "")[:350],
                    "relevance_score": result.get("score", 0.0),
                })

        except Exception as e:
            logger.warning(f"Precedent search failed: {e}")

        # 다음 단계 제시
        next_steps = [
            "관련 판례 상세 검토",
            "증거 자료 수집",
            "전문가 의견 확보",
            "소장/답변서 작성"
        ]

        logger.info(f"[precedent_researcher_agent] Found {len(precedents)} precedents")

        return {
            "related_precedents": precedents,
            "next_steps": next_steps,
            "completed_tasks": state.get("completed_tasks", []) + ["research"]
        }

    except Exception as e:
        logger.error(f"[precedent_researcher_agent] Error: {e}")
        return {
            "related_precedents": [],
            "next_steps": [],
            "completed_tasks": state.get("completed_tasks", []) + ["research_failed"]
        }


async def generate_analysis_node(state: CaseAnalysisState) -> Dict[str, Any]:
    """
    종합 분석 생성 노드: 최종 분석 보고서 생성
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
        legal_strategy = state.get("legal_strategy")
        complexity_score = state.get("complexity_score", 0)
        case_content = state.get("case_content", "")[:2000]

        # 분석 프롬프트
        prompt = f"""다음 정보를 바탕으로 사건 종합 분석을 작성해주세요.

사건 유형: {case_type}
복잡도 점수: {complexity_score}점

당사자 정보:
{json.dumps(parties, ensure_ascii=False, indent=2) if parties else "정보 없음"}

법적 쟁점:
{json.dumps(issues, ensure_ascii=False, indent=2) if issues else "정보 없음"}

관련 판례:
{json.dumps([p.get('title', '') for p in precedents[:3]], ensure_ascii=False) if precedents else "없음"}

{f"법률 전략: {legal_strategy[:500]}..." if legal_strategy else ""}

사건 요약:
{case_content}

다음 내용을 포함한 종합 분석을 작성해주세요:
1. 사건 개요
2. 주요 쟁점 분석
3. 관련 판례 참고
4. 법적 검토 의견
5. 향후 대응 방향

분석 결과:"""

        # PII 마스킹 적용 (OpenAI API에 개인정보 전송 방지)
        masker = get_masker(mode="balanced")
        masked_prompt, pii_mapping = masker.mask(prompt)
        logger.debug(f"[generate_analysis_node] PII masked: {len(pii_mapping)} entities")

        analysis = llm_client.generate(
            prompt=masked_prompt,
            temperature=0.3,
            max_tokens=2000
        )

        # PII 복원 (응답에서 플레이스홀더를 원본으로 복원)
        analysis = masker.restore(analysis, pii_mapping)

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
    Case Analysis Workflow 생성 (Complexity-based Routing)

    그래프 구조:
        START
          |
          v
        analyze
          |
          v
    assess_complexity
          |
          v
    [route_by_complexity]
       /        \
      v          v
   simple     complex
      |          |
      |          v
      |     strategize
      |          |
      +----+-----+
           |
           v
        research
           |
           v
    generate_analysis
           |
           v
          END

    Returns:
        컴파일된 StateGraph
    """
    workflow = StateGraph(CaseAnalysisState)

    # 노드 추가
    workflow.add_node("analyze", case_analyst_agent)
    workflow.add_node("assess_complexity", complexity_assessor_node)
    workflow.add_node("strategize", legal_strategist_agent)
    workflow.add_node("research", precedent_researcher_agent)
    workflow.add_node("generate_analysis", generate_analysis_node)

    # 엣지 정의
    # START -> analyze
    workflow.add_edge(START, "analyze")

    # analyze -> assess_complexity
    workflow.add_edge("analyze", "assess_complexity")

    # assess_complexity -> [조건부] strategize or research
    workflow.add_conditional_edges(
        "assess_complexity",
        route_by_complexity,
        {
            "complex": "strategize",
            "simple": "research"
        }
    )

    # strategize -> research (복잡한 사건은 전략 수립 후 판례 검색)
    workflow.add_edge("strategize", "research")

    # research -> generate_analysis
    workflow.add_edge("research", "generate_analysis")

    # generate_analysis -> END
    workflow.add_edge("generate_analysis", END)

    # 컴파일 (Checkpointing 없음)
    return workflow.compile()


# ============================================================================
# Workflow Class (BaseWorkflow 상속)
# ============================================================================

class CaseWorkflow(BaseWorkflow[CaseAnalysisState]):
    """
    Case Analysis Workflow 클래스 (Complexity-based Routing)

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
        workflow.add_node("analyze", case_analyst_agent)
        workflow.add_node("assess_complexity", complexity_assessor_node)
        workflow.add_node("strategize", legal_strategist_agent)
        workflow.add_node("research", precedent_researcher_agent)
        workflow.add_node("generate_analysis", generate_analysis_node)

        # 엣지 정의
        workflow.add_edge(START, "analyze")
        workflow.add_edge("analyze", "assess_complexity")

        workflow.add_conditional_edges(
            "assess_complexity",
            route_by_complexity,
            {
                "complex": "strategize",
                "simple": "research"
            }
        )

        workflow.add_edge("strategize", "research")
        workflow.add_edge("research", "generate_analysis")
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
            complexity_score=0,
            legal_strategy=None,
            next_steps=[],
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
            "complexity_score": result.get("complexity_score", 0),
            "legal_strategy": result.get("legal_strategy"),
            "next_steps": result.get("next_steps", []),
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
