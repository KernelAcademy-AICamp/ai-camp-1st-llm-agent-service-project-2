"""
Document Processor Service
Handles PDF, DOCX, TXT file parsing and text extraction
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

# Text chunking
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Document processor for extracting text from various file formats
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None
    ):
        """
        Initialize document processor

        Args:
            chunk_size: Maximum size of each text chunk
            chunk_overlap: Overlap between consecutive chunks
            separators: Custom separators for text splitting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

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
            full_text = self._clean_text(full_text)

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
            full_text = self._clean_text(full_text)

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

            text = self._clean_text(text)

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
                text = self._clean_text(text)
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

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove excessive newlines
        text = re.sub(r'\n\s*\n+', '\n\n', text)

        # Remove leading/trailing whitespace
        text = text.strip()

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

    def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        Process a document file (auto-detect format)

        Args:
            file_path: Path to document file

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
            extraction_result = self.extract_text_from_pdf(file_path)
        elif extension == '.docx':
            extraction_result = self.extract_text_from_docx(file_path)
        elif extension == '.txt':
            extraction_result = self.extract_text_from_txt(file_path)
        else:
            return {
                'success': False,
                'error': f'Unsupported file type: {extension}'
            }

        if not extraction_result['success']:
            return extraction_result

        # Chunk the text
        text = extraction_result['text']
        chunks = self.chunk_text(text)

        return {
            'success': True,
            'text': text,
            'chunks': chunks,
            'chunk_count': len(chunks),
            'file_type': extraction_result['file_type'],
            'metadata': extraction_result
        }
