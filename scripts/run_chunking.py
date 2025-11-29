"""
전체 데이터 청킹 실행 스크립트
AI-Hub 형사법 데이터를 타입별 최적화된 전략으로 청킹
"""

import sys
import yaml
import json
import argparse
import time
import platform
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from typing import List, Dict, Any, Optional

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.criminal_law_data_loader import CriminalLawDataLoader
from libs.rag_core.chunking import create_chunker
from libs.rag_core.chunking.chunker import merge_small_chunks


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """청킹 설정 로드"""
    if config_path is None:
        config_path = PROJECT_ROOT / 'configs' / 'chunking_config.yaml'

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_chunker_for_type(data_type: str, config: dict):
    """데이터 타입에 맞는 청커 반환"""
    strategy_map = config['chunking']['strategy_map']
    strategies = config['chunking']['strategies']

    # 타입에 맞는 전략 찾기
    strategy_name = strategy_map.get(data_type, config['chunking']['default_strategy'])
    strategy_config = strategies.get(strategy_name, {})

    # 청커 생성
    return create_chunker({
        'strategy': strategy_name,
        **strategy_config
    })


def chunk_source_documents(documents: List[Dict], data_type: str, config: dict, split: str = 'training') -> List[Dict]:
    """
    원천 데이터 청킹

    ⚠️ 주의: CriminalLawDataLoader가 이미 500자 단위로 청킹을 수행합니다.
    이 함수는 데이터 로더의 청킹 결과를 그대로 사용하거나,
    필요시 추가 청킹을 수행합니다.

    이중 청킹을 방지하려면 CriminalLawDataLoader의 chunk_size를
    충분히 크게 설정하거나 (예: 10000), 이 함수에서 청킹을 스킵하세요.

    Args:
        documents: 처리할 문서 리스트
        data_type: 데이터 타입 (법령, 판결문, 결정례, 해석례)
        config: 청킹 설정
        split: 데이터 분할 (Training 또는 Validation)
    """
    # ✅ split에 따라 TS_ 또는 VS_ 접두사 사용
    prefix = 'TS_' if split == 'training' else 'VS_'
    chunker = get_chunker_for_type(f'{prefix}{data_type}', config)
    all_chunks = []

    for doc in tqdm(documents, desc=f"Chunking {prefix}{data_type}"):
        metadata = doc.get('metadata', {})
        content = doc.get('content', '')

        # 이미 구조화된 데이터인지 확인
        # - chunk_index가 있으면 이미 청킹됨
        # - section이 있는 판결문은 데이터 로더가 이미 섹션별로 분리함
        is_pre_structured = (
            'chunk_index' in metadata or
            (data_type == '판결문' and 'section' in metadata and metadata.get('structure_type') == 'precedent_section')
        )

        if is_pre_structured:
            # CriminalLawDataLoader에서 이미 구조화된 경우
            # 콘텐츠가 충분히 작으면 그대로 사용, 크면 추가 청킹
            if len(content) <= chunker.chunk_size if hasattr(chunker, 'chunk_size') else 600:
                all_chunks.append({
                    'content': content,
                    'metadata': {
                        **metadata,
                        'chunking_strategy': f'loader_pre_structured_{data_type}'
                    }
                })
            else:
                # 섹션이 너무 크면 추가 청킹 수행
                chunks = chunker.chunk(content, metadata)
                for chunk in chunks:
                    chunk['metadata']['pre_structured'] = True
                all_chunks.extend(chunks)
        else:
            # 청킹되지 않은 원본 데이터인 경우 청킹 수행
            chunks = chunker.chunk(content, metadata)
            all_chunks.extend(chunks)

    # ⭐ 작은 청크 병합 후처리 (100자 미만 청크를 인접 청크와 병합)
    all_chunks = merge_small_chunks(all_chunks, min_size=100, max_merged_size=800)

    return all_chunks


