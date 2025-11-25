# 세션별 프롬프트 가이드

> **목적**: 각 세션에서 사용할 프롬프트를 미리 작성해둔 문서
> **사용법**: 복사 & 붙여넣기로 새 세션 시작

---

## 📋 기본 패턴

**매 세션마다 사용:**
```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md

현재 브랜치: [브랜치명]

[작업 설명]

다음을 해줘:
1. 현재 상태 파악
2. [구체적인 작업 내용]
3. 완료 후 결과 보고

시작하자.
```

---

## 🔄 Phase 2 완료 → Phase 3 시작

### Session 0-A: Phase 2 정리 및 develop PR

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md

Phase 2 작업 커밋 및 push

다음을 해줘:
1. 현재 상태 파악
2. QUICK_START.md Step 1 실행 (코드 커밋 및 push)
3. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ 코드 커밋 완료
- ✅ Push 완료
- ⚠️ develop PR은 사용자가 GitHub UI에서 직접 생성 및 머지
- ✅ `feature/document-management` 브랜치 생성

---

### Session 0-B: Phase 2 통합 테스트 (Week 0)

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md

현재 브랜치: develop

Week 0: Phase 2 통합 테스트 (기존 구현 기능 검증)

다음을 해줘:

1. 현재 상태 파악
   - Phase 2에서 구현된 기능 목록 확인
   - 서버 실행 상태 확인

2. 서버 실행
   - Django: cd apps/backend_api && python manage.py runserver
   - FastAPI: cd apps/ai-service && uvicorn main:app --reload --port 8001
   - Frontend: cd apps/web-frontend && npm run dev

3. Phase 2 기능 통합 테스트

   **테스트 1: 회원가입/로그인 E2E**
   - 브라우저: http://localhost:5173/
   - 회원가입 (email, password, full_name)
   - 로그인 (email, password)
   - JWT 토큰 발급 확인
   - /home 리다이렉트 확인
   - 로그아웃 확인

   **테스트 2: Case Management E2E**
   - /cases 페이지 이동
   - 사건 파일 업로드 (uploadCaseFiles)
   - 사건 목록 표시 확인
   - 사건 상세 보기
   - 사건 수정
   - 사건 삭제

   **테스트 3: Legal Research (RAG Chat) E2E**
   - /research 페이지 이동
   - 질문 입력: "횡령죄의 성립요건은?"
   - POST /api/v1/rag/chat 호출
   - 답변 표시 확인
   - 출처 판례 목록 확인
   - 판례 링크 클릭 동작 확인

   **테스트 4: Precedent 검색 E2E**
   - GET /api/v1/precedents/?case_number=2020도12345
   - GET /api/v1/precedents/?court=대법원&case_type=형사
   - 검색 결과 확인

   **테스트 5: AI Service 상태 확인**
   - GET /health
   - model_status: "available" 확인
   - ChromaDB 연결 확인 (precedent collection)

   **테스트 6: 에러 핸들링**
   - 로그인 없이 보호된 페이지 접근 (401 Unauthorized)
   - 잘못된 토큰으로 API 호출 (401)
   - 존재하지 않는 사건 ID로 조회 (404)

4. 성능 테스트
   - RAG Chat 응답 속도 측정 (< 5초 목표)
   - 파일 업로드 속도 측정
   - 페이지 로딩 속도 체크

5. 테스트 결과 보고
   - ✅ 성공한 테스트
   - ❌ 실패한 테스트
   - 발견된 버그 및 개선 사항

6. 버그 수정 (필요시)

7. Git commit: "test: Phase 2 integration tests (Week 0)"

8. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ 회원가입/로그인 동작 확인
- ✅ Case Management 전체 기능 확인
- ✅ RAG Chat 동작 확인 (Precedent 검색)
- ✅ AI Service 상태 확인
- ✅ Phase 2 모든 기능 검증 완료
- 🐛 발견된 버그 수정 완료

**사용자 작업 (테스트 후):**
- 📝 Phase 2가 정상 동작함을 확인했으면 Phase 3 진행 준비 완료

---

## 📦 Phase 3-1: Document 관리 시스템

### Session 1: Document 모델 구현 (Phase 1)

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md

현재 브랜치: feature/document-management

Phase 3-1 Phase 1: Document/DocumentChunk 모델 구현

다음을 해줘:
1. 현재 상태 파악
2. apps/backend_api/documents/models.py 구현
   - Document 모델 (id, user, title, doc_type, original_file, status, timestamps)
   - DocumentChunk 모델 (document FK, chunk_index, text, embedding_id)
3. Migration 생성 및 실행
4. Admin 등록
5. Git commit
6. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ Document/DocumentChunk 모델 생성
- ✅ Migration 실행 완료
- ✅ Admin 등록 완료

---

### Session 2-A: Django 파일 업로드 API (Phase 2-1)

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
@apps/backend_api/cases/serializers.py
@apps/backend_api/cases/views.py
@apps/backend_api/documents/models.py

현재 브랜치: feature/document-upload

Phase 3-1 Phase 2-1: Django 파일 업로드 API 구현

다음을 해줘:

1. 현재 상태 파악
   - cases/serializers.py의 CaseSerializer 패턴 확인
   - cases/views.py의 CaseViewSet 및 upload 액션 확인
   - documents/models.py의 Document 모델 필드 확인

2. apps/backend_api/documents/serializers.py 구현
   - CaseSerializer 패턴을 참고해서 DocumentSerializer 작성
   - 필수 필드: id, user, user_email, title, doc_type, status, file_size, created_at, updated_at
   - read_only_fields: id, user, user_email, file_size, created_at, updated_at
   - validate_title() 메서드 구현 (CaseSerializer 패턴 참조)
   - original_file 필드는 FileField로 처리

3. apps/backend_api/documents/views.py 구현
   - CaseViewSet 패턴을 참고해서 DocumentViewSet 작성
   - permission_classes = [IsAuthenticated]
   - get_queryset(): 현재 사용자의 Document만 반환
   - perform_create(): user 자동 설정

   **upload 액션 (cases/views.py의 upload 패턴 참조):**
   ```python
   @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
   def upload(self, request):
       # POST /api/v1/documents/upload/
       # Form Data: file, title, doc_type
       # 파일 검증: 최대 10MB, 확장자 .pdf/.docx/.txt
       # Document 생성 (status='UPLOADED')
       # AI Service 전처리 트리거는 나중에 구현
   ```

   **CRUD 액션:**
   - list(): GET /api/v1/documents/ (문서 목록)
   - retrieve(): GET /api/v1/documents/{id}/ (문서 상세)
   - destroy(): DELETE /api/v1/documents/{id}/ (문서 삭제)

