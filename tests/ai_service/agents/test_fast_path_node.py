"""
Fast Path Node 단위 테스트

Phase 2: Adaptive Agent - Fast Path 테스트
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from apps.ai_service.agents.nodes.fast_path_node import (
    fast_path_node,
    fast_path_node_sync,
    _generate_general_chat_response,
    _execute_simple_rag,
)
from apps.ai_service.agents.states.master_agent_state import (
    ExtendedMasterAgentState,
    ComplexityLevel,
)


class TestFastPathNode:
    """Fast Path 노드 테스트"""

    # =========================================================================
    # 캐시 히트 테스트
    # =========================================================================

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_response(self):
        """캐시 히트 시 캐시된 응답 반환"""
        state: ExtendedMasterAgentState = {
            "user_message": "절도죄 형량은?",
            "cache_hit": True,
            "workflow_results": {"cached_response": "절도죄의 법정형은..."},
            "streaming_events": [],
            "response_metadata": {},
            "complexity_level": "FAST",
            "complexity_confidence": 1.0,
            "complexity_reason": "캐시 히트",
            "execution_path": "fast",
        }

        result = await fast_path_node(state)

        assert result["final_response"] == "절도죄의 법정형은..."
        assert result["response_metadata"]["path"] == "fast"
        assert result["response_metadata"]["source"] == "cache"
        assert result["response_metadata"]["cached"] is True

    # =========================================================================
    # 일반 대화 테스트
    # =========================================================================

    @pytest.mark.asyncio
    @patch("apps.ai_service.agents.nodes.fast_path_node.create_llm_client")
    async def test_general_chat_uses_llm_direct(self, mock_create_llm):
        """일반 대화는 LLM 직접 응답"""
        # LLM mock 설정
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "안녕하세요! 무엇을 도와드릴까요?"
        mock_create_llm.return_value = mock_llm

        state: ExtendedMasterAgentState = {
            "user_message": "안녕하세요",
            "cache_hit": False,
            "workflow_results": {},
            "streaming_events": [],
            "response_metadata": {},
            "complexity_level": "FAST",
            "complexity_confidence": 0.95,
            "complexity_reason": "일반 대화",
            "execution_path": "fast",
        }

        result = await fast_path_node(state)

        assert result["final_response"] == "안녕하세요! 무엇을 도와드릴까요?"
        assert result["response_metadata"]["path"] == "fast"
        assert result["response_metadata"]["source"] == "llm_direct"
        assert result["response_metadata"]["category"] == "general_chat"

    @pytest.mark.asyncio
    @patch("apps.ai_service.agents.nodes.fast_path_node.create_llm_client")
    async def test_general_chat_fallback_on_error(self, mock_create_llm):
        """LLM 실패 시 폴백 응답"""
        mock_create_llm.side_effect = Exception("LLM 오류")

        response = await _generate_general_chat_response("안녕하세요")

        assert "안녕하세요" in response
        assert "도와드릴까요" in response

    # =========================================================================
    # 단순 RAG 테스트
    # =========================================================================

    @pytest.mark.asyncio
    @patch("apps.ai_service.agents.nodes.fast_path_node.is_general_chat")
    async def test_non_general_chat_triggers_rag(self, mock_is_general_chat):
        """일반 대화가 아닌 경우 RAG 실행"""
        mock_is_general_chat.return_value = False

        state: ExtendedMasterAgentState = {
            "user_message": "절도죄란?",
            "cache_hit": False,
            "workflow_results": {},
            "streaming_events": [],
            "response_metadata": {},
            "complexity_level": "FAST",
            "complexity_confidence": 0.85,
            "complexity_reason": "단순 질문",
            "execution_path": "fast",
        }

        # WorkflowExecutor가 없으므로 RAG 폴백 사용
        with patch("apps.ai_service.agents.nodes.fast_path_node._execute_simple_rag") as mock_rag:
            mock_rag.return_value = {
                "answer": "절도죄는 타인의 재물을 절취하는 범죄입니다.",
                "sources": [],
            }

            result = await fast_path_node(state)

            assert result["response_metadata"]["path"] == "fast"
            assert result["response_metadata"]["source"] == "rag"
            assert "rag_result" in result["workflow_results"]

    # =========================================================================
    # 스트리밍 이벤트 테스트
    # =========================================================================

    @pytest.mark.asyncio
    async def test_streaming_events_added(self):
        """스트리밍 이벤트가 추가되는지 확인"""
        state: ExtendedMasterAgentState = {
            "user_message": "테스트",
            "cache_hit": True,
            "workflow_results": {"cached_response": "캐시된 응답"},
            "streaming_events": [],
            "response_metadata": {},
            "complexity_level": "FAST",
            "complexity_confidence": 1.0,
            "complexity_reason": "캐시 히트",
            "execution_path": "fast",
        }

        result = await fast_path_node(state)

        events = result["streaming_events"]
        assert len(events) >= 2  # start + complete

        event_types = [e["event"] for e in events]
        assert "fast_path_start" in event_types
        assert "fast_path_complete" in event_types

    # =========================================================================
    # 동기 버전 테스트
    # =========================================================================

    def test_sync_version_works(self):
        """동기 버전 테스트"""
        state: ExtendedMasterAgentState = {
            "user_message": "테스트",
            "cache_hit": True,
            "workflow_results": {"cached_response": "캐시된 응답"},
            "streaming_events": [],
            "response_metadata": {},
            "complexity_level": "FAST",
            "complexity_confidence": 1.0,
            "complexity_reason": "캐시 히트",
            "execution_path": "fast",
        }

        result = fast_path_node_sync(state)

        assert result["final_response"] == "캐시된 응답"


class TestGenerateResponseNodeFastPathSkip:
    """Generate Response Node의 Fast Path 스킵 로직 테스트"""

    @pytest.mark.asyncio
    @patch("apps.ai_service.agents.nodes.generate_response_node.create_llm_client")
    async def test_fast_path_skips_llm(self, mock_create_llm):
        """Fast Path 응답이 이미 있으면 LLM 호출 스킵"""
        from apps.ai_service.agents.nodes.generate_response_node import generate_response_node

        state = {
            "user_message": "안녕하세요",
            "final_response": "안녕하세요! 무엇을 도와드릴까요?",
            "response_metadata": {
                "path": "fast",
                "source": "llm_direct",
            },
            "streaming_events": [],
            "workflow_results": {},
            "tool_results": {},
            "errors": [],
            "intent": None,
            "attachments": [],
        }

        result = await generate_response_node(state)

        # LLM이 호출되지 않아야 함
        mock_create_llm.assert_not_called()

        # 응답이 유지되어야 함
        assert result["final_response"] == "안녕하세요! 무엇을 도와드릴까요?"

        # complete 이벤트가 추가되어야 함
        events = result["streaming_events"]
        event_types = [e["event"] for e in events]
        assert "complete" in event_types

    @pytest.mark.asyncio
    @patch("apps.ai_service.agents.nodes.generate_response_node.create_llm_client")
    async def test_non_fast_path_calls_llm(self, mock_create_llm):
        """Fast Path가 아닌 경우 LLM 호출"""
        from apps.ai_service.agents.nodes.generate_response_node import generate_response_node

        mock_llm = MagicMock()
        mock_llm.generate.return_value = "생성된 응답입니다."
        mock_create_llm.return_value = mock_llm

        state = {
            "user_message": "계약서를 분석해줘",
            "final_response": None,
            "response_metadata": {
                "path": "medium",
                "status": "success",
            },
            "streaming_events": [],
            "workflow_results": {"document_workflow": {"summary": "계약서 요약"}},
            "tool_results": {},
            "errors": [],
            "intent": None,
            "attachments": [],
        }

        result = await generate_response_node(state)

        # LLM이 호출되어야 함
        mock_create_llm.assert_called()


class TestFastPathIntegration:
    """Fast Path 통합 테스트"""

    @pytest.mark.asyncio
    async def test_fast_path_end_to_end_cache_hit(self):
        """캐시 히트 E2E 테스트"""
        from apps.ai_service.agents.nodes.generate_response_node import generate_response_node

        # 1. Fast Path 노드 실행
        initial_state: ExtendedMasterAgentState = {
            "user_message": "절도죄 형량은?",
            "cache_hit": True,
            "workflow_results": {"cached_response": "절도죄의 법정형은 6년 이하의 징역..."},
            "streaming_events": [],
            "response_metadata": {},
            "complexity_level": "FAST",
            "complexity_confidence": 1.0,
            "complexity_reason": "캐시 히트",
            "execution_path": "fast",
        }

        fast_result = await fast_path_node(initial_state)

        # 2. Generate Response 노드 실행 (Fast Path 스킵 확인)
        with patch("apps.ai_service.agents.nodes.generate_response_node.create_llm_client") as mock_llm:
            final_result = await generate_response_node(fast_result)

            # LLM이 호출되지 않아야 함
            mock_llm.assert_not_called()

            # 최종 응답 확인
            assert final_result["final_response"] == "절도죄의 법정형은 6년 이하의 징역..."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
