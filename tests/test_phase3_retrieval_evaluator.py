"""
Phase 3 테스트: 검색 결과 평가기 검증

retrieval_evaluator.py의 기능을 테스트합니다.
"""

import sys
sys.path.insert(0, "/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2")

from apps.ai_service.agents.nodes.retrieval_evaluator import (
    EvaluationResult,
    EVALUATION_PROMPT,
    _format_results,
    _generate_alternative_query,
    quick_evaluate,
)


def test_evaluation_prompt():
    """EVALUATION_PROMPT 구조 검증"""
    print("=" * 60)
    print("Phase 3 테스트: EVALUATION_PROMPT 검증")
    print("=" * 60)

    # 필수 섹션 확인
    required_sections = [
        "## 원래 질문",
        "## 검색 결과",
        "## 평가 기준",
        "관련성 (Relevance)",
        "완전성 (Completeness)",
        "## 출력 형식",
        "{query}",
        "{results}",
    ]

    print("\n[필수 섹션 확인]")
    all_passed = True
    for section in required_sections:
        if section in EVALUATION_PROMPT:
            print(f"  ✅ {section}")
        else:
            print(f"  ❌ {section} - 누락됨!")
            all_passed = False

    # 권장 행동 확인
    actions = ["use", "retry", "expand", "different_tool"]
    print("\n[권장 행동 확인]")
    for action in actions:
        if action in EVALUATION_PROMPT:
            print(f"  ✅ {action}")
        else:
            print(f"  ❌ {action} - 누락됨!")
            all_passed = False

    return all_passed


def test_format_results():
    """_format_results 함수 테스트"""
    print("\n" + "=" * 60)
    print("Phase 3 테스트: 결과 포맷팅")
    print("=" * 60)

    all_passed = True

    # 테스트 케이스 1: 일반적인 검색 결과
    normal_results = [
        {
            "title": "민법 제750조",
            "text": "고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는 그 손해를 배상할 책임이 있다.",
            "score": 0.92,
        },
        {
            "title": "대법원 2020다12345",
            "content": "불법행위 손해배상 청구 사건...",
            "relevance_score": 0.85,
        },
    ]

    formatted = _format_results(normal_results)
    print("\n[일반 결과 포맷팅]")

    checks = [
        ("민법 제750조", "제목 포함"),
        ("0.92", "점수 포함"),
        ("고의 또는 과실", "텍스트 포함"),
        ("대법원", "두 번째 결과"),
    ]

    for check_str, check_name in checks:
        if check_str in formatted:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}: 누락됨")
            all_passed = False

    # 테스트 케이스 2: 빈 결과
    empty_results = []
    formatted_empty = _format_results(empty_results)
    print("\n[빈 결과 포맷팅]")
    if "없음" in formatted_empty:
        print("  ✅ 빈 결과 메시지 반환")
    else:
        print(f"  ⚠️ 빈 결과: '{formatted_empty}'")

    # 테스트 케이스 3: 최대 길이 제한
    long_results = [
        {"text": "x" * 1000, "score": 0.9} for _ in range(10)
    ]
    formatted_long = _format_results(long_results, max_chars=1000)
    print("\n[길이 제한 테스트]")
    if len(formatted_long) <= 1200:  # 약간의 여유
        print(f"  ✅ 길이 제한 적용: {len(formatted_long)} chars")
    else:
        print(f"  ❌ 길이 제한 초과: {len(formatted_long)} chars")
        all_passed = False

    return all_passed


def test_alternative_query():
    """_generate_alternative_query 함수 테스트"""
    print("\n" + "=" * 60)
    print("Phase 3 테스트: 대안 쿼리 생성")
    print("=" * 60)

    all_passed = True

    test_cases = [
        # (원래 쿼리, 설명)
        ("손해배상", "짧은 쿼리"),
        ("민법 제750조에 따른 불법행위로 인한 손해배상 청구의 요건과 효과에 대해 설명해주세요. 특히 고의와 과실의 구별 기준이 궁금합니다.", "긴 쿼리"),
        ("판례", "매우 짧은 쿼리"),
    ]

    print("\n[대안 쿼리 생성]")
    for query, desc in test_cases:
        alt = _generate_alternative_query(query)
        print(f"  [{desc}]")
        print(f"    원본: {query[:50]}{'...' if len(query) > 50 else ''}")
        print(f"    대안: {alt}")

        # 긴 쿼리는 줄어들어야 함
        if len(query) > 50 and len(alt) <= 50:
            print(f"    ✅ 길이 제한 적용")
        elif len(query) <= 50:
            print(f"    ✅ 적절한 처리")
        else:
            print(f"    ⚠️ 길이 제한 미적용")

    return all_passed


