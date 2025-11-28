"""
RAG 전체 파이프라인 벤치마크

검색(Retrieval) + LLM 답변 생성(Generation) 전체 측정
Before/After 비교를 위한 발표용 데이터 수집
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
    """단일 RAG 결과"""
    query_id: str
    query: str
    category: str

    # 검색 결과
    retrieval_time_ms: float
    retrieved_chunks: List[Dict[str, Any]]
    top_scores: List[float]

    # LLM 답변
    answer: str
    generation_time_ms: float
    total_time_ms: float

    # 품질 지표
    keyword_hit_rate: float
    hit_at_k: Dict[int, bool]
    mrr: float


@dataclass
class RAGBenchmarkMetrics:
    """RAG 벤치마크 전체 메트릭"""
    timestamp: str
    config_name: str

    # 시스템 설정
    vector_db: str
    embedding_model: str
    embedding_dim: int
    llm_model: str
    total_documents: int
    chunking_strategy: str

    # 검색 성능
    avg_retrieval_time_ms: float
    avg_generation_time_ms: float
    avg_total_time_ms: float

    # 검색 품질
    avg_top1_score: float
    avg_top3_score: float
    avg_top1_score_normalized: float  # 정규화된 스코어 (0-1)
    hit_rate_at_1: float
    hit_rate_at_3: float
    hit_rate_at_5: float
    mrr: float
    avg_keyword_hit_rate: float

    # 카테고리별 성능
    category_performance: Dict[str, Dict[str, float]]

    # 쿼리별 상세 결과 (발표용)
    query_results: List[Dict]

    # 소스별 성능 (판결문/법령/결정례) - default 있는 필드는 마지막에
    source_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # 청킹 통계
    chunking_stats: Dict[str, Any] = field(default_factory=dict)

    # 토큰 사용량 통계
    token_usage: Dict[str, Any] = field(default_factory=dict)

    # 답변 품질 지표 (신뢰도 측정용)
    answer_quality: Dict[str, Any] = field(default_factory=dict)


class RAGBenchmark:
    """RAG 전체 파이프라인 벤치마크"""

    def __init__(self, config_name: str = "default"):
        self.config_name = config_name
        self.retriever = None
        self.chatbot = None
        self.llm_client = None
        self.vectordb = None
        self.embedder = None

    def setup_current_system(self):
        """현재 시스템 설정 (Before 측정용)"""
        from embeddings.embedder import KoreanLegalEmbedder
        from embeddings.vectordb import ChromaVectorDB
        from retrieval.hybrid_retriever import HybridRetriever
        from retrieval.retriever import LegalDocumentRetriever
        from retrieval.bm25_index import BM25Index
        from llm.llm_client import create_llm_client
        from llm.rag_chatbot import RAGChatbot

        print("🔧 현재 시스템 설정 중...")

        # 임베딩 모델
        self.embedder = KoreanLegalEmbedder()
        self.embedding_model = self.embedder.model_name
        self.embedding_dim = self.embedder.get_embedding_dimension()
        print(f"  ✅ 임베딩: {self.embedding_model} ({self.embedding_dim}d)")

        # VectorDB
        chroma_dir = BASE_DIR / "data" / "vectordb" / "chroma_criminal_law"
        self.vectordb = ChromaVectorDB(
            collection_name="criminal_law_docs",
            persist_directory=str(chroma_dir)
        )
        self.total_documents = self.vectordb.get_count()
        print(f"  ✅ ChromaDB: {self.total_documents:,}개 문서")

        # Semantic Retriever
        semantic_retriever = LegalDocumentRetriever(
            vectordb=self.vectordb,
            embedder=self.embedder
        )

        # BM25 Index
        bm25_dir = BASE_DIR / "data" / "bm25_index"
        bm25 = BM25Index([])
        if bm25_dir.exists():
            bm25.load(str(bm25_dir))
            print(f"  ✅ BM25 인덱스 로드")

        # Hybrid Retriever
        self.retriever = HybridRetriever(
            semantic_retriever=semantic_retriever,
            bm25_index=bm25
        )

        # LLM Client
        self.llm_model = os.getenv("LLM_MODEL", "alias:qwen4b")
        self.llm_client = create_llm_client(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            api_key=os.getenv("LLM_API_KEY"),
            model=self.llm_model,
            base_url=os.getenv("LLM_BASE_URL")
        )
        print(f"  ✅ LLM: {self.llm_model}")

        # RAG Chatbot
        self.chatbot = RAGChatbot(
            llm_client=self.llm_client,
            retriever=self.retriever
        )

        print("✅ 시스템 설정 완료\n")

    def search_and_generate(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """검색 + LLM 답변 생성"""
        total_start = time.perf_counter()

        # 1. 검색
        retrieval_start = time.perf_counter()
        retrieved_docs = self.retriever.retrieve(query, top_k=top_k)
        retrieval_time = (time.perf_counter() - retrieval_start) * 1000

        # 검색 결과 정리
        chunks = []
        scores = []
        for doc in retrieved_docs:
            chunks.append({
                'text': doc.get('text', doc.get('content', '')),
                'score': doc.get('score', 0),
                'metadata': doc.get('metadata', {}),
                'source': doc.get('metadata', {}).get('source', 'unknown')
            })
            scores.append(doc.get('score', 0))

        # 2. LLM 답변 생성
        generation_start = time.perf_counter()

        # context 생성
        context = self._format_context(retrieved_docs)

        # LLM 호출 (토큰 사용량 포함)
        llm_result = self._generate_answer(query, context)

        generation_time = (time.perf_counter() - generation_start) * 1000
        total_time = (time.perf_counter() - total_start) * 1000

        return {
            'chunks': chunks,
            'scores': scores,
            'answer': llm_result['answer'],
            'token_usage': llm_result.get('usage'),
            'retrieval_time_ms': retrieval_time,
            'generation_time_ms': generation_time,
            'total_time_ms': total_time
        }

    def _format_context(self, docs: List[Dict], max_chars: int = 3000) -> str:
        """검색 결과를 context 문자열로 변환 (토큰 제한 고려)"""
        context_parts = []
        total_chars = 0

        for i, doc in enumerate(docs, 1):
            text = doc.get('text', doc.get('content', ''))
            source = doc.get('metadata', {}).get('source', 'unknown')

            # 개별 문서 길이 제한
            if len(text) > 800:
                text = text[:800] + "..."

            part = f"[문서 {i}] ({source})\n{text}"

            # 전체 context 길이 제한
            if total_chars + len(part) > max_chars:
                break

            context_parts.append(part)
            total_chars += len(part)

        return "\n\n".join(context_parts)

    def _generate_answer(self, query: str, context: str) -> Dict[str, Any]:
        """LLM으로 답변 생성 (토큰 사용량 포함)"""
        system_prompt = """당신은 형사법 전문 AI 어시스턴트입니다.
