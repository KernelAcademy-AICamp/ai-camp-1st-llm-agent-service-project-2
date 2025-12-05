#!/usr/bin/env python3
"""
RAG 컴포넌트별 비교 벤치마크

Before vs After 시스템 비교:
- Before: ChromaDB + ko-sroberta-multitask (768d) + 500자 청킹
- After: Qdrant + snowflake-arctic-embed (1024d) + 법률특화 청킹

비교 범위: 판결문 + 결정례 (공정한 비교를 위해 동일 데이터 타입)
"""

import sys
import os
import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field

# Add project root to path
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "libs" / "rag_core"))

from dotenv import load_dotenv
load_dotenv()


@dataclass
class SearchResult:
    """검색 결과"""
    query: str
    query_id: str
    category: str

    # 검색 결과
    chunks: List[Dict[str, Any]]
    scores: List[float]
    search_time_ms: float

    # 품질 지표
    hit_at_k: Dict[int, bool] = field(default_factory=dict)
    mrr: float = 0.0
    keyword_hit_rate: float = 0.0


@dataclass
class ComparisonResult:
    """Before vs After 비교 결과"""
    timestamp: str

    # 시스템 정보
    before_config: Dict[str, Any]
    after_config: Dict[str, Any]

    # 검색 성능
    before_avg_time_ms: float
    after_avg_time_ms: float
    time_improvement_pct: float

    # 검색 품질
    before_hit_rate_1: float
    after_hit_rate_1: float
    before_hit_rate_3: float
    after_hit_rate_3: float
    before_mrr: float
    after_mrr: float

    # 쿼리별 상세 결과
    query_results: List[Dict[str, Any]]

    # 청킹 통계
    before_chunking_stats: Dict[str, Any] = field(default_factory=dict)
    after_chunking_stats: Dict[str, Any] = field(default_factory=dict)


class BeforeSystem:
    """Before 시스템: ChromaDB + ko-sroberta-multitask"""

    def __init__(self):
        self.embedder = None
        self.collection = None  # ChromaDB collection
        self.config = {
            "name": "Before",
            "vector_db": "ChromaDB",
            "embedding_model": "jhgan/ko-sroberta-multitask",
            "embedding_dim": 768,
            "chunking": "fixed_500"
        }

    def setup(self):
        """시스템 초기화"""
        import chromadb
        from embeddings.embedder import KoreanLegalEmbedder

        print("🔧 Before 시스템 설정 중...")

        # 임베딩 모델 (로컬)
        self.embedder = KoreanLegalEmbedder()
        print(f"  ✅ 임베딩: {self.config['embedding_model']} ({self.config['embedding_dim']}d)")

        # ChromaDB 직접 사용
        chroma_dir = BASE_DIR / "data" / "vectordb" / "chroma_criminal_law"
        client = chromadb.PersistentClient(path=str(chroma_dir))
        self.collection = client.get_collection("criminal_law_docs")
        doc_count = self.collection.count()
        print(f"  ✅ ChromaDB: {doc_count:,}개 문서")

        self.config["total_documents"] = doc_count
        print("✅ Before 시스템 준비 완료\n")

    def search(self, query: str, top_k: int = 5) -> SearchResult:
        """검색 수행"""
        start_time = time.perf_counter()

        # 쿼리 임베딩
        query_embedding = self.embedder.embed_query(query)

        # ChromaDB 검색
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        search_time = (time.perf_counter() - start_time) * 1000

        chunks = []
        scores = []

        # ChromaDB는 distance 반환 (낮을수록 유사)
        if results and results.get('documents') and results['documents'][0]:
            documents = results['documents'][0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]

            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0
                # distance를 similarity score로 변환 (1 - distance 또는 1/(1+distance))
                score = 1.0 / (1.0 + distance)

                chunks.append({
                    "text": doc,
                    "score": score,
                    "metadata": metadata,
                    "source": metadata.get("source", "unknown")
                })
                scores.append(score)

        return SearchResult(
            query=query,
            query_id="",
            category="",
            chunks=chunks,
            scores=scores,
            search_time_ms=search_time
        )

    def get_chunking_stats(self, sample_size: int = 5000) -> Dict[str, Any]:
        """청킹 통계 수집"""
        try:
            sample = self.collection.peek(limit=sample_size)
            if not sample or not sample.get('documents'):
                return {}

            documents = sample['documents']
            lengths = [len(doc) for doc in documents]

            return {
                "sample_size": len(documents),
                "avg_length": round(float(np.mean(lengths)), 1),
                "min_length": int(np.min(lengths)),
                "max_length": int(np.max(lengths)),
                "std_length": round(float(np.std(lengths)), 1),
                "median_length": round(float(np.median(lengths)), 1)
            }
        except Exception as e:
            print(f"  ⚠️ 청킹 통계 수집 실패: {e}")
            return {}


