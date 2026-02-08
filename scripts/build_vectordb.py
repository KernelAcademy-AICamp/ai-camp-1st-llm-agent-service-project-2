"""
Vector Database 구축 스크립트

세 가지 데이터 소스 지원:
1. AI-Hub 형사법 데이터 (CSV/JSON 파일) - 기본 지식 베이스
2. PostgreSQL 크롤링 데이터 - 최신 판례 업데이트
3. 청킹된 데이터 (JSON) - 미리 청킹된 데이터

사용법:
    # AI-Hub 데이터로 구축
    python scripts/build_vectordb.py --source aihub --max_files 100

    # 청킹된 데이터로 구축 (권장)
    python scripts/build_vectordb.py --source chunked --chunks-path data/processed/chunks.json

    # PostgreSQL 데이터로 구축
    python scripts/build_vectordb.py --source db --max_docs 100
"""

import sys
import asyncio
import os
import json
from pathlib import Path
import time
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load environment variables
load_dotenv()

import logging
from tqdm import tqdm

# ⚠️ 올바른 import 경로 (libs.rag_core 사용)
from libs.rag_core.embeddings.embedder import KoreanLegalEmbedder
from libs.rag_core.embeddings.vectordb import create_vector_db

# Remote embedder (선택적)
try:
    from libs.rag_core.embeddings.remote_embedder import RemoteEmbedder
except ImportError:
    RemoteEmbedder = None

# Qdrant VectorDB
from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB

# Data loader for AI-Hub data
from scripts.criminal_law_data_loader import CriminalLawDataLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경변수
EMBED_MODE = os.getenv("EMBED_MODE", "local")  # remote, local
EMBED_MODEL = os.getenv("EMBED_MODEL", "dragonkue/snowflake-arctic-embed-l-v2.0-ko")
REMOTE_EMBED_URL = os.getenv("REMOTE_EMBED_BASE_URL", "https://llm.wonllmapi.uk")

VECTOR_DB = os.getenv("VECTOR_DB", "qdrant")  # qdrant (default)
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "law_documents")


