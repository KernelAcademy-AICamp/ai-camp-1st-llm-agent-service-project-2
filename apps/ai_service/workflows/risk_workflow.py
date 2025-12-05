"""
Risk Analysis Workflow

Phase 4 - Week 12: 리스크 분석 LangGraph 워크플로우 (Iterative Refinement)

워크플로우 흐름:
1. identify_node: 리스크 식별 (risk_identifier_agent)
2. assess_node: 심각도 평가 (severity_assessor_agent)
3. check_review_node: 전문가 검토 필요 여부 확인
4. [조건부] review_node: 전문가 검토 (Human-in-the-Loop, interrupt)
5. [조건부] should_refine: 재분석 필요 시 identify로 돌아감 (최대 3회)
6. mitigate_node: 완화 전략 수립 (mitigation_planner_agent)

Iterative Refinement Pattern:
- review → should_refine → "refine" → identify (최대 3회)
- review → should_refine → "proceed" → mitigate → END

Checkpointing: 필수 (Human-in-the-Loop, TTL: 7일)

사용:
    from apps.ai_service.workflows.risk_workflow import (
        create_risk_workflow,
        RiskWorkflow
    )

    workflow = RiskWorkflow()
    result = await workflow.arun(text="계약서 내용...", doc_type="CONTRACT")

    # Human-in-the-Loop 재개
    result = await workflow.resume(
        thread_id="xxx",
        human_review={"approved": True, "comments": "검토 완료"}
    )
"""

from typing import Dict, Any, Optional, List
import logging
import json
import re

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

from apps.ai_service.workflows.base import BaseWorkflow
from apps.ai_service.workflows.states.risk_state import (
    RiskAnalysisState,
    RiskItem,
    HumanReviewResult,
    RiskSeverity,
    SeverityAssessment,
)

logger = logging.getLogger(__name__)

# Constants
RISK_CHECKPOINT_TTL = 7 * 24 * 3600  # 7일
MAX_REFINEMENT_ITERATIONS = 3


# ============================================================================
# Node Functions
# ============================================================================

async def risk_identifier_agent(state: RiskAnalysisState) -> Dict[str, Any]:
    """
    리스크 식별 에이전트: 문서에서 리스크 요소 추출

    Iterative Refinement: refinement_iteration 증가
    """
    logger.info("[risk_identifier_agent] Identifying risks")

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
                "error": "No text provided for risk analysis",
                "completed_tasks": state.get("completed_tasks", []) + ["identify_failed"]
            }

        # 과거 리스크 패턴 및 규제 요구사항
        risk_patterns = """
    - 불공정 조항: 일방적 계약 해지, 과도한 위약금
    - 개인정보 위험: 동의 없는 수집, 제3자 제공
    - 규제 위반: 소비자보호법, 전자상거래법 위반
    """

        regulations = """
    - 전자상거래법 제17조 (청약철회)
    - 개인정보보호법 제15조 (개인정보 수집·이용)
    - 소비자기본법 제16조 (소비자분쟁해결기준)
    """

        # 리스크 식별 프롬프트
        prompt = f"""당신은 법률 리스크 분석 전문가입니다. 다음 {doc_type} 문서에서 잠재적 리스크를 식별해주세요.

문서 내용:
{text[:8000]}

참고 리스크 패턴:
{risk_patterns}

규제 요구사항:
{regulations}

다음 JSON 배열 형식으로 리스크를 식별해주세요:

[
  {{
    "risk_type": "LEGAL|FINANCIAL|COMPLIANCE|OPERATIONAL|REPUTATIONAL|OTHER",
    "description": "리스크에 대한 상세 설명",
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
    "recommendation": "리스크 완화 권장사항",
    "clause_reference": "관련 조항 (있는 경우)"
  }}
]

리스크 심각도 기준:
- CRITICAL: 즉시 조치 필요 (법적 분쟁, 대규모 손실 가능성)
- HIGH: 높은 주의 필요 (상당한 리스크)
- MEDIUM: 검토 권장 (일반적 리스크)
- LOW: 참고 수준 (경미한 리스크)
- INFO: 정보성 (특이사항)

최대 5개의 주요 리스크만 식별하세요. 반드시 유효한 JSON 형식으로만 응답해주세요."""

        response = llm_client.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=1500
        )

        # JSON 파싱
        risks: List[RiskItem] = []

        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))

                for risk_data in data:
                    severity = risk_data.get("severity", "MEDIUM").upper()
                    if severity not in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
                        severity = "MEDIUM"

                    risks.append({
                        "risk_type": risk_data.get("risk_type", "OTHER"),
                        "description": risk_data.get("description", ""),
                        "severity": severity,
                        "recommendation": risk_data.get("recommendation"),
                        "clause_reference": risk_data.get("clause_reference"),
                    })
        except Exception as e:
            logger.warning(f"Failed to parse risks: {e}")

        # Refinement iteration 증가
        current_iteration = state.get("refinement_iteration", 0) + 1

        logger.info(f"[risk_identifier_agent] Identified {len(risks)} risks (iteration {current_iteration})")

        return {
            "identified_risks": risks,
            "refinement_iteration": current_iteration,
            "completed_tasks": state.get("completed_tasks", []) + [f"identify_risks_iter{current_iteration}"]
        }

    except Exception as e:
        logger.error(f"[risk_identifier_agent] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["identify_risks_failed"]
        }


