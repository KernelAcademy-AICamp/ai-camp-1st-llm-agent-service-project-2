"""
단일 PDF 파일 테스트 스크립트
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_single_pdf(pdf_path):
    """단일 PDF 파일 테스트"""
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        logger.error(f"파일을 찾을 수 없습니다: {pdf_file}")
        return None

    logger.info("=" * 70)
    logger.info(f"PDF 파일 테스트: {pdf_file.name}")
    logger.info("=" * 70)

    try:
        # [1단계] PyMuPDF 텍스트 추출 시도
        logger.info("[1단계] PyMuPDF 텍스트 추출 시도...")
        pymupdf_result = PDFTextExtractor.extract_text_with_pymupdf(pdf_file)
        is_extractable = PDFTextExtractor.is_text_extractable(pymupdf_result)

        if is_extractable:
            # PyMuPDF 텍스트 사용 가능
            logger.info("  ✅ PyMuPDF로 텍스트 추출 가능")
            logger.info(f"  - 페이지 수: {pymupdf_result['page_count']}")
            logger.info(f"  - 글자 수: {pymupdf_result['char_count']}자")
            logger.info(f"  - 추출률: {pymupdf_result['extraction_rate']:.1f}%")

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
            logger.info("  ℹ️  PyMuPDF 추출 불가 → OCR 필요")
            logger.info(f"\n[2단계] OCR 텍스트 추출 (개선된 적응형 전처리)...")

            # V2: 개선된 품질 평가 및 선택적 전처리
            ocr_result = extract_pdf_with_preprocessing(
                pdf_file,
                dpi=300,
                preset='standard',
                adaptive=True
            )

            # OCR 텍스트 병합
            full_text = '\n'.join([page['text'] for page in ocr_result['pages']])

            logger.info(f"  ✅ OCR 완료")
            logger.info(f"  - 페이지 수: {ocr_result['page_count']}")
            logger.info(f"  - 글자 수: {ocr_result['total_chars']}자")
            logger.info(f"  - 평균 신뢰도: {ocr_result['avg_confidence']:.1f}%")

            # 페이지별 상세 정보
            logger.info(f"\n  📄 페이지별 상세:")
            for i, page in enumerate(ocr_result['pages'], 1):
                logger.info(f"    Page {i}:")
                logger.info(f"      - 글자 수: {len(page['text'])}자")
                logger.info(f"      - 신뢰도: {page['confidence']:.1f}%")
                logger.info(f"      - 품질 점수: {page.get('quality_score', 'N/A')}")
                logger.info(f"      - 전처리: {page.get('preset_used', 'N/A')}")

            # OCR 후처리 적용
            logger.info(f"\n[2.5단계] OCR 후처리 (오인식 단어 교정)...")
            full_text_before = full_text
            full_text = apply_ocr_postprocessing(full_text, verbose=True)

            extraction_method = 'ocr_v2'
            metadata = {
                'extraction_method': extraction_method,
                'char_count': ocr_result['total_chars'],
                'page_count': ocr_result['page_count'],
                'avg_confidence': ocr_result['avg_confidence'],
                'preprocessing': 'adaptive_selective',
                'preset_usage': ocr_result.get('preset_usage', {}),
                'quality_info': 'improved_weighted_scoring',
                'page_details': [
                    {
                        'page': i,
                        'chars': len(p['text']),
                        'confidence': p['confidence'],
                        'quality_score': p.get('quality_score', 'N/A'),
                        'preset': p.get('preset_used', 'N/A')
                    }
                    for i, p in enumerate(ocr_result['pages'], 1)
                ]
            }

        # [3단계] 문서 타입별 구조화
        logger.info(f"\n[3단계] 문서 타입별 구조화...")
        structurer = DocumentStructurer(full_text, pdf_file.name)
        structured_data = structurer.structure()

        # 메타데이터 추가
        structured_data['추출방법'] = extraction_method
        structured_data['추출메타데이터'] = metadata
        structured_data['처리시각'] = datetime.now().isoformat()

        logger.info("=" * 70)
        logger.info(f"✅ 파이프라인 완료")
        logger.info(f"  문서 타입: {structured_data.get('데이터타입', 'Unknown')}")
        logger.info(f"  추출 방법: {extraction_method.upper()}")
        logger.info(f"  글자 수: {metadata['char_count']}자")

        if extraction_method.startswith('ocr'):
            logger.info(f"  OCR 신뢰도: {metadata['avg_confidence']:.1f}%")
            logger.info(f"  전처리: {metadata.get('preprocessing', 'N/A')}")

        # 구조화된 데이터 필드 확인
        logger.info(f"\n📋 추출된 필드:")
        for key, value in structured_data.items():
            if key not in ['추출방법', '추출메타데이터', '처리시각', '파일명']:
                if isinstance(value, str):
                    preview = value[:100] + "..." if len(value) > 100 else value
                    logger.info(f"  - {key}: {len(value) if len(value) > 50 else preview}자")
                else:
                    logger.info(f"  - {key}: {value}")

        logger.info("=" * 70)

        return structured_data

    except Exception as e:
        logger.error(f"처리 실패: {pdf_file.name} - {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python test_single_pdf.py <PDF_파일_경로>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    result = test_single_pdf(pdf_path)

    if result:
        # 결과 저장
        output_dir = Path("test_results")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_type = result.get("데이터타입", "unknown")
        filename = Path(pdf_path).stem

        output_file = output_dir / f"{doc_type}_{filename}_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 결과 저장: {output_file}")
