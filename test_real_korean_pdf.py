"""
실제 한글 계약서 PDF OCR 테스트
"""

from app.services.ocr_pipeline import OCRPipeline
from app.services.formatters import CSVFormatter, JSONFormatter
import os


def test_korean_contract_pdf():
    """한글 계약서 PDF OCR 테스트"""
    print("=" * 60)
    print("한글 계약서 PDF OCR 테스트")
    print("=" * 60)

    pdf_path = "tests/계약서_1.pdf"

    if not os.path.exists(pdf_path):
        print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return

    # 파일 정보
    file_size = os.path.getsize(pdf_path)
    print(f"\n파일: {pdf_path}")
    print(f"크기: {file_size / 1024:.2f} KB")

    # 1. OCR 파이프라인 초기화
    print("\n" + "=" * 60)
    print("OCR 처리 시작")
    print("=" * 60)

    pipeline = OCRPipeline(
        engine_name='tesseract',
        dpi=300,
        enable_preprocessing=True,
        aggressive_preprocessing=False,
        max_workers=4
    )

    # 2. PDF 처리
    print("\nOCR 실행 중...")
    result = pipeline.process_pdf(pdf_path, document_id="계약서_001")

    # 3. 결과 출력
    print("\n" + "=" * 60)
    print("OCR 처리 결과")
    print("=" * 60)

    print(f"\n문서 ID: {result.document_id}")
    print(f"총 페이지: {result.total_pages}")
    print(f"처리 성공: {result.processed_pages}/{result.total_pages} 페이지")
    print(f"평균 신뢰도: {result.average_confidence:.2f}%")
    print(f"총 단어 수: {result.total_word_count}")
    print(f"처리 시간: {result.total_processing_time:.2f}초")
    print(f"처리 속도: {result.total_pages / result.total_processing_time:.2f} 페이지/초")

    # 4. 페이지별 상세 결과
    print("\n" + "=" * 60)
    print("페이지별 상세 결과")
    print("=" * 60)

    for page_result in result.page_results:
        print(f"\n페이지 {page_result.page_number}:")
        print(f"  신뢰도: {page_result.confidence:.2f}%")
        print(f"  단어 수: {page_result.word_count}")
        print(f"  처리 시간: {page_result.processing_time:.2f}초")

        if page_result.error:
            print(f"  ⚠️  오류: {page_result.error}")
        else:
            # 처음 200자만 미리보기
            preview = page_result.text[:200].replace('\n', ' ')
            print(f"  내용: {preview}...")

    # 5. 전체 텍스트 미리보기
    print("\n" + "=" * 60)
    print("추출된 텍스트 미리보기 (처음 500자)")
    print("=" * 60)
    print(result.total_text[:500])
    print("...")

    # 6. CSV 저장
    print("\n" + "=" * 60)
    print("CSV 형식으로 저장")
    print("=" * 60)

    csv_formatter = CSVFormatter()
    structured_rows = csv_formatter.format_ocr_result(
        result,
        output_path="계약서_structured.csv"
    )

    print(f"✅ CSV 저장 완료: 계약서_structured.csv")
    print(f"   총 {len(structured_rows)} 행")

    # 처음 5행 미리보기
    print("\n처음 5행:")
    for i, row in enumerate(structured_rows[:5]):
        print(f"  {i+1}. [{row.section_type}] {row.content[:60]}...")

    # 7. JSON 저장
    print("\n" + "=" * 60)
    print("JSON 형식으로 저장")
    print("=" * 60)

    json_formatter = JSONFormatter()

    # 일반 JSON
    json_data = json_formatter.format_ocr_result(
        result,
        output_path="계약서_document.json"
    )
    print(f"✅ JSON 저장 완료: 계약서_document.json")

    # AI 학습용 데이터
    ai_summary = json_formatter.format_for_ai_training(
        result,
        task_type='summarization',
        output_path="계약서_ai_training.json"
    )
    print(f"✅ AI 학습 데이터 저장 완료: 계약서_ai_training.json")

    # 8. 품질 평가
    print("\n" + "=" * 60)
    print("OCR 품질 평가")
    print("=" * 60)

    if result.average_confidence >= 90:
        quality = "✅ 매우 우수"
        recommendation = "전처리 없이도 훌륭한 품질입니다."
    elif result.average_confidence >= 80:
        quality = "✅ 우수"
        recommendation = "현재 설정이 최적입니다."
    elif result.average_confidence >= 70:
        quality = "⚠️  양호"
        recommendation = "일반 전처리로 개선 가능합니다."
    elif result.average_confidence >= 60:
        quality = "⚠️  보통"
        recommendation = "공격적 전처리 또는 DPI 향상을 권장합니다."
    else:
        quality = "❌ 불량"
        recommendation = "DPI 600으로 재처리 또는 원본 이미지 품질 확인 필요합니다."

    print(f"\n품질 등급: {quality}")
    print(f"신뢰도: {result.average_confidence:.2f}%")
    print(f"권장사항: {recommendation}")

    # 9. 생성된 파일 목록
    print("\n" + "=" * 60)
    print("생성된 파일")
    print("=" * 60)

    output_files = [
        "계약서_structured.csv",
        "계약서_document.json",
        "계약서_ai_training.json"
    ]

    for filename in output_files:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"✅ {filename} ({size:,} bytes)")

    # 10. 한글 인식 테스트
    print("\n" + "=" * 60)
    print("한글 인식 분석")
    print("=" * 60)

    # 한글 문자 수 세기
    korean_chars = sum(1 for c in result.total_text if '가' <= c <= '힣')
    total_chars = len(result.total_text.replace(' ', '').replace('\n', ''))

    if total_chars > 0:
        korean_ratio = (korean_chars / total_chars) * 100
        print(f"총 문자 수: {total_chars:,}")
        print(f"한글 문자 수: {korean_chars:,}")
        print(f"한글 비율: {korean_ratio:.1f}%")

        if korean_ratio > 50:
            print("✅ 한글 문서로 정상 인식되었습니다.")
        elif korean_ratio > 20:
            print("⚠️  한글과 영문이 혼합된 문서입니다.")
        else:
            print("⚠️  주로 영문으로 인식되었습니다. 한글 언어팩 확인 필요.")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

    return result