async def severity_assessor_agent(state: RiskAnalysisState) -> Dict[str, Any]:
    """
    심각도 평가 에이전트: 전체 리스크 레벨 평가 및 점수화
    """
    logger.info("[severity_assessor_agent] Assessing overall severity")

    try:
        risks = state.get("identified_risks", [])

        # 심각도별 점수
        severity_scores = {
            "CRITICAL": 100,
            "HIGH": 75,
            "MEDIUM": 50,
            "LOW": 25,
            "INFO": 10
        }

        # CRITICAL/HIGH 리스크 카운트
        critical_count = sum(1 for r in risks if r.get("severity") == "CRITICAL")
        high_count = sum(1 for r in risks if r.get("severity") == "HIGH")

        # Overall score 계산
        if risks:
            overall_score = sum(
                severity_scores.get(r.get("severity", "MEDIUM"), 50)
                for r in risks
            ) / len(risks)
        else:
            overall_score = 0

        # 전문가 검토 필요 여부 결정
        requires_human_review = (
            critical_count > 0 or
            high_count >= 3 or
            overall_score >= 70
        )

        severity_assessment: SeverityAssessment = {
            "overall_score": overall_score,
            "critical_count": critical_count,
            "high_count": high_count
        }

        logger.info(
            f"[severity_assessor_agent] Score={overall_score:.1f}, "
            f"Critical={critical_count}, High={high_count}, "
            f"requires_review={requires_human_review}"
        )

        return {
            "severity_assessment": severity_assessment,
            "requires_human_review": requires_human_review,
            "completed_tasks": state.get("completed_tasks", []) + ["assess_severity"]
        }

    except Exception as e:
        logger.error(f"[severity_assessor_agent] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["assess_severity_failed"]
        }


async def check_review_node(state: RiskAnalysisState) -> Dict[str, Any]:
    """
    리뷰 필요 여부 확인 노드
    """
    logger.info("[check_review_node] Checking if review is needed")

    # 이미 상태에서 결정됨
    return {
        "completed_tasks": state.get("completed_tasks", []) + ["check_review"]
    }


def needs_human_review(state: RiskAnalysisState) -> bool:
    """Human review 필요 여부 반환"""
    return state.get("requires_human_review", False)


async def human_review_node(state: RiskAnalysisState) -> Dict[str, Any]:
    """
    Human-in-the-Loop: 전문가 리뷰 대기

    interrupt() 함수 동작 방식:
    1. interrupt()가 호출되면 워크플로우가 중단됨
    2. 클라이언트에서 Command(resume=value)로 재개 시
    3. interrupt()의 반환값으로 value가 전달됨
    """
    logger.info("[human_review_node] Requesting human review (interrupt)")

    # 이미 검토 완료된 경우 스킵
    if state.get("human_review"):
        logger.info("[human_review_node] Human review already completed, skipping")
        return {
            "completed_tasks": state.get("completed_tasks", []) + ["human_review_skipped"]
        }

    # 검토 대기 중인 리스크 정보 구성
    risks = state.get("identified_risks", [])
    assessment = state.get("severity_assessment", {})

    critical_risks = [r for r in risks if r.get("severity") == "CRITICAL"]
    high_risks = [r for r in risks if r.get("severity") == "HIGH"]

    review_info = {
        "message": "고위험 리스크가 발견되어 전문가 검토가 필요합니다.",
        "document_id": state.get("document_id"),
        "total_risks": len(risks),
        "critical_risks": critical_risks,
        "high_risks": high_risks,
        "severity_assessment": assessment,
        "awaiting_review": True,
        "refinement_iteration": state.get("refinement_iteration", 0),
    }

    # Human-in-the-Loop: 워크플로우 중단
    # Command(resume={"approved": True, "feedback": "..."})로 재개
    feedback = interrupt(review_info)

    # 피드백 형식: {"approved": bool, "comments": str, "feedback": str}
    if feedback:
        logger.info(f"[human_review_node] Human review received")

        human_review: HumanReviewResult = {
            "reviewer_id": feedback.get("reviewer_id"),
            "approved": feedback.get("approved", False),
            "comments": feedback.get("comments"),
            "modified_risks": feedback.get("modified_risks"),
        }

        return {
            "human_review": human_review,
            "review_feedback": feedback.get("feedback") or feedback.get("comments") or "",
            "completed_tasks": state.get("completed_tasks", []) + ["human_review"]
        }

    return {
        "completed_tasks": state.get("completed_tasks", []) + ["human_review_pending"]
    }


