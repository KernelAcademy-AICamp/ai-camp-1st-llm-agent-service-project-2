#!/usr/bin/env python3
"""
3가지 청킹 전략 벤치마크 비교

A. FixedChunking (500자 고정) - ChromaDB 시절 전략
B. OriginalPrecedentChunking (600자, min=30) - 현재 법률특화 전략
C. ImprovedPrecedentChunking (1000자, min=300) - 개선된 법률특화 전략

동일 조건:
- VectorDB: Qdrant (실제 저장은 안함, 메모리에서 검색)
- 임베딩: snowflake-arctic-embed-l-v2.0-ko (1024d)
"""

import sys
import json
import random
import re
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import numpy as np
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "libs" / "rag_core"))

from dotenv import load_dotenv
load_dotenv()


# ============================================================
# A. FixedChunking - ChromaDB 시절 500자 고정 청킹
# ============================================================

class FixedChunking:
    """ChromaDB 시절: 500자 고정 크기 청킹 (섹션 구분 없음)"""

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

            if len(chunk_text) > 50:  # 최소 길이
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        **metadata,
                        'chunk_id': chunk_id,
                        'section': 'fixed',  # 섹션 구분 없음
                        'chunking_strategy': 'fixed_500'
                    }
                })
                chunk_id += 1

            start = end - self.overlap

        return chunks


# ============================================================
# B. OriginalPrecedentChunking - 현재 법률특화 (min=30)
# ============================================================

class OriginalPrecedentChunking:
    """현재 전략: 법률특화 청킹 (chunk_size=600, min=30)"""

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

        return self._chunk_sections(sections, metadata)

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

            if len(content) < self.min_chunk_size:
                continue

            if len(content) <= self.chunk_size:
                chunks.append({
                    'content': content,
                    'metadata': {
                        **metadata,
                        'chunk_id': chunk_id,
                        'section': section_type,
                        'chunking_strategy': 'original_precedent'
                    }
                })
                chunk_id += 1
            else:
                # 큰 섹션 분할
                start = 0
                while start < len(content):
                    end = start + self.chunk_size
                    chunk_text = content[start:end].strip()

                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append({
                            'content': chunk_text,
                            'metadata': {
                                **metadata,
                                'chunk_id': chunk_id,
                                'section': section_type,
                                'chunking_strategy': 'original_precedent'
                            }
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
            chunk_text = text[start:end].strip()

            if len(chunk_text) >= self.min_chunk_size:
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        **metadata,
                        'chunk_id': chunk_id,
                        'section': 'other',
                        'chunking_strategy': 'original_precedent'
                    }
                })
                chunk_id += 1

            start = end - self.overlap

        return chunks


# ============================================================
# C. ImprovedPrecedentChunking - 개선된 법률특화 (min=300)
# ============================================================

class ImprovedPrecedentChunking:
    """개선된 전략: 법률특화 청킹 (chunk_size=1000, min=300, merge_case_info)"""

    SECTION_PATTERNS = {
        'summary': r'【?판시사항】?|【?판결요지】?|【?결정요지】?',
        'judgment': r'【?주\s*문】?|주\s+문',
        'reasoning': r'【?이\s*유】?|이\s+유',
        'reference': r'【?참조조문】?|【?참조판례】?|【?참조결정】?',
        'case_info': r'사\s*건|피고인|원고|피고|청\s*구\s*인|신\s*청\s*인',
        'decision': r'【?결\s*정】?|결\s+정',
    }

    SECTION_IMPORTANCE = {
        'summary': 'high',
        'reasoning': 'high',
        'judgment': 'medium',
        'reference': 'medium',
        'decision': 'medium',
        'case_info': 'low',
        'other': 'low',
    }

    def __init__(self, chunk_size: int = 1000, min_chunk_size: int = 300,
                 max_chunk_size: int = 1500, overlap: int = 100,
                 merge_case_info: bool = True):
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
        """연속된 case_info 섹션을 하나로 병합"""
        merged = []
        case_info_buffer = []

        for section in sections:
            if section['type'] == 'case_info':
                case_info_buffer.append(section['content'])
            else:
                if case_info_buffer:
                    merged.append({
                        'type': 'case_info',
                        'content': '\n'.join(case_info_buffer)
                    })
                    case_info_buffer = []
                merged.append(section)

        if case_info_buffer:
            merged.append({
                'type': 'case_info',
                'content': '\n'.join(case_info_buffer)
            })

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
                    'metadata': {
                        **metadata,
                        'chunk_id': chunk_id,
                        'section': section_type,
                        'importance': importance,
                        'chunking_strategy': 'improved_precedent'
                    }
                })
                chunk_id += 1
            else:
                # 큰 섹션은 문단 단위로 분할
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
                                'metadata': {
                                    **metadata,
                                    'chunk_id': chunk_id,
                                    'section': section_type,
                                    'importance': importance,
                                    'chunking_strategy': 'improved_precedent'
                                }
                            })
                            chunk_id += 1
                        current_chunk = para

                if current_chunk:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'metadata': {
                            **metadata,
                            'chunk_id': chunk_id,
                            'section': section_type,
                            'importance': importance,
                            'chunking_strategy': 'improved_precedent'
                        }
                    })
                    chunk_id += 1

        return chunks

    def _merge_small_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """최소 크기 미달 청크를 인접 청크와 병합"""
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
            chunk_text = text[start:end].strip()

            if len(chunk_text) >= self.min_chunk_size:
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        **metadata,
                        'chunk_id': chunk_id,
                        'section': 'other',
                        'importance': 'medium',
                        'chunking_strategy': 'improved_sliding_window'
                    }
                })
                chunk_id += 1

            start = end - self.overlap

        return chunks


