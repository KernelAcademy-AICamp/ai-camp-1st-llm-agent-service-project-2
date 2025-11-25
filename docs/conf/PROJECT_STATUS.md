# 프로젝트 상태 대시보드

> **최종 업데이트**: 2025-11-25 (Phase 3-4 Session 10 완료)
> **현재 브랜치**: feature/risk-analysis
> **다음 작업**: Phase 3-5 Session 11 (LLM Comparison)
> **전체 진행도**: 85% (Phase 2: 100%, Phase 3: 78%)
> **프로젝트**: law-saas (법률 문서 SaaS)

---

## 📊 프로젝트 개요

### 아키텍처
- **Frontend**: React (TypeScript) - `apps/web-frontend/`
- **Backend API**: Django + DRF - `apps/backend_api/`
- **AI Service**: FastAPI - `apps/ai-service/`
- **Vector DB**: ChromaDB (448,370+ precedent documents)
- **Database**: PostgreSQL (lawlaw DB)

### 현재 구현 상태 요약
| 영역 | 완료 | 진행중 | 대기 | 진행도 |
|------|------|--------|------|--------|
| **User/Auth** | ✅ | - | - | 100% |
| **Case Management** | ✅ | - | - | 100% |
| **Precedent DB** | ✅ | - | - | 100% |
| **RAG Chatbot** | ✅ | - | - | 100% |
| **AI Analysis** | ✅ | - | - | 100% |
| **Frontend UI** | ✅ | - | - | 100% |
| **Document Upload** | ✅ | - | - | 100% |
| **Summary/Clauses** | ✅ | - | - | 100% |
| **Organization** | ✅ | - | - | 100% |
| **Risk Analysis** | ✅ | - | - | 100% |
| **LLM Comparison** | ⬜ | - | ⬜ | 0% |

---

## 🎯 Phase 2 완료 현황 (Django Migration)

### ✅ 완료된 핵심 기능 (Phase 2 - Day 13~21)

#### 1. Django Backend (100% 완료)
**구현된 Models:**
- ✅ `User` - 커스텀 사용자 모델 (email 기반 인증, JWT)
- ✅ `Case` - 사건 관리 (title, content, analysis, status)
- ✅ `ChatHistory` - RAG 챗봇 대화 기록
- ✅ `Precedent` - 대법원 판례 (448,370+ documents)
- ✅ `PrecedentFeedback` - 사용자 판례 피드백
- ✅ `PrecedentFeedbackStats` - 피드백 통계 (필터링용)

**구현된 APIs:**
- ✅ `/api/v1/auth/signup` - 회원가입
- ✅ `/api/v1/auth/login` - 로그인 (JWT 발급)
- ✅ `/api/v1/auth/me` - 현재 사용자 정보
- ✅ `/api/v1/auth/profile` - 프로필 수정
- ✅ `/api/v1/auth/change-password` - 비밀번호 변경
- ✅ `/api/v1/cases/` - Case CRUD (list, create, retrieve, update, delete)
- ✅ `/api/v1/cases/{id}/chat_histories/` - 사건별 대화 기록
- ✅ `/api/v1/ai/chat/rag` - RAG 챗봇 프록시
- ✅ `/api/v1/ai/analyze/case` - 사건 분석 프록시
- ✅ `/api/v1/ai/generate/document` - 문서 생성 프록시
- ✅ `/api/v1/ai/health` - AI Service 헬스체크

**기술 스택:**
- Django 5.1.3 + DRF
- PostgreSQL (lawlaw DB)
- JWT Authentication (djangorestframework-simplejwt)
- CORS 설정 완료
- Admin 페이지 등록 완료

#### 2. AI Service (FastAPI) (100% 완료)

**구현된 APIs:**
- ✅ `POST /v1/chat/rag` - RAG 기반 판례 Q&A
  - Constitutional AI 적용
  - Hybrid Retrieval (Semantic + BM25)
  - Feedback-based filtering
  - ChromaDB 448,370+ 판례 검색
- ✅ `POST /v1/analyze/case` - 사건 분석
  - 사건 요약, 핵심 이슈 추출
  - 관련 판례 자동 검색
  - 당사자/중요 날짜 추출
- ✅ `POST /v1/analyze/generate` - 법률 문서 생성
  - 소장, 답변서 등 템플릿 기반 생성
  - 사건 정보 자동 반영
- ✅ `GET /health` - AI Service 헬스체크