def compare_preprocessing_modes():
    """전처리 모드 비교"""
    print("\n\n" + "=" * 60)
    print("전처리 모드 비교 테스트")
    print("=" * 60)

    pdf_path = "tests/계약서_1.pdf"

    if not os.path.exists(pdf_path):
        print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return

    modes = [
        ("전처리 없음", False, False),
        ("일반 전처리", True, False),
        ("공격적 전처리", True, True)
    ]

    results = []

    for mode_name, enable_prep, aggressive in modes:
        print(f"\n[{mode_name}] 처리 중...")

        pipeline = OCRPipeline(
            engine_name='tesseract',
            dpi=300,
            enable_preprocessing=enable_prep,
            aggressive_preprocessing=aggressive
        )

        result = pipeline.process_pdf(pdf_path)
        results.append((mode_name, result))

        print(f"  신뢰도: {result.average_confidence:.2f}%")
        print(f"  처리 시간: {result.total_processing_time:.2f}초")

    # 비교 결과
    print("\n" + "=" * 60)
    print("비교 결과")
    print("=" * 60)

    print(f"\n{'모드':<15} {'신뢰도':<12} {'처리시간':<12} {'단어수':<10}")
    print("-" * 60)

    for mode_name, result in results:
        print(f"{mode_name:<15} {result.average_confidence:>7.2f}%   {result.total_processing_time:>7.2f}초   {result.total_word_count:>8,}")

    # 최고 신뢰도 찾기
    best_mode = max(results, key=lambda x: x[1].average_confidence)
    print(f"\n✅ 최고 성능: {best_mode[0]} (신뢰도 {best_mode[1].average_confidence:.2f}%)")


if __name__ == "__main__":
    # 기본 테스트
    result = test_korean_contract_pdf()

    # 전처리 비교 (선택적)
    if result and result.average_confidence < 90:
        print("\n신뢰도가 90% 미만이므로 전처리 비교 테스트를 실행합니다...")
        compare_preprocessing_modes()
