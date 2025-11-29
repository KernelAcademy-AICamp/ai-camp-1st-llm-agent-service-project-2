"""
Base State Definitions for LangGraph Workflows

Phase 4 - Week 11: LangGraph 기반 상태 관리
"""

from typing import TypedDict, Dict, Any, Optional
from datetime import datetime


class BaseState(TypedDict, total=False):
    """
    모든 LangGraph Workflow의 기본 상태

    공통 필드:
        - session_id: 세션 식별자
        - user_id: 사용자 식별자 (옵션)
        - created_at: 상태 생성 시간
        - updated_at: 상태 업데이트 시간
        - error: 에러 메시지 (있을 경우)
        - metadata: 추가 메타데이터
    """
    session_id: str
    user_id: Optional[str]
    created_at: str
    updated_at: str
    error: Optional[str]
    metadata: Dict[str, Any]
