# Django 마이그레이션 완벽 가이드 (Option C)

> **Last Updated**: 2025-11-20
> **Version**: 1.2 (Phase 1.5 추가 - Django 전환 준비)
> **전략**: 점진적 전환 (AI Service 분리 → Django 전환 준비 → Django 전환)
> **예상 기간**: 5.5주 (Phase 1: 2주, **Phase 1.5: 3일**, Phase 2: 3주)
>
> **v1.2 업데이트 (2025-11-20):**
> - 🆕 **Phase 1.5 추가**: Django 전환 준비 단계 (inspectdb, fake migration)
> - 🆕 **AI Service DB 모델 간소화**: Raw SQL 사용으로 스키마 동기화 부담 감소
> - 🆕 **실무 검증**: 현재 프로젝트 DB 상태 확인 (SQLite, 4개 테이블)
> - 📚 **보완 문서 추가**: docs/DJANGO_MIGRATION_補完.md (별도 파일)
>
> **v1.1 업데이트 (이전):**
> - ✅ Day 3: PrecedentFeedbackStats 스키마를 실제 DB와 일치하도록 수정
> - ✅ Day 4: feedback_adapter.py 반환값을 실제 컬럼명과 일치하도록 수정
> - ✅ Day 5 이전: libs/rag_core/retrieval/filters.py 사전 생성 완료
> - ✅ Day 6-7: scenario_detector.py DB 비의존 확인 (이동 가능)

---

## 📋 목차

