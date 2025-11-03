"""
필터링된 학습 데이터 → 시스템 DB 형식 변환
filtered_traffic_cases_*.json 파일을 PostgreSQL 모델 형식으로 변환
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 데이터 형식 설명
# ============================================================================
"""
입력 형식 (필터링된 학습 데이터):
{
  "metadata": {...},
  "cases": [
    {
      "case_id": "78434",
      "case_type": "판결문",
      "data_type": "QA",
      "file_path": "...",
      "info": {
        "precedId": "78434",
        "caseName": "...",
        "caseNum": "2007노1012",
        "sentenceDate": "2007.05.01",
        "courtName": "부산지방법원"
      },
      "label": {
        "instruction": "...",
        "input": "...",
        "output": "..."
      },
      "matched_keywords": [...],
      "is_strong_match": false
    }
  ]
}

출력 형식 (PostgreSQL):
1. documents 테이블: 문서 메타데이터
2. document_structured_data 테이블: 구조화된 내용 (CSV 형식)
3. document_ai_labels 테이블: AI 학습 데이터
"""


# ============================================================================
# 유틸리티 함수
# ============================================================================
def generate_file_hash(content: str) -> str:
    """문자열 콘텐츠의 SHA-256 해시 생성"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def extract_source_csv_path(case_data: Dict) -> Optional[str]:
    """
    원천 CSV 파일 경로 추출

    예: TL_판결문_QA/HS_P_78434_QA_8099.json → TS_판결문/HS_P_78434.csv
    """
    file_path = case_data.get("file_path", "")

    if not file_path:
        return None

    # 라벨링데이터 경로를 원천데이터 경로로 변환
    if "02.라벨링데이터" in file_path:
        # 파일명에서 케이스 ID 추출
        file_name = Path(file_path).stem  # HS_P_78434_QA_8099
        parts = file_name.split("_")

        if len(parts) >= 3:
            # HS_P_78434
            case_prefix = "_".join(parts[:3])

            # 케이스 타입에 따라 원천 데이터 디렉토리 결정
            case_type = case_data.get("case_type", "")

            if case_type == "판결문":
                source_dir = "TS_판결문"
            elif case_type == "결정례":
                source_dir = "TS_결정례"
            elif case_type == "해석례":
                source_dir = "TS_해석례"
            elif case_type == "법령":
                source_dir = "TS_법령"
            else:
                return None

            # 원천 경로 생성
            source_path = file_path.replace("02.라벨링데이터", "01.원천데이터")
            source_path = source_path.replace(Path(file_path).parts[-2], source_dir)
            source_path = source_path.replace(file_name + ".json", case_prefix + ".csv")

            return source_path

    return None


