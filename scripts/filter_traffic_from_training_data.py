"""
.data 폴더의 형사법 LLM 학습 데이터에서 교통 관련 데이터 필터링
크롤링 코드와 동일한 키워드 및 필터링 방식 적용
"""

import json
import csv
import os
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 크롤링 코드와 동일한 키워드
# ============================================================================
TRAFFIC_KEYWORDS = [
    # 기본 키워드
    "교통사고", "도로교통법", "차량", "자동차",

    # 위반 행위
    "음주운전", "무면허운전", "무면허", "신호위반", "속도위반", "과속",
    "중앙선침범", "중앙선", "차선위반", "안전거리미확보", "끼어들기",
    "난폭운전", "보복운전", "뺑소니", "도주", "사고후도주",
    "구호조치불이행", "음주측정거부",

    # 법규
    "교통사고처리특례법", "특정범죄가중처벌등에관한법률",
    "교통법규", "교통단속", "음주측정",

    # 운전/차량
    "운전", "운전면허", "면허취소", "면허정지",
    "차량운행", "정차", "주차", "주정차위반",

    # 사고 유형
    "추돌사고", "추돌", "접촉사고", "전복사고", "인명사고",
    "보행자", "횡단보도", "인도", "자전거도로",

    # 기타
    "교통체계", "도로", "고속도로", "자동차전용도로",
    "이륜차", "오토바이", "자전거", "전동킥보드"
]

# 강한 키워드 (높은 연관성)
STRONG_KEYWORDS = [
    "교통사고", "도로교통법", "음주운전", "뺑소니",
    "교통사고처리특례법", "무면허운전", "신호위반"
]


# ============================================================================
# 데이터 구조
# ============================================================================
@dataclass
class SourceData:
    """원천 데이터 (CSV)"""
    case_id: str
    section_type: str
    sentence_number: int
    content: str


@dataclass
class LabelData:
    """라벨링 데이터 (JSON)"""
    file_path: str
    info: Dict
    label: Dict


@dataclass
class FilteredCase:
    """필터링된 케이스"""
    case_id: str
    case_type: str  # 판결문/결정례/해석례/법령
    data_type: str  # QA/SUM
    source_data: Optional[List[SourceData]]
    label_data: LabelData
    matched_keywords: List[str]
    is_strong_match: bool


# ============================================================================
# 필터링 함수 (크롤링과 동일한 로직)
# ============================================================================
def is_traffic_related(text: str, threshold: int = 1) -> tuple[bool, List[str], bool]:
    """
    텍스트가 교통 관련인지 판단

    Args:
        text: 검사할 텍스트
        threshold: 최소 매칭 키워드 수

    Returns:
        (연관성 여부, 매칭된 키워드 리스트, 강한 매칭 여부)
    """
    if not text:
        return False, [], False

    text_lower = text.lower()
    matched_keywords = []
    strong_match = False

    for keyword in TRAFFIC_KEYWORDS:
        if keyword.lower() in text_lower:
            matched_keywords.append(keyword)

            # 강한 키워드 매칭 확인
            if keyword in STRONG_KEYWORDS:
                strong_match = True

    # 판단 로직
    # 1. 강한 키워드가 하나라도 있으면 연관 있음
    if strong_match:
        return True, matched_keywords, True

    # 2. 일반 키워드가 threshold 이상이면 연관 있음
    if len(matched_keywords) >= threshold:
        return True, matched_keywords, False

    return False, matched_keywords, False


