"""
PDF 처리 파이프라인
PyMuPDF 텍스트 추출 우선 → OCR 전환 (품질 기반 전처리 포함)
"""

import json
from pathlib import Path
from datetime import datetime
import logging
import fitz  # PyMuPDF
import unicodedata
import re

# 삭제된 import (pdf_extractor는 독립적으로 동작)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """PDF 텍스트 추출 가능 여부 판단"""

    @staticmethod
    def extract_text_with_pymupdf(pdf_path: Path) -> dict:
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
        logger.info(f"  [1단계] PyMuPDF 텍스트 추출 시도...")

        try:
            doc = fitz.open(pdf_path)
            pages_text = []
            total_chars = 0

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                # Unicode 정규화
                text = unicodedata.normalize('NFC', text)

                pages_text.append(text)
                total_chars += len(text.strip())

            doc.close()

            # 전체 텍스트 병합
            full_text = '\n'.join(pages_text)

            # 추출률 계산
            extraction_rate = total_chars / len(pages_text) if pages_text else 0

            result = {
                'success': True,
                'text': full_text,
                'page_count': len(pages_text),
                'char_count': total_chars,
                'extraction_rate': extraction_rate
            }

            logger.info(f"    PyMuPDF 추출 완료: {total_chars}자 ({len(pages_text)}페이지)")
            logger.info(f"    페이지당 평균: {extraction_rate:.1f}자")

            return result

        except Exception as e:
            logger.error(f"    PyMuPDF 추출 실패: {e}")
            return {
                'success': False,
                'text': '',
                'page_count': 0,
                'char_count': 0,
                'extraction_rate': 0,
                'error': str(e)
            }

    @staticmethod
    def is_text_extractable(extraction_result: dict, min_chars_per_page: int = 100) -> bool:
        """
        텍스트 추출 가능 여부 판단

        Args:
            extraction_result: extract_text_with_pymupdf() 결과
            min_chars_per_page: 페이지당 최소 글자 수 (기본 100자)

        Returns:
            bool: True이면 PyMuPDF 텍스트 사용 가능, False이면 OCR 필요
        """
        if not extraction_result['success']:
            logger.info(f"    판단: OCR 필요 (추출 실패)")
            return False

        # 최소 글자 수 확인
        if extraction_result['char_count'] < 50:
            logger.info(f"    판단: OCR 필요 (총 글자 수 부족: {extraction_result['char_count']}자)")
            return False

        # 페이지당 평균 글자 수 확인
        if extraction_result['extraction_rate'] < min_chars_per_page:
            logger.info(f"    판단: OCR 필요 (페이지당 평균 부족: {extraction_result['extraction_rate']:.1f}자)")
            return False

        # 의미 있는 텍스트 확인 (한글/영어 비율)
        text = extraction_result['text']
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_meaningful = korean_chars + english_chars

        meaningful_ratio = total_meaningful / extraction_result['char_count'] if extraction_result['char_count'] > 0 else 0

        if meaningful_ratio < 0.3:  # 의미 있는 글자가 30% 미만
            logger.info(f"    판단: OCR 필요 (의미 있는 텍스트 부족: {meaningful_ratio:.1%})")
            return False

        logger.info(f"    판단: PyMuPDF 텍스트 사용 가능 ✓")
        logger.info(f"      - 총 글자: {extraction_result['char_count']}자")
        logger.info(f"      - 페이지당 평균: {extraction_result['extraction_rate']:.1f}자")
        logger.info(f"      - 의미 있는 텍스트: {meaningful_ratio:.1%}")
        return True


