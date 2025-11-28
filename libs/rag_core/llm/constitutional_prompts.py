"""
Constitutional AI 프롬프트 시스템

Anthropic의 Constitutional AI 방법론을 적용하여
법률 AI가 따라야 할 원칙을 정의하고 자기 검증을 수행합니다.
"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class Principle:
    """단일 원칙 정의"""
    name: str
    principle: str
    critique_question: str
    revision_instruction: str


class ConstitutionalPrinciples:
    """
    형사법 AI 필수 원칙 (5개 유지)

    제거된 원칙:
    - no_hallucination: accuracy와 내용 중복

    유지 이유:
    - accuracy: 법률 정보의 핵심 (검색 문서 기반)
    - cite_sources: 신뢰도의 근거
    - disclaimer: 법적 보호 필수
    - professional_tone: 법률 전문성 유지
    - korean_legal_terms: 법률 용어 정확성
    """

    PRINCIPLES = {
        "accuracy": Principle(
            name="정확성",
            principle="검색된 문서에 있는 내용만 답변한다. 없으면 '관련 정보 부족'이라고 답한다.",
            critique_question="검색 문서에 없는 내용을 추측했는가?",
            revision_instruction="문서에 없는 내용을 삭제하세요."
        ),

        "cite_sources": Principle(
            name="출처 명시",
            principle="[법령: 형법 제XX조], [판례: 대법원 XXXX도XXXX] 형식으로 출처 표시",
            critique_question="출처가 명시되었는가?",
            revision_instruction="출처를 추가하세요."
        ),

        "disclaimer": Principle(
            name="면책 조항",
            principle="답변 끝에 '⚠️ 법률 정보 제공이며, 구체적 사안은 변호사와 상담하세요' 포함",
            critique_question="면책 조항이 있는가?",
            revision_instruction="면책 조항을 추가하세요."
        ),

        "professional_tone": Principle(
            name="전문적 어조",
            principle="법률 전문가로서 객관적이고 정확한 어조를 유지한다.",
            critique_question="답변이 객관적이고 전문적인가?",
            revision_instruction="감정적/주관적 표현을 객관적으로 수정하세요."
        ),

        "korean_legal_terms": Principle(
            name="법률 용어 정확성",
            principle="법률 용어를 정확하게 사용하고, 필요시 쉬운 설명을 추가한다.",
            critique_question="법률 용어가 정확하게 사용되었는가?",
            revision_instruction="법률 용어를 정확히 사용하고, 괄호 안에 설명을 추가하세요."
        )
    }

    @classmethod
    def get_all_principles_text(cls) -> str:
        """간결한 원칙 텍스트"""
        text = "<Rules>\n"
        for idx, (key, p) in enumerate(cls.PRINCIPLES.items(), 1):
            text += f"{idx}. {p.principle}\n"
        text += "</Rules>"
        return text

    @classmethod
    def get_critique_prompts(cls) -> List[str]:
        """자기 비판용 질문 목록 반환"""
        return [p.critique_question for p in cls.PRINCIPLES.values()]


class FewShotExamples:
    """
    1-Shot Learning을 위한 간결한 예시

    변경 이유:
    - 토큰 효율성: ~3,000 → ~500 토큰 (약 83% 절감)
    - 1개 예시로도 패턴 학습 충분
    - 간결한 답변 형태를 모범으로 제시
    """

    EXAMPLES = [
        {
            "name": "간결한 정의형 답변",
            "question": "절도죄의 구성요건은 무엇인가요?",
            "context": """
[법령: 형법 제329조]
타인의 재물을 절취한 자는 6년 이하의 징역 또는 1천만원 이하의 벌금에 처한다.

[판례: 대법원 2019도56789]
절도죄가 성립하기 위해서는 타인의 재물을 그 의사에 반하여 자기 또는 제3자의 점유로 옮기는 행위가 있어야 한다.
""",
            "answer": """**절도죄**(형법 제329조)의 구성요건:

1. **객체**: 타인의 재물
2. **행위**: 절취 (점유 이전)
3. **주관적 요건**: 불법영득의사

[판례: 대법원 2019도56789] 타인의 재물을 그 의사에 반하여 자기 또는 제3자의 점유로 옮기는 행위

**형량**: 6년 이하 징역 또는 1천만원 이하 벌금

⚠️ 법률 정보 제공이며, 구체적 사안은 변호사와 상담하세요."""
        }
    ]

    # 추가 예시 (필요시 동적 선택용)
    COMPARISON_EXAMPLE = {
        "name": "비교형 답변",
        "question": "절도죄와 강도죄의 차이점은?",
        "context": "...",
        "answer": """**핵심 차이**: 폭행·협박의 유무

| 구분 | 절도죄 | 강도죄 |
|------|--------|--------|
| 수단 | 몰래 | 폭행·협박 |
| 형량 | 6년↓ | 3년↑ |

[출처: 형법 제329조, 제333조]

