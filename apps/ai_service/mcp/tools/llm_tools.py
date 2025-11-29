"""
LLM Comparison MCP Tools

Phase 4 - Week 12: LLM 비교 MCP Tools

도구 목록:
- execute_on_model: 특정 LLM 모델에서 작업 실행
- get_model_metadata: 모델 메타데이터 조회
- calculate_llm_metrics: LLM 결과 평가 메트릭 계산
- store_comparison_log: 비교 로그 저장

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""

from typing import Dict, Any, Optional, List
import logging
import time

logger = logging.getLogger(__name__)


async def execute_on_model(
    model_name: str,
    task: str,
    input_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    특정 LLM 모델에서 작업 실행

    Args:
        model_name: 모델 이름 ("gpt-4", "claude-3", "gemini-pro" 등)
        task: 작업 유형 ("summarize", "analyze", "extract_clauses" 등)
        input_data: 입력 데이터

    Returns:
        실행 결과
        - result: 실행 결과 텍스트
        - latency: 응답 시간 (초)
        - tokens: 출력 토큰 수
        - cost: 예상 비용 (USD)
    """
    logger.info(f"Executing task '{task}' on model: {model_name}")

    start_time = time.time()

    try:
        # 모델 초기화
        if model_name.startswith("gpt"):
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=model_name)
        elif model_name.startswith("claude"):
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model=model_name)
        else:
            # 기본값으로 프로젝트 LLM 클라이언트 사용
            from libs.rag_core.llm.llm_client import get_llm
            llm = get_llm(model=model_name)

        # 작업별 프롬프트 생성
        if task == "summarize":
            prompt = f"다음 문서를 요약하세요:\n\n{input_data.get('text', '')}"
        elif task == "analyze":
            prompt = f"다음 내용을 분석하세요:\n\n{input_data.get('text', '')}"
        elif task == "extract_clauses":
            prompt = f"다음 계약서의 핵심 조항을 추출하세요:\n\n{input_data.get('text', '')}"
        else:
            prompt = input_data.get("prompt", str(input_data))

        # 실행
        result = await llm.ainvoke(prompt)

        latency = time.time() - start_time
        content = result.content if hasattr(result, 'content') else str(result)

        # 토큰 및 비용 계산 (추정)
        tokens = len(content.split())
        cost = tokens * 0.00001  # 임시 비용 계산

        return {
            "result": content,
            "latency": round(latency, 3),
            "tokens": tokens,
            "cost": round(cost, 6),
            "model": model_name,
            "task": task
        }

    except Exception as e:
        logger.error(f"Error executing on model {model_name}: {e}")
        return {
            "error": str(e),
            "result": "",
            "latency": time.time() - start_time,
            "tokens": 0,
            "cost": 0.0,
            "model": model_name,
            "task": task
        }


async def get_model_metadata(model_name: str) -> Dict[str, Any]:
    """
    모델 메타데이터 조회

    Args:
        model_name: 모델 이름

    Returns:
        모델 메타데이터
        - provider: 제공자
        - max_tokens: 최대 토큰
        - cost_per_token: 토큰당 비용
        - capabilities: 기능 리스트
    """
    logger.info(f"Getting metadata for model: {model_name}")

    # 모델 메타데이터 (실제로는 DB에서 조회)
    model_info = {
        "gpt-4": {
            "provider": "openai",
            "max_tokens": 8192,
            "cost_per_1k_input": 0.03,
            "cost_per_1k_output": 0.06,
            "capabilities": ["text-generation", "analysis", "summarization"]
        },
        "gpt-4-turbo": {
            "provider": "openai",
            "max_tokens": 128000,
            "cost_per_1k_input": 0.01,
            "cost_per_1k_output": 0.03,
            "capabilities": ["text-generation", "analysis", "summarization", "vision"]
        },
        "claude-3-opus": {
            "provider": "anthropic",
            "max_tokens": 200000,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "capabilities": ["text-generation", "analysis", "summarization", "code"]
        },
        "claude-3-sonnet": {
            "provider": "anthropic",
            "max_tokens": 200000,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "capabilities": ["text-generation", "analysis", "summarization"]
        },
        "gemini-pro": {
            "provider": "google",
            "max_tokens": 32000,
            "cost_per_1k_input": 0.0005,
            "cost_per_1k_output": 0.0015,
            "capabilities": ["text-generation", "analysis"]
        }
    }

    # 기본 매칭
    for key, info in model_info.items():
        if key in model_name.lower():
            return {
                "model_name": model_name,
                **info
            }

    # 기본값
    return {
        "model_name": model_name,
        "provider": "unknown",
        "max_tokens": 4096,
        "cost_per_1k_input": 0.01,
        "cost_per_1k_output": 0.01,
        "capabilities": ["text-generation"]
    }


