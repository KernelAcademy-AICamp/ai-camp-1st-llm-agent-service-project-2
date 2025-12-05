#!/usr/bin/env python3
"""
격리된 컴포넌트 비교 벤치마크

각 컴포넌트(청킹, 임베딩, VectorDB)의 영향을 개별적으로 측정

실험 1: 청킹만 비교
├─ 임베딩: ko-sroberta (동일)
├─ VectorDB: ChromaDB 메모리 (동일)
└─ 청킹: 500자 vs 법률특화

실험 2: 임베딩만 비교
├─ 청킹: 법률특화 (동일)
├─ VectorDB: ChromaDB 메모리 (동일)
└─ 임베딩: ko-sroberta vs snowflake-arctic

실험 3: VectorDB만 비교
├─ 청킹: 법률특화 (동일)
├─ 임베딩: snowflake-arctic (동일)
└─ VectorDB: ChromaDB vs Qdrant
"""

import sys
import os
import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict, field

# Add project root to path
BASE_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "libs" / "rag_core"))

from dotenv import load_dotenv
load_dotenv()


@dataclass
class SearchResult:
    """검색 결과"""
    query: str
    query_id: str
    top_chunks: List[Dict[str, Any]]
    scores: List[float]
    search_time_ms: float
    hit_at_k: Dict[int, bool] = field(default_factory=dict)
    mrr: float = 0.0


@dataclass
class ExperimentResult:
    """실험 결과"""
    experiment_name: str
    description: str

    # 시스템 A vs B 설정
    system_a_config: Dict[str, str]
    system_b_config: Dict[str, str]

    # 변경된 컴포넌트
    changed_component: str

    # 성능 지표
    system_a_avg_time_ms: float
    system_b_avg_time_ms: float
    system_a_hit_rate_1: float
    system_b_hit_rate_1: float
    system_a_hit_rate_3: float
    system_b_hit_rate_3: float
    system_a_mrr: float
    system_b_mrr: float

    # 쿼리별 상세
    query_results: List[Dict[str, Any]]


class ChromaIndex:
    """ChromaDB 인덱스"""

    def __init__(self, embeddings: np.ndarray, metadata: List[Dict], collection_name: str = "isolated_test"):
        import chromadb

        self.client = chromadb.Client()  # 메모리 모드
        self.collection_name = collection_name
        self.original_metadata = metadata  # 원본 메타데이터 저장

        # 기존 컬렉션 삭제 후 재생성
        try:
            self.client.delete_collection(collection_name)
        except:
            pass

        self.collection = self.client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        # 데이터 삽입
        ids = [str(i) for i in range(len(embeddings))]
        documents = [m.get("text", "") for m in metadata]

        # ChromaDB는 평탄화된 메타데이터만 지원 (str, int, float, bool만 허용)
        def flatten_metadata(m):
            flat = {}
            for k, v in m.items():
                if k == "text":
                    continue
                if isinstance(v, dict):
                    # 중첩 dict를 문자열로 변환
                    for sub_k, sub_v in v.items():
                        if isinstance(sub_v, (str, int, float, bool)) or sub_v is None:
                            flat[f"{k}_{sub_k}"] = sub_v
                elif isinstance(v, (str, int, float, bool)) or v is None:
                    flat[k] = v
                else:
                    flat[k] = str(v)
            return flat

        metadatas = [flatten_metadata(m) for m in metadata]

        # 배치 삽입
        batch_size = 1000
        for i in range(0, len(embeddings), batch_size):
            end = min(i + batch_size, len(embeddings))
            self.collection.add(
                ids=ids[i:end],
                embeddings=embeddings[i:end].tolist(),
                documents=documents[i:end],
                metadatas=metadatas[i:end]
            )

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """검색"""
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        formatted = []
        if results and results.get('documents') and results['documents'][0]:
            documents = results['documents'][0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]

            for i, doc in enumerate(documents):
                meta = metadatas[i] if i < len(metadatas) else {}
                dist = distances[i] if i < len(distances) else 1.0
                score = 1.0 / (1.0 + dist)

                formatted.append({
                    "text": doc,
                    "score": score,
                    "metadata": meta
                })

        return formatted

    def cleanup(self):
        """컬렉션 삭제"""
        try:
            self.client.delete_collection(self.collection_name)
        except:
            pass


