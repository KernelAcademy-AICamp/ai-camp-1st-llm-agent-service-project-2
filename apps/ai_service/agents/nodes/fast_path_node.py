"""
Fast Path Node

FAST 경로 처리 노드:
1. 일반 대화 → LLM 직접 응답 (워크플로우 없음)
2. 캐시 히트 → 캐시된 응답 반환
3. 단순 RAG → RAG 워크플로우 1회 실행

목표 응답 시간: 1-2초
LLM 호출: 0-1회
"""

from datetime import datetime
from typing import Dict, Any, Optional
import logging

from apps.ai_service.agents.states.master_agent_state import (
    ExtendedMasterAgentState,
    StreamingEvent,
    ProgressStep,
    create_progress_event,
)
from apps.ai_service.agents.intent_classifier import is_general_chat
from libs.rag_core.llm.llm_client import create_llm_client
from apps.ai_service.config.settings import settings

logger = logging.getLogger(__name__)


# =============================================================================
# 일반 대화 응답 프롬프트
# =============================================================================

GENERAL_CHAT_PROMPT = """당신은 법률 AI 어시스턴트입니다.
사용자가 일반적인 대화(인사, 잡담 등)를 하고 있습니다.
친절하고 간결하게 응답하세요.

사용자: {user_message}

응답:"""


# =============================================================================
# Fast Path Node
# =============================================================================

