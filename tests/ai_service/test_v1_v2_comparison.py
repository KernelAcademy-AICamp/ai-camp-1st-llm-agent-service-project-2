"""
V1 vs V2 API Comparison Tests - Phase 4 Session 18

Phase 4 - Week 14: v1과 v2 API 기능적 동일성 검증

테스트 목적:
1. 기능적 동일성 검증 (같은 입력 → 동일한 유형의 출력)
2. 응답 형식 호환성 확인
3. 성능 비교 (latency, token usage)

테스트 범위:
- RAG Chat: v1 /v1/rag/query vs v2 /v2/rag/chat
- Document Analysis: v1 /v1/llm/summarize vs v2 /v2/documents/analyze/text
- Risk Analysis: v1 /v1/llm/analyze_risk vs v2 /v2/risk/analyze
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import logging
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== Constants =====

V1_BASE_URL = "http://localhost:8001/v1"
V2_BASE_URL = "http://localhost:8001/v2"

TIMEOUT = 120  # seconds


# ===== Test Data Fixtures =====

@pytest.fixture
def rag_test_cases():
    """RAG 질의응답 테스트 케이스"""
    return [
        {
            "name": "형사법 사기죄 질의",
            "query": "사기죄의 구성요건은 무엇인가요?",
            "top_k": 5,
            "expected_keywords": ["기망", "착오", "재산", "처분"],
        },
        {
            "name": "민법 계약 해제 질의",
            "query": "계약 해제의 요건은 무엇인가요?",
            "top_k": 3,
            "expected_keywords": ["해제", "계약", "이행"],
        },
    ]


@pytest.fixture
def document_analysis_test_cases():
    """문서 분석 테스트 케이스"""
    return [
        {
            "name": "계약서 요약",
            "text": """
            본 계약은 갑(주식회사 ABC)과 을(주식회사 XYZ) 간에
            소프트웨어 개발 용역에 관하여 체결하는 계약입니다.

            제1조 (목적)
            본 계약은 을이 갑에게 소프트웨어 개발 용역을 제공함에 있어
            필요한 사항을 정함을 목적으로 합니다.

            제2조 (계약 기간)
            본 계약의 유효기간은 2024년 1월 1일부터 2024년 12월 31일까지로 합니다.

            제3조 (계약 금액)
            용역 대가는 1억원(부가세 별도)으로 하며,
            계약 체결 시 30%, 중간 검수 시 40%, 최종 검수 시 30%를 지급합니다.
            """,
            "document_type": "CONTRACT",
            "expected_in_summary": ["소프트웨어", "개발", "용역", "계약"],
        },
        {
            "name": "판결문 요약",
            "text": """
            대법원 2023. 5. 15. 선고 2022도12345 판결

            【판시사항】
            피고인이 피해자를 기망하여 금원을 편취한 경우 사기죄의 성립 여부

            【판결요지】
            사기죄가 성립하기 위해서는 기망행위, 피해자의 착오,
            재산상 처분행위 및 재산상 손해가 있어야 하며,
            이들 사이에 순차적 인과관계가 있어야 한다.
            """,
            "document_type": "CASE_LAW",
            "expected_in_summary": ["사기죄", "기망", "판결"],
        },
    ]


@pytest.fixture
def risk_analysis_test_cases():
    """리스크 분석 테스트 케이스"""
    return [
        {
            "name": "고위험 계약서",
            "text": """
            제5조 (손해배상)
            을은 본 계약 위반으로 인한 모든 손해에 대하여 무제한의 배상책임을 부담합니다.
            갑은 어떠한 경우에도 손해배상 책임을 지지 않습니다.

            제6조 (해지)
            갑은 을에게 통지 없이 언제든지 본 계약을 해지할 수 있으며,
            이 경우 을에게 어떠한 보상도 하지 않습니다.
            """,
            "document_type": "CONTRACT",
            "expected_risk_level": "high",
        },
        {
            "name": "저위험 계약서",
            "text": """
            제5조 (손해배상)
            각 당사자는 상대방에게 발생한 직접 손해에 대해서만
            계약금액을 한도로 배상책임을 부담합니다.

            제6조 (해지)
            각 당사자는 30일 전 서면 통지로 본 계약을 해지할 수 있습니다.
            """,
            "document_type": "CONTRACT",
            "expected_risk_level": "low",
        },
    ]


# ===== Helper Functions =====

async def call_v1_rag(query: str, top_k: int = 5) -> Dict[str, Any]:
    """V1 RAG API 호출"""
    import httpx

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.post(
            f"{V1_BASE_URL}/rag/query",
            json={"query": query, "top_k": top_k}
        )
        latency = (time.time() - start) * 1000  # ms

        return {
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
            "latency_ms": latency,
            "version": "v1"
        }


async def call_v2_rag(query: str, top_k: int = 5) -> Dict[str, Any]:
    """V2 RAG API 호출"""
    import httpx

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.post(
            f"{V2_BASE_URL}/rag/chat",
            json={"query": query, "top_k": top_k}
        )
        latency = (time.time() - start) * 1000  # ms

        return {
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
            "latency_ms": latency,
            "version": "v2"
        }


async def call_v1_document_analysis(text: str, doc_type: str = "CONTRACT") -> Dict[str, Any]:
    """V1 문서 분석 API 호출"""
    import httpx

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.post(
            f"{V1_BASE_URL}/llm/summarize",
            json={
                "document_id": f"test_{int(time.time())}",
                "text": text,
                "summary_type": "GLOBAL",
                "document_type": doc_type
            }
        )
        latency = (time.time() - start) * 1000  # ms

        return {
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
            "latency_ms": latency,
            "version": "v1"
        }


async def call_v2_document_analysis(text: str, doc_type: str = "CONTRACT") -> Dict[str, Any]:
    """V2 문서 분석 API 호출"""
    import httpx

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.post(
            f"{V2_BASE_URL}/documents/analyze/text",
            json={
                "text": text,
                "document_type": doc_type
            }
        )
        latency = (time.time() - start) * 1000  # ms

        return {
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
            "latency_ms": latency,
            "version": "v2"
        }


async def call_v1_risk_analysis(text: str, doc_type: str = "CONTRACT") -> Dict[str, Any]:
    """V1 리스크 분석 API 호출"""
    import httpx

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.post(
            f"{V1_BASE_URL}/llm/analyze_risk",
            json={
                "document_id": f"test_{int(time.time())}",
                "text": text,
                "document_type": doc_type
            }
        )
        latency = (time.time() - start) * 1000  # ms

        return {
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
            "latency_ms": latency,
            "version": "v1"
        }


async def call_v2_risk_analysis(text: str, doc_type: str = "CONTRACT") -> Dict[str, Any]:
    """V2 리스크 분석 API 호출"""
    import httpx

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        start = time.time()
        response = await client.post(
            f"{V2_BASE_URL}/risk/analyze",
            json={
                "document_text": text,
                "document_type": doc_type
            }
        )
        latency = (time.time() - start) * 1000  # ms

        return {
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
            "latency_ms": latency,
            "version": "v2"
        }


def compare_responses(v1_result: Dict, v2_result: Dict, comparison_type: str) -> Dict[str, Any]:
    """V1과 V2 응답 비교"""
    comparison = {
        "type": comparison_type,
        "v1_status": v1_result["status_code"],
        "v2_status": v2_result["status_code"],
        "v1_latency_ms": v1_result["latency_ms"],
        "v2_latency_ms": v2_result["latency_ms"],
        "latency_diff_ms": v2_result["latency_ms"] - v1_result["latency_ms"],
        "latency_improvement_percent": (
            (v1_result["latency_ms"] - v2_result["latency_ms"]) / v1_result["latency_ms"] * 100
            if v1_result["latency_ms"] > 0 else 0
        ),
        "both_success": v1_result["status_code"] == 200 and v2_result["status_code"] == 200,
    }

    # 응답 구조 비교
    if comparison["both_success"]:
        v1_data = v1_result["data"]
        v2_data = v2_result["data"]

        if comparison_type == "rag":
            comparison["v1_has_answer"] = "answer" in v1_data
            comparison["v2_has_answer"] = "answer" in v2_data
            comparison["v1_answer_length"] = len(v1_data.get("answer", ""))
            comparison["v2_answer_length"] = len(v2_data.get("answer", ""))
            comparison["structure_compatible"] = (
                comparison["v1_has_answer"] and comparison["v2_has_answer"]
            )

        elif comparison_type == "document_analysis":
            comparison["v1_has_summary"] = "summary" in v1_data
            comparison["v2_has_summary"] = "summary" in v2_data
            comparison["v1_summary_length"] = len(v1_data.get("summary", ""))
            comparison["v2_summary_length"] = len(v2_data.get("summary", ""))
            comparison["structure_compatible"] = (
                comparison["v1_has_summary"] and comparison["v2_has_summary"]
            )

        elif comparison_type == "risk_analysis":
            comparison["v1_has_risk_score"] = "overall_risk_score" in v1_data or "risk_score" in v1_data
            comparison["v2_has_risk_score"] = "overall_risk_score" in v2_data or "risk_score" in v2_data
            comparison["v1_risk_items_count"] = len(v1_data.get("risk_items", []))
            comparison["v2_risk_items_count"] = len(v2_data.get("risk_items", []))
            comparison["structure_compatible"] = (
                comparison["v1_has_risk_score"] and comparison["v2_has_risk_score"]
            )

    return comparison


# ===== Unit Tests (No Server Required) =====

class TestComparisonHelpers:
    """비교 헬퍼 함수 테스트"""

    def test_compare_responses_structure(self):
        """compare_responses 함수 구조 테스트"""
        v1_result = {
            "status_code": 200,
            "data": {"answer": "test answer", "sources": []},
            "latency_ms": 1000,
            "version": "v1"
        }
        v2_result = {
            "status_code": 200,
            "data": {"answer": "test answer v2", "sources": []},
            "latency_ms": 800,
            "version": "v2"
        }

        comparison = compare_responses(v1_result, v2_result, "rag")

        assert comparison["type"] == "rag"
        assert comparison["both_success"] is True
        assert comparison["v1_latency_ms"] == 1000
        assert comparison["v2_latency_ms"] == 800
        assert comparison["latency_diff_ms"] == -200
        assert comparison["latency_improvement_percent"] == 20.0

    def test_compare_responses_failure(self):
        """실패 케이스 비교 테스트"""
        v1_result = {
            "status_code": 200,
            "data": {"answer": "success"},
            "latency_ms": 1000,
            "version": "v1"
        }
        v2_result = {
            "status_code": 500,
            "data": None,
            "latency_ms": 100,
            "version": "v2"
        }

        comparison = compare_responses(v1_result, v2_result, "rag")

        assert comparison["both_success"] is False
        assert comparison["v1_status"] == 200
        assert comparison["v2_status"] == 500


# ===== Integration Tests (Server Required) =====

class TestRAGComparison:
    """RAG API v1 vs v2 비교 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_rag_basic_query(self, rag_test_cases):
        """기본 RAG 질의 비교"""
        test_case = rag_test_cases[0]

        # 병렬로 v1, v2 호출
        v1_result, v2_result = await asyncio.gather(
            call_v1_rag(test_case["query"], test_case["top_k"]),
            call_v2_rag(test_case["query"], test_case["top_k"])
        )

        comparison = compare_responses(v1_result, v2_result, "rag")

        # 검증
        assert comparison["both_success"], f"API 호출 실패: v1={v1_result['status_code']}, v2={v2_result['status_code']}"
        assert comparison["structure_compatible"], "응답 구조 불일치"

        # 응답에 기대 키워드 포함 확인
        v1_answer = v1_result["data"].get("answer", "")
        v2_answer = v2_result["data"].get("answer", "")

        for keyword in test_case["expected_keywords"]:
            assert keyword in v1_answer or keyword in v2_answer, f"키워드 '{keyword}' 누락"

        logger.info(f"[RAG] v1: {v1_result['latency_ms']:.0f}ms, v2: {v2_result['latency_ms']:.0f}ms")
        logger.info(f"[RAG] 개선율: {comparison['latency_improvement_percent']:.1f}%")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_rag_all_cases(self, rag_test_cases):
        """모든 RAG 테스트 케이스 비교"""
        results = []

        for test_case in rag_test_cases:
            v1_result, v2_result = await asyncio.gather(
                call_v1_rag(test_case["query"], test_case["top_k"]),
                call_v2_rag(test_case["query"], test_case["top_k"])
            )

            comparison = compare_responses(v1_result, v2_result, "rag")
            comparison["test_name"] = test_case["name"]
            results.append(comparison)

        # 전체 결과 분석
        success_count = sum(1 for r in results if r["both_success"])
        avg_improvement = sum(r["latency_improvement_percent"] for r in results) / len(results)

        logger.info(f"[RAG 전체] 성공: {success_count}/{len(results)}, 평균 개선율: {avg_improvement:.1f}%")

        assert success_count == len(results), f"일부 테스트 실패"


