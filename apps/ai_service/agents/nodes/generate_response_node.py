"""
Generate Response Node - 응답 생성 노드

Phase 5: Agent Hub - Master Agent Graph Node

설계 문서: docs/AGENT_HUB_DESIGN.md 섹션 6.3.3

역할:
- LLM 기반 응답 생성
- 사용자 친화적 포맷팅
- 응답 형식 결정 (텍스트, 구조화, 비교 등)
"""

from datetime import datetime
from enum import Enum
import logging
from typing import Dict, Any, List, Optional

from apps.ai_service.agents.states.master_agent_state import (
    MasterAgentState,
    StreamingEvent,
    Intent,
    IntentCategory,
)
from libs.rag_core.llm.llm_client import create_llm_client
from apps.ai_service.config.settings import settings

logger = logging.getLogger(__name__)


# =============================================================================
# 응답 포맷 타입
# =============================================================================

class ResponseFormat(str, Enum):
    """응답 포맷 타입"""
    TEXT = "text"                    # 일반 텍스트
    STRUCTURED = "structured"        # 구조화된 데이터 (표, 리스트)
    COMPARISON = "comparison"        # 비교 뷰
    CHART = "chart"                  # 차트/그래프
    DOCUMENT = "document"            # 문서 미리보기
    TIMELINE = "timeline"            # 타임라인
    MIXED = "mixed"                  # 혼합


# =============================================================================
# 응답 생성 프롬프트 템플릿
# =============================================================================

RESPONSE_GENERATION_PROMPT = """당신은 법률 AI 어시스턴트입니다.
아래의 실행 결과를 바탕으로 사용자에게 친화적이고 전문적인 응답을 생성하세요.

## 사용자 질문
{user_message}

## 실행된 작업
{executed_tasks}

## 실행 결과
{results}

## 응답 가이드라인
1. 명확하고 이해하기 쉬운 언어를 사용하세요
2. 중요한 정보는 강조하세요 (볼드, 리스트 등)
3. 법률 용어는 필요시 간단한 설명을 추가하세요
4. 결과가 여러 개인 경우 구조화하여 표시하세요
5. 리스크나 주의사항이 있으면 명확히 알려주세요
6. 추가 질문이 필요한 경우 안내하세요

## 응답 형식
- 마크다운 형식을 사용하세요
- 제목, 소제목, 리스트, 표 등을 적절히 활용하세요
- 한국어로 응답하세요

응답:"""


ERROR_RESPONSE_PROMPT = """당신은 법률 AI 어시스턴트입니다.
작업 실행 중 오류가 발생했습니다. 사용자에게 친절하게 상황을 설명하세요.

## 사용자 질문
{user_message}

## 발생한 오류
{errors}

## 응답 가이드라인
1. 오류 상황을 정중하게 설명하세요
2. 가능한 대안이나 해결 방법을 제안하세요
3. 다시 시도해볼 것을 권유하세요

응답:"""


GENERAL_CHAT_PROMPT = """당신은 '법률 AI 어시스턴트'입니다.
사용자가 법률과 무관한 일반적인 대화를 시작했습니다. 친근하고 자연스럽게 응답하세요.

## 사용자 메시지
{user_message}

## 응답 가이드라인
1. 친근하고 자연스러운 대화체로 응답하세요
2. 법률 AI 어시스턴트로서의 정체성을 유지하되, 딱딱하지 않게 응답하세요
3. 필요하다면 법률 관련 질문을 유도할 수 있지만 강요하지 마세요
4. 간결하게 응답하세요 (1-3문장)
5. 이모지는 사용하지 마세요

예시:
- "안녕하세요" → "안녕하세요! 무엇을 도와드릴까요? 법률 관련 질문이 있으시면 편하게 말씀해 주세요."
- "고마워" → "별말씀을요. 다른 궁금한 점이 있으시면 언제든 질문해 주세요."
- "넌 뭐야?" → "저는 법률 AI 어시스턴트입니다. 법률 질문, 계약서 분석, 판례 검색 등을 도와드릴 수 있습니다."

응답:"""


# =============================================================================
# 노드 구현
# =============================================================================

