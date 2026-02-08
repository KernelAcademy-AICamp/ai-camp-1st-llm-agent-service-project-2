"""
Chunking Strategy V2 테스트 스크립트
새로운 청킹 전략을 실제 데이터로 테스트하고 기존 전략과 비교

Usage:
    python scripts/test_chunking_v2.py
    python scripts/test_chunking_v2.py --type 법령 --samples 5
    python scripts/test_chunking_v2.py --all --samples 3
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
from typing import List, Dict, Any

# 데이터 로더
from scripts.criminal_law_data_loader import CriminalLawDataLoader

# 기존 청킹 전략
from libs.rag_core.chunking.legal_chunker import (
    LegalArticleChunking,
    PrecedentAutoChunking,
    InterpretationChunking,
    QAPreserveChunking
)

# 새로운 청킹 전략
from libs.rag_core.chunking.legal_chunker_v2 import (
    LegalArticleChunkingV2,
    PrecedentChunkingV2,
    InterpretationChunkingV2,
    QAPreserveChunkingV2,
    get_chunker_v2
)


def print_separator(title: str = ""):
    """구분선 출력"""
    print("\n" + "=" * 80)
    if title:
        print(f" {title}")
        print("=" * 80)


def print_chunk_info(chunks: List[Dict], prefix: str = ""):
    """청크 정보 출력"""
    print(f"{prefix}총 청크 수: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        content = chunk.get('content', '')
        metadata = chunk.get('metadata', {})
        print(f"{prefix}  [{i}] 길이: {len(content):,}자, 타입: {metadata.get('chunk_type', 'N/A')}")
        # 첫 100자 미리보기
        preview = content[:100].replace('\n', ' ')
        print(f"{prefix}      미리보기: {preview}...")


def compare_chunking(doc: Dict, old_chunker, new_chunker, doc_type: str):
    """기존 vs 새로운 청킹 비교"""
    content = doc.get('content', '')
    metadata = doc.get('metadata', {})

    print(f"\n--- 문서: {metadata.get('doc_id', 'N/A')} ({doc_type}) ---")
    print(f"원본 길이: {len(content):,}자")

    # 기존 청킹
    try:
        old_chunks = old_chunker.chunk(content, metadata)
        print("\n[기존 전략]")
        print_chunk_info(old_chunks, "  ")
    except Exception as e:
        print(f"\n[기존 전략] 오류: {e}")
        old_chunks = []

    # 새로운 청킹
    try:
        new_chunks = new_chunker.chunk(content, metadata)
        print("\n[새로운 전략 V2]")
        print_chunk_info(new_chunks, "  ")
    except Exception as e:
        print(f"\n[새로운 전략 V2] 오류: {e}")
        new_chunks = []

    # 비교 요약
    print("\n[비교 결과]")
    old_count = len(old_chunks)
    new_count = len(new_chunks)
    print(f"  청크 수: {old_count} → {new_count} ({'증가' if new_count > old_count else '감소' if new_count < old_count else '동일'})")

    if old_chunks and new_chunks:
        old_avg_len = sum(len(c.get('content', '')) for c in old_chunks) / len(old_chunks)
        new_avg_len = sum(len(c.get('content', '')) for c in new_chunks) / len(new_chunks)
        print(f"  평균 청크 길이: {old_avg_len:.0f}자 → {new_avg_len:.0f}자")

    return old_chunks, new_chunks


def test_law_chunking(loader: CriminalLawDataLoader, samples: int = 3):
    """법령 청킹 테스트"""
    print_separator("법령 (法令) 청킹 테스트")

    docs = loader.load_source_data(types=['법령'], max_per_type=samples)
    print(f"로드된 법령 문서: {len(docs)}개")

    old_chunker = LegalArticleChunking()
    new_chunker = LegalArticleChunkingV2()

    for doc in docs[:samples]:
        compare_chunking(doc, old_chunker, new_chunker, '법령')


def test_precedent_chunking(loader: CriminalLawDataLoader, samples: int = 3):
    """판결문 청킹 테스트"""
    print_separator("판결문 (判決文) 청킹 테스트")

    docs = loader.load_source_data(types=['판결문'], max_per_type=samples)
    print(f"로드된 판결문 문서: {len(docs)}개")

    old_chunker = PrecedentAutoChunking()
    new_chunker = PrecedentChunkingV2()

    for doc in docs[:samples]:
        compare_chunking(doc, old_chunker, new_chunker, '판결문')


def test_decision_chunking(loader: CriminalLawDataLoader, samples: int = 3):
    """결정례 청킹 테스트"""
    print_separator("결정례 (決定例) 청킹 테스트")

    docs = loader.load_source_data(types=['결정례'], max_per_type=samples)
    print(f"로드된 결정례 문서: {len(docs)}개")

    old_chunker = PrecedentAutoChunking()
    new_chunker = PrecedentChunkingV2()

    for doc in docs[:samples]:
        compare_chunking(doc, old_chunker, new_chunker, '결정례')


def test_interpretation_chunking(loader: CriminalLawDataLoader, samples: int = 3):
    """해석례 청킹 테스트"""
    print_separator("해석례 (解釋例) 청킹 테스트")

    docs = loader.load_source_data(types=['해석례'], max_per_type=samples)
    print(f"로드된 해석례 문서: {len(docs)}개")

    old_chunker = InterpretationChunking()
    new_chunker = InterpretationChunkingV2()

    for doc in docs[:samples]:
        compare_chunking(doc, old_chunker, new_chunker, '해석례')


def test_qa_chunking(loader: CriminalLawDataLoader, samples: int = 3):
    """QA 데이터 청킹 테스트"""
    print_separator("QA 데이터 청킹 테스트")

    docs = loader.load_labeled_data(types=['판결문_QA', '법령_QA'], max_per_type=samples)
    print(f"로드된 QA 문서: {len(docs)}개")

    old_chunker = QAPreserveChunking()
    new_chunker = QAPreserveChunkingV2()

    for doc in docs[:samples]:
        doc_type = doc.get('metadata', {}).get('type', 'QA')
        compare_chunking(doc, old_chunker, new_chunker, doc_type)


def test_sum_chunking(loader: CriminalLawDataLoader, samples: int = 3):
    """SUM 데이터 청킹 테스트"""
    print_separator("SUM (요약) 데이터 청킹 테스트")

    docs = loader.load_labeled_data(types=['판결문_SUM', '결정례_SUM'], max_per_type=samples)
    print(f"로드된 SUM 문서: {len(docs)}개")

    old_chunker = QAPreserveChunking()
    new_chunker = QAPreserveChunkingV2()

    for doc in docs[:samples]:
        doc_type = doc.get('metadata', {}).get('type', 'SUM')
        compare_chunking(doc, old_chunker, new_chunker, doc_type)


def test_automatic_strategy_selection(loader: CriminalLawDataLoader, samples: int = 2):
    """자동 전략 선택 테스트 (get_chunker_v2)"""
    print_separator("자동 전략 선택 테스트")

    test_cases = [
        ('법령', ['법령']),
        ('판결문', ['판결문']),
        ('결정례', ['결정례']),
        ('해석례', ['해석례']),
    ]

    for name, types in test_cases:
        docs = loader.load_source_data(types=types, max_per_type=samples)
        if docs:
            doc = docs[0]
            metadata = doc.get('metadata', {})
            doc_type = metadata.get('type', '')

            print(f"\n[{name}] doc_type='{doc_type}'")
            chunker = get_chunker_v2(doc_type)
            print(f"  선택된 전략: {chunker.__class__.__name__}")

            chunks = chunker.chunk(doc['content'], metadata)
            print(f"  청크 수: {len(chunks)}")


def run_full_test(loader: CriminalLawDataLoader, samples: int = 3):
    """전체 테스트 실행"""
    test_law_chunking(loader, samples)
    test_precedent_chunking(loader, samples)
    test_decision_chunking(loader, samples)
    test_interpretation_chunking(loader, samples)
    test_qa_chunking(loader, samples)
    test_sum_chunking(loader, samples)
    test_automatic_strategy_selection(loader, samples)


def detailed_chunk_analysis(doc: Dict, chunker, doc_type: str):
    """상세 청크 분석"""
    content = doc.get('content', '')
    metadata = doc.get('metadata', {})

    print(f"\n{'='*60}")
    print(f"문서 ID: {metadata.get('doc_id', 'N/A')}")
    print(f"문서 타입: {doc_type}")
    print(f"원본 길이: {len(content):,}자")
    print(f"메타데이터 키: {list(metadata.keys())}")
    print(f"{'='*60}")

    print("\n[원본 콘텐츠 (처음 500자)]")
    print("-" * 40)
    print(content[:500])
    print("-" * 40)

    chunks = chunker.chunk(content, metadata)

    print(f"\n[청킹 결과] 총 {len(chunks)}개 청크")
    for i, chunk in enumerate(chunks):
        chunk_content = chunk.get('content', '')
        chunk_meta = chunk.get('metadata', {})

        print(f"\n--- 청크 #{i} ---")
        print(f"길이: {len(chunk_content):,}자")
        print(f"타입: {chunk_meta.get('chunk_type', 'N/A')}")
        print(f"전략: {chunk_meta.get('chunking_strategy', 'N/A')}")
        print(f"메타데이터: {chunk_meta}")
        print(f"\n내용 전체:")
        print(chunk_content[:1000] if len(chunk_content) > 1000 else chunk_content)
        print("-" * 40)

    return chunks


def main():
    parser = argparse.ArgumentParser(description='청킹 전략 V2 테스트')
    parser.add_argument('--type', type=str, default=None,
                       help='테스트할 데이터 타입 (법령, 판결문, 결정례, 해석례, qa, sum)')
    parser.add_argument('--samples', type=int, default=3,
                       help='타입별 테스트 샘플 수')
    parser.add_argument('--all', action='store_true',
                       help='전체 테스트 실행')
    parser.add_argument('--detailed', action='store_true',
                       help='상세 분석 모드')
    parser.add_argument('--base-path', type=str, default=None,
                       help='데이터 기본 경로')

    args = parser.parse_args()

    # 데이터 로더 초기화
    print("데이터 로더 초기화 중...")
    loader = CriminalLawDataLoader(base_path=args.base_path)

    if args.all:
        run_full_test(loader, args.samples)
    elif args.type:
        doc_type = args.type.lower()

        if doc_type == '법령':
            if args.detailed:
                docs = loader.load_source_data(types=['법령'], max_per_type=args.samples)
                for doc in docs[:args.samples]:
                    detailed_chunk_analysis(doc, LegalArticleChunkingV2(), '법령')
            else:
                test_law_chunking(loader, args.samples)

        elif doc_type == '판결문':
            if args.detailed:
                docs = loader.load_source_data(types=['판결문'], max_per_type=args.samples)
                for doc in docs[:args.samples]:
                    detailed_chunk_analysis(doc, PrecedentChunkingV2(), '판결문')
            else:
                test_precedent_chunking(loader, args.samples)

        elif doc_type == '결정례':
            if args.detailed:
                docs = loader.load_source_data(types=['결정례'], max_per_type=args.samples)
                for doc in docs[:args.samples]:
                    detailed_chunk_analysis(doc, PrecedentChunkingV2(), '결정례')
            else:
                test_decision_chunking(loader, args.samples)

        elif doc_type == '해석례':
            if args.detailed:
                docs = loader.load_source_data(types=['해석례'], max_per_type=args.samples)
                for doc in docs[:args.samples]:
                    detailed_chunk_analysis(doc, InterpretationChunkingV2(), '해석례')
            else:
                test_interpretation_chunking(loader, args.samples)

        elif doc_type == 'qa':
            if args.detailed:
                docs = loader.load_labeled_data(types=['판결문_QA'], max_per_type=args.samples)
                for doc in docs[:args.samples]:
                    detailed_chunk_analysis(doc, QAPreserveChunkingV2(), 'QA')
            else:
                test_qa_chunking(loader, args.samples)

        elif doc_type == 'sum':
            if args.detailed:
                docs = loader.load_labeled_data(types=['판결문_SUM'], max_per_type=args.samples)
                for doc in docs[:args.samples]:
                    detailed_chunk_analysis(doc, QAPreserveChunkingV2(), 'SUM')
            else:
                test_sum_chunking(loader, args.samples)

        else:
            print(f"알 수 없는 타입: {doc_type}")
            print("지원 타입: 법령, 판결문, 결정례, 해석례, qa, sum")
    else:
        # 기본: 각 타입별 1개씩 빠른 테스트
        print("빠른 테스트 실행 (각 타입별 1개)")
        run_full_test(loader, samples=1)

    print_separator("테스트 완료")


if __name__ == "__main__":
    main()
