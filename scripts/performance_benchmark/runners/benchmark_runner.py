#!/usr/bin/env python3
"""
Benchmark Runner for Performance Testing

Executes standard test cases and collects performance metrics.
Used to compare Phase 3 (current) vs Phase 4 (LangGraph + FastMCP) implementations.

Usage:
    python benchmark_runner.py --mode phase3 --output results/phase3_baseline_v1.json
    python benchmark_runner.py --mode phase4 --output results/phase4_langgraph_v2.json

Phase 4 (v2 API) Features:
- LangGraph StateGraph 기반 워크플로우
- Checkpointing (Risk, LLM Compare, Crawler)
- Human-in-the-Loop 패턴
- MCP Tools 통합
"""

import argparse
import json
import os
import sys
import time
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from performance_benchmark.runners.metrics_collector import (
    MetricsCollector,
    BenchmarkResult,
    TimingContext
)


class BenchmarkRunner:
    """
    Executes benchmark tests and collects metrics.

    Supports two modes:
    - phase3: Current Django + FastAPI implementation
    - phase4: LangGraph + FastMCP implementation (future)
    """

    def __init__(
        self,
        mode: str = "phase3",
        base_url: str = "http://localhost:8000/api/v1",
        ai_service_url: str = "http://localhost:8001"
    ):
        self.mode = mode
        self.base_url = base_url
        self.ai_service_url = ai_service_url
        self.collector = MetricsCollector()
        self.results: List[BenchmarkResult] = []
        self.token: Optional[str] = None

        # Load test cases
        self.test_cases = self._load_test_cases()

    def _load_test_cases(self) -> Dict[str, Any]:
        """Load standard test cases from JSON file"""
        test_file = Path(__file__).parent.parent / "test_cases" / "standard_tests.json"
        if test_file.exists():
            with open(test_file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            print(f"Warning: Test cases file not found at {test_file}")
            return {"test_cases": {}}

    def _authenticate(self) -> bool:
        """Authenticate and get access token"""
        email = f"benchmark_user_{int(time.time())}@test.com"
        password = "BenchmarkPassword123"

        try:
            # Sign up
            resp = requests.post(
                f"{self.base_url}/auth/signup",
                json={
                    "email": email,
                    "password": password,
                    "password_confirm": password,
                    "full_name": "Benchmark User"
                },
                timeout=30
            )

            # Login
            resp = requests.post(
                f"{self.base_url}/auth/login",
                json={"email": email, "password": password},
                timeout=30
            )

            data = resp.json()
            if "access" in data:
                self.token = data["access"]
                return True

            return False
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False

    def _headers(self) -> Dict[str, str]:
        """Get headers with authorization"""
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def run_rag_chat_tests(self) -> List[BenchmarkResult]:
        """Run RAG chat benchmark tests"""
        print(f"\n--- RAG Chat Tests ({self.mode}) ---")
        results = []

        test_cases = self.test_cases.get("test_cases", {}).get("rag_chat", {}).get("tests", [])

        for test in test_cases:
            test_id = test["test_id"]
            test_name = test["name"]
            query = test["query"]
            top_k = test.get("top_k", 5)

            print(f"  Running: {test_name}...", end=" ", flush=True)

            if self.mode == "phase4":
                # Phase 4: v2 API (LangGraph)
                def execute_rag():
                    return requests.post(
                        f"{self.ai_service_url}/v2/rag/chat",
                        json={"query": query, "top_k": top_k},
                        timeout=120
                    )
            else:
                # Phase 3: v1 API
                def execute_rag():
                    return requests.post(
                        f"{self.base_url}/ai/chat/rag",
                        headers=self._headers(),
                        json={"query": query, "top_k": top_k},
                        timeout=120
                    )

            perf_metrics, response = self.collector.collect_performance_metrics(
                operation=f"rag_chat_{test_id}",
                func=execute_rag
            )

            result = BenchmarkResult(
                test_id=test_id,
                test_name=test_name,
                category=test.get("category", "general"),
                performance=perf_metrics
            )

            if response and response.status_code == 200:
                data = response.json()
                result.llm = self.collector.collect_llm_metrics(data)
                result.response_data = {
                    "answer_length": len(data.get("answer", "")),
                    "sources_count": len(data.get("sources", [])),
                    "status": "success",
                    "api_version": "v2" if self.mode == "phase4" else "v1"
                }
                print(f"OK ({perf_metrics.duration_ms:.0f}ms)")
            else:
                result.response_data = {
                    "status": "error",
                    "error": perf_metrics.error_message or "Unknown error",
                    "api_version": "v2" if self.mode == "phase4" else "v1"
                }
                print(f"FAIL")

            results.append(result)

        return results

    def run_document_analysis_tests(self) -> List[BenchmarkResult]:
        """Run document analysis benchmark tests (summarize + clause extraction)"""
        print(f"\n--- Document Analysis Tests ({self.mode}) ---")
        results = []

        test_cases = self.test_cases.get("test_cases", {}).get("document_analysis", {}).get("tests", [])

        for test in test_cases:
            test_id = test["test_id"]
            test_name = test["name"]
            content = test["test_content"]

            print(f"  Running: {test_name}...", end=" ", flush=True)

            if self.mode == "phase4":
                # Phase 4: v2 API (LangGraph)
                def execute_summarize():
                    return requests.post(
                        f"{self.ai_service_url}/v2/documents/analyze/text",
                        json={
                            "text": content,
                            "document_type": test.get("document_type", "CONTRACT")
                        },
                        timeout=120
                    )
            else:
                # Phase 3: v1 API
                def execute_summarize():
                    return requests.post(
                        f"{self.ai_service_url}/v1/llm/summarize",
                        json={
                            "document_id": f"benchmark_{test_id}",
                            "text": content,
                            "summary_type": "GLOBAL",
                            "document_type": test.get("document_type", "CONTRACT")
                        },
                        timeout=120
                    )

            perf_metrics, response = self.collector.collect_performance_metrics(
                operation=f"doc_analysis_{test_id}",
                func=execute_summarize
            )

            result = BenchmarkResult(
                test_id=test_id,
                test_name=test_name,
                category=test.get("category", "general"),
                performance=perf_metrics
            )

            if response and response.status_code == 200:
                data = response.json()
                result.llm = self.collector.collect_llm_metrics(data)
                result.response_data = {
                    "summary_length": len(data.get("summary", "")),
                    "status": "success",
                    "api_version": "v2" if self.mode == "phase4" else "v1"
                }
                print(f"OK ({perf_metrics.duration_ms:.0f}ms)")
            else:
                result.response_data = {
                    "status": "error",
                    "error": perf_metrics.error_message or "Unknown error",
                    "api_version": "v2" if self.mode == "phase4" else "v1"
                }
                print(f"FAIL")

            results.append(result)

        return results

    def run_risk_analysis_tests(self) -> List[BenchmarkResult]:
        """Run risk analysis benchmark tests (Phase 3-4)"""
        print(f"\n--- Risk Analysis Tests ({self.mode}) ---")
        results = []

        test_cases = self.test_cases.get("test_cases", {}).get("risk_analysis", {}).get("tests", [])

        for test in test_cases:
            test_id = test["test_id"]
            test_name = test["name"]
            content = test["test_content"]

            print(f"  Running: {test_name}...", end=" ", flush=True)

            if self.mode == "phase4":
                # Phase 4: v2 API (LangGraph with Checkpointing)
                def execute_risk():
                    return requests.post(
                        f"{self.ai_service_url}/v2/risk/analyze",
                        json={
                            "document_text": content,
                            "document_type": test.get("document_type", "CONTRACT")
                        },
                        timeout=120
                    )
            else:
                # Phase 3: v1 API
                def execute_risk():
                    return requests.post(
                        f"{self.ai_service_url}/v1/llm/analyze_risk",
                        json={
                            "document_id": f"benchmark_{test_id}",
                            "text": content,
                            "document_type": test.get("document_type", "CONTRACT")
                        },
                        timeout=120
                    )

            perf_metrics, response = self.collector.collect_performance_metrics(
                operation=f"risk_analysis_{test_id}",
                func=execute_risk
            )

            result = BenchmarkResult(
                test_id=test_id,
                test_name=test_name,
                category=test.get("category", "general"),
                performance=perf_metrics
            )

            if response and response.status_code == 200:
                data = response.json()
                result.llm = self.collector.collect_llm_metrics(data)
                result.response_data = {
                    "risk_score": data.get("overall_risk_score", data.get("risk_score", 0)),
                    "risk_items_count": len(data.get("risk_items", [])),
                    "severity": data.get("severity", "unknown"),
                    "status": "success",
                    "api_version": "v2" if self.mode == "phase4" else "v1",
                    "checkpointing": self.mode == "phase4"
                }
                print(f"OK ({perf_metrics.duration_ms:.0f}ms)")
            else:
                result.response_data = {
                    "status": "error",
                    "error": perf_metrics.error_message or "Unknown error",
                    "api_version": "v2" if self.mode == "phase4" else "v1"
                }
                print(f"FAIL")

            results.append(result)

        return results

    def run_analytics_tests(self) -> List[BenchmarkResult]:
        """Run analytics benchmark tests (Phase 4 only)"""
        if self.mode != "phase4":
            return []

        print(f"\n--- Analytics Tests ({self.mode}) ---")
        results = []

        # Analytics test cases (Phase 4 전용)
        analytics_tests = [
            {
                "test_id": "analytics_overview",
                "name": "Analytics Overview",
                "time_range": "1d"
            },
            {
                "test_id": "analytics_trends",
                "name": "Analytics Trends",
                "time_range": "7d"
            },
            {
                "test_id": "analytics_generate",
                "name": "Analytics Full Report",
                "time_range": "1d"
            }
        ]

        for test in analytics_tests:
            test_id = test["test_id"]
            test_name = test["name"]
            time_range = test["time_range"]

            print(f"  Running: {test_name}...", end=" ", flush=True)

            if test_id == "analytics_overview":
                def execute_analytics():
                    return requests.get(
                        f"{self.ai_service_url}/v2/analytics/overview",
                        params={"time_range": time_range},
                        timeout=60
                    )
            elif test_id == "analytics_trends":
                def execute_analytics():
                    return requests.get(
                        f"{self.ai_service_url}/v2/analytics/trends",
                        params={"time_range": time_range},
                        timeout=60
                    )
            else:
                def execute_analytics():
                    return requests.post(
                        f"{self.ai_service_url}/v2/analytics/generate",
                        json={"time_range": time_range},
                        timeout=120
                    )

            perf_metrics, response = self.collector.collect_performance_metrics(
                operation=f"analytics_{test_id}",
                func=execute_analytics
            )

            result = BenchmarkResult(
                test_id=test_id,
                test_name=test_name,
                category="analytics",
                performance=perf_metrics
            )

            if response and response.status_code == 200:
                data = response.json()
                result.response_data = {
                    "status": "success",
                    "api_version": "v2",
                    "checkpointing": False  # Analytics는 Checkpointing 불필요
                }
                print(f"OK ({perf_metrics.duration_ms:.0f}ms)")
            else:
                result.response_data = {
                    "status": "error",
                    "error": perf_metrics.error_message or "Unknown error",
                    "api_version": "v2"
                }
                print(f"FAIL")

            results.append(result)

        return results

    def run_crawler_tests(self) -> List[BenchmarkResult]:
        """Run crawler benchmark tests (Phase 4 only)"""
        if self.mode != "phase4":
            return []

        print(f"\n--- Crawler Tests ({self.mode}) ---")
        results = []

        # Crawler health test only (실제 크롤링은 시간이 오래 걸림)
        crawler_tests = [
            {
                "test_id": "crawler_health",
                "name": "Crawler Health Check",
            }
        ]

        for test in crawler_tests:
            test_id = test["test_id"]
            test_name = test["name"]

            print(f"  Running: {test_name}...", end=" ", flush=True)

            def execute_crawler():
                return requests.get(
                    f"{self.ai_service_url}/v2/crawler/health",
                    timeout=30
                )

            perf_metrics, response = self.collector.collect_performance_metrics(
                operation=f"crawler_{test_id}",
                func=execute_crawler
            )

            result = BenchmarkResult(
                test_id=test_id,
                test_name=test_name,
                category="crawler",
                performance=perf_metrics
            )

            if response and response.status_code == 200:
                data = response.json()
                result.response_data = {
                    "status": "success",
                    "api_version": "v2",
                    "checkpointing": data.get("checkpointing", True),
                    "max_retry": data.get("max_retry", 3)
                }
                print(f"OK ({perf_metrics.duration_ms:.0f}ms)")
            else:
                result.response_data = {
                    "status": "error",
                    "error": perf_metrics.error_message or "Unknown error",
                    "api_version": "v2"
                }
                print(f"FAIL")

            results.append(result)

        return results

    def calculate_summary(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Calculate summary statistics from results"""
        summary = {}

        # Group by test type
        groups = {}
        for r in results:
            prefix = r.test_id.split("_")[0]
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(r)

        for group_name, group_results in groups.items():
            durations = [r.performance.duration_ms for r in group_results if r.performance]
            tokens = [r.llm.total_tokens for r in group_results if r.llm]
            costs = [r.llm.estimated_cost_usd for r in group_results if r.llm]

            if durations:
                sorted_durations = sorted(durations)
                p95_idx = int(len(sorted_durations) * 0.95)

                summary[group_name] = {
                    "count": len(group_results),
                    "avg_duration_ms": round(sum(durations) / len(durations), 2),
                    "min_duration_ms": round(min(durations), 2),
                    "max_duration_ms": round(max(durations), 2),
                    "p95_duration_ms": round(sorted_durations[min(p95_idx, len(sorted_durations)-1)], 2),
                    "total_tokens": sum(tokens),
                    "avg_tokens": round(sum(tokens) / len(tokens), 2) if tokens else 0,
                    "total_cost_usd": round(sum(costs), 6),
                    "success_rate": round(
                        sum(1 for r in group_results if r.response_data.get("status") == "success") /
                        len(group_results) * 100, 2
                    )
                }

        # Overall summary
        all_durations = [r.performance.duration_ms for r in results if r.performance]
        all_costs = [r.llm.estimated_cost_usd for r in results if r.llm]

        summary["overall"] = {
            "total_tests": len(results),
            "total_duration_ms": round(sum(all_durations), 2),
            "avg_duration_ms": round(sum(all_durations) / len(all_durations), 2) if all_durations else 0,
            "total_cost_usd": round(sum(all_costs), 6),
            "success_rate": round(
                sum(1 for r in results if r.response_data.get("status") == "success") /
                len(results) * 100, 2
            ) if results else 0
        }

        return summary

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all benchmark tests"""
        print(f"\n{'='*60}")
        print(f"Performance Benchmark - {self.mode.upper()}")
        print(f"{'='*60}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Base URL: {self.base_url}")
        print(f"AI Service: {self.ai_service_url}")
        if self.mode == "phase4":
            print(f"API Version: v2 (LangGraph)")

        # Authenticate (Phase 3 only needs this)
        if self.mode == "phase3":
            print("\nAuthenticating...")
            if not self._authenticate():
                print("Warning: Authentication failed, some tests may fail")
        else:
            print("\nPhase 4: Using direct AI Service calls (v2 API)")

        # Run test suites
        all_results = []

        # RAG Chat tests
        rag_results = self.run_rag_chat_tests()
        all_results.extend(rag_results)

        # Document Analysis tests
        doc_results = self.run_document_analysis_tests()
        all_results.extend(doc_results)

        # Risk Analysis tests
        risk_results = self.run_risk_analysis_tests()
        all_results.extend(risk_results)

        # Phase 4 전용 테스트
        analytics_results = self.run_analytics_tests()
        all_results.extend(analytics_results)

        crawler_results = self.run_crawler_tests()
        all_results.extend(crawler_results)

        # Calculate summary
        summary = self.calculate_summary(all_results)

        # Build final output
        output = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "mode": self.mode,
                "api_version": "v2" if self.mode == "phase4" else "v1",
                "version": self.test_cases.get("version", "1.0.0"),
                "system": self.collector.get_system_info(),
                "langgraph_enabled": self.mode == "phase4",
                "checkpointing_enabled": self.mode == "phase4"
            },
            "results": {
                "rag_chat": [r.to_dict() for r in rag_results],
                "document_analysis": [r.to_dict() for r in doc_results],
                "risk_analysis": [r.to_dict() for r in risk_results],
                "analytics": [r.to_dict() for r in analytics_results] if analytics_results else [],
                "crawler": [r.to_dict() for r in crawler_results] if crawler_results else []
            },
            "summary": summary
        }

        return output

    def save_results(self, output: Dict[str, Any], output_path: str):
        """Save results to JSON file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {output_path}")

    def print_summary(self, output: Dict[str, Any]):
        """Print summary to console"""
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}")

        summary = output.get("summary", {})
        overall = summary.get("overall", {})

        print(f"\nTotal Tests: {overall.get('total_tests', 0)}")
        print(f"Success Rate: {overall.get('success_rate', 0)}%")
        print(f"Total Duration: {overall.get('total_duration_ms', 0):.0f}ms")
        print(f"Avg Duration: {overall.get('avg_duration_ms', 0):.0f}ms")
        print(f"Total Cost: ${overall.get('total_cost_usd', 0):.4f}")

        print(f"\nBy Category:")
        for cat, stats in summary.items():
            if cat != "overall":
                print(f"  {cat}:")
                print(f"    - Tests: {stats.get('count', 0)}")
                print(f"    - Avg: {stats.get('avg_duration_ms', 0):.0f}ms")
                print(f"    - P95: {stats.get('p95_duration_ms', 0):.0f}ms")
                print(f"    - Success: {stats.get('success_rate', 0)}%")


def main():
    parser = argparse.ArgumentParser(
        description="Performance Benchmark Runner"
    )
    parser.add_argument(
        "--mode",
        choices=["phase3", "phase4"],
        default="phase3",
        help="Benchmark mode (phase3 or phase4)"
    )
    parser.add_argument(
        "--output",
        default="results/benchmark_results.json",
        help="Output file path"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000/api/v1",
        help="Django API base URL"
    )
    parser.add_argument(
        "--ai-url",
        default="http://localhost:8001",
        help="AI Service URL"
    )

    args = parser.parse_args()

    # Change to script directory
    os.chdir(Path(__file__).parent.parent)

    # Run benchmark
    runner = BenchmarkRunner(
        mode=args.mode,
        base_url=args.base_url,
        ai_service_url=args.ai_url
    )

    output = runner.run_all_tests()
    runner.print_summary(output)
    runner.save_results(output, args.output)

    # Exit with appropriate code
    success_rate = output.get("summary", {}).get("overall", {}).get("success_rate", 0)
    sys.exit(0 if success_rate >= 80 else 1)


if __name__ == "__main__":
    main()
