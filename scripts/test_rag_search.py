"""
간단한 RAG 검색 테스트 스크립트

학습 목적: 벡터 DB에서 검색만 테스트 (LLM 없이)
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

def test_queries():
    """여러 쿼리로 검색 테스트"""

    test_cases = [
        "절도죄의 구성요건은 무엇인가요?",
        "정당방위가 성립하는 요건은?",
        "사기죄와 횡령죄의 차이점은?",
        "업무상과실치사죄의 형량은?",
    ]

    print("=" * 60)
    print("🔍 RAG 검색 테스트")
    print("=" * 60)
    print()

    # 1. 임베딩 모델 로드
    print("Step 1: 임베딩 모델 로드 중...")
    embedder = KoreanLegalEmbedder(
        model_name=config.embedding.model_name,
        device=config.embedding.device
    )
    print(f"✅ 모델 로드 완료: {config.embedding.model_name}\n")

    # 2. 벡터 DB 로드
    print("Step 2: 벡터 DB 로드 중...")
    vectordb = create_vector_db(
        "chroma",
        persist_directory=config.vectordb.chroma_persist_dir,
        collection_name=config.vectordb.collection_name
    )

    doc_count = vectordb.get_count()
    print(f"✅ 벡터 DB 로드 완료: {doc_count}개 문서\n")

    if doc_count == 0:
        print("❌ 벡터 DB가 비어있습니다!")
        print("먼저 벡터 DB를 구축하세요:")
        print("  python scripts/build_vectordb.py --max_files 10 --max_docs 100")
        return

    # 3. Retriever 생성
    print("Step 3: Retriever 생성...")
    retriever = LegalDocumentRetriever(
        vectordb=vectordb,
        embedder=embedder,
        top_k=3
    )
    print(f"✅ Retriever 생성 완료\n")

    # 4. 테스트 쿼리 실행
    print("=" * 60)
    print("🧪 테스트 쿼리 실행")
    print("=" * 60)
    print()

    for i, query in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"Query {i}: {query}")
        print(f"{'=' * 60}\n")

        # 검색 실행
        results = retriever.retrieve(query, top_k=3)

        if not results:
            print("❌ 검색 결과 없음")
            continue

        print(f"✅ {len(results)}개 문서 검색됨:\n")

        # 결과 출력
        for j, doc in enumerate(results, 1):
            score = doc.get('score', 0)
            text = doc.get('text', '')
            metadata = doc.get('metadata', {})

            source_type = metadata.get('source_type', 'unknown')
            file_name = metadata.get('file_name', 'unknown')

            print(f"[결과 {j}] (유사도: {score:.4f})")
            print(f"  출처: {source_type} - {file_name}")
            print(f"  내용: {text[:150]}...")
            print()

    print("\n" + "=" * 60)
    print("🎉 모든 테스트 완료!")
    print("=" * 60)
    print()
    print("다음 단계:")
    print("  1. LLM과 연동하여 실제 답변 생성:")
    print("     python scripts/chat_cli.py --show_sources")
    print()
    print("  2. Constitutional AI 챗봇 실행:")
    print("     python src/ui/app.py")

if __name__ == "__main__":
    try:
        test_queries()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        print("\n트러블슈팅:")
        print("  1. 벡터 DB가 구축되었는지 확인")
        print("  2. TROUBLESHOOTING.md 참조")