1. [현재 상황 분석](#-현재-상황-분석)
2. [마이그레이션 전략](#-마이그레이션-전략)
3. [Phase 1: AI Service 분리](#-phase-1-ai-service-분리-2주)
4. [**Phase 1.5: Django 전환 준비**](#-phase-15-django-전환-준비-3일--필수) ⭐ **신규 추가**
5. [Phase 2: Django 전환](#-phase-2-django-전환-3주)
6. [체크리스트](#-체크리스트)
7. [v1.2 업데이트 내역](#-v12-업데이트-내역-2025-11-20)

---

## 📊 현재 상황 분석

### Git 상태

```bash
Branch: develop
Recent commits:
- 45ee64b: chore: add root requirements.txt for monorepo
- 55b1937: Merge PR #11 (feature/monorepo-migration)
- de9a02e: refactor: migrate apps/backend to use libs/rag_core

Status: Clean, ready for new feature branch ✅
```

### 현재 구조 (GIT_MIGRATION_STRATEGY.md 완료 후)

```
ai-camp-1st-llm-agent-service-project-2/  (Git connected)
├── apps/
│   ├── backend/          ✅ FastAPI (libs/rag_core 사용 중)
│   │   ├── main.py       ✅ libs/rag_core import
│   │   ├── routers/      ✅ chat, cases, auth, adapters 등
│   │   ├── services/     ✅ analyzer, generator, crawler 등
│   │   ├── models/       ✅ SQLAlchemy (User, Case, Precedent)
│   │   └── core/
│   │       ├── auth/     ✅ FastAPI JWT 인증
│   │       └── retrieval/
│   │           └── feedback_filter.py  ✅ DB 의존적 필터
│   │
│   ├── web-frontend/     ✅ React
│   ├── ai-service/       ⚠️  비어있음 (.gitkeep만 존재)
│   └── data-pipeline/    ✅ ETL
│
├── libs/
│   ├── rag_core/         ✅ RAG 핵심 로직 (DB 비의존)
│   │   ├── embeddings/
│   │   ├── llm/
│   │   └── retrieval/
│   └── domain_model/     ✅ 공통 Pydantic 모델
│
├── data/                 ✅ VectorDB, 업로드 (Git 제외)
├── configs/              ✅ 설정 파일
└── docs/                 ✅ 문서
```

### 주요 성과 (이미 완료된 작업)

✅ **libs/rag_core 구축 완료**
- embeddings/, llm/, retrieval/ 모듈화
- DB 비의존적 설계
- apps/backend에서 import 중

✅ **Git 저장소 정리**
- develop 브랜치 clean 상태
- PR #11 머지 완료
- monorepo 구조 안정화

✅ **apps/backend 리팩토링**
- libs/rag_core 사용하도록 변경
- 정상 작동 확인

---

## 🎯 마이그레이션 전략

### 최종 목표 구조

```
ai-camp-1st-llm-agent-service-project-2/
├── apps/
│   ├── backend-api/      🎯 Django (비즈니스 로직, API Gateway)
│   │   ├── manage.py
│   │   ├── backend_api/  (Django 프로젝트)
│   │   ├── users/        (Django 앱)
│   │   ├── cases/        (Django 앱)
│   │   ├── precedents/   (Django 앱)
│   │   ├── documents/    (Django 앱)
│   │   └── api/          (API 엔드포인트)
│   │       └── v1/
│   │           ├── auth.py
│   │           ├── cases.py
│   │           └── ai_proxy.py  ⭐ AI Service 호출
│   │
│   ├── ai-service/       🎯 FastAPI (AI 전용 엔진)
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── chat.py       (RAG 챗봇)
│   │   │   ├── search.py     (VectorDB 검색)
│   │   │   └── embeddings.py (임베딩 생성)
│   │   ├── services/
│   │   │   ├── analyzer.py       (사건 분석)
│   │   │   ├── generator.py      (문서 생성)
│   │   │   └── feedback_adapter.py  (DB 피드백)
│   │   └── models/       (SQLAlchemy Read-Only)
│   │
│   ├── web-frontend/     ✅ React (변경 없음)
│   └── data-pipeline/    ✅ ETL (변경 없음)
│
├── libs/
│   ├── rag_core/         ✅ RAG 핵심 로직 (유지)
│   └── domain_model/     ✅ 공통 모델 (유지)
│
└── apps/backend/         🔴 삭제 예정 (Phase 2 완료 후)
```

### API 흐름 (최종)

```
Frontend (3000)
    ↓ HTTP
Django Backend API (8000)
    ↓ JWT 검증
    ↓
    ├─→ Django ORM (User, Case, Precedent 관리)
    └─→ AI Service (8001)
            ↓
            ├─→ libs/rag_core (RAG 로직)
            ├─→ VectorDB (ChromaDB, FAISS, BM25)
            └─→ LLM (GPT-4)
```

### 왜 점진적 전환인가?

| 측면 | 직접 Django (Option A) | 점진적 전환 (Option C) |
|------|----------------------|---------------------|
| **안정성** | 2개 서비스 동시 개발 (위험) | 1개씩 순차 개발 (안전) |
| **Git 관리** | 1개 큰 PR (리뷰 어려움) | 2개 작은 PR (리뷰 쉬움) |
| **디버깅** | 문제 발생 시 범위 넓음 | 문제 격리 용이 |
| **예상 시간** | 4주 (재작업 위험) | 5주 (예측 가능) |
| **검증 포인트** | 통합 테스트 시점 | Phase 1 완료 시점 + 통합 |

---

## 📦 Phase 1: AI Service 분리 (2주)

### 목표

- apps/backend에서 AI 관련 로직만 apps/ai-service로 분리
- apps/backend는 비즈니스 로직만 남김 (FastAPI 유지)
- 두 서비스 간 HTTP 통신 구현
- PR #1 생성 및 머지

### 최종 결과 (Phase 1 완료 후)

```
apps/
├── backend/          ✅ FastAPI (비즈니스 로직 + AI 프록시)
│   ├── routers/
│   │   ├── auth.py       (JWT 인증)
│   │   ├── cases.py      (사건 CRUD)
│   │   ├── chat.py       ⭐ AI Service 프록시로 변경
│   │   └── adapters.py   ⭐ AI Service 프록시로 변경
│   ├── services/
│   │   ├── file_parser.py
│   │   ├── precedent_crawler.py
│   │   └── (analyzer.py, generator.py 제거됨)
│   └── models/       (SQLAlchemy, 그대로 유지)
│
└── ai-service/       ✅ FastAPI (AI 전용)
    ├── main.py       (libs/rag_core import)
    ├── routers/
    │   ├── chat.py       (RAG 챗봇)
    │   ├── search.py     (VectorDB 검색)
    │   └── adapters.py   (Constitutional AI)
    ├── services/
    │   ├── analyzer.py       (사건 분석)
    │   ├── generator.py      (문서 생성)
    │   └── feedback_adapter.py  (DB 읽기)
    └── models/
        ├── database.py       (PostgreSQL Read-Only)
        └── precedent_feedback.py  (SQLAlchemy)
```

---

### Week 1: apps/ai-service 구축

#### Day 1: Git 브랜치 생성 및 구조 설정

```bash
# 1. develop 브랜치 최신화
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
git checkout develop
git pull origin develop

# 2. 새 feature 브랜치 생성
git checkout -b feature/ai-service-separation

# 3. 백업 생성 (선택)
cd /Users/myidwon/dev
tar -czf ai-camp-backup-$(date +%Y%m%d).tar.gz ai-camp-1st-llm-agent-service-project-2/

# 4. 디렉토리 구조 생성
cd ai-camp-1st-llm-agent-service-project-2/apps/ai-service

# .gitkeep 제거
rm -f .gitkeep

# 디렉토리 생성
mkdir -p routers services models config

# __init__.py 생성
touch __init__.py
touch routers/__init__.py
touch services/__init__.py
touch models/__init__.py
touch config/__init__.py

# 5. 확인
ls -la
# main.py, routers/, services/, models/, config/, __init__.py 확인

# 6. Git commit
git add apps/ai-service/
git commit -m "chore: create apps/ai-service directory structure

- Remove .gitkeep
- Add routers/, services/, models/, config/ directories
- Add __init__.py files for Python modules"
```

#### Day 2: config/settings.py 및 main.py 작성

**Step 1: config/settings.py**

```python
# apps/ai-service/config/settings.py
"""
AI Service Configuration
환경변수 기반 설정
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """AI Service 설정"""

    # Service
    SERVICE_NAME: str = "LawLaw AI Service"
    SERVICE_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"

    # Database (Read-Only)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:5432/lawlaw"
    )

    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")  # Custom endpoint
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent.parent
    VECTORDB_DIR: Path = BASE_DIR / "data" / "vectordb"
    CHROMA_DIR: Path = VECTORDB_DIR / "chroma_criminal_law"
    BM25_DIR: Path = VECTORDB_DIR / "bm25"

    # CORS (Django Backend만 허용)
    CORS_ORIGINS: list = [
        "http://localhost:8000",  # Django Backend
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**Step 2: main.py**

```python
# apps/ai-service/main.py
"""
LawLaw AI Service
FastAPI 기반 AI 전용 엔진 - RAG, LLM, Embeddings
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys
import logging

# ==========================================
# PYTHONPATH 설정 (Monorepo 구조)
# ==========================================
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# ==========================================
# libs/rag_core Import
# ==========================================
from libs.rag_core import (
    create_llm_client,
    KoreanLegalEmbedder,
    ChromaVectorDB,
    BM25Index,
    LegalDocumentRetriever,
    HybridRetriever,
    AdapterChatbot
)

from config.settings import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title=settings.SERVICE_NAME,
    description="형사법 전문 AI 엔진 - RAG, LLM, Embeddings",
    version=settings.SERVICE_VERSION
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== AI Components 초기화 =====

embedder = None
vectordb = None
bm25_index = None
hybrid_retriever = None
llm_client = None
chatbot = None

@app.on_event("startup")
async def startup_event():
    """서비스 시작 시 AI 컴포넌트 초기화"""
    global embedder, vectordb, bm25_index, hybrid_retriever, llm_client, chatbot

    logger.info(f"🚀 Starting {settings.SERVICE_NAME}...")

    try:
        # 1. Embedder 초기화
        embedder = KoreanLegalEmbedder()
        logger.info("✅ Embedder initialized")

        # 2. VectorDB 초기화
        if settings.CHROMA_DIR.exists():
            vectordb = ChromaVectorDB(
                persist_directory=str(settings.CHROMA_DIR),
                collection_name="criminal_law_docs"
            )
            logger.info(f"✅ VectorDB loaded: {vectordb.get_count()} documents")
        else:
            logger.warning(f"⚠️  VectorDB not found at {settings.CHROMA_DIR}")

        # 3. BM25 Index 초기화
        if settings.BM25_DIR.exists():
            bm25_index = BM25Index()
            bm25_index.load(str(settings.BM25_DIR))
            logger.info(f"✅ BM25 index loaded: {bm25_index.get_count()} documents")
        else:
            logger.warning(f"⚠️  BM25 index not found at {settings.BM25_DIR}")

        # 4. Semantic Retriever 초기화
        if embedder and vectordb:
            semantic_retriever = LegalDocumentRetriever(
                embedder=embedder,
                vectordb=vectordb
            )

            # 5. Hybrid Retriever 초기화
            if bm25_index:
                hybrid_retriever = HybridRetriever(
                    semantic_retriever=semantic_retriever,
                    bm25_index=bm25_index,
                    fusion_method='rrf',
                    semantic_weight=0.5,
                    enable_adaptive_weighting=True
                )
                logger.info("✅ Hybrid Retriever initialized")
            else:
                hybrid_retriever = semantic_retriever
                logger.info("⚠️  Using Semantic Retriever only (BM25 not found)")

        # 6. LLM Client 초기화
        if settings.LLM_API_KEY:
            llm_client = create_llm_client(
                provider=settings.LLM_PROVIDER,
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL,
                base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS
            )
            logger.info(f"✅ LLM client initialized (provider={settings.LLM_PROVIDER})")

            # 7. Chatbot 초기화
            if hybrid_retriever:
                chatbot = AdapterChatbot(
                    retriever=hybrid_retriever,
                    llm_client=llm_client,
                    enable_self_critique=True,
                    critique_threshold=0.5
                )
                logger.info("✅ Constitutional AI Chatbot initialized")
        else:
            logger.warning("⚠️  LLM_API_KEY not set, chatbot will not be available")

    except Exception as e:
        logger.error(f"❌ Failed to initialize AI components: {e}")
        logger.info("Service will run in degraded mode")

@app.on_event("shutdown")
async def shutdown_event():
    """서비스 종료 시 정리"""
    logger.info("👋 Shutting down AI Service...")

# ===== Health Check =====

@app.get("/")
async def root():
    return {
        "name": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if llm_client else "degraded",
        "llm": "available" if llm_client else "unavailable",
        "embedder": "available" if embedder else "unavailable",
        "vectordb": f"{vectordb.get_count()} documents" if vectordb else "unavailable",
        "bm25": f"{bm25_index.get_count()} documents" if bm25_index else "unavailable",
        "retriever": "hybrid" if bm25_index else "semantic_only"
    }

# ===== Router 등록 (나중에 추가) =====
# from routers import chat, search, embeddings
# app.include_router(chat.router)
# app.include_router(search.router)
# app.include_router(embeddings.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
```

**Step 3: requirements.txt**

```txt
# apps/ai-service/requirements.txt
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
sqlalchemy>=2.0.23
asyncpg>=0.29.0
httpx>=0.25.2

# libs/rag_core에서 필요한 의존성은 root requirements.txt에 이미 있음
```

**Step 4: Git commit**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 파일 생성 확인
ls -la apps/ai-service/

# Git add
git add apps/ai-service/

# Commit
git commit -m "feat: add ai-service main.py and config

- Add config/settings.py with environment-based configuration
- Add main.py with libs/rag_core integration
- Initialize AI components (Embedder, VectorDB, BM25, LLM)
- Add health check endpoints
- Add requirements.txt for ai-service dependencies

AI Service will run on port 8001
Supports multiple LLM providers (OpenAI, Ollama, Anthropic)"

# Push
git push -u origin feature/ai-service-separation
```

**Step 5: 테스트**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# PYTHONPATH 설정
export PYTHONPATH=$(pwd):$PYTHONPATH

# 환경변수 설정 (.env 파일 사용 또는 직접 설정)
export LLM_API_KEY="your-api-key"
export LLM_PROVIDER="openai"

# AI Service 실행
cd apps/ai-service
python main.py

# 다른 터미널에서 테스트
curl http://localhost:8001/
curl http://localhost:8001/health
```

**예상 출력:**

```json
// GET /
{
  "name": "LawLaw AI Service",
  "version": "1.0.0",
  "status": "running"
}

// GET /health
{
  "status": "healthy",
  "llm": "available",
  "embedder": "available",
  "vectordb": "388000 documents",
  "bm25": "388000 documents",
  "retriever": "hybrid"
}
```

---

#### Day 3: models/database.py 및 precedent_feedback.py

**Step 1: models/database.py (Read-Only DB 연결)**

```python
# apps/ai-service/models/database.py
"""
Database Connection (Read-Only)
Django와 동일한 PostgreSQL 공유, 읽기 전용
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import logging

logger = logging.getLogger(__name__)

# 환경변수에서 DATABASE_URL 가져오기
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/lawlaw"
)

# Read-Only 엔진 생성
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # SQL 로그 비활성화 (프로덕션)
    pool_pre_ping=True,  # 연결 상태 확인
    pool_size=5,  # 읽기 전용이므로 작게
    max_overflow=10,
    # Read-Only 트랜잭션 격리 수준
    isolation_level="READ COMMITTED"
)

# AsyncSession factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# SQLAlchemy Base
Base = declarative_base()

async def get_db():
    """
    DB 세션 의존성

    Usage:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """
    DB 초기화 (테스트용)
    실제 테이블 생성은 Django migrations에서 수행
    """
    async with engine.begin() as conn:
        # 테이블은 생성하지 않음 (Read-Only)
        logger.info("✅ Database connection initialized (Read-Only)")

async def close_db():
    """DB 연결 종료"""
    await engine.dispose()
    logger.info("👋 Database connection closed")
```

**Step 2: models/precedent_feedback.py (Django 테이블 매핑)**

```python
# apps/ai-service/models/precedent_feedback.py
"""
Precedent Feedback Model (Read-Only)
Django의 precedent_feedback_stats 테이블 매핑
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float
from datetime import datetime
from .database import Base

class PrecedentFeedbackStats(Base):
    """
    판례 피드백 통계 (Read-Only)

    Django 모델과 동일한 테이블 매핑
    apps.backend.models.precedent_feedback.PrecedentFeedbackStats와 공유

    Note:
        - 이 모델은 읽기 전용입니다
        - 테이블 생성/수정은 Django migrations에서 수행
        - AI Service는 should_exclude=True인 판례 ID를 읽어서 필터링
    """
    __tablename__ = "precedent_feedback_stats"

    # Primary key
    precedent_id = Column(String(200), primary_key=True, index=True)

    # Aggregated stats
    total_likes = Column(Integer, default=0, nullable=False)
    total_dislikes = Column(Integer, default=0, nullable=False)
    like_ratio = Column(Float, default=0.0, nullable=False)  # 0.0 ~ 1.0
    total_feedback_count = Column(Integer, default=0, nullable=False)
    avg_relevance_score = Column(Float, nullable=True)

    # Exclusion flags
    should_exclude = Column(Boolean, default=False, nullable=False, index=True)
    exclusion_threshold = Column(Float, default=0.3, nullable=False)

    # Timestamp
    last_updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<PrecedentFeedbackStats {self.precedent_id} (👍 {self.total_likes} / 👎 {self.total_dislikes})>"
```

**Step 3: models/__init__.py**

```python
# apps/ai-service/models/__init__.py
"""
AI Service Models
SQLAlchemy models for read-only database access
"""

from .database import Base, get_db, init_db, close_db, engine
from .precedent_feedback import PrecedentFeedbackStats

__all__ = [
    'Base',
    'get_db',
    'init_db',
    'close_db',
    'engine',
    'PrecedentFeedbackStats',
]
```

**Step 4: Git commit**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

git add apps/ai-service/models/

git commit -m "feat: add ai-service database models (read-only)

- Add models/database.py with read-only PostgreSQL connection
- Add models/precedent_feedback.py (Django table mapping)
- Configure async SQLAlchemy engine
- Add get_db() dependency for FastAPI routes

DB Configuration:
- Read-only access to Django database
- Isolation level: READ COMMITTED
- Pool size: 5 (small, for reading only)
- Maps to Django's precedent_feedback_stats table"

git push origin feature/ai-service-separation
```

---

#### Day 4: services/feedback_adapter.py

**Step 1: services/feedback_adapter.py**

```python
# apps/ai-service/services/feedback_adapter.py
"""
Feedback Adapter
데이터베이스 기반 피드백 제공자 (Read-Only)
"""

from typing import Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from models.precedent_feedback import PrecedentFeedbackStats

logger = logging.getLogger(__name__)

class DatabaseFeedbackProvider:
    """
    데이터베이스 기반 피드백 제공자

    Django에서 관리하는 precedent_feedback_stats 테이블을 읽어서
    제외할 판례 ID 목록을 제공합니다.

    Usage:
        provider = DatabaseFeedbackProvider(db)
        excluded_ids = await provider.get_excluded_ids()
        # excluded_ids: {"precedent_id_1", "precedent_id_2", ...}
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_excluded_ids(self) -> Set[str]:
        """
        제외할 판례 ID 조회

        should_exclude=True인 판례 ID를 반환합니다.
        이 판례들은 RAG 검색 결과에서 필터링됩니다.

        Returns:
            제외할 판례 ID 집합
        """
        try:
            result = await self.db.execute(
                select(PrecedentFeedbackStats.precedent_id)
                .where(PrecedentFeedbackStats.should_exclude == True)
            )
            excluded_ids = result.scalars().all()

            if excluded_ids:
                logger.info(f"📊 Loaded {len(excluded_ids)} excluded precedents from DB")
            else:
                logger.debug("📊 No excluded precedents found in DB")

            return set(excluded_ids)

        except Exception as e:
            logger.warning(f"⚠️  Failed to get excluded IDs from DB: {e}")
            logger.info("Continuing without feedback filtering")
            return set()

    async def get_feedback_stats(self, precedent_id: str) -> dict:
        """
        특정 판례의 피드백 통계 조회

        Args:
            precedent_id: 판례 ID

        Returns:
            피드백 통계 dict 또는 None
        """
        try:
            result = await self.db.execute(
                select(PrecedentFeedbackStats)
                .where(PrecedentFeedbackStats.precedent_id == precedent_id)
            )
            stats = result.scalar_one_or_none()

            if stats:
                return {
                    "precedent_id": stats.precedent_id,
                    "total_likes": stats.total_likes,
                    "total_dislikes": stats.total_dislikes,
                    "total_feedback_count": stats.total_feedback_count,
                    "like_ratio": stats.like_ratio,
                    "avg_relevance_score": stats.avg_relevance_score,
                    "should_exclude": stats.should_exclude,
                    "exclusion_threshold": stats.exclusion_threshold,
                    "last_updated": stats.last_updated.isoformat() if stats.last_updated else None
                }
            else:
                return None

        except Exception as e:
            logger.warning(f"⚠️  Failed to get feedback stats for {precedent_id}: {e}")
            return None
```

**Step 2: services/__init__.py**

```python
# apps/ai-service/services/__init__.py
"""
AI Service Services
비즈니스 로직 및 AI 서비스
"""

from .feedback_adapter import DatabaseFeedbackProvider

__all__ = [
    'DatabaseFeedbackProvider',
]
```

**Step 3: Git commit**

```bash
git add apps/ai-service/services/

git commit -m "feat: add feedback adapter for database filtering

- Add services/feedback_adapter.py
- Implement DatabaseFeedbackProvider (read-only)
- Get excluded precedent IDs from Django database
- Support feedback-based RAG filtering

This adapter reads precedent_feedback_stats table
to filter out low-quality precedents from RAG results."

git push origin feature/ai-service-separation
```

---

#### Day 5: routers/chat.py (RAG 챗봇 API)

**Step 1: routers/chat.py**

```python
# apps/ai-service/routers/chat.py
"""
Chat Router
RAG 챗봇 API 엔드포인트
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from models.database import get_db
from services.feedback_adapter import DatabaseFeedbackProvider
from libs.rag_core.retrieval.filters import filter_results

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/chat", tags=["chat"])

# ===== Request/Response Models =====

class RAGRequest(BaseModel):
    """RAG 질의응답 요청"""
    query: str = Field(..., description="사용자 질문", min_length=1)
    top_k: int = Field(5, description="검색할 문서 수", ge=1, le=20)
    include_sources: bool = Field(True, description="출처 포함 여부")
    enable_critique: bool = Field(True, description="Constitutional AI 활성화")

class Source(BaseModel):
    """출처 정보"""
    source: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}

class RAGResponse(BaseModel):
    """RAG 질의응답 응답"""
    answer: str
    sources: List[Source]
    query: str
    model: str
    timestamp: str
    critique_log: Optional[List[Dict[str, Any]]] = None

# ===== API Endpoints =====

@router.post("/rag", response_model=RAGResponse)
async def rag_chat(
    request: RAGRequest,
    app_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    RAG 기반 질의응답

    - Constitutional AI 적용
    - Hybrid Retrieval (Semantic + BM25)
    - Feedback-based filtering

    인증:
        - 이 엔드포인트는 인증이 없습니다
        - Django Backend에서 이미 JWT 검증을 수행했다고 가정
        - user_id는 헤더로 전달받음: X-User-ID (선택)

    Args:
        request: RAG 요청 (query, top_k, include_sources)
        app_request: FastAPI Request 객체
        db: DB 세션 (피드백 조회용)

    Returns:
        RAG 응답 (answer, sources, metadata)
    """
    try:
        # AI 컴포넌트 가져오기
        chatbot = app_request.app.state.chatbot
        if not chatbot:
            raise HTTPException(
                status_code=503,
                detail="AI chatbot is not available. Please check LLM_API_KEY configuration."
            )

        # 사용자 ID (선택)
        user_id = app_request.headers.get("X-User-ID")
        if user_id:
            logger.info(f"📨 RAG request from user {user_id}: {request.query[:50]}...")
        else:
            logger.info(f"📨 RAG request (anonymous): {request.query[:50]}...")

        # 1. 피드백 필터 적용 (DB에서 제외할 판례 ID 조회)
        feedback_provider = DatabaseFeedbackProvider(db)
        excluded_ids = await feedback_provider.get_excluded_ids()

        # 2. RAG 검색 (top_k + excluded 보정)
        #    excluded_ids가 있으면 더 많이 검색해서 필터링 후 top_k 유지
        retrieval_top_k = request.top_k + min(len(excluded_ids), 5)

        # 3. Constitutional AI + RAG
        result = chatbot.chat(
            query=request.query,
            top_k=retrieval_top_k,
            include_critique_log=request.enable_critique
        )

        # 4. 피드백 필터 적용 (제외할 판례 제거)
        sources = result.get('sources', [])
        if excluded_ids:
            sources = filter_results(
                results=sources,
                excluded_ids=excluded_ids,
                id_key='source'
            )
            logger.info(f"🔍 Filtered {len(result['sources']) - len(sources)} precedents by feedback")

        # 5. top_k로 잘라내기
        sources = sources[:request.top_k]

        # 6. 응답 생성
        return RAGResponse(
            answer=result['answer'],
            sources=[
                Source(
                    source=s.get('source', ''),
                    content=s.get('content', ''),
                    score=s.get('score', 0.0),
                    metadata=s.get('metadata', {})
                )
                for s in (sources if request.include_sources else [])
            ],
            query=request.query,
            model=result.get('model', 'Unknown'),
            timestamp=datetime.now().isoformat(),
            critique_log=result.get('critique_log') if request.enable_critique else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ RAG chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/health")
async def chat_health(app_request: Request):
    """Chat 라우터 헬스체크"""
    chatbot = app_request.app.state.chatbot
    return {
        "status": "healthy" if chatbot else "unavailable",
        "chatbot": "available" if chatbot else "not_initialized"
    }
```

**Step 2: main.py에 router 등록**

```python
# apps/ai-service/main.py (수정)

# ... (기존 코드) ...

# ===== Router 등록 =====
from routers import chat

app.include_router(chat.router)

# ... (기존 코드) ...
```

**Step 3: routers/__init__.py**

```python
# apps/ai-service/routers/__init__.py
"""
AI Service Routers
FastAPI 라우터 모음
"""

from . import chat

__all__ = ['chat']
```

**Step 4: libs/rag_core/retrieval/filters.py 확인**

libs/rag_core에 이미 filter_results 함수가 있는지 확인하고, 없으면 추가:

```python
# libs/rag_core/retrieval/filters.py
"""
Retrieval Filters
검색 결과 필터링 (순수 로직, DB 비의존)
"""

from typing import List, Dict, Any, Set

def filter_results(
    results: List[Dict[str, Any]],
    excluded_ids: Set[str],
    id_key: str = 'source'
) -> List[Dict[str, Any]]:
    """
    검색 결과 필터링

    excluded_ids에 포함된 ID를 가진 결과를 제거합니다.

    Args:
        results: 검색 결과 리스트
        excluded_ids: 제외할 ID 집합
        id_key: 결과에서 ID를 가져올 키 (기본: 'source')

    Returns:
        필터링된 검색 결과

    Example:
        >>> results = [
        ...     {"source": "doc1", "content": "..."},
        ...     {"source": "doc2", "content": "..."},
        ...     {"source": "doc3", "content": "..."}
        ... ]
        >>> excluded = {"doc2"}
        >>> filtered = filter_results(results, excluded)
        >>> len(filtered)
        2
    """
    if not excluded_ids:
        return results

    filtered = []
    for result in results:
        doc_id = result.get(id_key)
        if doc_id and doc_id not in excluded_ids:
            filtered.append(result)

    return filtered
```

**Step 5: Git commit**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# libs/rag_core/retrieval/filters.py 추가 (필요시)
# git add libs/rag_core/retrieval/filters.py

# ai-service router 추가
git add apps/ai-service/routers/
git add apps/ai-service/main.py

git commit -m "feat: add RAG chat API endpoint

- Add routers/chat.py with /v1/chat/rag endpoint
- Implement RAGRequest/RAGResponse models
- Add Constitutional AI + Hybrid Retrieval
- Add feedback-based filtering (read from DB)
- Register chat router in main.py

API Features:
- POST /v1/chat/rag: RAG-based Q&A
- Hybrid search (Semantic + BM25)
- Feedback filtering (exclude low-quality precedents)
- Constitutional AI critique (optional)
- GET /v1/chat/health: Router health check"

git push origin feature/ai-service-separation
```

**Step 6: 테스트**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# PYTHONPATH 설정
export PYTHONPATH=$(pwd):$PYTHONPATH

# 환경변수 설정
export LLM_API_KEY="your-api-key"
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/lawlaw"

# AI Service 실행
cd apps/ai-service
python main.py

# 다른 터미널에서 테스트
curl -X POST http://localhost:8001/v1/chat/rag \
  -H "Content-Type: application/json" \
  -d '{
    "query": "음주운전 처벌 기준은?",
    "top_k": 3,
    "include_sources": true,
    "enable_critique": true
  }'

# 헬스체크
curl http://localhost:8001/v1/chat/health
```

**예상 출력:**

```json
{
  "answer": "음주운전 처벌 기준은 혈중알코올농도에 따라 다릅니다...",
  "sources": [
    {
      "source": "판례번호",
      "content": "판례 내용...",
      "score": 0.95,
      "metadata": {}
    }
  ],
  "query": "음주운전 처벌 기준은?",
  "model": "GPT-4 Turbo + Constitutional AI",
  "timestamp": "2025-11-20T10:00:00",
  "critique_log": [...]
}
```

---

### Week 2: apps/backend 수정 및 통합

#### Day 6-7: apps/backend에서 AI 서비스 추출

**현재 apps/backend 상태 분석:**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/apps/backend

# AI 관련 파일 (ai-service로 이동 예정)
ls -la services/case_analyzer.py
ls -la services/document_generator.py
ls -la services/scenario_detector.py

# 유지할 파일 (비즈니스 로직)
ls -la routers/auth.py
ls -la routers/cases.py
ls -la routers/precedents.py
ls -la models/user.py
ls -la models/case.py
ls -la models/precedent.py
```

**Step 1: apps/backend/services → apps/ai-service/services 복사**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# case_analyzer.py 복사
cp apps/backend/services/case_analyzer.py apps/ai-service/services/

# document_generator.py 복사
cp apps/backend/services/document_generator.py apps/ai-service/services/

# scenario_detector.py 복사
cp apps/backend/services/scenario_detector.py apps/ai-service/services/
```

**Step 2: ai-service/services 파일들의 import 수정**

파일들이 이미 libs/rag_core를 사용하고 있는지 확인하고, 필요시 수정:

```python
# apps/ai-service/services/case_analyzer.py (확인 및 수정)

# 기존 import가 apps.backend.core인 경우 수정
# from apps.backend.core.llm import create_llm_client
# ↓
from libs.rag_core import create_llm_client, HybridRetriever

# 나머지는 그대로 유지
```

**Step 3: ai-service에 분석/생성 API 추가**

```python
# apps/ai-service/routers/analyze.py
"""
Analyze Router
사건 분석 및 문서 생성 API
"""

from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/analyze", tags=["analyze"])

# ===== Request/Response Models =====

class AnalyzeRequest(BaseModel):
    """사건 분석 요청"""
    text: str = Field(..., description="분석할 사건 텍스트")
    include_related_cases: bool = Field(True, description="관련 판례 검색 포함")

class AnalyzeResponse(BaseModel):
    """사건 분석 응답"""
    analysis: Dict[str, Any]
    related_cases: List[Dict[str, Any]]

class GenerateRequest(BaseModel):
    """문서 생성 요청"""
    case_info: Dict[str, Any]
    document_type: str = Field(..., description="문서 유형 (complaint, response, etc.)")

class GenerateResponse(BaseModel):
    """문서 생성 응답"""
    document: str
    metadata: Dict[str, Any]

# ===== API Endpoints =====

@router.post("/case", response_model=AnalyzeResponse)
async def analyze_case(
    request: AnalyzeRequest,
    app_request: Request
):
    """
    사건 분석

    텍스트를 분석하여 사건 정보를 추출하고
    관련 판례를 검색합니다.
    """
    try:
        # CaseAnalyzer import (지연 import)
        from services.case_analyzer import CaseAnalyzer

        # AI 컴포넌트 가져오기
        llm_client = app_request.app.state.llm_client
        retriever = app_request.app.state.retriever

        if not llm_client:
            raise HTTPException(
                status_code=503,
                detail="LLM client is not available"
            )

        # CaseAnalyzer 초기화
        analyzer = CaseAnalyzer(
            llm_client=llm_client,
            retriever=retriever if request.include_related_cases else None
        )

        # 분석 수행
        result = analyzer.analyze(request.text)

        return AnalyzeResponse(
            analysis=result.get('analysis', {}),
            related_cases=result.get('related_cases', [])
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Case analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@router.post("/generate", response_model=GenerateResponse)
async def generate_document(
    request: GenerateRequest,
    app_request: Request
):
    """
    법률 문서 생성

    사건 정보를 기반으로 법률 문서를 생성합니다.
    """
    try:
        from services.document_generator import DocumentGenerator

        llm_client = app_request.app.state.llm_client
        if not llm_client:
            raise HTTPException(
                status_code=503,
                detail="LLM client is not available"
            )

        generator = DocumentGenerator(llm_client=llm_client)

        result = generator.generate(
            case_info=request.case_info,
            document_type=request.document_type
        )

        return GenerateResponse(
            document=result.get('document', ''),
            metadata=result.get('metadata', {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Document generation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}"
        )
```

**Step 4: ai-service/main.py에 router 등록**

```python
# apps/ai-service/main.py (수정)

# ... (기존 코드) ...

# ===== Router 등록 =====
from routers import chat, analyze

app.include_router(chat.router)
app.include_router(analyze.router)

# ... (기존 코드) ...
```

**Step 5: services/__init__.py 업데이트**

```python
# apps/ai-service/services/__init__.py
"""
AI Service Services
"""

from .feedback_adapter import DatabaseFeedbackProvider

# Lazy import (필요시 import)
# from .case_analyzer import CaseAnalyzer
# from .document_generator import DocumentGenerator
# from .scenario_detector import ScenarioDetector

__all__ = [
    'DatabaseFeedbackProvider',
]
```

**Step 6: Git commit**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

git add apps/ai-service/services/case_analyzer.py
git add apps/ai-service/services/document_generator.py
git add apps/ai-service/services/scenario_detector.py
git add apps/ai-service/routers/analyze.py
git add apps/ai-service/main.py

git commit -m "feat: add analysis and generation APIs

- Copy case_analyzer.py from apps/backend
- Copy document_generator.py from apps/backend
- Copy scenario_detector.py from apps/backend
- Add routers/analyze.py with /v1/analyze endpoints
- POST /v1/analyze/case: Case analysis with related precedents
- POST /v1/analyze/generate: Legal document generation

Services now available in AI Service (port 8001)"

git push origin feature/ai-service-separation
```

---

#### Day 8-9: apps/backend 프록시 구현

**목표:** apps/backend의 chat, cases 라우터를 AI Service 프록시로 변경

**Step 1: apps/backend/routers/chat.py 프록시로 변경**

먼저 기존 파일 백업:

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/apps/backend/routers

# 백업 (나중에 참고용)
cp chat.py chat.py.backup
```

새로운 chat.py (프록시):

```python
# apps/backend/routers/chat.py (완전히 새로 작성)
"""
Chat Router - AI Service Proxy
RAG 챗봇 API를 AI Service로 프록시
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import os
import logging

from apps.backend.core.auth.dependencies import get_current_user
from apps.backend.models.user import User
# from apps.backend.models.chat_history import ChatHistory  # 필요시
from apps.backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# AI Service URL
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")

# ===== Request/Response Models =====

class ChatRequest(BaseModel):
    """채팅 요청"""
    query: str
    top_k: int = 5
    include_sources: bool = True
    enable_critique: bool = True

class ChatResponse(BaseModel):
    """채팅 응답"""
    answer: str
    sources: List[Dict[str, Any]]
    query: str
    model: str
    timestamp: str
    critique_log: Optional[List[Dict[str, Any]]] = None

# ===== Router Setup =====

def setup_chat_routes(**kwargs) -> APIRouter:
    """
    Chat 라우터 설정 (하위 호환성)

    기존 setup_chat_routes(chatbot, llm_client, ...) 시그니처 유지
    하지만 실제로는 사용하지 않고 AI Service로 프록시
    """
    router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

    @router.post("/rag", response_model=ChatResponse)
    async def chat_rag(
        request: ChatRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """
        RAG 채팅 (AI Service 프록시)

        Flow:
        1. Django Backend: JWT 검증 (get_current_user)
        2. AI Service 호출 (내부 HTTP)
        3. Django Backend: ChatHistory 저장 (선택)
        4. 응답 반환
        """
        try:
            logger.info(f"📨 RAG request from user {current_user.id}: {request.query[:50]}...")

            # AI Service 호출
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{AI_SERVICE_URL}/v1/chat/rag",
                    json=request.dict(),
                    headers={"X-User-ID": str(current_user.id)}
                )
                response.raise_for_status()
                ai_result = response.json()

            # ChatHistory 저장 (선택)
            # chat_history = ChatHistory(
            #     user_id=current_user.id,
            #     query=request.query,
            #     answer=ai_result['answer'],
            #     sources=ai_result['sources'],
            #     model=ai_result['model']
            # )
            # db.add(chat_history)
            # await db.commit()

            logger.info(f"✅ RAG response sent to user {current_user.id}")
            return ChatResponse(**ai_result)

        except httpx.HTTPError as e:
            logger.error(f"❌ AI Service error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"AI Service unavailable: {str(e)}"
            )
        except Exception as e:
            logger.error(f"❌ Chat error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

    @router.get("/health")
    async def chat_health():
        """Chat 프록시 헬스체크"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{AI_SERVICE_URL}/v1/chat/health")
                response.raise_for_status()
                return {"status": "healthy", "ai_service": response.json()}
        except:
            return {"status": "degraded", "ai_service": "unavailable"}

    return router
```

**Step 2: apps/backend/routers/adapters.py 프록시로 변경**

```python
# apps/backend/routers/adapters.py (프록시)
"""
Adapters Router - AI Service Proxy
Constitutional AI 어댑터 API
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import logging

from apps.backend.core.auth.dependencies import get_current_user
from apps.backend.models.user import User

logger = logging.getLogger(__name__)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")

# ===== Request/Response Models =====

class AdapterRequest(BaseModel):
    """어댑터 요청"""
    query: str
    top_k: int = 5

class AdapterResponse(BaseModel):
    """어댑터 응답"""
    answer: str
    sources: list
    critique_log: Optional[list] = None

# ===== Router Setup =====

def setup_adapter_routes(**kwargs) -> APIRouter:
    """Adapter 라우터 설정"""
    router = APIRouter(prefix="/api/v1/adapters", tags=["adapters"])

    @router.post("/chat", response_model=AdapterResponse)
    async def adapter_chat(
        request: AdapterRequest,
        current_user: User = Depends(get_current_user)
    ):
        """Constitutional AI 어댑터 채팅 (프록시)"""
        try:
            # AI Service의 /v1/chat/rag 호출 (Constitutional AI 포함)
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{AI_SERVICE_URL}/v1/chat/rag",
                    json={
                        "query": request.query,
                        "top_k": request.top_k,
                        "include_sources": True,
                        "enable_critique": True  # Constitutional AI 활성화
                    },
                    headers={"X-User-ID": str(current_user.id)}
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=503,
                detail=f"AI Service unavailable: {str(e)}"
            )

    return router
```

**Step 3: apps/backend/routers/cases.py 일부 수정**

```python
# apps/backend/routers/cases.py (일부 수정)

# 기존 import
from apps.backend.services.file_parser import FileParser
from apps.backend.services.scenario_detector import ScenarioDetector
# from apps.backend.services.case_analyzer import CaseAnalyzer  # 제거

import httpx
import os

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")

def setup_case_routes(
    scenario_detector: ScenarioDetector,
    file_parser: FileParser,
    upload_dir: Path,
    **kwargs  # case_analyzer 제거됨
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

    @router.post("/analyze")
    async def analyze_case(
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user)
    ):
        """사건 분석 (AI Service 프록시)"""
        try:
            # 1. 파일 파싱 (Backend에서 수행)
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as f:
                f.write(await file.read())

            text = file_parser.parse(file_path)

            # 2. AI Service 호출
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{AI_SERVICE_URL}/v1/analyze/case",
                    json={
                        "text": text,
                        "include_related_cases": True
                    },
                    headers={"X-User-ID": str(current_user.id)}
                )
                response.raise_for_status()
                analysis_result = response.json()

            # 3. Case DB 저장 (Backend에서 수행)
            case = Case(
                user_id=current_user.id,
                title=file.filename,
                content=text,
                analysis=analysis_result['analysis'],
                status="analyzed"
            )
            db.add(case)
            await db.commit()

            return analysis_result

        except Exception as e:
            logger.error(f"❌ Case analysis error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # 다른 엔드포인트 (CRUD)는 그대로 유지
    # ...

    return router
```

**Step 4: apps/backend/main.py 수정**

```python
# apps/backend/main.py (수정)

# AI 관련 import 제거
# from apps.backend.services.case_analyzer import CaseAnalyzer  # 제거
# from apps.backend.services.document_generator import DocumentGenerator  # 제거

# AI 컴포넌트 초기화 제거
# case_analyzer = None
# document_generator = None
# if llm_client:
#     case_analyzer = CaseAnalyzer(...)  # 제거
#     document_generator = DocumentGenerator(...)  # 제거

# Router 등록 시 AI 컴포넌트 제거
chat_router = setup_chat_routes()  # 인자 제거
cases_router = setup_case_routes(
    scenario_detector=scenario_detector,
    file_parser=file_parser,
    upload_dir=UPLOAD_DIR
    # case_analyzer=case_analyzer  # 제거
)
```

**Step 5: Git commit**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 백업 파일 제외
git add apps/backend/routers/chat.py
git add apps/backend/routers/adapters.py
git add apps/backend/routers/cases.py
git add apps/backend/main.py

git commit -m "refactor: convert backend routers to AI Service proxies

- Update chat.py to proxy /v1/chat/rag to AI Service
- Update adapters.py to proxy Constitutional AI calls
- Update cases.py to use AI Service for analysis
- Remove CaseAnalyzer, DocumentGenerator from main.py
- Add AI_SERVICE_URL environment variable support

Backend now acts as API Gateway:
- Handles JWT authentication
- Proxies AI requests to AI Service (8001)
- Manages business data (User, Case, Precedent)"

git push origin feature/ai-service-separation
```

---

#### Day 10: 통합 테스트

**Step 1: 환경변수 설정**

```bash
# .env 파일 생성 (root)
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

cat > .env << 'EOF'
# LLM Configuration
LLM_PROVIDER=openai
LLM_API_KEY=your-api-key-here
LLM_MODEL=gpt-4-turbo-preview
LLM_BASE_URL=
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=2000

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/lawlaw

# AI Service
AI_SERVICE_URL=http://localhost:8001
EOF

# .env는 .gitignore에 이미 추가되어 있음
```

**Step 2: 동시 실행 스크립트**

```bash
# scripts/run_dev.sh
cat > scripts/run_dev.sh << 'EOF'
#!/bin/bash

# 개발 환경 실행 스크립트

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==================================="
echo "LawLaw Development Environment"
echo "==================================="

# PYTHONPATH 설정
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# .env 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# AI Service 실행 (백그라운드)
echo ""
echo "[1/3] Starting AI Service (port 8001)..."
cd apps/ai-service
python main.py > ../../logs/ai-service.log 2>&1 &
AI_SERVICE_PID=$!
echo "✅ AI Service started (PID: $AI_SERVICE_PID)"

# 5초 대기 (AI Service 초기화)
sleep 5

# Backend 실행 (백그라운드)
cd "$PROJECT_ROOT"
echo ""
echo "[2/3] Starting Backend (port 8000)..."
cd apps/backend
python main.py > ../../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# 5초 대기
sleep 5

# Frontend 실행 (포그라운드)
cd "$PROJECT_ROOT"
echo ""
echo "[3/3] Starting Frontend (port 3000)..."
cd apps/web-frontend
npm start

# Ctrl+C 시 모든 프로세스 종료
trap "kill $AI_SERVICE_PID $BACKEND_PID" EXIT
EOF

chmod +x scripts/run_dev.sh

# logs 디렉토리 생성
mkdir -p logs
echo "*.log" >> .gitignore
```

**Step 3: 통합 테스트**

```bash
# Terminal 1: AI Service
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
export PYTHONPATH=$(pwd):$PYTHONPATH
export $(cat .env | grep -v '^#' | xargs)
cd apps/ai-service
python main.py

# Terminal 2: Backend
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
export PYTHONPATH=$(pwd):$PYTHONPATH
export $(cat .env | grep -v '^#' | xargs)
cd apps/backend
python main.py

# Terminal 3: 테스트
# 1. Health check
curl http://localhost:8001/health
curl http://localhost:8000/health

# 2. AI Service 직접 호출
curl -X POST http://localhost:8001/v1/chat/rag \
  -H "Content-Type: application/json" \
  -d '{"query": "음주운전 처벌", "top_k": 3}'

# 3. Backend 프록시 호출 (JWT 필요)
# 먼저 로그인하여 토큰 획득
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}' \
  | jq -r '.access_token')

# RAG 챗봇 호출
curl -X POST http://localhost:8000/api/v1/chat/rag \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "음주운전 처벌", "top_k": 3}'
```

**Step 4: 통합 테스트 스크립트**

```bash
# scripts/test_integration.sh
cat > scripts/test_integration.sh << 'EOF'
#!/bin/bash

set -e

echo "======================================="
echo "Integration Test: Backend <-> AI Service"
echo "======================================="

# 1. AI Service 헬스체크
echo ""
echo "[1/4] Testing AI Service..."
curl -s http://localhost:8001/health | jq .

# 2. Backend 헬스체크
echo ""
echo "[2/4] Testing Backend..."
curl -s http://localhost:8000/health | jq .

# 3. Backend Chat 프록시 헬스체크
echo ""
echo "[3/4] Testing Backend Chat Proxy..."
curl -s http://localhost:8000/api/v1/chat/health | jq .

# 4. RAG 챗봇 직접 테스트 (AI Service)
echo ""
echo "[4/4] Testing RAG Chat (AI Service direct)..."
curl -s -X POST http://localhost:8001/v1/chat/rag \
  -H "Content-Type: application/json" \
  -d '{"query": "테스트 질문", "top_k": 1, "include_sources": false}' \
  | jq '.answer'

echo ""
echo "======================================="
echo "✅ All integration tests passed!"
echo "======================================="
EOF

chmod +x scripts/test_integration.sh
```

**Step 5: Git commit**

```bash
git add scripts/run_dev.sh
git add scripts/test_integration.sh
git add .gitignore

git commit -m "test: add development and integration test scripts

- Add scripts/run_dev.sh for running all services
- Add scripts/test_integration.sh for integration testing
- Add logs/ to .gitignore

Usage:
- ./scripts/run_dev.sh: Start all services
- ./scripts/test_integration.sh: Test Backend <-> AI Service"

git push origin feature/ai-service-separation
```

---

### Phase 1 완료 체크리스트

```bash
# Phase 1 완료 확인
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

echo "=== Phase 1 Checklist ==="
echo ""
echo "✅ Week 1: apps/ai-service 구축"
echo "  [x] Day 1: Directory structure created"
echo "  [x] Day 2: config/settings.py, main.py"
echo "  [x] Day 3: models/database.py, precedent_feedback.py"
echo "  [x] Day 4: services/feedback_adapter.py"
echo "  [x] Day 5: routers/chat.py"
echo ""
echo "✅ Week 2: apps/backend 수정"
echo "  [x] Day 6-7: AI services copied to ai-service"
echo "  [x] Day 8-9: Backend routers converted to proxies"
echo "  [x] Day 10: Integration tests"
echo ""
echo "✅ Git Status"
ls -la apps/ai-service/ | grep -E "(main.py|routers|services|models)"
echo ""
echo "✅ Services Running"
curl -s http://localhost:8001/health | jq -r '.status'
curl -s http://localhost:8000/health | jq -r '.status'
```

---

### Phase 1 PR 생성 및 머지

**Step 1: PR 준비**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 최종 push
git push origin feature/ai-service-separation

# GitHub에서 PR 생성
# https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2/compare/develop...feature/ai-service-separation
```

**PR Title:**
```
feat: Separate AI Service from Backend (Phase 1)
```

**PR Description:**

```markdown
## 📋 변경 사항

### ✅ apps/ai-service 구축
- FastAPI 기반 AI 전용 엔진 (포트 8001)
- libs/rag_core import 및 활용
- 독립 실행 가능

**주요 파일:**
- `main.py`: AI 컴포넌트 초기화 (Embedder, VectorDB, LLM, Chatbot)
- `config/settings.py`: 환경변수 기반 설정
- `routers/chat.py`: RAG 챗봇 API (`/v1/chat/rag`)
- `routers/analyze.py`: 사건 분석/문서 생성 API
- `services/feedback_adapter.py`: DB 피드백 필터 (Read-Only)
- `models/database.py`: PostgreSQL 연결 (Read-Only)

### ✅ apps/backend 리팩토링
- AI 로직 제거, 비즈니스 로직만 유지
- AI Service 프록시로 변경

**변경된 파일:**
- `routers/chat.py`: AI Service 프록시 (`POST /api/v1/chat/rag`)
- `routers/adapters.py`: Constitutional AI 프록시
- `routers/cases.py`: 분석 API 프록시
- `main.py`: AI 컴포넌트 초기화 제거

### ✅ 통합 테스트
- Backend (8000) ↔ AI Service (8001) HTTP 통신
- JWT 인증 유지 (Backend에서 처리)
- 피드백 필터링 동작 확인

## 🎯 변경 이유

### 문제점
- 모든 AI 로직이 Backend에 혼재
- GPU 서버에 AI 서비스만 배포 불가능
- 관심사 분리 부족

### 해결책
- AI Service 독립 실행 (포트 8001)
- Backend는 API Gateway 역할
- libs/rag_core 공유

## 🧪 테스트

### 로컬 테스트
```bash
# Terminal 1: AI Service
cd apps/ai-service && python main.py

# Terminal 2: Backend
cd apps/backend && python main.py

# Terminal 3: Integration test
./scripts/test_integration.sh
```

### 체크리스트
- [x] AI Service 독립 실행 (8001)
- [x] Backend 실행 (8000)
- [x] Backend → AI Service 프록시 동작
- [x] RAG 챗봇 기능 정상
- [x] 피드백 필터링 동작
- [x] JWT 인증 유지
- [x] libs/rag_core import 성공

## ⚠️ Breaking Changes

### 환경변수 추가
```bash
# .env에 추가 필요
AI_SERVICE_URL=http://localhost:8001
```

### 실행 방법 변경
```bash
# 기존 (Backend만)
cd apps/backend && python main.py

# 변경 후 (Backend + AI Service)
./scripts/run_dev.sh
# 또는
# Terminal 1: cd apps/ai-service && python main.py
# Terminal 2: cd apps/backend && python main.py
```

## 📝 다음 단계 (Phase 2)

Phase 1 완료 후:
- [ ] Phase 2: Django 전환 시작
- [ ] Django 프로젝트 생성
- [ ] SQLAlchemy → Django ORM 마이그레이션
- [ ] FastAPI auth → Django SimpleJWT

## 👥 리뷰어

@팀원1 @팀원2

## 📚 관련 문서

- [DJANGO_MIGRATION_PLAN.md](docs/DJANGO_MIGRATION_PLAN.md)
- [MIGRATION_MASTER_PLAN.md](docs/MIGRATION_MASTER_PLAN.md)
```

**Step 2: PR 머지**

1. PR 생성
2. 팀원 리뷰
3. CI/CD 통과 확인
4. Approve 후 머지
5. develop 브랜치 업데이트

```bash
# 머지 후
git checkout develop
git pull origin develop

# 브랜치 정리
git branch -d feature/ai-service-separation
```

---

## 🔄 Phase 1.5: Django 전환 준비 (3일) ⭐ 필수

> **중요**: 이 단계는 원래 문서에 누락되었으나, Django 전환의 성공을 위해 **반드시 필요**합니다.
> Phase 1 완료 후, Phase 2 시작 전에 수행하세요.

### 목표

- 기존 SQLite/PostgreSQL DB 스키마 분석
- Django 모델과 기존 테이블 매핑 전략 수립
- Fake migration으로 데이터 손실 없이 Django 관리 시작
- AI Service DB 모델 간소화

### 현재 DB 상태 확인

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# SQLite DB 확인
ls -lh data/lawlaw.db

# 테이블 목록 확인
sqlite3 data/lawlaw.db ".tables"
# 출력: precedent_feedback  precedent_feedback_stats  precedents  users

# users 테이블 스키마 확인
sqlite3 data/lawlaw.db ".schema users"
```

**예상 출력:**
```sql
CREATE TABLE users (
    id UUID NOT NULL,
    email VARCHAR NOT NULL,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR NOT NULL,
    lawyer_registration_number VARCHAR,
    specializations JSON NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id)
);
```

---

### Day 0.1: DB 마이그레이션 전략 선택

#### Option A: SQLite 유지 (개발 환경)

**장점:**
- ✅ 기존 데이터 그대로 사용
- ✅ 추가 DB 설정 불필요
- ✅ 빠른 시작

**단점:**
- ⚠️ JSON 필드 제한적 지원
- ⚠️ 동시성 제한
- ⚠️ 프로덕션 비권장

**Django settings.py:**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR.parent.parent / 'data' / 'lawlaw.db',
    }
}
```

#### Option B: PostgreSQL 전환 (권장)

**장점:**
- ✅ 프로덕션 대비
- ✅ JSON 필드 완전 지원
- ✅ 동시성 우수
- ✅ Django 최적화

**단점:**
- ⚠️ PostgreSQL 설치 필요
- ⚠️ 데이터 마이그레이션 필요

**마이그레이션 절차:**
```bash
# 1. PostgreSQL 설치 (macOS)
brew install postgresql@15
brew services start postgresql@15

# 2. DB 생성
createdb lawlaw

# 3. SQLite → PostgreSQL 데이터 이전 (나중에 수행)
# Django로 dumpdata → loaddata
```

**선택 가이드:**
- MVP 개발 속도 중시 → **Option A (SQLite)**
- 프로덕션 준비 중시 → **Option B (PostgreSQL)**

---

### Day 0.2: Django inspectdb 실행 (중요!)

**목적**: 기존 DB 테이블을 Django 모델로 자동 변환

#### Step 1: 임시 Django 프로젝트 생성

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 임시 작업 디렉토리
mkdir -p temp_django_inspect
cd temp_django_inspect

# 가상환경 (선택)
python -m venv venv
source venv/bin/activate

# Django 설치
pip install Django psycopg2-binary  # PostgreSQL용
# 또는
pip install Django  # SQLite용

# 프로젝트 생성
django-admin startproject inspect_project .
```

#### Step 2: settings.py 수정 (기존 DB 연결)

```python
# temp_django_inspect/inspect_project/settings.py

# Option A: SQLite 사용 시
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '../data/lawlaw.db',
    }
}

# Option B: PostgreSQL 사용 시 (데이터 이전 후)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'lawlaw',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

#### Step 3: inspectdb 실행

```bash
cd temp_django_inspect

# 모든 테이블 분석
python manage.py inspectdb > inspected_models.py

# 확인
cat inspected_models.py
```

**예상 출력:**
```python
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table

from django.db import models

class Users(models.Model):
    id = models.UUIDField(primary_key=True)
    email = models.CharField(unique=True, max_length=255)
    hashed_password = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    lawyer_registration_number = models.CharField(max_length=255, blank=True, null=True)
    specializations = models.JSONField()
    is_active = models.BooleanField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False  # ← 중요! Django가 테이블 관리하지 않음
        db_table = 'users'


class PrecedentFeedbackStats(models.Model):
    precedent_id = models.CharField(primary_key=True, max_length=200)
    total_likes = models.IntegerField()
    total_dislikes = models.IntegerField()
    like_ratio = models.FloatField()
    total_feedback_count = models.IntegerField()
    avg_relevance_score = models.FloatField(blank=True, null=True)
    should_exclude = models.BooleanField()
    exclusion_threshold = models.FloatField()
    last_updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'precedent_feedback_stats'

# ... (다른 테이블들)
```

#### Step 4: 분석 결과 저장

```bash
# 분석 결과를 문서로 저장
cp inspected_models.py ../docs/INSPECTED_MODELS_REFERENCE.py

# 정리
cd ..
rm -rf temp_django_inspect
```

**이 파일을 Phase 2에서 Django 모델 작성 시 참고합니다.**

---

### Day 0.3: Fake Initial Migration 전략

**목적**: 기존 테이블을 Django가 관리하도록 설정 (테이블 재생성 방지)

#### 문제 상황

```bash
# Django 모델 작성 후 migrate 실행 시
python manage.py migrate

# ❌ 에러 발생
django.db.utils.ProgrammingError: table "users" already exists
```

#### 해결 방법: --fake-initial

**원리:**
1. Django가 migration 파일 생성 (테이블 생성 SQL 포함)
2. `--fake-initial`: SQL 실행하지 않고, migration 기록만 저장
3. 이후 스키마 변경부터 Django가 관리

**실행 순서:**
```bash
# Phase 2 Django 프로젝트에서

# 1. Django 모델 작성 (inspected_models.py 참고)
# apps/backend-api/users/models.py
# apps/backend-api/precedents/models.py
# ...

# 2. Migration 파일 생성
python manage.py makemigrations

# 출력 예시:
# Migrations for 'users':
#   users/migrations/0001_initial.py
#     - Create model User

# 3. Fake migration 실행
python manage.py migrate --fake-initial

# 출력:
# Operations to perform:
#   Apply all migrations: admin, auth, contenttypes, sessions, users, ...
# Running migrations:
#   Applying users.0001_initial... FAKED

# 4. 확인
python manage.py showmigrations

# 출력:
# users
#  [X] 0001_initial  # ← FAKED로 적용됨
```

**주의사항:**
- ⚠️ `managed = False` → `managed = True` 변경 필수
- ⚠️ 컬럼 타입, nullable, default 값 정확히 매핑
- ⚠️ Foreign Key는 `on_delete` 명시 필수

---

### Day 0.4: AI Service DB 모델 간소화

**문제**: AI Service와 Django Backend의 모델 중복 관리

**현재 계획 (문제 있음):**
```python
# apps/ai-service/models/precedent_feedback.py (SQLAlchemy)
class PrecedentFeedbackStats(Base):
    precedent_id = Column(String(200), primary_key=True)
    total_likes = Column(Integer, default=0)
    total_dislikes = Column(Integer, default=0)
    like_ratio = Column(Float, default=0.0)
    # ... 모든 컬럼 정의

# apps/backend-api/precedents/models.py (Django)
class PrecedentFeedbackStats(models.Model):
    precedent_id = models.CharField(primary_key=True, max_length=200)
    total_likes = models.IntegerField(default=0)
    total_dislikes = models.IntegerField(default=0)
    like_ratio = models.FloatField(default=0.0)
    # ... 동일한 컬럼 중복
```

**문제점:**
- Django에서 컬럼 추가/변경 시 AI Service도 수동 동기화 필요
- 휴먼 에러 가능성 (스키마 불일치)
- 유지보수 부담

#### 해결 방안 1: Raw SQL 사용 (권장)

```python
# apps/ai-service/services/feedback_adapter.py

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Set
import logging

logger = logging.getLogger(__name__)

class DatabaseFeedbackProvider:
    """
    Raw SQL 기반 피드백 제공자 (스키마 변경에 덜 민감)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_excluded_ids(self) -> Set[str]:
        """
        제외할 판례 ID 조회 (Raw SQL)

        장점:
        - Django 스키마 변경에 영향 받지 않음 (컬럼명만 일치하면 됨)
        - 모델 정의 불필요
        - 최소한의 의존성
        """
        try:
            result = await self.db.execute(text(
                "SELECT precedent_id FROM precedent_feedback_stats "
                "WHERE should_exclude = true"
            ))
            excluded_ids = {row[0] for row in result.fetchall()}

            if excluded_ids:
                logger.info(f"📊 Loaded {len(excluded_ids)} excluded precedents from DB")
            else:
                logger.debug("📊 No excluded precedents found in DB")

            return excluded_ids

        except Exception as e:
            logger.warning(f"⚠️  Failed to get excluded IDs from DB: {e}")
            logger.info("Continuing without feedback filtering")
            return set()

    async def get_feedback_stats(self, precedent_id: str) -> dict:
        """
        특정 판례의 피드백 통계 조회 (Raw SQL)
        """
        try:
            result = await self.db.execute(
                text(
                    "SELECT precedent_id, total_likes, total_dislikes, "
                    "total_feedback_count, like_ratio, avg_relevance_score, "
                    "should_exclude, exclusion_threshold, last_updated "
                    "FROM precedent_feedback_stats "
                    "WHERE precedent_id = :precedent_id"
                ),
                {"precedent_id": precedent_id}
            )
            row = result.fetchone()

            if row:
                return {
                    "precedent_id": row[0],
                    "total_likes": row[1],
                    "total_dislikes": row[2],
                    "total_feedback_count": row[3],
                    "like_ratio": row[4],
                    "avg_relevance_score": row[5],
                    "should_exclude": row[6],
                    "exclusion_threshold": row[7],
                    "last_updated": row[8].isoformat() if row[8] else None
                }
            else:
                return None

        except Exception as e:
            logger.warning(f"⚠️  Failed to get feedback stats for {precedent_id}: {e}")
            return None
```

**장점:**
- ✅ 스키마 변경에 덜 민감
- ✅ 모델 중복 제거
- ✅ 유지보수 간편

**단점:**
- ⚠️ 타입 안정성 낮음 (raw tuple)
- ⚠️ ORM 기능 사용 불가

#### 해결 방안 2: 최소 모델 유지

```python
# apps/ai-service/models/precedent_feedback.py

from sqlalchemy import Column, String, Boolean
from .database import Base

class PrecedentFeedbackStats(Base):
    """
    최소한의 컬럼만 정의 (필요한 것만)

    Django에서 추가한 새 컬럼은 무시됨 (에러 안 남)
    """
    __tablename__ = "precedent_feedback_stats"

    # 필수 컬럼만
    precedent_id = Column(String(200), primary_key=True)
    should_exclude = Column(Boolean, nullable=False, default=False)

    # 나머지 컬럼은 정의하지 않음
    # Django에서 추가해도 AI Service는 영향 없음
```

**장점:**
- ✅ ORM 기능 사용 가능
- ✅ 타입 안정성

**단점:**
- ⚠️ 여전히 모델 동기화 필요 (최소화)

---

### Phase 1.5 Git Commit

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# Raw SQL 버전으로 변경
git add apps/ai-service/services/feedback_adapter.py

# 기존 모델 제거
git rm apps/ai-service/models/precedent_feedback.py

# models/__init__.py 업데이트
git add apps/ai-service/models/__init__.py

git commit -m "refactor: simplify AI Service DB access with Raw SQL

- Remove PrecedentFeedbackStats SQLAlchemy model
- Use Raw SQL in DatabaseFeedbackProvider
- Reduce schema synchronization burden with Django
- Make AI Service less coupled to DB schema

Benefits:
- Django schema changes don't affect AI Service
- Simpler maintenance
- Clear separation: Django = master, AI Service = read-only client"

git push origin feature/ai-service-separation
```

---

### Phase 1.5 완료 체크리스트

```bash
# Phase 1.5 검증
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

echo "=== Phase 1.5 Checklist ==="
echo ""
echo "✅ DB 현황 파악"
echo "  [x] SQLite DB 확인: data/lawlaw.db"
echo "  [x] 테이블 목록 확인: users, precedents, precedent_feedback, precedent_feedback_stats"
echo "  [x] 스키마 분석 완료"
echo ""
echo "✅ Django 전환 준비"
echo "  [x] inspectdb 실행 완료"
echo "  [x] inspected_models.py 저장 (docs/INSPECTED_MODELS_REFERENCE.py)"
echo "  [x] Fake migration 전략 이해"
echo ""
echo "✅ AI Service 간소화"
echo "  [x] Raw SQL로 변경 (DatabaseFeedbackProvider)"
echo "  [x] SQLAlchemy 모델 제거 또는 최소화"
echo "  [x] 스키마 동기화 부담 감소"
echo ""
echo "✅ 다음 단계 준비"
echo "  [ ] Phase 2: Django 프로젝트 생성"
echo "  [ ] Django 모델 작성 (inspected_models.py 참고)"
echo "  [ ] --fake-initial migration 실행"
```

---

## 📦 Phase 2: Django 전환 (3주)

### 목표

- Django 기반 backend-api 구축
- SQLAlchemy → Django ORM 전환
- FastAPI auth → Django SimpleJWT
- apps/backend 제거
- PR #2 생성 및 머지

### 최종 결과 (Phase 2 완료 후)

```
apps/
├── backend-api/      ✅ Django (비즈니스 로직, API Gateway)
│   ├── manage.py
│   ├── backend_api/  (Django 프로젝트)
│   ├── users/        (Django 앱)
│   ├── cases/        (Django 앱)
│   └── api/v1/       (API 엔드포인트)
│       └── ai_proxy.py
│
├── ai-service/       ✅ FastAPI (AI 전용, Phase 1에서 완성)
├── web-frontend/     ✅ React
└── data-pipeline/    ✅ ETL

apps/backend/         🔴 삭제됨
```

---

### Week 3: Django 프로젝트 + User 모델

#### Day 11-12: Django 프로젝트 생성

**Step 1: Git 브랜치 생성**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# develop 브랜치 최신화
git checkout develop
git pull origin develop

# 새 feature 브랜치 생성
git checkout -b feature/django-backend

# 백업 (선택)
cd /Users/myidwon/dev
tar -czf ai-camp-backup-django-$(date +%Y%m%d).tar.gz ai-camp-1st-llm-agent-service-project-2/
```

**Step 2: Django 설치 및 프로젝트 생성**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/apps

# Django 프로젝트 생성
django-admin startproject backend_api

# 디렉토리 이름 변경
mv backend_api backend-api

cd backend-api

# Django 앱 생성
python manage.py startapp users
python manage.py startapp cases
python manage.py startapp precedents
python manage.py startapp documents
python manage.py startapp api

# 추가 디렉토리
mkdir -p api/v1
mkdir -p core
mkdir -p integrations

# 확인
ls -la
# manage.py, backend_api/, users/, cases/, ... 확인
```

**Step 3: requirements.txt**

```txt
# apps/backend-api/requirements.txt
Django>=4.2.7
djangorestframework>=3.14.0
djangorestframework-simplejwt>=5.3.0
django-cors-headers>=4.3.0
psycopg2-binary>=2.9.9
httpx>=0.25.2
python-dotenv>=1.0.0
```

**Step 4: settings.py 기본 설정**

```python
# apps/backend-api/backend_api/settings.py (전체 수정)

import os
from pathlib import Path
from datetime import timedelta

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    # Local apps
    'users',
    'cases',
    'precedents',
    'documents',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS (must be before CommonMiddleware)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend_api.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'lawlaw'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# SimpleJWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React Frontend
]
CORS_ALLOW_CREDENTIALS = True

