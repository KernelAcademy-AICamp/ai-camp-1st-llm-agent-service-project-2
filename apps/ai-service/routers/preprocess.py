"""
Document Preprocessing Router
Handles document upload, text extraction, and chunking
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import tempfile
import os
from pathlib import Path

from services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/preprocess",
    tags=["Document Preprocessing"]
)


# Request/Response Models
class PreprocessRequest(BaseModel):
    """Request model for document preprocessing"""
    file_url: str = Field(..., description="URL or path to document file")
    chunk_size: Optional[int] = Field(1000, description="Maximum chunk size")
    chunk_overlap: Optional[int] = Field(200, description="Overlap between chunks")


class ChunkData(BaseModel):
    """Chunk data model"""
    chunk_index: int
    text: str
    start_offset: int
    end_offset: int
    token_count: int


class PreprocessResponse(BaseModel):
    """Response model for document preprocessing"""
    success: bool
    document_id: Optional[str] = None
    text: Optional[str] = None
    chunks: List[ChunkData] = []
    chunk_count: int = 0
    file_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/document", response_model=PreprocessResponse)
async def preprocess_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT)"),
    chunk_size: int = Form(1000, description="Maximum chunk size"),
    chunk_overlap: int = Form(200, description="Overlap between chunks")
):
    """
    Preprocess a document file

    - Extract text from PDF, DOCX, or TXT files
    - Clean and normalize text
    - Split text into chunks for embedding
    - Return chunks with metadata

    Args:
        file: Uploaded document file
        chunk_size: Maximum size of each chunk (default: 1000)
        chunk_overlap: Overlap between chunks (default: 200)

    Returns:
        Preprocessed document with chunks
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.txt']
    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save uploaded file to temporary location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        logger.info(f"Processing document: {file.filename} ({len(content)} bytes)")

        # Initialize document processor
        processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        # Process document
        result = processor.process_document(tmp_file_path)

        # Clean up temporary file
        os.unlink(tmp_file_path)

        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Failed to process document')
            )

        # Convert chunks to response model
        chunks = [ChunkData(**chunk) for chunk in result['chunks']]

        logger.info(
            f"Document processed successfully: {file.filename} "
            f"({result['chunk_count']} chunks)"
        )

        return PreprocessResponse(
            success=True,
            text=result['text'],
            chunks=chunks,
            chunk_count=result['chunk_count'],
            file_type=result['file_type'],
            metadata=result.get('metadata', {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preprocessing document: {e}", exc_info=True)
        # Clean up temporary file if it exists
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/text", response_model=PreprocessResponse)
async def preprocess_text(
    text: str = Form(..., description="Text content to preprocess"),
    chunk_size: int = Form(1000, description="Maximum chunk size"),
    chunk_overlap: int = Form(200, description="Overlap between chunks")
):
    """
    Preprocess raw text

    - Clean and normalize text
    - Split text into chunks for embedding

    Args:
        text: Raw text content
        chunk_size: Maximum size of each chunk (default: 1000)
        chunk_overlap: Overlap between chunks (default: 200)

    Returns:
        Preprocessed text with chunks
    """
    try:
        logger.info(f"Processing raw text ({len(text)} characters)")

        # Initialize document processor
        processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        # Clean text
        cleaned_text = processor._clean_text(text)

        # Chunk text
        chunks = processor.chunk_text(cleaned_text)

        # Convert chunks to response model
        chunk_models = [ChunkData(**chunk) for chunk in chunks]

        logger.info(f"Text processed successfully ({len(chunks)} chunks)")

        return PreprocessResponse(
            success=True,
            text=cleaned_text,
            chunks=chunk_models,
            chunk_count=len(chunks),
            file_type='text',
            metadata={'original_length': len(text), 'cleaned_length': len(cleaned_text)}
        )

    except Exception as e:
        logger.error(f"Error preprocessing text: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
