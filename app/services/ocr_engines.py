"""
OCR Engine Implementations
Tesseract, EasyOCR, PaddleOCR 구현
"""

import logging
from typing import Dict, Any
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class TesseractOCREngine:
    """Tesseract OCR 엔진 (CPU 전용)"""

    def __init__(self, config: Dict[str, Any]):
        try:
            import pytesseract
            self.pytesseract = pytesseract
            self.config = config
            logger.info("Initialized Tesseract OCR Engine (CPU)")
        except ImportError:
            logger.error("pytesseract not installed. Run: pip install pytesseract")
            raise

    def extract_text(self, image: Image.Image) -> tuple[str, float]:
        """
        텍스트 추출

        Args:
            image: PIL Image 객체

        Returns:
            tuple: (추출된 텍스트, 신뢰도)
        """
        try:
            # OCR 실행
            ocr_data = self.pytesseract.image_to_data(
                image,
                lang=self.config['lang'],
                config=self.config['config'],
                output_type=self.pytesseract.Output.DICT
            )

            # 텍스트 및 신뢰도 추출
            text_parts = []
            confidences = []

            for i, word in enumerate(ocr_data['text']):
                conf = float(ocr_data['conf'][i])
                if conf > 0 and word.strip():
                    text_parts.append(word)
                    confidences.append(conf)

            text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return text, avg_confidence

        except Exception as e:
            logger.error(f"Tesseract OCR error: {e}")
            return "", 0.0


class EasyOCREngine:
    """EasyOCR 엔진 (GPU 지원)"""

    def __init__(self, config: Dict[str, Any]):
        try:
            import easyocr
            self.reader = easyocr.Reader(
                config['lang_list'],
                gpu=config['gpu'],
                model_storage_directory=config.get('model_storage_directory'),
                download_enabled=config.get('download_enabled', True)
            )
            logger.info(f"Initialized EasyOCR Engine (GPU: {config['gpu']})")
        except ImportError:
            logger.error("easyocr not installed. Run: pip install easyocr")
            raise

    def extract_text(self, image: Image.Image) -> tuple[str, float]:
        """
        텍스트 추출

        Args:
            image: PIL Image 객체

        Returns:
            tuple: (추출된 텍스트, 신뢰도)
        """
        try:
            # PIL Image를 NumPy 배열로 변환
            img_array = np.array(image)

            # OCR 실행
            results = self.reader.readtext(img_array)

            # 텍스트 및 신뢰도 추출
            if not results:
                return "", 0.0

            text_parts = [result[1] for result in results]
            confidences = [result[2] for result in results]

            text = ' '.join(text_parts)
            avg_confidence = (sum(confidences) / len(confidences)) * 100 if confidences else 0.0

            return text, avg_confidence

        except Exception as e:
            logger.error(f"EasyOCR error: {e}")
            return "", 0.0


class PaddleOCREngine:
    """PaddleOCR 엔진 (GPU 지원, 가장 정확)"""

    def __init__(self, config: Dict[str, Any]):
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                lang=config['lang'],
                use_angle_cls=config['use_angle_cls'],
                use_gpu=config['use_gpu'],
                gpu_mem=config.get('gpu_mem', 2048),
                enable_mkldnn=config.get('enable_mkldnn', True),
                cpu_threads=config.get('cpu_threads', 4),
                show_log=config.get('show_log', False)
            )
            logger.info(f"Initialized PaddleOCR Engine (GPU: {config['use_gpu']})")
        except ImportError:
            logger.error("paddleocr not installed. Run: pip install paddleocr")
            raise

    def extract_text(self, image: Image.Image) -> tuple[str, float]:
        """
        텍스트 추출

        Args:
            image: PIL Image 객체

        Returns:
            tuple: (추출된 텍스트, 신뢰도)
        """
        try:
            # PIL Image를 NumPy 배열로 변환
            img_array = np.array(image)

            # OCR 실행
            results = self.ocr.ocr(img_array, cls=True)

            # 텍스트 및 신뢰도 추출
            if not results or not results[0]:
                return "", 0.0

            text_parts = []
            confidences = []

            for line in results[0]:
                if line:
                    text_parts.append(line[1][0])
                    confidences.append(line[1][1])

            text = ' '.join(text_parts)
            avg_confidence = (sum(confidences) / len(confidences)) * 100 if confidences else 0.0

            return text, avg_confidence

        except Exception as e:
            logger.error(f"PaddleOCR error: {e}")
            return "", 0.0
