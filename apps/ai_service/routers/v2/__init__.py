"""
V2 API Routers - LangGraph Based

Phase 4 - Week 11: LangGraph 기반 API

라우터 목록:
- rag_router: /v2/rag/* (RAG 질의응답)

Week 12 예정:
- risk_router: /v2/risk/* (리스크 분석)
- comparison_router: /v2/llm/* (LLM 비교)
"""

from apps.ai_service.routers.v2.rag import router as rag_router

__all__ = ["rag_router"]
