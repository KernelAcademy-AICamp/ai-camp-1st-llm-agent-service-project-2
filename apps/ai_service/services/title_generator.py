"""
Session Title Generator Service

하이브리드 방식으로 채팅 세션 제목 자동 생성:
1. 즉시: 의도 기반 + 첫 메시지 기반 간단 제목
2. 비동기: LLM 기반 스마트 제목 생성
"""

import asyncio
import os
import re
from typing import Optional
from loguru import logger

# LLM imports
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from apps.ai_service.repositories.agent_hub_repository import update_session_metadata

# API 키 (환경변수에서 직접 로드)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", os.getenv("CLAUDE_API_KEY", ""))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", ""))


# 의도 카테고리별 한국어 프리픽스
INTENT_PREFIXES = {
    "GENERAL_CHAT": "대화",
    "QUERY": "법률 문의",
    "DOCUMENT_ANALYSIS": "문서 분석",
    "CASE_ANALYSIS": "사건 분석",
    "RISK_ASSESSMENT": "리스크 평가",
    "COMPARISON": "비교 분석",
    "SEARCH": "검색",
    "GENERATION": "문서 생성",
    "ANALYTICS": "통계 분석",
    "MULTI_TASK": "복합 작업",
    "UNKNOWN": "대화",
}

# 제거할 불필요한 접두어 패턴
NOISE_PATTERNS = [
    r"^(안녕하세요[,.]?\s*)",
    r"^(안녕[,.]?\s*)",
    r"^(네[,.]?\s*)",
    r"^(음[,.]?\s*)",
    r"^(그[,.]?\s*)",
    r"^(저[,.]?\s*)",
    r"^(제가\s*)",
    r"^(혹시\s*)",
    r"^(그런데\s*)",
    r"^(참고로\s*)",
]


def clean_message(message: str) -> str:
    """메시지에서 불필요한 접두어 제거"""
    cleaned = message.strip()
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def extract_key_phrase(message: str, max_length: int = 25) -> str:
    """메시지에서 핵심 구문 추출"""
    cleaned = clean_message(message)

    # 물음표로 끝나면 질문 추출
    if "?" in cleaned:
        # 첫 번째 질문 추출
        question = cleaned.split("?")[0].strip()
        if len(question) <= max_length:
            return question
        # 너무 길면 마지막 부분 사용
        words = question.split()
        result = ""
        for word in reversed(words):
            if len(result) + len(word) + 1 <= max_length:
                result = word + " " + result if result else word
            else:
                break
        return result.strip() if result else question[:max_length]

    # 첫 문장 추출
    sentences = re.split(r'[.!?\n]', cleaned)
    first_sentence = sentences[0].strip() if sentences else cleaned

    if len(first_sentence) <= max_length:
        return first_sentence

    # 너무 길면 자르기
    return first_sentence[:max_length].rsplit(" ", 1)[0] + "..."


def generate_simple_title(
    message: str,
    intent: str = "UNKNOWN",
    max_length: int = 40
) -> str:
    """
    즉시 생성: 의도 + 메시지 기반 간단 제목

    Args:
        message: 사용자 첫 메시지
        intent: 분류된 의도 카테고리
        max_length: 최대 제목 길이

    Returns:
        생성된 제목 문자열
    """
    prefix = INTENT_PREFIXES.get(intent, "대화")
    key_phrase = extract_key_phrase(message, max_length=max_length - len(prefix) - 3)

    if key_phrase:
        title = f"{prefix}: {key_phrase}"
    else:
        title = f"{prefix}"

    return title[:max_length]


