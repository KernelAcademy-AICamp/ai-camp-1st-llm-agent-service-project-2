"""
V2 API E2E Tests - Phase 4 Session 18

Phase 4 - Week 14: v2 API 엔드투엔드 테스트

테스트 목적:
1. 모든 v2 API 엔드포인트 기능 검증
2. 워크플로우 전체 흐름 테스트
3. 에러 핸들링 검증

테스트 범위:
- RAG Chat API (/v2/rag/*)
- Document Analysis API (/v2/documents/*)
- Case Analysis API (/v2/cases/*)
- Risk Analysis API (/v2/risk/*)
- LLM Compare API (/v2/llm/*)
- Crawler API (/v2/crawler/*)
- Analytics API (/v2/analytics/*)
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
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

SAMPLE_CONTRACT = """
소프트웨어 개발 용역 계약서

제1조 (목적)
본 계약은 갑(의뢰인)과 을(수급인) 간에 소프트웨어 개발 용역에 관하여 체결합니다.

제2조 (계약 기간)
2024년 1월 1일부터 2024년 12월 31일까지 (12개월)

제3조 (계약 금액)
총 1억원 (부가세 별도)
- 계약금 (30%): 계약 체결 시
- 중도금 (40%): 중간 검수 완료 시
- 잔금 (30%): 최종 검수 완료 시

제4조 (손해배상)
각 당사자는 본 계약 위반으로 인해 상대방에게 발생한 손해를 배상하여야 합니다.

제5조 (비밀유지)
양 당사자는 본 계약 이행 과정에서 취득한 상대방의 비밀정보를 제3자에게 누설하지 아니합니다.
"""

SAMPLE_CASE = """
대법원 2023. 5. 15. 선고 2022도12345 판결

【사건】
사기

【피고인】
홍길동

【판시사항】
허위의 투자 수익을 약속하고 금원을 편취한 사안에서 사기죄의 성립 여부

【판결요지】
피고인이 실제로는 투자금을 다른 용도에 사용할 의사였음에도 불구하고
피해자에게 높은 수익률을 보장한다고 기망하여 투자금을 교부받은 경우,
기망행위와 피해자의 착오 및 처분행위 사이에 인과관계가 인정되어 사기죄가 성립한다.

【주문】
상고 기각
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


# ===== Unit Tests (No Server Required) =====

class TestV2RouterImports:
    """V2 라우터 import 테스트"""

    def test_all_routers_importable(self):
        """모든 v2 라우터 import 가능 확인"""
        from apps.ai_service.routers.v2 import (
            rag_router,
            documents_router,
            cases_router,
            risk_router,
            llm_compare_router,
            crawler_router,
            analytics_router,
        )

        routers = [
            rag_router,
            documents_router,
            cases_router,
            risk_router,
            llm_compare_router,
            crawler_router,
            analytics_router,
        ]

        for router in routers:
            assert router is not None
            assert hasattr(router, "routes")

    def test_router_prefixes(self):
        """라우터 프리픽스 확인"""
        from apps.ai_service.routers.v2 import (
            rag_router,
            documents_router,
            cases_router,
            risk_router,
            llm_compare_router,
            crawler_router,
            analytics_router,
        )

        expected_prefixes = {
            "rag_router": "/v2/rag",
            "documents_router": "/v2/documents",
            "cases_router": "/v2/cases",
            "risk_router": "/v2/risk",
            "llm_compare_router": "/v2/llm",
            "crawler_router": "/v2/crawler",
            "analytics_router": "/v2/analytics",
        }

        routers = {
            "rag_router": rag_router,
            "documents_router": documents_router,
            "cases_router": cases_router,
            "risk_router": risk_router,
            "llm_compare_router": llm_compare_router,
            "crawler_router": crawler_router,
            "analytics_router": analytics_router,
        }

        for name, router in routers.items():
            assert router.prefix == expected_prefixes[name], f"{name} prefix mismatch"


# ===== E2E Tests - Health Checks =====

