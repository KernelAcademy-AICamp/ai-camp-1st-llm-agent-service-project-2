"""
RAG Evaluation Metrics
답변 품질 평가를 위한 메트릭 모듈
"""

from typing import List, Dict, Any
import re
from collections import Counter


def calculate_bleu(reference: str, candidate: str, n: int = 4) -> float:
    """
    Calculate BLEU score (간단 버전).

    Args:
        reference: 정답 문장
        candidate: 생성된 답변
        n: n-gram (기본 4)

    Returns:
        BLEU score (0-1)
    """
    try:
        from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

        # 토큰화 (간단하게 공백 기준)
        ref_tokens = reference.split()
        cand_tokens = candidate.split()

        # BLEU 계산
        smoothing = SmoothingFunction().method1
        score = sentence_bleu([ref_tokens], cand_tokens,
                             weights=(0.25, 0.25, 0.25, 0.25),
                             smoothing_function=smoothing)
        return round(score, 4)

    except ImportError:
        # NLTK 없으면 간단한 단어 겹침 비율로 근사
        ref_words = set(reference.split())
        cand_words = set(candidate.split())

        if not cand_words:
            return 0.0

        overlap = len(ref_words & cand_words)
        return round(overlap / len(cand_words), 4)


def calculate_rouge_l(reference: str, candidate: str) -> float:
    """
    Calculate ROUGE-L score (Longest Common Subsequence 기반).

    Args:
        reference: 정답 문장
        candidate: 생성된 답변

    Returns:
        ROUGE-L F1 score (0-1)
    """
    def lcs_length(s1: List[str], s2: List[str]) -> int:
        """Longest Common Subsequence 길이 계산."""
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])

        return dp[m][n]

    ref_tokens = reference.split()
    cand_tokens = candidate.split()

    if not ref_tokens or not cand_tokens:
        return 0.0

    lcs_len = lcs_length(ref_tokens, cand_tokens)

    # ROUGE-L Recall, Precision, F1
    recall = lcs_len / len(ref_tokens) if ref_tokens else 0
    precision = lcs_len / len(cand_tokens) if cand_tokens else 0

    if recall + precision == 0:
        return 0.0

    f1 = 2 * (recall * precision) / (recall + precision)
    return round(f1, 4)


def calculate_semantic_similarity(reference: str, candidate: str, embedder=None) -> float:
    """
    Calculate semantic similarity using embeddings.

    Args:
        reference: 정답 문장
        candidate: 생성된 답변
        embedder: 임베딩 모델 (None이면 간단한 방법 사용)

    Returns:
        Cosine similarity (0-1)
    """
    if embedder is None:
        # 임베딩 없으면 단어 겹침으로 근사
        ref_words = set(reference.split())
        cand_words = set(candidate.split())

        if not ref_words or not cand_words:
            return 0.0

        overlap = len(ref_words & cand_words)
        union = len(ref_words | cand_words)

        return round(overlap / union if union > 0 else 0.0, 4)

    # 임베딩 기반 유사도
    try:
        ref_emb = embedder.embed(reference)
        cand_emb = embedder.embed(candidate)

        # Cosine similarity
        import numpy as np
        dot_product = np.dot(ref_emb, cand_emb)
        norm_ref = np.linalg.norm(ref_emb)
        norm_cand = np.linalg.norm(cand_emb)

        if norm_ref == 0 or norm_cand == 0:
            return 0.0

        similarity = dot_product / (norm_ref * norm_cand)
        return round(float(similarity), 4)

    except Exception as e:
        print(f"⚠️ Semantic similarity calculation failed: {e}")
        return 0.0


def calculate_exact_match(reference: str, candidate: str) -> bool:
    """
    Exact match check (정규화 후).

    Args:
        reference: 정답 문장
        candidate: 생성된 답변

    Returns:
        True if exact match
    """
    # 정규화: 소문자, 공백 제거, 특수문자 제거
    def normalize(text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    return normalize(reference) == normalize(candidate)


def calculate_f1_score(reference: str, candidate: str) -> float:
    """
    Token-level F1 score.

    Args:
        reference: 정답 문장
        candidate: 생성된 답변

    Returns:
        F1 score (0-1)
    """
    ref_tokens = reference.split()
    cand_tokens = candidate.split()

    if not ref_tokens or not cand_tokens:
        return 0.0

    ref_counter = Counter(ref_tokens)
    cand_counter = Counter(cand_tokens)

    # True Positives: 겹치는 토큰
    common = ref_counter & cand_counter
    tp = sum(common.values())

    if tp == 0:
        return 0.0

    precision = tp / len(cand_tokens)
    recall = tp / len(ref_tokens)

    f1 = 2 * (precision * recall) / (precision + recall)
    return round(f1, 4)


def evaluate_answer(reference: str, candidate: str, embedder=None) -> Dict[str, Any]:
    """
    답변 종합 평가.

    Args:
        reference: 정답
        candidate: 생성된 답변
        embedder: 임베딩 모델 (선택)

    Returns:
        평가 메트릭 딕셔너리
    """
    return {
        'exact_match': calculate_exact_match(reference, candidate),
        'f1_score': calculate_f1_score(reference, candidate),
        'bleu': calculate_bleu(reference, candidate),
        'rouge_l': calculate_rouge_l(reference, candidate),
        'semantic_similarity': calculate_semantic_similarity(reference, candidate, embedder)
    }


def calculate_retrieval_metrics(retrieved_docs: List[Dict], relevant_docs: List[str], k: int = 5) -> Dict[str, float]:
    """
    검색 성능 평가 메트릭.

    Args:
        retrieved_docs: 검색된 문서 리스트
        relevant_docs: 관련 문서 ID 리스트
        k: Top-K

    Returns:
        검색 메트릭 딕셔너리
    """
    if not retrieved_docs or not relevant_docs:
        return {
            'precision_at_k': 0.0,
            'recall_at_k': 0.0,
            'mrr': 0.0,
            'map': 0.0
        }

    # Top-K 문서만 평가
    top_k_docs = retrieved_docs[:k]

    # 관련 문서 개수 카운트
    retrieved_relevant = 0
    first_relevant_rank = None

    for idx, doc in enumerate(top_k_docs, 1):
        doc_id = doc.get('metadata', {}).get('doc_id', '')

        # 관련 문서인지 확인
        is_relevant = any(rel_id in str(doc_id) for rel_id in relevant_docs)

        if is_relevant:
            retrieved_relevant += 1
            if first_relevant_rank is None:
                first_relevant_rank = idx

    # Precision@K
    precision_at_k = retrieved_relevant / k if k > 0 else 0.0

    # Recall@K
    recall_at_k = retrieved_relevant / len(relevant_docs) if relevant_docs else 0.0

    # MRR (Mean Reciprocal Rank)
    mrr = 1.0 / first_relevant_rank if first_relevant_rank else 0.0

    # MAP (Mean Average Precision) - 간단 버전
    map_score = precision_at_k  # 단일 쿼리에서는 P@K와 동일

    return {
        'precision_at_k': round(precision_at_k, 4),
        'recall_at_k': round(recall_at_k, 4),
        'mrr': round(mrr, 4),
        'map': round(map_score, 4)
    }
