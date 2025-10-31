"""
OCR 처리 파이프라인
PDF → Image → Preprocess → OCR → Text
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime

from app.services.pdf_processor import PDFProcessor, PDFInfo
from app.services.image_preprocessor import ImagePreprocessor
from app.services.ocr_engine_selector import OCREngineSelector
from app.services.ocr_engines import TesseractOCREngine

logger = logging.getLogger(__name__)


@dataclass
class OCRPageResult:
    """페이지별 OCR 결과"""
    page_number: int
    text: str
    confidence: float
    word_count: int
    processing_time: float
    error: Optional[str] = None


@dataclass
class OCRDocumentResult:
    """문서 전체 OCR 결과"""
    document_id: str
    file_path: str
    total_pages: int
    processed_pages: int
    page_results: List[OCRPageResult] = field(default_factory=list)
    total_text: str = ""
    average_confidence: float = 0.0
    total_word_count: int = 0
    total_processing_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class OCRPipeline:
    """완전한 OCR 처리 파이프라인"""

    def __init__(
        self,
        engine_name: str = 'auto',
        dpi: int = 300,
        enable_preprocessing: bool = True,
        aggressive_preprocessing: bool = False,
        max_workers: int = 4
    ):
        """
        Args:
            engine_name: OCR 엔진 ('auto', 'tesseract', 'easyocr', 'paddleocr')
            dpi: PDF 변환 DPI
            enable_preprocessing: 이미지 전처리 활성화
            aggressive_preprocessing: 공격적 전처리 (품질이 낮은 이미지용)
            max_workers: 병렬 처리 워커 수
        """
        self.pdf_processor = PDFProcessor(dpi=dpi)
        self.image_preprocessor = ImagePreprocessor()
        self.enable_preprocessing = enable_preprocessing
        self.aggressive_preprocessing = aggressive_preprocessing
        self.max_workers = max_workers

        # OCR 엔진 초기화
        if engine_name == 'auto':
            engine_name = OCREngineSelector.select_engine()

        config = OCREngineSelector.get_engine_config(engine_name)
        self.ocr_engine = self._initialize_engine(engine_name, config)

        logger.info(f"OCR 파이프라인 초기화: 엔진={engine_name}, DPI={dpi}, 전처리={enable_preprocessing}")

    def _initialize_engine(self, engine_name: str, config: Dict[str, Any]):
        """OCR 엔진 초기화"""
        if engine_name == 'tesseract':
            return TesseractOCREngine(config)
        else:
            logger.warning(f"지원하지 않는 엔진: {engine_name}, Tesseract 사용")
            return TesseractOCREngine(OCREngineSelector.get_engine_config('tesseract'))

    def process_pdf(
        self,
        pdf_path: str,
        document_id: Optional[str] = None,
        first_page: Optional[int] = None,
        last_page: Optional[int] = None
    ) -> OCRDocumentResult:
        """
        PDF 문서 전체 OCR 처리

        Args:
            pdf_path: PDF 파일 경로
            document_id: 문서 ID (None이면 파일명 사용)
            first_page: 시작 페이지
            last_page: 끝 페이지

        Returns:
            OCRDocumentResult
        """
        start_time = datetime.now()

        # 문서 ID
        if not document_id:
            document_id = Path(pdf_path).stem

        logger.info(f"PDF OCR 처리 시작: {pdf_path}")

        try:
            # 1. PDF 정보 추출
            pdf_info = PDFInfo.from_file(pdf_path)

            # 2. PDF → Images
            images = self.pdf_processor.pdf_to_images(
                pdf_path,
                first_page=first_page,
                last_page=last_page
            )

            # 3. 병렬 OCR 처리
            page_results = self._process_pages_parallel(images)

            # 4. 결과 집계
            result = self._aggregate_results(
                document_id=document_id,
                pdf_path=pdf_path,
                page_results=page_results,
                pdf_info=pdf_info
            )

            # 처리 시간
            result.total_processing_time = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"PDF OCR 완료: {result.processed_pages}/{result.total_pages} 페이지, "
                f"평균 신뢰도={result.average_confidence:.2f}%, "
                f"처리 시간={result.total_processing_time:.2f}초"
            )

            return result

        except Exception as e:
            logger.error(f"PDF OCR 처리 실패: {str(e)}")
            raise

    def _process_pages_parallel(self, images: List[Image.Image]) -> List[OCRPageResult]:
        """
        페이지 병렬 처리

        Args:
            images: 페이지 이미지 리스트

        Returns:
            페이지 결과 리스트
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 작업 제출
            future_to_page = {
                executor.submit(self._process_single_page, i + 1, img): i
                for i, img in enumerate(images)
            }

            # 결과 수집
            for future in as_completed(future_to_page):
                page_idx = future_to_page[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.debug(f"페이지 {result.page_number} 처리 완료")
                except Exception as e:
                    logger.error(f"페이지 {page_idx + 1} 처리 실패: {str(e)}")
                    results.append(OCRPageResult(
                        page_number=page_idx + 1,
                        text="",
                        confidence=0.0,
                        word_count=0,
                        processing_time=0.0,
                        error=str(e)
                    ))

        # 페이지 번호 순으로 정렬
        results.sort(key=lambda x: x.page_number)
        return results

    def _process_single_page(self, page_number: int, image: Image.Image) -> OCRPageResult:
        """
        단일 페이지 OCR 처리

        Args:
            page_number: 페이지 번호
            image: 페이지 이미지

        Returns:
            OCRPageResult
        """
        start_time = datetime.now()

        try:
            # 이미지 전처리
            if self.enable_preprocessing:
                image = self.image_preprocessor.ocr_pipeline(
                    image,
                    aggressive=self.aggressive_preprocessing
                )

            # OCR 실행
            text, confidence = self.ocr_engine.extract_text(image)

            # 단어 수 계산
            word_count = len(text.split())

            processing_time = (datetime.now() - start_time).total_seconds()

            return OCRPageResult(
                page_number=page_number,
                text=text,
                confidence=confidence,
                word_count=word_count,
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"페이지 {page_number} OCR 실패: {str(e)}")
            return OCRPageResult(
                page_number=page_number,
                text="",
                confidence=0.0,
                word_count=0,
                processing_time=0.0,
                error=str(e)
            )

    def _aggregate_results(
        self,
        document_id: str,
        pdf_path: str,
        page_results: List[OCRPageResult],
        pdf_info: PDFInfo
    ) -> OCRDocumentResult:
        """
        페이지 결과를 문서 결과로 집계

        Args:
            document_id: 문서 ID
            pdf_path: PDF 경로
            page_results: 페이지 결과 리스트
            pdf_info: PDF 정보

        Returns:
            OCRDocumentResult
        """
        # 전체 텍스트
        total_text = "\n\n".join([r.text for r in page_results if not r.error])

        # 평균 신뢰도
        confidences = [r.confidence for r in page_results if not r.error]
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # 총 단어 수
        total_word_count = sum([r.word_count for r in page_results])

        # 총 처리 시간
        total_processing_time = sum([r.processing_time for r in page_results])

        # 메타데이터
        metadata = {
            'pdf_title': pdf_info.title,
            'pdf_author': pdf_info.author,
            'pdf_subject': pdf_info.subject,
            'file_size': pdf_info.file_size,
            'dpi': self.pdf_processor.dpi,
            'preprocessing_enabled': self.enable_preprocessing,
            'aggressive_preprocessing': self.aggressive_preprocessing
        }

        return OCRDocumentResult(
            document_id=document_id,
            file_path=pdf_path,
            total_pages=len(page_results),
            processed_pages=len([r for r in page_results if not r.error]),
            page_results=page_results,
            total_text=total_text,
            average_confidence=average_confidence,
            total_word_count=total_word_count,
            total_processing_time=total_processing_time,
            metadata=metadata
        )

    def process_image(self, image: Image.Image) -> tuple[str, float]:
        """
        단일 이미지 OCR (간단 버전)

        Args:
            image: 이미지

        Returns:
            (텍스트, 신뢰도)
        """
        if self.enable_preprocessing:
            image = self.image_preprocessor.ocr_pipeline(
                image,
                aggressive=self.aggressive_preprocessing
            )

        return self.ocr_engine.extract_text(image)
