"""
Document Processor Service
Handles PDF, DOCX, TXT, and image file parsing and text extraction
With OCR support for scanned PDFs and image files (PNG, JPG, etc.)
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
    from services.ocr import (
        PDFProcessingPipeline,
        apply_ocr_postprocessing,
        DocumentQualityAssessor,
        ocr_image_with_preprocessing,
    )
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    PDFProcessingPipeline = None
    apply_ocr_postprocessing = None
    DocumentQualityAssessor = None
    ocr_image_with_preprocessing = None

# Image processing for OCR - Surya OCR (preferred) or Tesseract (fallback)
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    Image = None
    PILLOW_AVAILABLE = False

# Try Surya OCR first (better accuracy: 97%+ vs Tesseract 87%)
try:
    from surya.recognition import RecognitionPredictor, FoundationPredictor
    from surya.detection import DetectionPredictor
    import torch

    # Determine device: MPS for Apple Silicon, CUDA for NVIDIA, else CPU
    if torch.backends.mps.is_available():
        SURYA_DEVICE = "mps"
    elif torch.cuda.is_available():
        SURYA_DEVICE = "cuda"
    else:
        SURYA_DEVICE = "cpu"

    SURYA_OCR_AVAILABLE = True
except ImportError:
    SURYA_OCR_AVAILABLE = False
    SURYA_DEVICE = "cpu"
    RecognitionPredictor = None
    FoundationPredictor = None
    DetectionPredictor = None

# Fallback to Tesseract
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    TESSERACT_AVAILABLE = False

IMAGE_OCR_AVAILABLE = PILLOW_AVAILABLE and (SURYA_OCR_AVAILABLE or TESSERACT_AVAILABLE)

# Supported image extensions for OCR
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp'}

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

    def extract_text_from_image(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from image file using OCR

        Priority: Surya OCR (97%+ accuracy) > Tesseract (87% accuracy)

        Supports: PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP

        Args:
            file_path: Path to image file

        Returns:
            Dictionary containing extracted text and metadata
        """
        if not IMAGE_OCR_AVAILABLE:
            return {
                'text': '',
                'file_type': 'image',
                'success': False,
                'error': 'Image OCR is not available. Please install surya-ocr or pytesseract.'
            }

        try:
            # Open image with PIL
            image = Image.open(file_path)
            original_size = image.size
            original_mode = image.mode

            # Convert to RGB if necessary (for formats like PNG with alpha channel)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create a white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            # Use Surya OCR (97%+ accuracy, much better than Tesseract 87%)
            if SURYA_OCR_AVAILABLE:
                logger.info(f"[extract_text_from_image] Using Surya OCR for: {file_path}")
                return self._extract_with_surya(image, original_size, original_mode)
            else:
                return {
                    'text': '',
                    'file_type': 'image',
                    'success': False,
                    'error': 'Surya OCR is not available. Please install surya-ocr: pip install surya-ocr'
                }

        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return {
                'text': '',
                'file_type': 'image',
                'success': False,
                'error': str(e)
            }

    def _extract_with_surya(self, image: Image.Image, original_size: tuple, original_mode: str) -> Dict[str, Any]:
        """
        Extract text using Surya OCR (97%+ accuracy)
        Uses MPS on Apple Silicon for acceleration
        """
        try:
            logger.info(f"[Surya OCR] Using device: {SURYA_DEVICE}")

            # Initialize Surya predictors with new API
            # FoundationPredictor takes device, RecognitionPredictor takes FoundationPredictor
            detection_predictor = DetectionPredictor(device=SURYA_DEVICE)
            foundation_predictor = FoundationPredictor(device=SURYA_DEVICE)
            recognition_predictor = RecognitionPredictor(foundation_predictor)

            # Run OCR - pass det_predictor to recognition_predictor
            recognition_results = recognition_predictor([image], det_predictor=detection_predictor)

            # Extract text from results
            text_lines = []
            total_confidence = 0.0
            confidence_count = 0

            for result in recognition_results:
                for line in result.text_lines:
                    text_lines.append(line.text)
                    if hasattr(line, 'confidence') and line.confidence is not None:
                        total_confidence += line.confidence
                        confidence_count += 1

            text = '\n'.join(text_lines)
            avg_confidence = (total_confidence / confidence_count * 100) if confidence_count > 0 else 95.0

            # Clean text
            text = self._clean_text(text, preserve_structure=False)

            # Surya is highly accurate, only needs review if very short text
            needs_review = len(text.strip()) < 10 or avg_confidence < 80.0

            return {
                'text': text,
                'file_type': 'image',
                'success': True,
                'extraction_method': 'surya_ocr',
                'needs_review': needs_review,
                'confidence': avg_confidence,
                'metadata': {
                    'image_size': f"{original_size[0]}x{original_size[1]}",
                    'image_mode': original_mode,
                    'ocr_engine': 'surya',
                    'line_count': len(text_lines),
                }
            }

        except Exception as e:
            logger.error(f"Surya OCR failed: {e}")
            return {
                'text': '',
                'file_type': 'image',
                'success': False,
                'error': f'Surya OCR failed: {str(e)}'
            }

    def _extract_with_tesseract(self, image: Image.Image, original_size: tuple, original_mode: str) -> Dict[str, Any]:
        """
        Extract text using Tesseract OCR (fallback, 87% accuracy)
        """
        custom_config = r'--oem 3 --psm 3 -l kor+eng'

        try:
            text = pytesseract.image_to_string(image, config=custom_config)
        except pytesseract.TesseractError:
            logger.warning("Korean language pack not available, falling back to English only")
            custom_config = r'--oem 3 --psm 3'
            text = pytesseract.image_to_string(image, config=custom_config)

        # Get OCR confidence
        try:
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in ocr_data['conf'] if c != '-1' and str(c).isdigit()]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        except Exception:
            avg_confidence = 50.0

        if apply_ocr_postprocessing:
            text = apply_ocr_postprocessing(text)

        text = self._clean_text(text, preserve_structure=False)
        needs_review = avg_confidence < 80.0

        return {
            'text': text,
            'file_type': 'image',
            'success': True,
            'extraction_method': 'tesseract',
            'needs_review': needs_review,
            'confidence': avg_confidence,
            'metadata': {
                'image_size': f"{original_size[0]}x{original_size[1]}",
                'image_mode': original_mode,
                'ocr_engine': 'tesseract',
            }
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
        elif extension in IMAGE_EXTENSIONS:
            extraction_result = self.extract_text_from_image(file_path)
            # extraction_method, needs_review are already set in extract_text_from_image
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
                masking_result = self.pii_masker.mask_with_result(text)
                text = masking_result.masked_text
                masked_metadata['pii_detected'] = masking_result.detected_entities
                masked_metadata['pii_masking_method'] = masking_result.mode
                masked_metadata['pii_processing_time'] = masking_result.processing_time
                masked_metadata['pii_mapping'] = masking_result.mapping  # 복원용 매핑 저장
                logger.info(f"PII masking completed: {len(masking_result.mapping)} entities masked")
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
        elif extension in IMAGE_EXTENSIONS:
            # Image files use OCR, always need review
            return self.extract_text_from_image(file_path)
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
