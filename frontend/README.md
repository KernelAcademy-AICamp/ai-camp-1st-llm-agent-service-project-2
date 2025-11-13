# LawLaw Frontend

> 형사법 전문 AI 어시스턴트 웹 애플리케이션 프론트엔드

## 📋 프로젝트 소개

LawLaw는 **Constitutional AI + RAG(Retrieval-Augmented Generation)** 기반의 형사법 전문 AI 어시스턴트입니다.
388,000개 이상의 형사법 판례와 법령 데이터를 활용하여 법률 정보를 제공합니다.

### 주요 기능

- **🤖 AI 법률 상담** - Constitutional AI 기반 챗봇 (Hybrid RAG: Semantic + BM25)
- **📊 사건 분석** - 사건 파일 업로드 및 AI 분석
- **📝 문서 자동 생성** - 소장, 답변서, 변론요지서 등 법률 문서 작성
- **⚖️ 최신 판례 검색** - 대법원 판례 실시간 크롤링 및 검색
- **👤 사용자 인증** - 회원가입/로그인 시스템

---

## 🛠️ 기술 스택

| Category | Technologies |
|----------|-------------|
| **Framework** | React 18.2 |
| **Language** | TypeScript 4.9 |
| **Routing** | React Router v6 |
| **HTTP Client** | Axios |
| **Icons** | React Icons |
| **Build Tool** | Create React App |

---

## 🚀 시작하기

### 1. 사전 요구사항

- Node.js 18+
- npm 또는 yarn
- **백엔드 서버 실행 필수** (포트 8000)

### 2. 설치

```bash
# 의존성 설치
npm install
```

### 3. 환경 변수 설정 (선택사항)

프로젝트 루트에 `.env` 파일 생성:

```bash
# Backend API URL (기본값: http://localhost:8000)
REACT_APP_API_URL=http://localhost:8000
```

### 4. 실행

```bash
# 개발 서버 실행 (포트 3000)
npm start

# 프로덕션 빌드
npm run build

# 테스트
npm test
```

---

## 📁 프로젝트 구조

```
frontend/
├── public/
│   └── index.html              # HTML 템플릿
├── src/
│   ├── api/
│   │   └── client.ts           # API 클라이언트 (Axios)
│   ├── components/
│   │   ├── Header/             # 헤더 컴포넌트
│   │   ├── Sidebar/            # 사이드바 네비게이션
│   │   ├── Layout/             # 레이아웃 래퍼
│   │   └── ...
│   ├── contexts/
│   │   └── AuthContext.tsx     # 인증 컨텍스트
│   ├── pages/
│   │   ├── Landing/            # 랜딩 페이지
│   │   ├── Home/               # 대시보드
│   │   ├── Login/              # 로그인
│   │   ├── Signup/             # 회원가입
│   │   ├── LegalResearch/      # AI 챗봇 (RAG)
│   │   ├── CaseManagement/     # 사건 관리
│   │   ├── DocumentEditor/     # 문서 작성
│   │   └── RecentPrecedents/   # 최신 판례
│   ├── services/
│   │   └── precedentScrapingService.ts  # 판례 크롤링
│   ├── styles/                 # 글로벌 스타일
│   ├── types.ts                # TypeScript 타입 정의
│   ├── App.tsx                 # 앱 루트 컴포넌트
│   └── index.tsx               # 앱 엔트리 포인트
├── package.json
└── tsconfig.json
```

---

## 🔌 백엔드 연동

이 프론트엔드는 **FastAPI 백엔드 서버**와 통신합니다.

### 백엔드 요구사항

1. **FastAPI 서버** (포트 8000)
   - Python 3.10+
   - ChromaDB 벡터 데이터베이스
   - BM25 인덱스

2. **필수 엔드포인트**
   - `GET /health` - 서버 상태 확인
   - `POST /api/chat-with-rag` - RAG 챗봇
   - `POST /api/search` - 판례 검색
   - `POST /api/cases/upload` - 사건 파일 업로드
   - `POST /api/documents/generate` - 문서 생성
   - `POST /api/auth/login` - 로그인
   - `POST /api/auth/signup` - 회원가입

### 백엔드 실행 (참고)

```bash
# 백엔드 디렉토리로 이동
cd ../backend

# Python 가상환경 활성화 (선택)
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# 서버 실행
python main.py
# 또는
uvicorn backend.main:app --reload --port 8000
```

---

## 🎨 주요 페이지 설명

### 1. 랜딩 페이지 (`/`)
- 프로젝트 소개
- 주요 기능 안내
- 로그인/회원가입 링크

