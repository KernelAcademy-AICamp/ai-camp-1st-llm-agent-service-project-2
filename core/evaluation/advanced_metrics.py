"""
Advanced RAG Evaluation Metrics using RAGAS
LLM 기반 고급 평가 메트릭 (Faithfulness, Answer Relevance, Context Relevance)
"""

from typing import List, Dict, Any, Optional
import os


def calculate_ragas_metrics(
    query: str,
    answer: str,
    contexts: List[str],
    ground_truth: Optional[str] = None,
    use_ragas: bool = True
) -> Dict[str, float]:
    """
    Calculate RAGAS metrics for RAG evaluation.

    Args:
        query: User question
        answer: Generated answer
        contexts: Retrieved context documents
        ground_truth: Ground truth answer (optional, for correctness)
        use_ragas: Whether to use RAGAS (requires OpenAI API key)

    Returns:
        Dictionary of RAGAS metrics
    """
    if not use_ragas or not os.getenv('OPENAI_API_KEY'):
        return {
            'faithfulness': None,
            'answer_relevancy': None,
            'context_precision': None,
            'context_recall': None,
            'note': 'RAGAS disabled or no OpenAI API key'
        }

    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        )
        from datasets import Dataset

        # Prepare dataset for RAGAS
        data = {
            'question': [query],
            'answer': [answer],
            'contexts': [contexts],
        }

        # Add ground truth if available
        if ground_truth:
            data['ground_truth'] = [ground_truth]

        dataset = Dataset.from_dict(data)

        # Select metrics based on available data
        metrics_to_use = [faithfulness, answer_relevancy]

        if ground_truth:
            metrics_to_use.extend([context_precision, context_recall])

        # Run RAGAS evaluation
        result = evaluate(dataset, metrics=metrics_to_use)

        # Extract scores
        return {
            'faithfulness': float(result.get('faithfulness', 0)),
            'answer_relevancy': float(result.get('answer_relevancy', 0)),
            'context_precision': float(result.get('context_precision', 0)) if ground_truth else None,
            'context_recall': float(result.get('context_recall', 0)) if ground_truth else None,
        }

    except ImportError:
        return {
            'faithfulness': None,
            'answer_relevancy': None,
            'context_precision': None,
            'context_recall': None,
            'note': 'RAGAS not installed. Run: pip install ragas'
        }
    except Exception as e:
        print(f"⚠️  RAGAS evaluation failed: {e}")
        return {
            'faithfulness': None,
            'answer_relevancy': None,
            'context_precision': None,
            'context_recall': None,
            'error': str(e)
        }


def calculate_ndcg(retrieved_docs: List[Dict], relevant_docs: List[str], k: int = 5) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain (NDCG@K).

    Args:
        retrieved_docs: Retrieved documents with relevance scores
        relevant_docs: List of relevant document IDs
        k: Number of top documents to consider

    Returns:
        NDCG score (0-1)
    """
    import numpy as np

    if not retrieved_docs or not relevant_docs:
        return 0.0

    # Get top-k documents
    top_k = retrieved_docs[:k]

    # Calculate relevance scores (1 if relevant, 0 if not)
    relevance_scores = []
    for doc in top_k:
        doc_id = doc.get('metadata', {}).get('doc_id', '')
        is_relevant = any(rel_id in str(doc_id) for rel_id in relevant_docs)
        relevance_scores.append(1.0 if is_relevant else 0.0)

    # Calculate DCG (Discounted Cumulative Gain)
    dcg = 0.0
    for i, rel in enumerate(relevance_scores, 1):
        dcg += rel / np.log2(i + 1)

    # Calculate IDCG (Ideal DCG)
    ideal_relevance = sorted(relevance_scores, reverse=True)
    idcg = 0.0
    for i, rel in enumerate(ideal_relevance, 1):
        idcg += rel / np.log2(i + 1)

    # NDCG
    if idcg == 0:
        return 0.0

    ndcg = dcg / idcg
    return round(float(ndcg), 4)


def calculate_hit_rate(retrieved_docs: List[Dict], relevant_docs: List[str], k: int = 5) -> float:
    """
    Calculate Hit Rate@K (also known as Recall@K in some contexts).
    Measures if at least one relevant document is in top-K.

    Args:
        retrieved_docs: Retrieved documents
        relevant_docs: List of relevant document IDs
        k: Number of top documents to consider

    Returns:
        Hit rate (0 or 1)
    """
    if not retrieved_docs or not relevant_docs:
        return 0.0

    top_k = retrieved_docs[:k]

    # Check if any relevant doc is in top-k
    for doc in top_k:
        doc_id = doc.get('metadata', {}).get('doc_id', '')
        if any(rel_id in str(doc_id) for rel_id in relevant_docs):
            return 1.0

    return 0.0


def calculate_token_usage(prompt: str, answer: str, model: str = "gpt-3.5-turbo") -> Dict[str, int]:
    """
    Estimate token usage for LLM calls.

    Args:
        prompt: Input prompt
        answer: Generated answer
        model: Model name

    Returns:
        Dictionary with token counts
    """
    try:
        import tiktoken

        # Get encoding for model
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        # Count tokens
        prompt_tokens = len(encoding.encode(prompt))
        completion_tokens = len(encoding.encode(answer))
        total_tokens = prompt_tokens + completion_tokens

        return {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens
        }

    except ImportError:
        return {
            'prompt_tokens': None,
            'completion_tokens': None,
            'total_tokens': None,
            'note': 'tiktoken not installed'
        }
    except Exception as e:
        return {
            'prompt_tokens': None,
            'completion_tokens': None,
            'total_tokens': None,
            'error': str(e)
        }


def evaluate_answer_advanced(
    query: str,
    answer: str,
    contexts: List[str],
    ground_truth: Optional[str] = None,
    relevant_docs: Optional[List[str]] = None,
    retrieved_docs: Optional[List[Dict]] = None,
    use_ragas: bool = False,
    k: int = 5
) -> Dict[str, Any]:
    """
    Comprehensive advanced evaluation combining all metrics.

    Args:
        query: User question
        answer: Generated answer
        contexts: Retrieved context texts
        ground_truth: Ground truth answer (optional)
        relevant_docs: List of relevant doc IDs (for retrieval metrics)
        retrieved_docs: Full retrieved documents with metadata
        use_ragas: Whether to use RAGAS (requires OpenAI API)
        k: Top-K for retrieval metrics

    Returns:
        Dictionary of all advanced metrics
    """
    metrics = {}

    # RAGAS metrics (if enabled)
    if use_ragas:
        ragas_metrics = calculate_ragas_metrics(
            query=query,
            answer=answer,
            contexts=contexts,
            ground_truth=ground_truth,
            use_ragas=True
        )
        metrics.update(ragas_metrics)

    # Additional retrieval metrics
    if retrieved_docs and relevant_docs:
        metrics['ndcg'] = calculate_ndcg(retrieved_docs, relevant_docs, k)
        metrics['hit_rate'] = calculate_hit_rate(retrieved_docs, relevant_docs, k)

    # Token usage
    metrics['token_usage'] = calculate_token_usage(query, answer)

    return metrics
