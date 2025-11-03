"""
Legal Document Specialized Chunking Strategies
법률 문서 특화 청킹 전략
"""

from .chunker import ChunkingStrategy
from typing import List, Dict, Any, Optional
import re


class LegalArticleChunking(ChunkingStrategy):
    """
    법령 조문 단위 청킹
    - 조문(제N조) 전체를 1개 청크로 유지
    - 너무 길면 항 단위 분리
    - 법령명 + 조문번호를 prefix로 추가
    """

    def __init__(self, chunk_size: int = 512, max_chunk_size: int = 1000,
                 include_header: bool = True):
        """
        Initialize legal article chunker.

        Args:
            chunk_size: Target chunk size in characters
            max_chunk_size: Maximum chunk size before splitting
            include_header: Include law title and article number as header
        """
        self.chunk_size = chunk_size
        self.max_chunk_size = max_chunk_size
        self.include_header = include_header

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk law article text.

        Args:
            text: Law article content
            metadata: {
                'law_id': '000239',
                'law_title': '건설기계관리법',
                'article_num': '제37조',
                'article_title': '수수료 등'
            }

        Returns:
            List of chunk dictionaries
        """
        if metadata is None:
            metadata = {}

        chunks = []

        # 헤더 생성
        header = ""
        if self.include_header:
            law_title = metadata.get('law_title', '')
            article_num = metadata.get('article_num', '')
            article_title = metadata.get('article_title', '')

            if law_title and article_num:
                if article_title:
                    header = f"[{law_title} {article_num} - {article_title}]\n"
                else:
                    header = f"[{law_title} {article_num}]\n"

        # 텍스트 길이 확인
        total_length = len(header) + len(text)

        # 짧으면 단일 청크
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
        # 길면 항 단위로 분리
        elif total_length <= self.max_chunk_size:
            # 하나의 청크로 유지 (max_chunk_size 이하)
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
            # 항(①, ②) 단위로 분리
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

        return chunks

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """
        Split text by paragraphs (항: ①, ②, ...).

        Args:
            text: Text to split

        Returns:
            List of paragraph texts
        """
        # 항 패턴: ①, ②, ③, ... 또는 (1), (2), ...
        paragraph_pattern = r'[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]|\(\d+\)'

        # 분리점 찾기
        paragraphs = []
        matches = list(re.finditer(paragraph_pattern, text))

        if not matches:
            # 항 구분이 없으면 전체를 하나로
            return [text]

        # 첫 번째 항 이전 텍스트
        if matches[0].start() > 0:
            paragraphs.append(text[:matches[0].start()].strip())

        # 각 항
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            paragraph_text = text[start:end].strip()

            if paragraph_text:
                paragraphs.append(paragraph_text)

        return [p for p in paragraphs if p]


class PrecedentSectionChunking(ChunkingStrategy):
    """
    판결문 섹션 기반 청킹
    - 헤더 (사건정보) 모든 청크에 포함
    - 판시사항+판결요지 → 단일 청크
    - 주문 → 단일 청크
    - 이유 → Sliding Window (긴 경우)
    """

    def __init__(self, chunk_size: int = 600, overlap: int = 50,
                 include_header: bool = True):
        """
        Initialize precedent section chunker.

        Args:
            chunk_size: Target chunk size
            overlap: Overlap between reasoning chunks
            include_header: Include case header in all chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.include_header = include_header

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk precedent sections.

        Args:
            text: Precedent section content
            metadata: {
                'precedent_id': '100029',
                'case_num': '84도2229',
                'court_name': '대법원',
                'sentence_date': '1984-12-26',
                'section_type': 'reasoning'  # summary/judgment/reasoning
            }

        Returns:
            List of chunk dictionaries
        """
        if metadata is None:
            metadata = {}

        chunks = []

        # 헤더 생성
        header = ""
        if self.include_header:
            court_name = metadata.get('court_name', '')
            sentence_date = metadata.get('sentence_date', '')
            case_num = metadata.get('case_num', '')
            case_name = metadata.get('case_name', '')

            header_parts = []
            if court_name:
                header_parts.append(court_name)
            if sentence_date:
                header_parts.append(sentence_date)

            if header_parts:
                header = f"[{' '.join(header_parts)}]\n"
                if case_num:
                    header += f"[사건번호: {case_num}]\n"
                if case_name:
                    header += f"[사건명: {case_name}]\n"
                header += "\n"

        section_type = metadata.get('section_type', 'other')

        # 섹션 타입에 따라 처리
        if section_type in ['summary', 'judgment']:
            # 판시사항/판결요지/주문은 단일 청크
            chunks.append({
                'content': header + text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'chunk_type': f'precedent_{section_type}',
                    'chunking_strategy': 'precedent_section'
                }
            })

        elif section_type == 'reasoning':
            # 이유는 긴 경우 sliding window로 분리
            if len(header) + len(text) <= self.chunk_size:
                # 짧으면 단일 청크
                chunks.append({
                    'content': header + text,
                    'metadata': {
                        **metadata,
                        'chunk_id': 0,
                        'chunk_type': 'precedent_reasoning',
                        'chunking_strategy': 'precedent_section'
                    }
                })
            else:
                # 긴 경우 sliding window
                reasoning_chunks = self._sliding_window_split(text, self.chunk_size - len(header), self.overlap)

                for idx, chunk_text in enumerate(reasoning_chunks):
                    chunks.append({
                        'content': header + chunk_text,
                        'metadata': {
                            **metadata,
                            'chunk_id': idx,
                            'chunk_type': 'precedent_reasoning',
                            'subsection': f'이유_{idx+1}',
                            'chunking_strategy': 'precedent_section'
                        }
                    })

        else:
            # 기타 섹션
            chunks.append({
                'content': header + text,
                'metadata': {
                    **metadata,
                    'chunk_id': 0,
                    'chunk_type': f'precedent_{section_type}',
                    'chunking_strategy': 'precedent_section'
                }
            })

        return chunks

    def _sliding_window_split(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Split text using sliding window (sentence-aware).

        Args:
            text: Text to split
            chunk_size: Size of each chunk
            overlap: Overlap between chunks

        Returns:
            List of chunk texts
        """
        # 문장 단위로 분리
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # 현재 청크에 추가하면 너무 길어지는 경우
            if current_length + sentence_length > chunk_size and current_chunk:
                # 현재 청크 저장
                chunks.append(' '.join(current_chunk))

                # Overlap 계산 (마지막 몇 문장 유지)
                overlap_sents = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    s_len = len(s)
                    if overlap_len + s_len <= overlap:
                        overlap_sents.insert(0, s)
                        overlap_len += s_len
                    else:
                        break

                current_chunk = overlap_sents
                current_length = overlap_len

            current_chunk.append(sentence)
            current_length += sentence_length

        # 마지막 청크
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks


