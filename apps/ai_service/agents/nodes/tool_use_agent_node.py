"""
Tool Use Agent Node

LLM의 Native Tool Use (Function Calling) 기능을 활용하는 에이전트 노드입니다.

특징:
1. LLM이 직접 도구 사용 여부와 도구 선택을 결정
2. ReAct 패턴: Observe → Think → Act 반복
3. 단순 질문은 도구 없이 직접 응답
4. 복잡한 질문은 필요한 만큼 도구 호출 반복

목표:
- Claude, ChatGPT와 같은 현대적 AI 서비스의 동작 방식 구현
- 키워드 기반 분류 → LLM 기반 동적 결정으로 전환
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import asyncio
import json

from apps.ai_service.agents.states.master_agent_state import (
    ExtendedMasterAgentState,
    StreamingEvent,
    ProgressStep,
    create_progress_event,
)
from apps.ai_service.agents.tools.tool_schemas import (
    get_openai_tools,
    get_anthropic_tools,
    TOOL_SCHEMAS,
    DEFAULT_AGENT_TOOLS,
    select_tools_for_query,
)
from apps.ai_service.agents.tools.registry import (
    get_tool_registry,
    ToolResult,
)
from apps.ai_service.agents.nodes.retrieval_evaluator import (
    evaluate_retrieval,
    quick_evaluate,
    EvaluationResult,
)
from apps.ai_service.agents.nodes.query_decomposer import (
    decompose_query,
    should_decompose,
    format_decomposition_for_prompt,
    DecomposedQuery,
)
from libs.rag_core.llm.llm_client import (
    get_llm_client,
    ToolCall,
    ToolUseResponse,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 상수 및 설정
# =============================================================================

MAX_TOOL_CALLS = 5  # 최대 도구 호출 횟수
DEFAULT_MODEL = "gpt-4o-mini"  # 기본 모델

SYSTEM_PROMPT = """당신은 법률 전문 AI 어시스턴트입니다. 사용자의 법률 관련 질문에 정확하고 신뢰할 수 있는 답변을 제공합니다.

## 응답 전략

### 1단계: 질문 분석
- 사용자가 실제로 원하는 정보가 무엇인지 파악
- 질문에 답하기 위해 필요한 정보 유형 식별
- 복합 질문인 경우 하위 질문으로 분해

### 2단계: 정보 수집 전략
- **단순 질문** (인사, 일반 상식): 도구 없이 직접 답변
- **법률 정보 질문**: 관련 도구로 검색
- **복합 질문**: 여러 도구를 순차적으로 사용

### 3단계: 결과 평가
- 검색 결과가 질문에 직접 관련되는지 평가
- 정보가 충분한지 판단
- 부족하면 다른 검색어로 재시도 또는 다른 도구 사용

### 4단계: 응답 생성
- 수집한 정보를 종합하여 답변 구성
- 불확실한 내용은 명시
- 출처가 있으면 언급

## 도구 사용 가이드

| 질문 유형 | 사용할 도구 | 검색어 팁 |
|----------|------------|----------|
| 법률 조문 | search_statutes | 법률명 + 조항번호 (예: "민법 제750조") |
| 판례 검색 | search_precedents | 쟁점 키워드 (예: "명예훼손 위자료 산정") |
| 일반 법률 질문 | search_legal | 구체적인 상황 설명 |
| 문서 분석 | analyze_document | 첨부된 문서 내용 전달 |
| 리스크 분석 | analyze_risk | 문서 내용 + 분석 관점 |
| 형사 사건 | analyze_criminal_case | 혐의 + 상황 설명 |
| 사용자 문서 | list_user_documents, search_user_documents | 문서 종류 또는 키워드 |

## 검색 품질 향상 팁

1. **구체적인 검색어 사용**
   - 나쁨: "손해배상"
   - 좋음: "민법 불법행위 손해배상 제750조"

2. **검색 결과 부족 시**
   - 동의어나 관련 용어로 재검색
   - 더 일반적이거나 더 구체적인 검색어 시도
   - 다른 도구 사용 고려

