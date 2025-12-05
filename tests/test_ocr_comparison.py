#!/usr/bin/env python
"""
Surya OCR vs Tesseract OCR 비교 테스트
형사사건 관련 이미지로 두 엔진의 성능을 비교
"""

import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, List
import json

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "apps" / "ai_service"))

from PIL import Image
import pytesseract

# Surya OCR
try:
    from surya.recognition import RecognitionPredictor, FoundationPredictor
    from surya.detection import DetectionPredictor
    import torch
    SURYA_AVAILABLE = True
except ImportError:
    SURYA_AVAILABLE = False

# 테스트 이미지 폴더
TEST_IMAGE_DIR = project_root / "docs" / "test" / "criminal_ocr_test"


class OCRComparison:
    """OCR 엔진 비교 클래스"""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

        # Surya 초기화
        if SURYA_AVAILABLE:
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

            print(f"Surya OCR 디바이스: {self.device}")
            self.detection_predictor = DetectionPredictor(device=self.device)
            self.foundation_predictor = FoundationPredictor(device=self.device)
            self.recognition_predictor = RecognitionPredictor(self.foundation_predictor)
        else:
            print("Surya OCR을 사용할 수 없습니다.")

    def ocr_with_surya(self, image: Image.Image) -> Dict[str, Any]:
        """Surya OCR로 텍스트 추출"""
        if not SURYA_AVAILABLE:
            return {'text': '', 'time': 0, 'error': 'Surya not available'}

        start_time = time.time()

        try:
            # RGB 변환
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # OCR 수행
            results = self.recognition_predictor([image], det_predictor=self.detection_predictor)

            # 텍스트 추출
            text_lines = []
            total_confidence = 0.0
            count = 0

            for result in results:
                for line in result.text_lines:
                    text_lines.append(line.text)
                    if hasattr(line, 'confidence') and line.confidence:
                        total_confidence += line.confidence
                        count += 1

            text = '\n'.join(text_lines)
            avg_confidence = (total_confidence / count * 100) if count > 0 else 95.0
            elapsed = time.time() - start_time

            return {
                'text': text,
                'time': elapsed,
                'confidence': avg_confidence,
                'line_count': len(text_lines),
                'char_count': len(text)
            }

        except Exception as e:
            return {'text': '', 'time': time.time() - start_time, 'error': str(e)}

    def ocr_with_tesseract(self, image: Image.Image) -> Dict[str, Any]:
        """Tesseract OCR로 텍스트 추출"""
        start_time = time.time()

        try:
            # RGB 변환
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # OCR 수행 (한글+영어)
            config = r'--oem 3 --psm 6 -l kor+eng'
            text = pytesseract.image_to_string(image, config=config)

            # 신뢰도 계산
            data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data['conf'] if str(c).lstrip('-').isdigit() and int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            elapsed = time.time() - start_time

            return {
                'text': text.strip(),
                'time': elapsed,
                'confidence': avg_confidence,
                'line_count': len([l for l in text.split('\n') if l.strip()]),
                'char_count': len(text.strip())
            }

        except Exception as e:
            return {'text': '', 'time': time.time() - start_time, 'error': str(e)}

    def compare_single_image(self, image_path: Path) -> Dict[str, Any]:
        """단일 이미지에 대해 두 엔진 비교"""
        print(f"\n{'='*60}")
        print(f"테스트: {image_path.name}")
        print('='*60)

        image = Image.open(image_path)
        print(f"이미지 크기: {image.size}, 모드: {image.mode}")

        # Surya OCR
        print("\n[Surya OCR 실행 중...]")
        surya_result = self.ocr_with_surya(image)
        print(f"  - 처리 시간: {surya_result['time']:.2f}초")
        print(f"  - 신뢰도: {surya_result.get('confidence', 0):.1f}%")
        print(f"  - 추출 글자 수: {surya_result.get('char_count', 0)}")

        # Tesseract OCR
        print("\n[Tesseract OCR 실행 중...]")
        tesseract_result = self.ocr_with_tesseract(image)
        print(f"  - 처리 시간: {tesseract_result['time']:.2f}초")
        print(f"  - 신뢰도: {tesseract_result.get('confidence', 0):.1f}%")
        print(f"  - 추출 글자 수: {tesseract_result.get('char_count', 0)}")

        result = {
            'image': image_path.name,
            'image_size': f"{image.size[0]}x{image.size[1]}",
            'surya': surya_result,
            'tesseract': tesseract_result
        }

        self.results.append(result)
        return result

    def run_comparison(self):
        """모든 테스트 이미지에 대해 비교 실행"""
        print("\n" + "="*70)
        print("Surya OCR vs Tesseract OCR 비교 테스트")
        print("="*70)

        if not TEST_IMAGE_DIR.exists():
            print(f"테스트 이미지 폴더가 없습니다: {TEST_IMAGE_DIR}")
            return

        image_files = sorted(TEST_IMAGE_DIR.glob("*.png"))
        print(f"테스트 이미지 수: {len(image_files)}")

        for image_path in image_files:
            self.compare_single_image(image_path)

        self.print_summary()

    def print_summary(self):
        """비교 결과 요약 출력"""
        print("\n" + "="*70)
        print("비교 결과 요약")
        print("="*70)

        # 헤더
        print(f"\n{'이미지':<30} {'Surya시간':<10} {'Surya신뢰도':<12} {'Tess시간':<10} {'Tess신뢰도':<12}")
        print("-"*74)

        total_surya_time = 0
        total_tess_time = 0
        total_surya_conf = 0
        total_tess_conf = 0

        for r in self.results:
            surya_time = r['surya'].get('time', 0)
            surya_conf = r['surya'].get('confidence', 0)
            tess_time = r['tesseract'].get('time', 0)
            tess_conf = r['tesseract'].get('confidence', 0)

            total_surya_time += surya_time
            total_tess_time += tess_time
            total_surya_conf += surya_conf
            total_tess_conf += tess_conf

            print(f"{r['image']:<30} {surya_time:<10.2f} {surya_conf:<12.1f} {tess_time:<10.2f} {tess_conf:<12.1f}")

        n = len(self.results)
        if n > 0:
            print("-"*74)
            print(f"{'평균':<30} {total_surya_time/n:<10.2f} {total_surya_conf/n:<12.1f} {total_tess_time/n:<10.2f} {total_tess_conf/n:<12.1f}")

        # 상세 비교
        print("\n" + "="*70)
        print("OCR 결과 상세 비교")
        print("="*70)

        for r in self.results:
            print(f"\n### {r['image']}")
            print(f"이미지 크기: {r['image_size']}")

            print("\n[Surya OCR 결과]")
            print("-"*40)
            surya_text = r['surya'].get('text', '')[:500]
            print(surya_text if surya_text else "(텍스트 없음)")
            if len(r['surya'].get('text', '')) > 500:
                print("... (이하 생략)")

            print("\n[Tesseract OCR 결과]")
            print("-"*40)
            tess_text = r['tesseract'].get('text', '')[:500]
            print(tess_text if tess_text else "(텍스트 없음)")
            if len(r['tesseract'].get('text', '')) > 500:
                print("... (이하 생략)")

    def get_markdown_report(self) -> str:
        """마크다운 형식의 리포트 생성"""
        report = []
        report.append("## OCR 엔진 비교 테스트 결과\n")
        report.append(f"테스트 일시: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"테스트 이미지 수: {len(self.results)}\n")

        # 요약 테이블
        report.append("\n### 성능 비교 요약\n")
        report.append("| 이미지 | Surya 시간(초) | Surya 신뢰도(%) | Tesseract 시간(초) | Tesseract 신뢰도(%) |")
        report.append("|--------|---------------|-----------------|-------------------|---------------------|")

        total_surya_time = 0
        total_tess_time = 0
        total_surya_conf = 0
        total_tess_conf = 0

        for r in self.results:
            surya_time = r['surya'].get('time', 0)
            surya_conf = r['surya'].get('confidence', 0)
            tess_time = r['tesseract'].get('time', 0)
            tess_conf = r['tesseract'].get('confidence', 0)

            total_surya_time += surya_time
            total_tess_time += tess_time
            total_surya_conf += surya_conf
            total_tess_conf += tess_conf

            report.append(f"| {r['image']} | {surya_time:.2f} | {surya_conf:.1f} | {tess_time:.2f} | {tess_conf:.1f} |")

        n = len(self.results)
        if n > 0:
            report.append(f"| **평균** | **{total_surya_time/n:.2f}** | **{total_surya_conf/n:.1f}** | **{total_tess_time/n:.2f}** | **{total_tess_conf/n:.1f}** |")

        # 상세 결과
        report.append("\n### 상세 OCR 결과\n")

        for r in self.results:
            report.append(f"\n#### {r['image']}\n")
            report.append(f"- 이미지 크기: {r['image_size']}\n")

            report.append("\n**Surya OCR 결과:**\n")
            report.append("```")
            surya_text = r['surya'].get('text', '')[:800]
            report.append(surya_text if surya_text else "(텍스트 없음)")
            report.append("```\n")

            report.append("**Tesseract OCR 결과:**\n")
            report.append("```")
            tess_text = r['tesseract'].get('text', '')[:800]
            report.append(tess_text if tess_text else "(텍스트 없음)")
            report.append("```\n")

        # 결론
        report.append("\n### 결론\n")
        if n > 0:
            avg_surya_conf = total_surya_conf / n
            avg_tess_conf = total_tess_conf / n
            avg_surya_time = total_surya_time / n
            avg_tess_time = total_tess_time / n

            report.append(f"| 항목 | Surya OCR | Tesseract OCR |")
            report.append(f"|------|-----------|---------------|")
            report.append(f"| 평균 신뢰도 | {avg_surya_conf:.1f}% | {avg_tess_conf:.1f}% |")
            report.append(f"| 평균 처리 시간 | {avg_surya_time:.2f}초 | {avg_tess_time:.2f}초 |")
            report.append(f"| 디바이스 | {self.device if SURYA_AVAILABLE else 'N/A'} | CPU |")

            if avg_surya_conf > avg_tess_conf:
                report.append(f"\n**Surya OCR**이 평균 신뢰도에서 **{avg_surya_conf - avg_tess_conf:.1f}%p** 더 높은 성능을 보였습니다.")
            else:
                report.append(f"\n**Tesseract OCR**이 평균 신뢰도에서 **{avg_tess_conf - avg_surya_conf:.1f}%p** 더 높은 성능을 보였습니다.")

        return '\n'.join(report)


def main():
    """메인 함수"""
    comparison = OCRComparison()
    comparison.run_comparison()

    # 마크다운 리포트 저장
    report = comparison.get_markdown_report()
    report_path = project_root / "docs" / "test" / "criminal_ocr_test" / "OCR_COMPARISON_RESULT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n리포트 저장: {report_path}")


if __name__ == "__main__":
    main()