async def generate_response_node(state: MasterAgentState) -> MasterAgentState:
    """
    응답 생성 노드

    집계된 결과를 바탕으로 사용자 친화적인 응답을 생성합니다.

    Args:
        state: MasterAgentState (현재 상태)

    Returns:
        업데이트된 MasterAgentState

    State 업데이트:
        - final_response: 최종 응답 텍스트
        - response_metadata: 응답 메타데이터 (포맷 등)
        - streaming_events: 응답 생성 완료 이벤트 추가

    이벤트 발생:
        1. response_generating: 응답 생성 시작
        2. response_chunk: 스트리밍 응답 청크
        3. complete: 최종 완료
    """
    logger.info("[generate_response_node] Starting response generation")

    try:
        streaming_events = list(state.get("streaming_events", []))
        response_metadata = state.get("response_metadata", {})

        # 1. 응답 생성 시작 이벤트
        generating_event = StreamingEvent(
            event="response_generating",
            data={"message": "응답을 생성하고 있습니다..."},
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(generating_event.model_dump())

        # 2. 상태 분석
        status = response_metadata.get("status", "unknown")
        workflow_results = state.get("workflow_results", {})
        tool_results = state.get("tool_results", {})
        errors = state.get("errors", [])

        # 3. 응답 포맷 결정
        intent_dict = state.get("intent")
        response_format = _determine_response_format(intent_dict, workflow_results)

        # 4. 응답 생성
        # GENERAL_CHAT인 경우 별도 처리 (워크플로우 없이 LLM 직접 응답)
        is_general_chat = False
        if intent_dict:
            intent = Intent(**intent_dict)
            # intent.category는 use_enum_values=True로 인해 문자열일 수 있음
            category_value = intent.category.value if hasattr(intent.category, 'value') else intent.category
            is_general_chat = category_value == "GENERAL_CHAT"

        if is_general_chat:
            # 일반 대화 - RAG 없이 LLM 직접 응답
            final_response = await _generate_general_chat_response(
                user_message=state["user_message"],
            )
            logger.info("[generate_response_node] Generated GENERAL_CHAT response")
        elif status == "failed" or (not workflow_results and not tool_results and not is_general_chat):
            # 실패 응답 생성
            final_response = await _generate_error_response(
                user_message=state["user_message"],
                errors=errors,
            )
        else:
            # 성공 응답 생성
            final_response = await _generate_success_response(
                user_message=state["user_message"],
                intent_dict=intent_dict,
                workflow_results=workflow_results,
                tool_results=tool_results,
                response_format=response_format,
            )

        # 5. 응답 메타데이터 업데이트
        response_metadata["format"] = response_format.value
        response_metadata["response_length"] = len(final_response)
        response_metadata["generated_at"] = datetime.now().isoformat()

        document_analysis = _extract_document_analysis(workflow_results)
        if document_analysis:
            # 기존 문서 여부 확인 (attachments의 metadata.is_existing)
            attachments = state.get("attachments", [])
            is_existing = _check_is_existing_document(attachments)
            if is_existing:
                document_analysis["is_existing"] = True
            response_metadata["document_analysis"] = document_analysis

        # 6. sources 추출 (RAG 워크플로우 결과에서)
        sources = _extract_sources_from_results(workflow_results)

        # 7. 완료 이벤트
        complete_event = StreamingEvent(
            event="complete",
            data={
                "response": final_response,
                "format": response_format.value,
                "execution_time": response_metadata.get("execution_time", 0),
                "workflows_executed": response_metadata.get("workflows_executed", []),
                "status": status,
                "sources": sources,  # RAG 참고자료 추가
                "document_analysis": document_analysis,
            },
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(complete_event.model_dump())

        # 8. 상태 업데이트
        state["final_response"] = final_response
        state["response_metadata"] = response_metadata
        state["streaming_events"] = streaming_events

        logger.info(
            f"[generate_response_node] Completed: "
            f"format={response_format.value}, length={len(final_response)}"
        )

        return state

    except Exception as e:
        logger.error(f"[generate_response_node] Error: {e}", exc_info=True)

        # 폴백 응답
        fallback_response = _generate_fallback_response(
            state["user_message"],
            str(e),
        )

        # 에러 이벤트
        error_event = StreamingEvent(
            event="error",
            data={
                "step": "generate_response",
                "error": str(e),
                "message": "응답 생성 중 오류가 발생했습니다.",
            },
            timestamp=datetime.now().isoformat(),
        )

        streaming_events = list(state.get("streaming_events", []))
        streaming_events.append(error_event.model_dump())

        # 완료 이벤트 (폴백)
        complete_event = StreamingEvent(
            event="complete",
            data={
                "response": fallback_response,
                "format": ResponseFormat.TEXT.value,
                "status": "error",
            },
            timestamp=datetime.now().isoformat(),
        )
        streaming_events.append(complete_event.model_dump())

        state["final_response"] = fallback_response
        state["streaming_events"] = streaming_events

        return state


def _determine_response_format(
    intent_dict: Optional[Dict[str, Any]],
    workflow_results: Dict[str, Any],
) -> ResponseFormat:
    """
    응답 포맷 결정

    Args:
        intent_dict: 의도 딕셔너리
        workflow_results: 워크플로우 결과

    Returns:
        ResponseFormat
    """
    if not intent_dict:
        return ResponseFormat.TEXT

    intent = Intent(**intent_dict)
    # intent.category는 use_enum_values=True로 인해 문자열일 수 있음
    category_value = intent.category.value if hasattr(intent.category, 'value') else intent.category

    # 의도별 포맷 매핑 (문자열 키로 비교)
    format_map = {
        "GENERAL_CHAT": ResponseFormat.TEXT,  # 일반 대화
        "QUERY": ResponseFormat.TEXT,
        "DOCUMENT_ANALYSIS": ResponseFormat.STRUCTURED,
        "CASE_ANALYSIS": ResponseFormat.STRUCTURED,
        "RISK_ASSESSMENT": ResponseFormat.STRUCTURED,
        "COMPARISON": ResponseFormat.COMPARISON,
        "SEARCH": ResponseFormat.STRUCTURED,
        "GENERATION": ResponseFormat.DOCUMENT,
        "ANALYTICS": ResponseFormat.CHART,
        "MULTI_TASK": ResponseFormat.MIXED,
    }

    return format_map.get(category_value, ResponseFormat.TEXT)


async def _generate_success_response(
    user_message: str,
    intent_dict: Optional[Dict[str, Any]],
    workflow_results: Dict[str, Any],
    tool_results: Dict[str, Any],
    response_format: ResponseFormat,
) -> str:
    """
    성공 응답 생성

    Args:
        user_message: 사용자 메시지
        intent_dict: 의도 딕셔너리
        workflow_results: 워크플로우 결과
        tool_results: 도구 결과
        response_format: 응답 포맷

    Returns:
        생성된 응답 텍스트
    """
    # 1. 실행된 작업 목록 생성
    executed_tasks = []
    for step_id in workflow_results.keys():
        executed_tasks.append(f"- 워크플로우: {step_id}")
    for tool_id in tool_results.keys():
        executed_tasks.append(f"- 도구: {tool_id}")

    executed_tasks_str = "\n".join(executed_tasks) if executed_tasks else "없음"

    # 2. 결과 포맷팅
    results_str = _format_results_for_prompt(workflow_results, tool_results)

    # 3. 프롬프트 생성
    prompt = RESPONSE_GENERATION_PROMPT.format(
        user_message=user_message,
        executed_tasks=executed_tasks_str,
        results=results_str,
    )

    # 4. LLM 호출
    try:
        llm = create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            temperature=0.7,
            max_tokens=2000,
        )

        response = llm.generate(prompt=prompt)

        return response

    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        # LLM 실패 시 결과 직접 포맷팅
        return _format_results_directly(
            user_message,
            workflow_results,
            tool_results,
            response_format,
        )


async def _generate_error_response(
    user_message: str,
    errors: List[Dict[str, Any]],
) -> str:
    """
    에러 응답 생성

    Args:
        user_message: 사용자 메시지
        errors: 에러 목록

    Returns:
        생성된 에러 응답 텍스트
    """
    # 에러 포맷팅
    error_str = "\n".join([
        f"- {err.get('step', 'unknown')}: {err.get('error', 'Unknown error')}"
        for err in errors
    ]) if errors else "알 수 없는 오류"

    # 프롬프트 생성
    prompt = ERROR_RESPONSE_PROMPT.format(
        user_message=user_message,
        errors=error_str,
    )

    # LLM 호출
    try:
        llm = create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            temperature=0.7,
            max_tokens=500,
        )

        response = llm.generate(prompt=prompt)

        return response

    except Exception:
        # LLM 실패 시 기본 에러 메시지
        return f"""죄송합니다. 요청을 처리하는 중 문제가 발생했습니다.

**발생한 문제:**
{error_str}

다시 시도해 주시거나, 요청을 좀 더 구체적으로 해주시면 도움이 될 수 있습니다.
추가적인 도움이 필요하시면 말씀해 주세요."""


