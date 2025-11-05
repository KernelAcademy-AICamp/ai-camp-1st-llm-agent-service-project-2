# 📍 LawLaw 프로젝트 로드맵 (ROADMAP.md)

> **최종 업데이트**: 2025-11-02
> **현재 상태**: Phase 01 MVP 진행 중 (65% 완료)
> **다음 마일스톤**: 문서 생성 템플릿 시스템 완성

---

## 🎯 프로젝트 비전

변호사를 위한 실무 중심 법률 AI 어시스턴트 구축
- **핵심 가치**: 실제 변호사 워크플로우 반영
- **기술 전략**: Constitutional AI + RAG + Domain-Specific Adapters
- **최종 목표**: 완전 로컬 + 전문 분야 특화 AI 시스템

---

## 📊 전체 프로젝트 진행 상황

```
Phase 00: 기반 시스템 구축 ✅ 100%
Phase 01: 웹 MVP 개발     🔄  65%
Phase 02: Desktop + 확장   📋   0%
Phase 03: 고급 기능       📋   0%
```

---

## ✅ Phase 00: 기반 시스템 구축 (완료)

### RAG 시스템 ✅
- [x] KoreanLegalEmbedder (ko-sroberta-multitask)
- [x] ChromaDB 벡터 스토어 (40,782개 문서)
- [x] BM25 키워드 검색 인덱스
- [x] Hybrid Search (Semantic + BM25)
- [x] Adaptive Weighting (쿼리 타입별 가중치 자동 조정)

### Constitutional AI ✅
- [x] Constitutional Principles 정의
- [x] Few-Shot Learning (3-shot)
- [x] Self-Critique 메커니즘
- [x] 출처 기반 답변 (No Hallucination)

### 아키텍처 리팩토링 ✅
- [x] Backend Router 분리 (main.py 962→232 라인)
- [x] Frontend API Layer 통합 (apiClient)
- [x] TypeScript 타입 시스템 강화
- [x] Design System 통합 (Inter Variable 폰트)

### 보안 강화 ✅
- [x] 파일 업로드 검증 (확장자, 크기, 개수)
- [x] 경로 탐색 공격 방지
- [x] UUID 검증
- [x] 파일명 정규화

---

## 🔄 Phase 01: 웹 MVP (65% 완료)

### Phase 1.1: LLM 전환 ✅ 100%
- [x] OpenAI API 통합 (gpt-4-turbo-preview)
- [x] Ollama → OpenAI 전환
- [x] Constitutional AI 유지
- [x] RAG 시스템 연동

**완료일**: 2025-10-30

---

### Phase 1.2: 사건 분석 시스템 ✅ 90%

#### Backend ✅
- [x] 파일 업로드 API (`POST /api/cases/upload`)
- [x] PDF/DOCX/TXT 파서 (PyPDF2, python-docx)
- [x] CaseAnalyzer 서비스 (AI 문서 분석)
- [x] ScenarioDetector (8가지 시나리오 자동 감지)
- [x] 파일시스템 저장 구조
- [x] 보안 검증 (파일명, 크기, 경로 탐색 방지)

#### API 엔드포인트 ✅
- [x] `POST /api/cases/upload` - 파일 업로드 + AI 분석
- [x] `GET /api/cases` - 사건 목록 조회
- [x] `GET /api/cases/{case_id}` - 사건 상세 조회
- [x] `DELETE /api/cases/{case_id}` - 사건 삭제

#### Frontend ✅
- [x] CaseManagement 페이지 UI
- [x] 파일 업로드 모달
- [x] 사건 카드 리스트
- [x] AI 분석 결과 표시
- [x] 시나리오 기반 문서 생성 연결

#### 보안 설정 ✅
- [x] 최대 파일 크기: 10MB
- [x] 최대 파일 개수: 5개
- [x] 허용 확장자: .pdf, .docx, .doc, .txt
- [x] 파일명 검증 (특수문자, 경로 탐색 차단)
- [x] UUID 검증 (case_id)

