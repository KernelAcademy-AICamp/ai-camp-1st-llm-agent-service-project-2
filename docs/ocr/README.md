# PDF OCR 텍스트 추출 및 법률 문서 구조화 시스템

법률 문서 PDF 파일의 텍스트를 추출하고, 문서 타입에 따라 자동으로 구조화하여 저장하는 지능형 OCR 파이프라인입니다.

---

## 📌 현재 구현 상태 (v2.0)

본 시스템은 **프로덕션 레디 상태**로, 법률 문서 특화 OCR 처리를 완벽히 지원합니다.

### ✅ 구현 완료된 주요 기능

- **PyMuPDF 우선 텍스트 추출**: 빠르고 정확한 네이티브 PDF 텍스트 추출
- **적응형 OCR 전처리**: 문서 품질 기반 선택적 이미지 전처리 (4단계 프리셋)
- **문서 타입별 자동 구조화**: 판결문, 소장, 내용증명, 합의서 등 자동 인식 및 필드 추출
- **FastAPI 기반 REST API**: 프론트엔드 연동 준비 완료
- **OCR 후처리**: 한글 오인식 자동 교정 (11+ 규칙)
- **Tesseract OCR 엔진**: 안정적이고 정확한 한글/영문 텍스트 추출

### 📊 성능 지표

| 지표 | 값 |
|------|-----|
| **처리 시간** | 10-20초/파일 (3페이지 기준) |
| **OCR 신뢰도** | 평균 75.5% (최고 92.1%) |
| **데이터 완전성** | 내용증명 94%, 소장 80% |
| **지원 문서 타입** | 판결문, 소장, 내용증명, 합의서, 일반 문서 |

---

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
# Python 패키지 설치
pip install -r backend/api/requirements_api.txt

# Tesseract OCR 설치 (macOS)
brew install tesseract tesseract-lang

# Tesseract OCR 설치 (Ubuntu/Debian)
sudo apt-get install -y tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng poppler-utils
```

### 2. API 서버 실행

```bash
# 프로젝트 루트에서 실행
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

# API 문서 확인
# http://localhost:8000/docs
```

### 3. 단일 파일 테스트

```bash
# 테스트 스크립트 실행
python scripts/test_single_pdf.py /path/to/your/document.pdf

# 결과는 test_results/ 디렉토리에 JSON으로 저장됨
```

### 4. API 호출 예제

```bash
# cURL로 PDF 처리
curl -X POST "http://localhost:8000/api/v1/process-pdf" \
  -F "file=@your_document.pdf" \
  -F "adaptive=true" \
  -F "apply_postprocessing=true"
```

---

## 🏗️ 시스템 아키텍처

### 핵심 컴포넌트

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (미구현)                         │
│              Streamlit / React 예정                          │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (완료)                          │
│         POST /api/v1/process-pdf                             │
│         POST /api/v1/process-pdf-batch                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                OCR Pipeline (core/ocr/)                      │
├─────────────────┬───────────────────┬───────────────────────┤
│  pdf_extractor  │  ocr_processor    │  document_structurer  │
│  (PyMuPDF)      │  (Tesseract+CV2)  │  (Type Detection)     │
└─────────────────┴───────────────────┴───────────────────────┘
                        │
                        ▼
                  JSON 구조화된 데이터
```

### 데이터 처리 플로우

```
PDF 파일 업로드
    ↓
[1] PyMuPDF 텍스트 추출 시도
    ├─ 성공 (품질 양호) → 추출된 텍스트 사용
    └─ 실패 (품질 불량) → OCR 프로세스 진행
         ↓
[2] 문서 품질 평가 (5가지 메트릭)
    - 선명도 (Sharpness)
    - 노이즈 레벨 (Noise Level)
    - 대비 (Contrast)
    - 밝기 (Brightness)
    - 해상도 (Resolution)
    ↓
[3] 적응형 전처리 선택
    - 점수 80+ → Minimal (최소 전처리)
    - 점수 60-80 → Selective (선택적 전처리)
    - 점수 40-60 → Standard (표준 전처리)
    - 점수 <40 → Aggressive (강력한 전처리)
    ↓
[4] 이미지 전처리 (선택된 프리셋에 따라)
    - Grayscale 변환
    - CLAHE 대비 향상
    - 노이즈 제거 (Non-local Means)
    - 이진화 (Otsu/Adaptive)
    - 샤프닝
    - 기울기 보정 (Deskewing)
    ↓
[5] Tesseract OCR 실행
    - 한글+영문 동시 인식
    - 신뢰도 스코어 측정
    ↓
[6] OCR 후처리 (Post-processing)
    - 한글 오인식 패턴 교정
    - 법률 용어 교정
    ↓
[7] 문서 타입 자동 감지
    - 판결문 / 소장 / 내용증명 / 합의서 / 기타
    ↓
[8] 타입별 구조화 파싱
    - 판결문 → 사건번호, 판결일, 주문, 이유 등
    - 소장 → 원고, 피고, 청구금액, 청구취지 등
    - 내용증명 → 발신자, 수신자, 제목, 날짜, 본문 등
    ↓
JSON 형식 출력 (메타데이터 + 구조화된 데이터)
```