4. apps/backend_api/documents/urls.py 생성
   - cases/urls.py 패턴 참조
   - router 등록

5. apps/backend_api/backend_api/urls.py 수정
   - documents URLs include 추가

6. Git commit: "feat(week1): add document upload API"
7. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ 파일 업로드 API 구현
- ✅ CRUD API 완성
- ✅ CaseViewSet 패턴과 일관성 유지

---

### Session 2-B: Frontend 업로드 UI (Phase 2-2)

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
@apps/web-frontend/src/api/client.ts
@apps/web-frontend/src/types.ts
@apps/web-frontend/src/pages/CaseManagement/CaseManagement.tsx
@apps/backend_api/documents/models.py

현재 브랜치: feature/document-ui

Phase 3-1 Phase 2-2: Frontend 업로드 UI 구현

다음을 해줘:

1. 현재 상태 파악
   - client.ts의 uploadCaseFiles(), getCases(), deleteCase() 패턴 확인
   - types.ts의 CaseAnalysis, CaseListItem 타입 확인
   - CaseManagement.tsx의 구조 및 state 관리 패턴 확인
   - Backend Document 모델의 필드 확인

2. src/types.ts에 타입 추가
   ```typescript
   // Backend Document 모델과 일치하는 타입
   export interface Document {
     id: string;
     user: string;  // UUID
     user_email?: string;
     title: string;
     doc_type: 'CASE' | 'CONTRACT' | 'STATUTE' | 'PRECEDENT' | 'OTHER';
     source_type: 'UPLOAD' | 'CRAWLED' | 'API';
     original_file?: string;  // File URL
     language: 'ko' | 'en';
     status: 'UPLOADED' | 'OCR_DONE' | 'PREPROCESSED' | 'EMBEDDED' | 'FAILED';
     file_size?: number;
     file_type?: string;
     page_count?: number;
     error_message?: string;
     created_at: string;
     updated_at: string;
   }

   export interface DocumentListResponse {
     count: number;
     next: string | null;
     previous: string | null;
     results: Document[];
   }

   export interface DocumentUploadResponse {
     id: string;
     title: string;
     status: string;
     message: string;
   }
   ```

3. src/api/client.ts에 함수 추가 (uploadCaseFiles 패턴 참조)
   ```typescript
   // 파일 업로드 (FormData 사용, Authorization 헤더 추가)
   async uploadDocument(
     file: File,
     title: string,
     docType: string,
     token: string
   ): Promise<DocumentUploadResponse> {
     const formData = new FormData();
     formData.append('file', file);
     formData.append('title', title);
     formData.append('doc_type', docType);

     const url = `${this.baseURL}/api/v1/documents/upload/`;
     // ... uploadCaseFiles 패턴 그대로 따라서 구현
   }

   // 문서 목록 조회 (getCases 패턴 참조)
   async getDocuments(token: string): Promise<DocumentListResponse> {
     return this.fetch<DocumentListResponse>('/api/v1/documents/', {}, token);
   }

   // 문서 상세 조회
   async getDocument(documentId: string, token: string): Promise<Document> {
     return this.fetch<Document>(`/api/v1/documents/${documentId}/`, {}, token);
   }

   // 문서 삭제 (deleteCase 패턴 참조)
   async deleteDocument(documentId: string, token: string): Promise<DeleteResponse> {
     return this.fetch<DeleteResponse>(`/api/v1/documents/${documentId}/`, {
       method: 'DELETE',
     }, token);
   }
   ```

4. apps/web-frontend/src/pages/DocumentManagement/ 디렉토리 및 파일 생성

   **DocumentManagement.tsx (CaseManagement.tsx 패턴 참조):**
   - CaseManagement.tsx의 구조 그대로 복사해서 Document용으로 수정
   - State 관리: documents, selectedDocument, isUploading, uploadError
   - useEffect로 loadDocuments() 호출
   - 파일 선택 핸들러, 업로드 핸들러, 삭제 핸들러
   - 업로드 모달 UI (showUploadModal)
   - 문서 목록 렌더링
   - react-icons 사용 (FiFolder, FiUpload, FiFileText, FiTrash2 등)

   **DocumentManagement.css:**
   - CaseManagement.css 복사해서 document-management 클래스로 수정

5. src/App.tsx에 라우팅 추가
   - import DocumentManagement
   - <Route path="/documents" element={<DocumentManagement />} />

6. Git commit: "feat(week2): add document upload UI"
7. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ 업로드 UI 완성 (CaseManagement 패턴과 일관성)
- ✅ API 함수 및 타입 정의 완료
- ✅ Backend API와 타입 일치

---

### Session 2-C: FastAPI OCR/전처리 파이프라인 (Phase 2-3)

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
@apps/ai-service/routers/analyze.py
@apps/ai-service/services/case_analyzer.py
@apps/backend_api/documents/models.py

현재 브랜치: feature/document-ocr

Phase 3-1 Phase 2-3: OCR/전처리 파이프라인 구현

다음을 해줘:

1. 현재 상태 파악
   - routers/analyze.py의 요청/응답 모델 패턴 확인
   - services/case_analyzer.py의 서비스 클래스 구조 확인
   - Backend Document 모델의 status 필드 확인

2. 의존성 확인 및 설치 (필요시)
   - pypdf (PDF 파싱)
   - python-docx (Docx 파싱)
   - langchain (TextSplitter)

3. apps/ai-service/services/document_processor.py 생성
   - case_analyzer.py 패턴 참고해서 DocumentProcessor 클래스 구현

   **필수 메서드:**
   ```python
   class DocumentProcessor:
       def __init__(self):
           from langchain.text_splitter import RecursiveCharacterTextSplitter
           self.text_splitter = RecursiveCharacterTextSplitter(
               chunk_size=1000,
               chunk_overlap=200
           )

       async def process_document(
           self, file_path: str, file_type: str
       ) -> Dict[str, Any]:
           # 파일 타입 별 처리
           # chunks 생성
           # return {text, chunks, page_count}
   ```

