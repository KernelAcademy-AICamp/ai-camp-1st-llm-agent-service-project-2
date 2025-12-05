#!/usr/bin/env python3
"""
임베딩 모델 비교 벤치마크

ko-sroberta-multitask (768d) vs snowflake-arctic-embed-l-v2.0-ko (1024d)
동일한 청킹 전략으로 두 모델의 검색 성능을 비교합니다.
"""

import sys
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from tqdm import tqdm

# Project path setup
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "libs" / "rag_core"))

DATA_DIR = Path(__file__).parent / "isolated_comparison" / "data"


# ============================================================
# 테스트 쿼리
# ============================================================

TEST_QUERIES = [
    {
        "query": "음주운전 처벌 기준과 형량",
        "keywords": ["음주", "혈중알코올", "면허취소", "징역", "벌금"],
        "expected_section": "이유"
    },
    {
        "query": "사기죄 구성요건과 고의",
        "keywords": ["기망", "착오", "재산상 이익", "편취"],
        "expected_section": "판시사항"
    },
    {
        "query": "폭행죄와 상해죄의 구별 기준",
        "keywords": ["폭행", "상해", "신체", "치료일수"],
        "expected_section": "이유"
    },
    {
        "query": "절도죄 처벌과 양형 기준",
        "keywords": ["절취", "타인", "재물", "형량"],
        "expected_section": "이유"
    },
    {
        "query": "명예훼손 성립 요건",
        "keywords": ["명예", "사실적시", "공연히", "비방"],
        "expected_section": "판시사항"
    },
    {
        "query": "정당방위 인정 기준",
        "keywords": ["정당방위", "위법성", "긴급피난", "과잉방위"],
        "expected_section": "이유"
    },
    {
        "query": "공무집행방해죄 판단 기준",
        "keywords": ["공무원", "직무집행", "폭행", "협박"],
        "expected_section": "이유"
    },
    {
        "query": "교통사고 과실 비율 판단",
        "keywords": ["과실", "주의의무", "신호위반", "손해배상"],
        "expected_section": "이유"
    },
]


# ============================================================
# 데이터 로딩
# ============================================================

def load_embeddings_and_metadata(name: str) -> Tuple[np.ndarray, List[Dict]]:
    """임베딩과 메타데이터 로드"""
    embeddings_path = DATA_DIR / f"{name}_embeddings.npy"
    metadata_path = DATA_DIR / f"{name}_metadata.json"

    embeddings = np.load(embeddings_path)
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    return embeddings, metadata


# ============================================================
# 검색 및 평가
# ============================================================

def search(
    query_embedding: np.ndarray,
    chunk_embeddings: np.ndarray,
    chunks: List[Dict],
    top_k: int = 5
) -> List[Dict]:
    """벡터 검색"""
    # 코사인 유사도
    similarities = np.dot(chunk_embeddings, query_embedding) / (
        np.linalg.norm(chunk_embeddings, axis=1) * np.linalg.norm(query_embedding) + 1e-10
    )

    # Top-K
    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        chunk = chunks[idx]
        score = float(similarities[idx])
        results.append({
            "score": score,
            "text": chunk["text"],
            "metadata": chunk.get("metadata", {})
        })

    return results


def evaluate_results(
    results: List[Dict],
    query_info: Dict
) -> Dict[str, Any]:
    """검색 결과 평가"""
    scores = [r["score"] for r in results]

    # 키워드 히트 체크
    keyword_hits = 0
    for result in results:
        text = result["text"].lower()
        for keyword in query_info["keywords"]:
            if keyword in text:
                keyword_hits += 1
                break

    # 법적 판단 관련 키워드 포함 여부
    legal_keywords = ['판단', '이유', '판시', '결정', '요지', '조문', '법률']
    legal_hits = 0
    for result in results:
        text = result["text"]
        if any(kw in text for kw in legal_keywords):
            legal_hits += 1

    # Top-1 상세 분석
    top1_text = results[0]["text"] if results else ""
    top1_has_reasoning = any(kw in top1_text for kw in ['판단', '이유', '따라서', '그러므로'])

    return {
        "avg_score": float(np.mean(scores)),
        "max_score": float(max(scores)),
        "min_score": float(min(scores)),
        "keyword_hit_rate": keyword_hits / len(results),
        "legal_hit_rate": legal_hits / len(results),
        "top1_has_reasoning": top1_has_reasoning,
        "top1_preview": top1_text[:200]
    }


