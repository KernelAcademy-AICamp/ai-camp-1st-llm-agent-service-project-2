#!/usr/bin/env python3
"""
v1 vs v2 API 실제 성능 비교 벤치마크
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, Any, List

BASE_URL = "http://localhost:8001"

# 테스트 쿼리 목록
TEST_QUERIES = [
    "형법 제250조 살인죄의 구성요건은 무엇인가요?",
    "정당방위의 성립요건에 대해 설명해주세요.",
    "절도죄와 강도죄의 차이점은 무엇인가요?",
    "명예훼손죄와 모욕죄는 어떻게 다른가요?",
    "사기죄의 기망행위 요건에 대해 알려주세요.",
]

def measure_request(url: str, payload: Dict[str, Any], name: str) -> Dict[str, Any]:
    """단일 요청 측정"""
    start_time = time.time()

    try:
        response = requests.post(url, json=payload, timeout=120)
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # ms

        if response.status_code == 200:
            data = response.json()
            return {
                "name": name,
                "success": True,
                "latency_ms": round(latency, 2),
                "status_code": response.status_code,
                "response_length": len(json.dumps(data)),
                "answer_length": len(data.get("answer", "")),
                "sources_count": len(data.get("sources", [])),
            }
        else:
            return {
                "name": name,
                "success": False,
                "latency_ms": round(latency, 2),
                "status_code": response.status_code,
                "error": response.text[:200],
            }
    except Exception as e:
        return {
            "name": name,
            "success": False,
            "latency_ms": 0,
            "error": str(e),
        }

def run_v1_tests() -> List[Dict[str, Any]]:
    """v1 API 테스트"""
    results = []
    print("\n📊 Running v1 API Tests (POST /v1/chat/rag)")
    print("=" * 60)

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"  [{i}/{len(TEST_QUERIES)}] Testing: {query[:30]}...")
        result = measure_request(
            f"{BASE_URL}/v1/chat/rag",
            {"query": query, "top_k": 5},
            f"v1_query_{i}"
        )
        results.append(result)

        if result["success"]:
            print(f"       ✅ {result['latency_ms']}ms, {result['answer_length']} chars, {result['sources_count']} sources")
        else:
            print(f"       ❌ Error: {result.get('error', 'Unknown')[:50]}")

    return results

def run_v2_tests() -> List[Dict[str, Any]]:
    """v2 API 테스트"""
    results = []
    print("\n📊 Running v2 API Tests (POST /v2/rag/chat)")
    print("=" * 60)

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"  [{i}/{len(TEST_QUERIES)}] Testing: {query[:30]}...")
        result = measure_request(
            f"{BASE_URL}/v2/rag/chat",
            {"query": query, "top_k": 5},
            f"v2_query_{i}"
        )
        results.append(result)

        if result["success"]:
            print(f"       ✅ {result['latency_ms']}ms, {result['answer_length']} chars, {result['sources_count']} sources")
        else:
            print(f"       ❌ Error: {result.get('error', 'Unknown')[:50]}")

    return results

def calculate_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """통계 계산"""
    successful = [r for r in results if r["success"]]

    if not successful:
        return {
            "total_tests": len(results),
            "success_count": 0,
            "success_rate": 0,
            "avg_latency_ms": 0,
            "min_latency_ms": 0,
            "max_latency_ms": 0,
            "avg_answer_length": 0,
            "avg_sources_count": 0,
        }

    latencies = [r["latency_ms"] for r in successful]
    answer_lengths = [r.get("answer_length", 0) for r in successful]
    sources_counts = [r.get("sources_count", 0) for r in successful]

    return {
        "total_tests": len(results),
        "success_count": len(successful),
        "success_rate": round(len(successful) / len(results) * 100, 2),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
        "min_latency_ms": round(min(latencies), 2),
        "max_latency_ms": round(max(latencies), 2),
        "avg_answer_length": round(sum(answer_lengths) / len(answer_lengths), 0),
        "avg_sources_count": round(sum(sources_counts) / len(sources_counts), 2),
    }

def compare_results(v1_stats: Dict, v2_stats: Dict) -> Dict[str, Any]:
    """v1 vs v2 비교"""
    if v1_stats["avg_latency_ms"] > 0 and v2_stats["avg_latency_ms"] > 0:
        latency_diff = v1_stats["avg_latency_ms"] - v2_stats["avg_latency_ms"]
        latency_improvement = (latency_diff / v1_stats["avg_latency_ms"]) * 100
    else:
        latency_diff = 0
        latency_improvement = 0

    return {
        "latency_diff_ms": round(latency_diff, 2),
        "latency_improvement_pct": round(latency_improvement, 2),
        "v2_faster": v2_stats["avg_latency_ms"] < v1_stats["avg_latency_ms"],
    }

def main():
    print("\n" + "=" * 70)
    print("🔬 v1 vs v2 API Performance Benchmark")
    print("=" * 70)
    print(f"📅 Date: {datetime.now().isoformat()}")
    print(f"🔗 Server: {BASE_URL}")
    print(f"📝 Test Queries: {len(TEST_QUERIES)}")

    # Health Check
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ Server Health: {health.json().get('status', 'unknown')}")
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return

    # Run tests
    v1_results = run_v1_tests()
    v2_results = run_v2_tests()

    # Calculate stats
    v1_stats = calculate_stats(v1_results)
    v2_stats = calculate_stats(v2_results)
    comparison = compare_results(v1_stats, v2_stats)

    # Print results
    print("\n" + "=" * 70)
    print("📊 BENCHMARK RESULTS")
    print("=" * 70)

    print("\n📌 v1 API (Phase 3 - Custom Python)")
    print("-" * 40)
    print(f"  Success Rate:    {v1_stats['success_rate']}%")
    print(f"  Avg Latency:     {v1_stats['avg_latency_ms']}ms")
    print(f"  Min Latency:     {v1_stats['min_latency_ms']}ms")
    print(f"  Max Latency:     {v1_stats['max_latency_ms']}ms")
    print(f"  Avg Answer Len:  {v1_stats['avg_answer_length']} chars")
    print(f"  Avg Sources:     {v1_stats['avg_sources_count']}")

    print("\n📌 v2 API (Phase 4 - LangGraph)")
    print("-" * 40)
    print(f"  Success Rate:    {v2_stats['success_rate']}%")
    print(f"  Avg Latency:     {v2_stats['avg_latency_ms']}ms")
    print(f"  Min Latency:     {v2_stats['min_latency_ms']}ms")
    print(f"  Max Latency:     {v2_stats['max_latency_ms']}ms")
    print(f"  Avg Answer Len:  {v2_stats['avg_answer_length']} chars")
    print(f"  Avg Sources:     {v2_stats['avg_sources_count']}")

    print("\n📌 COMPARISON")
    print("-" * 40)
    if comparison["v2_faster"]:
        print(f"  ✅ v2 is FASTER by {abs(comparison['latency_diff_ms'])}ms ({abs(comparison['latency_improvement_pct'])}% improvement)")
    else:
        print(f"  ⚠️  v1 is faster by {abs(comparison['latency_diff_ms'])}ms")

    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "test_queries": TEST_QUERIES,
        "v1": {"results": v1_results, "stats": v1_stats},
        "v2": {"results": v2_results, "stats": v2_stats},
        "comparison": comparison,
    }

    output_path = "scripts/v1_v2_benchmark_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n📁 Results saved to: {output_path}")
    print("=" * 70)

if __name__ == "__main__":
    main()
