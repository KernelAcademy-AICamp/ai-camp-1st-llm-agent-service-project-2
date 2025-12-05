#!/usr/bin/env python3
"""
A (Fixed 500자) 청킹 전략만 테스트

기존 B, C 결과와 비교하기 위해 A만 추가 테스트
- B (Original): 0.4893 avg score, 10% important hit rate
- C (Improved): 0.4778 avg score, 30% important hit rate
"""

import sys
import os
from pathlib import Path
import json
import csv
import random
from typing import List, Dict, Any
import numpy as np
from tqdm import tqdm

# Project path setup
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "libs" / "rag_core"))

from dotenv import load_dotenv
load_dotenv()


# ============================================================
# Fixed 500자 청킹 (ChromaDB 시절 전략)
# ============================================================

class FixedChunking:
    """500자 고정 청킹 - ChromaDB 시절 Before 전략"""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: Dict = None) -> List[Dict]:
        if metadata is None:
            metadata = {}

        chunks = []
        start = 0
        chunk_id = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end].strip()

            if len(chunk_text) > 30:
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        **metadata,
                        'chunk_id': chunk_id,
                        'section': 'unknown',  # 섹션 정보 없음
                        'chunking_strategy': 'fixed_500'
                    }
                })
                chunk_id += 1

            start = end - self.overlap

        return chunks


# ============================================================
# 데이터 로딩
# ============================================================