def run_benchmark(
    model_name: str,
    embeddings: np.ndarray,
    chunks: List[Dict],
    query_embeddings: np.ndarray
) -> Dict[str, Any]:
    """벤치마크 실행"""

    results = []

    for i, query_info in enumerate(TEST_QUERIES):
        query_emb = query_embeddings[i]
        search_results = search(query_emb, embeddings, chunks, top_k=5)
        evaluation = evaluate_results(search_results, query_info)
        evaluation["query"] = query_info["query"]
        evaluation["top_results"] = search_results[:3]  # 상위 3개만 저장
        results.append(evaluation)

    # 전체 통계
    avg_scores = [r["avg_score"] for r in results]
    keyword_rates = [r["keyword_hit_rate"] for r in results]
    legal_rates = [r["legal_hit_rate"] for r in results]
    reasoning_hits = sum(1 for r in results if r["top1_has_reasoning"])

    return {
        "model": model_name,
        "overall_avg_score": float(np.mean(avg_scores)),
        "overall_keyword_hit": float(np.mean(keyword_rates) * 100),
        "overall_legal_hit": float(np.mean(legal_rates) * 100),
        "top1_reasoning_rate": reasoning_hits / len(results) * 100,
        "query_results": results
    }


# ============================================================
# 메인
# ============================================================

