# 기능 체크리스트

> **최종 업데이트**: 2025-11-24 (Phase 3-3 Session 7 완료)
> **Phase 2 완료**: 100% (핵심 기능 모두 구현)
> **Phase 3-1 완료**: 100% (Document 관리 시스템)
> **Phase 3-2 완료**: 100% (AI 분석 결과 저장 - Summary/Clause 전체 완료)
> **Phase 3-3 진행중**: 67% (Session 7/9 완료 - Organization CRUD API 구현)
> **전체 진행도**: 80% (Phase 3: 67% 완료)

---

## 범례

- ✅ 완료
- 🚧 진행중
- ⬜ 대기
- ⚠️ 블로킹
- 🔄 리뷰 중

---

## Phase 2: Django Migration (✅ 100% 완료)

### ✅ User/Auth (100% 완료)

#### 2.1. Django User Model
- ✅ User 모델 설계 (AbstractUser 커스텀)
  - ✅ email 기반 인증 (username 비활성화)
  - ✅ UUID primary key
  - ✅ lawyer_registration_number, specializations 필드
  - ✅ UserManager 커스텀 (email 기반)
- ✅ Migration 생성 및 실행
  - ✅ `0001_initial` (2025-11-20)
  - ✅ `0002_add_django_auth_fields` (2025-11-21)
- ✅ Admin 페이지 등록
- ✅ Git commit: "feat: implement User model and JWT authentication (Phase 2 Day 13-14)"

#### 2.2. JWT Authentication
- ✅ djangorestframework-simplejwt 설치 및 설정
- ✅ Auth API 구현
  - ✅ `POST /api/v1/auth/signup` - 회원가입
  - ✅ `POST /api/v1/auth/login` - 로그인 (JWT 발급)
  - ✅ `POST /api/v1/auth/logout` - 로그아웃
  - ✅ `GET /api/v1/auth/me` - 현재 사용자 정보
  - ✅ `PUT /api/v1/auth/profile` - 프로필 수정
  - ✅ `POST /api/v1/auth/change-password` - 비밀번호 변경
- ✅ Permission 설정 (IsAuthenticated)
- ✅ Serializer 작성 (UserSerializer, LoginSerializer)
- ✅ Git commit: 통합 커밋

**완료일**: 2025-11-20
**커밋**: `2b46599`

---

### ✅ Precedent DB (100% 완료)

#### 3.1. Precedent Models
- ✅ Precedent 모델 구현
  - ✅ UUID primary key
  - ✅ case_number (unique, indexed)
  - ✅ title, summary, full_text
  - ✅ judgment_summary
  - ✅ reference_statutes, reference_precedents (JSON strings)
  - ✅ court, decision_date, case_type
  - ✅ specialization_tags (JSON string)
- ✅ PrecedentFeedback 모델 구현
  - ✅ user, precedent_id, query
  - ✅ feedback_type (like/dislike)
  - ✅ is_helpful, relevance_score, comment
  - ✅ session_id
- ✅ PrecedentFeedbackStats 모델 구현
  - ✅ precedent_id (primary key)
  - ✅ total_likes, total_dislikes, total_feedback_count
  - ✅ like_ratio, avg_relevance_score
  - ✅ should_exclude, exclusion_threshold
  - ✅ update_stats() 메서드
- ✅ Migration 생성 및 실행 (`0001_initial`)
- ✅ Admin 페이지 등록
- ✅ Git commit: "feat: add Precedent models and admin"

**완료일**: 2025-11-20
**커밋**: `e2cb89c`
**데이터**: ChromaDB 448,370+ precedent documents

---

### ✅ Case Management (100% 완료)

#### 4.1. Case Models
- ✅ Case 모델 설계
  - ✅ UUID primary key
  - ✅ user (FK to User)
  - ✅ title, content
  - ✅ analysis (JSONField)
  - ✅ status (draft/analyzing/analyzed/completed)
  - ✅ timestamps
- ✅ ChatHistory 모델 설계
  - ✅ UUID primary key
  - ✅ user (FK to User)
  - ✅ case (FK to Case, nullable)
  - ✅ query, answer
  - ✅ sources (JSONField)
  - ✅ model
- ✅ Migration 생성 및 실행 (`0001_initial`)
- ✅ Admin 페이지 등록
- ✅ Git commit: "feat: add Case models and AI Service proxy"

#### 4.2. Case CRUD API
- ✅ CaseSerializer 작성
- ✅ ChatHistorySerializer 작성
- ✅ CaseViewSet 구현
  - ✅ `GET /api/v1/cases/` - 사건 목록
  - ✅ `POST /api/v1/cases/` - 사건 생성
  - ✅ `GET /api/v1/cases/{id}/` - 사건 상세
  - ✅ `PUT /api/v1/cases/{id}/` - 사건 수정
  - ✅ `DELETE /api/v1/cases/{id}/` - 사건 삭제
  - ✅ `GET /api/v1/cases/{id}/chat_histories/` - 사건별 대화 기록
- ✅ Permission 설정 (사용자 본인만 조회/수정)
- ✅ URL 라우팅 설정
- ✅ Git commit: "feat: add Case and ChatHistory CRUD API (Day 18.5)"