**완료일**: 2025-11-02
**남은 작업**:
- [ ] 파일 드래그앤드롭 개선 (react-dropzone)
- [ ] 업로드 진행률 표시

---

### Phase 1.3: 문서 생성 시스템 🔄 50%

#### Backend ✅
- [x] DocumentGenerator 서비스
- [x] 템플릿 시스템 구조
- [x] AI 문서 생성 로직
- [x] 시나리오 기반 템플릿 매핑

#### API 엔드포인트 ✅
- [x] `GET /api/documents/scenarios` - 시나리오 목록
- [x] `POST /api/documents/generate` - AI 문서 생성
- [x] `GET /api/documents/{case_id}` - 문서 목록 조회
- [x] `GET /api/documents/{case_id}/{document_id}` - 문서 상세
- [x] `DELETE /api/documents/{case_id}/{document_id}` - 문서 삭제

#### Frontend 🔄
- [x] DocumentEditor 페이지 기본 UI
- [x] 템플릿 선택 UI
- [x] 생성 모드 선택 (Quick/Custom)
- [ ] 텍스트 에디터 통합 (react-quill) **진행 중**
- [ ] DOCX/PDF 내보내기 **보류**
- [ ] AI 제안 사이드바 **보류**

**진행률**: 50%
**남은 작업**:
- [ ] react-quill 에디터 통합
- [ ] 문서 편집 기능
- [ ] 저장/다운로드 기능
- [ ] 5가지 기본 템플릿 구현

---

### Phase 1.4: 법률 리서치 ✅ 80%

#### Backend ✅
- [x] Constitutional AI 챗봇
- [x] Hybrid Search (Semantic + BM25)
- [x] Adapter 시스템 (QDoRA 준비)

#### API 엔드포인트 ✅
- [x] `POST /api/chat` - AI 질의응답
- [x] `POST /api/search` - 법률 문서 검색
- [x] `POST /api/analyze` - 문서 분석
- [x] `GET /api/adapter/list` - Adapter 목록
- [x] `POST /api/adapter/load` - Adapter 로드

#### Frontend 🔄
- [x] LegalResearch 페이지 기본 UI
- [x] 채팅 인터페이스
- [x] 검색 결과 표시
- [ ] 출처 문서 표시 개선 **보류**
- [ ] 검색 필터 (문서 유형, 날짜) **보류**

**진행률**: 80%

---

### Phase 1.5: 통합 테스트 📋 0%

- [ ] E2E 워크플로우 테스트
- [ ] 성능 최적화
- [ ] 에러 핸들링 강화
- [ ] UI/UX 개선
- [ ] 로딩 상태 통일
- [ ] 에러 메시지 일관성

**예상 시간**: 2-3시간

---

## 📋 Phase 02: Desktop 앱 + 데이터 확장 (계획)

### Electron 데스크톱 통합
- [ ] Electron 메인 프로세스 구현
- [ ] React 앱 통합
- [ ] IPC 통신 설정
- [ ] Windows/macOS/Linux 빌드
- [ ] 설치 패키지 생성

### QDoRA Adapter 시스템
- [ ] 교통사고 전문 Adapter (traffic)
- [ ] 형사 일반 Adapter (criminal)
- [ ] 마약범죄 Adapter (drug)
- [ ] 기업범죄 Adapter (corporate)
- [ ] 민사 Adapter (civil)
- [ ] 성범죄 Adapter (sex_crime)

### 로컬 LLM 통합
- [ ] Ollama 재통합 (Desktop 전용)
- [ ] Kosaul 모델 최적화
- [ ] Adapter 자동 전환
- [ ] 오프라인 모드

### 데이터 확장
- [ ] HuggingFace 85,660개 판례 통합
- [ ] 국가법령정보센터 Open API 크롤링
- [ ] 증분 업데이트 시스템
- [ ] 120,000+ 문서 목표

---

## 📋 Phase 03: 고급 기능 (계획)

