#!/usr/bin/env python3
"""
하이브리드 검색 테스트 (Dense + Sparse)

Dense 벡터(의미 검색)와 Sparse 벡터(키워드 검색)를 조합한
하이브리드 검색을 테스트합니다.

사용법:
    python scripts/test_hybrid_search.py "음주운전 처벌 기준"
    python scripts/test_hybrid_search.py "사기죄 고의" --alpha 0.7
"""

import sys
import os
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "libs" / "rag_core"))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.models import (
    SparseVector, NamedSparseVector, NamedVector,
    Prefetch, FusionQuery, Fusion,
    SearchRequest, Filter
)

# BM25 인코더
from scripts.add_sparse_vectors import KoreanBM25Encoder

# 임베딩
from embeddings.remote_embedder import RemoteEmbedder

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "law_documents")
VOCAB_PATH = "data/processed/bm25_vocab.json"


def hybrid_search(
    client: QdrantClient,
    collection_name: str,
    query: str,
    embedder: RemoteEmbedder,
    bm25_encoder: KoreanBM25Encoder,
    top_k: int = 5,
    alpha: float = 0.5  # dense 가중치 (1-alpha = sparse 가중치)
):
    """
    하이브리드 검색 (RRF Fusion)

    Args:
        client: Qdrant 클라이언트
        collection_name: 컬렉션 이름
        query: 검색 쿼리
        embedder: Dense 임베더
        bm25_encoder: Sparse 인코더
        top_k: 반환 결과 수
        alpha: Dense 벡터 가중치 (0~1)

    Returns:
        검색 결과 리스트
    """
    # Dense 벡터 생성
    dense_vector = embedder.embed_query(query)

    # Sparse 벡터 생성
    sparse_indices, sparse_values = bm25_encoder.encode(query)

    # Reciprocal Rank Fusion (RRF) 검색
    results = client.query_points(
        collection_name=collection_name,
        prefetch=[
            # Dense 검색 (의미적 유사도)
            Prefetch(
                query=dense_vector,
                using="dense",
                limit=top_k * 2
            ),
            # Sparse 검색 (키워드 매칭)
            Prefetch(
                query=SparseVector(
                    indices=sparse_indices,
                    values=sparse_values
                ),
                using="bm25",
                limit=top_k * 2
            )
        ],
        query=FusionQuery(fusion=Fusion.RRF),  # RRF로 결과 통합
        limit=top_k,
        with_payload=True
    )

    return results.points


def dense_only_search(
    client: QdrantClient,
    collection_name: str,
    query: str,
    embedder: RemoteEmbedder,
    top_k: int = 5
):
    """Dense 벡터만 사용한 검색"""
    dense_vector = embedder.embed_query(query)

    results = client.query_points(
        collection_name=collection_name,
        query=dense_vector,
        using="dense",
        limit=top_k,
        with_payload=True
    )

    return results.points


def sparse_only_search(
    client: QdrantClient,
    collection_name: str,
    query: str,
    bm25_encoder: KoreanBM25Encoder,
    top_k: int = 5
):
    """Sparse 벡터만 사용한 검색"""
    sparse_indices, sparse_values = bm25_encoder.encode(query)

    results = client.query_points(
        collection_name=collection_name,
        query=SparseVector(
            indices=sparse_indices,
            values=sparse_values
        ),
        using="bm25",
        limit=top_k,
        with_payload=True
    )

    return results.points


def print_results(results, title: str):
    """검색 결과 출력"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print(f"{'='*60}")

    for i, point in enumerate(results, 1):
        text = point.payload.get('text', '')[:200]
        source = point.payload.get('source', 'unknown')
        section = point.payload.get('section', '')
        score = point.score

        print(f"\n[{i}] Score: {score:.4f} | {source} | {section}")
        print(f"    {text}...")


def main():
    parser = argparse.ArgumentParser(description="하이브리드 검색 테스트")
    parser.add_argument("query", type=str, help="검색 쿼리")
    parser.add_argument("--top-k", type=int, default=5, help="결과 수")
    parser.add_argument("--alpha", type=float, default=0.5,
                       help="Dense 가중치 (0~1, 기본 0.5)")
    parser.add_argument("--compare", action="store_true",
                       help="Dense/Sparse/Hybrid 비교")

    args = parser.parse_args()

    print("\n" + "="*60)
    print(f"🔍 하이브리드 검색: \"{args.query}\"")
    print("="*60)

    # 클라이언트 초기화
    client = QdrantClient(url=QDRANT_URL, timeout=60)

    # 컬렉션 확인
    info = client.get_collection(QDRANT_COLLECTION)
    print(f"\n컬렉션: {QDRANT_COLLECTION}")
    print(f"  포인트 수: {info.points_count:,}")

    # 벡터 설정 확인
    vectors_config = info.config.params.vectors
    sparse_config = info.config.sparse_vectors_config

    if isinstance(vectors_config, dict):
        print(f"  Dense 벡터: {list(vectors_config.keys())}")
    else:
        print(f"  Dense 벡터: default ({vectors_config.size}d)")

    if sparse_config:
        print(f"  Sparse 벡터: {list(sparse_config.keys())}")
    else:
        print("  ⚠️ Sparse 벡터 없음 - add_sparse_vectors.py 먼저 실행 필요")
        return

    # 인코더 초기화
    embedder = RemoteEmbedder(model="dragonkue/snowflake-arctic-embed-l-v2.0-ko")
    bm25_encoder = KoreanBM25Encoder(vocab_path=VOCAB_PATH)

    if not bm25_encoder.vocab:
        print("❌ BM25 어휘 사전이 없습니다. add_sparse_vectors.py를 먼저 실행하세요.")
        return

    print(f"  BM25 어휘 크기: {len(bm25_encoder.vocab):,}")

    if args.compare:
        # 세 가지 방식 비교
        print("\n📊 검색 방식 비교")

        # 1. Dense only
        dense_results = dense_only_search(
            client, QDRANT_COLLECTION, args.query, embedder, args.top_k
        )
        print_results(dense_results, "Dense Only (의미 검색)")

        # 2. Sparse only
        sparse_results = sparse_only_search(
            client, QDRANT_COLLECTION, args.query, bm25_encoder, args.top_k
        )
        print_results(sparse_results, "Sparse Only (키워드 검색)")

        # 3. Hybrid
        hybrid_results = hybrid_search(
            client, QDRANT_COLLECTION, args.query,
            embedder, bm25_encoder, args.top_k, args.alpha
        )
        print_results(hybrid_results, f"Hybrid (alpha={args.alpha})")

    else:
        # 하이브리드 검색만
        results = hybrid_search(
            client, QDRANT_COLLECTION, args.query,
            embedder, bm25_encoder, args.top_k, args.alpha
        )
        print_results(results, f"Hybrid Search (alpha={args.alpha})")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
