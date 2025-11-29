"""
LangGraph Workflow Definitions

Phase 4 - Week 11~13: LangGraph 기반 워크플로우

포함 워크플로우:
- RAG Workflow (Week 11)
- Crawler Workflow (Week 13, Checkpointing 필수)

사용:
    from apps.ai_service.graphs import RAGWorkflow, CrawlerWorkflow
"""

# RAG Workflow (rag_graph.py)
from apps.ai_service.graphs.rag_graph import RAGWorkflow, create_rag_workflow

# Crawler Workflow (crawler_graph.py) - Week 13
from apps.ai_service.graphs.crawler_graph import (
    CrawlerWorkflow,
    create_crawler_workflow,
    fetch_node,
    parse_node,
    validate_node,
    store_node,
    retry_node,
)

__all__ = [
    # RAG Workflow
    "RAGWorkflow",
    "create_rag_workflow",
    # Crawler Workflow (Week 13)
    "CrawlerWorkflow",
    "create_crawler_workflow",
    "fetch_node",
    "parse_node",
    "validate_node",
    "store_node",
    "retry_node",
]


# Legacy compatibility (deprecated)
def get_rag_workflow():
    """DEPRECATED: Use RAGWorkflow directly"""
    import warnings
    warnings.warn(
        "get_rag_workflow is deprecated. Use RAGWorkflow() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return RAGWorkflow()