**완료일**: 2025-11-21
**커밋**: `303ec6d`

---

### ✅ AI Service Proxy (100% 완료)

#### 5.1. AI Service 통합
- ✅ ai_proxy.py 구현
  - ✅ `POST /api/v1/ai/chat/rag` - RAG 챗봇 프록시
  - ✅ `POST /api/v1/ai/analyze/case` - 사건 분석 프록시
  - ✅ `POST /api/v1/ai/generate/document` - 문서 생성 프록시
  - ✅ `GET /api/v1/ai/health` - AI Service 헬스체크
- ✅ httpx 기반 비동기 HTTP 통신
- ✅ X-User-ID 헤더 전달 (JWT 인증 사용자)
- ✅ 에러 핸들링 (AI Service 미응답 시)
- ✅ Git commit: 통합 커밋

**완료일**: 2025-11-21
**커밋**: `1ae576a`

---

### ✅ AI Service (FastAPI) (100% 완료)

#### 6.1. RAG Chatbot
- ✅ ConstitutionalLawChatbot 구현
  - ✅ Constitutional AI 적용
  - ✅ Critique-based 답변 정제
  - ✅ chat() 메서드 (query, top_k, include_critique_log)
- ✅ HybridRetriever 구현
  - ✅ Semantic search (ChromaDB)
  - ✅ BM25 search
  - ✅ 하이브리드 랭킹 (alpha 가중치)
- ✅ KoreanLegalEmbedder 구현
  - ✅ 한국어 법률 도메인 임베딩
- ✅ DatabaseFeedbackProvider 구현
  - ✅ PostgreSQL에서 피드백 조회
  - ✅ should_exclude=True인 판례 ID 반환
- ✅ `/v1/chat/rag` API 구현
  - ✅ RAGRequest/RAGResponse 모델
  - ✅ 피드백 기반 필터링
  - ✅ top_k 자동 보정
- ✅ Git commit: Phase 2 통합

#### 6.2. Case Analyzer
- ✅ CaseAnalyzer 서비스 구현
  - ✅ analyze_documents() 메서드
  - ✅ 사건 요약 생성
  - ✅ 핵심 이슈 추출
  - ✅ 당사자/중요 날짜 추출
  - ✅ 관련 판례 자동 검색
- ✅ `/v1/analyze/case` API 구현
  - ✅ AnalyzeRequest/AnalyzeResponse 모델
  - ✅ LLM 기반 분석
  - ✅ RAG 연동 (관련 판례 검색)
- ✅ Git commit: Phase 2 통합

#### 6.3. Document Generator
- ✅ DocumentGenerator 서비스 구현
  - ✅ generate_document() 메서드
  - ✅ 템플릿 기반 문서 생성 (소장, 답변서 등)
  - ✅ 사건 정보 자동 반영
  - ✅ generation_mode (quick/custom)
- ✅ `/v1/analyze/generate` API 구현
  - ✅ GenerateRequest/GenerateResponse 모델
  - ✅ LLM 기반 생성
- ✅ Git commit: Phase 2 통합

**완료일**: 2025-11-20
**커밋**: `33aa3d4` (refactor: remove FastAPI backend, complete Django migration)

---

### ✅ Frontend (React) (100% 완료)

#### 7.1. Authentication UI
- ✅ Login 페이지
  - ✅ 이메일/비밀번호 입력
  - ✅ JWT 토큰 저장 (localStorage)
  - ✅ 로그인 성공 시 리다이렉트
- ✅ Signup 페이지
  - ✅ 회원가입 폼
  - ✅ 변호사 등록번호 (선택)
  - ✅ 전문 분야 (선택)
- ✅ AuthContext 구현
  - ✅ login(), logout() 함수
  - ✅ user 상태 관리
  - ✅ JWT 토큰 관리
- ✅ Git commit: Phase 2 통합

#### 7.2. Case Management UI
- ✅ CaseManagement 페이지
  - ✅ 사건 목록 표시
  - ✅ 사건 생성 폼
  - ✅ 사건 상세 보기
  - ✅ 사건 수정/삭제
  - ✅ AI 분석 결과 표시
- ✅ API 연동
  - ✅ getCases()
  - ✅ createCase()
  - ✅ updateCase()
  - ✅ deleteCase()
- ✅ Git commit: Phase 2 통합

#### 7.3. Legal Research UI
- ✅ LegalResearch 페이지
  - ✅ RAG 챗봇 인터페이스
  - ✅ 질문 입력 폼
  - ✅ 답변 표시
  - ✅ 출처 판례 리스트
  - ✅ Constitutional AI critique log (선택)
- ✅ API 연동
  - ✅ ragChat()
- ✅ Git commit: Phase 2 통합

#### 7.4. Other Pages
- ✅ Landing 페이지
- ✅ Home 대시보드
- ✅ DocumentEditor
- ✅ RecentPrecedents
- ✅ Layout 컴포넌트
- ✅ Git commit: Phase 2 통합

**완료일**: 2025-11-21
**커밋**: Phase 2 통합

---

## Phase 3: 확장 기능 (⬜ 0% 완료)

### Week 0: 현재 작업 마무리 (✅ 100% 완료)

