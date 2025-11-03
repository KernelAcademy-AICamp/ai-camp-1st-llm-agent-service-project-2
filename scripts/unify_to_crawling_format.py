"""
학습 데이터를 크롤링 데이터 형식으로 통합 변환
CSV 파일의 전문 내용을 포함하여 일관된 형식으로 저장

목표 형식:
{
  "검색어": "교통사고",
  "데이터타입": "판례",
  "사건번호": "2007노799",
  "선고일자": "2008.02.15",
  "법원명": "전주지방법원",
  "판례일련번호": "79038",
  "수집시각": "2025-11-03T...",
  "상세정보": {
    "판례내용": {
      "판시사항": "...",
      "판결요지": "...",
      "참조조문": "...",
      "전문": "..."
    }
  }
}
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# CSV 파일 읽기
# ============================================================================
def read_csv_full_content(csv_path: str) -> Dict[str, List[str]]:
    """
    CSV 파일에서 전문 내용 읽기

    Returns:
        {
            "판례내용": ["【피 고 인】", "【항 소 인】 검사", ...],
            "참조조문": [...],
            "참조판례": [...]
        }
    """
    sections = {}

    try:
        if not Path(csv_path).exists():
            return sections

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                section_type = row.get('구분', '')
                content = row.get('내용', '')

                if section_type not in sections:
                    sections[section_type] = []

                sections[section_type].append(content)

    except Exception as e:
        logger.warning(f"CSV 읽기 실패: {csv_path} - {str(e)}")

    return sections


def extract_judgment_parts(full_content: List[str]) -> Dict[str, str]:
    """
    전문에서 판시사항, 판결요지 등 추출

    Args:
        full_content: 전문 문장 리스트

    Returns:
        {
            "판시사항": "...",
            "판결요지": "...",
            "이유": "...",
            "주문": "..."
        }
    """
    parts = {
        "판시사항": "",
        "판결요지": "",
        "이유": "",
        "주문": "",
        "전문": "\n".join(full_content)
    }

    current_section = None
    section_content = []

    for line in full_content:
        line = line.strip()

        # 섹션 시작 감지
        if "【판시사항】" in line or line.startswith("판시사항"):
            if current_section and section_content:
                parts[current_section] = "\n".join(section_content)
            current_section = "판시사항"
            section_content = []
        elif "【판결요지】" in line or line.startswith("판결요지"):
            if current_section and section_content:
                parts[current_section] = "\n".join(section_content)
            current_section = "판결요지"
            section_content = []
        elif "【이    유】" in line or "【이유】" in line or line.startswith("이유"):
            if current_section and section_content:
                parts[current_section] = "\n".join(section_content)
            current_section = "이유"
            section_content = []
        elif "【주    문】" in line or "【주문】" in line:
            if current_section and section_content:
                parts[current_section] = "\n".join(section_content)
            current_section = "주문"
            section_content = []
        else:
            if current_section:
                section_content.append(line)

    # 마지막 섹션 저장
    if current_section and section_content:
        parts[current_section] = "\n".join(section_content)

    return parts


# ============================================================================
# 변환 함수
# ============================================================================
def convert_training_to_crawling_format(case_data: Dict) -> Dict:
    """
    학습 데이터 → 크롤링 데이터 형식 변환

    Args:
        case_data: 필터링된 학습 데이터

    Returns:
        크롤링 형식 딕셔너리
    """
    info = case_data.get('info', {})
    label = case_data.get('label', {})
    case_type = case_data.get('case_type', '판결문')

    # 데이터 타입 매핑
    data_type_map = {
        '판결문': '판례',
        '결정례': '결정례',
        '해석례': '해석례',
        '법령': '법령'
    }

    # 기본 정보
    unified_data = {
        "검색어": "교통관련",  # 매칭된 키워드 중 첫 번째
        "데이터타입": data_type_map.get(case_type, '판례'),
        "사건번호": info.get('caseNum', ''),
        "선고일자": info.get('sentenceDate', ''),
        "법원명": info.get('courtName', ''),
        "판례일련번호": case_data.get('case_id', ''),
        "사건종류명": info.get('caseTypeName', ''),
        "판결유형": info.get('sentenceType', ''),
        "데이터출처명": "형사법 LLM 학습 데이터",
        "수집시각": datetime.now().isoformat(),
    }

    # 검색어는 매칭된 키워드 중 강한 키워드 우선
    matched_keywords = case_data.get('matched_keywords', [])
    if matched_keywords:
        # 강한 키워드 우선 선택
        strong_keywords = ["교통사고", "도로교통법", "음주운전", "뺑소니",
                          "교통사고처리특례법", "무면허운전", "신호위반"]
        for kw in strong_keywords:
            if kw in matched_keywords:
                unified_data["검색어"] = kw
                break
        if unified_data["검색어"] == "교통관련":
            unified_data["검색어"] = matched_keywords[0]

    # 상세정보 구성
    detail_content = {}

    # CSV 파일에서 전문 읽기
    csv_path = case_data.get('file_path', '').replace('02.라벨링데이터', '01.원천데이터')

    if case_type == '판결문':
        csv_path = csv_path.replace('TL_판결문_QA', 'TS_판결문').replace('TL_판결문_SUM', 'TS_판결문')
    elif case_type == '결정례':
        csv_path = csv_path.replace('TL_결정례_QA', 'TS_결정례')
    elif case_type == '해석례':
        csv_path = csv_path.replace('TL_해석례_SUM', 'TS_해석례')
    elif case_type == '법령':
        csv_path = csv_path.replace('TL_법령_QA', 'TS_법령')

    # 파일명 변경 (JSON → CSV, _QA_xxx → "")
    if csv_path:
        csv_filename = Path(csv_path).stem
        # HS_P_78434_QA_8099 → HS_P_78434
        parts = csv_filename.split('_')
        if len(parts) >= 3:
            base_name = '_'.join(parts[:3])  # HS_P_78434
            csv_path = str(Path(csv_path).parent / f"{base_name}.csv")

    # CSV에서 전문 읽기
    csv_sections = read_csv_full_content(csv_path)

    if csv_sections:
        # 판례내용이 있으면 파싱
        if '판례내용' in csv_sections:
            judgment_parts = extract_judgment_parts(csv_sections['판례내용'])
            detail_content = {
                "판시사항": judgment_parts.get('판시사항', ''),
                "판결요지": judgment_parts.get('판결요지', label.get('output', '')),
                "이유": judgment_parts.get('이유', ''),
                "주문": judgment_parts.get('주문', ''),
                "참조조문": "\n".join(csv_sections.get('참조조문', [])),
                "참조판례": "\n".join(csv_sections.get('참조판례', [])),
                "전문": judgment_parts.get('전문', '')
            }
        else:
            # 일반적인 섹션 구조
            for section_type, content_list in csv_sections.items():
                detail_content[section_type] = "\n".join(content_list)
    else:
        # CSV 파일이 없으면 label 데이터로 구성
        detail_content = {
            "질의지침": label.get('instruction', ''),
            "질문": label.get('input', ''),
            "판결요지": label.get('output', ''),
            "참조조문": "",
            "전문": ""
        }

    # 상세정보 추가 (크롤링 형식: 평평한 구조)
    unified_data["상세정보"] = detail_content

    # 메타데이터 추가
    unified_data["메타데이터"] = {
        "원본파일경로": case_data.get('file_path', ''),
        "CSV경로": csv_path,
        "CSV존재여부": bool(csv_sections),
        "매칭키워드": matched_keywords,
        "강한매칭": case_data.get('is_strong_match', False),
        "데이터타입": case_data.get('data_type', ''),  # QA/SUM
        "AI학습데이터": {
            "instruction": label.get('instruction', ''),
            "input": label.get('input', ''),
            "output": label.get('output', '')
        }
    }

    return unified_data


# ============================================================================
# 배치 변환
# ============================================================================
def unify_training_data(
    filtered_file: str,
    output_dir: str = "unified_traffic_data"
):
    """
    필터링된 학습 데이터를 크롤링 형식으로 통합 변환

    Args:
        filtered_file: 필터링된 JSON 파일
        output_dir: 출력 디렉토리
    """
    logger.info("="*60)
    logger.info("학습 데이터 → 크롤링 형식 통합 변환")
    logger.info("="*60)
    logger.info(f"입력 파일: {filtered_file}")

    # 출력 디렉토리 생성
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    # 입력 파일 읽기
    with open(filtered_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cases = data.get('cases', [])
    metadata = data.get('metadata', {})

    logger.info(f"\n총 케이스 수: {len(cases):,}건")

    # 통합 데이터 구조
    unified_data = {
        "수집정보": {
            "수집시각": datetime.now().isoformat(),
            "데이터출처": "형사법 LLM 학습 데이터",
            "원본메타데이터": metadata,
            "판례수": 0,
            "결정례수": 0,
            "해석례수": 0,
            "법령수": 0,
            "총건수": len(cases)
        },
        "판례": [],
        "결정례": [],
        "해석례": [],
        "법령": []
    }

    # 통계
    stats = {
        "total": len(cases),
        "with_csv": 0,
        "without_csv": 0,
        "by_type": {}
    }

    # 변환
    logger.info("\n변환 중...")

    for i, case in enumerate(cases):
        if (i + 1) % 1000 == 0:
            logger.info(f"  진행: {i+1:,}/{len(cases):,} ({(i+1)/len(cases)*100:.1f}%)")

        try:
            # 크롤링 형식으로 변환
            unified_case = convert_training_to_crawling_format(case)

            # 타입별 분류
            case_type = case.get('case_type', '판결문')

            if case_type == '판결문':
                unified_data["판례"].append(unified_case)
            elif case_type == '결정례':
                unified_data["결정례"].append(unified_case)
            elif case_type == '해석례':
                unified_data["해석례"].append(unified_case)
            elif case_type == '법령':
                unified_data["법령"].append(unified_case)

            # 통계
            if unified_case["메타데이터"]["CSV존재여부"]:
                stats["with_csv"] += 1
            else:
                stats["without_csv"] += 1

            stats["by_type"][case_type] = stats["by_type"].get(case_type, 0) + 1

        except Exception as e:
            logger.error(f"  케이스 변환 실패 (ID: {case.get('case_id')}): {str(e)}")
            continue

    # 수집정보 업데이트
    unified_data["수집정보"]["판례수"] = len(unified_data["판례"])
    unified_data["수집정보"]["결정례수"] = len(unified_data["결정례"])
    unified_data["수집정보"]["해석례수"] = len(unified_data["해석례"])
    unified_data["수집정보"]["법령수"] = len(unified_data["법령"])

    # 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"unified_traffic_data_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, ensure_ascii=False, indent=2)

    # 통계 출력
    logger.info("\n" + "="*60)
    logger.info("통합 완료")
    logger.info("="*60)
    logger.info(f"총 변환: {stats['total']:,}건")
    logger.info(f"  CSV 전문 포함: {stats['with_csv']:,}건 ({stats['with_csv']/stats['total']*100:.1f}%)")
    logger.info(f"  CSV 없음: {stats['without_csv']:,}건 ({stats['without_csv']/stats['total']*100:.1f}%)")

    logger.info(f"\n타입별 통계:")
    logger.info(f"  판례: {len(unified_data['판례']):,}건")
    logger.info(f"  결정례: {len(unified_data['결정례']):,}건")
    logger.info(f"  해석례: {len(unified_data['해석례']):,}건")
    logger.info(f"  법령: {len(unified_data['법령']):,}건")

    logger.info(f"\n출력 파일: {output_file}")

    # 파일 크기
    import os
    file_size = os.path.getsize(output_file) / (1024*1024)
    logger.info(f"파일 크기: {file_size:.1f}MB")

    # 샘플 출력
    if unified_data["판례"]:
        logger.info("\n" + "="*60)
        logger.info("샘플 케이스 (판례 첫 번째)")
        logger.info("="*60)
        sample = unified_data["판례"][0]
        logger.info(f"검색어: {sample['검색어']}")
        logger.info(f"사건번호: {sample['사건번호']}")
        logger.info(f"법원명: {sample['법원명']}")
        logger.info(f"선고일자: {sample['선고일자']}")
        logger.info(f"CSV 전문: {'있음' if sample['메타데이터']['CSV존재여부'] else '없음'}")

        detail = sample['상세정보']
        if detail.get('판결요지'):
            logger.info(f"\n판결요지: {detail['판결요지'][:200]}...")
        if detail.get('전문'):
            logger.info(f"\n전문 길이: {len(detail['전문'])}자")

    return output_file


# ============================================================================
# 메인 함수
# ============================================================================
def main():
    """메인 실행 함수"""
    import sys

    if len(sys.argv) < 2:
        print("사용법: python unify_to_crawling_format.py <filtered_json_file>")
        print("예제: python unify_to_crawling_format.py filtered_traffic_data/filtered_traffic_cases_20251103_170355.json")
        sys.exit(1)

    filtered_file = sys.argv[1]

    if not Path(filtered_file).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {filtered_file}")
        sys.exit(1)

    unify_training_data(filtered_file)

    logger.info("\n" + "="*60)
    logger.info("모든 작업 완료")
    logger.info("="*60)


if __name__ == "__main__":
    main()
