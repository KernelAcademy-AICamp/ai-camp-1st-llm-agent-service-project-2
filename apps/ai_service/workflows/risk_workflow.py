"""
Risk Analysis Workflow

Phase 4 - Week 12: 리스크 분석 LangGraph 워크플로우

워크플로우 흐름:
1. identify_risks_node: 리스크 식별
2. assess_severity_node: 심각도 평가
3. check_human_review_node: 전문가 검토 필요 여부 확인
4. [조건부] human_review_node: 전문가 검토 (interrupt)
5. generate_report_node: 보고서 생성

Checkpointing: 필수 (Human-in-the-Loop, TTL: 7일)

Human-in-the-Loop:
- 고위험(CRITICAL/HIGH) 리스크 발견 시 전문가 검토 요청
- langgraph.types.interrupt()로 워크플로우 중단
- 전문가 검토 후 resume로 재개

사용:
    from apps.ai_service.workflows.risk_workflow import (
        create_risk_workflow,
        RiskWorkflow
    )

    # 워크플로우 실행
    workflow = RiskWorkflow()
    result = await workflow.arun(
        text="계약서 내용...",
        doc_type="CONTRACT"
    )

    # Human-in-the-Loop 재개
    result = await workflow.resume(
        thread_id="xxx",
        human_review={
            "approved": True,
            "comments": "검토 완료"
        }
    )
"""

from typing import Dict, Any, Optional, List
import logging
import json
import os

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

from apps.ai_service.workflows.base import BaseWorkflow
from apps.ai_service.workflows.states.risk_state import (
    RiskAnalysisState,
    RiskItem,
    HumanReviewResult,
    RiskSeverity,
)

logger = logging.getLogger(__name__)

# Checkpointing TTL (7일)
RISK_CHECKPOINT_TTL = 7 * 24 * 3600


# ============================================================================
# Node Functions
# ============================================================================

async def identify_risks_node(state: RiskAnalysisState) -> Dict[str, Any]:
    """
    리스크 식별 노드: 문서에서 리스크 요소 추출

    기존 services/risk_analyzer.py 로직 활용
    """
    logger.info("[identify_risks_node] Identifying risks")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client

        llm_client = get_llm_client()
        text = state.get("text", "")
        doc_type = state.get("doc_type", "CONTRACT")

        if not text:
            return {
                "error": "No text provided for risk analysis",
                "completed_tasks": state.get("completed_tasks", []) + ["identify_risks_failed"]
            }

        # 리스크 식별 프롬프트
        prompt = f"""당신은 법률 리스크 분석 전문가입니다. 다음 {doc_type} 문서에서 잠재적 리스크를 식별해주세요.

문서 내용:
{text[:8000]}

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

최대 10개의 리스크를 식별하세요. 반드시 유효한 JSON 형식으로만 응답해주세요."""

        response = llm_client.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=3000
        )

        # JSON 파싱
        risks: List[RiskItem] = []

        try:
            import re
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

        logger.info(f"[identify_risks_node] Identified {len(risks)} risks")

        return {
            "identified_risks": risks,
            "completed_tasks": state.get("completed_tasks", []) + ["identify_risks"]
        }

    except Exception as e:
        logger.error(f"[identify_risks_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["identify_risks_failed"]
        }


async def assess_severity_node(state: RiskAnalysisState) -> Dict[str, Any]:
    """
    심각도 평가 노드: 전체 리스크 레벨 평가

    CRITICAL/HIGH 리스크가 있으면 전문가 검토 플래그 설정
    """
    logger.info("[assess_severity_node] Assessing overall severity")

    try:
        risks = state.get("identified_risks", [])

        # CRITICAL/HIGH 리스크 카운트
        critical_count = sum(1 for r in risks if r.get("severity") == "CRITICAL")
        high_count = sum(1 for r in risks if r.get("severity") == "HIGH")

        # 전문가 검토 필요 여부 결정
        requires_human_review = (critical_count > 0) or (high_count >= 2)

        logger.info(
            f"[assess_severity_node] Critical={critical_count}, High={high_count}, "
            f"requires_review={requires_human_review}"
        )

        return {
            "requires_human_review": requires_human_review,
            "completed_tasks": state.get("completed_tasks", []) + ["assess_severity"]
        }

    except Exception as e:
        logger.error(f"[assess_severity_node] Error: {e}")
        return {
            "error": str(e),
            "completed_tasks": state.get("completed_tasks", []) + ["assess_severity_failed"]
        }


