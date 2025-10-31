"""
Tesseract OCR 기능 테스트
"""

import pytesseract
from PIL import Image, ImageDraw, ImageFont
import os


def test_tesseract_korean():
    """한글 OCR 테스트"""
    print("=" * 60)
    print("Tesseract 한글 OCR 테스트")
    print("=" * 60)

    # 1. 테스트 이미지 생성
    print("\n[1] 테스트 이미지 생성...")
    img = Image.new('RGB', (600, 150), color='white')
    d = ImageDraw.Draw(img)

    # 텍스트 그리기 (간단한 폰트 사용)
    test_text = "Hello World\n안녕하세요 대한민국\n형법 제1조"
    d.text((20, 20), test_text, fill='black')

    # 이미지 저장
    test_image_path = 'test_korean_ocr.png'
    img.save(test_image_path)
    print(f"   테스트 이미지 저장됨: {test_image_path}")

    # 2. OCR 실행
    print("\n[2] OCR 실행 중...")
    print("   언어: 한국어 + 영어 (kor+eng)")

    try:
        # 한글 + 영어 OCR
        extracted_text = pytesseract.image_to_string(img, lang='kor+eng')

        print("\n[3] OCR 결과:")
        print("-" * 60)
        print(f"원본 텍스트:\n{test_text}")
        print("-" * 60)
        print(f"추출된 텍스트:\n{extracted_text}")
        print("-" * 60)

        # 4. OCR 상세 정보 (confidence 포함)
        print("\n[4] OCR 상세 정보:")
        data = pytesseract.image_to_data(img, lang='kor+eng', output_type=pytesseract.Output.DICT)

        avg_confidence = sum([float(c) for c in data['conf'] if c != '-1']) / len([c for c in data['conf'] if c != '-1'])
        print(f"   평균 신뢰도: {avg_confidence:.2f}%")
        print(f"   감지된 단어 수: {len([w for w in data['text'] if w.strip()])}")

        # 5. 성공 여부 확인
        print("\n[5] 테스트 결과:")
        if extracted_text.strip():
            print("   ✅ 성공: 텍스트 추출 완료")
            return True
        else:
            print("   ❌ 실패: 텍스트가 추출되지 않았습니다")
            return False

    except Exception as e:
        print(f"\n   ❌ 오류 발생: {str(e)}")
        return False
    finally:
        # 테스트 이미지 삭제
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
            print(f"\n[6] 정리: 테스트 이미지 삭제됨")


def test_tesseract_info():
    """Tesseract 정보 확인"""
    print("\n" + "=" * 60)
    print("Tesseract 시스템 정보")
    print("=" * 60)

    # 버전
    version = pytesseract.get_tesseract_version()
    print(f"\n버전: {version}")

    # 설치된 언어
    languages = pytesseract.get_languages()
    korean_langs = [lang for lang in languages if 'kor' in lang.lower()]

    print(f"\n설치된 전체 언어 수: {len(languages)}")
    print(f"한국어 언어팩: {korean_langs}")

    # Tesseract 실행 파일 경로
    tesseract_cmd = pytesseract.pytesseract.tesseract_cmd
    print(f"\nTesseract 경로: {tesseract_cmd}")


if __name__ == "__main__":
    # Tesseract 정보 출력
    test_tesseract_info()

    # 한글 OCR 테스트
    print("\n")
    success = test_tesseract_korean()

    # 최종 결과
    print("\n" + "=" * 60)
    print("최종 결과")
    print("=" * 60)
    if success:
        print("✅ Tesseract OCR 설치 및 테스트 완료")
        print("   - 한글 언어팩 설치됨")
        print("   - OCR 기능 정상 작동")
    else:
        print("❌ Tesseract OCR 테스트 실패")
    print("=" * 60)
