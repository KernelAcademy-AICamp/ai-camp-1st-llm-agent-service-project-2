"""
Phase 5 테스트: 응답 종합기 검증

SYNTHESIS_PROMPT와 _format_tool_results_for_synthesis 함수를 테스트합니다.
"""

import sys
sys.path.insert(0, "/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2")

from apps.ai_service.agents.nodes.tool_use_agent_node import (
    SYNTHESIS_PROMPT,
    _format_tool_results_for_synthesis,
)


def test_synthesis_prompt():
    """SYNTHESIS_PROMPT 구조 검증"""
    print("=" * 60)
    print("Phase 5 테스트: SYNTHESIS_PROMPT 검증")
    print("=" * 60)

    # 필수 섹션 확인
    required_sections = [
        "## 원래 질문",
        "## 수집된 정보",
        "## 작업",
        "## 답변 작성 원칙",
        "## 출력",
        "{query}",
        "{tool_results}",
    ]

    print("\n[필수 섹션 확인]")
    all_passed = True
    for section in required_sections:
        if section in SYNTHESIS_PROMPT:
            print(f"  ✅ {section}")
        else:
            print(f"  ❌ {section} - 누락됨!")
            all_passed = False

    # 원칙 확인
    principles = ["구조화", "종합", "명확성", "출처 명시", "한계 인정"]
    print("\n[답변 작성 원칙 확인]")
    for p in principles:
        if p in SYNTHESIS_PROMPT:
            print(f"  ✅ {p}")
        else:
            print(f"  ❌ {p} - 누락됨!")
            all_passed = False

    return all_passed


def test_format_tool_results():
    """_format_tool_results_for_synthesis 함수 테스트"""
    print("\n" + "=" * 60)
    print("Phase 5 테스트: 도구 결과 포맷팅")
    print("=" * 60)

    all_passed = True

    # 테스트 케이스 1: 검색 도구 결과
    search_results = [
        {
            "tool_name": "search_legal",
            "result": {
                "success": True,
                "data": {
                    "answer": "민법 제750조는 불법행위로 인한 손해배상에 관한 규정입니다.",
                    "sources": [
                        {"title": "민법 제750조", "text": "고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는 그 손해를 배상할 책임이 있다."},
                        {"title": "대법원 2020다12345", "text": "불법행위 성립요건에 관한 판례...", "score": 0.85},
                    ],
                },
            },
        },
    ]

    formatted = _format_tool_results_for_synthesis(search_results)
    print("\n[검색 도구 결과 포맷팅]")

    checks = [
        ("### search_legal 결과", "도구 이름 헤더"),
        ("**요약**:", "요약 섹션"),
        ("**출처**:", "출처 섹션"),
        ("민법 제750조", "출처 제목"),
    ]

    for check_str, check_name in checks:
        if check_str in formatted:
            print(f"  ✅ {check_name}: 포함됨")
        else:
            print(f"  ❌ {check_name}: 누락됨")
            all_passed = False

    # 테스트 케이스 2: 분석 도구 결과
    analysis_results = [
        {
            "tool_name": "analyze_document",
            "result": {
                "success": True,
                "data": {
                    "summary": "이 계약서는 서비스 이용 계약으로, 계약 기간은 1년입니다.",
                    "risks": [
                        {"description": "해지 조건이 불명확함"},
                        {"description": "위약금 조항이 과도함"},
                    ],
                },
            },
        },
    ]

    formatted_analysis = _format_tool_results_for_synthesis(analysis_results)
    print("\n[분석 도구 결과 포맷팅]")

    analysis_checks = [
        ("### analyze_document 결과", "도구 이름 헤더"),
        ("**분석 결과**:", "분석 결과 섹션"),
        ("**식별된 항목**:", "리스크 항목 섹션"),
    ]

    for check_str, check_name in analysis_checks:
        if check_str in formatted_analysis:
            print(f"  ✅ {check_name}: 포함됨")
        else:
            print(f"  ❌ {check_name}: 누락됨")
            all_passed = False

    # 테스트 케이스 3: 실패한 도구 결과
    failed_results = [
        {
            "tool_name": "search_precedents",
            "result": {
                "success": False,
                "error": "검색 결과 없음",
            },
        },
    ]

    formatted_failed = _format_tool_results_for_synthesis(failed_results)
    print("\n[실패한 도구 결과 포맷팅]")

    if "(실패)" in formatted_failed and "검색 결과 없음" in formatted_failed:
        print("  ✅ 실패 상태 및 오류 메시지 포함")
    else:
        print("  ❌ 실패 정보 누락")
        all_passed = False

    # 테스트 케이스 4: 최대 길이 제한
    long_results = []
    for i in range(10):
        long_results.append({
            "tool_name": f"tool_{i}",
            "result": {
                "success": True,
                "data": {"content": "x" * 500},
            },
        })

    formatted_long = _format_tool_results_for_synthesis(long_results, max_chars=2000)
    print("\n[최대 길이 제한 테스트]")

    if len(formatted_long) <= 2500:  # 약간의 여유
        print(f"  ✅ 길이 제한 적용됨: {len(formatted_long)} chars")
    else:
        print(f"  ❌ 길이 제한 초과: {len(formatted_long)} chars")
        all_passed = False

    if "생략" in formatted_long:
        print("  ✅ 생략 메시지 포함")
    else:
        print("  ⚠️ 생략 메시지 없음 (길이가 충분히 짧을 수 있음)")

    # 테스트 케이스 5: 빈 결과
    empty_results = []
    formatted_empty = _format_tool_results_for_synthesis(empty_results)
    print("\n[빈 결과 포맷팅]")

    if formatted_empty == "":
        print("  ✅ 빈 문자열 반환")
    else:
        print(f"  ⚠️ 빈 결과에 대해: '{formatted_empty}'")

    return all_passed


def test_format_output():
    """포맷팅 결과 출력"""
    print("\n" + "=" * 60)
    print("포맷팅 결과 샘플")
    print("=" * 60)

    sample_results = [
        {
            "tool_name": "search_legal",
            "result": {
                "success": True,
                "data": {
                    "answer": "근로기준법에 따르면 연차휴가는 1년간 80% 이상 출근한 근로자에게 15일의 유급휴가가 주어집니다.",
                    "sources": [
                        {"title": "근로기준법 제60조", "text": "사용자는 1년간 80퍼센트 이상 출근한 근로자에게 15일의 유급휴가를 주어야 한다.", "score": 0.92},
                        {"title": "대법원 2019다56789", "text": "연차휴가 산정 기준에 관한 판결...", "score": 0.78},
                    ],
                },
            },
        },
    ]

    formatted = _format_tool_results_for_synthesis(sample_results)
    print(formatted)


if __name__ == "__main__":
    result1 = test_synthesis_prompt()
    result2 = test_format_tool_results()
    test_format_output()

    print("\n" + "=" * 60)
    if result1 and result2:
        print("✅ Phase 5 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 60)

    sys.exit(0 if (result1 and result2) else 1)
