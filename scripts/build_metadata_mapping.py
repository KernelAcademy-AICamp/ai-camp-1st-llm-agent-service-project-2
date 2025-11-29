"""
원천데이터용 메타데이터 매핑 구축 스크립트
라벨링 JSON의 info 필드에서 메타데이터를 추출하여 매핑 파일 생성

사용법:
    python scripts/build_metadata_mapping.py

출력:
    data/metadata_mapping.json
"""

import sys
import json
from pathlib import Path
from tqdm import tqdm
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def build_metadata_mapping(base_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    라벨링 JSON에서 원천데이터 ID → 메타데이터 매핑 구축

    Returns:
        {
            'precedent': {precedent_id: {...metadata...}},
            'decision': {decision_id: {...metadata...}},
            'interpretation': {interpretation_id: {...metadata...}},
            'law': {law_id: {...metadata...}}
        }
    """
    mapping = {
        'precedent': {},      # precedId → metadata
        'decision': {},       # determintId → metadata
        'interpretation': {}, # interpreId → metadata
        'law': {}             # lawId → metadata
    }

    labeled_path = base_path / "Training" / "02.라벨링데이터"

    # === 판결문 매핑 ===
    print("📚 판결문 메타데이터 수집 중...")
    for folder in ["TL_판결문_QA", "TL_판결문_SUM"]:
        folder_path = labeled_path / folder
        if folder_path.exists():
            for json_file in tqdm(list(folder_path.glob("*.json")), desc=folder):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    info = data.get('info', {})

                    precedent_id = str(info.get('precedId', ''))
                    if precedent_id and precedent_id not in mapping['precedent']:
                        mapping['precedent'][precedent_id] = {
                            'case_name': info.get('caseName', ''),
                            'case_num': info.get('caseNum', ''),
                            'sentence_date': _convert_date(info.get('sentenceDate', '')),
                            'court_name': info.get('courtName', ''),
                            'court_code': info.get('courtCode', ''),
                            'case_type': info.get('caseTypeName', ''),
                        }
                except Exception as e:
                    continue

    # === 결정례 매핑 ===
    print("📚 결정례 메타데이터 수집 중...")
    for folder in ["TL_결정례_QA", "TL_결정례_SUM"]:
        folder_path = labeled_path / folder
        if folder_path.exists():
            for json_file in tqdm(list(folder_path.glob("*.json")), desc=folder):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    info = data.get('info', {})

                    decision_id = str(info.get('determintId', ''))
                    if decision_id and decision_id not in mapping['decision']:
                        mapping['decision'][decision_id] = {
                            'case_name': info.get('caseName', ''),
                            'case_num': info.get('caseNum', ''),
                            'final_date': _convert_date(info.get('finalDate', '')),
                            'case_code': info.get('caseCode', ''),
                            'court_code': info.get('courtCode', ''),
                        }
                except Exception as e:
                    continue

    # === 해석례 매핑 ===
    print("📚 해석례 메타데이터 수집 중...")
    for folder in ["TL_해석례_QA", "TL_해석례_SUM"]:
        folder_path = labeled_path / folder
        if folder_path.exists():
            for json_file in tqdm(list(folder_path.glob("*.json")), desc=folder):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    info = data.get('info', {})

                    interp_id = str(info.get('interpreId', ''))
                    if interp_id and interp_id not in mapping['interpretation']:
                        mapping['interpretation'][interp_id] = {
                            'agenda': info.get('agenda', ''),
                            'agenda_num': info.get('agendaNum', ''),
                            'interp_date': _convert_date(info.get('interpreDate', '')),
                            'interp_ministry': info.get('interpreMinName', ''),
                            'question_ministry': info.get('questionMinName', ''),
                        }
                except Exception as e:
                    continue

    # === 법령 매핑 ===
    print("📚 법령 메타데이터 수집 중...")
    folder_path = labeled_path / "TL_법령_QA"
    if folder_path.exists():
        for json_file in tqdm(list(folder_path.glob("*.json")), desc="TL_법령_QA"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                info = data.get('info', {})

                law_id = str(info.get('lawId', ''))
                if law_id and law_id not in mapping['law']:
                    mapping['law'][law_id] = {
                        'law_title': info.get('title', ''),
                        'ministry': info.get('ministry', ''),
                        'promulg_date': _convert_date(info.get('promulgDate', '')),
                        'effect_date': _convert_date(info.get('effectDate', '')),
                        'promulg_num': info.get('promulgNum', ''),
                    }
            except Exception as e:
                continue

    return mapping


def _convert_date(date_str: str) -> str:
    """날짜 형식 변환 (YYYYMMDD, YYYY.MM.DD → YYYY-MM-DD)"""
    if not date_str:
        return ''

    date_str = str(date_str).strip().rstrip('.')

    # YYYYMMDD 형식
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    # YYYY.MM.DD 형식
    if '.' in date_str:
        return date_str.replace('.', '-')

    return date_str


def save_mapping(mapping: Dict, output_path: Path):
    """매핑 파일 저장"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 매핑 저장 완료: {output_path}")


def print_stats(mapping: Dict):
    """매핑 통계 출력"""
    print("\n" + "="*50)
    print("📊 메타데이터 매핑 통계")
    print("="*50)
    print(f"  판결문: {len(mapping['precedent']):,}개 ID 매핑")
    print(f"  결정례: {len(mapping['decision']):,}개 ID 매핑")
    print(f"  해석례: {len(mapping['interpretation']):,}개 ID 매핑")
    print(f"  법령: {len(mapping['law']):,}개 ID 매핑")
    print(f"\n  총 매핑: {sum(len(v) for v in mapping.values()):,}개")


if __name__ == '__main__':
    import os

    # 기본 경로 설정
    base_path = Path(os.getenv(
        "CRIMINAL_LAW_BASE_PATH",
        PROJECT_ROOT / "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터" / "3.개방데이터" / "1.데이터"
    ))

    # ✅ 문서와 일치하도록 data/ 폴더에 저장
    output_path = PROJECT_ROOT / "data" / "metadata_mapping.json"

    print(f"📂 데이터 경로: {base_path}")
    print(f"📂 출력 경로: {output_path}")

    # 매핑 구축
    mapping = build_metadata_mapping(base_path)

    # 통계 출력
    print_stats(mapping)

    # 저장
    save_mapping(mapping, output_path)

    # 샘플 출력
    print("\n📋 샘플 데이터:")
    if mapping['precedent']:
        sample_id = list(mapping['precedent'].keys())[0]
        print(f"  판결문 {sample_id}: {mapping['precedent'][sample_id]}")
