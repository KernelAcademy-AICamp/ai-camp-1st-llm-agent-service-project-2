"""
V2 API Routers - LangGraph Based

Phase 4 - Week 11-13: LangGraph 기반 API

라우터 목록:
- rag_router: /v2/rag/* (RAG 질의응답)
- documents_router: /v2/documents/* (문서 분석)
- cases_router: /v2/cases/* (사건 분석)
- criminal_cases_router: /v2/criminal/* (형사 사건 관리)
- risk_router: /v2/risk/* (리스크 분석 - Checkpointing)
- llm_compare_router: /v2/llm/* (LLM 비교 - Checkpointing)
- crawler_router: /v2/crawler/* (크롤러 - Checkpointing, Week 13)
- analytics_router: /v2/analytics/* (Analytics - Checkpointing 불필요, Week 13)
- agent_hub_router: /v2/agent-hub/* (Agent Hub - Master Agent Orchestrator)
- sentencing_router: /v2/sentencing/* (양형기준 조회 - Phase 3)
"""

from apps.ai_service.routers.v2.rag import router as rag_router
from apps.ai_service.routers.v2.documents import router as documents_router
from apps.ai_service.routers.v2.cases import router as cases_router
from apps.ai_service.routers.v2.criminal_cases import router as criminal_cases_router
from apps.ai_service.routers.v2.risk import router as risk_router
from apps.ai_service.routers.v2.llm_compare import router as llm_compare_router
from apps.ai_service.routers.v2.crawler import router as crawler_router
from apps.ai_service.routers.v2.analytics import router as analytics_router
from apps.ai_service.routers.v2.agent_hub import router as agent_hub_router
from apps.ai_service.routers.v2.sentencing import router as sentencing_router

__all__ = [
    "rag_router",
    "documents_router",
    "cases_router",
    "criminal_cases_router",
    "risk_router",
    "llm_compare_router",
    "crawler_router",
    "analytics_router",
    "agent_hub_router",
    "sentencing_router",
]
