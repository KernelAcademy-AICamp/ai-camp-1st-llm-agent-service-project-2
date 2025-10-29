"""Evaluation module for RAG pipeline."""

from .metrics import (
    evaluate_answer,
    calculate_retrieval_metrics,
    calculate_bleu,
    calculate_rouge_l,
    calculate_semantic_similarity,
    calculate_exact_match,
    calculate_f1_score
)

from .advanced_metrics import (
    calculate_ragas_metrics,
    calculate_ndcg,
    calculate_hit_rate,
    calculate_token_usage,
    evaluate_answer_advanced
)

__all__ = [
    # Basic metrics
    'evaluate_answer',
    'calculate_retrieval_metrics',
    'calculate_bleu',
    'calculate_rouge_l',
    'calculate_semantic_similarity',
    'calculate_exact_match',
    'calculate_f1_score',
    # Advanced metrics
    'calculate_ragas_metrics',
    'calculate_ndcg',
    'calculate_hit_rate',
    'calculate_token_usage',
    'evaluate_answer_advanced'
]