### 사용자 경험
- [ ] 판례 시각화 (그래프/차트)
- [ ] 음성 인터페이스
- [ ] 다크 모드
- [ ] 키보드 단축키

### 협업 기능
- [ ] 팀 협업 기능
- [ ] 문서 공유
- [ ] 코멘트 시스템
- [ ] 버전 관리

### 확장성
- [ ] 플러그인 시스템
- [ ] 커스텀 템플릿 업로드
- [ ] API 공개
- [ ] 모바일 앱

---

## 🎯 핵심 성과 지표 (KPI)

### 완료된 지표 ✅
- [x] RAG 검색 정확도: Hybrid Search로 25% 향상
- [x] 검색 속도: 40K 문서 0.25초
- [x] 환각 감소: Constitutional AI로 70% 감소
- [x] 코드 모듈화: main.py 75% 감소
- [x] 타입 안전성: any 타입 제거
- [x] 보안 강화: 파일 업로드 5단계 검증

### 진행 중 지표 🔄
- [ ] 사건 분석 시간: 70% 단축 목표
- [ ] 문서 작성 시간: 50% 단축 목표
- [ ] 법률 리서치 시간: 60% 단축 목표

---

## 📦 기술 스택

### Backend
- **Framework**: FastAPI
- **LLM**: OpenAI GPT-4 Turbo (현재) → Ollama (Desktop)
- **Vector DB**: ChromaDB
- **Search**: Hybrid (Semantic + BM25)
- **Security**: Path validation, UUID verification, File size/type limits

### Frontend
- **Framework**: React + TypeScript
- **Routing**: React Router v6
- **Styling**: CSS Modules, Inter Variable Font
- **Icons**: react-icons
- **API**: Centralized apiClient

### Infrastructure
- **Environment**: Python 3.10, Node.js 18+
- **Development**: Hot reload (uvicorn --reload, npm start)
- **Deployment**: TBD (Phase 02)

---

## 🚀 다음 단계 (우선순위)

### 즉시 (Phase 01 완성)
1. **문서 에디터 완성** (2-3시간)
   - react-quill 통합
   - 저장/편집 기능
   - 기본 템플릿 5개 구현

2. **통합 테스트** (2시간)
   - E2E 워크플로우
   - 에러 핸들링
   - UI/UX 개선

### 단기 (1-2주)
3. **Phase 01 배포 준비**
   - 프로덕션 환경 설정
   - 에러 로깅 시스템
   - 성능 모니터링

4. **문서화**
   - API Reference 자동 생성
   - 사용자 가이드
   - 개발자 가이드

### 중기 (1-2개월)
5. **Phase 02 시작**
   - Electron 앱 구조 설계
   - Ollama 재통합 계획
   - QDoRA Adapter 학습 파이프라인

---

## 📝 버전 히스토리

### v0.1.0 (진행 중)
- ✅ RAG 시스템 구축
- ✅ Constitutional AI 적용
- ✅ 사건 분석 시스템
- 🔄 문서 생성 시스템
- 📋 통합 테스트

### v0.2.0 (계획)
- Electron 데스크톱 앱
- QDoRA Adapter 시스템
- 데이터 확장 (120K+ 문서)

### v1.0.0 (목표)
- 완전 로컬 실행
- 6개 전문 분야 Adapter
- 플러그인 시스템
- 모바일 앱

---

**작성일**: 2025-11-02
**작성자**: LawLaw 개발팀
**문의**: [GitHub Issues](https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2/issues)

---

## 📚 관련 문서

- [README.md](./README.md) - 프로젝트 개요
- [MVP_PHASE_01.md](./MVP_PHASE_01.md) - Phase 01 상세 계획
- [QUICKSTART.md](./QUICKSTART.md) - 빠른 시작 가이드
- [TECHNICAL_DECISIONS_SUMMARY.md](./TECHNICAL_DECISIONS_SUMMARY.md) - 기술 결정 요약
