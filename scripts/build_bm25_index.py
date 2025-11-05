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
from app.backend.core.retrieval.bm25_index import BM25Index
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """BM25 인덱스 생성 메인 함수"""

    # ChromaDB 로드
    chroma_path = BASE_DIR / "data" / "vectordb" / "chroma_criminal_law"
    logger.info(f"Loading ChromaDB from {chroma_path}")

    client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False)
    )

    collection = client.get_collection(name="criminal_law_docs")
    total_docs = collection.count()
    logger.info(f"Found {total_docs:,} documents in ChromaDB")

    # BM25 인덱스 초기화
    logger.info("Initializing BM25 index...")
    bm25_index = BM25Index(k1=1.5, b=0.75)

    # 배치 크기
    batch_size = 1000

    # 문서를 배치로 로드하여 BM25 인덱스에 추가
    logger.info(f"Building BM25 index (batch_size={batch_size})...")

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

    logger.info(f"✅ BM25 index built successfully ({bm25_index.get_count():,} documents)")

    # 인덱스 저장
    output_path = BASE_DIR / "data" / "vectordb" / "bm25"
    logger.info(f"Saving BM25 index to {output_path}")

    bm25_index.save(str(output_path))

    logger.info("✅ BM25 index saved successfully")

    # 저장 크기 확인
    index_size = sum(f.stat().st_size for f in output_path.glob('**/*') if f.is_file())
    logger.info(f"Index size: {index_size / 1024 / 1024:.2f} MB")

    # 테스트 검색
    logger.info("\n=== Test Search ===")
    test_queries = ["형법 제329조", "절도죄", "정당방위"]

    for query in test_queries:
        results = bm25_index.search(query, top_k=3)
        logger.info(f"\nQuery: '{query}'")
        logger.info(f"Found {len(results)} results")
        if results:
            logger.info(f"Top result score: {results[0]['score']:.4f}")

    logger.info("\n✅ All done!")


if __name__ == "__main__":
    main()
