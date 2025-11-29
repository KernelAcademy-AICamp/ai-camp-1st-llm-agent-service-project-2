"""
V2 API Routers - LangGraph Based

Phase 4 - Week 11-12: LangGraph 기반 API

라우터 목록:
- rag_router: /v2/rag/* (RAG 질의응답)
- documents_router: /v2/documents/* (문서 분석)
- cases_router: /v2/cases/* (사건 분석)
- risk_router: /v2/risk/* (리스크 분석 - Checkpointing)
"""

from apps.ai_service.routers.v2.rag import router as rag_router
from apps.ai_service.routers.v2.documents import router as documents_router
from apps.ai_service.routers.v2.cases import router as cases_router
from apps.ai_service.routers.v2.risk import router as risk_router

__all__ = [
    "rag_router",
    "documents_router",
    "cases_router",
    "risk_router",
]
