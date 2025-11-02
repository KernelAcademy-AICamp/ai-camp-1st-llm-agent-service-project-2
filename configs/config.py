import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# AI Hub 데이터 실제 경로 (Downloads 폴더)
# 학습 목적: 실제 다운로드 받은 데이터 경로를 직접 사용
AIHUB_DATA_DIR = Path.home() / "Downloads" / "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터" / "3.개방데이터" / "1.데이터" / "Training" / "01.원천데이터"

RAW_DATA_DIR = AIHUB_DATA_DIR  # AI Hub 원천데이터 직접 사용
PROCESSED_DATA_DIR = DATA_DIR / "processed"
VECTORDB_DIR = DATA_DIR / "vectordb"


class EmbeddingConfig(BaseModel):
    """Embedding configuration"""
    model_name: str = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")
    device: str = "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu"
    batch_size: int = 32


class VectorDBConfig(BaseModel):
    """Vector database configuration"""
    db_type: str = os.getenv("VECTOR_DB_TYPE", "chroma")
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", str(VECTORDB_DIR / "chroma"))
    faiss_index_path: str = os.getenv("FAISS_INDEX_PATH", str(VECTORDB_DIR / "faiss"))
    bm25_index_path: str = os.getenv("BM25_INDEX_PATH", str(VECTORDB_DIR / "bm25"))
    collection_name: str = "criminal_law_docs"


class RAGConfig(BaseModel):
    """RAG configuration"""
    top_k: int = int(os.getenv("TOP_K_RETRIEVAL", "5"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # Search method: "semantic", "bm25", "hybrid"
    search_type: str = os.getenv("SEARCH_TYPE", "hybrid")

    # BM25 parameters
    bm25_k1: float = float(os.getenv("BM25_K1", "1.5"))  # Term frequency saturation
    bm25_b: float = float(os.getenv("BM25_B", "0.75"))   # Length normalization

    # Hybrid search parameters
    fusion_method: str = os.getenv("FUSION_METHOD", "rrf")  # "rrf" or "weighted_sum"
    semantic_weight: float = float(os.getenv("SEMANTIC_WEIGHT", "0.5"))  # 0.0 ~ 1.0
    rrf_k: int = int(os.getenv("RRF_K", "60"))  # RRF constant
    enable_adaptive_weighting: bool = os.getenv("ENABLE_ADAPTIVE_WEIGHTING", "true").lower() == "true"


class LLMConfig(BaseModel):
    """LLM configuration"""
    model_name: str = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
    temperature: float = 0.1
    max_tokens: int = 2000
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Ollama configuration
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "kosaul-q4")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class Config:
    """Main configuration class"""
    embedding = EmbeddingConfig()
    vectordb = VectorDBConfig()
    rag = RAGConfig()
    llm = LLMConfig()

    # Data paths
    raw_data_dir = RAW_DATA_DIR
    processed_data_dir = PROCESSED_DATA_DIR


config = Config()
