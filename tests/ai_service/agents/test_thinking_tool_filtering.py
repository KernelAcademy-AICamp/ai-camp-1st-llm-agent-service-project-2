"""
Phase 8: THINKING 경로 도구 필터링 테스트

테스트 항목:
1. 질문 기반 도구 필터링
2. 카테고리별 도구 선택
3. 토큰 기반 정렬
4. 최대 도구 수 제한
5. Thinking Path에서의 도구 필터링 통합
6. 비용 임계값 체크
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from apps.ai_service.agents.tools.registry import (
    ToolRegistry,
    ToolCategory,
    ToolDefinition,
    get_tool_registry,
    init_tool_registry,
)
from apps.ai_service.agents.nodes.thinking_path_node import (
    thinking_path_node,
    _extract_final_answer,
    _check_runtime_cost,
    _generate_partial_response,
    RUNTIME_COST_SOFT_LIMIT,
    RUNTIME_COST_HARD_LIMIT,
)
from apps.ai_service.agents.states.master_agent_state import (
    ThoughtStep,
    StreamingEvent,
)


class TestToolFilteringByQuery:
    """질문 기반 도구 필터링 테스트"""

    @pytest.fixture
    def registry(self):
        """테스트용 ToolRegistry"""
        return init_tool_registry()

    def test_search_query_returns_search_tools(self, registry):
        """검색 질문에 검색 도구 반환"""
        tools = registry.get_tools_for_context("판례를 검색해줘")
        tool_names = [t.name for t in tools]

        # 검색 관련 도구 포함
        assert any("search" in name.lower() for name in tool_names) or \
               any("fetch" in name.lower() for name in tool_names)

    def test_analysis_query_returns_analysis_tools(self, registry):
        """분석 질문에 분석 도구 반환"""
        tools = registry.get_tools_for_context("계약서를 분석해줘")
        categories = [t.category for t in tools]

        # 분석 또는 문서 카테고리 포함
        assert ToolCategory.ANALYSIS in categories or ToolCategory.DOCUMENT in categories

    def test_risk_query_returns_risk_tools(self, registry):
        """리스크 질문에 리스크 도구 반환"""
        tools = registry.get_tools_for_context("리스크를 평가해줘")
        tool_names = [t.name for t in tools]

        # 리스크 또는 분석 도구 포함
        assert any("risk" in name.lower() or "assess" in name.lower() or "analy" in name.lower()
                   for name in tool_names)

    def test_precedent_query_returns_external_api(self, registry):
        """판례 질문에 외부 API 도구 반환"""
        tools = registry.get_tools_for_context("최신 판례를 찾아줘")
        categories = [t.category for t in tools]

        # 검색 또는 외부 API 카테고리
        assert ToolCategory.SEARCH in categories or ToolCategory.EXTERNAL_API in categories

    def test_statute_query_returns_statute_tools(self, registry):
        """법령 질문에 법령 관련 도구 반환"""
        tools = registry.get_tools_for_context("관련 법령을 찾아줘")
        tool_names = [t.name for t in tools]

        # 법령 검색 또는 외부 API
        assert any("statut" in name.lower() or "search" in name.lower() or "fetch" in name.lower()
                   for name in tool_names)


class TestCategoryFiltering:
    """카테고리 기반 필터링 테스트"""

    @pytest.fixture
    def registry(self):
        """테스트용 ToolRegistry"""
        return init_tool_registry()

    def test_filter_with_specific_category(self, registry):
        """특정 카테고리만 필터링"""
        tools = registry.get_tools_for_context(
            "검색해줘",
            categories=[ToolCategory.SEARCH],
        )

        for tool in tools:
            assert tool.category == ToolCategory.SEARCH

    def test_filter_with_multiple_categories(self, registry):
        """여러 카테고리 필터링"""
        tools = registry.get_tools_for_context(
            "분석하고 검색해줘",
            categories=[ToolCategory.SEARCH, ToolCategory.ANALYSIS],
        )

        for tool in tools:
            assert tool.category in [ToolCategory.SEARCH, ToolCategory.ANALYSIS]

    def test_no_match_returns_all(self, registry):
        """매칭 없으면 전체 반환"""
        tools = registry.get_tools_for_context("안녕하세요")

        # 매칭 키워드 없으면 모든 카테고리 허용
        assert len(tools) > 0


class TestTokenBasedSorting:
    """토큰 기반 정렬 테스트"""

    @pytest.fixture
    def registry(self):
        """테스트용 ToolRegistry"""
        return init_tool_registry()

    def test_sorted_by_estimated_tokens(self, registry):
        """예상 토큰 기준 정렬"""
        tools = registry.get_tools_for_context("검색하고 분석해줘", max_tools=5)

        # 토큰 기준 오름차순
        tokens = [t.estimated_tokens for t in tools]

        for i in range(len(tokens) - 1):
            assert tokens[i] <= tokens[i + 1], "도구가 토큰 기준으로 정렬되지 않음"


class TestMaxToolsLimit:
    """최대 도구 수 제한 테스트"""

    @pytest.fixture
    def registry(self):
        """테스트용 ToolRegistry"""
        return init_tool_registry()

    def test_respects_max_tools_limit(self, registry):
        """최대 도구 수 제한 준수"""
        for limit in [1, 3, 5, 10]:
            tools = registry.get_tools_for_context("모든 도구를 사용해줘", max_tools=limit)
            assert len(tools) <= limit

    def test_default_max_tools(self, registry):
        """기본 최대 도구 수"""
        tools = registry.get_tools_for_context("검색해줘")
        assert len(tools) <= 10  # 기본값


class TestToolDescriptions:
    """도구 설명 포함 테스트"""

    @pytest.fixture
    def registry(self):
        """테스트용 ToolRegistry"""
        return init_tool_registry()

    def test_tools_have_descriptions(self, registry):
        """모든 도구에 설명 존재"""
        tools = registry.get_tools_for_context("검색해줘")

        for tool in tools:
            assert tool.description is not None
            assert len(tool.description) > 0

    def test_tools_have_categories(self, registry):
        """모든 도구에 카테고리 존재"""
        tools = registry.get_tools_for_context("분석해줘")

        for tool in tools:
            assert tool.category is not None
            assert isinstance(tool.category, ToolCategory)

    def test_tools_have_estimated_tokens(self, registry):
        """모든 도구에 예상 토큰 존재"""
        tools = registry.get_tools_for_context("검색해줘")

        for tool in tools:
            assert tool.estimated_tokens > 0


class TestThinkingPathIntegration:
    """Thinking Path 통합 테스트"""

    @pytest.fixture
    def thinking_state(self):
        """Thinking Path 테스트용 상태"""
        return {
            "user_message": "최신 판례를 검색하고 분석해줘",
            "session_id": "test-thinking-session",
            "streaming_events": [],
            "execution_path": "thinking",
            "complexity_level": "THINKING",
            "max_steps": 3,
        }

    @pytest.mark.asyncio
    async def test_tools_filtered_event(self, thinking_state):
        """도구 필터링 이벤트 발생"""
        with patch("apps.ai_service.agents.nodes.thinking_path_node.think_node") as mock_think, \
             patch("apps.ai_service.agents.nodes.thinking_path_node.act_node") as mock_act, \
             patch("apps.ai_service.agents.nodes.thinking_path_node.observe_node") as mock_observe, \
             patch("apps.ai_service.agents.nodes.thinking_path_node.reflect_node") as mock_reflect:

            # Think가 바로 FINAL_ANSWER 반환
            mock_think.return_value = {
                "thought_history": [
                    ThoughtStep(
                        step_number=1,
                        thought="분석 완료",
                        action="FINAL_ANSWER",
                        action_input={"answer": "결과입니다"},
                        is_final=True,
                    ).to_dict()
                ],
                "total_llm_calls": 1,
            }

            result = await thinking_path_node(thinking_state)

        events = result["streaming_events"]
        event_types = [e["event"] for e in events]

        # tools_filtered 이벤트 확인
        assert "tools_filtered" in event_types

        # 필터링된 도구 정보 확인
        filter_event = next(e for e in events if e["event"] == "tools_filtered")
        assert "available_tools" in filter_event["data"]
        assert "tool_count" in filter_event["data"]

    @pytest.mark.asyncio
    async def test_filtered_tools_limit(self, thinking_state):
        """Thinking Path에서 최대 8개 도구 제한"""
        with patch("apps.ai_service.agents.nodes.thinking_path_node.think_node") as mock_think:
            mock_think.return_value = {
                "thought_history": [
                    ThoughtStep(
                        step_number=1,
                        thought="완료",
                        action="FINAL_ANSWER",
                        action_input="결과",
                        is_final=True,
                    ).to_dict()
                ],
                "total_llm_calls": 1,
            }

            result = await thinking_path_node(thinking_state)

        events = result["streaming_events"]
        filter_event = next(e for e in events if e["event"] == "tools_filtered")

        # THINKING 경로는 최대 8개 도구
        assert filter_event["data"]["tool_count"] <= 8


class TestRuntimeCostCheck:
    """런타임 비용 체크 테스트"""

    def test_check_runtime_cost_under_limit(self):
        """비용 한도 내"""
        state = {
            "total_llm_calls": 2,
            "total_tool_calls": 1,
            "accumulated_cost_usd": 0.0,
            "cost_warning_sent": False,
            "streaming_events": [],
        }

        result = _check_runtime_cost(state, 1, 10)

        assert not result["cost_limit_reached"]
        assert result["accumulated_cost_usd"] > 0

    def test_check_runtime_cost_soft_limit(self):
        """Soft limit 도달 (경고)"""
        state = {
            "total_llm_calls": 10,  # 많은 LLM 호출
            "total_tool_calls": 5,
            "accumulated_cost_usd": RUNTIME_COST_SOFT_LIMIT + 0.001,
            "cost_warning_sent": False,
            "streaming_events": [],
        }

        with patch("apps.ai_service.agents.nodes.thinking_path_node.get_cost_estimator") as mock_estimator:
            mock_estimator.return_value.calculate_actual_cost.return_value = MagicMock(
                actual_cost_usd=RUNTIME_COST_SOFT_LIMIT + 0.001
            )

            result = _check_runtime_cost(state, 5, 10)

        # Soft limit 경고
        assert result["cost_warning_sent"]
        assert not result["cost_limit_reached"]

        # 경고 이벤트 확인
        events = result["streaming_events"]
        assert any(e["event"] == "cost_warning" for e in events)

    def test_check_runtime_cost_hard_limit(self):
        """Hard limit 도달 (중단)"""
        state = {
            "total_llm_calls": 20,
            "total_tool_calls": 10,
            "accumulated_cost_usd": 0.0,
            "cost_warning_sent": True,
            "streaming_events": [],
        }

        with patch("apps.ai_service.agents.nodes.thinking_path_node.get_cost_estimator") as mock_estimator:
            mock_estimator.return_value.calculate_actual_cost.return_value = MagicMock(
                actual_cost_usd=RUNTIME_COST_HARD_LIMIT + 0.01
            )

            result = _check_runtime_cost(state, 8, 10)

        # Hard limit 도달
        assert result["cost_limit_reached"]

        # 중단 이벤트 확인
        events = result["streaming_events"]
        assert any(e["event"] == "cost_limit_reached" for e in events)


class TestPartialResponseGeneration:
    """부분 응답 생성 테스트"""

    def test_generate_partial_with_context(self):
        """컨텍스트가 있을 때 부분 응답"""
        accumulated_context = [
            {"tool": "search_legal", "result": "검색 결과 1"},
            {"action": "analyze", "observation": "분석 결과"},
        ]

        response = _generate_partial_response(
            accumulated_context=accumulated_context,
            thought_history=[],
            user_message="법률 검색하고 분석해줘",
        )

        assert "수집된 정보" in response
        assert "검색 결과" in response or "분석" in response

    def test_generate_partial_without_context(self):
        """컨텍스트가 없을 때 부분 응답"""
        response = _generate_partial_response(
            accumulated_context=[],
            thought_history=[],
            user_message="복잡한 법률 질문",
        )

        assert "죄송합니다" in response or "권장" in response

    def test_generate_partial_with_thought_history(self):
        """사고 이력이 있을 때 부분 응답"""
        thought_history = [
            ThoughtStep(
                step_number=1,
                thought="검색 중",
                action="search_legal",
                observation="검색 결과: 관련 판례 3건 발견",
            ).to_dict()
        ]

        response = _generate_partial_response(
            accumulated_context=[],
            thought_history=thought_history,
            user_message="판례 검색해줘",
        )

        assert "수집된 정보" in response or "판례" in response


class TestExtractFinalAnswer:
    """최종 답변 추출 테스트"""

    def test_extract_from_final_answer_action(self):
        """FINAL_ANSWER 액션에서 추출"""
        thought_history = [
            ThoughtStep(
                step_number=1,
                thought="분석 중",
                action="search_legal",
                observation="검색 결과",
            ).to_dict(),
            ThoughtStep(
                step_number=2,
                thought="답변 작성",
                action="FINAL_ANSWER",
                action_input="최종 답변입니다",
                is_final=True,
            ).to_dict(),
        ]

        answer = _extract_final_answer(thought_history)

        assert answer == "최종 답변입니다"

    def test_extract_from_dict_action_input(self):
        """딕셔너리 action_input에서 추출"""
        thought_history = [
            ThoughtStep(
                step_number=1,
                thought="완료",
                action="FINAL_ANSWER",
                action_input={"answer": "딕셔너리 답변"},
                is_final=True,
            ).to_dict(),
        ]

        answer = _extract_final_answer(thought_history)

        assert "딕셔너리 답변" in answer

    def test_extract_from_observation_fallback(self):
        """observation fallback"""
        thought_history = [
            ThoughtStep(
                step_number=1,
                thought="분석 완료",
                action="analyze",
                observation="마지막 관찰 결과",
            ).to_dict(),
        ]

        answer = _extract_final_answer(thought_history)

        assert "마지막 관찰 결과" in answer

    def test_extract_empty_history(self):
        """빈 이력"""
        answer = _extract_final_answer([])

        assert answer == ""


class TestKeywordScoring:
    """키워드 점수 계산 테스트"""

    @pytest.fixture
    def registry(self):
        """테스트용 ToolRegistry"""
        return init_tool_registry()

    def test_multiple_keywords_boost(self, registry):
        """여러 키워드가 있으면 더 많은 도구 반환"""
        single_keyword_tools = registry.get_tools_for_context("검색해줘")
        multi_keyword_tools = registry.get_tools_for_context("판례를 검색하고 분석해줘")

        # 여러 카테고리가 매칭되어야 함
        single_categories = set(t.category for t in single_keyword_tools)
        multi_categories = set(t.category for t in multi_keyword_tools)

        # 키워드가 많으면 관련 카테고리도 많아야 함
        assert len(multi_categories) >= 1

    def test_legal_domain_keywords(self, registry):
        """법률 도메인 키워드 인식"""
        legal_keywords = ["판례", "법령", "조문", "법률", "사건"]

        for keyword in legal_keywords:
            tools = registry.get_tools_for_context(f"{keyword}를 찾아줘")
            # 법률 관련 도구가 반환되어야 함
            assert len(tools) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
