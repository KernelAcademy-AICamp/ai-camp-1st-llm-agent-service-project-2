"""
Multi-Engine OCR Service
하드웨어에 따라 자동으로 최적 엔진 사용
"""

import logging
from typing import Dict, Any
from PIL import Image

from app.services.ocr_engine_selector import OCREngineSelector
from app.services.ocr_engines import TesseractOCREngine, EasyOCREngine, PaddleOCREngine

logger = logging.getLogger(__name__)


class MultiEngineOCRService:
    """
    멀티 엔진 OCR 서비스
    하드웨어에 따라 자동으로 최적 엔진 선택
    """

    def __init__(self):
        # 최적 엔진 선택
        self.engine_name = OCREngineSelector.select_engine()
        self.engine_config = OCREngineSelector.get_engine_config(self.engine_name)

        # 엔진 초기화
        self.engine = self._initialize_engine()

        logger.info(f"MultiEngineOCRService initialized with {self.engine_name}")

    def _initialize_engine(self):
        """선택된 엔진 초기화"""
        engines = {
            'tesseract': TesseractOCREngine,
            'easyocr': EasyOCREngine,
            'paddleocr': PaddleOCREngine
        }

        engine_class = engines.get(self.engine_name, TesseractOCREngine)

        try:
            return engine_class(self.engine_config)
        except Exception as e:
            logger.error(f"Failed to initialize {self.engine_name}: {e}")
            logger.info("Falling back to Tesseract OCR")
            # Fallback to Tesseract
            self.engine_name = 'tesseract'
            self.engine_config = OCREngineSelector.get_engine_config('tesseract')
            return TesseractOCREngine(self.engine_config)

    def extract_text(self, image: Image.Image) -> tuple[str, float]:
        """
        이미지에서 텍스트 추출

        Args:
            image: PIL Image 객체

        Returns:
            tuple: (추출된 텍스트, 신뢰도)
        """
        try:
            return self.engine.extract_text(image)
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return "", 0.0

    def get_engine_info(self) -> Dict[str, Any]:
        """현재 사용 중인 엔진 정보 반환"""
        from app.core.hardware_detector import get_hardware_info

        hw_info = get_hardware_info()

        return {
            "engine": self.engine_name,
            "device": hw_info.device_type.value,
            "device_name": hw_info.device_name,
            "device_count": hw_info.device_count,
            "total_memory": hw_info.total_memory,
            "config": self.engine_config
        }

    def test_ocr(self, image: Image.Image) -> Dict[str, Any]:
        """
        OCR 테스트 (디버깅용)

        Args:
            image: PIL Image 객체

        Returns:
            dict: 테스트 결과
        """
        import time

        start_time = time.time()
        text, confidence = self.extract_text(image)
        elapsed_time = time.time() - start_time

        return {
            "engine": self.engine_name,
            "text": text,
            "confidence": confidence,
            "text_length": len(text),
            "word_count": len(text.split()),
            "elapsed_time": elapsed_time,
            "engine_info": self.get_engine_info()
        }
