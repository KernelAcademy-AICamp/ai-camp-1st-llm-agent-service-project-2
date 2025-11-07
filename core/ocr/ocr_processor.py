"""
이미지 전처리를 통한 OCR 품질 개선
다양한 전처리 기법을 적용하여 OCR 정확도 향상
"""

import fitz  # PyMuPDF
from pathlib import Path
import json
from datetime import datetime
import logging
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import numpy as np
import cv2
import io
import unicodedata

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentQualityAssessor:
    """문서 품질 평가 클래스"""

    @staticmethod
    def assess_sharpness(image):
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
    def assess_noise(image):
        """
        노이즈 수준 평가 (표준편차 분석)
        높을수록 노이즈가 많음 (>50: 많음, 20-50: 보통, <20: 적음)
        """
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        elif len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 로컬 표준편차로 노이즈 추정
        kernel_size = 5
        local_mean = cv2.blur(image.astype(float), (kernel_size, kernel_size))
        local_sq_mean = cv2.blur((image.astype(float) ** 2), (kernel_size, kernel_size))
        local_variance = local_sq_mean - (local_mean ** 2)
        noise_level = np.mean(np.sqrt(local_variance))

        return noise_level

    @staticmethod
    def assess_contrast(image):
        """
        대비 평가 (히스토그램 분석)
        높을수록 대비가 좋음 (>80: 좋음, 40-80: 보통, <40: 낮음)
        """
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        elif len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # RMS contrast (Root Mean Square)
        rms_contrast = np.std(image)
        return rms_contrast

    @staticmethod
    def assess_brightness(image):
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
    def assess_resolution(image):
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
    def assess_quality(image):
        """
        종합 품질 평가 (가중치 기반)
        Returns: dict with quality scores and recommended preprocessing
        """
        sharpness = DocumentQualityAssessor.assess_sharpness(image)
        noise = DocumentQualityAssessor.assess_noise(image)
        contrast = DocumentQualityAssessor.assess_contrast(image)
        brightness = DocumentQualityAssessor.assess_brightness(image)
        resolution = DocumentQualityAssessor.assess_resolution(image)

        # 원본 점수
        scores = {
            'sharpness': sharpness,
            'noise': noise,
            'contrast': contrast,
            'brightness': brightness,
            'resolution_mp': resolution
        }

        # 각 항목을 0-100 점수로 정규화
        normalized = {
            'sharpness': min(100, sharpness / 2),  # 200 = 100점
            'noise': max(0, 100 - noise * 2),      # 0 = 100점, 50+ = 0점
            'contrast': min(100, contrast * 1.25), # 80 = 100점
            'brightness': 100 if 100 < brightness < 180 else max(0, 100 - abs(brightness - 140) / 2),
            'resolution': min(100, resolution * 50)  # 2MP = 100점
        }

        # 가중치 적용 (중요도에 따라)
        weights = {
            'sharpness': 0.30,    # 선명도 가장 중요
            'contrast': 0.25,     # 대비 중요
            'noise': 0.20,        # 노이즈 중간
            'resolution': 0.15,   # 해상도 중간
            'brightness': 0.10    # 밝기 덜 중요
        }

        # 총점 계산
        total_score = sum(normalized[k] * weights[k] for k in weights)

        # 품질 등급 및 전처리 전략 결정
        if total_score >= 80:
            quality_level = 'excellent'
            recommended_preset = 'minimal'
        elif total_score >= 60:
            quality_level = 'good'
            recommended_preset = 'selective'
        else:
            quality_level = 'poor'
            recommended_preset = 'selective'

        # 전처리 필요도 판단 (개별)
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
        """그레이스케일 변환 - 색상 정보 제거로 텍스트 강조"""
        if isinstance(image, Image.Image):
            return image.convert('L')
        else:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def increase_contrast(image, factor=2.0):
        """대비 증가 - 텍스트와 배경의 구분 명확화"""
        if isinstance(image, Image.Image):
            enhancer = ImageEnhance.Contrast(image)
            return enhancer.enhance(factor)
        else:
            # OpenCV: CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(image)

    @staticmethod
    def sharpen(image):
        """선명도 증가 - 흐릿한 텍스트 개선"""
        if isinstance(image, Image.Image):
            return image.filter(ImageFilter.SHARPEN)
        else:
            kernel = np.array([[-1, -1, -1],
                             [-1,  9, -1],
                             [-1, -1, -1]])
            return cv2.filter2D(image, -1, kernel)

    @staticmethod
    def denoise(image):
        """노이즈 제거 - 얼룩, 점 제거"""
        if isinstance(image, Image.Image):
            # PIL은 간단한 필터만 제공
            return image.filter(ImageFilter.MedianFilter(size=3))
        else:
            # OpenCV: Non-local Means Denoising
            return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)

    @staticmethod
    def binarization(image, method='otsu'):
        """이진화 - 흑백으로 명확히 구분"""
        if isinstance(image, Image.Image):
            image = ImagePreprocessor.pil_to_cv2(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if method == 'otsu':
            # Otsu's 자동 임계값
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif method == 'adaptive':
            # 적응형 임계값 (국소 영역별 임계값)
            binary = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 11, 2)
        else:
            # 고정 임계값
            _, binary = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)

        return ImagePreprocessor.cv2_to_pil(binary)

    @staticmethod
    def remove_shadows(image):
        """그림자 제거 - 스캔 문서의 그림자 영향 감소"""
        if isinstance(image, Image.Image):
            image = ImagePreprocessor.pil_to_cv2(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Morphological operations으로 배경 추정
        dilated = cv2.dilate(image, np.ones((7, 7), np.uint8))
        bg = cv2.medianBlur(dilated, 21)

        # 배경을 빼서 그림자 제거
        diff = 255 - cv2.absdiff(image, bg)

        # 정규화
        norm = cv2.normalize(diff, None, alpha=0, beta=255,
                            norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)

        return ImagePreprocessor.cv2_to_pil(norm)

    @staticmethod
    def deskew(image):
        """기울기 보정 - 스캔 시 기울어진 문서 보정"""
        if isinstance(image, Image.Image):
            image = ImagePreprocessor.pil_to_cv2(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 텍스트 감지
        coords = np.column_stack(np.where(image > 0))

        if len(coords) == 0:
            return ImagePreprocessor.cv2_to_pil(image)

        # 최소 영역 사각형으로 각도 계산
        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # 회전
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h),
                                flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_REPLICATE)

        return ImagePreprocessor.cv2_to_pil(rotated)

    @staticmethod
    def upscale(image, scale=2):
        """해상도 증가 - 작은 텍스트 개선"""
        if isinstance(image, Image.Image):
            new_size = (image.width * scale, image.height * scale)
            return image.resize(new_size, Image.Resampling.LANCZOS)
        else:
            return cv2.resize(image, None, fx=scale, fy=scale,
                            interpolation=cv2.INTER_CUBIC)

    @staticmethod
    def morphology_operations(image):
        """형태학적 연산 - 텍스트 구조 개선"""
        if isinstance(image, Image.Image):
            image = ImagePreprocessor.pil_to_cv2(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 작은 구멍 채우기
        kernel = np.ones((2, 2), np.uint8)
        closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)

        # 작은 점 제거
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)

        return ImagePreprocessor.cv2_to_pil(opened)

    @staticmethod
    def adjust_brightness(image, factor=0.0):
        """
        밝기 조정
        factor: -1.0 ~ 1.0 (음수=어둡게, 양수=밝게)
        """
        if isinstance(image, Image.Image):
            enhancer = ImageEnhance.Brightness(image)
            return enhancer.enhance(1.0 + factor)
        else:
            # OpenCV: 밝기 조정
            adjusted = cv2.convertScaleAbs(image, alpha=1.0, beta=int(255 * factor))
            return adjusted