4. apps/ai-service/routers/preprocess.py 생성
   - analyze.py의 router 패턴 참고

   **Request/Response 모델:**
   ```python
   class PreprocessRequest(BaseModel):
       document_id: str
       file_path: str
       file_type: str

   class PreprocessResponse(BaseModel):
       document_id: str
       status: str
       chunk_count: int
       chunks: List[Dict]
   ```

   **API:**
   ```python
   @router.post("/document")
   async def preprocess_document(request: PreprocessRequest):
       # DocumentProcessor 사용
   ```

5. apps/ai-service/main.py 수정
   - preprocess router include

6. Git commit: "feat(week1): add OCR and preprocessing pipeline"
7. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ OCR 파이프라인 완성
- ✅ 전처리 API 구현 (FastAPI 패턴 일관성)

---

### Session 2-D: Week 1-2 통합 테스트 (Document 관리 시스템)

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
를 참조해서
현재 브랜치: feature/document-management

Phase 3-1 통합 테스트 (Document 업로드 → OCR → 임베딩)

다음을 해줘:

1. 현재 상태 파악
   - 모든 서브 브랜치가 feature/document-management에 머지되었는지 확인
   - Django, FastAPI, Frontend 서버 실행 상태 확인

2. 서버 실행 (필요시)
   - Django: cd apps/backend_api && python manage.py runserver
   - FastAPI: cd apps/ai-service && uvicorn main:app --reload --port 8001
   - Frontend: cd apps/web-frontend && npm run dev

3. 통합 테스트 실행

   **테스트 1: Django API 테스트**
   - GET /api/v1/documents/ (빈 목록 확인)
   - GET /api/health/ (서버 상태 확인)

   **테스트 2: 파일 업로드 E2E**
   - 브라우저: http://localhost:5173/login
   - 로그인 (테스트 계정 또는 신규 가입)
   - /documents 페이지로 이동
   - PDF 파일 업로드 (title: "테스트 계약서", doc_type: "CONTRACT")
   - 업로드 성공 확인 (status: "UPLOADED")
   - 문서 목록에서 새 문서 확인

   **테스트 3: FastAPI 전처리 API 테스트**
   - Django에서 업로드한 문서의 file_path 확인
   - POST /v1/preprocess/document 호출
   - Response: chunk_count, status 확인

   **테스트 4: 에러 핸들링 테스트**
   - 잘못된 파일 업로드 (확장자 .exe 등)
   - 10MB 초과 파일 업로드
   - 빈 제목으로 업로드
   - 각각 에러 메시지 확인

4. 테스트 결과 보고
   - ✅ 성공한 테스트
   - ❌ 실패한 테스트 (에러 메시지 포함)
   - 발견된 버그 및 수정 필요 사항

5. 버그 수정 (필요시)
   - 테스트 실패 원인 분석
   - 코드 수정
   - 재테스트

6. Git commit: 테스트 관련 파일은 커밋하지 않고 수정한 부분에 맞게 수정했다고 커밋 하면됨. 커밋 메세지에 커밋한 사람은 추가하지 않고 이모티콘도 제외

7. 완료 후 결과 보고

시작하자.
```

**사용자 작업 (테스트 전):**
- ⚠️ 각 서브 브랜치 → feature/document-management PR 생성 및 머지 (사용자가 직접)

**사용자 작업 (테스트 후):**
- ⚠️ feature/document-management → develop PR 생성 및 머지 (사용자가 직접)

**예상 결과:**
- ✅ Django 파일 업로드 API 동작 확인
- ✅ Frontend 업로드 UI 동작 확인
- ✅ FastAPI 전처리 파이프라인 동작 확인
- ✅ E2E 워크플로우 검증 완료
- ✅ 버그 발견 및 수정 (있을 경우)

---

## 📊 Phase 3-2: AI 분석 결과 저장

### Session 4: Summary/KeyClause 모델 구현

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
을 먼저 참조하고 
현재 브랜치가 어떤지, 이전 상황이 완료가 되었는지, develop으로 가서 pull도 받고,
브랜치: feature/ai-analysis-storage

Phase 3-2 Phase 1: Summary/KeyClause 모델 구현

다음을 해줘:
1. 현재 상태 파악
2. apps/backend_api/documents/models.py에 추가
   - Summary 모델 (document FK, llm_model, summary_type, content, meta)
   - KeyClause 모델 (document FK, clause_type, title, content, importance_score)
3. Migration 생성 및 실행
4. Admin 등록
5. Serializer 작성
6. Git commit
7. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ Summary/KeyClause 모델 생성
- ✅ Migration 완료

---

### Session 5-A: Django Summary/Clause API

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md

현재 브랜치: feature/ai-analysis-storage

Phase 3-2 Phase 2-1: Django Summary/Clause API 구현

다음을 해줘:
1. 현재 상태 파악
2. ViewSet 구현
   - GET /api/v1/documents/{id}/summary/
   - GET /api/v1/documents/{id}/clauses/
   - POST /api/v1/documents/{id}/analyze/
3. AI Service 호출 로직
4. 결과 저장 로직
5. Git commit
6. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ Summary/Clause API 완성

---

### Session 5-B: FastAPI LLM APIs

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
를 참조한 후 현재 상황을 확인하고 다음을 진행해줘.
현재 브랜치: feature/ai-analysis-storage

Phase 3-2 Phase 2-2: FastAPI LLM APIs 구현

다음을 해줘:
1. 현재 상태 파악
2. apps/ai-service/services/summarizer.py 구현
3. apps/ai-service/services/clause_extractor.py 구현
4. apps/ai-service/routers/llm.py 구현
   - POST /v1/llm/summarize
   - POST /v1/llm/clauses
5. 프롬프트 템플릿 작성
6. Git commit
7. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ LLM API 완성
- ✅ 요약/조항 추출 가능

---

### Session 5-C: Frontend 분석 UI

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
를 참조한 후 현재 상황을 확인하고 다음을 진행해줘.
현재 브랜치: feature/ai-analysis-storage

Phase 3-2 Phase 2-3: Frontend 문서 분석 UI 구현

다음을 해줘:
1. 현재 상태 파악
2. DocumentDetail 페이지 확장
3. SummarySection 컴포넌트 추가
4. ClauseList 컴포넌트 추가
5. "요약 생성" / "조항 추출" 버튼 추가
6. API 연동
7. Git commit
8. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ 문서 분석 UI 완성

---

### Session 5-D: Week 3-4 통합 테스트 (문서 분석 시스템)

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
를 참조해서 아래의 사항을 진행해줘
현재 브랜치: feature/ai-analysis-storage

Phase 3-2 통합 테스트 (문서 요약 → 조항 추출 → 저장)

다음을 해줘:

1. 현재 상태 파악
   - 모든 서브 브랜치가 feature/ai-analysis-storage에 머지되었는지 확인
   - 서버 실행 상태 확인

2. 서버 실행 (필요시)

3. 통합 테스트 실행

   **테스트 1: 문서 요약 E2E**
   - 브라우저: 기존 업로드된 문서 선택
   - DocumentDetail 페이지 이동
   - "요약 생성" 버튼 클릭
   - API: POST /api/v1/documents/{id}/analyze/
   - FastAPI: POST /v1/llm/summarize 호출 확인
   - Summary 저장 확인
   - 브라우저에 요약 텍스트 표시 확인

   **테스트 2: 조항 추출 E2E**
   - "조항 추출" 버튼 클릭
   - API: POST /api/v1/documents/{id}/analyze/
   - FastAPI: POST /v1/llm/clauses 호출 확인
   - KeyClause 목록 저장 확인
   - 브라우저에 조항 리스트 표시 확인

   **테스트 3: 기존 결과 로드**
   - 페이지 새로고침
   - GET /api/v1/documents/{id}/summary/
   - GET /api/v1/documents/{id}/clauses/
   - 기존 분석 결과 로드 확인

   **테스트 4: LLM 응답 품질 확인**
   - 요약: 핵심 내용이 잘 요약되었는지 확인
   - 조항: 계약 조항이 올바르게 추출되었는지 확인
   - importance_score 정상 범위 (0-100) 확인

   **테스트 5: 에러 핸들링**
   - LLM API 타임아웃 시나리오
   - 잘못된 document_id로 요청
   - 각각 에러 메시지 확인

4. 테스트 결과 보고
   - ✅ 성공한 테스트
   - ❌ 실패한 테스트
   - LLM 응답 품질 평가

5. 버그 수정 (필요시)

6. Git commit: "test: Week 3-4 integration tests"

7. 완료 후 결과 보고

시작하자.
```

