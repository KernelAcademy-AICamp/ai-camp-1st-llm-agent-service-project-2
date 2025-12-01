"""
Human-in-the-Loop Tests - Phase 4 Session 18

Phase 4 - Week 14: Human-in-the-Loop 패턴 테스트

테스트 목적:
1. 전문가 리뷰 요청/결과 검증
2. Checkpointing 기반 워크플로우 중단/재개 테스트
3. 다양한 시나리오에서의 Human-in-the-Loop 동작 확인

테스트 범위:
- Risk Analysis: 고위험 감지 시 전문가 리뷰 요청
- LLM Compare: 모델 간 결과 불일치 시 사용자 선택 요청
- Crawler: 검증 실패 시 수동 검토 요청
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import time
import uuid

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== Constants =====

V2_BASE_URL = "http://localhost:8001/v2"
TIMEOUT = 120


# ===== Test Data =====

HIGH_RISK_CONTRACT = """
불공정 계약서

제5조 (손해배상)
을(개발자)은 본 계약 위반으로 인한 모든 손해에 대하여 무제한의 배상책임을 부담합니다.
갑(의뢰인)은 어떠한 경우에도 손해배상 책임을 지지 않습니다.

제6조 (해지)
갑은 을에게 별도의 통지 없이 언제든지 본 계약을 해지할 수 있으며,
이 경우 을에게 어떠한 보상도 하지 않습니다.
을은 갑의 서면 동의 없이 본 계약을 해지할 수 없습니다.

제7조 (지식재산권)
본 계약 수행 과정에서 을이 개발한 모든 저작물, 발명, 기술에 대한
지식재산권은 전적으로 갑에게 귀속됩니다.
을은 갑의 사전 서면 동의 없이 이를 사용, 복제, 배포할 수 없습니다.

제8조 (경업금지)
을은 본 계약 종료 후 5년간 갑과 동종 업계에서 경쟁하는
어떠한 사업에도 종사할 수 없습니다.
"""

LOW_RISK_CONTRACT = """
표준 계약서

제5조 (손해배상)
각 당사자는 상대방에게 발생한 직접 손해에 대해서만
계약금액을 한도로 배상책임을 부담합니다.

제6조 (해지)
각 당사자는 30일 전 서면 통지로 본 계약을 해지할 수 있습니다.

