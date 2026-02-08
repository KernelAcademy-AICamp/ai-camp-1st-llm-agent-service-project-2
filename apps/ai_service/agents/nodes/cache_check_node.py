"""
Cache Check Node

복잡도 분류 전에 캐시를 확인하여 FAST 경로로 빠르게 분기

Phase 5: Adaptive Agent - 캐싱 전략
"""

from datetime import datetime
from typing import Dict, Any
import logging

from apps.ai_service.agents.states.master_agent_state import (
    ExtendedMasterAgentState,
    StreamingEvent,
)
from apps.ai_service.agents.cache.response_cache import (
    generate_cache_key,
    get_response_cache,
)

logger = logging.getLogger(__name__)


async def cache_check_node(state: ExtendedMasterAgentState) -> Dict[str, Any]:
    """
    캐시 확인 노드

    Redis 캐시에서 응답 확인.
    캐시 히트 시 cache_hit=True, workflow_results.cached_response 설정.

    Args:
        state: ExtendedMasterAgentState

    Returns:
        업데이트할 필드 딕셔너리
    """
    user_message = state.get("user_message", "")
    user_context = state.get("user_context", {})
    attachments = state.get("attachments", [])

    organization_id = user_context.get("organization_id") if user_context else None

    # 캐시 키 생성
    cache_key = generate_cache_key(
        user_message=user_message,
        organization_id=organization_id,
        attachments=attachments,
    )

    # Redis 캐시 확인
    cache = get_response_cache()
    cached_data = await cache.get(cache_key)

    streaming_events = list(state.get("streaming_events", []))

    if cached_data:
        logger.info(f"[cache_check_node] Cache hit for key: {cache_key[:30]}...")

        cache_event = StreamingEvent(
            event="cache_hit",
            data={
                "cached": True,
                "cached_at": cached_data.get("cached_at"),
                "path": cached_data.get("path"),
            },
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(cache_event.model_dump())

        return {
            "cache_key": cache_key,
            "cache_hit": True,
            "workflow_results": {
                "cached_response": cached_data.get("response"),
                "cache_metadata": cached_data.get("metadata", {}),
            },
            "streaming_events": streaming_events,
        }
    else:
        logger.debug(f"[cache_check_node] Cache miss for key: {cache_key[:30]}...")
        return {
            "cache_key": cache_key,
            "cache_hit": False,
        }


def cache_check_node_sync(state: ExtendedMasterAgentState) -> Dict[str, Any]:
    """동기 버전"""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                cache_check_node(state)
            )
            return future.result()
    except RuntimeError:
        return asyncio.run(cache_check_node(state))