3. **복합 질문 처리**
   - "A와 B를 비교해줘" → A 검색 → B 검색 → 비교 정리
   - "이 계약서 분석하고 유사 판례 찾아줘" → 문서 분석 → 판례 검색

## 응답 원칙

- 검색 결과를 그대로 나열하지 말고 종합해서 설명
- 확실하지 않은 내용은 "~로 보입니다", "~일 수 있습니다" 표현 사용
- 법적 조언이 아닌 정보 제공임을 필요시 안내
- 한국어로 답변
"""

# =============================================================================
# 응답 종합 프롬프트 (Phase 5)
# =============================================================================

SYNTHESIS_PROMPT = """당신은 정보 종합 전문가입니다.

## 원래 질문
{query}

## 수집된 정보
{tool_results}

## 작업
위 정보를 종합하여 사용자 질문에 대한 답변을 작성하세요.

## 답변 작성 원칙

1. **구조화**: 정보를 논리적으로 정리
2. **종합**: 여러 소스 정보를 통합
3. **명확성**: 핵심 내용 강조
4. **출처 명시**: 정보 출처 언급 (예: "민법 제750조에 따르면...")
5. **한계 인정**: 불확실한 내용은 명시

## 출력
사용자에게 직접 전달할 답변을 작성하세요. 한국어로 답변하세요.
"""


# =============================================================================
# Tool Use Agent 노드
# =============================================================================

async def tool_use_agent_node(state: ExtendedMasterAgentState) -> Dict[str, Any]:
    """
    Tool Use Agent 노드

    LLM의 Native Tool Use 기능을 활용해 동적으로 도구를 선택하고 실행합니다.

    처리 흐름:
    1. 사용자 메시지와 컨텍스트 준비
    2. LLM에 도구와 함께 메시지 전송
    3. LLM이 도구 호출을 요청하면 실행
    4. 도구 결과를 LLM에 전달 (반복)
    5. 최종 응답 생성

    Args:
        state: ExtendedMasterAgentState

    Returns:
        업데이트할 필드 딕셔너리
    """
    logger.info("[tool_use_agent_node] Starting Tool Use Agent")

    user_message = state.get("user_message", "")
    conversation_history = state.get("conversation_history", [])
    attachments = state.get("attachments", [])
    user_context = state.get("user_context", {})
    user_id = user_context.get("user_id") if user_context else None

    streaming_events = list(state.get("streaming_events", []))

    # =========================================================================
    # 1. 진행 이벤트
    # =========================================================================
    progress_start = create_progress_event(
        step=ProgressStep.ANALYZING,
        percentage=10,
        message="질문을 분석하고 있습니다...",
        execution_path="tool_use_agent",
        step_details={"step": "start", "phase": "analyzing"},
    )
    streaming_events.append(progress_start.model_dump())

    # =========================================================================
    # 2. Phase 4: 쿼리 분해 (복합 질문 처리)
    # =========================================================================
    decomposed = None
    if should_decompose(user_message):
        try:
            # LLM 호출 전에 미리 클라이언트 가져오기
            temp_llm = get_llm_client(model_name=DEFAULT_MODEL)
            decomposed = await decompose_query(user_message, llm_client=temp_llm)

            if decomposed.is_complex:
                logger.info(
                    f"[tool_use_agent_node] Query decomposed into "
                    f"{len(decomposed.sub_queries)} sub-queries"
                )

                # 분해 이벤트
                decompose_event = StreamingEvent(
                    event="query_decomposed",
                    data={
                        "is_complex": True,
                        "sub_queries": decomposed.sub_queries,
                        "reasoning": decomposed.reasoning[:100] if decomposed.reasoning else "",
                    },
                    timestamp=datetime.now().isoformat(),
                )
                streaming_events.append(decompose_event.model_dump())

        except Exception as e:
            logger.warning(f"[tool_use_agent_node] Query decomposition failed: {e}")

    # =========================================================================
    # 3. 메시지 준비
    # =========================================================================
    messages = _prepare_messages(
        user_message=user_message,
        conversation_history=conversation_history,
        attachments=attachments,
        decomposed=decomposed,  # 분해 정보 전달
    )

    # =========================================================================
    # 4. 도구 정의 준비 (Phase 2: 동적 도구 선택)
    # =========================================================================
    # 질문에 적합한 도구만 동적으로 선택
    tool_names = select_tools_for_query(
        query=user_message,
        has_attachment=bool(attachments),
        has_user_context=bool(user_id),
        max_tools=6,
    )

    tools = get_openai_tools(tool_names)

    logger.info(f"[tool_use_agent_node] Selected tools ({len(tools)}): {tool_names}")

    # 도구 선택 이벤트 (프론트엔드에서 "검색 중" 표시에 사용)
    tools_selected_event = StreamingEvent(
        event="tools_selected",
        data={
            "tools": tool_names,
            "message": "법률 정보를 검색하고 있습니다...",
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(tools_selected_event.model_dump())

    # =========================================================================
    # 4. LLM Client 가져오기
    # =========================================================================
    try:
        llm_client = get_llm_client(model_name=DEFAULT_MODEL)
    except Exception as e:
        logger.error(f"[tool_use_agent_node] Failed to get LLM client: {e}")
        return _create_error_response(
            error=f"LLM 클라이언트 초기화 실패: {e}",
            streaming_events=streaming_events,
        )

    # =========================================================================
    # 5. ReAct Loop: LLM 호출 → 도구 실행 반복
    # =========================================================================
    tool_results = []
    total_tool_calls = 0

    for iteration in range(MAX_TOOL_CALLS + 1):
        logger.info(f"[tool_use_agent_node] Iteration {iteration + 1}")

        # 진행 이벤트
        if iteration > 0:
            progress_tool = create_progress_event(
                step=ProgressStep.EXECUTING,
                percentage=30 + (iteration * 15),
                message=f"도구 실행 중... ({iteration}/{MAX_TOOL_CALLS})",
                execution_path="tool_use_agent",
                step_details={"iteration": iteration, "tool_calls": total_tool_calls},
            )
            streaming_events.append(progress_tool.model_dump())

        # LLM 호출 (Tool Use)
        try:
            response: ToolUseResponse = llm_client.chat_with_tools(
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
        except NotImplementedError:
            logger.warning("[tool_use_agent_node] Model does not support tool use, using direct response")
            # Tool Use 미지원 시 일반 응답
            direct_response = llm_client.chat(
                messages=messages,
                max_tokens=2000,
            )
            return _create_success_response(
                content=direct_response,
                tool_results=tool_results,
                streaming_events=streaming_events,
                path="tool_use_agent_fallback",
            )
        except Exception as e:
            logger.error(f"[tool_use_agent_node] LLM call failed: {e}")
            return _create_error_response(
                error=f"LLM 호출 실패: {e}",
                streaming_events=streaming_events,
            )

        # 도구 호출이 없으면 최종 응답
        if response.stop_reason == "end_turn" or not response.tool_calls:
            logger.info("[tool_use_agent_node] No tool calls, generating final response")

            # 최종 응답 생성
            final_content = response.content
            if not final_content:
                # content가 없으면 별도 호출 (Phase 5: 응답 종합기 사용)
                final_content = await _generate_final_response(
                    llm_client, messages, tool_results, user_query=user_message
                )

            return _create_success_response(
                content=final_content,
                tool_results=tool_results,
                streaming_events=streaming_events,
                path="tool_use_agent",
                total_tool_calls=total_tool_calls,
            )

        # 도구 호출 실행
        for tool_call in response.tool_calls:
            total_tool_calls += 1
            logger.info(f"[tool_use_agent_node] Tool call: {tool_call.name}")

            # 스트리밍 이벤트
            tool_event = StreamingEvent(
                event="tool_call",
                data={
                    "tool_name": tool_call.name,
                    "arguments": tool_call.arguments,
                    "iteration": iteration,
                },
                timestamp=datetime.now().isoformat(),
            )
            streaming_events.append(tool_event.model_dump())

            # 도구 실행
            tool_result = await _execute_tool(
                tool_name=tool_call.name,
                arguments=tool_call.arguments,
                user_id=user_id,
            )

            tool_results.append({
                "tool_call_id": tool_call.id,
                "tool_name": tool_call.name,
                "arguments": tool_call.arguments,
                "result": tool_result,
            })

            # Phase 3: 검색 도구인 경우 결과 평가
            if tool_call.name in ["search_legal", "search_precedents", "search_statutes"]:
                search_results = tool_result.get("data", {}).get("sources", [])

                if search_results:
                    # 빠른 평가 먼저 수행
                    if not quick_evaluate(search_results, min_score=0.4):
                        logger.info(f"[tool_use_agent_node] Quick eval: low scores, consider retry")

                    # 상세 평가 (iteration 여유가 있을 때만)
                    if iteration < MAX_TOOL_CALLS - 1:
                        try:
                            evaluation = await evaluate_retrieval(
                                query=tool_call.arguments.get("query", user_message),
                                results=search_results,
                                llm_client=llm_client,
                            )

                            # 평가 결과를 도구 결과에 추가
                            tool_results[-1]["evaluation"] = {
                                "relevance_score": evaluation.relevance_score,
                                "completeness_score": evaluation.completeness_score,
                                "suggested_action": evaluation.suggested_action,
                                "reasoning": evaluation.reasoning[:200] if evaluation.reasoning else "",
                            }

                            # 평가 이벤트
                            eval_event = StreamingEvent(
                                event="retrieval_evaluation",
                                data={
                                    "tool_name": tool_call.name,
                                    "relevance_score": evaluation.relevance_score,
                                    "completeness_score": evaluation.completeness_score,
                                    "suggested_action": evaluation.suggested_action,
                                },
                                timestamp=datetime.now().isoformat(),
                            )
                            streaming_events.append(eval_event.model_dump())

                            logger.info(
                                f"[tool_use_agent_node] Retrieval evaluation: "
                                f"relevance={evaluation.relevance_score:.2f}, "
                                f"completeness={evaluation.completeness_score:.2f}, "
                                f"action={evaluation.suggested_action}"
                            )

                        except Exception as e:
                            logger.warning(f"[tool_use_agent_node] Evaluation failed: {e}")

            # 메시지에 도구 결과 추가
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": json.dumps(tool_call.arguments, ensure_ascii=False),
                    }
                }],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result, ensure_ascii=False, default=str),
            })

            # 도구 결과 이벤트
            result_event = StreamingEvent(
                event="tool_result",
                data={
                    "tool_name": tool_call.name,
                    "success": tool_result.get("success", True),
                },
                timestamp=datetime.now().isoformat(),
            )
            streaming_events.append(result_event.model_dump())

    # 최대 반복 도달 (Phase 5: 응답 종합기 사용)
    logger.warning(f"[tool_use_agent_node] Max iterations reached ({MAX_TOOL_CALLS})")
    final_content = await _generate_final_response(
        llm_client, messages, tool_results, user_query=user_message
    )

    return _create_success_response(
        content=final_content,
        tool_results=tool_results,
        streaming_events=streaming_events,
        path="tool_use_agent",
        total_tool_calls=total_tool_calls,
        max_reached=True,
    )


# =============================================================================
# Helper 함수들
# =============================================================================

def _prepare_messages(
    user_message: str,
    conversation_history: List[Dict[str, Any]],
    attachments: List[Dict[str, Any]],
    decomposed: Optional[DecomposedQuery] = None,
) -> List[Dict[str, Any]]:
    """
    LLM 메시지 준비

    Args:
        user_message: 사용자 메시지
        conversation_history: 대화 기록
        attachments: 첨부 파일
        decomposed: 분해된 쿼리 (Phase 4)

    Returns:
        메시지 목록
    """
    # 시스템 프롬프트 준비
    system_content = SYSTEM_PROMPT

    # Phase 4: 복합 질문이면 분해 정보 추가
    if decomposed and decomposed.is_complex:
        decomposition_note = format_decomposition_for_prompt(decomposed)
        if decomposition_note:
            system_content += decomposition_note

    messages = [{"role": "system", "content": system_content}]

    # 대화 기록 추가 (최근 10개)
    if conversation_history:
        recent_history = conversation_history[-10:]
        for msg in recent_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"]:
                messages.append({"role": role, "content": content})

    # 현재 사용자 메시지
    current_message = user_message

    # 첨부 파일 내용 추가
    if attachments:
        attachment_text = "\n\n--- 첨부 문서 ---\n"
        for att in attachments:
            filename = att.get("filename", "문서")
            content = att.get("content", "")
            if content:
                attachment_text += f"\n[{filename}]\n{content[:5000]}\n"  # 5000자 제한

        current_message += attachment_text

    messages.append({"role": "user", "content": current_message})

    return messages


async def _execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    도구 실행

    Args:
        tool_name: 도구 이름
        arguments: 도구 인자
        user_id: 사용자 ID (사용자 문서 도구용)

    Returns:
        도구 실행 결과
    """
    registry = get_tool_registry()

    # user_id 필요한 도구에 추가
    if user_id and tool_name in [
        "list_user_documents",
        "search_user_documents",
        "get_document_analysis",
        "list_documents_with_risk",
        "get_risk_overview",
        "list_user_criminal_cases",
        "get_criminal_case_highest_sentence",
        # Generic DB Query Tools (Phase 7)
        "query_user_criminal_cases",
        "get_criminal_case_detail",
        "get_user_case_statistics",
    ]:
        arguments["user_id"] = user_id

    try:
        result: ToolResult = await registry.execute_tool(
            tool_name=tool_name,
            inputs=arguments,
        )

        if result.success:
            return {
                "success": True,
                "data": result.data,
            }
        else:
            return {
                "success": False,
                "error": result.error,
            }

    except Exception as e:
        logger.error(f"[_execute_tool] Error executing {tool_name}: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def _generate_final_response(
    llm_client,
    messages: List[Dict[str, Any]],
    tool_results: List[Dict[str, Any]],
    user_query: str = "",
) -> str:
    """
    최종 응답 생성 (Phase 5: 응답 종합기)

    도구 결과가 있으면 SYNTHESIS_PROMPT를 사용하여 종합된 응답 생성.
    도구 결과가 없으면 기존 방식으로 응답 생성.

    Args:
        llm_client: LLM 클라이언트
        messages: 메시지 기록
        tool_results: 도구 실행 결과
        user_query: 원래 사용자 질문

    Returns:
        최종 응답 텍스트
    """
    # 도구 결과가 있으면 synthesize_response 사용
    if tool_results:
        return await synthesize_response(
            query=user_query,
            tool_results=tool_results,
            llm_client=llm_client,
        )

    # 도구 결과가 없으면 기존 방식
    try:
        clean_messages = []
        for msg in messages:
            if msg.get("role") == "tool":
                clean_messages.append({
                    "role": "system",
                    "content": f"[도구 결과]\n{msg.get('content', '')}",
                })
            elif msg.get("tool_calls"):
                tool_names = [tc["function"]["name"] for tc in msg["tool_calls"]]
                clean_messages.append({
                    "role": "assistant",
                    "content": f"[도구 호출: {', '.join(tool_names)}]",
                })
            else:
                clean_messages.append(msg)

        response = llm_client.chat(
            messages=clean_messages,
            max_tokens=2000,
        )
        return response

    except Exception as e:
        logger.error(f"[_generate_final_response] Error: {e}")
        return f"응답 생성 중 오류가 발생했습니다: {e}"


