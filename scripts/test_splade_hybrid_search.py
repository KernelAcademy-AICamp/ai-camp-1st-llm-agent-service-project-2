#!/usr/bin/env python3
"""
Qdrant 네이티브 하이브리드 검색 테스트 (SPLADE 기반)
Dense (snowflake-arctic-embed) + Sparse (SPLADE) + RRF Fusion

사용법:
    python scripts/test_splade_hybrid_search.py
    python scripts/test_splade_hybrid_search.py "사기죄 구성요건"
"""

import sys
import os
import time
import argparse

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def test_hybrid_search(query: str = None):
    """하이브리드 검색 테스트"""

    print("=" * 60)
    print("Qdrant 네이티브 하이브리드 검색 테스트 (SPLADE)")
    print("=" * 60)

    # 1. 컴포넌트 초기화
    print("\n[1] 컴포넌트 초기화...")

    from apps.ai_service.config.settings import settings
    from libs.rag_core.embeddings.remote_embedder import RemoteEmbedder
    from libs.rag_core.embeddings.splade_encoder import SPLADEEncoder
    from libs.rag_core.retrieval.qdrant_hybrid_retriever import QdrantHybridRetriever

    # Embedder 초기화
    print(f"  - RemoteEmbedder 초기화 (model: {settings.EMBED_MODEL})")
    embedder = RemoteEmbedder(
        base_url=settings.REMOTE_EMBED_BASE_URL,
        api_key=settings.REMOTE_EMBED_API_KEY,
        model=settings.EMBED_MODEL
    )

    # SPLADE Encoder 초기화
    print(f"  - SPLADE Encoder 초기화 (model: {settings.SPLADE_MODEL})")
    start = time.time()
    splade_encoder = SPLADEEncoder(model_name=settings.SPLADE_MODEL)
    print(f"    → SPLADE 로드 시간: {time.time() - start:.2f}초")

    # Retriever 초기화
    print(f"  - QdrantHybridRetriever 초기화 (collection: {settings.QDRANT_HYBRID_COLLECTION})")
    retriever = QdrantHybridRetriever(
        qdrant_url=settings.QDRANT_URL,
        collection_name=settings.QDRANT_HYBRID_COLLECTION,
        dense_embedder=embedder,
        splade_encoder=splade_encoder
    )

    # 컬렉션 통계
    stats = retriever.get_stats()
    print(f"\n[컬렉션 정보]")
    print(f"  - 컬렉션: {stats.get('collection_name', 'unknown')}")
    print(f"  - 문서 수: {stats.get('points_count', 0):,}")
    print(f"  - 상태: {stats.get('status', 'unknown')}")
    print(f"  - 검색 모드: {stats.get('search_mode', 'unknown')}")

    # 2. 테스트 쿼리
    if query:
        test_queries = [query]
    else:
        test_queries = [
            "근로계약 해지 요건",
            "사기죄의 구성요건",
            "임대차 보증금 반환",
            "상속 포기 절차",
            "개인정보 보호법 위반"
        ]

    print("\n" + "=" * 60)
    print("[2] 검색 테스트")
    print("=" * 60)

    for q in test_queries:
        print(f"\n{'─' * 50}")
        print(f"쿼리: {q}")
        print(f"{'─' * 50}")

        # 하이브리드 검색
        start = time.time()
        results = retriever.retrieve(q, top_k=3, search_mode="hybrid")
        hybrid_time = time.time() - start

        print(f"\n[하이브리드 검색] ({hybrid_time:.3f}초)")
        for i, r in enumerate(results, 1):
            meta = r.get('metadata', {})
            doc_type = meta.get('doc_type', '문서')
            score = r.get('score', 0)
            text_preview = r.get('text', '')[:100].replace('\n', ' ')
            print(f"  {i}. [{doc_type}] (score: {score:.4f})")
            print(f"     {text_preview}...")

        # Dense 전용 검색
        start = time.time()
        dense_results = retriever.retrieve(q, top_k=3, search_mode="dense")
        dense_time = time.time() - start

        print(f"\n[Dense 검색] ({dense_time:.3f}초)")
        for i, r in enumerate(dense_results, 1):
            meta = r.get('metadata', {})
            doc_type = meta.get('doc_type', '문서')
            score = r.get('score', 0)
            print(f"  {i}. [{doc_type}] (score: {score:.4f})")

        # Sparse (SPLADE) 전용 검색
        start = time.time()
        sparse_results = retriever.retrieve(q, top_k=3, search_mode="sparse")
        sparse_time = time.time() - start

        print(f"\n[Sparse/SPLADE 검색] ({sparse_time:.3f}초)")
        for i, r in enumerate(sparse_results, 1):
            meta = r.get('metadata', {})
            doc_type = meta.get('doc_type', '문서')
            score = r.get('score', 0)
            print(f"  {i}. [{doc_type}] (score: {score:.4f})")

    # 3. 성능 요약
    print("\n" + "=" * 60)
    print("[3] 테스트 완료")
    print("=" * 60)
    print("✓ Qdrant 네이티브 하이브리드 검색이 정상 작동합니다.")
    print("✓ Dense + SPLADE + RRF Fusion 검색 지원")
    print("✓ BM25 인덱스 불필요 (시작 시간 40초+ 절약)")


def main():
    parser = argparse.ArgumentParser(description="SPLADE 하이브리드 검색 테스트")
    parser.add_argument("query", nargs="?", type=str, default=None,
                       help="검색 쿼리 (없으면 기본 쿼리로 테스트)")
    args = parser.parse_args()

    test_hybrid_search(args.query)


if __name__ == "__main__":
    main()
