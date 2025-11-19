"""
BM25 인덱스 생성 스크립트
ChromaDB에서 문서를 로드하여 BM25 인덱스 구축

실행 방법:
    python scripts/build_bm25_index.py

소요 시간: ~10분 (388,767 문서)
출력: data/vectordb/bm25/ (약 500MB)
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import chromadb
from chromadb.config import Settings
from apps.backend.core.retrieval.bm25_index import BM25Index
from tqdm import tqdm
import logging
import time
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """BM25 인덱스 생성 메인 함수"""

    # 전체 시작 시간
    total_start_time = time.time()
    timing_metrics = {}

    # ChromaDB 로드 (프로젝트 루트의 data 디렉토리 사용)
    chroma_path = BASE_DIR / "data" / "vectordb" / "chroma_criminal_law"
    logger.info(f"Loading ChromaDB from {chroma_path}")

    load_start = time.time()
    client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False)
    )

    collection = client.get_collection(name="criminal_law_docs")
    total_docs = collection.count()
    timing_metrics['chromadb_load_time'] = time.time() - load_start
    logger.info(f"Found {total_docs:,} documents in ChromaDB (loaded in {timing_metrics['chromadb_load_time']:.2f}s)")

    # BM25 인덱스 초기화
    logger.info("Initializing BM25 index...")
    init_start = time.time()
    bm25_index = BM25Index(k1=1.5, b=0.75)
    timing_metrics['bm25_init_time'] = time.time() - init_start

    # 배치 크기
    batch_size = 1000

    # 문서를 배치로 로드하여 BM25 인덱스에 추가
    logger.info(f"Building BM25 index (batch_size={batch_size})...")

    build_start = time.time()
    for offset in tqdm(range(0, total_docs, batch_size), desc="Processing batches"):
        # ChromaDB에서 배치 로드
        results = collection.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas"]
        )

        texts = results['documents']
        metadatas = results['metadatas']

        # BM25 인덱스에 추가
        bm25_index.add_documents(texts=texts, metadatas=metadatas)

    timing_metrics['bm25_build_time'] = time.time() - build_start
    logger.info(f"✅ BM25 index built successfully ({bm25_index.get_count():,} documents) in {timing_metrics['bm25_build_time']:.2f}s")

    # 인덱스 저장 (프로젝트 루트의 data 디렉토리 사용)
    output_path = BASE_DIR / "data" / "vectordb" / "bm25"
    logger.info(f"Saving BM25 index to {output_path}")

    save_start = time.time()
    bm25_index.save(str(output_path))
    timing_metrics['bm25_save_time'] = time.time() - save_start

    logger.info(f"✅ BM25 index saved successfully in {timing_metrics['bm25_save_time']:.2f}s")

    # 저장 크기 확인
    index_size = sum(f.stat().st_size for f in output_path.glob('**/*') if f.is_file())
    timing_metrics['index_size_mb'] = index_size / 1024 / 1024
    logger.info(f"Index size: {timing_metrics['index_size_mb']:.2f} MB")

    # 테스트 검색
    logger.info("\n=== Test Search ===")
    test_queries = ["형법 제329조", "절도죄", "정당방위"]

    test_start = time.time()
    for query in test_queries:
        results = bm25_index.search(query, top_k=3)
        logger.info(f"\nQuery: '{query}'")
        logger.info(f"Found {len(results)} results")
        if results:
            logger.info(f"Top result score: {results[0]['score']:.4f}")
    timing_metrics['test_search_time'] = time.time() - test_start

    # 전체 시간 계산
    timing_metrics['total_time'] = time.time() - total_start_time
    timing_metrics['total_documents'] = total_docs
    timing_metrics['timestamp'] = datetime.now().isoformat()

    # 성능 메트릭 저장
    metrics_path = BASE_DIR / "data" / "pipeline_metrics" / "bm25_build_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(timing_metrics, f, indent=2, ensure_ascii=False)

    logger.info(f"\n{'='*60}")
    logger.info("📊 Performance Metrics Summary:")
    logger.info(f"{'='*60}")
    logger.info(f"  ChromaDB Load Time:  {timing_metrics['chromadb_load_time']:>8.2f}s")
    logger.info(f"  BM25 Init Time:      {timing_metrics['bm25_init_time']:>8.2f}s")
    logger.info(f"  BM25 Build Time:     {timing_metrics['bm25_build_time']:>8.2f}s")
    logger.info(f"  BM25 Save Time:      {timing_metrics['bm25_save_time']:>8.2f}s")
    logger.info(f"  Test Search Time:    {timing_metrics['test_search_time']:>8.2f}s")
    logger.info(f"  {'─'*60}")
    logger.info(f"  TOTAL TIME:          {timing_metrics['total_time']:>8.2f}s")
    logger.info(f"  Total Documents:     {timing_metrics['total_documents']:>8,}")
    logger.info(f"  Index Size:          {timing_metrics['index_size_mb']:>8.2f} MB")
    logger.info(f"  Metrics saved to:    {metrics_path}")
    logger.info(f"{'='*60}")

    logger.info("\n✅ All done!")


if __name__ == "__main__":
    main()