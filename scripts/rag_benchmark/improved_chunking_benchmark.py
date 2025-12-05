#!/usr/bin/env python3
"""
개선된 청킹 전략 벤치마크

기존 PrecedentAutoChunking vs 개선된 ImprovedPrecedentChunking 비교

테스트:
1. 동일한 문서에 두 가지 청킹 적용
2. 동일한 임베딩 모델 (snowflake-arctic) 사용
3. 동일한 쿼리로 검색 성능 비교
"""

import sys
import json
import random
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import numpy as np
from tqdm import tqdm

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "libs" / "rag_core"))

from dotenv import load_dotenv
load_dotenv()

import re


# ============================================================
# 청킹 전략들
# ============================================================

class OriginalPrecedentChunking:
    """기존 PrecedentAutoChunking (chunk_size=600)"""

    SECTION_PATTERNS = {
        'summary': r'【?판시사항】?|【?판결요지】?|【?결정요지】?',
        'judgment': r'【?주\s*문】?|주\s+문',
        'reasoning': r'【?이\s*유】?|이\s+유',
        'reference': r'【?참조조문】?|【?참조판례】?|【?참조결정】?',
        'case_info': r'사\s*건|피고인|원고|피고|청\s*구\s*인|신\s*청\s*인',
        'decision': r'【?결\s*정】?|결\s+정',
    }

    def __init__(self, chunk_size: int = 600, min_chunk_size: int = 30, overlap: int = 100):
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: Dict = None) -> List[Dict]:
        if metadata is None:
            metadata = {}

        sections = self._detect_sections(text)

        if not sections:
            return self._sliding_window_chunk(text, metadata)

        chunks = self._chunk_sections(sections, metadata)
        return chunks

    def _detect_sections(self, text: str) -> List[Dict]:
        sections = []
        lines = text.split('\n')
        current_content = []
        current_type = 'other'

        for line in lines:
            line_stripped = line.strip()
            detected_type = None

            for section_type, pattern in self.SECTION_PATTERNS.items():
                if re.search(pattern, line_stripped):
                    detected_type = section_type
                    break

            if detected_type:
                if current_content:
                    sections.append({'type': current_type, 'content': '\n'.join(current_content)})
                current_type = detected_type
                current_content = [line]
            else:
                current_content.append(line)

        if current_content:
            sections.append({'type': current_type, 'content': '\n'.join(current_content)})

        return sections if len(sections) > 1 else []

    def _chunk_sections(self, sections: List[Dict], metadata: Dict) -> List[Dict]:
        chunks = []
        chunk_id = 0

        for section in sections:
            content = section['content'].strip()
            section_type = section['type']

            if not content or len(content) < self.min_chunk_size:
                continue

            if len(content) <= self.chunk_size:
                chunks.append({
                    'content': content,
                    'metadata': {**metadata, 'chunk_id': chunk_id, 'section': section_type,
                                'chunking_strategy': 'original_precedent'}
                })
                chunk_id += 1
            else:
                # Split long sections
                start = 0
                while start < len(content):
                    end = start + self.chunk_size
                    chunk_text = content[start:end]
                    if len(chunk_text.strip()) >= self.min_chunk_size:
                        chunks.append({
                            'content': chunk_text.strip(),
                            'metadata': {**metadata, 'chunk_id': chunk_id, 'section': section_type,
                                        'chunking_strategy': 'original_precedent'}
                        })
                        chunk_id += 1
                    start = end - self.overlap

        return chunks

    def _sliding_window_chunk(self, text: str, metadata: Dict) -> List[Dict]:
        chunks = []
        start = 0
        chunk_id = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            if len(chunk_text.strip()) >= self.min_chunk_size:
                chunks.append({
                    'content': chunk_text.strip(),
                    'metadata': {**metadata, 'chunk_id': chunk_id, 'section': 'other',
                                'chunking_strategy': 'original_sliding'}
                })
                chunk_id += 1

            start = end - self.overlap

        return chunks