---

## 🧩 핵심 모듈 상세

### 1. PDF 텍스트 추출기 (`core/ocr/pdf_extractor.py`)

**기능**:
- PyMuPDF를 사용한 고속 텍스트 추출
- 추출 품질 자동 평가 및 폴백 로직
- 페이지별 추출률 측정

**주요 메서드**:
```python
extract_text_from_pdf(pdf_path: str) -> dict
    ├─ PyMuPDF 텍스트 추출
    ├─ 품질 평가 (문자 수, 의미있는 텍스트 비율)
    └─ 추출 성공 여부 판단
```

### 2. OCR 프로세서 (`core/ocr/ocr_processor.py`)

**기능**:
- 문서 품질 자동 평가 (5가지 메트릭)
- 적응형 이미지 전처리
- Tesseract OCR 실행 및 신뢰도 측정

**핵심 클래스**:

#### `DocumentQualityAssessor`
품질 평가 메트릭:
- **Sharpness** (선명도): Laplacian variance 계산
- **Noise Level** (노이즈): 로컬 표준편차 측정
- **Contrast** (대비): RMS contrast 계산
- **Brightness** (밝기): 평균 픽셀 값 분석
- **Resolution** (해상도): 메가픽셀 평가

#### `ImagePreprocessor`
전처리 기법:
- Grayscale 변환
- CLAHE (대비 향상)
- Sharpening (샤프닝)
- Denoising (노이즈 제거)
- Binarization (이진화)
- Shadow removal (그림자 제거)
- Deskewing (기울기 보정)
- Upscaling (업스케일링)

#### `AdaptiveOCRProcessor`
적응형 프리셋 선택:
- **Minimal** (80-100점): 기본 전처리만
- **Selective** (60-80점): 선택적 전처리
- **Standard** (40-60점): 표준 전처리 세트
- **Aggressive** (<40점): 모든 전처리 적용

### 3. 문서 구조화기 (`core/ocr/document_structurer.py`)

**기능**:
- 문서 타입 자동 감지
- 타입별 필드 추출
- 구조화된 JSON 데이터 생성

**지원 문서 타입**:

#### 📜 판결문 (Judgment)
추출 필드:
- 사건번호, 판결일, 법원명
- 원고/피고 정보
- 주문, 청구취지, 이유

#### 📋 소장 (Complaint)
추출 필드:
- 원고, 피고 (이름, 주소)
- 청구금액
- 청구취지, 청구원인

#### ✉️ 내용증명 (Notice)
추출 필드:
- 발신자, 수신자
- 제목, 날짜
- 주요 내용

#### 🤝 합의서 (Agreement)
추출 필드:
- 당사자 정보
- 합의 일자
- 합의 내용

### 4. OCR 후처리기 (`core/ocr/postprocessor.py`)

**기능**:
- 한글 OCR 오인식 패턴 자동 교정
- 법률 용어 전용 교정

**교정 규칙 예시**:
```
"정구취지" → "청구취지"
"엉" → "원"
"돼고인" → "피고인"
"관결" → "판결"
등 11+ 규칙
```

---

## 📁 실제 프로젝트 구조