def check_label_file_traffic_related(file_path: str) -> Optional[tuple[bool, List[str], bool, Dict]]:
    """
    라벨링 JSON 파일이 교통 관련인지 확인

    Returns:
        (연관성 여부, 매칭 키워드, 강한 매칭 여부, 데이터) 또는 None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 검색할 텍스트 수집
        search_texts = []

        # info 섹션
        if 'info' in data:
            info = data['info']
            if 'caseName' in info:
                search_texts.append(str(info['caseName']))

        # label 섹션
        if 'label' in data:
            label = data['label']
            if 'instruction' in label:
                search_texts.append(str(label['instruction']))
            if 'input' in label:
                search_texts.append(str(label['input']))
            if 'output' in label:
                search_texts.append(str(label['output']))

        # 전체 텍스트 결합
        full_text = " ".join(search_texts)

        # 연관성 판단
        is_related, keywords, strong = is_traffic_related(full_text)

        return is_related, keywords, strong, data

    except Exception as e:
        logger.warning(f"파일 읽기 실패: {file_path} - {str(e)}")
        return None


def read_source_csv(file_path: str) -> List[SourceData]:
    """
    원천 CSV 파일 읽기

    Returns:
        SourceData 리스트
    """
    source_data = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                source_data.append(SourceData(
                    case_id=row['판례일련번호'] if '판례일련번호' in row else row.get('해석례일련번호', row.get('결정례일련번호', '')),
                    section_type=row['구분'],
                    sentence_number=int(row['문장번호']),
                    content=row['내용']
                ))

    except Exception as e:
        logger.warning(f"CSV 읽기 실패: {file_path} - {str(e)}")

    return source_data


# ============================================================================
# 필터링 메인 함수
# ============================================================================
def filter_training_data(
    data_dir: str,
    output_dir: str = "filtered_traffic_data",
    max_workers: int = 4
):
    """
    학습 데이터에서 교통 관련 데이터 필터링

    Args:
        data_dir: .data 디렉토리 경로
        output_dir: 출력 디렉토리
        max_workers: 병렬 처리 워커 수
    """
    logger.info("="*60)
    logger.info("교통 관련 데이터 필터링 시작")
    logger.info("="*60)
    logger.info(f"입력 디렉토리: {data_dir}")
    logger.info(f"출력 디렉토리: {output_dir}")

    data_path = Path(data_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    # 라벨링 데이터 디렉토리
    label_dirs = [
        "Training/02.라벨링데이터/TL_판결문_QA",
        "Training/02.라벨링데이터/TL_판결문_SUM",
        "Training/02.라벨링데이터/TL_결정례_QA",
        "Training/02.라벨링데이터/TL_해석례_SUM",
        "Training/02.라벨링데이터/TL_법령_QA",
    ]

    # 원천 데이터 디렉토리
    source_dirs = {
        "판결문": "Training/01.원천데이터/TS_판결문",
        "결정례": "Training/01.원천데이터/TS_결정례",
        "해석례": "Training/01.원천데이터/TS_해석례",
        "법령": "Training/01.원천데이터/TS_법령",
    }

    # 통계
    stats = {
        "total_files": 0,
        "traffic_related": 0,
        "strong_match": 0,
        "by_type": {}
    }

    filtered_cases = []

    # 라벨링 데이터 처리
    for label_dir in label_dirs:
        full_label_dir = data_path / label_dir

        if not full_label_dir.exists():
            logger.warning(f"디렉토리 없음: {full_label_dir}")
            continue

        # JSON 파일 목록
        json_files = list(full_label_dir.glob("*.json"))
        stats["total_files"] += len(json_files)

        logger.info(f"\n처리 중: {label_dir}")
        logger.info(f"  파일 수: {len(json_files):,}개")

        # 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(check_label_file_traffic_related, str(f)): f
                for f in json_files
            }

            processed = 0
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                processed += 1

                if processed % 1000 == 0:
                    logger.info(f"  진행: {processed:,}/{len(json_files):,} ({processed/len(json_files)*100:.1f}%)")

                try:
                    result = future.result()

                    if result:
                        is_related, keywords, strong, data = result

                        if is_related:
                            stats["traffic_related"] += 1

                            if strong:
                                stats["strong_match"] += 1

                            # 케이스 타입 파악
                            if "판결문_QA" in label_dir:
                                case_type = "판결문"
                                data_type = "QA"
                            elif "판결문_SUM" in label_dir:
                                case_type = "판결문"
                                data_type = "SUM"
                            elif "결정례_QA" in label_dir:
                                case_type = "결정례"
                                data_type = "QA"
                            elif "해석례_SUM" in label_dir:
                                case_type = "해석례"
                                data_type = "SUM"
                            elif "법령_QA" in label_dir:
                                case_type = "법령"
                                data_type = "QA"
                            else:
                                case_type = "기타"
                                data_type = "UNKNOWN"

                            # 통계
                            key = f"{case_type}_{data_type}"
                            stats["by_type"][key] = stats["by_type"].get(key, 0) + 1

                            # 케이스 ID 추출
                            case_id = data.get("info", {}).get("precedId") or \
                                     data.get("info", {}).get("determintId") or \
                                     data.get("info", {}).get("interpreId") or \
                                     file_path.stem

                            # 필터링된 케이스 추가
                            filtered_case = FilteredCase(
                                case_id=case_id,
                                case_type=case_type,
                                data_type=data_type,
                                source_data=None,  # 나중에 필요시 로드
                                label_data=LabelData(
                                    file_path=str(file_path),
                                    info=data.get("info", {}),
                                    label=data.get("label", {})
                                ),
                                matched_keywords=keywords,
                                is_strong_match=strong
                            )

                            filtered_cases.append(filtered_case)

                except Exception as e:
                    logger.error(f"  파일 처리 실패: {file_path} - {str(e)}")

        logger.info(f"  완료: 교통 관련 {stats['traffic_related']}건")

    # 결과 저장
    logger.info("\n" + "="*60)
    logger.info("결과 저장")
    logger.info("="*60)

    # 필터링된 데이터를 JSON으로 저장
    output_data = {
        "metadata": {
            "filtering_date": datetime.now().isoformat(),
            "source_directory": str(data_dir),
            "total_files_processed": stats["total_files"],
            "traffic_related_count": stats["traffic_related"],
            "strong_match_count": stats["strong_match"],
            "by_type": stats["by_type"],
            "keywords_used": TRAFFIC_KEYWORDS,
            "strong_keywords": STRONG_KEYWORDS
        },
        "cases": [
            {
                "case_id": case.case_id,
                "case_type": case.case_type,
                "data_type": case.data_type,
                "file_path": case.label_data.file_path,
                "info": case.label_data.info,
                "label": case.label_data.label,
                "matched_keywords": case.matched_keywords,
                "is_strong_match": case.is_strong_match
            }
            for case in filtered_cases
        ]
    }

    # JSON 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"filtered_traffic_cases_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"저장 완료: {output_file}")

    # 통계 출력
    logger.info("\n" + "="*60)
    logger.info("필터링 통계")
    logger.info("="*60)
    logger.info(f"총 처리 파일: {stats['total_files']:,}개")
    logger.info(f"교통 관련: {stats['traffic_related']:,}개 ({stats['traffic_related']/stats['total_files']*100:.2f}%)")
    logger.info(f"강한 매칭: {stats['strong_match']:,}개 ({stats['strong_match']/stats['traffic_related']*100:.2f}%)")

    logger.info("\n타입별 통계:")
    for type_key, count in sorted(stats['by_type'].items()):
        logger.info(f"  {type_key}: {count:,}개")

    # 샘플 출력
    if filtered_cases:
        logger.info("\n" + "="*60)
        logger.info("샘플 케이스 (첫 번째)")
        logger.info("="*60)
        sample = filtered_cases[0]
        logger.info(f"케이스 ID: {sample.case_id}")
        logger.info(f"타입: {sample.case_type} - {sample.data_type}")
        logger.info(f"매칭 키워드: {', '.join(sample.matched_keywords[:5])}")
        logger.info(f"강한 매칭: {sample.is_strong_match}")
        logger.info(f"\nInstruction: {sample.label_data.label.get('instruction', 'N/A')[:100]}...")
        logger.info(f"Input: {sample.label_data.label.get('input', 'N/A')[:100]}...")
        logger.info(f"Output: {sample.label_data.label.get('output', 'N/A')[:100]}...")

    return output_file


# ============================================================================
# 메인 함수
# ============================================================================
def main():
    """메인 실행 함수"""
    import sys

    if len(sys.argv) < 2:
        print("사용법: python filter_traffic_from_training_data.py <data_directory>")
        print("예제: python filter_traffic_from_training_data.py '.data/04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/3.개방데이터/1.데이터'")
        sys.exit(1)

    data_dir = sys.argv[1]

    if not Path(data_dir).exists():
        print(f"❌ 디렉토리를 찾을 수 없습니다: {data_dir}")
        sys.exit(1)

    output_file = filter_training_data(data_dir)

    logger.info("\n" + "="*60)
    logger.info("모든 작업 완료")
    logger.info("="*60)
    logger.info(f"결과 파일: {output_file}")


if __name__ == "__main__":
    main()