class ImprovedPrecedentChunking:
    """개선된 청킹 (chunk_size=1000, min=300, merge_case_info)"""

    SECTION_PATTERNS = {
        'summary': r'【?판시사항】?|【?판결요지】?|【?결정요지】?',
        'judgment': r'【?주\s*문】?|주\s+문',
        'reasoning': r'【?이\s*유】?|이\s+유',
        'reference': r'【?참조조문】?|【?참조판례】?|【?참조결정】?',
        'case_info': r'사\s*건|피고인|원고|피고|청\s*구\s*인|신\s*청\s*인',
        'decision': r'【?결\s*정】?|결\s+정',
    }

    SECTION_IMPORTANCE = {
        'summary': 'high', 'reasoning': 'high',
        'judgment': 'medium', 'reference': 'medium', 'decision': 'medium',
        'case_info': 'low', 'other': 'low',
    }

    def __init__(self, chunk_size: int = 1000, min_chunk_size: int = 300,
                 max_chunk_size: int = 1500, overlap: int = 100, merge_case_info: bool = True):
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.merge_case_info = merge_case_info

    def chunk(self, text: str, metadata: Dict = None) -> List[Dict]:
        if metadata is None:
            metadata = {}

        sections = self._detect_sections(text)

        if not sections:
            return self._sliding_window_chunk(text, metadata)

        if self.merge_case_info:
            sections = self._merge_case_info_sections(sections)

        chunks = self._chunk_sections(sections, metadata)
        chunks = self._merge_small_chunks(chunks)

        return chunks

    def _detect_sections(self, text: str) -> List[Dict]:
        sections = []
        lines = text.split('\n')
        current_content = []
        current_type = 'other'

        for line in lines:
            line_stripped = line.strip()
            detected_type = None

            for section_type, pattern in self.SECTION_PATTERNS.items():
                if re.search(pattern, line_stripped):
                    detected_type = section_type
                    break

            if detected_type:
                if current_content:
                    sections.append({'type': current_type, 'content': '\n'.join(current_content)})
                current_type = detected_type
                current_content = [line]
            else:
                current_content.append(line)

        if current_content:
            sections.append({'type': current_type, 'content': '\n'.join(current_content)})

        return sections if len(sections) > 1 else []

    def _merge_case_info_sections(self, sections: List[Dict]) -> List[Dict]:
        merged = []
        case_info_buffer = []

        for section in sections:
            if section['type'] == 'case_info':
                case_info_buffer.append(section['content'])
            else:
                if case_info_buffer:
                    merged.append({'type': 'case_info', 'content': '\n'.join(case_info_buffer)})
                    case_info_buffer = []
                merged.append(section)

        if case_info_buffer:
            merged.append({'type': 'case_info', 'content': '\n'.join(case_info_buffer)})

        return merged

    def _chunk_sections(self, sections: List[Dict], metadata: Dict) -> List[Dict]:
        chunks = []
        chunk_id = 0

        for section in sections:
            content = section['content'].strip()
            section_type = section['type']
            importance = self.SECTION_IMPORTANCE.get(section_type, 'low')

            if not content:
                continue

            effective_max = self.max_chunk_size if importance == 'high' else self.chunk_size

            if len(content) <= effective_max:
                chunks.append({
                    'content': content,
                    'metadata': {**metadata, 'chunk_id': chunk_id, 'section': section_type,
                                'importance': importance, 'chunking_strategy': 'improved_precedent'}
                })
                chunk_id += 1
            else:
                # Split by paragraphs
                paragraphs = re.split(r'\n\s*\n', content)
                current_chunk = ""

                for para in paragraphs:
                    para = para.strip()
                    if not para:
                        continue

                    if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                        current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
                    else:
                        if current_chunk:
                            chunks.append({
                                'content': current_chunk.strip(),
                                'metadata': {**metadata, 'chunk_id': chunk_id, 'section': section_type,
                                            'importance': importance, 'chunking_strategy': 'improved_precedent'}
                            })
                            chunk_id += 1
                        current_chunk = para

                if current_chunk:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'metadata': {**metadata, 'chunk_id': chunk_id, 'section': section_type,
                                    'importance': importance, 'chunking_strategy': 'improved_precedent'}
                    })
                    chunk_id += 1

        return chunks

    def _merge_small_chunks(self, chunks: List[Dict]) -> List[Dict]:
        if not chunks:
            return chunks

        merged = []
        buffer = None

        for chunk in chunks:
            content_len = len(chunk['content'])

            if content_len >= self.min_chunk_size:
                if buffer:
                    if (buffer['metadata'].get('section') == chunk['metadata'].get('section') and
                        len(buffer['content']) + content_len + 2 <= self.max_chunk_size):
                        chunk['content'] = f"{buffer['content']}\n\n{chunk['content']}"
                    else:
                        merged.append(buffer)
                    buffer = None
                merged.append(chunk)
            else:
                if buffer:
                    if (buffer['metadata'].get('section') == chunk['metadata'].get('section') and
                        len(buffer['content']) + content_len + 2 <= self.max_chunk_size):
                        buffer['content'] = f"{buffer['content']}\n\n{chunk['content']}"
                    else:
                        merged.append(buffer)
                        buffer = chunk
                else:
                    buffer = chunk

        if buffer:
            merged.append(buffer)

        return merged

    def _sliding_window_chunk(self, text: str, metadata: Dict) -> List[Dict]:
        chunks = []
        start = 0
        chunk_id = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            if len(chunk_text.strip()) >= self.min_chunk_size:
                chunks.append({
                    'content': chunk_text.strip(),
                    'metadata': {**metadata, 'chunk_id': chunk_id, 'section': 'other',
                                'importance': 'medium', 'chunking_strategy': 'improved_sliding'}
                })
                chunk_id += 1

            start = end - self.overlap

        return chunks


