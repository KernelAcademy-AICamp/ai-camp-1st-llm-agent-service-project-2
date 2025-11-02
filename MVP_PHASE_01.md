# 📋 LawLaw 웹 MVP - Phase 01 개발 계획

## 🎯 프로젝트 개요

### 목표
실제 변호사 워크플로우에 맞춘 웹 기반 법률 AI 어시스턴트 구축

### 핵심 전략
- **LLM**: Ollama(로컬) → **OpenAI/Claude API** (빠르고 정확한 응답)
- **RAG**: 기존 ChromaDB + Hybrid Search 그대로 활용
- **Desktop 앱**: Phase 02로 연기, 웹 우선 개발

---

## 📁 실무 변호사 워크플로우

### 실제 업무 프로세스
1. **사건 접수** → 의뢰인 상담 + 문서 수령
2. **사건 분석** → 문서 읽고 쟁점 파악
3. **법률 리서치** → 관련 판례/법령 검색
4. **전략 수립** → 소송 전략, 합의 방안 등
5. **문서 작성** → 준비서면, 의견서 등

### MVP 3가지 핵심 기능
1. **법률 리서치** (AI 질의응답)
2. **사건 분석** (파일 업로드 → AI 분석 → 파일링)
3. **문서 작성** (템플릿 기반 + AI 어시스트)

---

## 🔧 기능 1: AI 질의응답 (법률 리서치)

### 현재 상태
- ✅ LegalResearch 페이지 70% 완성
- ✅ RAG 시스템 구축 (ChromaDB + Hybrid Search)
- ✅ Constitutional AI 프롬프트 적용
- ⚠️ Ollama(로컬) 사용 중 (느림)

### 변경 사항
**Ollama → OpenAI/Claude API로 전환**
- 속도: 2-3분 → 3-5초
- 정확도: 대형 LLM의 법률 이해도 높음
- 안정성: API 호출이 로컬 실행보다 안정적

### 구현 계획
1. `.env` 파일 API 키 확인 (✅ 이미 있음)
2. `app/backend/main.py`에서 provider 변경
3. 기존 RAG 유지
4. Constitutional AI 프롬프트 유지

---

## 🔧 기능 2: 문서 업로드 → AI 분석 → 사건 파일링

### 워크플로우
```
의뢰인 문서 업로드 (PDF, DOCX, TXT)
  ↓
AI 자동 분석:
  - 문서 유형 자동 분류
  - 핵심 내용 요약
  - 법적 쟁점 추출
  - 관련 판례 검색 (RAG)
  ↓
사건 폴더 자동 생성:
  - 사건명 제안
  - 파일 자동 정리
  - 타임라인 구성
  ↓
대시보드 표시:
  - 사건 개요
  - 중요 날짜
  - 다음 단계 제안
```

### Backend 구현 항목
1. **파일 업로드 API**
   - 엔드포인트: `POST /cases/upload`
   - 여러 파일 동시 업로드 지원
   - PDF/DOCX/TXT 파서 (PyPDF2, python-docx)

2. **사건 분석 서비스**
   - OpenAI API로 문서 분석
   - RAG로 관련 판례 검색
   - 사건명 자동 제안

3. **데이터 저장**
   - 파일시스템: `data/cases/{case_id}/`
   - 메타데이터: `metadata.json`
   - 분석 결과: `analysis.json`

4. **API 엔드포인트**
   - `POST /cases/upload` - 파일 업로드 + 분석
   - `GET /cases` - 사건 목록 조회
   - `GET /cases/{id}` - 사건 상세 조회
   - `POST /cases/{id}/analyze` - 사건 재분석

### Frontend 구현 항목
1. **CaseManagement 페이지 완성**
   - 파일 드래그앤드롭 (react-dropzone)
   - 업로드 진행 상태 표시
   - 분석 결과 카드 UI

2. **사건 카드 컴포넌트**
   - 사건 요약 표시
   - 주요 쟁점 리스트
   - 관련 판례 미리보기
   - 상세보기/재분석 버튼

### 데이터 구조
```
data/cases/
├── case_001/
│   ├── metadata.json      # 사건 기본 정보
│   ├── analysis.json      # AI 분석 결과
│   └── files/
│       ├── 판결문.pdf
│       └── 계약서.docx
```

**metadata.json**
- case_id, case_name, created_at
- plaintiff, defendant, case_number
- files 리스트

**analysis.json**
- summary (사건 요약)
- document_types (문서 유형)
- issues (주요 쟁점)
- key_dates (중요 날짜)
- related_cases (관련 판례)
- suggested_next_steps (다음 단계 제안)

---

## 🔧 기능 3: 법률 문서 작성 (템플릿 + AI)