주어진 법률 문서를 참고하여 질문에 정확하고 상세하게 답변하세요.
답변은 검색된 문서의 내용을 기반으로 하되, 법률 전문 용어를 적절히 사용하세요."""

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
            # chat_with_usage 메서드 사용하여 토큰 정보도 함께 반환
            result = self.llm_client.chat_with_usage(messages, temperature=0.1)
            return {
                'answer': result['content'],
                'usage': result.get('usage')
            }
        except Exception as e:
            return {
                'answer': f"[답변 생성 실패: {str(e)}]",
                'usage': None
            }

    def normalize_score(self, score: float, method: str = "minmax") -> float:
        """
        검색 스코어 정규화 (0-1 범위)

        HybridRetriever의 스코어는 BM25와 Semantic 스코어가 혼합되어
        절대값 비교가 어려움. 정규화를 통해 Before/After 비교 용이하게 함.
        """
        if method == "sigmoid":
            # Sigmoid 정규화: 극단값 완화
            import math
            return 1 / (1 + math.exp(-10 * (score - 0.01)))
        elif method == "minmax":
            # Min-Max 정규화: 관찰된 범위 기준
            # HybridRetriever 스코어 범위: 약 0.005 ~ 0.015
            min_score, max_score = 0.005, 0.02
            normalized = (score - min_score) / (max_score - min_score)
            return max(0.0, min(1.0, normalized))
        else:
            return score

    def calculate_metrics(self, results: List[Dict], keywords: List[str],
                         expected_topics: List[str]) -> Dict[str, Any]:
        """검색 품질 지표 계산"""
        scores = results.get('scores', [])
        chunks = results.get('chunks', [])

        # 키워드 매칭률
        keyword_hits = 0
        for keyword in keywords:
            for chunk in chunks[:5]:
                if keyword.lower() in chunk['text'].lower():
                    keyword_hits += 1
                    break
        keyword_hit_rate = keyword_hits / len(keywords) if keywords else 0

        # Hit@K
        hit_at_k = {}
        for k in [1, 3, 5, 10]:
            hit = False
            for chunk in chunks[:k]:
                for topic in expected_topics:
                    if topic.lower() in chunk['text'].lower():
                        hit = True
                        break
                if hit:
                    break
            hit_at_k[k] = hit

        # MRR
        mrr = 0.0
        for i, chunk in enumerate(chunks):
            for topic in expected_topics:
                if topic.lower() in chunk['text'].lower():
                    mrr = 1.0 / (i + 1)
                    break
            if mrr > 0:
                break

        # 정규화된 스코어
        normalized_scores = [self.normalize_score(s) for s in scores] if scores else []

        # 소스별 분류
        source_distribution = {}
        for chunk in chunks:
            source = chunk.get('source', 'unknown')
            source_distribution[source] = source_distribution.get(source, 0) + 1

        return {
            'keyword_hit_rate': keyword_hit_rate,
            'hit_at_k': hit_at_k,
            'mrr': mrr,
            'normalized_scores': normalized_scores,
            'source_distribution': source_distribution
        }

    def calculate_answer_quality(self, answer: str, keywords: List[str]) -> Dict[str, Any]:
        """
        답변 품질 지표 계산 (신뢰도 측정용)

        Args:
            answer: LLM 답변
            keywords: 기대 키워드 목록

        Returns:
            dict with quality metrics
        """
        # 1. 응답 길이/단어 수
        answer_length = len(answer)
        # 한국어 단어 수: 공백 기준 + 연속 한글/영문 기준 혼합
        word_count = len(answer.split())

        # 2. 출처 포함 여부 (법령, 판례, 조문 참조)
        citation_patterns = [
            r'\[법령[:\s]',           # [법령: ...
            r'\[판례[:\s]',           # [판례: ...
            r'\[결정례[:\s]',          # [결정례: ...
            r'제\d+조',               # 제123조
            r'\d{4}[가-힣]+\d+',      # 2023도1234 형식 판례번호
            r'형법\s*제',             # 형법 제...
            r'도로교통법\s*제',         # 도로교통법 제...
            r'특정범죄.*?가중처벌',     # 특정범죄가중처벌법
        ]
        has_citation = any(re.search(pattern, answer) for pattern in citation_patterns)
        citation_count = sum(1 for pattern in citation_patterns if re.search(pattern, answer))

        # 3. 면책 조항 포함 여부
        disclaimer_patterns = [
            r'⚠️',
            r'주의[:\s]',
            r'참고[:\s]',
            r'법률\s*전문가',
            r'전문\s*상담',
            r'실제\s*사안',
            r'개별\s*사례',
            r'일반적인\s*정보',
        ]
        has_disclaimer = any(re.search(pattern, answer) for pattern in disclaimer_patterns)

        # 4. 핵심 키워드 포함률 (답변에서)
        keyword_hits = 0
        matched_keywords = []
        for keyword in keywords:
            if keyword.lower() in answer.lower():
                keyword_hits += 1
                matched_keywords.append(keyword)
        answer_keyword_hit_rate = keyword_hits / len(keywords) if keywords else 0

        # 5. 구조화 여부 (번호 매기기, 제목 등)
        has_structure = bool(re.search(r'(^\d+\.|^-\s|^•\s|\n\d+\.\s|\n-\s)', answer, re.MULTILINE))

        return {
            'answer_length': answer_length,
            'word_count': word_count,
            'has_citation': has_citation,
            'citation_count': citation_count,
            'has_disclaimer': has_disclaimer,
            'answer_keyword_hit_rate': answer_keyword_hit_rate,
            'matched_keywords': matched_keywords,
            'has_structure': has_structure
        }

    def collect_chunking_stats(self, sample_size: int = 5000) -> Dict[str, Any]:
        """청킹 통계 수집 (Before/After 비교용 상세 정보)"""
        print(f"📊 청킹 통계 수집 중...")

        try:
            # ChromaDB collection의 peek() 메서드 사용
            sample = self.vectordb.collection.peek(limit=sample_size)
            if not sample or not sample.get('documents'):
                return {}

            documents = sample['documents']
            metadatas = sample.get('metadatas', [])

            lengths = [len(doc) for doc in documents]

            # 소스별 분포 및 통계
            source_stats = {}
            for doc, meta in zip(documents, metadatas):
                source = meta.get('source', meta.get('type', 'unknown'))
                if source not in source_stats:
                    source_stats[source] = {'count': 0, 'lengths': []}
                source_stats[source]['count'] += 1
                source_stats[source]['lengths'].append(len(doc))

            # 소스별 상세 통계
            source_detailed = {}
            for source, data in source_stats.items():
                lens = data['lengths']
                source_detailed[source] = {
                    'count': data['count'],
                    'percentage': round(data['count'] / len(documents) * 100, 2),
                    'avg_length': round(float(np.mean(lens)), 1),
                    'min_length': int(np.min(lens)),
                    'max_length': int(np.max(lens)),
                    'std_length': round(float(np.std(lens)), 1)
                }

            # 길이 분포 (히스토그램용)
            length_buckets = {
                '0-200': 0,
                '201-400': 0,
                '401-600': 0,
                '601-800': 0,
                '801-1000': 0,
                '1000+': 0
            }
            for length in lengths:
                if length <= 200:
                    length_buckets['0-200'] += 1
                elif length <= 400:
                    length_buckets['201-400'] += 1
                elif length <= 600:
                    length_buckets['401-600'] += 1
                elif length <= 800:
                    length_buckets['601-800'] += 1
                elif length <= 1000:
                    length_buckets['801-1000'] += 1
                else:
                    length_buckets['1000+'] += 1

            return {
                'total_chunks': self.total_documents,
                'sample_size': len(documents),
                'avg_length': round(float(np.mean(lengths)), 1),
                'min_length': int(np.min(lengths)),
                'max_length': int(np.max(lengths)),
                'std_length': round(float(np.std(lengths)), 1),
                'median_length': round(float(np.median(lengths)), 1),
                'percentile_25': round(float(np.percentile(lengths, 25)), 1),
                'percentile_75': round(float(np.percentile(lengths, 75)), 1),
                'percentile_90': round(float(np.percentile(lengths, 90)), 1),
                'length_distribution': length_buckets,
                'source_stats': source_detailed
            }
        except Exception as e:
            print(f"  ⚠️ 청킹 통계 수집 실패: {e}")
            return {}

    def run_benchmark(self, queries_path: str, top_k: int = 3) -> RAGBenchmarkMetrics:
        """벤치마크 실행"""
        with open(queries_path, 'r', encoding='utf-8') as f:
            queries_data = json.load(f)

        queries = queries_data['queries']
        print(f"\n📊 RAG 벤치마크 시작: {len(queries)}개 쿼리")
        print("=" * 70)

        all_results = []
        all_retrieval_times = []
        all_generation_times = []
        all_total_times = []
        all_top1_scores = []
        all_top3_scores = []
        all_top1_scores_normalized = []  # 정규화된 스코어
        all_keyword_hits = []
        all_hit_at_k = {1: [], 3: [], 5: [], 10: []}
        all_mrr = []
        category_results = {}
        source_results = {}  # 소스별 성능
        all_token_usage = []  # 토큰 사용량
        all_answer_quality = []  # 답변 품질 지표

        for q in queries:
            print(f"\n[{q['id']}] {q['query']}")

            # 검색 + 답변 생성
            results = self.search_and_generate(q['query'], top_k=top_k)

            # 품질 지표 계산
            keywords = q.get('keywords', [])
            expected_topics = q.get('expected_topics', keywords)
            metrics = self.calculate_metrics(results, keywords, expected_topics)

            # 답변 품질 지표 계산
            answer_quality = self.calculate_answer_quality(results['answer'], keywords)

            # 결과 저장
            query_result = {
                'query_id': q['id'],
                'query': q['query'],
                'category': q['category'],
                'keywords': keywords,
                'expected_topics': expected_topics,

                # 시간
                'retrieval_time_ms': results['retrieval_time_ms'],
                'generation_time_ms': results['generation_time_ms'],
                'total_time_ms': results['total_time_ms'],

                # 검색 결과
                'top_scores': results['scores'][:5],
                'retrieved_chunks': [
                    {
                        'rank': i + 1,
                        'score': c['score'],
                        'text_preview': c['text'][:200] + '...' if len(c['text']) > 200 else c['text'],
                        'text_full': c['text'],
                        'text_length': len(c['text']),
                        'source': c['source']
                    }
                    for i, c in enumerate(results['chunks'][:3])
                ],

                # LLM 답변
                'answer': results['answer'],
                'token_usage': results.get('token_usage'),

                # 품질 지표
                'keyword_hit_rate': metrics['keyword_hit_rate'],
                'hit_at_k': metrics['hit_at_k'],
                'mrr': metrics['mrr'],
                'normalized_top1_score': metrics['normalized_scores'][0] if metrics['normalized_scores'] else 0,
                'source_distribution': metrics['source_distribution'],

                # 답변 품질 지표 (신뢰도 측정용)
                'answer_quality': answer_quality
            }
            all_results.append(query_result)

            # 답변 품질 수집
            all_answer_quality.append(answer_quality)

            # 집계
            all_retrieval_times.append(results['retrieval_time_ms'])
            all_generation_times.append(results['generation_time_ms'])
            all_total_times.append(results['total_time_ms'])

            scores = results['scores']
            if scores:
                all_top1_scores.append(scores[0])
                all_top3_scores.append(np.mean(scores[:3]) if len(scores) >= 3 else np.mean(scores))
                # 정규화된 스코어 수집
                if metrics['normalized_scores']:
                    all_top1_scores_normalized.append(metrics['normalized_scores'][0])

            all_keyword_hits.append(metrics['keyword_hit_rate'])
            for k in [1, 3, 5, 10]:
                all_hit_at_k[k].append(metrics['hit_at_k'].get(k, False))
            all_mrr.append(metrics['mrr'])

            # 카테고리별 수집
            cat = q['category']
            if cat not in category_results:
                category_results[cat] = {'scores': [], 'times': [], 'hits': [], 'mrr': [], 'normalized_scores': []}
            category_results[cat]['scores'].append(scores[0] if scores else 0)
            category_results[cat]['times'].append(results['total_time_ms'])
            category_results[cat]['hits'].append(metrics['keyword_hit_rate'])
            category_results[cat]['mrr'].append(metrics['mrr'])
            if metrics['normalized_scores']:
                category_results[cat]['normalized_scores'].append(metrics['normalized_scores'][0])

            # 소스별 성능 수집
            for chunk in results['chunks']:
                source = chunk.get('source', 'unknown')
                if source not in source_results:
                    source_results[source] = {'scores': [], 'mrr': [], 'count': 0}
                source_results[source]['scores'].append(chunk.get('score', 0))
                source_results[source]['count'] += 1
            # 이 쿼리의 top-1 결과 소스에 MRR 기록
            if results['chunks']:
                top_source = results['chunks'][0].get('source', 'unknown')
                if top_source not in source_results:
                    source_results[top_source] = {'scores': [], 'mrr': [], 'count': 0}
                source_results[top_source]['mrr'].append(metrics['mrr'])

            # 토큰 사용량 수집
            if results.get('token_usage'):
                all_token_usage.append(results['token_usage'])

            # 출력
            print(f"   검색: {results['retrieval_time_ms']:.0f}ms | 생성: {results['generation_time_ms']:.0f}ms | 전체: {results['total_time_ms']:.0f}ms")
            print(f"   Top-1 Score: {scores[0]:.4f}" if scores else "   No results")
            print(f"   Hit@1/3/5: {metrics['hit_at_k'].get(1)}/{metrics['hit_at_k'].get(3)}/{metrics['hit_at_k'].get(5)} | MRR: {metrics['mrr']:.4f}")
            # 토큰 사용량 출력
            if results.get('token_usage'):
                tu = results['token_usage']
                print(f"   토큰: 입력={tu['prompt_tokens']:,} | 출력={tu['completion_tokens']:,} | 합계={tu['total_tokens']:,}")
            # 답변 품질 지표 출력
            aq = answer_quality
            citation_mark = "✓" if aq['has_citation'] else "✗"
            disclaimer_mark = "✓" if aq['has_disclaimer'] else "✗"
            print(f"   품질: 길이={aq['answer_length']:,}자 | 단어={aq['word_count']} | 출처={citation_mark} | 면책={disclaimer_mark} | 키워드={aq['answer_keyword_hit_rate']:.0%}")
            print(f"   답변 미리보기: {results['answer'][:100]}..." if len(results['answer']) > 100 else f"   답변: {results['answer']}")

        # 청킹 통계
        chunking_stats = self.collect_chunking_stats()

        # 카테고리별 성능
        category_performance = {}
        for cat, data in category_results.items():
            category_performance[cat] = {
                'avg_score': float(np.mean(data['scores'])),
                'avg_score_normalized': float(np.mean(data['normalized_scores'])) if data['normalized_scores'] else 0,
                'avg_time': float(np.mean(data['times'])),
                'avg_hit_rate': float(np.mean(data['hits'])),
                'avg_mrr': float(np.mean(data['mrr']))
            }

        # 소스별 성능 (판결문/법령/결정례 등)
        source_performance = {}
        for source, data in source_results.items():
            source_performance[source] = {
                'result_count': data['count'],
                'avg_score': float(np.mean(data['scores'])) if data['scores'] else 0,
                'avg_mrr': float(np.mean(data['mrr'])) if data['mrr'] else 0,
                'top1_count': len(data['mrr'])  # top-1으로 선택된 횟수
            }

        # 토큰 사용량 통계
        token_usage_stats = {}
        if all_token_usage:
            total_prompt = sum(t.get('prompt_tokens', 0) for t in all_token_usage)
            total_completion = sum(t.get('completion_tokens', 0) for t in all_token_usage)
            total_tokens = sum(t.get('total_tokens', 0) for t in all_token_usage)
            token_usage_stats = {
                'total_prompt_tokens': total_prompt,
                'total_completion_tokens': total_completion,
                'total_tokens': total_tokens,
                'avg_prompt_tokens': total_prompt / len(all_token_usage),
                'avg_completion_tokens': total_completion / len(all_token_usage),
                'avg_total_tokens': total_tokens / len(all_token_usage),
                'query_count': len(all_token_usage),
                'per_query': all_token_usage
            }

        # 답변 품질 통계
        answer_quality_stats = {}
        if all_answer_quality:
            answer_quality_stats = {
                'avg_answer_length': float(np.mean([aq['answer_length'] for aq in all_answer_quality])),
                'avg_word_count': float(np.mean([aq['word_count'] for aq in all_answer_quality])),
                'min_answer_length': int(np.min([aq['answer_length'] for aq in all_answer_quality])),
                'max_answer_length': int(np.max([aq['answer_length'] for aq in all_answer_quality])),
                'citation_rate': float(np.mean([1 if aq['has_citation'] else 0 for aq in all_answer_quality])),
                'disclaimer_rate': float(np.mean([1 if aq['has_disclaimer'] else 0 for aq in all_answer_quality])),
                'avg_answer_keyword_hit_rate': float(np.mean([aq['answer_keyword_hit_rate'] for aq in all_answer_quality])),
                'structure_rate': float(np.mean([1 if aq['has_structure'] else 0 for aq in all_answer_quality])),
                'query_count': len(all_answer_quality)
            }

        # 메트릭 생성
        metrics = RAGBenchmarkMetrics(
            timestamp=datetime.now().isoformat(),
            config_name=self.config_name,
            vector_db="chroma",
            embedding_model=self.embedding_model,
            embedding_dim=self.embedding_dim,
            llm_model=self.llm_model,
            total_documents=self.total_documents,
            chunking_strategy="fixed_500" if "before" in self.config_name.lower() else "legal_specialized",

            avg_retrieval_time_ms=float(np.mean(all_retrieval_times)),
            avg_generation_time_ms=float(np.mean(all_generation_times)),
            avg_total_time_ms=float(np.mean(all_total_times)),

            avg_top1_score=float(np.mean(all_top1_scores)) if all_top1_scores else 0,
            avg_top3_score=float(np.mean(all_top3_scores)) if all_top3_scores else 0,
            avg_top1_score_normalized=float(np.mean(all_top1_scores_normalized)) if all_top1_scores_normalized else 0,
            hit_rate_at_1=float(np.mean(all_hit_at_k[1])),
            hit_rate_at_3=float(np.mean(all_hit_at_k[3])),
            hit_rate_at_5=float(np.mean(all_hit_at_k[5])),
            mrr=float(np.mean(all_mrr)),
            avg_keyword_hit_rate=float(np.mean(all_keyword_hits)),

            category_performance=category_performance,
            source_performance=source_performance,
            query_results=all_results,
            chunking_stats=chunking_stats,
            token_usage=token_usage_stats,
            answer_quality=answer_quality_stats
        )

        return metrics

    def save_results(self, metrics: RAGBenchmarkMetrics, output_path: str):
        """결과 저장"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(metrics), f, ensure_ascii=False, indent=2)

        print(f"\n✅ 결과 저장: {output_file}")

    def print_summary(self, metrics: RAGBenchmarkMetrics):
        """결과 요약 출력"""
        print("\n" + "=" * 70)
        print("📊 RAG 벤치마크 결과 요약")
        print("=" * 70)
        print(f"설정: {metrics.config_name}")
        print(f"시간: {metrics.timestamp}")

        print("\n[ 시스템 설정 ]")
        print(f"  VectorDB: {metrics.vector_db}")
        print(f"  임베딩: {metrics.embedding_model} ({metrics.embedding_dim}d)")
        print(f"  LLM: {metrics.llm_model}")
        print(f"  총 문서 수: {metrics.total_documents:,}")
        print(f"  청킹 전략: {metrics.chunking_strategy}")

        print("\n[ 성능 (시간) ]")
        print(f"  평균 검색 시간: {metrics.avg_retrieval_time_ms:.0f}ms")
        print(f"  평균 생성 시간: {metrics.avg_generation_time_ms:.0f}ms")
        print(f"  평균 전체 시간: {metrics.avg_total_time_ms:.0f}ms")

        print("\n[ 검색 품질 ] ⭐ 발표 핵심")
        print(f"  평균 Top-1 Score (raw): {metrics.avg_top1_score:.4f}")
        print(f"  평균 Top-1 Score (normalized): {metrics.avg_top1_score_normalized:.4f}")
        print(f"  Hit Rate@1: {metrics.hit_rate_at_1:.1%}")
        print(f"  Hit Rate@3: {metrics.hit_rate_at_3:.1%}")
        print(f"  Hit Rate@5: {metrics.hit_rate_at_5:.1%}")
        print(f"  MRR: {metrics.mrr:.4f}")
        print(f"  키워드 매칭률: {metrics.avg_keyword_hit_rate:.1%}")

        print("\n[ 카테고리별 성능 ]")
        for cat, perf in metrics.category_performance.items():
            print(f"  {cat}: Score={perf['avg_score']:.4f}, Norm={perf['avg_score_normalized']:.2f}, MRR={perf['avg_mrr']:.4f}")

        print("\n[ 소스별 성능 (판결문/법령/결정례) ] ⭐ NEW")
        if metrics.source_performance:
            for source, perf in sorted(metrics.source_performance.items(), key=lambda x: -x[1]['result_count']):
                print(f"  {source}: 검색건수={perf['result_count']}, Top-1횟수={perf['top1_count']}, MRR={perf['avg_mrr']:.4f}")

        print("\n[ 청킹 통계 ] ⭐ NEW")
        if metrics.chunking_stats:
            cs = metrics.chunking_stats
            print(f"  총 청크 수: {cs.get('total_chunks', 'N/A'):,}")
            print(f"  평균 길이: {cs.get('avg_length', 'N/A')} chars")
            print(f"  중간값: {cs.get('median_length', 'N/A')} chars")
            print(f"  표준편차: {cs.get('std_length', 'N/A')}")
            print(f"  25/75/90 백분위: {cs.get('percentile_25', 'N/A')}/{cs.get('percentile_75', 'N/A')}/{cs.get('percentile_90', 'N/A')}")
            if cs.get('length_distribution'):
                print(f"  길이 분포: {cs['length_distribution']}")
            if cs.get('source_stats'):
                print("  소스별 청크 통계:")
                for src, stats in cs['source_stats'].items():
                    print(f"    {src}: {stats['count']}개 ({stats['percentage']:.1f}%), 평균={stats['avg_length']:.0f}자")

        print("\n[ 토큰 사용량 ]")
        if metrics.token_usage:
            tu = metrics.token_usage
            print(f"  총 입력 토큰: {tu.get('total_prompt_tokens', 0):,}")
            print(f"  총 출력 토큰: {tu.get('total_completion_tokens', 0):,}")
            print(f"  총 토큰: {tu.get('total_tokens', 0):,}")
            print(f"  평균 입력 토큰/쿼리: {tu.get('avg_prompt_tokens', 0):,.0f}")
            print(f"  평균 출력 토큰/쿼리: {tu.get('avg_completion_tokens', 0):,.0f}")
            print(f"  평균 총 토큰/쿼리: {tu.get('avg_total_tokens', 0):,.0f}")
        else:
            print("  토큰 사용량 정보 없음 (API가 usage 미제공)")

        print("\n[ 답변 품질 지표 ] ⭐ 발표 핵심 (신뢰도)")
        if metrics.answer_quality:
            aq = metrics.answer_quality
            print(f"  평균 답변 길이: {aq.get('avg_answer_length', 0):,.0f}자")
            print(f"  평균 단어 수: {aq.get('avg_word_count', 0):,.0f}개")
            print(f"  답변 길이 범위: {aq.get('min_answer_length', 0):,} ~ {aq.get('max_answer_length', 0):,}자")
            print(f"  출처 포함률: {aq.get('citation_rate', 0):.1%}")
            print(f"  면책 조항 포함률: {aq.get('disclaimer_rate', 0):.1%}")
            print(f"  키워드 포함률 (답변): {aq.get('avg_answer_keyword_hit_rate', 0):.1%}")
            print(f"  구조화 답변 비율: {aq.get('structure_rate', 0):.1%}")
        else:
            print("  답변 품질 정보 없음")

        print("\n[ 발표용 예시 답변 (Q01) ]")
        if metrics.query_results:
            q1 = metrics.query_results[0]
            print(f"  쿼리: {q1['query']}")
            print(f"  답변: {q1['answer'][:300]}..." if len(q1['answer']) > 300 else f"  답변: {q1['answer']}")

        print("=" * 70)


def run_before_benchmark():
    """Before 측정 실행"""
    print("\n" + "=" * 70)
    print("🔄 Before RAG 벤치마크 (현재 시스템)")
    print("=" * 70)

    benchmark = RAGBenchmark(config_name="before_chroma_hybrid_rag")
    benchmark.setup_current_system()

    queries_path = BASE_DIR / "data" / "benchmark" / "test_queries.json"
    metrics = benchmark.run_benchmark(str(queries_path))

    output_path = BASE_DIR / "scripts" / "rag_benchmark" / "results" / f"before_rag_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    benchmark.save_results(metrics, str(output_path))
    benchmark.print_summary(metrics)

    return metrics, str(output_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG 벤치마크")
    parser.add_argument("--mode", choices=["before", "after"], default="before",
                       help="벤치마크 모드")

    args = parser.parse_args()

    if args.mode == "before":
        run_before_benchmark()
    elif args.mode == "after":
        print("After 모드는 청킹/임베딩 개선 후 실행하세요.")