def route_human_review(state: RiskAnalysisState) -> str:
    """
    전문가 검토 라우팅 함수

    Returns:
        "human_review" if review needed, "generate_report" otherwise
    """
    if state.get("requires_human_review", False) and not state.get("human_review"):
        return "human_review"
    return "generate_report"


async def human_review_node(state: RiskAnalysisState) -> Dict[str, Any]:
    """
    전문가 검토 노드: Human-in-the-Loop

    interrupt()를 사용하여 워크플로우 중단
    전문가가 검토 후 resume()로 재개
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
    critical_risks = [r for r in risks if r.get("severity") == "CRITICAL"]
    high_risks = [r for r in risks if r.get("severity") == "HIGH"]

    review_info = {
        "message": "고위험 리스크가 발견되어 전문가 검토가 필요합니다.",
        "document_id": state.get("document_id"),
        "total_risks": len(risks),
        "critical_risks": critical_risks,
        "high_risks": high_risks,
        "awaiting_review": True,
    }

    # Human-in-the-Loop: 워크플로우 중단
    # 전문가가 검토 후 resume()로 human_review 값을 제공하면 재개
    human_review_result = interrupt(review_info)

    # interrupt()에서 반환된 값은 resume() 시 제공된 값
    # 형식: {"approved": bool, "comments": str, "modified_risks": List[RiskItem]}
    if human_review_result:
        logger.info(f"[human_review_node] Human review received: {human_review_result}")
        return {
            "human_review": human_review_result,
            "completed_tasks": state.get("completed_tasks", []) + ["human_review"]
        }

    # 검토 대기 중
    return {
        "completed_tasks": state.get("completed_tasks", []) + ["human_review_pending"]
    }


async def generate_report_node(state: RiskAnalysisState) -> Dict[str, Any]:
    """
    보고서 생성 노드: 최종 리스크 분석 보고서 생성
    """
    logger.info("[generate_report_node] Generating risk report")

    try:
        from libs.rag_core.llm.llm_client import get_llm_client

        llm_client = get_llm_client()

        risks = state.get("identified_risks", [])
        human_review = state.get("human_review")
        doc_type = state.get("doc_type", "CONTRACT")

        # 전문가 검토 결과 반영
        review_notes = ""
        if human_review:
            if human_review.get("approved"):
                review_notes = f"\n\n**전문가 검토 완료**: {human_review.get('comments', '')}"
            else:
                review_notes = f"\n\n**전문가 검토 의견**: {human_review.get('comments', '')}"

            # 수정된 리스크 반영
            if human_review.get("modified_risks"):
                risks = human_review.get("modified_risks")

        # 리스크 통계
        severity_counts = {}
        for risk in risks:
            sev = risk.get("severity", "MEDIUM")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        # 보고서 생성 프롬프트
        prompt = f"""다음 리스크 분석 결과를 바탕으로 {doc_type} 문서의 리스크 분석 보고서를 작성해주세요.

식별된 리스크:
{json.dumps(risks, ensure_ascii=False, indent=2)}

심각도별 통계:
- CRITICAL: {severity_counts.get('CRITICAL', 0)}건
- HIGH: {severity_counts.get('HIGH', 0)}건
- MEDIUM: {severity_counts.get('MEDIUM', 0)}건
- LOW: {severity_counts.get('LOW', 0)}건
- INFO: {severity_counts.get('INFO', 0)}건

다음 형식으로 보고서를 작성해주세요:

## 리스크 분석 보고서

