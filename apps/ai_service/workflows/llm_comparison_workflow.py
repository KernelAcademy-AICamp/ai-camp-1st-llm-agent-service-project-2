"""
LLM Comparison Workflow

Phase 4 - Week 12: LLM 비교 워크플로우 구현

워크플로우 구조:
1. dispatch_to_models_node: 여러 모델에 병렬로 작업 전송
2. evaluate_results_node: 각 모델 결과 평가
3. check_agreement_node: 모델 간 결과 일치도 확인
4. [conditional] user_choice_node: 결과 불일치 시 사용자 선택 (Human-in-the-Loop)
5. select_best_model_node: 최적 모델 선택

그래프 구조:
dispatch → evaluate → check_agreement → [agree: select, disagree: user_choice] → select → END

Checkpointing: 필수 (Human-in-the-Loop, TTL: 1시간)
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_core.runnables import RunnableConfig

from apps.ai_service.workflows.states.llm_comparison_state import (
    LLMComparisonState,
    ModelMetrics,
)

logger = logging.getLogger(__name__)

# 일치도 임계값 (이 값 미만이면 사용자 선택 필요)
AGREEMENT_THRESHOLD = 0.8


# =============================================================================
# Node Functions
# =============================================================================

async def dispatch_to_models_node(
    state: LLMComparisonState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """여러 모델에 병렬로 작업 전송 (직접 LLM 클라이언트 호출)"""
    logger.info("Starting dispatch_to_models_node")

    async def execute_on_model(model_name: str, provider: str, task: str, input_data: dict) -> str:
        """단일 모델에서 작업 실행"""
        import os
        try:
            from libs.rag_core.llm.llm_client import create_llm_client

            # 모델 이름에서 provider 추론 (명시적으로 전달되지 않은 경우)
            if not provider:
                if 'gpt' in model_name.lower() or 'openai' in model_name.lower():
                    provider = 'openai'
                elif 'claude' in model_name.lower():
                    provider = 'anthropic'
                elif 'gemini' in model_name.lower():
                    provider = 'google'
                else:
                    provider = 'openai'  # 기본값

            # API 키 가져오기
            if provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY', '')
            elif provider == 'anthropic':
                api_key = os.getenv('CLAUDE_API_KEY', os.getenv('ANTHROPIC_API_KEY', ''))
            elif provider == 'google':
                api_key = os.getenv('GEMINI_API_KEY', os.getenv('GOOGLE_API_KEY', ''))
            else:
                api_key = os.getenv('LLM_API_KEY', '')

            if not api_key:
                return f"[Error: API key not configured for provider {provider}]"

            # 클라이언트 생성
            client = create_llm_client(
                provider=provider,
                api_key=api_key,
                model=model_name
            )

            # 프롬프트 생성
            prompt = f"{task}\n\n입력: {input_data}"

            # 동기 호출을 비동기로 실행 (LLMClient는 동기 메서드만 있음)
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, client.generate, prompt)

            return result
        except Exception as e:
            logger.error(f"Error executing on model {model_name}: {e}")
            return f"[Error: {str(e)}]"

    model_configs = state.get("model_configs", [])
    task = state.get("task", "summarize")
    input_data = state.get("input_data", {})

    if not model_configs:
        return {
            "results": {},
            "error": "No model configs provided",
            "completed_tasks": state.get("completed_tasks", []) + ["dispatch_to_models"],
        }

    # 병렬 실행
    tasks = [
        execute_on_model(
            model_config.get("model_name", "gpt-4"),
            model_config.get("provider", ""),
            task,
            input_data
        )
        for model_config in model_configs
    ]

    # 동시 실행
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    # 결과 저장
    results = {}
    for model_config, result in zip(model_configs, results_list):
        model_name = model_config.get("model_name", "unknown")
        if isinstance(result, Exception):
            results[model_name] = f"[Error: {str(result)}]"
        else:
            results[model_name] = result

    logger.info(f"Dispatched to {len(results)} models")

    return {
        "results": results,
        "completed_tasks": state.get("completed_tasks", []) + ["dispatch_to_models"],
    }


async def evaluate_results_node(
    state: LLMComparisonState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """각 모델 결과 평가 (직접 메트릭 계산)"""
    logger.info("Starting evaluate_results_node")

    results = state.get("results", {})
    evaluation_metrics: Dict[str, ModelMetrics] = {}

    # 메트릭 수집
    latencies = []
    costs = []

    for model_name, result in results.items():
        if isinstance(result, str) and result.startswith("[Error"):
            # 에러 결과는 낮은 품질로 처리
            metrics: ModelMetrics = {
                "latency": 999.0,
                "token_count": 0,
                "quality": 0.0,
                "cost": 0.0,
                "latency_normalized": None,
                "cost_normalized": None,
            }
        else:
            # 간단한 메트릭 계산 (실제로는 측정된 값 사용)
            token_count = len(str(result).split())
            latency = 0.5 + (token_count * 0.01)  # 추정 지연 시간
            cost = 0.01 * token_count  # 토큰 기반 비용 추정

            metrics: ModelMetrics = {
                "latency": latency,
                "token_count": token_count,
                "quality": 0.8,  # 실제로는 별도 평가 로직 필요
                "cost": cost,
                "latency_normalized": None,
                "cost_normalized": None,
            }

            latencies.append(latency)
            costs.append(cost)

        evaluation_metrics[model_name] = metrics

    # 정규화 (0-1 범위)
    if latencies:
        max_latency = max(latencies)
        max_cost = max(costs) if costs else 1.0

        for model_name, metrics in evaluation_metrics.items():
            if metrics["latency"] < 999:
                metrics["latency_normalized"] = metrics["latency"] / max_latency if max_latency > 0 else 0
                metrics["cost_normalized"] = metrics["cost"] / max_cost if max_cost > 0 else 0

    logger.info(f"Evaluated {len(evaluation_metrics)} model results")

    return {
        "evaluation_metrics": evaluation_metrics,
        "completed_tasks": state.get("completed_tasks", []) + ["evaluate_results"],
    }


async def check_agreement_node(
    state: LLMComparisonState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """모델 간 결과 일치도 확인"""
    logger.info("Starting check_agreement_node")

    results = state.get("results", {})
    valid_results = [
        r for r in results.values()
        if isinstance(r, str) and not r.startswith("[Error")
    ]

    if len(valid_results) < 2:
        # 비교할 결과가 부족하면 일치로 간주
        agreement_score = 1.0
    else:
        # 간단한 일치도 계산: 결과 길이 및 공통 단어 비율
        # 실제로는 BLEU, ROUGE, 또는 의미론적 유사도 사용 권장
        word_sets = [set(r.split()) for r in valid_results]

        if len(word_sets) >= 2:
            # Jaccard similarity 기반 일치도
            intersection = word_sets[0]
            union = word_sets[0]

            for ws in word_sets[1:]:
                intersection = intersection & ws
                union = union | ws

            agreement_score = len(intersection) / len(union) if union else 0.0
        else:
            agreement_score = 1.0

    logger.info(f"Agreement score: {agreement_score}")

    return {
        "agreement_score": agreement_score,
        "completed_tasks": state.get("completed_tasks", []) + ["check_agreement"],
    }


async def user_choice_node(
    state: LLMComparisonState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """Human-in-the-loop: 사용자가 최적 모델 선택

    interrupt() 함수 동작 방식:
    1. interrupt()가 호출되면 워크플로우가 중단됨
    2. 클라이언트에서 Command(resume=value)로 재개 시
    3. interrupt()의 반환값으로 value가 전달됨
    """
    logger.info("Starting user_choice_node - waiting for human input")

    # interrupt로 워크플로우 중단
    # Command(resume="gpt-4")로 재개 시, choice = "gpt-4"
    choice = interrupt({
        "message": "Models produced different results. Please select the best one.",
        "results": state.get("results", {}),
        "metrics": state.get("evaluation_metrics", {}),
        "agreement_score": state.get("agreement_score", 0.0),
    })

    logger.info(f"User selected: {choice}")

    return {
        "user_preference": choice,
        "completed_tasks": state.get("completed_tasks", []) + ["user_choice"],
    }


async def select_best_model_node(
    state: LLMComparisonState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """최적 모델 선택"""
    logger.info("Starting select_best_model_node")

    user_preference = state.get("user_preference")
    metrics = state.get("evaluation_metrics", {})

    if user_preference:
        # 사용자 선택 우선
        best_model = user_preference
        logger.info(f"User preference selected: {best_model}")
    else:
        # 자동 선택: metrics 기반
        scores = {}

        for model_name, metric in metrics.items():
            if metric.get("quality", 0) == 0:
                # 에러 결과는 제외
                continue

            # 종합 점수 계산 (quality, latency, cost 가중 평균)
            quality = metric.get("quality", 0)
            latency_norm = metric.get("latency_normalized", 0.5)
            cost_norm = metric.get("cost_normalized", 0.5)

            score = (
                quality * 0.5 +
                (1 - latency_norm) * 0.3 +
                (1 - cost_norm) * 0.2
            )
            scores[model_name] = score

        if scores:
            best_model = max(scores, key=scores.get)
            logger.info(f"Auto-selected best model: {best_model} (score: {scores[best_model]:.3f})")
        else:
            # 기본값
            best_model = list(state.get("results", {}).keys())[0] if state.get("results") else None
            logger.warning(f"No valid metrics, defaulting to: {best_model}")

    return {
        "best_model": best_model,
        "completed_tasks": state.get("completed_tasks", []) + ["select_best_model"],
    }


# =============================================================================
# Routing Functions
# =============================================================================

def results_agree(state: LLMComparisonState) -> Literal["agree", "disagree"]:
    """결과 일치 여부 반환"""
    agreement_score = state.get("agreement_score", 0.0)
    if agreement_score >= AGREEMENT_THRESHOLD:
        logger.info(f"Results agree (score: {agreement_score})")
        return "agree"
    else:
        logger.info(f"Results disagree (score: {agreement_score}), routing to user_choice")
        return "disagree"


# =============================================================================
# Workflow Creation
# =============================================================================

def create_llm_comparison_workflow(checkpointer: Optional[Any] = None):
    """LLM 비교 워크플로우 생성

    Args:
        checkpointer: 체크포인터 (None이면 MemorySaver 사용)

    Returns:
        컴파일된 워크플로우
    """
    workflow = StateGraph(LLMComparisonState)

    # Nodes
    workflow.add_node("dispatch", dispatch_to_models_node)
    workflow.add_node("evaluate", evaluate_results_node)
    workflow.add_node("check_agreement", check_agreement_node)
    workflow.add_node("user_choice", user_choice_node)
    workflow.add_node("select", select_best_model_node)

    # Entry point
    workflow.set_entry_point("dispatch")

    # Edges
    workflow.add_edge("dispatch", "evaluate")
    workflow.add_edge("evaluate", "check_agreement")

    # Conditional: 결과 차이 크면 사용자 선택
    workflow.add_conditional_edges(
        "check_agreement",
        results_agree,
        {
            "agree": "select",
            "disagree": "user_choice"
        }
    )

    workflow.add_edge("user_choice", "select")
    workflow.add_edge("select", END)

    # LLM Comparison: Checkpointing 필수!
    # - Human-in-the-Loop (모델 결과 불일치 시 사용자 선택 대기)
    # - 비용 절감 (여러 LLM 호출 결과 보존, 재실행 방지)
    # - TTL: 1시간 (사용자 선택 대기 시간)
    # 프로덕션: RedisSaver(redis_client) 사용
    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


# =============================================================================
# Convenience Functions
# =============================================================================

async def run_llm_comparison(
    task: str,
    input_data: Dict[str, Any],
    model_configs: list,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """LLM 비교 워크플로우 실행 헬퍼

    Args:
        task: 수행할 작업 ("summarize", "analyze", "extract_clauses" 등)
        input_data: 입력 데이터
        model_configs: 비교할 모델 설정 리스트
        thread_id: 스레드 ID (체크포인팅용)

    Returns:
        워크플로우 실행 결과
    """
    import uuid

    workflow = create_llm_comparison_workflow()

    initial_state: LLMComparisonState = {
        "task": task,
        "input_data": input_data,
        "model_configs": model_configs,
        "results": {},
        "evaluation_metrics": {},
        "best_model": None,
        "user_preference": None,
        "agreement_score": 0.0,
        "completed_tasks": [],
        "error": None,
    }

    config = {
        "configurable": {
            "thread_id": thread_id or str(uuid.uuid4())
        }
    }

    result = await workflow.ainvoke(initial_state, config)

    return result


async def resume_llm_comparison(
    workflow,
    thread_id: str,
    user_choice: str,
) -> Dict[str, Any]:
    """중단된 LLM 비교 워크플로우 재개

    Args:
        workflow: 컴파일된 워크플로우
        thread_id: 스레드 ID
        user_choice: 사용자가 선택한 모델 이름

    Returns:
        워크플로우 실행 결과
    """
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    # Command(resume=...)로 워크플로우 재개
    result = await workflow.ainvoke(
        Command(resume=user_choice),
        config
    )

    return result