class QdrantIndex:
    """Qdrant 인덱스"""

    def __init__(self, embeddings: np.ndarray, metadata: List[Dict], collection_name: str):
        from qdrant_client import QdrantClient
        from qdrant_client.models import VectorParams, Distance, PointStruct

        self.client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
        self.collection_name = collection_name
        self.dimension = embeddings.shape[1]

        # 기존 컬렉션 삭제 후 재생성
        try:
            self.client.delete_collection(collection_name)
        except:
            pass

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=self.dimension,
                distance=Distance.COSINE
            )
        )

        # 데이터 삽입
        points = []
        for i, (emb, meta) in enumerate(zip(embeddings, metadata)):
            payload = meta.copy()
            points.append(PointStruct(
                id=i,
                vector=emb.tolist(),
                payload=payload
            ))

        # 배치 삽입
        batch_size = 100
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=collection_name,
                points=points[i:i+batch_size]
            )

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """검색"""
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding.tolist(),
            limit=top_k,
            with_payload=True
        )

        formatted = []
        for point in results.points:
            payload = dict(point.payload) if point.payload else {}
            text = payload.pop("text", "")
            formatted.append({
                "text": text,
                "score": point.score,
                "metadata": payload
            })

        return formatted

    def cleanup(self):
        """컬렉션 삭제"""
        try:
            self.client.delete_collection(self.collection_name)
        except:
            pass