# ============================================================
# 벤치마크 로직
# ============================================================

def load_sample_documents(data_dir: Path, doc_types: List[str], sample_size: int = 100) -> List[Dict]:
    """샘플 문서 로드"""
    import csv

    documents = []

    for doc_type in doc_types:
        type_dir = data_dir / f"TS_{doc_type}"
        if not type_dir.exists():
            continue

        files = list(type_dir.glob("*.csv"))
        sample_files = random.sample(files, min(sample_size, len(files)))

        for file_path in sample_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)

                if not rows:
                    continue

                doc_id = rows[0].get('판례일련번호', file_path.stem)

                sections = {}
                for row in rows:
                    section = row.get('구분', 'unknown')
                    content = row.get('내용', '')
                    if section not in sections:
                        sections[section] = []
                    sections[section].append(content)

                full_text_parts = []
                for section, contents in sections.items():
                    if contents:
                        full_text_parts.append(f"[{section}]")
                        full_text_parts.extend(contents)

                full_text = "\n".join(full_text_parts)

                if len(full_text) > 100:
                    documents.append({
                        'doc_id': str(doc_id),
                        'doc_type': doc_type,
                        'content': full_text,
                        'sections': sections
                    })
            except:
                continue

    return documents


def extract_keywords_from_docs(documents: List[Dict]) -> List[str]:
    """문서에서 검색 키워드 추출"""
    keywords = []

    keyword_patterns = [
        r'음주운전', r'절도', r'사기', r'폭행', r'상해',
        r'횡령', r'배임', r'강도', r'살인', r'마약',
        r'도로교통법', r'형법', r'특정경제범죄', r'정당방위',
        r'혈중알코올', r'처벌', r'양형', r'집행유예'
    ]

    for doc in documents:
        content = doc['content']
        for pattern in keyword_patterns:
            if re.search(pattern, content):
                keywords.append(pattern)

    # 빈도 기반으로 상위 키워드 선택
    from collections import Counter
    keyword_counts = Counter(keywords)
    return [kw for kw, _ in keyword_counts.most_common(10)]


