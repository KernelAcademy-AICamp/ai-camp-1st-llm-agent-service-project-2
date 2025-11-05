"""
LawLaw Backend Server
FastAPI 기반 백엔드 서버 - Ollama를 통한 로컬 LLM 연동
RAG + Constitutional AI 통합
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import logging
import sys
from pathlib import Path

# 프로젝트 루트 경로를 Python path에 추가
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Core 모듈 임포트
from app.backend.core.llm.llm_client import create_llm_client
from app.backend.core.embeddings.embedder import KoreanLegalEmbedder
from app.backend.core.embeddings.vectordb import ChromaVectorDB
from app.backend.core.retrieval.retriever import LegalDocumentRetriever
from app.backend.core.retrieval.bm25_index import BM25Index
from app.backend.core.retrieval.hybrid_retriever import HybridRetriever
from app.backend.core.llm.adapter_chatbot import AdapterChatbot

# Services 모듈 임포트
from app.backend.services.file_parser import FileParser
from app.backend.services.case_analyzer import CaseAnalyzer
from app.backend.services.scenario_detector import ScenarioDetector
from app.backend.services.document_generator import DocumentGenerator
from app.backend.services.scourt_scraper import SCourtScraper
from app.backend.services.precedent_crawler import PrecedentCrawler
from app.backend.services.scheduler import PrecedentScheduler
from app.backend.services.openlaw_client import OpenLawAPIClient

# Routers 임포트
from app.backend.routers.chat import setup_chat_routes
from app.backend.routers.cases import setup_case_routes
from app.backend.routers.documents import setup_document_routes
from app.backend.routers.adapters import setup_adapter_routes
from app.backend.routers.auth import setup_auth_routes
from app.backend.routers.precedents import setup_precedent_routes
from app.backend.routers.precedent_scraping import router as scraping_router
from app.backend.routers.precedent_search import router as search_router

# Database 임포트
from app.backend.database import engine, Base
from app.backend.models.precedent import Precedent
from app.backend.models.user import User

from configs.config import config
import os
import asyncio

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="LawLaw Backend API",
    description="형사법 전문 AI 어시스턴트 백엔드 API",
    version="0.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "file://"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RAG 시스템 초기화
embedder = None
vectordb = None
bm25_index = None
hybrid_retriever = None
constitutional_chatbot = None

try:
    # 임베딩 모델 초기화
    embedder = KoreanLegalEmbedder()
    logger.info("Embedder initialized successfully")

    # 벡터 DB 초기화 (형사법 ChromaDB 로드)
    vectordb = ChromaVectorDB(
        persist_directory=str(BASE_DIR / "data" / "vectordb" / "chroma_criminal_law"),
        collection_name="criminal_law_docs"
    )
    logger.info(f"Vector DB loaded with {vectordb.get_count()} documents")

    # BM25 인덱스 초기화
    bm25_index_path = BASE_DIR / "data" / "vectordb" / "bm25"
    if bm25_index_path.exists():
        bm25_index = BM25Index()
        bm25_index.load(str(bm25_index_path))
        logger.info(f"BM25 index loaded with {bm25_index.get_count()} documents")

    # Semantic Retriever 초기화
    semantic_retriever = LegalDocumentRetriever(embedder=embedder, vectordb=vectordb)

    # Hybrid Retriever 초기화 (Semantic + BM25)
    if bm25_index:
        hybrid_retriever = HybridRetriever(
            semantic_retriever=semantic_retriever,
            bm25_index=bm25_index,
            fusion_method='rrf',
            semantic_weight=0.5,
            enable_adaptive_weighting=True
        )
        logger.info("Hybrid Retriever initialized successfully")
    else:
        hybrid_retriever = semantic_retriever
        logger.info("Using Semantic Retriever only (BM25 index not found)")

except Exception as e:
    logger.error(f"Failed to initialize RAG system: {e}")
    logger.info("Will use fallback mode without RAG")

# LLM 클라이언트 초기화
llm_client = None
OPENAI_API_KEY = config.llm.openai_api_key
MODEL_NAME = "gpt-4-turbo-preview"

try:
    llm_client = create_llm_client(
        provider="openai",
        api_key=OPENAI_API_KEY,
        model=MODEL_NAME,
        temperature=0.1,
        max_tokens=2000
    )
    logger.info(f"OpenAI LLM client initialized successfully (model={MODEL_NAME})")

    if hybrid_retriever and llm_client:
        constitutional_chatbot = AdapterChatbot(
            retriever=hybrid_retriever,
            llm_client=llm_client,
            enable_self_critique=True,
            critique_threshold=0.5
        )
        logger.info("Adapter-enabled Constitutional AI Chatbot initialized successfully")

except Exception as e:
    logger.warning(f"Failed to initialize LLM client: {e}")
    logger.info("API will run without LLM support")

# 업로드 디렉토리 설정
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Services 초기화
file_parser = FileParser()
scenario_detector = ScenarioDetector()

case_analyzer = None
if llm_client:
    case_analyzer = CaseAnalyzer(llm_client=llm_client, retriever=hybrid_retriever)
    logger.info("CaseAnalyzer initialized successfully")

document_generator = None
if llm_client:
    document_generator = DocumentGenerator(llm_client=llm_client)
    logger.info("DocumentGenerator initialized successfully")

# ============================================
# Precedent Crawler & Scheduler 초기화
# ============================================

scourt_scraper = None
precedent_crawler = None
precedent_scheduler = None
openlaw_client = None

try:
    # OpenLaw API Client 초기화
    OPENLAW_API_KEY = os.getenv("OPENLAW_API_KEY", "fox_racer")  # 기본값: 공용 키
    openlaw_client = OpenLawAPIClient(api_key=OPENLAW_API_KEY)
    logger.info(f"OpenLaw API client initialized (key: {OPENLAW_API_KEY[:10]}...)")

    # Supreme Court Portal Scraper 초기화
    scourt_scraper = SCourtScraper()
    logger.info("Supreme Court portal scraper initialized")

    # Precedent Crawler 초기화
    precedent_crawler = PrecedentCrawler(scraper=scourt_scraper)
    logger.info("Precedent crawler initialized")

    # Precedent Scheduler 초기화
    precedent_scheduler = PrecedentScheduler(crawler=precedent_crawler)
    logger.info("Precedent scheduler initialized")

except Exception as e:
    logger.error(f"Failed to initialize precedent crawling system: {e}")
    logger.info("API will run without precedent crawling support")

# ============================================
# Database Tables 생성
# ============================================

async def create_db_tables():
    """데이터베이스 테이블 생성"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")