async def fast_path_node(state: ExtendedMasterAgentState) -> Dict[str, Any]:
    """
    Fast Path 처리 노드

    처리 흐름:
    1. 캐시 히트 확인 → 캐시 응답 반환
    2. 일반 대화 확인 → LLM 직접 응답
    3. 그 외 → 단순 RAG 실행

    입력:
        - user_message: 사용자 메시지
        - cache_hit: 캐시 히트 여부
        - complexity_level: "FAST"

    출력:
        - final_response: 최종 응답 (설정됨)
        - response_metadata: {"path": "fast", "source": "cache|llm|rag"}
        - workflow_results: RAG 실행 시 결과

    Args:
        state: ExtendedMasterAgentState

    Returns:
        업데이트할 필드 딕셔너리
    """
    logger.info("[fast_path_node] Processing FAST path")

    user_message = state.get("user_message", "")
    cache_hit = state.get("cache_hit", False)
    cached_response = state.get("workflow_results", {}).get("cached_response")

    streaming_events = list(state.get("streaming_events", []))

    # 진행 상황 이벤트: Fast Path 시작 (25%)
    progress_start = create_progress_event(
        step=ProgressStep.EXECUTING,
        percentage=25,
        message="빠른 응답을 생성하고 있습니다...",
        execution_path="fast",
    )
    streaming_events.append(progress_start.model_dump())

    # 처리 시작 이벤트 (기존 호환성 유지)
    start_event = StreamingEvent(
        event="fast_path_start",
        data={"step": "fast_path", "message": "빠른 응답을 생성하고 있습니다..."},
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(start_event.model_dump())

    # =========================================================================
    # 1. 캐시 히트 처리
    # =========================================================================
    if cache_hit and cached_response:
        logger.info("[fast_path_node] Cache hit - returning cached response")

        # 진행 상황 이벤트: 캐시 응답 (80%)
        progress_cache = create_progress_event(
            step=ProgressStep.GENERATING,
            percentage=80,
            message="캐시된 응답을 반환합니다...",
            execution_path="fast",
            step_details={"source": "cache"},
        )
        streaming_events.append(progress_cache.model_dump())

        complete_event = StreamingEvent(
            event="fast_path_complete",
            data={"source": "cache", "cached": True},
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(complete_event.model_dump())

        return {
            "final_response": cached_response,
            "response_metadata": {
                "path": "fast",
                "source": "cache",
                "cached": True,
            },
            "streaming_events": streaming_events,
        }

    # =========================================================================
    # 2. 일반 대화 처리 (LLM 직접 응답)
    # =========================================================================
    if is_general_chat(user_message):
        logger.info("[fast_path_node] General chat - direct LLM response")

        # 진행 상황 이벤트: 응답 생성 중 (50%)
        progress_generating = create_progress_event(
            step=ProgressStep.GENERATING,
            percentage=50,
            message="응답을 생성하고 있습니다...",
            execution_path="fast",
            step_details={"source": "llm_direct"},
        )
        streaming_events.append(progress_generating.model_dump())

        response = await _generate_general_chat_response(user_message)

        # 진행 상황 이벤트: 완료 (80%)
        progress_complete = create_progress_event(
            step=ProgressStep.GENERATING,
            percentage=80,
            message="응답 생성이 완료되었습니다.",
            execution_path="fast",
            step_details={"source": "llm_direct", "category": "general_chat"},
        )
        streaming_events.append(progress_complete.model_dump())

        complete_event = StreamingEvent(
            event="fast_path_complete",
            data={"source": "llm_direct", "category": "general_chat"},
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(complete_event.model_dump())

        return {
            "final_response": response,
            "response_metadata": {
                "path": "fast",
                "source": "llm_direct",
                "category": "general_chat",
            },
            "streaming_events": streaming_events,
        }

    # =========================================================================
    # 3. 단순 RAG 처리
    # =========================================================================
    logger.info("[fast_path_node] Simple RAG query")

    # 진행 상황 이벤트: RAG 검색 중 (40%)
    progress_searching = create_progress_event(
        step=ProgressStep.SEARCHING,
        percentage=40,
        message="관련 정보를 검색하고 있습니다...",
        execution_path="fast",
        step_details={"source": "rag"},
    )
    streaming_events.append(progress_searching.model_dump())

    rag_result = await _execute_simple_rag(user_message, state)

    # 진행 상황 이벤트: RAG 완료 (70%)
    progress_rag_complete = create_progress_event(
        step=ProgressStep.EXECUTING,
        percentage=70,
        message="검색 결과를 정리하고 있습니다...",
        execution_path="fast",
        step_details={"source": "rag", "has_results": bool(rag_result)},
    )
    streaming_events.append(progress_rag_complete.model_dump())

    complete_event = StreamingEvent(
        event="fast_path_complete",
        data={"source": "rag", "has_results": bool(rag_result)},
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(complete_event.model_dump())

    return {
        "workflow_results": {"rag_result": rag_result},
        "response_metadata": {
            "path": "fast",
            "source": "rag",
        },
        "streaming_events": streaming_events,
        # final_response는 generate_response_node에서 생성
    }


def fast_path_node_sync(state: ExtendedMasterAgentState) -> Dict[str, Any]:
    """Fast Path 노드 (동기 버전)"""
    import asyncio
    return asyncio.run(fast_path_node(state))


# =============================================================================
# Helper 함수들
# =============================================================================

async def _generate_general_chat_response(user_message: str) -> str:
    """
    일반 대화에 대한 LLM 직접 응답 생성

    Args:
        user_message: 사용자 메시지

    Returns:
        LLM 응답
    """
    try:
        llm = create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            temperature=0.7,  # 대화에는 약간의 변형 허용
            max_tokens=200,   # 짧은 응답
        )

        prompt = GENERAL_CHAT_PROMPT.format(user_message=user_message)
        response = llm.generate(prompt=prompt)

        return response.strip()

    except Exception as e:
        logger.error(f"[fast_path_node] General chat response failed: {e}")
        return "안녕하세요! 무엇을 도와드릴까요?"


async def _execute_simple_rag(
    user_message: str,
    state: ExtendedMasterAgentState,
) -> Optional[Dict[str, Any]]:
    """
    단순 RAG 쿼리 실행

    Args:
        user_message: 사용자 메시지
        state: 현재 상태

    Returns:
        RAG 결과 딕셔너리
    """
    try:
        # WorkflowExecutor를 통한 RAG 실행
        from apps.ai_service.agents.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor()
        result = await executor.execute(
            workflow_name="rag_workflow",
            inputs={
                "query": user_message,
                "top_k": 3,  # 단순 RAG는 적은 결과
            }
        )

        return result

    except ImportError:
        # WorkflowExecutor가 없는 경우 (Phase 5 이전)
        logger.warning("[fast_path_node] WorkflowExecutor not available, using fallback")
        return await _execute_simple_rag_fallback(user_message)

    except Exception as e:
        logger.error(f"[fast_path_node] Simple RAG failed: {e}")
        return None


async def _execute_simple_rag_fallback(user_message: str) -> Optional[Dict[str, Any]]:
    """
    WorkflowExecutor가 없을 때 직접 RAG 실행 (폴백)

    Args:
        user_message: 사용자 메시지

    Returns:
        RAG 결과 딕셔너리
    """
    try:
        # RAG Core 직접 사용
        from libs.rag_core.embeddings.remote_embedder import RemoteEmbedder
        from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB
        from libs.rag_core.llm.llm_client import create_llm_client

        # 검색 실행
        embedder = RemoteEmbedder()
        vectordb = QdrantVectorDB()

        query_vector = embedder.embed_query(user_message)
        search_results = vectordb.search(query_vector, top_k=3)

        if not search_results:
            return {"answer": "관련 정보를 찾지 못했습니다.", "sources": []}

        # 컨텍스트 구성
        context = "\n\n".join([
            f"[{i+1}] {r.get('content', r.get('text', ''))[:500]}"
            for i, r in enumerate(search_results)
        ])

        # LLM 응답 생성
        llm = create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            temperature=0.3,
            max_tokens=500,
        )

        prompt = f"""다음 참고자료를 바탕으로 질문에 답변하세요.

## 참고자료
{context}

## 질문
{user_message}

## 답변:"""

        answer = llm.generate(prompt=prompt)

        return {
            "answer": answer,
            "sources": search_results,
        }

    except Exception as e:
        logger.error(f"[fast_path_node] RAG fallback failed: {e}")
        return None