# AI Service
AI_SERVICE_URL = os.getenv('AI_SERVICE_URL', 'http://localhost:8001')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

**Step 5: Git commit**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

git add apps/backend-api/

git commit -m "feat: create Django project structure

- Create Django project 'backend_api'
- Create Django apps: users, cases, precedents, documents, api
- Add settings.py with PostgreSQL, JWT, CORS configuration
- Add requirements.txt for Django dependencies

Project structure:
- Django 4.2+
- DRF (Django REST Framework)
- SimpleJWT for authentication
- PostgreSQL database
- CORS for React frontend"

git push -u origin feature/django-backend
```

---

#### Day 13-14: User 모델 마이그레이션

**Step 1: users/models.py**

```python
# apps/backend-api/users/models.py
"""
User Model
Django ORM 기반 사용자 모델 (FastAPI User 모델 대체)
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    """
    커스텀 사용자 모델

    기존 apps.backend.models.user.User (SQLAlchemy)를
    Django ORM으로 마이그레이션

    주요 변경사항:
    - SQLAlchemy → Django ORM
    - UUID primary key 유지
    - email 기반 인증 (username 비활성화)
    """

    # Primary Key (UUID)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Email (unique, 로그인에 사용)
    email = models.EmailField(
        unique=True,
        db_index=True,
        verbose_name='이메일'
    )

    # Profile
    full_name = models.CharField(
        max_length=255,
        verbose_name='이름'
    )

    lawyer_registration_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='변호사 등록번호'
    )

    specializations = models.JSONField(
        default=list,
        blank=True,
        verbose_name='전문 분야'
    )

    # AbstractUser 필드 재정의
    username = None  # email 사용하므로 username 비활성화
    first_name = None  # full_name 사용
    last_name = None  # full_name 사용

    # 로그인에 사용할 필드
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']  # createsuperuser 시 요구되는 필드

    class Meta:
        db_table = 'users'
        verbose_name = '사용자'
        verbose_name_plural = '사용자'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.full_name} ({self.email})"
```

**Step 2: users/serializers.py**

```python
# apps/backend-api/users/serializers.py
"""
User Serializers
Django REST Framework Serializers
"""

from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """사용자 정보 Serializer (읽기)"""

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'full_name',
            'lawyer_registration_number',
            'specializations',
            'is_active',
            'is_staff',
            'date_joined',
            'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

class UserCreateSerializer(serializers.ModelSerializer):
    """사용자 생성 Serializer"""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'email',
            'password',
            'password_confirm',
            'full_name',
            'lawyer_registration_number',
            'specializations'
        ]

    def validate(self, data):
        """비밀번호 확인 검증"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                "password_confirm": "비밀번호가 일치하지 않습니다."
            })
        return data

    def create(self, validated_data):
        """사용자 생성"""
        # password_confirm 제거
        validated_data.pop('password_confirm')

        # 사용자 생성 (비밀번호 해시 자동 처리)
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            lawyer_registration_number=validated_data.get('lawyer_registration_number'),
            specializations=validated_data.get('specializations', [])
        )
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    """사용자 수정 Serializer"""

    class Meta:
        model = User
        fields = [
            'full_name',
            'lawyer_registration_number',
            'specializations'
        ]