async def generate_smart_title(
    message: str,
    response: str = "",
    intent: str = "UNKNOWN",
    max_length: int = 40
) -> Optional[str]:
    """
    LLM 기반 스마트 제목 생성

    빠르고 저렴한 모델(Claude Haiku 또는 GPT-3.5-turbo)을 사용하여
    대화 내용을 요약한 의미있는 제목 생성

    Args:
        message: 사용자 첫 메시지
        response: AI 응답 (있으면)
        intent: 분류된 의도
        max_length: 최대 제목 길이

    Returns:
        생성된 제목 또는 None (실패 시)
    """
    try:
        # 프롬프트 구성
        context = f"사용자 질문: {message[:300]}"
        if response:
            context += f"\n\nAI 응답 요약: {response[:200]}"

        system_prompt = """당신은 채팅 세션의 제목을 생성하는 전문가입니다.
주어진 대화 내용을 바탕으로 간결하고 명확한 한국어 제목을 생성하세요.

규칙:
- 20자 이내로 작성
- 핵심 주제를 담아야 함
- 동사보다 명사 위주
- 따옴표, 괄호, 설명 없이 제목만 출력
- "~에 대한 질문", "~문의" 같은 형식 선호

좋은 예시:
- 근로계약 해지 절차
- 부동산 매매 계약서 검토
- 상속세 계산 방법
- 형사 고소장 작성법"""

        user_prompt = f"""{context}

위 대화의 제목을 20자 이내로 생성하세요. 제목만 출력:"""

        # LLM 호출 (빠른 모델 우선)
        llm = None

        # Claude Haiku 시도
        if ANTHROPIC_API_KEY:
            try:
                llm = ChatAnthropic(
                    model="claude-3-haiku-20240307",
                    api_key=ANTHROPIC_API_KEY,
                    max_tokens=50,
                    temperature=0.3,
                )
            except Exception as e:
                logger.debug(f"Claude Haiku 초기화 실패: {e}")

        # GPT-3.5-turbo 폴백
        if llm is None and OPENAI_API_KEY:
            try:
                llm = ChatOpenAI(
                    model="gpt-3.5-turbo",
                    api_key=OPENAI_API_KEY,
                    max_tokens=50,
                    temperature=0.3,
                )
            except Exception as e:
                logger.debug(f"GPT-3.5-turbo 초기화 실패: {e}")

        if llm is None:
            logger.warning("LLM 제목 생성 불가: API 키 없음")
            return None

        # 호출
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        result = await llm.ainvoke(messages)
        title = result.content.strip()

        # 후처리
        # 따옴표 제거
        title = title.strip('"\'「」『』')
        # 줄바꿈 제거
        title = title.split("\n")[0].strip()
        # 길이 제한
        if len(title) > max_length:
            title = title[:max_length - 3] + "..."

        logger.debug(f"스마트 제목 생성 완료: {title}")
        return title

    except Exception as e:
        logger.warning(f"스마트 제목 생성 실패: {e}")
        return None


async def generate_and_update_title(
    session_id: str,
    message: str,
    response: str = "",
    intent: str = "UNKNOWN",
    current_title: str = "",
) -> str:
    """
    세션 제목 생성 및 DB 업데이트 (비동기)

    1단계: 즉시 간단 제목 생성 및 저장
    2단계: 비동기로 LLM 스마트 제목 생성 후 업데이트

    Args:
        session_id: 세션 ID
        message: 사용자 첫 메시지
        response: AI 응답
        intent: 분류된 의도
        current_title: 현재 제목 (비어있으면 새로 생성)

    Returns:
        생성된 제목
    """
    # 이미 의미있는 제목이 있으면 스킵
    if current_title and current_title not in ["", "새 대화", "New Chat"]:
        return current_title

    # 1단계: 즉시 간단 제목 생성
    simple_title = generate_simple_title(message, intent)

    # DB 업데이트 (즉시)
    try:
        await update_session_metadata(session_id, {"title": simple_title})
        logger.debug(f"세션 {session_id} 간단 제목 저장: {simple_title}")
    except Exception as e:
        logger.warning(f"간단 제목 저장 실패: {e}")

    # 2단계: 비동기 스마트 제목 생성 (백그라운드)
    asyncio.create_task(_update_smart_title(session_id, message, response, intent))

    return simple_title


async def _update_smart_title(
    session_id: str,
    message: str,
    response: str,
    intent: str,
) -> None:
    """백그라운드에서 스마트 제목 생성 및 업데이트"""
    try:
        # 약간의 딜레이 (응답 완료 후 실행되도록)
        await asyncio.sleep(1)

        smart_title = await generate_smart_title(message, response, intent)

        if smart_title:
            await update_session_metadata(session_id, {"title": smart_title})
            logger.info(f"세션 {session_id} 스마트 제목 업데이트: {smart_title}")
    except Exception as e:
        logger.warning(f"스마트 제목 업데이트 실패: {e}")


# 테스트용
if __name__ == "__main__":
    # 간단 제목 테스트
    test_cases = [
        ("계약 해지에 대해서 알려줘", "QUERY"),
        ("이 계약서 분석해줘", "DOCUMENT_ANALYSIS"),
        ("최근 대법원 판례 중 주요한 것들을 알려주세요", "SEARCH"),
        ("안녕하세요, 근로기준법상 연차휴가 규정에 대해 설명해주세요", "QUERY"),
        ("부동산 매매 계약 시 체크리스트를 알려주세요", "QUERY"),
    ]

    for message, intent in test_cases:
        title = generate_simple_title(message, intent)
        print(f"[{intent}] {message[:30]}... → {title}")