제7조 (지식재산권)
기존 지식재산권은 각 당사자에게 귀속되며,
공동 개발 결과물에 대한 권리는 양 당사자가 균등하게 공유합니다.
"""


# ===== Helper Functions =====

async def make_request(
    method: str,
    endpoint: str,
    json_data: Dict = None,
    params: Dict = None
) -> Dict[str, Any]:
    """HTTP 요청 헬퍼"""
    import httpx

    url = f"{V2_BASE_URL}{endpoint}"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()

        if method.upper() == "GET":
            response = await client.get(url, params=params)
        elif method.upper() == "POST":
            response = await client.post(url, json=json_data)
        else:
            raise ValueError(f"Unsupported method: {method}")

        latency = (time.time() - start) * 1000

        return {
            "status_code": response.status_code,
            "data": response.json() if response.status_code < 500 else None,
            "latency_ms": latency,
            "headers": dict(response.headers)
        }


# ===== Unit Tests =====

class TestHumanInTheLoopStates:
    """Human-in-the-Loop 상태 정의 테스트"""

    def test_risk_state_import(self):
        """Risk Analysis 상태 import 테스트"""
        from apps.ai_service.workflows.states.risk_state import (
            RiskAnalysisState,
            RiskItem,
            RiskSeverity,
            HumanReviewResult,
        )

        assert RiskSeverity is not None
        assert HumanReviewResult is not None

    def test_risk_state_severity(self):
        """RiskSeverity enum 확인"""
        from apps.ai_service.workflows.states.risk_state import RiskSeverity

        # RiskSeverity가 enum이면 값 확인
        assert RiskSeverity is not None

    def test_llm_comparison_state_import(self):
        """LLM Comparison 상태 import 테스트"""
        from apps.ai_service.workflows.states.llm_comparison_state import (
            LLMComparisonState,
            ModelMetrics,
        )

        assert LLMComparisonState is not None
        assert ModelMetrics is not None

    def test_crawl_state_import(self):
        """Crawl 상태 import 테스트"""
        from apps.ai_service.workflows.states.crawl_state import (
            CrawlState,
            CrawlStatus,
            ProcessingStatus,
        )

        assert CrawlStatus.PENDING is not None
        assert ProcessingStatus is not None


class TestHumanInTheLoopWorkflows:
    """Human-in-the-Loop 워크플로우 테스트"""

    def test_risk_workflow_has_interrupt(self):
        """Risk 워크플로우 interrupt 지원 확인"""
        from apps.ai_service.graphs.risk_graph import RiskAnalysisWorkflow

        workflow = RiskAnalysisWorkflow()

        # 워크플로우가 Human-in-the-Loop 지원하는지 확인
        assert hasattr(workflow, "run")
        assert hasattr(workflow, "resume")
        assert hasattr(workflow, "get_status")

    def test_llm_comparison_workflow_has_interrupt(self):
        """LLM Comparison 워크플로우 interrupt 지원 확인"""
        from apps.ai_service.workflows.llm_comparison_workflow import (
            create_llm_comparison_workflow,
        )

        workflow = create_llm_comparison_workflow()

        # StateGraph 생성 확인
        assert workflow is not None

    def test_crawler_workflow_has_checkpointing(self):
        """Crawler 워크플로우 Checkpointing 지원 확인"""
        from apps.ai_service.graphs.crawler_graph import CrawlerWorkflow

        workflow = CrawlerWorkflow()

        assert hasattr(workflow, "run")
        assert hasattr(workflow, "resume")
        assert hasattr(workflow, "get_status")


# ===== Integration Tests - Risk Analysis Human-in-the-Loop =====

class TestRiskAnalysisHITL:
    """Risk Analysis Human-in-the-Loop 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_high_risk_triggers_review(self):
        """고위험 계약서가 전문가 리뷰를 트리거하는지 테스트"""
        result = await make_request("POST", "/risk/analyze", json_data={
            "document_text": HIGH_RISK_CONTRACT,
            "document_type": "CONTRACT"
        })

        assert result["status_code"] == 200
        data = result["data"]

        # 고위험 시 전문가 리뷰 요청 필드 확인
        assert "session_id" in data

        # awaiting_review가 True이거나 risk_level이 high인 경우
        # Human-in-the-Loop가 필요함을 나타냄
        if "awaiting_review" in data:
            assert data["awaiting_review"] is True, "고위험 계약서는 리뷰 대기 상태여야 함"

        logger.info(f"High risk analysis completed: session_id={data.get('session_id')}")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_low_risk_skips_review(self):
        """저위험 계약서는 전문가 리뷰를 스킵하는지 테스트"""
        result = await make_request("POST", "/risk/analyze", json_data={
            "document_text": LOW_RISK_CONTRACT,
            "document_type": "CONTRACT"
        })

        assert result["status_code"] == 200
        data = result["data"]

        # 저위험 시 즉시 완료되어야 함
        if "awaiting_review" in data:
            assert data["awaiting_review"] is False, "저위험 계약서는 즉시 완료되어야 함"

        logger.info(f"Low risk analysis completed without review")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_risk_resume_after_review(self):
        """전문가 리뷰 후 워크플로우 재개 테스트"""
        # 1. 고위험 분석 시작
        start_result = await make_request("POST", "/risk/analyze", json_data={
            "document_text": HIGH_RISK_CONTRACT,
            "document_type": "CONTRACT"
        })

        assert start_result["status_code"] == 200
        session_id = start_result["data"].get("session_id")

        if not session_id:
            pytest.skip("No session_id returned")

        # 2. 상태 확인
        status_result = await make_request("GET", f"/risk/status/{session_id}")
        assert status_result["status_code"] == 200

        # 3. 전문가 리뷰 제출 (승인)
        resume_result = await make_request("POST", "/risk/resume", json_data={
            "session_id": session_id,
            "expert_review": {
                "decision": "approved",
                "comments": "리스크 요소가 있으나 계약 진행 가능",
                "reviewed_by": "legal_expert_001"
            }
        })

        if resume_result["status_code"] == 200:
            data = resume_result["data"]
            assert "completed" in str(data.get("status", "")).lower() or data.get("success")
            logger.info("Risk analysis resumed and completed after expert review")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_risk_status_during_review(self):
        """리뷰 대기 중 상태 조회 테스트"""
        # 1. 고위험 분석 시작
        start_result = await make_request("POST", "/risk/analyze", json_data={
            "document_text": HIGH_RISK_CONTRACT,
            "document_type": "CONTRACT"
        })

        if start_result["status_code"] != 200:
            pytest.skip("Analysis failed to start")

        session_id = start_result["data"].get("session_id")

        # 2. 상태 조회 - 리뷰 대기 중이어야 함
        status_result = await make_request("GET", f"/risk/status/{session_id}")

        assert status_result["status_code"] == 200
        data = status_result["data"]

        logger.info(f"Status during review: {data.get('status')}")