class AfterSystem:
    """After 시스템: Qdrant + snowflake-arctic-embed"""

    def __init__(self):
        self.embedder = None
        self.vectordb = None
        self.config = {
            "name": "After",
            "vector_db": "Qdrant",
            "embedding_model": "dragonkue/snowflake-arctic-embed-l-v2.0-ko",
            "embedding_dim": 1024,
            "chunking": "legal_specialized"
        }

    def setup(self):
        """시스템 초기화"""
        from embeddings.remote_embedder import RemoteEmbedder
        from embeddings.qdrant_vectordb import QdrantVectorDB

        print("🔧 After 시스템 설정 중...")

        # 원격 임베딩
        self.embedder = RemoteEmbedder(
            model="dragonkue/snowflake-arctic-embed-l-v2.0-ko"
        )
        print(f"  ✅ 임베딩: {self.config['embedding_model']} ({self.config['embedding_dim']}d)")

        # Qdrant
        self.vectordb = QdrantVectorDB(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            collection_name="law_documents",
            embedding_dim=1024
        )
        doc_count = self.vectordb.get_count()
        print(f"  ✅ Qdrant: {doc_count:,}개 문서")

        self.config["total_documents"] = doc_count
        print("✅ After 시스템 준비 완료\n")

    def search(self, query: str, top_k: int = 5, filter_types: List[str] = None) -> SearchResult:
        """검색 수행 (필터링 가능)"""
        start_time = time.perf_counter()

        # 쿼리 임베딩
        query_embedding = self.embedder.embed_query(query)

        # 검색 (필터링 적용)
        if filter_types:
            results = self.search_with_filter(query_embedding, top_k, filter_types)
        else:
            results = self.vectordb.search(query_embedding, top_k=top_k)

        search_time = (time.perf_counter() - start_time) * 1000

        chunks = []
        scores = []
        for r in results:
            chunks.append({
                "text": r.get("text", r.get("content", "")),
                "score": r.get("score", 0),
                "metadata": r.get("metadata", {}),
                "source": r.get("metadata", {}).get("source",
                         r.get("metadata", {}).get("type", "unknown"))
            })
            scores.append(r.get("score", 0))

        return SearchResult(
            query=query,
            query_id="",
            category="",
            chunks=chunks,
            scores=scores,
            search_time_ms=search_time
        )

    def search_with_filter(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        filter_types: List[str]
    ) -> List[Dict[str, Any]]:
        """타입 필터링이 적용된 검색"""
        from qdrant_client.models import Filter, FieldCondition, MatchAny

        try:
            filter_condition = Filter(
                should=[
                    FieldCondition(
                        key="type",
                        match=MatchAny(any=filter_types)
                    )
                ]
            )

            results = self.vectordb.client.query_points(
                collection_name=self.vectordb.collection_name,
                query=query_embedding.tolist(),
                query_filter=filter_condition,
                limit=top_k,
                with_payload=True
            )

            formatted_results = []
            for point in results.points:
                payload = dict(point.payload) if point.payload else {}
                text = payload.pop('text', '')

                formatted_results.append({
                    "id": point.id,
                    "text": text,
                    "metadata": payload,
                    "score": point.score
                })

            return formatted_results

        except Exception as e:
            print(f"  ⚠️ 필터 검색 실패: {e}")
            # 필터 없이 재시도
            return self.vectordb.search(query_embedding, top_k=top_k)

    def get_chunking_stats(self, sample_size: int = 5000) -> Dict[str, Any]:
        """청킹 통계 수집"""
        try:
            # Qdrant에서 샘플링
            results = self.vectordb.client.scroll(
                collection_name=self.vectordb.collection_name,
                limit=sample_size,
                with_payload=True,
                with_vectors=False
            )

            points = results[0]
            if not points:
                return {}

            lengths = []
            for point in points:
                text = point.payload.get('text', '') if point.payload else ''
                lengths.append(len(text))

            return {
                "sample_size": len(lengths),
                "avg_length": round(float(np.mean(lengths)), 1),
                "min_length": int(np.min(lengths)),
                "max_length": int(np.max(lengths)),
                "std_length": round(float(np.std(lengths)), 1),
                "median_length": round(float(np.median(lengths)), 1)
            }
        except Exception as e:
            print(f"  ⚠️ 청킹 통계 수집 실패: {e}")
            return {}


