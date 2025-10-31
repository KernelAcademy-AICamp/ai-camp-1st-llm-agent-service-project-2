"""
Hardware Detection Test Script
하드웨어 감지 및 OCR 엔진 선택 테스트
"""

import sys
import os

# 현재 디렉토리를 Python path에 추가
sys.path.insert(0, os.path.dirname(__file__))

def test_hardware_detection():
    """하드웨어 감지 테스트"""
    print("=" * 70)
    print("Testing Hardware Detection")
    print("=" * 70)

    try:
        from app.core.hardware_detector import print_hardware_info, get_hardware_info

        # 하드웨어 정보 출력
        print_hardware_info()

        # 하드웨어 정보 조회
        hw = get_hardware_info()

        print(f"\nDevice Type: {hw.device_type.value}")
        print(f"Device Count: {hw.device_count}")
        print(f"Device Name: {hw.device_name}")

        if hw.total_memory:
            print(f"Total Memory: {hw.total_memory} MB")

        if hw.cuda_version:
            print(f"CUDA Version: {hw.cuda_version}")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


def test_ocr_engine_selection():
    """OCR 엔진 선택 테스트"""
    print("\n" + "=" * 70)
    print("Testing OCR Engine Selection")
    print("=" * 70)

    try:
        from app.services.ocr_engine_selector import OCREngineSelector

        # 엔진 선택
        engine_name = OCREngineSelector.select_engine()
        engine_config = OCREngineSelector.get_engine_config(engine_name)

        print(f"\nSelected Engine: {engine_name.upper()}")
        print(f"Configuration:")
        for key, value in engine_config.items():
            print(f"  {key}: {value}")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("\n🚀 Starting Hardware & OCR Engine Tests\n")

    # 테스트 실행
    hw_test = test_hardware_detection()
    ocr_test = test_ocr_engine_selection()

    # 결과 요약
    print("\n" + "=" * 70)
    print("Test Results")
    print("=" * 70)
    print(f"Hardware Detection: {'✅ PASS' if hw_test else '❌ FAIL'}")
    print(f"OCR Engine Selection: {'✅ PASS' if ocr_test else '❌ FAIL'}")
    print("=" * 70)

    # 종료 코드
    sys.exit(0 if (hw_test and ocr_test) else 1)