def should_refine(state: RiskAnalysisState) -> str:
    """
    리뷰 피드백에 따라 재분석 여부 결정

    Returns:
        "refine" if feedback contains "refine" and iteration < 3, "proceed" otherwise
    """
    review_feedback = state.get("review_feedback", "")
    refinement_iteration = state.get("refinement_iteration", 0)

    # 피드백에 "refine" 또는 "재분석" 포함 시 재분석
    should_do_refine = (
        review_feedback and
        ("refine" in review_feedback.lower() or "재분석" in review_feedback)
    )

    # 최대 3회 refinement
    if should_do_refine and refinement_iteration < MAX_REFINEMENT_ITERATIONS:
        logger.info(f"[should_refine] Refinement requested (iteration {refinement_iteration})")
        return "refine"

    logger.info("[should_refine] Proceeding to mitigate")
    return "proceed"


async def mitigation_planner_agent(state: RiskAnalysisState) -> Dict[str, Any]:
    """
    완화 전략 수립 에이전트: 리스크의 recommendation을 사용 (LLM 호출 없음)

    Note: risk_identifier_agent가 이미 각 리스크에 recommendation을 생성하므로
          별도 LLM 호출 없이 해당 정보를 mitigation_strategies로 변환
    """
    logger.info("[mitigation_planner_agent] Extracting strategies from risk recommendations (no LLM)")

    try:
        risks = state.get("identified_risks", [])
        human_review = state.get("human_review")

        # 전문가 검토 결과 반영
        if human_review and human_review.get("modified_risks"):
            risks = human_review.get("modified_risks")

        # 리스크의 recommendation을 전략으로 변환 (LLM 호출 없음)
        strategies = []
        for i, risk in enumerate(risks, 1):
            risk_type = risk.get("risk_type", "OTHER")
            severity = risk.get("severity", "MEDIUM")
            recommendation = risk.get("recommendation", "")

            if recommendation:
                strategies.append(f"{i}. [{severity}] {risk_type}: {recommendation}")

        logger.info(f"[mitigation_planner_agent] Extracted {len(strategies)} strategies (no LLM)")

        return {
            "mitigation_strategies": strategies,
            "completed_tasks": state.get("completed_tasks", []) + ["mitigate"]
        }

    except Exception as e:
        logger.error(f"[mitigation_planner_agent] Error: {e}")
        return {
            "mitigation_strategies": [],
            "completed_tasks": state.get("completed_tasks", []) + ["mitigate_failed"]
        }


