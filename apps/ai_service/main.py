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
    QdrantHybridRetriever,
    SPLADEEncoder,
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

# Agent Hub 디버그 로깅 활성화 (환경변수 AGENT_DEBUG=true로 제어)
import os
if os.getenv("AGENT_DEBUG", "false").lower() == "true":
    # Agent 관련 모듈 DEBUG 레벨 설정
    for module_name in [
        "apps.ai_service.agents",
        "apps.ai_service.agents.nodes",
        "apps.ai_service.agents.master_agent",
        "apps.ai_service.agents.nodes.complexity_classifier_node",
        "apps.ai_service.agents.nodes.medium_path_node",
        "apps.ai_service.agents.nodes.fast_path_node",
        "apps.ai_service.agents.nodes.deep_path_node",
        "apps.ai_service.agents.nodes.generate_response_node",
        "apps.ai_service.agents.tools.registry",
        "libs.rag_core.llm.llm_client",
    ]:
        logging.getLogger(module_name).setLevel(logging.DEBUG)
    logger.info("🔧 Agent Hub DEBUG 모드 활성화됨")

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
    criminal_cases_router as criminal_cases_v2_router,
    risk_router as risk_v2_router,
    llm_compare_router as llm_compare_v2_router,
    crawler_router as crawler_v2_router,
    analytics_router as analytics_v2_router,
    agent_hub_router as agent_hub_v2_router,
    sentencing_router as sentencing_v2_router,
)

app.include_router(rag_v2_router)
app.include_router(documents_v2_router)
app.include_router(cases_v2_router)
app.include_router(criminal_cases_v2_router)
app.include_router(risk_v2_router)
app.include_router(llm_compare_v2_router)
app.include_router(crawler_v2_router)
app.include_router(analytics_v2_router)
app.include_router(agent_hub_v2_router)
app.include_router(sentencing_v2_router)

# ===== Startup Event =====

