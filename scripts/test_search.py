"""
통합 검색 테스트

환경변수 REMOTE_EMBED_BASE_URL과 REMOTE_EMBED_API_KEY가 설정되어 있어야 합니다.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv()

# .env 파일에서 설정 읽기 (REMOTE_EMBED_BASE_URL을 실제 서버 주소로 설정 필요)
EMBED_MODE = os.getenv("EMBED_MODE", "remote")
REMOTE_EMBED_URL = os.getenv("REMOTE_EMBED_BASE_URL", "https://llm.wonllmapi.uk")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "law_documents")


def test_search(query: str, top_k: int = 5):
    """검색 테스트"""
    print(f"\n🔍 Query: {query}")
    print("="*70)

    # 임베더 초기화
    if EMBED_MODE == "remote":
        from libs.rag_core.embeddings import RemoteEmbedder
        embedder = RemoteEmbedder(base_url=REMOTE_EMBED_URL)
    else:
        from libs.rag_core.embeddings import KoreanLegalEmbedder
        embedder = KoreanLegalEmbedder()

    # VectorDB 초기화
    from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB
    vectordb = QdrantVectorDB(
        url=QDRANT_URL,
        collection_name=QDRANT_COLLECTION,
        embedding_dim=embedder.get_embedding_dimension()
    )

    # 쿼리 임베딩
    query_embedding = embedder.embed_query(query)

    # 검색
    results = vectordb.search(query_embedding, top_k=top_k)

    # 결과 출력
    print(f"\n📊 Found {len(results)} results:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result['score']:.4f}")
        print(f"   Type: {result['metadata'].get('type', 'N/A')}")
        print(f"   Source: {result['metadata'].get('source', 'N/A')}")

        text = result.get('text', '')
        preview = text[:200] + '...' if len(text) > 200 else text
        print(f"   Text: {preview}\n")

    # 정리
    if hasattr(embedder, 'close'):
        embedder.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('query', type=str, help='Search query')
    parser.add_argument('--top-k', type=int, default=5, help='Number of results')

    args = parser.parse_args()
    test_search(args.query, args.top_k)