def load_sample_documents(data_dir: Path, sample_size: int = 50) -> List[Dict]:
    """샘플 문서 로딩"""
    documents = []

    for doc_type in ["TS_판결문", "TS_결정례"]:
        type_dir = data_dir / doc_type
        if not type_dir.exists():
            continue

        files = list(type_dir.glob("*.csv"))
        sample_files = random.sample(files, min(sample_size // 2, len(files)))

        for file_path in sample_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)

                if not rows:
                    continue

                # 섹션별로 내용 수집
                sections = {}
                for row in rows:
                    section = row.get('구분', 'unknown')
                    content = row.get('내용', '')
                    if section not in sections:
                        sections[section] = []
                    sections[section].append(content)

                # 전체 텍스트 구성
                full_text_parts = []
                for section, contents in sections.items():
                    if contents:
                        full_text_parts.append(f"[{section}]")
                        full_text_parts.extend(contents)

                full_text = "\n".join(full_text_parts)

                if len(full_text) > 200:
                    documents.append({
                        'doc_id': rows[0].get('판례일련번호', file_path.stem),
                        'doc_type': doc_type.replace('TS_', ''),
                        'content': full_text,
                        'sections': sections
                    })
            except Exception:
                pass

    return documents


# ============================================================
# 테스트 쿼리
# ============================================================

TEST_QUERIES = [
    {"query": "음주운전 처벌 기준", "keywords": ["음주", "혈중알코올", "면허취소"]},
    {"query": "사기죄 구성요건", "keywords": ["기망", "착오", "재산상 이익"]},
    {"query": "폭행죄와 상해죄 차이", "keywords": ["폭행", "상해", "신체"]},
    {"query": "절도죄 형량", "keywords": ["절취", "타인", "재물"]},
    {"query": "명예훼손 판단 기준", "keywords": ["명예", "사실적시", "공연히"]},
]


# ============================================================
# 메인 테스트
# ============================================================

def main():
    random.seed(42)

    print("=" * 70)
    print("A (Fixed 500자) 청킹 전략 테스트")
    print("=" * 70)

    # 데이터 경로
    data_dir = BASE_DIR / "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터" / "3.개방데이터" / "1.데이터" / "Training" / "01.원천데이터"

    # 1. 샘플 문서 로딩
    print("\n📥 샘플 문서 로딩...")
    documents = load_sample_documents(data_dir, sample_size=50)
    print(f"   로딩된 문서: {len(documents)}개")

    # 2. A 전략 청킹
    print("\n✂️ A (Fixed 500자) 청킹 적용...")
    chunker = FixedChunking(chunk_size=500, overlap=50)

    all_chunks = []
    for doc in tqdm(documents, desc="   청킹"):
        chunks = chunker.chunk(doc['content'], {'doc_id': doc['doc_id']})
        for chunk in chunks:
            chunk['doc_sections'] = doc.get('sections', {})
        all_chunks.append(chunks)

    total_chunks = sum(len(c) for c in all_chunks)
    avg_length = np.mean([len(c['content']) for chunks in all_chunks for c in chunks])
    print(f"   생성된 청크: {total_chunks}개")
    print(f"   평균 길이: {avg_length:.0f}자")

    # 3. 임베딩 생성
    print("\n🔢 임베딩 생성 (snowflake-arctic)...")
    from embeddings.remote_embedder import RemoteEmbedder
    embedder = RemoteEmbedder(model="dragonkue/snowflake-arctic-embed-l-v2.0-ko")

    # 청크 임베딩
    all_texts = [c['content'] for chunks in all_chunks for c in chunks]
    chunk_embeddings = []
    batch_size = 16

    for i in tqdm(range(0, len(all_texts), batch_size), desc="   청크 임베딩"):
        batch = all_texts[i:i+batch_size]
        embs = embedder.embed_documents(batch)
        chunk_embeddings.extend(embs)

    chunk_embeddings = np.array(chunk_embeddings)
    print(f"   청크 임베딩 shape: {chunk_embeddings.shape}")

    # 쿼리 임베딩
    query_texts = [q['query'] for q in TEST_QUERIES]
    query_embeddings = embedder.embed_documents(query_texts)
    query_embeddings = np.array(query_embeddings)

    # 4. 검색 테스트
    print("\n🔍 검색 테스트...")

    # 평탄화된 청크 리스트
    flat_chunks = [c for chunks in all_chunks for c in chunks]

    results = []
    important_hits = 0
    total_queries = 0

    for q_idx, query in enumerate(TEST_QUERIES):
        q_emb = query_embeddings[q_idx]

        # 코사인 유사도
        similarities = np.dot(chunk_embeddings, q_emb) / (
            np.linalg.norm(chunk_embeddings, axis=1) * np.linalg.norm(q_emb)
        )

        # Top-5
        top_indices = np.argsort(similarities)[::-1][:5]

        top_results = []
        for idx in top_indices:
            chunk = flat_chunks[idx]
            score = float(similarities[idx])

            # 중요 섹션 체크 (원본 문서에서)
            doc_sections = chunk.get('doc_sections', {})
            has_important = any(
                section in ['이유', '판시사항', '판결요지', '결정요지']
                for section in doc_sections.keys()
            )

            # 청크가 중요 섹션 내용을 포함하는지
            content = chunk['content']
            contains_reasoning = any(
                keyword in content
                for keyword in ['판단', '이유', '요지', '결론']
            )

            top_results.append({
                'score': score,
                'has_important': has_important,
                'contains_reasoning': contains_reasoning,
                'content_preview': content[:100]
            })

        # 중요 섹션 히트 체크
        has_important_hit = any(r['contains_reasoning'] for r in top_results)
        if has_important_hit:
            important_hits += 1
        total_queries += 1

        avg_score = np.mean([r['score'] for r in top_results])
        results.append({
            'query': query['query'],
            'avg_score': avg_score,
            'has_important_hit': has_important_hit,
            'top_results': top_results
        })

    # 5. 결과 요약
    print("\n" + "=" * 70)
    print("📊 결과 요약")
    print("=" * 70)

    overall_avg = np.mean([r['avg_score'] for r in results])
    important_rate = important_hits / total_queries * 100

    print(f"\n[A] Fixed 500자 청킹")
    print(f"    평균 유사도: {overall_avg:.4f}")
    print(f"    중요섹션 히트율: {important_rate:.1f}%")
    print(f"    총 청크 수: {total_chunks}")
    print(f"    평균 청크 길이: {avg_length:.0f}자")

    # 기존 B, C 결과와 비교
    print("\n" + "-" * 70)
    print("3가지 전략 비교 (동일 임베딩: snowflake-arctic)")
    print("-" * 70)

    comparison = {
        'A_Fixed500': {
            'avg_score': overall_avg,
            'important_rate': important_rate,
            'chunk_count': total_chunks,
            'avg_length': avg_length
        },
        'B_Original': {
            'avg_score': 0.4893,
            'important_rate': 10.0,
            'chunk_count': 'N/A',
            'avg_length': 206
        },
        'C_Improved': {
            'avg_score': 0.4778,
            'important_rate': 30.0,
            'chunk_count': 'N/A',
            'avg_length': 500
        }
    }

    print(f"\n{'전략':<15} {'평균 유사도':>12} {'중요섹션 히트율':>15} {'평균 길이':>10}")
    print("-" * 55)
    for name, data in comparison.items():
        print(f"{name:<15} {data['avg_score']:>12.4f} {data['important_rate']:>14.1f}% {data['avg_length']:>10}")

    # A vs C 비교
    print("\n" + "-" * 70)
    print("A vs C 비교 (ChromaDB 시절 vs 개선된 전략)")
    print("-" * 70)

    score_diff = comparison['A_Fixed500']['avg_score'] - comparison['C_Improved']['avg_score']
    hit_diff = comparison['C_Improved']['important_rate'] - comparison['A_Fixed500']['important_rate']

    print(f"\n유사도 점수 차이: {score_diff:+.4f} (A - C)")
    print(f"중요섹션 히트율 차이: {hit_diff:+.1f}%p (C - A)")

    if hit_diff > 0:
        print(f"\n✅ C (Improved)가 중요 섹션 검색에서 {hit_diff:.1f}%p 더 우수")

    print("\n" + "=" * 70)

    # 결과 저장
    output_path = Path(__file__).parent / "fixed500_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'A_Fixed500': {
                'avg_score': float(overall_avg),
                'important_rate': float(important_rate),
                'chunk_count': total_chunks,
                'avg_length': float(avg_length)
            },
            'comparison': {k: {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv
                              for kk, vv in v.items()}
                          for k, v in comparison.items()}
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 결과 저장: {output_path}")


if __name__ == "__main__":
    main()