#### 0.1. Git 정리
- ✅ Git 상태 확인 (2025-11-23)
- ✅ 설계문서 vs 현재 구현 분석 (2025-11-23)
- ✅ 7주 개발 계획 수립 (2025-11-23)
- ✅ Uncommitted 변경사항 커밋 (8개 파일) (2025-11-24)
  - ✅ Git commit 및 push (2025-11-24)
- ✅ feature/document-management 브랜치 생성 (2025-11-24)

#### 0.2. Phase 2 통합 테스트 (Session 0-B)
- ✅ 통합 테스트 생략 (Phase 2 기능 정상 동작 확인됨)
  - ✅ 회원가입/로그인 기능 확인
  - ✅ Case Management 기능 확인
  - ✅ RAG Chat 기능 확인
  - ✅ AI Service 연동 확인

#### 0.3. 문서화
- ✅ PROJECT_STATUS.md 업데이트 (2025-11-24)
- ✅ FEATURE_CHECKLIST.md 업데이트 (2025-11-24)
- ✅ SESSION_PROMPTS.md 확인 (2025-11-24)

**완료일**: 2025-11-24

---

### Week 1-2: Document 관리 기반 구축 (✅ 100% 완료)

#### ✅ Session 1: Document 모델 구현 (완료)
- ✅ Document 모델 설계
  - id, user, title, doc_type, original_file
  - status (UPLOADED/OCR_DONE/PREPROCESSED/EMBEDDED/FAILED)
  - source_type, language, file_size, file_type, page_count, error_message
- ✅ DocumentChunk 모델 설계
  - document FK, chunk_index, text, embedding_id
  - page_number, token_count, start_offset, end_offset
- ✅ Migration 생성 및 실행 (0001_initial)
- ✅ Admin 등록 (DocumentChunkInline)
- ✅ Git commit: "feat(week1): add Document and DocumentChunk models"

#### ✅ Session 2-A: 파일 업로드 API (Django) (완료)
- ✅ DocumentSerializer 작성
  - CaseSerializer 패턴 참조
  - 필수 필드: id, user, user_email, title, doc_type, status, file_size
  - read_only_fields, validate_title() 구현
- ✅ DocumentViewSet 구현
  - permission_classes = [IsAuthenticated]
  - get_queryset(), perform_create()
  - upload 액션: POST /api/v1/documents/upload/
  - CRUD: list, retrieve, destroy
- ✅ 파일 검증 (최대 10MB, .pdf/.docx/.txt)
- ✅ URLs 설정 (documents/urls.py, router 등록)
- ✅ Git commit: "feat(week1): add document upload API"

#### ✅ Session 2-B: Frontend 업로드 UI (완료)
- ✅ types.ts 타입 정의 (Document, DocumentListResponse, DocumentUploadResponse)
- ✅ client.ts API 함수 (uploadDocument, getDocuments, getDocument, deleteDocument)
- ✅ DocumentManagement 페이지 구현
  - State 관리, 파일 업로드 핸들러
  - 업로드 모달 UI, 문서 목록 렌더링
- ✅ DocumentManagement.css 작성
- ✅ App.tsx 라우팅 추가 (/documents)
- ✅ Git commit: "feat(week2): add document upload UI"

#### ✅ Session 2-C: OCR/전처리 파이프라인 (FastAPI) (완료)
- ✅ 의존성 설치 (pypdf, python-docx, langchain)
- ✅ DocumentProcessor 서비스 구현
  - process_document() 메서드
  - 파일 타입별 처리 (PDF, Docx, TXT)
  - RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
- ✅ preprocess.py 라우터 생성
  - PreprocessRequest/PreprocessResponse 모델
  - POST /v1/preprocess/document API
- ✅ main.py에 router include
- ✅ Git commit: "feat(week1): add OCR and preprocessing pipeline"

#### ✅ Session 2-D: Week 1-2 통합 테스트 (완료)
- ✅ Django API 테스트
  - GET /api/v1/documents/ 확인
  - GET /api/health/ 서버 상태 확인
- ✅ 파일 업로드 E2E
  - 로그인 → /documents 페이지
  - PDF 파일 업로드 (title, doc_type)
  - 업로드 성공 확인 (status: "UPLOADED")
  - 문서 목록에서 새 문서 확인
- ✅ FastAPI 전처리 API 테스트
  - POST /v1/preprocess/document 호출
  - Response: chunk_count, status 확인
- ✅ 에러 핸들링 테스트
  - 잘못된 파일, 크기 초과, 빈 제목 검증
- ✅ Git commit: "test: Week 1-2 integration tests"
- ✅ feature/document-management → develop 머지 완료

**완료일**: 2025-11-24

---

### Week 3-4: AI 분석 결과 저장 (✅ 100% 완료)

#### ✅ Session 4: Summary/KeyClause 모델 구현 (완료)
- ✅ Summary 모델 설계
  - ✅ document (FK to Document)
  - ✅ llm_model (사용된 LLM 모델)
  - ✅ summary_type (GLOBAL/SECTION)
  - ✅ content (요약 텍스트)
  - ✅ meta (JSONField - 추가 메타데이터)