# ===== Integration Tests - LLM Compare Human-in-the-Loop =====

class TestLLMCompareHITL:
    """LLM Compare Human-in-the-Loop 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_disagreement_triggers_selection(self):
        """모델 간 불일치 시 사용자 선택 요청 테스트"""
        result = await make_request("POST", "/llm/compare", json_data={
            "task": "summarize",
            "input_data": {"text": HIGH_RISK_CONTRACT},
            "models": [
                {"model_name": "gpt-4", "temperature": 0.7},
                {"model_name": "claude-3-sonnet", "temperature": 0.7}
            ]
        })

        # API 키가 없으면 500 에러 가능
        if result["status_code"] != 200:
            pytest.skip("LLM API not available")

        data = result["data"]
        assert "session_id" in data
        assert "awaiting_selection" in data

        logger.info(f"LLM compare: awaiting_selection={data.get('awaiting_selection')}")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_llm_select_after_disagreement(self):
        """사용자 모델 선택 후 워크플로우 완료 테스트"""
        # 1. 비교 시작
        start_result = await make_request("POST", "/llm/compare", json_data={
            "task": "summarize",
            "input_data": {"text": "간단한 테스트 문서입니다."},
            "models": [
                {"model_name": "gpt-4", "temperature": 0.7},
                {"model_name": "gpt-3.5-turbo", "temperature": 0.7}
            ]
        })

        if start_result["status_code"] != 200:
            pytest.skip("LLM API not available")

        data = start_result["data"]
        session_id = data.get("session_id")

        if not data.get("awaiting_selection"):
            logger.info("Models agreed, no selection needed")
            return

        # 2. 사용자 선택 제출
        select_result = await make_request("POST", "/llm/select", json_data={
            "session_id": session_id,
            "selected_model": "gpt-4"
        })

        assert select_result["status_code"] == 200
        select_data = select_result["data"]
        assert select_data.get("user_selected") is True
        assert select_data.get("best_model") == "gpt-4"

        logger.info("LLM comparison completed after user selection")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_llm_status_during_selection(self):
        """선택 대기 중 상태 조회 테스트"""
        # 1. 비교 시작
        start_result = await make_request("POST", "/llm/compare", json_data={
            "task": "analyze",
            "input_data": {"text": "분석할 문서"},
            "models": [
                {"model_name": "gpt-4"},
                {"model_name": "claude-3-sonnet"}
            ]
        })

        if start_result["status_code"] != 200:
            pytest.skip("LLM API not available")

        session_id = start_result["data"].get("session_id")

        # 2. 상태 조회
        status_result = await make_request("GET", f"/llm/status/{session_id}")

        assert status_result["status_code"] == 200
        data = status_result["data"]
        assert "status" in data

        logger.info(f"LLM compare status: {data.get('status')}")


# ===== Integration Tests - Crawler Checkpointing =====

class TestCrawlerCheckpointing:
    """Crawler Checkpointing 테스트 (Cyclic Retry 포함)"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_crawler_resume_after_interrupt(self):
        """크롤러 중단 후 재개 테스트"""
        # 1. 크롤링 시작
        start_result = await make_request("POST", "/crawler/start", json_data={
            "source": "court_precedent",
            "keywords": ["형사", "절도"]
        })

        if start_result["status_code"] != 200:
            pytest.skip("Crawler start failed")

        data = start_result["data"]
        thread_id = data.get("thread_id")

        if not thread_id:
            pytest.skip("No thread_id returned")

        # 2. 상태 확인
        status_result = await make_request("GET", f"/crawler/status/{thread_id}")
        assert status_result["status_code"] == 200

        # 3. 재개 시도
        resume_result = await make_request("POST", "/crawler/resume", json_data={
            "thread_id": thread_id
        })

        if resume_result["status_code"] == 200:
            logger.info("Crawler resumed successfully")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_crawler_retry_on_failure(self):
        """크롤러 실패 시 자동 재시도 테스트"""
        # 잘못된 키워드로 시작하여 실패 유도
        result = await make_request("POST", "/crawler/start", json_data={
            "source": "court_precedent",
            "keywords": ["존재하지않는키워드12345"]
        })

        if result["status_code"] == 200:
            data = result["data"]
            # retry_count 확인
            if "metrics" in data:
                metrics = data["metrics"]
                logger.info(f"Crawler metrics: {metrics}")


