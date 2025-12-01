"""
LangGraph State Definitions

Phase 4 - Week 11: LangGraph 기반 상태 관리

상태 정의:
- BaseState: 공통 상태 필드
- RAGState: RAG 워크플로우 상태
- create_initial_rag_state: RAG 상태 초기화 헬퍼

Week 12 예정:
- RiskState: 리스크 분석 상태
- ComparisonState: LLM 비교 상태
"""

from apps.ai_service.states.base import BaseState
from apps.ai_service.states.rag_state import RAGState, create_initial_rag_state

__all__ = ["BaseState", "RAGState", "create_initial_rag_state"]
