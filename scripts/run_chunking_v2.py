# -*- coding: utf-8 -*-
"""
청킹 V2 실행 스크립트
11개 데이터 타입 (Training + Validation) 청킹

Usage:
    python scripts/run_chunking_v2.py --split both --output chunks_v2.json
    python scripts/run_chunking_v2.py --split training --max-per-type 100
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from tqdm import tqdm

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.criminal_law_data_loader import CriminalLawDataLoader
from libs.rag_core.chunking.legal_chunker_v2 import get_chunker_v2, CHUNKING_STRATEGY_MAP_V2


def chunk_documents(documents: List[Dict[str, Any]], show_progress: bool = True) -> List[Dict[str, Any]]:
    """
    문서 리스트를 청킹

    Args:
        documents: 로드된 문서 리스트
        show_progress: 진행률 표시 여부

    Returns:
        청킹된 결과 리스트
    """
    all_chunks = []
    iterator = tqdm(documents, desc="Chunking") if show_progress else documents

    for doc in iterator:
        content = doc.get('content', '')
        metadata = doc.get('metadata', {})
        doc_type = metadata.get('type', '')

        if not content.strip():
            continue

        # 적절한 청킹 전략 선택
        chunker = get_chunker_v2(doc_type)

        try:
            chunks = chunker.chunk(content, metadata)

            # 각 청크에 원본 문서 정보 추가
            for chunk in chunks:
                chunk['metadata']['original_doc_type'] = doc_type
                chunk['metadata']['original_doc_id'] = metadata.get('doc_id', '')

            all_chunks.extend(chunks)
        except Exception as e:
            print(f"Warning: Failed to chunk document {metadata.get('doc_id', 'unknown')}: {e}")
            continue

    return all_chunks


def main():
    parser = argparse.ArgumentParser(description='V2 청킹 실행 스크립트')
    parser.add_argument('--base-path', type=str, default=None,
                       help='데이터 기본 경로 (기본: 자동 탐지)')
    parser.add_argument('--split', type=str, default='both',
                       choices=['training', 'validation', 'both'],
                       help='데이터 스플릿 선택')
    parser.add_argument('--max-per-type', type=int, default=None,
                       help='타입별 최대 문서 수 (테스트용)')
    parser.add_argument('--output', type=str, default='chunks_v2.json',
                       help='출력 파일명')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='출력 디렉토리 (기본: data/processed)')

    args = parser.parse_args()

    print("=" * 60)
    print("V2 청킹 실행 스크립트")
    print("=" * 60)
    print(f"Split: {args.split}")
    print(f"Max per type: {args.max_per_type or 'unlimited'}")

    # 데이터 로더 초기화
    print("\n데이터 로더 초기화 중...")
    loader = CriminalLawDataLoader(base_path=args.base_path)

    # 원천데이터 타입
    source_types = ['법령', '판결문', '결정례', '해석례']

    # 라벨링데이터 타입 (법령_SUM 제외)
    labeled_types = [
        '법령_QA',
        '판결문_QA', '판결문_SUM',
        '결정례_QA', '결정례_SUM',
        '해석례_QA', '해석례_SUM'
    ]

    print(f"\n원천데이터 타입: {source_types}")
    print(f"라벨링데이터 타입: {labeled_types}")

    # 스플릿 설정
    if args.split == 'both':
        splits = ['training', 'validation']
    else:
        splits = [args.split]

    all_chunks = []
    stats = {}

    for split in splits:
        print(f"\n{'='*40}")
        print(f"Processing {split.upper()} split")
        print(f"{'='*40}")

        # 원천데이터 로드 및 청킹
        print(f"\n[원천데이터 로드]")
        source_docs = loader.load_source_data(
            types=source_types,
            max_per_type=args.max_per_type,
            split=split
        )
        print(f"  로드된 원천 문서: {len(source_docs):,}개")

        if source_docs:
            source_chunks = chunk_documents(source_docs)
            print(f"  생성된 원천 청크: {len(source_chunks):,}개")
            all_chunks.extend(source_chunks)
            stats[f'{split}_source_docs'] = len(source_docs)
            stats[f'{split}_source_chunks'] = len(source_chunks)

        # 라벨링데이터 로드 및 청킹
        print(f"\n[라벨링데이터 로드]")
        labeled_docs = loader.load_labeled_data(
            types=labeled_types,
            max_per_type=args.max_per_type,
            split=split
        )
        print(f"  로드된 라벨링 문서: {len(labeled_docs):,}개")

        if labeled_docs:
            labeled_chunks = chunk_documents(labeled_docs)
            print(f"  생성된 라벨링 청크: {len(labeled_chunks):,}개")
            all_chunks.extend(labeled_chunks)
            stats[f'{split}_labeled_docs'] = len(labeled_docs)
            stats[f'{split}_labeled_chunks'] = len(labeled_chunks)

    # 통계 출력
    print("\n" + "=" * 60)
    print("청킹 완료 통계")
    print("=" * 60)
    print(f"총 청크 수: {len(all_chunks):,}개")
    for key, value in stats.items():
        print(f"  {key}: {value:,}")

    # 청크 크기 분포
    if all_chunks:
        lengths = [len(c.get('content', '')) for c in all_chunks]
        print(f"\n청크 크기 분포:")
        print(f"  최소: {min(lengths):,}자")
        print(f"  최대: {max(lengths):,}자")
        print(f"  평균: {sum(lengths) / len(lengths):.0f}자")

    # 타입별 청크 수
    type_counts = {}
    for chunk in all_chunks:
        doc_type = chunk.get('metadata', {}).get('original_doc_type', 'unknown')
        type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

    print(f"\n타입별 청크 수:")
    for doc_type, count in sorted(type_counts.items()):
        print(f"  {doc_type}: {count:,}개")

    # 결과 저장
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = project_root / 'data' / 'processed'

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / args.output

    print(f"\n결과 저장 중: {output_path}")

    # 메타데이터와 함께 저장
    output_data = {
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'split': args.split,
            'max_per_type': args.max_per_type,
            'total_chunks': len(all_chunks),
            'stats': stats,
            'type_counts': type_counts,
            'chunking_version': 'v2'
        },
        'chunks': all_chunks
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"저장 완료: {output_path}")
    print(f"파일 크기: {output_path.stat().st_size / (1024*1024):.1f} MB")

    print("\n" + "=" * 60)
    print("청킹 완료!")
    print("=" * 60)

    return output_path


if __name__ == "__main__":
    main()