async def _generate_general_chat_response(user_message: str) -> str:
    """
    일반 대화 응답 생성 (RAG 없이 LLM 직접 호출)

    법률과 무관한 일반적인 대화에 대해 친근하게 응답합니다.

    Args:
        user_message: 사용자 메시지

    Returns:
        생성된 응답 텍스트
    """
    # 프롬프트 생성
    prompt = GENERAL_CHAT_PROMPT.format(user_message=user_message)

    # LLM 호출
    try:
        llm = create_llm_client(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
            temperature=0.8,  # 일반 대화는 조금 더 창의적으로
            max_tokens=300,   # 간결한 응답
        )

        response = llm.generate(prompt=prompt)
        return response

    except Exception as e:
        logger.error(f"[_generate_general_chat_response] LLM generation failed: {e}")
        # LLM 실패 시 기본 응답
        return "안녕하세요! 법률 AI 어시스턴트입니다. 법률 관련 질문이 있으시면 편하게 말씀해 주세요."


def _generate_fallback_response(user_message: str, error: str) -> str:
    """
    폴백 응답 생성 (LLM 없이)

    Args:
        user_message: 사용자 메시지
        error: 에러 메시지

    Returns:
        폴백 응답 텍스트
    """
    return f"""죄송합니다. 요청을 처리하는 중 예기치 않은 오류가 발생했습니다.

**원래 질문:** {user_message[:100]}{"..." if len(user_message) > 100 else ""}

**오류 내용:** {error}

다시 시도해 주시거나, 다른 방식으로 질문해 주시면 도움을 드리겠습니다."""


