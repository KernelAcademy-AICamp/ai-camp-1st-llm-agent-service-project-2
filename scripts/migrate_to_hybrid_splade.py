#!/usr/bin/env python3
"""
SPLADE 기반 하이브리드 검색 마이그레이션 스크립트

기존 Qdrant 컬렉션(unnamed dense vector)을
named vector(dense) + sparse vector(SPLADE) 구조로 마이그레이션합니다.

사용법:
    # 1. 드라이런 (변경 없이 미리보기)
    python scripts/migrate_to_hybrid_splade.py --dry-run

    # 2. 실제 실행
    python scripts/migrate_to_hybrid_splade.py

    # 3. 배치 크기 조정 (메모리 부족 시)
    python scripts/migrate_to_hybrid_splade.py --batch-size 16

    # 4. 특정 개수만 테스트
    python scripts/migrate_to_hybrid_splade.py --limit 1000

마이그레이션 순서:
    1. law_documents_hybrid 새 컬렉션 생성 (named dense + sparse)
    2. 기존 데이터 복사 + SPLADE sparse 벡터 추가
    3. law_documents → law_documents_backup (백업)
    4. law_documents_hybrid → law_documents (교체)
"""

import sys
import os
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger
from tqdm import tqdm

import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

# Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    SparseVector, SparseVectorParams, SparseIndexParams,
    VectorsConfig, UpdateStatus
)

# 환경변수
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "law_documents")


# ============================================================
# SPLADE Encoder
# ============================================================

