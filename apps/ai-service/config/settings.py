"""
AI Service Configuration
환경변수 기반 설정 (PostgreSQL)
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

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent.parent
    VECTORDB_DIR: Path = BASE_DIR / "data" / "vectordb"
    CHROMA_DIR: Path = VECTORDB_DIR / "chroma_criminal_law"
    BM25_DIR: Path = VECTORDB_DIR / "bm25"

    # CORS (Django Backend만 허용)
    CORS_ORIGINS: list = [
        "http://localhost:8000",  # Django Backend (Phase 2)
        "http://localhost:8000",  # FastAPI Backend (Phase 1)
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # .env의 추가 변수 무시

settings = Settings()
