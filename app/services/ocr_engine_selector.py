"""
OCR Engine Selector
하드웨어 환경에 따라 최적의 OCR 엔진 자동 선택
"""

from typing import Protocol, Dict, Any
import logging

from app.core.hardware_detector import get_hardware_info, DeviceType
from app.core.config import settings

logger = logging.getLogger(__name__)


class OCREngine(Protocol):
    """OCR 엔진 인터페이스"""

    def extract_text(self, image) -> tuple[str, float]:
        """
        텍스트 추출

        Args:
            image: PIL Image 객체

        Returns:
            tuple: (추출된 텍스트, 신뢰도)
        """
        ...


class OCREngineSelector:
    """
    하드웨어 환경에 따라 최적의 OCR 엔진 선택
    """

    @staticmethod
    def select_engine() -> str:
        """
        최적의 OCR 엔진 선택

        Returns:
            str: 엔진 이름 ('tesseract', 'easyocr', 'paddleocr')
        """
        # 환경변수로 강제 지정한 경우
        if settings.OCR_ENGINE and settings.OCR_ENGINE.lower() != 'auto':
            engine = settings.OCR_ENGINE.lower()
            logger.info(f"OCR engine manually set to: {engine}")
            return engine

        # 하드웨어 정보 조회
        hw_info = get_hardware_info()

        # GPU 사용 가능한 경우
        if hw_info.device_type in [DeviceType.CUDA, DeviceType.ROCM, DeviceType.MPS]:
            # CUDA GPU 메모리가 충분한 경우 (4GB 이상)
            if hw_info.device_type == DeviceType.CUDA and hw_info.total_memory and hw_info.total_memory >= 4096:
                logger.info(f"Selected PaddleOCR (CUDA GPU with {hw_info.total_memory}MB)")
                return 'paddleocr'  # 가장 정확하고 빠름
            else:
                logger.info(f"Selected EasyOCR ({hw_info.device_type.value.upper()} GPU)")
                return 'easyocr'  # 메모리 효율적

        # CPU만 사용 가능한 경우
        logger.info("Selected Tesseract (CPU)")
        return 'tesseract'  # 가장 가볍고 안정적

    @staticmethod
    def get_engine_config(engine_name: str) -> Dict[str, Any]:
        """
        선택된 엔진의 설정 반환

        Args:
            engine_name: 엔진 이름

        Returns:
            dict: 엔진별 설정
        """
        hw_info = get_hardware_info()

        configs = {
            'tesseract': {
                'lang': settings.TESSERACT_LANG,
                'config': '--oem 3 --psm 6',  # LSTM 엔진, 단일 블록 텍스트
                'use_gpu': False,
                'dpi': settings.TESSERACT_DPI
            },
            'easyocr': {
                'lang_list': ['ko', 'en'],
                'gpu': hw_info.device_type != DeviceType.CPU,
                'model_storage_directory': './models/easyocr',
                'download_enabled': True,
                'device': hw_info.device_type.value
            },
            'paddleocr': {
                'lang': 'korean',
                'use_angle_cls': True,
                'use_gpu': hw_info.device_type == DeviceType.CUDA,
                'gpu_mem': min(hw_info.total_memory // 2, 4096) if hw_info.total_memory else 2048,
                'enable_mkldnn': True,
                'cpu_threads': settings.OCR_MAX_WORKERS,
                'show_log': False
            }
        }

        config = configs.get(engine_name, configs['tesseract'])
        logger.debug(f"Engine config for {engine_name}: {config}")
        return config


def initialize_ocr_service() -> tuple[str, Dict[str, Any]]:
    """
    OCR 서비스 초기화

    Returns:
        tuple: (엔진 이름, 엔진 설정)
    """
    # 하드웨어 정보 출력
    from app.core.hardware_detector import print_hardware_info
    print_hardware_info()

    # 최적 엔진 선택
    engine_name = OCREngineSelector.select_engine()
    engine_config = OCREngineSelector.get_engine_config(engine_name)

    print(f"\nSelected OCR Engine: {engine_name.upper()}")
    print(f"Configuration: {engine_config}\n")

    return engine_name, engine_config