class TestV2HealthEndpoints:
    """V2 헬스체크 E2E 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_rag_health(self):
        """RAG v2 헬스체크"""
        result = await make_request("GET", "/rag/health")

        assert result["status_code"] == 200
        data = result["data"]
        assert data["status"] == "healthy"
        assert data["version"] == "v2"
        assert data["engine"] == "LangGraph"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_documents_health(self):
        """Documents v2 헬스체크"""
        result = await make_request("GET", "/documents/health")

        assert result["status_code"] == 200
        data = result["data"]
        assert data["status"] == "healthy"
        assert data["version"] == "v2"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_cases_health(self):
        """Cases v2 헬스체크"""
        result = await make_request("GET", "/cases/health")

        assert result["status_code"] == 200
        data = result["data"]
        assert data["status"] == "healthy"
        assert data["version"] == "v2"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_risk_health(self):
        """Risk v2 헬스체크"""
        result = await make_request("GET", "/risk/health")

        assert result["status_code"] == 200
        data = result["data"]
        assert data["status"] == "healthy"
        assert data["checkpointing"] is True

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_llm_compare_health(self):
        """LLM Compare v2 헬스체크"""
        result = await make_request("GET", "/llm/health")

        assert result["status_code"] == 200
        data = result["data"]
        assert data["status"] == "healthy"
        assert data["checkpointing"] is True
        assert "human_in_the_loop" in data["features"]

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_crawler_health(self):
        """Crawler v2 헬스체크"""
        result = await make_request("GET", "/crawler/health")

        assert result["status_code"] == 200
        data = result["data"]
        assert data["status"] == "healthy"
        assert data["checkpointing"] is True
        assert "cyclic_retry" in data["features"]

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analytics_health(self):
        """Analytics v2 헬스체크"""
        result = await make_request("GET", "/analytics/health")

        assert result["status_code"] == 200
        data = result["data"]
        assert data["status"] == "healthy"
        assert data["checkpointing"] is False  # Analytics는 Checkpointing 불필요

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_all_health_endpoints_parallel(self):
        """모든 헬스체크 병렬 실행"""
        endpoints = [
            "/rag/health",
            "/documents/health",
            "/cases/health",
            "/risk/health",
            "/llm/health",
            "/crawler/health",
            "/analytics/health",
        ]

        results = await asyncio.gather(
            *[make_request("GET", ep) for ep in endpoints]
        )

        all_healthy = all(r["status_code"] == 200 and r["data"]["status"] == "healthy" for r in results)
        assert all_healthy, "Not all health endpoints returned healthy status"

        logger.info(f"All {len(endpoints)} health endpoints healthy")


# ===== E2E Tests - RAG API =====

class TestRAGE2E:
    """RAG v2 E2E 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_rag_chat_basic(self):
        """기본 RAG 채팅 테스트"""
        result = await make_request("POST", "/rag/chat", json_data={
            "query": "사기죄의 구성요건은 무엇인가요?",
            "top_k": 5
        })

        assert result["status_code"] == 200
        data = result["data"]
        assert "answer" in data
        assert "sources" in data
        assert len(data["answer"]) > 0

        logger.info(f"RAG Chat latency: {result['latency_ms']:.0f}ms")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_rag_compare_v1_v2(self):
        """RAG v1 vs v2 비교 엔드포인트 테스트"""
        result = await make_request("POST", "/rag/compare", json_data={
            "query": "계약 해제 요건은?",
            "top_k": 3
        })

        assert result["status_code"] == 200
        data = result["data"]
        assert "v1_result" in data or "v2_result" in data


# ===== E2E Tests - Document Analysis API =====

class TestDocumentAnalysisE2E:
    """Document Analysis v2 E2E 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analyze_text_basic(self):
        """텍스트 분석 기본 테스트"""
        result = await make_request("POST", "/documents/analyze/text", json_data={
            "text": SAMPLE_CONTRACT,
            "document_type": "CONTRACT"
        })

        assert result["status_code"] == 200
        data = result["data"]
        assert "summary" in data
        assert len(data["summary"]) > 0

        logger.info(f"Document Analysis latency: {result['latency_ms']:.0f}ms")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analyze_text_case_law(self):
        """판례 분석 테스트"""
        result = await make_request("POST", "/documents/analyze/text", json_data={
            "text": SAMPLE_CASE,
            "document_type": "CASE_LAW"
        })

        assert result["status_code"] == 200
        data = result["data"]
        assert "summary" in data


# ===== E2E Tests - Case Analysis API =====

class TestCaseAnalysisE2E:
    """Case Analysis v2 E2E 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_case_analysis_basic(self):
        """기본 사건 분석 테스트"""
        result = await make_request("POST", "/cases/analyze", json_data={
            "case_text": SAMPLE_CASE,
            "analyze_type": "comprehensive"
        })

        assert result["status_code"] == 200
        data = result["data"]
        assert "analysis" in data or "result" in data

        logger.info(f"Case Analysis latency: {result['latency_ms']:.0f}ms")


# ===== E2E Tests - Risk Analysis API =====

class TestRiskAnalysisE2E:
    """Risk Analysis v2 E2E 테스트 (Checkpointing 포함)"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_risk_analysis_basic(self):
        """기본 리스크 분석 테스트"""
        result = await make_request("POST", "/risk/analyze", json_data={
            "document_text": SAMPLE_CONTRACT,
            "document_type": "CONTRACT"
        })

        assert result["status_code"] == 200
        data = result["data"]
        assert "session_id" in data or "risk_score" in data

        logger.info(f"Risk Analysis latency: {result['latency_ms']:.0f}ms")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_risk_analysis_status(self):
        """리스크 분석 상태 조회 테스트"""
        # 먼저 분석 시작
        start_result = await make_request("POST", "/risk/analyze", json_data={
            "document_text": SAMPLE_CONTRACT,
            "document_type": "CONTRACT"
        })

        if start_result["status_code"] == 200:
            session_id = start_result["data"].get("session_id")
            if session_id:
                # 상태 조회
                status_result = await make_request("GET", f"/risk/status/{session_id}")
                assert status_result["status_code"] == 200


# ===== E2E Tests - LLM Compare API =====

class TestLLMCompareE2E:
    """LLM Compare v2 E2E 테스트 (Human-in-the-Loop)"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_llm_compare_basic(self):
        """기본 LLM 비교 테스트"""
        result = await make_request("POST", "/llm/compare", json_data={
            "task": "summarize",
            "input_data": {"text": SAMPLE_CONTRACT[:500]},
            "models": [
                {"model_name": "gpt-4", "temperature": 0.7},
                {"model_name": "claude-3-sonnet", "temperature": 0.7}
            ]
        })

        assert result["status_code"] in [200, 500]  # 500은 API 키 없는 경우

        if result["status_code"] == 200:
            data = result["data"]
            assert "session_id" in data
            assert "awaiting_selection" in data

        logger.info(f"LLM Compare latency: {result['latency_ms']:.0f}ms")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_llm_models_list(self):
        """지원 모델 목록 조회 테스트"""
        result = await make_request("GET", "/llm/models")

        assert result["status_code"] == 200
        data = result["data"]
        assert "models" in data
        assert "default_models" in data


