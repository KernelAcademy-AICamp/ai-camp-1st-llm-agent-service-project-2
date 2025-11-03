"""
교통 관련 법률 데이터 필터링 스크립트

사용법:
    python scripts/filter_traffic_data.py

기능:
    - 원본 형사법 데이터에서 교통 관련 데이터만 추출
    - 폴더 구조 유지
    - CSV(원천데이터)와 JSON(라벨링데이터) 모두 처리
"""

import os
import csv
import json
import shutil
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

# ============================================================================
# 설정: 여기만 수정하면 됩니다
# ============================================================================

# 교통 관련 키워드 (필요에 따라 추가/삭제)
TRAFFIC_KEYWORDS = [
    '교통', '도로교통법', '도로', '운전', '자동차', '차량', '음주운전',
    '무면허', '신호위반', '속도위반', '주정차', '교통사고', '난폭운전',
    '통행', '주차', '정차', '보행자', '횡단보도', '신호등', '면허',
    '사고', '충돌', '접촉', '과속', '안전거리', '차선', '중앙선',
    '추월', '급정거', '급출발', '정지선', '일시정지', '음주', '혈중알코올',
    '운전면허', '이륜차', '오토바이', '버스', '트럭', '화물차',
    '견인', '주행', '운행', '정차위반', '주차위반', '속도제한',
]

# 원본 데이터 경로
SOURCE_BASE = "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/3.개방데이터/1.데이터"

# 출력 데이터 경로
OUTPUT_BASE = "교통법 데이터/3.개방데이터/1.데이터"

# ============================================================================
# 필터링 로직
# ============================================================================

def contains_traffic_keyword(text):
    """텍스트에 교통 관련 키워드가 포함되어 있는지 확인"""
    if not text:
        return False
    text = str(text).lower()
    return any(keyword.lower() in text for keyword in TRAFFIC_KEYWORDS)


