#!/usr/bin/env python3
"""
개선된 판결문/결정례 포인트를 기존 Qdrant에 추가

GPU 서버에서 임베딩된 원천_판결문/원천_결정례 데이터를
Mac의 기존 Qdrant 컬렉션에 추가합니다.

현재 Mac Qdrant에는 원천_판결문/원천_결정례가 없으므로
삭제 없이 단순 추가만 수행합니다.

사용법:
    # 1. dry-run (실제 변경 없이 미리보기)
    python scripts/merge_improved_points.py --dry-run

    # 2. 실제 실행
    python scripts/merge_improved_points.py

    # 3. 배치 크기 조정 (메모리 부족 시)
    python scripts/merge_improved_points.py --batch-size 200
"""

import json
import os
import argparse
from pathlib import Path
from collections import Counter
from tqdm import tqdm

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

# 기본 설정
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "law_documents")
DEFAULT_POINTS_FILE = "data/improved_points.json"
DEFAULT_BATCH_SIZE = 500


def main():
    parser = argparse.ArgumentParser(description="개선된 포인트 병합")
    parser.add_argument("--points-file", type=str, default=DEFAULT_POINTS_FILE,
                       help=f"포인트 파일 경로 (기본: {DEFAULT_POINTS_FILE})")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                       help=f"배치 크기 (기본: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--dry-run", action="store_true",
                       help="실제 변경 없이 미리보기")
    parser.add_argument("--qdrant-url", type=str, default=QDRANT_URL,
                       help=f"Qdrant URL (기본: {QDRANT_URL})")
    parser.add_argument("--collection", type=str, default=COLLECTION_NAME,
                       help=f"컬렉션 이름 (기본: {COLLECTION_NAME})")

    args = parser.parse_args()

    print("\n" + "="*60)
    print(" 🔄 개선된 판결문/결정례 포인트 추가")
    print("="*60)
    print(f"  Qdrant URL: {args.qdrant_url}")
    print(f"  Collection: {args.collection}")
    print(f"  Points file: {args.points_file}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Dry-run: {args.dry_run}")
    print("="*60 + "\n")

    # 1. Qdrant 연결
    print("📡 Step 1: Qdrant 연결 중...")
    client = QdrantClient(url=args.qdrant_url, timeout=600)

    try:
        info = client.get_collection(args.collection)
        print(f"  ✓ 현재 포인트 수: {info.points_count:,}개")
    except Exception as e:
        print(f"  ✗ 컬렉션 연결 실패: {e}")
        return

    before_count = info.points_count

    # 2. 포인트 파일 로드
    print(f"\n📂 Step 2: 포인트 파일 로드 중... ({args.points_file})")

    points_path = Path(args.points_file)
    if not points_path.exists():
        print(f"  ✗ 파일이 없습니다: {points_path}")
        print("  힌트: GPU 서버에서 가져온 파일을 먼저 압축 해제하세요.")
        print("        gunzip data/improved_points.json.gz")
        return

    with open(points_path, 'r', encoding='utf-8') as f:
        new_points = json.load(f)

    print(f"  ✓ 로드된 포인트: {len(new_points):,}개")

    # 3. 포인트 분석
    print("\n📊 Step 3: 포인트 분석...")
    sources = Counter()
    for p in new_points:
        source = p.get('payload', {}).get('source', 'unknown')
        sources[source] += 1

    print("  Source 분포:")
    for source, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"    {source}: {count:,}개")

    # 예상 source 확인
    expected_sources = {'원천_판결문', '원천_결정례'}
    actual_sources = set(sources.keys())

    if not actual_sources.intersection(expected_sources):
        print(f"\n  ⚠️ 경고: 예상 source가 없습니다!")
        print(f"     예상: {expected_sources}")
        print(f"     실제: {actual_sources}")

    # Dry-run 모드
    if args.dry_run:
        print("\n[DRY-RUN] 실제 변경 없이 종료합니다.")
        print(f"  추가될 포인트: {len(new_points):,}개")
        print(f"  예상 최종 포인트: {before_count + len(new_points):,}개")
        return

    # 4. 배치 업서트
    print(f"\n⬆️ Step 4: 업서트 중... (batch_size={args.batch_size})")

    total = len(new_points)
    success_count = 0
    error_count = 0

    for i in tqdm(range(0, total, args.batch_size), desc="Uploading"):
        batch = new_points[i:i+args.batch_size]

        try:
            points = [
                PointStruct(
                    id=p["id"],
                    vector=p["vector"],
                    payload=p["payload"]
                )
                for p in batch
            ]
            client.upsert(collection_name=args.collection, points=points)
            success_count += len(batch)
        except Exception as e:
            error_count += len(batch)
            print(f"\n  ✗ 배치 업서트 실패 (offset={i}): {e}")

    # 5. 검증
    print("\n🔍 Step 5: 검증 중...")
    info = client.get_collection(args.collection)
    after_count = info.points_count

    print(f"  이전 포인트: {before_count:,}개")
    print(f"  추가된 포인트: {after_count - before_count:,}개")
    print(f"  최종 포인트: {after_count:,}개")

    if error_count > 0:
        print(f"  ⚠️ 실패한 포인트: {error_count:,}개")

    # 6. Source별 최종 분포 확인 (샘플링)
    print("\n📊 Step 6: 최종 Source 분포 확인 (샘플)...")
    final_sources = Counter()
    offset = None
    sample_limit = 20000

    while len(final_sources) == 0 or sum(final_sources.values()) < sample_limit:
        points, next_offset = client.scroll(
            collection_name=args.collection,
            limit=5000,
            offset=offset,
            with_payload=['source'],
            with_vectors=False
        )

        if not points:
            break

        for p in points:
            source = p.payload.get('source', 'unknown')
            final_sources[source] += 1

        offset = next_offset
        if offset is None:
            break

    print("  Source 분포 (샘플):")
    for source, count in sorted(final_sources.items(), key=lambda x: -x[1])[:15]:
        print(f"    {source}: {count:,}개")

    # 완료
    print("\n" + "="*60)
    print(" ✅ 병합 완료!")
    print("="*60)
    print(f"  최종 포인트 수: {after_count:,}개")
    print(f"  추가된 포인트: {after_count - before_count:,}개")
    print("\n📤 다음 단계:")
    print("   python scripts/add_sparse_vectors.py --fit-vocab --batch-size 500")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
