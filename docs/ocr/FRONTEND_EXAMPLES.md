# 프론트엔드 연동 예제 모음

## 목차
1. [React + TypeScript](#1-react--typescript)
2. [Next.js](#2-nextjs)
3. [Vue 3 + Composition API](#3-vue-3--composition-api)
4. [Angular](#4-angular)
5. [Svelte](#5-svelte)

---

## 1. React + TypeScript

### 설치
```bash
npm install axios
```

### 타입 정의
```typescript
// types/pdf.types.ts
export interface PDFProcessResult {
  success: boolean;
  message: string;
  data?: PDFData;
  error?: string;
}

export interface PDFData {
  데이터타입: '소장' | '내용증명' | '판결문' | '합의서' | '기타';
  파일명: string;
  추출방법: 'pymupdf' | 'ocr_v2';
  추출메타데이터: MetaData;
  처리시각: string;
  원본파일명: string;

  // 소장 필드
  사건명?: string;
  법원?: string;
  원고?: string;
  피고?: string;
  청구금액?: string;
  청구취지?: string;
  청구원인?: string;

  // 내용증명 필드
  제목?: string;
  수신인?: string;
  발신인?: string;
  발신일자?: string;
  주요내용?: string;
}

export interface MetaData {
  extraction_method: string;
  char_count: number;
  page_count: number;
  avg_confidence?: number;
  extraction_rate?: number;
  preprocessing?: string;
  preset_usage?: Record<string, number>;
  quality_info?: string;
}
```

### 컴포넌트
```typescript
// components/PDFUploader.tsx
import React, { useState, useCallback } from 'react';
import axios, { AxiosError } from 'axios';
import { PDFProcessResult, PDFData } from '../types/pdf.types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const PDFUploader: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<PDFData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];

    if (selectedFile) {
      if (selectedFile.type === 'application/pdf') {
        setFile(selectedFile);
        setError(null);
        setResult(null);
      } else {
        setError('PDF 파일만 업로드 가능합니다.');
        setFile(null);
      }
    }
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!file) {
      setError('파일을 선택해주세요.');
      return;
    }

    setLoading(true);
    setError(null);
    setProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post<PDFProcessResult>(
        `${API_BASE_URL}/api/v1/process-pdf`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          params: {
            adaptive: true,
            apply_postprocessing: true,
          },
          timeout: 120000,
          onUploadProgress: (progressEvent) => {
            const percentCompleted = progressEvent.total
              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
              : 0;
            setProgress(percentCompleted);
          },
        }
      );

      if (response.data.success && response.data.data) {
        setResult(response.data.data);
      } else {
        setError(response.data.error || '처리 실패');
      }
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      setError(
        axiosError.response?.data?.detail ||
        axiosError.message ||
        '서버와 통신 중 오류가 발생했습니다.'
      );
    } finally {
      setLoading(false);
      setProgress(0);
    }
  };

  const handleReset = () => {
    setFile(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="pdf-uploader">
      <h2>PDF 문서 업로드</h2>

      <form onSubmit={handleSubmit}>
        <div className="file-input-wrapper">
          <input
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
            disabled={loading}
            id="pdf-input"
          />
          <label htmlFor="pdf-input" className="file-label">
            {file ? file.name : '파일 선택'}
          </label>
        </div>

        <button type="submit" disabled={!file || loading}>
          {loading ? '처리 중...' : '업로드'}
        </button>

        {file && !loading && (
          <button type="button" onClick={handleReset} className="reset-btn">
            초기화
          </button>
        )}
      </form>

      {loading && (
        <div className="loading">
          <p>PDF 파일을 처리하고 있습니다...</p>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <p>{progress}% 완료</p>
        </div>
      )}

      {error && (
        <div className="error">
          <p>❌ {error}</p>
        </div>
      )}

      {result && <ResultDisplay result={result} />}
    </div>
  );
};

// 결과 표시 컴포넌트
interface ResultDisplayProps {
  result: PDFData;
}

const ResultDisplay: React.FC<ResultDisplayProps> = ({ result }) => {
  return (
    <div className="result">
      <h3>✅ 처리 완료</h3>

      <div className="metadata">
        <p><strong>문서 타입:</strong> {result.데이터타입}</p>
        <p><strong>추출 방법:</strong> {result.추출방법.toUpperCase()}</p>
        <p><strong>처리 시각:</strong> {new Date(result.처리시각).toLocaleString('ko-KR')}</p>
      </div>

      {result.데이터타입 === '내용증명' && (
        <NoticeContent data={result} />
      )}

      {result.데이터타입 === '소장' && (
        <ComplaintContent data={result} />
      )}

      <MetaDataDisplay metadata={result.추출메타데이터} />
    </div>
  );
};

// 내용증명 표시
const NoticeContent: React.FC<{ data: PDFData }> = ({ data }) => (
  <div className="content notice-content">
    <h4>내용증명 정보</h4>
    <div className="field">
      <label>제목:</label>
      <span>{data.제목}</span>
    </div>
    <div className="field">
      <label>수신인:</label>
      <span>{data.수신인 || '(없음)'}</span>
    </div>
    <div className="field">
      <label>발신인:</label>
      <span>{data.발신인}</span>
    </div>
    <div className="field">
      <label>발신일자:</label>
      <span>{data.발신일자}</span>
    </div>
    <div className="field main-content">
      <label>주요내용:</label>
      <pre>{data.주요내용}</pre>
    </div>
  </div>
);

// 소장 표시
const ComplaintContent: React.FC<{ data: PDFData }> = ({ data }) => (
  <div className="content complaint-content">
    <h4>소장 정보</h4>
    <div className="field">
      <label>사건명:</label>
      <span>{data.사건명}</span>
    </div>
    {data.법원 && (
      <div className="field">
        <label>법원:</label>
        <span>{data.법원}</span>
      </div>
    )}
    <div className="field">
      <label>원고:</label>
      <span>{data.원고}</span>
    </div>
    <div className="field">
      <label>피고:</label>
      <span>{data.피고}</span>
    </div>
    <div className="field amount">
      <label>청구금액:</label>
      <span className="highlight">{data.청구금액}</span>
    </div>
    <div className="field">
      <label>청구취지:</label>
      <pre>{data.청구취지}</pre>
    </div>
    <div className="field">
      <label>청구원인:</label>
      <pre>{data.청구원인}</pre>
    </div>
  </div>
);

// 메타데이터 표시
const MetaDataDisplay: React.FC<{ metadata: MetaData }> = ({ metadata }) => (
  <div className="metadata-detail">
    <h4>추출 정보</h4>
    <div className="stats">
      <div className="stat-item">
        <span className="label">페이지 수</span>
        <span className="value">{metadata.page_count}</span>
      </div>
      <div className="stat-item">
        <span className="label">글자 수</span>
        <span className="value">{metadata.char_count.toLocaleString()}자</span>
      </div>
      {metadata.avg_confidence && (
        <div className="stat-item">
          <span className="label">OCR 신뢰도</span>
          <span className={`value ${metadata.avg_confidence >= 90 ? 'high' : metadata.avg_confidence >= 70 ? 'medium' : 'low'}`}>
            {metadata.avg_confidence.toFixed(1)}%
          </span>
        </div>
      )}
      {metadata.extraction_rate && (
        <div className="stat-item">
          <span className="label">추출률</span>
          <span className="value">{metadata.extraction_rate.toFixed(1)}%</span>
        </div>
      )}
    </div>
  </div>
);

export default PDFUploader;
```

### 스타일링 (CSS)
```css
/* styles/PDFUploader.css */
.pdf-uploader {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.file-input-wrapper {
  margin: 20px 0;
}

input[type="file"] {
  display: none;
}

.file-label {
  display: inline-block;
  padding: 10px 20px;
  background-color: #f0f0f0;
  border: 2px dashed #ccc;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.file-label:hover {
  background-color: #e0e0e0;
  border-color: #999;
}

button {
  padding: 10px 20px;
  margin: 0 10px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

button:hover:not(:disabled) {
  background-color: #0056b3;
}

button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.reset-btn {
  background-color: #6c757d;
}

.reset-btn:hover {
  background-color: #545b62;
}

.loading {
  margin: 20px 0;
  text-align: center;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background-color: #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  margin: 10px 0;
}

.progress-fill {
  height: 100%;
  background-color: #007bff;
  transition: width 0.3s ease;
}

.error {
  padding: 15px;
  margin: 20px 0;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  color: #721c24;
}

.result {
  margin-top: 30px;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.metadata, .metadata-detail {
  margin: 20px 0;
  padding: 15px;
  background-color: white;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.content {
  margin: 20px 0;
  padding: 20px;
  background-color: white;
  border-radius: 4px;
}

.field {
  margin: 15px 0;
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 10px;
}

.field label {
  font-weight: bold;
  color: #333;
}

.field.amount .value {
  font-size: 1.2em;
  color: #007bff;
  font-weight: bold;
}

.field pre {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  grid-column: 1 / -1;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.stat-item .label {
  font-size: 0.9em;
  color: #666;
  margin-bottom: 5px;
}

.stat-item .value {
  font-size: 1.5em;
  font-weight: bold;
  color: #333;
}

.stat-item .value.high {
  color: #28a745;
}

.stat-item .value.medium {
  color: #ffc107;
}

.stat-item .value.low {
  color: #dc3545;
}
```

---

## 2. Next.js

### API Route (옵션)
```typescript
// pages/api/upload-pdf.ts
import type { NextApiRequest, NextApiResponse } from 'next';
import formidable from 'formidable';
import fs from 'fs';
import axios from 'axios';

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const form = formidable({});

  form.parse(req, async (err, fields, files) => {
    if (err) {
      return res.status(500).json({ error: 'File parsing failed' });
    }

    const file = files.file;
    if (!file || Array.isArray(file)) {
      return res.status(400).json({ error: 'Invalid file' });
    }

    try {
      const formData = new FormData();
      const fileBuffer = fs.readFileSync(file.filepath);
      const blob = new Blob([fileBuffer], { type: 'application/pdf' });
      formData.append('file', blob, file.originalFilename || 'document.pdf');

      const response = await axios.post(
        `${process.env.API_BASE_URL}/api/v1/process-pdf`,
        formData,
        {
          params: {
            adaptive: true,
            apply_postprocessing: true,
          },
          timeout: 120000,
        }
      );

      res.status(200).json(response.data);
    } catch (error) {
      res.status(500).json({ error: 'Processing failed' });
    }
  });
}
```

### Page Component
```typescript
// pages/upload.tsx
import { useState } from 'react';
import axios from 'axios';
import { PDFUploader } from '../components/PDFUploader';

export default function UploadPage() {
  return (
    <div className="container">
      <h1>PDF 문서 처리</h1>
      <PDFUploader />
    </div>
  );
}
```

---

## 3. Vue 3 + Composition API

```vue
<!-- components/PDFUploader.vue -->
<template>
  <div class="pdf-uploader">
    <h2>PDF 문서 업로드</h2>

    <form @submit.prevent="handleSubmit">
      <div class="file-input-wrapper">
        <input
          type="file"
          accept="application/pdf"
          @change="handleFileChange"
          :disabled="loading"
          ref="fileInput"
          id="pdf-input"
        />
        <label for="pdf-input" class="file-label">
          {{ file ? file.name : '파일 선택' }}
        </label>
      </div>

      <button type="submit" :disabled="!file || loading">
        {{ loading ? '처리 중...' : '업로드' }}
      </button>

      <button v-if="file && !loading" type="button" @click="handleReset" class="reset-btn">
        초기화
      </button>
    </form>

    <!-- 로딩 상태 -->
    <div v-if="loading" class="loading">
      <p>PDF 파일을 처리하고 있습니다...</p>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${progress}%` }" />
      </div>
      <p>{{ progress }}% 완료</p>
    </div>

    <!-- 에러 표시 -->
    <div v-if="error" class="error">
      <p>❌ {{ error }}</p>
    </div>

    <!-- 결과 표시 -->
    <ResultDisplay v-if="result" :result="result" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import axios, { AxiosError } from 'axios';
import ResultDisplay from './ResultDisplay.vue';
import type { PDFProcessResult, PDFData } from '../types/pdf.types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const file = ref<File | null>(null);
const result = ref<PDFData | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const progress = ref(0);
const fileInput = ref<HTMLInputElement>();

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const selectedFile = target.files?.[0];

  if (selectedFile) {
    if (selectedFile.type === 'application/pdf') {
      file.value = selectedFile;
      error.value = null;
      result.value = null;
    } else {
      error.value = 'PDF 파일만 업로드 가능합니다.';
      file.value = null;
    }
  }
};

const handleSubmit = async () => {
  if (!file.value) {
    error.value = '파일을 선택해주세요.';
    return;
  }

  loading.value = true;
  error.value = null;
  progress.value = 0;

  const formData = new FormData();
  formData.append('file', file.value);

  try {
    const response = await axios.post<PDFProcessResult>(
      `${API_BASE_URL}/api/v1/process-pdf`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        params: {
          adaptive: true,
          apply_postprocessing: true,
        },
        timeout: 120000,
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            progress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        },
      }
    );

    if (response.data.success && response.data.data) {
      result.value = response.data.data;
    } else {
      error.value = response.data.error || '처리 실패';
    }
  } catch (err) {
    const axiosError = err as AxiosError<{ detail?: string }>;
    error.value =
      axiosError.response?.data?.detail ||
      axiosError.message ||
      '서버와 통신 중 오류가 발생했습니다.';
  } finally {
    loading.value = false;
    progress.value = 0;
  }
};

const handleReset = () => {
  file.value = null;
  result.value = null;
  error.value = null;
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};
</script>

<style scoped>
/* 앞의 CSS와 동일 */
</style>
```

---

더 많은 예제와 상세 설명은 [API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md)를 참고하세요.
