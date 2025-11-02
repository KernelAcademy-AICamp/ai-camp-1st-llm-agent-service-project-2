"""
학습 목적: 각 컴포넌트를 단계별로 테스트하여 문제 파악

이 스크립트는 RAG 시스템의 각 단계를 독립적으로 테스트합니다:
1. 데이터 로딩
2. 전처리 및 청킹
3. 임베딩 모델 로드
4. 벡터 DB 생성

각 단계에서 시간이 얼마나 걸리는지, 어디서 문제가 발생하는지 확인할 수 있습니다.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from configs.config import config
from src.data.loader import LawDataLoader
from src.data.preprocessor import LawTextPreprocessor
from src.embeddings.embedder import KoreanLegalEmbedder

def test_step_1_data_loading():
    """Step 1: 데이터 로딩 테스트"""
    logger.info("=" * 60)
    logger.info("Step 1: 데이터 로딩 테스트")
    logger.info("=" * 60)

    loader = LawDataLoader(config.raw_data_dir)
    logger.info(f"데이터 경로: {config.raw_data_dir}")

    # 10개 파일만 로드
    df = loader.load_source_data(max_files=10)

    if df.empty:
        logger.error("❌ 데이터 로딩 실패!")
        return None

    logger.info(f"✅ 데이터 로딩 성공!")
    logger.info(f"   - 로드된 행 수: {len(df)}")
    logger.info(f"   - 컬럼: {df.columns.tolist()}")
    logger.info(f"   - 샘플 텍스트: {df['text'].iloc[0][:100]}...")

    return df

def test_step_2_preprocessing(df):
    """Step 2: 전처리 및 청킹 테스트"""
    if df is None or df.empty:
        logger.error("❌ Step 1을 먼저 통과해야 합니다")
        return None

    logger.info("\n" + "=" * 60)
    logger.info("Step 2: 전처리 및 청킹 테스트")
    logger.info("=" * 60)

    preprocessor = LawTextPreprocessor(
        chunk_size=config.rag.chunk_size,
        chunk_overlap=config.rag.chunk_overlap
    )

    logger.info(f"청킹 설정: size={config.rag.chunk_size}, overlap={config.rag.chunk_overlap}")

    # 청킹
    chunks = preprocessor.process_dataframe(df, text_column='text')
    texts, metadatas = preprocessor.prepare_for_embedding(chunks)

    # 테스트용으로 100개만 사용
    texts = texts[:100]
    metadatas = metadatas[:100]

    logger.info(f"✅ 전처리 성공!")
    logger.info(f"   - 생성된 청크 수: {len(texts)}")
    logger.info(f"   - 첫 번째 청크: {texts[0][:100]}...")

    return texts, metadatas

def test_step_3_embedding_model():
    """Step 3: 임베딩 모델 로드 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("Step 3: 임베딩 모델 로드 테스트")
    logger.info("=" * 60)

    logger.info(f"모델: {config.embedding.model_name}")
    logger.info(f"디바이스: {config.embedding.device}")
    logger.info("⚠️  주의: 모델이 없으면 다운로드되므로 시간이 걸릴 수 있습니다 (약 1-2분)")

    try:
        embedder = KoreanLegalEmbedder(
            model_name=config.embedding.model_name,
            device=config.embedding.device,
            batch_size=8  # 작은 배치 사이즈로 테스트
        )

        logger.info(f"✅ 임베딩 모델 로드 성공!")
        logger.info(f"   - 임베딩 차원: {embedder.get_embedding_dimension()}")

        # 간단한 테스트
        test_embedding = embedder.embed_query("테스트 쿼리")
        logger.info(f"   - 테스트 임베딩 shape: {test_embedding.shape}")

        return embedder

    except Exception as e:
        logger.error(f"❌ 임베딩 모델 로드 실패: {e}")
        return None

def test_step_4_embedding_generation(embedder, texts):
    """Step 4: 실제 임베딩 생성 테스트"""
    if embedder is None or not texts:
        logger.error("❌ Step 3을 먼저 통과해야 합니다")
        return None

    logger.info("\n" + "=" * 60)
    logger.info("Step 4: 임베딩 생성 테스트")
    logger.info("=" * 60)

    logger.info(f"임베딩 생성 시작: {len(texts)}개 텍스트")

    try:
        embeddings = embedder.embed_documents(texts[:50], show_progress=True)

        logger.info(f"✅ 임베딩 생성 성공!")
        logger.info(f"   - Embeddings shape: {embeddings.shape}")

        return embeddings

    except Exception as e:
        logger.error(f"❌ 임베딩 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    logger.info("🚀 RAG 시스템 컴포넌트 단계별 테스트 시작\n")

    # Step 1
    df = test_step_1_data_loading()
    if df is None:
        return

    # Step 2
    result = test_step_2_preprocessing(df)
    if result is None:
        return
    texts, metadatas = result

    # Step 3
    embedder = test_step_3_embedding_model()
    if embedder is None:
        return

    # Step 4
    embeddings = test_step_4_embedding_generation(embedder, texts)
    if embeddings is None:
        return

    logger.info("\n" + "=" * 60)
    logger.info("🎉 모든 컴포넌트 테스트 통과!")
    logger.info("=" * 60)
    logger.info("이제 전체 벡터 DB 구축을 실행할 수 있습니다:")
    logger.info("  python scripts/build_vectordb.py --max_files 10 --max_docs 100")

if __name__ == "__main__":
    main()