def load_chunked_data(chunks_path: str) -> list:
    """미리 청킹된 데이터 로드"""
    path = Path(chunks_path)
    if not path.exists():
        raise FileNotFoundError(f"청킹 파일을 찾을 수 없습니다: {chunks_path}")

    logger.info(f"Loading chunked data from: {chunks_path}")
    with open(path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    logger.info(f"✅ Loaded {len(chunks):,} chunks")

    # 형식 변환
    documents = []
    for chunk in chunks:
        documents.append({
            'text': chunk['content'],
            'metadata': chunk.get('metadata', {})
        })

    return documents


def load_aihub_data(max_files: int = None) -> list:
    """AI-Hub 형사법 데이터 로드"""
    logger.info("Loading AI-Hub criminal law data...")

    try:
        loader = CriminalLawDataLoader()

        documents = loader.load_dataset(
            use_source=True,
            use_labeled=False,
            source_types=['판결문', '법령', '결정례', '해석례'],
            max_per_type=max_files,
            split='training'
        )

        logger.info(f"Loaded {len(documents)} documents from AI-Hub data")

        formatted_docs = []
        for doc in documents:
            formatted_docs.append({
                "text": doc['content'],
                "metadata": {
                    "source": doc['metadata'].get('source', ''),
                    "doc_id": doc['metadata'].get('doc_id', ''),
                    "type": doc['metadata'].get('type', ''),
                    "file": doc['metadata'].get('file', '')
                }
            })

        return formatted_docs

    except Exception as e:
        logger.error(f"Error loading AI-Hub data: {e}")
        return []


async def load_precedents_from_db(max_docs: int = None) -> list:
    """PostgreSQL DB에서 판례 로드"""
    logger.info("Loading precedents from PostgreSQL database...")

    try:
        from sqlalchemy import select
        from apps.backend_api.core.database import async_session
        from apps.backend_api.models.precedent import Precedent

        async with async_session() as session:
            stmt = select(Precedent).order_by(Precedent.id.desc())
            if max_docs:
                stmt = stmt.limit(max_docs)

            result = await session.execute(stmt)
            precedents = result.scalars().all()

        logger.info(f"Loaded {len(precedents)} precedents from database")

        documents = []
        for prec in precedents:
            text_parts = []
            if prec.case_number:
                text_parts.append(f"사건번호: {prec.case_number}")
            if prec.title:
                text_parts.append(f"제목: {prec.title}")
            if prec.summary:
                text_parts.append(f"요약: {prec.summary}")
            if prec.full_text:
                text_parts.append(f"전문: {prec.full_text}")

            full_text = "\n".join(text_parts)

            metadata = {
                "id": prec.id,
                "case_number": prec.case_number or "",
                "title": prec.title or "",
                "source": "postgresql_db",
                "type": "precedent"
            }

            documents.append({
                "text": full_text,
                "metadata": metadata
            })

        return documents

    except ImportError as e:
        logger.warning(f"Database module not available: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading from database: {e}")
        return []


def initialize_embedder():
    """환경변수에 따라 임베더 초기화"""
    logger.info(f"\nStep 2: Initializing embedder (mode: {EMBED_MODE})...")
    embed_init_start = time.time()

    if EMBED_MODE == "remote":
        if RemoteEmbedder is None:
            raise ImportError("RemoteEmbedder not available. Install httpx.")

        logger.info(f"Using RemoteEmbedder: {REMOTE_EMBED_URL}")
        embedder = RemoteEmbedder(
            base_url=REMOTE_EMBED_URL,
            batch_size=96,
            timeout=600
        )
    else:  # local
        logger.info(f"Using local KoreanLegalEmbedder: {EMBED_MODEL}")
        embedder = KoreanLegalEmbedder(
            model_name=EMBED_MODEL,
            device=None  # auto-detect
        )

    elapsed = time.time() - embed_init_start
    logger.info(f"✅ Embedder initialized in {elapsed:.2f}s")
    logger.info(f"   Dimension: {embedder.get_embedding_dimension()}")

    return embedder


def initialize_vectordb(embedding_dim: int):
    """환경변수에 따라 VectorDB 초기화"""
    logger.info(f"\nStep 4: Initializing VectorDB (type: {VECTOR_DB})...")
    vectordb_init_start = time.time()

    # Qdrant is the only supported VectorDB
    logger.info(f"Using Qdrant: {QDRANT_URL}")
    vectordb = QdrantVectorDB(
        url=QDRANT_URL,
        collection_name=QDRANT_COLLECTION,
        embedding_dim=embedding_dim,
        distance="cosine"
    )

    elapsed = time.time() - vectordb_init_start
    logger.info(f"✅ VectorDB initialized in {elapsed:.2f}s")

    return vectordb


def main(
    source: str = "db",
    max_docs: int = None,
    max_files: int = None,
    chunks_path: str = None,
    build_bm25: bool = False
):
    """메인 함수"""
    logger.info("\n" + "="*70)
    logger.info(" 🚀 Vector Database Construction (Integrated)")
    logger.info("="*70 + "\n")

    total_start_time = time.time()
    timing_metrics = {}

    # 1. 데이터 로드
    logger.info(f"Step 1: Loading data from {source}...")
    load_start = time.time()

    if source == "chunked":
        if not chunks_path:
            raise ValueError("--chunks-path required when source=chunked")
        documents = load_chunked_data(chunks_path)
    elif source == "aihub":
        documents = load_aihub_data(max_files=max_files)
    elif source == "db":
        documents = asyncio.run(load_precedents_from_db(max_docs))
    else:
        logger.error(f"Unknown source: {source}. Use 'aihub', 'db', or 'chunked'")
        return

    if not documents:
        logger.error("❌ No documents found!")
        return

    timing_metrics['data_load_time'] = time.time() - load_start
    logger.info(f"✅ Loaded {len(documents)} documents in {timing_metrics['data_load_time']:.2f}s")

    # max_docs 제한
    if max_docs and len(documents) > max_docs:
        logger.info(f"Limiting to {max_docs} documents")
        documents = documents[:max_docs]

    texts = [doc['text'] for doc in documents]
    metadatas = [doc['metadata'] for doc in documents]

    # 2. 임베더 초기화
    embedder = initialize_embedder()

    # 3. 임베딩 생성
    logger.info("\nStep 3: Generating embeddings...")
    logger.info(f"   Processing {len(texts)} documents...")
    embed_start = time.time()

    embeddings = embedder.embed_documents(texts, show_progress=True)

    timing_metrics['embedding_time'] = time.time() - embed_start
    timing_metrics['docs_per_second'] = len(texts) / timing_metrics['embedding_time']
    logger.info(f"✅ Embeddings generated in {timing_metrics['embedding_time']:.2f}s")
    logger.info(f"   Speed: {timing_metrics['docs_per_second']:.2f} docs/sec")
    logger.info(f"   Shape: {embeddings.shape}")

    # 4. VectorDB 저장
    vectordb = initialize_vectordb(embeddings.shape[1])

    logger.info("\nStep 5: Storing in VectorDB...")
    store_start = time.time()

    vectordb.add_documents(texts, embeddings, metadatas)

    timing_metrics['vectordb_time'] = time.time() - store_start
    logger.info(f"✅ Stored in VectorDB in {timing_metrics['vectordb_time']:.2f}s")

    # 5. 저장 및 검증
    vectordb.save()
    final_count = vectordb.get_count()
    logger.info(f"   Total documents in DB: {final_count:,}")

    # 6. 통계
    if hasattr(vectordb, 'get_stats'):
        stats = vectordb.get_stats()
        logger.info(f"\nVectorDB Stats: {stats}")

    # 7. 테스트 검색
    logger.info("\nStep 6: Testing search...")
    test_queries = ["형법 제329조", "절도죄", "정당방위"]

    for query in test_queries:
        try:
            query_embedding = embedder.embed_query(query)
            results = vectordb.search(query_embedding, top_k=3)
            logger.info(f"   ✓ Query: '{query}' -> {len(results)} results")
            if results and 'score' in results[0]:
                logger.info(f"     Top score: {results[0]['score']:.4f}")
        except Exception as e:
            logger.error(f"   ✗ Query failed: {e}")

    # 8. 메트릭 저장
    total_time = time.time() - total_start_time
    timing_metrics['total_time'] = total_time
    timing_metrics['total_documents'] = final_count
    timing_metrics['timestamp'] = datetime.now().isoformat()
    timing_metrics['data_source'] = source
    timing_metrics['embed_mode'] = EMBED_MODE
    timing_metrics['vector_db'] = VECTOR_DB
    timing_metrics['embedding_dim'] = embeddings.shape[1]

    metrics_path = BASE_DIR / 'data' / 'pipeline_metrics' / 'vectordb_build_metrics.json'
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(timing_metrics, f, indent=2, ensure_ascii=False)

    # 요약 출력
    logger.info("\n" + "="*70)
    logger.info(" 📊 Performance Metrics Summary")
    logger.info("="*70)
    logger.info(f"  Data Source:             {source.upper()}")
    logger.info(f"  Embed Mode:              {EMBED_MODE}")
    logger.info(f"  Vector DB:               {VECTOR_DB}")
    logger.info(f"  Data Load Time:          {timing_metrics['data_load_time']:>8.2f}s")
    logger.info(f"  Embedding Time:          {timing_metrics['embedding_time']:>8.2f}s")
    logger.info(f"  VectorDB Time:           {timing_metrics['vectordb_time']:>8.2f}s")
    logger.info(f"  {'─'*70}")
    logger.info(f"  TOTAL TIME:              {total_time:>8.2f}s")
    logger.info(f"  Total Documents:         {final_count:>8,}")
    logger.info(f"  Processing Speed:        {timing_metrics['docs_per_second']:>8.2f} docs/sec")
    logger.info(f"  Embedding Dimension:     {timing_metrics['embedding_dim']}")
    logger.info(f"  Metrics saved to:        {metrics_path}")
    logger.info("="*70 + "\n")

    logger.info("✅ Vector Database construction complete!\n")

    # Close embedder if needed
    if hasattr(embedder, 'close'):
        embedder.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build Vector Database from criminal law data",
        epilog="""
사용 예시:
  # 1. 청킹된 데이터로 구축 (권장)
  python scripts/build_vectordb.py --source chunked --chunks-path data/processed/chunks.json

  # 2. AI-Hub 데이터 빠른 테스트 (100개 파일)
  python scripts/build_vectordb.py --source aihub --max_files 100

  # 3. AI-Hub 전체 데이터
  python scripts/build_vectordb.py --source aihub --build_bm25

  # 4. PostgreSQL 데이터
  python scripts/build_vectordb.py --source db --max_docs 100
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source",
        type=str,
        default="db",
        choices=["aihub", "db", "chunked"],
        help="Data source: 'aihub', 'db', or 'chunked'"
    )
    parser.add_argument(
        "--max_files",
        type=int,
        default=None,
        help="Maximum number of files to load from AI-Hub data"
    )
    parser.add_argument(
        "--max_docs",
        type=int,
        default=None,
        help="Maximum number of documents to process"
    )
    parser.add_argument(
        "--chunks-path",
        type=str,
        default=None,
        help="Path to chunked data JSON (required when source=chunked)"
    )
    parser.add_argument(
        "--build_bm25",
        action="store_true",
        help="Build BM25 index after Vector DB construction"
    )

    args = parser.parse_args()

    main(
        source=args.source,
        max_docs=args.max_docs,
        max_files=args.max_files,
        chunks_path=args.chunks_path,
        build_bm25=args.build_bm25
    )