async def generate_report_node(state: RiskAnalysisState) -> Dict[str, Any]:
    """
    보고서 생성 노드: 템플릿 기반 보고서 생성 (LLM 호출 없음)

    Note: LLM 호출 없이 템플릿을 사용하여 빠르게 보고서 생성
          리스크 정보와 권장사항은 risk_identifier_agent에서 이미 생성됨

    Returns:
        - summary: 프론트엔드에 표시될 간결한 요약 (3-5줄)
        - report: 상세 보고서 (전체 분석)
    """
    logger.info("[generate_report_node] Generating risk report (template-based, no LLM)")

    try:
        risks = state.get("identified_risks", [])
        human_review = state.get("human_review")
        doc_type = state.get("doc_type", "CONTRACT")
        assessment = state.get("severity_assessment", {})
        strategies = state.get("mitigation_strategies", [])

        # 전문가 검토 결과 반영
        review_notes = ""
        if human_review:
            if human_review.get("approved"):
                review_notes = f"\n\n**전문가 검토 완료**: {human_review.get('comments', '')}"
            else:
                review_notes = f"\n\n**전문가 검토 의견**: {human_review.get('comments', '')}"

            if human_review.get("modified_risks"):
                risks = human_review.get("modified_risks")

        # 리스크 통계
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for risk in risks:
            sev = risk.get("severity", "MEDIUM")
            if sev in severity_counts:
                severity_counts[sev] += 1

        # 위험 수준 평가
        overall_score = assessment.get("overall_score", 0)
        if overall_score >= 70:
            risk_level = "높음"
            risk_conclusion = "전문가 검토가 강력히 권장됩니다."
        elif overall_score >= 40:
            risk_level = "중간"
            risk_conclusion = "주요 조항에 대한 검토가 권장됩니다."
        else:
            risk_level = "낮음"
            risk_conclusion = "일반적인 주의를 기울여 진행하시면 됩니다."

        # ============================================
        # 간결한 Summary 생성 (프론트엔드 표시용)
        # 통계는 프론트엔드에서 별도 카드로 표시하므로 여기서는 내용 분석만
        # ============================================

        # 주요 리스크 설명 (CRITICAL/HIGH 우선)
        high_priority_risks = [r for r in risks if r.get("severity") in ["CRITICAL", "HIGH"]]
        other_risks = [r for r in risks if r.get("severity") not in ["CRITICAL", "HIGH"]]

        summary_parts = []

        # 주요 리스크 설명
        if high_priority_risks:
            summary_parts.append("### 주요 위험 요소")
            for risk in high_priority_risks[:3]:
                risk_type = risk.get('risk_type', 'OTHER')
                desc = risk.get('description', '')[:100]
                summary_parts.append(f"- **{risk_type}**: {desc}")

        # 기타 리스크 요약
        if other_risks:
            summary_parts.append("\n### 추가 검토 사항")
            for risk in other_risks[:2]:
                risk_type = risk.get('risk_type', 'OTHER')
                desc = risk.get('description', '')[:80]
                summary_parts.append(f"- {risk_type}: {desc}")

        # 결론
        summary_parts.append(f"\n### 결론\n{risk_conclusion}")

        summary = "\n".join(summary_parts) if summary_parts else "분석된 리스크가 없습니다."

        # ============================================
        # 상세 Report 생성 (전체 분석)
        # ============================================
        report = f"""## 

### 요약
- 문서 유형: {doc_type}
- 전체 위험 점수: {overall_score:.1f}점 ({risk_level})
- 식별된 리스크: 총 {len(risks)}건 (CRITICAL: {severity_counts['CRITICAL']}, HIGH: {severity_counts['HIGH']}, MEDIUM: {severity_counts['MEDIUM']})

### 주요 리스크
"""
        # CRITICAL/HIGH 리스크만 상세 표시
        critical_high = [r for r in risks if r.get("severity") in ["CRITICAL", "HIGH"]]
        if critical_high:
            for i, risk in enumerate(critical_high[:3], 1):  # 최대 3개만
                report += f"""
**{i}. [{risk.get('severity')}] {risk.get('risk_type', 'OTHER')}**
- {risk.get('description', '')}
"""
        else:
            report += "> 고위험 리스크가 발견되지 않았습니다.\n"

        # 권장 조치 (최대 3개)
        if strategies:
            report += "\n### 권장 조치\n"
            for strategy in strategies[:3]:
                report += f"- {strategy}\n"

        report += f"\n### 결론\n{risk_conclusion}{review_notes}"

        logger.info(f"[generate_report_node] Generated summary ({len(summary)} chars) + report ({len(report)} chars)")

        return {
            "summary": summary,
            "report": report,
            "completed_tasks": state.get("completed_tasks", []) + ["generate_report"]
        }

    except Exception as e:
        logger.error(f"[generate_report_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["generate_report_failed"]
        }


# ============================================================================
# Routing Functions
# ============================================================================

def route_human_review(state: RiskAnalysisState) -> str:
    """
    전문가 검토 라우팅 함수

    Returns:
        "human_review" if review needed AND skip_human_review is False, "mitigate" otherwise

    Note:
        Django backend에서 호출 시 자동 진행을 위해 skip_human_review=True로 설정
        Human-in-the-Loop가 필요한 경우 skip_human_review=False로 설정
    """
    skip_review = state.get("skip_human_review", True)  # 기본값: 자동 진행

    if state.get("requires_human_review", False) and not state.get("human_review") and not skip_review:
        return "human_review"
    return "mitigate"


