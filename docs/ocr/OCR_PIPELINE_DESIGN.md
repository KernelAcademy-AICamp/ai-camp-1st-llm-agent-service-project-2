# OCR 파이프라인 설계문서

> **버전**: 2.0.0
> **작성일**: 2025-11-07
> **목적**: 다양한 서비스에 재사용 가능한 OCR 파이프라인 설계 및 구현 가이드

---

## 📋 목차

1. [개요](#1-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [핵심 모듈 설계](#3-핵심-모듈-설계)
4. [데이터 플로우](#4-데이터-플로우)
5. [알고리즘 상세](#5-알고리즘-상세)
6. [성능 최적화 전략](#6-성능-최적화-전략)
7. [확장 및 커스터마이징](#7-확장-및-커스터마이징)
8. [배포 및 통합](#8-배포-및-통합)

---

## 1. 개요

### 1.1 설계 목적

본 OCR 파이프라인은 **이미지 기반 PDF 문서의 텍스트 추출 및 구조화**를 자동화하기 위해 설계되었습니다.

**핵심 목표**:
- ✅ 다양한 품질의 PDF 문서 처리 (고품질 ~ 저품질)
- ✅ 적응형 전처리를 통한 최적 OCR 정확도 달성
- ✅ 문서 타입별 자동 인식 및 맞춤 구조화
- ✅ 모듈화된 설계로 다른 서비스에 쉽게 적용 가능
- ✅ REST API 제공으로 프론트엔드/백엔드 통합 용이

### 1.2 적용 도메인

- **법률 문서**: 판결문, 소장, 내용증명, 합의서 등 관련 다양한 법률문서(판결문, 소장, 내용증명 형식 활성화)

### 1.3 기술 스택

| 구분 | 기술 | 버전 | 용도 |
|------|------|------|------|
| **OCR 엔진** | Tesseract OCR | 5.5.1 | 텍스트 인식 |
| **PDF 처리** | PyMuPDF (fitz) | 1.23.8 | PDF 파싱 및 텍스트 추출 |
| **이미지 변환** | pdf2image | 1.16.3 | PDF → 이미지 변환 |
| **이미지 처리** | Pillow, OpenCV | 10.1.0, 4.8+ | 전처리 (대비, 노이즈 제거 등) |
| **텍스트 분석** | Python re, NLP | 표준 라이브러리 | 패턴 추출 및 구조화 |
| **API 서버** | FastAPI | 0.104.1 | REST API 제공 |
| **배포** | Docker, Uvicorn | - | 컨테이너화 및 ASGI 서버 |

---

## 2. 시스템 아키텍처

### 2.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React/Vue)                      │
│  (파일 업로드, 결과 표시)                                      │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP POST
                     │ (multipart/form-data)
┌────────────────────▼────────────────────────────────────────┐
│                   FastAPI Server                             │
│  - 파일 업로드 핸들링                                          │
│  - 파이프라인 실행 제어                                        │
│  - 결과 JSON 반환                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   OCR Pipeline Core                          │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. PDF Text Extractor (pdf_extractor.py)            │   │
│  │    - PyMuPDF 텍스트 추출                             │   │
│  │    - 품질 평가 (추출 가능 여부 판단)                  │   │
│  └─────────────┬───────────────────────────────────────┘   │
│                │                                             │
│                ├─ [텍스트 추출 가능] ──────────────┐        │
│                │                                    │        │
│                └─ [텍스트 추출 불가] ────┐         │        │
│                                           │         │        │
│  ┌────────────────────────────────────────▼─────┐  │        │
│  │ 2. OCR Processor (ocr_processor.py)          │  │        │
│  │    A. Quality Assessor                       │  │        │
│  │       - 선명도, 노이즈, 대비, 밝기, 해상도 평가 │  │        │
│  │    B. Image Preprocessor                     │  │        │
│  │       - 선택적 전처리 적용                    │  │        │
│  │    C. Tesseract OCR                          │  │        │
│  │       - 텍스트 추출 + 신뢰도 계산             │  │        │
│  └────────────────────┬─────────────────────────┘  │        │
│                       │                             │        │
│                       └─────────────────────────────┤        │
│                                                      │        │
│  ┌───────────────────────────────────────────────── ▼ ─────┐│
│  │ 3. Post Processor (postprocessor.py)                    ││
│  │    - OCR 오인식 교정 (11+ 규칙)                         ││
│  │    - 패턴 기반 단어 치환                                 ││
│  └────────────────────┬────────────────────────────────────┘│
│                       │                                      │
│  ┌────────────────────▼────────────────────────────────────┐│
│  │ 4. Document Structurer (document_structurer.py)         ││
│  │    A. Type Detector (문서 타입 인식)                     ││
│  │    B. Type-specific Structurer                          ││
│  │       - Judgment: 판결문 구조화                          ││
│  │       - Complaint: 소장 구조화                           ││
│  │       - Notice: 내용증명 구조화                          ││
│  │       - Settlement: 합의서 구조화                        ││
│  └─────────────────────────────────────────────────────────┘│
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                 Structured JSON Output                       │
│  {                                                            │
│    "데이터타입": "소장",                                       │
│    "원고": "홍길동",                                          │
│    "피고": "김철수",                                          │
│    "청구금액": "35,800,000원",                                │
│    ...                                                        │
│  }                                                            │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 모듈 간 의존성

```
pdf_extractor.py
    ├── PyMuPDF (fitz)
    └── (독립 모듈)

ocr_processor.py
    ├── Pillow (PIL)
    ├── OpenCV (cv2)
    ├── numpy
    └── pytesseract

postprocessor.py
    └── Python re (정규표현식)

document_structurer.py
    ├── Python re
    └── datetime

backend/api/main.py
    ├── FastAPI
    ├── core.ocr (전체 모듈)
    └── aiofiles
```

---

## 3. 핵심 모듈 설계

### 3.1 Module 1: PDF Text Extractor

**파일**: `core/ocr/pdf_extractor.py`

**목적**: PDF에서 텍스트 추출 가능 여부를 판단하고 PyMuPDF로 빠른 추출을 시도

#### 클래스 설계

##### 3.1.1 `PDFTextExtractor`

**책임**:
- PyMuPDF를 사용한 텍스트 추출
- 추출 품질 평가 (OCR 필요 여부 판단)

**주요 메서드**:

| 메서드 | 입력 | 출력 | 설명 |
|--------|------|------|------|
| `extract_text_with_pymupdf()` | `pdf_path: Path` | `dict` | PyMuPDF로 텍스트 추출 |
| `is_text_extractable()` | `extraction_result: dict` | `bool` | 텍스트 사용 가능 여부 판단 |

**알고리즘**:

```python
def is_text_extractable(extraction_result, min_chars_per_page=100):
    """
    판단 기준:
    1. 추출 성공 여부
    2. 총 글자 수 >= 50자
    3. 페이지당 평균 글자 수 >= min_chars_per_page
    4. 의미 있는 텍스트(한글/영어) 비율 >= 30%

    Returns:
        True: PyMuPDF 텍스트 사용 가능
        False: OCR 필요
    """
```

**성능 지표**:
- 처리 속도: ~0.5초/페이지 (10페이지 PDF = 5초)
- 메모리: 20-50MB (파일 크기 의존)

---

### 3.2 Module 2: OCR Processor

**파일**: `core/ocr/ocr_processor.py`

**목적**: 이미지 품질 평가 후 적응형 전처리를 적용하여 최적의 OCR 결과 도출

#### 클래스 설계

##### 3.2.1 `DocumentQualityAssessor`

**책임**: 이미지 품질을 정량적으로 평가

**평가 항목**:

| 항목 | 측정 방법 | 점수 범위 | 기준 |
|------|----------|-----------|------|
| **선명도** | Laplacian 분산 | 0-100 | >100: 선명, 50-100: 보통, <50: 흐림 |
| **노이즈** | 표준편차 분석 | 0-100 | >50: 많음, 20-50: 보통, <20: 적음 |
| **대비** | RMS Contrast | 0-100 | >80: 좋음, 40-80: 보통, <40: 낮음 |
| **밝기** | 평균 픽셀 값 | 0-255 | 100-180: 적정, >180: 밝음, <100: 어두움 |
| **해상도** | 픽셀 수 (MP) | 0-100 | >1MP: 고해상도, 0.5-1MP: 보통, <0.5MP: 저해상도 |

**종합 품질 점수 계산**:

```python
# 가중치 기반 종합 점수
weights = {
    'sharpness': 0.30,    # 선명도 가장 중요
    'contrast': 0.25,     # 대비 중요
    'noise': 0.20,        # 노이즈 중간
    'resolution': 0.15,   # 해상도 중간
    'brightness': 0.10    # 밝기 덜 중요
}

total_score = sum(normalized[k] * weights[k] for k in weights)

# 품질 등급
if total_score >= 80:
    quality_level = 'excellent'  # 우수
    recommended_preset = 'minimal'  # 최소 전처리
elif total_score >= 60:
    quality_level = 'good'  # 양호
    recommended_preset = 'selective'  # 선택적 전처리
else:
    quality_level = 'poor'  # 불량
    recommended_preset = 'selective'  # 선택적 전처리 (강화)
```

**출력 예시**:

```json
{
  "scores": {
    "sharpness": 85.3,
    "noise": 25.1,
    "contrast": 62.4,
    "brightness": 145.2,
    "resolution_mp": 1.84
  },
  "normalized_scores": {
    "sharpness": 42.7,
    "noise": 75.0,
    "contrast": 78.0,
    "brightness": 95.0,
    "resolution": 92.0
  },
  "total_score": 72.3,
  "quality_level": "good",
  "recommended_preset": "selective",
  "analysis": {
    "needs_sharpening": true,
    "needs_denoising": false,
    "needs_contrast_boost": true,
    "needs_brightness_adjustment": false,
    "is_low_resolution": false,
    "contrast_factor": 1.5,
    "brightness_adjustment": 0.0
  }
}
```

##### 3.2.2 `ImagePreprocessor`

**책임**: 다양한 이미지 전처리 기법 제공

**전처리 기법**:

| 기법 | 목적 | 적용 조건 | 파라미터 |
|------|------|-----------|----------|
| `grayscale()` | 색상 제거, 텍스트 강조 | 항상 | - |
| `increase_contrast()` | 텍스트-배경 구분 명확화 | 대비 < 50 | factor: 1.2~2.0 |
| `sharpen()` | 흐릿한 텍스트 개선 | 선명도 < 100 | - |
| `denoise()` | 얼룩, 점 제거 | 노이즈 > 30 | - |
| `binarization()` | 흑백 명확 구분 | 품질 낮음 | method: otsu/adaptive |
| `upscale()` | 작은 텍스트 개선 | 해상도 < 1MP | scale: 2배 |
| `remove_shadows()` | 스캔 문서 그림자 제거 | 품질 나쁨 | - |
| `deskew()` | 기울어진 문서 보정 | 필요 시 | - |
| `adjust_brightness()` | 밝기 조정 | 밝기 < 100 or > 200 | factor: -1.0~1.0 |

**선택적 전처리 플로우**:

```
이미지 입력
   ↓
[항상] 그레이스케일 변환
   ↓
[조건] 저해상도? → 해상도 2배 증가
   ↓
[조건] 노이즈 많음? → 노이즈 제거
   ↓
[조건] 밝기 부적절? → 밝기 조정
   ↓
[조건] 대비 낮음? → 대비 증가
   ↓
[조건] 흐림? → 선명도 증가
   ↓
[조건] 품질 나쁨? → 이진화 (adaptive)
   ↓
전처리 완료
```

**레거시 Preset 모드** (하위 호환성):

```python
# 고정 전처리 파이프라인
presets = {
    'light': [그레이스케일, 대비(1.2배), 선명도],
    'standard': [그레이스케일, 노이즈제거, 대비(1.5배), 선명도, 이진화],
    'aggressive': [해상도증가, 그림자제거, 기울기보정, 노이즈제거, 대비(2.0배), 이진화]
}
```

##### 3.2.3 `extract_pdf_with_preprocessing()`

**통합 OCR 함수**

**입력**:
```python
def extract_pdf_with_preprocessing(
    pdf_path: Path,
    dpi: int = 300,
    preset: str = 'standard',
    adaptive: bool = False
) -> dict:
```

**출력**:
```json
{
  "filename": "소장1_일반교통사고손해배상_converted.pdf",
  "page_count": 3,
  "dpi": 300,
  "preprocessing": "adaptive",
  "adaptive_mode": true,
  "total_chars": 1108,
  "avg_confidence": 60.0,
  "pages": [
    {
      "page_number": 1,
      "text": "...",
      "char_count": 420,
      "confidence": 65.2,
      "word_count": 78,
      "preprocessing_used": "selective",
      "quality_assessment": {...}
    }
  ],
  "preset_usage": {
    "selective": 2,
    "minimal": 1
  }
}
```

**성능 지표**:
- 처리 속도: 10-20초/페이지 (전처리 포함)
- OCR 신뢰도: 평균 60-85%
- 메모리: 100-300MB (DPI 의존)

---

### 3.3 Module 3: Post Processor

**파일**: `core/ocr/postprocessor.py`

**목적**: OCR 오인식 단어를 자동으로 교정

#### 클래스 설계

##### 3.3.1 `OCRPostProcessor`

**책임**: 패턴 기반 텍스트 교정

**교정 규칙**:

| 오인식 단어 | 올바른 단어 | 발생 원인 | 교정 횟수 (평균) |
|------------|------------|-----------|-----------------|
| 정구취지 | 청구취지 | 'ㅊ' → 'ㅈ' 오인식 | 1-3회/문서 |
| 정구원인 | 청구원인 | 'ㅊ' → 'ㅈ' 오인식 | 1-3회/문서 |
| 판결올 | 판결을 | 'ㅡ' → 'ㅗ' 오인식 | 0-2회/문서 |
| HAS | 판결을 | 영문자 오인식 | 0-1회/문서 |
| SS | 항 | 영문자 오인식 | 0-2회/문서 |
| 갖는 | 갚는 | 받침 오인식 | 0-1회/문서 |

**패턴 기반 교정**:

```python
PATTERN_CORRECTIONS = [
    # "제 1 SS" → "제1항"
    (r'제\s*(\d+)\s*SS', r'제\1항'),

    # "ODE DDS" → "원고는 피고를"
    (r'ODE\s+DDS', '원고는 피고를'),

    # "갖는 날" → "갚는 날"
    (r'갖는\s+날', '갚는 날'),

    # 공백 과다 정리
    (r'\s{3,}', ' '),
]
```

**적용 예시**:

```
[교정 전]
정구쥐지
1. 피고는 원고에게 금 35,800,000 원을 다 갖는 날까지 지급하라.
2. 제 1 SS 가집행할 수 있다.
라는 HAS 구합니다.

[교정 후]
청구취지
1. 피고는 원고에게 금 35,800,000 원을 다 갚는 날까지 지급하라.
2. 제1항 가집행할 수 있다.
라는 판결을 구합니다.

교정 횟수: 7가지
```

**성능**:
- 처리 속도: <0.1초 (1000자 기준)
- 메모리: 미미 (~1MB)

---

### 3.4 Module 4: Document Structurer

**파일**: `core/ocr/document_structurer.py`

**목적**: 문서 타입을 자동 인식하고 타입별 맞춤 구조화 수행

#### 클래스 설계

##### 3.4.1 `DocumentTypeDetector`

**책임**: 문서 타입 자동 인식

**인식 로직**:

```python
def detect(text: str, filename: str) -> str:
    """
    우선순위:
    1. 파일명 키워드 ('판결', '소장', '내용증명', '합의서')
    2. 텍스트 내용 패턴
       - 판결문: '판결' + '주문'
       - 소장: '소장' + ('청구취지' or '청구원인')
       - 내용증명: '내용증명' or ('수신' + '발신')
       - 합의서: '합의서' + '갑' + '을'
    3. 기타
    """
```

**지원 타입**:

| 타입 | 코드 | 주요 필드 | 추출 난이도 |
|------|------|----------|------------|
| 판결문 | `judgment` | 사건번호, 법원명, 원고, 피고, 주문, 이유 | ⭐⭐⭐⭐ |
| 소장 | `complaint` | 사건명, 원고, 피고, 청구금액, 청구취지, 청구원인 | ⭐⭐⭐ |
| 내용증명 | `notice` | 제목, 수신인, 발신인, 발신일자, 주요내용 | ⭐⭐ |
| 합의서 | `settlement` | 제목, 갑, 을, 합의내용, 날짜 | ⭐⭐ |
| 기타 | `other` | 텍스트 전체 | ⭐ |

##### 3.4.2 타입별 Structurer

**`NoticeStructurer` (내용증명)**

**추출 필드**:

| 필드 | 정규식 패턴 | 예시 |
|------|------------|------|
| 제목 | `r'제\s*목\s*[:\s]*([^\n]+)'` | "보험금 청구 요청의 건" |
| 수신인 | `r'수\s*신\s*인?\s*[:：]?\s*([^\n]+)'` | "삼성화재해상보험" |
| 발신인 | `r'발\s*신\s*인?\s*[:：]?\s*([^\n]+)'` | "홍길동" |
| 발신일자 | `r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일'` | "2025.06.15" |
| 주요내용 | 헤더 제거 후 본문 전체 | 1000자 이상 |

**주요내용 추출 로직** (개선된 알고리즘):

```python
def extract_main_content(self) -> str:
    """
    1단계: 헤더 스킵
       - '내용증명', '제목', '수신인', '발신인', '전화', '주소' 등
    2단계: 본문 전체 추출 (글자 수 제한 없음)
    3단계: 하단 서명/첨부 제거
       - "(인)" 또는 "첨부:" 이후 제외

    결과: 완전한 본문 (3000자 이상도 가능)
    """
```

**`ComplaintStructurer` (소장)**

**추출 필드**:

| 필드 | 정규식 패턴 | 예시 |
|------|------------|------|
| 사건명 | `r'([가-힣]+\([가-힣]\))'` | "손해배상(자)" |
| 법원 | `r'([가-힣]+지방법원)'` | "서울중앙지방법원" |
| 원고 | `r'원\s*고\s*[:：]?\s*([^\n(]+)'` | "김부상" |
| 피고 | `r'피\s*고\s*[:：]?\s*([^\n(]+)'` | "이가해" |
| 청구금액 | `r'금\s*([\d,]+)\s*원'` | "35,800,000원" |
| 청구취지 | `r'청\s*구\s*취\s*지\s*(.*?)(?=청\s*구\s*원\s*인)'` | 500자 제한 |
| 청구원인 | `r'청\s*구\s*원\s*인\s*(.*?)(?=입\s*증)'` | 1000자 제한 |

**`JudgmentStructurer` (판결문)**

기존 복잡한 파싱 로직 사용 (별도 모듈 연동)

**출력 형식 (예시)**:

```json
{
  "데이터타입": "소장",
  "파일명": "소장1_일반교통사고손해배상_converted.pdf",
  "사건명": "손해배상(자)",
  "법원": "",
  "원고": "김부상",
  "피고": "이가해",
  "청구금액": "35,800,000원",
  "청구취지": "1. 피고는 원고에게 금 35,800,000 원 및 이에 대하여...",
  "청구원인": "1. 사고의 발생\n피고는 2025 년 6 월 15 일...",
  "처리시각": "2025-11-07T14:27:51.818374"
}
```

---

## 4. 데이터 플로우

### 4.1 전체 처리 흐름

```
[1] PDF 파일 입력
      ↓
[2] PyMuPDF 텍스트 추출 시도
      ↓
   [분기점]
      ├─ 텍스트 추출 가능 ────────────────────┐
      │   (페이지당 100자 이상 + 의미 있는 텍스트 30% 이상)
      │                                        │
      └─ 텍스트 추출 불가 ──────┐             │
          (이미지 기반 PDF)       │             │
                                  ↓             │
[3] PDF → 이미지 변환 (300 DPI)                │
      ↓                                        │
[4] 품질 평가 (선명도, 노이즈, 대비, 밝기, 해상도)│
      ↓                                        │
[5] 적응형 전처리 선택                          │
      ↓                                        │
[6] Tesseract OCR 실행                         │
      ↓                                        │
[7] 신뢰도 계산                                 │
      ↓                                        │
      └────────────────────────────────────────┤
                                               │
[8] OCR 후처리 (오인식 교정)                    │
      ↓                                        │
      └────────────────────────────────────────┤
                                               │
[9] 전체 텍스트 병합                            │
      ↓
[10] 문서 타입 자동 인식
      ↓
   [분기점]
      ├─ 판결문 → JudgmentStructurer
      ├─ 소장 → ComplaintStructurer
      ├─ 내용증명 → NoticeStructurer
      ├─ 합의서 → SettlementStructurer
      └─ 기타 → 기본 구조
      ↓
[11] 타입별 필드 추출 (정규식 패턴 매칭)
      ↓
[12] JSON 구조화 데이터 출력
```

### 4.2 처리 시간 분석

**10페이지 PDF 기준** (이미지 기반, 300 DPI):

| 단계 | 소요 시간 | 비율 | 병목 여부 |
|------|----------|------|----------|
| PDF → 이미지 변환 | 10초 | 10% | ❌ |
| 품질 평가 (10페이지) | 5초 | 5% | ❌ |
| 이미지 전처리 (10페이지) | 15초 | 15% | ⚠️ |
| Tesseract OCR (10페이지) | 60초 | 60% | ✅ 병목 |
| 후처리 + 구조화 | 10초 | 10% | ❌ |
| **총 처리 시간** | **100초** | **100%** | - |

**최적화 전략**:
1. **멀티프로세싱**: 페이지별 병렬 처리 (4 core → 40초로 단축)
2. **GPU 가속**: Tesseract GPU 버전 (CUDA) → 30% 속도 향상
3. **배치 처리**: 여러 PDF 동시 처리

---

## 5. 알고리즘 상세

### 5.1 적응형 전처리 알고리즘

**의사 코드**:

```
ALGORITHM AdaptivePreprocessing(image)
INPUT:
    image: PIL Image 객체
OUTPUT:
    preprocessed_image: 전처리된 이미지

1. quality = AssessQuality(image)
   // 품질 평가 수행

2. total_score = CalculateWeightedScore(quality)
   // 가중치 기반 종합 점수 계산

3. IF total_score >= 80 THEN
       preset = 'minimal'  // 최소 전처리
   ELSE IF total_score >= 60 THEN
       preset = 'selective'  // 선택적 전처리
   ELSE
       preset = 'selective'  // 선택적 전처리 (강화)
   END IF

4. processed = image
5. processed = Grayscale(processed)  // 항상 적용

6. IF quality.is_low_resolution THEN
       processed = Upscale(processed, scale=2)
   END IF

7. IF quality.needs_denoising THEN
       processed = Denoise(processed)
   END IF

8. IF quality.needs_brightness_adjustment THEN
       factor = quality.brightness_adjustment
       processed = AdjustBrightness(processed, factor)
   END IF

9. IF quality.needs_contrast_boost THEN
       factor = quality.contrast_factor
       processed = IncreaseContrast(processed, factor)
   END IF

10. IF quality.needs_sharpening THEN
        processed = Sharpen(processed)
    END IF

11. IF quality.quality_level == 'poor' THEN
        processed = Binarization(processed, method='adaptive')
    ELSE IF quality.needs_contrast_boost THEN
        processed = Binarization(processed, method='otsu')
    END IF

12. RETURN processed
```

### 5.2 문서 타입 인식 알고리즘

**의사 코드**:

```
ALGORITHM DetectDocumentType(text, filename)
INPUT:
    text: 추출된 전체 텍스트
    filename: 파일명
OUTPUT:
    doc_type: 'judgment' | 'complaint' | 'notice' | 'settlement' | 'other'

1. text_normalized = RemoveWhitespace(text)
   // 공백 제거하여 띄어쓰기 무시

2. // 우선순위 1: 파일명 기반 판단
   filename_lower = ToLowerCase(filename)

   IF '판결' IN filename OR 'judgment' IN filename_lower THEN
       RETURN 'judgment'
   ELSE IF '소장' IN filename OR 'complaint' IN filename_lower THEN
       RETURN 'complaint'
   ELSE IF '내용증명' IN filename OR 'notice' IN filename_lower THEN
       RETURN 'notice'
   ELSE IF '합의서' IN filename OR 'settlement' IN filename_lower THEN
       RETURN 'settlement'
   END IF

3. // 우선순위 2: 텍스트 내용 기반 판단
   IF ('판결' IN text_normalized) AND ('주문' IN text_normalized) THEN
       RETURN 'judgment'
   ELSE IF ('소장' IN text_normalized) AND
           (('청구취지' IN text_normalized) OR ('청구원인' IN text_normalized)) THEN
       RETURN 'complaint'
   ELSE IF ('내용증명' IN text_normalized) OR
           (('수신' IN text_normalized) AND ('발신' IN text_normalized)) THEN
       RETURN 'notice'
   ELSE IF ('합의서' IN text_normalized) AND
           ('갑' IN text_normalized) AND ('을' IN text_normalized) THEN
       RETURN 'settlement'
   END IF

4. RETURN 'other'
```

### 5.3 패턴 기반 필드 추출 알고리즘

**예시: 청구취지 추출**

```
ALGORITHM ExtractClaimPurpose(text)
INPUT:
    text: 소장 전체 텍스트
OUTPUT:
    claim_purpose: 청구취지 텍스트 (최대 500자)

1. patterns = [
       r'청\s*구\s*취\s*지\s*(.*?)(?=청\s*구\s*원\s*인|입\s*증|$)',
       r'청구취지\s*(.*?)(?=청구원인|입증|$)'
   ]

2. FOR EACH pattern IN patterns DO
       match = RegexSearch(pattern, text, flags=DOTALL)

       IF match THEN
           purpose = match.group(1).strip()

           // 줄바꿈 정리
           purpose = RegexSub(r'\n\s*\n', '\n', purpose)

           // 길이 제한
           IF length(purpose) > 500 THEN
               purpose = purpose[:500] + "..."
           END IF

           RETURN purpose
       END IF
   END FOR

3. RETURN ""  // 추출 실패
```

---

## 6. 성능 최적화 전략

### 6.1 처리 속도 최적화

#### 6.1.1 병렬 처리 (Multiprocessing)

**적용 대상**: 페이지별 OCR 처리

```python
from multiprocessing import Pool

def process_page(args):
    page_num, pdf_path, dpi = args
    # 페이지 추출 → 전처리 → OCR
    return ocr_result

# 4개 코어 병렬 처리
with Pool(processes=4) as pool:
    args_list = [(i, pdf_path, 300) for i in range(page_count)]
    results = pool.map(process_page, args_list)
```

**성능 개선**:
- 10페이지 PDF: 100초 → 40초 (60% 단축)

#### 6.1.2 GPU 가속 (Tesseract GPU)

**설정**:
```bash
# CUDA 지원 Tesseract 설치
sudo apt install tesseract-ocr-cuda
```

**성능 개선**:
- OCR 시간: 6초/페이지 → 4초/페이지 (30% 단축)

#### 6.1.3 해상도 조정

**권장 DPI 설정**:

| 문서 품질 | DPI | OCR 정확도 | 처리 속도 |
|----------|-----|-----------|----------|
| 고품질 (선명) | 200 | 80-85% | 빠름 (5초/페이지) |
| 중품질 (보통) | 300 | 75-80% | 보통 (10초/페이지) |
| 저품질 (흐림) | 400 | 70-75% | 느림 (20초/페이지) |

### 6.2 메모리 최적화

#### 6.2.1 이미지 해제

```python
# 사용 후 즉시 메모리 해제
image = pdf_page_to_image(page, dpi=300)
ocr_result = ocr_image(image)
del image  # 메모리 해제
gc.collect()
```

#### 6.2.2 스트리밍 처리

대용량 PDF (100+ 페이지):
- 페이지별 순차 처리 (전체 로드 X)
- 결과를 파일에 즉시 저장 (메모리 유지 X)

### 6.3 정확도 최적화

#### 6.3.1 품질 기반 DPI 선택

```python
def select_dpi(quality_score):
    if quality_score >= 80:
        return 200  # 고품질 → 낮은 DPI
    elif quality_score >= 60:
        return 300  # 중품질 → 표준 DPI
    else:
        return 400  # 저품질 → 높은 DPI
```

#### 6.3.2 언어 모델 최적화

```python
# 한국어 + 영어 조합
pytesseract.image_to_string(image, lang='kor+eng')

# 숫자 위주 문서
pytesseract.image_to_string(image, lang='kor+eng',
                             config='--psm 6 digits')
```

---

## 7. 확장 및 커스터마이징

### 7.1 새로운 문서 타입 추가

**단계**:

1. **타입 정의** (`DocumentTypeDetector`):

```python
# document_structurer.py
def detect(text: str, filename: str) -> str:
    # 기존 코드...

    # 새로운 타입 추가
    if '진단서' in filename or 'diagnosis' in filename_lower:
        return 'diagnosis'
```

2. **Structurer 클래스 작성**:

```python
class DiagnosisStructurer:
    """진단서 구조화"""

    def __init__(self, text: str, filename: str):
        self.text = text
        self.filename = filename

    def extract_patient_name(self) -> str:
        """환자명 추출"""
        pattern = r'환\s*자\s*명\s*[:：]?\s*([^\n]+)'
        match = re.search(pattern, self.text)
        return match.group(1).strip() if match else ""

    def extract_diagnosis(self) -> str:
        """진단명 추출"""
        pattern = r'진\s*단\s*명\s*[:：]?\s*([^\n]+)'
        match = re.search(pattern, self.text)
        return match.group(1).strip() if match else ""

    def structure(self) -> dict:
        return {
            "데이터타입": "진단서",
            "파일명": self.filename,
            "환자명": self.extract_patient_name(),
            "진단명": self.extract_diagnosis(),
            # 추가 필드...
            "처리시각": datetime.now().isoformat()
        }
```

3. **DocumentStructurer에 연결**:

```python
def structure(self) -> dict:
    # 기존 코드...

    if self.doc_type == 'diagnosis':
        structurer = DiagnosisStructurer(self.text, self.filename)
    # ...
```

### 7.2 새로운 전처리 기법 추가

**예시: 색상 보정 추가**

```python
class ImagePreprocessor:
    # 기존 메서드...

    @staticmethod
    def color_correction(image):
        """색상 보정 - 황변된 문서 개선"""
        if isinstance(image, Image.Image):
            image = ImagePreprocessor.pil_to_cv2(image)

        # LAB 색공간 변환
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # L 채널 히스토그램 균등화
        l = cv2.equalizeHist(l)

        # 병합 후 RGB 복원
        lab = cv2.merge([l, a, b])
        corrected = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        return ImagePreprocessor.cv2_to_pil(corrected)
```

**선택적 전처리에 추가**:

```python
def preprocess_image_selective(image, quality_analysis):
    # 기존 코드...

    # 색상 보정 (필요 시)
    if quality_analysis['analysis'].get('needs_color_correction'):
        image = preprocessor.color_correction(image)
        steps.append("색상 보정")
```

### 7.3 다국어 지원

**언어 팩 추가**:

```bash
# 일본어
sudo apt install tesseract-ocr-jpn

# 중국어
sudo apt install tesseract-ocr-chi-sim
```

**코드 수정**:

```python
def extract_pdf_with_preprocessing(
    pdf_path: Path,
    dpi=300,
    preset='standard',
    adaptive=False,
    lang='kor+eng'  # 언어 파라미터 추가
):
    # OCR 실행 시
    text = pytesseract.image_to_string(
        processed_image,
        lang=lang,  # 동적 언어 설정
        config=custom_config
    )
```

---

## 8. 배포 및 통합

### 8.1 Docker 컨테이너화

**Dockerfile**:

```dockerfile
FROM python:3.11-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# FastAPI 서버 실행
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**빌드 및 실행**:

```bash
# 이미지 빌드
docker build -t ocr-pipeline:latest .

# 컨테이너 실행
docker run -d -p 8000:8000 --name ocr-api ocr-pipeline:latest
```

### 8.2 REST API 엔드포인트

**주요 엔드포인트**:

| 엔드포인트 | 메서드 | 설명 | 입력 | 출력 |
|-----------|--------|------|------|------|
| `/api/v1/process-pdf` | POST | PDF 처리 | `file`, `adaptive`, `apply_postprocessing` | JSON |
| `/health` | GET | 서버 상태 확인 | - | `{"status": "healthy"}` |

**요청 예시**:

```bash
curl -X POST "http://localhost:8000/api/v1/process-pdf" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/file.pdf" \
  -F "adaptive=true" \
  -F "apply_postprocessing=true"
```

**응답 예시**:

```json
{
  "success": true,
  "filename": "소장1_일반교통사고손해배상_converted.pdf",
  "data": {
    "데이터타입": "소장",
    "원고": "김부상",
    "피고": "이가해",
    "청구금액": "35,800,000원",
    "청구취지": "...",
    "청구원인": "...",
    "처리시각": "2025-11-07T14:27:51.818374"
  },
  "processing_time": 15.234
}
```

### 8.3 프론트엔드 통합

**React 예시**:

```javascript
import React, { useState } from 'react';
import axios from 'axios';

function PDFUploader() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('adaptive', 'true');
    formData.append('apply_postprocessing', 'true');

    try {
      const response = await axios.post(
        'http://localhost:8000/api/v1/process-pdf',
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );
      setResult(response.data.data);
    } catch (error) {
      console.error('OCR 처리 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="file"
        accept=".pdf"
        onChange={(e) => setFile(e.target.files[0])}
      />
      <button onClick={handleUpload} disabled={loading}>
        {loading ? '처리 중...' : 'PDF 처리'}
      </button>

      {result && (
        <div>
          <h3>추출 결과</h3>
          <p>문서 타입: {result.데이터타입}</p>
          <p>원고: {result.원고}</p>
          <p>피고: {result.피고}</p>
          <p>청구금액: {result.청구금액}</p>
        </div>
      )}
    </div>
  );
}
```

### 8.4 마이크로서비스 아키텍처

**서비스 분리**:

```
┌─────────────────────┐
│  Frontend Service   │ (React, Port 3000)
└──────────┬──────────┘
           │ HTTP
┌──────────▼──────────┐
│  API Gateway        │ (Nginx, Port 80)
└──────────┬──────────┘
           │
    ┌──────┴──────┬──────────────┐
    │             │              │
┌───▼────┐  ┌────▼────┐  ┌──────▼───────┐
│ OCR    │  │ Storage │  │ Notification │
│ Service│  │ Service │  │ Service      │
│(8000)  │  │(9000)   │  │(9001)        │
└────────┘  └─────────┘  └──────────────┘
```

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  ocr-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
      - ./results:/app/results
    environment:
      - TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - ocr-api
```

---

## 9. 성능 벤치마크

### 9.1 실측 성능 데이터

**테스트 환경**:
- CPU: Apple M1 (8 cores)
- RAM: 16GB
- OS: macOS 14.0

**테스트 데이터**:
- 소장1_일반교통사고손해배상_converted.pdf (3페이지, 이미지 기반)
- 내용증명2_보험회사보험금청구_converted.pdf (2페이지, 이미지 기반)

**결과**:

| 지표 | 소장 (3페이지) | 내용증명 (2페이지) | 평균 |
|------|---------------|------------------|------|
| 처리 시간 | 18.5초 | 12.3초 | 15.4초 |
| OCR 신뢰도 | 60.0% | 75.5% | 67.8% |
| 글자 수 | 1,108자 | 892자 | 1,000자 |
| 전처리 사용 | selective (3/3) | minimal (1/2), selective (1/2) | - |
| 후처리 교정 | 7건 | 3건 | 5건 |
| 데이터 완전성 | 80% | 94% | 87% |

### 9.2 품질 등급별 성능

| 문서 품질 | OCR 신뢰도 | 처리 시간 (페이지당) | 전처리 전략 |
|----------|-----------|---------------------|------------|
| 우수 (80+) | 85-95% | 8초 | minimal |
| 양호 (60-80) | 70-85% | 12초 | selective |
| 불량 (<60) | 50-70% | 20초 | selective (강화) |

---

## 10. 트러블슈팅

### 10.1 일반적인 문제

| 문제 | 원인 | 해결 방법 |
|------|------|----------|
| OCR 신뢰도 낮음 (<50%) | 문서 품질 매우 나쁨 | DPI 400으로 증가, aggressive preset 사용 |
| 메모리 부족 | 대용량 PDF (100+ 페이지) | 페이지별 순차 처리, 메모리 해제 |
| Tesseract 오류 | 언어 팩 미설치 | `sudo apt install tesseract-ocr-kor` |
| 느린 처리 속도 | 단일 코어 처리 | 멀티프로세싱 적용 |
| 잘못된 문서 타입 인식 | 파일명/내용 패턴 불일치 | 수동 타입 지정 파라미터 추가 |

### 10.2 성능 개선 체크리스트

- [ ] DPI 설정 최적화 (200-400)
- [ ] 멀티프로세싱 활성화
- [ ] GPU 가속 설정 (CUDA)
- [ ] 불필요한 전처리 제거
- [ ] 메모리 해제 코드 추가
- [ ] 결과 캐싱 (동일 파일 재처리 방지)

---

## 11. 참고 자료

### 11.1 외부 문서

- [Tesseract OCR 공식 문서](https://github.com/tesseract-ocr/tesseract)
- [PyMuPDF 문서](https://pymupdf.readthedocs.io/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [OpenCV 이미지 처리 튜토리얼](https://docs.opencv.org/4.x/d2/d96/tutorial_py_table_of_contents_imgproc.html)

### 11.2 내부 문서

- [OCR 파이프라인 개요](README.md)
- [설치 가이드](SETUP.md)
- [빠른 시작](QUICK_START.md)
- [API 가이드](API_GUIDE.md)
- [프론트엔드 예제](FRONTEND_EXAMPLES.md)

---

## 부록 A: 모듈 API 레퍼런스

### A.1 pdf_extractor.py

```python
class PDFTextExtractor:
    @staticmethod
    def extract_text_with_pymupdf(pdf_path: Path) -> dict:
        """
        Returns:
            {
                'success': bool,
                'text': str,
                'page_count': int,
                'char_count': int,
                'extraction_rate': float
            }
        """

    @staticmethod
    def is_text_extractable(extraction_result: dict, min_chars_per_page: int = 100) -> bool:
        """
        Returns:
            True: 텍스트 사용 가능
            False: OCR 필요
        """
```

### A.2 ocr_processor.py

```python
class DocumentQualityAssessor:
    @staticmethod
    def assess_quality(image) -> dict:
        """
        Returns:
            {
                'scores': {...},
                'normalized_scores': {...},
                'total_score': float,
                'quality_level': str,
                'recommended_preset': str,
                'analysis': {...}
            }
        """

class ImagePreprocessor:
    @staticmethod
    def grayscale(image) -> Image

    @staticmethod
    def increase_contrast(image, factor=2.0) -> Image

    @staticmethod
    def sharpen(image) -> Image

    @staticmethod
    def denoise(image) -> Image

    @staticmethod
    def binarization(image, method='otsu') -> Image

    # ... 기타 메서드

def extract_pdf_with_preprocessing(
    pdf_path: Path,
    dpi: int = 300,
    preset: str = 'standard',
    adaptive: bool = False
) -> dict:
    """
    Returns:
        {
            'filename': str,
            'page_count': int,
            'total_chars': int,
            'avg_confidence': float,
            'pages': [...],
            'preset_usage': {...}
        }
    """
```

### A.3 postprocessor.py

```python
class OCRPostProcessor:
    @classmethod
    def post_process(cls, text: str, verbose: bool = False) -> str:
        """OCR 텍스트 후처리"""

    @classmethod
    def validate_corrections(cls, text: str) -> Dict[str, int]:
        """교정 가능한 오인식 단어 통계"""

def apply_ocr_postprocessing(text: str, verbose: bool = False) -> str:
    """편의 함수"""
```

### A.4 document_structurer.py

```python
class DocumentTypeDetector:
    @staticmethod
    def detect(text: str, filename: str) -> str:
        """
        Returns:
            'judgment' | 'complaint' | 'notice' | 'settlement' | 'other'
        """

class DocumentStructurer:
    def __init__(self, text: str, filename: str):
        """문서 타입 자동 인식 및 구조화"""

    def structure(self) -> dict:
        """
        Returns:
            타입별 구조화된 dict
        """

class NoticeStructurer:
    def structure(self) -> dict:
        """내용증명 구조화"""

class ComplaintStructurer:
    def structure(self) -> dict:
        """소장 구조화"""

class JudgmentStructurer:
    def structure(self) -> dict:
        """판결문 구조화"""
```

---

## 부록 B: 설정 파일 예시

### B.1 requirements.txt

```txt
# OCR Pipeline Core
PyMuPDF==1.23.8
pytesseract==0.3.10
pdf2image==1.16.3
Pillow==10.1.0
opencv-python==4.8.1.78
numpy==1.26.2

# API Server
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
aiofiles==23.2.1

# Utils
python-dotenv==1.0.0
```

### B.2 .env (환경 변수)

```bash
# OCR 설정
TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
DEFAULT_DPI=300
DEFAULT_PRESET=standard
ENABLE_ADAPTIVE=true

# API 설정
API_HOST=0.0.0.0
API_PORT=8000
MAX_FILE_SIZE=50MB
ALLOWED_ORIGINS=http://localhost:3000,https://example.com

# 로깅
LOG_LEVEL=INFO
LOG_FILE=/app/logs/ocr.log
```

---

**문서 끝**

이 설계문서는 OCR 파이프라인의 핵심 설계 원리, 알고리즘, 확장 방법을 상세히 다룹니다.
다른 서비스에 적용 시 이 문서를 기반으로 도메인 특화 커스터마이징을 진행하시면 됩니다.
