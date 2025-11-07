# 빠른 테스트 가이드

현재 시스템에서 실행 가능한 모든 테스트를 정리했습니다.

## 사전 요구사항

```bash
# 가상환경 활성화 (모든 테스트 전에 실행)
source .venv/bin/activate
```

## 1. 하드웨어 감지 테스트

시스템의 GPU/CPU를 자동으로 감지합니다.

```bash
python test_hardware.py
```

**예상 출력**:
```
============================================================
Hardware Detection Test
============================================================

Device Type: mps
Device Count: 1
Device Name: Apple M1
Total Memory: None
Platform: Darwin
Platform Version: 25.0.0

============================================================
OCR Engine Selection
============================================================

Selected Engine: tesseract
Engine Config: {'lang': 'kor+eng', 'config': '--oem 3 --psm 6', 'use_gpu': False, 'dpi': 300}

✅ PASS: Hardware detection and OCR engine selection successful
```

## 2. Tesseract OCR 기본 테스트

Tesseract의 설치 상태와 한글 OCR 기능을 테스트합니다.

```bash
python test_tesseract_ocr.py
```

**예상 출력**:
```
============================================================
Tesseract 시스템 정보
============================================================

버전: 5.5.1

설치된 전체 언어 수: 126
한국어 언어팩: ['kor', 'kor_vert']

Tesseract 경로: tesseract

============================================================
Tesseract 한글 OCR 테스트
============================================================

[1] 테스트 이미지 생성...
   테스트 이미지 저장됨: test_korean_ocr.png

[2] OCR 실행 중...
   언어: 한국어 + 영어 (kor+eng)

[3] OCR 결과:
------------------------------------------------------------
원본 텍스트:
Hello World
안녕하세요 대한민국
형법 제1조
------------------------------------------------------------
추출된 텍스트:
[OCR 결과가 여기 표시됨]
------------------------------------------------------------

[4] OCR 상세 정보:
   평균 신뢰도: XX.XX%
   감지된 단어 수: X

[5] 테스트 결과:
   ✅ 성공: 텍스트 추출 완료

============================================================
최종 결과
============================================================
✅ Tesseract OCR 설치 및 테스트 완료
   - 한글 언어팩 설치됨
   - OCR 기능 정상 작동
============================================================
```

## 3. OCR 서비스 통합 테스트

프로젝트의 OCR 서비스 전체를 테스트합니다.

```bash
python test_ocr_service.py
```

**예상 출력**:
```
============================================================
하드웨어 정보
============================================================

디바이스 타입: mps
디바이스 수: 1
디바이스 이름: Apple M1
플랫폼: Darwin

============================================================
OCR 엔진 선택 테스트
============================================================

[자동 선택 모드]
선택된 엔진: tesseract
설정: {'lang': 'kor+eng', 'config': '--oem 3 --psm 6', 'use_gpu': False, 'dpi': 300}

[Tesseract 강제 모드]
선택된 엔진: tesseract
설정: {'lang': 'kor+eng', 'config': '--oem 3 --psm 6', 'use_gpu': False, 'dpi': 300}

============================================================
Tesseract 엔진 직접 테스트
============================================================

[1] Tesseract 엔진 초기화...
   ✅ 엔진 초기화 완료
   설정: {'lang': 'kor+eng', 'config': '--oem 3 --psm 6', 'use_gpu': False, 'dpi': 300}

[2] 테스트 이미지 생성...
   ✅ 이미지 생성 완료

[3] OCR 실행...

[4] 결과:
   추출된 텍스트: 'Testlmage anon'
   신뢰도: 45.00%

   ✅ 성공: 텍스트 추출 완료

============================================================
최종 테스트 결과
============================================================
✅ 모든 테스트 통과
   - 하드웨어 감지 완료
   - OCR 엔진 선택 완료
   - Tesseract OCR 작동 확인
============================================================
```

## 4. Tesseract 명령줄 테스트

Tesseract를 직접 명령줄에서 테스트할 수 있습니다.

```bash
# 버전 확인
tesseract --version

# 설치된 언어 확인
tesseract --list-langs

# 한글 언어팩 확인
tesseract --list-langs | grep kor
```

**예상 출력**:
```
tesseract 5.5.1

Available languages:
...
kor
kor_vert
...
```

## 5. Python 패키지 확인

설치된 Python 패키지를 확인합니다.