class ChangePasswordSerializer(serializers.Serializer):
    """비밀번호 변경 Serializer"""

    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        min_length=8,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, data):
        """새 비밀번호 확인 검증"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password_confirm": "새 비밀번호가 일치하지 않습니다."
            })
        return data
```

**Step 3: api/v1/auth.py**

```python
# apps/backend-api/api/v1/auth.py
"""
Authentication API
JWT 기반 인증 엔드포인트
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from users.models import User
from users.serializers import (
    UserSerializer,
    UserCreateSerializer,
    ChangePasswordSerializer
)

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """
    회원가입

    POST /api/v1/auth/signup
    {
        "email": "user@example.com",
        "password": "password123",
        "password_confirm": "password123",
        "full_name": "홍길동",
        "specializations": ["형사일반"]
    }
    """
    serializer = UserCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    return Response(
        {
            "message": "회원가입이 완료되었습니다.",
            "user": UserSerializer(user).data
        },
        status=status.HTTP_201_CREATED
    )

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    로그인 (JWT 토큰 발급)

    POST /api/v1/auth/login
    {
        "email": "user@example.com",
        "password": "password123"
    }

    Response:
    {
        "access": "...",
        "refresh": "...",
        "user": {...}
    }
    """
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {"error": "이메일과 비밀번호를 입력해주세요."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 사용자 인증
    user = authenticate(request, username=email, password=password)

    if user is None:
        return Response(
            {"error": "이메일 또는 비밀번호가 올바르지 않습니다."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {"error": "비활성화된 계정입니다."},
            status=status.HTTP_403_FORBIDDEN
        )

    # JWT 토큰 생성
    refresh = RefreshToken.for_user(user)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    로그아웃 (Refresh 토큰 블랙리스트)

    POST /api/v1/auth/logout
    {
        "refresh": "..."
    }
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response(
            {"message": "로그아웃 되었습니다."},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    현재 사용자 정보

    GET /api/v1/auth/me
    """
    return Response(UserSerializer(request.user).data)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    프로필 수정

    PUT/PATCH /api/v1/auth/profile
    """
    from users.serializers import UserUpdateSerializer

    serializer = UserUpdateSerializer(
        request.user,
        data=request.data,
        partial=request.method == 'PATCH'
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(UserSerializer(request.user).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    비밀번호 변경

    POST /api/v1/auth/change-password
    """
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = request.user

    # 기존 비밀번호 확인
    if not user.check_password(serializer.validated_data['old_password']):
        return Response(
            {"error": "기존 비밀번호가 올바르지 않습니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 새 비밀번호 설정
    user.set_password(serializer.validated_data['new_password'])
    user.save()

    return Response({"message": "비밀번호가 변경되었습니다."})
```

**Step 4: urls.py 설정**

```python
# apps/backend-api/api/v1/urls.py
"""
API v1 URL Configuration
"""

from django.urls import path
from . import auth

urlpatterns = [
    # Authentication
    path('auth/signup', auth.signup, name='signup'),
    path('auth/login', auth.login, name='login'),
    path('auth/logout', auth.logout, name='logout'),
    path('auth/me', auth.me, name='me'),
    path('auth/profile', auth.update_profile, name='update_profile'),
    path('auth/change-password', auth.change_password, name='change_password'),
]
```

```python
# apps/backend-api/backend_api/urls.py (수정)
"""
Backend API URL Configuration
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.v1.urls')),
]
```

**Step 5: Admin 등록**

```python
# apps/backend-api/users/admin.py
"""
User Admin
Django Admin 설정
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """사용자 Admin"""

    list_display = ['email', 'full_name', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['email', 'full_name', 'lawyer_registration_number']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('개인정보', {
            'fields': ('full_name', 'lawyer_registration_number', 'specializations')
        }),
        ('권한', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('중요한 날짜', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2'),
        }),
    )
```

**Step 6: Migrations 생성 및 실행**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/apps/backend-api

# Migrations 생성
python manage.py makemigrations users

# 확인
python manage.py showmigrations

# DB 적용
python manage.py migrate

# Superuser 생성
python manage.py createsuperuser
# Email: admin@example.com
# Full name: 관리자
# Password: (입력)

# 서버 실행 테스트
python manage.py runserver 0.0.0.0:8000
```

**Step 7: 테스트**

```bash
# Terminal 1: Django 서버
cd apps/backend-api
python manage.py runserver

# Terminal 2: API 테스트

# 1. 회원가입
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "password_confirm": "testpass123",
    "full_name": "테스트 사용자",
    "specializations": ["형사일반"]
  }'

# 2. 로그인
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }' | jq -r '.access')

echo "Token: $TOKEN"

# 3. 내 정보 조회
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# 4. Django Admin 접속
# http://localhost:8000/admin
```

**Step 8: Git commit**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

git add apps/backend-api/users/
git add apps/backend-api/api/v1/
git add apps/backend-api/backend_api/urls.py

git commit -m "feat: add User model and authentication APIs

- Add users/models.py with Django User model (UUID primary key)
- Add users/serializers.py for DRF serialization
- Add users/admin.py for Django Admin
- Add api/v1/auth.py with JWT authentication endpoints
- Configure URL routing for auth APIs

APIs:
- POST /api/v1/auth/signup: User registration
- POST /api/v1/auth/login: JWT login
- POST /api/v1/auth/logout: Logout (blacklist refresh token)
- GET /api/v1/auth/me: Get current user
- PUT /api/v1/auth/profile: Update profile
- POST /api/v1/auth/change-password: Change password

Migration: SQLAlchemy User → Django ORM User
Authentication: FastAPI JWT → Django SimpleJWT"

git push origin feature/django-backend
```

---

### Week 4: Case, Precedent 모델 마이그레이션

#### Day 15-16: Precedent 모델

**Step 1: precedents/models.py**

```python
# apps/backend-api/precedents/models.py
"""
Precedent Models
판례 모델 (SQLAlchemy → Django ORM 마이그레이션)
"""

from django.db import models
import uuid

class Precedent(models.Model):
    """
    대법원 판례 모델

    기존 apps.backend.models.precedent.Precedent (SQLAlchemy)를
    Django ORM으로 마이그레이션
    """

    # Primary Key (UUID)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Case Information
    case_number = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name='사건번호'
    )

    title = models.CharField(
        max_length=500,
        verbose_name='판례 제목'
    )

    summary = models.TextField(
        blank=True,
        null=True,
        verbose_name='판례 요약'
    )

    full_text = models.TextField(
        blank=True,
        null=True,
        verbose_name='판례 전문'
    )

    # Additional Details from Supreme Court Portal
    judgment_summary = models.TextField(
        blank=True,
        null=True,
        verbose_name='판시사항'
    )

    reference_statutes = models.JSONField(
        default=list,
        blank=True,
        verbose_name='참조조문'
    )

    reference_precedents = models.JSONField(
        default=list,
        blank=True,
        verbose_name='참조판례'
    )

    precedent_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='대법원 포털 판례 ID'
    )

    # Court and Date
    court = models.CharField(
        max_length=100,
        default='대법원',
        verbose_name='법원명'
    )

    decision_date = models.DateTimeField(
        db_index=True,
        verbose_name='선고일자'
    )

    # Classification
    case_type = models.CharField(
        max_length=50,
        default='형사',
        verbose_name='사건종류'
    )

    specialization_tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='전문분야 태그'
    )

    # References
    citation = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='판례 인용 정보'
    )

    case_link = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='원본 링크'
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'precedents'
        verbose_name = '판례'
        verbose_name_plural = '판례'
        ordering = ['-decision_date']
        indexes = [
            models.Index(fields=['-decision_date'], name='idx_decision_date_desc'),
            models.Index(fields=['case_type', '-decision_date'], name='idx_case_type_date'),
        ]

    def __str__(self):
        return f"{self.case_number} - {self.title[:30]}"


