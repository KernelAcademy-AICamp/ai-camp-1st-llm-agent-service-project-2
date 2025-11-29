"""
LangGraph Workflow Definitions (DEPRECATED)

⚠️ DEPRECATED: 이 모듈은 workflows/로 이동되었습니다.
하위 호환성을 위해 workflows/로 리다이렉트합니다.

Phase 4 - Week 11: LangGraph 기반 워크플로우

사용:
    # 새로운 import 경로 (권장)
    from apps.ai_service.workflows import get_rag_workflow, create_rag_workflow

    # 레거시 import 경로 (deprecated)
    from apps.ai_service.graphs import get_rag_workflow, create_rag_workflow
"""

import warnings

# workflows 모듈에서 가져오기 (리다이렉트)
from apps.ai_service.workflows import get_rag_workflow, create_rag_workflow

# Deprecation 경고
warnings.warn(
    "apps.ai_service.graphs is deprecated. "
    "Use apps.ai_service.workflows instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["get_rag_workflow", "create_rag_workflow"]