### 1. 요약
(전반적인 리스크 수준 및 주요 발견사항)

### 2. 주요 리스크
(CRITICAL/HIGH 리스크 상세 설명)

### 3. 권장 조치
(리스크 완화를 위한 구체적 조치사항)

### 4. 결론
(종합 의견 및 다음 단계){review_notes}

보고서:"""

        report = llm_client.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=2000
        )

        logger.info(f"[generate_report_node] Report generated: {len(report)} chars")

        return {
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
# Workflow Graph Creation
# ============================================================================

def create_risk_workflow(use_checkpointing: bool = True) -> StateGraph:
    """
    Risk Analysis Workflow 생성

    그래프 구조:
        START
          |
          v
    identify_risks
          |
          v
    assess_severity
          |
          v
    [조건부 분기]
          |
    +-----+-----+
    |           |
    v           v
human_review  generate_report
    |           ^
    |           |
    +-----------+
          |
          v
        END

    Checkpointing: 필수 (Human-in-the-Loop)

    Args:
        use_checkpointing: Checkpointing 사용 여부 (기본: True)

    Returns:
        컴파일된 StateGraph
    """
    # StateGraph 생성
    workflow = StateGraph(RiskAnalysisState)

    # 노드 추가
    workflow.add_node("identify_risks", identify_risks_node)
    workflow.add_node("assess_severity", assess_severity_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("generate_report", generate_report_node)

    # 엣지 정의
    # START -> identify_risks
    workflow.add_edge(START, "identify_risks")

    # identify_risks -> assess_severity
    workflow.add_edge("identify_risks", "assess_severity")

    # assess_severity -> [조건부] human_review or generate_report
    workflow.add_conditional_edges(
        "assess_severity",
        route_human_review,
        {
            "human_review": "human_review",
            "generate_report": "generate_report",
        }
    )

    # human_review -> generate_report
    workflow.add_edge("human_review", "generate_report")

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
    Risk Analysis Workflow 클래스

    BaseWorkflow를 상속하여 표준화된 인터페이스 제공
    Human-in-the-Loop 지원

    사용:
        workflow = RiskWorkflow()

        # 분석 시작
        result = await workflow.arun(
            text="계약서 내용...",
            doc_type="CONTRACT"
        )

        # 전문가 검토가 필요한 경우 (result에 awaiting_review=True)
        result = await workflow.resume(
            thread_id=result["session_id"],
            human_review={
                "approved": True,
                "comments": "검토 완료"
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
        workflow.add_node("identify_risks", identify_risks_node)
        workflow.add_node("assess_severity", assess_severity_node)
        workflow.add_node("human_review", human_review_node)
        workflow.add_node("generate_report", generate_report_node)

        # 엣지 정의
        workflow.add_edge(START, "identify_risks")
        workflow.add_edge("identify_risks", "assess_severity")
        workflow.add_conditional_edges(
            "assess_severity",
            route_human_review,
            {
                "human_review": "human_review",
                "generate_report": "generate_report",
            }
        )
        workflow.add_edge("human_review", "generate_report")
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
        **kwargs
    ) -> RiskAnalysisState:
        """
        초기 상태 생성

        Args:
            text: 분석할 텍스트
            doc_type: 문서 타입
            document_id: 문서 ID

        Returns:
            초기 RiskAnalysisState
        """
        return RiskAnalysisState(
            document_id=document_id,
            text=text,
            doc_type=doc_type,
            identified_risks=[],
            requires_human_review=False,
            human_review=None,
            report=None,
            completed_tasks=[],
            iteration_count=0,
            error=None,
        )

    async def resume(
        self,
        thread_id: str,
        human_review: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Human-in-the-Loop 재개

        전문가 검토 후 워크플로우 재개

        Args:
            thread_id: 세션 ID (스레드 ID)
            human_review: 검토 결과
                {
                    "approved": bool,
                    "comments": str,
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
            "requires_human_review": result.get("requires_human_review", False),
            "human_review": result.get("human_review"),
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