```
/Users/nw_mac/Documents/OCR_Project/
├── backend/
│   └── api/
│       ├── main.py                    # FastAPI 서버 (v2.0.0)
│       └── requirements_api.txt       # API 의존성
│
├── core/
│   └── ocr/                           # ✅ OCR 파이프라인 (완성)
│       ├── __init__.py
│       ├── pdf_extractor.py          # PyMuPDF 텍스트 추출
│       ├── ocr_processor.py          # 적응형 OCR (784줄)
│       ├── document_structurer.py    # 문서 타입 감지 & 구조화
│       └── postprocessor.py          # 오인식 교정
│
├── scripts/
│   ├── test_single_pdf.py            # 단일 PDF 테스트
│   └── process_pdf_directory.py      # 배치 처리 (v2)
│
├── tests/ocr/
│   └── test_data/                    # 테스트용 법률 문서 PDF
│       ├── 내용증명2_보험회사보험금청구_converted.pdf (1.4MB)
│       └── 소장1_일반교통사고손해배상_converted.pdf (1.1MB)
│
├── docs/ocr/                          # ✅ 완벽한 문서화
│   ├── README.md                     # 본 문서
│   ├── SETUP.md                      # 설치 가이드
│   ├── QUICK_START.md                # 빠른 시작
│   ├── API_GUIDE.md                  # API 통합 가이드 (924줄)
│   ├── FRONTEND_EXAMPLES.md          # 프론트엔드 예제
│   └── archive/                      # 테스트 결과 아카이브
│
├── frontend/                          # ❌ 미구현 (예정)
├── notebooks/                         # ❌ 비어있음
├── experiments/                       # 실험 설정 폴더
│
├── .gitignore                        # 포괄적인 gitignore
├── .env.example                      # 환경변수 템플릿 (비어있음)
├── requirements.txt                  # ❌ 비어있음 (통합 필요)
└── README.md                         # 프로젝트 메인 문서
```

---

## 📊 출력 데이터 형식

### JSON 응답 예시

```json
{
  "success": true,
  "processing_time": 12.34,
  "extraction_method": "OCR",
  "document_type": "내용증명",
  "total_pages": 3,
  "metadata": {
    "total_pages": 3,
    "avg_confidence": 75.5,
    "quality_scores": [
      {"page": 1, "score": 68.2, "preset": "selective"},
      {"page": 2, "score": 72.1, "preset": "selective"}
    ]
  },
  "structured_data": {
    "발신자": "홍길동",
    "수신자": "ABC보험회사",
    "제목": "보험금 청구의 건",
    "날짜": "2024년 3월 15일",
    "주요내용": "교통사고 보험금 청구..."
  },
  "full_text": "내용증명\n\n발신: 홍길동\n..."
}
```

---

## 🔗 관련 문서

더 자세한 내용은 다음 문서를 참조하세요:

- **[⚙️ 설치 가이드](SETUP.md)** - 환경 설정 및 의존성 설치
- **[🚀 빠른 시작](QUICK_START.md)** - 5분 안에 테스트 실행
- **[🔌 API 가이드](API_GUIDE.md)** - API 통합 전체 가이드 (924줄)
- **[💻 프론트엔드 예제](FRONTEND_EXAMPLES.md)** - React/Vue.js 통합 예제

---

## 🛠️ 기술 스택

### 구현됨 ✅
- **Python 3.11**
- **FastAPI 0.104.1** - REST API 프레임워크
- **PyMuPDF 1.23.8** - PDF 텍스트 추출
- **Pytesseract 0.3.10** - OCR 엔진
- **OpenCV 4.8.1** - 이미지 전처리
- **Pillow 10.1.0** - 이미지 처리
- **NumPy 1.26.2** - 수치 계산

### 계획됨 📋
- LangChain - LLM 오케스트레이션
- Chroma/FAISS - 벡터 데이터베이스
- PostgreSQL - 관계형 데이터베이스
- Streamlit/React - 프론트엔드
- Docker - 컨테이너화

---

## 🎯 개발 로드맵

### ✅ Phase 1: OCR 파이프라인 (완료)
- [x] PyMuPDF 텍스트 추출
- [x] 적응형 OCR 전처리
- [x] 문서 타입 감지 및 구조화
- [x] FastAPI 백엔드
- [x] 테스트 스크립트
- [x] 완벽한 문서화

### 🔄 Phase 2: 웹 인터페이스 (진행 중)
- [ ] Streamlit 기본 UI
- [ ] PDF 업로드 기능
- [ ] 결과 시각화
- [ ] 의존성 통합 (`requirements.txt`)

### 📋 Phase 3: RAG & LLM (예정)
- [ ] 문서 청킹 모듈
- [ ] 임베딩 생성
- [ ] Vector DB 연동
- [ ] LangChain 통합
- [ ] 문서 QA 기능

### 🚀 Phase 4: 고급 기능 (예정)
- [ ] 문서 비교
- [ ] 유사 문서 검색
- [ ] 트렌드 분석
- [ ] 리스크 평가

---

## 💬 지원 및 문의

- **이슈 리포트**: GitHub Issues
- **문서 버그**: `docs/ocr/` 폴더 내 해당 문서 확인
- **기능 제안**: Pull Request 환영

---

## 📜 라이선스

MIT License

---

**🏛️ 법률 문서 AI 분석 서비스를 위한 OCR 시스템**
