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

    # ========== Backend API Integration ==========
    BACKEND_API_URL: str = os.getenv("BACKEND_API_URL", "http://localhost:8000")

    # ========== JWT Configuration ==========
    # Django SECRET_KEY와 동일하게 설정해야 함
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    # ========== Redis Configuration ==========
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_URI: str = os.getenv("REDIS_URI", "redis://localhost:6379/0")

    # ========== Session Configuration ==========
    SESSION_EXPIRE_HOURS: int = int(os.getenv("SESSION_EXPIRE_HOURS", "12"))
    MAX_CONVERSATION_LENGTH: int = int(os.getenv("MAX_CONVERSATION_LENGTH", "50"))

    class Config:
        # 프로젝트 루트의 .env 파일을 명시적으로 지정
        # 배포 환경에서는 환경변수로 직접 주입되므로 .env 파일이 없어도 동작
        env_file = str(Path(__file__).parent.parent.parent.parent / ".env")
        case_sensitive = True
        extra = "ignore"  # .env의 추가 변수 무시

settings = Settings()