def load_prepared_data(data_dir: Path, name: str) -> Tuple[np.ndarray, List[Dict]]:
    """준비된 데이터 로딩"""
    embeddings = np.load(data_dir / f"{name}_embeddings.npy")

    with open(data_dir / f"{name}_metadata.json", 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    return embeddings, metadata


def load_test_queries(queries_path: Path) -> List[Dict]:
    """테스트 쿼리 로딩"""
    with open(queries_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['queries']


def calculate_metrics(
    result: SearchResult,
    keywords: List[str],
    expected_topics: List[str]
) -> SearchResult:
    """품질 지표 계산"""

    # Hit@K
    for k in [1, 3, 5]:
        hit = False
        for chunk in result.top_chunks[:k]:
            text = chunk.get('text', '').lower()
            for topic in expected_topics:
                if topic.lower() in text:
                    hit = True
                    break
            if hit:
                break
        result.hit_at_k[k] = hit

    # MRR
    result.mrr = 0.0
    for i, chunk in enumerate(result.top_chunks):
        text = chunk.get('text', '').lower()
        for topic in expected_topics:
            if topic.lower() in text:
                result.mrr = 1.0 / (i + 1)
                break
        if result.mrr > 0:
            break

    return result


class IsolatedComparison:
    """격리된 컴포넌트 비교"""

    def __init__(self, data_dir: Path, queries_path: Path):
        self.data_dir = data_dir
        self.queries = load_test_queries(queries_path)

        # 임베더 초기화 (쿼리 임베딩용)
        self.ko_sroberta_embedder = None
        self.arctic_embedder = None

    def setup_embedders(self):
        """임베더 초기화"""
        from embeddings.embedder import KoreanLegalEmbedder
        from embeddings.remote_embedder import RemoteEmbedder

        print("🔧 임베더 초기화 중...")
        self.ko_sroberta_embedder = KoreanLegalEmbedder()
        self.arctic_embedder = RemoteEmbedder(
            model="dragonkue/snowflake-arctic-embed-l-v2.0-ko"
        )
        print("✅ 임베더 준비 완료\n")

    def run_experiment_1_chunking(self, top_k: int = 5) -> ExperimentResult:
        """실험 1: 청킹만 비교"""
        print("\n" + "=" * 70)
        print("🔬 실험 1: 청킹 전략 비교")
        print("=" * 70)
        print("  ├─ 임베딩: ko-sroberta (동일)")
        print("  ├─ VectorDB: ChromaDB 메모리 (동일)")
        print("  └─ 청킹: 500자 고정 vs 법률특화")
        print()

        # 데이터 로딩
        fixed_emb, fixed_meta = load_prepared_data(self.data_dir, "fixed_kosroberta")
        legal_emb, legal_meta = load_prepared_data(self.data_dir, "legal_kosroberta")

        print(f"  고정 500자: {len(fixed_meta)}개 청크")
        print(f"  법률특화: {len(legal_meta)}개 청크")

        # ChromaDB 인덱스 생성
        fixed_index = ChromaIndex(fixed_emb, fixed_meta, "exp1_fixed")
        legal_index = ChromaIndex(legal_emb, legal_meta, "exp1_legal")

        # 검색 테스트
        fixed_results = []
        legal_results = []

        for q in self.queries:
            query_emb = self.ko_sroberta_embedder.embed_query(q['query'])
            keywords = q.get('keywords', [])
            expected_topics = q.get('expected_topics', keywords)

            # 고정 청킹 검색
            start = time.perf_counter()
            fixed_hits = fixed_index.search(query_emb, top_k)
            fixed_time = (time.perf_counter() - start) * 1000

            fixed_result = SearchResult(
                query=q['query'],
                query_id=q['id'],
                top_chunks=fixed_hits,
                scores=[h['score'] for h in fixed_hits],
                search_time_ms=fixed_time
            )
            fixed_result = calculate_metrics(fixed_result, keywords, expected_topics)
            fixed_results.append(fixed_result)

            # 법률특화 검색
            start = time.perf_counter()
            legal_hits = legal_index.search(query_emb, top_k)
            legal_time = (time.perf_counter() - start) * 1000

            legal_result = SearchResult(
                query=q['query'],
                query_id=q['id'],
                top_chunks=legal_hits,
                scores=[h['score'] for h in legal_hits],
                search_time_ms=legal_time
            )
            legal_result = calculate_metrics(legal_result, keywords, expected_topics)
            legal_results.append(legal_result)

            print(f"  [{q['id']}] 고정: Hit@1={fixed_result.hit_at_k.get(1)} | "
                  f"법률: Hit@1={legal_result.hit_at_k.get(1)}")

        # 정리
        fixed_index.cleanup()
        legal_index.cleanup()

        return self._aggregate_results(
            "실험1_청킹비교",
            "청킹 전략만 변경 (임베딩/VectorDB 동일)",
            {"chunking": "fixed_500", "embedding": "ko-sroberta", "vectordb": "ChromaDB"},
            {"chunking": "legal_specialized", "embedding": "ko-sroberta", "vectordb": "ChromaDB"},
            "chunking",
            fixed_results,
            legal_results
        )

    def run_experiment_2_embedding(self, top_k: int = 5) -> ExperimentResult:
        """실험 2: 임베딩만 비교"""
        print("\n" + "=" * 70)
        print("🔬 실험 2: 임베딩 모델 비교")
        print("=" * 70)
        print("  ├─ 청킹: 법률특화 (동일)")
        print("  ├─ VectorDB: ChromaDB 메모리 (동일)")
        print("  └─ 임베딩: ko-sroberta vs snowflake-arctic")
        print()

        # 데이터 로딩 (법률특화 청킹, 다른 임베딩)
        kosro_emb, kosro_meta = load_prepared_data(self.data_dir, "legal_kosroberta")
        arctic_emb, arctic_meta = load_prepared_data(self.data_dir, "legal_arctic")

        print(f"  ko-sroberta (768d): {len(kosro_meta)}개 청크")
        print(f"  snowflake-arctic (1024d): {len(arctic_meta)}개 청크")

        # ChromaDB 인덱스 생성
        kosro_index = ChromaIndex(kosro_emb, kosro_meta, "exp2_kosro")
        arctic_index = ChromaIndex(arctic_emb, arctic_meta, "exp2_arctic")

        # 검색 테스트
        kosro_results = []
        arctic_results = []

        for q in self.queries:
            keywords = q.get('keywords', [])
            expected_topics = q.get('expected_topics', keywords)

            # ko-sroberta 쿼리 임베딩 + 검색
            kosro_query = self.ko_sroberta_embedder.embed_query(q['query'])
            start = time.perf_counter()
            kosro_hits = kosro_index.search(kosro_query, top_k)
            kosro_time = (time.perf_counter() - start) * 1000

            kosro_result = SearchResult(
                query=q['query'],
                query_id=q['id'],
                top_chunks=kosro_hits,
                scores=[h['score'] for h in kosro_hits],
                search_time_ms=kosro_time
            )
            kosro_result = calculate_metrics(kosro_result, keywords, expected_topics)
            kosro_results.append(kosro_result)

            # arctic 쿼리 임베딩 + 검색
            arctic_query = self.arctic_embedder.embed_query(q['query'])
            start = time.perf_counter()
            arctic_hits = arctic_index.search(arctic_query, top_k)
            arctic_time = (time.perf_counter() - start) * 1000

            arctic_result = SearchResult(
                query=q['query'],
                query_id=q['id'],
                top_chunks=arctic_hits,
                scores=[h['score'] for h in arctic_hits],
                search_time_ms=arctic_time
            )
            arctic_result = calculate_metrics(arctic_result, keywords, expected_topics)
            arctic_results.append(arctic_result)

            print(f"  [{q['id']}] ko-sroberta: Hit@1={kosro_result.hit_at_k.get(1)} | "
                  f"arctic: Hit@1={arctic_result.hit_at_k.get(1)}")

        # 정리
        kosro_index.cleanup()
        arctic_index.cleanup()

        return self._aggregate_results(
            "실험2_임베딩비교",
            "임베딩 모델만 변경 (청킹/VectorDB 동일)",
            {"chunking": "legal_specialized", "embedding": "ko-sroberta (768d)", "vectordb": "ChromaDB"},
            {"chunking": "legal_specialized", "embedding": "snowflake-arctic (1024d)", "vectordb": "ChromaDB"},
            "embedding",
            kosro_results,
            arctic_results
        )

    def run_experiment_3_vectordb(self, top_k: int = 5) -> ExperimentResult:
        """실험 3: VectorDB만 비교"""
        print("\n" + "=" * 70)
        print("🔬 실험 3: VectorDB 비교")
        print("=" * 70)
        print("  ├─ 청킹: 법률특화 (동일)")
        print("  ├─ 임베딩: snowflake-arctic (동일)")
        print("  └─ VectorDB: ChromaDB vs Qdrant")
        print()

        # 데이터 로딩
        emb, meta = load_prepared_data(self.data_dir, "legal_arctic")
        print(f"  데이터: {len(meta)}개 청크")

        # 인덱스 생성
        chroma_index = ChromaIndex(emb, meta, "exp3_chroma")
        qdrant_index = QdrantIndex(emb, meta, "isolated_comparison_test")

        # 검색 테스트
        chroma_results = []
        qdrant_results = []

        for q in self.queries:
            query_emb = self.arctic_embedder.embed_query(q['query'])
            keywords = q.get('keywords', [])
            expected_topics = q.get('expected_topics', keywords)

            # ChromaDB 검색
            start = time.perf_counter()
            chroma_hits = chroma_index.search(query_emb, top_k)
            chroma_time = (time.perf_counter() - start) * 1000

            chroma_result = SearchResult(
                query=q['query'],
                query_id=q['id'],
                top_chunks=chroma_hits,
                scores=[h['score'] for h in chroma_hits],
                search_time_ms=chroma_time
            )
            chroma_result = calculate_metrics(chroma_result, keywords, expected_topics)
            chroma_results.append(chroma_result)

            # Qdrant 검색
            start = time.perf_counter()
            qdrant_hits = qdrant_index.search(query_emb, top_k)
            qdrant_time = (time.perf_counter() - start) * 1000

            qdrant_result = SearchResult(
                query=q['query'],
                query_id=q['id'],
                top_chunks=qdrant_hits,
                scores=[h['score'] for h in qdrant_hits],
                search_time_ms=qdrant_time
            )
            qdrant_result = calculate_metrics(qdrant_result, keywords, expected_topics)
            qdrant_results.append(qdrant_result)

            print(f"  [{q['id']}] ChromaDB: {chroma_time:.1f}ms | Qdrant: {qdrant_time:.1f}ms")

        # 정리
        chroma_index.cleanup()
        qdrant_index.cleanup()

        return self._aggregate_results(
            "실험3_VectorDB비교",
            "VectorDB만 변경 (청킹/임베딩 동일)",
            {"chunking": "legal_specialized", "embedding": "snowflake-arctic", "vectordb": "ChromaDB"},
            {"chunking": "legal_specialized", "embedding": "snowflake-arctic", "vectordb": "Qdrant"},
            "vectordb",
            chroma_results,
            qdrant_results
        )

    def _aggregate_results(
        self,
        name: str,
        description: str,
        config_a: Dict,
        config_b: Dict,
        changed_component: str,
        results_a: List[SearchResult],
        results_b: List[SearchResult]
    ) -> ExperimentResult:
        """결과 집계"""

        query_comparisons = []
        for ra, rb in zip(results_a, results_b):
            query_comparisons.append({
                "query_id": ra.query_id,
                "query": ra.query,
                "system_a": {
                    "time_ms": ra.search_time_ms,
                    "hit_at_1": ra.hit_at_k.get(1, False),
                    "hit_at_3": ra.hit_at_k.get(3, False),
                    "mrr": ra.mrr,
                    "top_score": ra.scores[0] if ra.scores else 0
                },
                "system_b": {
                    "time_ms": rb.search_time_ms,
                    "hit_at_1": rb.hit_at_k.get(1, False),
                    "hit_at_3": rb.hit_at_k.get(3, False),
                    "mrr": rb.mrr,
                    "top_score": rb.scores[0] if rb.scores else 0
                }
            })

        return ExperimentResult(
            experiment_name=name,
            description=description,
            system_a_config=config_a,
            system_b_config=config_b,
            changed_component=changed_component,
            system_a_avg_time_ms=np.mean([r.search_time_ms for r in results_a]),
            system_b_avg_time_ms=np.mean([r.search_time_ms for r in results_b]),
            system_a_hit_rate_1=np.mean([r.hit_at_k.get(1, False) for r in results_a]),
            system_b_hit_rate_1=np.mean([r.hit_at_k.get(1, False) for r in results_b]),
            system_a_hit_rate_3=np.mean([r.hit_at_k.get(3, False) for r in results_a]),
            system_b_hit_rate_3=np.mean([r.hit_at_k.get(3, False) for r in results_b]),
            system_a_mrr=np.mean([r.mrr for r in results_a]),
            system_b_mrr=np.mean([r.mrr for r in results_b]),
            query_results=query_comparisons
        )

    def print_summary(self, results: List[ExperimentResult]):
        """결과 요약 출력"""

        print("\n" + "=" * 70)
        print("📊 격리된 컴포넌트 비교 결과 요약")
        print("=" * 70)

        for exp in results:
            print(f"\n[{exp.experiment_name}] {exp.description}")
            print("-" * 50)

            # 변경된 컴포넌트 표시
            print(f"  변경 요소: {exp.changed_component}")
            print(f"    A: {exp.system_a_config[exp.changed_component]}")
            print(f"    B: {exp.system_b_config[exp.changed_component]}")

            # 핵심 지표
            print(f"\n  Hit Rate@1: {exp.system_a_hit_rate_1:.1%} → {exp.system_b_hit_rate_1:.1%} ", end="")
            diff = exp.system_b_hit_rate_1 - exp.system_a_hit_rate_1
            if diff > 0:
                print(f"(+{diff:.1%}) ✅")
            elif diff < 0:
                print(f"({diff:.1%}) ⚠️")
            else:
                print("(동일)")

            print(f"  Hit Rate@3: {exp.system_a_hit_rate_3:.1%} → {exp.system_b_hit_rate_3:.1%} ", end="")
            diff = exp.system_b_hit_rate_3 - exp.system_a_hit_rate_3
            if diff > 0:
                print(f"(+{diff:.1%}) ✅")
            elif diff < 0:
                print(f"({diff:.1%}) ⚠️")
            else:
                print("(동일)")

            print(f"  MRR:        {exp.system_a_mrr:.4f} → {exp.system_b_mrr:.4f} ", end="")
            diff = exp.system_b_mrr - exp.system_a_mrr
            if diff > 0:
                print(f"(+{diff:.4f}) ✅")
            elif diff < 0:
                print(f"({diff:.4f}) ⚠️")
            else:
                print("(동일)")

            print(f"  검색 속도:   {exp.system_a_avg_time_ms:.1f}ms → {exp.system_b_avg_time_ms:.1f}ms")

        # 종합 분석
        print("\n" + "=" * 70)
        print("📈 컴포넌트별 기여도 분석")
        print("=" * 70)

        contributions = {}
        for exp in results:
            component = exp.changed_component
            hit1_diff = exp.system_b_hit_rate_1 - exp.system_a_hit_rate_1
            mrr_diff = exp.system_b_mrr - exp.system_a_mrr
            contributions[component] = {
                "hit_rate_1_diff": hit1_diff,
                "mrr_diff": mrr_diff
            }

        print("\n  각 컴포넌트 변경이 성능에 미친 영향:")
        for component, impact in contributions.items():
            print(f"\n  [{component}]")
            print(f"    Hit Rate@1 변화: {impact['hit_rate_1_diff']:+.1%}")
            print(f"    MRR 변화:       {impact['mrr_diff']:+.4f}")

        print("\n" + "=" * 70)

    def save_results(self, results: List[ExperimentResult], output_dir: Path):
        """결과 저장"""

        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"isolated_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_dir / filename

        def convert_numpy(obj):
            """numpy 타입을 Python 기본 타입으로 변환"""
            if isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(i) for i in obj]
            return obj

        data = {
            "timestamp": datetime.now().isoformat(),
            "experiments": [convert_numpy(asdict(r)) for r in results]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 결과 저장: {filepath}")
        return filepath


def main():
    import argparse

    parser = argparse.ArgumentParser(description="격리된 컴포넌트 비교 벤치마크")
    parser.add_argument("--data-dir", type=str,
                       default=str(BASE_DIR / "scripts" / "rag_benchmark" / "isolated_comparison" / "data"),
                       help="준비된 데이터 디렉토리")
    parser.add_argument("--queries", type=str,
                       default=str(BASE_DIR / "scripts" / "rag_benchmark" / "queries" / "test_queries.json"),
                       help="테스트 쿼리 파일")
    parser.add_argument("--output-dir", type=str,
                       default=str(BASE_DIR / "scripts" / "rag_benchmark" / "isolated_comparison" / "results"),
                       help="결과 저장 디렉토리")
    parser.add_argument("--top-k", type=int, default=5, help="검색 결과 수")

    args = parser.parse_args()

    print("=" * 70)
    print("🔬 격리된 컴포넌트 비교 벤치마크")
    print("=" * 70)
    print(f"📅 {datetime.now().isoformat()}")
    print()

    # 데이터 확인
    data_dir = Path(args.data_dir)
    if not (data_dir / "preparation_summary.json").exists():
        print("❌ 준비된 데이터가 없습니다.")
        print("   먼저 prepare_data.py를 실행하세요:")
        print(f"   python {BASE_DIR}/scripts/rag_benchmark/isolated_comparison/prepare_data.py")
        return

    # 비교 실행
    comparison = IsolatedComparison(data_dir, Path(args.queries))
    comparison.setup_embedders()

    results = []

    # 실험 1: 청킹 비교
    results.append(comparison.run_experiment_1_chunking(args.top_k))

    # 실험 2: 임베딩 비교
    results.append(comparison.run_experiment_2_embedding(args.top_k))

    # 실험 3: VectorDB 비교
    results.append(comparison.run_experiment_3_vectordb(args.top_k))

    # 결과 출력 및 저장
    comparison.print_summary(results)
    comparison.save_results(results, Path(args.output_dir))


if __name__ == "__main__":
    main()
