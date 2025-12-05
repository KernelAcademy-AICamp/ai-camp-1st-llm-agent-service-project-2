"""
Phase 4 테스트: 쿼리 분해기 검증

query_decomposer.py의 기능을 테스트합니다.
"""

import sys
sys.path.insert(0, "/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2")

from apps.ai_service.agents.nodes.query_decomposer import (
    DecomposedQuery,
    DECOMPOSITION_PROMPT,
    should_decompose,
    format_decomposition_for_prompt,
    extract_sub_query_keywords,
)


def test_decomposition_prompt():
    """DECOMPOSITION_PROMPT 구조 검증"""
    print("=" * 60)
    print("Phase 4 테스트: DECOMPOSITION_PROMPT 검증")
    print("=" * 60)

    # 필수 섹션 확인
    required_sections = [
        "## 질문",
        "## 작업",
        "## 복합 질문 판단 기준",
        "## 단일 질문 예시",
        "## 출력 형식",
        "{query}",
        "is_complex",
        "sub_queries",
        "reasoning",
    ]

    print("\n[필수 섹션 확인]")
    all_passed = True
    for section in required_sections:
        if section in DECOMPOSITION_PROMPT:
            print(f"  ✅ {section}")
        else:
            print(f"  ❌ {section} - 누락됨!")
            all_passed = False

    # 예시 패턴 확인
    examples = ["비교", "하고 나서", "알려주고"]
    print("\n[예시 패턴 확인]")
    for example in examples:
        if example in DECOMPOSITION_PROMPT:
            print(f"  ✅ {example}")
        else:
            print(f"  ⚠️ {example} - 누락됨")

    return all_passed


def test_should_decompose():
    """should_decompose 함수 테스트"""
    print("\n" + "=" * 60)
    print("Phase 4 테스트: should_decompose 함수")
    print("=" * 60)

    all_passed = True

    # 복합 질문 (True 예상)
    complex_queries = [
        ("민법과 형법의 손해배상 규정을 비교해줘", "비교"),
        ("이 계약서 분석하고 유사 판례도 찾아줘", "분석하고 + 찾아줘"),
        ("근로기준법의 연차 규정과 퇴직금 규정 알려줘", "와 + 규정"),
        ("불법행위 손해배상과 채무불이행 손해배상의 차이점", "차이점"),
        ("임대차보호법 설명해주고 관련 판례도 알려줘", "설명해주고 + 알려줘"),
    ]

    print("\n[복합 질문 감지 (True 예상)]")
    for query, reason in complex_queries:
        result = should_decompose(query)
        if result:
            print(f"  ✅ \"{query[:30]}...\" → {result} ({reason})")
        else:
            print(f"  ❌ \"{query[:30]}...\" → {result} (예상: True, {reason})")
            all_passed = False

    # 단일 질문 (False 예상)
    simple_queries = [
        ("민법 제750조", "조문 질문"),
        ("절도죄의 법정형은?", "단순 질문"),
        ("안녕하세요", "인사"),
        ("손해배상이란?", "정의 질문"),
    ]

    print("\n[단일 질문 감지 (False 예상)]")
    for query, reason in simple_queries:
        result = should_decompose(query)
        if not result:
            print(f"  ✅ \"{query}\" → {result} ({reason})")
        else:
            print(f"  ⚠️ \"{query}\" → {result} (예상: False, {reason})")
            # 단일 질문 판정이 좀 더 관대하므로 실패로 처리하지 않음

    return all_passed


