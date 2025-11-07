"""
PDF OCR 파이프라인 FastAPI 서버
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
import logging

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ocr import (
    PDFTextExtractor,
    extract_pdf_with_preprocessing,
    apply_ocr_postprocessing,
    DocumentStructurer
)


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="PDF OCR Pipeline API",
    description="이미지화된 PDF 문서 텍스트 추출 및 구조화 API",
    version="2.0.0"
)

# CORS 설정 (프론트엔드에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영시에는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 응답 모델
class ProcessResponse(BaseModel):
    """PDF 처리 결과 응답 모델"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    timestamp: str
    version: str


@app.get("/", response_model=HealthResponse)
async def root():
    """루트 엔드포인트"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="2.0.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스체크 엔드포인트"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="2.0.0"
    )


@app.post("/api/v1/process-pdf", response_model=ProcessResponse)
async def process_pdf(
    file: UploadFile = File(...),
    adaptive: bool = True,
    apply_postprocessing: bool = True
):
    """
    PDF 파일 처리 엔드포인트

    Args:
        file: 업로드된 PDF 파일
        adaptive: 적응형 전처리 활성화 여부 (기본: True)
        apply_postprocessing: OCR 후처리 적용 여부 (기본: True)

    Returns:
        ProcessResponse: 처리 결과
    """
    # 임시 파일 생성
    temp_file = None

    try:
        # 파일 확장자 검증
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="PDF 파일만 업로드 가능합니다."
            )

        logger.info(f"파일 수신: {file.filename}")

        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp:
            temp_file = Path(temp.name)
            shutil.copyfileobj(file.file, temp)

        logger.info(f"임시 파일 저장: {temp_file}")

        # [1단계] PyMuPDF 텍스트 추출 시도
        logger.info("[1단계] PyMuPDF 텍스트 추출 시도...")
        pymupdf_result = PDFTextExtractor.extract_text_with_pymupdf(temp_file)
        is_extractable = PDFTextExtractor.is_text_extractable(pymupdf_result)

        if is_extractable:
            # PyMuPDF 텍스트 사용 가능
            logger.info("  ✅ PyMuPDF로 텍스트 추출 가능")

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
            logger.info("[2단계] OCR 텍스트 추출 (개선된 적응형 전처리)...")

            # V2: 개선된 품질 평가 및 선택적 전처리
            ocr_result = extract_pdf_with_preprocessing(
                temp_file,
                dpi=300,
                preset='standard',
                adaptive=adaptive
            )

            # OCR 텍스트 병합
            full_text = '\n'.join([page['text'] for page in ocr_result['pages']])

            logger.info(f"  ✅ OCR 완료 (신뢰도: {ocr_result['avg_confidence']:.1f}%)")

            # OCR 후처리 적용
            if apply_postprocessing:
                logger.info("[2.5단계] OCR 후처리 (오인식 단어 교정)...")
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

        # [3단계] 문서 타입별 구조화
        logger.info("[3단계] 문서 타입별 구조화...")
        structurer = DocumentStructurer(full_text, file.filename)
        structured_data = structurer.structure()

        # 메타데이터 추가
        structured_data['추출방법'] = extraction_method
        structured_data['추출메타데이터'] = metadata
        structured_data['처리시각'] = datetime.now().isoformat()
        structured_data['원본파일명'] = file.filename

        logger.info(f"✅ 파이프라인 완료: {structured_data.get('데이터타입', 'Unknown')}")

        return ProcessResponse(
            success=True,
            message="PDF 처리가 성공적으로 완료되었습니다.",
            data=structured_data
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"처리 실패: {str(e)}")
        import traceback
        traceback.print_exc()

        return ProcessResponse(
            success=False,
            message="PDF 처리 중 오류가 발생했습니다.",
            error=str(e)
        )

    finally:
        # 임시 파일 정리
        if temp_file and temp_file.exists():
            temp_file.unlink()
            logger.info(f"임시 파일 삭제: {temp_file}")


@app.post("/api/v1/process-pdf-batch")
async def process_pdf_batch(
    files: list[UploadFile] = File(...),
    adaptive: bool = True,
    apply_postprocessing: bool = True
):
    """
    여러 PDF 파일 일괄 처리 엔드포인트

    Args:
        files: 업로드된 PDF 파일 목록
        adaptive: 적응형 전처리 활성화 여부
        apply_postprocessing: OCR 후처리 적용 여부

    Returns:
        dict: 처리 결과 목록
    """
    results = []

    for file in files:
        try:
            result = await process_pdf(file, adaptive, apply_postprocessing)
            results.append({
                "filename": file.filename,
                "success": result.success,
                "data": result.data,
                "error": result.error
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    return {
        "total": len(files),
        "success_count": sum(1 for r in results if r["success"]),
        "results": results
    }


@app.get("/api/v1/stats")
async def get_stats():
    """
    API 통계 엔드포인트 (향후 확장용)
    """
    return {
        "status": "operational",
        "version": "2.0.0",
        "features": [
            "PyMuPDF 우선 추출",
            "적응형 OCR 전처리",
            "선택적 이미지 전처리",
            "OCR 후처리 교정",
            "문서 타입별 구조화"
        ],
        "supported_document_types": [
            "판결문",
            "소장",
            "내용증명",
            "합의서",
            "기타"
        ]
    }


if __name__ == "__main__":
    import uvicorn

    # 개발 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