# ===== E2E Tests - Crawler API =====

class TestCrawlerE2E:
    """Crawler v2 E2E 테스트 (Checkpointing + Cyclic Retry)"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_crawler_start(self):
        """크롤러 시작 테스트"""
        result = await make_request("POST", "/crawler/start", json_data={
            "source": "court_precedent",
            "keywords": ["형사", "사기"]
        })

        assert result["status_code"] in [200, 500]

        if result["status_code"] == 200:
            data = result["data"]
            assert "thread_id" in data
            assert "status" in data

        logger.info(f"Crawler start latency: {result['latency_ms']:.0f}ms")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_crawler_status(self):
        """크롤러 상태 조회 테스트"""
        # 임의의 job_id로 상태 조회 (not_found 예상)
        result = await make_request("GET", "/crawler/status/test-job-123")

        assert result["status_code"] == 200
        data = result["data"]
        assert "status" in data


# ===== E2E Tests - Analytics API =====

class TestAnalyticsE2E:
    """Analytics v2 E2E 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analytics_generate(self):
        """분석 리포트 생성 테스트"""
        result = await make_request("POST", "/analytics/generate", json_data={
            "time_range": "1d",
            "user_id": None,
            "organization_id": None
        })

        assert result["status_code"] == 200
        data = result["data"]
        assert "summary" in data
        assert "timestamp" in data

        logger.info(f"Analytics generate latency: {result['latency_ms']:.0f}ms")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analytics_overview(self):
        """대시보드 개요 조회 테스트"""
        result = await make_request("GET", "/analytics/overview", params={
            "time_range": "1d"
        })

        assert result["status_code"] == 200
        data = result["data"]
        assert "total_documents" in data
        assert "active_users" in data

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analytics_trends(self):
        """트렌드 데이터 조회 테스트"""
        result = await make_request("GET", "/analytics/trends", params={
            "time_range": "7d"
        })

        assert result["status_code"] == 200
        data = result["data"]
        assert "trends" in data
        assert "time_range" in data

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analytics_anomaly_types(self):
        """이상 유형 목록 조회 테스트"""
        result = await make_request("GET", "/analytics/anomaly-types")

        assert result["status_code"] == 200
        data = result["data"]
        assert "anomaly_types" in data
        assert "severity_levels" in data

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analytics_insight_categories(self):
        """인사이트 카테고리 목록 조회 테스트"""
        result = await make_request("GET", "/analytics/insight-categories")

        assert result["status_code"] == 200
        data = result["data"]
        assert "categories" in data


# ===== Full E2E Flow Tests =====

class TestFullE2EFlows:
    """전체 E2E 흐름 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_document_processing_flow(self):
        """문서 처리 전체 흐름 테스트"""
        # 1. 문서 분석
        doc_result = await make_request("POST", "/documents/analyze/text", json_data={
            "text": SAMPLE_CONTRACT,
            "document_type": "CONTRACT"
        })
        assert doc_result["status_code"] == 200

        # 2. 리스크 분석
        risk_result = await make_request("POST", "/risk/analyze", json_data={
            "document_text": SAMPLE_CONTRACT,
            "document_type": "CONTRACT"
        })
        assert risk_result["status_code"] == 200

        # 3. RAG 질의
        rag_result = await make_request("POST", "/rag/chat", json_data={
            "query": "이 계약서의 주요 위험 요소는?",
            "top_k": 3
        })
        assert rag_result["status_code"] == 200

        logger.info("Document processing flow completed successfully")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_analytics_dashboard_flow(self):
        """Analytics 대시보드 흐름 테스트"""
        # 1. 개요 조회
        overview = await make_request("GET", "/analytics/overview", params={"time_range": "1d"})
        assert overview["status_code"] == 200

        # 2. 트렌드 조회
        trends = await make_request("GET", "/analytics/trends", params={"time_range": "7d"})
        assert trends["status_code"] == 200

        # 3. 전체 리포트 생성
        report = await make_request("POST", "/analytics/generate", json_data={"time_range": "1d"})
        assert report["status_code"] == 200

        logger.info("Analytics dashboard flow completed successfully")


# ===== Main =====

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