def test_quick_evaluate():
    """quick_evaluate 함수 테스트"""
    print("\n" + "=" * 60)
    print("Phase 3 테스트: 빠른 평가")
    print("=" * 60)

    all_passed = True

    # 테스트 케이스 1: 높은 점수 결과
    high_score_results = [
        {"text": "결과 1", "score": 0.9},
        {"text": "결과 2", "score": 0.85},
        {"text": "결과 3", "score": 0.8},
    ]

    result = quick_evaluate(high_score_results, min_score=0.5)
    print("\n[높은 점수 결과]")
    if result:
        print("  ✅ True 반환 (예상대로)")
    else:
        print("  ❌ False 반환 (높은 점수인데)")
        all_passed = False

    # 테스트 케이스 2: 낮은 점수 결과
    low_score_results = [
        {"text": "결과 1", "score": 0.3},
        {"text": "결과 2", "score": 0.2},
    ]

    result = quick_evaluate(low_score_results, min_score=0.5)
    print("\n[낮은 점수 결과]")
    if not result:
        print("  ✅ False 반환 (예상대로)")
    else:
        print("  ❌ True 반환 (낮은 점수인데)")
        all_passed = False

    # 테스트 케이스 3: 빈 결과
    result = quick_evaluate([], min_score=0.5)
    print("\n[빈 결과]")
    if not result:
        print("  ✅ False 반환 (예상대로)")
    else:
        print("  ❌ True 반환 (빈 결과인데)")
        all_passed = False

    # 테스트 케이스 4: 점수 정보 없는 결과
    no_score_results = [
        {"text": "결과 1"},
        {"text": "결과 2"},
    ]

    result = quick_evaluate(no_score_results, min_score=0.5)
    print("\n[점수 없는 결과]")
    if result:
        print("  ✅ True 반환 (점수 없으면 일단 사용)")
    else:
        print("  ⚠️ False 반환")

    return all_passed


def test_evaluation_result_dataclass():
    """EvaluationResult 데이터클래스 테스트"""
    print("\n" + "=" * 60)
    print("Phase 3 테스트: EvaluationResult 데이터클래스")
    print("=" * 60)

    all_passed = True

    # 인스턴스 생성 테스트
    result = EvaluationResult(
        is_relevant=True,
        is_sufficient=True,
        relevance_score=0.85,
        completeness_score=0.78,
        reasoning="검색 결과가 질문과 관련이 높습니다.",
        suggested_action="use",
        suggested_query=None,
    )

    print("\n[EvaluationResult 생성]")
    checks = [
        (result.is_relevant == True, "is_relevant"),
        (result.relevance_score == 0.85, "relevance_score"),
        (result.completeness_score == 0.78, "completeness_score"),
        (result.suggested_action == "use", "suggested_action"),
        (result.suggested_query is None, "suggested_query (None)"),
    ]

    for passed, name in checks:
        if passed:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name}")
            all_passed = False

    # suggested_query 있는 경우
    result_with_query = EvaluationResult(
        is_relevant=False,
        is_sufficient=False,
        relevance_score=0.2,
        completeness_score=0.1,
        reasoning="검색 결과가 부족합니다.",
        suggested_action="retry",
        suggested_query="민법 불법행위 손해배상",
    )

    print("\n[suggested_query 있는 경우]")
    if result_with_query.suggested_query == "민법 불법행위 손해배상":
        print("  ✅ suggested_query 설정됨")
    else:
        print("  ❌ suggested_query 설정 실패")
        all_passed = False

    return all_passed


if __name__ == "__main__":
    result1 = test_evaluation_prompt()
    result2 = test_format_results()
    result3 = test_alternative_query()
    result4 = test_quick_evaluate()
    result5 = test_evaluation_result_dataclass()

    print("\n" + "=" * 60)
    all_passed = all([result1, result2, result3, result4, result5])
    if all_passed:
        print("✅ Phase 3 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)
