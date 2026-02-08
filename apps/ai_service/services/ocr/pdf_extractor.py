"""
PDF 처리 파이프라인
PyMuPDF 텍스트 추출 우선 -> OCR 전환 (품질 기반 전처리 포함)
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import unicodedata

import fitz  # PyMuPDF

from .ocr_processor import extract_pdf_with_preprocessing

logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """PDF 텍스트 추출 및 판단"""

    @staticmethod
    def extract_text_with_pymupdf(pdf_path: Path) -> Dict[str, Any]:
        """
        PyMuPDF로 텍스트 추출 시도

        Returns:
            dict: {
                'success': bool,
                'text': str,
                'page_count': int,
                'char_count': int,
                'extraction_rate': float  # 페이지당 평균 글자 수
            }
        """
        logger.info(f"[Step 1] PyMuPDF text extraction: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            pages_text = []
            total_chars = 0

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                text = unicodedata.normalize('NFC', text)
                pages_text.append(text)
                total_chars += len(text.strip())

            doc.close()

            full_text = '\n'.join(pages_text)
            extraction_rate = total_chars / len(pages_text) if pages_text else 0

            result = {
                'success': True,
                'text': full_text,
                'page_count': len(pages_text),
                'char_count': total_chars,
                'extraction_rate': extraction_rate
            }

            logger.info(f"PyMuPDF extracted: {total_chars} chars ({len(pages_text)} pages)")
            logger.info(f"Avg per page: {extraction_rate:.1f} chars")

            return result

        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            return {
                'success': False,
                'text': '',
                'page_count': 0,
                'char_count': 0,
                'extraction_rate': 0,
                'error': str(e)
            }

    @staticmethod
    def is_text_extractable(extraction_result: Dict[str, Any], min_chars_per_page: int = 100) -> bool:
        """
        텍스트 추출 가능 여부 판단

        Args:
            extraction_result: extract_text_with_pymupdf() 결과
            min_chars_per_page: 페이지당 최소 글자 수 (기본 100자)

        Returns:
            bool: True이면 PyMuPDF 텍스트 사용 가능, False이면 OCR 필요
        """
        if not extraction_result['success']:
            logger.info("Decision: OCR needed (extraction failed)")
            return False

        if extraction_result['char_count'] < 50:
            logger.info(f"Decision: OCR needed (total chars too low: {extraction_result['char_count']})")
            return False

        if extraction_result['extraction_rate'] < min_chars_per_page:
            logger.info(f"Decision: OCR needed (avg per page too low: {extraction_result['extraction_rate']:.1f})")
            return False

        text = extraction_result['text']
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_meaningful = korean_chars + english_chars

        meaningful_ratio = total_meaningful / extraction_result['char_count'] if extraction_result['char_count'] > 0 else 0

        if meaningful_ratio < 0.3:
            logger.info(f"Decision: OCR needed (meaningful text ratio too low: {meaningful_ratio:.1%})")
            return False

        logger.info("Decision: PyMuPDF text usable")
        logger.info(f"  - Total chars: {extraction_result['char_count']}")
        logger.info(f"  - Avg per page: {extraction_result['extraction_rate']:.1f}")
        logger.info(f"  - Meaningful ratio: {meaningful_ratio:.1%}")
        return True


class PDFProcessingPipeline:
    """PDF 처리 통합 파이프라인"""

    def __init__(self, min_chars_per_page: int = 100):
        """
        Args:
            min_chars_per_page: OCR 전환 판단 기준 (페이지당 최소 글자 수)
        """
        self.min_chars_per_page = min_chars_per_page

    def process_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        PDF 파일 처리 (PyMuPDF 우선, 필요시 OCR)

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            dict: {
                'success': bool,
                'text': str,
                'extraction_method': str ('pymupdf' or 'ocr'),
                'metadata': dict,
                'needs_review': bool (OCR의 경우 True)
            }
        """
        logger.info(f"Processing PDF: {pdf_path}")

        # Step 1: PyMuPDF 텍스트 추출 시도
        pymupdf_result = PDFTextExtractor.extract_text_with_pymupdf(pdf_path)
        is_extractable = PDFTextExtractor.is_text_extractable(
            pymupdf_result,
            self.min_chars_per_page
        )

        if is_extractable:
            # PyMuPDF 텍스트 사용
            logger.info("Using PyMuPDF extracted text")

            return {
                'success': True,
                'text': pymupdf_result['text'],
                'extraction_method': 'pymupdf',
                'needs_review': False,
                'confidence': 100.0,  # Direct extraction is reliable
                'metadata': {
                    'char_count': pymupdf_result['char_count'],
                    'page_count': pymupdf_result['page_count'],
                    'extraction_rate': pymupdf_result['extraction_rate']
                }
            }

        else:
            # OCR 필요
            logger.info("Falling back to OCR extraction")

            ocr_result = extract_pdf_with_preprocessing(
                pdf_path,
                dpi=300,
                preset='standard',
                adaptive=True
            )

            full_text = '\n'.join([page['text'] for page in ocr_result['pages']])

            return {
                'success': True,
                'text': full_text,
                'extraction_method': 'ocr',
                'needs_review': True,  # OCR 결과는 사용자 검토 필요
                'confidence': ocr_result['avg_confidence'],
                'metadata': {
                    'char_count': ocr_result['total_chars'],
                    'page_count': ocr_result['page_count'],
                    'avg_confidence': ocr_result['avg_confidence'],
                    'preprocessing': ocr_result['preprocessing'],
                    'preset_usage': ocr_result.get('preset_usage', {})
                }
            }

    def extract_text_only(self, pdf_path: Path) -> Dict[str, Any]:
        """
        텍스트만 추출 (구조화 없이)

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            추출 결과 dict
        """
        return self.process_pdf(pdf_path)
