"""
PDF 처리 서비스
PDF → Image 변환 및 이미지 전처리
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image
from pdf2image import convert_from_path
import numpy as np

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 문서를 이미지로 변환하고 전처리"""

    def __init__(self, dpi: int = 300):
        """
        Args:
            dpi: 이미지 해상도 (기본 300, 고품질 600)
        """
        self.dpi = dpi

    def pdf_to_images(
        self,
        pdf_path: str,
        first_page: Optional[int] = None,
        last_page: Optional[int] = None
    ) -> List[Image.Image]:
        """
        PDF를 이미지 리스트로 변환

        Args:
            pdf_path: PDF 파일 경로
            first_page: 시작 페이지 (None이면 첫 페이지)
            last_page: 끝 페이지 (None이면 마지막 페이지)

        Returns:
            PIL Image 리스트
        """
        try:
            logger.info(f"PDF 변환 시작: {pdf_path} (DPI: {self.dpi})")

            images = convert_from_path(
                pdf_path,
                dpi=self.dpi,
                first_page=first_page,
                last_page=last_page,
                fmt='PNG'
            )

            logger.info(f"PDF 변환 완료: {len(images)} 페이지")
            return images

        except Exception as e:
            logger.error(f"PDF 변환 실패: {str(e)}")
            raise

    def get_pdf_page_count(self, pdf_path: str) -> int:
        """
        PDF 페이지 수 확인

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            페이지 수
        """
        try:
            import PyMuPDF as fitz
            doc = fitz.open(pdf_path)
            page_count = doc.page_count
            doc.close()
            return page_count
        except Exception as e:
            logger.warning(f"PyMuPDF로 페이지 수 확인 실패: {str(e)}, pdf2image 사용")
            # Fallback: 전체 변환
            images = self.pdf_to_images(pdf_path)
            return len(images)

    def preprocess_image(
        self,
        image: Image.Image,
        grayscale: bool = True,
        contrast_enhance: bool = True,
        denoise: bool = False
    ) -> Image.Image:
        """
        이미지 전처리로 OCR 품질 향상

        Args:
            image: 원본 이미지
            grayscale: 그레이스케일 변환
            contrast_enhance: 대비 향상
            denoise: 노이즈 제거

        Returns:
            전처리된 이미지
        """
        try:
            # 1. 그레이스케일 변환
            if grayscale and image.mode != 'L':
                image = image.convert('L')
                logger.debug("그레이스케일 변환 완료")

            # 2. 대비 향상
            if contrast_enhance:
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.5)  # 대비 1.5배
                logger.debug("대비 향상 완료")

            # 3. 노이즈 제거 (선택적)
            if denoise:
                # PIL의 filter 사용
                from PIL import ImageFilter
                image = image.filter(ImageFilter.MedianFilter(size=3))
                logger.debug("노이즈 제거 완료")

            return image

        except Exception as e:
            logger.error(f"이미지 전처리 실패: {str(e)}")
            return image  # 실패 시 원본 반환

    def binarize_image(self, image: Image.Image, threshold: int = 128) -> Image.Image:
        """
        이미지 이진화 (흑백 변환)

        Args:
            image: 그레이스케일 이미지
            threshold: 임계값 (0-255)

        Returns:
            이진화된 이미지
        """
        try:
            if image.mode != 'L':
                image = image.convert('L')

            # Otsu's 이진화 (자동 임계값)
            img_array = np.array(image)

            # 간단한 임계값 기반 이진화
            binary = (img_array > threshold).astype(np.uint8) * 255

            result = Image.fromarray(binary, mode='L')
            logger.debug(f"이진화 완료 (임계값: {threshold})")
            return result

        except Exception as e:
            logger.error(f"이진화 실패: {str(e)}")
            return image

    def enhance_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        OCR에 최적화된 이미지 전처리 파이프라인

        Args:
            image: 원본 이미지

        Returns:
            OCR 최적화 이미지
        """
        # 1. 그레이스케일
        image = self.preprocess_image(
            image,
            grayscale=True,
            contrast_enhance=True,
            denoise=False
        )

        # 2. 샤프닝 (선명도 향상)
        from PIL import ImageFilter
        image = image.filter(ImageFilter.SHARPEN)

        # 3. 대비 재조정
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.3)

        logger.debug("OCR 최적화 전처리 완료")
        return image

    def save_images(
        self,
        images: List[Image.Image],
        output_dir: str,
        prefix: str = "page"
    ) -> List[str]:
        """
        이미지를 파일로 저장

        Args:
            images: 이미지 리스트
            output_dir: 출력 디렉토리
            prefix: 파일명 접두사

        Returns:
            저장된 파일 경로 리스트
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_paths = []
        for i, image in enumerate(images):
            filename = f"{prefix}_{i+1:04d}.png"
            filepath = output_path / filename
            image.save(filepath, 'PNG')
            saved_paths.append(str(filepath))
            logger.debug(f"저장 완료: {filepath}")

        logger.info(f"{len(saved_paths)}개 이미지 저장 완료")
        return saved_paths


class PDFInfo:
    """PDF 문서 정보"""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.page_count: int = 0
        self.file_size: int = 0
        self.title: Optional[str] = None
        self.author: Optional[str] = None
        self.subject: Optional[str] = None

    @classmethod
    def from_file(cls, pdf_path: str) -> 'PDFInfo':
        """
        PDF 파일로부터 정보 추출

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            PDFInfo 객체
        """
        info = cls(pdf_path)

        try:
            import PyMuPDF as fitz
            doc = fitz.open(pdf_path)

            info.page_count = doc.page_count
            info.file_size = Path(pdf_path).stat().st_size

            # 메타데이터
            metadata = doc.metadata
            if metadata:
                info.title = metadata.get('title')
                info.author = metadata.get('author')
                info.subject = metadata.get('subject')

            doc.close()
            logger.info(f"PDF 정보 추출 완료: {pdf_path}")

        except Exception as e:
            logger.error(f"PDF 정보 추출 실패: {str(e)}")
            info.file_size = Path(pdf_path).stat().st_size if Path(pdf_path).exists() else 0

        return info