class PDFProcessingPipeline:
    """PDF 처리 통합 파이프라인"""

    def __init__(self, search_keyword: str = "교통사고"):
        self.search_keyword = search_keyword

    def process_pdf(self, pdf_path: Path) -> dict:
        """
        PDF 파일 전체 처리 파이프라인

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            dict: 구조화된 데이터
        """
        logger.info("="*70)
        logger.info(f"PDF 처리 파이프라인 시작: {pdf_path.name}")
        logger.info("="*70)

        # [1단계] PyMuPDF 텍스트 추출 시도
        pymupdf_result = PDFTextExtractor.extract_text_with_pymupdf(pdf_path)
        is_extractable = PDFTextExtractor.is_text_extractable(pymupdf_result)

        if is_extractable:
            # PyMuPDF 텍스트 사용 가능 → 바로 구조화
            logger.info("  [경로] PyMuPDF 텍스트 → 구조화")

            extraction_method = 'pymupdf'
            full_text = pymupdf_result['text']
            metadata = {
                'extraction_method': extraction_method,
                'char_count': pymupdf_result['char_count'],
                'page_count': pymupdf_result['page_count'],
                'extraction_rate': pymupdf_result['extraction_rate']
            }

        else:
            # OCR 필요
            logger.info("  [경로] OCR 추출 (품질 평가 → 전처리 → OCR)")

            # [2단계] 품질 기반 OCR 추출 (adaptive 모드)
            logger.info(f"  [2단계] OCR 텍스트 추출 (적응형 전처리)...")

            ocr_result = extract_pdf_with_preprocessing(
                pdf_path,
                dpi=300,
                preset='standard',
                adaptive=True  # 품질 기반 자동 전처리 선택
            )

            # OCR 텍스트 병합
            full_text = '\n'.join([page['text'] for page in ocr_result['pages']])

            extraction_method = 'ocr'
            metadata = {
                'extraction_method': extraction_method,
                'char_count': ocr_result['total_chars'],
                'page_count': ocr_result['page_count'],
                'avg_confidence': ocr_result['avg_confidence'],
                'preprocessing': ocr_result['preprocessing'],
                'preset_usage': ocr_result.get('preset_usage', {})
            }

        # [3단계] 텍스트 파싱
        logger.info(f"  [3단계] 텍스트 파싱...")
        parser = OCRTextParser(full_text, pdf_path.name)
        parsed_data = parser.parse()

        # [4단계] 데이터 구조화
        logger.info(f"  [4단계] 데이터 구조화...")
        structurer = OCRDataStructurer(parsed_data, self.search_keyword)
        structured_data = structurer.structure()

        # 메타데이터 추가
        structured_data['추출방법'] = extraction_method
        structured_data['추출메타데이터'] = metadata
        structured_data['처리시각'] = datetime.now().isoformat()

        logger.info("="*70)
        logger.info(f"✅ 파이프라인 완료")
        logger.info(f"  추출 방법: {extraction_method.upper()}")
        logger.info(f"  글자 수: {metadata['char_count']}자")
        logger.info(f"  사건번호: {structured_data.get('사건번호', 'N/A')}")
        logger.info(f"  법원명: {structured_data.get('법원명', 'N/A')}")
        logger.info("="*70)

        return structured_data


def main():
    """메인 실행"""
    # PDF 디렉토리
    pdf_dir = Path("raw_pdf_data")

    if not pdf_dir.exists():
        logger.error(f"디렉토리를 찾을 수 없습니다: {pdf_dir}")
        return

    # PDF 파일 찾기 (converted 파일 우선)
    pdf_files = []
    for pdf_file in pdf_dir.glob("*.pdf"):
        normalized_name = unicodedata.normalize('NFC', pdf_file.name)
        if '변환' in normalized_name or 'converted' in normalized_name:
            pdf_files.append(pdf_file)

    if not pdf_files:
        # converted 없으면 모든 PDF
        pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        logger.error("PDF 파일을 찾을 수 없습니다.")
        return

    logger.info("="*70)
    logger.info("PDF 처리 파이프라인")
    logger.info("="*70)
    logger.info(f"총 {len(pdf_files)}개 파일")
    logger.info("")

    # 출력 디렉토리
    output_dir = Path("pipeline_output")
    output_dir.mkdir(exist_ok=True)

    # 파이프라인 초기화
    pipeline = PDFProcessingPipeline(search_keyword="교통사고")

    # 모든 파일 처리
    all_results = []

    for idx, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"\n[{idx}/{len(pdf_files)}] {pdf_file.name}")

        try:
            result = pipeline.process_pdf(pdf_file)
            all_results.append(result)

        except Exception as e:
            logger.error(f"처리 실패: {pdf_file.name} - {e}")
            import traceback
            traceback.print_exc()
            continue

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 통합 JSON 저장
    output_file = output_dir / f"pipeline_result_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "검색어": "교통사고",
            "데이터타입": "판례",
            "처리시각": datetime.now().isoformat(),
            "총건수": len(all_results),
            "케이스": all_results
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ 통합 결과 저장: {output_file}")

    # 개별 파일 저장
    for result in all_results:
        case_id = result.get("판례일련번호", "unknown")
        individual_file = output_dir / f"case_{case_id}.json"

        with open(individual_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 개별 파일 저장: {individual_file}")

    # 요약 통계
    logger.info("\n" + "="*70)
    logger.info("📊 파이프라인 요약")
    logger.info("="*70)
    logger.info(f"총 처리: {len(all_results)}건")

    # 추출 방법별 통계
    extraction_methods = {}
    for result in all_results:
        method = result.get('추출방법', 'unknown')
        extraction_methods[method] = extraction_methods.get(method, 0) + 1

    logger.info(f"\n추출 방법별 분포:")
    for method, count in extraction_methods.items():
        logger.info(f"  {method.upper()}: {count}건")

    # 사건종류별 통계
    case_types = {}
    for result in all_results:
        case_type = result.get('사건종류명', 'Unknown')
        case_types[case_type] = case_types.get(case_type, 0) + 1

    logger.info(f"\n사건종류별 분포:")
    for case_type, count in case_types.items():
        logger.info(f"  {case_type}: {count}건")

    logger.info("="*70)


if __name__ == "__main__":
    main()