**사용자 작업 (테스트 전):**
- ⚠️ 각 서브 브랜치 → feature/ai-analysis-storage PR 생성 및 머지 (사용자가 직접)

**사용자 작업 (테스트 후):**
- ⚠️ feature/ai-analysis-storage → develop PR 생성 및 머지 (사용자가 직접)

**예상 결과:**
- ✅ 문서 요약 API 동작 확인
- ✅ 조항 추출 API 동작 확인
- ✅ 분석 결과 저장 및 로드 확인
- ✅ LLM 응답 품질 검증
- ✅ E2E 워크플로우 검증 완료

---

## 🏢 Phase 3-3: Organization/Project

### Session 6: Organization 모델 구현

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
을 참조해서 현재 상황은 파악하고 다음을 진행해줘.

현재 브랜치를 확인하고 develop 브랜치로 이동 후 pull 받고 이어서 진행.
브랜치 : feature/organization

Phase 3-3 Phase 1: Organization 모델 구현

다음을 해줘:
1. 현재 상태 파악
2. apps/backend_api/organizations/models.py 구현
   - Organization 모델
   - Membership 모델
   - Project 모델
3. Migration 생성 및 실행
4. Admin 등록
5. Git commit
6. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ Organization, Membership, Project 모델 구현 완료
- ✅ Migration 생성 및 DB 테이블 생성 (organizations, memberships, projects)
- ✅ Admin 페이지 등록 (OrganizationAdmin, MembershipAdmin, ProjectAdmin)
- ✅ Git commit: "feat(week5): add Organization, Membership, Project models (Session 6)"

**완료 일시:** 2025-11-24
**커밋:** `8a953974`

---

### Session 7: Organization CRUD API 구현

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
을 참조해서 현재 상황을 파악하고 다음을 진행해줘.

현재 브랜치: feature/organization

Phase 3-3 Phase 2: Organization/Member/Project CRUD API 구현

다음을 해줘:
1. 현재 상태 파악
   - Session 6 완료 여부 확인 (Organization 모델)

2. Serializer 작성 (apps/backend_api/organizations/serializers.py)
   - OrganizationSerializer
   - MembershipSerializer
   - ProjectSerializer
   - 참조: apps/backend_api/documents/serializers.py

3. ViewSet 구현 (apps/backend_api/organizations/views.py)
   - OrganizationViewSet (CRUD)
     - list, create, retrieve, update, destroy
     - members 액션: GET /organizations/{id}/members/
     - add_member 액션: POST /organizations/{id}/members/
     - remove_member 액션: DELETE /organizations/{id}/members/{user_id}/
     - update_member_role 액션: PUT /organizations/{id}/members/{user_id}/
   - ProjectViewSet (CRUD)
     - list, create, retrieve, update, destroy
     - 조직별 프로젝트 필터링
   - 권한 체크 로직
     - IsOrganizationAdmin: admin만 멤버 추가/삭제/역할 변경 가능
     - IsOrganizationMember: 멤버만 조직/프로젝트 조회 가능
     - IsProjectEditor: EDITOR 이상만 프로젝트 수정 가능

4. URLs 설정 (apps/backend_api/organizations/urls.py)
   - router 설정
   - app_name = 'organizations'

5. Main URLs 통합 (apps/backend_api/api/urls.py)
   - path('organizations/', include('organizations.urls'))

6. Git commit

7. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ OrganizationSerializer, MembershipSerializer, ProjectSerializer 구현
- ✅ OrganizationViewSet, ProjectViewSet 구현 (CRUD + 멤버 관리)
- ✅ 권한 체크 로직 구현 (IsOrganizationAdmin, IsOrganizationMember, IsProjectEditor)
- ✅ URLs 설정 및 라우팅 완료
- ✅ API 엔드포인트 생성:
  - GET/POST /api/v1/organizations/
  - GET/PUT/DELETE /api/v1/organizations/{id}/
  - GET /api/v1/organizations/{id}/members/
  - POST /api/v1/organizations/{id}/members/
  - DELETE /api/v1/organizations/{id}/members/{user_id}/
  - PUT /api/v1/organizations/{id}/members/{user_id}/
  - GET/POST /api/v1/projects/
  - GET/PUT/DELETE /api/v1/projects/{id}/
- ✅ Git commit: "feat(week5): add Organization and Project APIs (Session 7)"

---

### Session 8: Organization UI 구현

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
을 참조해서 현재 상황을 파악하고 다음을 진행해줘.

현재 브랜치: feature/organization

Phase 3-3 Phase 3: Organization UI 구현

