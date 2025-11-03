"""
OCR 파이프라인 통합 테스트
"""

from app.services.ocr_pipeline import OCRPipeline
import time


def test_ocr_pipeline():
    """OCR 파이프라인 전체 테스트"""
    print("=" * 60)
    print("OCR 파이프라인 통합 테스트")
    print("=" * 60)

    # 1. 파이프라인 초기화
    print("\n[1] OCR 파이프라인 초기화...")
    pipeline = OCRPipeline(
        engine_name='tesseract',
        dpi=300,
        enable_preprocessing=True,
        aggressive_preprocessing=False,
        max_workers=4
    )
    print("✅ 초기화 완료")

    # 2. PDF 처리
    pdf_path = "sample_legal_document.pdf"
    print(f"\n[2] PDF 처리: {pdf_path}")

    result = pipeline.process_pdf(pdf_path)

    # 3. 결과 출력
    print("\n" + "=" * 60)
    print("처리 결과")
    print("=" * 60)

    print(f"\n문서 ID: {result.document_id}")
    print(f"파일: {result.file_path}")
    print(f"총 페이지: {result.total_pages}")
    print(f"처리 페이지: {result.processed_pages}")
    print(f"평균 신뢰도: {result.average_confidence:.2f}%")
    print(f"총 단어 수: {result.total_word_count}")
    print(f"처리 시간: {result.total_processing_time:.2f}초")

    # 4. 페이지별 결과
    print("\n" + "=" * 60)
    print("페이지별 결과")
    print("=" * 60)

    for page_result in result.page_results:
        print(f"\n페이지 {page_result.page_number}:")
        print(f"  신뢰도: {page_result.confidence:.2f}%")
        print(f"  단어 수: {page_result.word_count}")
        print(f"  처리 시간: {page_result.processing_time:.2f}초")
        if page_result.error:
            print(f"  오류: {page_result.error}")

    # 5. 추출된 텍스트
    print("\n" + "=" * 60)
    print("추출된 텍스트")
    print("=" * 60)
    print(result.total_text)
    print("=" * 60)

    # 6. 메타데이터
    print("\n" + "=" * 60)
    print("메타데이터")
    print("=" * 60)
    for key, value in result.metadata.items():
        print(f"  {key}: {value}")

    # 7. 성능 평가
    print("\n" + "=" * 60)
    print("성능 평가")
    print("=" * 60)

    if result.average_confidence >= 80:
        print("✅ 우수: OCR 품질이 매우 좋습니다")
    elif result.average_confidence >= 60:
        print("⚠️  양호: OCR 품질이 괜찮습니다")
    else:
        print("⚠️  개선 필요: 전처리 옵션 조정 권장")

    pages_per_second = result.total_pages / result.total_processing_time
    print(f"\n처리 속도: {pages_per_second:.2f} 페이지/초")

    return result


def test_with_preprocessing_comparison():
    """전처리 적용 여부 비교 테스트"""
    print("\n\n" + "=" * 60)
    print("전처리 적용 여부 비교")
    print("=" * 60)

    pdf_path = "sample_legal_document.pdf"

    # 1. 전처리 없음
    print("\n[1] 전처리 없음...")
    pipeline_no_prep = OCRPipeline(
        engine_name='tesseract',
        dpi=300,
        enable_preprocessing=False
    )
    result_no_prep = pipeline_no_prep.process_pdf(pdf_path)
    print(f"   신뢰도: {result_no_prep.average_confidence:.2f}%")
    print(f"   처리 시간: {result_no_prep.total_processing_time:.2f}초")

    # 2. 일반 전처리
    print("\n[2] 일반 전처리...")
    pipeline_prep = OCRPipeline(
        engine_name='tesseract',
        dpi=300,
        enable_preprocessing=True,
        aggressive_preprocessing=False
    )
    result_prep = pipeline_prep.process_pdf(pdf_path)
    print(f"   신뢰도: {result_prep.average_confidence:.2f}%")
    print(f"   처리 시간: {result_prep.total_processing_time:.2f}초")

    # 3. 공격적 전처리
    print("\n[3] 공격적 전처리...")
    pipeline_aggressive = OCRPipeline(
        engine_name='tesseract',
        dpi=300,
        enable_preprocessing=True,
        aggressive_preprocessing=True
    )
    result_aggressive = pipeline_aggressive.process_pdf(pdf_path)
    print(f"   신뢰도: {result_aggressive.average_confidence:.2f}%")
    print(f"   처리 시간: {result_aggressive.total_processing_time:.2f}초")

    # 비교 결과
    print("\n" + "=" * 60)
    print("비교 결과")
    print("=" * 60)

    print(f"\n{'설정':<20} {'신뢰도':<15} {'처리시간':<15} {'성능':<10}")
    print("-" * 60)
    print(f"{'전처리 없음':<20} {result_no_prep.average_confidence:>7.2f}%      {result_no_prep.total_processing_time:>7.2f}초      {'기준':<10}")
    print(f"{'일반 전처리':<20} {result_prep.average_confidence:>7.2f}%      {result_prep.total_processing_time:>7.2f}초      {'+' + str(round(result_prep.average_confidence - result_no_prep.average_confidence, 2)) + '%':<10}")
    print(f"{'공격적 전처리':<20} {result_aggressive.average_confidence:>7.2f}%      {result_aggressive.total_processing_time:>7.2f}초      {'+' + str(round(result_aggressive.average_confidence - result_no_prep.average_confidence, 2)) + '%':<10}")

    print("\n✅ 권장: ", end="")
    if result_aggressive.average_confidence > result_prep.average_confidence + 5:
        print("공격적 전처리 (품질이 낮은 문서용)")
    elif result_prep.average_confidence > result_no_prep.average_confidence + 5:
        print("일반 전처리 (균형잡힌 선택)")
    else:
        print("전처리 없음 (고품질 PDF용)")


if __name__ == "__main__":
    # 기본 테스트
    test_ocr_pipeline()

    # 전처리 비교
    test_with_preprocessing_comparison()

    print("\n" + "=" * 60)
    print("모든 테스트 완료")
    print("=" * 60)