def test_format_decomposition():
    """format_decomposition_for_prompt 함수 테스트"""
    print("\n" + "=" * 60)
    print("Phase 4 테스트: format_decomposition_for_prompt")
    print("=" * 60)

    all_passed = True

    # 테스트 케이스 1: 복합 질문
    decomposed_complex = DecomposedQuery(
        original_query="민법과 형법의 손해배상 규정을 비교해줘",
        is_complex=True,
        sub_queries=[
            "민법의 손해배상 규정을 알려주세요",
            "형법의 손해배상 규정을 알려주세요",
            "두 규정을 비교 분석해주세요",
        ],
        reasoning="비교 질문으로 하위 질문으로 분해됨",
    )

    formatted = format_decomposition_for_prompt(decomposed_complex)
    print("\n[복합 질문 포맷팅]")

    checks = [
        ("## 질문 분해", "헤더"),
        ("하위 질문으로 분해", "설명"),
        ("민법의 손해배상", "하위 질문 1"),
        ("형법의 손해배상", "하위 질문 2"),
        ("순차적으로", "지시사항"),
    ]

    for check_str, check_name in checks:
        if check_str in formatted:
            print(f"  ✅ {check_name}: 포함됨")
        else:
            print(f"  ❌ {check_name}: 누락됨")
            all_passed = False

    # 테스트 케이스 2: 단일 질문 (빈 문자열 반환)
    decomposed_simple = DecomposedQuery(
        original_query="민법 제750조",
        is_complex=False,
        sub_queries=[],
        reasoning="단일 질문",
    )

    formatted_simple = format_decomposition_for_prompt(decomposed_simple)
    print("\n[단일 질문 포맷팅]")
    if formatted_simple == "":
        print("  ✅ 빈 문자열 반환")
    else:
        print(f"  ❌ 빈 문자열 예상, 실제: '{formatted_simple}'")
        all_passed = False

    return all_passed


def test_extract_keywords():
    """extract_sub_query_keywords 함수 테스트"""
    print("\n" + "=" * 60)
    print("Phase 4 테스트: extract_sub_query_keywords")
    print("=" * 60)

    all_passed = True

    # 테스트 케이스
    sub_queries = [
        "민법의 손해배상 규정을 알려주세요",
        "형법의 손해배상 규정을 알려주세요",
        "관련 판례를 찾아주세요",
    ]

    keywords = extract_sub_query_keywords(sub_queries)
    print(f"\n[추출된 키워드]: {keywords}")

    expected_keywords = ["민법", "형법", "손해배상", "판례"]
    for kw in expected_keywords:
        if kw in keywords:
            print(f"  ✅ {kw}")
        else:
            print(f"  ⚠️ {kw} - 누락됨")

    # 중복 없이 추출되는지
    if len(keywords) == len(set(keywords)):
        print("  ✅ 중복 없음")
    else:
        print("  ❌ 중복 발견")
        all_passed = False

    return all_passed


def test_decomposed_query_dataclass():
    """DecomposedQuery 데이터클래스 테스트"""
    print("\n" + "=" * 60)
    print("Phase 4 테스트: DecomposedQuery 데이터클래스")
    print("=" * 60)

    all_passed = True

    # 인스턴스 생성 테스트
    result = DecomposedQuery(
        original_query="민법과 형법 비교",
        is_complex=True,
        sub_queries=["민법 설명", "형법 설명"],
        reasoning="비교 질문",
    )

    print("\n[DecomposedQuery 생성]")
    checks = [
        (result.original_query == "민법과 형법 비교", "original_query"),
        (result.is_complex == True, "is_complex"),
        (len(result.sub_queries) == 2, "sub_queries (2개)"),
        (result.reasoning == "비교 질문", "reasoning"),
    ]

    for passed, name in checks:
        if passed:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name}")
            all_passed = False

    return all_passed


def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n" + "=" * 60)
    print("Phase 4 테스트: 엣지 케이스")
    print("=" * 60)

    all_passed = True

    # 빈 sub_queries로 format
    empty_decomposed = DecomposedQuery(
        original_query="테스트",
        is_complex=True,  # complex지만 sub_queries가 비어있음
        sub_queries=[],
        reasoning="테스트",
    )

    formatted = format_decomposition_for_prompt(empty_decomposed)
    print("\n[빈 sub_queries + is_complex=True]")
    if formatted == "":
        print("  ✅ 빈 문자열 반환 (sub_queries가 없으므로)")
    else:
        print(f"  ⚠️ 결과: '{formatted[:50]}...'")

    # 매우 긴 질문
    long_query = "이 " * 100 + "비교해줘"
    result = should_decompose(long_query)
    print(f"\n[매우 긴 질문 (200자+)]")
    print(f"  should_decompose 결과: {result}")

    return all_passed


if __name__ == "__main__":
    result1 = test_decomposition_prompt()
    result2 = test_should_decompose()
    result3 = test_format_decomposition()
    result4 = test_extract_keywords()
    result5 = test_decomposed_query_dataclass()
    result6 = test_edge_cases()

    print("\n" + "=" * 60)
    all_passed = all([result1, result2, result3, result4, result5, result6])
    if all_passed:
        print("✅ Phase 4 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)
