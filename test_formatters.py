"""
CSV/JSON 포맷터 테스트
"""

from app.services.ocr_pipeline import OCRPipeline
from app.services.formatters import CSVFormatter, JSONFormatter


def test_formatters():
    """포맷터 통합 테스트"""
    print("=" * 60)
    print("CSV/JSON 포맷터 테스트")
    print("=" * 60)

    # 1. OCR 처리
    print("\n[1] PDF OCR 처리...")
    pipeline = OCRPipeline(
        engine_name='tesseract',
        dpi=300,
        enable_preprocessing=True
    )

    ocr_result = pipeline.process_pdf("sample_legal_document.pdf")
    print(f"✅ OCR 완료: {ocr_result.processed_pages} 페이지")

    # 2. CSV 포맷팅
    print("\n[2] CSV 포맷팅...")
    csv_formatter = CSVFormatter()

    structured_rows = csv_formatter.format_ocr_result(
        ocr_result,
        output_path="output_structured.csv"
    )

    print(f"✅ CSV 생성 완료: {len(structured_rows)} 행")
    print("\n처음 5행:")
    for i, row in enumerate(structured_rows[:5]):
        print(f"  {i+1}. [{row.section_type}] {row.content[:50]}...")

    # 3. JSON 포맷팅
    print("\n[3] JSON 포맷팅...")
    json_formatter = JSONFormatter()

    json_data = json_formatter.format_ocr_result(
        ocr_result,
        output_path="output_document.json"
    )

    print(f"✅ JSON 생성 완료")
    print(f"   문서 ID: {json_data['document_id']}")
    print(f"   페이지 수: {json_data['metadata']['total_pages']}")
    print(f"   평균 신뢰도: {json_data['metadata']['average_confidence']:.2f}%")

    # 4. AI 학습용 데이터
    print("\n[4] AI 학습용 데이터 생성...")

    # 요약 작업
    ai_data_summary = json_formatter.format_for_ai_training(
        ocr_result,
        task_type='summarization',
        output_path="output_ai_summarization.json"
    )
    print(f"✅ 요약 작업 데이터: {len(ai_data_summary)} 샘플")

    # 분류 작업
    ai_data_classification = json_formatter.format_for_ai_training(
        ocr_result,
        task_type='classification',
        output_path="output_ai_classification.json"
    )
    print(f"✅ 분류 작업 데이터: {len(ai_data_classification)} 샘플")

    # 5. 생성된 파일 확인
    print("\n" + "=" * 60)
    print("생성된 파일")
    print("=" * 60)

    import os
    files = [
        "output_structured.csv",
        "output_document.json",
        "output_ai_summarization.json",
        "output_ai_classification.json"
    ]

    for filename in files:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"✅ {filename} ({size} bytes)")
        else:
            print(f"❌ {filename} (없음)")

    # 6. CSV 내용 미리보기
    print("\n" + "=" * 60)
    print("CSV 내용 미리보기 (처음 10줄)")
    print("=" * 60)

    with open("output_structured.csv", 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 10:
                break
            print(line.rstrip())

    # 7. JSON 내용 미리보기
    print("\n" + "=" * 60)
    print("JSON 내용 미리보기")
    print("=" * 60)

    import json
    with open("output_document.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(json.dumps(data, indent=2, ensure_ascii=False)[:500] + "...")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    test_formatters()
