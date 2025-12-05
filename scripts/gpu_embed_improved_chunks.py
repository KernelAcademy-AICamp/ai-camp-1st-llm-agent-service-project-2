#!/usr/bin/env python3
"""
GPU 서버에서 개선된 청크 임베딩 + Qdrant 저장 스크립트

Mac에서 selective_rechunk.py --skip-embed로 생성된 chunks_improved.json을
Ubuntu GPU 서버로 전송 후 이 스크립트를 실행합니다.

사용법 (Ubuntu GPU 서버에서):
    cd ~/embedding_work
    source venv/bin/activate
    python gpu_embed_improved_chunks.py

    # 배치 크기 조정 (GPU 메모리 부족 시)
    python gpu_embed_improved_chunks.py --batch-size 32
"""

import json
import time
import hashlib
import argparse
from datetime import datetime
from tqdm import tqdm
import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# ===== 기본 설정 =====
DEFAULT_CHUNKS_PATH = "chunks_improved.json"
MODEL_NAME = "dragonkue/snowflake-arctic-embed-l-v2.0-ko"
COLLECTION_NAME = "law_documents"
DEFAULT_BATCH_SIZE = 32  # 긴 청크용 배치 크기 (OOM 방지)
MAX_TEXT_LENGTH = 1000  # 텍스트 최대 길이 (약 500토큰, 모델 max_length=512 고려)
QDRANT_PORT = 8633  # Ubuntu에서 사용하는 포트