```bash
python -c "
import pytesseract
print('Tesseract 버전:', pytesseract.get_tesseract_version())
print('지원 언어 수:', len(pytesseract.get_languages()))
print('한글 언어팩:', [lang for lang in pytesseract.get_languages() if 'kor' in lang])
"
```

**예상 출력**:
```
Tesseract 버전: 5.5.1
지원 언어 수: 126
한글 언어팩: ['kor', 'kor_vert']
```

## 6. 환경 설정 확인

`.env` 파일의 설정을 확인합니다.

```bash
python -c "
from app.core.config import settings
print('앱 이름:', settings.APP_NAME)
print('앱 버전:', settings.APP_VERSION)
print('OCR 엔진:', settings.OCR_ENGINE)
print('디버그 모드:', settings.DEBUG)
print('암호화 키 설정:', '✅' if settings.ENCRYPTION_KEY else '❌')
print('JWT 시크릿 설정:', '✅' if settings.JWT_SECRET else '❌')
"
```

**예상 출력**:
```
앱 이름: PDF OCR System
앱 버전: 0.1.0
OCR 엔진: auto
디버그 모드: True
암호화 키 설정: ✅
JWT 시크릿 설정: ✅
```

## 7. 보안 기능 테스트

JWT 토큰 생성과 파일 해싱을 테스트합니다.

```bash
python -c "
from app.core.security import create_access_token, hash_file

# JWT 토큰 생성
token = create_access_token({'user_id': 1, 'username': 'test'})
print('JWT 토큰 생성:', '✅')
print('토큰 길이:', len(token))

# 파일 해싱
test_data = b'Hello World'
file_hash = hash_file(test_data)
print('파일 해싱:', '✅')
print('해시:', file_hash[:16] + '...')
"
```

**예상 출력**:
```
JWT 토큰 생성: ✅
토큰 길이: 180
파일 해싱: ✅
해시: a591a6d40bf420...
```

## 8. 모든 테스트 한번에 실행

```bash
echo "=== 1. 하드웨어 감지 ===" && \
python test_hardware.py && \
echo "" && \
echo "=== 2. Tesseract OCR ===" && \
python test_tesseract_ocr.py && \
echo "" && \
echo "=== 3. OCR 서비스 통합 ===" && \
python test_ocr_service.py
```

## 테스트 파일 위치

```
프로젝트 루트/
├── test_hardware.py           # 하드웨어 감지 테스트
├── test_tesseract_ocr.py      # Tesseract 기본 테스트
└── test_ocr_service.py        # OCR 서비스 통합 테스트
```

## 문제 해결

### 문제 1: "ModuleNotFoundError"

```bash
# 가상환경 활성화 확인
source .venv/bin/activate

# 패키지 재설치
pip install -r requirements.txt
```

### 문제 2: "tesseract 명령을 찾을 수 없음"

```bash
# Tesseract 재설치 (macOS)
brew reinstall tesseract tesseract-lang

# 경로 확인
which tesseract
```

### 문제 3: "한글이 인식되지 않음"

```bash
# 한글 언어팩 확인
tesseract --list-langs | grep kor

# 언어팩 재설치
brew reinstall tesseract-lang
```

## 다음 단계

현재 테스트가 모두 통과하면:

1. **실제 PDF 문서로 테스트**
   - 판례 PDF 파일 준비
   - OCR 실행 및 결과 확인

2. **FastAPI 서버 실행**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   - API 문서: http://localhost:8000/docs
   - 헬스 체크: http://localhost:8000/health

3. **데이터베이스 설정**
   - PostgreSQL 설치
   - Redis 설치
   - MinIO 설치

## 요약

| 테스트 | 명령어 | 예상 소요 시간 | 상태 |
|--------|--------|----------------|------|
| 하드웨어 감지 | `python test_hardware.py` | 1초 | ✅ |
| Tesseract OCR | `python test_tesseract_ocr.py` | 5초 | ✅ |
| OCR 서비스 | `python test_ocr_service.py` | 5초 | ✅ |
| 환경 설정 | `python -c "..."` | 1초 | ✅ |
| 보안 기능 | `python -c "..."` | 1초 | ✅ |

**총 소요 시간**: 약 15초

---

**생성 날짜**: 2025-10-30
**테스트 환경**: macOS (Apple M1), Python 3.11.9, Tesseract 5.5.1
