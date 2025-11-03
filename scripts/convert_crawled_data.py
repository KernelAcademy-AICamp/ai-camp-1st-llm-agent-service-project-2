"""
크롤링 데이터 → 시스템 DB 형식 변환
법제처 OpenAPI 데이터를 PostgreSQL 모델 형식으로 변환
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 데이터 형식 비교
# ============================================================================
"""
크롤링 데이터 형식 (법제처 OpenAPI):
{
  "검색어": "교통사고",
  "데이터타입": "판례",
  "사건번호": "2023도1234",
  "선고일자": "2023-05-15",
  "법원명": "대법원",
  "판례일련번호": "202305151234",
  "상세정보": {
    "판례내용": {...},
    "참조조문": "도로교통법 제148조..."
  }
}

시스템 DB 형식 (PostgreSQL):
1. documents 테이블:
   - id (UUID)
   - filename, file_hash
   - document_type: precedent/interpretation
   - storage_type: public
   - ocr_status: completed (크롤링 데이터는 이미 텍스트)

2. document_structured_data 테이블:
   - source_id: 판례일련번호
   - section_type: 판시사항/판결요지/참조조문
   - content: 실제 텍스트

3. document_ai_labels 테이블:
   - case_name, case_number, decision_date
   - court_name
   - instruction, input_text, output_text (AI 학습용)

차이점 분석:
✅ 장점: 시스템 DB가 더 구조화되고 OCR/AI 학습에 최적화
❌ 단점: 변환 과정 필요, 크롤링 원본 데이터 일부 손실 가능

