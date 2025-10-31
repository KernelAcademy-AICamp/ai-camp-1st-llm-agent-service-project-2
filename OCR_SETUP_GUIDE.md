# 설치 및 실행 가이드

## 1. 가상환경 활성화

```bash
source .venv/bin/activate  # 이미 생성되어 있음
# Windows: .venv\Scripts\activate
```

## 2. 의존성 설치

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Tesseract OCR 설치

### macOS
```bash
brew install tesseract tesseract-lang poppler
```

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng poppler-utils
```

## 4. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# 암호화 키 생성
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

생성된 키를 `.env` 파일의 `ENCRYPTION_KEY`에 설정

## 5. 하드웨어 테스트

```bash
python test_hardware.py
```

이 명령어로 시스템의 GPU/CPU 환경과 자동 선택된 OCR 엔진을 확인할 수 있습니다.

## 6. 데이터베이스 설정 (PostgreSQL)

```bash
# PostgreSQL 접속
sudo -u postgres psql

# 데이터베이스 생성
CREATE DATABASE ocrdb;
CREATE USER ocruser WITH PASSWORD 'ocrpassword';
GRANT ALL PRIVILEGES ON DATABASE ocrdb TO ocruser;
\c ocrdb
GRANT ALL ON SCHEMA public TO ocruser;
\q
```

## 7. Redis & MinIO 실행 (Docker)

```bash
# Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# MinIO
docker run -d --name minio -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"
```

## 8. FastAPI 서버 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 9. API 테스트

브라우저에서 다음 URL 접속:

- API 문서: http://localhost:8000/docs
- 헬스 체크: http://localhost:8000/health
- 하드웨어 정보: http://localhost:8000/hardware-info
- OCR 엔진 정보: http://localhost:8000/ocr-engine-info

## 문제 해결

### Tesseract를 찾을 수 없는 경우

```python
# app/services/ocr_engines.py에서 tesseract 경로 설정
import pytesseract
pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'  # macOS
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows
```

### PostgreSQL 연결 오류

```bash
# PostgreSQL 서비스 시작
sudo systemctl start postgresql

# 연결 테스트
psql -h localhost -U ocruser -d ocrdb
```

## GPU 지원 (선택사항)

### NVIDIA GPU (CUDA)

```bash
# PyTorch CUDA 설치
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# OCR 엔진 설치
pip install easyocr paddlepaddle-gpu paddleocr
```

### Apple Silicon (MPS)

```bash
# PyTorch MPS 설치
pip install torch torchvision

# EasyOCR 설치
pip install easyocr
```

시스템이 자동으로 사용 가능한 GPU를 감지하고 최적의 엔진을 선택합니다!