def main():
    parser = argparse.ArgumentParser(description="GPU 임베딩 + Qdrant 저장")
    parser.add_argument("--chunks-path", type=str, default=DEFAULT_CHUNKS_PATH,
                       help=f"청크 파일 경로 (기본: {DEFAULT_CHUNKS_PATH})")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                       help=f"배치 크기 (기본: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--port", type=int, default=QDRANT_PORT,
                       help=f"Qdrant 포트 (기본: {QDRANT_PORT})")
    parser.add_argument("--append", action="store_true",
                       help="기존 컬렉션에 추가 (삭제하지 않음)")

    args = parser.parse_args()

    # 타이밍 메트릭
    timing_metrics = {}
    total_start = time.time()

    print("\n" + "="*60)
    print(" 🚀 GPU 임베딩 + Qdrant 저장 (개선된 청크)")
    print("="*60)

    # ===== 1. 청크 로드 =====
    print(f"\n📂 Step 1: 청크 로드 중... ({args.chunks_path})")
    load_start = time.time()

    with open(args.chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"   총 청크 개수: {len(chunks):,}개")

    # 형식 변환: {"content": ..., "metadata": ...} → texts, metadatas
    texts = [chunk["content"] for chunk in chunks]
    metadatas = [chunk.get("metadata", {}) for chunk in chunks]

    timing_metrics["data_load_time"] = time.time() - load_start
    print(f"✅ 청크 로드 완료: {timing_metrics['data_load_time']:.2f}s")

    # ===== 2. 임베딩 모델 로드 =====
    print(f"\n🤖 Step 2: 임베딩 모델 로드... ({MODEL_NAME})")
    embed_init_start = time.time()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"   사용 디바이스: {device}")

    if device == "cuda":
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    model = SentenceTransformer(MODEL_NAME, device=device)

    # 임베딩 차원 확인
    test_emb = model.encode(["테스트"], convert_to_numpy=True)
    embedding_dim = test_emb.shape[1]
    print(f"   임베딩 차원: {embedding_dim}")

    timing_metrics["embed_init_time"] = time.time() - embed_init_start
    print(f"✅ 모델 로드 완료: {timing_metrics['embed_init_time']:.2f}s")

    # ===== 3. Qdrant 연결 및 컬렉션 설정 =====
    print(f"\n🗄️ Step 3: Qdrant 연결 중... (포트: {args.port})")
    vectordb_init_start = time.time()

    client = QdrantClient(url=f"http://localhost:{args.port}", timeout=300)

    # 컬렉션 확인
    collections = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME in collections:
        if args.append:
            print(f"   기존 컬렉션 '{COLLECTION_NAME}' 유지 (--append 모드)")
            existing_count = client.get_collection(COLLECTION_NAME).points_count
            print(f"   기존 포인트: {existing_count:,}개")
        else:
            print(f"   기존 컬렉션 '{COLLECTION_NAME}' 삭제 중...")
            client.delete_collection(COLLECTION_NAME)
            print(f"   새 컬렉션 '{COLLECTION_NAME}' 생성 중...")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
            )
    else:
        print(f"   새 컬렉션 '{COLLECTION_NAME}' 생성 중...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
        )

    timing_metrics["vectordb_init_time"] = time.time() - vectordb_init_start
    print(f"✅ Qdrant 초기화 완료: {timing_metrics['vectordb_init_time']:.2f}s")

    # ===== 4. 임베딩 + 업서트 =====
    print(f"\n⚡ Step 4: 임베딩 + 업서트 진행 중... ({len(texts):,}개 문서)")
    print(f"   배치 크기: {args.batch_size}")
    embed_start = time.time()

    total = len(texts)
    batch_size = args.batch_size

    for start in tqdm(range(0, total, batch_size), desc="Embedding & Uploading"):
        end = min(start + batch_size, total)

        batch_texts_orig = texts[start:end]  # 원본 저장용
        batch_metas = metadatas[start:end]

        # 긴 텍스트 truncate (모델 max_length 초과 방지, 임베딩용)
        batch_texts_embed = [t[:MAX_TEXT_LENGTH] if len(t) > MAX_TEXT_LENGTH else t for t in batch_texts_orig]

        # 배치 단위로 임베딩 (원본 스크립트와 동일)
        batch_embs = model.encode(
            batch_texts_embed,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        points = []
        for idx, (text, emb, meta) in enumerate(
            zip(batch_texts_orig, batch_embs, batch_metas), start=start  # 원본 텍스트 저장
        ):
            # document_id 생성 (QdrantVectorDB.add_documents()와 동일한 로직)
            if "document_id" in meta:
                doc_id = meta["document_id"]
            else:
                source = meta.get("source", "unknown")
                chunk_id = meta.get("chunk_id", idx)
                doc_id = f"{source}_{chunk_id}"

            # 메타데이터 정리
            cleaned = {}
            for key, value in meta.items():
                if isinstance(value, (str, int, float, bool)):
                    cleaned[key] = value
                elif value is not None:
                    cleaned[key] = str(value)

            # text와 document_id를 payload에 포함
            cleaned["text"] = text
            cleaned["document_id"] = doc_id

            # 결정적 ID 생성 (해시 기반)
            numeric_id = int(hashlib.md5(doc_id.encode()).hexdigest()[:16], 16)

            points.append(
                PointStruct(
                    id=numeric_id,
                    vector=emb.tolist(),
                    payload=cleaned,
                )
            )

        # Qdrant에 업서트
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    timing_metrics["embedding_time"] = time.time() - embed_start
    timing_metrics["docs_per_second"] = total / timing_metrics["embedding_time"]
    print(f"✅ 임베딩 + 저장 완료: {timing_metrics['embedding_time']:.2f}s")
    print(f"   처리 속도: {timing_metrics['docs_per_second']:.2f} docs/sec")

    # ===== 5. 검증 =====
    print("\nℹ️ Step 5: 컬렉션 정보 확인 중...")
    info = client.get_collection(COLLECTION_NAME)
    final_count = info.points_count

    # ===== 6. 테스트 검색 =====
    print("\n🔍 Step 6: 테스트 검색...")
    test_queries = ["음주운전 처벌", "사기죄 고의", "정당방위"]

    for query in test_queries:
        try:
            query_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
            results = client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_emb.tolist(),
                limit=3
            )
            print(f"   ✓ Query: '{query}' -> {len(results)} results")
            if results:
                print(f"     Top score: {results[0].score:.4f}")
                # 결과 미리보기
                top_text = results[0].payload.get('text', '')[:100]
                print(f"     Preview: {top_text}...")
        except Exception as e:
            print(f"   ✗ Query failed: {e}")

    # ===== 7. 메트릭 저장 =====
    total_time = time.time() - total_start
    timing_metrics["total_time"] = total_time
    timing_metrics["total_documents"] = final_count
    timing_metrics["timestamp"] = datetime.now().isoformat()
    timing_metrics["embedding_dim"] = embedding_dim
    timing_metrics["model_name"] = MODEL_NAME
    timing_metrics["collection_name"] = COLLECTION_NAME
    timing_metrics["batch_size"] = args.batch_size
    timing_metrics["device"] = device

    metrics_path = "embedding_improved_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(timing_metrics, f, indent=2, ensure_ascii=False)

    # ===== 요약 =====
    print("\n" + "="*60)
    print(" 📊 Performance Metrics Summary")
    print("="*60)
    print(f"  Model:                   {MODEL_NAME}")
    print(f"  Collection:              {COLLECTION_NAME}")
    print(f"  Device:                  {device}")
    print(f"  Batch Size:              {args.batch_size}")
    print(f"  Data Load Time:          {timing_metrics['data_load_time']:>8.2f}s")
    print(f"  Model Init Time:         {timing_metrics['embed_init_time']:>8.2f}s")
    print(f"  Embedding Time:          {timing_metrics['embedding_time']:>8.2f}s")
    print(f"  {'─'*60}")
    print(f"  TOTAL TIME:              {total_time:>8.2f}s ({total_time/60:.1f}분)")
    print(f"  Total Documents:         {final_count:>8,}")
    print(f"  Processing Speed:        {timing_metrics['docs_per_second']:>8.2f} docs/sec")
    print("="*60)
    print(f"\n✅ 완료! 저장된 포인트 수: {final_count:,}개")
    print(f"   메트릭 저장: {metrics_path}")

    print("\n📤 다음 단계:")
    print("   1. sudo docker stop qdrant_embed")
    print("   2. tar -czvf qdrant_storage.tar.gz qdrant_storage/")
    print("   3. Mac에서: scp ai-ubuntu:~/embedding_work/qdrant_storage.tar.gz .")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