### 워크플로우
```
템플릿 선택:
  - 준비서면, 법률 의견서
  - 항소이유서, 합의서, 내용증명
  ↓
필수 정보 입력:
  - 사건번호, 당사자명, 날짜
  - (선택) 사건 폴더에서 가져오기
  ↓
AI 어시스트:
  - 관련 판례 자동 인용 (RAG)
  - 법리 설명 자동 생성
  - 문장 개선 제안
  ↓
편집 및 완성:
  - 텍스트 에디터로 수정
  - DOCX/PDF 다운로드
```

### Backend 구현 항목
1. **템플릿 시스템**
   - JSON 형식으로 템플릿 정의
   - Jinja2로 렌더링
   - 5가지 기본 템플릿 제공

2. **문서 생성 서비스**
   - 사용자 입력 + AI 생성 결합
   - RAG로 관련 판례 검색
   - OpenAI로 법리 설명 생성

3. **문서 내보내기**
   - HTML → DOCX 변환 (python-docx)
   - 파일 다운로드 API

4. **API 엔드포인트**
   - `GET /templates` - 템플릿 목록
   - `POST /documents/generate` - AI 문서 생성
   - `POST /documents/save` - 문서 저장
   - `GET /documents/{id}/export` - DOCX/PDF 내보내기

### Frontend 구현 항목
1. **DocumentEditor 페이지 완성**
   - 왼쪽: 템플릿 선택 + 입력 폼
   - 오른쪽: 텍스트 에디터 (react-quill)
   - 사이드바: AI 제안 (관련 판례 등)

2. **템플릿 폼**
   - 필수 필드 입력
   - 사건 폴더 연결 옵션
   - AI 생성 버튼

3. **에디터**
   - 실시간 편집
   - 저장/다운로드 버튼
   - AI 제안 적용 버튼

### 템플릿 예시 (준비서면)
```
준 비 서 면

사건: {{case_number}}
원고: {{plaintiff}}
피고: {{defendant}}

청구취지
{{ai_generated_claim}}

청구원인
{{ai_generated_cause}}

입증방법
{{evidence_list}}

관련 판례
{{rag_related_cases}}

결론
{{ai_generated_conclusion}}
```

---

## 🛠️ 구현 우선순위 및 일정

### Phase 1.1: LLM 전환 (1시간)
- [ ] OpenAI API 키 확인
- [ ] config.py 수정
- [ ] main.py provider 변경
- [ ] 테스트

### Phase 1.2: 파일 업로드 + 사건 분석 (4-5시간)
**Backend**
- [ ] 파일 업로드 API
- [ ] PDF/DOCX 파서
- [ ] 사건 분석 로직
- [ ] 파일시스템 저장

**Frontend**
- [ ] CaseManagement 페이지 UI
- [ ] 드래그앤드롭
- [ ] 분석 결과 카드

### Phase 1.3: 문서 작성 템플릿 (3-4시간)
**Backend**
- [ ] 템플릿 시스템
- [ ] 문서 생성 API
- [ ] DOCX 내보내기

**Frontend**
- [ ] DocumentEditor 페이지 UI
- [ ] 템플릿 폼
- [ ] react-quill 에디터

### Phase 1.4: 통합 테스트 (2시간)
- [ ] E2E 테스트
- [ ] 성능 최적화
- [ ] 에러 핸들링
- [ ] UI/UX 개선

**총 예상 시간**: 10-12시간 (1-2일)

---

## 📦 추가 패키지

### Backend
```bash
pip install PyPDF2 python-docx python-multipart jinja2
```

### Frontend
```bash
npm install react-dropzone react-quill
```

---

## 🎯 MVP 완성 후 기대 효과

### 업무 효율성
- ✅ 사건 분석 시간 **70% 단축**
- ✅ 문서 작성 시간 **50% 단축**
- ✅ 법률 리서치 시간 **60% 단축**

### 실무 가치
- ✅ 실제 변호사 워크플로우 반영
- ✅ 의뢰인 문서 → AI 분석 → 문서 작성 전체 흐름
- ✅ 판례 기반 답변으로 신뢰도 확보

### 기술적 장점
- ✅ 빠른 응답 (OpenAI API)
- ✅ 정확한 답변 (RAG + Constitutional AI)
- ✅ 확장 가능 (템플릿 추가 용이)

---

## 📝 Phase 02 계획

- [ ] Electron 데스크톱 앱 통합
- [ ] QDoRA Adapter 시스템 (전문 분야별)
- [ ] 오프라인 모드 지원
- [ ] 더 많은 문서 템플릿
- [ ] 음성 인터페이스
- [ ] 팀 협업 기능

---

**작성일**: 2024-11-01
**버전**: 1.0