# ============================================================================
# Workflow Graph Creation
# ============================================================================

def create_risk_workflow(use_checkpointing: bool = True) -> StateGraph:
    """
    Risk Analysis Workflow 생성 (Iterative Refinement)

    그래프 구조:
        START
          |
          v
       identify <-----------------------+
          |                             |
          v                             |
        assess                          |
          |                             |
          v                             |
    check_review                        |
          |                             |
          v                             |
    [needs_human_review]                |
       /        \                       |
      v          v                      |
  review      mitigate                  |
      |          |                      |
      v          v                      |
[should_refine]  |                      |
   /      \      |                      |
  v        v     |                      |
refine  proceed  |                      |
  |        |     |                      |
  +--------+-----+                      |
           |                            |
           v                            |
      generate_report                   |
           |                            |
           v                            |
          END

    Cyclic: review → should_refine → "refine" → identify (최대 3회)

    Returns:
        컴파일된 StateGraph
    """
    workflow = StateGraph(RiskAnalysisState)

    # 노드 추가
    workflow.add_node("identify", risk_identifier_agent)
    workflow.add_node("assess", severity_assessor_agent)
    workflow.add_node("check_review", check_review_node)
    workflow.add_node("review", human_review_node)
    workflow.add_node("mitigate", mitigation_planner_agent)
    workflow.add_node("generate_report", generate_report_node)

    # 엣지 정의
    workflow.add_edge(START, "identify")
    workflow.add_edge("identify", "assess")
    workflow.add_edge("assess", "check_review")

    # check_review -> [조건부] review or mitigate
    workflow.add_conditional_edges(
        "check_review",
        route_human_review,
        {
            "human_review": "review",
            "mitigate": "mitigate"
        }
    )

    # review -> [조건부] identify (refine) or mitigate (proceed)
    workflow.add_conditional_edges(
        "review",
        should_refine,
        {
            "refine": "identify",  # Cyclic: 재분석
            "proceed": "mitigate"
        }
    )

    # mitigate -> generate_report
    workflow.add_edge("mitigate", "generate_report")

    # generate_report -> END
    workflow.add_edge("generate_report", END)

    # 컴파일 (Checkpointing 포함)
    if use_checkpointing:
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()


# ============================================================================
# Workflow Class (BaseWorkflow 상속)
# ============================================================================

