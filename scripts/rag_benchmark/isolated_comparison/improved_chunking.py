#!/usr/bin/env python3
"""
개선된 법률특화 청킹 전략

문제점:
1. 현재 PrecedentAutoChunking은 평균 206자의 너무 작은 청크 생성
2. case_info 섹션이 72.9%로 과다 (대부분 짧은 메타데이터)
3. 핵심 내용(reasoning, summary)이 너무 분산됨

개선 방향:
1. 최소 청크 크기를 300자로 설정 (작은 청크 병합)
2. case_info 섹션은 하나로 합치기
3. chunk_size를 1000자로 증가 (더 많은 컨텍스트 유지)
4. 중요 섹션(reasoning, summary) 우선순위 부여
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ImprovedChunk:
    """개선된 청크 데이터 구조"""
    chunk_id: str
    doc_id: str
    doc_type: str
    text: str
    chunk_index: int
    section: str
    importance: str  # high, medium, low
    metadata: Dict[str, Any]


class ImprovedPrecedentChunking:
    """
    개선된 판결문/결정례 청킹 전략

    변경사항:
    1. chunk_size: 600 → 1000 (더 많은 컨텍스트)
    2. min_chunk_size: 30 → 300 (너무 작은 청크 방지)
    3. case_info 병합: 연속된 case_info 섹션을 하나로
    4. 중요도 태깅: reasoning/summary는 high, case_info는 low
    """

    # 섹션 패턴 (기존과 동일)
    SECTION_PATTERNS = {
        'summary': r'【?판시사항】?|【?판결요지】?|【?결정요지】?',
        'judgment': r'【?주\s*문】?|주\s+문',
        'reasoning': r'【?이\s*유】?|이\s+유',
        'reference': r'【?참조조문】?|【?참조판례】?|【?참조결정】?',
        'case_info': r'사\s*건|피고인|원고|피고|청\s*구\s*인|신\s*청\s*인',
        'decision': r'【?결\s*정】?|결\s+정',
    }

    # 섹션별 중요도
    SECTION_IMPORTANCE = {
        'summary': 'high',      # 판시사항 - 핵심 요약
        'reasoning': 'high',    # 이유 - 법적 판단 근거
        'judgment': 'medium',   # 주문 - 결론
        'reference': 'medium',  # 참조 - 관련 법령/판례
        'decision': 'medium',   # 결정
        'case_info': 'low',     # 사건 정보 - 메타데이터
        'other': 'low',
    }

    def __init__(
        self,
        chunk_size: int = 1000,      # ✅ 600 → 1000
        min_chunk_size: int = 300,   # ✅ 30 → 300 (너무 작은 청크 방지)
        max_chunk_size: int = 1500,  # ✅ 최대 크기 추가
        overlap: int = 100,
        merge_case_info: bool = True # ✅ case_info 병합 옵션
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

        # 1. 섹션 감지
        sections = self._detect_sections(text)

        if not sections:
            # 섹션 감지 실패 시 sliding window
            return self._sliding_window_chunk(text, metadata)

        # 2. case_info 섹션 병합 (옵션)
        if self.merge_case_info:
            sections = self._merge_case_info_sections(sections)

        # 3. 섹션별 청킹
        chunks = self._chunk_sections(sections, metadata)

        # 4. 작은 청크 병합
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
        """
        ✅ 연속된 case_info 섹션을 하나로 병합

        Before: [case_info, case_info, case_info, reasoning, ...]
        After:  [case_info(병합), reasoning, ...]
        """
        merged = []
        case_info_buffer = []

        for section in sections:
            if section['type'] == 'case_info':
                case_info_buffer.append(section['content'])
            else:
                # case_info 버퍼가 있으면 먼저 처리
                if case_info_buffer:
                    merged.append({
                        'type': 'case_info',
                        'content': '\n'.join(case_info_buffer)
                    })
                    case_info_buffer = []

                merged.append(section)

        # 마지막 버퍼 처리
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

            # ✅ 중요 섹션(reasoning, summary)은 더 큰 청크 허용
            effective_max = self.max_chunk_size if importance == 'high' else self.chunk_size

            if len(section_content) <= effective_max:
                # 섹션 전체를 하나의 청크로
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
                # 큰 섹션은 문단 단위로 분할
                sub_chunks = self._split_long_section(
                    section_content,
                    section_type,
                    importance,
                    metadata
                )
                for sub in sub_chunks:
                    sub['metadata']['chunk_id'] = chunk_id
                    chunks.append(sub)
                    chunk_id += 1

        return chunks

    def _split_long_section(
        self,
        content: str,
        section_type: str,
        importance: str,
        metadata: Dict
    ) -> List[Dict]:
        """긴 섹션을 문단 단위로 분할"""
        chunks = []

        # 문단으로 분리 (빈 줄 기준)
        paragraphs = re.split(r'\n\s*\n', content)

        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 현재 청크에 추가 가능하면 추가
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
            else:
                # 현재 청크 저장
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

                # 새 문단이 너무 길면 문장 단위로 분할
                if len(para) > self.chunk_size:
                    sentence_chunks = self._split_by_sentences(
                        para, section_type, importance, metadata
                    )
                    chunks.extend(sentence_chunks)
                    current_chunk = ""
                else:
                    current_chunk = para

        # 마지막 청크 처리
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
        self,
        text: str,
        section_type: str,
        importance: str,
        metadata: Dict
    ) -> List[Dict]:
        """문장 단위로 분할"""
        chunks = []
        sentences = re.split(r'(?<=[.?!。])\s+', text)

        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
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
        """
        ✅ 최소 크기 미달 청크를 인접 청크와 병합

        - 같은 섹션끼리만 병합
        - max_chunk_size 초과하지 않는 범위에서 병합
        """
        if not chunks:
            return chunks

        merged = []
        buffer = None

        for chunk in chunks:
            content_len = len(chunk['content'])

            if content_len >= self.min_chunk_size:
                # 버퍼에 있는 작은 청크 먼저 처리
                if buffer:
                    # 현재 청크와 같은 섹션이고 합쳐도 max_chunk_size 이하면 병합
                    if (buffer['metadata'].get('section') == chunk['metadata'].get('section') and
                        len(buffer['content']) + content_len + 2 <= self.max_chunk_size):
                        chunk['content'] = f"{buffer['content']}\n\n{chunk['content']}"
                    else:
                        merged.append(buffer)
                    buffer = None

                merged.append(chunk)
            else:
                # 작은 청크 → 버퍼에 저장
                if buffer:
                    # 버퍼에 이미 있으면 병합 시도
                    if (buffer['metadata'].get('section') == chunk['metadata'].get('section') and
                        len(buffer['content']) + content_len + 2 <= self.max_chunk_size):
                        buffer['content'] = f"{buffer['content']}\n\n{chunk['content']}"
                    else:
                        merged.append(buffer)
                        buffer = chunk
                else:
                    buffer = chunk

        # 마지막 버퍼 처리
        if buffer:
            merged.append(buffer)

        return merged

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
# 비교 테스트
# ============================================================

def compare_chunking_strategies(sample_text: str, doc_metadata: Dict = None):
    """기존 vs 개선 전략 비교"""
    from libs.rag_core.chunking.legal_chunker import PrecedentAutoChunking

    # 기존 전략
    old_chunker = PrecedentAutoChunking(
        chunk_size=600,
        overlap=100,
        auto_detect_sections=True
    )

    # 개선된 전략
    new_chunker = ImprovedPrecedentChunking(
        chunk_size=1000,
        min_chunk_size=300,
        max_chunk_size=1500,
        overlap=100,
        merge_case_info=True
    )

    old_chunks = old_chunker.chunk(sample_text, doc_metadata or {})
    new_chunks = new_chunker.chunk(sample_text, doc_metadata or {})

    print(f"\n{'='*60}")
    print("기존 전략 vs 개선된 전략 비교")
    print(f"{'='*60}")

    print(f"\n[기존 PrecedentAutoChunking]")
    print(f"  청크 수: {len(old_chunks)}")
    if old_chunks:
        import numpy as np
        old_lengths = [len(c.get('content', '')) for c in old_chunks]
        print(f"  평균 길이: {np.mean(old_lengths):.0f}자")
        print(f"  최소/최대: {min(old_lengths)} / {max(old_lengths)}자")

    print(f"\n[개선된 ImprovedPrecedentChunking]")
    print(f"  청크 수: {len(new_chunks)}")
    if new_chunks:
        import numpy as np
        new_lengths = [len(c.get('content', '')) for c in new_chunks]
        print(f"  평균 길이: {np.mean(new_lengths):.0f}자")
        print(f"  최소/최대: {min(new_lengths)} / {max(new_lengths)}자")

    return old_chunks, new_chunks


if __name__ == "__main__":
    # 테스트용 샘플 텍스트
    sample = """
사건
2023노1234 음주운전

피고인 홍길동
항소인 피고인

【주문】
피고인의 항소를 기각한다.

【이유】
1. 항소이유의 요지
피고인은 원심판결에 대하여 양형부당을 주장하며 항소하였다.

2. 판단
가. 양형부당 주장에 대한 판단
형사소송법의 공판중심주의와 직접주의에 따르면, 양형판단에 관하여도 제1심의 고유한 영역이 존재하고, 제1심의 양형이 재량의 합리적인 범위를 벗어나지 않는 경우에는 이를 존중함이 타당하다.

피고인은 혈중알코올농도 0.12%의 만취 상태에서 약 2km를 운전하였다. 이는 도로교통법 제44조에서 규정한 음주운전 금지 의무를 명백히 위반한 것이다.

나. 결론
원심의 형(벌금 500만 원)은 피고인의 범행 내용, 동종 전과 유무, 반성의 태도 등을 종합적으로 고려할 때 적정하다고 판단된다.

3. 결론
그러므로 피고인의 항소는 이유 없어 형사소송법 제364조 제4항에 따라 이를 기각한다.

【참조조문】
도로교통법 제44조, 제148조의2
형사소송법 제364조 제4항
"""

    compare_chunking_strategies(sample)
