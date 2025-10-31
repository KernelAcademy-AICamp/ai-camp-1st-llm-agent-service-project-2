# PDF OCR 텍스트 추출 및 법률 데이터 구조화 시스템

판례 및 계약서 PDF 파일을 OCR 엔진으로 텍스트를 추출하고, 기존 법률 데이터 사이트와 동일한 CSV/JSON 형식으로 구조화하여 저장하는 시스템입니다.

## 핵심 기능

- **멀티 OCR 엔진 지원**: Tesseract (CPU), EasyOCR (GPU), PaddleOCR (GPU)
- **하드웨어 자동 감지**: CUDA, Apple Silicon (MPS), AMD ROCm, CPU
- **법률 데이터 형식 호환**: CSV (구조화 데이터) + JSON (AI 라벨)
- **데이터베이스 분리**: 전체DB (공개) / 사용자DB (암호화)
- **비동기 처리**: Celery + Redis를 이용한 백그라운드 OCR 작업
- **REST API**: FastAPI 기반의 완전한 API 시스템

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                          │
│     파일 업로드 UI  |  문서 관리  |  검색 인터페이스        │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                API Gateway (FastAPI)                         │
│          인증/인가 (JWT)  |  Rate Limiting                   │
└───┬──────────────┬──────────────┬──────────────────────────┘
    │              │              │
    ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐
│ Upload   │  │ OCR      │  │ Document     │
│ Service  │  │ Service  │  │ Management   │
└────┬─────┘  └────┬─────┘  └──────┬───────┘
     │             │                │
     │             ▼                │
     │      ┌─────────────┐         │
     │      │ Celery      │         │
     │      │ Worker      │         │
     │      └──────┬──────┘         │
     │             │                │
     ▼             ▼                ▼
┌───────────────────────────────────────────────────────────┐
│                    Storage Layer                          │
├─────────────────┬──────────────────┬──────────────────────┤
│ PostgreSQL DB   │  MinIO/S3        │  Redis Cache         │
│ (전체DB+사용자DB) │  (파일 저장소)   │  (세션/큐 데이터)     │
└─────────────────┴──────────────────┴──────────────────────┘
```

## 빠른 시작

> **📖 상세 문서**:
> - [Tesseract 설치 가이드](TESSERACT_INSTALLATION.md)
> - [테스트 결과](TESSERACT_TEST_RESULTS.md)
> - [현재 개발 상태](CURRENT_STATUS.md)

### 1. 필수 요구사항

- Python 3.10 이상
- PostgreSQL 15 이상
- Redis 7 이상
- Tesseract OCR 4.x
- MinIO 또는 AWS S3

### 2. 설치

```bash
# 1. 저장소 클론 및 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. Tesseract OCR 설치 (Ubuntu/Debian)
sudo apt-get install -y tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng
sudo apt-get install -y poppler-utils

# macOS
brew install tesseract tesseract-lang poppler
```

### 3. 환경 설정

`.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일 편집하여 필요한 값 설정:

```env
# Application
APP_NAME=PDF OCR System
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql+asyncpg://ocruser:ocrpassword@localhost:5432/ocrdb

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage (MinIO)
STORAGE_ENDPOINT=localhost:9000
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin

# Encryption
ENCRYPTION_KEY=your-fernet-key-here

# OCR Engine (auto, tesseract, easyocr, paddleocr)
OCR_ENGINE=auto
```

암호화 키 생성:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. 데이터베이스 초기화

```bash
# PostgreSQL 데이터베이스 생성
sudo -u postgres psql
CREATE DATABASE ocrdb;
CREATE USER ocruser WITH PASSWORD 'ocrpassword';
GRANT ALL PRIVILEGES ON DATABASE ocrdb TO ocruser;
\q

# Alembic 마이그레이션 (선택사항)
alembic upgrade head
```

### 5. 서비스 실행

```bash
# Terminal 1: FastAPI 서버
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Redis (Docker)
docker run -d -p 6379:6379 redis:7-alpine

# Terminal 3: MinIO (Docker)
docker run -d -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"
```

### 6. API 테스트

```bash
# 헬스 체크
curl http://localhost:8000/health

# 하드웨어 정보 확인
curl http://localhost:8000/hardware-info

# OCR 엔진 정보 확인
curl http://localhost:8000/ocr-engine-info
```

API 문서: http://localhost:8000/docs

## 프로젝트 구조