- ✅ KeyClause 모델 설계
  - ✅ document (FK to Document)
  - ✅ clause_type (계약 조항 타입)
  - ✅ title (조항 제목)
  - ✅ content (조항 내용)
  - ✅ importance_score (중요도 점수 0-100)
  - ✅ llm_model
- ✅ Migration 생성 및 실행 (0002_summary_keyclause)
- ✅ Admin 등록
  - ✅ SummaryAdmin, KeyClauseAdmin
  - ✅ list_display, list_filter 설정
- ✅ Serializer 작성
  - ✅ SummarySerializer
  - ✅ KeyClauseSerializer
- ✅ Git commit: "feat: add Summary and KeyClause models"

**완료일**: 2025-11-24
**참조**: SESSION_PROMPTS.md → Session 4

#### ✅ Session 5-A: Django Summary/Clause API (완료)
- ✅ ViewSet 구현
  - ✅ GET /api/v1/documents/{id}/summary/ - 최신 GLOBAL 요약 조회
  - ✅ GET /api/v1/documents/{id}/clauses/ - 모든 핵심 조항 조회
  - ✅ POST /api/v1/documents/{id}/analyze/ - AI 분석 트리거
- ✅ AI Service 호출 로직
  - ✅ _generate_summary() 메서드 (POST /v1/llm/summarize 호출)
  - ✅ _extract_clauses() 메서드 (POST /v1/llm/clauses 호출)
  - ✅ httpx 기반 비동기 통신
  - ✅ 60초 타임아웃 설정
- ✅ 결과 저장 로직
  - ✅ Summary 객체 생성 및 저장
  - ✅ KeyClause 객체 배치 생성
  - ✅ meta 필드 활용 (token_count, model_version)
  - ✅ 에러 핸들링 및 로깅
- ✅ Git commit: "feat: add Summary and Clause API endpoints"

**완료일**: 2025-11-24
**소요 시간**: 약 3시간
**참조**: SESSION_PROMPTS.md → Session 5-A

#### ✅ Session 5-B: FastAPI LLM APIs (완료)
- ✅ services/summarizer.py 구현
  - ✅ Summarizer 클래스 with summarize() 메서드
  - ✅ GLOBAL/SECTION 요약 타입 지원
  - ✅ 법률 문서 최적화 프롬프트 템플릿
  - ✅ 토큰 수 추정 기능
- ✅ services/clause_extractor.py 구현
  - ✅ ClauseExtractor 클래스 with extract_clauses() 메서드
  - ✅ 10가지 조항 타입 지원 (PAYMENT, OBLIGATION, TERMINATION, etc.)
  - ✅ JSON 파싱 + Fallback 수동 파싱 로직
  - ✅ 중요도 점수 (0-100) 자동 산정
  - ✅ 문서 타입별 프롬프트 최적화
- ✅ routers/llm.py 구현
  - ✅ POST /v1/llm/summarize - 문서 요약 생성
  - ✅ POST /v1/llm/clauses - 핵심 조항 추출
  - ✅ Request/Response 모델 정의
  - ✅ 에러 핸들링 및 검증
- ✅ main.py 라우터 등록
- ✅ Git commit: "feat: add LLM summarize and clause extraction APIs (Session 5-B)"

**완료일**: 2025-11-24
**소요 시간**: 약 2시간
**참조**: SESSION_PROMPTS.md → Session 5-B

#### ✅ Session 5-C: Frontend 분석 UI (완료)
- ✅ types.ts 타입 정의
  - ✅ Summary 인터페이스 (id, document, llm_model, summary_type, content, meta, created_at)
  - ✅ KeyClause 인터페이스 (id, document, clause_type, title, content, importance_score, llm_model, created_at)
  - ✅ SummaryType, ClauseType 타입 정의
  - ✅ API 응답 타입 (SummaryResponse, ClausesResponse, AnalyzeDocumentResponse)
- ✅ API Client 함수 추가
  - ✅ getDocumentSummary(documentId, token)
  - ✅ getDocumentClauses(documentId, token)
  - ✅ analyzeDocument(documentId, token)
- ✅ SummarySection 컴포넌트
  - ✅ 요약 표시 (content, llm_model, summary_type, 생성일시)
  - ✅ "요약 생성" / "요약 재생성" 버튼
  - ✅ 로딩/에러 상태 처리
  - ✅ 메타데이터 표시 (접기/펼치기)
- ✅ ClauseList 컴포넌트
  - ✅ 조항 카드 그리드 레이아웃
  - ✅ 조항 타입 한글 라벨 (10가지)
  - ✅ 중요도 배지 (매우 중요/중요/보통)
  - ✅ 중요도순 자동 정렬
  - ✅ "조항 추출" / "조항 재추출" 버튼
- ✅ DocumentDetail 페이지 확장
  - ✅ Summary/Clause 상태 관리
  - ✅ loadSummary(), loadClauses() 함수
  - ✅ handleGenerateSummary(), handleExtractClauses() 핸들러
  - ✅ AI 분석 섹션 통합
- ✅ CSS 스타일링
  - ✅ SummarySection.css
  - ✅ ClauseList.css
  - ✅ DocumentDetail.css 업데이트
  - ✅ 반응형 디자인
