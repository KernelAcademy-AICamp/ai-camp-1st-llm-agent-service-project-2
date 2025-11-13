"""
벡터 데이터베이스 구축 스크립트

사용법:
    python scripts/build_vectordb.py --db_type chroma --text_column text
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import argparse
from loguru import logger
from configs.config import config
from backend.core.data.loader import LawDataLoader
from backend.core.data.preprocessor import LawTextPreprocessor
from backend.core.embeddings.embedder import KoreanLegalEmbedder
from backend.core.embeddings.vectordb import create_vector_db
from backend.core.retrieval.bm25_index import BM25Index


def main(args):
    logger.info("Starting vector database construction...")
    logger.info(f"학습 목적: 작은 데이터셋으로 테스트 후 전체 데이터로 확장")

    # 1. Load data
    logger.info("Step 1: Loading data...")
    loader = LawDataLoader(config.raw_data_dir)

    # max_files 파라미터로 테스트용 데이터 로딩
    # 이유: 40,782개 전체 파일 로딩은 시간이 오래 걸림
    df = loader.load_source_data(max_files=args.max_files)

    if df.empty:
        logger.error("No data found! Please check your data directory.")
        return

    logger.info(f"Loaded {len(df)} rows of text data")
    stats = loader.get_data_statistics(df)
    logger.info(f"Data statistics: {stats}")

    # 2. Preprocess and chunk
    logger.info("Step 2: Preprocessing and chunking...")
    preprocessor = LawTextPreprocessor(
        chunk_size=config.rag.chunk_size,
        chunk_overlap=config.rag.chunk_overlap
    )

    # Determine text column
    text_column = args.text_column
    if text_column not in df.columns:
        # Try to auto-detect
        possible_columns = ['text', 'content', 'document', '내용', '본문']
        for col in possible_columns:
            if col in df.columns:
                text_column = col
                logger.info(f"Auto-detected text column: {text_column}")
                break

        if text_column not in df.columns:
            logger.error(f"Text column '{text_column}' not found in dataframe. Available columns: {df.columns.tolist()}")
            return

    chunks = preprocessor.process_dataframe(df, text_column=text_column)
    texts, metadatas = preprocessor.prepare_for_embedding(chunks)

    logger.info(f"Created {len(chunks)} chunks from {len(df)} documents")

    # Limit for testing if specified
    if args.max_docs and args.max_docs < len(texts):
        logger.info(f"Limiting to {args.max_docs} documents for testing")
        texts = texts[:args.max_docs]
        metadatas = metadatas[:args.max_docs]

    # 3. Generate embeddings
    logger.info("Step 3: Generating embeddings...")
    embedder = KoreanLegalEmbedder(
        model_name=config.embedding.model_name,
        device=config.embedding.device,
        batch_size=config.embedding.batch_size
    )

    embeddings = embedder.embed_documents(texts, show_progress=True)
    logger.info(f"Generated embeddings with shape: {embeddings.shape}")

    # 4. Build vector database
    logger.info(f"Step 4: Building {args.db_type} vector database...")

    if args.db_type == "chroma":
        vectordb = create_vector_db(
            "chroma",
            persist_directory=config.vectordb.chroma_persist_dir,
            collection_name=config.vectordb.collection_name
        )
    elif args.db_type == "faiss":
        vectordb = create_vector_db(
            "faiss",
            index_path=config.vectordb.faiss_index_path,
            dimension=embedder.get_embedding_dimension()
        )
    else:
        raise ValueError(f"Unknown db_type: {args.db_type}")

    # Add documents
    vectordb.add_documents(texts, embeddings, metadatas)

    # Save
    vectordb.save()

    logger.info(f"Vector database built successfully!")
    logger.info(f"Total documents in DB: {vectordb.get_count()}")

    # 5. Build BM25 index (for Hybrid Search)
    if args.build_bm25:
        logger.info("Step 5: Building BM25 index for Hybrid Search...")
        bm25_index = BM25Index(
            k1=config.rag.bm25_k1,
            b=config.rag.bm25_b
        )

        # Add documents (same texts used for vector DB)
        bm25_index.add_documents(texts, metadatas)

        # Save
        bm25_index.save(config.vectordb.bm25_index_path)

        logger.info(f"BM25 index built successfully!")
        logger.info(f"Total documents in BM25 index: {bm25_index.get_count()}")
    else:
        logger.info("Step 5: Skipping BM25 index (use --build_bm25 to enable)")
        bm25_index = None

    # Test search
    if args.test_query:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing search with query: '{args.test_query}'")
        logger.info(f"{'='*80}")

        # Semantic Search
        logger.info("\n[Semantic Search Results]")
        query_embedding = embedder.embed_query(args.test_query)
        semantic_results = vectordb.search(query_embedding, top_k=3)

        for i, result in enumerate(semantic_results):
            logger.info(f"\n--- Semantic Result {i+1} (score: {result['score']:.4f}) ---")
            logger.info(f"Text: {result['text'][:200]}...")
            logger.info(f"Metadata: {result['metadata']}")

        # BM25 Search (if index was built)
        if bm25_index:
            logger.info("\n[BM25 Search Results]")
            bm25_results = bm25_index.search(args.test_query, top_k=3)

            for i, result in enumerate(bm25_results):
                logger.info(f"\n--- BM25 Result {i+1} (score: {result['score']:.4f}) ---")
                logger.info(f"Text: {result['text'][:200]}...")
                logger.info(f"Metadata: {result['metadata']}")

            # Query analysis
            logger.info("\n[Query Analysis]")
            analysis = bm25_index.analyze_query(args.test_query)
            logger.info(f"Tokens: {analysis['tokens']}")
            logger.info(f"Top keywords: {analysis['top_keywords']}")
            logger.info(f"Has statute reference: {analysis['has_statute_ref']}")
            logger.info(f"Has case number: {analysis['has_case_number']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build vector database from law data",
        epilog="""
학습 목적 사용 예시:
  # 1. 빠른 테스트 (10개 파일만)
  python scripts/build_vectordb.py --max_files 10 --max_docs 100

  # 2. 중간 크기 테스트 (100개 파일)
  python scripts/build_vectordb.py --max_files 100 --max_docs 1000

  # 3. 전체 데이터 (40,782개 파일 - 오래 걸림!)
  python scripts/build_vectordb.py
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--db_type", type=str, default="chroma", choices=["chroma", "faiss"],
                       help="Vector database type")
    parser.add_argument("--build_bm25", action="store_true",
                       help="Build BM25 index for Hybrid Search (recommended)")
    parser.add_argument("--text_column", type=str, default="text",
                       help="Name of the text column in the CSV")
    parser.add_argument("--max_files", type=int, default=None,
                       help="Maximum number of CSV files to load (for testing). Default: all 40,782 files")
    parser.add_argument("--max_docs", type=int, default=None,
                       help="Maximum number of documents to embed (for testing)")
    parser.add_argument("--test_query", type=str, default="절도죄의 구성요건은 무엇인가요?",
                       help="Test query after building DB")

    args = parser.parse_args()
    main(args)
