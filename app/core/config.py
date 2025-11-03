"""
Application Configuration
환경변수 기반 애플리케이션 설정
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Application
    APP_NAME: str = "PDF OCR System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str

    # Storage (MinIO/S3)
    STORAGE_ENDPOINT: str
    STORAGE_ACCESS_KEY: str
    STORAGE_SECRET_KEY: str
    STORAGE_BUCKET_PUBLIC: str = "public-docs"
    STORAGE_BUCKET_PRIVATE: str = "private-docs"
    STORAGE_USE_SSL: bool = False

    # Encryption
    ENCRYPTION_KEY: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # OCR Settings
    OCR_ENGINE: str = "auto"  # auto, tesseract, easyocr, paddleocr
    TESSERACT_LANG: str = "kor+eng"
    TESSERACT_DPI: int = 300
    OCR_MAX_WORKERS: int = 4
    OCR_CONFIDENCE_THRESHOLD: float = 60.0

    # File Upload
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: str = ".pdf"
    ALLOWED_MIME_TYPES: str = "application/pdf"

    # Rate Limiting
    RATE_LIMIT_UPLOADS: str = "10/hour"
    RATE_LIMIT_API: str = "100/minute"

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # CORS
    CORS_ORIGINS: str

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins as list"""
        if not self.CORS_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Monitoring (Optional)
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """설정 객체 반환 (싱글톤)"""
    return Settings()


settings = get_settings()