class ComponentComparison:
    """컴포넌트 비교 벤치마크"""

    def __init__(self):
        self.before = BeforeSystem()
        self.after = AfterSystem()

        # 판결문 + 결정례만 필터 (공정한 비교)
        self.filter_types = ["source_판결문", "source_결정례"]

    def setup(self):
        """시스템들 초기화"""
        print("=" * 70)
        print("🔬 RAG 컴포넌트 비교 벤치마크")
        print("=" * 70)
        print(f"📅 {datetime.now().isoformat()}")
        print(f"🔍 비교 범위: 판결문 + 결정례 (동일 데이터 타입)")
        print()

        self.before.setup()
        self.after.setup()

    def calculate_metrics(
        self,
        result: SearchResult,
        keywords: List[str],
        expected_topics: List[str]
    ) -> SearchResult:
        """검색 품질 지표 계산"""
        chunks = result.chunks

        # 키워드 매칭률
        keyword_hits = 0
        for keyword in keywords:
            for chunk in chunks[:5]:
                if keyword.lower() in chunk['text'].lower():
                    keyword_hits += 1
                    break
        result.keyword_hit_rate = keyword_hits / len(keywords) if keywords else 0

        # Hit@K
        for k in [1, 3, 5]:
            hit = False
            for chunk in chunks[:k]:
                for topic in expected_topics:
                    if topic.lower() in chunk['text'].lower():
                        hit = True
                        break
                if hit:
                    break
            result.hit_at_k[k] = hit

        # MRR
        result.mrr = 0.0
        for i, chunk in enumerate(chunks):
            for topic in expected_topics:
                if topic.lower() in chunk['text'].lower():
                    result.mrr = 1.0 / (i + 1)
                    break
            if result.mrr > 0:
                break

        return result

    def run_comparison(self, queries_path: str, top_k: int = 5) -> ComparisonResult:
        """비교 벤치마크 실행"""
        with open(queries_path, 'r', encoding='utf-8') as f:
            queries_data = json.load(f)

        queries = queries_data['queries']
        print(f"\n📊 비교 테스트 시작: {len(queries)}개 쿼리")
        print("=" * 70)

        before_results = []
        after_results = []
        query_comparisons = []

        for q in queries:
            print(f"\n[{q['id']}] {q['query']}")
            keywords = q.get('keywords', [])
            expected_topics = q.get('expected_topics', keywords)

            # Before 검색
            before_result = self.before.search(q['query'], top_k=top_k)
            before_result.query_id = q['id']
            before_result.category = q['category']
            before_result = self.calculate_metrics(before_result, keywords, expected_topics)
            before_results.append(before_result)

            # After 검색 (필터링 적용)
            after_result = self.after.search(
                q['query'],
                top_k=top_k,
                filter_types=self.filter_types
            )
            after_result.query_id = q['id']
            after_result.category = q['category']
            after_result = self.calculate_metrics(after_result, keywords, expected_topics)
            after_results.append(after_result)

            # 비교 출력
            print(f"   Before: {before_result.search_time_ms:.0f}ms | "
                  f"Hit@1={before_result.hit_at_k.get(1)} | "
                  f"MRR={before_result.mrr:.4f} | "
                  f"Top1Score={before_result.scores[0]:.4f}" if before_result.scores else "No results")
            print(f"   After:  {after_result.search_time_ms:.0f}ms | "
                  f"Hit@1={after_result.hit_at_k.get(1)} | "
                  f"MRR={after_result.mrr:.4f} | "
                  f"Top1Score={after_result.scores[0]:.4f}" if after_result.scores else "No results")

            # 개선 여부
            time_diff = before_result.search_time_ms - after_result.search_time_ms
            time_emoji = "🚀" if time_diff > 0 else "🐢"
            print(f"   {time_emoji} 시간차: {time_diff:+.0f}ms")

            # 쿼리별 비교 저장
            query_comparisons.append({
                "query_id": q['id'],
                "query": q['query'],
                "category": q['category'],
                "before": {
                    "time_ms": before_result.search_time_ms,
                    "hit_at_1": before_result.hit_at_k.get(1, False),
                    "hit_at_3": before_result.hit_at_k.get(3, False),
                    "mrr": before_result.mrr,
                    "top_score": before_result.scores[0] if before_result.scores else 0,
                    "top_chunks": [
                        {
                            "text_preview": c['text'][:200],
                            "score": c['score'],
                            "source": c['source']
                        }
                        for c in before_result.chunks[:3]
                    ]
                },
                "after": {
                    "time_ms": after_result.search_time_ms,
                    "hit_at_1": after_result.hit_at_k.get(1, False),
                    "hit_at_3": after_result.hit_at_k.get(3, False),
                    "mrr": after_result.mrr,
                    "top_score": after_result.scores[0] if after_result.scores else 0,
                    "top_chunks": [
                        {
                            "text_preview": c['text'][:200],
                            "score": c['score'],
                            "source": c['source']
                        }
                        for c in after_result.chunks[:3]
                    ]
                }
            })

        # 청킹 통계 수집
        print("\n📊 청킹 통계 수집 중...")
        before_chunking = self.before.get_chunking_stats()
        after_chunking = self.after.get_chunking_stats()

        # 집계
        before_times = [r.search_time_ms for r in before_results]
        after_times = [r.search_time_ms for r in after_results]

        before_hit1 = np.mean([r.hit_at_k.get(1, False) for r in before_results])
        after_hit1 = np.mean([r.hit_at_k.get(1, False) for r in after_results])
        before_hit3 = np.mean([r.hit_at_k.get(3, False) for r in before_results])
        after_hit3 = np.mean([r.hit_at_k.get(3, False) for r in after_results])

        before_mrr = np.mean([r.mrr for r in before_results])
        after_mrr = np.mean([r.mrr for r in after_results])

        avg_before_time = np.mean(before_times)
        avg_after_time = np.mean(after_times)
        time_improvement = ((avg_before_time - avg_after_time) / avg_before_time * 100) if avg_before_time > 0 else 0

        return ComparisonResult(
            timestamp=datetime.now().isoformat(),
            before_config=self.before.config,
            after_config=self.after.config,
            before_avg_time_ms=avg_before_time,
            after_avg_time_ms=avg_after_time,
            time_improvement_pct=time_improvement,
            before_hit_rate_1=before_hit1,
            after_hit_rate_1=after_hit1,
            before_hit_rate_3=before_hit3,
            after_hit_rate_3=after_hit3,
            before_mrr=before_mrr,
            after_mrr=after_mrr,
            query_results=query_comparisons,
            before_chunking_stats=before_chunking,
            after_chunking_stats=after_chunking
        )

    def print_summary(self, result: ComparisonResult):
        """결과 요약 출력"""
        print("\n" + "=" * 70)
        print("📊 비교 결과 요약")
        print("=" * 70)

        print("\n[ 시스템 설정 ]")
        print(f"  Before: {result.before_config['vector_db']} + {result.before_config['embedding_model']}")
        print(f"          문서 수: {result.before_config.get('total_documents', 'N/A'):,}")
        print(f"  After:  {result.after_config['vector_db']} + {result.after_config['embedding_model']}")
        print(f"          문서 수: {result.after_config.get('total_documents', 'N/A'):,}")

        print("\n[ 검색 속도 비교 ]")
        print(f"  Before 평균: {result.before_avg_time_ms:.1f}ms")
        print(f"  After 평균:  {result.after_avg_time_ms:.1f}ms")
        if result.time_improvement_pct > 0:
            print(f"  🚀 개선율: {result.time_improvement_pct:.1f}% 빠름")
        else:
            print(f"  🐢 변화: {abs(result.time_improvement_pct):.1f}% 느림")

        print("\n[ 검색 품질 비교 ] ⭐ 핵심 지표")
        print(f"  Hit Rate@1: {result.before_hit_rate_1:.1%} → {result.after_hit_rate_1:.1%} "
              f"({'↑' if result.after_hit_rate_1 > result.before_hit_rate_1 else '↓' if result.after_hit_rate_1 < result.before_hit_rate_1 else '→'})")
        print(f"  Hit Rate@3: {result.before_hit_rate_3:.1%} → {result.after_hit_rate_3:.1%} "
              f"({'↑' if result.after_hit_rate_3 > result.before_hit_rate_3 else '↓' if result.after_hit_rate_3 < result.before_hit_rate_3 else '→'})")
        print(f"  MRR:        {result.before_mrr:.4f} → {result.after_mrr:.4f} "
              f"({'↑' if result.after_mrr > result.before_mrr else '↓' if result.after_mrr < result.before_mrr else '→'})")

        print("\n[ 청킹 통계 비교 ]")
        if result.before_chunking_stats and result.after_chunking_stats:
            bc = result.before_chunking_stats
            ac = result.after_chunking_stats
            print(f"  평균 청크 길이: {bc.get('avg_length', 0):.0f}자 → {ac.get('avg_length', 0):.0f}자")
            print(f"  중앙값:        {bc.get('median_length', 0):.0f}자 → {ac.get('median_length', 0):.0f}자")
            print(f"  표준편차:      {bc.get('std_length', 0):.0f} → {ac.get('std_length', 0):.0f}")

        # 종합 평가
        print("\n[ 종합 평가 ]")
        improvements = 0
        if result.after_hit_rate_1 >= result.before_hit_rate_1:
            improvements += 1
        if result.after_hit_rate_3 >= result.before_hit_rate_3:
            improvements += 1
        if result.after_mrr >= result.before_mrr:
            improvements += 1
        if result.time_improvement_pct > 0:
            improvements += 1

        if improvements >= 3:
            print("  ✅ 전반적으로 After 시스템이 우수함")
        elif improvements >= 2:
            print("  ⚖️ 혼합된 결과 (일부 개선, 일부 저하)")
        else:
            print("  ⚠️ Before 시스템이 일부 지표에서 더 나음")

        print("=" * 70)

    def save_results(self, result: ComparisonResult, output_dir: str):
        """결과 저장"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_path / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)

        print(f"\n✅ 결과 저장: {filepath}")
        return str(filepath)


def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="RAG 컴포넌트 비교 벤치마크")
    parser.add_argument("--queries", type=str,
                       default=str(BASE_DIR / "scripts" / "rag_benchmark" / "queries" / "test_queries.json"),
                       help="테스트 쿼리 파일 경로")
    parser.add_argument("--top-k", type=int, default=5,
                       help="검색 결과 수")
    parser.add_argument("--output", type=str,
                       default=str(BASE_DIR / "scripts" / "rag_benchmark" / "results"),
                       help="결과 저장 디렉토리")

    args = parser.parse_args()

    # 비교 실행
    comparison = ComponentComparison()
    comparison.setup()

    result = comparison.run_comparison(args.queries, top_k=args.top_k)
    comparison.print_summary(result)
    comparison.save_results(result, args.output)


if __name__ == "__main__":
    main()
