"""
CSV 파일의 판결문 전문을 structured_data에 추가하는 스크립트

기존: instruction, input, output만 저장 (27,436행)
추가: CSV 파일의 모든 문장 추가 (예상 +200,000행)

주의: 이 작업은 선택사항입니다. 대부분의 경우 필요하지 않습니다.
"""

import json
import csv
from pathlib import Path
import logging
from typing import Dict, List, Optional
import uuid
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_source_csv(csv_path: str) -> List[Dict]:
    """
    원천 CSV 파일 읽기

    CSV 형식:
    판례일련번호,구분,문장번호,내용
    79038,판례내용,1,【피 고 인】
    79038,판례내용,2,【항 소 인】 검사
    ...
    """
    rows = []

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                rows.append({
                    'case_id': row.get('판례일련번호', row.get('결정례일련번호', row.get('해석례일련번호', ''))),
                    'section_type': row.get('구분', ''),
                    'sentence_number': int(row.get('문장번호', 0)),
                    'content': row.get('내용', '')
                })

    except FileNotFoundError:
        logger.warning(f"CSV 파일 없음: {csv_path}")
    except Exception as e:
        logger.error(f"CSV 읽기 실패: {csv_path} - {str(e)}")

    return rows


def add_csv_fulltext(input_file: str, output_file: str = None):
    """
    CSV 전문을 structured_data에 추가

    Args:
        input_file: 입력 JSON 파일 (converted_training_db_format_*.json)
        output_file: 출력 JSON 파일 (None이면 자동 생성)
    """
    logger.info("="*60)
    logger.info("CSV 전문 추가 시작")
    logger.info("="*60)
    logger.info(f"입력 파일: {input_file}")

    # 입력 파일 읽기
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    documents = data['documents']
    structured_data = data['structured_data']

    logger.info(f"\n기존 Structured Data: {len(structured_data):,}행")
    logger.info(f"Documents: {len(documents):,}건")

    # CSV 파일이 있는 케이스 찾기
    csv_available = sum(1 for doc in documents if doc['metadata'].get('source_csv_path'))
    logger.info(f"CSV 경로 정보 있는 케이스: {csv_available:,}건")

    # CSV 내용 추가
    added_count = 0
    failed_count = 0
    total_sentences = 0

    for i, doc in enumerate(documents):
        if (i + 1) % 100 == 0:
            logger.info(f"  진행: {i+1:,}/{len(documents):,} (추가: {added_count:,}건, {total_sentences:,}문장)")

        csv_path = doc['metadata'].get('source_csv_path')

        if not csv_path:
            continue

        # CSV 파일 읽기
        csv_rows = read_source_csv(csv_path)

        if not csv_rows:
            failed_count += 1
            continue

        # CSV 내용을 structured_data에 추가
        doc_id = doc['id']
        case_id = doc['metadata'].get('source_identifier', doc['id'])

        # 기존 sentence_number의 최대값 찾기 (instruction=1, input=2, output=3)
        base_sentence_num = 10  # CSV 내용은 10번부터 시작

        for row in csv_rows:
            structured_data.append({
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "source_id": case_id,
                "section_type": row['section_type'],  # 판례내용, 참조조문, 참조판례 등
                "sentence_number": base_sentence_num + row['sentence_number'],
                "content": row['content'],
                "page_number": 1,
                "created_at": datetime.now().isoformat(),
                "metadata": {
                    "source": "csv_fulltext",
                    "original_sentence_number": row['sentence_number']
                }
            })
            total_sentences += 1

        added_count += 1

    # 결과 저장
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"converted_training_data/converted_with_fulltext_{timestamp}.json"

    data['structured_data'] = structured_data
    data['metadata']['csv_fulltext_added'] = True
    data['metadata']['csv_fulltext_added_date'] = datetime.now().isoformat()
    data['metadata']['csv_fulltext_stats'] = {
        'added_documents': added_count,
        'failed_documents': failed_count,
        'total_sentences': total_sentences
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 통계
    logger.info("\n" + "="*60)
    logger.info("CSV 전문 추가 완료")
    logger.info("="*60)
    logger.info(f"기존 Structured Data: 27,436행")
    logger.info(f"추가된 Structured Data: {total_sentences:,}행")
    logger.info(f"최종 Structured Data: {len(structured_data):,}행")
    logger.info(f"\n성공: {added_count:,}건")
    logger.info(f"실패: {failed_count:,}건 (CSV 파일 없음)")
    logger.info(f"\n출력 파일: {output_file}")

    # 파일 크기 비교
    import os
    input_size = os.path.getsize(input_file) / (1024*1024)
    output_size = os.path.getsize(output_file) / (1024*1024)
    logger.info(f"\n파일 크기:")
    logger.info(f"  입력: {input_size:.1f}MB")
    logger.info(f"  출력: {output_size:.1f}MB ({output_size/input_size:.1f}배)")


def main():
    """메인 실행 함수"""
    import sys

    if len(sys.argv) < 2:
        print("사용법: python add_csv_fulltext_to_structured_data.py <input_json_file>")
        print("예제: python add_csv_fulltext_to_structured_data.py converted_training_data/converted_training_db_format_20251103_170534.json")
        print("\n⚠️  주의: 이 작업은 선택사항입니다.")
        print("   대부분의 경우 output_text에 있는 판결 요지로 충분합니다.")
        print("   CSV 전문이 정말 필요한 경우에만 실행하세요.")
        sys.exit(1)

    input_file = sys.argv[1]

    if not Path(input_file).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        sys.exit(1)

    # 확인 받기
    print("\n⚠️  CSV 전문 추가 확인")
    print("="*60)
    print("이 작업은 다음과 같은 영향이 있습니다:")
    print("  - 파일 크기: 56MB → 약 300MB (5~6배 증가)")
    print("  - Structured Data: 27,436행 → 약 200,000행")
    print("  - 처리 시간: 약 10~20분 소요")
    print("\n대부분의 경우 이 작업은 필요하지 않습니다.")
    print("output_text에 이미 판결 요지가 포함되어 있습니다.")
    print("="*60)

    response = input("\n계속 진행하시겠습니까? (yes/no): ")

    if response.lower() != 'yes':
        print("취소되었습니다.")
        sys.exit(0)

    add_csv_fulltext(input_file)

    logger.info("\n" + "="*60)
    logger.info("모든 작업 완료")
    logger.info("="*60)


if __name__ == "__main__":
    main()