class RiskWorkflow(BaseWorkflow[RiskAnalysisState]):
    """
    Risk Analysis Workflow 클래스 (Iterative Refinement)

    Human-in-the-Loop 지원

    사용:
        workflow = RiskWorkflow()

        # 분석 시작
        result = await workflow.arun(
            text="계약서 내용...",
            doc_type="CONTRACT"
        )

        # 전문가 검토 후 재개 (피드백에 "refine" 포함 시 재분석)
        result = await workflow.resume(
            thread_id=result["session_id"],
            human_review={
                "approved": False,
                "comments": "refine - 추가 리스크 검토 필요"
            }
        )
    """

    def __init__(self, use_checkpointing: bool = True):
        self.use_checkpointing = use_checkpointing
        self.checkpointer = MemorySaver() if use_checkpointing else None
        super().__init__(
            name="risk_analysis_workflow",
            use_checkpointing=use_checkpointing
        )

    def create_graph(self) -> StateGraph:
        """StateGraph 생성"""
        workflow = StateGraph(RiskAnalysisState)

        # 노드 추가
        workflow.add_node("identify", risk_identifier_agent)
        workflow.add_node("assess", severity_assessor_agent)
        workflow.add_node("check_review", check_review_node)
        workflow.add_node("review", human_review_node)
        workflow.add_node("mitigate", mitigation_planner_agent)
        workflow.add_node("generate_report", generate_report_node)

        # 엣지 정의
        workflow.add_edge(START, "identify")
        workflow.add_edge("identify", "assess")
        workflow.add_edge("assess", "check_review")

        workflow.add_conditional_edges(
            "check_review",
            route_human_review,
            {
                "human_review": "review",
                "mitigate": "mitigate"
            }
        )

        workflow.add_conditional_edges(
            "review",
            should_refine,
            {
                "refine": "identify",
                "proceed": "mitigate"
            }
        )

        workflow.add_edge("mitigate", "generate_report")
        workflow.add_edge("generate_report", END)

        return workflow

    def _build_and_compile(self) -> StateGraph:
        """그래프 생성 및 컴파일 (오버라이드)"""
        graph = self.create_graph()

        if self.use_checkpointing:
            return graph.compile(checkpointer=self.checkpointer)
        return graph.compile()

    def create_initial_state(
        self,
        text: str,
        doc_type: str = "CONTRACT",
        document_id: Optional[str] = None,
        skip_human_review: bool = True,
        **kwargs
    ) -> RiskAnalysisState:
        """
        초기 상태 생성

        Args:
            text: 분석할 텍스트
            doc_type: 문서 타입
            document_id: 문서 ID
            skip_human_review: Human-in-the-Loop 스킵 여부 (기본: True)

        Returns:
            초기 RiskAnalysisState
        """
        return RiskAnalysisState(
            document_id=document_id,
            text=text,
            doc_type=doc_type,
            identified_risks=[],
            severity_assessment=None,
            mitigation_strategies=[],
            requires_human_review=False,
            human_review=None,
            review_feedback=None,
            refinement_iteration=0,
            summary=None,
            report=None,
            completed_tasks=[],
            iteration_count=0,
            skip_human_review=skip_human_review,
            error=None,
        )

    async def resume(
        self,
        thread_id: str,
        human_review: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Human-in-the-Loop 재개

        전문가 검토 후 워크플로우 재개.
        피드백에 "refine" 포함 시 최대 3회까지 재분석.

        Args:
            thread_id: 세션 ID (스레드 ID)
            human_review: 검토 결과
                {
                    "approved": bool,
                    "comments": str (refine 포함 시 재분석),
                    "feedback": str,
                    "modified_risks": List[RiskItem] (선택)
                }

        Returns:
            워크플로우 실행 결과
        """
        import time
        start_time = time.time()

        logger.info(f"[{self.name}] Resuming workflow, thread_id={thread_id}")

        try:
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ttl": RISK_CHECKPOINT_TTL
                }
            }

            # Command를 사용하여 interrupt에서 반환할 값 전달
            result = await self.graph.ainvoke(
                Command(resume=human_review),
                config=config
            )

            processing_time = time.time() - start_time
            logger.info(f"[{self.name}] Resumed in {processing_time:.2f}s")

            return self._format_result(result, processing_time, thread_id)

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"[{self.name}] Resume error: {e}")
            return self._format_error(e, processing_time, thread_id)

    async def arun(self, **kwargs) -> Dict[str, Any]:
        """
        워크플로우 비동기 실행 (오버라이드)

        Checkpointing을 위한 thread_id 설정
        """
        import time
        import uuid

        start_time = time.time()
        session_id = kwargs.get("session_id") or str(uuid.uuid4())

        logger.info(f"[{self.name}] Starting async run, session={session_id}")

        try:
            initial_state = self.create_initial_state(**kwargs)

            config = {
                "configurable": {
                    "thread_id": session_id,
                    "checkpoint_ttl": RISK_CHECKPOINT_TTL
                }
            }

            result = await self.graph.ainvoke(initial_state, config=config)

            processing_time = time.time() - start_time
            logger.info(f"[{self.name}] Completed in {processing_time:.2f}s")

            return self._format_result(result, processing_time, session_id)

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"[{self.name}] Error: {e}")
            return self._format_error(e, processing_time, session_id)

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
        # 전문가 검토 대기 중인지 확인
        awaiting_review = (
            result.get("requires_human_review", False) and
            not result.get("human_review") and
            not result.get("report")
        )

        return {
            "success": result.get("error") is None,
            "document_id": result.get("document_id"),
            "doc_type": result.get("doc_type"),
            "identified_risks": result.get("identified_risks", []),
            "severity_assessment": result.get("severity_assessment"),
            "mitigation_strategies": result.get("mitigation_strategies", []),
            "requires_human_review": result.get("requires_human_review", False),
            "human_review": result.get("human_review"),
            "refinement_iteration": result.get("refinement_iteration", 0),
            "summary": result.get("summary"),
            "report": result.get("report"),
            "awaiting_review": awaiting_review,
            "completed_tasks": result.get("completed_tasks", []),
            "processing_time": processing_time,
            "session_id": session_id,
            "error": result.get("error"),
        }


# ============================================================================
# Factory Functions
# ============================================================================

def get_risk_workflow(use_checkpointing: bool = True) -> RiskWorkflow:
    """RiskWorkflow 인스턴스 반환"""
    return RiskWorkflow(use_checkpointing=use_checkpointing)
