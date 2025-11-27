"""
Vector Database 구축 스크립트

두 가지 데이터 소스 지원:
1. AI-Hub 형사법 데이터 (45,882개 CSV 파일) - 기본 지식 베이스
2. PostgreSQL 크롤링 데이터 - 최신 판례 업데이트

사용법:
    # AI-Hub 데이터로 구축 (권장)
    python scripts/build_vectordb.py --source aihub --max_files 100

    # PostgreSQL 데이터로 구축
    python scripts/build_vectordb.py --source db --max_docs 100

    # 전체 AI-Hub 데이터 (오래 걸림!)
    python scripts/build_vectordb.py --source aihub --build_bm25
"""

import sys
import asyncio
from pathlib import Path
import time
import json
from datetime import datetime

# Add project root to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import logging
from sqlalchemy import select
from tqdm import tqdm

# RAG Core imports
from libs.rag_core.embeddings.embedder import KoreanLegalEmbedder
from libs.rag_core.embeddings.vectordb import ChromaVectorDB

# AI Service imports
from apps.ai_service.models.database import async_session
from apps.ai_service.models.precedent import Precedent

# Data loader for AI-Hub data
from scripts.criminal_law_data_loader import CriminalLawDataLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_precedents_from_db(max_docs: int = None) -> list:
    """PostgreSQL DB에서 판례 로드"""
    logger.info("Loading precedents from PostgreSQL database...")

    async with async_session() as session:
        # 판례 쿼리
        stmt = select(Precedent).order_by(Precedent.id.desc())
        if max_docs:
            stmt = stmt.limit(max_docs)

        result = await session.execute(stmt)
        precedents = result.scalars().all()

    logger.info(f"Loaded {len(precedents)} precedents from database")

    # 문서 형식으로 변환
    documents = []
    for prec in precedents:
        # 판례 텍스트 구성
        text_parts = []
        if prec.case_number:
            text_parts.append(f"사건번호: {prec.case_number}")
        if prec.title:
            text_parts.append(f"제목: {prec.title}")
        if prec.court:
            text_parts.append(f"법원: {prec.court}")
        if prec.decision_date:
            text_parts.append(f"선고일: {prec.decision_date}")
        if prec.summary:
            text_parts.append(f"요약: {prec.summary}")
        if prec.full_text:
            text_parts.append(f"전문: {prec.full_text}")

        full_text = "\n".join(text_parts)

        metadata = {
            "id": prec.id,
            "case_number": prec.case_number or "",
            "title": prec.title or "",
            "court": prec.court or "",
            "decision_date": str(prec.decision_date) if prec.decision_date else "",
            "case_type": prec.case_type or "",
            "source": "postgresql_db",
            "type": "precedent"
        }

        documents.append({
            "text": full_text,
            "metadata": metadata
        })

    return documents


def load_aihub_data(max_files: int = None) -> list:
    """AI-Hub 형사법 데이터 로드"""
    logger.info("Loading AI-Hub criminal law data...")

    try:
        # CriminalLawDataLoader 초기화
        loader = CriminalLawDataLoader()

        # 원천 데이터 로드 (판례, 법령, 결정례, 해석례)
        documents = loader.load_dataset(
            use_source=True,
            use_labeled=False,  # 원천 데이터만 사용 (라벨링 데이터는 QA용)
            source_types=['판결문', '법령', '결정례', '해석례'],
            max_per_type=max_files,
            split='training'
        )

        logger.info(f"Loaded {len(documents)} documents from AI-Hub data")

        # 형식 변환
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
        logger.info("Please check if the data directory exists:")
        logger.info("  04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/")
        return []