# =============================================================================
# 응답 종합기 (Phase 5)
# =============================================================================

async def synthesize_response(
    query: str,
    tool_results: List[Dict[str, Any]],
    llm_client=None,
    model_name: str = "gpt-4o-mini",
) -> str:
    """
    도구 결과를 종합하여 최종 응답 생성 (Phase 5)

    Args:
        query: 원래 질문
        tool_results: 도구 실행 결과 목록
        llm_client: LLM 클라이언트 (없으면 새로 생성)
        model_name: 종합에 사용할 모델

    Returns:
        종합된 응답 텍스트
    """
    # 도구 결과 포맷팅
    results_text = _format_tool_results_for_synthesis(tool_results)

    # 결과가 없으면 기본 메시지
    if not results_text.strip():
        return "검색 결과가 없습니다. 다른 검색어로 다시 시도해 주세요."

    try:
        # LLM 클라이언트 준비
        if llm_client is None:
            llm_client = get_llm_client(model_name=model_name)

        # 종합 프롬프트 생성
        prompt = SYNTHESIS_PROMPT.format(
            query=query,
            tool_results=results_text,
        )

        response = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )

        logger.info(f"[synthesize_response] Generated response ({len(response)} chars)")
        return response

    except Exception as e:
        logger.error(f"[synthesize_response] Error: {e}")
        return f"응답 생성 중 오류가 발생했습니다: {e}"


