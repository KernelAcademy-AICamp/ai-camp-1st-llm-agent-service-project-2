#!/usr/bin/env python3
"""
선택적 재청킹 스크립트

TS_판결문과 TS_결정례만 개선된 청킹 전략으로 재처리하고
Qdrant VectorDB를 업데이트합니다.

기존 데이터:
- TS_판결문: 40,796 docs → 497,883 chunks (precedent_auto)
- TS_결정례: 7,409 docs → 66,993 chunks (precedent_auto)

개선사항:
- chunk_size: 600 → 1000
- min_chunk_size: 30 → 300 (작은 청크 병합)
- max_chunk_size: 1500 (중요 섹션 보존)
- case_info 섹션 병합

사용법:
    # 1. 드라이런 (실제 변경 없이 미리보기)
    python scripts/selective_rechunk.py --dry-run

    # 2. 실제 실행 (판결문과 결정례만)
    python scripts/selective_rechunk.py --types 판결문 결정례

    # 3. 테스트 (소량)
    python scripts/selective_rechunk.py --max-per-type 100 --dry-run
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from tqdm import tqdm

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "libs" / "rag_core"))

from dotenv import load_dotenv
load_dotenv()

import numpy as np
from loguru import logger


# ============================================================
# 개선된 청킹 클래스 (improved_chunking.py에서 복사)
# ============================================================

import re
from dataclasses import dataclass


class ImprovedPrecedentChunking:
    """
    개선된 판결문/결정례 청킹 전략

    변경사항:
    1. chunk_size: 600 → 1000 (더 많은 컨텍스트)
    2. min_chunk_size: 30 → 300 (너무 작은 청크 방지)
    3. case_info 병합: 연속된 case_info 섹션을 하나로
    4. 중요도 태깅: reasoning/summary는 high, case_info는 low
    """

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

    def __init__(
        self,
        chunk_size: int = 800,
        min_chunk_size: int = 200,
        max_chunk_size: int = 1000,  # 모델 max_length 512토큰 고려
        overlap: int = 100,
        merge_case_info: bool = True
    ):
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.merge_case_info = merge_case_info

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """텍스트를 청크로 분할"""
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

    def _detect_sections(self, text: str) -> List[Dict[str, Any]]:
        """섹션 자동 감지"""
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
                    sections.append({
                        'type': current_type,
                        'content': '\n'.join(current_content)
                    })

                current_type = detected_type
                current_content = [line]
            else:
                current_content.append(line)

        if current_content:
            sections.append({
                'type': current_type,
                'content': '\n'.join(current_content)
            })

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
        """섹션별 청킹 수행"""
        chunks = []
        chunk_id = 0

        for section in sections:
            section_content = section['content'].strip()
            section_type = section['type']
            importance = self.SECTION_IMPORTANCE.get(section_type, 'low')

            if not section_content:
                continue

            effective_max = self.max_chunk_size if importance == 'high' else self.chunk_size

            if len(section_content) <= effective_max:
                chunks.append({
                    'content': section_content,
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
                sub_chunks = self._split_long_section(
                    section_content, section_type, importance, metadata
                )
                for sub in sub_chunks:
                    sub['metadata']['chunk_id'] = chunk_id
                    chunks.append(sub)
                    chunk_id += 1

        return chunks

    def _split_long_section(
        self, content: str, section_type: str, importance: str, metadata: Dict
    ) -> List[Dict]:
        """긴 섹션을 문단 단위로 분할"""
        chunks = []
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
                            'section': section_type,
                            'importance': importance,
                            'chunking_strategy': 'improved_precedent'
                        }
                    })

                if len(para) > self.chunk_size:
                    sentence_chunks = self._split_by_sentences(
                        para, section_type, importance, metadata
                    )
                    chunks.extend(sentence_chunks)
                    current_chunk = ""
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append({
                'content': current_chunk.strip(),
                'metadata': {
                    **metadata,
                    'section': section_type,
                    'importance': importance,
                    'chunking_strategy': 'improved_precedent'
                }
            })

        return chunks

    def _split_by_sentences(
        self, text: str, section_type: str, importance: str, metadata: Dict
    ) -> List[Dict]:
        """문장 단위로 분할"""
        chunks = []
        sentences = re.split(r'(?<=[.?!。])\s+', text)
        current_chunk = ""

        for sentence in sentences:
            # 단일 문장이 max_chunk_size 초과하면 강제 분할
            if len(sentence) > self.max_chunk_size:
                if current_chunk:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'metadata': {
                            **metadata,
                            'section': section_type,
                            'importance': importance,
                            'chunking_strategy': 'improved_precedent'
                        }
                    })
                    current_chunk = ""
                # 긴 문장을 max_chunk_size 단위로 강제 분할
                for i in range(0, len(sentence), self.max_chunk_size - self.overlap):
                    chunk_text = sentence[i:i + self.max_chunk_size]
                    if chunk_text.strip():
                        chunks.append({
                            'content': chunk_text.strip(),
                            'metadata': {
                                **metadata,
                                'section': section_type,
                                'importance': importance,
                                'chunking_strategy': 'improved_precedent_force_split'
                            }
                        })
            elif len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                current_chunk = f"{current_chunk} {sentence}" if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'metadata': {
                            **metadata,
                            'section': section_type,
                            'importance': importance,
                            'chunking_strategy': 'improved_precedent'
                        }
                    })
                current_chunk = sentence

        if current_chunk:
            chunks.append({
                'content': current_chunk.strip(),
                'metadata': {
                    **metadata,
                    'section': section_type,
                    'importance': importance,
                    'chunking_strategy': 'improved_precedent'
                }
            })

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
            # 마지막 buffer도 min_chunk_size 미만이면 이전 청크에 병합 시도
            if len(buffer['content']) < self.min_chunk_size and merged:
                last_chunk = merged[-1]
                if len(last_chunk['content']) + len(buffer['content']) + 2 <= self.max_chunk_size:
                    last_chunk['content'] = f"{last_chunk['content']}\n\n{buffer['content']}"
                else:
                    merged.append(buffer)  # 병합 불가능하면 그냥 추가
            else:
                merged.append(buffer)

        # 최종 필터: min_chunk_size 미만인 청크 제거 (너무 작은 청크는 노이즈)
        final_chunks = [c for c in merged if len(c['content']) >= 50]  # 최소 50자 보장

        return final_chunks if final_chunks else merged  # 모두 제거되면 원본 반환

    def _sliding_window_chunk(self, text: str, metadata: Dict) -> List[Dict]:
        """폴백: Sliding window 청킹"""
        chunks = []
        start = 0
        chunk_id = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            if len(chunk_text.strip()) >= self.min_chunk_size:
                chunks.append({
                    'content': chunk_text.strip(),
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
# 메인 로직
# ============================================================

def load_existing_chunks(chunks_path: Path) -> Tuple[List[Dict], List[Dict]]:
    """
    기존 청크 로드 및 분리

    Returns:
        (판결문/결정례 청크, 나머지 청크)
    """
    with open(chunks_path, 'r', encoding='utf-8') as f:
        all_chunks = json.load(f)

    precedent_chunks = []
    other_chunks = []

    for chunk in all_chunks:
        strategy = chunk.get('metadata', {}).get('chunking_strategy', '')
        source = chunk.get('metadata', {}).get('source', '')

        # precedent_auto 또는 판결문/결정례 관련 청크 분리
        if 'precedent' in strategy or '판결문' in source or '결정례' in source:
            precedent_chunks.append(chunk)
        else:
            other_chunks.append(chunk)

    logger.info(f"기존 청크 분석:")
    logger.info(f"  - 판결문/결정례: {len(precedent_chunks):,}개")
    logger.info(f"  - 기타 (유지): {len(other_chunks):,}개")

    return precedent_chunks, other_chunks


def load_raw_documents(
    data_dir: Path,
    doc_types: List[str],
    max_per_type: int = None
) -> List[Dict]:
    """원본 문서 로드"""
    import csv
    import random

    documents = []

    for doc_type in doc_types:
        type_dir = data_dir / f"TS_{doc_type}"
        if not type_dir.exists():
            logger.warning(f"디렉토리 없음: {type_dir}")
            continue

        files = list(type_dir.glob("*.csv"))
        if max_per_type and len(files) > max_per_type:
            files = random.sample(files, max_per_type)

        logger.info(f"📂 TS_{doc_type}: {len(files)}개 파일 로딩...")

        for file_path in tqdm(files, desc=f"  TS_{doc_type}"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)

                if not rows:
                    continue

                doc_id = rows[0].get('판례일련번호', file_path.stem)

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

                if len(full_text) < 100:
                    continue

                title = sections.get('판시사항', [''])[0][:100] if '판시사항' in sections else f"{doc_type}_{doc_id}"

                documents.append({
                    'doc_id': str(doc_id),
                    'doc_type': doc_type,
                    'title': title,
                    'content': full_text,
                    'metadata': {
                        'file_path': str(file_path),
                        'source': f'TS_{doc_type}',
                        'sections': list(sections.keys())
                    }
                })

            except Exception as e:
                logger.debug(f"파일 로드 실패: {file_path}: {e}")
                continue

    logger.info(f"✅ 총 {len(documents)}개 문서 로딩 완료")
    return documents


def rechunk_documents(
    documents: List[Dict],
    chunker: ImprovedPrecedentChunking
) -> List[Dict]:
    """문서들을 개선된 전략으로 재청킹"""
    all_chunks = []

    for doc in tqdm(documents, desc="재청킹"):
        # source 형식: TS_판결문 → 원천_판결문 (기존 chunks_full.json과 동일)
        raw_source = doc['metadata'].get('source', '')
        if raw_source.startswith('TS_'):
            source = raw_source.replace('TS_', '원천_')
        else:
            source = f"원천_{doc['doc_type']}"

        metadata = {
            'doc_id': doc['doc_id'],
            'doc_type': doc['doc_type'],
            'title': doc['title'],
            'source': source,
            'data_source': '원천',
            'split': 'training',
            **{k: v for k, v in doc.get('metadata', {}).items() if k not in ['source']}
        }

        chunks = chunker.chunk(doc['content'], metadata)
        all_chunks.extend(chunks)

    return all_chunks


def delete_from_qdrant(
    client,
    collection_name: str,
    filter_conditions: List[Dict],
    dry_run: bool = False
) -> int:
    """Qdrant에서 조건에 맞는 포인트 삭제"""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    # 삭제 대상 카운트
    count = 0
    for condition in filter_conditions:
        field = condition['field']
        value = condition['value']

        try:
            result = client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    should=[
                        FieldCondition(key=field, match=MatchValue(value=value))
                    ]
                ),
                limit=1,
                with_payload=False,
                with_vectors=False
            )
            # 실제 카운트는 scroll로 얻기 어려우므로 추정
        except Exception as e:
            logger.warning(f"카운트 실패: {e}")

    if dry_run:
        logger.info(f"[DRY-RUN] 삭제 예정 조건: {filter_conditions}")
        return 0

    # 실제 삭제
    for condition in filter_conditions:
        field = condition['field']
        value = condition['value']

        try:
            client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    should=[
                        FieldCondition(key=field, match=MatchValue(value=value))
                    ]
                )
            )
            logger.info(f"  삭제됨: {field}={value}")
        except Exception as e:
            logger.error(f"삭제 실패: {e}")

    return count


def embed_and_upsert(
    chunks: List[Dict],
    embedder,
    vectordb,
    batch_size: int = 72,
    dry_run: bool = False
) -> int:
    """청크 임베딩 및 VectorDB 업서트"""
    if dry_run:
        logger.info(f"[DRY-RUN] {len(chunks)}개 청크 임베딩 및 저장 예정")
        return len(chunks)

    texts = [c['content'] for c in chunks]
    metadatas = [c['metadata'] for c in chunks]

    logger.info(f"임베딩 생성 중... ({len(texts)}개)")

    # 배치 임베딩
    all_embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="임베딩"):
        batch = texts[i:i+batch_size]
        embeddings = embedder.embed_documents(batch)
        all_embeddings.extend(embeddings)

    embeddings_array = np.array(all_embeddings)
    logger.info(f"✅ 임베딩 완료: shape={embeddings_array.shape}")

    # VectorDB 저장
    vectordb.add_documents(texts, embeddings_array, metadatas)
    logger.info(f"✅ VectorDB 저장 완료: {len(texts)}개")

    return len(texts)


def main():
    parser = argparse.ArgumentParser(description="TS_판결문/결정례 선택적 재청킹")
    parser.add_argument("--types", nargs="+", default=["판결문", "결정례"],
                       help="재처리할 데이터 타입 (기본: 판결문 결정례)")
    parser.add_argument("--max-per-type", type=int, default=None,
                       help="타입별 최대 문서 수 (테스트용)")
    parser.add_argument("--dry-run", action="store_true",
                       help="실제 변경 없이 미리보기")
    parser.add_argument("--skip-delete", action="store_true",
                       help="VectorDB 삭제 스킵 (재시작 시)")
    parser.add_argument("--skip-embed", action="store_true",
                       help="임베딩 스킵 (청크 파일만 생성, GPU 서버용)")
    parser.add_argument("--chunks-output", type=str,
                       default="data/processed/chunks_improved.json",
                       help="새 청크 저장 경로")

    args = parser.parse_args()

    print("\n" + "="*70)
    print(" 🔄 선택적 재청킹 (판결문/결정례)")
    print("="*70)
    print(f"  시작: {datetime.now().isoformat()}")
    print(f"  대상: {args.types}")
    print(f"  Dry-run: {args.dry_run}")
    print("="*70 + "\n")

    # 경로 설정
    data_dir = PROJECT_ROOT / "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터" / "3.개방데이터" / "1.데이터" / "Training" / "01.원천데이터"

    # 1. 원본 문서 로드
    logger.info("\n📥 [1/4] 원본 문서 로드...")
    documents = load_raw_documents(data_dir, args.types, args.max_per_type)

    if not documents:
        logger.error("문서가 없습니다!")
        return

    # 2. 개선된 전략으로 재청킹
    logger.info("\n✂️ [2/4] 개선된 전략으로 재청킹...")
    chunker = ImprovedPrecedentChunking(
        chunk_size=800,
        min_chunk_size=200,
        max_chunk_size=1000,  # 모델 max_length(512토큰 ≈ 1000자) 고려
        overlap=100,
        merge_case_info=True
    )

    new_chunks = rechunk_documents(documents, chunker)

    # 통계
    lengths = [len(c['content']) for c in new_chunks]
    sections = {}
    for c in new_chunks:
        sec = c['metadata'].get('section', 'unknown')
        sections[sec] = sections.get(sec, 0) + 1

    logger.info(f"\n📊 재청킹 결과:")
    logger.info(f"  문서 수: {len(documents):,}")
    logger.info(f"  청크 수: {len(new_chunks):,}")
    logger.info(f"  평균 길이: {np.mean(lengths):.0f}자")
    logger.info(f"  최소/최대: {min(lengths)} / {max(lengths)}자")
    logger.info(f"  섹션 분포: {sections}")

    if args.dry_run:
        # 드라이런: 샘플 출력만
        logger.info("\n[DRY-RUN] 샘플 청크:")
        for i, chunk in enumerate(new_chunks[:3]):
            logger.info(f"\n  --- 청크 {i+1} ---")
            logger.info(f"  섹션: {chunk['metadata'].get('section')}")
            logger.info(f"  중요도: {chunk['metadata'].get('importance')}")
            logger.info(f"  길이: {len(chunk['content'])}자")
            logger.info(f"  내용: {chunk['content'][:100]}...")
        return

    # 청크 파일 저장 (--skip-embed 여부와 관계없이)
    output_path = PROJECT_ROOT / args.chunks_output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(new_chunks, f, ensure_ascii=False, indent=2)

    logger.info(f"\n💾 청크 파일 저장: {output_path}")

    if args.skip_embed:
        # GPU 서버 임베딩용 - 청크 파일만 생성하고 종료
        logger.info("\n✅ 청크 파일 생성 완료! (--skip-embed 모드)")
        logger.info(f"  청크 수: {len(new_chunks):,}개")
        logger.info(f"  파일: {output_path}")
        logger.info("\n📤 다음 단계:")
        logger.info("  1. scp로 Ubuntu GPU 서버에 전송")
        logger.info("  2. GPU 서버에서 임베딩 실행")
        logger.info("  3. Qdrant 스토리지를 Mac으로 가져오기")
        print("="*70 + "\n")
        return

    # 3. VectorDB 업데이트
    logger.info("\n🗄️ [3/4] VectorDB 연결...")

    from qdrant_client import QdrantClient
    from libs.rag_core.embeddings.remote_embedder import RemoteEmbedder
    from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB

    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "user_documents")  # 실제 컬렉션명
    REMOTE_EMBED_URL = os.getenv("REMOTE_EMBED_BASE_URL", "https://llm.wonllmapi.uk")

    # VectorDB 초기화 (delete_by_filter 사용)
    embedder = RemoteEmbedder(
        base_url=REMOTE_EMBED_URL,
        batch_size=72,  # OOM 방지를 위해 96 → 72
        timeout=600
    )

    vectordb = QdrantVectorDB(
        url=QDRANT_URL,
        collection_name=QDRANT_COLLECTION,
        embedding_dim=embedder.get_embedding_dimension(),
        timeout=600  # 대량 삭제 작업용 10분 타임아웃
    )

    # 기존 데이터 삭제 (source 필드로 필터링 - 원천 데이터만)
    if not args.skip_delete:
        logger.info("\n🗑️ 기존 원천_판결문/원천_결정례 청크 삭제...")

        # 삭제 전 카운트
        before_count = vectordb.get_count()
        target_count = vectordb.count_by_filter({"source": ["원천_판결문", "원천_결정례"]})
        logger.info(f"  현재 총 포인트: {before_count:,}개")
        logger.info(f"  삭제 대상: {target_count:,}개")

        # 삭제 실행
        deleted = vectordb.delete_by_filter({"source": ["원천_판결문", "원천_결정례"]})
        logger.info(f"  삭제 완료: {deleted:,}개")

    # 4. 임베딩 및 저장
    logger.info("\n🔢 [4/4] 임베딩 및 저장...")
    embed_and_upsert(new_chunks, embedder, vectordb, dry_run=args.dry_run)

    logger.info(f"\n✅ 완료!")
    logger.info(f"  청크 저장: {output_path}")
    logger.info(f"  VectorDB: {QDRANT_URL}/{QDRANT_COLLECTION}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
