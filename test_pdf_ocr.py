"""
실제 PDF 문서를 사용한 OCR 테스트
PDF -> Image -> OCR -> Text 전체 파이프라인 검증
"""

import os
import sys
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def create_sample_legal_pdf(output_path: str = "sample_legal_document.pdf"):
    """
    샘플 법률 문서 PDF 생성
    """
    print("=" * 60)
    print("샘플 법률 문서 PDF 생성")
    print("=" * 60)

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # 텍스트 작성 (한글 폰트 없이 영문으로)
    y_position = height - 100

    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, y_position, "Supreme Court Decision")

    y_position -= 40
    c.setFont("Helvetica", 12)

    legal_text = [
        "Case No: 2024-Criminal-001",
        "",
        "Summary of Decision:",
        "The defendant's conduct constitutes a violation",
        "of Article 250 of the Criminal Code.",
        "",
        "Rationale:",
        "1. The defendant intentionally caused harm",
        "2. The evidence clearly demonstrates intent",
        "3. There are no mitigating circumstances",
        "",
        "Conclusion:",
        "The defendant is found guilty and sentenced",
        "to imprisonment for a period of 3 years.",
    ]

    for line in legal_text:
        c.drawString(100, y_position, line)
        y_position -= 20
        if y_position < 100:
            break

    c.save()
    print(f"✅ PDF 생성 완료: {output_path}")
    return output_path


def pdf_to_images(pdf_path: str, dpi: int = 300):
    """
    PDF를 이미지로 변환
    """
    print("\n" + "=" * 60)
    print("PDF → Image 변환")
    print("=" * 60)

    print(f"PDF 파일: {pdf_path}")
    print(f"DPI: {dpi}")

    try:
        images = convert_from_path(pdf_path, dpi=dpi)
        print(f"✅ 변환 완료: {len(images)} 페이지")

        for i, img in enumerate(images):
            print(f"   페이지 {i+1}: {img.size[0]}x{img.size[1]} pixels")

        return images
    except Exception as e:
        print(f"❌ 오류: {str(e)}")
        return None


def perform_ocr(image: Image.Image, lang: str = 'eng'):
    """
    이미지에서 OCR 수행
    """
    try:
        # OCR 실행 (상세 정보 포함)
        text = pytesseract.image_to_string(image, lang=lang)

        # 신뢰도 정보
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)

        # 평균 신뢰도 계산
        confidences = [float(c) for c in data['conf'] if c != '-1']
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # 단어 수
        words = [w for w in data['text'] if w.strip()]

        return {
            'text': text,
            'confidence': avg_confidence,
            'word_count': len(words),
            'line_count': text.count('\n') + 1 if text else 0
        }
    except Exception as e:
        return {
            'text': '',
            'confidence': 0,
            'word_count': 0,
            'line_count': 0,
            'error': str(e)
        }


def test_pdf_ocr_pipeline(pdf_path: str = None):
    """
    전체 PDF OCR 파이프라인 테스트
    """
    print("\n" + "=" * 60)
    print("PDF OCR 파이프라인 테스트")
    print("=" * 60)

    # 1. PDF 준비
    if not pdf_path:
        pdf_path = create_sample_legal_pdf()

    if not os.path.exists(pdf_path):
        print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return

    # 2. PDF → Images
    images = pdf_to_images(pdf_path)

    if not images:
        print("❌ PDF 변환 실패")
        return

    # 3. OCR 수행
    print("\n" + "=" * 60)
    print("OCR 실행")
    print("=" * 60)

    results = []
    for i, image in enumerate(images):
        print(f"\n페이지 {i+1} OCR 중...")
        result = perform_ocr(image, lang='eng')

        print(f"   신뢰도: {result['confidence']:.2f}%")
        print(f"   단어 수: {result['word_count']}")
        print(f"   줄 수: {result['line_count']}")

        if 'error' in result:
            print(f"   ⚠️  오류: {result['error']}")

        results.append(result)

    # 4. 결과 분석
    print("\n" + "=" * 60)
    print("전체 결과 분석")
    print("=" * 60)

    total_words = sum(r['word_count'] for r in results)
    avg_confidence = sum(r['confidence'] for r in results) / len(results) if results else 0

    print(f"\n총 페이지 수: {len(results)}")
    print(f"총 단어 수: {total_words}")
    print(f"평균 신뢰도: {avg_confidence:.2f}%")

    # 5. 추출된 텍스트 출력
    print("\n" + "=" * 60)
    print("추출된 텍스트")
    print("=" * 60)

    for i, result in enumerate(results):
        print(f"\n[페이지 {i+1}]")
        print("-" * 60)
        print(result['text'])
        print("-" * 60)

    # 6. 성능 평가
    print("\n" + "=" * 60)
    print("성능 평가")
    print("=" * 60)

    if avg_confidence >= 80:
        print("✅ 우수: OCR 품질이 매우 좋습니다 (80% 이상)")
    elif avg_confidence >= 60:
        print("⚠️  양호: OCR 품질이 괜찮습니다 (60-80%)")
    elif avg_confidence >= 40:
        print("⚠️  보통: OCR 품질 개선 필요 (40-60%)")
    else:
        print("❌ 불량: OCR 품질이 낮습니다 (40% 미만)")

    print("\n개선 권장사항:")
    if avg_confidence < 80:
        print("  - 이미지 전처리 (그레이스케일, 이진화)")
        print("  - DPI 향상 (300 → 600)")
        print("  - 노이즈 제거")
        print("  - 텍스트 영역 크롭")

    # 7. 정리
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

    return results


def test_korean_pdf():
    """
    한글 텍스트 OCR 테스트 (이미지 기반)
    """
    print("\n" + "=" * 60)
    print("한글 OCR 테스트 (이미지 직접 생성)")
    print("=" * 60)

    # 한글 텍스트 이미지 생성
    img = Image.new('RGB', (800, 600), color='white')
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)

    # 영문 + 간단한 텍스트
    test_text = """
    Korean Legal Document Test

    Article 1: General Provisions
    Article 2: Rights and Obligations
    Article 3: Penalties
    """

    d.text((50, 50), test_text, fill='black')

    print("\n이미지 생성 완료")
    print(f"크기: {img.size}")

    # OCR 실행
    print("\nOCR 실행 중 (영문 모드)...")
    result = perform_ocr(img, lang='eng')

    print(f"\n신뢰도: {result['confidence']:.2f}%")
    print(f"단어 수: {result['word_count']}")
    print("\n추출된 텍스트:")
    print("-" * 60)
    print(result['text'])
    print("-" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("PDF OCR 통합 테스트")
    print("=" * 60)

    # Tesseract 버전 확인
    print(f"\nTesseract 버전: {pytesseract.get_tesseract_version()}")

    # 테스트 1: PDF OCR 파이프라인
    test_pdf_ocr_pipeline()

    # 테스트 2: 한글 이미지 OCR
    test_korean_pdf()

    print("\n" + "=" * 60)
    print("모든 테스트 완료")
    print("=" * 60)
