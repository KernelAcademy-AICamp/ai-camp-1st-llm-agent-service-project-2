"""
LawLaw Backend Server
FastAPI 기반 백엔드 서버 - Monorepo 구조
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import logging
import sys
from pathlib import Path

# ==========================================
# PYTHONPATH 설정 (Monorepo 구조)
# ==========================================
BASE_DIR = Path(__file__).parent.parent.parent  # ai-camp-1st-llm-agent-service-project-2/
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

# ==========================================
# apps/backend Import
# ==========================================
from apps.backend.services.file_parser import FileParser
from apps.backend.services.case_analyzer import CaseAnalyzer
from apps.backend.services.scenario_detector import ScenarioDetector
from apps.backend.services.document_generator import DocumentGenerator
from apps.backend.services.scourt_scraper import SCourtScraper
from apps.backend.services.precedent_crawler import PrecedentCrawler
from apps.backend.services.scheduler import PrecedentScheduler
from apps.backend.services.openlaw_client import OpenLawAPIClient

# Routers
from apps.backend.routers.chat import setup_chat_routes
from apps.backend.routers.cases import setup_case_routes
from apps.backend.routers.documents import setup_document_routes
from apps.backend.routers.adapters import setup_adapter_routes
from apps.backend.routers.auth import setup_auth_routes
from apps.backend.routers.precedents import setup_precedent_routes
from apps.backend.routers.precedent_scraping import router as scraping_router
from apps.backend.routers.precedent_search import router as search_router
from apps.backend.routers.feedback import setup_feedback_routes

# Database
from apps.backend.database import engine, Base
from apps.backend.models.precedent import Precedent
from apps.backend.models.precedent_feedback import PrecedentFeedback, PrecedentFeedbackStats
from apps.backend.models.user import User

# Config
from configs.config import config
import os
import asyncio

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="LawLaw Backend API",
    description="형사법 전문 AI 어시스턴트 백엔드 API (Monorepo)",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "file://"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# RAG 시스템 초기화 (libs/rag_core 활용)
# ==========================================

embedder = None
vectordb = None
bm25_index = None
hybrid_retriever = None
constitutional_chatbot = None

try:
    # 임베딩 모델 초기화
    embedder = KoreanLegalEmbedder()
    logger.info("✅ Embedder initialized (from libs/rag_core)")

    # 벡터 DB 초기화
    vectordb = ChromaVectorDB(
        persist_directory=str(BASE_DIR / "data" / "vectordb" / "chroma_criminal_law"),
        collection_name="criminal_law_docs"
    )
    logger.info(f"✅ Vector DB loaded: {vectordb.get_count()} documents")

    # BM25 인덱스 초기화
    bm25_index_path = BASE_DIR / "data" / "vectordb" / "bm25"
    if bm25_index_path.exists():
        bm25_index = BM25Index()
        bm25_index.load(str(bm25_index_path))
        logger.info(f"✅ BM25 index loaded: {bm25_index.get_count()} documents")

    # Semantic Retriever 초기화
    semantic_retriever = LegalDocumentRetriever(
        embedder=embedder,
        vectordb=vectordb
    )

    # Hybrid Retriever 초기화
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

except Exception as e:
    logger.error(f"❌ Failed to initialize RAG system: {e}")
    logger.info("Will use fallback mode without RAG")

# LLM 클라이언트 초기화
llm_client = None
try:
    llm_client = create_llm_client(
        provider=config.llm.provider,
        api_key=config.llm.api_key,
        model=config.llm.model,
        base_url=config.llm.base_url,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens
    )
    logger.info(f"✅ LLM client initialized (provider={config.llm.provider})")

    if hybrid_retriever and llm_client:
        constitutional_chatbot = AdapterChatbot(
            retriever=hybrid_retriever,
            llm_client=llm_client,
            enable_self_critique=True,
            critique_threshold=0.5
        )
        logger.info("✅ Constitutional AI Chatbot initialized")

except Exception as e:
    logger.warning(f"⚠️  Failed to initialize LLM: {e}")
    logger.info("API will run without LLM support")

# 업로드 디렉토리
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Services 초기화
file_parser = FileParser()
scenario_detector = ScenarioDetector()

case_analyzer = None
if llm_client:
    case_analyzer = CaseAnalyzer(llm_client=llm_client, retriever=hybrid_retriever)
    logger.info("✅ CaseAnalyzer initialized")

document_generator = None
if llm_client:
    document_generator = DocumentGenerator(llm_client=llm_client)
    logger.info("✅ DocumentGenerator initialized")

# Precedent Crawler & Scheduler 초기화
scourt_scraper = None
precedent_crawler = None
precedent_scheduler = None
openlaw_client = None

try:
    openlaw_client = OpenLawAPIClient(api_key=os.getenv("OPENLAW_API_KEY", "fox_racer"))
    scourt_scraper = SCourtScraper()
    precedent_crawler = PrecedentCrawler(scraper=scourt_scraper)
    precedent_scheduler = PrecedentScheduler(crawler=precedent_crawler)
    logger.info("✅ Precedent crawling system initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize precedent system: {e}")

# ==========================================
# Database Tables
# ==========================================

async def create_db_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created")

# ==========================================
# Startup & Shutdown
# ==========================================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting LawLaw Backend (Monorepo)...")
    await create_db_tables()

    if precedent_scheduler:
        precedent_scheduler.start()
        asyncio.create_task(precedent_scheduler.run_initial_crawl())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Shutting down LawLaw Backend...")
    if precedent_scheduler:
        precedent_scheduler.shutdown()

# ==========================================
# Health Check
# ==========================================

class HealthResponse(BaseModel):
    status: str
    model_status: str
    rag_status: str
    timestamp: str

@app.get("/")
async def root():
    return {
        "name": "LawLaw Backend API (Monorepo)",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy" if llm_client else "degraded",
        model_status="available" if llm_client else "not_configured",
        rag_status="available" if hybrid_retriever else "not_configured",
        timestamp=datetime.now().isoformat()
    )

# ==========================================
# Router Registration
# ==========================================

chat_router = setup_chat_routes(
    constitutional_chatbot=constitutional_chatbot,
    llm_client=llm_client,
    hybrid_retriever=hybrid_retriever,
    openlaw_client=openlaw_client
)
app.include_router(chat_router)

cases_router = setup_case_routes(
    case_analyzer=case_analyzer,
    scenario_detector=scenario_detector,
    file_parser=file_parser,
    upload_dir=UPLOAD_DIR
)
app.include_router(cases_router)

documents_router = setup_document_routes(
    document_generator=document_generator,
    scenario_detector=scenario_detector,
    upload_dir=UPLOAD_DIR
)
app.include_router(documents_router)

adapters_router = setup_adapter_routes(
    constitutional_chatbot=constitutional_chatbot
)
app.include_router(adapters_router)

auth_router = setup_auth_routes()
app.include_router(auth_router)

precedents_router = setup_precedent_routes(
    crawler=precedent_crawler,
    openlaw_client=openlaw_client
)
app.include_router(precedents_router)

app.include_router(scraping_router)
app.include_router(search_router)

feedback_router = setup_feedback_routes()
app.include_router(feedback_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
