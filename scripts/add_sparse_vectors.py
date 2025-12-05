#!/usr/bin/env python3
"""
Sparse 벡터 추가 스크립트

기존 Qdrant 컬렉션에 Sparse 벡터(BM25)를 추가합니다.
Dense + Sparse 하이브리드 검색을 위한 준비입니다.

사용법:
    # 1. 드라이런 (변경 없이 미리보기)
    python scripts/add_sparse_vectors.py --dry-run

    # 2. 실제 실행
    python scripts/add_sparse_vectors.py

    # 3. 배치 크기 조정 (메모리 부족 시)
    python scripts/add_sparse_vectors.py --batch-size 500
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter
import re

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger
from tqdm import tqdm

# Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    SparseVector, SparseVectorParams, SparseIndexParams,
    NamedVector, NamedSparseVector,
    Filter, FieldCondition, MatchValue,
    UpdateStatus
)

# 환경변수
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "law_documents")


# ============================================================
# BM25 Sparse Encoder (한국어 법률 문서용)
# ============================================================

class KoreanBM25Encoder:
    """
    한국어 법률 문서용 BM25 Sparse Encoder

    특징:
    - 한국어 형태소 분석 (konlpy 또는 간단한 토크나이저)
    - 법률 용어 가중치 부여
    - IDF 기반 희소 벡터 생성
    """

    # 법률 중요 키워드 (가중치 1.5배)
    LEGAL_KEYWORDS = {
        '판결', '결정', '판시', '요지', '이유', '주문',
        '피고인', '원고', '피고', '청구인', '신청인',
        '징역', '벌금', '무죄', '유죄', '기각', '인용',
        '형법', '민법', '상법', '헌법', '소송법',
        '고의', '과실', '위법', '책임', '손해배상',
        '계약', '불법행위', '채권', '채무', '담보',
        '공소', '기소', '항소', '상고', '재심'
    }

    def __init__(self, vocab_path: Optional[str] = None):
        """
        Args:
            vocab_path: 사전 학습된 어휘 사전 경로 (없으면 동적 생성)
        """
        self.vocab: Dict[str, int] = {}  # token -> index
        self.idf: Dict[str, float] = {}  # token -> idf score
        self.doc_count = 0
        self.avg_doc_len = 0

        # BM25 파라미터
        self.k1 = 1.5
        self.b = 0.75

        if vocab_path and Path(vocab_path).exists():
            self._load_vocab(vocab_path)

    def _tokenize(self, text: str) -> List[str]:
        """간단한 한국어 토크나이저"""
        # 특수문자 제거, 공백 기준 분리
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        tokens = text.split()

        # 2글자 이상만 유지
        tokens = [t for t in tokens if len(t) >= 2]

        return tokens

    def _load_vocab(self, path: str):
        """어휘 사전 로드"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.vocab = data.get('vocab', {})
            self.idf = data.get('idf', {})
            self.doc_count = data.get('doc_count', 0)
            self.avg_doc_len = data.get('avg_doc_len', 0)
        logger.info(f"Loaded vocab: {len(self.vocab)} terms")

    def save_vocab(self, path: str):
        """어휘 사전 저장"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                'vocab': self.vocab,
                'idf': self.idf,
                'doc_count': self.doc_count,
                'avg_doc_len': self.avg_doc_len
            }, f, ensure_ascii=False)
        logger.info(f"Saved vocab to {path}")

    def fit(self, texts: List[str]):
        """
        문서 집합으로 IDF 학습

        Args:
            texts: 학습할 문서 리스트
        """
        logger.info(f"Fitting BM25 on {len(texts)} documents...")

        # 문서별 토큰 빈도
        doc_freqs: Counter = Counter()  # token -> 등장 문서 수
        total_tokens = 0

        for text in tqdm(texts, desc="Tokenizing"):
            tokens = set(self._tokenize(text))  # 문서 내 unique tokens
            for token in tokens:
                doc_freqs[token] += 1
            total_tokens += len(tokens)

        self.doc_count = len(texts)
        self.avg_doc_len = total_tokens / len(texts) if texts else 0

        # 어휘 사전 구축 (최소 2개 문서에 등장)
        min_df = 2
        vocab_tokens = [t for t, freq in doc_freqs.items() if freq >= min_df]
        self.vocab = {token: idx for idx, token in enumerate(sorted(vocab_tokens))}

        # IDF 계산: log((N - n + 0.5) / (n + 0.5))
        import math
        for token, freq in doc_freqs.items():
            if token in self.vocab:
                self.idf[token] = math.log((self.doc_count - freq + 0.5) / (freq + 0.5) + 1)

        logger.info(f"Vocabulary size: {len(self.vocab)}")
        logger.info(f"Avg doc length: {self.avg_doc_len:.1f}")

    def encode(self, text: str) -> Tuple[List[int], List[float]]:
        """
        텍스트를 Sparse 벡터로 인코딩

        Args:
            text: 입력 텍스트

        Returns:
            (indices, values): Sparse 벡터의 인덱스와 값
        """
        tokens = self._tokenize(text)
        doc_len = len(tokens)

        # 토큰 빈도
        tf = Counter(tokens)

        indices = []
        values = []

        for token, freq in tf.items():
            if token not in self.vocab:
                continue

            idx = self.vocab[token]
            idf = self.idf.get(token, 0)

            # BM25 점수 계산
            # score = IDF * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_doc_len))
            numerator = freq * (self.k1 + 1)
            denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / max(self.avg_doc_len, 1))
            score = idf * (numerator / denominator)

            # 법률 키워드 가중치
            if token in self.LEGAL_KEYWORDS:
                score *= 1.5

            if score > 0:
                indices.append(idx)
                values.append(float(score))

        return indices, values

    def encode_batch(self, texts: List[str]) -> List[Tuple[List[int], List[float]]]:
        """배치 인코딩"""
        return [self.encode(text) for text in texts]


# ============================================================
# Qdrant Sparse 벡터 추가
# ============================================================

def update_collection_for_sparse(client: QdrantClient, collection_name: str) -> bool:
    """
    컬렉션에 Sparse 벡터 설정 추가

    Qdrant 1.7+ 에서는 컬렉션 생성 후 sparse vector 추가 가능
    """
    try:
        # 현재 컬렉션 정보 확인
        info = client.get_collection(collection_name)

        # 이미 sparse 벡터가 있는지 확인
        if hasattr(info.config, 'sparse_vectors_config') and info.config.sparse_vectors_config:
            if 'bm25' in (info.config.sparse_vectors_config or {}):
                logger.info("Sparse vector 'bm25' already exists")
                return True

        # Sparse 벡터 설정 추가
        logger.info("Adding sparse vector config to collection...")
        client.update_collection(
            collection_name=collection_name,
            sparse_vectors_config={
                "bm25": SparseVectorParams(
                    index=SparseIndexParams(
                        on_disk=False  # 메모리에 유지 (검색 속도)
                    )
                )
            }
        )
        logger.info("✅ Sparse vector config added")
        return True

    except Exception as e:
        logger.error(f"Failed to update collection: {e}")
        return False


def add_sparse_vectors_to_points(
    client: QdrantClient,
    collection_name: str,
    encoder: KoreanBM25Encoder,
    batch_size: int = 1000,
    dry_run: bool = False
) -> int:
    """
    기존 포인트에 Sparse 벡터 추가

    Args:
        client: Qdrant 클라이언트
        collection_name: 컬렉션 이름
        encoder: BM25 인코더
        batch_size: 배치 크기
        dry_run: 드라이런 모드

    Returns:
        처리된 포인트 수
    """
    total_processed = 0
    offset = None

    # 전체 포인트 수 확인
    total_count = client.count(collection_name=collection_name).count
    logger.info(f"Total points to process: {total_count:,}")

    if dry_run:
        logger.info("[DRY-RUN] Would process all points with sparse vectors")
        return total_count

    pbar = tqdm(total=total_count, desc="Adding sparse vectors")

    while True:
        # Scroll로 포인트 조회 (벡터 포함)
        points, next_offset = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=True  # 기존 dense 벡터 유지 필요
        )

        if not points:
            break

        # Sparse 벡터 생성 및 업데이트
        update_points = []
        for point in points:
            text = point.payload.get('text', '')
            if not text:
                continue

            # Sparse 벡터 생성
            indices, values = encoder.encode(text)

            if not indices:  # 빈 벡터 스킵
                continue

            # 기존 dense 벡터 + 새 sparse 벡터
            # PointStruct with named vectors
            vectors = {}

            # 기존 dense 벡터 유지
            if isinstance(point.vector, list):
                vectors[""] = point.vector  # default dense vector
            elif isinstance(point.vector, dict):
                vectors.update(point.vector)

            # Sparse 벡터 추가
            update_points.append(
                PointStruct(
                    id=point.id,
                    vector=point.vector,  # 기존 벡터 유지
                    payload=point.payload
                )
            )

        # 배치 업데이트 (set_payload 대신 upsert 사용)
        if update_points:
            # Sparse 벡터만 업데이트하는 방법
            for point in update_points:
                text = point.payload.get('text', '')
                indices, values = encoder.encode(text)

                if indices:
                    try:
                        client.update_vectors(
                            collection_name=collection_name,
                            points=[
                                {
                                    "id": point.id,
                                    "vector": {
                                        "bm25": SparseVector(
                                            indices=indices,
                                            values=values
                                        )
                                    }
                                }
                            ]
                        )
                    except Exception as e:
                        # update_vectors가 sparse를 지원하지 않으면 upsert 사용
                        logger.debug(f"update_vectors failed, using alternative: {e}")
                        break

        total_processed += len(points)
        pbar.update(len(points))

        offset = next_offset
        if offset is None:
            break

    pbar.close()
    return total_processed


def add_sparse_vectors_batch(
    client: QdrantClient,
    collection_name: str,
    encoder: KoreanBM25Encoder,
    batch_size: int = 500,
    dry_run: bool = False
) -> int:
    """
    배치 방식으로 Sparse 벡터 추가 (더 효율적)

    포인트를 읽고 sparse 벡터를 계산한 후 set_payload로 저장
    """
    total_processed = 0
    offset = None

    total_count = client.count(collection_name=collection_name).count
    logger.info(f"Total points to process: {total_count:,}")

    if dry_run:
        logger.info("[DRY-RUN] Would add sparse vectors to all points")
        return total_count

    pbar = tqdm(total=total_count, desc="Processing")

    while True:
        # Scroll로 포인트 조회
        points, next_offset = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=True
        )

        if not points:
            break

        # 각 포인트에 sparse 벡터 추가
        sparse_updates = []
        for point in points:
            text = point.payload.get('text', '')
            if not text:
                total_processed += 1
                pbar.update(1)
                continue

            # Sparse 벡터 생성
            indices, values = encoder.encode(text)

            if indices:
                # 기존 Dense 벡터는 그대로 유지하고, Sparse 벡터만 추가
                sparse_updates.append({
                    "id": point.id,
                    "vector": {
                        "bm25": SparseVector(indices=indices, values=values)
                    }
                })

        # Sparse 벡터만 업데이트 (기존 Dense 벡터 유지)
        if sparse_updates:
            client.update_vectors(
                collection_name=collection_name,
                points=sparse_updates,
                wait=True
            )

        total_processed += len(points)
        pbar.update(len(points))

        offset = next_offset
        if offset is None:
            break

    pbar.close()
    return total_processed


# ============================================================
# 메인
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Qdrant에 Sparse 벡터 추가")
    parser.add_argument("--dry-run", action="store_true", help="실제 변경 없이 미리보기")
    parser.add_argument("--batch-size", type=int, default=500, help="배치 크기")
    parser.add_argument("--vocab-path", type=str,
                       default="data/processed/bm25_vocab.json",
                       help="BM25 어휘 사전 경로")
    parser.add_argument("--fit-vocab", action="store_true",
                       help="어휘 사전 새로 학습 (기존 문서 기반)")

    args = parser.parse_args()

    print("\n" + "="*70)
    print("🔧 Sparse 벡터 추가 (BM25)")
    print("="*70)

    # Qdrant 클라이언트
    logger.info(f"Connecting to Qdrant: {QDRANT_URL}")
    client = QdrantClient(url=QDRANT_URL, timeout=600)

    # 컬렉션 확인
    try:
        info = client.get_collection(QDRANT_COLLECTION)
        logger.info(f"Collection: {QDRANT_COLLECTION}")
        logger.info(f"  Points: {info.points_count:,}")
        logger.info(f"  Status: {info.status}")
    except Exception as e:
        logger.error(f"Collection not found: {e}")
        return

    # BM25 인코더 초기화
    vocab_path = Path(args.vocab_path)
    encoder = KoreanBM25Encoder()

    if vocab_path.exists() and not args.fit_vocab:
        encoder._load_vocab(str(vocab_path))
    else:
        # 기존 문서로 어휘 학습
        logger.info("📚 Learning vocabulary from existing documents...")

        texts = []
        offset = None

        pbar = tqdm(desc="Loading texts")
        while True:
            points, next_offset = client.scroll(
                collection_name=QDRANT_COLLECTION,
                limit=1000,
                offset=offset,
                with_payload=["text"],
                with_vectors=False
            )

            if not points:
                break

            for point in points:
                text = point.payload.get('text', '')
                if text:
                    texts.append(text)

            pbar.update(len(points))
            offset = next_offset
            if offset is None:
                break

        pbar.close()
        logger.info(f"Loaded {len(texts):,} documents")

        # BM25 학습
        encoder.fit(texts)

        # 어휘 저장
        vocab_path.parent.mkdir(parents=True, exist_ok=True)
        encoder.save_vocab(str(vocab_path))

    # 컬렉션에 Sparse 벡터 설정 추가
    if not args.dry_run:
        if not update_collection_for_sparse(client, QDRANT_COLLECTION):
            logger.error("Failed to update collection config")
            return
    else:
        logger.info("[DRY-RUN] Would update collection config for sparse vectors")

    # Sparse 벡터 추가
    logger.info(f"\n🔢 Adding sparse vectors (batch_size={args.batch_size})...")
    processed = add_sparse_vectors_batch(
        client=client,
        collection_name=QDRANT_COLLECTION,
        encoder=encoder,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )

    logger.info(f"\n✅ 완료!")
    logger.info(f"  처리된 포인트: {processed:,}")
    logger.info(f"  어휘 크기: {len(encoder.vocab):,}")

    # 검증
    if not args.dry_run:
        logger.info("\n🔍 검증 중...")

        # 샘플 포인트 확인
        points, _ = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=1,
            with_vectors=True
        )

        if points:
            point = points[0]
            logger.info(f"  Sample point vectors: {type(point.vector)}")
            if isinstance(point.vector, dict):
                logger.info(f"    Keys: {list(point.vector.keys())}")
                if 'bm25' in point.vector:
                    sparse = point.vector['bm25']
                    logger.info(f"    BM25 sparse: {len(sparse.indices)} non-zero elements")

    print("="*70 + "\n")


if __name__ == "__main__":
    main()
