# Tesseract OCR 설치 가이드 (macOS)

## 1. Homebrew로 Tesseract 설치

### 기본 설치
```bash
# Tesseract OCR 설치
brew install tesseract

# 한글 언어팩 설치
brew install tesseract-lang

# PDF 처리를 위한 Poppler 설치
brew install poppler
```

### 설치 확인
```bash
# Tesseract 버전 확인
tesseract --version

# 설치된 언어 확인
tesseract --list-langs
```

## 2. Python 패키지 설치

```bash
# 가상환경 활성화
source .venv/bin/activate

# Tesseract Python 래퍼 설치
pip install pytesseract

# PDF 처리 패키지 설치
pip install pdf2image Pillow PyMuPDF
```

## 3. 설치 확인 테스트

### 간단한 테스트
```bash
source .venv/bin/activate

python -c "
import pytesseract
from PIL import Image
import io

# Tesseract 버전 확인
print('Tesseract 버전:', pytesseract.get_tesseract_version())

# 지원 언어 확인
print('지원 언어:', pytesseract.get_languages())
"
```

### 실제 이미지 OCR 테스트
```python
# test_ocr.py
import pytesseract
from PIL import Image, ImageDraw, ImageFont

# 테스트 이미지 생성
img = Image.new('RGB', (400, 100), color='white')
d = ImageDraw.Draw(img)
d.text((10, 10), "Hello 안녕하세요", fill='black')
img.save('test_image.png')

# OCR 실행
text = pytesseract.image_to_string(img, lang='kor+eng')
print("추출된 텍스트:", text)
```

## 4. Tesseract 경로 설정 (필요시)

만약 pytesseract가 tesseract를 찾지 못하면:

```python
# app/services/ocr_engines.py에 추가
import pytesseract

# macOS Homebrew 기본 경로
pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

# Apple Silicon (M1/M2/M3)의 경우
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
```

또는 터미널에서 경로 확인:
```bash
which tesseract
```

## 5. 설치 후 전체 시스템 테스트

```bash
source .venv/bin/activate

# 우리 프로젝트의 하드웨어 테스트 실행
python test_hardware.py

# OCR 엔진 선택 확인 (Tesseract 설치 후)
python -c "
from app.services.ocr_engine_selector import OCREngineSelector

engine = OCREngineSelector.select_engine()
config = OCREngineSelector.get_engine_config(engine)

print(f'선택된 엔진: {engine}')
print(f'설정: {config}')
"
```

## 6. 문제 해결

### 문제 1: tesseract 명령어를 찾을 수 없음
```bash
# Homebrew 재설치
brew reinstall tesseract tesseract-lang

# 경로 확인
echo $PATH
```

### 문제 2: 한글이 인식되지 않음
```bash
# 한글 언어팩 재설치
brew reinstall tesseract-lang

# 언어팩 확인
tesseract --list-langs | grep kor
```

### 문제 3: PDF 변환 오류
```bash
# Poppler 설치 확인
brew list | grep poppler

# 재설치
brew reinstall poppler
```

## 7. 추가 유용한 도구

### ImageMagick (이미지 전처리용)
```bash
brew install imagemagick
```

### Ghostscript (PDF 처리 향상)
```bash
brew install ghostscript
```

## 8. 성능 비교

| 엔진 | 속도 | 정확도 | GPU | 한글 지원 |
|------|------|--------|-----|-----------|
| Tesseract | ⭐⭐⭐ | ⭐⭐⭐ | ❌ | ⭐⭐⭐ |
| EasyOCR | ⭐⭐ | ⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐⭐ |
| PaddleOCR | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐⭐ |

**권장**: 
- CPU만 있으면 → **Tesseract**
- GPU 있으면 → **EasyOCR** 또는 **PaddleOCR**
- M1 Mac → **EasyOCR** (자동 선택됨)

## 9. 우리 프로젝트에서 사용

Tesseract 설치 후, 시스템이 자동으로 감지하지만 강제로 사용하려면:

```bash
# .env 파일 수정
OCR_ENGINE=tesseract  # auto 대신 tesseract
```

또는 코드에서:
```python
from app.services.multi_engine_ocr_service import MultiEngineOCRService

# Tesseract 강제 사용
import os
os.environ['OCR_ENGINE'] = 'tesseract'

ocr_service = MultiEngineOCRService()
```

---

**설치 시간**: 약 5-10분
**디스크 공간**: 약 100-200MB
**필요 권한**: 관리자 권한 (Homebrew)
