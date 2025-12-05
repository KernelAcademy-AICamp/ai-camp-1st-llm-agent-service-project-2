"""
Phase 2 테스트: 동적 도구 선택 검증

질문 유형에 따라 적절한 도구가 선택되는지 확인합니다.
"""

import sys
sys.path.insert(0, "/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2")

from apps.ai_service.agents.tools.tool_schemas import (
    select_tools_for_query,
    QUERY_TYPE_TOOLS,
    KEYWORD_TO_QUERY_TYPE,
)


def test_dynamic_tool_selection():
    """동적 도구 선택 테스트"""
    print("=" * 60)
    print("Phase 2 테스트: 동적 도구 선택")
    print("=" * 60)

    # 테스트 케이스 정의
    test_cases = [
        # 단순 질문 (일반 법률 검색으로 폴백)
        {
            "query": "안녕하세요",
            "expected_tools": ["search_legal"],
            "description": "단순 인사 → 일반 법률 검색만",
        },
        {
            "query": "오늘 날씨 어때?",
            "expected_tools": ["search_legal"],
            "description": "관련없는 질문 → 일반 법률 검색만",
        },

        # 법령 검색
        {
            "query": "민법 제750조",
            "expected_tools": ["search_statutes", "search_legal"],
            "description": "법률 조문 질문 → search_statutes",
        },
        {
            "query": "근로기준법 연차 규정",
            "expected_tools": ["search_statutes", "search_legal"],
            "description": "법률 규정 질문 → search_statutes",
        },

        # 판례 검색
        {
            "query": "명예훼손 판례 찾아줘",
            "expected_tools": ["search_precedents", "search_legal"],
            "description": "판례 검색 → search_precedents",
        },
        {
            "query": "대법원 판결 알려줘",
            "expected_tools": ["search_precedents", "search_legal"],
            "description": "대법원 판결 → search_precedents",
        },

        # 문서 분석
        {
            "query": "이 계약서 분석해줘",
            "expected_tools": ["analyze_document", "analyze_risk", "search_legal"],
            "description": "문서 분석 → analyze_document",
        },

        # 형사법
        {
            "query": "절도죄 양형 예측해줘",
            "expected_tools": ["analyze_criminal_case", "search_precedents", "search_legal"],
            "description": "형사 양형 → analyze_criminal_case",
        },

        # 리스크
        {
            "query": "리스크 평가해줘",
            "expected_tools": ["analyze_risk", "search_legal"],
            "description": "리스크 분석 → analyze_risk",
        },

        # 복합 질문
        {
            "query": "민법 판례 찾아줘",
            "expected_tools": ["search_statutes", "search_precedents", "search_legal"],
            "description": "복합 질문 → 여러 도구 선택",
        },
    ]

    passed = 0
    failed = 0

    for tc in test_cases:
        query = tc["query"]
        expected = set(tc["expected_tools"])
        description = tc["description"]

        # 도구 선택
        selected = select_tools_for_query(query)
        selected_set = set(selected)

        # 검증: 기대한 도구들이 모두 선택되었는지
        if expected.issubset(selected_set):
            print(f"\n✅ {description}")
            print(f"   질문: \"{query}\"")
            print(f"   선택된 도구: {selected}")
            passed += 1
        else:
            print(f"\n❌ {description}")
            print(f"   질문: \"{query}\"")
            print(f"   기대: {list(expected)}")
            print(f"   실제: {selected}")
            print(f"   누락: {expected - selected_set}")
            failed += 1

    # 첨부 파일 테스트
    print("\n" + "-" * 40)
    print("[첨부 파일 테스트]")
    selected_with_attachment = select_tools_for_query(
        "분석해줘",
        has_attachment=True,
    )
    if "analyze_document" in selected_with_attachment:
        print(f"✅ 첨부 파일 있음 → analyze_document 포함")
        print(f"   선택된 도구: {selected_with_attachment}")
        passed += 1
    else:
        print(f"❌ 첨부 파일 있음 → analyze_document 누락")
        failed += 1

    # 사용자 컨텍스트 테스트
    print("\n" + "-" * 40)
    print("[사용자 컨텍스트 테스트]")
    selected_with_user = select_tools_for_query(
        "내 문서 목록 보여줘",
        has_user_context=True,
    )
    if "list_user_documents" in selected_with_user:
        print(f"✅ 사용자 컨텍스트 있음 → list_user_documents 포함")
        print(f"   선택된 도구: {selected_with_user}")
        passed += 1
    else:
        print(f"❌ 사용자 컨텍스트 있음 → list_user_documents 누락")
        failed += 1

    selected_without_user = select_tools_for_query(
        "내 문서 목록 보여줘",
        has_user_context=False,
    )
    if "list_user_documents" not in selected_without_user:
        print(f"✅ 사용자 컨텍스트 없음 → list_user_documents 제외")
        print(f"   선택된 도구: {selected_without_user}")
        passed += 1
    else:
        print(f"❌ 사용자 컨텍스트 없음 → list_user_documents가 잘못 포함됨")
        failed += 1

    # 최대 도구 수 테스트
    print("\n" + "-" * 40)
    print("[최대 도구 수 테스트]")
    selected_max = select_tools_for_query(
        "민법 형법 상법 판례 계약서 분석해줘",
        max_tools=4,
    )
    if len(selected_max) <= 4:
        print(f"✅ max_tools=4 → 도구 수: {len(selected_max)}")
        print(f"   선택된 도구: {selected_max}")
        passed += 1
    else:
        print(f"❌ max_tools=4 초과 → 도구 수: {len(selected_max)}")
        failed += 1

    # 결과 요약
    print("\n" + "=" * 60)
    print(f"테스트 결과: {passed} 통과, {failed} 실패")
    print("=" * 60)

    return failed == 0


def test_keyword_coverage():
    """키워드 매핑 커버리지 테스트"""
    print("\n" + "=" * 60)
    print("키워드 매핑 커버리지")
    print("=" * 60)

    print(f"\n총 키워드 수: {len(KEYWORD_TO_QUERY_TYPE)}")
    print(f"질문 유형 수: {len(QUERY_TYPE_TOOLS)}")

    for query_type, tools in QUERY_TYPE_TOOLS.items():
        keywords = [k for k, v in KEYWORD_TO_QUERY_TYPE.items() if v == query_type]
        print(f"\n[{query_type}]")
        print(f"  도구: {tools}")
        print(f"  키워드: {keywords[:5]}{'...' if len(keywords) > 5 else ''}")


if __name__ == "__main__":
    test_keyword_coverage()
    print("\n")
    result = test_dynamic_tool_selection()

    sys.exit(0 if result else 1)