```
.
├── app/
│   ├── api/                    # API 엔드포인트
│   │   └── v1/
│   │       └── endpoints/
│   ├── core/                   # 핵심 모듈
│   │   ├── config.py          # 환경 설정
│   │   ├── database.py        # DB 연결
│   │   ├── security.py        # 인증/암호화
│   │   └── hardware_detector.py # GPU/CPU 감지
│   ├── models/                 # 데이터베이스 모델
│   │   ├── user.py
│   │   └── document.py
│   ├── services/              # 비즈니스 로직
│   │   ├── ocr_engine_selector.py
│   │   ├── ocr_engines.py
│   │   ├── multi_engine_ocr_service.py
│   │   └── storage_service.py
│   ├── workers/               # Celery Workers
│   ├── schemas/               # Pydantic 스키마
│   ├── utils/                 # 유틸리티
│   └── main.py               # FastAPI 앱
├── .claude/                   # 설계 문서
│   ├── README.md
│   ├── pdf_ocr_system_architecture.md
│   ├── OCR_DATA_STRUCTURE_AND_GPU_DESIGN.md
│   └── QUICKSTART_GUIDE.md
├── requirements.txt
├── .env.example
└── README.md
```

## GPU/CPU 자동 감지

시스템은 하드웨어 환경에 따라 자동으로 최적의 OCR 엔진을 선택합니다:

| 하드웨어 | OCR 엔진 | 비고 |
|----------|----------|------|
| **NVIDIA GPU (CUDA)** | PaddleOCR / EasyOCR | 가장 빠르고 정확 |
| **Apple Silicon (MPS)** | EasyOCR | M1/M2/M3 Mac |
| **AMD GPU (ROCm)** | PaddleOCR / EasyOCR | Linux only |
| **CPU** | Tesseract | 가장 안정적 |

**선택 로직**:
- GPU 있고 VRAM ≥ 4GB → **PaddleOCR** (최고 정확도)
- GPU 있고 VRAM < 4GB → **EasyOCR** (메모리 효율)
- CPU만 사용 가능 → **Tesseract** (가장 안정적)

## 데이터 형식

### CSV 형식 (구조화 데이터)

#### 판례
```csv
판례일련번호,구분,문장번호,내용
64524,판례내용,1,【피 고 인】
64524,판례내용,2,【항 소 인】 피고인
```

#### 해석례
```csv
해석례일련번호,구분,문장번호,내용
312586,질의요지,1,"「자동차손해배상보장법」..."
312586,회답,2,...
```

### JSON 형식 (AI 라벨)

```json
{
    "info": {
        "lawClass": "02",
        "DocuType": "03",
        "interpreId": "312864",
        "agenda": "공중위생관리법제11조(적용법률)관련",
        "interpreDate": "2005.11.25"
    },
    "label": {
        "instruction": "질의에 대한 응답은 15어절 이상...",
        "input": "경찰관서에서 숙박업자가...",
        "output": "경찰관서에서 숙박업자의...",
        "originwordCnt": "62",
        "labelwordCnt": "53"
    }
}
```

## 개발 로드맵

### ✅ 완료된 기능
- [x] 프로젝트 구조 설정
- [x] 하드웨어 자동 감지 시스템
- [x] 멀티 OCR 엔진 지원 (프레임워크)
- [x] Tesseract OCR 설치 및 통합 완료
- [x] 데이터베이스 모델 정의
- [x] 파일 저장소 서비스
- [x] 환경 설정 및 보안

### 🔄 진행 중
- [ ] 파일 업로드 API
- [ ] OCR 처리 파이프라인
- [ ] Celery Worker 구현
- [ ] CSV/JSON 출력 포맷터

### 📋 예정
- [ ] 문서 관리 API (CRUD)
- [ ] 검색 기능
- [ ] 사용자 인증/인가
- [ ] 프론트엔드 UI
- [ ] 테스트 코드
- [ ] Docker Compose 배포

## 보안

- **JWT 기반 인증**: 24시간 유효 토큰
- **파일 암호화**: AES-256-GCM (사용자DB)
- **Rate Limiting**: 시간당 10개 업로드 제한
- **감사 로그**: 모든 작업 추적
- **파일 검증**: 크기, 확장자, MIME 타입 검증

## 성능 최적화

- **병렬 처리**: 멀티프로세싱으로 페이지별 병렬 OCR
- **GPU 가속**: CUDA/MPS 자동 활용
- **Redis 캐싱**: 메타데이터, OCR 상태, 검색 결과
- **DB 인덱싱**: 복합 인덱스로 쿼리 최적화

## 라이선스

MIT License

## 문의

프로젝트에 대한 질문이나 제안사항이 있으시면 Issue를 등록해주세요.

---

**Made with ❤️ for AI Legal Document Analysis Service**
