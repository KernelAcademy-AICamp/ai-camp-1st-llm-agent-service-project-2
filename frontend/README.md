# LawLaw Frontend

> 형사법 전문 AI 어시스턴트 웹 애플리케이션

Constitutional AI + RAG 기반 형사법 전문 AI 어시스턴트의 프론트엔드입니다.

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

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
npm install
```

### 2. 환경 변수 설정 (선택)
`.env` 파일 생성:
```bash
REACT_APP_API_URL=http://localhost:8000
```

### 3. 개발 서버 실행
```bash
npm start
```
브라우저에서 `http://localhost:3000` 접속

### 4. 프로덕션 빌드
```bash
npm run build
```

> **참고**: 백엔드 서버(포트 8000)가 실행 중이어야 합니다.

---

## 📄 주요 페이지

### 1. Landing (`/`)
프로젝트 소개 및 로그인/회원가입

### 2. Home (`/app`)
대시보드 - 통계 요약 및 빠른 액세스

### 3. Legal Research (`/research`)
- Constitutional AI 챗봇
- Hybrid RAG (Semantic + BM25)
- 388K+ 형사법 판례 검색
- 출처 표시

### 4. Case Management (`/cases`)
- 사건 파일 업로드 (PDF, DOCX)
- AI 사건 분석
- 쟁점 추출 및 관련 판례 검색

### 5. Document Editor (`/docs`)
법률 문서 자동 생성
- 소장, 답변서, 변론요지서
- 내용증명
- 각종 계약서

### 6. Recent Precedents (`/research/cases`)
- 대법원 판례 실시간 크롤링
- 판례 상세 정보
- 키워드 검색

### 7. Login (`/login`)
JWT 기반 로그인

### 8. Signup (`/signup`)
회원가입

---

## 📂 프로젝트 구조

```
frontend/
├── src/
│   ├── api/              # API 클라이언트
│   ├── components/       # 공통 컴포넌트 (Header, Sidebar, Layout 등)
│   ├── contexts/         # React Context (Auth)
│   ├── pages/            # 8개 페이지 컴포넌트
│   ├── services/         # 서비스 로직
│   ├── styles/           # 글로벌 스타일
│   └── types.ts          # TypeScript 타입
└── package.json
```

---

**Repository**: [KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2](https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2)