@app.on_event("startup")
async def startup_event():
    """
    서비스 시작 시 AI 컴포넌트 초기화
    """
    logger.info("=" * 60)
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    logger.info("=" * 60)

    # 개발 모드에서 필수 서비스 연결 실패 시에도 기본 서비스 시작 허용
    import os
    DEV_MODE = os.getenv("DEV_MODE", "True") == "True"

    try:
        # 1. Database 초기화
        await init_db()
        logger.info("✅ Database connection initialized")

        # 기본 상태 초기화 (None으로 설정)
        app.state.embedder = None
        app.state.vectordb = None
        app.state.bm25 = None
        app.state.retriever = None
        app.state.llm_client = None
        app.state.chatbot = None
        app.state.crawler_pipeline = None
        app.state.crawler_scheduler = None
        app.state.document_indexer = None  # 사용자 문서 인덱서

        # ===== v2 컴포넌트 (RAG Workflow용) =====
        vectordb_v2 = None
        embedder_v2 = None
        bm25 = None

        try:
            # 2a. v2 Embedder 초기화 (EMBED_MODE에 따라 로컬/원격 선택)
            # 모델: dragonkue/snowflake-arctic-embed-l-v2.0-ko (1024 dim)
            if settings.EMBED_MODE == "local":
                from libs.rag_core.embeddings.embedder import KoreanLegalEmbedder
                logger.info("📊 Initializing v2 LocalEmbedder (sentence-transformers)...")
                embedder_v2 = KoreanLegalEmbedder(model_name=settings.EMBED_MODEL)
                logger.info(f"✅ v2 LocalEmbedder initialized (model: {settings.EMBED_MODEL})")
            else:
                logger.info("📊 Initializing v2 RemoteEmbedder...")
                embedder_v2 = RemoteEmbedder(
                    base_url=settings.REMOTE_EMBED_BASE_URL,
                    api_key=settings.REMOTE_EMBED_API_KEY,
                    model=settings.EMBED_MODEL
                )
                logger.info(f"✅ v2 RemoteEmbedder initialized (model: {settings.EMBED_MODEL})")
            app.state.embedder = embedder_v2
        except Exception as e:
            logger.warning(f"⚠️  Embedder initialization failed: {e}")

        try:
            # 3a. v2 VectorDB 로드 (QdrantVectorDB)
            # dragonkue/snowflake-arctic-embed-l-v2.0-ko = 1024 dim
            embedding_dim = 1024
            logger.info(f"📦 Loading v2 QdrantVectorDB (dim={embedding_dim})...")
            vectordb_v2 = QdrantVectorDB(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
                collection_name=settings.QDRANT_COLLECTION,
                embedding_dim=embedding_dim
            )
            v2_doc_count = vectordb_v2.get_count()
            app.state.vectordb = vectordb_v2  # v2용 (RAG workflow)
            logger.info(f"✅ v2 QdrantVectorDB loaded: {v2_doc_count} documents")
        except Exception as e:
            logger.warning(f"⚠️  QdrantVectorDB initialization failed: {e}")
            logger.warning("⚠️  RAG features will not be available")

        # Crawler도 RemoteEmbedder 사용 (동일한 임베딩 모델: dragonkue/snowflake-arctic-embed-l-v2.0-ko)
        # KoreanLegalEmbedder는 더 이상 사용하지 않음

        # 4. Retriever 초기화 (SEARCH_MODE에 따라 선택)
        retriever = None
        splade_encoder = None
        bm25 = None

        if settings.SEARCH_MODE == "hybrid" and vectordb_v2 and embedder_v2:
            # ===== Qdrant 네이티브 하이브리드 검색 (Dense + SPLADE) =====
            logger.info("🔍 Initializing Qdrant Hybrid Search (Dense + SPLADE)...")

            try:
                # SPLADE 인코더 로드
                logger.info(f"📦 Loading SPLADE encoder: {settings.SPLADE_MODEL}")
                splade_encoder = SPLADEEncoder(model_name=settings.SPLADE_MODEL)
                app.state.splade_encoder = splade_encoder
                logger.info(f"✅ SPLADE encoder loaded (vocab_size={splade_encoder.vocab_size})")

                # QdrantHybridRetriever 초기화
                retriever = QdrantHybridRetriever(
                    qdrant_url=settings.QDRANT_URL,
                    qdrant_api_key=settings.QDRANT_API_KEY or None,
                    collection_name=settings.QDRANT_HYBRID_COLLECTION,
                    dense_embedder=embedder_v2,
                    splade_encoder=splade_encoder
                )
                app.state.retriever = retriever
                logger.info(f"✅ Qdrant Hybrid Retriever initialized (collection={settings.QDRANT_HYBRID_COLLECTION})")
                logger.info(f"   📊 Documents: {retriever.get_count()}")

            except Exception as e:
                logger.warning(f"⚠️  Hybrid Retriever initialization failed: {e}")
                logger.warning("⚠️  Falling back to legacy mode (BM25)")
                settings.SEARCH_MODE = "legacy"

        if settings.SEARCH_MODE == "legacy" and vectordb_v2 and embedder_v2:
            # ===== 레거시 모드: Dense + BM25 =====
            logger.info("🔍 Initializing Legacy Hybrid Search (Dense + BM25)...")

            # BM25 Index 로드
            logger.info("📦 Loading BM25 index...")
            if settings.BM25_DIR.exists():
                try:
                    bm25 = BM25Index()
                    bm25.load(str(settings.BM25_DIR))
                    app.state.bm25 = bm25
                    logger.info(f"✅ BM25 index loaded: {bm25.get_count()} documents")
                except Exception as e:
                    logger.warning(f"⚠️  BM25 index load failed: {e}")
                    bm25 = BM25Index()
                    app.state.bm25 = bm25
            else:
                logger.warning("⚠️  BM25 index not found, creating empty index")
                bm25 = BM25Index()
                app.state.bm25 = bm25

            # LegalDocumentRetriever 초기화
            semantic_retriever = LegalDocumentRetriever(
                vectordb=vectordb_v2,
                embedder=embedder_v2
            )

            # Legacy HybridRetriever 초기화 (BM25 기반)
            retriever = HybridRetriever(
                semantic_retriever=semantic_retriever,
                bm25_index=bm25
            )
            app.state.retriever = retriever
            logger.info("✅ Legacy Hybrid Retriever initialized (BM25)")

        if retriever:
            # RAG 노드에 전역 retriever 설정 (LangGraph checkpointing 직렬화 문제 방지)
            from apps.ai_service.workflows.nodes.rag_nodes import set_global_retriever
            set_global_retriever(retriever)
            logger.info("✅ Global retriever set for RAG nodes")

        # DocumentIndexer 초기화 (사용자 문서 임베딩/검색)
        if vectordb_v2 and embedder_v2:
            try:
                from apps.ai_service.services.document_indexer import DocumentIndexer
                document_indexer = DocumentIndexer(
                    vectordb=vectordb_v2,
                    embedder=embedder_v2,
                    collection_name="user_documents",
                    qdrant_url=settings.QDRANT_URL
                )
                app.state.document_indexer = document_indexer
                logger.info(f"✅ DocumentIndexer initialized (collection: user_documents)")
            except Exception as e:
                logger.warning(f"⚠️  DocumentIndexer initialization failed: {e}")

        if not retriever:
            logger.warning("⚠️  Retriever not initialized - RAG features will be limited")

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

            # 8. Constitutional AI Chatbot 초기화 (retriever가 있을 때만)
            if retriever:
                chatbot = ConstitutionalLawChatbot(
                    llm_client=llm_client,
                    retriever=retriever
                )
                app.state.chatbot = chatbot
                logger.info("✅ Constitutional AI Chatbot initialized")
            else:
                logger.warning("⚠️  Retriever not available, chatbot will not be available")
        else:
            logger.warning("⚠️  LLM_API_KEY not set, chatbot will not be available")

        # 9. Crawler Pipeline 초기화 (RemoteEmbedder + QdrantVectorDB)
        if embedder_v2 and vectordb_v2:
            try:
                logger.info("🕷️ Initializing Crawler Pipeline...")
                from services.crawler_pipeline import CrawlerPipeline
                from services.scheduler import CrawlJobScheduler

                crawler_pipeline = CrawlerPipeline(
                    embedder=embedder_v2,      # RemoteEmbedder (로컬 API)
                    vectordb=vectordb_v2,      # QdrantVectorDB
                    bm25_index=bm25
                )
                app.state.crawler_pipeline = crawler_pipeline
                logger.info("✅ Crawler Pipeline initialized (QdrantVectorDB + RemoteEmbedder)")

                # 10. Crawler Scheduler 초기화
                logger.info("📅 Initializing Crawler Scheduler...")
                crawler_scheduler = CrawlJobScheduler(pipeline=crawler_pipeline)
                crawler_scheduler.start()
                app.state.crawler_scheduler = crawler_scheduler
                logger.info("✅ Crawler Scheduler initialized")
            except Exception as e:
                logger.warning(f"⚠️  Crawler Pipeline initialization failed: {e}")

        # 11. WorkflowExecutor 초기화 (retriever 주입)
        logger.info("🔧 Initializing WorkflowExecutor...")
        from apps.ai_service.agents.workflow_executor import init_workflow_executor
        workflow_executor = init_workflow_executor(retriever=retriever)
        app.state.workflow_executor = workflow_executor
        logger.info("✅ WorkflowExecutor initialized with retriever")

        logger.info("=" * 60)
        logger.info("🚀 AI Service startup complete!")
        logger.info(f"📡 Listening on http://{settings.HOST}:{settings.PORT}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        if not DEV_MODE:
            raise
        logger.warning("⚠️  DEV_MODE: Starting with limited functionality")

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
