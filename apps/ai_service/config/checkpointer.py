"""
LangGraph Checkpointer 설정

Phase 4 - Week 11: Checkpointing 전략

Checkpointing 적용 워크플로우 (선택적):
- Risk Analysis: Human-in-the-Loop, Iterative refinement (TTL: 7일)
- LLM Comparison: 결과 불일치 시 사용자 선택 (TTL: 1시간)
- Crawler: 장시간 실행, 재시작 복구 (TTL: 24시간)

Checkpointing 불필요:
- RAG Chatbot: 빠른 응답, 재실행 비용 낮음
- Document Analysis: 빠른 실행 (10-20초)
- Case Analysis: 빠른 실행 (10-15초)

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md - Checkpointing 전략 섹션
"""

import os
from typing import Optional
from contextlib import asynccontextmanager
from loguru import logger

# 개발 환경: MemorySaver (서버 재시작 시 삭제)
from langgraph.checkpoint.memory import MemorySaver


def get_memory_checkpointer() -> MemorySaver:
    """
    개발 환경용 메모리 기반 Checkpointer

    특징:
    - 서버 재시작 시 모든 상태 삭제
    - 빠른 읽기/쓰기
    - 설정 불필요

    Returns:
        MemorySaver 인스턴스
    """
    logger.info("Using MemorySaver (development)")
    return MemorySaver()


# Redis 환경변수
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")


async def get_redis_checkpointer():
    """
    프로덕션 환경용 Redis 기반 Checkpointer

    특징:
    - 서버 재시작에도 상태 유지
    - TTL 자동 정리
    - 분산 환경 지원

    사용법 (context manager 패턴 권장):
        async with get_redis_checkpointer() as checkpointer:
            graph = workflow.compile(checkpointer=checkpointer)
            result = await graph.ainvoke(state, config)

    Returns:
        RedisSaver 인스턴스 (async context manager)
    """
    try:
        from langgraph.checkpoint.redis import RedisSaver
        logger.info(f"Using RedisSaver (production): {REDIS_URI}")
        return RedisSaver.from_conn_string(REDIS_URI)
    except ImportError:
        logger.warning("langgraph-checkpoint-redis not installed, falling back to MemorySaver")
        return MemorySaver()
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}, falling back to MemorySaver")
        return MemorySaver()


def get_checkpointer(use_redis: bool = False) -> MemorySaver:
    """
    환경에 따른 Checkpointer 반환

    Args:
        use_redis: Redis 사용 여부 (기본: False)

    Returns:
        Checkpointer 인스턴스

    Note:
        Redis를 사용할 경우 async context manager로 사용 권장
        (get_redis_checkpointer 함수 참고)
    """
    if use_redis:
        logger.info("Redis checkpointer requested - use get_redis_checkpointer() for async context")

    # Week 11에서는 개발 환경이므로 MemorySaver 사용
    return get_memory_checkpointer()


# TTL 설정 (워크플로우별)
CHECKPOINT_TTL_CONFIG = {
    "risk_analysis": 7 * 24 * 3600,    # 7일 (전문가 검토 대기)
    "llm_comparison": 3600,             # 1시간 (사용자 선택 대기)
    "crawler": 24 * 3600,               # 24시간 (크롤링 재개)
}


def get_workflow_config(
    workflow_type: str,
    thread_id: str,
    user_id: Optional[str] = None
) -> dict:
    """
    워크플로우별 설정 생성

    Args:
        workflow_type: 워크플로우 타입 (risk_analysis, llm_comparison, crawler, rag)
        thread_id: 실행 식별자
        user_id: 사용자 ID (선택)

    Returns:
        LangGraph config dict
    """
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    # Checkpointing이 필요한 워크플로우만 TTL 설정
    if workflow_type in CHECKPOINT_TTL_CONFIG:
        config["configurable"]["checkpoint_ttl"] = CHECKPOINT_TTL_CONFIG[workflow_type]

    if user_id:
        config["configurable"]["user_id"] = user_id

    return config
