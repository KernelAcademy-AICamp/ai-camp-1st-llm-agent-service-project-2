#!/usr/bin/env python
"""
BM25 인덱스 재구축 스크립트 (v2 - chunks_full.json 기반)

Qdrant와 동일한 chunks_full.json(716,191개) 기반으로 BM25 인덱스 생성
Hybrid Search를 위해 두 인덱스가 동기화되어야 함

실행 방법:
    python scripts/build_bm25_index.py

예상 소요 시간: ~5-10분 (716,191 문서)
출력: data/vectordb/bm25/ (약 1.5GB)

변경 이력:
    - v1: 기존 데이터 기반 (448,370개)
    - v2: chunks_full.json 기반 (716,191개) - Qdrant 동기화

     Building BM25 index:  67%|██████▋   | 48/72 [04:50<04:42, 11.78s/it]
     2025-11-30 22:32:10.834 | INFO     | 
     libs.rag_core.retrieval.bm25_index:add_documents:102 - Added 10000 
     documents to BM25 index. Total: 490000
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# 프로젝트 루트 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from loguru import logger
from libs.rag_core.retrieval.bm25_index import BM25Index


def build_bm25_index(
    chunks_path: str = "data/processed/chunks_full.json",
    output_path: str = "data/vectordb/bm25",
    k1: float = 1.5,
    b: float = 0.75,
    batch_size: int = 10000
):
    """
    BM25 인덱스 구축 (chunks_full.json 기반)

    Args:
        chunks_path: 청킹 데이터 경로
        output_path: 인덱스 저장 경로
        k1: BM25 term frequency saturation 파라미터
        b: BM25 length normalization 파라미터
        batch_size: 배치 크기 (메모리 관리용)
    """
    total_start_time = time.time()
    timing_metrics = {}

    chunks_file = BASE_DIR / chunks_path
    output_dir = BASE_DIR / output_path

    logger.info(f"{'='*60}")
    logger.info(f"BM25 Index Build (chunks_full.json 기반)")
    logger.info(f"{'='*60}")
    logger.info(f"Source: {chunks_file}")
    logger.info(f"Output: {output_dir}")

    # 청킹 데이터 로드
    load_start = time.time()
    logger.info(f"Loading chunks from: {chunks_file}")

    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    timing_metrics['load_time'] = time.time() - load_start
    logger.info(f"Loaded {len(chunks):,} chunks in {timing_metrics['load_time']:.2f}s")

    # BM25 인덱스 생성
    logger.info(f"Initializing BM25 index (k1={k1}, b={b})...")
    bm25 = BM25Index(k1=k1, b=b)

    # 배치 처리로 문서 추가
    build_start = time.time()

    for i in tqdm(range(0, len(chunks), batch_size), desc="Building BM25 index"):
        batch = chunks[i:i + batch_size]

        texts = []
        metadatas = []

        for chunk in batch:
            # content 필드 사용 (chunks_full.json 형식)
            text = chunk.get("content", "")
            metadata = chunk.get("metadata", {})

            if text.strip():
                texts.append(text)
                metadatas.append(metadata)

        if texts:
            bm25.add_documents(texts, metadatas)

    timing_metrics['build_time'] = time.time() - build_start
    logger.info(f"Built BM25 index with {bm25.get_count():,} documents in {timing_metrics['build_time']:.2f}s")

    # 저장
    save_start = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Saving index to: {output_dir}")
    bm25.save(str(output_dir))
    timing_metrics['save_time'] = time.time() - save_start

    # 저장 크기 확인
    index_size = sum(f.stat().st_size for f in output_dir.glob('**/*') if f.is_file())
    timing_metrics['index_size_mb'] = index_size / 1024 / 1024

    # 검증
    logger.info("\nVerifying index...")
    bm25_loaded = BM25Index()
    bm25_loaded.load(str(output_dir))

    test_queries = ["형법 절도죄", "제329조", "정당방위", "2023도1234"]
    for query in test_queries:
        results = bm25_loaded.search(query, top_k=3)
        logger.info(f"  Query: '{query}' -> {len(results)} results")
        if results:
            doc_type = results[0].get('metadata', {}).get('doc_type', 'unknown')
            logger.info(f"    Top: score={results[0]['score']:.4f}, doc_type={doc_type}")

    # Qdrant 동기화 확인
    logger.info("\n=== Qdrant 동기화 확인 ===")
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url="http://localhost:6333")
        qdrant_count = client.get_collection("law_documents").points_count
        bm25_count = bm25_loaded.get_count()

        logger.info(f"  Qdrant: {qdrant_count:,}개")
        logger.info(f"  BM25:   {bm25_count:,}개")

        if qdrant_count == bm25_count:
            logger.info("  ✅ 동기화 완료!")
        else:
            diff = abs(qdrant_count - bm25_count)
            logger.warning(f"  ⚠️ 불일치: 차이 {diff:,}개")
    except Exception as e:
        logger.warning(f"  Qdrant 연결 실패: {e}")

    # 성능 메트릭
    timing_metrics['total_time'] = time.time() - total_start_time
    timing_metrics['total_documents'] = bm25_loaded.get_count()
    timing_metrics['timestamp'] = datetime.now().isoformat()

    logger.info(f"\n{'='*60}")
    logger.info("📊 Performance Metrics Summary:")
    logger.info(f"{'='*60}")
    logger.info(f"  Load Time:     {timing_metrics['load_time']:>8.2f}s")
    logger.info(f"  Build Time:    {timing_metrics['build_time']:>8.2f}s")
    logger.info(f"  Save Time:     {timing_metrics['save_time']:>8.2f}s")
    logger.info(f"  {'─'*56}")
    logger.info(f"  TOTAL TIME:    {timing_metrics['total_time']:>8.2f}s")
    logger.info(f"  Documents:     {timing_metrics['total_documents']:>8,}")
    logger.info(f"  Index Size:    {timing_metrics['index_size_mb']:>8.2f} MB")
    logger.info(f"{'='*60}")

    # 메트릭 저장
    metrics_path = BASE_DIR / "data" / "pipeline_metrics" / "bm25_build_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(timing_metrics, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ BM25 Index Build Complete!")
    logger.info(f"  Metrics saved to: {metrics_path}")


if __name__ == "__main__":
    build_bm25_index()