def filter_csv_files(source_dir, output_dir, data_type):
    """CSV 파일에서 교통 관련 문서 필터링 (문서 단위)"""

    source_path = Path(source_dir) / data_type
    output_path = Path(output_dir) / data_type

    if not source_path.exists():
        print(f"⚠️  경로가 존재하지 않습니다: {source_path}")
        return

    output_path.mkdir(parents=True, exist_ok=True)

    csv_files = list(source_path.glob("*.csv"))
    print(f"\n📄 {data_type} 처리 중... (총 {len(csv_files)}개 파일)")

    total_docs = 0
    filtered_docs = 0
    skipped_files = 0

    for csv_file in tqdm(csv_files, desc=f"  {data_type}"):
        try:
            # CSV 파일 읽기 및 문서별 그룹화
            document_groups = defaultdict(list)

            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 수정: 판결문은 '판례일련번호' 사용
                    doc_id = (row.get('결정례일련번호') or
                             row.get('법령일련번호') or
                             row.get('판례일련번호') or  # 판결문용 (수정됨!)
                             row.get('해석례일련번호'))
                    if doc_id:
                        document_groups[doc_id].append(row)

            # 문서 ID를 찾지 못한 경우 경고
            if not document_groups:
                skipped_files += 1
                continue

            # 교통 관련 문서 필터링
            traffic_docs = {}
            for doc_id, rows in document_groups.items():
                total_docs += 1
                # 문서 내 모든 행의 내용을 검사
                full_text = ' '.join([row.get('내용', '') for row in rows])
                if contains_traffic_keyword(full_text):
                    traffic_docs[doc_id] = rows
                    filtered_docs += 1

            # 필터링된 문서만 새 CSV에 저장
            if traffic_docs:
                output_file = output_path / csv_file.name
                with open(output_file, 'w', encoding='utf-8', newline='') as f:
                    if traffic_docs:
                        fieldnames = list(list(traffic_docs.values())[0][0].keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        for rows in traffic_docs.values():
                            writer.writerows(rows)

        except Exception as e:
            print(f"  ❌ 파일 처리 실패: {csv_file.name} - {e}")
            skipped_files += 1

    if skipped_files > 0:
        print(f"  ⚠️  스킵된 파일: {skipped_files}개")
    print(f"  ✅ 완료: {filtered_docs}/{total_docs} 문서 추출 ({filtered_docs/total_docs*100:.1f}%)" if total_docs > 0 else "  ✅ 완료: 0/0 문서")


def filter_json_files(source_dir, output_dir, data_type):
    """JSON 파일에서 교통 관련 문서 필터링"""

    source_path = Path(source_dir) / data_type
    output_path = Path(output_dir) / data_type

    if not source_path.exists():
        print(f"⚠️  경로가 존재하지 않습니다: {source_path}")
        return

    output_path.mkdir(parents=True, exist_ok=True)

    json_files = list(source_path.glob("*.json"))
    print(f"\n📄 {data_type} 처리 중... (총 {len(json_files)}개 파일)")

    filtered_count = 0

    for json_file in tqdm(json_files, desc=f"  {data_type}"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 여러 필드에서 교통 키워드 검색
            search_fields = []

            # info 필드
            if 'info' in data:
                search_fields.extend([
                    data['info'].get('caseName', ''),
                    data['info'].get('caseNum', ''),
                ])

            # label 필드
            if 'label' in data:
                search_fields.extend([
                    data['label'].get('instruction', ''),
                    data['label'].get('input', ''),
                    data['label'].get('output', ''),
                ])

            # 키워드 검색
            full_text = ' '.join(search_fields)
            if contains_traffic_keyword(full_text):
                output_file = output_path / json_file.name
                shutil.copy2(json_file, output_file)
                filtered_count += 1

        except Exception as e:
            print(f"  ❌ 파일 처리 실패: {json_file.name} - {e}")

    print(f"  ✅ 완료: {filtered_count}/{len(json_files)} 파일 추출")


def main():
    """메인 실행 함수"""

    print("=" * 80)
    print("🚗 교통 관련 법률 데이터 필터링 시작")
    print("=" * 80)
    print(f"\n📂 원본 경로: {SOURCE_BASE}")
    print(f"📂 출력 경로: {OUTPUT_BASE}")
    print(f"\n🔍 필터링 키워드 ({len(TRAFFIC_KEYWORDS)}개):")
    print(f"   {', '.join(TRAFFIC_KEYWORDS[:10])}...")
    print("\n" + "=" * 80)

    # Training 데이터 처리
    print("\n📚 Training 데이터 처리 시작")
    print("-" * 80)

    source_training = os.path.join(SOURCE_BASE, "Training")
    output_training = os.path.join(OUTPUT_BASE, "Training")

    # 원천데이터 (CSV)
    print("\n[1/2] 원천데이터 (CSV) 처리")
    source_csv = os.path.join(source_training, "01.원천데이터")
    output_csv = os.path.join(output_training, "01.원천데이터")

    for data_type in ['TS_결정례', 'TS_법령', 'TS_판결문', 'TS_해석례']:
        filter_csv_files(source_csv, output_csv, data_type)

    # 라벨링데이터 (JSON)
    print("\n[2/2] 라벨링데이터 (JSON) 처리")
    source_json = os.path.join(source_training, "02.라벨링데이터")
    output_json = os.path.join(output_training, "02.라벨링데이터")

    for data_type in ['TL_결정례_QA', 'TL_결정례_SUM', 'TL_법령_QA',
                      'TL_판결문_QA', 'TL_판결문_SUM', 'TL_해석례_QA', 'TL_해석례_SUM']:
        filter_json_files(source_json, output_json, data_type)

    # Validation 데이터 처리
    print("\n" + "=" * 80)
    print("\n📚 Validation 데이터 처리 시작")
    print("-" * 80)

    source_validation = os.path.join(SOURCE_BASE, "Validation")
    output_validation = os.path.join(OUTPUT_BASE, "Validation")

    if os.path.exists(source_validation):
        # 원천데이터 (CSV) - Validation은 VS_ 접두사 사용
        print("\n[1/2] 원천데이터 (CSV) 처리")
        source_csv = os.path.join(source_validation, "01.원천데이터")
        output_csv = os.path.join(output_validation, "01.원천데이터")

        for data_type in ['VS_결정례', 'VS_법령', 'VS_판결문', 'VS_해석례']:
            filter_csv_files(source_csv, output_csv, data_type)

        # 라벨링데이터 (JSON) - Validation은 VL_ 접두사 사용
        print("\n[2/2] 라벨링데이터 (JSON) 처리")
        source_json = os.path.join(source_validation, "02.라벨링데이터")
        output_json = os.path.join(output_validation, "02.라벨링데이터")

        for data_type in ['VL_결정례_QA', 'VL_결정례_SUM', 'VL_법령_QA',
                          'VL_판결문_QA', 'VL_판결문_SUM', 'VL_해석례_QA', 'VL_해석례_SUM']:
            filter_json_files(source_json, output_json, data_type)
    else:
        print("⚠️  Validation 데이터가 존재하지 않습니다.")

    print("\n" + "=" * 80)
    print("✅ 교통 관련 데이터 필터링 완료!")
    print(f"📂 결과 확인: {OUTPUT_BASE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
