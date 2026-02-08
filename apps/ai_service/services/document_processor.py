"""
Document Processor Service
Handles PDF, DOCX, TXT file parsing and text extraction
With OCR fallback for scanned PDFs
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

# PDF processing
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# DOCX processing
try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

# OCR processing
try:
    from services.ocr import PDFProcessingPipeline, apply_ocr_postprocessing
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    PDFProcessingPipeline = None
    apply_ocr_postprocessing = None

# Text chunking
from langchain_text_splitters import RecursiveCharacterTextSplitter

# PII Masking
from .pii_masker import PiiMasker

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Document processor for extracting text from various file formats
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        enable_masking: bool = True
    ):
        """
        Initialize document processor

        Args:
            chunk_size: Maximum size of each text chunk
            chunk_overlap: Overlap between consecutive chunks
            separators: Custom separators for text splitting
            enable_masking: Whether to enable PII masking (default: True)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.enable_masking = enable_masking
        
        if self.enable_masking:
            try:
                self.pii_masker = PiiMasker(use_llm=True)
            except Exception as e:
                logger.error(f"Failed to initialize PiiMasker: {e}")
                self.pii_masker = None
        else:
            self.pii_masker = None

        # Default separators for Korean legal documents
        if separators is None:
            separators = [
                "\n\n",  # Paragraph breaks
                "\n",    # Line breaks
                "。",    # Korean period
                ". ",    # English period
                "! ",    # Exclamation
                "? ",    # Question
                " ",     # Space
                ""       # Character
            ]

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,
        )

    def extract_text_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from PDF file

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary containing extracted text and metadata
        """
        if PdfReader is None:
            raise ImportError("pypdf is not installed. Install with: pip install pypdf")

        try:
            reader = PdfReader(file_path)
            text_parts = []
            page_count = len(reader.pages)

            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append({
                        'page_number': page_num,
                        'text': page_text
                    })

            full_text = "\n\n".join(part['text'] for part in text_parts)
            # PyMuPDF extracts structured text - preserve original structure
            full_text = self._clean_text(full_text, preserve_structure=True)

            return {
                'text': full_text,
                'page_count': page_count,
                'pages': text_parts,
                'file_type': 'pdf',
                'success': True
            }

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return {
                'text': '',
                'page_count': 0,
                'pages': [],
                'file_type': 'pdf',
                'success': False,
                'error': str(e)
            }

    def extract_pdf_with_ocr_fallback(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from PDF with OCR fallback for scanned documents

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary containing extracted text, extraction method, and metadata
        """
        if not OCR_AVAILABLE:
            logger.warning("OCR not available, using direct extraction only")
            result = self.extract_text_from_pdf(file_path)
            result['extraction_method'] = 'pypdf'
            result['needs_review'] = False
            return result

        try:
            pipeline = PDFProcessingPipeline()
            ocr_result = pipeline.process_pdf(Path(file_path))

            if not ocr_result['success']:
                return {
                    'text': '',
                    'page_count': 0,
                    'file_type': 'pdf',
                    'success': False,
                    'extraction_method': 'failed',
                    'needs_review': False,
                    'error': 'PDF processing failed'
                }

            text = ocr_result['text']
            extraction_method = ocr_result['extraction_method']
            needs_review = ocr_result['needs_review']

            # Apply OCR post-processing if OCR was used
            if extraction_method == 'ocr' and apply_ocr_postprocessing:
                text = apply_ocr_postprocessing(text)

            # OCR text may lose structure - apply formatting
            # PyMuPDF text preserves structure - keep as is
            preserve_structure = (extraction_method != 'ocr')
            text = self._clean_text(text, preserve_structure=preserve_structure)

            return {
                'text': text,
                'page_count': ocr_result['metadata'].get('page_count', 0),
                'file_type': 'pdf',
                'success': True,
                'extraction_method': extraction_method,
                'needs_review': needs_review,
                'confidence': ocr_result.get('confidence', 100.0),
                'metadata': ocr_result['metadata']
            }

        except Exception as e:
            logger.error(f"Error in OCR fallback extraction: {e}")
            # Fallback to direct extraction
            result = self.extract_text_from_pdf(file_path)
            result['extraction_method'] = 'pypdf_fallback'
            result['needs_review'] = False
            return result

    def extract_text_from_docx(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from DOCX file

        Args:
            file_path: Path to DOCX file

        Returns:
            Dictionary containing extracted text and metadata
        """
        if DocxDocument is None:
            raise ImportError("python-docx is not installed. Install with: pip install python-docx")

        try:
            doc = DocxDocument(file_path)
            paragraphs = []

            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)

            full_text = "\n\n".join(paragraphs)
            # DOCX preserves structure - keep as is
            full_text = self._clean_text(full_text, preserve_structure=True)

            return {
                'text': full_text,
                'paragraph_count': len(paragraphs),
                'file_type': 'docx',
                'success': True
            }

        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            return {
                'text': '',
                'paragraph_count': 0,
                'file_type': 'docx',
                'success': False,
                'error': str(e)
            }

    def extract_text_from_txt(self, file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Extract text from TXT file

        Args:
            file_path: Path to TXT file
            encoding: File encoding (default: utf-8)

        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()

            # TXT files preserve structure - keep as is
            text = self._clean_text(text, preserve_structure=True)

            return {
                'text': text,
                'file_type': 'txt',
                'success': True
            }

        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='cp949') as f:
                    text = f.read()
                # TXT files preserve structure - keep as is
                text = self._clean_text(text, preserve_structure=True)
                return {
                    'text': text,
                    'file_type': 'txt',
                    'success': True
                }
            except Exception as e:
                logger.error(f"Error extracting text from TXT (encoding fallback): {e}")
                return {
                    'text': '',
                    'file_type': 'txt',
                    'success': False,
                    'error': str(e)
                }

        except Exception as e:
            logger.error(f"Error extracting text from TXT: {e}")
            return {
                'text': '',
                'file_type': 'txt',
                'success': False,
                'error': str(e)
            }

    def _clean_text(self, text: str, preserve_structure: bool = True) -> str:
        """
        Clean extracted text with optional structure formatting

        Args:
            text: Raw text
            preserve_structure: If True, preserve existing document structure (default).
                              If False, apply legal document formatting (for OCR text).

        Returns:
            Cleaned text
        """
        # Normalize excessive whitespace while preserving structure
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
        text = re.sub(r'\n\s*\n+', '\n\n', text)  # Multiple newlines to double newline

        # Only apply legal formatting for non-structured text (e.g., OCR output)
        if not preserve_structure:
            text = self._format_legal_text(text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def _format_legal_text(self, text: str) -> str:
        """
        Format text with legal document structure (articles, sections, clauses)

        Args:
            text: Text to format

        Returns:
            Formatted text with appropriate line breaks
        """
        # 법률 문서 구조 패턴들

        # 제N조 (Article) - 앞에 두 줄바꿈 추가
        # 예: 제1조, 제10조, 제1조의2
        text = re.sub(r'(?<!\n)\s*(제\s*\d+\s*조(?:\s*의\s*\d+)?)', r'\n\n\1', text)

        # 제N항 (Paragraph/Section) - 앞에 줄바꿈 추가
        # 예: 제1항, 제2항
        text = re.sub(r'(?<!\n)\s*(제\s*\d+\s*항)', r'\n\1', text)

        # ①②③④⑤⑥⑦⑧⑨⑩ 등 원문자 (Numbered items) - 앞에 줄바꿈 추가
        text = re.sub(r'(?<!\n)\s*([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])', r'\n\1', text)

        # 1. 2. 3. 형식 (Numbered list with period)
        # 문장 끝 마침표와 구분하기 위해 공백 뒤에 오는 경우만 처리
        text = re.sub(r'(?<!\n)\s+(\d{1,2})\.\s+(?=[가-힣A-Za-z])', r'\n\1. ', text)

        # 1) 2) 3) 형식 (Numbered list with parenthesis)
        text = re.sub(r'(?<!\n)\s*(\d{1,2}\))\s*', r'\n\1 ', text)

        # 가. 나. 다. 형식 (Korean alphabetic list with period)
        text = re.sub(r'(?<!\n)\s*([가나다라마바사아자차카타파하])\.\s+', r'\n\1. ', text)

        # 가) 나) 다) 형식 (Korean alphabetic list with parenthesis)
        text = re.sub(r'(?<!\n)\s*([가나다라마바사아자차카타파하]\))\s*', r'\n\1 ', text)

        # 제N호 (Item number) - 앞에 줄바꿈 추가
        text = re.sub(r'(?<!\n)\s*(제\s*\d+\s*호)', r'\n\1', text)

        # 부칙, 별표 등 특별 섹션 - 앞에 두 줄바꿈
        text = re.sub(r'(?<!\n)\s*(부\s*칙)', r'\n\n\1', text)
        text = re.sub(r'(?<!\n)\s*(별\s*표)', r'\n\n\1', text)

        # [대괄호] 또는 【겹대괄호】로 시작하는 헤더 - 앞에 두 줄바꿈
        text = re.sub(r'(?<!\n)\s*(\[.+?\])', r'\n\n\1', text)
        text = re.sub(r'(?<!\n)\s*(【.+?】)', r'\n\n\1', text)

        # 장(Chapter), 절(Section) - 앞에 두 줄바꿈
        text = re.sub(r'(?<!\n)\s*(제\s*\d+\s*장)', r'\n\n\1', text)
        text = re.sub(r'(?<!\n)\s*(제\s*\d+\s*절)', r'\n\n\1', text)

        # 단서 조항 "다만," "단," - 앞에 줄바꿈
        text = re.sub(r'(?<!\n)\s*(다만\s*,)', r'\n\1', text)
        text = re.sub(r'(?<!\n)\s*(단\s*,)', r'\n\1', text)

        # 연속된 줄바꿈 정리 (3개 이상은 2개로)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 줄 시작의 불필요한 공백 제거
        text = re.sub(r'\n +', '\n', text)

        return text

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunks with metadata
        """
        if not text:
            return []

        chunks = self.text_splitter.split_text(text)

        result = []
        for idx, chunk in enumerate(chunks):
            chunk_data = {
                'chunk_index': idx,
                'text': chunk,
                'start_offset': text.find(chunk),
                'end_offset': text.find(chunk) + len(chunk),
                'token_count': len(chunk.split())  # Approximate token count
            }

            if metadata:
                chunk_data.update(metadata)

            result.append(chunk_data)

        return result

    def process_document(self, file_path: str, use_ocr_fallback: bool = True) -> Dict[str, Any]:
        """
        Process a document file (auto-detect format)

        Args:
            file_path: Path to document file
            use_ocr_fallback: Whether to use OCR fallback for PDFs (default: True)

        Returns:
            Dictionary containing processed text, chunks, and metadata
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return {
                'success': False,
                'error': f'File not found: {file_path}'
            }

        extension = file_path_obj.suffix.lower()

        # Extract text based on file type
        if extension == '.pdf':
            if use_ocr_fallback:
                extraction_result = self.extract_pdf_with_ocr_fallback(file_path)
            else:
                extraction_result = self.extract_text_from_pdf(file_path)
                extraction_result['extraction_method'] = 'pypdf'
                extraction_result['needs_review'] = False
        elif extension == '.docx':
            extraction_result = self.extract_text_from_docx(file_path)
            extraction_result['extraction_method'] = 'docx'
            extraction_result['needs_review'] = False
        elif extension == '.txt':
            extraction_result = self.extract_text_from_txt(file_path)
            extraction_result['extraction_method'] = 'txt'
            extraction_result['needs_review'] = False
        else:
            return {
                'success': False,
                'error': f'Unsupported file type: {extension}'
            }

        if not extraction_result['success']:
            return extraction_result

        # Chunk the text
        text = extraction_result['text']
        
        # Apply PII Masking if enabled
        masked_metadata = {}
        if self.enable_masking and self.pii_masker:
            try:
                logger.info(f"Masking PII for document: {file_path}")
                masking_result = self.pii_masker.mask_document(text)
                text = masking_result.masked_text
                masked_metadata['pii_detected'] = masking_result.detected_entities
                masked_metadata['pii_masking_method'] = masking_result.method
                masked_metadata['pii_processing_time'] = masking_result.processing_time
            except Exception as e:
                logger.error(f"PII masking failed for {file_path}: {e}")
                # Continue with original text if masking fails
        
        chunks = self.chunk_text(text)

        return {
            'success': True,
            'text': text,
            'chunks': chunks,
            'chunk_count': len(chunks),
            'file_type': extraction_result['file_type'],
            'extraction_method': extraction_result.get('extraction_method', 'unknown'),
            'needs_review': extraction_result.get('needs_review', False),
            'confidence': extraction_result.get('confidence', 100.0),
            'metadata': {**extraction_result, **masked_metadata}
        }

    def extract_text_for_review(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from document for user review (Phase 1 of two-phase flow)

        This method extracts text and returns immediately without chunking,
        allowing the user to review and edit the extracted text before processing.

        Args:
            file_path: Path to document file

        Returns:
            Dictionary containing:
            - success: bool
            - text: extracted text
            - extraction_method: 'pymupdf' or 'ocr'
            - needs_review: True if OCR was used
            - confidence: OCR confidence score (100.0 if direct extraction)
            - metadata: additional extraction metadata
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return {
                'success': False,
                'error': f'File not found: {file_path}'
            }

        extension = file_path_obj.suffix.lower()

        if extension == '.pdf':
            return self.extract_pdf_with_ocr_fallback(file_path)
        elif extension == '.docx':
            result = self.extract_text_from_docx(file_path)
            result['extraction_method'] = 'docx'
            result['needs_review'] = False
            result['confidence'] = 100.0
            return result
        elif extension == '.txt':
            result = self.extract_text_from_txt(file_path)
            result['extraction_method'] = 'txt'
            result['needs_review'] = False
            result['confidence'] = 100.0
            return result
        else:
            return {
                'success': False,
                'error': f'Unsupported file type: {extension}'
            }

    def process_with_confirmed_text(
        self,
        text: str,
        file_type: str,
        original_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process document with user-confirmed text (Phase 2 of two-phase flow)

        This method takes the user-confirmed/edited text and performs chunking.

        Args:
            text: User-confirmed/edited text
            file_type: Original file type ('pdf', 'docx', 'txt')
            original_metadata: Original extraction metadata

        Returns:
            Dictionary containing processed text, chunks, and metadata
        """
        # User-confirmed text should preserve existing structure
        text = self._clean_text(text, preserve_structure=True)
        chunks = self.chunk_text(text)

        return {
            'success': True,
            'text': text,
            'chunks': chunks,
            'chunk_count': len(chunks),
            'file_type': file_type,
            'extraction_method': 'user_confirmed',
            'needs_review': False,
            'metadata': original_metadata or {}
        }
