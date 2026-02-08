"""
Configuration management for LawLaw Backend
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: str = "openai"
    api_key: Optional[str] = None  # Unified API key (LLM_API_KEY)
    base_url: Optional[str] = None  # Base URL for custom/self-hosted endpoints (LLM_BASE_URL)
    openai_api_key: Optional[str] = None  # Deprecated: use api_key
    gemini_api_key: Optional[str] = None
    model: str = "gpt-4-turbo-preview"
    temperature: float = 0.1
    max_tokens: int = 2000

class EmbeddingConfig(BaseModel):
    """Embedding model configuration"""
    model: str = "BAAI/bge-m3"
    provider: str = "huggingface"
    device: str = "cpu"

class VectorDBConfig(BaseModel):
    """Vector database configuration"""
    db_type: str = "qdrant"
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None

class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = "sqlite+aiosqlite:///./lawlaw.db"

class APIConfig(BaseModel):
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    secret_key: str = "your-secret-key-change-in-production"

class Config(BaseModel):
    """Main configuration"""
    llm: LLMConfig
    embedding: EmbeddingConfig
    vectordb: VectorDBConfig
    database: DatabaseConfig
    api: APIConfig

# Create configuration instance
config = Config(
    llm=LLMConfig(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),  # Prefer LLM_API_KEY
        base_url=os.getenv("LLM_BASE_URL"),  # Optional: for custom endpoints
        openai_api_key=os.getenv("OPENAI_API_KEY"),  # Deprecated: for backward compatibility
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        model=os.getenv("LLM_MODEL", "gpt-4-turbo-preview"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000"))
    ),
    embedding=EmbeddingConfig(
        model=os.getenv("EMBED_MODEL", "BAAI/bge-m3"),
        provider=os.getenv("EMBED_PROVIDER", "huggingface"),
        device=os.getenv("DEVICE", "cpu")
    ),
    vectordb=VectorDBConfig(
        db_type=os.getenv("VECTOR_DB", "qdrant"),
        qdrant_url=os.getenv("QDRANT_URL"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY")
    ),
    database=DatabaseConfig(
        url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./lawlaw.db")
    ),
    api=APIConfig(
        host=os.getenv("BACKEND_API_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_API_PORT", "8000")),
        debug=os.getenv("DEBUG", "True").lower() == "true",
        secret_key=os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    )
)