# ============================================================================
# 변환 함수
# ============================================================================
def convert_case_to_document(case_data: Dict, source_csv_exists: bool = False) -> Dict:
    """
    케이스 데이터 → Document 모델 형식 변환

    Args:
        case_data: 필터링된 케이스 데이터
        source_csv_exists: 원천 CSV 파일 존재 여부

    Returns:
        Document 형식 딕셔너리
    """
    doc_id = str(uuid.uuid4())

    # 기본 정보
    case_id = case_data.get("case_id", str(uuid.uuid4())[:8])
    case_type = case_data.get("case_type", "판결문")
    data_type = case_data.get("data_type", "QA")
    info = case_data.get("info", {})

    # 파일명 생성
    filename = f"{case_type}_{case_id}_{data_type}.json"

    # 전체 텍스트 생성 (해시 계산용)
    label = case_data.get("label", {})
    full_content = json.dumps(case_data, ensure_ascii=False)
    file_hash = generate_file_hash(full_content)

    # 문서 타입 결정
    document_type_map = {
        "판결문": "precedent",
        "결정례": "decision",
        "해석례": "interpretation",
        "법령": "statute"
    }
    document_type = document_type_map.get(case_type, "precedent")

    # 제목 생성
    title = info.get("caseName") or info.get("caseNum") or case_id

    # 설명 생성
    description_parts = []
    if "courtName" in info:
        description_parts.append(info["courtName"])
    if "sentenceDate" in info:
        description_parts.append(info["sentenceDate"])
    description = " ".join(description_parts) if description_parts else f"{case_type} {data_type}"

    # 태그 생성
    tags = [case_type, data_type]
    if "courtName" in info:
        tags.append(info["courtName"])
    if case_data.get("is_strong_match"):
        tags.append("강한매칭")
    tags.extend(case_data.get("matched_keywords", [])[:5])  # 상위 5개 키워드

    document = {
        "id": doc_id,
        "filename": filename,
        "original_filename": filename,
        "file_size": len(full_content),
        "file_hash": file_hash,
        "mime_type": "application/json",
        "document_type": document_type,
        "storage_type": "public",  # 학습 데이터는 공개
        "is_public": True,
        "storage_path": f"public-docs/training/{case_type}/{case_id}.json",
        "is_encrypted": False,
        "ocr_status": "completed",  # 이미 텍스트 데이터
        "ocr_completed_at": datetime.now().isoformat(),
        "ocr_confidence": 100.0,
        "page_count": 1,
        "title": title,
        "description": description,
        "tags": tags,
        "metadata": {
            "source": "training_data",
            "original_file_path": case_data.get("file_path"),
            "source_csv_path": extract_source_csv_path(case_data),
            "source_csv_exists": source_csv_exists,
            "matched_keywords": case_data.get("matched_keywords", []),
            "is_strong_match": case_data.get("is_strong_match", False)
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    return document


def convert_case_to_structured_data(case_data: Dict, document_id: str) -> List[Dict]:
    """
    케이스 데이터 → DocumentStructuredData 형식 변환

    학습 데이터는 이미 QA/SUM 형식으로 정리되어 있으므로,
    label의 instruction, input, output을 별도 행으로 저장

    Args:
        case_data: 필터링된 케이스 데이터
        document_id: 문서 ID

    Returns:
        DocumentStructuredData 형식 딕셔너리 리스트
    """
    structured_rows = []
    case_id = case_data.get("case_id")
    label = case_data.get("label", {})

    # Instruction
    if "instruction" in label and label["instruction"]:
        structured_rows.append({
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "source_id": case_id,
            "section_type": "instruction",
            "sentence_number": 1,
            "content": str(label["instruction"]),
            "page_number": 1,
            "created_at": datetime.now().isoformat()
        })

    # Input (질문/입력)
    if "input" in label and label["input"]:
        structured_rows.append({
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "source_id": case_id,
            "section_type": "input",
            "sentence_number": 2,
            "content": str(label["input"]),
            "page_number": 1,
            "created_at": datetime.now().isoformat()
        })

    # Output (답변/출력)
    if "output" in label and label["output"]:
        structured_rows.append({
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "source_id": case_id,
            "section_type": "output",
            "sentence_number": 3,
            "content": str(label["output"]),
            "page_number": 1,
            "created_at": datetime.now().isoformat()
        })

    return structured_rows


def convert_case_to_ai_label(case_data: Dict, document_id: str) -> Dict:
    """
    케이스 데이터 → DocumentAILabel 형식 변환

    Args:
        case_data: 필터링된 케이스 데이터
        document_id: 문서 ID

    Returns:
        DocumentAILabel 형식 딕셔너리
    """
    info = case_data.get("info", {})
    label = case_data.get("label", {})
    case_type = case_data.get("case_type", "판결문")
    data_type = case_data.get("data_type", "QA")

    # 문서 타입 코드
    docu_type_map = {
        "판결문": "02",
        "결정례": "03",
        "해석례": "04",
        "법령": "05"
    }

    instruction = label.get("instruction", "")
    input_text = label.get("input", "")
    output_text = label.get("output", "")

    ai_label = {
        "id": str(uuid.uuid4()),
        "document_id": document_id,
        "law_class": info.get("lawClass", "02"),
        "docu_type": docu_type_map.get(case_type, "02"),
        "source_identifier": case_data.get("case_id"),
        "case_name": info.get("caseName"),
        "case_number": info.get("caseNum"),
        "decision_date": info.get("sentenceDate"),
        "court_name": info.get("courtName"),
        "instruction": instruction,
        "input_text": input_text,
        "output_text": output_text,
        "origin_word_count": len(output_text.split()) if output_text else 0,
        "label_word_count": len(output_text.split()) if output_text else 0,
        "label_type": data_type,  # QA, SUM
        "generated_by": "TRAINING_DATA",
        "quality_score": 90.0,  # 공식 학습 데이터이므로 높은 점수
        "metadata": {
            "matched_keywords": case_data.get("matched_keywords", []),
            "is_strong_match": case_data.get("is_strong_match", False),
            "sentence_type": info.get("sentenceType"),
            "full_text_available": info.get("fullText") == "Y"
        },
        "created_at": datetime.now().isoformat()
    }

    return ai_label


# ============================================================================
# 배치 변환 함수
# ============================================================================
def convert_filtered_file(input_file: str, output_dir: str = "converted_training_data"):
    """
    필터링된 JSON 파일 → DB 형식 변환

    Args:
        input_file: 입력 JSON 파일 경로 (filtered_traffic_cases_*.json)
        output_dir: 출력 디렉토리
    """
    logger.info("="*60)
    logger.info("필터링된 학습 데이터 변환 시작")
    logger.info("="*60)
    logger.info(f"입력 파일: {input_file}")

    # 출력 디렉토리 생성
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # 입력 파일 읽기
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    cases = data.get("cases", [])

    logger.info(f"\n총 케이스 수: {len(cases):,}건")
    logger.info(f"데이터 타입별:")
    for type_key, count in metadata.get("by_type", {}).items():
        logger.info(f"  {type_key}: {count:,}건")

    # 결과 저장
    results = {
        "metadata": {
            "conversion_date": datetime.now().isoformat(),
            "source_file": input_file,
            "original_metadata": metadata
        },
        "documents": [],
        "structured_data": [],
        "ai_labels": []
    }

    # 변환 진행
    logger.info(f"\n변환 중...")

    for i, case in enumerate(cases):
        if (i + 1) % 1000 == 0:
            logger.info(f"  진행: {i+1:,}/{len(cases):,} ({(i+1)/len(cases)*100:.1f}%)")

        try:
            # Document 변환
            doc = convert_case_to_document(case)
            results["documents"].append(doc)

            # Structured Data 변환
            structured = convert_case_to_structured_data(case, doc["id"])
            results["structured_data"].extend(structured)

            # AI Label 변환
            ai_label = convert_case_to_ai_label(case, doc["id"])
            results["ai_labels"].append(ai_label)

        except Exception as e:
            logger.error(f"  케이스 변환 실패 (ID: {case.get('case_id')}): {str(e)}")
            continue

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"converted_training_db_format_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 통계
    logger.info("\n" + "="*60)
    logger.info("변환 완료")
    logger.info("="*60)
    logger.info(f"Documents: {len(results['documents']):,}건")
    logger.info(f"Structured Data: {len(results['structured_data']):,}행")
    logger.info(f"AI Labels: {len(results['ai_labels']):,}건")
    logger.info(f"\n출력 파일: {output_file}")

    # 샘플 출력
    if results["documents"]:
        logger.info("\n" + "="*60)
        logger.info("샘플 Document (첫 번째)")
        logger.info("="*60)
        sample = results["documents"][0]
        logger.info(f"ID: {sample['id']}")
        logger.info(f"Title: {sample['title']}")
        logger.info(f"Type: {sample['document_type']} ({sample['storage_type']})")
        logger.info(f"Tags: {', '.join(sample['tags'][:5])}")
        logger.info(f"Matched Keywords: {', '.join(sample['metadata']['matched_keywords'][:5])}")

    return output_file


# ============================================================================
# 메인 함수
# ============================================================================
def main():
    """메인 실행 함수"""
    import sys

    if len(sys.argv) < 2:
        print("사용법: python convert_filtered_training_data.py <filtered_json_file>")
        print("예제: python convert_filtered_training_data.py filtered_traffic_data/filtered_traffic_cases_20251103_170355.json")
        sys.exit(1)

    input_file = sys.argv[1]

    if not Path(input_file).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        sys.exit(1)

    convert_filtered_file(input_file)

    logger.info("\n" + "="*60)
    logger.info("모든 작업 완료")
    logger.info("="*60)


if __name__ == "__main__":
    main()