다음을 해줘:
1. 현재 상태 파악
   - Session 7 완료 여부 확인 (Organization API)

2. types.ts 타입 정의 (apps/web-frontend/src/types.ts)
   - Organization 인터페이스
   - Membership 인터페이스
   - Project 인터페이스
   - MemberRole 타입
   - API 응답 타입

3. API Client 함수 추가 (apps/web-frontend/src/api/client.ts)
   - getOrganizations, createOrganization, getOrganization, updateOrganization, deleteOrganization
   - getOrganizationMembers, addMember, removeMember, updateMemberRole
   - getProjects, createProject, getProject, updateProject, deleteProject
   - 참조: 기존 Document API 함수

4. Organizations 페이지 (apps/web-frontend/src/pages/Organizations.tsx)
   - 조직 목록 표시
   - 조직 생성 모달
   - 조직 상세 보기
   - 멤버 관리 UI

5. MemberManagement 컴포넌트 (apps/web-frontend/src/components/MemberManagement.tsx)
   - 멤버 목록 표시
   - 멤버 초대 폼
   - 역할 변경 드롭다운
   - 멤버 제거 버튼

6. Projects 페이지 (apps/web-frontend/src/pages/Projects.tsx)
   - 프로젝트 목록 표시 (조직별 필터링)
   - 프로젝트 생성 모달
   - 프로젝트 상세 보기

7. CSS 스타일링
   - Organizations.css
   - MemberManagement.css
   - Projects.css

8. App.tsx 라우팅 추가
   - /organizations
   - /projects

9. Git commit

10. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ types.ts 타입 정의 (Organization, Membership, Project)
- ✅ API Client 함수 구현 (조직/멤버/프로젝트 CRUD)
- ✅ Organizations 페이지 구현 (목록, 생성, 상세)
- ✅ MemberManagement 컴포넌트 구현 (멤버 관리)
- ✅ Projects 페이지 구현 (목록, 생성, 상세)
- ✅ CSS 스타일링 완료
- ✅ 라우팅 설정 (/organizations, /projects)
- ✅ Git commit: "feat(week5): add Organization management UI (Session 8)"

---

### Session 9: Week 5 통합 테스트 (Organization/Project)

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
을 참조해서 현재 상황을 파악하고 다음을 진행해줘.

현재 브랜치: feature/organization

Phase 3-3 통합 테스트 (Organization → Member 관리 → Project)

다음을 해줘:

1. 현재 상태 파악
   - Session 6, 7, 8 완료 여부 확인
   - Django 서버 실행 상태 확인 (http://localhost:8000)
   - Frontend 서버 실행 상태 확인 (http://localhost:3000)

2. E2E 통합 테스트 실행

   **테스트 1: Organization CRUD (API + UI)**
   - POST /api/v1/organizations/ (조직 생성)
     - name: "테스트 법률사무소"
   - GET /api/v1/organizations/ (조직 목록)
   - GET /api/v1/organizations/{id}/ (조직 상세)
   - PUT /api/v1/organizations/{id}/ (조직 수정)
     - name: "수정된 법률사무소"
   - 브라우저 UI에서도 동일 테스트 (/organizations)
     - 조직 생성 버튼 클릭
     - 조직 목록 확인
     - 조직 상세 페이지 이동

   **테스트 2: Member 관리 (API + UI)**
   - 사전 준비: 테스트 사용자 2명 생성 (user1, user2)
   - POST /api/v1/organizations/{id}/members/ (멤버 초대)
     - user_id: user2의 ID
     - role: EDITOR
   - GET /api/v1/organizations/{id}/members/ (멤버 목록)
     - creator는 ADMIN으로 자동 추가되어야 함
     - user2가 EDITOR로 표시되어야 함
   - PUT /api/v1/organizations/{id}/members/{user_id}/ (역할 변경)
     - role: ADMIN으로 변경
   - DELETE /api/v1/organizations/{id}/members/{user_id}/ (멤버 제거)
   - 브라우저 UI에서도 동일 테스트
     - 멤버 초대 폼
     - 멤버 목록 표시
     - 역할 변경 드롭다운
     - 멤버 제거 버튼

   **테스트 3: Project CRUD (API + UI)**
   - POST /api/v1/projects/ (프로젝트 생성 with organization)
     - organization: 테스트 조직 ID
     - name: "계약서 검토 프로젝트"
     - description: "2025년 상반기 계약서 검토"
   - GET /api/v1/projects/ (내 프로젝트 목록)
   - GET /api/v1/projects/{id}/ (프로젝트 상세)
   - PUT /api/v1/projects/{id}/ (프로젝트 수정)
   - 브라우저 UI에서도 동일 테스트 (/projects)

   **테스트 4: 권한 체크 (중요!)**
   - 다른 사용자로 로그인 (user3)
   - 다른 조직의 프로젝트 접근 시도 → 403 Forbidden 확인
   - 멤버가 아닌 사용자의 조직 접근 시도 → 403 확인
   - VIEWER role 사용자로 로그인
     - 조직 수정 시도 → 403 확인
     - 프로젝트 수정 시도 → 403 확인
     - 멤버 추가 시도 → 403 확인

   **테스트 5: UI/UX 검증**
   - 모든 페이지 로딩 확인
   - 에러 메시지 표시 확인
   - 성공 메시지 표시 확인
   - 반응형 디자인 확인 (브라우저 크기 조절)

3. 테스트 결과 보고
   - ✅ 성공한 테스트 (API/UI 구분)
   - ❌ 실패한 테스트 (에러 메시지 포함)
   - 권한 체크 정상 동작 확인
   - 발견된 버그 목록

4. 버그 수정 (발견 시)
   - Critical/Major 버그 즉시 수정
   - Minor 버그는 Issue로 기록

5. Git commit (테스트 완료 후)
   - test: Week 5 integration tests (Session 9)

6. feature/organization → develop PR 준비
   - 변경사항 요약
   - 테스트 결과 요약

시작하자.
```

**예상 결과:**
- ✅ Organization CRUD E2E 테스트 완료 (API + UI)
- ✅ Member 관리 E2E 테스트 완료 (초대, 역할 변경, 제거)
- ✅ Project CRUD E2E 테스트 완료
- ✅ 권한 체크 검증 완료 (403 Forbidden)
- ✅ UI/UX 검증 완료
- ✅ 버그 수정 완료 (발견 시)
- ✅ Git commit: "test: Week 5 integration tests (Session 9)"
- ✅ feature/organization → develop PR 준비 완료

**사용자 작업 (테스트 후):**
- ⚠️ feature/organization → develop PR 생성 및 머지 (사용자가 직접)

---

## ⚠️ Phase 3-4: 리스크 분석

### Session 10: Risk Analysis 구현

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md

현재 브랜치: feature/risk-analysis

Phase 3-4: 리스크 분석 시스템 구현

다음을 해줘:
1. 현재 상태 파악
2. RiskAnalysisResult 모델 (Django)
3. POST /v1/llm/analyze_risk API (FastAPI)
4. RiskDashboard 페이지 (Frontend)
5. 리스크 점수 산정 로직
6. 리스크 항목 시각화
7. Git commit 및 push
8. 완료 후 결과 보고

시작하자.
```

**사용자 작업:**
- ⚠️ feature/risk-analysis → develop PR 생성 및 머지 (사용자가 직접)

**예상 결과:**
- ✅ 리스크 분석 시스템 완성

---

## 🔄 Phase 3-5: LLM 비교

### Session 11: LLM Comparison 구현

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md

현재 브랜치: feature/llm-comparison

Phase 3-5: LLM 비교 시스템 구현

다음을 해줘:
1. 현재 상태 파악
2. LLMModelConfig, LLMCallLog 모델 (Django)
3. POST /v1/llm/compare API (FastAPI)
4. ModelComparison 페이지 (Frontend)
5. 멀티 모델 호출 로직
6. 토큰/latency 측정
7. 비교 테이블 UI
8. Git commit 및 push
9. 완료 후 결과 보고

시작하자.
```

**사용자 작업:**
- ⚠️ feature/llm-comparison → develop PR 생성 및 머지 (사용자가 직접)

**예상 결과:**
- ✅ LLM 비교 시스템 완성

---

---

## 🕷️ Phase 3-6: 크롤링/데이터 수집 시스템

### Session 13: 크롤링 시스템 구현

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
@docs/설계문서.md

현재 브랜치: feature/crawling-system

Phase 3-6: 크롤링/데이터 수집 시스템 구현

다음을 해줘:

1. 현재 상태 파악
   - Phase 3-5 (LLM Comparison) 완료 확인
   - develop 브랜치로 이동 후 pull
   - feature/crawling-system 브랜치 생성

2. Django Models 구현 (apps/backend_api/crawler/)
   **DataSource 모델:**
   - id (UUID), name, source_type (COURT_API/STATUTE_API/WEB_CRAWL)
   - base_url, api_key_required, is_active
   - config (JSONField - 크롤링 설정)
   - created_at, updated_at

   **CrawlJob 모델:**
   - id (UUID), data_source (FK), status (PENDING/RUNNING/COMPLETED/FAILED)
   - schedule_type (MANUAL/DAILY/WEEKLY)
   - last_run_at, next_run_at
   - documents_collected (IntegerField), errors (JSONField)
   - created_at, updated_at

   **CrawlLog 모델:**
   - id (UUID), crawl_job (FK), document (FK - nullable)
   - status, error_message, metadata (JSONField)
   - created_at

3. Migration 생성 및 실행
   - python manage.py makemigrations crawler
   - python manage.py migrate

4. Admin 등록 (apps/backend_api/crawler/admin.py)
   - DataSourceAdmin (수동 트리거 버튼 추가)
   - CrawlJobAdmin (CrawlLogInline 포함)
   - CrawlLogAdmin

5. Serializer 작성 (apps/backend_api/crawler/serializers.py)
   - DataSourceSerializer
   - CrawlJobSerializer
   - CrawlLogSerializer

6. ViewSet 구현 (apps/backend_api/crawler/views.py)
   - DataSourceViewSet (CRUD)
     - trigger_crawl 액션: POST /api/v1/data-sources/{id}/crawl/
   - CrawlJobViewSet (list, retrieve)

7. FastAPI Crawler Service (apps/ai-service/services/crawler.py)
   - CourtPrecedentCrawler 클래스
     - crawl_precedents() 메서드
     - 대법원 판례 API 연동 (mock 또는 실제 API)
   - StatuteCrawler 클래스
     - crawl_statutes() 메서드
     - 법령 API 연동

8. FastAPI Router (apps/ai-service/routers/crawler.py)
   - POST /v1/crawler/court-precedents
     - 입력: { data_source_id, filters: { start_date, end_date, case_type } }
     - 출력: { job_id, status, documents_collected }
   - POST /v1/crawler/statutes
   - GET /v1/crawler/jobs/{job_id}/status

9. URLs 설정
   - Django: crawler/urls.py 생성 및 main urls 등록
   - FastAPI: main.py에 crawler router 등록

10. Git commit: "feat(week8): add crawling system (Session 13)"

11. 완료 후 결과 보고

시작하자.
```

**사용자 작업:**
- ⚠️ feature/crawling-system → develop PR 생성 및 머지 (사용자가 직접)

**예상 결과:**
- ✅ 크롤링 모델 및 API 구현
- ✅ 대법원 판례/법령 수집 기능
- ✅ Admin 인터페이스에서 수동 트리거 가능

---

## 📊 Phase 3-7: 고급 대시보드

### Session 14-A: 통계 API 구현

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md

현재 브랜치: feature/advanced-dashboard

Phase 3-7 Phase 1: 통계 API 구현

다음을 해줘:

1. 현재 상태 파악
   - Phase 3-6 (Crawling) 완료 확인
   - develop 브랜치로 이동 후 pull
   - feature/advanced-dashboard 브랜치 생성

2. Django Models 확장 (apps/backend_api/dashboard/)
   **ProjectStats 모델:**
   - project (OneToOneField)
   - total_documents, total_summaries, total_clauses
   - total_risk_analyses, total_searches
   - last_activity_at, updated_at

   **OrganizationStats 모델:**
   - organization (OneToOneField)
   - total_projects, total_members, total_documents
   - monthly_document_count (JSONField)
   - top_active_users (JSONField)
   - updated_at

3. Migration 생성 및 실행

4. Serializer 작성 (apps/backend_api/dashboard/serializers.py)
   - DashboardOverviewSerializer
   - ProjectStatsSerializer
   - OrganizationStatsSerializer
   - RecentActivitySerializer

5. ViewSet 구현 (apps/backend_api/dashboard/views.py)
   - DashboardViewSet (읽기 전용, ViewSet 상속)
     - overview 액션: GET /api/v1/dashboard/overview/
       - 전체 통계 (문서 수, 분석 수, 사용자 활동)
     - project_stats 액션: GET /api/v1/dashboard/projects/{id}/stats/
     - organization_stats 액션: GET /api/v1/dashboard/organizations/{id}/stats/
     - recent_activities 액션: GET /api/v1/dashboard/activities/recent/
       - 최근 10개 활동

6. 통계 계산 로직 (apps/backend_api/dashboard/utils.py)
   - calculate_project_stats(project_id)
   - calculate_organization_stats(organization_id)
   - get_recent_activities(user, limit=10)

7. URLs 설정
   - dashboard/urls.py 생성
   - main urls에 등록

8. Git commit: "feat(week9): add dashboard stats API (Session 14-A)"

9. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ 통계 모델 및 API 구현
- ✅ 프로젝트/조직 통계 조회 가능

---

### Session 14-B: 시각화 대시보드 UI

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
@apps/web-frontend/src/pages/Home/Home.tsx

현재 브랜치: feature/advanced-dashboard

Phase 3-7 Phase 2: 시각화 대시보드 UI 구현

다음을 해줘:

1. 현재 상태 파악
   - Session 14-A 완료 확인 (통계 API)

2. 라이브러리 설치
   - cd apps/web-frontend
   - npm install recharts
   - npm install react-grid-layout

3. types.ts 타입 정의
   - DashboardOverview 인터페이스
   - ProjectStats, OrganizationStats 인터페이스
   - ActivityItem 인터페이스
   - ChartDataPoint 인터페이스

4. API Client 함수 (apps/web-frontend/src/api/client.ts)
   - getDashboardOverview(token)
   - getProjectStats(projectId, token)
   - getOrganizationStats(organizationId, token)
   - getRecentActivities(token)

5. Dashboard 페이지 (apps/web-frontend/src/pages/Dashboard/)
   - Dashboard.tsx (메인 대시보드)
     - Grid 레이아웃 (3x3)
     - 통계 카드 섹션 (상단 3개)
     - 차트 섹션 (중앙 6개)
     - 최근 활동 섹션 (우측 사이드바)

6. 차트 컴포넌트 (apps/web-frontend/src/components/Charts/)
   - DocumentTrendChart.tsx (문서 업로드 추이 - LineChart)
     - 최근 30일 문서 수 추이
     - recharts의 LineChart, Line, XAxis, YAxis 사용
   - DocumentTypeChart.tsx (문서 타입 분포 - PieChart)
     - CASE/CONTRACT/STATUTE 비율
     - recharts의 PieChart, Pie, Cell 사용
   - RiskHeatmap.tsx (리스크 점수 히트맵)
     - 문서별 리스크 점수 시각화
   - OrganizationUsageChart.tsx (조직별 사용량 - BarChart)
     - 조직별 문서/분석 수

7. 통계 카드 컴포넌트 (apps/web-frontend/src/components/StatCard/)
   - StatCard.tsx
     - props: { icon, title, value, change, color }
     - 아이콘, 제목, 값, 변화율 표시
     - react-icons 사용

8. 최근 활동 컴포넌트 (apps/web-frontend/src/components/ActivityTimeline/)
   - ActivityTimeline.tsx
     - 시간 순 활동 목록
     - 활동 타입별 아이콘
     - "더 보기" 버튼

9. CSS 스타일링
   - Dashboard.css (Grid 레이아웃, 카드 스타일)
   - Charts/Charts.css
   - StatCard.css
   - ActivityTimeline.css

10. App.tsx 라우팅 수정
    - /dashboard 경로 추가
    - Home을 Dashboard로 리디렉션 (선택)

11. Git commit: "feat(week9): add advanced dashboard UI (Session 14-B)"

12. 완료 후 결과 보고

시작하자.
```

**예상 결과:**
- ✅ 차트 기반 대시보드 완성
- ✅ 통계 카드, 활동 타임라인
- ✅ 반응형 그리드 레이아웃

---

### Session 14-C: Week 8-9 통합 테스트

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md

현재 브랜치: feature/advanced-dashboard

Phase 3-7 통합 테스트 (크롤링 + 대시보드)

다음을 해줘:

1. 현재 상태 파악
   - Session 13, 14-A, 14-B 완료 확인

2. 서버 실행 (필요시)
   - Django, FastAPI, Frontend

3. 통합 테스트 실행

   **테스트 1: 크롤링 시스템 E2E**
   - Admin 페이지에서 DataSource 생성
   - 크롤링 Job 수동 트리거
   - POST /api/v1/data-sources/{id}/crawl/
   - FastAPI: POST /v1/crawler/court-precedents 호출 확인
   - CrawlLog 생성 확인
   - 수집된 문서 Document 테이블 저장 확인

   **테스트 2: 대시보드 통계 API**
   - GET /api/v1/dashboard/overview/
     - total_documents, total_users 확인
   - GET /api/v1/dashboard/projects/{id}/stats/
   - GET /api/v1/dashboard/activities/recent/

   **테스트 3: 대시보드 UI E2E**
   - 브라우저: http://localhost:5173/dashboard
   - 통계 카드 표시 확인
   - DocumentTrendChart 렌더링 확인
   - DocumentTypeChart (Pie Chart) 확인
   - RiskHeatmap 확인
   - ActivityTimeline 표시 확인

   **테스트 4: 차트 데이터 정확성**
   - 수동으로 문서 5개 업로드
   - 대시보드 새로고침
   - 문서 수 증가 확인
   - 차트 데이터 업데이트 확인

   **테스트 5: 성능 테스트**
   - 대시보드 로딩 속도 (< 2초)
   - 차트 렌더링 속도
   - 통계 API 응답 속도 (< 500ms)

4. 테스트 결과 보고

5. 버그 수정 (필요시)

6. Git commit: "test: Week 8-9 integration tests (Session 14-C)"

7. feature/advanced-dashboard → develop PR 준비

시작하자.
```

**사용자 작업 (테스트 후):**
- ⚠️ feature/advanced-dashboard → develop PR 생성 및 머지 (사용자가 직접)

**예상 결과:**
- ✅ 크롤링 시스템 동작 확인
- ✅ 대시보드 API 정상 동작
- ✅ 차트 시각화 정상 렌더링
- ✅ 통계 데이터 정확성 검증

---

## 🎉 최종 통합

### Session 15: Week 10 최종 E2E 테스트 및 배포 준비

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md

현재 브랜치: develop

Week 7: 전체 E2E 테스트 및 배포 준비

다음을 해줘:

1. 현재 상태 파악
   - Phase 3 모든 기능 구현 완료 확인
   - 모든 feature 브랜치가 develop에 머지되었는지 확인

2. 서버 실행 및 상태 확인
   - Django, FastAPI, Frontend 모두 실행
   - 데이터베이스 마이그레이션 최신 상태 확인

3. 전체 시스템 E2E 테스트

   **시나리오 1: 신규 사용자 전체 워크플로우**
   - 회원가입 → 로그인
   - Organization 생성 → Member 초대
   - Project 생성
   - Document 업로드 (PDF 계약서)
   - 문서 전처리 완료 대기 (status: EMBEDDED)
   - 문서 요약 생성
   - 조항 추출
   - 리스크 분석 (Phase 3-4)
   - 여러 LLM 비교 (Phase 3-5)
   - 크롤링 작업 실행 (Phase 3-6)
   - 대시보드 통계 확인 (Phase 3-7)

   **시나리오 2: 기존 사용자 협업 워크플로우**
   - User A: Organization admin
   - User B: Organization member (EDITOR role)
   - User C: Organization member (VIEWER role)
   - User A가 Document 업로드
   - User B가 Document 수정 가능 확인
   - User C가 Document 읽기만 가능 확인
   - User C가 수정 시도 → 403 Forbidden

   **시나리오 3: RAG Chat + Precedent 검색 통합**
   - Case 생성 및 파일 업로드
   - RAG Chat: "이 사건과 유사한 판례는?"
   - Precedent 목록 확인
   - Precedent 상세 보기
   - ChatHistory 저장 확인

   **시나리오 4: 성능 테스트**
   - 대용량 PDF (5MB) 업로드 → 전처리 시간 측정
   - 100개 Document 목록 조회 → 응답 속도 확인
   - 동시 5개 RAG Chat 요청 → 처리 시간 측정
   - LLM API latency 측정

4. 통합 테스트 결과 검증
   - ✅ 모든 Phase 2 기능 정상 동작
   - ✅ 모든 Phase 3 기능 정상 동작
   - ✅ 권한 체크 정상 동작
   - ✅ 에러 핸들링 정상 동작
   - ✅ 성능 기준 충족 (RAG Chat < 5초)

5. 버그 수정 (발견 시)
   - 우선순위 결정 (Critical/Major/Minor)
   - Critical/Major 버그 즉시 수정
   - Minor 버그 Issue로 기록

6. 배포 준비
   - Docker Compose 설정 확인
   - 환경변수 정리 (.env.example 작성)
   - README.md 업데이트
     - 프로젝트 소개
     - 기능 목록
     - 설치 방법
     - 실행 방법
     - API 문서 링크
   - API 문서 작성 (Swagger/Postman)

7. Git commit 및 main PR 준비
   - Git commit: "test: Week 10 final E2E tests and deployment prep"
   - develop → main PR 준비 안내

8. 최종 결과 보고
   - Phase 2 기능 목록 (✅/❌)
   - Phase 3 기능 목록 (✅/❌)
   - 성능 테스트 결과
   - 발견된 버그 및 개선 사항
   - 배포 준비 완료 체크리스트

시작하자.
```

**예상 결과:**
- ✅ 전체 E2E 테스트 완료 (Phase 2 + Phase 3)
- ✅ 사용자 시나리오 검증 완료
- ✅ 협업 기능 검증 완료
- ✅ 성능 테스트 통과
- ✅ 배포 준비 완료 (Docker, README, 환경변수)
- 📝 발견된 버그 문서화

**사용자 작업 (테스트 후):**
- ⚠️ develop → main PR 생성 및 머지 (사용자가 직접)
- 🎉 프로젝트 완성!

---

## 💡 사용 팁

### 1. 병렬 작업할 때

**3개 터미널이 필요한 경우:**
```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md
@docs/conf/PARALLEL_WORKFLOW_GUIDE.md

Phase 3-1 Phase 2 병렬 작업 시작

Terminal 1: feature/document-upload
Terminal 2: feature/document-ui
Terminal 3: feature/document-ocr

다음을 해줘:
1. 현재 상태 파악
2. 병렬 작업 방법 안내
3. 각 터미널별 작업 지시

시작하자.
```

---

### 2. Git 문제 해결

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/GIT_BRANCH_STRATEGY.md

Git 상태가 이상해:

```bash
git status
[출력 결과 붙여넣기]
```

다음을 해줘:
1. Git 상태 분석
2. 해결 방법 제시
3. 단계별 실행 가이드

시작하자.
```

---

### 3. 작업 중단 후 재개

```markdown
새 세션 시작.

@docs/conf/PROJECT_STATUS.md
@docs/conf/FEATURE_CHECKLIST.md

현재 브랜치: [브랜치명]

이전 세션에서 [작업명] 중단했어.

다음을 해줘:
1. 이전 작업 진행 상황 파악
2. 남은 작업 확인
3. 이어서 작업 진행
4. 완료 후 결과 보고

시작하자.
```

---

## 📊 진행도 추적

### 구현 세션 (Implementation)
- [x] Session 0-A: Phase 2 정리
- [x] Session 1: Document 모델
- [x] Session 2-A: Upload API
- [x] Session 2-B: Upload UI
- [x] Session 2-C: OCR Pipeline
- [x] Session 4: Summary 모델
- [x] Session 5-A: Summary API
- [x] Session 5-B: LLM APIs
- [x] Session 5-C: Analysis UI
- [x] Session 6: Organization 모델
- [x] Session 7: Organization API
- [ ] Session 8: Organization UI
- [ ] Session 10: Risk Analysis
- [ ] Session 11: LLM Comparison
- [ ] Session 13: Crawling System
- [ ] Session 14-A: Dashboard Stats API
- [ ] Session 14-B: Dashboard UI

### 테스트 세션 (Testing)
- [x] Session 0-B: Phase 2 통합 테스트 (Week 0)
- [x] Session 2-D: Week 1-2 통합 테스트 (Document 관리)
- [x] Session 5-D: Week 3-4 통합 테스트 (문서 분석)
- [ ] Session 9: Week 5 통합 테스트 (Organization)
- [ ] Session 14-C: Week 8-9 통합 테스트 (Crawling + Dashboard)
- [ ] Session 15: Week 10 최종 E2E 테스트

---

**문서 위치**: `docs/conf/SESSION_PROMPTS.md`
**마지막 업데이트**: 2025-11-24 (Session 7 완료, Week 8-10 추가)
