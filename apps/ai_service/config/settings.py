"""
AI Service Configuration
환경변수 기반 설정 (PostgreSQL + Qdrant)
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

    # Database (PostgreSQL Read-Only)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://myidwon:@localhost:5432/lawlaw"
    )

    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")  # Custom endpoint
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))

    # ========== Qdrant Configuration ==========
    VECTOR_DB: str = os.getenv("VECTOR_DB", "qdrant")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "law_documents")
    QDRANT_DISTANCE: str = os.getenv("QDRANT_DISTANCE", "cosine")

    # ========== Embedding Configuration ==========
    EMBED_MODE: str = os.getenv("EMBED_MODE", "remote")  # local / remote
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "dragonkue/snowflake-arctic-embed-l-v2.0-ko")

    # Remote Embedder (OpenAI 호환 API)
    REMOTE_EMBED_BASE_URL: str = os.getenv("REMOTE_EMBED_BASE_URL", "")
    REMOTE_EMBED_API_KEY: str = os.getenv("REMOTE_EMBED_API_KEY", "")

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent.parent
    VECTORDB_DIR: Path = BASE_DIR / "data" / "vectordb"
    BM25_DIR: Path = VECTORDB_DIR / "bm25"

    # CORS (Django Backend만 허용)
    CORS_ORIGINS: list = [
        "http://localhost:8000",  # Django Backend (Phase 2)
        "http://localhost:3000",  # Frontend (Next.js)
    ]

    class Config:
        # 프로젝트 루트의 .env 파일을 명시적으로 지정
        # 배포 환경에서는 환경변수로 직접 주입되므로 .env 파일이 없어도 동작
        env_file = str(Path(__file__).parent.parent.parent.parent / ".env")
        case_sensitive = True
        extra = "ignore"  # .env의 추가 변수 무시

settings = Settings()