### 2. 대시보드 (`/app`)
- 통계 요약
- 빠른 액세스 메뉴

### 3. AI 법률 상담 (`/research`)
- **Constitutional AI** 기반 챗봇
- **Hybrid RAG** (Semantic + BM25 검색)
- 388K+ 판례 데이터 활용
- 출처 표시 (참고 판례)

### 4. 사건 관리 (`/cases`)
- 사건 파일 업로드 (PDF, DOCX)
- AI 사건 분석
- 쟁점 추출 및 관련 판례 검색

### 5. 문서 작성 (`/docs`)
- 법률 문서 자동 생성
  - 소장
  - 답변서
  - 변론요지서
  - 내용증명
  - 각종 계약서

### 6. 최신 판례 (`/research/cases`)
- 대법원 판례 실시간 크롤링
- 판례 상세 정보
- 키워드 검색

---

## 🔐 인증 시스템

### JWT 기반 인증

```typescript
// 로그인 예시
const response = await apiClient.login({
  username: "user@example.com",
  password: "password123"
});

// access_token 저장
localStorage.setItem('token', response.access_token);

// 인증이 필요한 요청
const user = await apiClient.getCurrentUser(token);
```

### 보호된 라우트

- 현재는 모든 페이지가 공개 (데모 목적)
- `ProtectedRoute` 컴포넌트로 인증 제어 가능

---

## 📡 API 클라이언트 사용법

```typescript
import { apiClient } from './api/client';

// RAG 챗봇
const response = await apiClient.chatWithRAG({
  query: "절도죄의 구성요건은 무엇인가요?",
  top_k: 5,
  include_sources: true
});

console.log(response.answer);  // AI 답변
console.log(response.sources); // 참고 판례

// 판례 검색
const results = await apiClient.searchVectorDB(
  "업무상 횡령",
  20  // top_k
);

// 사건 파일 업로드
const files = [file1, file2];
const analysis = await apiClient.uploadCaseFiles(files);

// 문서 생성
const document = await apiClient.generateDocument({
  document_type: "소장",
  case_id: "case123",
  parameters: {
    plaintiff: "홍길동",
    defendant: "김철수",
    claim_amount: 10000000
  }
});
```

---

## 🧪 개발 가이드

### 새 페이지 추가

1. `src/pages/` 에 폴더 생성
2. 컴포넌트 작성 (`PageName.tsx`, `PageName.css`)
3. `src/App.tsx` 에 라우트 추가

```tsx
<Route path="/new-page" element={
  <Layout>
    <NewPage />
  </Layout>
} />
```

### API 엔드포인트 추가

`src/api/client.ts` 에 메서드 추가:

```typescript
async newEndpoint(data: RequestType): Promise<ResponseType> {
  return this.fetch<ResponseType>('/api/new-endpoint', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
```

### 스타일링 규칙

- CSS Modules 사용 (`*.css`)
- 공통 스타일은 `src/styles/` 사용
- 색상 변수는 `variables.css` 참조

---

## 🐛 트러블슈팅

### 백엔드 연결 실패

```
Error: Network Error
```

**해결:**
1. 백엔드 서버 실행 확인 (`http://localhost:8000`)
2. CORS 설정 확인
3. `.env` 파일의 `REACT_APP_API_URL` 확인

### Constitutional AI 챗봇 에러

```
503 Service Unavailable: Constitutional AI chatbot not available
```

**원인:**
- ChromaDB 벡터 데이터베이스 미설치
- BM25 인덱스 누락

**해결:**
1. 백엔드에 ChromaDB 설치 (`data/vectordb/chroma_criminal_law/`)
2. BM25 인덱스 설치 (`data/vectordb/bm25/`)
3. 백엔드 재시작

---

## 📦 배포

### 프로덕션 빌드

```bash
npm run build
```

빌드 결과물은 `build/` 폴더에 생성됩니다.

### 정적 호스팅 (예: Vercel, Netlify)

1. GitHub에 푸시
2. Vercel/Netlify에 연결
3. 환경 변수 설정:
   - `REACT_APP_API_URL`: 프로덕션 백엔드 URL

---

## 👥 팀 정보

- **레포지토리**: [KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2](https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2)
- **브랜치**: `feat/frontend`
- **개발 환경**: React 18 + TypeScript 4

---

## 📝 라이선스

이 프로젝트는 교육 목적으로 개발되었습니다.

---

## 🤝 기여 가이드

1. 이 레포지토리 Fork
2. 새 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 생성

---

## 📞 문의

프로젝트 관련 문의사항은 이슈를 생성해주세요.