def pdf_page_to_image(page, dpi=300):
    """PDF 페이지를 이미지로 변환 (기본)"""
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def preprocess_image_selective(image, quality_analysis):
    """
    품질 분석 결과에 따른 선택적 전처리
    필요한 처리만 적용하여 최적화
    """
    preprocessor = ImagePreprocessor()
    analysis = quality_analysis['analysis']
    steps = []

    # 항상 그레이스케일 변환
    image = preprocessor.grayscale(image)
    steps.append("그레이스케일")

    # 저해상도인 경우 해상도 증가
    if analysis['is_low_resolution']:
        image = preprocessor.upscale(image, scale=2)
        steps.append("해상도 증가(2배)")

    # 노이즈 제거 (필요한 경우)
    if analysis['needs_denoising']:
        image = preprocessor.denoise(image)
        steps.append("노이즈 제거")

    # 밝기 조정 (필요한 경우)
    if analysis['needs_brightness_adjustment']:
        factor = analysis['brightness_adjustment']
        image = preprocessor.adjust_brightness(image, factor=factor)
        steps.append(f"밝기 조정({factor:+.1f})")

    # 대비 증가 (필요한 경우)
    if analysis['needs_contrast_boost']:
        factor = analysis['contrast_factor']
        image = preprocessor.increase_contrast(image, factor=factor)
        steps.append(f"대비 증가({factor}배)")

    # 선명도 개선 (필요한 경우)
    if analysis['needs_sharpening']:
        image = preprocessor.sharpen(image)
        steps.append("선명도")

    # 품질이 나쁜 경우에만 이진화
    quality_level = quality_analysis['quality_level']
    if quality_level == 'poor':
        image = preprocessor.binarization(image, method='adaptive')
        steps.append("이진화(적응형)")
    elif analysis['needs_contrast_boost']:
        # 대비가 약간 낮은 경우 Otsu 이진화
        image = preprocessor.binarization(image, method='otsu')
        steps.append("이진화(Otsu)")

    logger.info(f"    전처리: {' → '.join(steps)}")
    return image


