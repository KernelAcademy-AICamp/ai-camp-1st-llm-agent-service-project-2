"""
AI Service - FastAPI Application
RAG 챗봇, 사건 분석, 문서 생성 전담 서비스
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from pathlib import Path

from config.settings import settings
from models.database import init_db, close_db

# libs/rag_core import
from libs.rag_core import (
    create_llm_client,
    HybridRetriever,
    ConstitutionalLawChatbot,
    BM25Index,
    LegalDocumentRetriever,
    # 로컬 임베딩 (Crawler Pipeline용)
    KoreanLegalEmbedder,
)
# RemoteEmbedder + QdrantVectorDB
from libs.rag_core.embeddings.remote_embedder import RemoteEmbedder
from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB

# Logging 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI App 생성
app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.SERVICE_VERSION,
    description="LawLaw AI Service - RAG 챗봇 및 법률 문서 분석/생성"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Router 등록 =====

# V1 Routers - DEPRECATED (Phase 4 완료 후 제거 예정)
# Django Backend는 v2 API를 직접 호출하도록 마이그레이션 완료
# v1 라우터는 하위 호환성을 위해 당분간 유지
from routers import chat, analyze, preprocess, rag, llm, crawler

# v1 라우터 등록 (Deprecated - 향후 제거 예정)
app.include_router(chat.router)       # DEPRECATED: use /v2/rag/chat
app.include_router(analyze.router)    # DEPRECATED: use /v2/cases/analyze
app.include_router(preprocess.router) # 유지 (preprocessing은 v1만 존재)
app.include_router(rag.router)        # DEPRECATED: use /v2/rag/*
app.include_router(llm.router)        # DEPRECATED: use /v2/llm/*, /v2/documents/*, /v2/risk/*
app.include_router(crawler.router)    # DEPRECATED: use /v2/crawler/*

# V2 Routers (LangGraph Based - Phase 4)
# 메인 API로 사용
from routers.v2 import (
    rag_router as rag_v2_router,
    documents_router as documents_v2_router,
    cases_router as cases_v2_router,
    risk_router as risk_v2_router,
    llm_compare_router as llm_compare_v2_router,
    crawler_router as crawler_v2_router,
    analytics_router as analytics_v2_router,
)

app.include_router(rag_v2_router)
app.include_router(documents_v2_router)
app.include_router(cases_v2_router)
app.include_router(risk_v2_router)
app.include_router(llm_compare_v2_router)
app.include_router(crawler_v2_router)
app.include_router(analytics_v2_router)

# ===== Startup Event =====

@app.on_event("startup")
async def startup_event():
    """
    서비스 시작 시 AI 컴포넌트 초기화
    """
    logger.info("=" * 60)
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    logger.info("=" * 60)

    try:
        # 1. Database 초기화
        await init_db()
        logger.info("✅ Database connection initialized (Read-Only PostgreSQL)")

        # ===== v2 컴포넌트 (RAG Workflow용) =====
        # 2a. v2 Embedder 초기화 (RemoteEmbedder - GPU 불필요)
        logger.info("📊 Initializing v2 RemoteEmbedder...")
        embedder_v2 = RemoteEmbedder(
            base_url=settings.REMOTE_EMBED_BASE_URL,
            api_key=settings.REMOTE_EMBED_API_KEY,
            model=settings.EMBED_MODEL
        )
        app.state.embedder = embedder_v2  # v2용 (RAG workflow)
        logger.info("✅ v2 RemoteEmbedder initialized")

        # 3a. v2 VectorDB 로드 (QdrantVectorDB)
        logger.info("📦 Loading v2 QdrantVectorDB...")
        vectordb_v2 = QdrantVectorDB(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
            collection_name=settings.QDRANT_COLLECTION,
            embedding_dim=1024  # snowflake-arctic-embed-l-v2.0-ko
        )
        v2_doc_count = vectordb_v2.get_count()
        app.state.vectordb = vectordb_v2  # v2용 (RAG workflow)
        logger.info(f"✅ v2 QdrantVectorDB loaded: {v2_doc_count} documents")

        # ===== Crawler Pipeline용 로컬 Embedder =====
        # KoreanLegalEmbedder - 로컬 GPU 사용 (크롤러 인덱싱용)
        logger.info("📊 Initializing KoreanLegalEmbedder for Crawler...")
        embedder_local = KoreanLegalEmbedder()
        app.state.embedder_local = embedder_local  # Crawler용 로컬 임베더
        logger.info("✅ KoreanLegalEmbedder initialized")

        # 4. BM25 Index 로드
        logger.info("📦 Loading BM25 index...")
        if settings.BM25_DIR.exists():
            bm25 = BM25Index()  # 빈 인스턴스 생성
            bm25.load(str(settings.BM25_DIR))  # 디렉토리 경로 전달
            app.state.bm25 = bm25
            logger.info(f"✅ BM25 index loaded: {bm25.get_count()} documents")
        else:
            logger.warning("⚠️  BM25 index not found, creating empty index")
            bm25 = BM25Index()
            app.state.bm25 = bm25

        # 5. v2 LegalDocumentRetriever 초기화 (RAG Workflow용)
        semantic_retriever = LegalDocumentRetriever(
            vectordb=vectordb_v2,
            embedder=embedder_v2
        )

        # 6. v2 Hybrid Retriever 초기화 (RAG Workflow용)
        retriever = HybridRetriever(
            semantic_retriever=semantic_retriever,
            bm25_index=bm25
        )
        app.state.retriever = retriever
        logger.info("✅ v2 Hybrid Retriever initialized")

        # 7. LLM Client 초기화
        if settings.LLM_API_KEY:
            logger.info(f"🤖 Initializing LLM client (provider={settings.LLM_PROVIDER})...")
            llm_client = create_llm_client(
                provider=settings.LLM_PROVIDER,
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL,
                base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS
            )
            app.state.llm_client = llm_client
            logger.info("✅ LLM client initialized")

            # 8. Constitutional AI Chatbot 초기화
            chatbot = ConstitutionalLawChatbot(
                llm_client=llm_client,
                retriever=retriever
            )
            app.state.chatbot = chatbot
            logger.info("✅ Constitutional AI Chatbot initialized")
        else:
            logger.warning("⚠️  LLM_API_KEY not set, chatbot will not be available")
            app.state.llm_client = None
            app.state.chatbot = None

        # 9. Crawler Pipeline 초기화 (KoreanLegalEmbedder + QdrantVectorDB)
        logger.info("🕷️ Initializing Crawler Pipeline...")
        from services.crawler_pipeline import CrawlerPipeline
        from services.scheduler import CrawlJobScheduler

        crawler_pipeline = CrawlerPipeline(
            embedder=embedder_local,   # KoreanLegalEmbedder (로컬 GPU)
            vectordb=vectordb_v2,      # QdrantVectorDB (공용)
            bm25_index=bm25
        )
        app.state.crawler_pipeline = crawler_pipeline
        logger.info("✅ Crawler Pipeline initialized (QdrantVectorDB + KoreanLegalEmbedder)")

        # 10. Crawler Scheduler 초기화
        logger.info("📅 Initializing Crawler Scheduler...")
        crawler_scheduler = CrawlJobScheduler(pipeline=crawler_pipeline)
        crawler_scheduler.start()
        app.state.crawler_scheduler = crawler_scheduler
        logger.info("✅ Crawler Scheduler initialized")

        logger.info("=" * 60)
        logger.info("🚀 AI Service startup complete!")
        logger.info(f"📡 Listening on http://{settings.HOST}:{settings.PORT}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """
    서비스 종료 시 리소스 정리
    """
    logger.info("👋 Shutting down AI Service...")

    # Scheduler 종료
    if hasattr(app.state, 'crawler_scheduler') and app.state.crawler_scheduler:
        app.state.crawler_scheduler.stop()
        logger.info("✅ Crawler Scheduler stopped")

    await close_db()
    logger.info("✅ Shutdown complete")

# ===== Health Check =====

@app.get("/health")
async def health_check():
    """
    헬스체크 엔드포인트

    Returns:
        서비스 상태 정보
    """
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "llm_available": app.state.llm_client is not None,
        "chatbot_available": app.state.chatbot is not None,
        "pipeline_available": hasattr(app.state, 'crawler_pipeline') and app.state.crawler_pipeline is not None,
        "scheduler_available": hasattr(app.state, 'crawler_scheduler') and app.state.crawler_scheduler is not None,
        "database": "connected"
    }

@app.get("/")
async def root():
    """
    루트 엔드포인트
    """
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "docs": "/docs",
        "health": "/health"
    }

# ===== Main Entry Point =====

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
