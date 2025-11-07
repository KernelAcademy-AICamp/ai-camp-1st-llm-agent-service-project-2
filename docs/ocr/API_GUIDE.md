# PDF OCR 파이프라인 API 통합 가이드

## 📋 목차
1. [API 서버 설정](#1-api-서버-설정)
2. [프론트엔드 연동](#2-프론트엔드-연동)
3. [API 엔드포인트](#3-api-엔드포인트)
4. [사용 예제](#4-사용-예제)
5. [배포 가이드](#5-배포-가이드)

---

## 1. API 서버 설정

### 1.1 의존성 설치

```bash
# API 서버 의존성 설치
cd api
pip install -r requirements.txt
```

### 1.2 서버 실행

#### 개발 환경 (로컬)
```bash
# 방법 1: Python으로 직접 실행
python api/main.py

# 방법 2: Uvicorn으로 실행
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 서버 실행 확인
# 브라우저에서 http://localhost:8000 접속
# Swagger UI: http://localhost:8000/docs
```

#### 프로덕션 환경
```bash
# Workers를 사용한 프로덕션 실행
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Docker를 사용한 실행 (Dockerfile 포함)
docker-compose up -d
```

### 1.3 서버 구조

```
프로젝트루트/
├── api/
│   ├── main.py              # FastAPI 앱 메인 파일
│   └── requirements.txt     # API 의존성
├── scripts/
│   ├── pdf_processing_pipeline.py
│   ├── structure_by_doctype.py
│   ├── ocr_with_preprocessing.py
│   └── ocr_postprocessing.py
└── test_results/            # 테스트 결과 저장
```

---

## 2. 프론트엔드 연동

### 2.1 React 예제

```jsx
import React, { useState } from 'react';
import axios from 'axios';

function PDFUploader() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 파일 선택 핸들러
  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];

    // PDF 파일인지 검증
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError(null);
    } else {
      setError('PDF 파일만 업로드 가능합니다.');
      setFile(null);
    }
  };

  // 파일 업로드 및 처리
  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!file) {
      setError('파일을 선택해주세요.');
      return;
    }

    setLoading(true);
    setError(null);

    // FormData 생성
    const formData = new FormData();
    formData.append('file', file);

    try {
      // API 호출
      const response = await axios.post(
        'http://localhost:8000/api/v1/process-pdf',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          params: {
            adaptive: true,              // 적응형 전처리 활성화
            apply_postprocessing: true   // OCR 후처리 활성화
          },
          timeout: 60000  // 60초 타임아웃
        }
      );

      // 결과 처리
      if (response.data.success) {
        setResult(response.data.data);
        console.log('처리 결과:', response.data.data);
      } else {
        setError(response.data.error || '처리 실패');
      }
    } catch (err) {
      console.error('업로드 에러:', err);
      setError(
        err.response?.data?.detail ||
        err.message ||
        '서버와 통신 중 오류가 발생했습니다.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pdf-uploader">
      <h2>PDF 문서 업로드</h2>

      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept="application/pdf"
          onChange={handleFileChange}
          disabled={loading}
        />

        <button type="submit" disabled={!file || loading}>
          {loading ? '처리 중...' : '업로드'}
        </button>
      </form>

      {/* 로딩 상태 */}
      {loading && (
        <div className="loading">
          <p>PDF 파일을 처리하고 있습니다...</p>
          <div className="spinner"></div>
        </div>
      )}

      {/* 에러 표시 */}
      {error && (
        <div className="error">
          <p>❌ {error}</p>
        </div>
      )}

      {/* 결과 표시 */}
      {result && (
        <div className="result">
          <h3>✅ 처리 완료</h3>

          <div className="metadata">
            <p><strong>문서 타입:</strong> {result.데이터타입}</p>
            <p><strong>추출 방법:</strong> {result.추출방법}</p>
            <p><strong>처리 시각:</strong> {result.처리시각}</p>
          </div>

          {/* 내용증명인 경우 */}
          {result.데이터타입 === '내용증명' && (
            <div className="content">
              <h4>내용증명 정보</h4>
              <p><strong>제목:</strong> {result.제목}</p>
              <p><strong>수신인:</strong> {result.수신인}</p>
              <p><strong>발신인:</strong> {result.발신인}</p>
              <p><strong>발신일자:</strong> {result.발신일자}</p>
              <div>
                <strong>주요내용:</strong>
                <pre>{result.주요내용}</pre>
              </div>
            </div>
          )}

          {/* 소장인 경우 */}
          {result.데이터타입 === '소장' && (
            <div className="content">
              <h4>소장 정보</h4>
              <p><strong>사건명:</strong> {result.사건명}</p>
              <p><strong>법원:</strong> {result.법원}</p>
              <p><strong>원고:</strong> {result.원고}</p>
              <p><strong>피고:</strong> {result.피고}</p>
              <p><strong>청구금액:</strong> {result.청구금액}</p>
              <div>
                <strong>청구취지:</strong>
                <pre>{result.청구취지}</pre>
              </div>
              <div>
                <strong>청구원인:</strong>
                <pre>{result.청구원인}</pre>
              </div>
            </div>
          )}

          {/* OCR 메타데이터 */}
          {result.추출메타데이터 && (
            <div className="metadata">
              <h4>추출 정보</h4>
              <p><strong>페이지 수:</strong> {result.추출메타데이터.page_count}</p>
              <p><strong>글자 수:</strong> {result.추출메타데이터.char_count}자</p>
              {result.추출메타데이터.avg_confidence && (
                <p><strong>OCR 신뢰도:</strong> {result.추출메타데이터.avg_confidence.toFixed(1)}%</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default PDFUploader;
```

### 2.2 Vue.js 예제

```vue
<template>
  <div class="pdf-uploader">
    <h2>PDF 문서 업로드</h2>

    <form @submit.prevent="handleSubmit">
      <input
        type="file"
        accept="application/pdf"
        @change="handleFileChange"
        :disabled="loading"
      />

      <button type="submit" :disabled="!file || loading">
        {{ loading ? '처리 중...' : '업로드' }}
      </button>
    </form>

    <!-- 로딩 상태 -->
    <div v-if="loading" class="loading">
      <p>PDF 파일을 처리하고 있습니다...</p>
    </div>

    <!-- 에러 표시 -->
    <div v-if="error" class="error">
      <p>❌ {{ error }}</p>
    </div>

    <!-- 결과 표시 -->
    <div v-if="result" class="result">
      <h3>✅ 처리 완료</h3>

      <div class="metadata">
        <p><strong>문서 타입:</strong> {{ result.데이터타입 }}</p>
        <p><strong>추출 방법:</strong> {{ result.추출방법 }}</p>
      </div>

      <!-- 내용증명인 경우 -->
      <div v-if="result.데이터타입 === '내용증명'" class="content">
        <h4>내용증명 정보</h4>
        <p><strong>발신인:</strong> {{ result.발신인 }}</p>
        <p><strong>수신인:</strong> {{ result.수신인 }}</p>
        <pre>{{ result.주요내용 }}</pre>
      </div>

      <!-- 소장인 경우 -->
      <div v-if="result.데이터타입 === '소장'" class="content">
        <h4>소장 정보</h4>
        <p><strong>원고:</strong> {{ result.원고 }}</p>
        <p><strong>피고:</strong> {{ result.피고 }}</p>
        <p><strong>청구금액:</strong> {{ result.청구금액 }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'PDFUploader',
  data() {
    return {
      file: null,
      result: null,
      loading: false,
      error: null
    };
  },
  methods: {
    handleFileChange(event) {
      const selectedFile = event.target.files[0];

      if (selectedFile && selectedFile.type === 'application/pdf') {
        this.file = selectedFile;
        this.error = null;
      } else {
        this.error = 'PDF 파일만 업로드 가능합니다.';
        this.file = null;
      }
    },

    async handleSubmit() {
      if (!this.file) {
        this.error = '파일을 선택해주세요.';
        return;
      }

      this.loading = true;
      this.error = null;

      const formData = new FormData();
      formData.append('file', this.file);

      try {
        const response = await axios.post(
          'http://localhost:8000/api/v1/process-pdf',
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
            params: {
              adaptive: true,
              apply_postprocessing: true
            },
            timeout: 60000
          }
        );

        if (response.data.success) {
          this.result = response.data.data;
        } else {
          this.error = response.data.error || '처리 실패';
        }
      } catch (err) {
        this.error = err.response?.data?.detail || err.message;
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>
```

### 2.3 JavaScript (Vanilla) 예제

```javascript
// HTML
/*
<input type="file" id="pdfInput" accept="application/pdf">
<button id="uploadBtn">업로드</button>
<div id="result"></div>
*/

const pdfInput = document.getElementById('pdfInput');
const uploadBtn = document.getElementById('uploadBtn');
const resultDiv = document.getElementById('result');

uploadBtn.addEventListener('click', async () => {
  const file = pdfInput.files[0];

  if (!file) {
    alert('파일을 선택해주세요.');
    return;
  }

  if (file.type !== 'application/pdf') {
    alert('PDF 파일만 업로드 가능합니다.');
    return;
  }

  // FormData 생성
  const formData = new FormData();
  formData.append('file', file);

  // 로딩 표시
  resultDiv.innerHTML = '<p>처리 중...</p>';
  uploadBtn.disabled = true;

  try {
    // API 호출
    const response = await fetch(
      'http://localhost:8000/api/v1/process-pdf?adaptive=true&apply_postprocessing=true',
      {
        method: 'POST',
        body: formData
      }
    );

    const data = await response.json();

    if (data.success) {
      // 결과 표시
      displayResult(data.data);
    } else {
      resultDiv.innerHTML = `<p class="error">❌ ${data.error}</p>`;
    }
  } catch (error) {
    resultDiv.innerHTML = `<p class="error">❌ ${error.message}</p>`;
  } finally {
    uploadBtn.disabled = false;
  }
});

function displayResult(result) {
  let html = `
    <h3>✅ 처리 완료</h3>
    <p><strong>문서 타입:</strong> ${result.데이터타입}</p>
    <p><strong>추출 방법:</strong> ${result.추출방법}</p>
  `;

  if (result.데이터타입 === '내용증명') {
    html += `
      <h4>내용증명 정보</h4>
      <p><strong>발신인:</strong> ${result.발신인}</p>
      <p><strong>수신인:</strong> ${result.수신인}</p>
      <p><strong>발신일자:</strong> ${result.발신일자}</p>
      <pre>${result.주요내용}</pre>
    `;
  } else if (result.데이터타입 === '소장') {
    html += `
      <h4>소장 정보</h4>
      <p><strong>원고:</strong> ${result.원고}</p>
      <p><strong>피고:</strong> ${result.피고}</p>
      <p><strong>청구금액:</strong> ${result.청구금액}</p>
    `;
  }

  resultDiv.innerHTML = html;
}
```

---

## 3. API 엔드포인트

### 3.1 단일 PDF 처리

**POST** `/api/v1/process-pdf`

#### Request
```bash
curl -X POST "http://localhost:8000/api/v1/process-pdf" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@소장1_일반교통사고손해배상_converted.pdf" \
  -F "adaptive=true" \
  -F "apply_postprocessing=true"
```

#### Response (성공)
```json
{
  "success": true,
  "message": "PDF 처리가 성공적으로 완료되었습니다.",
  "data": {
    "데이터타입": "소장",
    "파일명": "소장1_일반교통사고손해배상_converted.pdf",
    "사건명": "손해배상(자)",
    "법원": "",
    "원고": "김부상",
    "피고": "이가해",
    "청구금액": "35,800,000원",
    "청구취지": "1. 피고는 원고에게 금 35,800,000 원...",
    "청구원인": "1. 사고의 발생\n피고는 2025 년 6 월 15 일...",
    "추출방법": "ocr_v2",
    "추출메타데이터": {
      "extraction_method": "ocr_v2",
      "char_count": 1108,
      "page_count": 3,
      "avg_confidence": 60.02631766381766,
      "preprocessing": "adaptive_selective"
    },
    "처리시각": "2025-11-06T18:30:00.123456",
    "원본파일명": "소장1_일반교통사고손해배상_converted.pdf"
  },
  "error": null
}
```

#### Response (실패)
```json
{
  "success": false,
  "message": "PDF 처리 중 오류가 발생했습니다.",
  "data": null,
  "error": "파일을 읽을 수 없습니다."
}
```

### 3.2 다중 PDF 처리 (배치)

**POST** `/api/v1/process-pdf-batch`

#### Request
```bash
curl -X POST "http://localhost:8000/api/v1/process-pdf-batch" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@file1.pdf" \
  -F "files=@file2.pdf" \
  -F "files=@file3.pdf"
```

#### Response
```json
{
  "total": 3,
  "success_count": 3,
  "results": [
    {
      "filename": "file1.pdf",
      "success": true,
      "data": { ... },
      "error": null
    },
    {
      "filename": "file2.pdf",
      "success": true,
      "data": { ... },
      "error": null
    },
    {
      "filename": "file3.pdf",
      "success": true,
      "data": { ... },
      "error": null
    }
  ]
}
```

### 3.3 헬스체크

**GET** `/health`

#### Response
```json
{
  "status": "healthy",
  "timestamp": "2025-11-06T18:30:00.123456",
  "version": "2.0.0"
}
```

### 3.4 API 통계

**GET** `/api/v1/stats`

#### Response
```json
{
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
```

---

## 4. 사용 예제

### 4.1 Python (requests 라이브러리)

```python
import requests

# 단일 파일 업로드
def upload_pdf(file_path):
    url = "http://localhost:8000/api/v1/process-pdf"

    with open(file_path, 'rb') as f:
        files = {'file': f}
        params = {
            'adaptive': True,
            'apply_postprocessing': True
        }

        response = requests.post(url, files=files, params=params)

    return response.json()

# 사용 예제
result = upload_pdf("소장1_일반교통사고손해배상_converted.pdf")

if result['success']:
    print("✅ 처리 완료")
    print(f"문서 타입: {result['data']['데이터타입']}")
    print(f"추출 방법: {result['data']['추출방법']}")
else:
    print(f"❌ 처리 실패: {result['error']}")
```

### 4.2 Node.js (axios)

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

async function uploadPDF(filePath) {
  const formData = new FormData();
  formData.append('file', fs.createReadStream(filePath));

  try {
    const response = await axios.post(
      'http://localhost:8000/api/v1/process-pdf',
      formData,
      {
        headers: formData.getHeaders(),
        params: {
          adaptive: true,
          apply_postprocessing: true
        }
      }
    );

    return response.data;
  } catch (error) {
    console.error('업로드 에러:', error.response?.data || error.message);
    throw error;
  }
}

// 사용 예제
uploadPDF('./소장1_일반교통사고손해배상_converted.pdf')
  .then(result => {
    if (result.success) {
      console.log('✅ 처리 완료');
      console.log('문서 타입:', result.data.데이터타입);
    } else {
      console.log('❌ 처리 실패:', result.error);
    }
  });
```

---

## 5. 배포 가이드

### 5.1 Docker를 사용한 배포

#### Dockerfile
```dockerfile
FROM python:3.11-slim

# Tesseract OCR 설치
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-kor \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 설치
COPY api/requirements.txt .
COPY OCR_requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -r OCR_requirements.txt

# 앱 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 서버 실행
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  pdf-ocr-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./scripts:/app/scripts
      - ./api:/app/api
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
```

#### 실행
```bash
# 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

### 5.2 시스템 서비스로 배포 (Linux)

#### systemd 서비스 파일
```ini
# /etc/systemd/system/pdf-ocr-api.service
[Unit]
Description=PDF OCR API Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 실행
```bash
# 서비스 등록
sudo systemctl daemon-reload
sudo systemctl enable pdf-ocr-api

# 서비스 시작
sudo systemctl start pdf-ocr-api

# 상태 확인
sudo systemctl status pdf-ocr-api

# 로그 확인
sudo journalctl -u pdf-ocr-api -f
```

### 5.3 Nginx 리버스 프록시 설정

```nginx
# /etc/nginx/sites-available/pdf-ocr-api
server {
    listen 80;
    server_name api.yourdomain.com;

    client_max_body_size 50M;  # 최대 파일 크기

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 타임아웃 설정 (OCR 처리 시간 고려)
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
    }
}
```

---

## 6. 트러블슈팅

### 6.1 CORS 에러
**증상**: 프론트엔드에서 API 호출 시 CORS 에러 발생

**해결**:
```python
# api/main.py의 CORS 설정에서 특정 도메인만 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # React 개발 서버
        "https://yourdomain.com"      # 프로덕션 도메인
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 6.2 파일 크기 제한
**증상**: 큰 PDF 파일 업로드 실패

**해결**:
```python
# api/main.py에 파일 크기 제한 추가
from fastapi import FastAPI, File, UploadFile, HTTPException
from starlette.requests import Request

@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    max_size = 50 * 1024 * 1024  # 50MB
    content_length = request.headers.get("content-length")

    if content_length and int(content_length) > max_size:
        raise HTTPException(status_code=413, detail="파일 크기가 너무 큽니다.")

    return await call_next(request)
```

### 6.3 타임아웃 문제
**증상**: OCR 처리 중 타임아웃 발생

**해결**:
- 프론트엔드: axios timeout 증가 (60초 → 120초)
- Nginx: proxy_read_timeout 증가
- 서버: uvicorn timeout 설정

---

## 7. 보안 고려사항

### 7.1 파일 검증
```python
# 파일 타입 검증 강화
import magic

def validate_pdf(file_content: bytes) -> bool:
    mime = magic.from_buffer(file_content, mime=True)
    return mime == 'application/pdf'
```

### 7.2 API 키 인증
```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "your-secret-api-key":
        raise HTTPException(status_code=401, detail="Invalid API Key")
```

### 7.3 Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/v1/process-pdf")
@limiter.limit("10/minute")  # 분당 10회 제한
async def process_pdf(...):
    ...
```

---

## 8. 모니터링

### 8.1 로깅
```python
import logging
from datetime import datetime

# 파일 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/api_{datetime.now():%Y%m%d}.log'),
        logging.StreamHandler()
    ]
)
```

### 8.2 성능 모니터링
```python
import time

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"Request processed in {process_time:.2f}s")
    return response
```

---

## 📞 지원

- API 문서: `http://localhost:8000/docs` (Swagger UI)
- ReDoc: `http://localhost:8000/redoc`
- GitHub Issues: [프로젝트 저장소]
