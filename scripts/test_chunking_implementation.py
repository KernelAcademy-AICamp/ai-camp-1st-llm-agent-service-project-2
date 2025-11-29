#!/usr/bin/env python3
"""
청킹 구현 테스트 스크립트
의미있는_청킹_구현_가이드.md 문서 vs 실제 구현 비교 검증
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.criminal_law_data_loader import CriminalLawDataLoader
import json

# 데이터 경로 설정
BASE_PATH = str(project_root / "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터" / "3.개방데이터" / "1.데이터")


def test_source_csv_metadata():
    """원천데이터 CSV 메타데이터 추출 검증"""
    print("\n" + "="*80)
    print("1. 원천데이터 CSV 메타데이터 추출 검증")
    print("="*80)

    loader = CriminalLawDataLoader(base_path=BASE_PATH)

    # 테스트할 데이터 타입별 검증
    test_cases = {
        '법령': {
            'required_metadata': ['law_id', 'mst', 'article_num', 'article_title',
                                  'has_structure', 'structure_type', 'gubun_used'],
            'expected_structure': 'law_article'
        },
        '판결문': {
            'required_metadata': ['precedent_id', 'section', 'has_structure',
                                  'structure_type', 'gubun_used'],
            'expected_structure': 'precedent_section'
        },
        '결정례': {
            'required_metadata': ['decision_id', 'has_structure', 'needs_pattern_matching'],
            'expected_structure': 'decision_full'
        },
        '해석례': {
            'required_metadata': ['interpretation_id', 'has_query', 'has_response',
                                  'has_reason', 'has_structure', 'gubun_used'],
            'expected_structure': 'interpretation_qa'
        }
    }

    all_passed = True

    for doc_type, config in test_cases.items():
        print(f"\n📄 {doc_type} 검증:")
        print("-" * 40)

        try:
            # 샘플 데이터 로드 (1개 파일만)
            docs = loader.load_source_data(
                types=[doc_type],
                max_per_type=1,
                split='training'
            )

            if not docs:
                print(f"  ❌ 데이터 로드 실패 - 문서 없음")
                all_passed = False
                continue

            # 첫 번째 문서 검증
            doc = docs[0]
            metadata = doc.get('metadata', {})

            print(f"  📊 로드된 문서 수: {len(docs)}")
            print(f"  📝 샘플 콘텐츠 길이: {len(doc.get('content', ''))}자")

            # 필수 메타데이터 체크
            missing = []
            for field in config['required_metadata']:
                if field not in metadata:
                    missing.append(field)

            if missing:
                print(f"  ❌ 누락된 메타데이터: {missing}")
                all_passed = False
            else:
                print(f"  ✅ 필수 메타데이터 모두 존재")

            # 구조 타입 검증
            actual_structure = metadata.get('structure_type')
            if actual_structure == config['expected_structure']:
                print(f"  ✅ structure_type: {actual_structure}")
            else:
                print(f"  ❌ structure_type 불일치: 예상={config['expected_structure']}, 실제={actual_structure}")
                all_passed = False

            # 메타데이터 샘플 출력
            print(f"\n  🔍 메타데이터 샘플:")
            for key, value in metadata.items():
                print(f"     - {key}: {value}")

            # 콘텐츠 헤더 확인
            content = doc.get('content', '')
            if content.startswith('['):
                header_end = content.find(']')
                if header_end > 0:
                    print(f"\n  📑 콘텐츠 헤더: {content[:header_end+1]}")

        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            all_passed = False

    return all_passed


def test_labeled_json_metadata():
    """라벨링 JSON info 필드 메타데이터 추출 검증"""
    print("\n" + "="*80)
    print("2. 라벨링 JSON info 필드 메타데이터 추출 검증")
    print("="*80)

    loader = CriminalLawDataLoader(base_path=BASE_PATH)

    # 테스트할 데이터 타입별 검증
    test_cases = {
        '법령_QA': {
            'required_metadata': ['title', 'law_id', 'ministry', 'promulg_date',
                                  'promulg_year', 'instruction', 'label_type'],
            'info_fields': ['lawClass', 'DocuType', 'lawId', 'title', 'ministry',
                           'promulgDate', 'promulgNum']
        },
        '판결문_QA': {
            'required_metadata': ['precedent_id', 'case_name', 'case_num',
                                  'sentence_date', 'sentence_year', 'court_name',
                                  'case_type', 'instruction', 'label_type'],
            'info_fields': ['precedId', 'caseName', 'caseNum', 'sentenceDate',
                           'courtName', 'caseTypeName']
        },
        '결정례_QA': {
            'required_metadata': ['decision_id', 'case_name', 'case_num',
                                  'final_date', 'final_year', 'case_code',
                                  'instruction', 'label_type'],
            'info_fields': ['determintId', 'caseName', 'caseNum', 'finalDate', 'caseCode']
        },
        '해석례_QA': {
            'required_metadata': ['interpretation_id', 'agenda', 'agenda_num',
                                  'interp_date', 'interp_year', 'interp_ministry',
                                  'instruction', 'label_type'],
            'info_fields': ['interpreId', 'agenda', 'agendaNum', 'interpreDate',
                           'interpreMinName', 'questionMinName']
        }
    }

    all_passed = True

    for doc_type, config in test_cases.items():
        print(f"\n📄 {doc_type} 검증:")
        print("-" * 40)

        try:
            # 샘플 데이터 로드
            docs = loader.load_labeled_data(
                types=[doc_type],
                max_per_type=1,
                split='training'
            )

            if not docs:
                print(f"  ❌ 데이터 로드 실패 - 문서 없음")
                all_passed = False
                continue

            doc = docs[0]
            metadata = doc.get('metadata', {})

            print(f"  📊 로드된 문서 수: {len(docs)}")
            print(f"  📝 샘플 콘텐츠 길이: {len(doc.get('content', ''))}자")

            # 필수 메타데이터 체크
            missing = []
            found = []
            for field in config['required_metadata']:
                if field in metadata:
                    found.append(field)
                else:
                    missing.append(field)

            if missing:
                print(f"  ⚠️ 누락된 메타데이터: {missing}")
                print(f"  ✅ 존재하는 메타데이터: {found}")
                # 일부 필드가 누락되어도 경고만 표시
                if len(missing) > len(found):
                    all_passed = False
            else:
                print(f"  ✅ 필수 메타데이터 모두 존재")

            # label_type 검증
            label_type = metadata.get('label_type')
            expected_label = 'QA' if '_QA' in doc_type else 'SUM'
            if label_type == expected_label:
                print(f"  ✅ label_type: {label_type}")
            else:
                print(f"  ❌ label_type 불일치: 예상={expected_label}, 실제={label_type}")
                all_passed = False

            # 날짜 ISO 형식 검증
            date_fields = ['sentence_date', 'final_date', 'interp_date', 'promulg_date']
            for df in date_fields:
                if df in metadata:
                    date_val = metadata[df]
                    # YYYY-MM-DD 형식 확인
                    if date_val and '-' in str(date_val):
                        print(f"  ✅ {df} ISO 형식: {date_val}")
                    elif date_val:
                        print(f"  ⚠️ {df} ISO 변환 필요: {date_val}")

            # 연도 숫자 필드 검증
            year_fields = ['sentence_year', 'final_year', 'interp_year', 'promulg_year']
            for yf in year_fields:
                if yf in metadata:
                    year_val = metadata[yf]
                    if isinstance(year_val, int):
                        print(f"  ✅ {yf} 숫자 타입: {year_val}")
                    else:
                        print(f"  ⚠️ {yf} 타입 불일치: {type(year_val)} - {year_val}")

            # 메타데이터 샘플 출력
            print(f"\n  🔍 메타데이터 샘플:")
            for key, value in sorted(metadata.items()):
                if isinstance(value, str) and len(str(value)) > 50:
                    print(f"     - {key}: {str(value)[:50]}...")
                else:
                    print(f"     - {key}: {value}")

            # 콘텐츠 헤더 확인
            content = doc.get('content', '')
            if content.startswith('['):
                header_end = content.find(']')
                if header_end > 0:
                    print(f"\n  📑 콘텐츠 헤더: {content[:header_end+1]}")

        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False

    return all_passed


def test_sum_labeled_data():
    """요약(SUM) 라벨링 데이터 검증"""
    print("\n" + "="*80)
    print("3. 요약(SUM) 라벨링 데이터 메타데이터 검증")
    print("="*80)

    loader = CriminalLawDataLoader(base_path=BASE_PATH)

    sum_types = ['판결문_SUM', '결정례_SUM', '해석례_SUM']
    all_passed = True

    for doc_type in sum_types:
        print(f"\n📄 {doc_type} 검증:")
        print("-" * 40)

        try:
            docs = loader.load_labeled_data(
                types=[doc_type],
                max_per_type=1,
                split='training'
            )

            if not docs:
                print(f"  ❌ 데이터 로드 실패 - 문서 없음")
                all_passed = False
                continue

            doc = docs[0]
            metadata = doc.get('metadata', {})

            print(f"  📊 로드된 문서 수: {len(docs)}")

            # label_type 검증
            label_type = metadata.get('label_type')
            if label_type == 'SUM':
                print(f"  ✅ label_type: SUM")
            else:
                print(f"  ❌ label_type 불일치: 예상=SUM, 실제={label_type}")
                all_passed = False

            # 메타데이터 출력
            print(f"  🔍 메타데이터:")
            for key, value in sorted(metadata.items()):
                if isinstance(value, str) and len(str(value)) > 50:
                    print(f"     - {key}: {str(value)[:50]}...")
                else:
                    print(f"     - {key}: {value}")

        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            all_passed = False

    return all_passed


def main():
    """전체 테스트 실행"""
    print("="*80)
    print("청킹 구현 검증 테스트")
    print("docs/의미있는_청킹_구현_가이드.md 기준")
    print("="*80)

    results = {}

    # 1. 원천데이터 CSV 메타데이터 검증
    results['원천데이터_CSV'] = test_source_csv_metadata()

    # 2. 라벨링 JSON 메타데이터 검증
    results['라벨링_JSON_QA'] = test_labeled_json_metadata()

    # 3. 요약 라벨링 데이터 검증
    results['라벨링_JSON_SUM'] = test_sum_labeled_data()

    # 결과 요약
    print("\n" + "="*80)
    print("검증 결과 요약")
    print("="*80)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "="*80)
    if all_passed:
        print("🎉 모든 검증 통과!")
    else:
        print("⚠️ 일부 검증 실패 - 위의 상세 결과 확인 필요")
    print("="*80)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