def _format_tool_results_for_synthesis(
    tool_results: List[Dict[str, Any]],
    max_chars: int = 4000,
) -> str:
    """
    종합을 위한 도구 결과 포맷팅

    Args:
        tool_results: 도구 실행 결과 목록
        max_chars: 최대 문자 수

    Returns:
        포맷팅된 결과 텍스트
    """
    formatted = []
    total_chars = 0

    for result in tool_results:
        tool_name = result.get("tool_name", "unknown")
        result_data = result.get("result", {})

        # 실패한 도구 결과 처리
        if not result_data.get("success", True):
            entry = f"### {tool_name} (실패)\n오류: {result_data.get('error', '알 수 없는 오류')}\n"
            formatted.append(entry)
            total_chars += len(entry)
            continue

        data = result_data.get("data", {})

        # 도구별 포맷팅
        if tool_name in ["search_legal", "search_precedents", "search_statutes"]:
            # 검색 도구 결과
            sources = data.get("sources", [])
            answer = data.get("answer", "")

            entry = f"### {tool_name} 결과\n"
            if answer:
                entry += f"**요약**: {answer[:500]}\n"
            if sources:
                entry += "**출처**:\n"
                for i, src in enumerate(sources[:3], 1):
                    title = src.get("title", src.get("case_name", "N/A"))
                    text = src.get("text", src.get("content", ""))[:200]
                    score = src.get("score", "")
                    score_str = f" (점수: {score:.2f})" if isinstance(score, float) else ""
                    entry += f"{i}. **{title}**{score_str}: {text}...\n"

        elif tool_name in ["analyze_document", "analyze_risk"]:
            # 분석 도구 결과
            entry = f"### {tool_name} 결과\n"
            if isinstance(data, dict):
                summary = data.get("summary", data.get("analysis", ""))
                if summary:
                    entry += f"**분석 결과**: {summary[:500]}\n"
                risks = data.get("risks", data.get("risk_items", []))
                if risks:
                    entry += "**식별된 항목**:\n"
                    for r in risks[:5]:
                        if isinstance(r, dict):
                            entry += f"- {r.get('description', r.get('content', str(r)))[:100]}\n"
                        else:
                            entry += f"- {str(r)[:100]}\n"
            else:
                entry += f"{str(data)[:500]}\n"

        elif tool_name in ["analyze_criminal_case", "analyze_case"]:
            # 사건 분석 결과
            entry = f"### {tool_name} 결과\n"
            if isinstance(data, dict):
                for key in ["summary", "analysis", "prediction", "recommendation"]:
                    if key in data:
                        entry += f"**{key}**: {str(data[key])[:300]}\n"
            else:
                entry += f"{str(data)[:500]}\n"

        else:
            # 기타 도구
            entry = f"### {tool_name} 결과\n"
            if isinstance(data, dict):
                entry += json.dumps(data, ensure_ascii=False, indent=2)[:500] + "\n"
            else:
                entry += f"{str(data)[:500]}\n"

        # 최대 길이 체크
        if total_chars + len(entry) > max_chars:
            formatted.append(f"... (결과 일부 생략, 총 {len(tool_results)}개 도구 결과 중 {len(formatted)}개 표시)")
            break

        formatted.append(entry)
        total_chars += len(entry)

    return "\n".join(formatted)