- ✅ 빌드 검증 및 경고 수정
- ✅ Git commit: "feat: add document analysis UI (Session 5-C)"

**완료일**: 2025-11-24
**소요 시간**: 약 3시간
**참조**: SESSION_PROMPTS.md → Session 5-C

#### ✅ Session 5-D: Week 3-4 통합 테스트 (완료)
- ✅ 문서 요약 E2E
  - ✅ 문서 선택 → DocumentDetail 페이지
  - ✅ "요약 생성" 버튼 클릭
  - ✅ POST /api/v1/documents/{id}/analyze/
  - ✅ FastAPI: POST /v1/llm/summarize 호출 확인
  - ✅ Summary 저장 확인
  - ✅ 브라우저에 요약 텍스트 표시 확인
- ✅ 조항 추출 E2E
  - ✅ "조항 추출" 버튼 클릭
  - ✅ POST /api/v1/documents/{id}/analyze/
  - ✅ FastAPI: POST /v1/llm/clauses 호출 확인
  - ✅ KeyClause 목록 저장 확인 (18개 조항)
  - ✅ 브라우저에 조항 리스트 표시 확인
- ✅ 기존 결과 로드
  - ✅ 페이지 새로고침 → GET /api/v1/documents/{id}/summary/
  - ✅ GET /api/v1/documents/{id}/clauses/
- ✅ LLM 응답 품질 확인
  - ✅ 요약: 핵심 내용 확인 (649자)
  - ✅ 조항: 올바른 추출 확인
  - ✅ importance_score 정상 범위 (60-95, 모두 0-100)
  - ✅ 요약 텍스트에 핵심 법률 용어 포함 확인
- ✅ 에러 핸들링
  - ✅ LLM API 타임아웃 (60초)
  - ✅ 잘못된 document_id (404 반환)
- ✅ 버그 수정 (LLM client 동기/비동기 문제 해결)
  - ✅ summarizer.py: await 제거
  - ✅ clause_extractor.py: await 제거
- ✅ Git commit: "fix: correct LLM client usage in summarizer and clause_extractor"
- ✅ feature/ai-analysis-storage → develop 머지 완료

**완료일**: 2025-11-24
**테스트 결과**: 10/10 PASSED (28.01초)
**참조**: PROJECT_STATUS.md → Phase 3-2 완료

---

### Week 5: Organization/Project (🚧 67% 완료)

#### ✅ Session 6: Organization 모델 구현 (완료)
- ✅ Organization 모델 설계
  - ✅ id (UUID), name, created_by, settings (JSONField)
  - ✅ member_count property
- ✅ Membership 모델 설계
  - ✅ id (UUID), organization, user, role (ADMIN/EDITOR/VIEWER)
  - ✅ unique_together: (organization, user)
  - ✅ is_admin, can_edit properties
- ✅ Project 모델 설계
  - ✅ id (UUID), organization, name, description, created_by
  - ✅ document_count, case_count properties
- ✅ Migration 생성 및 실행 (0001_initial.py)
  - ✅ 3개 모델 테이블 생성 (organizations, memberships, projects)
  - ✅ 인덱스 최적화 (created_at, role, FK)
- ✅ Admin 페이지 등록
  - ✅ OrganizationAdmin (MembershipInline 포함)
  - ✅ MembershipAdmin (권한 표시)
  - ✅ ProjectAdmin (통계 표시)
- ✅ Git commit: `8a953974` - "feat(week5): add Organization, Membership, Project models (Session 6)"

**완료일**: 2025-11-24
**소요 시간**: 약 2시간

#### ✅ Session 7: Organization/Member/Project CRUD API (완료)
- ✅ Serializers 구현
  - ✅ OrganizationSerializer, OrganizationDetailSerializer
  - ✅ MembershipSerializer (user_email, role_display, is_admin, can_edit)
  - ✅ ProjectSerializer (organization_name, document_count, case_count)
  - ✅ AddMemberSerializer (user_email, role validation)
  - ✅ UpdateMemberRoleSerializer (role validation)
- ✅ Permission classes 구현
  - ✅ IsOrganizationAdmin (add/remove members, update roles)
  - ✅ IsOrganizationMember (view organization/projects)
  - ✅ IsProjectEditor (ADMIN/EDITOR can edit)
  - ✅ IsOrganizationOwnerOrAdmin (update/delete org)
- ✅ OrganizationViewSet 구현
  - ✅ CRUD: list, create, retrieve, update, destroy
  - ✅ @transaction.atomic on create (자동 admin 멤버십 생성)
  - ✅ Member management actions:
    - GET /api/v1/organizations/{id}/members/
    - POST /api/v1/organizations/{id}/add_member/
    - DELETE /api/v1/organizations/{id}/remove_member/{user_id}/
    - PUT /api/v1/organizations/{id}/update_member_role/{user_id}/
  - ✅ 보호 로직 (owner 제거 방지, 마지막 admin 제거/강등 방지)
- ✅ ProjectViewSet 구현
  - ✅ CRUD: list, create, retrieve, update, destroy
  - ✅ 조직별 필터링 (query param: organization)
  - ✅ 검색 기능 (name, description)
  - ✅ 멤버십 검증 (프로젝트 생성 시)
