"""
이미지 전처리 서비스
OCR 품질 향상을 위한 이미지 처리
"""

import logging
from typing import Tuple, Optional
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """이미지 전처리 파이프라인"""

    @staticmethod
    def to_grayscale(image: Image.Image) -> Image.Image:
        """그레이스케일 변환"""
        if image.mode != 'L':
            return image.convert('L')
        return image

    @staticmethod
    def enhance_contrast(image: Image.Image, factor: float = 1.5) -> Image.Image:
        """
        대비 향상

        Args:
            image: 입력 이미지
            factor: 대비 배율 (1.0=원본, >1.0=향상)
        """
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)

    @staticmethod
    def enhance_sharpness(image: Image.Image, factor: float = 2.0) -> Image.Image:
        """
        선명도 향상

        Args:
            image: 입력 이미지
            factor: 선명도 배율 (1.0=원본, >1.0=향상)
        """
        enhancer = ImageEnhance.Sharpness(image)
        return enhancer.enhance(factor)

    @staticmethod
    def enhance_brightness(image: Image.Image, factor: float = 1.2) -> Image.Image:
        """
        밝기 조정

        Args:
            image: 입력 이미지
            factor: 밝기 배율 (1.0=원본, >1.0=밝게)
        """
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(factor)

    @staticmethod
    def remove_noise(image: Image.Image, method: str = 'median') -> Image.Image:
        """
        노이즈 제거

        Args:
            image: 입력 이미지
            method: 'median', 'blur', 'gaussian'
        """
        if method == 'median':
            return image.filter(ImageFilter.MedianFilter(size=3))
        elif method == 'blur':
            return image.filter(ImageFilter.BLUR)
        elif method == 'gaussian':
            return image.filter(ImageFilter.GaussianBlur(radius=1))
        else:
            return image

    @staticmethod
    def binarize(
        image: Image.Image,
        method: str = 'otsu',
        threshold: int = 128
    ) -> Image.Image:
        """
        이진화 (흑백 변환)

        Args:
            image: 그레이스케일 이미지
            method: 'otsu' (자동), 'fixed' (고정 임계값)
            threshold: 고정 임계값 (method='fixed'일 때)
        """
        # 그레이스케일 확인
        if image.mode != 'L':
            image = ImagePreprocessor.to_grayscale(image)

        img_array = np.array(image)

        if method == 'otsu':
            # Otsu's 방법 (자동 임계값 계산)
            threshold = ImagePreprocessor._calculate_otsu_threshold(img_array)

        # 이진화
        binary = (img_array > threshold).astype(np.uint8) * 255
        return Image.fromarray(binary, mode='L')

    @staticmethod
    def _calculate_otsu_threshold(img_array: np.ndarray) -> int:
        """
        Otsu's 방법으로 최적 임계값 계산

        Args:
            img_array: 그레이스케일 이미지 배열

        Returns:
            최적 임계값
        """
        # 히스토그램 계산
        hist, bin_edges = np.histogram(img_array.flatten(), bins=256, range=(0, 256))

        # 정규화
        hist = hist.astype(float)
        hist /= hist.sum()

        # 누적 합
        cumsum = np.cumsum(hist)
        cumsum_mean = np.cumsum(hist * np.arange(256))

        # 전체 평균
        global_mean = cumsum_mean[-1]

        # 최대 분산 찾기
        max_variance = 0
        threshold = 0

        for i in range(256):
            # 배경 확률
            w0 = cumsum[i]
            if w0 == 0:
                continue

            # 전경 확률
            w1 = 1 - w0
            if w1 == 0:
                break

            # 배경 평균
            mean0 = cumsum_mean[i] / w0

            # 전경 평균
            mean1 = (global_mean - cumsum_mean[i]) / w1

            # 클래스 간 분산
            variance = w0 * w1 * (mean0 - mean1) ** 2

            if variance > max_variance:
                max_variance = variance
                threshold = i

        return threshold

    @staticmethod
    def adaptive_threshold(image: Image.Image, block_size: int = 11) -> Image.Image:
        """
        적응형 임계값 (지역별 이진화)

        Args:
            image: 그레이스케일 이미지
            block_size: 블록 크기 (홀수)
        """
        try:
            import cv2
            # PIL → OpenCV
            img_array = np.array(image)

            # 적응형 임계값
            binary = cv2.adaptiveThreshold(
                img_array,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                block_size,
                2
            )

            return Image.fromarray(binary)

        except ImportError:
            logger.warning("OpenCV가 설치되지 않음, Otsu 방법 사용")
            return ImagePreprocessor.binarize(image, method='otsu')

    @staticmethod
    def deskew(image: Image.Image) -> Image.Image:
        """
        이미지 기울기 보정

        Args:
            image: 입력 이미지

        Returns:
            보정된 이미지
        """
        try:
            import cv2
            from scipy.ndimage import rotate

            # PIL → numpy
            img_array = np.array(image)

            # 그레이스케일 확인
            if len(img_array.shape) > 2:
                img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                img_gray = img_array

            # 이진화
            _, binary = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 좌표 찾기
            coords = np.column_stack(np.where(binary > 0))

            # 최소 면적 사각형
            angle = cv2.minAreaRect(coords)[-1]

            # 각도 조정
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            # 회전
            if abs(angle) > 0.5:  # 0.5도 이상만 보정
                rotated = rotate(img_array, angle, reshape=False, mode='nearest')
                return Image.fromarray(rotated.astype(np.uint8))

            return image

        except ImportError:
            logger.warning("OpenCV/scipy가 설치되지 않음, 기울기 보정 스킵")
            return image
        except Exception as e:
            logger.error(f"기울기 보정 실패: {str(e)}")
            return image

    @classmethod
    def ocr_pipeline(
        cls,
        image: Image.Image,
        aggressive: bool = False
    ) -> Image.Image:
        """
        OCR 최적화 전처리 파이프라인

        Args:
            image: 원본 이미지
            aggressive: 공격적 전처리 여부

        Returns:
            전처리된 이미지
        """
        logger.debug("OCR 전처리 파이프라인 시작")

        # 1. 그레이스케일
        image = cls.to_grayscale(image)

        if aggressive:
            # 공격적 전처리
            # 2. 노이즈 제거
            image = cls.remove_noise(image, method='median')

            # 3. 대비 향상
            image = cls.enhance_contrast(image, factor=1.8)

            # 4. 선명도 향상
            image = cls.enhance_sharpness(image, factor=2.5)

            # 5. 이진화
            image = cls.binarize(image, method='otsu')

        else:
            # 일반 전처리
            # 2. 대비 향상
            image = cls.enhance_contrast(image, factor=1.5)

            # 3. 선명도 향상
            image = cls.enhance_sharpness(image, factor=2.0)

        logger.debug("OCR 전처리 파이프라인 완료")
        return image

    @classmethod
    def denoise_pipeline(cls, image: Image.Image) -> Image.Image:
        """
        노이즈 제거에 특화된 파이프라인

        Args:
            image: 원본 이미지

        Returns:
            노이즈 제거된 이미지
        """
        image = cls.to_grayscale(image)
        image = cls.remove_noise(image, method='median')
        image = cls.remove_noise(image, method='gaussian')
        return image