class PrecedentFeedback(models.Model):
    """
    판례 피드백 모델

    사용자가 RAG 검색 결과로 받은 판례에 대한 피드백
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='precedent_feedbacks',
        verbose_name='사용자'
    )

    precedent_id = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name='판례 ID'
    )

    query = models.TextField(
        verbose_name='사용자 질의'
    )

    feedback_type = models.CharField(
        max_length=20,
        choices=[
            ('like', '좋아요'),
            ('dislike', '싫어요'),
        ],
        verbose_name='피드백 유형'
    )

    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name='추가 의견'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'precedent_feedback'
        verbose_name = '판례 피드백'
        verbose_name_plural = '판례 피드백'
        ordering = ['-created_at']
        unique_together = [['user', 'precedent_id', 'feedback_type']]

    def __str__(self):
        return f"{self.user.email} - {self.precedent_id} ({self.feedback_type})"


class PrecedentFeedbackStats(models.Model):
    """
    판례 피드백 통계

    집계된 피드백 통계 (AI Service에서 읽기 전용으로 사용)
    """

    precedent_id = models.CharField(
        max_length=255,
        primary_key=True,
        verbose_name='판례 ID'
    )

    like_count = models.IntegerField(
        default=0,
        verbose_name='좋아요 수'
    )

    dislike_count = models.IntegerField(
        default=0,
        verbose_name='싫어요 수'
    )

    total_count = models.IntegerField(
        default=0,
        verbose_name='총 피드백 수'
    )

    like_ratio = models.IntegerField(
        default=0,
        verbose_name='좋아요 비율 (%)'
    )

    should_exclude = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='검색 결과 제외 여부'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'precedent_feedback_stats'
        verbose_name = '판례 피드백 통계'
        verbose_name_plural = '판례 피드백 통계'

    def __str__(self):
        return f"{self.precedent_id} (👍 {self.like_count} / 👎 {self.dislike_count})"

    def update_stats(self):
        """피드백 통계 업데이트"""
        feedbacks = PrecedentFeedback.objects.filter(precedent_id=self.precedent_id)

        self.like_count = feedbacks.filter(feedback_type='like').count()
        self.dislike_count = feedbacks.filter(feedback_type='dislike').count()
        self.total_count = feedbacks.count()

        if self.total_count > 0:
            self.like_ratio = int((self.like_count / self.total_count) * 100)
        else:
            self.like_ratio = 0

        # 제외 기준: 총 피드백 5개 이상 + 좋아요 비율 30% 미만
        self.should_exclude = (
            self.total_count >= 5 and self.like_ratio < 30
        )

        self.save()
```

**Step 2: precedents/serializers.py**

```python
# apps/backend-api/precedents/serializers.py
"""
Precedent Serializers
"""

from rest_framework import serializers
from .models import Precedent, PrecedentFeedback, PrecedentFeedbackStats

class PrecedentSerializer(serializers.ModelSerializer):
    """판례 Serializer"""

    class Meta:
        model = Precedent
        fields = [
            'id',
            'case_number',
            'title',
            'summary',
            'full_text',
            'judgment_summary',
            'reference_statutes',
            'reference_precedents',
            'precedent_id',
            'court',
            'decision_date',
            'case_type',
            'specialization_tags',
            'citation',
            'case_link',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class PrecedentListSerializer(serializers.ModelSerializer):
    """판례 목록 Serializer (간략)"""

    class Meta:
        model = Precedent
        fields = [
            'id',
            'case_number',
            'title',
            'summary',
            'court',
            'decision_date',
            'case_type',
            'specialization_tags'
        ]

class PrecedentFeedbackSerializer(serializers.ModelSerializer):
    """판례 피드백 Serializer"""

    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = PrecedentFeedback
        fields = [
            'id',
            'user',
            'user_email',
            'precedent_id',
            'query',
            'feedback_type',
            'comment',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']

class PrecedentFeedbackCreateSerializer(serializers.ModelSerializer):
    """판례 피드백 생성 Serializer"""

    class Meta:
        model = PrecedentFeedback
        fields = [
            'precedent_id',
            'query',
            'feedback_type',
            'comment'
        ]

class PrecedentFeedbackStatsSerializer(serializers.ModelSerializer):
    """판례 피드백 통계 Serializer"""

    class Meta:
        model = PrecedentFeedbackStats
        fields = [
            'precedent_id',
            'like_count',
            'dislike_count',
            'total_count',
            'like_ratio',
            'should_exclude',
            'created_at',
            'updated_at'
        ]
```

**Step 3: precedents/admin.py**

```python
# apps/backend-api/precedents/admin.py
"""
Precedent Admin
"""

from django.contrib import admin
from .models import Precedent, PrecedentFeedback, PrecedentFeedbackStats

@admin.register(Precedent)
class PrecedentAdmin(admin.ModelAdmin):
    """판례 Admin"""

    list_display = [
        'case_number',
        'title_short',
        'court',
        'decision_date',
        'case_type',
        'created_at'
    ]
    list_filter = ['case_type', 'court', 'decision_date']
    search_fields = ['case_number', 'title', 'summary']
    date_hierarchy = 'decision_date'
    ordering = ['-decision_date']

    fieldsets = (
        ('기본 정보', {
            'fields': ('case_number', 'title', 'court', 'decision_date', 'case_type')
        }),
        ('판례 내용', {
            'fields': ('summary', 'full_text', 'judgment_summary')
        }),
        ('참조', {
            'fields': ('reference_statutes', 'reference_precedents', 'citation', 'case_link')
        }),
        ('분류', {
            'fields': ('specialization_tags', 'precedent_id')
        }),
    )

    def title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_short.short_description = '제목'

@admin.register(PrecedentFeedback)
class PrecedentFeedbackAdmin(admin.ModelAdmin):
    """판례 피드백 Admin"""

    list_display = ['user', 'precedent_id', 'feedback_type', 'created_at']
    list_filter = ['feedback_type', 'created_at']
    search_fields = ['user__email', 'precedent_id', 'query']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

@admin.register(PrecedentFeedbackStats)
class PrecedentFeedbackStatsAdmin(admin.ModelAdmin):
    """판례 피드백 통계 Admin"""

    list_display = [
        'precedent_id',
        'like_count',
        'dislike_count',
        'total_count',
        'like_ratio',
        'should_exclude',
        'updated_at'
    ]
    list_filter = ['should_exclude']
    search_fields = ['precedent_id']
    ordering = ['-updated_at']
    readonly_fields = ['created_at', 'updated_at']
```

**Step 4: Migrations 및 테스트**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/apps/backend-api

# Migrations 생성
python manage.py makemigrations precedents

# 확인
python manage.py showmigrations

# DB 적용
python manage.py migrate

# Django shell 테스트
python manage.py shell
```

```python
# Django shell에서
from precedents.models import Precedent
from datetime import datetime

# 테스트 판례 생성
precedent = Precedent.objects.create(
    case_number='2023도1234',
    title='음주운전 판례',
    summary='음주운전에 관한 판례입니다.',
    decision_date=datetime.now(),
    case_type='형사',
    specialization_tags=['교통사고', '음주운전']
)

print(f"Created: {precedent}")

# 조회
Precedent.objects.all()
```

**Step 5: Git commit**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

git add apps/backend-api/precedents/

git commit -m "feat: add Precedent models and admin

- Add precedents/models.py (Precedent, PrecedentFeedback, PrecedentFeedbackStats)
- Add precedents/serializers.py for DRF
- Add precedents/admin.py for Django Admin
- Add migrations for precedent tables

Models migrated from SQLAlchemy to Django ORM:
- Precedent: 388K+ Supreme Court precedents
- PrecedentFeedback: User feedback on precedents
- PrecedentFeedbackStats: Aggregated feedback statistics (read by AI Service)"

git push origin feature/django-backend
```

---

#### Day 17-18: Case 모델 및 AI Service 프록시

**Step 1: cases/models.py**

```python
# apps/backend-api/cases/models.py
"""
Case Models
사건 모델
"""

from django.db import models
import uuid

class Case(models.Model):
    """사건 모델"""

    STATUS_CHOICES = [
        ('draft', '작성중'),
        ('analyzing', '분석중'),
        ('analyzed', '분석완료'),
        ('completed', '완료'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='cases',
        verbose_name='사용자'
    )

    title = models.CharField(
        max_length=255,
        verbose_name='사건명'
    )

    content = models.TextField(
        verbose_name='사건 내용'
    )

    analysis = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='AI 분석 결과'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='상태'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'cases'
        verbose_name = '사건'
        verbose_name_plural = '사건'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.user.email})"


class ChatHistory(models.Model):
    """채팅 히스토리"""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='chat_histories',
        verbose_name='사용자'
    )

    case = models.ForeignKey(
        Case,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_histories',
        verbose_name='관련 사건'
    )

    query = models.TextField(
        verbose_name='사용자 질문'
    )

    answer = models.TextField(
        verbose_name='AI 답변'
    )

    sources = models.JSONField(
        default=list,
        blank=True,
        verbose_name='출처 판례'
    )

    model = models.CharField(
        max_length=100,
        default='',
        verbose_name='사용 모델'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'chat_history'
        verbose_name = '채팅 히스토리'
        verbose_name_plural = '채팅 히스토리'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.query[:30]}"
```

**Step 2: api/v1/ai_proxy.py (AI Service 프록시)**

```python
# apps/backend-api/api/v1/ai_proxy.py
"""
AI Service Proxy
Django → AI Service HTTP 통신
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import httpx
import os
import logging