- ✅ URLs 설정
  - ✅ organizations/urls.py (DefaultRouter)
  - ✅ backend_api/urls.py 통합
- ✅ API 테스트 6/6 통과
  - ✅ POST /api/v1/organizations/ (201)
  - ✅ GET /api/v1/organizations/ (200)
  - ✅ GET /api/v1/organizations/{id}/ (200)
  - ✅ GET /api/v1/organizations/{id}/members/ (200)
  - ✅ POST /api/v1/projects/ (201)
  - ✅ GET /api/v1/projects/ (200)
- ✅ Git commit: `04e42b84` - "feat(week5): add Organization/Project CRUD APIs (Session 7)"

**완료일**: 2025-11-24
**소요 시간**: 약 3시간

#### Session 8: Frontend UI (⬜ 0% 완료)
- ⬜ types.ts 타입 정의 (Organization, Membership, Project)
- ⬜ API Client 함수 (조직/멤버/프로젝트 CRUD)
- ⬜ Organizations 페이지 (목록, 생성, 상세)
- ⬜ MemberManagement 컴포넌트 (멤버 초대, 역할 변경, 제거)
- ⬜ Projects 페이지 (목록, 생성, 상세)
- ⬜ CSS 스타일링
- ⬜ 라우팅 설정 (/organizations, /projects)
- ⬜ Git commit: "feat(week5): add Organization management UI (Session 8)"

**예상 소요**: 8-10시간

#### Session 9: Week 5 통합 테스트 (⬜ 0% 완료)
- ⬜ Organization CRUD E2E (API + UI)
  - ⬜ POST /api/v1/organizations/ (조직 생성)
  - ⬜ GET /api/v1/organizations/ (조직 목록)
  - ⬜ GET /api/v1/organizations/{id}/ (조직 상세)
  - ⬜ PUT /api/v1/organizations/{id}/ (조직 수정)
  - ⬜ 브라우저 UI 테스트 (/organizations)
- ⬜ Member 관리 E2E (API + UI)
  - ⬜ 테스트 사용자 2명 생성
  - ⬜ POST /api/v1/organizations/{id}/members/ (멤버 초대)
  - ⬜ GET /api/v1/organizations/{id}/members/ (멤버 목록)
  - ⬜ PUT /api/v1/organizations/{id}/members/{user_id}/ (역할 변경)
  - ⬜ DELETE /api/v1/organizations/{id}/members/{user_id}/ (멤버 제거)
  - ⬜ 브라우저 UI 테스트 (멤버 관리)
- ⬜ Project CRUD E2E (API + UI)
  - ⬜ POST /api/v1/projects/ (프로젝트 생성)
  - ⬜ GET /api/v1/projects/ (프로젝트 목록)
  - ⬜ 브라우저 UI 테스트 (/projects)
- ⬜ 권한 체크 검증
  - ⬜ 다른 조직의 프로젝트 접근 시도 (403 Forbidden)
  - ⬜ 멤버가 아닌 사용자의 조직 접근 시도 (403)
  - ⬜ VIEWER role의 수정 시도 (403)
- ⬜ UI/UX 검증
  - ⬜ 페이지 로딩, 에러 메시지, 성공 메시지
  - ⬜ 반응형 디자인
- ⬜ 버그 수정 (발견 시)
- ⬜ Git commit: "test: Week 5 integration tests (Session 9)"
- ⬜ feature/organization → develop PR 준비

**예상 소요**: 4-6시간
**예상 완료**: 2025-11-25

---

### Week 6: 리스크 분석 (⬜ 0% 완료)

#### 4.1. RiskAnalysisResult 모델
- ⬜ 모델 설계
- ⬜ Migration 및 Admin
- ⬜ Serializer 및 API
- ⬜ Git commit: "feat(week6): add RiskAnalysisResult model"

**예상 소요**: 4-6시간

#### 4.2. Risk Analysis API (FastAPI)
- ⬜ `POST /llm/analyze_risk` 구현
- ⬜ 프롬프트 작성
- ⬜ 리스크 점수 산정
- ⬜ Git commit: "feat(week6): add risk analysis API"

**예상 소요**: 6-8시간

#### 4.3. Frontend Dashboard
- ⬜ RiskDashboard 페이지
- ⬜ 리스크 점수 차트
- ⬜ 리스크 항목 리스트
- ⬜ Git commit: "feat(week6): add risk analysis dashboard"

**예상 소요**: 8-10시간

**예상 완료**: 2026-01-04

---

### Week 7: LLM 비교 (⬜ 0% 완료)

#### 5.1. LLM Models
- ⬜ LLMModelConfig, LLMCallLog 모델 설계
- ⬜ Migration 및 Admin
- ⬜ Git commit: "feat(week7): add LLM config models"

**예상 소요**: 4-6시간

#### 5.2. LLM Comparison API (FastAPI)
- ⬜ `POST /llm/compare` 구현
- ⬜ 멀티 모델 호출 로직
- ⬜ 토큰/latency 측정
- ⬜ Git commit: "feat(week7): add LLM comparison API"

**예상 소요**: 6-8시간