def main(source: str = "db", max_docs: int = None, max_files: int = None, build_bm25: bool = False):
    """메인 함수"""
    logger.info("\n" + "="*70)
    logger.info(" 🚀 Vector Database Construction")
    logger.info("="*70 + "\n")

    # 전체 시작 시간
    total_start_time = time.time()
    timing_metrics = {}

    # 1. 데이터 로드
    logger.info(f"Step 1: Loading data from {source}...")
    load_start = time.time()

    if source == "aihub":
        documents = load_aihub_data(max_files=max_files)
    elif source == "db":
        documents = asyncio.run(load_precedents_from_db(max_docs))
    else:
        logger.error(f"Unknown source: {source}. Use 'aihub' or 'db'")
        return

    if not documents:
        logger.error("❌ No documents found!")
        if source == "db":
            logger.info("Please run the backend server first to crawl precedents.")
        elif source == "aihub":
            logger.info("Please check if the AI-Hub data directory exists.")
        return

    timing_metrics['data_load_time'] = time.time() - load_start
    logger.info(f"✅ Loaded {len(documents)} documents in {timing_metrics['data_load_time']:.2f}s")

    # max_docs 제한 적용 (AI-Hub 데이터의 경우)
    if max_docs and len(documents) > max_docs:
        logger.info(f"Limiting to {max_docs} documents")
        documents = documents[:max_docs]

    # 텍스트와 메타데이터 분리
    texts = [doc['text'] for doc in documents]
    metadatas = [doc['metadata'] for doc in documents]

    # 2. 임베딩 모델 초기화
    logger.info("\nStep 2: Initializing embedding model...")
    embed_init_start = time.time()

    embedder = KoreanLegalEmbedder()

    timing_metrics['embedder_init_time'] = time.time() - embed_init_start
    logger.info(f"✅ Embedder initialized in {timing_metrics['embedder_init_time']:.2f}s")
    logger.info(f"   Model: {embedder.model_name}")
    logger.info(f"   Device: {embedder.device}")
    logger.info(f"   Dimension: {embedder.get_embedding_dimension()}")

    # 3. 임베딩 생성
    logger.info("\nStep 3: Generating embeddings...")
    logger.info(f"   Processing {len(texts)} documents...")

    embed_start = time.time()

    embeddings = embedder.embed_documents(texts, show_progress=True)

    timing_metrics['embedding_generation_time'] = time.time() - embed_start
    timing_metrics['docs_per_second'] = len(texts) / timing_metrics['embedding_generation_time']

    logger.info(f"✅ Generated embeddings in {timing_metrics['embedding_generation_time']:.2f}s")
    logger.info(f"   Speed: {timing_metrics['docs_per_second']:.2f} docs/sec")
    logger.info(f"   Embedding shape: {embeddings.shape}")

    # 4. Vector DB 초기화 및 저장
    logger.info("\nStep 4: Initializing ChromaDB...")
    vectordb_init_start = time.time()

    chroma_path = BASE_DIR / "data" / "vectordb" / "chroma_criminal_law"
    vectordb = ChromaVectorDB(
        persist_directory=str(chroma_path),
        collection_name="criminal_law_docs"
    )

    timing_metrics['vectordb_init_time'] = time.time() - vectordb_init_start
    logger.info(f"✅ ChromaDB initialized in {timing_metrics['vectordb_init_time']:.2f}s")
    logger.info(f"   Path: {chroma_path}")

    # 5. 문서 추가
    logger.info("\nStep 5: Adding documents to ChromaDB...")
    add_docs_start = time.time()

    vectordb.add_documents(texts, embeddings, metadatas)

    timing_metrics['add_documents_time'] = time.time() - add_docs_start
    logger.info(f"✅ Added {len(texts)} documents in {timing_metrics['add_documents_time']:.2f}s")

    # 6. 저장 및 검증
    logger.info("\nStep 6: Saving and verifying...")
    save_start = time.time()

    vectordb.save()
    final_count = vectordb.get_count()

    timing_metrics['save_time'] = time.time() - save_start
    logger.info(f"✅ Saved successfully in {timing_metrics['save_time']:.2f}s")
    logger.info(f"   Total documents in DB: {final_count:,}")

    # DB 크기 확인
    if chroma_path.exists():
        db_size = sum(f.stat().st_size for f in chroma_path.glob('**/*') if f.is_file())
        timing_metrics['vectordb_size_mb'] = db_size / 1024 / 1024
        logger.info(f"   Database size: {timing_metrics['vectordb_size_mb']:.2f} MB")

    # 7. BM25 인덱스 구축 (옵션)
    if build_bm25:
        logger.info("\nStep 7: Building BM25 index...")
        import subprocess

        bm25_start = time.time()
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "scripts" / "build_bm25_index.py")],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True
        )

        timing_metrics['bm25_build_time'] = time.time() - bm25_start

        if result.returncode == 0:
            logger.info(f"✅ BM25 index built in {timing_metrics['bm25_build_time']:.2f}s")
        else:
            logger.warning(f"⚠️  BM25 index build failed: {result.stderr}")
    else:
        logger.info("\nStep 7: Skipping BM25 index (use --build_bm25 to enable)")

    # 8. 테스트 검색
    logger.info("\nStep 8: Testing search...")
    test_queries = ["형법 제329조", "절도죄", "정당방위"]

    test_start = time.time()
    search_successful = True

    for query in test_queries:
        try:
            query_embedding = embedder.embed_query(query)
            results = vectordb.search(query_embedding, top_k=3)
            logger.info(f"   ✓ Query: '{query}' -> {len(results)} results")
            if results and 'score' in results[0]:
                logger.info(f"     Top score: {results[0]['score']:.4f}")
        except Exception as e:
            logger.error(f"   ✗ Query failed: {e}")
            search_successful = False

    timing_metrics['test_search_time'] = time.time() - test_start
    timing_metrics['search_successful'] = search_successful

    # 전체 시간 계산
    timing_metrics['total_time'] = time.time() - total_start_time
    timing_metrics['total_documents'] = final_count
    timing_metrics['timestamp'] = datetime.now().isoformat()
    timing_metrics['data_source'] = source
    timing_metrics['embedding_model'] = embedder.model_name
    timing_metrics['embedding_dimension'] = embedder.get_embedding_dimension()

    # 성능 메트릭 저장
    metrics_path = BASE_DIR / "data" / "pipeline_metrics" / "vectordb_build_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(timing_metrics, f, indent=2, ensure_ascii=False)

    # 요약 출력
    logger.info("\n" + "="*70)
    logger.info(" 📊 Performance Metrics Summary")
    logger.info("="*70)
    logger.info(f"  Data Source:             {source.upper()}")
    logger.info(f"  Data Load Time:          {timing_metrics['data_load_time']:>8.2f}s")
    logger.info(f"  Embedder Init Time:      {timing_metrics['embedder_init_time']:>8.2f}s")
    logger.info(f"  Embedding Generation:    {timing_metrics['embedding_generation_time']:>8.2f}s")
    logger.info(f"  VectorDB Init Time:      {timing_metrics['vectordb_init_time']:>8.2f}s")
    logger.info(f"  Add Documents Time:      {timing_metrics['add_documents_time']:>8.2f}s")
    logger.info(f"  Save Time:               {timing_metrics['save_time']:>8.2f}s")
    if build_bm25 and 'bm25_build_time' in timing_metrics:
        logger.info(f"  BM25 Build Time:         {timing_metrics['bm25_build_time']:>8.2f}s")
    logger.info(f"  Test Search Time:        {timing_metrics['test_search_time']:>8.2f}s")
    logger.info(f"  {'─'*70}")
    logger.info(f"  TOTAL TIME:              {timing_metrics['total_time']:>8.2f}s")
    logger.info(f"  Total Documents:         {timing_metrics['total_documents']:>8,}")
    logger.info(f"  Processing Speed:        {timing_metrics['docs_per_second']:>8.2f} docs/sec")
    logger.info(f"  Database Size:           {timing_metrics.get('vectordb_size_mb', 0):>8.2f} MB")
    logger.info(f"  Embedding Model:         {timing_metrics['embedding_model']}")
    logger.info(f"  Device:                  {embedder.device}")
    logger.info(f"  Embedding Dimension:     {timing_metrics['embedding_dimension']}")
    logger.info(f"  Metrics saved to:        {metrics_path}")
    logger.info("="*70 + "\n")

    logger.info("✅ Vector Database construction complete!\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build Vector Database from criminal law data",
        epilog="""
사용 예시:
  # 1. AI-Hub 데이터 빠른 테스트 (100개 파일)
  python scripts/build_vectordb.py --source aihub --max_files 100

  # 2. AI-Hub 데이터 중간 크기 (1,000개 파일)
  python scripts/build_vectordb.py --source aihub --max_files 1000 --build_bm25

  # 3. AI-Hub 전체 데이터 (45,882개 파일 - 오래 걸림!)
  python scripts/build_vectordb.py --source aihub --build_bm25

  # 4. PostgreSQL 크롤링 데이터 (100개)
  python scripts/build_vectordb.py --source db --max_docs 100

  # 5. PostgreSQL 전체 데이터
  python scripts/build_vectordb.py --source db --build_bm25
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source",
        type=str,
        default="db",
        choices=["aihub", "db"],
        help="Data source: 'aihub' (형사법 데이터) or 'db' (PostgreSQL 크롤링 데이터)"
    )
    parser.add_argument(
        "--max_files",
        type=int,
        default=None,
        help="Maximum number of files to load from AI-Hub data (for testing)"
    )
    parser.add_argument(
        "--max_docs",
        type=int,
        default=None,
        help="Maximum number of documents to process (for testing)"
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
        build_bm25=args.build_bm25
    )