class SPLADEEncoder:
    """
    SPLADE Sparse Encoder

    SPLADE (Sparse Lexical and Dense) 모델을 사용하여
    의미 기반 sparse 벡터를 생성합니다.
    """

    def __init__(
        self,
        model_name: str = "naver/splade-cocondenser-ensembledistil",
        device: Optional[str] = None,
        max_length: int = 512
    ):
        """
        Args:
            model_name: SPLADE 모델 이름
            device: 사용할 디바이스 (None이면 자동 선택)
            max_length: 최대 토큰 길이
        """
        self.model_name = model_name
        self.max_length = max_length

        # 디바이스 설정
        if device is None:
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
        else:
            self.device = device

        logger.info(f"Loading SPLADE model: {model_name}")
        logger.info(f"Device: {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForMaskedLM.from_pretrained(model_name)
        self.model.eval()
        self.model.to(self.device)

        # 어휘 크기
        self.vocab_size = self.tokenizer.vocab_size
        logger.info(f"SPLADE loaded. Vocab size: {self.vocab_size}")

    def encode(self, text: str) -> Tuple[List[int], List[float]]:
        """
        단일 텍스트를 SPLADE sparse 벡터로 인코딩

        Args:
            text: 입력 텍스트

        Returns:
            (indices, values): sparse 벡터의 인덱스와 값
        """
        with torch.no_grad():
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=self.max_length,
                truncation=True,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            output = self.model(**inputs)
            logits = output.logits
            attention_mask = inputs["attention_mask"]

            # SPLADE 스파스 벡터 계산
            # max pooling over sequence + ReLU + log
            sparse_vec = torch.max(
                torch.log(1 + torch.relu(logits)) * attention_mask.unsqueeze(-1),
                dim=1
            )[0]
            sparse_vec = sparse_vec.squeeze()

            # Non-zero 인덱스와 값 추출
            non_zero_mask = sparse_vec > 0
            indices = torch.nonzero(non_zero_mask).squeeze(-1).cpu().tolist()
            values = sparse_vec[non_zero_mask].cpu().tolist()

            # 단일 값인 경우 리스트로 변환
            if isinstance(indices, int):
                indices = [indices]
                values = [values]

            return indices, values

    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[Tuple[List[int], List[float]]]:
        """
        배치 인코딩

        Args:
            texts: 입력 텍스트 리스트
            batch_size: 배치 크기
            show_progress: 진행률 표시 여부

        Returns:
            List of (indices, values) tuples
        """
        results = []

        iterator = range(0, len(texts), batch_size)
        if show_progress:
            iterator = tqdm(iterator, desc="SPLADE encoding", unit="batch")

        for i in iterator:
            batch_texts = texts[i:i + batch_size]

            with torch.no_grad():
                inputs = self.tokenizer(
                    batch_texts,
                    return_tensors="pt",
                    max_length=self.max_length,
                    truncation=True,
                    padding=True
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                output = self.model(**inputs)
                logits = output.logits
                attention_mask = inputs["attention_mask"]

                # SPLADE 스파스 벡터 계산 (배치)
                sparse_vecs = torch.max(
                    torch.log(1 + torch.relu(logits)) * attention_mask.unsqueeze(-1),
                    dim=1
                )[0]

                # 각 벡터에서 non-zero 추출
                for sparse_vec in sparse_vecs:
                    non_zero_mask = sparse_vec > 0
                    indices = torch.nonzero(non_zero_mask).squeeze(-1).cpu().tolist()
                    values = sparse_vec[non_zero_mask].cpu().tolist()

                    if isinstance(indices, int):
                        indices = [indices]
                        values = [values]

                    results.append((indices, values))

        return results


# ============================================================
# Migration Functions
# ============================================================

def create_hybrid_collection(
    client: QdrantClient,
    collection_name: str,
    dense_size: int = 1024,
    dry_run: bool = False
) -> bool:
    """
    하이브리드 컬렉션 생성 (named dense + sparse)
    """
    if dry_run:
        logger.info(f"[DRY-RUN] Would create collection: {collection_name}")
        logger.info(f"  - dense vector: size={dense_size}, cosine")
        logger.info(f"  - sparse vector: splade")
        return True

    try:
        # 기존 컬렉션 삭제 (있으면)
        try:
            client.delete_collection(collection_name)
            logger.info(f"Deleted existing collection: {collection_name}")
        except Exception:
            pass

        # 새 컬렉션 생성
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(
                    size=dense_size,
                    distance=Distance.COSINE
                )
            },
            sparse_vectors_config={
                "splade": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False)
                )
            }
        )

        logger.info(f"✅ Created hybrid collection: {collection_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        return False


def migrate_points(
    client: QdrantClient,
    source_collection: str,
    target_collection: str,
    encoder: SPLADEEncoder,
    batch_size: int = 32,
    limit: Optional[int] = None,
    dry_run: bool = False
) -> int:
    """
    포인트 마이그레이션 (dense + sparse 벡터)
    """
    # 전체 포인트 수 확인
    total_count = client.count(collection_name=source_collection).count
    if limit:
        total_count = min(total_count, limit)

    logger.info(f"Total points to migrate: {total_count:,}")

    if dry_run:
        logger.info(f"[DRY-RUN] Would migrate {total_count:,} points")
        return total_count

    processed = 0
    offset = None

    pbar = tqdm(total=total_count, desc="Migrating", unit="points")

    while processed < total_count:
        # 배치로 포인트 조회
        fetch_limit = min(batch_size, total_count - processed)

        points, next_offset = client.scroll(
            collection_name=source_collection,
            limit=fetch_limit,
            offset=offset,
            with_payload=True,
            with_vectors=True
        )

        if not points:
            break

        # 텍스트 추출
        texts = []
        valid_points = []
        for point in points:
            text = point.payload.get("text", "")
            if text:
                texts.append(text)
                valid_points.append(point)

        if not texts:
            processed += len(points)
            pbar.update(len(points))
            offset = next_offset
            continue

        # SPLADE 인코딩 (배치)
        sparse_vectors = encoder.encode_batch(texts, batch_size=batch_size)

        # 새 포인트 생성
        new_points = []
        for point, (indices, values) in zip(valid_points, sparse_vectors):
            # 기존 dense 벡터
            dense_vector = point.vector if isinstance(point.vector, list) else point.vector.get("", point.vector)

            new_points.append(
                PointStruct(
                    id=point.id,
                    vector={
                        "dense": dense_vector,
                        "splade": SparseVector(indices=indices, values=values)
                    },
                    payload=point.payload
                )
            )

        # 새 컬렉션에 삽입
        if new_points:
            client.upsert(
                collection_name=target_collection,
                points=new_points,
                wait=True
            )

        processed += len(points)
        pbar.update(len(points))

        offset = next_offset
        if offset is None:
            break

    pbar.close()
    return processed


def rename_collections(
    client: QdrantClient,
    original: str,
    backup: str,
    new_hybrid: str,
    dry_run: bool = False
) -> bool:
    """
    컬렉션 이름 변경 (백업 및 교체)

    순서:
    1. original → backup (백업)
    2. new_hybrid → original (교체)
    """
    if dry_run:
        logger.info(f"[DRY-RUN] Would rename collections:")
        logger.info(f"  1. {original} → {backup}")
        logger.info(f"  2. {new_hybrid} → {original}")
        return True

    try:
        # Qdrant는 직접 rename을 지원하지 않으므로
        # alias를 사용하거나 데이터를 복사해야 함
        # 여기서는 간단히 기존 컬렉션을 삭제하고 새 이름으로 복사

        # 1. 기존 컬렉션 → 백업 (이미 데이터가 있으므로 그대로 둠)
        # Qdrant에서는 컬렉션 이름 변경이 불가하므로
        # 기존 컬렉션을 backup 이름으로 alias 설정하거나
        # 그냥 두고 새 컬렉션을 사용

        logger.info(f"📦 Original collection '{original}' will be kept as backup")
        logger.info(f"📦 New hybrid collection is '{new_hybrid}'")
        logger.info(f"")
        logger.info(f"⚠️  Qdrant doesn't support direct rename.")
        logger.info(f"   To use the new collection, update your code to use:")
        logger.info(f"   QDRANT_COLLECTION={new_hybrid}")
        logger.info(f"")
        logger.info(f"   Or manually:")
        logger.info(f"   1. Delete '{original}' collection")
        logger.info(f"   2. Recreate '{original}' with hybrid config")
        logger.info(f"   3. Copy data from '{new_hybrid}'")

        return True

    except Exception as e:
        logger.error(f"Failed to rename collections: {e}")
        return False


def verify_migration(
    client: QdrantClient,
    collection_name: str
) -> bool:
    """
    마이그레이션 검증
    """
    try:
        info = client.get_collection(collection_name)
        logger.info(f"\n🔍 Verification: {collection_name}")
        logger.info(f"  Points: {info.points_count:,}")
        logger.info(f"  Status: {info.status}")

        # 샘플 포인트 확인
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=1,
            with_vectors=True
        )

        if points:
            point = points[0]
            if isinstance(point.vector, dict):
                logger.info(f"  Vector keys: {list(point.vector.keys())}")

                if "dense" in point.vector:
                    dense = point.vector["dense"]
                    logger.info(f"  Dense vector dim: {len(dense)}")

                if "splade" in point.vector:
                    sparse = point.vector["splade"]
                    logger.info(f"  SPLADE non-zero elements: {len(sparse.indices)}")
                    logger.info(f"  ✅ Hybrid structure verified!")
                    return True

        logger.warning("Could not verify hybrid structure")
        return False

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="SPLADE 기반 하이브리드 검색 마이그레이션"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="실제 변경 없이 미리보기"
    )
    parser.add_argument(
        "--batch-size", type=int, default=32,
        help="SPLADE 인코딩 배치 크기 (기본: 32)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="마이그레이션할 최대 문서 수 (테스트용)"
    )
    parser.add_argument(
        "--source", type=str, default=QDRANT_COLLECTION,
        help=f"원본 컬렉션 (기본: {QDRANT_COLLECTION})"
    )
    parser.add_argument(
        "--target", type=str, default=None,
        help="대상 컬렉션 (기본: {source}_hybrid)"
    )
    parser.add_argument(
        "--device", type=str, default=None,
        choices=["cpu", "cuda", "mps"],
        help="SPLADE 디바이스 (기본: 자동)"
    )

    args = parser.parse_args()

    source_collection = args.source
    target_collection = args.target or f"{source_collection}_hybrid"

    print("\n" + "=" * 70)
    print("🚀 SPLADE 기반 하이브리드 검색 마이그레이션")
    print("=" * 70)
    print(f"  Source: {source_collection}")
    print(f"  Target: {target_collection}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Limit: {args.limit or 'All'}")
    print(f"  Dry run: {args.dry_run}")
    print("=" * 70 + "\n")

    # Qdrant 클라이언트
    logger.info(f"Connecting to Qdrant: {QDRANT_URL}")
    client = QdrantClient(url=QDRANT_URL, timeout=600)

    # 원본 컬렉션 확인
    try:
        info = client.get_collection(source_collection)
        logger.info(f"Source collection: {source_collection}")
        logger.info(f"  Points: {info.points_count:,}")
        logger.info(f"  Status: {info.status}")

        # Dense 벡터 크기 확인
        vectors_config = info.config.params.vectors
        if hasattr(vectors_config, "size"):
            dense_size = vectors_config.size
        else:
            # Named vectors인 경우
            dense_size = 1024  # 기본값
        logger.info(f"  Dense size: {dense_size}")

    except Exception as e:
        logger.error(f"Source collection not found: {e}")
        return

    # SPLADE 인코더 초기화
    logger.info("\n📦 Loading SPLADE encoder...")
    start_time = time.time()
    encoder = SPLADEEncoder(device=args.device)
    logger.info(f"  Loaded in {time.time() - start_time:.1f}s")

    # 1. 하이브리드 컬렉션 생성
    logger.info(f"\n📁 Creating hybrid collection: {target_collection}")
    if not create_hybrid_collection(
        client, target_collection, dense_size, dry_run=args.dry_run
    ):
        logger.error("Failed to create hybrid collection")
        return

    # 2. 포인트 마이그레이션
    logger.info(f"\n🔄 Migrating points...")
    start_time = time.time()
    processed = migrate_points(
        client=client,
        source_collection=source_collection,
        target_collection=target_collection,
        encoder=encoder,
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run
    )
    elapsed = time.time() - start_time

    logger.info(f"\n✅ Migration complete!")
    logger.info(f"  Processed: {processed:,} points")
    logger.info(f"  Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    logger.info(f"  Speed: {processed/elapsed:.1f} points/sec")

    # 3. 검증
    if not args.dry_run:
        verify_migration(client, target_collection)

    # 4. 다음 단계 안내
    print("\n" + "=" * 70)
    print("📌 다음 단계")
    print("=" * 70)
    print(f"""
1. 새 하이브리드 컬렉션 확인:
   - Collection: {target_collection}
   - Vectors: dense (1024) + splade (sparse)

2. 검색 코드 업데이트:
   - 환경변수: QDRANT_COLLECTION={target_collection}
   - 또는 코드에서 하이브리드 검색 사용

3. 기존 컬렉션 정리 (선택):
   - {source_collection}: 원본 (백업으로 유지 권장)
   - {target_collection}: 새 하이브리드

4. 하이브리드 검색 예시:
   client.query_points(
       collection_name="{target_collection}",
       prefetch=[
           Prefetch(query=dense_vector, using="dense", limit=100),
           Prefetch(query=SparseVector(indices, values), using="splade", limit=100),
       ],
       query=FusionQuery(fusion=Fusion.RRF),
       limit=10
   )
""")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