async def calculate_llm_metrics(
    results: Dict[str, Any],
    task: str,
    ground_truth: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    LLM 결과 평가 메트릭 계산

    Args:
        results: 모델별 결과 (model_name -> result)
        task: 작업 유형
        ground_truth: 정답 (있는 경우)

    Returns:
        모델별 메트릭
        - quality: 품질 점수 (0-1)
        - latency_normalized: 정규화된 지연 시간
        - cost_normalized: 정규화된 비용
    """
    logger.info(f"Calculating LLM metrics for task: {task}")

    metrics = {}

    # 정규화를 위한 최대값 수집
    latencies = []
    costs = []

    for model_name, result in results.items():
        if isinstance(result, dict):
            latencies.append(result.get("latency", 0))
            costs.append(result.get("cost", 0))

    max_latency = max(latencies) if latencies else 1.0
    max_cost = max(costs) if costs else 1.0

    for model_name, result in results.items():
        if isinstance(result, dict) and "error" not in result:
            content = result.get("result", "")
            latency = result.get("latency", 0)
            cost = result.get("cost", 0)

            # 품질 점수 (휴리스틱)
            quality = 0.7
            word_count = len(str(content).split())
            if word_count > 50:
                quality += 0.1
            if word_count > 200:
                quality += 0.1
            if word_count < 10:
                quality -= 0.2

            # ground_truth 비교
            if ground_truth:
                result_words = set(str(content).split())
                truth_words = set(ground_truth.split())
                if truth_words:
                    overlap = len(result_words & truth_words)
                    union = len(result_words | truth_words)
                    similarity = overlap / union if union > 0 else 0
                    quality = min(1.0, quality * 0.5 + similarity * 0.5)

            metrics[model_name] = {
                "quality": round(min(1.0, max(0.0, quality)), 3),
                "latency": latency,
                "latency_normalized": round(latency / max_latency, 3) if max_latency > 0 else 0,
                "cost": cost,
                "cost_normalized": round(cost / max_cost, 3) if max_cost > 0 else 0,
                "tokens": result.get("tokens", 0)
            }
        else:
            # 에러 결과
            metrics[model_name] = {
                "quality": 0.0,
                "latency": 0.0,
                "latency_normalized": 1.0,
                "cost": 0.0,
                "cost_normalized": 0.0,
                "error": result.get("error", "Unknown error") if isinstance(result, dict) else "Invalid result"
            }

    return metrics


async def store_comparison_log(comparison_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    비교 로그 저장

    Args:
        comparison_data: 비교 데이터
        - task: 작업 유형
        - models: 비교한 모델 리스트
        - results: 모델별 결과
        - metrics: 모델별 메트릭
        - best_model: 선택된 최적 모델
        - user_preference: 사용자 선택 (있는 경우)

    Returns:
        저장 결과
        - log_id: 로그 ID
        - saved_at: 저장 시간
    """
    logger.info("Storing comparison log")

    try:
        import uuid
        from datetime import datetime

        log_id = str(uuid.uuid4())
        saved_at = datetime.now().isoformat()

        # 실제로는 DB에 저장
        # await ComparisonLog.objects.acreate(
        #     log_id=log_id,
        #     task=comparison_data.get("task"),
        #     models=comparison_data.get("models"),
        #     results=comparison_data.get("results"),
        #     metrics=comparison_data.get("metrics"),
        #     best_model=comparison_data.get("best_model"),
        #     user_preference=comparison_data.get("user_preference"),
        #     created_at=datetime.now()
        # )

        logger.info(f"Comparison log saved: {log_id}")

        return {
            "log_id": log_id,
            "saved_at": saved_at,
            "status": "saved"
        }

    except Exception as e:
        logger.error(f"Error storing comparison log: {e}")
        return {
            "error": str(e),
            "status": "failed"
        }


async def select_best_model(
    metrics: Dict[str, Dict[str, Any]],
    criteria: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    최적 모델 선택

    Args:
        metrics: 모델별 메트릭
        criteria: 가중치 기준 (quality, latency, cost)

    Returns:
        선택 결과
        - best_model: 최적 모델 이름
        - score: 종합 점수
        - reasoning: 선택 이유
    """
    logger.info("Selecting best model")

    # 기본 가중치
    default_criteria = {
        "quality": 0.5,
        "latency": 0.3,
        "cost": 0.2
    }

    criteria = criteria or default_criteria

    scores = {}

    for model_name, metric in metrics.items():
        if "error" in metric:
            scores[model_name] = 0.0
            continue

        # 종합 점수 계산
        quality = metric.get("quality", 0)
        latency_norm = metric.get("latency_normalized", 0.5)
        cost_norm = metric.get("cost_normalized", 0.5)

        score = (
            quality * criteria.get("quality", 0.5) +
            (1 - latency_norm) * criteria.get("latency", 0.3) +
            (1 - cost_norm) * criteria.get("cost", 0.2)
        )

        scores[model_name] = round(score, 3)

    if not scores:
        return {
            "best_model": None,
            "score": 0.0,
            "reasoning": "No valid models to compare"
        }

    best_model = max(scores, key=scores.get)

    return {
        "best_model": best_model,
        "score": scores[best_model],
        "scores": scores,
        "reasoning": f"{best_model} achieved the highest weighted score ({scores[best_model]:.3f})"
    }