#### 5.3. Frontend UI
- ⬜ ModelComparison 페이지
- ⬜ 비교 테이블
- ⬜ 평가 입력 UI
- ⬜ Git commit: "feat(week7): add model comparison UI"

**예상 소요**: 6-8시간

---

### Week 8: 크롤링/데이터 수집 시스템 (⬜ 0% 완료)

#### Session 13: 크롤링 시스템 구현 (⬜ 0% 완료)
- ⬜ Django Models (apps/backend_api/crawler/)
  - ⬜ DataSource 모델 (source_type, base_url, config)
  - ⬜ CrawlJob 모델 (status, schedule_type, documents_collected)
  - ⬜ CrawlLog 모델 (error tracking, metadata)
- ⬜ Migration 생성 및 실행
- ⬜ Admin 등록 (DataSourceAdmin, CrawlJobAdmin, CrawlLogAdmin)
- ⬜ Serializer 작성 (DataSourceSerializer, CrawlJobSerializer)
- ⬜ ViewSet 구현
  - ⬜ DataSourceViewSet (CRUD + trigger_crawl 액션)
  - ⬜ CrawlJobViewSet (list, retrieve, 상태 조회)
- ⬜ FastAPI Crawler Service (apps/ai-service/services/crawler.py)
  - ⬜ CourtPrecedentCrawler (대법원 판례 API)
  - ⬜ StatuteCrawler (법령 API)
- ⬜ FastAPI Router (apps/ai-service/routers/crawler.py)
  - ⬜ POST /v1/crawler/court-precedents
  - ⬜ POST /v1/crawler/statutes
  - ⬜ GET /v1/crawler/jobs/{job_id}/status
- ⬜ URLs 설정 (Django + FastAPI)
- ⬜ Git commit: "feat(week8): add crawling system (Session 13)"

**예상 소요**: 8-12시간

---

### Week 9: 고급 대시보드 (⬜ 0% 완료)

#### Session 14-A: 통계 API 구현 (⬜ 0% 완료)
- ⬜ Django Models 확장 (apps/backend_api/dashboard/)
  - ⬜ ProjectStats 모델 (total_documents, total_summaries, last_activity_at)
  - ⬜ OrganizationStats 모델 (monthly_document_count, top_active_users)
- ⬜ Migration 생성 및 실행
- ⬜ Serializer 작성
  - ⬜ DashboardOverviewSerializer
  - ⬜ ProjectStatsSerializer, OrganizationStatsSerializer
- ⬜ ViewSet 구현 (DashboardViewSet - 읽기 전용)
  - ⬜ GET /api/v1/dashboard/overview/
  - ⬜ GET /api/v1/dashboard/projects/{id}/stats/
  - ⬜ GET /api/v1/dashboard/organizations/{id}/stats/
  - ⬜ GET /api/v1/dashboard/activities/recent/
- ⬜ 통계 계산 로직 (utils.py)
- ⬜ Git commit: "feat(week9): add dashboard stats API (Session 14-A)"

**예상 소요**: 4-6시간

#### Session 14-B: 시각화 대시보드 UI (⬜ 0% 완료)
- ⬜ 라이브러리 설치 (recharts, react-grid-layout)
- ⬜ types.ts 타입 정의 (DashboardOverview, ProjectStats, ActivityItem)
- ⬜ API Client 함수 (getDashboardOverview, getProjectStats 등)
- ⬜ Dashboard 페이지 (Grid 레이아웃)
- ⬜ 차트 컴포넌트 (apps/web-frontend/src/components/Charts/)
  - ⬜ DocumentTrendChart (Line Chart - 문서 추이)
  - ⬜ DocumentTypeChart (Pie Chart - 문서 타입 분포)
  - ⬜ RiskHeatmap (리스크 점수 히트맵)
  - ⬜ OrganizationUsageChart (Bar Chart - 조직별 사용량)
- ⬜ StatCard 컴포넌트 (통계 카드)
- ⬜ ActivityTimeline 컴포넌트 (최근 활동)
- ⬜ CSS 스타일링
- ⬜ 라우팅 설정 (/dashboard)
- ⬜ Git commit: "feat(week9): add advanced dashboard UI (Session 14-B)"

**예상 소요**: 8-10시간

#### Session 14-C: Week 8-9 통합 테스트 (⬜ 0% 완료)
- ⬜ 크롤링 시스템 E2E
  - ⬜ DataSource 생성 및 크롤링 트리거
  - ⬜ CrawlLog 생성 확인
  - ⬜ 수집된 문서 Document 저장 확인
- ⬜ 대시보드 통계 API 테스트
  - ⬜ GET /api/v1/dashboard/overview/
  - ⬜ GET /api/v1/dashboard/projects/{id}/stats/
- ⬜ 대시보드 UI E2E
  - ⬜ 브라우저: http://localhost:5173/dashboard
  - ⬜ 통계 카드 표시 확인
  - ⬜ 차트 렌더링 확인 (Trend, Pie, Heatmap, Bar)
- ⬜ 차트 데이터 정확성 검증
- ⬜ 성능 테스트 (대시보드 로딩 < 2초, API < 500ms)
- ⬜ Git commit: "test: Week 8-9 integration tests (Session 14-C)"

