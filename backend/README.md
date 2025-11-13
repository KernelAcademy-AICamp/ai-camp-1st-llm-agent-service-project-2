# LawLaw Backend

> 형사법 전문 AI 어시스턴트 백엔드 API

Constitutional AI + RAG 기반 형사법 전문 AI 어시스턴트의 백엔드입니다.

---

## 🛠️ 기술 스택

| Category | Technologies |
|----------|-------------|
| **Framework** | FastAPI 0.104+ |
| **Language** | Python 3.10+ |
| **Database** | SQLite (AsyncIO) |
| **LLM** | OpenAI GPT-4 Turbo, Ollama |
| **Vector DB** | ChromaDB 0.4.18+ |
| **Embeddings** | Sentence Transformers (Korean Legal) |
| **RAG** | Hybrid Retrieval (Semantic + BM25) |
| **Auth** | JWT (python-jose) |

---

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
`.env` 파일 생성:
```bash
# LLM API Keys
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Authentication
JWT_SECRET_KEY=your-secure-secret-key-here

# OpenLaw API (Optional)
OPENLAW_API_KEY=fox_racer  # 기본값: 공용 키
```

### 3. 데이터베이스 초기화
```bash
python scripts/init_db.py
```

### 4. 벡터 DB 구축 (처음 1회만)
```bash
python scripts/build_vectordb.py --max_files 10 --max_docs 1000
```

### 5. 서버 실행
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
브라우저에서 `http://localhost:8000/docs` 접속

---

## 📂 프로젝트 구조

```
backend/
├── core/                    # Core 모듈
│   ├── auth/               # JWT 인증
│   ├── embeddings/         # Embedding & VectorDB
│   ├── llm/                # LLM Clients & Constitutional AI
│   └── retrieval/          # Hybrid RAG Retriever
├── routers/                # API 엔드포인트 (8개)
│   ├── chat.py            # 챗봇 & RAG 검색
│   ├── cases.py           # 사건 분석
│   ├── documents.py       # 문서 생성
│   ├── adapters.py        # QDoRA Adapter 관리
│   ├── auth.py            # 회원가입/로그인
│   ├── precedents.py      # 판례 관리
│   ├── precedent_scraping.py  # 판례 크롤링
│   └── feedback.py        # 사용자 피드백
├── services/              # 비즈니스 로직
│   ├── case_analyzer.py
│   ├── document_generator.py
│   ├── scourt_scraper.py
│   └── openlaw_client.py
├── models/                # SQLAlchemy 모델
│   ├── user.py
│   ├── precedent.py
│   └── precedent_feedback.py
├── templates/             # 문서 템플릿 (10종)
├── main.py               # FastAPI 앱
├── database.py           # DB 설정
└── requirements.txt
```

---

## 🎯 주요 기능

### 1. Constitutional AI Chatbot
- 6가지 헌법적 원칙 기반 답변
- Self-Critique & Revision
- 388K+ 형사법 문서 RAG

### 2. Hybrid RAG Search
- Semantic Search (Vector DB)
- BM25 Keyword Search
- RRF (Reciprocal Rank Fusion)
- Adaptive Weighting

### 3. QDoRA Adapter 지원
- 전문 분야별 Adapter (교통사고, 마약, 성범죄 등)
- 실시간 Adapter 전환
- Ollama 통합

### 4. 문서 자동 생성
- 소장, 답변서, 변론요지서
- 내용증명, 계약서
- AI 기반 자동 작성

### 5. 실시간 판례 크롤링
- 대법원 판례 스크래핑
- OpenLaw API 통합
- 자동 스케줄링

---

## 📊 API 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API 정보 |
| GET | `/health` | 서버 상태 체크 |
| POST | `/api/chat` | 챗봇 대화 |
| POST | `/api/chat-with-rag` | RAG 기반 챗봇 |
| POST | `/api/search` | Hybrid 검색 |
| POST | `/api/cases/upload` | 사건 파일 업로드 |
| POST | `/api/documents/generate` | 문서 생성 |
| GET | `/api/adapters` | Adapter 목록 |
| POST | `/api/auth/signup` | 회원가입 |
| POST | `/api/auth/login` | 로그인 |

전체 API 문서: `http://localhost:8000/docs`

---

## ⚠️ 주의사항

1. **환경 변수 필수**: `.env` 파일에서 API 키 설정 필요
2. **벡터 DB 구축**: 처음 실행 시 `build_vectordb.py` 필수 실행
3. **Production 설정**:
   - `JWT_SECRET_KEY` 반드시 변경
   - CORS origins 설정
   - 로깅 레벨 조정

---

**Repository**: [ai-camp-1st-llm-agent-service-project-2](https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2)