권장 사항:
1. 크롤링 원본 데이터는 JSON 파일로 별도 보관 (백업/검증용)
2. 변환된 데이터만 PostgreSQL에 저장
3. document 테이블에 원본 JSON 경로 참조 추가
"""


# ============================================================================
# 변환 함수
# ============================================================================
def convert_precedent_to_document(case_data: Dict) -> Dict:
    """
    판례 데이터 → Document 모델 형식 변환

    Args:
        case_data: 크롤링된 판례 데이터

    Returns:
        Document 형식 딕셔너리
    """
    doc_id = str(uuid.uuid4())

    # 파일명 생성 (판례일련번호 기반)
    case_id = case_data.get("판례일련번호", str(uuid.uuid4())[:8])
    filename = f"precedent_{case_id}.json"

    document = {
        "id": doc_id,
        "filename": filename,
        "original_filename": filename,
        "file_size": len(json.dumps(case_data, ensure_ascii=False)),
        "file_hash": "",  # SHA-256 해시 계산 필요
        "mime_type": "application/json",
        "document_type": "precedent",
        "storage_type": "public",  # 판례는 공개 데이터
        "is_public": True,
        "storage_path": f"public-docs/precedents/{case_id}.json",
        "is_encrypted": False,
        "ocr_status": "completed",  # 크롤링 데이터는 이미 텍스트
        "ocr_completed_at": datetime.now().isoformat(),
        "ocr_confidence": 100.0,  # 크롤링 데이터는 100%
        "page_count": 1,
        "title": case_data.get("사건번호"),
        "description": f"{case_data.get('법원명')} {case_data.get('선고일자')}",
        "tags": [
            case_data.get("검색어"),
            "판례",
            case_data.get("법원명"),
            case_data.get("사건종류명")
        ],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    return document


def convert_precedent_to_structured_data(case_data: Dict, document_id: str) -> List[Dict]:
    """
    판례 데이터 → DocumentStructuredData 형식 변환

    Args:
        case_data: 크롤링된 판례 데이터
        document_id: 문서 ID

    Returns:
        DocumentStructuredData 형식 딕셔너리 리스트
    """
    structured_rows = []
    case_id = case_data.get("판례일련번호")

    detail = case_data.get("상세정보", {})

    if isinstance(detail, dict):
        content = detail.get("판례내용", {})

        # 판시사항
        if "판시사항" in content:
            structured_rows.append({
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "source_id": case_id,
                "section_type": "판시사항",
                "sentence_number": 1,
                "content": str(content["판시사항"]),
                "page_number": 1,
                "created_at": datetime.now().isoformat()
            })

        # 판결요지
        if "판결요지" in content:
            structured_rows.append({
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "source_id": case_id,
                "section_type": "판결요지",
                "sentence_number": 2,
                "content": str(content["판결요지"]),
                "page_number": 1,
                "created_at": datetime.now().isoformat()
            })

        # 참조조문
        if "참조조문" in content:
            structured_rows.append({
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "source_id": case_id,
                "section_type": "참조조문",
                "sentence_number": 3,
                "content": str(content["참조조문"]),
                "page_number": 1,
                "created_at": datetime.now().isoformat()
            })

        # 전문 (있는 경우)
        if "전문" in content:
            structured_rows.append({
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "source_id": case_id,
                "section_type": "전문",
                "sentence_number": 4,
                "content": str(content["전문"]),
                "page_number": 1,
                "created_at": datetime.now().isoformat()
            })

    return structured_rows


def convert_precedent_to_ai_label(case_data: Dict, document_id: str) -> Dict:
    """
    판례 데이터 → DocumentAILabel 형식 변환

    Args:
        case_data: 크롤링된 판례 데이터
        document_id: 문서 ID

    Returns:
        DocumentAILabel 형식 딕셔너리
    """
    detail = case_data.get("상세정보", {})
    content = detail.get("판례내용", {}) if isinstance(detail, dict) else {}

    # AI 학습용 데이터 생성
    # Input: 사건 정보 + 참조조문
    # Output: 판결요지

    input_parts = []
    if "사건번호" in case_data:
        input_parts.append(f"사건번호: {case_data['사건번호']}")
    if "법원명" in case_data:
        input_parts.append(f"법원: {case_data['법원명']}")
    if "참조조문" in content:
        input_parts.append(f"참조조문: {content['참조조문']}")

    input_text = " | ".join(input_parts)
    output_text = content.get("판결요지", "")

    ai_label = {
        "id": str(uuid.uuid4()),
        "document_id": document_id,
        "law_class": "02",  # 판례
        "docu_type": "02",  # 판례
        "source_identifier": case_data.get("판례일련번호"),
        "case_name": case_data.get("사건번호"),
        "case_number": case_data.get("사건번호"),
        "decision_date": case_data.get("선고일자"),
        "court_name": case_data.get("법원명"),
        "instruction": "다음 사건의 판결요지를 설명하세요.",
        "input_text": input_text,
        "output_text": output_text,
        "origin_word_count": len(output_text.split()) if output_text else 0,
        "label_word_count": len(output_text.split()) if output_text else 0,
        "label_type": "QA",
        "generated_by": "CRAWLING",
        "quality_score": 95.0,  # 법제처 공식 데이터이므로 높은 점수
        "created_at": datetime.now().isoformat()
    }

    return ai_label


def convert_interpretation_to_document(case_data: Dict) -> Dict:
    """해석례 데이터 → Document 모델 형식 변환"""
    doc_id = str(uuid.uuid4())

    case_id = case_data.get("해석례일련번호", str(uuid.uuid4())[:8])
    filename = f"interpretation_{case_id}.json"

    document = {
        "id": doc_id,
        "filename": filename,
        "original_filename": filename,
        "file_size": len(json.dumps(case_data, ensure_ascii=False)),
        "file_hash": "",
        "mime_type": "application/json",
        "document_type": "interpretation",
        "storage_type": "public",
        "is_public": True,
        "storage_path": f"public-docs/interpretations/{case_id}.json",
        "is_encrypted": False,
        "ocr_status": "completed",
        "ocr_completed_at": datetime.now().isoformat(),
        "ocr_confidence": 100.0,
        "page_count": 1,
        "title": case_data.get("안건명"),
        "description": f"{case_data.get('소관부처')} {case_data.get('해석일자')}",
        "tags": [
            case_data.get("검색어"),
            "해석례",
            case_data.get("소관부처")
        ],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    return document


# ============================================================================
# 배치 변환 함수
# ============================================================================
def convert_crawled_file(input_file: str, output_dir: str = "converted_data"):
    """
    크롤링 JSON 파일 → DB 형식 변환

    Args:
        input_file: 입력 JSON 파일 경로
        output_dir: 출력 디렉토리
    """
    logger.info(f"파일 변환 시작: {input_file}")

    # 출력 디렉토리 생성
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # 입력 파일 읽기
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 결과 저장
    results = {
        "documents": [],
        "structured_data": [],
        "ai_labels": []
    }

    # 판례 변환
    precedents = data.get("판례", [])
    logger.info(f"판례 {len(precedents)}건 변환 중...")

    for case in precedents:
        doc = convert_precedent_to_document(case)
        results["documents"].append(doc)

        structured = convert_precedent_to_structured_data(case, doc["id"])
        results["structured_data"].extend(structured)

        ai_label = convert_precedent_to_ai_label(case, doc["id"])
        results["ai_labels"].append(ai_label)

    # 해석례 변환
    interpretations = data.get("해석례", [])
    logger.info(f"해석례 {len(interpretations)}건 변환 중...")

    for case in interpretations:
        doc = convert_interpretation_to_document(case)
        results["documents"].append(doc)

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"converted_db_format_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 통계
    logger.info("\n" + "="*60)
    logger.info("변환 완료")
    logger.info("="*60)
    logger.info(f"Documents: {len(results['documents'])}건")
    logger.info(f"Structured Data: {len(results['structured_data'])}행")
    logger.info(f"AI Labels: {len(results['ai_labels'])}건")
    logger.info(f"\n출력 파일: {output_file}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법: python convert_crawled_data.py <input_json_file>")
        print("예제: python convert_crawled_data.py traffic_legal_data_20231103.json")
        sys.exit(1)

    input_file = sys.argv[1]

    if not Path(input_file).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        sys.exit(1)

    convert_crawled_file(input_file)
