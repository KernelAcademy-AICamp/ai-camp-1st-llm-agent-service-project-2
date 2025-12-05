"""
OCR 시스템 테스트
PDF 및 이미지 파일에서 OCR을 통한 텍스트 추출 테스트
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "apps" / "ai_service"))

import pytest


class TestOCRAvailability:
    """OCR 관련 라이브러리 가용성 테스트"""

    def test_pillow_available(self):
        """Pillow 라이브러리 가용성 확인"""
        from PIL import Image
        assert Image is not None
        print("Pillow: Available")

    def test_surya_ocr_available(self):
        """Surya OCR 라이브러리 가용성 확인"""
        try:
            from surya.recognition import RecognitionPredictor, FoundationPredictor
            from surya.detection import DetectionPredictor
            import torch

            # Device 확인
            if torch.backends.mps.is_available():
                device = "mps"
            elif torch.cuda.is_available():
                device = "cuda"
            else:
                device = "cpu"

            print(f"Surya OCR: Available (device: {device})")
            assert True
        except ImportError as e:
            pytest.skip(f"Surya OCR not available: {e}")

    def test_tesseract_available(self):
        """Tesseract 라이브러리 가용성 확인"""
        try:
            import pytesseract
            # Tesseract 버전 확인
            version = pytesseract.get_tesseract_version()
            print(f"Tesseract: Available (version: {version})")
            assert True
        except Exception as e:
            pytest.skip(f"Tesseract not available: {e}")

    def test_pymupdf_available(self):
        """PyMuPDF 라이브러리 가용성 확인"""
        import fitz
        print(f"PyMuPDF (fitz): Available (version: {fitz.version})")
        assert fitz is not None


class TestDocumentProcessor:
    """DocumentProcessor를 통한 OCR 테스트"""

    @pytest.fixture
    def processor(self):
        """DocumentProcessor 인스턴스 생성"""
        from services.document_processor import DocumentProcessor
        return DocumentProcessor(enable_masking=False)

    @pytest.fixture
    def test_images_dir(self):
        """테스트 이미지 디렉토리"""
        return Path("/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/docs/test")

    def test_extract_text_from_png(self, processor, test_images_dir):
        """PNG 이미지에서 텍스트 추출 테스트"""
        # 카카오톡 채팅 캡처 이미지
        image_path = test_images_dir / "카카오톡_사기거래_2024-024.png"

        if not image_path.exists():
            pytest.skip(f"Test image not found: {image_path}")

        result = processor.extract_text_from_image(str(image_path))

        print("\n" + "="*60)
        print("PNG OCR 결과:")
        print("="*60)
        print(f"성공 여부: {result['success']}")
        print(f"추출 방법: {result.get('extraction_method', 'N/A')}")
        print(f"신뢰도: {result.get('confidence', 'N/A'):.1f}%")
        print(f"리뷰 필요: {result.get('needs_review', False)}")
        print(f"\n추출된 텍스트 (일부):\n{result['text'][:500]}...")
        print("="*60)

        assert result['success'] is True
        assert len(result['text']) > 0
        assert result['file_type'] == 'image'

    def test_extract_text_from_png_contract(self, processor, test_images_dir):
        """매매계약서 PNG에서 텍스트 추출 테스트"""
        image_path = test_images_dir / "매매계약서_사기_2024-028.png"

        if not image_path.exists():
            pytest.skip(f"Test image not found: {image_path}")

        result = processor.extract_text_from_image(str(image_path))

        print("\n" + "="*60)
        print("매매계약서 OCR 결과:")
        print("="*60)
        print(f"성공 여부: {result['success']}")
        print(f"추출 방법: {result.get('extraction_method', 'N/A')}")
        print(f"신뢰도: {result.get('confidence', 'N/A'):.1f}%")
        print(f"\n추출된 텍스트 (일부):\n{result['text'][:500]}...")
        print("="*60)

        assert result['success'] is True
        assert len(result['text']) > 0

    def test_extract_text_from_pdf(self, processor, test_images_dir):
        """PDF에서 텍스트 추출 테스트 (PyMuPDF 우선)"""
        pdf_path = test_images_dir / "7_목격자_진술서.pdf"

        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found: {pdf_path}")

        result = processor.extract_pdf_with_ocr_fallback(str(pdf_path))

        print("\n" + "="*60)
        print("PDF 텍스트 추출 결과:")
        print("="*60)
        print(f"성공 여부: {result['success']}")
        print(f"추출 방법: {result.get('extraction_method', 'N/A')}")
        print(f"신뢰도: {result.get('confidence', 'N/A')}")
        print(f"리뷰 필요: {result.get('needs_review', False)}")
        print(f"페이지 수: {result.get('page_count', 'N/A')}")
        print(f"\n추출된 텍스트 (일부):\n{result['text'][:500]}...")
        print("="*60)

        assert result['success'] is True

    def test_process_document_image(self, processor, test_images_dir):
        """process_document로 이미지 처리 테스트"""
        image_path = test_images_dir / "진단서_상해_2024-026.png"

        if not image_path.exists():
            pytest.skip(f"Test image not found: {image_path}")

        result = processor.process_document(str(image_path))

        print("\n" + "="*60)
        print("process_document (이미지) 결과:")
        print("="*60)
        print(f"성공 여부: {result['success']}")
        print(f"추출 방법: {result.get('extraction_method', 'N/A')}")
        print(f"청크 수: {result.get('chunk_count', 0)}")
        print(f"신뢰도: {result.get('confidence', 'N/A'):.1f}%")
        print(f"\n추출된 텍스트 (일부):\n{result['text'][:500]}...")
        print("="*60)

        assert result['success'] is True
        assert result['chunk_count'] >= 0


class TestOCRPipeline:
    """OCR 파이프라인 직접 테스트"""

    def test_quality_assessor(self):
        """이미지 품질 평가 테스트"""
        from services.ocr import DocumentQualityAssessor
        from PIL import Image

        # 테스트 이미지 로드
        test_path = Path("/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/docs/test/카카오톡_사기거래_2024-024.png")
        if not test_path.exists():
            pytest.skip(f"Test image not found: {test_path}")

        image = Image.open(test_path)

        # 품질 평가
        quality = DocumentQualityAssessor.assess_quality(image)

        print("\n" + "="*60)
        print("이미지 품질 평가 결과:")
        print("="*60)
        print(f"원본 점수:")
        for key, value in quality['scores'].items():
            print(f"  - {key}: {value:.2f}")
        print(f"\n정규화 점수:")
        for key, value in quality['normalized_scores'].items():
            print(f"  - {key}: {value:.2f}")
        print(f"\n종합 점수: {quality['total_score']:.1f}")
        print(f"품질 레벨: {quality['quality_level']}")
        print(f"권장 전처리: {quality['recommended_preset']}")
        print(f"\n분석:")
        for key, value in quality['analysis'].items():
            print(f"  - {key}: {value}")
        print("="*60)

        assert 'total_score' in quality
        assert 'quality_level' in quality

    def test_pdf_processing_pipeline(self):
        """PDF 처리 파이프라인 테스트"""
        from services.ocr import PDFProcessingPipeline

        pdf_path = Path("/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/docs/test/7_목격자_진술서.pdf")
        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found: {pdf_path}")

        pipeline = PDFProcessingPipeline()
        result = pipeline.process_pdf(pdf_path)

        print("\n" + "="*60)
        print("PDF 파이프라인 처리 결과:")
        print("="*60)
        print(f"성공 여부: {result['success']}")
        print(f"추출 방법: {result['extraction_method']}")
        print(f"리뷰 필요: {result['needs_review']}")
        print(f"신뢰도: {result.get('confidence', 'N/A')}")
        print(f"\n메타데이터:")
        for key, value in result.get('metadata', {}).items():
            print(f"  - {key}: {value}")
        print(f"\n추출된 텍스트 (일부):\n{result['text'][:500]}...")
        print("="*60)

        assert result['success'] is True

    def test_ocr_postprocessor(self):
        """OCR 후처리 테스트"""
        from services.ocr import apply_ocr_postprocessing

        # 오인식 텍스트 예시
        test_text = """
        정구취지
        피고는 원고에게 100만원을 갖는 날까지 지급하라.
        제 1 SS 피고의 행위는 불법이다.
        """

        corrected = apply_ocr_postprocessing(test_text, verbose=True)

        print("\n" + "="*60)
        print("OCR 후처리 결과:")
        print("="*60)
        print(f"원본:\n{test_text}")
        print(f"\n교정 후:\n{corrected}")
        print("="*60)

        # 교정 확인
        assert "청구취지" in corrected
        assert "갚는 날" in corrected
        assert "제1항" in corrected


class TestSuryaOCR:
    """Surya OCR 직접 테스트"""

    def test_surya_direct(self):
        """Surya OCR 직접 호출 테스트"""
        try:
            from surya.recognition import RecognitionPredictor, FoundationPredictor
            from surya.detection import DetectionPredictor
            import torch
        except ImportError:
            pytest.skip("Surya OCR not installed")

        from PIL import Image

        # 테스트 이미지
        test_path = Path("/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/docs/test/카카오톡_사기거래_2024-024.png")
        if not test_path.exists():
            pytest.skip(f"Test image not found: {test_path}")

        # 이미지 로드
        image = Image.open(test_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # 디바이스 결정
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

        print(f"\nUsing device: {device}")

        # Surya OCR 초기화 및 실행
        detection_predictor = DetectionPredictor(device=device)
        foundation_predictor = FoundationPredictor(device=device)
        recognition_predictor = RecognitionPredictor(foundation_predictor)

        # OCR 수행
        recognition_results = recognition_predictor([image], det_predictor=detection_predictor)

        # 결과 추출
        text_lines = []
        for result in recognition_results:
            for line in result.text_lines:
                text_lines.append(line.text)

        full_text = '\n'.join(text_lines)

        print("\n" + "="*60)
        print("Surya OCR 직접 테스트 결과:")
        print("="*60)
        print(f"인식된 라인 수: {len(text_lines)}")
        print(f"\n추출된 텍스트:\n{full_text}")
        print("="*60)

        assert len(text_lines) > 0


def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "="*70)
    print("OCR 시스템 테스트 시작")
    print("="*70)

    # 라이브러리 가용성 테스트
    print("\n[1/4] 라이브러리 가용성 테스트")
    test_avail = TestOCRAvailability()
    test_avail.test_pillow_available()
    test_avail.test_pymupdf_available()
    try:
        test_avail.test_surya_ocr_available()
    except Exception as e:
        print(f"  Surya OCR: Not available ({e})")
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"  Tesseract: Available (version: {version})")
    except Exception as e:
        print(f"  Tesseract: Not available")

    # DocumentProcessor 테스트
    print("\n[2/4] DocumentProcessor 테스트")
    from services.document_processor import DocumentProcessor
    processor = DocumentProcessor(enable_masking=False)
    test_images_dir = Path("/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/docs/test")

    test_proc = TestDocumentProcessor()

    # PNG 테스트
    image_path = test_images_dir / "카카오톡_사기거래_2024-024.png"
    if image_path.exists():
        result = processor.extract_text_from_image(str(image_path))
        print(f"\n  PNG OCR:")
        print(f"    - 성공: {result['success']}")
        print(f"    - 방법: {result.get('extraction_method', 'N/A')}")
        print(f"    - 신뢰도: {result.get('confidence', 'N/A'):.1f}%")
        print(f"    - 텍스트 길이: {len(result['text'])} chars")

    # PDF 테스트
    pdf_path = test_images_dir / "7_목격자_진술서.pdf"
    if pdf_path.exists():
        result = processor.extract_pdf_with_ocr_fallback(str(pdf_path))
        print(f"\n  PDF 추출:")
        print(f"    - 성공: {result['success']}")
        print(f"    - 방법: {result.get('extraction_method', 'N/A')}")
        print(f"    - 리뷰 필요: {result.get('needs_review', False)}")
        print(f"    - 텍스트 길이: {len(result['text'])} chars")

    # 품질 평가 테스트
    print("\n[3/4] 이미지 품질 평가 테스트")
    from services.ocr import DocumentQualityAssessor

    image = Image.open(image_path)
    quality = DocumentQualityAssessor.assess_quality(image)
    print(f"  - 종합 점수: {quality['total_score']:.1f}")
    print(f"  - 품질 레벨: {quality['quality_level']}")
    print(f"  - 권장 전처리: {quality['recommended_preset']}")

    # 후처리 테스트
    print("\n[4/4] OCR 후처리 테스트")
    from services.ocr import apply_ocr_postprocessing

    test_text = "정구취지: 피고는 원고에게 100만원을 갖는 날까지 지급하라."
    corrected = apply_ocr_postprocessing(test_text)
    print(f"  원본: {test_text}")
    print(f"  교정: {corrected}")

    print("\n" + "="*70)
    print("OCR 시스템 테스트 완료")
    print("="*70)


if __name__ == "__main__":
    # PIL Image import
    from PIL import Image

    run_all_tests()