def main():
    print("=" * 70)
    print("임베딩 모델 비교 벤치마크")
    print("ko-sroberta (768d) vs snowflake-arctic (1024d)")
    print("=" * 70)

    # 데이터 로드
    print("\n📥 데이터 로딩...")

    # 동일 청킹 전략으로 두 모델 비교 (법률특화 청킹 사용)
    legal_kosroberta_emb, legal_kosroberta_chunks = load_embeddings_and_metadata("legal_kosroberta")
    legal_arctic_emb, legal_arctic_chunks = load_embeddings_and_metadata("legal_arctic")

    # 고정 청킹에서도 비교
    fixed_kosroberta_emb, fixed_kosroberta_chunks = load_embeddings_and_metadata("fixed_kosroberta")
    fixed_arctic_emb, fixed_arctic_chunks = load_embeddings_and_metadata("fixed_arctic")

    print(f"   법률특화 청킹: {len(legal_kosroberta_chunks):,}개 청크")
    print(f"   고정 500자 청킹: {len(fixed_kosroberta_chunks):,}개 청크")

    # 쿼리 임베딩 생성
    print("\n🔢 쿼리 임베딩 생성...")

    from embeddings.embedder import KoreanLegalEmbedder
    from embeddings.remote_embedder import RemoteEmbedder

    # ko-sroberta 쿼리 임베딩
    ko_embedder = KoreanLegalEmbedder()
    query_texts = [q["query"] for q in TEST_QUERIES]
    ko_query_embs = np.array(ko_embedder.embed_documents(query_texts))

    # snowflake-arctic 쿼리 임베딩
    arctic_embedder = RemoteEmbedder(model="dragonkue/snowflake-arctic-embed-l-v2.0-ko")
    arctic_query_embs = np.array(arctic_embedder.embed_documents(query_texts))

    print(f"   ko-sroberta 쿼리 임베딩: {ko_query_embs.shape}")
    print(f"   snowflake-arctic 쿼리 임베딩: {arctic_query_embs.shape}")

    # 벤치마크 실행
    print("\n🔍 벤치마크 실행...")

    results = {}

    # 1. 법률특화 청킹 + ko-sroberta
    print("\n  [1/4] 법률특화 + ko-sroberta")
    results["legal_kosroberta"] = run_benchmark(
        "ko-sroberta (768d)",
        legal_kosroberta_emb,
        legal_kosroberta_chunks,
        ko_query_embs
    )

    # 2. 법률특화 청킹 + snowflake-arctic
    print("  [2/4] 법률특화 + snowflake-arctic")
    results["legal_arctic"] = run_benchmark(
        "snowflake-arctic (1024d)",
        legal_arctic_emb,
        legal_arctic_chunks,
        arctic_query_embs
    )

    # 3. 고정 청킹 + ko-sroberta
    print("  [3/4] 고정500자 + ko-sroberta")
    results["fixed_kosroberta"] = run_benchmark(
        "ko-sroberta (768d)",
        fixed_kosroberta_emb,
        fixed_kosroberta_chunks,
        ko_query_embs
    )

    # 4. 고정 청킹 + snowflake-arctic
    print("  [4/4] 고정500자 + snowflake-arctic")
    results["fixed_arctic"] = run_benchmark(
        "snowflake-arctic (1024d)",
        fixed_arctic_emb,
        fixed_arctic_chunks,
        arctic_query_embs
    )

    # 결과 출력
    print("\n" + "=" * 70)
    print("📊 결과 요약")
    print("=" * 70)

    print("\n[1] 임베딩 모델별 성능 비교 (법률특화 청킹 기준)")
    print("-" * 60)
    print(f"{'모델':<25} {'평균 유사도':>12} {'키워드 히트':>12} {'법적판단 히트':>12}")
    print("-" * 60)

    for key in ["legal_kosroberta", "legal_arctic"]:
        r = results[key]
        print(f"{r['model']:<25} {r['overall_avg_score']:>12.4f} {r['overall_keyword_hit']:>11.1f}% {r['overall_legal_hit']:>11.1f}%")

    # 개선율 계산
    ko_score = results["legal_kosroberta"]["overall_avg_score"]
    arctic_score = results["legal_arctic"]["overall_avg_score"]
    improvement = (arctic_score - ko_score) / ko_score * 100

    print(f"\n  → snowflake-arctic 개선율: {improvement:+.1f}%")

    print("\n[2] 청킹 전략별 성능 비교 (snowflake-arctic 기준)")
    print("-" * 60)
    print(f"{'청킹 전략':<25} {'평균 유사도':>12} {'키워드 히트':>12} {'법적판단 히트':>12}")
    print("-" * 60)

    for key, name in [("fixed_arctic", "고정 500자"), ("legal_arctic", "법률특화")]:
        r = results[key]
        print(f"{name:<25} {r['overall_avg_score']:>12.4f} {r['overall_keyword_hit']:>11.1f}% {r['overall_legal_hit']:>11.1f}%")

    print("\n[3] 4가지 조합 전체 비교")
    print("-" * 70)
    print(f"{'조합':<30} {'평균 유사도':>12} {'Top1 법적판단':>15}")
    print("-" * 70)

    for key, name in [
        ("fixed_kosroberta", "고정500자 + ko-sroberta"),
        ("fixed_arctic", "고정500자 + snowflake-arctic"),
        ("legal_kosroberta", "법률특화 + ko-sroberta"),
        ("legal_arctic", "법률특화 + snowflake-arctic"),
    ]:
        r = results[key]
        print(f"{name:<30} {r['overall_avg_score']:>12.4f} {r['top1_reasoning_rate']:>14.1f}%")

    # 쿼리별 상세 결과 (예시 출력)
    print("\n" + "=" * 70)
    print("📝 쿼리별 검색 결과 예시 (Top-1)")
    print("=" * 70)

    for i, query_info in enumerate(TEST_QUERIES[:3]):  # 상위 3개 쿼리만
        print(f"\n쿼리: \"{query_info['query']}\"")
        print("-" * 50)

        for key, name in [("legal_kosroberta", "ko-sroberta"), ("legal_arctic", "snowflake-arctic")]:
            r = results[key]["query_results"][i]
            print(f"\n  [{name}] Score: {r['avg_score']:.4f}")
            print(f"  → {r['top1_preview'][:150]}...")

    # 결과 저장
    output_path = Path(__file__).parent / "embedding_model_results.json"

    # numpy types 변환
    def convert_numpy(obj):
        if isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(v) for v in obj]
        return obj

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(convert_numpy(results), f, ensure_ascii=False, indent=2)

    print(f"\n💾 결과 저장: {output_path}")
    print("=" * 70)

    return results


if __name__ == "__main__":
    main()