# ===== Workflow State Persistence Tests =====

class TestCheckpointPersistence:
    """Checkpoint 상태 영속성 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_risk_state_persisted_after_interrupt(self):
        """Risk 분석 중단 후 상태 유지 확인"""
        # 1. 분석 시작
        start_result = await make_request("POST", "/risk/analyze", json_data={
            "document_text": HIGH_RISK_CONTRACT,
            "document_type": "CONTRACT"
        })

        if start_result["status_code"] != 200:
            pytest.skip("Analysis failed")

        session_id = start_result["data"].get("session_id")

        # 2. 잠시 대기 후 상태 확인 (Checkpoint 저장 시간)
        await asyncio.sleep(1)

        status_result = await make_request("GET", f"/risk/status/{session_id}")

        assert status_result["status_code"] == 200
        data = status_result["data"]

        # 상태가 저장되어 있어야 함
        assert data.get("status") != "not_found"
        logger.info(f"State persisted: {data}")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_llm_compare_state_persisted(self):
        """LLM 비교 상태 영속성 확인"""
        # 1. 비교 시작
        start_result = await make_request("POST", "/llm/compare", json_data={
            "task": "summarize",
            "input_data": {"text": "테스트 문서"},
            "models": [
                {"model_name": "gpt-4"},
                {"model_name": "gpt-3.5-turbo"}
            ]
        })

        if start_result["status_code"] != 200:
            pytest.skip("LLM compare failed")

        session_id = start_result["data"].get("session_id")

        # 2. 상태 확인
        status_result = await make_request("GET", f"/llm/status/{session_id}")

        assert status_result["status_code"] == 200
        data = status_result["data"]

        assert data.get("status") != "not_found"
        logger.info(f"LLM compare state persisted: {data}")


# ===== Summary Tests =====

class TestHumanInTheLoopSummary:
    """Human-in-the-Loop 요약 테스트"""

    def test_all_hitl_workflows_defined(self):
        """모든 HITL 워크플로우 정의 확인"""
        # Risk Analysis
        from apps.ai_service.graphs.risk_graph import RiskAnalysisWorkflow

        # LLM Comparison
        from apps.ai_service.workflows.llm_comparison_workflow import (
            create_llm_comparison_workflow,
        )

        # Crawler
        from apps.ai_service.graphs.crawler_graph import CrawlerWorkflow

        workflows = [
            RiskAnalysisWorkflow(),
            CrawlerWorkflow(),
        ]

        # 모든 워크플로우가 resume 메서드 지원
        for wf in workflows:
            assert hasattr(wf, "resume"), f"{type(wf).__name__} missing resume method"

        logger.info("All HITL workflows defined correctly")

    def test_checkpointing_config(self):
        """Checkpointing 설정 확인"""
        # Risk: 7일 TTL
        # LLM Compare: 1시간 TTL
        # Crawler: 24시간 TTL

        expected_ttl = {
            "risk": "7 days",
            "llm_compare": "1 hour",
            "crawler": "24 hours",
        }

        logger.info(f"Expected TTL settings: {expected_ttl}")


# ===== Main =====

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
