"""
LangGraph Workflow Definitions

Phase 4 - Week 11: LangGraph 기반 워크플로우

워크플로우 목록:
- RAGWorkflow: RAG 기반 질의응답 (Checkpointing 불필요)

Week 12 예정:
- RiskWorkflow: 리스크 분석 (Checkpointing 필수)
- ComparisonWorkflow: LLM 비교 (Checkpointing 필수)
"""

# 지연 import로 순환 참조 방지
def get_rag_workflow():
    """RAG Workflow 인스턴스 반환"""
    from apps.ai_service.graphs.rag_graph import RAGWorkflow
    return RAGWorkflow()


def create_rag_workflow():
    """RAG Workflow StateGraph 생성"""
    from apps.ai_service.graphs.rag_graph import create_rag_workflow as _create
    return _create()


__all__ = ["get_rag_workflow", "create_rag_workflow"]