def _format_results_for_prompt(
    workflow_results: Dict[str, Any],
    tool_results: Dict[str, Any],
) -> str:
    """
    프롬프트용 결과 포맷팅

    Args:
        workflow_results: 워크플로우 결과
        tool_results: 도구 결과

    Returns:
        포맷팅된 결과 문자열
    """
    parts = []

    # 워크플로우 결과
    if workflow_results:
        parts.append("### 워크플로우 결과")
        for step_id, result in workflow_results.items():
            parts.append(f"\n**{step_id}:**")
            parts.append(_format_dict_for_prompt(result))

    # 도구 결과
    if tool_results:
        parts.append("\n### 도구 결과")
        for tool_id, result in tool_results.items():
            parts.append(f"\n**{tool_id}:**")
            parts.append(_format_dict_for_prompt(result))

    return "\n".join(parts) if parts else "결과 없음"


def _format_dict_for_prompt(data: Any, indent: int = 0) -> str:
    """
    딕셔너리를 프롬프트용 문자열로 변환

    Args:
        data: 데이터
        indent: 들여쓰기 레벨

    Returns:
        포맷팅된 문자열
    """
    prefix = "  " * indent

    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}- {key}:")
                lines.append(_format_dict_for_prompt(value, indent + 1))
            else:
                value_str = str(value)[:200]
                if len(str(value)) > 200:
                    value_str += "..."
                lines.append(f"{prefix}- {key}: {value_str}")
        return "\n".join(lines)

    elif isinstance(data, list):
        if not data:
            return f"{prefix}(빈 목록)"
        lines = []
        for item in data[:10]:  # 최대 10개만 표시
            lines.append(_format_dict_for_prompt(item, indent))
        if len(data) > 10:
            lines.append(f"{prefix}... 외 {len(data) - 10}개")
        return "\n".join(lines)

    else:
        return f"{prefix}{str(data)[:200]}"


def _format_results_directly(
    user_message: str,
    workflow_results: Dict[str, Any],
    tool_results: Dict[str, Any],
    response_format: ResponseFormat,
) -> str:
    """
    결과 직접 포맷팅 (LLM 없이)

    Args:
        user_message: 사용자 메시지
        workflow_results: 워크플로우 결과
        tool_results: 도구 결과
        response_format: 응답 포맷

    Returns:
        포맷팅된 응답 텍스트
    """
    parts = [f"## 분석 결과\n"]

    # 주요 결과 추출
    for step_id, result in workflow_results.items():
        if isinstance(result, dict):
            # answer 또는 response 키가 있으면 우선 표시
            if "answer" in result:
                parts.append(result["answer"])
            elif "response" in result:
                parts.append(result["response"])
            elif "summary" in result:
                parts.append(f"### 요약\n{result['summary']}")

            # 추가 정보
            if "risks" in result:
                parts.append("\n### 리스크 분석")
                for risk in result.get("risks", [])[:5]:
                    if isinstance(risk, dict):
                        parts.append(f"- {risk.get('description', risk)}")
                    else:
                        parts.append(f"- {risk}")

            if "recommendations" in result:
                parts.append("\n### 권장 사항")
                for rec in result.get("recommendations", [])[:5]:
                    parts.append(f"- {rec}")

    # 도구 결과
    for tool_id, result in tool_results.items():
        if isinstance(result, dict):
            if "results" in result:
                parts.append(f"\n### 검색 결과 ({len(result['results'])}건)")
                for item in result.get("results", [])[:5]:
                    if isinstance(item, dict):
                        parts.append(f"- {item.get('title', item)}")
                    else:
                        parts.append(f"- {item}")

    return "\n".join(parts)