def run_benchmark(documents: List[Dict], queries: List[str]) -> Dict:
    """벤치마크 실행"""

    print("\n" + "="*70)
    print(" 개선된 청킹 전략 벤치마크")
    print("="*70)
    print(f" 문서 수: {len(documents)}")
    print(f" 쿼리 수: {len(queries)}")
    print("="*70)

    # 두 가지 청킹 전략
    original_chunker = OriginalPrecedentChunking(chunk_size=600, min_chunk_size=30, overlap=100)
    improved_chunker = ImprovedPrecedentChunking(chunk_size=1000, min_chunk_size=300,
                                                   max_chunk_size=1500, merge_case_info=True)

    # 청킹 실행
    print("\n[1] 청킹 중...")

    original_chunks = []
    improved_chunks = []

    for doc in tqdm(documents, desc="청킹"):
        metadata = {'doc_id': doc['doc_id'], 'doc_type': doc['doc_type']}

        orig = original_chunker.chunk(doc['content'], metadata)
        impr = improved_chunker.chunk(doc['content'], metadata)

        original_chunks.extend(orig)
        improved_chunks.extend(impr)

    # 청킹 통계
    orig_lengths = [len(c['content']) for c in original_chunks]
    impr_lengths = [len(c['content']) for c in improved_chunks]

    print(f"\n[청킹 통계]")
    print(f"  Original: {len(original_chunks):,} chunks, avg {np.mean(orig_lengths):.0f}자")
    print(f"  Improved: {len(improved_chunks):,} chunks, avg {np.mean(impr_lengths):.0f}자")
    print(f"  청크 수 감소: {(1 - len(improved_chunks)/len(original_chunks))*100:.1f}%")

    # 섹션 분포
    orig_sections = {}
    impr_sections = {}
    for c in original_chunks:
        sec = c['metadata'].get('section', 'unknown')
        orig_sections[sec] = orig_sections.get(sec, 0) + 1
    for c in improved_chunks:
        sec = c['metadata'].get('section', 'unknown')
        impr_sections[sec] = impr_sections.get(sec, 0) + 1

    print(f"\n[섹션 분포]")
    print(f"  Original: {orig_sections}")
    print(f"  Improved: {impr_sections}")

    # 임베딩 생성
    print("\n[2] 임베딩 생성 중...")

    from embeddings.remote_embedder import RemoteEmbedder
    embedder = RemoteEmbedder(batch_size=32, timeout=300)

    # 청크 텍스트 추출
    orig_texts = [c['content'] for c in original_chunks]
    impr_texts = [c['content'] for c in improved_chunks]

    print(f"  Original 임베딩 ({len(orig_texts)} chunks)...")
    orig_embeddings = []
    for i in tqdm(range(0, len(orig_texts), 32), desc="Original"):
        batch = orig_texts[i:i+32]
        embs = embedder.embed_documents(batch)
        orig_embeddings.extend(embs)
    orig_embeddings = np.array(orig_embeddings)

    print(f"  Improved 임베딩 ({len(impr_texts)} chunks)...")
    impr_embeddings = []
    for i in tqdm(range(0, len(impr_texts), 32), desc="Improved"):
        batch = impr_texts[i:i+32]
        embs = embedder.embed_documents(batch)
        impr_embeddings.extend(embs)
    impr_embeddings = np.array(impr_embeddings)

    # 검색 테스트
    print("\n[3] 검색 테스트...")

    results = {
        'original': {'hits': [], 'scores': []},
        'improved': {'hits': [], 'scores': []}
    }

    for query in tqdm(queries, desc="쿼리 검색"):
        query_emb = np.array(embedder.embed_query(query))

        # Original 검색
        orig_sims = np.dot(orig_embeddings, query_emb) / (
            np.linalg.norm(orig_embeddings, axis=1) * np.linalg.norm(query_emb)
        )
        orig_top_idx = np.argsort(orig_sims)[-5:][::-1]
        orig_top_scores = orig_sims[orig_top_idx]

        # Improved 검색
        impr_sims = np.dot(impr_embeddings, query_emb) / (
            np.linalg.norm(impr_embeddings, axis=1) * np.linalg.norm(query_emb)
        )
        impr_top_idx = np.argsort(impr_sims)[-5:][::-1]
        impr_top_scores = impr_sims[impr_top_idx]

        # 결과 저장
        results['original']['scores'].append(orig_top_scores[0])
        results['improved']['scores'].append(impr_top_scores[0])

        # 섹션 분석 (top-1 결과의 섹션)
        orig_section = original_chunks[orig_top_idx[0]]['metadata'].get('section', 'unknown')
        impr_section = improved_chunks[impr_top_idx[0]]['metadata'].get('section', 'unknown')

        results['original']['hits'].append({
            'query': query,
            'section': orig_section,
            'score': float(orig_top_scores[0]),
            'text_preview': orig_texts[orig_top_idx[0]][:100]
        })
        results['improved']['hits'].append({
            'query': query,
            'section': impr_section,
            'score': float(impr_top_scores[0]),
            'text_preview': impr_texts[impr_top_idx[0]][:100]
        })

    # 결과 분석
    print("\n" + "="*70)
    print(" 벤치마크 결과")
    print("="*70)

    orig_avg_score = np.mean(results['original']['scores'])
    impr_avg_score = np.mean(results['improved']['scores'])

    print(f"\n[평균 유사도 점수]")
    print(f"  Original: {orig_avg_score:.4f}")
    print(f"  Improved: {impr_avg_score:.4f}")
    print(f"  차이: {(impr_avg_score - orig_avg_score)*100:.2f}%")

    # 섹션별 히트 분석
    print(f"\n[Top-1 히트 섹션 분포]")
    orig_hit_sections = {}
    impr_hit_sections = {}
    for hit in results['original']['hits']:
        sec = hit['section']
        orig_hit_sections[sec] = orig_hit_sections.get(sec, 0) + 1
    for hit in results['improved']['hits']:
        sec = hit['section']
        impr_hit_sections[sec] = impr_hit_sections.get(sec, 0) + 1

    print(f"  Original: {orig_hit_sections}")
    print(f"  Improved: {impr_hit_sections}")

    # 중요 섹션 (reasoning, summary) 히트율
    orig_important = sum(1 for h in results['original']['hits'] if h['section'] in ['reasoning', 'summary'])
    impr_important = sum(1 for h in results['improved']['hits'] if h['section'] in ['reasoning', 'summary'])

    print(f"\n[중요 섹션(reasoning/summary) 히트율]")
    print(f"  Original: {orig_important}/{len(queries)} ({orig_important/len(queries)*100:.1f}%)")
    print(f"  Improved: {impr_important}/{len(queries)} ({impr_important/len(queries)*100:.1f}%)")

    # 결과 반환
    summary = {
        'timestamp': datetime.now().isoformat(),
        'documents': len(documents),
        'queries': len(queries),
        'chunking': {
            'original': {
                'chunk_count': len(original_chunks),
                'avg_length': float(np.mean(orig_lengths)),
                'section_distribution': orig_sections
            },
            'improved': {
                'chunk_count': len(improved_chunks),
                'avg_length': float(np.mean(impr_lengths)),
                'section_distribution': impr_sections
            },
            'reduction': (1 - len(improved_chunks)/len(original_chunks)) * 100
        },
        'search': {
            'original': {
                'avg_score': float(orig_avg_score),
                'hit_sections': orig_hit_sections,
                'important_hit_rate': orig_important / len(queries)
            },
            'improved': {
                'avg_score': float(impr_avg_score),
                'hit_sections': impr_hit_sections,
                'important_hit_rate': impr_important / len(queries)
            }
        },
        'detailed_results': results
    }

    print("="*70)

    return summary


def main():
    import argparse

    parser = argparse.ArgumentParser(description="개선된 청킹 전략 벤치마크")
    parser.add_argument("--sample-size", type=int, default=100, help="타입별 샘플 문서 수")
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드")

    args = parser.parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)

    # 데이터 경로
    data_dir = PROJECT_ROOT / "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터" / "3.개방데이터" / "1.데이터" / "Training" / "01.원천데이터"

    # 문서 로드
    print("문서 로드 중...")
    documents = load_sample_documents(data_dir, ["판결문", "결정례"], args.sample_size)
    print(f"로드된 문서: {len(documents)}")

    # 키워드 추출
    keywords = extract_keywords_from_docs(documents)
    print(f"테스트 쿼리: {keywords}")

    # 벤치마크 실행
    results = run_benchmark(documents, keywords)

    # 결과 저장
    output_path = PROJECT_ROOT / "scripts" / "rag_benchmark" / "results" / f"improved_chunking_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {output_path}")


if __name__ == "__main__":
    main()
