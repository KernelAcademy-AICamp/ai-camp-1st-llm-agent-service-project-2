"""
Legal Document Specialized Chunking Strategies v2
법률 문서 특화 청킹 전략 - 개선 버전

개선사항:
1. DataLoader의 메타데이터 활용 강화
2. 구조화된 데이터와 비구조화 데이터 구분 처리
3. 각 데이터 타입별 최적화된 청킹
4. 메타데이터 기반 컨텍스트 헤더 자동 생성
"""

from .chunker import ChunkingStrategy, SlidingWindowChunking, merge_small_chunks
from typing import List, Dict, Any, Optional, Tuple
import re


class LegalArticleChunkingV2(ChunkingStrategy):
    """
    법령 조문 단위 청킹 v2

    개선사항:
    - DataLoader가 이미 조문 단위로 그룹화한 것을 신뢰
    - 조문 내부의 항/호/목 구조를 활용한 분할
    - 메타데이터의 article_num, article_title 활용
    - 법령명 헤더 자동 생성 개선

    DataLoader 출력 구조:
    - content: "[법령명 제N조 - 제목]\n조문 전체 내용"
    - metadata: law_id, article_num, article_title, law_title, has_structure, gubun_used
    """

    # 최소 유효 청크 크기 - 이보다 작은 청크는 스킵
    MIN_VALID_CHUNK_SIZE: int = 50

    def __init__(self,
                 chunk_size: int = 512,
                 max_chunk_size: int = 800,
                 min_chunk_size: int = 100,
                 merge_max_size: int = 600,
                 hard_max_size: int = 1500,
                 overlap: int = 100,
                 preserve_structure: bool = True,
                 min_valid_size: int = 50):
        """
        Args:
            chunk_size: 기본 청크 크기
            max_chunk_size: 분할 없이 허용하는 최대 크기
            min_chunk_size: 병합 시 최소 청크 크기
            merge_max_size: 병합 시 최대 청크 크기
            hard_max_size: 강제 분할 기준 크기
            overlap: 분할 시 오버랩 크기
            preserve_structure: 구조 보존 여부
            min_valid_size: 최소 유효 청크 크기 (이보다 작으면 스킵)
        """
        self.chunk_size = chunk_size
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.merge_max_size = merge_max_size
        self.hard_max_size = hard_max_size
        self.overlap = overlap
        self.preserve_structure = preserve_structure
        self.min_valid_size = min_valid_size

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if metadata is None:
            metadata = {}

        chunks = []

        # 최소 크기 미만인 경우 스킵 (의미없는 장/절 제목 등)
        if len(text.strip()) < self.min_valid_size:
            return []

        # DataLoader가 이미 구조화했는지 확인
        has_structure = metadata.get('has_structure', False)
        gubun_used = metadata.get('gubun_used', False)

        # 헤더와 본문 분리 (DataLoader가 이미 헤더를 추가한 경우)
        header, body = self._extract_header_and_body(text)

        # 텍스트 길이 확인
        total_length = len(text)

        if total_length <= self.chunk_size:
            # 짧은 텍스트: 그대로 반환
            chunks.append({
                'content': text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'chunk_type': 'law_article',
                    'is_complete_article': True,
                    'chunking_strategy': 'legal_article_v2'
                }
            })
        elif total_length <= self.max_chunk_size:
            # 중간 길이: 그대로 반환
            chunks.append({
                'content': text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'chunk_type': 'law_article',
                    'is_complete_article': True,
                    'chunking_strategy': 'legal_article_v2'
                }
            })
        else:
            # 긴 텍스트: 항/호/목 단위로 분할
            if self.preserve_structure and has_structure:
                # 구조화된 데이터: 항/호/목 기준 분할
                paragraphs = self._split_by_legal_structure(body)
            else:
                # 비구조화 데이터: 패턴 기반 분할
                paragraphs = self._split_by_patterns(body)

            # 청크 생성
            for idx, paragraph in enumerate(paragraphs):
                chunk_content = f"{header}\n{paragraph}" if header and idx == 0 else paragraph

                # 첫 번째 청크가 아닌 경우에도 짧은 컨텍스트 헤더 추가
                if idx > 0 and header:
                    short_header = self._create_continuation_header(metadata)
                    chunk_content = f"{short_header}{paragraph}"

                chunks.append({
                    'content': chunk_content,
                    'metadata': {
                        **metadata,
                        'chunk_id': idx,
                        'chunk_type': 'law_paragraph',
                        'paragraph_num': idx + 1,
                        'is_complete_article': False,
                        'chunking_strategy': 'legal_article_v2'
                    }
                })

            # 작은 청크 병합
            if len(chunks) > 1:
                chunks = merge_small_chunks(
                    chunks,
                    min_size=self.min_chunk_size,
                    max_merged_size=self.merge_max_size
                )

        # hard_max_size 초과 청크 강제 분할
        chunks = self._enforce_hard_max(chunks)

        return chunks

    def _extract_header_and_body(self, text: str) -> Tuple[str, str]:
        """헤더와 본문 분리 (DataLoader가 추가한 [법령명 제N조] 형식)"""
        match = re.match(r'^(\[.*?\])\n?(.*)', text, re.DOTALL)
        if match:
            return match.group(1), match.group(2).strip()
        return '', text

    def _create_continuation_header(self, metadata: Dict[str, Any]) -> str:
        """연속 청크를 위한 짧은 헤더"""
        article_num = metadata.get('article_num', '')
        law_title = metadata.get('law_title', metadata.get('title', ''))

        if law_title and article_num:
            return f"[{law_title} {article_num} 계속]\n"
        elif article_num:
            return f"[{article_num} 계속]\n"
        return ""

    def _split_by_legal_structure(self, text: str) -> List[str]:
        """
        법령 구조 기반 분할 (항, 호, 목)

        구조 우선순위:
        1. 항 (①②③...) - 주요 분할 단위
        2. 호 (1. 2. 3.) - 보조 분할 단위
        3. 목 (가. 나. 다.) - 최소 분할 단위

        개선사항:
        - 첫 번째 부분(헤더+조문명)이 짧으면 첫 번째 항과 병합
        """
        # 항 패턴 (①②③④⑤⑥⑦⑧⑨⑩ 등)
        hang_pattern = r'([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])'

        # 항으로 먼저 분할 시도
        hang_parts = re.split(hang_pattern, text)

        if len(hang_parts) > 1:
            # 항 기준 분할 성공
            paragraphs = []
            prefix = hang_parts[0].strip()  # 첫 번째 항 이전의 내용 (조문명 등)

            i = 1
            first_item = True
            while i < len(hang_parts):
                marker = hang_parts[i]
                content = hang_parts[i + 1] if i + 1 < len(hang_parts) else ''

                if first_item and prefix:
                    # 첫 번째 항에 prefix(조문명) 포함
                    current = f"{prefix}\n{marker}{content.strip()}"
                    first_item = False
                else:
                    current = f"{marker}{content.strip()}"

                paragraphs.append(current)
                i += 2

            return paragraphs if paragraphs else [text]

        # 호 패턴으로 분할 시도 (1. 2. 3.)
        ho_parts = re.split(r'(\d+\.)', text)
        if len(ho_parts) > 3:  # 최소 2개 이상의 호가 있어야
            paragraphs = []
            prefix = ho_parts[0].strip()

            i = 1
            first_item = True
            while i < len(ho_parts):
                marker = ho_parts[i]
                content = ho_parts[i + 1] if i + 1 < len(ho_parts) else ''

                if first_item and prefix:
                    current = f"{prefix}\n{marker}{content.strip()}"
                    first_item = False
                else:
                    current = f"{marker}{content.strip()}"

                paragraphs.append(current)
                i += 2

            return paragraphs if paragraphs else [text]

        # 분할 패턴 없음: 문장 단위로 분할
        return self._split_by_sentences(text)

    def _split_by_patterns(self, text: str) -> List[str]:
        """패턴 기반 분할 (비구조화 데이터용)"""
        # 항 패턴
        paragraph_pattern = r'[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]|\(\d+\)'

        matches = list(re.finditer(paragraph_pattern, text))

        if not matches:
            return self._split_by_sentences(text)

        paragraphs = []

        # 첫 번째 매치 전 텍스트
        if matches[0].start() > 0:
            paragraphs.append(text[:matches[0].start()].strip())

        # 각 매치 처리
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            paragraph_text = text[start:end].strip()

            if paragraph_text:
                paragraphs.append(paragraph_text)

        return [p for p in paragraphs if p]

    def _split_by_sentences(self, text: str) -> List[str]:
        """문장 단위 분할 (마지막 폴백)"""
        sentences = re.split(r'(?<=[.?!。])\s+', text)

        paragraphs = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) <= self.chunk_size:
                current = f"{current} {sentence}" if current else sentence
            else:
                if current:
                    paragraphs.append(current.strip())
                current = sentence

        if current:
            paragraphs.append(current.strip())

        return paragraphs if paragraphs else [text]

    def _enforce_hard_max(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """hard_max_size 초과 청크 강제 분할"""
        result = []
        for chunk in chunks:
            content = chunk.get('content', '')
            if len(content) <= self.hard_max_size:
                result.append(chunk)
            else:
                sub_chunks = self._force_split(content, chunk.get('metadata', {}))
                result.extend(sub_chunks)
        return result

    def _force_split(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """강제 분할 (sliding window)"""
        chunks = []
        step = self.hard_max_size - self.overlap
        chunk_idx = 0

        for i in range(0, len(text), step):
            sub_content = text[i:i + self.hard_max_size].strip()
            if sub_content:
                chunks.append({
                    'content': sub_content,
                    'metadata': {
                        **metadata,
                        'chunk_id': f"{metadata.get('chunk_id', 0)}_{chunk_idx}",
                        'forced_split': True,
                        'sub_chunk_idx': chunk_idx
                    }
                })
                chunk_idx += 1

            if i + self.hard_max_size >= len(text):
                break

        return chunks


class PrecedentChunkingV2(ChunkingStrategy):
    """
    판결문/결정례 청킹 v2

    개선사항:
    - DataLoader가 섹션별로 분리한 것을 신뢰
    - 섹션 메타데이터(section) 활용
    - 긴 섹션의 효율적 분할
    - 판시사항/주문/이유 등 중요 섹션 식별

    DataLoader 출력 구조:
    - content: "[판례번호 사건명 - 섹션명]\n섹션 내용"
    - metadata: precedent_id, section, case_name, case_num, has_structure
    """

    # 중요 섹션 (검색 가중치 부여용)
    IMPORTANT_SECTIONS = ['판시사항', '판결요지', '결정요지', '주문']

    # 최소 유효 청크 크기
    MIN_VALID_CHUNK_SIZE: int = 50

    def __init__(self,
                 chunk_size: int = 600,
                 overlap: int = 100,
                 hard_max_size: int = 1500,
                 preserve_section_context: bool = True,
                 min_valid_size: int = 50):
        """
        Args:
            chunk_size: 기본 청크 크기
            overlap: 오버랩 크기
            hard_max_size: 강제 분할 기준
            preserve_section_context: 섹션 컨텍스트 보존
            min_valid_size: 최소 유효 청크 크기
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.hard_max_size = hard_max_size
        self.preserve_section_context = preserve_section_context
        self.min_valid_size = min_valid_size

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if metadata is None:
            metadata = {}

        # 최소 크기 미만인 경우 스킵
        if len(text.strip()) < self.min_valid_size:
            return []

        chunks = []

        # DataLoader가 이미 섹션별로 분리했는지 확인
        section = metadata.get('section', '')
        has_structure = metadata.get('has_structure', False)

        # 섹션 중요도 판단
        is_important = section in self.IMPORTANT_SECTIONS

        if len(text) <= self.chunk_size:
            # 짧은 텍스트: 그대로 반환
            chunks.append({
                'content': text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'chunk_type': 'precedent_section',
                    'is_complete_section': True,
                    'is_important_section': is_important,
                    'chunking_strategy': 'precedent_v2'
                }
            })
        else:
            # 긴 텍스트: 내부 구조 기반 분할
            header, body = self._extract_header_and_body(text)

            if has_structure:
                sub_sections = self._detect_subsections(body)
            else:
                sub_sections = self._split_by_context(body)

            for idx, sub_content in enumerate(sub_sections):
                chunk_content = sub_content

                # 첫 번째 청크에는 헤더 포함
                if idx == 0 and header:
                    chunk_content = f"{header}\n{sub_content}"
                elif header and self.preserve_section_context:
                    # 후속 청크에는 간략한 컨텍스트 추가
                    short_header = self._create_continuation_header(metadata, section)
                    chunk_content = f"{short_header}{sub_content}"

                chunks.append({
                    'content': chunk_content,
                    'metadata': {
                        **metadata,
                        'chunk_id': idx,
                        'chunk_type': 'precedent_section',
                        'is_complete_section': len(sub_sections) == 1,
                        'is_important_section': is_important,
                        'section_part': idx + 1,
                        'total_parts': len(sub_sections),
                        'chunking_strategy': 'precedent_v2'
                    }
                })

        # hard_max_size 초과 처리
        return self._enforce_hard_max(chunks)

    def _extract_header_and_body(self, text: str) -> Tuple[str, str]:
        """헤더와 본문 분리"""
        match = re.match(r'^(\[.*?\])\n?(.*)', text, re.DOTALL)
        if match:
            return match.group(1), match.group(2).strip()
        return '', text

    def _create_continuation_header(self, metadata: Dict[str, Any], section: str) -> str:
        """연속 청크를 위한 컨텍스트 헤더"""
        case_num = metadata.get('case_num', '')
        if case_num:
            return f"[{case_num} {section} 계속]\n"
        return f"[{section} 계속]\n"

    def _detect_subsections(self, text: str) -> List[str]:
        """
        판결문 내부 하위 구조 감지

        패턴:
        - 숫자. 또는 가. 나. 다.
        - 1), 2), 3)
        - (가), (나)
        """
        # 번호 패턴
        patterns = [
            r'(\d+\.\s)',           # 1. 2. 3.
            r'([가나다라마바사아자차카타파하]\.\s)',  # 가. 나. 다.
            r'(\(\d+\)\s)',         # (1) (2) (3)
            r'(\([가나다라]\)\s)',   # (가) (나) (다)
        ]

        for pattern in patterns:
            parts = re.split(pattern, text)
            if len(parts) > 3:  # 최소 2개 구분
                return self._merge_split_parts(parts)

        # 패턴 없음: 문장 기반 분할
        return self._split_by_semantic_units(text)

    def _merge_split_parts(self, parts: List[str]) -> List[str]:
        """분할된 부분 병합 (구분자와 내용)"""
        result = []
        current = parts[0].strip() if parts[0].strip() else None

        i = 1
        while i < len(parts):
            marker = parts[i]
            content = parts[i + 1] if i + 1 < len(parts) else ''

            if current:
                result.append(current)

            current = f"{marker}{content.strip()}"
            i += 2

        if current:
            result.append(current)

        return result if result else ['\n'.join(parts)]

    def _split_by_context(self, text: str) -> List[str]:
        """문맥 기반 분할 (비구조화 데이터)"""
        # 줄바꿈으로 먼저 분리
        paragraphs = text.split('\n\n')

        result = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current) + len(para) <= self.chunk_size:
                current = f"{current}\n\n{para}" if current else para
            else:
                if current:
                    result.append(current)
                current = para

        if current:
            result.append(current)

        return result if result else [text]

    def _split_by_semantic_units(self, text: str) -> List[str]:
        """의미 단위 분할"""
        sentences = re.split(r'(?<=[.?!。])\s+', text)

        result = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) <= self.chunk_size:
                current = f"{current} {sentence}" if current else sentence
            else:
                if current:
                    result.append(current.strip())
                current = sentence

        if current:
            result.append(current.strip())

        return result if result else [text]

    def _enforce_hard_max(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """hard_max_size 초과 청크 강제 분할"""
        result = []
        for chunk in chunks:
            content = chunk.get('content', '')
            if len(content) <= self.hard_max_size:
                result.append(chunk)
            else:
                step = self.hard_max_size - self.overlap
                sub_idx = 0
                for i in range(0, len(content), step):
                    sub_content = content[i:i + self.hard_max_size].strip()
                    if sub_content:
                        result.append({
                            'content': sub_content,
                            'metadata': {
                                **chunk['metadata'],
                                'chunk_id': f"{chunk['metadata'].get('chunk_id', 0)}_{sub_idx}",
                                'forced_split': True,
                                'sub_chunk_idx': sub_idx
                            }
                        })
                        sub_idx += 1
                    if i + self.hard_max_size >= len(content):
                        break
        return result


class InterpretationChunkingV2(ChunkingStrategy):
    """
    해석례 청킹 v2

    개선사항:
    - DataLoader가 이미 [질의요지], [회답], [이유] 구조로 포맷한 것을 신뢰
    - 메타데이터의 has_query, has_response, has_reason 활용
    - Q&A 구조 보존 우선

    DataLoader 출력 구조:
    - content: "[해석례 번호]\n[질의요지]\n...\n\n[회답]\n...\n\n[이유]\n..."
    - metadata: interpretation_id, has_query, has_response, has_reason, has_structure
    """

    # 섹션 패턴 (DataLoader가 생성한 형식)
    SECTION_MARKERS = {
        'query': r'\[질의요지\]',
        'response': r'\[회답\]',
        'reason': r'\[이유\]'
    }

    # 최소 유효 청크 크기
    MIN_VALID_CHUNK_SIZE: int = 50

    def __init__(self,
                 max_length: int = 1000,
                 max_chunk_size: int = 1500,
                 overlap: int = 100,
                 preserve_qa_pair: bool = True,
                 min_valid_size: int = 50):
        """
        Args:
            max_length: 분할 없이 허용하는 최대 길이
            max_chunk_size: 개별 청크 최대 크기
            overlap: 오버랩 크기
            preserve_qa_pair: Q&A 쌍 보존 여부
            min_valid_size: 최소 유효 청크 크기
        """
        self.max_length = max_length
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.preserve_qa_pair = preserve_qa_pair
        self.min_valid_size = min_valid_size

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if metadata is None:
            metadata = {}

        # 최소 크기 미만인 경우 스킵
        if len(text.strip()) < self.min_valid_size:
            return []

        chunks = []

        # DataLoader가 이미 구조화했는지 확인
        has_structure = metadata.get('has_structure', False)
        has_query = metadata.get('has_query', False)
        has_response = metadata.get('has_response', False)
        has_reason = metadata.get('has_reason', False)

        if len(text) <= self.max_length:
            # 짧은 텍스트: Q&A 전체를 하나의 청크로
            chunks.append({
                'content': text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'chunk_type': 'interpretation_whole',
                    'interpretation_preserved': True,
                    'chunking_strategy': 'interpretation_v2'
                }
            })
        else:
            # 긴 텍스트: 섹션별로 분할
            if has_structure:
                chunks = self._chunk_by_sections(text, metadata)
            else:
                chunks = self._chunk_by_patterns(text, metadata)

        # 최대 크기 초과 처리
        return self._enforce_max_size(chunks)

    def _chunk_by_sections(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        DataLoader가 생성한 섹션 구조 기반 분할
        [질의요지], [회답], [이유] 마커 활용
        """
        chunks = []
        chunk_id = 0

        # 헤더 추출 (예: [해석례 xxx])
        header_match = re.match(r'^(\[해석례[^\]]*\])\n?', text)
        header = header_match.group(1) if header_match else ''
        body = text[header_match.end():] if header_match else text

        # 섹션 분리
        sections = self._split_into_sections(body)

        for section_type, content in sections:
            if not content.strip():
                continue

            # 섹션 컨텍스트 추가
            section_text = content
            if header and chunk_id == 0:
                section_text = f"{header}\n{content}"
            elif self.preserve_qa_pair:
                # 후속 청크에 간략한 컨텍스트 추가
                interp_id = metadata.get('interpretation_id', '')
                if interp_id:
                    section_text = f"[해석례 {interp_id} {section_type}]\n{content}"

            chunks.append({
                'content': section_text,
                'metadata': {
                    **metadata,
                    'chunk_id': chunk_id,
                    'chunk_type': f'interpretation_{section_type}',
                    'section_type': section_type,
                    'interpretation_preserved': False,
                    'chunking_strategy': 'interpretation_v2'
                }
            })
            chunk_id += 1

        # 청크가 없으면 전체를 하나의 청크로
        if not chunks:
            chunks.append({
                'content': text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'chunk_type': 'interpretation_whole',
                    'interpretation_preserved': True,
                    'chunking_strategy': 'interpretation_v2'
                }
            })

        return chunks

    def _split_into_sections(self, text: str) -> List[Tuple[str, str]]:
        """텍스트를 섹션별로 분리"""
        sections = []

        # 모든 섹션 마커 찾기
        all_markers = []
        for section_type, pattern in self.SECTION_MARKERS.items():
            for match in re.finditer(pattern, text):
                all_markers.append((match.start(), match.end(), section_type))

        # 위치순 정렬
        all_markers.sort(key=lambda x: x[0])

        if not all_markers:
            return [('unknown', text)]

        # 첫 번째 마커 전 텍스트
        if all_markers[0][0] > 0:
            pre_text = text[:all_markers[0][0]].strip()
            if pre_text:
                sections.append(('header', pre_text))

        # 각 섹션 추출
        for i, (start, end, section_type) in enumerate(all_markers):
            # 다음 마커까지 또는 끝까지
            next_start = all_markers[i + 1][0] if i + 1 < len(all_markers) else len(text)
            section_content = text[start:next_start].strip()
            sections.append((section_type, section_content))

        return sections

    def _chunk_by_patterns(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """패턴 기반 분할 (비구조화 데이터)"""
        # 질의/회신 패턴 감지
        query_patterns = [r'\[질의요지\]', r'질의\s*:', r'Q\s*:', r'질문\s*:']
        response_patterns = [r'\[회답\]', r'\[회신\]', r'\[이유\]', r'회답\s*:', r'A\s*:', r'답변\s*:']

        has_query = any(re.search(p, text) for p in query_patterns)
        has_response = any(re.search(p, text) for p in response_patterns)

        if has_query or has_response:
            # 질의/회신 패턴으로 분할
            for pattern in response_patterns:
                match = re.search(pattern, text)
                if match:
                    query_part = text[:match.start()].strip()
                    response_part = text[match.start():].strip()

                    chunks = []
                    chunk_id = 0

                    if query_part:
                        chunks.append({
                            'content': query_part,
                            'metadata': {
                                **metadata,
                                'chunk_id': chunk_id,
                                'chunk_type': 'interpretation_query',
                                'section_type': 'query',
                                'interpretation_preserved': False,
                                'chunking_strategy': 'interpretation_v2'
                            }
                        })
                        chunk_id += 1

                    if response_part:
                        chunks.append({
                            'content': response_part,
                            'metadata': {
                                **metadata,
                                'chunk_id': chunk_id,
                                'chunk_type': 'interpretation_response',
                                'section_type': 'response',
                                'interpretation_preserved': False,
                                'chunking_strategy': 'interpretation_v2'
                            }
                        })

                    return chunks if chunks else [self._create_whole_chunk(text, metadata)]

        # 패턴 없음: 전체를 하나로
        return [self._create_whole_chunk(text, metadata)]

    def _create_whole_chunk(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """전체를 하나의 청크로"""
        return {
            'content': text,
            'metadata': {
                **metadata,
                'chunk_id': 0,
                'chunk_type': 'interpretation_whole',
                'interpretation_preserved': True,
                'chunking_strategy': 'interpretation_v2'
            }
        }

    def _enforce_max_size(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """최대 크기 초과 청크 분할"""
        result = []
        for chunk in chunks:
            content = chunk.get('content', '')
            if len(content) <= self.max_chunk_size:
                result.append(chunk)
            else:
                # 문장 단위 분할 시도
                sub_chunks = self._split_long_content(content, chunk.get('metadata', {}))
                result.extend(sub_chunks)
        return result

    def _split_long_content(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """긴 콘텐츠 분할"""
        sentences = re.split(r'(?<=[.?!。])\s+', text)
        chunks = []
        current = ""
        chunk_idx = 0

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= self.max_chunk_size:
                current = f"{current} {sentence}" if current else sentence
            else:
                if current:
                    chunks.append({
                        'content': current.strip(),
                        'metadata': {
                            **metadata,
                            'chunk_id': f"{metadata.get('chunk_id', 0)}_{chunk_idx}",
                            'split_from_long': True
                        }
                    })
                    chunk_idx += 1
                current = sentence

        if current:
            chunks.append({
                'content': current.strip(),
                'metadata': {
                    **metadata,
                    'chunk_id': f"{metadata.get('chunk_id', 0)}_{chunk_idx}" if chunk_idx > 0 else metadata.get('chunk_id', 0),
                    'split_from_long': chunk_idx > 0
                }
            })

        # 문장 분할로도 해결 안 되면 sliding window
        final = []
        for chunk in chunks:
            if len(chunk['content']) > self.max_chunk_size:
                step = self.max_chunk_size - self.overlap
                content = chunk['content']
                sub_idx = 0
                for i in range(0, len(content), step):
                    sub = content[i:i + self.max_chunk_size].strip()
                    if sub:
                        final.append({
                            'content': sub,
                            'metadata': {
                                **chunk['metadata'],
                                'forced_split': True,
                                'sub_chunk_idx': sub_idx
                            }
                        })
                        sub_idx += 1
                    if i + self.max_chunk_size >= len(content):
                        break
            else:
                final.append(chunk)

        return final if final else chunks


class QAPreserveChunkingV2(ChunkingStrategy):
    """
    QA/SUM 데이터 청킹 v2

    개선사항:
    - 라벨링 데이터의 info 메타데이터 활용
    - Q&A 쌍 보존 최우선
    - 요약 데이터도 지원
    - 컨텍스트 헤더 개선

    DataLoader 출력 구조:
    - content: "[문서타입 QA/요약 - 제목/번호]\nQ: ...\nA: ..."
    - metadata: label_type (QA/SUM), input, output, case_name, case_num 등
    """

    # 최소 유효 청크 크기
    MIN_VALID_CHUNK_SIZE: int = 50

    def __init__(self,
                 max_length: int = 1000,
                 hard_max_size: int = 1500,
                 overlap: int = 100,
                 preserve_qa: bool = True,
                 min_valid_size: int = 50):
        """
        Args:
            max_length: 분할 없이 허용하는 최대 길이
            hard_max_size: 강제 분할 기준
            overlap: 오버랩 크기
            preserve_qa: Q&A 쌍 보존 우선
            min_valid_size: 최소 유효 청크 크기
        """
        self.max_length = max_length
        self.hard_max_size = hard_max_size
        self.overlap = overlap
        self.preserve_qa = preserve_qa
        self.min_valid_size = min_valid_size

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if metadata is None:
            metadata = {}

        # 최소 크기 미만인 경우 스킵
        if len(text.strip()) < self.min_valid_size:
            return []

        label_type = metadata.get('label_type', 'QA')

        if len(text) <= self.max_length:
            # 짧은 텍스트: 그대로 반환
            return [{
                'content': text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'chunk_type': f'{label_type.lower()}_whole',
                    'qa_preserved': True,
                    'chunking_strategy': 'qa_preserve_v2'
                }
            }]

        # 긴 텍스트 처리
        if label_type == 'QA' and self.preserve_qa:
            chunks = self._chunk_qa(text, metadata)
        else:
            chunks = self._chunk_sum(text, metadata)

        # 최대 크기 초과 처리
        return self._enforce_hard_max(chunks)

    def _chunk_qa(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """QA 데이터 청킹 - Q&A 분리"""
        chunks = []

        # Q: ... A: ... 패턴 감지
        qa_match = re.search(r'(Q:\s*.*?)(?=A:\s*)(A:\s*.*)', text, re.DOTALL | re.IGNORECASE)

        if qa_match:
            question = qa_match.group(1).strip()
            answer = qa_match.group(2).strip()

            # 헤더 추출
            header_match = re.match(r'^(\[.*?\])\n?', text)
            header = header_match.group(1) if header_match else ''

            if question:
                q_content = f"{header}\n{question}" if header else question
                chunks.append({
                    'content': q_content,
                    'metadata': {
                        **metadata,
                        'chunk_id': 0,
                        'chunk_type': 'qa_question',
                        'qa_preserved': False,
                        'chunking_strategy': 'qa_preserve_v2'
                    }
                })

            if answer:
                # 답변에는 간략한 컨텍스트 추가
                if header:
                    a_header = header.replace('QA', 'A').replace(']', ' 답변]')
                    a_content = f"{a_header}\n{answer}"
                else:
                    a_content = answer

                chunks.append({
                    'content': a_content,
                    'metadata': {
                        **metadata,
                        'chunk_id': 1,
                        'chunk_type': 'qa_answer',
                        'qa_preserved': False,
                        'chunking_strategy': 'qa_preserve_v2'
                    }
                })
        else:
            # Q/A 패턴 없음: 전체를 하나로
            chunks.append({
                'content': text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'chunk_type': 'qa_whole',
                    'qa_preserved': True,
                    'chunking_strategy': 'qa_preserve_v2'
                }
            })

        return chunks

    def _chunk_sum(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """SUM(요약) 데이터 청킹"""
        chunks = []

        # 문장 단위로 분할
        sentences = re.split(r'(?<=[.?!。])\s+', text)
        current = ""
        chunk_idx = 0

        # 헤더 추출
        header_match = re.match(r'^(\[.*?\])\n?', text)
        header = header_match.group(1) if header_match else ''
        body = text[header_match.end():] if header_match else text

        sentences = re.split(r'(?<=[.?!。])\s+', body)

        for sentence in sentences:
            if len(current) + len(sentence) <= self.max_length:
                current = f"{current} {sentence}" if current else sentence
            else:
                if current:
                    chunk_content = f"{header}\n{current.strip()}" if header and chunk_idx == 0 else current.strip()
                    chunks.append({
                        'content': chunk_content,
                        'metadata': {
                            **metadata,
                            'chunk_id': chunk_idx,
                            'chunk_type': 'sum_part',
                            'chunking_strategy': 'qa_preserve_v2'
                        }
                    })
                    chunk_idx += 1
                current = sentence

        if current:
            chunk_content = f"{header}\n{current.strip()}" if header and chunk_idx == 0 else current.strip()
            chunks.append({
                'content': chunk_content,
                'metadata': {
                    **metadata,
                    'chunk_id': chunk_idx,
                    'chunk_type': 'sum_part' if chunk_idx > 0 else 'sum_whole',
                    'chunking_strategy': 'qa_preserve_v2'
                }
            })

        return chunks if chunks else [{'content': text, 'metadata': {**metadata, 'chunk_id': 0, 'chunk_type': 'sum_whole', 'chunking_strategy': 'qa_preserve_v2'}}]

    def _enforce_hard_max(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """hard_max_size 초과 청크 분할"""
        result = []
        for chunk in chunks:
            content = chunk.get('content', '')
            if len(content) <= self.hard_max_size:
                result.append(chunk)
            else:
                # sliding window 분할
                step = self.hard_max_size - self.overlap
                sub_idx = 0
                for i in range(0, len(content), step):
                    sub = content[i:i + self.hard_max_size].strip()
                    if sub:
                        result.append({
                            'content': sub,
                            'metadata': {
                                **chunk['metadata'],
                                'chunk_id': f"{chunk['metadata'].get('chunk_id', 0)}_{sub_idx}",
                                'forced_split': True,
                                'sub_chunk_idx': sub_idx
                            }
                        })
                        sub_idx += 1
                    if i + self.hard_max_size >= len(content):
                        break
        return result


# 전략 매핑 (데이터 타입 → 청킹 전략)
# 실제 데이터 기준: 11개 타입 (법령_SUM은 존재하지 않음)
CHUNKING_STRATEGY_MAP_V2 = {
    # 원천데이터 (4개)
    'source_법령': LegalArticleChunkingV2,
    'source_판결문': PrecedentChunkingV2,
    'source_결정례': PrecedentChunkingV2,  # 결정례도 판결문과 유사한 구조
    'source_해석례': InterpretationChunkingV2,

    # 라벨링데이터 QA (4개)
    'labeled_법령_QA': QAPreserveChunkingV2,
    'labeled_판결문_QA': QAPreserveChunkingV2,
    'labeled_결정례_QA': QAPreserveChunkingV2,
    'labeled_해석례_QA': QAPreserveChunkingV2,

    # 라벨링데이터 SUM (3개) - 법령_SUM은 데이터 없음
    'labeled_판결문_SUM': QAPreserveChunkingV2,
    'labeled_결정례_SUM': QAPreserveChunkingV2,
    'labeled_해석례_SUM': QAPreserveChunkingV2,
}


def get_chunker_v2(doc_type: str, **kwargs) -> ChunkingStrategy:
    """
    데이터 타입에 맞는 청킹 전략 반환

    Args:
        doc_type: 문서 타입 (예: 'source_법령', 'labeled_판결문_QA')
        **kwargs: 청킹 전략 파라미터

    Returns:
        ChunkingStrategy 인스턴스
    """
    strategy_class = CHUNKING_STRATEGY_MAP_V2.get(doc_type)

    if strategy_class:
        return strategy_class(**kwargs)

    # 폴백: 타입에서 키워드 추출
    if '법령' in doc_type:
        return LegalArticleChunkingV2(**kwargs)
    elif '판결문' in doc_type or '결정례' in doc_type:
        return PrecedentChunkingV2(**kwargs)
    elif '해석례' in doc_type:
        return InterpretationChunkingV2(**kwargs)
    elif '_QA' in doc_type or '_SUM' in doc_type:
        return QAPreserveChunkingV2(**kwargs)

    # 기본 폴백
    return SlidingWindowChunking(**kwargs)