# ============================================
# Startup & Shutdown Events
# ============================================

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    logger.info("Starting LawLaw Backend...")

    # 데이터베이스 테이블 생성
    await create_db_tables()

    # 스케줄러 시작
    if precedent_scheduler:
        precedent_scheduler.start()
        logger.info("Precedent scheduler started")

        # 초기 크롤링 실행 (비동기)
        asyncio.create_task(precedent_scheduler.run_initial_crawl())
        logger.info("Initial precedent crawl scheduled")

@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 실행"""
    logger.info("Shutting down LawLaw Backend...")

    # 스케줄러 종료
    if precedent_scheduler:
        precedent_scheduler.shutdown()
        logger.info("Precedent scheduler shut down")

# ============================================
# Health Check Endpoint
# ============================================

class HealthResponse(BaseModel):
    status: str
    model_status: str
    timestamp: str

@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "name": "LawLaw Backend API",
        "version": "0.1.0",
        "status": "running"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """서버 및 모델 상태 확인"""
    try:
        if llm_client and OPENAI_API_KEY:
            model_available = True
        else:
            model_available = False

        return HealthResponse(
            status="healthy" if model_available else "degraded",
            model_status="available" if model_available else "not_configured",
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            model_status="error",
            timestamp=datetime.now().isoformat()
        )

# ============================================
# Router Registration
# ============================================

# Chat & Search Router 등록
chat_router = setup_chat_routes(
    constitutional_chatbot=constitutional_chatbot,
    llm_client=llm_client,
    hybrid_retriever=hybrid_retriever,
    openlaw_client=openlaw_client
)
app.include_router(chat_router)

# Cases Router 등록
cases_router = setup_case_routes(
    case_analyzer=case_analyzer,
    scenario_detector=scenario_detector,
    file_parser=file_parser,
    upload_dir=UPLOAD_DIR
)
app.include_router(cases_router)

# Documents Router 등록
documents_router = setup_document_routes(
    document_generator=document_generator,
    scenario_detector=scenario_detector,
    upload_dir=UPLOAD_DIR
)
app.include_router(documents_router)

# Adapters Router 등록
adapters_router = setup_adapter_routes(
    constitutional_chatbot=constitutional_chatbot
)
app.include_router(adapters_router)

# Auth Router 등록
auth_router = setup_auth_routes()
app.include_router(auth_router)

# Precedents Router 등록
precedents_router = setup_precedent_routes(crawler=precedent_crawler, openlaw_client=openlaw_client)
app.include_router(precedents_router)

# Precedent Scraping Router 등록 (Playwright 기반)
app.include_router(scraping_router)

# Precedent VectorDB Search Router 등록 (ChromaDB 기반)
app.include_router(search_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)