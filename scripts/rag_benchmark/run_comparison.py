#!/usr/bin/env python3
"""
RAG 시스템 비교 벤치마크 실행기

사용법:
    # 검색만 비교 (빠름)
    python run_comparison.py --mode search

    # 전체 RAG 비교 (검색 + LLM)
    python run_comparison.py --mode full

    # 특정 쿼리 파일 사용
    python run_comparison.py --mode search --queries path/to/queries.json
"""

import sys
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))


def run_search_comparison(args):
    """검색만 비교"""
    from scripts.rag_benchmark.component_comparison import ComponentComparison

    print("🔍 검색 비교 모드 (Retrieval Only)")
    print("-" * 50)

    comparison = ComponentComparison()
    comparison.setup()

    result = comparison.run_comparison(args.queries, top_k=args.top_k)
    comparison.print_summary(result)
    filepath = comparison.save_results(result, args.output)

    return filepath


def run_full_comparison(args):
    """전체 RAG 비교 (검색 + LLM)"""
    from scripts.rag_benchmark.full_comparison import FullComparisonBenchmark

    print("🔬 전체 RAG 비교 모드 (Retrieval + Generation)")
    print("-" * 50)

    benchmark = FullComparisonBenchmark()
    benchmark.setup()

    result = benchmark.run_comparison(args.queries, top_k=args.top_k)
    benchmark.print_summary(result)
    filepath = benchmark.save_results(result, args.output)

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="RAG 시스템 비교 벤치마크",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    # 검색만 비교 (빠름)
    python run_comparison.py --mode search

    # 전체 RAG 비교 (검색 + LLM 답변)
    python run_comparison.py --mode full

    # top_k 변경
    python run_comparison.py --mode search --top-k 10
        """
    )

    parser.add_argument(
        "--mode",
        choices=["search", "full"],
        default="search",
        help="비교 모드: search(검색만), full(검색+LLM)"
    )
    parser.add_argument(
        "--queries",
        type=str,
        default=str(BASE_DIR / "scripts" / "rag_benchmark" / "queries" / "test_queries.json"),
        help="테스트 쿼리 파일 경로"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="검색 결과 수"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(BASE_DIR / "scripts" / "rag_benchmark" / "results"),
        help="결과 저장 디렉토리"
    )

    args = parser.parse_args()

    print()
    print("=" * 70)
    print("🔬 RAG 시스템 Before vs After 비교 벤치마크")
    print("=" * 70)
    print()
    print("📋 비교 대상:")
    print("  Before: ChromaDB + ko-sroberta-multitask (768d) + 500자 청킹")
    print("  After:  Qdrant + snowflake-arctic-embed (1024d) + 법률특화 청킹")
    print()
    print("🔍 비교 범위: 판결문 + 결정례 (동일 데이터 타입)")
    print()

    if args.mode == "search":
        run_search_comparison(args)
    elif args.mode == "full":
        run_full_comparison(args)


if __name__ == "__main__":
    main()