from cases.models import ChatHistory

logger = logging.getLogger(__name__)

AI_SERVICE_URL = os.getenv('AI_SERVICE_URL', 'http://localhost:8001')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rag_chat(request):
    """
    RAG 챗봇 (AI Service 프록시)

    POST /api/v1/ai/chat/rag
    {
        "query": "음주운전 처벌 기준은?",
        "top_k": 5,
        "include_sources": true,
        "enable_critique": true
    }

    Flow:
    1. Django: JWT 검증 (IsAuthenticated)
    2. AI Service 호출 (내부 HTTP)
    3. Django: ChatHistory 저장
    4. 응답 반환
    """
    try:
        user = request.user
        query = request.data.get('query')

        if not query:
            return Response(
                {"error": "query is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"📨 RAG request from {user.email}: {query[:50]}...")

        # AI Service 호출
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/v1/chat/rag",
                json=request.data,
                headers={"X-User-ID": str(user.id)}
            )
            response.raise_for_status()
            ai_result = response.json()

        # ChatHistory 저장
        ChatHistory.objects.create(
            user=user,
            query=query,
            answer=ai_result.get('answer', ''),
            sources=ai_result.get('sources', []),
            model=ai_result.get('model', '')
        )

        logger.info(f"✅ RAG response sent to {user.email}")
        return Response(ai_result)

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ RAG chat error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_case(request):
    """
    사건 분석 (AI Service 프록시)

    POST /api/v1/ai/analyze/case
    {
        "text": "사건 내용...",
        "include_related_cases": true
    }
    """
    try:
        user = request.user
        text = request.data.get('text')

        if not text:
            return Response(
                {"error": "text is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"📨 Case analysis request from {user.email}")

        # AI Service 호출
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/v1/analyze/case",
                json=request.data,
                headers={"X-User-ID": str(user.id)}
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"✅ Case analysis response sent to {user.email}")
        return Response(result)

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ Case analysis error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_document(request):
    """
    문서 생성 (AI Service 프록시)

    POST /api/v1/ai/generate/document
    {
        "case_info": {...},
        "document_type": "complaint"
    }
    """
    try:
        user = request.user

        logger.info(f"📨 Document generation request from {user.email}")

        # AI Service 호출
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/v1/analyze/generate",
                json=request.data,
                headers={"X-User-ID": str(user.id)}
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"✅ Document generation response sent to {user.email}")
        return Response(result)

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ Document generation error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
async def health_check(request):
    """AI Service 헬스체크"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{AI_SERVICE_URL}/health")
            response.raise_for_status()
            return Response({
                "status": "healthy",
                "ai_service": response.json()
            })
    except:
        return Response({
            "status": "degraded",
            "ai_service": "unavailable"
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
```

**Step 3: api/v1/urls.py 업데이트**

```python
# apps/backend-api/api/v1/urls.py (수정)
from django.urls import path
from . import auth, ai_proxy

urlpatterns = [
    # Authentication
    path('auth/signup', auth.signup, name='signup'),
    path('auth/login', auth.login, name='login'),
    path('auth/logout', auth.logout, name='logout'),
    path('auth/me', auth.me, name='me'),
    path('auth/profile', auth.update_profile, name='update_profile'),
    path('auth/change-password', auth.change_password, name='change_password'),

    # AI Service Proxy
    path('ai/chat/rag', ai_proxy.rag_chat, name='ai_rag_chat'),
    path('ai/analyze/case', ai_proxy.analyze_case, name='ai_analyze_case'),
    path('ai/generate/document', ai_proxy.generate_document, name='ai_generate_document'),
    path('ai/health', ai_proxy.health_check, name='ai_health'),
]
```

**Step 4: settings.py에 async 지원 추가**

```python
# apps/backend-api/backend_api/settings.py (추가)

# ASGI 설정 (async view 지원)
ASGI_APPLICATION = 'backend_api.asgi.application'
```

**Step 5: asgi.py 수정**

```python
# apps/backend-api/backend_api/asgi.py
"""
ASGI config for backend_api project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_api.settings')

application = get_asgi_application()
```

**Step 6: Migrations 및 Git commit**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/apps/backend-api

# Migrations
python manage.py makemigrations cases
python manage.py migrate

# Git commit
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

git add apps/backend-api/cases/
git add apps/backend-api/api/v1/ai_proxy.py
git add apps/backend-api/api/v1/urls.py
git add apps/backend-api/backend_api/asgi.py
git add apps/backend-api/backend_api/settings.py

git commit -m "feat: add Case models and AI Service proxy

- Add cases/models.py (Case, ChatHistory)
- Add api/v1/ai_proxy.py for AI Service communication
- Add async view support (ASGI)
- Add AI proxy endpoints:
  - POST /api/v1/ai/chat/rag
  - POST /api/v1/ai/analyze/case
  - POST /api/v1/ai/generate/document
  - GET /api/v1/ai/health

Django now acts as API Gateway:
- JWT authentication
- AI Service proxy
- ChatHistory persistence"

git push origin feature/django-backend
```

---

### Week 5: apps/backend 제거 및 최종 검증

#### Day 19-20: 통합 테스트

**Step 1: 3-tier 통합 테스트 스크립트**

```bash
# scripts/test_django_integration.sh
cat > /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/scripts/test_django_integration.sh << 'EOF'
#!/bin/bash

set -e

echo "==========================================="
echo "Django Integration Test"
echo "==========================================="

# 1. AI Service 헬스체크
echo ""
echo "[1/5] Testing AI Service..."
AI_STATUS=$(curl -s http://localhost:8001/health | jq -r '.status')
echo "AI Service: $AI_STATUS"

if [ "$AI_STATUS" != "healthy" ]; then
    echo "❌ AI Service is not healthy!"
    exit 1
fi

# 2. Django 헬스체크
echo ""
echo "[2/5] Testing Django Backend..."
curl -s http://localhost:8000/api/v1/ai/health | jq .

# 3. 회원가입
echo ""
echo "[3/5] Testing User Signup..."
curl -s -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-django@example.com",
    "password": "testpass123",
    "password_confirm": "testpass123",
    "full_name": "Django 테스트",
    "specializations": ["형사일반"]
  }' | jq '.message'

# 4. 로그인 및 토큰 획득
echo ""
echo "[4/5] Testing Login & JWT..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-django@example.com",
    "password": "testpass123"
  }' | jq -r '.access')

echo "Token: ${TOKEN:0:50}..."

# 5. RAG 챗봇 테스트 (Django → AI Service)
echo ""
echo "[5/5] Testing RAG Chat (Django → AI Service)..."
ANSWER=$(curl -s -X POST http://localhost:8000/api/v1/ai/chat/rag \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "음주운전 처벌 기준",
    "top_k": 2,
    "include_sources": false
  }' | jq -r '.answer')

echo "Answer: ${ANSWER:0:100}..."

echo ""
echo "==========================================="
echo "✅ All Django integration tests passed!"
echo "==========================================="
EOF

chmod +x scripts/test_django_integration.sh
```

**Step 2: 동시 실행 스크립트 (Django 버전)**

```bash
# scripts/run_django_dev.sh
cat > scripts/run_django_dev.sh << 'EOF'
#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==========================================="
echo "LawLaw Development (Django)"
echo "==========================================="

# PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# .env 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Logs 디렉토리
mkdir -p logs

# AI Service 실행
echo ""
echo "[1/3] Starting AI Service (port 8001)..."
cd apps/ai-service
python main.py > ../../logs/ai-service.log 2>&1 &
AI_PID=$!
echo "✅ AI Service started (PID: $AI_PID)"

sleep 5

# Django Backend 실행
echo ""
echo "[2/3] Starting Django Backend (port 8000)..."
cd "$PROJECT_ROOT/apps/backend-api"
python manage.py runserver 0.0.0.0:8000 > ../../logs/django.log 2>&1 &
DJANGO_PID=$!
echo "✅ Django Backend started (PID: $DJANGO_PID)"

sleep 5

# Frontend 실행
echo ""
echo "[3/3] Starting Frontend (port 3000)..."
cd "$PROJECT_ROOT/apps/web-frontend"
npm start

# Cleanup
trap "kill $AI_PID $DJANGO_PID" EXIT
EOF

chmod +x scripts/run_django_dev.sh
```

**Step 3: 실제 통합 테스트**

```bash
# Terminal 1: AI Service
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
export PYTHONPATH=$(pwd):$PYTHONPATH
export $(cat .env | grep -v '^#' | xargs)
cd apps/ai-service
python main.py

# Terminal 2: Django Backend
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
export PYTHONPATH=$(pwd):$PYTHONPATH
export $(cat .env | grep -v '^#' | xargs)
cd apps/backend-api
python manage.py runserver

# Terminal 3: 통합 테스트
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
./scripts/test_django_integration.sh
```

**Step 4: Frontend .env 업데이트**

```bash
# apps/web-frontend/.env (확인 및 수정)
cat > /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/apps/web-frontend/.env << 'EOF'
REACT_APP_API_URL=http://localhost:8000
REACT_APP_NAME=LawLaw
REACT_APP_VERSION=2.0.0
EOF
```

**Step 5: Git commit**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

git add scripts/test_django_integration.sh
git add scripts/run_django_dev.sh
git add apps/web-frontend/.env

git commit -m "test: add Django integration test scripts

- Add scripts/test_django_integration.sh
- Add scripts/run_django_dev.sh for 3-tier startup
- Update web-frontend .env for Django backend

Test flow:
1. AI Service health check
2. Django health check
3. User signup/login
4. RAG chat (Django → AI Service)
5. ChatHistory persistence"

git push origin feature/django-backend
```

---

#### Day 21: apps/backend 제거

**⚠️ 중요: 제거 전 최종 확인**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

echo "=== Final Checklist Before Removing apps/backend ==="
echo ""
echo "✅ Checklist:"
echo "[ ] Django Backend running on port 8000"
echo "[ ] AI Service running on port 8001"
echo "[ ] Frontend connected to Django (not FastAPI)"
echo "[ ] User signup/login working"
echo "[ ] RAG chat working (Django → AI Service → Response)"
echo "[ ] ChatHistory being saved in Django DB"
echo "[ ] Precedent models migrated"
echo "[ ] All tests passing"
echo ""
read -p "All checks passed? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "❌ Aborted. Fix issues first."
    exit 1
fi
```

**Step 1: apps/backend 백업**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 백업 디렉토리 생성
mkdir -p backups

# tar로 백업
tar -czf backups/apps-backend-$(date +%Y%m%d_%H%M%S).tar.gz apps/backend/

# 확인
ls -lh backups/

echo "✅ Backup created: backups/apps-backend-*.tar.gz"
```

**Step 2: apps/backend 제거**

```bash
# apps/backend 디렉토리 제거
rm -rf apps/backend/

# 확인
ls -la apps/

# apps/ai-service, apps/backend-api, apps/web-frontend, apps/data-pipeline만 남아있어야 함
```

**Step 3: root requirements.txt 업데이트**

```bash
# root requirements.txt에서 FastAPI 관련 제거 (선택)
# Django와 AI Service 각각 requirements.txt 있으므로
# root는 공통 의존성만 유지

cat > requirements.txt << 'EOF'
# Common dependencies for monorepo
# Individual apps have their own requirements.txt

# libs/rag_core dependencies
sentence-transformers>=2.2.2
chromadb>=0.4.18
faiss-cpu>=1.7.4
rank-bm25>=0.2.2
openai>=1.3.0
anthropic>=0.7.0
tiktoken>=0.5.1

# Common utilities
python-dotenv>=1.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
EOF
```

**Step 4: README.md 업데이트**

```bash
# README.md 수정 (Django 기준으로)
cat > README.md << 'EOF'
# LawLaw - 형사법 전문 AI 어시스턴트

> 법률 전문가를 위한 AI 기반 법률 서비스 플랫폼 (Django + FastAPI AI Service)

## 🏗️ 프로젝트 구조 (Monorepo)

```
lawlaw/
├── apps/
│   ├── backend-api/      # Django (비즈니스 로직, API Gateway, 포트 8000)
│   ├── ai-service/       # FastAPI (AI 전용 엔진, 포트 8001)
│   ├── web-frontend/     # React (포트 3000)
│   └── data-pipeline/    # ETL 파이프라인
│
├── libs/
│   ├── rag_core/         # RAG 핵심 로직 (공유 라이브러리)
│   └── domain_model/     # 공통 Pydantic 모델
│
├── data/                 # VectorDB, 업로드 (Git 제외)
├── configs/              # 설정 파일
└── docs/                 # 문서
```

## 🚀 빠른 시작

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### 1. 환경 설정

```bash
# Repository 클론
git clone https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2.git
cd ai-camp-1st-llm-agent-service-project-2

# 환경변수 설정
cp .env.example .env
# .env 파일 편집 (LLM API 키, DB 설정 등)
```

### 2. AI Service 실행

```bash
cd apps/ai-service

# Python 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# PYTHONPATH 설정
export PYTHONPATH=$(pwd)/../..:$PYTHONPATH

# 실행
python main.py
```

AI Service: http://localhost:8001

### 3. Django Backend 실행

```bash
cd apps/backend-api

# 의존성 설치
pip install -r requirements.txt

# Migrations
python manage.py migrate

# Superuser 생성 (선택)
python manage.py createsuperuser

# 실행
python manage.py runserver
```

Django Backend: http://localhost:8000
Django Admin: http://localhost:8000/admin

### 4. Frontend 실행

```bash
cd apps/web-frontend

# 의존성 설치
npm install

# 실행
npm start
```

Frontend: http://localhost:3000

## 📚 주요 기능

- ✅ **RAG 기반 챗봇**: 형사법 판례 기반 질의응답
- ✅ **사건 분석**: 사건 문서 자동 분석 및 관련 판례 검색
- ✅ **문서 생성**: AI 기반 법률 문서 자동 생성
- ✅ **판례 검색**: 388K+ 형사법 판례 하이브리드 검색 (Semantic + BM25)
- ✅ **Constitutional AI**: 헌법적 원칙 기반 AI 응답
- ✅ **피드백 시스템**: 사용자 피드백 기반 판례 필터링

## 🏗️ 아키텍처

```
Frontend (React, 3000)
    ↓
Django Backend (API Gateway, 8000)
    ├─→ Django ORM (User, Case, Precedent 관리)
    └─→ AI Service (FastAPI, 8001)
            ↓
            ├─→ libs/rag_core (RAG 로직)
            ├─→ VectorDB (ChromaDB, FAISS, BM25)
            └─→ LLM (GPT-4 / Custom)
```

## 🧪 테스트

```bash
# Django 통합 테스트
./scripts/test_django_integration.sh

# 전체 서비스 실행 (개발 모드)
./scripts/run_django_dev.sh
```

## 📖 문서

- [Django 마이그레이션 가이드](docs/DJANGO_MIGRATION_PLAN.md)
- [API 문서](http://localhost:8000/api/v1/) (Django 실행 후)
- [AI Service API](http://localhost:8001/docs) (AI Service 실행 후)

## 🤝 기여

1. Feature 브랜치 생성: `git checkout -b feature/amazing-feature`
2. 변경사항 커밋: `git commit -m 'feat: add amazing feature'`
3. Push: `git push origin feature/amazing-feature`
4. Pull Request 생성

## 📝 라이선스

MIT License

## 👥 팀

Team 2 - KernelAcademy AI Camp 1st
EOF
```

**Step 5: Git commit (apps/backend 제거)**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

git add -A
git status

# apps/backend 제거 확인
git commit -m "refactor: remove apps/backend (replaced by Django)

BREAKING CHANGE: apps/backend (FastAPI) has been removed

Replaced by:
- apps/backend-api (Django): Business logic, API Gateway
- apps/ai-service (FastAPI): AI engine only

Migration completed:
- ✅ User authentication → Django SimpleJWT
- ✅ User, Case, Precedent models → Django ORM
- ✅ AI logic → apps/ai-service
- ✅ All tests passing
- ✅ Frontend connected to Django
- ✅ ChatHistory persistence working

Backup: backups/apps-backend-*.tar.gz

Updated files:
- Remove apps/backend/
- Update README.md for Django architecture
- Update requirements.txt (common only)"

git push origin feature/django-backend
```

---

## ✅ 체크리스트

### Phase 1: AI Service 분리
- [ ] Git 브랜치 생성: feature/ai-service-separation
- [ ] Week 1: apps/ai-service 구축
  - [ ] Day 1: Directory structure
  - [ ] Day 2: main.py, config/settings.py
  - [ ] Day 3: models/database.py
  - [ ] Day 4: services/feedback_adapter.py
  - [ ] Day 5: routers/chat.py
- [ ] Week 2: apps/backend 프록시
  - [ ] Day 6-7: AI services 복사
  - [ ] Day 8-9: Backend proxy 구현
  - [ ] Day 10: 통합 테스트
- [ ] PR #1 생성 및 머지

### Phase 2: Django 전환
- [ ] Git 브랜치 생성: feature/django-backend
- [ ] Week 3: Django + User
  - [ ] Day 11-12: Django 프로젝트 생성
  - [ ] Day 13-14: User 모델, JWT 인증
- [ ] Week 4: Models + Proxy
  - [ ] Day 15-16: Precedent 모델
  - [ ] Day 17-18: Case 모델, AI 프록시
- [ ] Week 5: 완료
  - [ ] Day 19-20: 통합 테스트
  - [ ] Day 21: apps/backend 제거
- [ ] PR #2 생성 및 머지

---

## 🚨 문제 해결 가이드

### 1. "ModuleNotFoundError: No module named 'libs'"

**원인**: PYTHONPATH 미설정

**해결**:
```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### 2. "AI Service unavailable" (Django에서)

**원인**: AI Service 미실행 또는 포트 불일치

**해결**:
```bash
# AI Service 실행 확인
curl http://localhost:8001/health

# 실행 안 되어 있으면
cd apps/ai-service
python main.py
```

### 3. "CORS error" (Frontend)

**원인**: Django CORS 설정 누락

**해결**:
```python
# apps/backend-api/backend_api/settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
```

### 4. "Database connection error"

**원인**: PostgreSQL 미실행 또는 DB 설정 오류

**해결**:
```bash
# PostgreSQL 실행 확인
psql -U postgres -c "SELECT 1"

# DB 생성
createdb lawlaw

# .env 확인
cat .env | grep DB_
```

### 5. "JWT token invalid"

**원인**: Django SECRET_KEY 변경됨

**해결**:
```bash
# 다시 로그인하여 새 토큰 받기
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "...", "password": "..."}'
```

---

## 🎯 최종 검증 (Phase 2 완료 후)

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

echo "=== Final Verification ==="
echo ""

# 1. 디렉토리 구조
echo "[1/7] Directory structure:"
ls -la apps/
# backend-api, ai-service, web-frontend, data-pipeline만 있어야 함

# 2. AI Service
echo ""
echo "[2/7] AI Service:"
curl -s http://localhost:8001/health | jq '.status'

# 3. Django Backend
echo ""
echo "[3/7] Django Backend:"
curl -s http://localhost:8000/api/v1/ai/health | jq '.status'

# 4. 통합 테스트
echo ""
echo "[4/7] Integration test:"
./scripts/test_django_integration.sh

# 5. Git 상태
echo ""
echo "[5/7] Git status:"
git status
git log --oneline -5

# 6. Frontend
echo ""
echo "[6/7] Frontend (manual check):"
echo "Visit http://localhost:3000"
echo "- Login working?"
echo "- RAG chat working?"
echo "- Case analysis working?"

# 7. Django Admin
echo ""
echo "[7/7] Django Admin (manual check):"
echo "Visit http://localhost:8000/admin"
echo "- User model visible?"
echo "- Precedent model visible?"
echo "- Case model visible?"

echo ""
echo "==========================================="
echo "✅ Phase 2 완료!"
echo "==========================================="
```

---

## 📋 Phase 2 PR 생성

**PR Title:**
```
feat: Replace FastAPI backend with Django (Phase 2)
```

**PR Description:**

```markdown
## 📋 변경 사항

### ✅ Django 백엔드 구축
- Django 4.2+ 기반 API Gateway
- Django REST Framework
- SimpleJWT 인증

**주요 구성:**
- `apps/backend-api/`: Django 프로젝트
- `users/`: User 모델, JWT 인증
- `cases/`: Case, ChatHistory 모델
- `precedents/`: Precedent, Feedback 모델
- `api/v1/`: REST API 엔드포인트

### ✅ 모델 마이그레이션 (SQLAlchemy → Django ORM)
- User: UUID primary key, email 기반 인증
- Precedent: 388K+ 판례 데이터
- PrecedentFeedback: 사용자 피드백
- PrecedentFeedbackStats: 집계 통계 (AI Service에서 읽기)
- Case: 사건 관리
- ChatHistory: 채팅 기록

### ✅ AI Service 프록시
- `POST /api/v1/ai/chat/rag`: RAG 챗봇
- `POST /api/v1/ai/analyze/case`: 사건 분석
- `POST /api/v1/ai/generate/document`: 문서 생성
- Django에서 JWT 검증 후 AI Service 호출

### ✅ apps/backend 제거
- FastAPI 백엔드 완전 제거
- Django + AI Service 구조로 전환 완료
- 백업: `backups/apps-backend-*.tar.gz`

## 🎯 변경 이유

### As-Is (Phase 1)
```
apps/backend (FastAPI) - 모든 기능
apps/ai-service (FastAPI) - AI 전용
```

### To-Be (Phase 2)
```
apps/backend-api (Django) - 비즈니스 로직, API Gateway
apps/ai-service (FastAPI) - AI 전용
```

**이유:**
- Django Admin 활용 (데이터 관리)
- Django ORM (강력한 쿼리, 관계 관리)
- 관심사 분리 (Business vs AI)
- 확장성 (마이크로서비스 준비)

## 🧪 테스트

### 로컬 테스트
```bash
# 1. 통합 테스트
./scripts/test_django_integration.sh

# 2. 전체 실행
./scripts/run_django_dev.sh
```

### 체크리스트
- [x] Django 서버 실행 (8000)
- [x] AI Service 실행 (8001)
- [x] User signup/login (JWT)
- [x] RAG 챗봇 (Django → AI Service)
- [x] ChatHistory 저장
- [x] Precedent 모델 마이그레이션
- [x] Frontend 연동
- [x] Django Admin 접근
- [x] apps/backend 제거 완료

## ⚠️ Breaking Changes

### 1. Backend URL 변경
```
기존: http://localhost:8000 (FastAPI)
변경: http://localhost:8000 (Django)
```

### 2. API 엔드포인트 변경
```
기존: /api/v1/chat/rag
변경: /api/v1/ai/chat/rag (프록시)
```

### 3. 인증 방식 변경
```
기존: FastAPI OAuth2 + JWT
변경: Django SimpleJWT
```

### 4. 실행 방법 변경
```bash
# 기존
cd apps/backend && python main.py

# 변경
cd apps/backend-api && python manage.py runserver
```

## 📝 마이그레이션 가이드

[DJANGO_MIGRATION_PLAN.md](docs/DJANGO_MIGRATION_PLAN.md) 참조

## 👥 리뷰어

@팀원1 @팀원2

## 📚 관련 문서

- Phase 1 PR: #XX (AI Service 분리)
- Phase 2 PR: #YY (이 PR)
```

---

## 🎉 최종 완료

**축하합니다! Django 마이그레이션 완료!** 🎊

### 최종 구조

```
ai-camp-1st-llm-agent-service-project-2/
├── apps/
│   ├── backend-api/      ✅ Django (비즈니스 로직)
│   ├── ai-service/       ✅ FastAPI (AI 엔진)
│   ├── web-frontend/     ✅ React
│   └── data-pipeline/    ✅ ETL
│
├── libs/
│   ├── rag_core/         ✅ RAG 핵심 로직
│   └── domain_model/     ✅ 공통 모델
│
└── docs/
    └── DJANGO_MIGRATION_PLAN.md  ✅ 이 문서
```

### 다음 단계

1. **PR #2 머지**
2. **develop 브랜치 업데이트**
3. **팀원 동기화**
4. **프로덕션 배포 준비**

---

**작성일**: 2025-11-20
**작성자**: Claude (AI Assistant)
**문서 버전**: 1.1 (Phase 1.5 추가)
**총 소요 예상**: 5.5주 (Phase 1: 2주, Phase 1.5: 3일, Phase 2: 3주)

---

## 📌 v1.1 업데이트 내역 (2025-11-20)

### 🆕 Phase 1.5 추가 (Django 전환 준비)

**추가된 내용:**
1. ✅ **DB 상태 확인** - SQLite 스키마 분석
2. ✅ **Django inspectdb 실행** - 기존 테이블을 Django 모델로 자동 변환
3. ✅ **Fake Initial Migration** - 데이터 손실 없이 Django 관리 시작
4. ✅ **AI Service DB 모델 간소화** - Raw SQL 사용으로 스키마 동기화 부담 감소

**왜 추가했나?**
- 원본 문서는 Phase 1 → Phase 2로 직접 전환하는 것으로 작성됨
- 하지만 **실제로는 중간 단계가 필요**함:
  - 기존 DB 스키마를 Django에 매핑하는 작업
  - `--fake-initial` migration으로 데이터 보존
  - AI Service 모델 중복 문제 해결
- 이 단계 없이 Phase 2 시작하면 **"table already exists" 에러** 발생
- Phase 1.5는 **3일 소요 예상** (원래 5주 → 5.5주로 증가)

**핵심 명령어:**
```bash
# inspectdb로 기존 스키마 분석
python manage.py inspectdb > inspected_models.py

# Fake migration으로 데이터 보존
python manage.py migrate --fake-initial
```

**AI Service 개선:**
```python
# 기존: SQLAlchemy 모델 (Django와 중복)
class PrecedentFeedbackStats(Base):
    precedent_id = Column(String(200), primary_key=True)
    # ... 모든 컬럼 정의

# 개선: Raw SQL (스키마 변경에 덜 민감)
result = await db.execute(text(
    "SELECT precedent_id FROM precedent_feedback_stats "
    "WHERE should_exclude = true"
))
```

---

## 🎯 마이그레이션 로드맵 (업데이트)

```
[Phase 1] AI Service 분리 (2주)
    ↓
[Phase 1.5] Django 전환 준비 (3일) ⭐ 신규 추가
    - inspectdb 실행
    - Django 모델 매핑 전략
    - Fake migration
    - AI Service Raw SQL 전환
    ↓
[Phase 2] Django 전환 (3주)
    - Django 프로젝트 생성
    - API 재작성
    - 인증 전환
    ↓
[완료] apps/backend 삭제
```

---

## ⚠️ 주의사항 (업데이트)

**Phase 1 완료 후 반드시 Phase 1.5를 수행하세요!**

Phase 1.5 없이 Phase 2 시작 시 발생 가능한 문제:
- ❌ `table "users" already exists` 에러
- ❌ Django 모델과 기존 스키마 불일치
- ❌ AI Service 모델 중복으로 유지보수 부담
- ❌ 데이터 손실 위험

**Phase 1.5는 선택이 아닌 필수입니다!**
