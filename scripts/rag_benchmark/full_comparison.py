#!/usr/bin/env python3
"""
RAG 전체 파이프라인 비교 벤치마크

검색(Retrieval) + LLM 답변 생성(Generation) 전체 비교
Before vs After 시스템의 실제 답변 품질까지 비교

비교 항목:
1. 검색 품질 (Hit Rate, MRR)
2. 검색 속도
3. 답변 품질 (출처 포함, 면책조항, 키워드 포함률)
4. 답변 일관성
"""

import sys
import os
import json
import time
import re
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
class RAGResult:
    """RAG 전체 파이프라인 결과"""
    query_id: str
    query: str
    category: str

    # 검색 결과
    search_time_ms: float
    chunks: List[Dict[str, Any]]
    scores: List[float]

    # LLM 답변
    answer: str
    generation_time_ms: float
    total_time_ms: float

    # 검색 품질
    hit_at_k: Dict[int, bool] = field(default_factory=dict)
    mrr: float = 0.0

    # 답변 품질
    answer_length: int = 0
    has_citation: bool = False
    has_disclaimer: bool = False
    keyword_hit_rate: float = 0.0


@dataclass
class FullComparisonResult:
    """전체 비교 결과"""
    timestamp: str

    # 시스템 정보
    before_config: Dict[str, Any]
    after_config: Dict[str, Any]

    # 검색 성능
    before_avg_search_time_ms: float
    after_avg_search_time_ms: float
    before_avg_total_time_ms: float
    after_avg_total_time_ms: float

    # 검색 품질
    before_hit_rate_1: float
    after_hit_rate_1: float
    before_mrr: float
    after_mrr: float

    # 답변 품질
    before_avg_answer_length: float
    after_avg_answer_length: float
    before_citation_rate: float
    after_citation_rate: float
    before_disclaimer_rate: float
    after_disclaimer_rate: float

    # 쿼리별 상세 결과
    query_results: List[Dict[str, Any]]


class BeforeRAGSystem:
    """Before RAG 시스템"""

    def __init__(self):
        self.embedder = None
        self.collection = None  # ChromaDB collection
        self.llm_client = None
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
        from llm.llm_client import create_llm_client

        print("🔧 Before RAG 시스템 설정 중...")

        # 임베딩 모델
        self.embedder = KoreanLegalEmbedder()
        print(f"  ✅ 임베딩: {self.config['embedding_model']}")

        # ChromaDB 직접 사용
        chroma_dir = BASE_DIR / "data" / "vectordb" / "chroma_criminal_law"
        client = chromadb.PersistentClient(path=str(chroma_dir))
        self.collection = client.get_collection("criminal_law_docs")
        doc_count = self.collection.count()
        print(f"  ✅ ChromaDB: {doc_count:,}개 문서")

        # LLM 클라이언트
        self.llm_model = os.getenv("LLM_MODEL", "alias:qwen4b")
        self.llm_client = create_llm_client(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            api_key=os.getenv("LLM_API_KEY"),
            model=self.llm_model,
            base_url=os.getenv("LLM_BASE_URL")
        )
        print(f"  ✅ LLM: {self.llm_model}")

        self.config["total_documents"] = doc_count
        self.config["llm_model"] = self.llm_model
        print("✅ Before RAG 시스템 준비 완료\n")

    def search_and_generate(self, query: str, top_k: int = 5) -> RAGResult:
        """검색 + LLM 답변 생성"""
        total_start = time.perf_counter()

        # 검색
        search_start = time.perf_counter()
        query_embedding = self.embedder.embed_query(query)

        # ChromaDB 검색
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        search_time = (time.perf_counter() - search_start) * 1000

        chunks = []
        scores = []

        # ChromaDB 결과 파싱
        if results and results.get('documents') and results['documents'][0]:
            documents = results['documents'][0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]

            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0
                score = 1.0 / (1.0 + distance)

                chunks.append({
                    "text": doc,
                    "score": score,
                    "source": metadata.get("source", "unknown")
                })
                scores.append(score)

        # LLM 답변 생성
        gen_start = time.perf_counter()
        context = self._format_context(chunks)
        answer = self._generate_answer(query, context)
        generation_time = (time.perf_counter() - gen_start) * 1000

        total_time = (time.perf_counter() - total_start) * 1000

        return RAGResult(
            query_id="",
            query=query,
            category="",
            search_time_ms=search_time,
            chunks=chunks,
            scores=scores,
            answer=answer,
            generation_time_ms=generation_time,
            total_time_ms=total_time
        )

    def _format_context(self, chunks: List[Dict], max_chars: int = 3000) -> str:
        """컨텍스트 포맷팅"""
        parts = []
        total = 0
        for i, chunk in enumerate(chunks, 1):
            text = chunk['text']
            if len(text) > 800:
                text = text[:800] + "..."
            part = f"[문서 {i}] ({chunk['source']})\n{text}"
            if total + len(part) > max_chars:
                break
            parts.append(part)
            total += len(part)
        return "\n\n".join(parts)

    def _generate_answer(self, query: str, context: str) -> str:
        """LLM 답변 생성"""
        system_prompt = """당신은 형사법 전문 AI 어시스턴트입니다.
주어진 법률 문서를 참고하여 질문에 정확하게 답변하세요."""

        user_prompt = f"""다음 법률 문서들을 참고하여 질문에 답변해주세요.

## 참고 문서
{context}

## 질문
{query}

## 답변"""

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]

        try:
            result = self.llm_client.chat(messages, temperature=0.1)
            return result
        except Exception as e:
            return f"[답변 생성 실패: {str(e)}]"