**예상 소요**: 4-6시간

---

### Week 10: 최종 통합 (⬜ 0% 완료)

#### Session 15: Week 10 최종 E2E 테스트 및 배포
- ⬜ 전체 시스템 E2E 테스트
  - ⬜ **시나리오 1: 신규 사용자 전체 워크플로우**
    - ⬜ 회원가입 → 로그인
    - ⬜ Organization 생성 → Member 초대
    - ⬜ Project 생성
    - ⬜ Document 업로드 (PDF 계약서)
    - ⬜ 문서 전처리 완료 대기 (status: EMBEDDED)
    - ⬜ 문서 요약 생성
    - ⬜ 조항 추출
    - ⬜ 리스크 분석 (Phase 3-4)
    - ⬜ 여러 LLM 비교 (Phase 3-5)
    - ⬜ 크롤링 작업 실행 (Phase 3-6)
    - ⬜ 대시보드 통계 확인 (Phase 3-7)
  - ⬜ **시나리오 2: 협업 워크플로우**
    - ⬜ User A: Organization admin
    - ⬜ User B: Organization member (EDITOR role)
    - ⬜ User C: Organization member (VIEWER role)
    - ⬜ User A가 Document 업로드
    - ⬜ User B가 Document 수정 가능 확인
    - ⬜ User C가 Document 읽기만 가능 확인
    - ⬜ User C가 수정 시도 → 403 Forbidden
  - ⬜ **시나리오 3: RAG Chat + Precedent 검색 통합**
    - ⬜ Case 생성 및 파일 업로드
    - ⬜ RAG Chat: "이 사건과 유사한 판례는?"
    - ⬜ Precedent 목록 확인
    - ⬜ Precedent 상세 보기
    - ⬜ ChatHistory 저장 확인
  - ⬜ **시나리오 4: 성능 테스트**
    - ⬜ 대용량 PDF (5MB) 업로드 → 전처리 시간 측정
    - ⬜ 100개 Document 목록 조회 → 응답 속도 확인
    - ⬜ 동시 5개 RAG Chat 요청 → 처리 시간 측정
    - ⬜ LLM API latency 측정
- ⬜ 통합 테스트 결과 검증
  - ⬜ 모든 Phase 2 기능 정상 동작
  - ⬜ 모든 Phase 3 기능 정상 동작
  - ⬜ 권한 체크 정상 동작
  - ⬜ 에러 핸들링 정상 동작
  - ⬜ 성능 기준 충족 (RAG Chat < 5초)
- ⬜ 버그 수정 (발견 시)
  - ⬜ Critical/Major 버그 즉시 수정
  - ⬜ Minor 버그 Issue로 기록
- ⬜ 배포 준비
  - ⬜ Docker Compose 설정 확인
  - ⬜ 환경변수 정리 (.env.example 작성)
  - ⬜ README.md 업데이트 (프로젝트 소개, 기능, 설치, 실행)
  - ⬜ API 문서 작성 (Swagger/Postman)
- ⬜ Git commit: "test: Week 10 final E2E tests and deployment prep"
- ⬜ develop → main PR 준비

**예상 완료**: 2026-01-18

---

## 📊 진행도 요약

### Phase 2 (Django Migration) - ✅ 100% 완료
| 영역 | 기능 수 | 완료 | 진행도 |
|------|---------|------|--------|
| User/Auth | 8 | 8 | ✅ 100% |
| Precedent DB | 6 | 6 | ✅ 100% |
| Case Management | 8 | 8 | ✅ 100% |
| AI Service Proxy | 4 | 4 | ✅ 100% |
| AI Service (FastAPI) | 12 | 12 | ✅ 100% |
| Frontend | 10 | 10 | ✅ 100% |
| **총계** | **48** | **48** | **✅ 100%** |

### Phase 3 (확장 기능) - 🚧 53% 완료
| Week | 기능 | 완료 | 진행도 |
|------|------|------|--------|
| Week 0 | 현재 작업 마무리 | 4/4 | ✅ 100% |
| Week 1-2 | Document 관리 | 6/6 | ✅ 100% |
| Week 3-4 | Summary/Clauses | 5/5 | ✅ 100% |
| Week 5 | Organization | 2/3 | 🚧 67% |
| Week 6 | Risk Analysis | 0/3 | ⬜ 0% |
| Week 7 | LLM Comparison | 0/3 | ⬜ 0% |
| Week 8 | Crawling System | 0/1 | ⬜ 0% |
| Week 9 | Advanced Dashboard | 0/3 | ⬜ 0% |
| Week 10 | Final Integration | 0/1 | ⬜ 0% |
| **총계** | | **17/32** | **🚧 53%** |

---

## 🔗 관련 문서

- ⭐ [빠른 시작 가이드](./QUICK_START.md)
- ⭐ [Git 브랜치 전략](./GIT_BRANCH_STRATEGY.md)
- [프로젝트 상태](./PROJECT_STATUS.md)
- [병렬 작업 가이드](./PARALLEL_WORKFLOW_GUIDE.md)
- [사용 시나리오](./HOW_TO_USE.md)
- [설계문서](../설계문서.md)
