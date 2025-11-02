"""
Hybrid Search 성능 비교 테스트

학습 목적:
- Semantic vs BM25 vs Hybrid 검색 성능 비교
- Adaptive weighting 효과 검증
- 다양한 쿼리 타입별 최적 검색 방식 분석
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from configs.config import config
from src.embeddings.embedder import KoreanLegalEmbedder
from src.embeddings.vectordb import create_vector_db
from src.retrieval.retriever import LegalDocumentRetriever
from src.retrieval.bm25_index import BM25Index
from src.retrieval.hybrid_retriever import HybridRetriever


def load_indexes():
    """벡터 DB와 BM25 인덱스 로드"""
    logger.info("Loading embedder...")
    embedder = KoreanLegalEmbedder(
        model_name=config.embedding.model_name,
        device=config.embedding.device
    )

    logger.info("Loading vector database...")
    vectordb = create_vector_db(
        config.vectordb.db_type,
        persist_directory=config.vectordb.chroma_persist_dir,
        collection_name=config.vectordb.collection_name
    )

    logger.info("Loading BM25 index...")
    bm25_index = BM25Index(
        k1=config.rag.bm25_k1,
        b=config.rag.bm25_b
    )
    bm25_index.load(config.vectordb.bm25_index_path)

    # Create retrievers
    semantic_retriever = LegalDocumentRetriever(
        vectordb=vectordb,
        embedder=embedder,
        top_k=5
    )

    hybrid_retriever = HybridRetriever(
        semantic_retriever=semantic_retriever,
        bm25_index=bm25_index,
        fusion_method=config.rag.fusion_method,
        semantic_weight=config.rag.semantic_weight,
        rrf_k=config.rag.rrf_k,
        enable_adaptive_weighting=config.rag.enable_adaptive_weighting
    )

    return embedder, semantic_retriever, bm25_index, hybrid_retriever


def test_query(
    query: str,
    semantic_retriever: LegalDocumentRetriever,
    bm25_index: BM25Index,
    hybrid_retriever: HybridRetriever,
    top_k: int = 5
):
    """단일 쿼리 테스트"""
    logger.info(f"\n{'='*100}")
    logger.info(f"Query: '{query}'")
    logger.info(f"{'='*100}")

    # Query analysis
    analysis = hybrid_retriever.analyze_query(query)
    logger.info(f"\n[Query Analysis]")
    logger.info(f"  Tokens: {analysis['bm25_analysis']['tokens']}")
    logger.info(f"  Has statute ref: {analysis['bm25_analysis']['has_statute_ref']}")
    logger.info(f"  Has case number: {analysis['bm25_analysis']['has_case_number']}")
    logger.info(f"  Adaptive semantic weight: {analysis['adaptive_semantic_weight']:.2f}")
    logger.info(f"  Adaptive BM25 weight: {analysis['adaptive_bm25_weight']:.2f}")

    # 1. Semantic Search
    logger.info(f"\n[1. Semantic Search Only]")
    semantic_results = semantic_retriever.retrieve(query, top_k=top_k)
    for i, result in enumerate(semantic_results[:3], 1):
        logger.info(f"  {i}. Score: {result['score']:.4f} | {result['text'][:100]}...")

    # 2. BM25 Search
    logger.info(f"\n[2. BM25 Search Only]")
    bm25_results = bm25_index.search(query, top_k=top_k)
    for i, result in enumerate(bm25_results[:3], 1):
        logger.info(f"  {i}. Score: {result['score']:.4f} | {result['text'][:100]}...")

    # 3. Hybrid Search
    logger.info(f"\n[3. Hybrid Search (Adaptive)]")
    hybrid_results = hybrid_retriever.retrieve(query, top_k=top_k)
    for i, result in enumerate(hybrid_results[:3], 1):
        fusion_info = f"[{result.get('fusion_method', 'unknown')}]"
        semantic_rank = result.get('semantic_rank', '-')
        bm25_rank = result.get('bm25_rank', '-')
        logger.info(
            f"  {i}. Score: {result['score']:.4f} | "
            f"Sem rank: {semantic_rank} | BM25 rank: {bm25_rank} | "
            f"{result['text'][:80]}..."
        )

    # Comparison
    logger.info(f"\n[Comparison Summary]")
    logger.info(f"  Semantic top-1 score: {semantic_results[0]['score']:.4f}")
    logger.info(f"  BM25 top-1 score: {bm25_results[0]['score']:.4f}")
    logger.info(f"  Hybrid top-1 score: {hybrid_results[0]['score']:.4f}")

    # Check if top results are different
    sem_top = semantic_results[0]['text'][:50]
    bm25_top = bm25_results[0]['text'][:50]
    hybrid_top = hybrid_results[0]['text'][:50]

    logger.info(f"\n  Top-1 diversity:")
    logger.info(f"    Semantic vs BM25: {'DIFFERENT' if sem_top != bm25_top else 'SAME'}")
    logger.info(f"    Hybrid vs Semantic: {'DIFFERENT' if hybrid_top != sem_top else 'SAME'}")
    logger.info(f"    Hybrid vs BM25: {'DIFFERENT' if hybrid_top != bm25_top else 'SAME'}")


def main():
    """메인 테스트 실행"""
    logger.info("="*100)
    logger.info("Hybrid Search Performance Test")
    logger.info("="*100)

    # Load indexes
    embedder, semantic_retriever, bm25_index, hybrid_retriever = load_indexes()

    # Stats
    stats = hybrid_retriever.get_search_stats()
    logger.info(f"\n[System Stats]")
    logger.info(f"  Semantic DB count: {stats['semantic_db_count']}")
    logger.info(f"  BM25 index count: {stats['bm25_index_count']}")
    logger.info(f"  Fusion method: {stats['fusion_method']}")
    logger.info(f"  Adaptive weighting: {stats['adaptive_weighting_enabled']}")

    # Test queries (다양한 유형)
    test_queries = [
        # 조항 번호 쿼리 (BM25 유리)
        "형법 제329조",
        "형사소송법 제200조",

        # 의미 질문 (Semantic 유리)
        "절도죄의 구성요건은 무엇인가요?",
        "정당방위가 성립하는 요건은?",

        # 복합 질문 (Hybrid 유리)
        "절도죄와 강도죄의 차이점은?",
        "업무상과실치사와 과실치사의 차이",

        # 판례 번호 (BM25 유리)
        "2023도1234",

        # 긴 서술형 질문 (Semantic 유리)
        "피고인이 피해자의 주거에 침입하여 재물을 절취한 경우 어떤 죄가 성립하나요?",
    ]

    for query in test_queries:
        test_query(
            query,
            semantic_retriever,
            bm25_index,
            hybrid_retriever,
            top_k=5
        )

    logger.info(f"\n{'='*100}")
    logger.info("Test completed!")
    logger.info("="*100)

    # Summary
    logger.info(f"\n[학습 포인트]")
    logger.info("1. 조항 번호 쿼리 (예: '형법 제329조')")
    logger.info("   → BM25 점수가 높고, Hybrid는 BM25 weight를 높임 (0.8)")
    logger.info("")
    logger.info("2. 의미 질문 (예: '절도죄의 구성요건은?')")
    logger.info("   → Semantic 점수가 높고, Hybrid는 Semantic weight를 높임 (0.7)")
    logger.info("")
    logger.info("3. 복합 질문 (예: '절도죄와 강도죄의 차이')")
    logger.info("   → Hybrid가 두 방식의 장점을 결합하여 최고 성능")
    logger.info("")
    logger.info("4. Adaptive Weighting")
    logger.info("   → 쿼리 타입을 자동 분석하여 가중치 조정")
    logger.info("   → 조항/판례 번호: BM25 ↑, 의미 질문: Semantic ↑")


if __name__ == "__main__":
    main()