class TestDocumentAnalysisComparison:
    """문서 분석 API v1 vs v2 비교 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_document_analysis_basic(self, document_analysis_test_cases):
        """기본 문서 분석 비교"""
        test_case = document_analysis_test_cases[0]

        v1_result, v2_result = await asyncio.gather(
            call_v1_document_analysis(test_case["text"], test_case["document_type"]),
            call_v2_document_analysis(test_case["text"], test_case["document_type"])
        )

        comparison = compare_responses(v1_result, v2_result, "document_analysis")

        assert comparison["both_success"], f"API 호출 실패"
        assert comparison["structure_compatible"], "응답 구조 불일치"

        # 요약에 기대 키워드 포함 확인
        v1_summary = v1_result["data"].get("summary", "")
        v2_summary = v2_result["data"].get("summary", "")

        for keyword in test_case["expected_in_summary"]:
            assert keyword in v1_summary or keyword in v2_summary, f"키워드 '{keyword}' 누락"

        logger.info(f"[DocAnalysis] v1: {v1_result['latency_ms']:.0f}ms, v2: {v2_result['latency_ms']:.0f}ms")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_document_analysis_all_cases(self, document_analysis_test_cases):
        """모든 문서 분석 테스트 케이스 비교"""
        results = []

        for test_case in document_analysis_test_cases:
            v1_result, v2_result = await asyncio.gather(
                call_v1_document_analysis(test_case["text"], test_case["document_type"]),
                call_v2_document_analysis(test_case["text"], test_case["document_type"])
            )

            comparison = compare_responses(v1_result, v2_result, "document_analysis")
            comparison["test_name"] = test_case["name"]
            results.append(comparison)

        success_count = sum(1 for r in results if r["both_success"])
        logger.info(f"[DocAnalysis 전체] 성공: {success_count}/{len(results)}")

        assert success_count == len(results)


class TestRiskAnalysisComparison:
    """리스크 분석 API v1 vs v2 비교 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_risk_analysis_basic(self, risk_analysis_test_cases):
        """기본 리스크 분석 비교"""
        test_case = risk_analysis_test_cases[0]

        v1_result, v2_result = await asyncio.gather(
            call_v1_risk_analysis(test_case["text"], test_case["document_type"]),
            call_v2_risk_analysis(test_case["text"], test_case["document_type"])
        )

        comparison = compare_responses(v1_result, v2_result, "risk_analysis")

        assert comparison["both_success"], f"API 호출 실패"
        assert comparison["structure_compatible"], "응답 구조 불일치"

        logger.info(f"[RiskAnalysis] v1: {v1_result['latency_ms']:.0f}ms, v2: {v2_result['latency_ms']:.0f}ms")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_risk_analysis_all_cases(self, risk_analysis_test_cases):
        """모든 리스크 분석 테스트 케이스 비교"""
        results = []

        for test_case in risk_analysis_test_cases:
            v1_result, v2_result = await asyncio.gather(
                call_v1_risk_analysis(test_case["text"], test_case["document_type"]),
                call_v2_risk_analysis(test_case["text"], test_case["document_type"])
            )

            comparison = compare_responses(v1_result, v2_result, "risk_analysis")
            comparison["test_name"] = test_case["name"]
            results.append(comparison)

        success_count = sum(1 for r in results if r["both_success"])
        logger.info(f"[RiskAnalysis 전체] 성공: {success_count}/{len(results)}")

        assert success_count == len(results)