**핵심 컴포넌트:**
- ✅ `ConstitutionalLawChatbot` - Constitutional AI 기반 챗봇
- ✅ `HybridRetriever` - Semantic + BM25 하이브리드 검색
- ✅ `KoreanLegalEmbedder` - 한국어 법률 임베딩
- ✅ `ChromaVectorDB` - 벡터 DB 관리
- ✅ `CaseAnalyzer` - 사건 분석 엔진
- ✅ `DocumentGenerator` - 법률 문서 생성 엔진
- ✅ `DatabaseFeedbackProvider` - DB 기반 피드백 필터

**기술 스택:**
- FastAPI + Uvicorn
- LangChain
- ChromaDB
- OpenAI API / Anthropic Claude
- PostgreSQL (feedback 조회)

#### 3. Frontend (React) (100% 완료)

**구현된 Pages:**
- ✅ `Landing` - 랜딩 페이지
- ✅ `Login` - 로그인
- ✅ `Signup` - 회원가입
- ✅ `Home` - 대시보드
- ✅ `LegalResearch` - RAG 챗봇 UI
  - 질문/답변 인터페이스
  - 출처 판례 표시
  - Constitutional AI critique log
- ✅ `CaseManagement` - 사건 관리
  - 사건 목록/생성/수정
  - AI 분석 결과 표시
- ✅ `DocumentEditor` - 문서 편집기
- ✅ `RecentPrecedents` - 최근 판례 조회

**구현된 Features:**
- ✅ JWT 기반 인증 (AuthContext)
- ✅ API Client (axios 기반)
- ✅ Responsive Design
- ✅ Error Handling
- ✅ Loading States

**기술 스택:**
- React 18 + TypeScript
- React Router v6
- Axios
- CSS Modules

---

## ✅ Phase 2 완료 (2025-11-24)

### Git 상태
- ✅ feature/django-migration 브랜치 커밋 및 Push 완료
- ✅ develop 브랜치 머지 완료

## ✅ Phase 3-1 완료 (Document 관리 - 100% 완료)

### 완료된 작업 요약 (2025-11-24)
- ✅ **Session 1: Document 모델 구현**
  - Document/DocumentChunk 모델 구현
  - Migration 및 Admin 등록

- ✅ **Session 2-A: Django 파일 업로드 API**
  - DocumentSerializer 작성
  - DocumentViewSet 구현 (upload, CRUD)
  - 파일 검증 (최대 10MB, .pdf/.docx/.txt)
  - URLs 설정

- ✅ **Session 2-B: Frontend 업로드 UI**
  - types.ts 타입 정의 (Document 인터페이스)
  - client.ts API 함수 (uploadDocument, getDocuments, deleteDocument)
  - DocumentManagement 페이지 구현

- ✅ **Session 2-C: OCR/전처리 파이프라인 (FastAPI)**
  - DocumentProcessor 서비스 구현
  - POST /v1/preprocess/document API
  - pypdf, python-docx, langchain 통합

- ✅ **Session 2-D: Week 1-2 통합 테스트**
  - E2E 테스트 완료 (업로드 → OCR → 전처리)
  - 에러 핸들링 검증
  - feature/document-management → develop 머지 완료

**완료일**: 2025-11-24
**Git 상태**: feature/document-management → develop 머지 완료

---

## ✅ Phase 3-2 완료 (AI 분석 결과 저장 - 100% 완료)

### 완료된 작업 요약 (2025-11-24)
1. ✅ **Session 4: Summary/KeyClause 모델 구현**
   - Summary 모델 (document FK, llm_model, summary_type, content, meta)
   - KeyClause 모델 (document FK, clause_type, title, content, importance_score)
   - Migration 생성 및 실행 (0002_summary_keyclause)
   - Admin 등록 (SummaryAdmin, KeyClauseAdmin)
   - Serializer 작성 (SummarySerializer, KeyClauseSerializer)

2. ✅ **Session 5-A: Django Summary/Clause API**
   - GET /api/v1/documents/{id}/summary/ - 문서 요약 조회
   - GET /api/v1/documents/{id}/clauses/ - 핵심 조항 조회
   - POST /api/v1/documents/{id}/analyze/ - AI 분석 트리거
   - Summary/KeyClause 자동 저장 로직

3. ✅ **Session 5-B: FastAPI LLM APIs**
   - POST /v1/llm/summarize - 문서 요약 생성
   - POST /v1/llm/clauses - 핵심 조항 추출
   - Summarizer 클래스 (GLOBAL/SECTION 요약)
   - ClauseExtractor 클래스 (10가지 조항 타입)

