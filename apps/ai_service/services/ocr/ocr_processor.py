"""
이미지 전처리를 통한 OCR 품질 개선
다양한 전처리 기법을 적용하여 OCR 정확도 향상
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class DocumentQualityAssessor:
    """문서 품질 평가 클래스"""

    @staticmethod
    def assess_sharpness(image) -> float:
        """
        선명도 평가 (Laplacian 분산)
        높을수록 선명함 (>100: 선명, 50-100: 보통, <50: 흐림)
        """
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        elif len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()
        return laplacian_var

    @staticmethod
    def assess_noise(image) -> float:
        """
        노이즈 수준 평가 (표준편차 분석)
        높을수록 노이즈가 많음 (>50: 많음, 20-50: 보통, <20: 적음)
        """
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        elif len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        kernel_size = 5
        local_mean = cv2.blur(image.astype(float), (kernel_size, kernel_size))
        local_sq_mean = cv2.blur((image.astype(float) ** 2), (kernel_size, kernel_size))
        local_variance = local_sq_mean - (local_mean ** 2)
        noise_level = np.mean(np.sqrt(local_variance))

        return noise_level

    @staticmethod
    def assess_contrast(image) -> float:
        """
        대비 평가 (히스토그램 분석)
        높을수록 대비가 좋음 (>80: 좋음, 40-80: 보통, <40: 낮음)
        """
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        elif len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        rms_contrast = np.std(image)
        return rms_contrast

    @staticmethod
    def assess_brightness(image) -> float:
        """
        밝기 평가 (평균 픽셀 값)
        0-255 범위 (100-180: 적정, >180: 밝음, <100: 어두움)
        """
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        elif len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        brightness = np.mean(image)
        return brightness

    @staticmethod
    def assess_resolution(image) -> float:
        """
        해상도 평가 (이미지 크기)
        픽셀 수로 평가 (>1M: 고해상도, 0.5M-1M: 보통, <0.5M: 저해상도)
        """
        if isinstance(image, Image.Image):
            width, height = image.size
        else:
            height, width = image.shape[:2]

        total_pixels = width * height
        return total_pixels / 1_000_000  # 메가픽셀 단위

    @staticmethod
    def assess_quality(image) -> Dict[str, Any]:
        """
        종합 품질 평가 (가중치 기반)
        Returns: dict with quality scores and recommended preprocessing
        """
        sharpness = DocumentQualityAssessor.assess_sharpness(image)
        noise = DocumentQualityAssessor.assess_noise(image)
        contrast = DocumentQualityAssessor.assess_contrast(image)
        brightness = DocumentQualityAssessor.assess_brightness(image)
        resolution = DocumentQualityAssessor.assess_resolution(image)

        scores = {
            'sharpness': sharpness,
            'noise': noise,
            'contrast': contrast,
            'brightness': brightness,
            'resolution_mp': resolution
        }

        normalized = {
            'sharpness': min(100, sharpness / 2),
            'noise': max(0, 100 - noise * 2),
            'contrast': min(100, contrast * 1.25),
            'brightness': 100 if 100 < brightness < 180 else max(0, 100 - abs(brightness - 140) / 2),
            'resolution': min(100, resolution * 50)
        }

        weights = {
            'sharpness': 0.30,
            'contrast': 0.25,
            'noise': 0.20,
            'resolution': 0.15,
            'brightness': 0.10
        }

        total_score = sum(normalized[k] * weights[k] for k in weights)

        if total_score >= 80:
            quality_level = 'excellent'
            recommended_preset = 'minimal'
        elif total_score >= 60:
            quality_level = 'good'
            recommended_preset = 'selective'
        else:
            quality_level = 'poor'
            recommended_preset = 'selective'

        needs_sharpening = sharpness < 100
        needs_denoising = noise > 30
        needs_contrast_boost = contrast < 50
        needs_brightness_adjustment = brightness < 100 or brightness > 200
        is_low_resolution = resolution < 1.0

        return {
            'scores': scores,
            'normalized_scores': normalized,
            'total_score': total_score,
            'quality_level': quality_level,
            'recommended_preset': recommended_preset,
            'analysis': {
                'needs_sharpening': bool(needs_sharpening),
                'needs_denoising': bool(needs_denoising),
                'needs_contrast_boost': bool(needs_contrast_boost),
                'needs_brightness_adjustment': bool(needs_brightness_adjustment),
                'is_low_resolution': bool(is_low_resolution),
                'contrast_factor': 2.0 if contrast < 30 else 1.5 if contrast < 50 else 1.2,
                'brightness_adjustment': -0.3 if brightness > 200 else 0.3 if brightness < 100 else 0
            }
        }


class ImagePreprocessor:
    """이미지 전처리 클래스"""

    @staticmethod
    def pil_to_cv2(pil_image):
        """PIL Image를 OpenCV 형식으로 변환"""
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    @staticmethod
    def cv2_to_pil(cv2_image):
        """OpenCV 이미지를 PIL 형식으로 변환"""
        return Image.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))

    @staticmethod
    def grayscale(image):
        """그레이스케일 변환"""
        if isinstance(image, Image.Image):
            return image.convert('L')
        else:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def increase_contrast(image, factor=2.0):
        """대비 증가"""
        if isinstance(image, Image.Image):
            enhancer = ImageEnhance.Contrast(image)
            return enhancer.enhance(factor)
        else:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(image)

    @staticmethod
    def sharpen(image):
        """선명도 증가"""
        if isinstance(image, Image.Image):
            return image.filter(ImageFilter.SHARPEN)
        else:
            kernel = np.array([[-1, -1, -1],
                             [-1,  9, -1],
                             [-1, -1, -1]])
            return cv2.filter2D(image, -1, kernel)

    @staticmethod
    def denoise(image):
        """노이즈 제거"""
        if isinstance(image, Image.Image):
            return image.filter(ImageFilter.MedianFilter(size=3))
        else:
            return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)

    @staticmethod
    def binarization(image, method='otsu'):
        """이진화"""
        if isinstance(image, Image.Image):
            image = ImagePreprocessor.pil_to_cv2(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if method == 'otsu':
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif method == 'adaptive':
            binary = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 11, 2)
        else:
            _, binary = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)

        return ImagePreprocessor.cv2_to_pil(binary)

    @staticmethod
    def remove_shadows(image):
        """그림자 제거"""
        if isinstance(image, Image.Image):
            image = ImagePreprocessor.pil_to_cv2(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        dilated = cv2.dilate(image, np.ones((7, 7), np.uint8))
        bg = cv2.medianBlur(dilated, 21)
        diff = 255 - cv2.absdiff(image, bg)
        norm = cv2.normalize(diff, None, alpha=0, beta=255,
                            norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)

        return ImagePreprocessor.cv2_to_pil(norm)

    @staticmethod
    def deskew(image):
        """기울기 보정"""
        if isinstance(image, Image.Image):
            image = ImagePreprocessor.pil_to_cv2(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        coords = np.column_stack(np.where(image > 0))

        if len(coords) == 0:
            return ImagePreprocessor.cv2_to_pil(image)

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h),
                                flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_REPLICATE)

        return ImagePreprocessor.cv2_to_pil(rotated)

    @staticmethod
    def upscale(image, scale=2):
        """해상도 증가"""
        if isinstance(image, Image.Image):
            new_size = (image.width * scale, image.height * scale)
            return image.resize(new_size, Image.Resampling.LANCZOS)
        else:
            return cv2.resize(image, None, fx=scale, fy=scale,
                            interpolation=cv2.INTER_CUBIC)

    @staticmethod
    def morphology_operations(image):
        """형태학적 연산"""
        if isinstance(image, Image.Image):
            image = ImagePreprocessor.pil_to_cv2(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        kernel = np.ones((2, 2), np.uint8)
        closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)

        return ImagePreprocessor.cv2_to_pil(opened)

    @staticmethod
    def adjust_brightness(image, factor=0.0):
        """밝기 조정 (factor: -1.0 ~ 1.0)"""
        if isinstance(image, Image.Image):
            enhancer = ImageEnhance.Brightness(image)
            return enhancer.enhance(1.0 + factor)
        else:
            adjusted = cv2.convertScaleAbs(image, alpha=1.0, beta=int(255 * factor))
            return adjusted


def pdf_page_to_image(page, dpi: int = 300) -> Image.Image:
    """PDF 페이지를 이미지로 변환"""
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def preprocess_image_selective(image, quality_analysis: Dict[str, Any]):
    """품질 분석 결과에 따른 선택적 전처리"""
    preprocessor = ImagePreprocessor()
    analysis = quality_analysis['analysis']
    steps = []

    image = preprocessor.grayscale(image)
    steps.append("grayscale")

    if analysis['is_low_resolution']:
        image = preprocessor.upscale(image, scale=2)
        steps.append("upscale(2x)")

    if analysis['needs_denoising']:
        image = preprocessor.denoise(image)
        steps.append("denoise")

    if analysis['needs_brightness_adjustment']:
        factor = analysis['brightness_adjustment']
        image = preprocessor.adjust_brightness(image, factor=factor)
        steps.append(f"brightness({factor:+.1f})")

    if analysis['needs_contrast_boost']:
        factor = analysis['contrast_factor']
        image = preprocessor.increase_contrast(image, factor=factor)
        steps.append(f"contrast({factor}x)")

    if analysis['needs_sharpening']:
        image = preprocessor.sharpen(image)
        steps.append("sharpen")

    quality_level = quality_analysis['quality_level']
    if quality_level == 'poor':
        image = preprocessor.binarization(image, method='adaptive')
        steps.append("binarize(adaptive)")
    elif analysis['needs_contrast_boost']:
        image = preprocessor.binarization(image, method='otsu')
        steps.append("binarize(otsu)")

    logger.debug(f"Preprocessing steps: {' -> '.join(steps)}")
    return image


def preprocess_image_pipeline(image, preset: str = 'standard'):
    """전처리 파이프라인 (preset 기반)"""
    preprocessor = ImagePreprocessor()

    if preset == 'standard':
        image = preprocessor.grayscale(image)
        image = preprocessor.denoise(image)
        image = preprocessor.increase_contrast(image, factor=1.5)
        image = preprocessor.sharpen(image)
        image = preprocessor.binarization(image, method='otsu')

    elif preset == 'aggressive':
        image = preprocessor.upscale(image, scale=2)
        image = preprocessor.remove_shadows(image)
        image = preprocessor.deskew(image)
        image = preprocessor.denoise(image)
        image = preprocessor.increase_contrast(image, factor=2.0)
        image = preprocessor.binarization(image, method='adaptive')

    elif preset == 'light':
        image = preprocessor.grayscale(image)
        image = preprocessor.increase_contrast(image, factor=1.2)
        image = preprocessor.sharpen(image)

    elif preset == 'minimal':
        image = preprocessor.grayscale(image)
        image = preprocessor.increase_contrast(image, factor=1.1)

    return image


def ocr_image_with_preprocessing(
    image,
    lang: str = 'kor+eng',
    preset: str = 'standard',
    quality_analysis: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """전처리 후 OCR 수행"""
    if quality_analysis and preset in ['selective', 'minimal']:
        processed_image = preprocess_image_selective(image, quality_analysis)
    else:
        processed_image = preprocess_image_pipeline(image, preset=preset)

    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(processed_image, lang=lang, config=custom_config)

    data = pytesseract.image_to_data(processed_image, lang=lang,
                                     config=custom_config, output_type=pytesseract.Output.DICT)

    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    return {
        'text': text,
        'confidence': avg_confidence,
        'word_count': len([w for w in data['text'] if w.strip()])
    }


def extract_pdf_with_preprocessing(
    pdf_path: Path,
    dpi: int = 300,
    preset: str = 'standard',
    adaptive: bool = False
) -> Dict[str, Any]:
    """
    PDF에서 전처리 + OCR 추출

    Args:
        pdf_path: PDF 파일 경로
        dpi: 해상도 (기본 300)
        preset: 전처리 모드 ('light', 'standard', 'aggressive', 'minimal')
        adaptive: True이면 페이지별 품질 평가 후 자동 선택

    Returns:
        추출 결과 dict
    """
    logger.info(f"Processing: {pdf_path}")

    doc = fitz.open(pdf_path)

    pages = []
    total_chars = 0
    total_confidence = 0
    preset_usage = {}

    for page_num in range(len(doc)):
        page = doc[page_num]

        logger.debug(f"Processing page {page_num + 1}/{len(doc)}")

        image = pdf_page_to_image(page, dpi=dpi)

        if adaptive:
            quality_assessment = DocumentQualityAssessor.assess_quality(image)
            selected_preset = quality_assessment['recommended_preset']
            logger.debug(f"Quality: {quality_assessment['quality_level']}, preset: {selected_preset}")
            preset_usage[selected_preset] = preset_usage.get(selected_preset, 0) + 1
        else:
            selected_preset = preset
            quality_assessment = None

        ocr_result = ocr_image_with_preprocessing(
            image,
            lang='kor+eng',
            preset=selected_preset,
            quality_analysis=quality_assessment
        )

        char_count = len(ocr_result['text'])
        confidence = ocr_result['confidence']

        page_data = {
            'page_number': page_num + 1,
            'text': ocr_result['text'],
            'char_count': char_count,
            'confidence': confidence,
            'word_count': ocr_result['word_count'],
            'preprocessing_used': selected_preset
        }

        if adaptive and quality_assessment:
            page_data['quality_assessment'] = quality_assessment

        pages.append(page_data)

        total_chars += char_count
        total_confidence += confidence

    doc.close()

    avg_confidence = total_confidence / len(pages) if pages else 0

    result = {
        'filename': pdf_path.name if hasattr(pdf_path, 'name') else str(pdf_path),
        'page_count': len(pages),
        'dpi': dpi,
        'preprocessing': preset if not adaptive else 'adaptive',
        'adaptive_mode': adaptive,
        'total_chars': total_chars,
        'avg_confidence': avg_confidence,
        'pages': pages
    }

    if adaptive:
        result['preset_usage'] = preset_usage

    logger.info(f"Completed: {total_chars} chars, avg confidence: {avg_confidence:.1f}%")

    return result