def preprocess_image_pipeline(image, preset='standard'):
    """
    전처리 파이프라인 (레거시 - 하위 호환성 유지)

    Presets:
    - 'standard': 표준 전처리 (대부분의 경우)
    - 'aggressive': 강력한 전처리 (품질이 나쁜 경우)
    - 'light': 가벼운 전처리 (품질이 좋은 경우)
    - 'custom': 모든 전처리 적용
    """
    preprocessor = ImagePreprocessor()

    if preset == 'standard':
        # 표준: 그레이스케일 → 노이즈 제거 → 대비 증가 → 선명도 → 이진화
        logger.info("    전처리: 그레이스케일 → 노이즈 제거 → 대비 증가 → 선명도 → 이진화")
        image = preprocessor.grayscale(image)
        image = preprocessor.denoise(image)
        image = preprocessor.increase_contrast(image, factor=1.5)
        image = preprocessor.sharpen(image)
        image = preprocessor.binarization(image, method='otsu')

    elif preset == 'aggressive':
        # 강력: 해상도 증가 → 그림자 제거 → 기울기 보정 → 노이즈 제거 → 대비 → 이진화
        logger.info("    전처리: 해상도 증가 → 그림자 제거 → 기울기 보정 → 노이즈 제거 → 대비 → 이진화")
        image = preprocessor.upscale(image, scale=2)
        image = preprocessor.remove_shadows(image)
        image = preprocessor.deskew(image)
        image = preprocessor.denoise(image)
        image = preprocessor.increase_contrast(image, factor=2.0)
        image = preprocessor.binarization(image, method='adaptive')

    elif preset == 'light':
        # 가벼운: 그레이스케일 → 대비 증가 → 선명도
        logger.info("    전처리: 그레이스케일 → 대비 증가 → 선명도")
        image = preprocessor.grayscale(image)
        image = preprocessor.increase_contrast(image, factor=1.2)
        image = preprocessor.sharpen(image)

    elif preset == 'custom':
        # 모든 전처리 적용 (실험용)
        logger.info("    전처리: 전체 파이프라인 적용")
        image = preprocessor.upscale(image, scale=2)
        image = preprocessor.grayscale(image)
        image = preprocessor.remove_shadows(image)
        image = preprocessor.deskew(image)
        image = preprocessor.denoise(image)
        image = preprocessor.increase_contrast(image, factor=1.8)
        image = preprocessor.sharpen(image)
        image = preprocessor.morphology_operations(image)
        image = preprocessor.binarization(image, method='adaptive')

    return image


