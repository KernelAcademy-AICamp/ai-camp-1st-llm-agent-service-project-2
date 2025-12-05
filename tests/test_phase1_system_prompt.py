"""
Phase 1 테스트: 시스템 프롬프트 강화 검증

개선된 SYSTEM_PROMPT가 제대로 적용되었는지 확인합니다.
"""

import asyncio
import sys
sys.path.insert(0, "/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2")

from apps.ai_service.agents.nodes.tool_use_agent_node import SYSTEM_PROMPT


def test_system_prompt_structure():
    """시스템 프롬프트 구조 검증"""
    print("=" * 60)
    print("Phase 1 테스트: 시스템 프롬프트 구조 검증")
    print("=" * 60)

    # 필수 섹션 확인
    required_sections = [
        "## 응답 전략",
        "### 1단계: 질문 분석",
        "### 2단계: 정보 수집 전략",
        "### 3단계: 결과 평가",
        "### 4단계: 응답 생성",
        "## 도구 사용 가이드",
        "## 검색 품질 향상 팁",
        "## 응답 원칙",
    ]

    print("\n[필수 섹션 확인]")
    all_passed = True
    for section in required_sections:
        if section in SYSTEM_PROMPT:
            print(f"  ✅ {section}")
        else:
            print(f"  ❌ {section} - 누락됨!")
            all_passed = False

    # 도구 사용 가이드 테이블 확인
    tool_guide_entries = [
        "search_statutes",
        "search_precedents",
        "search_legal",
        "analyze_document",
        "analyze_risk",
        "analyze_criminal_case",
    ]

    print("\n[도구 사용 가이드 테이블 확인]")
    for tool in tool_guide_entries:
        if tool in SYSTEM_PROMPT:
            print(f"  ✅ {tool}")
        else:
            print(f"  ❌ {tool} - 누락됨!")
            all_passed = False

    # 검색 품질 팁 확인
    quality_tips = [
        "구체적인 검색어 사용",
        "검색 결과 부족 시",
        "복합 질문 처리",
    ]

    print("\n[검색 품질 향상 팁 확인]")
    for tip in quality_tips:
        if tip in SYSTEM_PROMPT:
            print(f"  ✅ {tip}")
        else:
            print(f"  ❌ {tip} - 누락됨!")
            all_passed = False

    # 새로운 응답 원칙 확인
    response_principles = [
        "검색 결과를 그대로 나열하지 말고 종합",
        "~로 보입니다",
        "한국어로 답변",
    ]

    print("\n[응답 원칙 확인]")
    for principle in response_principles:
        if principle in SYSTEM_PROMPT:
            print(f"  ✅ {principle}")
        else:
            print(f"  ❌ {principle} - 누락됨!")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 모든 검증 통과!")
    else:
        print("❌ 일부 검증 실패")
    print("=" * 60)

    return all_passed


def test_system_prompt_content():
    """시스템 프롬프트 내용 출력"""
    print("\n" + "=" * 60)
    print("현재 SYSTEM_PROMPT 내용 (처음 1500자)")
    print("=" * 60)
    print(SYSTEM_PROMPT[:1500])
    print("...")
    print(f"\n총 길이: {len(SYSTEM_PROMPT)} 자")


if __name__ == "__main__":
    test_system_prompt_content()
    print("\n")
    result = test_system_prompt_structure()

    # 종료 코드 설정
    sys.exit(0 if result else 1)