# ============================================================
# 문서 로딩
# ============================================================

def load_documents(data_dir: Path, sample_size: int = 50) -> List[Dict]:
    """판결문/결정례 샘플 로딩"""
    documents = []

    for doc_type in ["TS_판결문", "TS_결정례"]:
        type_dir = data_dir / doc_type
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

                sections = {}
                for row in rows:
                    section = row.get('구분', 'unknown')
                    content = row.get('내용', '')
                    if section not in sections:
                        sections[section] = []
                    sections[section].append(content)

                full_text = "\n".join([
                    f"[{sec}]\n" + "\n".join(contents)
                    for sec, contents in sections.items()
                ])

                if len(full_text) > 200:
                    documents.append({
                        'doc_id': rows[0].get('판례일련번호', file_path.stem),
                        'doc_type': doc_type.replace('TS_', ''),
                        'content': full_text,
                        'sections': list(sections.keys())
                    })
            except:
                continue

    return documents


# ============================================================
# 벤치마크 실행
# ============================================================

def run_three_way_benchmark(documents: List[Dict], queries: List[str]) -> Dict:
    """3가지 청킹 전략 비교 벤치마크"""

    print("\n" + "="*70)
    print(" 3가지 청킹 전략 비교 벤치마크")
    print("="*70)
    print(f" 문서 수: {len(documents)}")
    print(f" 쿼리 수: {len(queries)}")
    print("="*70)

    # 3가지 청킹 전략
    chunkers = {
        'A_Fixed500': FixedChunking(chunk_size=500, overlap=50),
        'B_Original': OriginalPrecedentChunking(chunk_size=600, min_chunk_size=30, overlap=100),
        'C_Improved': ImprovedPrecedentChunking(chunk_size=1000, min_chunk_size=300,
                                                  max_chunk_size=1500, merge_case_info=True)
    }

    # 청킹 실행
    print("\n[1] 청킹 중...")
    all_chunks = {name: [] for name in chunkers}

    for doc in tqdm(documents, desc="청킹"):
        metadata = {'doc_id': doc['doc_id'], 'doc_type': doc['doc_type']}

        for name, chunker in chunkers.items():
            chunks = chunker.chunk(doc['content'], metadata)
            all_chunks[name].extend(chunks)

    # 청킹 통계
    print(f"\n[청킹 통계]")
    for name, chunks in all_chunks.items():
        lengths = [len(c['content']) for c in chunks]
        print(f"  {name}: {len(chunks):,} chunks, avg {np.mean(lengths):.0f}자")

    # 섹션 분포
    print(f"\n[섹션 분포]")
    for name, chunks in all_chunks.items():
        sections = {}
        for c in chunks:
            sec = c['metadata'].get('section', 'unknown')
            sections[sec] = sections.get(sec, 0) + 1
        print(f"  {name}: {dict(sorted(sections.items(), key=lambda x: -x[1]))}")

    # 임베딩 생성
    print("\n[2] 임베딩 생성 중...")

    from embeddings.remote_embedder import RemoteEmbedder
    embedder = RemoteEmbedder(batch_size=32, timeout=300)

    all_embeddings = {}

    for name, chunks in all_chunks.items():
        texts = [c['content'] for c in chunks]
        print(f"  {name} 임베딩 ({len(texts)} chunks)...")

        embeddings = []
        for i in tqdm(range(0, len(texts), 32), desc=f"  {name}"):
            batch = texts[i:i+32]
            embs = embedder.embed_documents(batch)
            embeddings.extend(embs)

        all_embeddings[name] = np.array(embeddings)

    # 검색 테스트
    print("\n[3] 검색 테스트...")

    results = {name: {'hits': [], 'scores': []} for name in chunkers}

    for query in tqdm(queries, desc="쿼리 검색"):
        query_emb = np.array(embedder.embed_query(query))

        for name in chunkers:
            embeddings = all_embeddings[name]
            chunks = all_chunks[name]
            texts = [c['content'] for c in chunks]

            # 코사인 유사도 계산
            sims = np.dot(embeddings, query_emb) / (
                np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_emb) + 1e-8
            )
            top_idx = np.argsort(sims)[-5:][::-1]
            top_scores = sims[top_idx]

            # 결과 저장
            results[name]['scores'].append(float(top_scores[0]))

            section = chunks[top_idx[0]]['metadata'].get('section', 'unknown')
            results[name]['hits'].append({
                'query': query,
                'section': section,
                'score': float(top_scores[0]),
                'text_preview': texts[top_idx[0]][:100]
            })

    # 결과 분석
    print("\n" + "="*70)
    print(" 벤치마크 결과")
    print("="*70)

    print(f"\n[평균 유사도 점수]")
    for name in chunkers:
        avg_score = np.mean(results[name]['scores'])
        print(f"  {name}: {avg_score:.4f}")

    # 기준점(A_Fixed500) 대비 차이
    base_score = np.mean(results['A_Fixed500']['scores'])
    print(f"\n[A_Fixed500 대비 차이]")
    for name in ['B_Original', 'C_Improved']:
        diff = np.mean(results[name]['scores']) - base_score
        print(f"  {name}: {diff*100:+.2f}%")

    # 섹션별 히트 분석
    print(f"\n[Top-1 히트 섹션 분포]")
    for name in chunkers:
        hit_sections = {}
        for hit in results[name]['hits']:
            sec = hit['section']
            hit_sections[sec] = hit_sections.get(sec, 0) + 1
        print(f"  {name}: {dict(sorted(hit_sections.items(), key=lambda x: -x[1]))}")

    # 중요 섹션 히트율
    print(f"\n[중요 섹션(reasoning/summary) 히트율]")
    for name in chunkers:
        important = sum(1 for h in results[name]['hits'] if h['section'] in ['reasoning', 'summary'])
        print(f"  {name}: {important}/{len(queries)} ({important/len(queries)*100:.1f}%)")

    print("="*70)

    return {
        'timestamp': datetime.now().isoformat(),
        'documents': len(documents),
        'queries': queries,
        'chunking_stats': {
            name: {
                'chunk_count': len(all_chunks[name]),
                'avg_length': float(np.mean([len(c['content']) for c in all_chunks[name]]))
            }
            for name in chunkers
        },
        'search_results': {
            name: {
                'avg_score': float(np.mean(results[name]['scores'])),
                'important_hit_rate': sum(1 for h in results[name]['hits']
                                          if h['section'] in ['reasoning', 'summary']) / len(queries)
            }
            for name in chunkers
        }
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="3가지 청킹 전략 비교")
    parser.add_argument("--sample-size", type=int, default=50, help="문서 타입별 샘플 수")
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    # 데이터 경로
    data_dir = PROJECT_ROOT / "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터" / \
               "3.개방데이터" / "1.데이터" / "Training" / "01.원천데이터"

    # 문서 로딩
    print("문서 로드 중...")
    documents = load_documents(data_dir, args.sample_size)
    print(f"로드된 문서: {len(documents)}")

    if not documents:
        print("문서를 찾을 수 없습니다!")
        return

    # 테스트 쿼리
    queries = ['형법', '처벌', '양형', '사기', '집행유예',
               '상해', '폭행', '도로교통법', '음주운전', '절도']

    print(f"테스트 쿼리: {queries}")

    # 벤치마크 실행
    results = run_three_way_benchmark(documents, queries)

    # 결과 저장
    output_dir = PROJECT_ROOT / "scripts" / "rag_benchmark" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"three_way_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {output_path}")


if __name__ == "__main__":
    main()
