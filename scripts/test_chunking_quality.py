"""
청킹 품질 검증 스크립트
- 각 데이터 타입별로 실제 청킹 테스트
- 예외 케이스 및 엣지 케이스 식별
- 청크 크기 분포 및 품질 분석
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.criminal_law_data_loader import CriminalLawDataLoader
from libs.rag_core.chunking.legal_chunker import (
    LegalArticleChunking,
    PrecedentAutoChunking,
    QAPreserveChunking,
    InterpretationChunking
)


def get_chunker_for_type(doc_type: str, data_source: str):
    """데이터 타입에 맞는 청커 반환"""
    if data_source == '원천':
        if doc_type == '법령':
            return LegalArticleChunking(chunk_size=512, max_chunk_size=800)
        elif doc_type in ['판결문', '결정례']:
            return PrecedentAutoChunking(chunk_size=600, overlap=100)
        elif doc_type == '해석례':
            return InterpretationChunking(max_length=1000)
    else:  # 라벨링
        return QAPreserveChunking(max_length=1000)

    return PrecedentAutoChunking()  # 기본값


def analyze_chunk_quality(chunks: List[Dict]) -> Dict[str, Any]:
    """청크 품질 분석"""
    if not chunks:
        return {'error': 'No chunks'}

    lengths = [len(c['content']) for c in chunks]

    analysis = {
        'chunk_count': len(chunks),
        'total_chars': sum(lengths),
        'avg_length': sum(lengths) // len(lengths) if lengths else 0,
        'min_length': min(lengths) if lengths else 0,
        'max_length': max(lengths) if lengths else 0,
        'tiny_chunks': len([l for l in lengths if l < 50]),    # 50자 미만
        'small_chunks': len([l for l in lengths if l < 100]),  # 100자 미만
        'medium_chunks': len([l for l in lengths if 100 <= l < 300]),  # 100-300자
        'good_chunks': len([l for l in lengths if 300 <= l <= 800]),   # 300-800자 (적정)
        'large_chunks': len([l for l in lengths if l > 800]),  # 800자 초과
    }

    # 문제 청크 상세 정보
    analysis['issues'] = []
    for i, chunk in enumerate(chunks):
        length = len(chunk['content'])
        if length < 50:
            analysis['issues'].append({
                'chunk_id': i,
                'length': length,
                'issue': 'tiny (<50자)',
                'preview': chunk['content'][:100]
            })
        elif length < 100:
            analysis['issues'].append({
                'chunk_id': i,
                'length': length,
                'issue': 'small (<100자)',
                'preview': chunk['content'][:100]
            })

    return analysis


def test_source_data_chunking(loader: CriminalLawDataLoader, doc_type: str, max_files: int = 10) -> Dict[str, Any]:
    """원천데이터 청킹 테스트"""
    print(f"\n{'='*60}")
    print(f"📄 원천데이터 테스트: {doc_type}")
    print('='*60)

    # 데이터 로드
    docs = loader.load_source_data(types=[doc_type], max_per_type=max_files, split='training')

    if not docs:
        return {'error': f'No {doc_type} documents found'}

    chunker = get_chunker_for_type(doc_type, '원천')

    all_chunks = []
    file_results = []

    for doc in docs:
        content = doc['content']
        metadata = doc['metadata']

        # 청킹 수행
        chunks = chunker.chunk(content, metadata)
        all_chunks.extend(chunks)

        # 파일별 분석
        file_analysis = analyze_chunk_quality(chunks)
        file_analysis['file'] = metadata.get('file', 'unknown')
        file_analysis['doc_id'] = metadata.get('doc_id', 'unknown')
        file_analysis['original_length'] = len(content)
        file_results.append(file_analysis)

    # 전체 분석
    overall_analysis = analyze_chunk_quality(all_chunks)
    overall_analysis['doc_type'] = doc_type
    overall_analysis['data_source'] = '원천'
    overall_analysis['files_tested'] = len(docs)
    overall_analysis['file_results'] = file_results

    # 결과 출력
    print(f"\n📊 전체 통계:")
    print(f"   문서 수: {len(docs)}")
    print(f"   총 청크 수: {overall_analysis['chunk_count']}")
    print(f"   평균 청크 크기: {overall_analysis['avg_length']}자")
    print(f"   최소/최대 크기: {overall_analysis['min_length']} ~ {overall_analysis['max_length']}자")
    print(f"\n   크기 분포:")
    print(f"     - 50자 미만 (극소): {overall_analysis['tiny_chunks']}개")
    print(f"     - 100자 미만 (작음): {overall_analysis['small_chunks']}개")
    print(f"     - 100-300자 (중간): {overall_analysis['medium_chunks']}개")
    print(f"     - 300-800자 (적정): {overall_analysis['good_chunks']}개")
    print(f"     - 800자 초과 (큼): {overall_analysis['large_chunks']}개")

    # 문제 청크 출력
    if overall_analysis['issues']:
        print(f"\n⚠️ 문제 청크 ({len(overall_analysis['issues'])}개):")
        for issue in overall_analysis['issues'][:5]:  # 최대 5개만 출력
            print(f"   - chunk_id={issue['chunk_id']}, {issue['length']}자, {issue['issue']}")
            print(f"     미리보기: {issue['preview'][:50]}...")

    return overall_analysis


def test_labeled_data_chunking(loader: CriminalLawDataLoader, doc_type: str, max_files: int = 10) -> Dict[str, Any]:
    """라벨링데이터 청킹 테스트"""
    print(f"\n{'='*60}")
    print(f"📄 라벨링데이터 테스트: {doc_type}")
    print('='*60)

    # 데이터 로드
    docs = loader.load_labeled_data(types=[doc_type], max_per_type=max_files, split='training')

    if not docs:
        return {'error': f'No {doc_type} documents found'}

    chunker = QAPreserveChunking(max_length=1000)

    all_chunks = []
    file_results = []

    for doc in docs:
        content = doc['content']
        metadata = doc['metadata']

        # 청킹 수행
        chunks = chunker.chunk(content, metadata)
        all_chunks.extend(chunks)

        # 파일별 분석
        file_analysis = analyze_chunk_quality(chunks)
        file_analysis['file'] = metadata.get('file', 'unknown')
        file_analysis['original_length'] = len(content)
        file_results.append(file_analysis)

    # 전체 분석
    overall_analysis = analyze_chunk_quality(all_chunks)
    overall_analysis['doc_type'] = doc_type
    overall_analysis['data_source'] = '라벨링'
    overall_analysis['files_tested'] = len(docs)
    overall_analysis['file_results'] = file_results

    # 결과 출력
    print(f"\n📊 전체 통계:")
    print(f"   문서 수: {len(docs)}")
    print(f"   총 청크 수: {overall_analysis['chunk_count']}")
    print(f"   평균 청크 크기: {overall_analysis['avg_length']}자")
    print(f"   최소/최대 크기: {overall_analysis['min_length']} ~ {overall_analysis['max_length']}자")

    # QA/SUM 데이터는 대부분 1개 청크여야 함
    preserved_count = sum(1 for c in all_chunks if c.get('metadata', {}).get('qa_preserved', False))
    print(f"\n   QA 보존율: {preserved_count}/{len(all_chunks)} ({100*preserved_count//len(all_chunks) if all_chunks else 0}%)")

    return overall_analysis


def test_edge_cases(loader: CriminalLawDataLoader) -> Dict[str, Any]:
    """엣지 케이스 테스트"""
    print(f"\n{'='*60}")
    print("🔍 엣지 케이스 테스트")
    print('='*60)

    edge_cases = {
        'empty_content': [],
        'very_short': [],
        'very_long': [],
        'no_structure': [],
        'special_chars': [],
    }

    # 각 타입별로 더 많은 파일 로드하여 엣지 케이스 찾기
    for doc_type in ['법령', '판결문', '결정례', '해석례']:
        docs = loader.load_source_data(types=[doc_type], max_per_type=30, split='training')

        for doc in docs:
            content = doc['content']
            metadata = doc['metadata']

            # 빈 콘텐츠
            if not content or len(content) < 10:
                edge_cases['empty_content'].append({
                    'doc_type': doc_type,
                    'doc_id': metadata.get('doc_id'),
                    'length': len(content)
                })

            # 매우 짧은 콘텐츠 (100자 미만)
            elif len(content) < 100:
                edge_cases['very_short'].append({
                    'doc_type': doc_type,
                    'doc_id': metadata.get('doc_id'),
                    'length': len(content),
                    'preview': content[:50]
                })

            # 매우 긴 콘텐츠 (10000자 초과)
            elif len(content) > 10000:
                edge_cases['very_long'].append({
                    'doc_type': doc_type,
                    'doc_id': metadata.get('doc_id'),
                    'length': len(content)
                })

            # 구조 정보 없음
            if not metadata.get('has_structure', True):
                edge_cases['no_structure'].append({
                    'doc_type': doc_type,
                    'doc_id': metadata.get('doc_id'),
                })

    # 결과 출력
    print("\n📊 엣지 케이스 현황:")
    for case_type, cases in edge_cases.items():
        print(f"   {case_type}: {len(cases)}개")
        if cases and len(cases) <= 3:
            for case in cases:
                print(f"     - {case}")

    return edge_cases


def test_specific_patterns(loader: CriminalLawDataLoader) -> Dict[str, Any]:
    """특정 패턴 처리 테스트"""
    print(f"\n{'='*60}")
    print("🔍 특정 패턴 처리 테스트")
    print('='*60)

    results = {}

    # 1. 결정례 섹션 패턴 감지 테스트
    print("\n1. 결정례 섹션 패턴 감지 테스트")
    docs = loader.load_source_data(types=['결정례'], max_per_type=5, split='training')
    chunker = PrecedentAutoChunking()

    for doc in docs[:3]:
        content = doc['content']
        sections = chunker._detect_sections(content)

        detected_types = [s['type'] for s in sections] if sections else []
        print(f"   문서 {doc['metadata'].get('doc_id')}: {len(sections)}개 섹션 감지")
        print(f"     섹션 타입: {detected_types}")

        if not sections:
            print(f"     ⚠️ 섹션 감지 실패 - sliding window 폴백")

    # 2. 법령 조문 번호 추출 테스트
    print("\n2. 법령 조문 번호 추출 테스트")
    docs = loader.load_source_data(types=['법령'], max_per_type=3, split='training')

    for doc in docs:
        article_num = doc['metadata'].get('article_num', '')
        article_title = doc['metadata'].get('article_title', '')
        print(f"   {doc['metadata'].get('file')}: {article_num} - {article_title}")

    # 3. 해석례 구조 보존 테스트
    print("\n3. 해석례 구조 보존 테스트")
    docs = loader.load_source_data(types=['해석례'], max_per_type=3, split='training')
    chunker = InterpretationChunking()

    for doc in docs:
        content = doc['content']
        metadata = doc['metadata']

        chunks = chunker.chunk(content, metadata)

        has_query = metadata.get('has_query', False)
        has_response = metadata.get('has_response', False)
        has_reason = metadata.get('has_reason', False)

        print(f"   문서 {metadata.get('doc_id')}: 질의={has_query}, 회답={has_response}, 이유={has_reason}")
        print(f"     청크 수: {len(chunks)}, 보존율: {chunks[0]['metadata'].get('interpretation_preserved', False)}")

    return results


def run_comprehensive_test():
    """종합 테스트 실행"""
    print("🧪 청킹 품질 종합 검증 테스트")
    print("="*60)

    # 데이터 경로 확인
    base_path = PROJECT_ROOT / "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터" / "3.개방데이터" / "1.데이터"

    if not base_path.exists():
        print(f"❌ 데이터 경로 없음: {base_path}")
        print("   환경변수 CRIMINAL_LAW_BASE_PATH를 설정하세요.")
        return

    loader = CriminalLawDataLoader(base_path=str(base_path), chunk_size=100000)

    results = {
        'source_data': {},
        'labeled_data': {},
        'edge_cases': {},
        'patterns': {}
    }

    # 1. 원천데이터 테스트
    print("\n" + "="*60)
    print("📁 원천데이터 청킹 테스트")
    print("="*60)

    for doc_type in ['법령', '판결문', '결정례', '해석례']:
        result = test_source_data_chunking(loader, doc_type, max_files=10)
        results['source_data'][doc_type] = result

    # 2. 라벨링데이터 테스트
    print("\n" + "="*60)
    print("📁 라벨링데이터 청킹 테스트")
    print("="*60)

    for doc_type in ['법령_QA', '판결문_QA', '결정례_QA', '해석례_QA', '판결문_SUM', '결정례_SUM', '해석례_SUM']:
        result = test_labeled_data_chunking(loader, doc_type, max_files=10)
        results['labeled_data'][doc_type] = result

    # 3. 엣지 케이스 테스트
    results['edge_cases'] = test_edge_cases(loader)

    # 4. 특정 패턴 테스트
    results['patterns'] = test_specific_patterns(loader)

    # 최종 요약
    print("\n" + "="*60)
    print("📊 최종 요약")
    print("="*60)

    total_issues = 0
    for data_type, type_results in results['source_data'].items():
        if isinstance(type_results, dict) and 'issues' in type_results:
            issue_count = len(type_results['issues'])
            total_issues += issue_count
            if issue_count > 0:
                print(f"   ⚠️ {data_type}: {issue_count}개 문제 청크")
            else:
                print(f"   ✅ {data_type}: 문제 없음")

    if total_issues == 0:
        print("\n🎉 모든 테스트 통과! 청킹 품질 양호")
    else:
        print(f"\n⚠️ 총 {total_issues}개의 문제 청크 발견. 위 상세 내용을 확인하세요.")

    return results


if __name__ == '__main__':
    results = run_comprehensive_test()
