"""
이미지화된 PDF 파일 처리 V2 (개선된 품질 평가 + 선택적 전처리)
"""

import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ocr.pdf_extractor import PDFTextExtractor
from core.ocr.document_structurer import DocumentStructurer
from core.ocr.ocr_processor import extract_pdf_with_preprocessing
from core.ocr.postprocessor import apply_ocr_postprocessing
import json
from datetime import datetime
import logging
import fitz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """이미지화된 PDF 디렉토리 처리 (V2 - 개선된 품질 평가)"""
    # imaged_PDF 디렉토리
    test_dir = Path("/Users/nw_mac/Documents/Github_crawling/ai-camp-1st-llm-agent-service-project-2/OCR_test/imaged_PDF")

    if not test_dir.exists():
        logger.error(f"디렉토리를 찾을 수 없습니다: {test_dir}")
        return

    # PDF 파일 찾기
    pdf_files = sorted(list(test_dir.glob("*.pdf")))

    if not pdf_files:
        logger.error("PDF 파일을 찾을 수 없습니다.")
        return

    logger.info("="*70)
    logger.info("이미지화된 PDF 처리 파이프라인 V2 (개선된 품질 평가 + 선택적 전처리)")
    logger.info("="*70)
    logger.info(f"총 {len(pdf_files)}개 파일")
    logger.info(f"디렉토리: {test_dir}")
    logger.info("")

    # 출력 디렉토리
    output_dir = Path("imaged_pdf_output_v2")
    output_dir.mkdir(exist_ok=True)

    # 모든 파일 처리
    all_results = []
    processing_stats = {
        'pymupdf': 0,
        'ocr': 0,
        'failed': 0
    }

    for idx, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"\n[{idx}/{len(pdf_files)}] {pdf_file.name}")
        logger.info("="*70)

        try:
            # [1단계] PyMuPDF 텍스트 추출 시도
            pymupdf_result = PDFTextExtractor.extract_text_with_pymupdf(pdf_file)
            is_extractable = PDFTextExtractor.is_text_extractable(pymupdf_result)

            if is_extractable:
                # PyMuPDF 텍스트 사용 가능
                logger.info("  [경로] PyMuPDF 텍스트 → 문서 타입별 구조화")

                extraction_method = 'pymupdf'
                full_text = pymupdf_result['text']
                metadata = {
                    'extraction_method': extraction_method,
                    'char_count': pymupdf_result['char_count'],
                    'page_count': pymupdf_result['page_count'],
                    'extraction_rate': pymupdf_result['extraction_rate']
                }

                processing_stats['pymupdf'] += 1

            else:
                # OCR 필요
                logger.info("  [경로] 품질 평가 → 선택적 전처리 → OCR → 후처리")
                logger.info(f"  [2단계] OCR 텍스트 추출 (개선된 적응형 전처리)...")

                # V2: 개선된 품질 평가 및 선택적 전처리
                ocr_result = extract_pdf_with_preprocessing(
                    pdf_file,
                    dpi=300,
                    preset='standard',  # 기본값 (adaptive=True이면 무시됨)
                    adaptive=True       # 적응형 모드 활성화
                )

                # OCR 텍스트 병합
                full_text = '\n'.join([page['text'] for page in ocr_result['pages']])

                # OCR 후처리 적용
                logger.info(f"  [2.5단계] OCR 후처리 (오인식 단어 교정)...")
                full_text = apply_ocr_postprocessing(full_text, verbose=False)

                extraction_method = 'ocr_v2'
                metadata = {
                    'extraction_method': extraction_method,
                    'char_count': ocr_result['total_chars'],
                    'page_count': ocr_result['page_count'],
                    'avg_confidence': ocr_result['avg_confidence'],
                    'preprocessing': 'adaptive_selective',
                    'preset_usage': ocr_result.get('preset_usage', {}),
                    'quality_info': 'improved_weighted_scoring'
                }

                processing_stats['ocr'] += 1

            # [3단계] 문서 타입별 구조화
            logger.info(f"  [3단계] 문서 타입별 구조화...")
            structurer = DocumentStructurer(full_text, pdf_file.name)
            structured_data = structurer.structure()

            # 메타데이터 추가
            structured_data['추출방법'] = extraction_method
            structured_data['추출메타데이터'] = metadata
            structured_data['처리시각'] = datetime.now().isoformat()

            logger.info("="*70)
            logger.info(f"✅ 파이프라인 완료")
            logger.info(f"  문서 타입: {structured_data.get('데이터타입', 'Unknown')}")
            logger.info(f"  추출 방법: {extraction_method.upper()}")
            logger.info(f"  글자 수: {metadata['char_count']}자")
            if extraction_method.startswith('ocr'):
                logger.info(f"  OCR 신뢰도: {metadata['avg_confidence']:.1f}%")
                logger.info(f"  전처리: {metadata.get('preprocessing', 'N/A')}")
            logger.info("="*70)

            all_results.append(structured_data)

        except Exception as e:
            logger.error(f"처리 실패: {pdf_file.name} - {e}")
            processing_stats['failed'] += 1
            import traceback
            traceback.print_exc()
            continue

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 통합 JSON 저장
    output_file = output_dir / f"imaged_pdf_result_v2_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "처리시각": datetime.now().isoformat(),
            "총건수": len(all_results),
            "버전": "V2 - 개선된 품질 평가 + 선택적 전처리",
            "문서타입별": {},
            "케이스": all_results
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ 통합 결과 저장: {output_file}")

    # 개별 파일 저장
    for result in all_results:
        doc_type = result.get("데이터타입", "unknown")
        filename = result.get("파일명", "unknown")

        # 파일명에서 .pdf 제거
        base_name = filename.replace('.pdf', '').replace('_converted', '')
        individual_file = output_dir / f"{doc_type}_{base_name}.json"

        with open(individual_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 개별 파일 저장: {individual_file}")

    # 요약 통계
    logger.info("\n" + "="*70)
    logger.info("📊 처리 요약")
    logger.info("="*70)
    logger.info(f"총 처리: {len(all_results)}건")
    logger.info(f"실패: {processing_stats['failed']}건")

    # 문서 타입별 통계
    doc_types = {}
    for result in all_results:
        doc_type = result.get('데이터타입', 'Unknown')
        doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

    logger.info(f"\n문서 타입별 분포:")
    for doc_type, count in doc_types.items():
        logger.info(f"  {doc_type}: {count}건")

    # 추출 방법별 통계
    logger.info(f"\n추출 방법별 분포:")
    logger.info(f"  PYMUPDF: {processing_stats['pymupdf']}건")
    logger.info(f"  OCR V2 (개선): {processing_stats['ocr']}건")

    # OCR 신뢰도 통계
    ocr_confidences = []
    quality_scores = []

    for result in all_results:
        if result.get('추출방법', '').startswith('ocr'):
            metadata = result.get('추출메타데이터', {})
            confidence = metadata.get('avg_confidence', 0)
            ocr_confidences.append(confidence)

            # 품질 정보
            logger.info(f"\n  📄 {result.get('파일명', 'Unknown')}")
            logger.info(f"     신뢰도: {confidence:.1f}%")
            logger.info(f"     전처리: {metadata.get('preprocessing', 'N/A')}")
            logger.info(f"     글자 수: {metadata.get('char_count', 0)}자")
            preset_usage = metadata.get('preset_usage', {})
            if preset_usage:
                logger.info(f"     전처리 전략 사용:")
                for preset, count in preset_usage.items():
                    logger.info(f"       - {preset}: {count}페이지")

    if ocr_confidences:
        avg_confidence = sum(ocr_confidences) / len(ocr_confidences)
        logger.info(f"\nOCR 평균 신뢰도: {avg_confidence:.1f}%")
        logger.info(f"OCR 최소 신뢰도: {min(ocr_confidences):.1f}%")
        logger.info(f"OCR 최대 신뢰도: {max(ocr_confidences):.1f}%")

    logger.info("="*70)

    return all_results, output_file


if __name__ == "__main__":
    main()