class QAContextEnrichmentChunking(ChunkingStrategy):
    """
    QA 데이터 청킹 with Context
    - Question + Answer 기본 구조
    - 원문 법령/판결문 일부 추가 (PostgreSQL에서 조회)
    """

    def __init__(self, db_client=None, include_context: bool = True,
                 context_length: int = 300):
        """
        Initialize QA context enrichment chunker.

        Args:
            db_client: PostgreSQL client for fetching source text
            include_context: Whether to include source context
            context_length: Maximum length of context to include
        """
        self.db_client = db_client
        self.include_context = include_context
        self.context_length = context_length

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk QA pair with optional context.

        Args:
            text: Not used (QA data comes from metadata)
            metadata: {
                'qa_id': 'HS_B_000239_QA_3005',
                'doc_type': '법령_QA',
                'doc_id': '000239',  # law_id or precedent_id
                'question': '...',
                'answer': '...',
                'instruction': '...',
                'related_article': '제37조'
            }

        Returns:
            List with single chunk dictionary
        """
        if metadata is None:
            metadata = {}

        question = metadata.get('question', metadata.get('input', ''))
        answer = metadata.get('answer', metadata.get('output', ''))
        instruction = metadata.get('instruction', '')

        # Context 추가
        context = ""
        if self.include_context and self.db_client:
            context = self._get_source_context(metadata)

        # QA 청크 구성
        chunk_content = ""

        if context:
            chunk_content += f"[참고 자료]\n{context}\n\n"

        if instruction:
            chunk_content += f"[지시사항]\n{instruction}\n\n"

        chunk_content += f"[질문]\n{question}\n\n[답변]\n{answer}"

        return [{
            'content': chunk_content,
            'metadata': {
                **metadata,
                'chunk_id': 0,
                'chunk_type': 'qa_pair',
                'has_context': bool(context),
                'chunking_strategy': 'qa_context'
            }
        }]

    def _get_source_context(self, metadata: Dict[str, Any]) -> str:
        """
        Get source context from database.

        Args:
            metadata: QA metadata

        Returns:
            Source context text
        """
        if not self.db_client:
            return ""

        doc_type = metadata.get('doc_type', '')
        doc_id = metadata.get('doc_id', metadata.get('law_id', metadata.get('precedent_id', '')))
        related_article = metadata.get('related_article', '')

        try:
            # 법령 QA
            if '법령' in doc_type:
                article_data = self.db_client.get_law_article(doc_id, related_article)
                if article_data:
                    content = article_data.get('content', '')
                    # 길이 제한
                    return content[:self.context_length] + ('...' if len(content) > self.context_length else '')

            # 판결문 QA
            elif '판결문' in doc_type:
                section_content = self.db_client.get_precedent_section(doc_id, 'summary')
                if section_content:
                    return section_content[:self.context_length] + ('...' if len(section_content) > self.context_length else '')

        except Exception as e:
            print(f"⚠️ Failed to get source context: {e}")

        return ""
