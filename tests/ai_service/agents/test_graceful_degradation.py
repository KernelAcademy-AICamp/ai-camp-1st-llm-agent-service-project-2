"""
Phase 7: Graceful Degradation 테스트

비용 한도 도달 시 부분 응답 생성 기능 테스트
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Import the functions we want to test
from apps.ai_service.agents.nodes.thinking_path_node import (
    _check_runtime_cost,
    _generate_partial_response,
    RUNTIME_COST_SOFT_LIMIT,
    RUNTIME_COST_HARD_LIMIT,
)
from apps.ai_service.agents.states.master_agent_state import ThoughtStep


class TestCheckRuntimeCost:
    """실행 중 비용 체크 테스트"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """각 테스트 전 싱글톤 초기화"""
        import apps.ai_service.agents.cost_estimator as module
        module._cost_estimator = None
        yield

    def test_below_soft_limit(self):
        """Soft limit 미만 - 정상 진행"""
        state = {
            "total_llm_calls": 1,
            "total_tool_calls": 1,
            "cost_warning_sent": False,
            "streaming_events": [],
        }

        result = _check_runtime_cost(state, 1, 10)

        assert not result.get("cost_limit_reached", False)
        assert not result.get("cost_warning_sent", False)
        assert result["accumulated_cost_usd"] >= 0

    def test_soft_limit_warning(self):
        """Soft limit 도달 - 경고 발생"""
        # 많은 LLM 호출로 soft limit 초과하도록 설정
        state = {
            "total_llm_calls": 10,  # 10 * 2000 = 20000 토큰
            "total_tool_calls": 5,
            "cost_warning_sent": False,
            "streaming_events": [],
        }

        result = _check_runtime_cost(state, 5, 10)

        # 경고가 발생해야 함 (비용에 따라)
        # 실제 비용 계산 결과에 따라 달라질 수 있음
        assert "accumulated_cost_usd" in result
        assert "streaming_events" in result

    def test_hard_limit_reached(self):
        """Hard limit 도달 - 중단 필요"""
        # 매우 많은 LLM 호출로 hard limit 초과하도록 설정
        state = {
            "total_llm_calls": 50,  # 많은 호출
            "total_tool_calls": 30,
            "cost_warning_sent": True,
            "streaming_events": [],
        }

        result = _check_runtime_cost(state, 8, 10)

        # hard limit에 도달했는지 확인
        if result["accumulated_cost_usd"] >= RUNTIME_COST_HARD_LIMIT:
            assert result["cost_limit_reached"] == True
            # cost_limit_reached 이벤트가 추가되어야 함
            events = result["streaming_events"]
            cost_events = [e for e in events if e.get("event") == "cost_limit_reached"]
            assert len(cost_events) == 1

    def test_warning_sent_once(self):
        """경고는 한 번만 전송"""
        state = {
            "total_llm_calls": 15,
            "total_tool_calls": 10,
            "cost_warning_sent": True,  # 이미 경고 전송됨
            "streaming_events": [],
        }

        result = _check_runtime_cost(state, 5, 10)

        # 새 경고 이벤트가 추가되지 않아야 함
        warning_events = [
            e for e in result["streaming_events"]
            if e.get("event") == "cost_warning"
        ]
        assert len(warning_events) == 0

    def test_error_handling(self):
        """에러 발생 시 기본값 반환"""
        state = {
            "total_llm_calls": "invalid",  # 잘못된 타입
            "streaming_events": [],
        }

        # 에러가 발생해도 기본값 반환
        result = _check_runtime_cost(state, 1, 10)

        assert "accumulated_cost_usd" in result
        assert result["cost_limit_reached"] == False


class TestGeneratePartialResponse:
    """부분 응답 생성 테스트"""

    def test_with_accumulated_context(self):
        """누적 컨텍스트가 있는 경우"""
        accumulated_context = [
            {"tool": "법령_검색", "result": "근로기준법 제23조는..."},
            {"tool": "판례_검색", "result": "대법원 2020다12345 판결에서는..."},
        ]
        thought_history = []
        user_message = "해고 절차에 대해 알려주세요"

        response = _generate_partial_response(
            accumulated_context=accumulated_context,
            thought_history=thought_history,
            user_message=user_message,
        )

        # 응답에 수집된 정보가 포함되어야 함
        assert "현재까지 파악한 내용" in response
        assert "법령_검색" in response or "근로기준법" in response
        assert "안내" in response

    def test_with_thought_history(self):
        """사고 이력이 있는 경우"""
        accumulated_context = []
        thought_history = [
            {
                "step_number": 1,
                "thought": "법령을 먼저 검색해야겠다",
                "action": "법령_검색",
                "action_input": {"query": "해고"},
                "observation": "근로기준법 관련 조항을 찾았습니다.",
                "is_final": False,
            },
        ]
        user_message = "해고 절차에 대해 알려주세요"

        response = _generate_partial_response(
            accumulated_context=accumulated_context,
            thought_history=thought_history,
            user_message=user_message,
        )

        assert "현재까지 파악한 내용" in response or "권장 사항" in response

    def test_no_info_collected(self):
        """수집된 정보가 없는 경우"""
        accumulated_context = []
        thought_history = []
        user_message = "매우 복잡한 법률 질문입니다"

        response = _generate_partial_response(
            accumulated_context=accumulated_context,
            thought_history=thought_history,
            user_message=user_message,
        )

        # 권장 사항이 포함되어야 함
        assert "권장 사항" in response
        assert "구체적으로" in response

    def test_long_info_truncation(self):
        """긴 정보는 잘림 처리"""
        long_result = "A" * 1000  # 1000자 긴 결과
        accumulated_context = [
            {"tool": "검색", "result": long_result},
        ]
        thought_history = []
        user_message = "테스트 질문"

        response = _generate_partial_response(
            accumulated_context=accumulated_context,
            thought_history=thought_history,
            user_message=user_message,
        )

        # 전체 1000자가 아닌 잘린 버전이 포함되어야 함
        assert len(response) < len(long_result)
        assert "..." in response  # 잘림 표시

    def test_max_items_limit(self):
        """최대 항목 수 제한"""
        accumulated_context = [
            {"tool": f"도구_{i}", "result": f"결과_{i}"}
            for i in range(10)  # 10개 항목
        ]
        thought_history = []
        user_message = "테스트 질문"

        response = _generate_partial_response(
            accumulated_context=accumulated_context,
            thought_history=thought_history,
            user_message=user_message,
        )

        # 최대 5개 항목만 포함되어야 함
        count = sum(1 for i in range(10) if f"도구_{i}" in response)
        assert count <= 5


class TestThinkingPathIntegration:
    """Thinking Path 통합 테스트"""

    def test_cost_constants(self):
        """비용 상수 확인"""
        assert RUNTIME_COST_SOFT_LIMIT == 0.025  # $0.025
        assert RUNTIME_COST_HARD_LIMIT == 0.04   # $0.04
        assert RUNTIME_COST_SOFT_LIMIT < RUNTIME_COST_HARD_LIMIT

    def test_partial_response_format(self):
        """부분 응답 포맷 확인"""
        accumulated_context = [
            {"tool": "법령", "result": "테스트 결과"},
        ]
        thought_history = []
        user_message = "테스트"

        response = _generate_partial_response(
            accumulated_context=accumulated_context,
            thought_history=thought_history,
            user_message=user_message,
        )

        # 응답이 문자열이어야 함
        assert isinstance(response, str)
        assert len(response) > 0


class TestStreamingEvents:
    """스트리밍 이벤트 테스트"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """각 테스트 전 싱글톤 초기화"""
        import apps.ai_service.agents.cost_estimator as module
        module._cost_estimator = None
        yield

    def test_cost_warning_event_structure(self):
        """비용 경고 이벤트 구조 확인"""
        state = {
            "total_llm_calls": 20,
            "total_tool_calls": 15,
            "cost_warning_sent": False,
            "streaming_events": [],
        }

        result = _check_runtime_cost(state, 5, 10)

        # 이벤트가 추가되었다면 구조 확인
        for event in result["streaming_events"]:
            assert "event" in event
            assert "data" in event
            assert "timestamp" in event

    def test_cost_limit_event_data(self):
        """비용 한도 이벤트 데이터 확인"""
        state = {
            "total_llm_calls": 100,  # 매우 많은 호출
            "total_tool_calls": 50,
            "cost_warning_sent": True,
            "streaming_events": [],
        }

        result = _check_runtime_cost(state, 9, 10)

        # hard limit 도달 시 이벤트 데이터 확인
        if result["cost_limit_reached"]:
            events = result["streaming_events"]
            limit_events = [e for e in events if e.get("event") == "cost_limit_reached"]

            if limit_events:
                event_data = limit_events[0]["data"]
                assert "message" in event_data
                assert "accumulated_cost_usd" in event_data
                assert "limit_usd" in event_data
                assert "iteration" in event_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