4. ✅ **Session 5-C: Frontend 분석 UI**
   - types.ts 타입 정의 (Summary, KeyClause)
   - API Client 함수 (getDocumentSummary, getDocumentClauses, analyzeDocument)
   - SummarySection 컴포넌트 (요약 표시, 생성/재생성 버튼)
   - ClauseList 컴포넌트 (조항 카드 그리드, 중요도 배지)
   - DocumentDetail 페이지 확장

5. ✅ **Session 5-D: Week 3-4 통합 테스트**
   - E2E 테스트 10/10 통과 (문서 요약, 조항 추출, 기존 결과 로드)
   - LLM 응답 품질 검증 완료
   - 버그 수정: LLM 클라이언트 호출 TypeError 수정
   - Git commit: "fix: correct LLM client usage in summarizer and clause_extractor"

**완료일**: 2025-11-24
**Git 상태**: feature/ai-analysis-storage → develop 머지 완료
**테스트 결과**: 10/10 통과 (28.01초)

---

## ✅ Phase 3-3 완료 (Organization/Project - 100% 완료)

### 완료된 작업 요약 (2025-11-24 ~ 2025-11-25)

1. ✅ **Session 6: Organization/Membership/Project 모델 구현** (2025-11-24 완료)
   - Organization 모델 (name, created_by, settings)
   - Membership 모델 (organization, user, role: ADMIN/EDITOR/VIEWER)
   - Project 모델 (organization, name, description, created_by)
   - Migration 생성 및 실행 (0001_initial.py)
   - Admin 페이지 등록 (OrganizationAdmin, MembershipAdmin, ProjectAdmin)
   - DB 테이블 생성 완료 (organizations, memberships, projects)
   - Git commit: `8a953974` - "feat(week5): add Organization, Membership, Project models (Session 6)"

2. ✅ **Session 7: Organization/Member/Project CRUD API** (2025-11-24 완료)
   - Serializers 구현 (OrganizationSerializer, MembershipSerializer, ProjectSerializer)
   - Permission classes 구현 (IsOrganizationAdmin, IsOrganizationMember, IsProjectEditor)
   - OrganizationViewSet 구현 (CRUD + 멤버 관리)
   - ProjectViewSet 구현 (CRUD + 조직별 필터링)
   - URLs 설정 및 Main URLs 통합
   - API 테스트 6/6 통과
   - Git commit: `04e42b84` - "feat(week5): add Organization/Project CRUD APIs (Session 7)"

3. ✅ **Session 8: Organization Frontend UI** (2025-11-25 완료)
   - types.ts 타입 정의 (Organization, Membership, Project)
   - API Client 함수 (조직/멤버/프로젝트 CRUD)
   - Organizations 페이지 (목록, 생성, 상세)
   - MemberManagement 컴포넌트 (멤버 초대, 역할 변경, 제거)
   - Projects 페이지 (목록, 생성, 상세)
   - CSS 스타일링 및 라우팅 설정
   - Git commit: `c4786058` - "feat: add Organization management UI (Session 8)"

