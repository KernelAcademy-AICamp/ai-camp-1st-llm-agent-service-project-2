"""
OCR 서비스 통합 테스트
실제 프로젝트의 OCR 엔진을 테스트합니다.
"""

import os
os.environ['OCR_ENGINE'] = 'tesseract'  # Tesseract 강제 사용

from app.services.ocr_engine_selector import OCREngineSelector
from app.services.ocr_engines import TesseractOCREngine
from PIL import Image, ImageDraw


def test_engine_selection():
    """OCR 엔진 선택 테스트"""
    print("=" * 60)
    print("OCR 엔진 선택 테스트")
    print("=" * 60)

    # 자동 선택
    os.environ['OCR_ENGINE'] = 'auto'
    engine = OCREngineSelector.select_engine()
    config = OCREngineSelector.get_engine_config(engine)

    print(f"\n[자동 선택 모드]")
    print(f"선택된 엔진: {engine}")
    print(f"설정: {config}")

    # Tesseract 강제 선택
    os.environ['OCR_ENGINE'] = 'tesseract'
    engine = OCREngineSelector.select_engine()
    config = OCREngineSelector.get_engine_config(engine)

    print(f"\n[Tesseract 강제 모드]")
    print(f"선택된 엔진: {engine}")
    print(f"설정: {config}")


def test_tesseract_engine():
    """Tesseract 엔진 직접 테스트"""
    print("\n" + "=" * 60)
    print("Tesseract 엔진 직접 테스트")
    print("=" * 60)

    try:
        # 엔진 초기화
        print("\n[1] Tesseract 엔진 초기화...")
        config = OCREngineSelector.get_engine_config('tesseract')
        engine = TesseractOCREngine(config)
        print("   ✅ 엔진 초기화 완료")
        print(f"   설정: {config}")

        # 테스트 이미지 생성
        print("\n[2] 테스트 이미지 생성...")
        img = Image.new('RGB', (400, 100), color='white')
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Test Image\n테스트 이미지", fill='black')
        print("   ✅ 이미지 생성 완료")

        # OCR 실행
        print("\n[3] OCR 실행...")
        text, confidence = engine.extract_text(img)

        print(f"\n[4] 결과:")
        print(f"   추출된 텍스트: {repr(text)}")
        print(f"   신뢰도: {confidence:.2f}%")

        if text.strip():
            print("\n   ✅ 성공: 텍스트 추출 완료")
            return True
        else:
            print("\n   ⚠️  경고: 텍스트가 비어있습니다")
            return False

    except Exception as e:
        print(f"\n   ❌ 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_hardware_info():
    """하드웨어 정보 확인"""
    print("\n" + "=" * 60)
    print("하드웨어 정보")
    print("=" * 60)

    from app.core.hardware_detector import get_hardware_info
    hw = get_hardware_info()

    print(f"\n디바이스 타입: {hw.device_type.value}")
    print(f"디바이스 수: {hw.device_count}")
    print(f"디바이스 이름: {hw.device_name}")
    if hw.total_memory:
        print(f"총 메모리: {hw.total_memory} MB")
    print(f"플랫폼: {hw.platform}")
    if hw.cuda_version:
        print(f"CUDA 버전: {hw.cuda_version}")


if __name__ == "__main__":
    # 하드웨어 정보
    test_hardware_info()

    # 엔진 선택 테스트
    print("\n")
    test_engine_selection()

    # Tesseract 엔진 테스트
    print("\n")
    success = test_tesseract_engine()

    # 최종 결과
    print("\n" + "=" * 60)
    print("최종 테스트 결과")
    print("=" * 60)
    if success:
        print("✅ 모든 테스트 통과")
        print("   - 하드웨어 감지 완료")
        print("   - OCR 엔진 선택 완료")
        print("   - Tesseract OCR 작동 확인")
    else:
        print("⚠️  일부 테스트 실패")
    print("=" * 60)