def chunk_labeled_documents(documents: List[Dict], data_type: str, config: dict, split: str = 'training') -> List[Dict]:
    """
    라벨링 데이터 청킹

    Args:
        documents: 처리할 문서 리스트
        data_type: 데이터 타입 (법령_QA, 판결문_QA 등)
        config: 청킹 설정
        split: 데이터 분할 (Training 또는 Validation)
    """
    # ✅ split에 따라 TL_ 또는 VL_ 접두사 사용
    prefix = 'TL_' if split == 'training' else 'VL_'
    chunker = get_chunker_for_type(f'{prefix}{data_type}', config)
    all_chunks = []

    for doc in tqdm(documents, desc=f"Chunking {prefix}{data_type}"):
        metadata = doc.get('metadata', {})
        content = doc.get('content', '')

        chunks = chunker.chunk(content, metadata)
        all_chunks.extend(chunks)

    # ⭐ 라벨링 데이터도 작은 청크 병합 후처리 적용
    all_chunks = merge_small_chunks(all_chunks, min_size=100, max_merged_size=800)

    return all_chunks


def main():
    parser = argparse.ArgumentParser(description='AI-Hub 형사법 데이터 청킹')
    parser.add_argument('--max-per-type', type=int, default=None, help='타입별 최대 파일 수 (테스트용)')
    parser.add_argument('--output', type=str, default='data/processed/chunks.json', help='출력 파일 경로')
    parser.add_argument('--source-types', nargs='+', default=['법령', '판결문', '결정례', '해석례'], help='처리할 원천데이터 타입')
    parser.add_argument('--labeled-types', nargs='+', default=['법령_QA', '판결문_QA', '결정례_QA', '해석례_QA', '판결문_SUM', '결정례_SUM', '해석례_SUM'], help='처리할 라벨링데이터 타입')
    parser.add_argument('--skip-source', action='store_true', help='원천데이터 스킵')
    parser.add_argument('--skip-labeled', action='store_true', help='라벨링데이터 스킵')
    # ✅ 신규: split 파라미터 추가
    parser.add_argument('--split', type=str, choices=['Training', 'Validation', 'both'], default='Training',
                        help='데이터 분할 선택 (Training, Validation, 또는 both)')

    args = parser.parse_args()

    # ========== 성능 측정 시작 ==========
    total_start_time = time.time()
    timing_metrics = {
        'source_data': {},
        'labeled_data': {}
    }

    print("\n" + "="*70)
    print(" 🚀 AI-Hub 형사법 데이터 청킹 시작")
    print("="*70)
    print(f"  시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python: {platform.python_version()}")
    print(f"  Platform: {platform.system()} {platform.release()}")
    print("="*70 + "\n")

    # 설정 로드
    config_start = time.time()
    config = load_config()
    timing_metrics['config_load_time'] = time.time() - config_start
    print(f"✅ 설정 파일 로드 완료 ({timing_metrics['config_load_time']:.2f}s)")

    # 데이터 로더 초기화
    # ⚠️ chunk_size를 크게 설정하여 로더의 사전 청킹을 비활성화
    # 이렇게 하면 이 스크립트의 청킹 전략이 적용됨
    loader_start = time.time()
    loader = CriminalLawDataLoader(chunk_size=100000)  # 사실상 청킹 비활성화
    timing_metrics['loader_init_time'] = time.time() - loader_start
    print(f"✅ 데이터 로더 초기화 완료 ({timing_metrics['loader_init_time']:.2f}s)")

    all_chunks = []
    stats = {}
    total_docs_processed = 0

    # ✅ split 옵션에 따라 처리할 분할 결정
    # CriminalLawDataLoader는 소문자 split 값을 사용 ('training', 'validation')
    splits_to_process = ['training', 'validation'] if args.split == 'both' else [args.split.lower()]

    for split in splits_to_process:
        split_prefix_source = 'TS_' if split == 'training' else 'VS_'
        split_prefix_labeled = 'TL_' if split == 'training' else 'VL_'

        # 원천데이터 처리
        if not args.skip_source:
            print("\n" + "="*50)
            print(f"📚 원천데이터 청킹 시작 [{split}]")
            print("="*50)

            for doc_type in args.source_types:
                type_start = time.time()
                type_key = f'{split_prefix_source}{doc_type}'
                print(f"\n🔄 Processing {type_key}...")

                # 데이터 로드
                load_start = time.time()
                docs = loader.load_source_data(types=[doc_type], max_per_type=args.max_per_type, split=split)
                load_time = time.time() - load_start
                print(f"  → 로드된 문서: {len(docs)}개 ({load_time:.2f}s)")

                # 청킹
                chunk_start = time.time()
                chunks = chunk_source_documents(docs, doc_type, config, split=split)
                chunk_time = time.time() - chunk_start

                all_chunks.extend(chunks)
                stats[type_key] = len(chunks)
                total_docs_processed += len(docs)

                # 타입별 메트릭 저장
                timing_metrics['source_data'][type_key] = {
                    'docs_count': len(docs),
                    'chunks_count': len(chunks),
                    'load_time': round(load_time, 2),
                    'chunk_time': round(chunk_time, 2),
                    'total_time': round(time.time() - type_start, 2),
                    'chunks_per_doc': round(len(chunks) / len(docs), 2) if docs else 0
                }
                print(f"  → 생성된 청크: {len(chunks)}개 ({chunk_time:.2f}s)")

        # 라벨링데이터 처리
        if not args.skip_labeled:
            print("\n" + "="*50)
            print(f"📚 라벨링데이터 청킹 시작 [{split}]")
            print("="*50)

            for doc_type in args.labeled_types:
                type_start = time.time()
                type_key = f'{split_prefix_labeled}{doc_type}'
                print(f"\n🔄 Processing {type_key}...")

                # 데이터 로드
                load_start = time.time()
                docs = loader.load_labeled_data(types=[doc_type], max_per_type=args.max_per_type, split=split)
                load_time = time.time() - load_start
                print(f"  → 로드된 문서: {len(docs)}개 ({load_time:.2f}s)")

                # 청킹
                chunk_start = time.time()
                chunks = chunk_labeled_documents(docs, doc_type, config, split=split)
                chunk_time = time.time() - chunk_start

                all_chunks.extend(chunks)
                stats[type_key] = len(chunks)
                total_docs_processed += len(docs)

                # 타입별 메트릭 저장
                timing_metrics['labeled_data'][type_key] = {
                    'docs_count': len(docs),
                    'chunks_count': len(chunks),
                    'load_time': round(load_time, 2),
                    'chunk_time': round(chunk_time, 2),
                    'total_time': round(time.time() - type_start, 2),
                    'chunks_per_doc': round(len(chunks) / len(docs), 2) if docs else 0
                }
                print(f"  → 생성된 청크: {len(chunks)}개 ({chunk_time:.2f}s)")

    # 결과 저장
    save_start = time.time()
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    timing_metrics['save_time'] = round(time.time() - save_start, 2)

    # ========== 청크 길이 통계 계산 ==========
    chunk_lengths = [len(c['content']) for c in all_chunks]
    if chunk_lengths:
        chunk_stats = {
            'min_length': min(chunk_lengths),
            'max_length': max(chunk_lengths),
            'avg_length': round(sum(chunk_lengths) / len(chunk_lengths), 1),
            'median_length': sorted(chunk_lengths)[len(chunk_lengths) // 2],
            'under_50': sum(1 for l in chunk_lengths if l < 50),
            'under_100': sum(1 for l in chunk_lengths if l < 100),
            'over_1000': sum(1 for l in chunk_lengths if l > 1000),
            'over_1500': sum(1 for l in chunk_lengths if l > 1500),
        }
        chunk_stats['under_50_pct'] = round(chunk_stats['under_50'] / len(chunk_lengths) * 100, 2)
        chunk_stats['under_100_pct'] = round(chunk_stats['under_100'] / len(chunk_lengths) * 100, 2)
    else:
        chunk_stats = {}

    # ========== 전체 시간 계산 ==========
    total_time = time.time() - total_start_time
    timing_metrics['total_time'] = round(total_time, 2)
    timing_metrics['total_docs_processed'] = total_docs_processed
    timing_metrics['total_chunks'] = len(all_chunks)
    timing_metrics['docs_per_second'] = round(total_docs_processed / total_time, 2) if total_time > 0 else 0
    timing_metrics['chunks_per_second'] = round(len(all_chunks) / total_time, 2) if total_time > 0 else 0

    # 통계 출력
    print("\n" + "="*70)
    print(" 📊 청킹 완료 통계")
    print("="*70)
    for key, value in stats.items():
        print(f"  {key}: {value:,}개 청크")
    print(f"\n  총 청크 수: {len(all_chunks):,}개")
    print(f"  저장 위치: {output_path}")

    # 청크 품질 통계 출력
    if chunk_stats:
        print("\n" + "-"*70)
        print(" 📏 청크 길이 통계")
        print("-"*70)
        print(f"  최소 길이:       {chunk_stats['min_length']:>6}자")
        print(f"  최대 길이:       {chunk_stats['max_length']:>6}자")
        print(f"  평균 길이:       {chunk_stats['avg_length']:>6}자")
        print(f"  중앙값:          {chunk_stats['median_length']:>6}자")
        print(f"  50자 미만:       {chunk_stats['under_50']:>6}개 ({chunk_stats['under_50_pct']}%)")
        print(f"  100자 미만:      {chunk_stats['under_100']:>6}개 ({chunk_stats['under_100_pct']}%)")
        print(f"  1000자 초과:     {chunk_stats['over_1000']:>6}개")
        print(f"  1500자 초과:     {chunk_stats['over_1500']:>6}개")

        # 품질 기준 체크
        if chunk_stats['under_50'] == 0 and chunk_stats['under_100_pct'] < 5:
            print("\n  ✅ 품질 기준 통과 (50자 미만 0%, 100자 미만 5% 이하)")
        else:
            print("\n  ⚠️ 품질 기준 미달 - 검토 필요")

    # 성능 통계 출력
    print("\n" + "-"*70)
    print(" ⚡ 성능 통계")
    print("-"*70)
    print(f"  총 소요 시간:    {total_time:>8.2f}초 ({total_time/60:.1f}분)")
    print(f"  처리 문서 수:    {total_docs_processed:>8,}개")
    print(f"  문서 처리 속도:  {timing_metrics['docs_per_second']:>8.2f} docs/sec")
    print(f"  청크 생성 속도:  {timing_metrics['chunks_per_second']:>8.2f} chunks/sec")
    print("="*70)

    # 메트릭 저장
    metrics_path = PROJECT_ROOT / 'data' / 'pipeline_metrics' / 'chunking_metrics.json'
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    full_metrics = {
        'timestamp': datetime.now().isoformat(),
        'run_config': {
            'max_per_type': args.max_per_type,
            'split': args.split,
            'source_types': args.source_types,
            'labeled_types': args.labeled_types,
            'skip_source': args.skip_source,
            'skip_labeled': args.skip_labeled,
            'output_path': str(output_path)
        },
        'environment': {
            'python_version': platform.python_version(),
            'platform': f"{platform.system()} {platform.release()}",
            'processor': platform.processor()
        },
        'timing': timing_metrics,
        'chunk_stats': chunk_stats,
        'stats_by_type': stats,
        'chunking_config': config['chunking']
    }

    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(full_metrics, f, ensure_ascii=False, indent=2)

    print(f"\n  📁 메트릭 저장: {metrics_path}")
    print(f"  📁 청크 저장: {output_path}")
    print(f"\n  완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