4. ✅ **Session 9: Week 5 통합 테스트** (2025-11-25 완료)
   - Organization CRUD E2E 테스트 완료
   - Member 관리 E2E 테스트 완료
   - Project CRUD E2E 테스트 완료
   - 권한 체크 검증 완료
   - feature/organization → develop PR 생성 및 머지 완료 (PR #18)

**완료일**: 2025-11-25
**Git 상태**: feature/organization → develop 머지 완료 (PR #18)
**커밋**: `fb4d216f` (Merge PR #18)

---

## ✅ Phase 3-4 완료 (Risk Analysis - 100% 완료)

### 완료된 작업 요약 (2025-11-25)

1. ✅ **Backend 구현** (2025-11-25 완료)
   - RiskAnalysisResult 모델 구현 (Django)
     - overall_risk_score, severity, risk_items (JSONField)
     - recommendations, summary, llm_model
   - Migration 생성 및 실행 (0003_riskanalysisresult)
   - Admin 페이지 등록 (RiskAnalysisResultAdmin)
   - Serializer 작성 (RiskAnalysisResultSerializer)
   - ViewSet 구현 (apps/backend_api/documents/views.py)
     - GET /api/v1/documents/{id}/risk_analysis/ - 리스크 분석 결과 조회
     - POST /api/v1/documents/{id}/analyze_risk/ - 리스크 분석 트리거
   - RiskAnalyzer 서비스 구현 (apps/ai-service/services/risk_analyzer.py)
     - 리스크 점수 산정 로직 (0-100)
     - 6가지 리스크 카테고리 (LEGAL, FINANCIAL, COMPLIANCE, OPERATIONAL, REPUTATIONAL, OTHER)
     - 5가지 심각도 레벨 (CRITICAL, HIGH, MEDIUM, LOW, INFO)
   - POST /v1/llm/analyze_risk API 구현 (FastAPI)
   - Git commit: `8b57b8de` - "feat: implement risk analysis system (Session 10)"

2. ✅ **Frontend 구현** (2025-11-25 완료)
   - types.ts: Risk Analysis 타입 정의
     - RiskSeverity, RiskCategory, RiskItem, RiskAnalysis
     - RiskAnalysisResponse, AnalyzeRiskResponse
   - client.ts: API 클라이언트 함수
     - getDocumentRiskAnalysis(documentId, token)
     - analyzeDocumentRisk(documentId, token)
   - RiskAnalysisSection 컴포넌트 구현
     - 리스크 점수 시각화 (SVG 원형 프로그레스 바)
     - 심각도 배지 (색상 코드로 구분)
     - 카테고리별 리스크 항목 그룹핑
     - 권장사항 섹션
     - 분석 트리거/재분석 버튼
     - 로딩/에러 상태 처리
     - 확장/축소 기능
   - RiskAnalysisSection.css 스타일링
     - 반응형 디자인 (모바일 대응)
     - 심각도별 색상 테마
   - DocumentDetail 페이지 통합
   - Git commit: `477d7965` - "feat(frontend): add Risk Analysis UI components and integration"

**완료일**: 2025-11-25
**현재 브랜치**: feature/risk-analysis
**커밋**: `8b57b8de` (Backend), `477d7965` (Frontend)
**다음 작업**: feature/risk-analysis → develop PR 생성 및 머지 후 Session 10.5 시작

---

## 🔀 Phase 3-4.5 대기중 (Document-Case 통합 - 0% 완료)

### Session 10.5: Document-Case 통합 작업

**목적**: Case와 Document 기능 중복 제거, 단일 Document 시스템으로 통합

**작업 내용:**
- CaseAnalysis 모델 추가 (Document OneToOne 관계)
- Case 분석 API를 Document API로 통합
- Case UI 스타일을 Document에 적용 (2-column 레이아웃)
- 타입별 최적화 분석 제공 (CASE/CONTRACT/STATUTE)
- 기존 Case 데이터 마이그레이션

**예상 기간**: 4일 (Day 1-4)
**상세 계획**: `docs/conf/DOCUMENT_CASE_INTEGRATION_PLAN.md` 참조
**시작 조건**: feature/risk-analysis → develop 머지 완료 후

---

## 📅 향후 계획 (설계문서 기반)

### Week 1-2: Document 관리 기반 구축 (⬜ 0% 완료)

**목표**: 판례 외 계약서/법령 업로드 및 분석 가능

#### 구현 필요 기능:
1. **Document 모델** (Django)
   - id, user, title, doc_type, original_file, status, timestamps
   - DocumentChunk 모델 (chunk 단위 저장)

2. **파일 업로드 API** (Django)
   - `POST /api/documents/upload/` (PDF/Docx 업로드)
   - `GET /api/documents/` (문서 목록)
   - `GET /api/documents/{id}/` (문서 상세)

3. **OCR/전처리 파이프라인** (FastAPI)
   - PDF 텍스트 추출 / OCR
   - Chunking (RecursiveCharacterTextSplitter)
   - `POST /preprocess/document`

4. **벡터DB 인덱싱** (FastAPI)
   - 임베딩 생성 및 ChromaDB 저장
   - `POST /rag/index`

5. **Frontend 업로드 UI**
   - DocumentUpload 컴포넌트 (Drag & Drop)
   - 업로드 진행률 표시
   - 문서 목록/상세 페이지

**예상 소요**: 2주 (30-40시간)

### Week 3-4: AI 분석 결과 저장 (⬜ 0% 완료)

**목표**: 요약/조항 추출 결과 DB 저장 및 재사용

#### 구현 필요 기능:
1. **Summary 모델** (Django)
   - document, llm_model, summary_type, content, meta

2. **KeyClause 모델** (Django)
   - document, clause_type, title, content, importance_score

3. **LLM APIs** (FastAPI)
   - `POST /llm/summarize` (문서 요약)
   - `POST /llm/clauses` (핵심 조항 추출)

4. **Frontend UI 확장**
   - 문서 상세 페이지에 요약/조항 섹션 추가

**예상 소요**: 2주 (30-40시간)

### Week 5: Organization/Project (⬜ 0% 완료)

**목표**: 멀티테넌시 지원 (조직/프로젝트 단위 관리)

#### 구현 필요 기능:
1. **Models** (Django)
   - Organization, Membership, Project

2. **APIs** (Django)
   - Organization CRUD
   - Member 관리
   - Project CRUD

3. **Frontend UI**
   - Organizations 페이지
   - MemberManagement 컴포넌트
   - Projects 페이지

**예상 소요**: 1주 (15-20시간)

### Week 6: 리스크 분석 (⬜ 0% 완료)

**목표**: 계약서 리스크 자동 탐지

#### 구현 필요 기능:
1. **RiskAnalysisResult 모델** (Django)
2. **API** (FastAPI): `POST /llm/analyze_risk`
3. **Frontend**: RiskDashboard 페이지

**예상 소요**: 1주 (15-20시간)

### Week 7: LLM 비교 (⬜ 0% 완료)

**목표**: 멀티 모델 성능 비교

#### 구현 필요 기능:
1. **LLMModelConfig, LLMCallLog 모델** (Django)
2. **API** (FastAPI): `POST /llm/compare`
3. **Frontend**: ModelComparison 페이지

**예상 소요**: 1주 (15-20시간)

---

## 🗄️ 현재 데이터베이스 스키마

### 구현된 테이블 (PostgreSQL: lawlaw)

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(254) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    password VARCHAR(128),
    lawyer_registration_number VARCHAR(50),
    specializations JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    date_joined TIMESTAMP WITH TIME ZONE,
    last_login TIMESTAMP WITH TIME ZONE
);
```

#### cases
```sql
CREATE TABLE cases (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    content TEXT,
    analysis JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### chat_history
```sql
CREATE TABLE chat_history (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    case_id UUID REFERENCES cases(id) ON DELETE SET NULL,
    query TEXT,
    answer TEXT,
    sources JSONB DEFAULT '[]',
    model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE
);
```

#### precedents
```sql
CREATE TABLE precedents (
    id UUID PRIMARY KEY,
    case_number VARCHAR(100) UNIQUE,
    title VARCHAR(500),
    summary TEXT,
    full_text TEXT,
    judgment_summary TEXT,
    reference_statutes TEXT DEFAULT '[]',  -- JSON string
    reference_precedents TEXT DEFAULT '[]',  -- JSON string
    precedent_id VARCHAR(100),
    court VARCHAR(100) DEFAULT '대법원',
    decision_date TIMESTAMP WITH TIME ZONE,
    case_type VARCHAR(50) DEFAULT '형사',
    specialization_tags TEXT DEFAULT '[]',  -- JSON string
    citation VARCHAR(200),
    case_link VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### precedent_feedback
```sql
CREATE TABLE precedent_feedback (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    precedent_id VARCHAR(200),
    query VARCHAR(1000),
    feedback_type VARCHAR(20),  -- 'like' or 'dislike'
    is_helpful BOOLEAN DEFAULT TRUE,
    relevance_score INTEGER,
    comment VARCHAR(500),
    session_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE
);
```

#### precedent_feedback_stats
```sql
CREATE TABLE precedent_feedback_stats (
    precedent_id VARCHAR(200) PRIMARY KEY,
    total_likes INTEGER DEFAULT 0,
    total_dislikes INTEGER DEFAULT 0,
    total_feedback_count INTEGER DEFAULT 0,
    like_ratio DOUBLE PRECISION DEFAULT 0.0,
    avg_relevance_score DOUBLE PRECISION,
    should_exclude BOOLEAN DEFAULT FALSE,
    exclusion_threshold DOUBLE PRECISION DEFAULT 0.3,
    last_updated TIMESTAMP WITH TIME ZONE
);
```

### 구현된 테이블 (Phase 3)

#### documents (Phase 3-1 완료)
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    doc_type VARCHAR(50),
    original_file VARCHAR(100),
    status VARCHAR(20) DEFAULT 'UPLOADED',
    source_type VARCHAR(20),
    language VARCHAR(10) DEFAULT 'ko',
    file_size INTEGER,
    file_type VARCHAR(10),
    page_count INTEGER,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### document_chunks (Phase 3-1 완료)
```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER,
    text TEXT,
    embedding_id VARCHAR(255),
    page_number INTEGER,
    token_count INTEGER,
    start_offset INTEGER,
    end_offset INTEGER,
    created_at TIMESTAMP WITH TIME ZONE
);
```

#### summaries (Phase 3-2 Session 4 완료)
```sql
CREATE TABLE summaries (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    llm_model VARCHAR(100),
    summary_type VARCHAR(20) DEFAULT 'GLOBAL',
    content TEXT,
    meta JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE
);
```

#### key_clauses (Phase 3-2 Session 4 완료)
```sql
CREATE TABLE key_clauses (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    clause_type VARCHAR(50),
    title VARCHAR(255),
    content TEXT,
    importance_score INTEGER CHECK (importance_score >= 0 AND importance_score <= 100),
    llm_model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE
);
```

#### organizations (Phase 3-3 Session 6 완료)
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### memberships (Phase 3-3 Session 6 완료)
```sql
CREATE TABLE memberships (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'VIEWER',  -- ADMIN/EDITOR/VIEWER
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (organization_id, user_id)
);
```

#### projects (Phase 3-3 Session 6 완료)
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### risk_analysis_results (Phase 3-4 Session 10 완료)
```sql
CREATE TABLE risk_analysis_results (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    overall_risk_score INTEGER CHECK (overall_risk_score >= 0 AND overall_risk_score <= 100),
    risk_items JSONB DEFAULT '[]',
    recommendations TEXT,
    llm_model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE
);
```

### 미구현 테이블 (설계문서 참조)

- `llm_model_configs` (Week 7)
- `llm_call_logs` (Week 7)

---

## 🔗 API 엔드포인트 현황

### Django Backend (http://localhost:8000)

#### ✅ 구현 완료
- `POST /api/v1/auth/signup` - 회원가입
- `POST /api/v1/auth/login` - 로그인 (JWT)
- `POST /api/v1/auth/logout` - 로그아웃
- `GET /api/v1/auth/me` - 현재 사용자 정보
- `PUT /api/v1/auth/profile` - 프로필 수정
- `POST /api/v1/auth/change-password` - 비밀번호 변경
- `GET /api/v1/cases/` - 사건 목록
- `POST /api/v1/cases/` - 사건 생성
- `GET /api/v1/cases/{id}/` - 사건 상세
- `PUT /api/v1/cases/{id}/` - 사건 수정
- `DELETE /api/v1/cases/{id}/` - 사건 삭제
- `GET /api/v1/cases/{id}/chat_histories/` - 사건별 대화 기록
- `POST /api/v1/ai/chat/rag` - RAG 챗봇 (프록시)
- `POST /api/v1/ai/analyze/case` - 사건 분석 (프록시)
- `POST /api/v1/ai/generate/document` - 문서 생성 (프록시)
- `GET /api/v1/ai/health` - AI Service 헬스체크

- `POST /api/v1/documents/upload/` - 문서 업로드 (Phase 3-1 완료)
- `GET /api/v1/documents/` - 문서 목록 (Phase 3-1 완료)
- `GET /api/v1/documents/{id}/` - 문서 상세 (Phase 3-1 완료)
- `DELETE /api/v1/documents/{id}/` - 문서 삭제 (Phase 3-1 완료)

#### ✅ Phase 3-2 추가 (Session 5-A)
- `GET /api/v1/documents/{id}/summary/` - 문서 요약 조회
- `GET /api/v1/documents/{id}/clauses/` - 핵심 조항 조회
- `POST /api/v1/documents/{id}/analyze/` - AI 분석 트리거

#### ✅ Phase 3-3 추가 (Session 7)
- `GET /api/v1/organizations/` - 조직 목록
- `POST /api/v1/organizations/` - 조직 생성
- `GET /api/v1/organizations/{id}/` - 조직 상세
- `PUT /api/v1/organizations/{id}/` - 조직 수정
- `DELETE /api/v1/organizations/{id}/` - 조직 삭제
- `GET /api/v1/organizations/{id}/members/` - 멤버 목록
- `POST /api/v1/organizations/{id}/add_member/` - 멤버 추가
- `DELETE /api/v1/organizations/{id}/remove_member/{user_id}/` - 멤버 제거
- `PUT /api/v1/organizations/{id}/update_member_role/{user_id}/` - 역할 변경
- `GET /api/v1/projects/` - 프로젝트 목록
- `POST /api/v1/projects/` - 프로젝트 생성
- `GET /api/v1/projects/{id}/` - 프로젝트 상세
- `PUT /api/v1/projects/{id}/` - 프로젝트 수정
- `DELETE /api/v1/projects/{id}/` - 프로젝트 삭제

#### ✅ Phase 3-4 추가 (Session 10)
- `GET /api/v1/documents/{id}/risk-analysis/` - 리스크 분석 결과 조회
- `POST /api/v1/documents/{id}/analyze-risk/` - 리스크 분석 트리거

### AI Service (FastAPI) (http://localhost:8001)

#### ✅ 구현 완료
- `POST /v1/chat/rag` - RAG 챗봇
- `POST /v1/analyze/case` - 사건 분석
- `POST /v1/analyze/generate` - 문서 생성
- `GET /health` - 헬스체크
- `POST /v1/preprocess/document` - 문서 전처리 (Phase 3-1 완료)
- `POST /v1/rag/index` - 벡터DB 인덱싱 (Phase 3-1 완료)
- `POST /v1/llm/summarize` - 문서 요약 생성 (Phase 3-2 Session 5-B 완료)
- `POST /v1/llm/clauses` - 핵심 조항 추출 (Phase 3-2 Session 5-B 완료)
- `POST /v1/llm/analyze_risk` - 리스크 분석 (Phase 3-4 Session 10 완료)

#### ⬜ 미구현
- `POST /v1/llm/compare` (Week 7)

---

## 🐛 알려진 이슈

### 현재 블로킹 이슈
**없음** - 핵심 기능 모두 동작 중

### 해결된 이슈
- ✅ Django migration 완료 (SQLAlchemy → Django ORM)
- ✅ JWT 인증 통합
- ✅ CORS 설정 완료
- ✅ AI Service <-> Django DB 연동 (feedback 조회)
- ✅ Frontend <-> Django API 통합

---

## 📈 진행도 요약

### Phase 2 (Django Migration) - 100% 완료
| 항목 | 상태 |
|------|------|
| User/Auth | ✅ 100% |
| Case Management | ✅ 100% |
| Precedent DB | ✅ 100% |
| RAG Chatbot | ✅ 100% |
| AI Analysis | ✅ 100% |
| Frontend UI | ✅ 100% |

### Phase 3 (확장 기능) - 78% 완료
| 주차 | 기능 | 진행도 |
|------|------|--------|
| Week 0 | 현재 작업 마무리 | ✅ 100% |
| Week 1-2 | Document 관리 | ✅ 100% |
| Week 3-4 | Summary/Clauses | ✅ 100% |
| Week 5 | Organization | ✅ 100% |
| Week 6 | Risk Analysis | ✅ 100% |
| Week 6.5 | **Document-Case 통합** | ⬜ 0% |
| Week 7 | LLM Comparison | ⬜ 0% |
| Week 8 | Crawling System | ⬜ 0% |
| Week 9 | Advanced Dashboard | ⬜ 0% |
| Week 10 | Final Integration | ⬜ 0% |

---

## 📝 다음 세션 TODO

### ✅ 완료된 Phase 3 체크리스트
1. ✅ **Phase 3-1** (Document 관리) - 100% 완료
2. ✅ **Phase 3-2** (AI 분석 결과 저장) - 100% 완료
3. ✅ **Phase 3-3** (Organization/Project) - 100% 완료
   - ✅ Session 6: Organization 모델
   - ✅ Session 7: Organization API
   - ✅ Session 8: Organization UI
   - ✅ Session 9: Week 5 통합 테스트
   - ✅ feature/organization → develop 머지 완료 (PR #18)
4. ✅ **Phase 3-4** (Risk Analysis) - 100% 완료
   - ✅ Session 10: Risk Analysis 시스템 구현
   - 🚧 feature/risk-analysis → develop PR 대기

5. ⬜ **Phase 3-4.5** (Document-Case 통합) - 0% 완료
   - ⬜ Session 10.5: Case와 Document 중복 제거 및 통합
   - 목표: 단일 Document 시스템, Case UI 유지
   - 상세 계획: `DOCUMENT_CASE_INTEGRATION_PLAN.md`

### 다음 작업 (Phase 3-4.5: Document-Case 통합 - Week 6.5)
**목표**: Case와 Document 중복 제거, 단일 시스템으로 통합

#### 구현 예정 기능:
1. [ ] **Session 10.5: Document-Case 통합** (Week 6.5 - 4일)
   - CaseAnalysis 모델 추가
   - Document API에 Case 기능 통합
   - Case UI 스타일을 Document에 적용
   - 데이터 마이그레이션
   - 상세: `docs/conf/DOCUMENT_CASE_INTEGRATION_PLAN.md`

2. [ ] **Session 11: LLM Comparison** (Week 7)
   - LLMModelConfig, LLMCallLog 모델
   - 멀티 모델 비교 API
   - ModelComparison 페이지

2. [ ] **Session 13: Crawling System** (Week 8)
   - DataSource, CrawlJob, CrawlLog 모델
   - 판례/법령 크롤러 (FastAPI)
   - Admin 인터페이스 및 스케줄러

3. [ ] **Session 14-A~C: Advanced Dashboard** (Week 9)
   - ProjectStats, OrganizationStats 모델
   - 통계 API (dashboard overview, project/org stats)
   - 차트 UI (DocumentTrendChart, RiskHeatmap 등)
   - 대시보드 통합 테스트

4. [ ] **Session 15: Final Integration** (Week 10)
   - 전체 E2E 테스트 (Phase 2 + Phase 3)
   - 배포 준비 (Docker, README, API 문서)
   - develop → main PR

---

## 🔗 관련 문서

- ⭐ [빠른 시작 가이드](./QUICK_START.md) - **지금 바로 시작**
- ⭐ [Git 브랜치 전략](./GIT_BRANCH_STRATEGY.md) - **필독**
- [기능 체크리스트](./FEATURE_CHECKLIST.md)
- [병렬 작업 가이드](./PARALLEL_WORKFLOW_GUIDE.md)
- [사용 시나리오](./HOW_TO_USE.md)
- [설계문서](../설계문서.md)

---

## ✅ Document-Case Integration 완료 (2025-11-25)

### 완료된 작업 요약
- ✅ **Day 1: 백엔드 모델 통합**
  - CaseAnalysis 모델 생성 (documents app)
  - ChatHistory 모델 수정 (document FK 추가)
  - 데이터 마이그레이션 완료 (7개 Case → Document+CaseAnalysis)
  - Admin 인터페이스 구성

- ✅ **Day 2: API 통합**
  - CaseAnalysisSerializer 구현
  - DocumentViewSet에 case-analysis 엔드포인트 추가
  - Case API에 deprecation 경고 추가
  - Parser classes 이슈 해결

- ✅ **Day 3: Frontend 통합**
  - DocumentCaseAnalysis 타입 정의
  - API Client 메소드 추가 (getCaseAnalysis, analyzeCase)
  - CaseAnalysisSection 컴포넌트 구현
  - DocumentDetail 페이지 통합

- ✅ **Day 4: AI Service 및 테스트**
  - AI Service /v1/llm/analyze_case 엔드포인트 구현
  - E2E 테스트 완료 (Case 업로드, 분석, 조회)
  - 모든 기능 정상 동작 확인

### 통합 결과
- Case와 Document 시스템 중복 제거
- Document 시스템으로 통합 (doc_type='CASE')
- Case의 우수한 UI/UX 보존
- 기존 데이터 무손실 마이그레이션

### Git 상태
- ✅ feature/document-case-integration 브랜치 작업 완료

---

## 📌 프로젝트 메타 정보

**프로젝트 위치**: `/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2`
**현재 Git 브랜치**: `feature/document-case-integration` (Document-Case 통합 완료)
**통합 브랜치**: `develop` (Phase 2, Phase 3-1, Phase 3-2, Phase 3-3, Phase 3-4 완료)
**Main 브랜치**: `main` (프로덕션)
**현재 작업**: Document-Case Integration 완료
**최근 커밋**: `87474f02` - "feat: integrate Case Analysis UI into Document system (Day 3)"
**최근 머지**: `8b57b8de` - "feat: implement risk analysis system (Session 10)"

**Git 브랜치 전략**: [GIT_BRANCH_STRATEGY.md](./GIT_BRANCH_STRATEGY.md) 참조

**팀원**: 박남욱, 정원형, 박재형
**프로젝트 기간**: 2024-10 ~ 2025-01 (예정)