⚠️ 법률 정보 제공입니다."""
    }

    @classmethod
    def format_examples(cls) -> str:
        """Few-shot 예시를 프롬프트 형식으로 포맷"""
        formatted = "<Example>\n"

        for example in cls.EXAMPLES:
            formatted += f"Q: {example['question']}\n"
            formatted += f"A: {example['answer']}\n"

        formatted += "</Example>"
        return formatted

    @classmethod
    def get_example_count(cls) -> int:
        """예시 개수 반환"""
        return len(cls.EXAMPLES)


class ConstitutionalPromptBuilder:
    """
    Constitutional AI 프롬프트 빌더

    왜 이런 구조인가?
    1. 원칙 명시: AI가 따라야 할 가이드라인 제공
    2. Few-shot: 구체적인 예시로 패턴 학습
    3. 자기 검증: AI가 스스로 답변을 검토하도록 유도
    """

    @staticmethod
    def build_system_prompt() -> str:
        """시스템 프롬프트 생성 (모델의 기본 역할 정의)"""
        return """당신은 대한민국 형사법 전문 AI 상담사입니다.

당신의 역할:
- 형사법 관련 질문에 정확하고 전문적으로 답변
- 제공된 판례, 법령, 해석례를 기반으로 답변
- 법률 정보 제공 (법률 자문 아님)

당신의 강점:
- 방대한 판례와 법령 데이터베이스 검색 능력
- 복잡한 법률 개념을 이해하기 쉽게 설명
- 객관적이고 정확한 정보 제공

당신의 한계:
- 실제 법률 자문 제공 불가
- 개별 사건에 대한 법적 판단 불가
- 검색 결과에 없는 내용은 답변 불가"""

    @staticmethod
    def build_user_prompt(
        question: str,
        context: str,
        max_length: int = 200  # 새 파라미터: 답변 최대 단어 수
    ) -> str:
        """
        사용자 프롬프트 생성 (간결한 버전)

        Args:
            question: 사용자 질문
            context: 검색된 문서 컨텍스트
            max_length: 답변 최대 단어 수 (기본 200)
        """

        prompt = f"""{ConstitutionalPrinciples.get_all_principles_text()}

{FewShotExamples.format_examples()}

<Documents>
{context}
</Documents>

<Question>
{question}
</Question>

<Instructions>
1. 검색된 문서만 사용하여 답변
2. 출처를 [법령: ...], [판례: ...] 형식으로 표시
3. 끝에 면책 조항 포함
4. **답변은 {max_length}단어 이내로 간결하게 작성**
</Instructions>

Answer:"""

        return prompt

    @staticmethod
    def build_critique_prompt(question: str, answer: str, context: str) -> str:
        """
        자기 비판 프롬프트 생성

        목적: AI가 자신의 답변을 검토하고 개선점 찾기
        """

        critique_questions = ConstitutionalPrinciples.get_critique_prompts()

        prompt = f"""<Self-Critique Task>

다음 답변이 Constitutional Principles를 준수하는지 엄격히 검토하세요.

**원본 질문**: {question}

**검색된 문서**: {context}

**생성된 답변**: {answer}

**검토 항목**:
"""

        for idx, question in enumerate(critique_questions, 1):
            prompt += f"{idx}. {question}\n"

        prompt += """
**지시사항**:
각 항목에 대해 YES/NO로 답하고, NO인 경우 구체적인 위반 내용을 설명하세요.

JSON 형식으로 응답:
{
    "violations": [
        {
            "principle": "원칙 이름",
            "violated": true/false,
            "reason": "위반 이유 (violated가 true인 경우)"
        }
    ],
    "needs_revision": true/false,
    "revision_suggestions": ["개선 제안 1", "개선 제안 2", ...]
}
</Self-Critique Task>"""

        return prompt

    @staticmethod
    def build_revision_prompt(original_answer: str, violations: dict) -> str:
        """
        수정 프롬프트 생성

        목적: 위반 사항을 수정한 개선된 답변 생성
        """

        prompt = f"""<Revision Task>

다음 답변에서 발견된 Constitutional Principles 위반 사항을 수정하세요.

**원본 답변**:
{original_answer}

**위반 사항**:
"""

        for violation in violations.get('violations', []):
            if violation['violated']:
                prompt += f"- [{violation['principle']}] {violation['reason']}\n"

        prompt += f"""
**개선 제안**:
{chr(10).join('- ' + s for s in violations.get('revision_suggestions', []))}

**지시사항**:
위 위반 사항을 수정하여 개선된 답변을 작성하세요.
- 모든 Constitutional Principles 준수
- 원본 답변의 핵심 내용은 유지
- 출처 명시, 면책 조항 포함

**수정된 답변**:
</Revision Task>"""

        return prompt


# 사용 예시 및 설명
if __name__ == "__main__":
    # 예시: 프롬프트 생성
    question = "절도죄의 구성요건은 무엇인가요?"
    context = "[법령: 형법 제329조] 타인의 재물을 절취한 자는..."

    builder = ConstitutionalPromptBuilder()

    print("=== SYSTEM PROMPT ===")
    print(builder.build_system_prompt())
    print("\n=== USER PROMPT ===")
    print(builder.build_user_prompt(question, context))

    print(f"\n=== INFO ===")
    print(f"Few-Shot Examples: {FewShotExamples.get_example_count()}개")
    print(f"Constitutional Principles: {len(ConstitutionalPrinciples.PRINCIPLES)}개")