def _create_success_response(
    content: str,
    tool_results: List[Dict[str, Any]],
    streaming_events: List[Dict[str, Any]],
    path: str,
    total_tool_calls: int = 0,
    max_reached: bool = False,
) -> Dict[str, Any]:
    """성공 응답 생성"""
    # 진행 완료 이벤트 (100%)
    progress_event = create_progress_event(
        step=ProgressStep.COMPLETE,
        percentage=100,
        message="답변이 완료되었습니다.",
        execution_path=path,
        step_details={
            "tool_calls": total_tool_calls,
            "max_reached": max_reached,
        },
    )
    streaming_events.append(progress_event.model_dump())

    # sources 추출 (검색 도구 결과에서)
    sources = []
    logger.info(f"[_create_success_response] Extracting sources from {len(tool_results)} tool results")

    for result in tool_results:
        tool_name = result.get("tool_name", "unknown")
        result_data = result.get("result", {})
        logger.debug(f"[_create_success_response] Tool: {tool_name}, success: {result_data.get('success')}")

        if result_data.get("success"):
            data = result_data.get("data", {})
            logger.debug(f"[_create_success_response] Data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")

            if "sources" in data:
                raw_sources = data["sources"]
                logger.info(f"[_create_success_response] Found {len(raw_sources)} sources in {tool_name}")

                for src in raw_sources[:3]:  # 최대 3개
                    if isinstance(src, dict):
                        # RAG workflow extract_sources() 반환 형식 매핑:
                        # title, case_number, court, date, doc_type, relevance_score, text_snippet, full_text
                        source_item = {
                            "title": src.get("title", src.get("case_name", "출처")),
                            # text_snippet 또는 full_text 사용
                            "content": (src.get("text_snippet") or src.get("full_text") or src.get("text") or "")[:500],
                            "case_number": src.get("case_number", src.get("source", "")),
                            "court": src.get("court", ""),
                            "date": src.get("date", src.get("decision_date", "")),
                            # relevance_score 또는 score 사용
                            "score": src.get("relevance_score", src.get("score", 0)),
                            "doc_type": src.get("doc_type", src.get("type", "precedent")),
                            "doc_id": src.get("doc_id", src.get("id", "")),
                        }
                        sources.append(source_item)
                        logger.debug(f"[_create_success_response] Added source: {source_item.get('title', 'no title')[:50]}")

    logger.info(f"[_create_success_response] Total sources extracted: {len(sources)}")

    # complete 이벤트 (실제 응답 포함) - agent_hub.py에서 final_response 추출에 필요
    complete_event = StreamingEvent(
        event="complete",
        data={
            "response": content,
            "format": "text",
            "status": "success",
            "tool_calls": total_tool_calls,
            "max_reached": max_reached,
            "sources": sources[:3],  # 최대 3개 소스
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(complete_event.model_dump())

    return {
        "final_response": content,
        "workflow_results": {
            "tool_results": tool_results,
            "total_tool_calls": total_tool_calls,
            "sources": sources,
        },
        "response_metadata": {
            "path": path,
            "tool_calls": total_tool_calls,
            "max_reached": max_reached,
        },
        "streaming_events": streaming_events,
    }


def _create_error_response(
    error: str,
    streaming_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """에러 응답 생성"""
    error_response = f"죄송합니다, 처리 중 오류가 발생했습니다: {error}"

    error_event = StreamingEvent(
        event="error",
        data={"error": error},
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(error_event.model_dump())

    # complete 이벤트 (에러 응답 포함) - agent_hub.py에서 final_response 추출에 필요
    complete_event = StreamingEvent(
        event="complete",
        data={
            "response": error_response,
            "format": "text",
            "status": "error",
            "error": error,
        },
        timestamp=datetime.now().isoformat(),
    )
    streaming_events.append(complete_event.model_dump())

    return {
        "errors": [{"step": "tool_use_agent", "error": error}],
        "final_response": error_response,
        "response_metadata": {
            "path": "tool_use_agent",
            "error": True,
        },
        "streaming_events": streaming_events,
    }


# =============================================================================
# 동기 버전 (LangGraph 호환)
# =============================================================================

def tool_use_agent_node_sync(state: ExtendedMasterAgentState) -> Dict[str, Any]:
    """Tool Use Agent 노드 (동기 버전)"""
    import asyncio
    return asyncio.run(tool_use_agent_node(state))
