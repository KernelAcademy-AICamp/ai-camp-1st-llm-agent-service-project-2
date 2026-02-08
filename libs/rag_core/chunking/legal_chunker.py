"""
Legal Document Specialized Chunking Strategies
법률 문서 특화 청킹 전략
"""

from .chunker import ChunkingStrategy, SlidingWindowChunking, merge_small_chunks
from typing import List, Dict, Any
import re


class LegalArticleChunking(ChunkingStrategy):
    """
    법령 조문 단위 청킹
    - 조문(제N조) 전체를 1개 청크로 유지
    - 너무 길면 항 단위 분리
    - 법령명 + 조문번호를 prefix로 추가

    메타데이터 필드명 (CriminalLawDataLoader와 일치):
    - title 또는 law_title: 법령명
    - article_num: 조문 번호 (예: 제1조)
    - article_title: 조문 제목 (예: 목적)
    """

    def __init__(self, chunk_size: int = 512, max_chunk_size: int = 800,
                 include_header: bool = True,
                 min_chunk_size: int = 100,
                 merge_max_size: int = 600,
                 hard_max_size: int = 1500,  # ⭐ 절대 최대 크기 (분할 강제)
                 overlap: int = 100):
        self.chunk_size = chunk_size
        self.max_chunk_size = max_chunk_size
        self.include_header = include_header
        self.min_chunk_size = min_chunk_size
        self.merge_max_size = merge_max_size
        self.hard_max_size = hard_max_size  # ⭐ 이 크기 초과 시 강제 분할
        self.overlap = overlap

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if metadata is None:
            metadata = {}

        chunks = []

        # 헤더 생성 - 다양한 필드명 지원 (title, law_title 모두 지원)
        header = ""
        if self.include_header:
            # title 또는 law_title 필드 참조 (라벨링 데이터는 title, 원천은 없음)
            law_title = metadata.get('title', '') or metadata.get('law_title', '')
            article_num = metadata.get('article_num', '')
            article_title = metadata.get('article_title', '')

            # 헤더 생성 로직 개선: article_num만 있어도 헤더 생성
            if article_num:
                if law_title and article_title:
                    header = f"[{law_title} {article_num} - {article_title}]\n"
                elif law_title:
                    header = f"[{law_title} {article_num}]\n"
                elif article_title:
                    header = f"[{article_num} - {article_title}]\n"
                else:
                    header = f"[{article_num}]\n"

        total_length = len(header) + len(text)

        if total_length <= self.chunk_size:
            chunks.append({
                'content': header + text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'chunk_type': 'law_article',
                    'is_complete_article': True,
                    'chunking_strategy': 'legal_article'
                }
            })
        elif total_length <= self.max_chunk_size:
            chunks.append({
                'content': header + text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'chunk_type': 'law_article',
                    'is_complete_article': True,
                    'chunking_strategy': 'legal_article'
                }
            })
        else:
            paragraphs = self._split_by_paragraphs(text)

            for idx, paragraph in enumerate(paragraphs):
                chunk_content = header + paragraph if idx == 0 else paragraph

                chunks.append({
                    'content': chunk_content,
                    'metadata': {
                        **metadata,
                        'chunk_id': idx,
                        'chunk_type': 'law_paragraph',
                        'paragraph_num': idx + 1,
                        'is_complete_article': False,
                        'chunking_strategy': 'legal_article'
                    }
                })

            # ⭐ 작은 청크 합치기
            if len(chunks) > 1:
                chunks = merge_small_chunks(
                    chunks,
                    min_size=self.min_chunk_size,
                    max_merged_size=self.merge_max_size
                )

        # ⭐ hard_max_size 초과 청크 강제 분할
        chunks = self._enforce_hard_max(chunks, metadata)

        return chunks

    def _enforce_hard_max(self, chunks: List[Dict[str, Any]], original_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        hard_max_size를 초과하는 청크를 강제 분할
        - 문장 단위로 분할 시도
        - 단일 문장이 너무 길면 sliding window
        """
        result = []
        for chunk in chunks:
            content = chunk.get('content', '')
            if len(content) <= self.hard_max_size:
                result.append(chunk)
            else:
                # 문장 단위로 분할
                sub_chunks = self._split_long_content(content, chunk.get('metadata', {}))
                result.extend(sub_chunks)
        return result

    def _split_long_content(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """긴 콘텐츠를 hard_max_size 이하로 분할"""
        chunks = []
        sentences = re.split(r'(?<=[.?!。])\s+', text)
        current_chunk = ""
        chunk_idx = metadata.get('chunk_id', 0)

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= self.hard_max_size:
                current_chunk = current_chunk + " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'metadata': {
                            **metadata,
                            'chunk_id': chunk_idx,
                            'hard_split': True
                        }
                    })
                    chunk_idx += 1
                current_chunk = sentence

        if current_chunk:
            chunks.append({
                'content': current_chunk.strip(),
                'metadata': {
                    **metadata,
                    'chunk_id': chunk_idx,
                    'hard_split': len(chunks) > 0
                }
            })

        # 단일 문장이 너무 긴 경우 sliding window
        final_chunks = []
        for chunk in chunks:
            if len(chunk['content']) > self.hard_max_size:
                step = self.hard_max_size - self.overlap
                content = chunk['content']
                sub_idx = 0
                for i in range(0, len(content), step):
                    sub_content = content[i:i + self.hard_max_size]
                    if sub_content.strip():
                        final_chunks.append({
                            'content': sub_content.strip(),
                            'metadata': {
                                **chunk['metadata'],
                                'forced_split': True,
                                'sub_chunk_idx': sub_idx
                            }
                        })
                        sub_idx += 1
                    if i + self.hard_max_size >= len(content):
                        break
            else:
                final_chunks.append(chunk)

        return final_chunks if final_chunks else chunks

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """항(①, ②, ...) 또는 (1), (2), ... 단위로 분리"""
        paragraph_pattern = r'[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]|\(\d+\)'

        paragraphs = []
        matches = list(re.finditer(paragraph_pattern, text))

        if not matches:
            return [text]

        if matches[0].start() > 0:
            paragraphs.append(text[:matches[0].start()].strip())

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            paragraph_text = text[start:end].strip()

            if paragraph_text:
                paragraphs.append(paragraph_text)

        return [p for p in paragraphs if p]


class PrecedentAutoChunking(ChunkingStrategy):
    """
    판결문/결정례 자동 섹션 감지 청킹
    - 섹션 패턴 자동 감지 (판시사항, 주문, 이유 등)
    - 섹션 없으면 Sliding Window로 폴백
    """

    # 결정례/판결문 섹션 패턴 (공백 유연하게 처리)
    SECTION_PATTERNS = {
        'summary': r'【?판시사항】?|【?판결요지】?|【?결정요지】?',  # ✅ 결정요지 추가
        'judgment': r'【?주\s*문】?|주\s+문',           # 공백 다수 지원: "주           문"
        'reasoning': r'【?이\s*유】?|이\s+유',          # 공백 다수 지원: "이           유"
        'reference': r'【?참조조문】?|【?참조판례】?|【?참조결정】?',  # ✅ 참조결정 추가
        'case_info': r'사\s*건|사\s+건|피고인|원고|피고|피\s*청\s*구\s*인|청\s*구\s*인|신\s*청\s*인|피\s*신\s*청\s*인',  # ✅ 신청인/피신청인 추가
        'decision': r'【?결\s*정】?|결\s+정',           # ✅ 【결정】 형식 지원
        'order': r'【?명\s*령】?|명\s+령'               # ✅ 신규: 명령 섹션 추가
    }

    def __init__(self, chunk_size: int = 600, overlap: int = 100,  # ✅ overlap 50 → 100
                 auto_detect_sections: bool = True):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.auto_detect_sections = auto_detect_sections

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if metadata is None:
            metadata = {}

        if self.auto_detect_sections:
            sections = self._detect_sections(text)

            if sections:
                return self._chunk_by_sections(sections, metadata)

        return self._sliding_window_chunk(text, metadata)

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

    def _chunk_by_sections(self, sections: List[Dict[str, Any]],
                          metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """섹션별 청킹"""
        chunks = []
        chunk_id = 0

        for section in sections:
            section_content = section['content'].strip()
            section_type = section['type']

            if not section_content:
                continue

            if len(section_content) <= self.chunk_size:
                chunks.append({
                    'content': section_content,
                    'metadata': {
                        **metadata,
                        'chunk_id': chunk_id,
                        'section': section_type,
                        'chunking_strategy': 'precedent_auto'
                    }
                })
                chunk_id += 1
            else:
                sub_chunks = self._split_long_section(section_content, section_type)
                for sub_chunk in sub_chunks:
                    chunks.append({
                        'content': sub_chunk,
                        'metadata': {
                            **metadata,
                            'chunk_id': chunk_id,
                            'section': section_type,
                            'chunking_strategy': 'precedent_auto'
                        }
                    })
                    chunk_id += 1

        return chunks

    def _split_long_section(self, text: str, section_type: str) -> List[str]:
        """긴 섹션 분할"""
        step_size = self.chunk_size - self.overlap
        chunks = []

        for i in range(0, len(text), step_size):
            end_pos = min(i + self.chunk_size, len(text))
            chunk_text = text[i:end_pos]
            if chunk_text.strip():
                chunks.append(chunk_text)
            if end_pos >= len(text):
                break

        return chunks

    def _sliding_window_chunk(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """폴백: sliding window 청킹"""
        chunker = SlidingWindowChunking(
            window_size=self.chunk_size,
            step_size=self.chunk_size - self.overlap
        )

        # metadata를 직접 전달하여 일관성 유지
        chunks = chunker.chunk(text, metadata)

        for chunk in chunks:
            chunk['metadata']['chunking_strategy'] = 'precedent_auto_fallback'

        return chunks


class QAPreserveChunking(ChunkingStrategy):
    """
    QA 데이터 보존 청킹
    - Q&A 전체를 하나의 청크로 유지
    - 너무 길면 (max_length 이상) 분할
    - hard_max_size 초과 시 강제 분할 (메타데이터 유지)
    """

    def __init__(self, max_length: int = 1000, preserve_whole: bool = True,
                 hard_max_size: int = 1500, overlap: int = 100):
        self.max_length = max_length
        self.preserve_whole = preserve_whole
        self.hard_max_size = hard_max_size  # ⭐ 절대 최대 크기
        self.overlap = overlap  # ⭐ 분할 시 오버랩

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if metadata is None:
            metadata = {}

        if self.preserve_whole and len(text) <= self.max_length:
            return [{
                'content': text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'qa_preserved': True,
                    'chunk_type': 'qa_whole',
                    'chunking_strategy': 'qa_preserve'
                }
            }]
        else:
            chunks = self._split_qa(text, metadata)
            # ⭐ hard_max_size 초과 청크 강제 분할
            return self._enforce_hard_max(chunks, metadata)

    def _enforce_hard_max(self, chunks: List[Dict[str, Any]], original_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """hard_max_size 초과 청크를 강제 분할 (메타데이터 유지)"""
        result = []
        for chunk in chunks:
            content = chunk.get('content', '')
            if len(content) <= self.hard_max_size:
                result.append(chunk)
            else:
                # 문장 단위로 분할 시도
                sub_chunks = self._split_long_content(content, chunk.get('metadata', {}))
                result.extend(sub_chunks)
        return result

    def _split_long_content(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """긴 콘텐츠를 hard_max_size 이하로 분할 (메타데이터 유지)"""
        chunks = []
        # 문장 단위로 분리 (마침표, 물음표, 느낌표 기준)
        sentences = re.split(r'(?<=[.?!。])\s+', text)
        current_chunk = ""
        chunk_idx = 0
        original_chunk_id = metadata.get('chunk_id', 0)

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= self.hard_max_size:
                current_chunk = current_chunk + " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'metadata': {
                            **metadata,
                            'chunk_id': f"{original_chunk_id}_{chunk_idx}",
                            'hard_split': True,
                            'split_index': chunk_idx,
                            'original_chunk_id': original_chunk_id
                        }
                    })
                    chunk_idx += 1
                current_chunk = sentence

        if current_chunk:
            chunks.append({
                'content': current_chunk.strip(),
                'metadata': {
                    **metadata,
                    'chunk_id': f"{original_chunk_id}_{chunk_idx}" if chunk_idx > 0 else original_chunk_id,
                    'hard_split': chunk_idx > 0,
                    'split_index': chunk_idx if chunk_idx > 0 else None,
                    'original_chunk_id': original_chunk_id if chunk_idx > 0 else None
                }
            })

        # 단일 문장이 너무 긴 경우 sliding window로 강제 분할
        final_chunks = []
        for chunk in chunks:
            if len(chunk['content']) > self.hard_max_size:
                step = self.hard_max_size - self.overlap
                content = chunk['content']
                sub_idx = 0
                for i in range(0, len(content), step):
                    sub_content = content[i:i + self.hard_max_size]
                    if sub_content.strip():
                        final_chunks.append({
                            'content': sub_content.strip(),
                            'metadata': {
                                **chunk['metadata'],
                                'forced_split': True,
                                'sub_chunk_idx': sub_idx
                            }
                        })
                        sub_idx += 1
                    if i + self.hard_max_size >= len(content):
                        break
            else:
                final_chunks.append(chunk)

        return final_chunks if final_chunks else chunks

    def _split_qa(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Q&A가 너무 길면 분리"""
        chunks = []

        # Q: ... A: ... 패턴 감지
        qa_pattern = r'(Q:\s*.*?)(?=A:\s*|$)(A:\s*.*)?'
        match = re.search(qa_pattern, text, re.DOTALL | re.IGNORECASE)

        if match:
            question = match.group(1).strip() if match.group(1) else ''
            answer = match.group(2).strip() if match.group(2) else ''

            if question:
                chunks.append({
                    'content': question,
                    'metadata': {
                        **metadata,
                        'chunk_id': 0,
                        'qa_preserved': False,
                        'chunk_type': 'qa_question',
                        'chunking_strategy': 'qa_preserve'
                    }
                })

            if answer:
                chunks.append({
                    'content': answer,
                    'metadata': {
                        **metadata,
                        'chunk_id': 1,
                        'qa_preserved': False,
                        'chunk_type': 'qa_answer',
                        'chunking_strategy': 'qa_preserve'
                    }
                })
        else:
            chunks.append({
                'content': text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'qa_preserved': True,
                    'chunk_type': 'qa_whole',
                    'chunking_strategy': 'qa_preserve'
                }
            })

        return chunks