# ===== Summary Test =====

class TestV1V2ComparisonSummary:
    """V1 vs V2 비교 요약 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="서버 실행 필요")
    async def test_full_comparison_report(
        self,
        rag_test_cases,
        document_analysis_test_cases,
        risk_analysis_test_cases
    ):
        """전체 비교 리포트 생성"""
        all_comparisons = []

        # RAG 테스트
        for tc in rag_test_cases:
            v1, v2 = await asyncio.gather(
                call_v1_rag(tc["query"], tc["top_k"]),
                call_v2_rag(tc["query"], tc["top_k"])
            )
            comparison = compare_responses(v1, v2, "rag")
            comparison["test_name"] = tc["name"]
            all_comparisons.append(comparison)

        # Document Analysis 테스트
        for tc in document_analysis_test_cases:
            v1, v2 = await asyncio.gather(
                call_v1_document_analysis(tc["text"], tc["document_type"]),
                call_v2_document_analysis(tc["text"], tc["document_type"])
            )
            comparison = compare_responses(v1, v2, "document_analysis")
            comparison["test_name"] = tc["name"]
            all_comparisons.append(comparison)

        # Risk Analysis 테스트
        for tc in risk_analysis_test_cases:
            v1, v2 = await asyncio.gather(
                call_v1_risk_analysis(tc["text"], tc["document_type"]),
                call_v2_risk_analysis(tc["text"], tc["document_type"])
            )
            comparison = compare_responses(v1, v2, "risk_analysis")
            comparison["test_name"] = tc["name"]
            all_comparisons.append(comparison)

        # 리포트 생성
        total = len(all_comparisons)
        success = sum(1 for c in all_comparisons if c["both_success"])
        avg_v1_latency = sum(c["v1_latency_ms"] for c in all_comparisons) / total
        avg_v2_latency = sum(c["v2_latency_ms"] for c in all_comparisons) / total
        avg_improvement = sum(c["latency_improvement_percent"] for c in all_comparisons) / total

        logger.info("=" * 60)
        logger.info("V1 vs V2 비교 리포트")
        logger.info("=" * 60)
        logger.info(f"총 테스트: {total}")
        logger.info(f"성공: {success} ({success/total*100:.1f}%)")
        logger.info(f"V1 평균 응답시간: {avg_v1_latency:.0f}ms")
        logger.info(f"V2 평균 응답시간: {avg_v2_latency:.0f}ms")
        logger.info(f"평균 성능 개선율: {avg_improvement:.1f}%")
        logger.info("=" * 60)

        assert success == total, f"일부 테스트 실패: {success}/{total}"


# ===== Main =====

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