def ocr_image_with_preprocessing(image, lang='kor+eng', preset='standard', quality_analysis=None):
    """전처리 후 OCR 수행"""
    # 선택적 전처리 (품질 분석 결과가 있으면)
    if quality_analysis and preset in ['selective', 'minimal']:
        processed_image = preprocess_image_selective(image, quality_analysis)
    else:
        # 레거시 전처리 (preset 사용)
        processed_image = preprocess_image_pipeline(image, preset=preset)

    # OCR 실행
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(processed_image, lang=lang, config=custom_config)

    # 신뢰도 계산
    data = pytesseract.image_to_data(processed_image, lang=lang,
                                     config=custom_config, output_type=pytesseract.Output.DICT)

    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    return {
        'text': text,
        'confidence': avg_confidence,
        'word_count': len([w for w in data['text'] if w.strip()])
    }


def extract_pdf_with_preprocessing(pdf_path: Path, dpi=300, preset='standard', adaptive=False):
    """
    PDF에서 전처리 + OCR 추출

    Args:
        pdf_path: PDF 파일 경로
        dpi: 해상도
        preset: 전처리 모드 ('light', 'standard', 'aggressive')
        adaptive: True이면 페이지별 품질 평가 후 자동 선택
    """
    logger.info(f"처리 중: {pdf_path.name}")

    if adaptive:
        logger.info(f"  전처리 모드: 적응형 (페이지별 자동 선택)")
    else:
        logger.info(f"  전처리 모드: {preset} (고정)")

    doc = fitz.open(pdf_path)

    pages = []
    total_chars = 0
    total_confidence = 0
    preset_usage = {}

    for page_num in range(len(doc)):
        page = doc[page_num]

        logger.info(f"  → Page {page_num + 1}/{len(doc)} 처리 중...")

        # PDF → 이미지 변환
        image = pdf_page_to_image(page, dpi=dpi)

        # 적응형 모드: 품질 평가 후 preset 선택
        if adaptive:
            quality_assessment = DocumentQualityAssessor.assess_quality(image)
            selected_preset = quality_assessment['recommended_preset']

            logger.info(f"     품질 평가: {quality_assessment['quality_level'].upper()} (종합점수: {quality_assessment['total_score']:.1f}/100)")
            logger.info(f"       - 선명도: {quality_assessment['scores']['sharpness']:.1f} ({quality_assessment['normalized_scores']['sharpness']:.0f}점)")
            logger.info(f"       - 노이즈: {quality_assessment['scores']['noise']:.1f} ({quality_assessment['normalized_scores']['noise']:.0f}점)")
            logger.info(f"       - 대비: {quality_assessment['scores']['contrast']:.1f} ({quality_assessment['normalized_scores']['contrast']:.0f}점)")
            logger.info(f"       - 밝기: {quality_assessment['scores']['brightness']:.1f} ({quality_assessment['normalized_scores']['brightness']:.0f}점)")
            logger.info(f"       - 해상도: {quality_assessment['scores']['resolution_mp']:.2f}MP ({quality_assessment['normalized_scores']['resolution']:.0f}점)")
            logger.info(f"     → 전처리 전략: {selected_preset.upper()}")

            # 필요한 전처리 항목 출력
            analysis = quality_assessment['analysis']
            needs = []
            if analysis['needs_sharpening']:
                needs.append("선명도")
            if analysis['needs_denoising']:
                needs.append("노이즈제거")
            if analysis['needs_contrast_boost']:
                needs.append(f"대비증가({analysis['contrast_factor']}배)")
            if analysis['needs_brightness_adjustment']:
                needs.append(f"밝기조정({analysis['brightness_adjustment']:+.1f})")
            if analysis['is_low_resolution']:
                needs.append("해상도증가")

            logger.info(f"     → 필요한 처리: {', '.join(needs) if needs else '없음'}")

            preset_usage[selected_preset] = preset_usage.get(selected_preset, 0) + 1
        else:
            selected_preset = preset
            quality_assessment = None

        # 전처리 + OCR
        ocr_result = ocr_image_with_preprocessing(image, lang='kor+eng', preset=selected_preset, quality_analysis=quality_assessment)

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

        logger.info(f"     글자 수: {char_count}자, 신뢰도: {confidence:.1f}%")

    doc.close()

    avg_confidence = total_confidence / len(pages) if pages else 0

    result = {
        'filename': pdf_path.name,
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

    logger.info(f"  완료: 총 {total_chars:,}자, 평균 신뢰도: {avg_confidence:.1f}%")

    if adaptive and preset_usage:
        logger.info(f"  전처리 사용 통계: {preset_usage}")

    return result


def compare_preprocessing_methods(pdf_path: Path, dpi=300):
    """여러 전처리 방법 비교"""
    logger.info(f"\n{'='*70}")
    logger.info(f"전처리 방법 비교: {pdf_path.name}")
    logger.info('='*70)

    presets = ['light', 'standard', 'aggressive']
    results = []

    for preset in presets:
        logger.info(f"\n[{preset.upper()}] 전처리 적용 중...")
        result = extract_pdf_with_preprocessing(pdf_path, dpi=dpi, preset=preset)
        results.append(result)

    # 비교 결과
    logger.info(f"\n{'='*70}")
    logger.info("전처리 방법 비교 결과")
    logger.info('='*70)

    for result in results:
        logger.info(f"\n[{result['preprocessing'].upper()}]")
        logger.info(f"  총 글자 수: {result['total_chars']:,}자")
        logger.info(f"  평균 신뢰도: {result['avg_confidence']:.1f}%")

    return results


def main():
    """메인 실행"""
    pdf_dir = Path("raw_pdf_data")

    # 이미지 기반 PDF 파일 찾기
    all_pdfs = list(pdf_dir.glob("*.pdf"))
    pdf_files = []

    for pdf_file in all_pdfs:
        normalized_name = unicodedata.normalize('NFC', pdf_file.name)
        if '변환' in normalized_name or 'converted' in normalized_name:
            pdf_files.append(pdf_file)

    if not pdf_files:
        logger.error("이미지 기반 PDF 파일을 찾을 수 없습니다.")
        return

    logger.info("="*70)
    logger.info("전처리 기반 OCR 텍스트 추출")
    logger.info("="*70)
    logger.info(f"총 {len(pdf_files)}개 파일")
    logger.info("")

    # 적응형 전처리 사용
    use_adaptive = True  # True: 품질 기반 자동 선택, False: 고정 preset
    preset = 'standard'  # adaptive=False일 때 사용

    if use_adaptive:
        logger.info(f"전처리 모드: 적응형 (자동 품질 평가)")
    else:
        logger.info(f"전처리 모드: {preset} (고정)")

    logger.info(f"OCR 엔진: Tesseract")
    logger.info(f"언어: 한글 + 영어 (kor+eng)")
    logger.info(f"해상도: 300 DPI")
    logger.info("="*70)
    logger.info("")

    # 모든 파일 처리
    all_results = []

    for idx, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"\n[{idx}/{len(pdf_files)}] {pdf_file.name}")
        result = extract_pdf_with_preprocessing(pdf_file, dpi=300, preset=preset, adaptive=use_adaptive)
        all_results.append(result)

    # 결과 저장
    output_dir = Path("extracted_pdf_data")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    mode_str = 'adaptive' if use_adaptive else preset

    # JSON 저장
    json_file = output_dir / f"ocr_preprocessed_{mode_str}_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            "추출시각": datetime.now().isoformat(),
            "파일수": len(all_results),
            "OCR엔진": "Tesseract",
            "언어": "kor+eng",
            "DPI": 300,
            "전처리모드": "적응형" if use_adaptive else preset,
            "문서": all_results
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ JSON 저장: {json_file}")

    # 개별 텍스트 파일 저장
    for result in all_results:
        txt_filename = result['filename'].replace('.pdf', f'_preprocessed_{mode_str}.txt')
        txt_file = output_dir / txt_filename

        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"파일: {result['filename']}\n")
            f.write(f"페이지 수: {result['page_count']}\n")
            f.write(f"전처리: {result['preprocessing']}\n")

            if result.get('adaptive_mode'):
                f.write(f"전처리 사용 통계: {result.get('preset_usage', {})}\n")

            f.write(f"OCR 언어: kor+eng\n")
            f.write(f"해상도: {result['dpi']} DPI\n")
            f.write(f"평균 신뢰도: {result['avg_confidence']:.1f}%\n")
            f.write("="*70 + "\n\n")

            for page in result['pages']:
                preset_used = page.get('preprocessing_used', 'unknown')
                f.write(f"[Page {page['page_number']}] (전처리: {preset_used}, 신뢰도: {page['confidence']:.1f}%)\n")

                if page.get('quality_assessment'):
                    qa = page['quality_assessment']
                    f.write(f"  품질: {qa['quality_level']} (선명도: {qa['scores']['sharpness']:.1f}, "
                           f"노이즈: {qa['scores']['noise']:.1f}, 대비: {qa['scores']['contrast']:.1f})\n")

                f.write("\n")
                f.write(page['text'])
                f.write("\n" + "-"*70 + "\n\n")

        logger.info(f"✅ 개별 파일 저장: {txt_file}")

    # 요약 통계
    logger.info("\n" + "="*70)
    logger.info("📊 최종 요약")
    logger.info("="*70)
    logger.info(f"처리된 파일: {len(all_results)}개")
    logger.info(f"총 페이지: {sum(r['page_count'] for r in all_results)}페이지")
    logger.info(f"총 글자 수: {sum(r['total_chars'] for r in all_results):,}자")
    logger.info(f"평균 신뢰도: {sum(r['avg_confidence'] for r in all_results) / len(all_results):.1f}%")

    if use_adaptive:
        # 전체 preset 사용 통계
        total_preset_usage = {}
        for result in all_results:
            if result.get('preset_usage'):
                for preset_name, count in result['preset_usage'].items():
                    total_preset_usage[preset_name] = total_preset_usage.get(preset_name, 0) + count

        logger.info("")
        logger.info(f"전처리 모드: 적응형")
        logger.info(f"전처리 사용 통계: {total_preset_usage}")
    else:
        logger.info("")
        logger.info(f"전처리 방법: {preset}")

    logger.info("="*70)

    return all_results


def test_single_file_comparison():
    """단일 파일로 전처리 방법 비교 테스트"""
    pdf_dir = Path("raw_pdf_data")

    # 첫 번째 converted 파일 찾기
    for pdf_file in pdf_dir.glob("*.pdf"):
        normalized_name = unicodedata.normalize('NFC', pdf_file.name)
        if '변환' in normalized_name or 'converted' in normalized_name:
            compare_preprocessing_methods(pdf_file, dpi=300)
            break


if __name__ == "__main__":
    # 전체 파일 처리
    main()

    # 또는 단일 파일 비교 테스트
    # test_single_file_comparison()