# ✅ 신규 추가: 해석례 전용 청킹 전략
class InterpretationChunking(ChunkingStrategy):
    """
    해석례 질의/회신 구조 보존 청킹
    - 질의요지와 회신을 하나의 청크로 유지
    - 패턴이 없으면 sliding_window로 폴백
    """

    QUERY_PATTERNS = [
        r'\[질의요지\]',
        r'질의\s*:',
        r'Q\s*:',
        r'질문\s*:'
    ]

    RESPONSE_PATTERNS = [
        r'\[회신\]',
        r'\[이유\]',           # ✅ 추가: 해석례 이유 섹션
        r'회신\s*:',
        r'A\s*:',
        r'답변\s*:',
        r'회답\s*:',
        r'이유\s*:'            # ✅ 추가: 이유 패턴
    ]

    def __init__(self, max_length: int = 1000, preserve_qa_structure: bool = True,
                 fallback_strategy: str = 'sliding_window',
                 max_chunk_size: int = 1500,  # ⭐ 신규: 청크 최대 크기 제한
                 overlap: int = 100):
        self.max_length = max_length
        self.preserve_qa_structure = preserve_qa_structure
        self.fallback_strategy = fallback_strategy
        self.max_chunk_size = max_chunk_size  # ⭐ 개별 청크 최대 크기
        self.overlap = overlap

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if metadata is None:
            metadata = {}

        if self.preserve_qa_structure:
            # 질의/회신 패턴 감지
            has_query = any(re.search(p, text) for p in self.QUERY_PATTERNS)
            has_response = any(re.search(p, text) for p in self.RESPONSE_PATTERNS)

            if has_query or has_response:
                if len(text) <= self.max_length:
                    return [{
                        'content': text,
                        'metadata': {
                            **metadata,
                            'chunk_id': 0,
                            'chunking_strategy': 'interpretation',
                            'has_query': has_query,
                            'has_response': has_response,
                            'interpretation_preserved': True
                        }
                    }]
                else:
                    return self._split_interpretation(text, metadata, has_query, has_response)

        # 폴백: sliding_window
        return self._fallback_chunk(text, metadata)

    def _split_interpretation(self, text: str, metadata: Dict[str, Any],
                              has_query: bool, has_response: bool) -> List[Dict[str, Any]]:
        """긴 해석례 분할 - 개별 파트도 max_chunk_size 초과 시 추가 분할"""
        chunks = []
        chunk_id = 0

        # 회신/이유 패턴으로 분리 시도
        for pattern in self.RESPONSE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                query_part = text[:match.start()].strip()
                response_part = text[match.start():].strip()

                # ⭐ 질의 파트 처리 (너무 길면 분할)
                if query_part:
                    if len(query_part) <= self.max_chunk_size:
                        chunks.append({
                            'content': query_part,
                            'metadata': {
                                **metadata,
                                'chunk_id': chunk_id,
                                'chunking_strategy': 'interpretation',
                                'chunk_type': 'query',
                                'interpretation_preserved': False
                            }
                        })
                        chunk_id += 1
                    else:
                        # 질의 파트가 너무 길면 추가 분할
                        sub_chunks = self._split_long_text(query_part, 'query', metadata)
                        for sub in sub_chunks:
                            sub['metadata']['chunk_id'] = chunk_id
                            chunk_id += 1
                        chunks.extend(sub_chunks)

                # ⭐ 회신/이유 파트 처리 (너무 길면 분할)
                if response_part:
                    if len(response_part) <= self.max_chunk_size:
                        chunks.append({
                            'content': response_part,
                            'metadata': {
                                **metadata,
                                'chunk_id': chunk_id,
                                'chunking_strategy': 'interpretation',
                                'chunk_type': 'response',
                                'interpretation_preserved': False
                            }
                        })
                        chunk_id += 1
                    else:
                        # 회신/이유 파트가 너무 길면 추가 분할
                        sub_chunks = self._split_long_text(response_part, 'response', metadata)
                        for sub in sub_chunks:
                            sub['metadata']['chunk_id'] = chunk_id
                            chunk_id += 1
                        chunks.extend(sub_chunks)

                return chunks if chunks else self._fallback_chunk(text, metadata)

        return self._fallback_chunk(text, metadata)

    def _split_long_text(self, text: str, chunk_type: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        긴 텍스트를 max_chunk_size 이하로 분할
        - 문장 단위로 분할 시도
        - 불가능하면 sliding window
        """
        chunks = []

        # 문장 단위로 분할 시도
        sentences = re.split(r'(?<=[.?!。])\s+', text)
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= self.max_chunk_size:
                current_chunk = current_chunk + " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'metadata': {
                            **metadata,
                            'chunking_strategy': 'interpretation',
                            'chunk_type': chunk_type,
                            'interpretation_preserved': False,
                            'was_split': True
                        }
                    })
                current_chunk = sentence

        if current_chunk:
            chunks.append({
                'content': current_chunk.strip(),
                'metadata': {
                    **metadata,
                    'chunking_strategy': 'interpretation',
                    'chunk_type': chunk_type,
                    'interpretation_preserved': False,
                    'was_split': len(chunks) > 0
                }
            })

        # 문장 분할로 해결 안 되면 (단일 문장이 너무 긴 경우) sliding window
        final_chunks = []
        for chunk in chunks:
            if len(chunk['content']) > self.max_chunk_size:
                # sliding window로 강제 분할
                step = self.max_chunk_size - self.overlap
                content = chunk['content']
                for i in range(0, len(content), step):
                    sub_content = content[i:i + self.max_chunk_size]
                    if sub_content.strip():
                        final_chunks.append({
                            'content': sub_content.strip(),
                            'metadata': {
                                **chunk['metadata'],
                                'forced_split': True
                            }
                        })
                    if i + self.max_chunk_size >= len(content):
                        break
            else:
                final_chunks.append(chunk)

        return final_chunks if final_chunks else chunks

    def _fallback_chunk(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """폴백: sliding window 청킹"""
        chunker = SlidingWindowChunking(window_size=512, step_size=256)
        chunks = chunker.chunk(text, metadata)

        for chunk in chunks:
            chunk['metadata']['chunking_strategy'] = 'interpretation_fallback'

        return chunks
