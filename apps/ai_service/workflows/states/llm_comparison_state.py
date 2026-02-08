"""
LLM Comparison State

Phase 4 - Week 12: LLM 비교 워크플로우 상태 정의

LLM 비교 워크플로우:
1. dispatch_to_models_node: 여러 모델에 병렬로 작업 전송
2. evaluate_results_node: 각 모델 결과 평가
3. check_agreement_node: 모델 간 결과 일치도 확인
4. user_choice_node: 결과 불일치 시 사용자 선택 (Human-in-the-Loop)
5. select_best_model_node: 최적 모델 선택

Checkpointing: 필수 (Human-in-the-Loop, TTL: 1시간)
"""

from typing import TypedDict, List, Dict, Any, Optional


class LLMModelConfig(TypedDict):
    """LLM 모델 설정"""
    model_name: str  # "gpt-4" | "claude-3" | "gemini-pro" | etc.
    provider: Optional[str]  # "openai" | "anthropic" | "google" | etc.
    temperature: Optional[float]
    max_tokens: Optional[int]


class ModelMetrics(TypedDict):
    """모델 실행 메트릭"""
    latency: float  # 응답 시간 (초)
    token_count: int  # 출력 토큰 수
    quality: float  # 품질 점수 (0-1)
    cost: float  # 비용 (USD)
    latency_normalized: Optional[float]  # 정규화된 지연 시간
    cost_normalized: Optional[float]  # 정규화된 비용


class LLMComparisonState(TypedDict):
    """
    LLM 비교 워크플로우 상태

    Attributes:
        task: 수행할 작업 유형
        input_data: 입력 데이터
        model_configs: 비교할 모델 설정 리스트
        results: 모델별 결과 (model_name -> result)
        evaluation_metrics: 모델별 메트릭 (model_name -> metrics)
        best_model: 선택된 최적 모델
        user_preference: 사용자가 선택한 모델 (Human-in-the-Loop)
        agreement_score: 모델 간 일치도 (0-1)
        completed_tasks: 완료된 작업 목록
        error: 에러 메시지 (있는 경우)
    """
    task: str  # "summarize" | "analyze" | "extract_clauses" | etc.
    input_data: Dict[str, Any]
    model_configs: List[LLMModelConfig]
    results: Dict[str, Any]  # model_name -> result
    evaluation_metrics: Dict[str, ModelMetrics]  # model_name -> metrics
    best_model: Optional[str]
    user_preference: Optional[str]
    agreement_score: float
    completed_tasks: List[str]
    error: Optional[str]