class AfterRAGSystem:
    """After RAG 시스템"""

    def __init__(self):
        self.embedder = None
        self.vectordb = None
        self.llm_client = None
        self.filter_types = ["source_판결문", "source_결정례"]
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
        from llm.llm_client import create_llm_client

        print("🔧 After RAG 시스템 설정 중...")

        # 원격 임베딩
        self.embedder = RemoteEmbedder(
            model="dragonkue/snowflake-arctic-embed-l-v2.0-ko"
        )
        print(f"  ✅ 임베딩: {self.config['embedding_model']}")

        # Qdrant
        self.vectordb = QdrantVectorDB(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            collection_name="law_documents",
            embedding_dim=1024
        )
        doc_count = self.vectordb.get_count()
        print(f"  ✅ Qdrant: {doc_count:,}개 문서")

        # LLM 클라이언트 (동일한 모델 사용)
        self.llm_model = os.getenv("LLM_MODEL", "alias:qwen4b")
        self.llm_client = create_llm_client(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            api_key=os.getenv("LLM_API_KEY"),
            model=self.llm_model,
            base_url=os.getenv("LLM_BASE_URL")
        )
        print(f"  ✅ LLM: {self.llm_model}")

        self.config["total_documents"] = doc_count
        self.config["llm_model"] = self.llm_model
        print("✅ After RAG 시스템 준비 완료\n")

    def search_and_generate(self, query: str, top_k: int = 5) -> RAGResult:
        """검색 + LLM 답변 생성 (필터링 적용)"""
        total_start = time.perf_counter()

        # 검색 (필터링)
        search_start = time.perf_counter()
        query_embedding = self.embedder.embed_query(query)
        results = self._search_with_filter(query_embedding, top_k)
        search_time = (time.perf_counter() - search_start) * 1000

        chunks = []
        scores = []
        for r in results:
            chunks.append({
                "text": r.get("text", ""),
                "score": r.get("score", 0),
                "source": r.get("metadata", {}).get("type",
                         r.get("metadata", {}).get("source", "unknown"))
            })
            scores.append(r.get("score", 0))

        # LLM 답변 생성
        gen_start = time.perf_counter()
        context = self._format_context(chunks)
        answer = self._generate_answer(query, context)
        generation_time = (time.perf_counter() - gen_start) * 1000

        total_time = (time.perf_counter() - total_start) * 1000

        return RAGResult(
            query_id="",
            query=query,
            category="",
            search_time_ms=search_time,
            chunks=chunks,
            scores=scores,
            answer=answer,
            generation_time_ms=generation_time,
            total_time_ms=total_time
        )

    def _search_with_filter(self, query_embedding, top_k: int) -> List[Dict]:
        """필터링된 검색"""
        from qdrant_client.models import Filter, FieldCondition, MatchAny

        try:
            filter_condition = Filter(
                should=[
                    FieldCondition(
                        key="type",
                        match=MatchAny(any=self.filter_types)
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

            formatted = []
            for point in results.points:
                payload = dict(point.payload) if point.payload else {}
                text = payload.pop('text', '')
                formatted.append({
                    "text": text,
                    "metadata": payload,
                    "score": point.score
                })
            return formatted

        except Exception as e:
            print(f"  ⚠️ 필터 검색 실패: {e}")
            return self.vectordb.search(query_embedding, top_k=top_k)

    def _format_context(self, chunks: List[Dict], max_chars: int = 3000) -> str:
        """컨텍스트 포맷팅"""
        parts = []
        total = 0
        for i, chunk in enumerate(chunks, 1):
            text = chunk['text']
            if len(text) > 800:
                text = text[:800] + "..."
            part = f"[문서 {i}] ({chunk['source']})\n{text}"
            if total + len(part) > max_chars:
                break
            parts.append(part)
            total += len(part)
        return "\n\n".join(parts)

    def _generate_answer(self, query: str, context: str) -> str:
        """LLM 답변 생성"""
        system_prompt = """당신은 형사법 전문 AI 어시스턴트입니다.
주어진 법률 문서를 참고하여 질문에 정확하게 답변하세요.
출처를 명시하고, 법률 상담이 필요할 수 있음을 안내하세요."""

        user_prompt = f"""다음 법률 문서들을 참고하여 질문에 답변해주세요.

## 참고 문서
{context}

## 질문
{query}

## 답변"""

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]

        try:
            result = self.llm_client.chat(messages, temperature=0.1)
            return result
        except Exception as e:
            return f"[답변 생성 실패: {str(e)}]"


class FullComparisonBenchmark:
    """전체 RAG 비교 벤치마크"""

    def __init__(self):
        self.before = BeforeRAGSystem()
        self.after = AfterRAGSystem()

    def setup(self):
        """시스템 초기화"""
        print("=" * 70)
        print("🔬 RAG 전체 파이프라인 비교 벤치마크")
        print("=" * 70)
        print(f"📅 {datetime.now().isoformat()}")
        print()

        self.before.setup()
        self.after.setup()

    def calculate_metrics(
        self,
        result: RAGResult,
        keywords: List[str],
        expected_topics: List[str]
    ) -> RAGResult:
        """품질 지표 계산"""
        # Hit@K
        for k in [1, 3, 5]:
            hit = False
            for chunk in result.chunks[:k]:
                for topic in expected_topics:
                    if topic.lower() in chunk['text'].lower():
                        hit = True
                        break
                if hit:
                    break
            result.hit_at_k[k] = hit

        # MRR
        result.mrr = 0.0
        for i, chunk in enumerate(result.chunks):
            for topic in expected_topics:
                if topic.lower() in chunk['text'].lower():
                    result.mrr = 1.0 / (i + 1)
                    break
            if result.mrr > 0:
                break

        # 답변 품질
        result.answer_length = len(result.answer)

        # 출처 포함 여부
        citation_patterns = [
            r'\[법령[:\s]', r'\[판례[:\s]', r'제\d+조',
            r'\d{4}[가-힣]+\d+', r'형법\s*제'
        ]
        result.has_citation = any(re.search(p, result.answer) for p in citation_patterns)

        # 면책조항 포함 여부
        disclaimer_patterns = [
            r'⚠️', r'주의', r'참고', r'법률\s*전문가',
            r'전문\s*상담', r'변호사'
        ]
        result.has_disclaimer = any(re.search(p, result.answer) for p in disclaimer_patterns)

        # 키워드 포함률
        keyword_hits = sum(1 for kw in keywords if kw.lower() in result.answer.lower())
        result.keyword_hit_rate = keyword_hits / len(keywords) if keywords else 0

        return result

    def run_comparison(self, queries_path: str, top_k: int = 5) -> FullComparisonResult:
        """비교 벤치마크 실행"""
        with open(queries_path, 'r', encoding='utf-8') as f:
            queries_data = json.load(f)

        queries = queries_data['queries']
        print(f"\n📊 전체 RAG 비교 시작: {len(queries)}개 쿼리")
        print("=" * 70)

        before_results = []
        after_results = []
        query_comparisons = []

        for q in queries:
            print(f"\n[{q['id']}] {q['query']}")
            keywords = q.get('keywords', [])
            expected_topics = q.get('expected_topics', keywords)

            # Before 실행
            before_result = self.before.search_and_generate(q['query'], top_k=top_k)
            before_result.query_id = q['id']
            before_result.category = q['category']
            before_result = self.calculate_metrics(before_result, keywords, expected_topics)
            before_results.append(before_result)

            # After 실행
            after_result = self.after.search_and_generate(q['query'], top_k=top_k)
            after_result.query_id = q['id']
            after_result.category = q['category']
            after_result = self.calculate_metrics(after_result, keywords, expected_topics)
            after_results.append(after_result)

            # 출력
            print(f"   Before: 검색={before_result.search_time_ms:.0f}ms | "
                  f"전체={before_result.total_time_ms:.0f}ms | "
                  f"Hit@1={before_result.hit_at_k.get(1)} | "
                  f"답변={before_result.answer_length}자")
            print(f"   After:  검색={after_result.search_time_ms:.0f}ms | "
                  f"전체={after_result.total_time_ms:.0f}ms | "
                  f"Hit@1={after_result.hit_at_k.get(1)} | "
                  f"답변={after_result.answer_length}자")

            # 쿼리별 비교 저장
            query_comparisons.append({
                "query_id": q['id'],
                "query": q['query'],
                "category": q['category'],
                "before": {
                    "search_time_ms": before_result.search_time_ms,
                    "total_time_ms": before_result.total_time_ms,
                    "hit_at_1": before_result.hit_at_k.get(1, False),
                    "mrr": before_result.mrr,
                    "answer": before_result.answer,
                    "answer_length": before_result.answer_length,
                    "has_citation": before_result.has_citation,
                    "has_disclaimer": before_result.has_disclaimer,
                    "top_chunks": [
                        {"text_preview": c['text'][:150], "score": c['score']}
                        for c in before_result.chunks[:2]
                    ]
                },
                "after": {
                    "search_time_ms": after_result.search_time_ms,
                    "total_time_ms": after_result.total_time_ms,
                    "hit_at_1": after_result.hit_at_k.get(1, False),
                    "mrr": after_result.mrr,
                    "answer": after_result.answer,
                    "answer_length": after_result.answer_length,
                    "has_citation": after_result.has_citation,
                    "has_disclaimer": after_result.has_disclaimer,
                    "top_chunks": [
                        {"text_preview": c['text'][:150], "score": c['score']}
                        for c in after_result.chunks[:2]
                    ]
                }
            })

        # 집계
        return FullComparisonResult(
            timestamp=datetime.now().isoformat(),
            before_config=self.before.config,
            after_config=self.after.config,
            before_avg_search_time_ms=np.mean([r.search_time_ms for r in before_results]),
            after_avg_search_time_ms=np.mean([r.search_time_ms for r in after_results]),
            before_avg_total_time_ms=np.mean([r.total_time_ms for r in before_results]),
            after_avg_total_time_ms=np.mean([r.total_time_ms for r in after_results]),
            before_hit_rate_1=np.mean([r.hit_at_k.get(1, False) for r in before_results]),
            after_hit_rate_1=np.mean([r.hit_at_k.get(1, False) for r in after_results]),
            before_mrr=np.mean([r.mrr for r in before_results]),
            after_mrr=np.mean([r.mrr for r in after_results]),
            before_avg_answer_length=np.mean([r.answer_length for r in before_results]),
            after_avg_answer_length=np.mean([r.answer_length for r in after_results]),
            before_citation_rate=np.mean([1 if r.has_citation else 0 for r in before_results]),
            after_citation_rate=np.mean([1 if r.has_citation else 0 for r in after_results]),
            before_disclaimer_rate=np.mean([1 if r.has_disclaimer else 0 for r in before_results]),
            after_disclaimer_rate=np.mean([1 if r.has_disclaimer else 0 for r in after_results]),
            query_results=query_comparisons
        )

    def print_summary(self, result: FullComparisonResult):
        """결과 요약 출력"""
        print("\n" + "=" * 70)
        print("📊 전체 RAG 비교 결과 요약")
        print("=" * 70)

        print("\n[ 시스템 설정 ]")
        print(f"  Before: {result.before_config['vector_db']} + {result.before_config['embedding_model']}")
        print(f"  After:  {result.after_config['vector_db']} + {result.after_config['embedding_model']}")

        print("\n[ 성능 비교 ]")
        print(f"  검색 시간: {result.before_avg_search_time_ms:.0f}ms → {result.after_avg_search_time_ms:.0f}ms")
        print(f"  전체 시간: {result.before_avg_total_time_ms:.0f}ms → {result.after_avg_total_time_ms:.0f}ms")

        print("\n[ 검색 품질 비교 ] ⭐ 핵심")
        print(f"  Hit Rate@1: {result.before_hit_rate_1:.1%} → {result.after_hit_rate_1:.1%}")
        print(f"  MRR:        {result.before_mrr:.4f} → {result.after_mrr:.4f}")

        print("\n[ 답변 품질 비교 ]")
        print(f"  평균 답변 길이: {result.before_avg_answer_length:.0f}자 → {result.after_avg_answer_length:.0f}자")
        print(f"  출처 포함률:   {result.before_citation_rate:.1%} → {result.after_citation_rate:.1%}")
        print(f"  면책조항 포함: {result.before_disclaimer_rate:.1%} → {result.after_disclaimer_rate:.1%}")

        print("\n[ 종합 평가 ]")
        improvements = []
        if result.after_hit_rate_1 > result.before_hit_rate_1:
            improvements.append("검색 정확도 향상")
        if result.after_mrr > result.before_mrr:
            improvements.append("MRR 향상")
        if result.after_avg_search_time_ms < result.before_avg_search_time_ms:
            improvements.append("검색 속도 향상")
        if result.after_citation_rate > result.before_citation_rate:
            improvements.append("출처 명시 향상")

        if improvements:
            print(f"  ✅ 개선 항목: {', '.join(improvements)}")
        else:
            print("  ⚠️ 개선 항목 없음")

        print("=" * 70)

    def save_results(self, result: FullComparisonResult, output_dir: str) -> str:
        """결과 저장"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"full_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_path / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)

        print(f"\n✅ 결과 저장: {filepath}")
        return str(filepath)


def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="RAG 전체 파이프라인 비교")
    parser.add_argument("--queries", type=str,
                       default=str(BASE_DIR / "scripts" / "rag_benchmark" / "queries" / "test_queries.json"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=str,
                       default=str(BASE_DIR / "scripts" / "rag_benchmark" / "results"))

    args = parser.parse_args()

    benchmark = FullComparisonBenchmark()
    benchmark.setup()

    result = benchmark.run_comparison(args.queries, top_k=args.top_k)
    benchmark.print_summary(result)
    benchmark.save_results(result, args.output)


if __name__ == "__main__":
    main()