def _extract_sources_from_results(workflow_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    워크플로우 결과에서 sources(참고자료) 추출

    RAG 워크플로우 결과에서 sources를 추출하여 프론트엔드에 전달합니다.

    Args:
        workflow_results: 워크플로우 실행 결과

    Returns:
        sources 목록 (각 항목: {title, content, source, score, doc_type, ...})
    """
    sources = []

    logger.debug(f"[_extract_sources_from_results] workflow_results keys: {list(workflow_results.keys())}")

    for step_id, result in workflow_results.items():
        logger.debug(f"[_extract_sources_from_results] step_id={step_id}, result type={type(result)}")

        if not isinstance(result, dict):
            logger.debug(f"[_extract_sources_from_results] Skipping non-dict result for {step_id}")
            continue

        logger.debug(f"[_extract_sources_from_results] step_id={step_id}, result keys={list(result.keys())}")

        # RAG 워크플로우 결과에서 sources 추출
        # RAG workflow returns: case_number, title, court, date, doc_type, relevance_score, text_snippet, full_text
        if "sources" in result:
            raw_sources = result.get("sources", [])
            for src in raw_sources:
                if isinstance(src, dict):
                    # RAG workflow 필드 매핑 (rag_nodes.py extract_sources 결과 구조)
                    source_item = {
                        "title": src.get("title", src.get("case_number", "출처 없음")),
                        "content": src.get("text_snippet", src.get("content", ""))[:300],
                        "source": src.get("case_number", src.get("source", "")),
                        "score": src.get("relevance_score", src.get("score", 0)),
                        "doc_type": src.get("doc_type", ""),
                        "court": src.get("court", ""),
                        "date": src.get("date", ""),
                        "case_number": src.get("case_number", ""),
                        "url": src.get("url", ""),
                    }
                    sources.append(source_item)
                elif isinstance(src, str):
                    sources.append({"title": src, "content": src})

        # 검색 결과에서도 추출 (search workflow)
        if "results" in result:
            for item in result.get("results", [])[:5]:
                if isinstance(item, dict):
                    sources.append({
                        "title": item.get("title", ""),
                        "content": item.get("content", item.get("snippet", ""))[:300],
                        "source": item.get("source", ""),
                        "url": item.get("url", ""),
                    })

    # 중복 제거 (title 기준)
    seen_titles = set()
    unique_sources = []
    for src in sources:
        title = src.get("title", "")
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_sources.append(src)

    logger.info(f"[_extract_sources_from_results] Extracted {len(unique_sources)} sources")
    return unique_sources[:10]  # 최대 10개


def _check_is_existing_document(attachments: List[Dict[str, Any]]) -> bool:
    """
    첨부 파일이 기존 문서인지 확인

    Args:
        attachments: 첨부 파일 목록

    Returns:
        기존 문서이면 True, 새 문서이면 False
    """
    if not attachments:
        return False

    for attachment in attachments:
        metadata = attachment.get("metadata", {})
        if isinstance(metadata, dict) and metadata.get("is_existing"):
            return True

    return False


def _extract_document_analysis(workflow_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """문서 분석 워크플로우 결과 추출"""

    for result in workflow_results.values():
        if not isinstance(result, dict):
            continue

        has_document_fields = any(
            key in result for key in ["summary", "clauses", "risks", "doc_type"]
        )

        if not has_document_fields:
            continue

        return {
            "document_id": result.get("document_id"),
            "doc_type": result.get("doc_type", "OTHER"),
            "summary": result.get("summary"),
            "clauses": result.get("clauses", []),
            "risks": result.get("risks"),
            "needs_expert_review": result.get("needs_expert_review", False),
        }

    return None


def generate_response_node_sync(state: MasterAgentState) -> MasterAgentState:
    """
    응답 생성 노드 (동기 버전)
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                generate_response_node(state)
            )
            return future.result()
    except RuntimeError:
        return asyncio.run(generate_response_node(state))
