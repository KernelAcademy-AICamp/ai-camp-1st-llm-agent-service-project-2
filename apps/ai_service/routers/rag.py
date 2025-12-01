"""
RAG Indexing Router
Handles document embedding and vector database indexing
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

from services.document_indexer import DocumentIndexer

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/rag",
    tags=["RAG Indexing"]
)


# Request/Response Models
class ChunkData(BaseModel):
    """Chunk data for indexing"""
    chunk_index: int
    text: str
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    token_count: Optional[int] = None


class IndexRequest(BaseModel):
    """Request model for document indexing"""
    document_id: str = Field(..., description="Document ID from Django")
    chunks: List[ChunkData] = Field(..., description="List of text chunks to index")
    document_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional document-level metadata"
    )


class IndexResponse(BaseModel):
    """Response model for document indexing"""
    success: bool
    indexed_count: int = 0
    embedding_ids: List[str] = []
    collection_name: Optional[str] = None
    total_documents: Optional[int] = None
    error: Optional[str] = None


class SearchRequest(BaseModel):
    """Request model for similarity search"""
    query: str = Field(..., description="Search query")
    top_k: int = Field(5, description="Number of results to return")
    document_id: Optional[str] = Field(
        None,
        description="Optional document ID to filter results"
    )


class SearchResult(BaseModel):
    """Search result model"""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """Response model for similarity search"""
    success: bool
    query: str
    results: List[SearchResult] = []
    error: Optional[str] = None


@router.post("/index", response_model=IndexResponse)
async def index_document(request: IndexRequest, fastapi_request: Request):
    """
    Index document chunks into vector database

    - Generate embeddings for each chunk
    - Store embeddings in Qdrant (user_documents collection)
    - Return embedding IDs for updating Django database

    Args:
        request: Index request with document ID and chunks
        fastapi_request: FastAPI request object (for accessing app state)

    Returns:
        Indexing results with embedding IDs
    """
    try:
        # Get embedder and vectordb from app state
        if not hasattr(fastapi_request.app.state, 'embedder'):
            raise HTTPException(
                status_code=500,
                detail="Embedder not initialized"
            )

        if not hasattr(fastapi_request.app.state, 'vectordb'):
            raise HTTPException(
                status_code=500,
                detail="VectorDB not initialized"
            )

        embedder = fastapi_request.app.state.embedder
        vectordb = fastapi_request.app.state.vectordb

        # Initialize document indexer
        indexer = DocumentIndexer(
            vectordb=vectordb,
            embedder=embedder,
            collection_name="user_documents"
        )

        logger.info(
            f"Indexing document {request.document_id} "
            f"with {len(request.chunks)} chunks"
        )

        # Convert Pydantic models to dicts
        chunks_dict = [chunk.model_dump() for chunk in request.chunks]

        # Index chunks
        result = indexer.index_chunks(
            chunks=chunks_dict,
            document_id=request.document_id,
            document_metadata=request.document_metadata
        )

        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Indexing failed')
            )

        logger.info(
            f"Successfully indexed document {request.document_id}: "
            f"{result['indexed_count']} chunks"
        )

        return IndexResponse(
            success=True,
            indexed_count=result['indexed_count'],
            embedding_ids=result['embedding_ids'],
            collection_name=result['collection_name'],
            total_documents=result['total_documents']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def search_similar(request: SearchRequest, fastapi_request: Request):
    """
    Search for similar chunks in user documents

    - Generate query embedding
    - Search in Qdrant user_documents collection
    - Return top-k similar chunks

    Args:
        request: Search request with query and parameters
        fastapi_request: FastAPI request object

    Returns:
        Search results with similar chunks
    """
    try:
        # Get embedder and vectordb from app state
        if not hasattr(fastapi_request.app.state, 'embedder'):
            raise HTTPException(
                status_code=500,
                detail="Embedder not initialized"
            )

        if not hasattr(fastapi_request.app.state, 'vectordb'):
            raise HTTPException(
                status_code=500,
                detail="VectorDB not initialized"
            )

        embedder = fastapi_request.app.state.embedder
        vectordb = fastapi_request.app.state.vectordb

        # Initialize document indexer
        indexer = DocumentIndexer(
            vectordb=vectordb,
            embedder=embedder,
            collection_name="user_documents"
        )

        logger.info(f"Searching for: '{request.query}' (top_k={request.top_k})")

        # Search similar chunks
        results = indexer.search_similar_chunks(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id
        )

        # Convert to response format
        search_results = [
            SearchResult(
                id=result['id'],
                text=result['text'],
                score=result['score'],
                metadata=result['metadata']
            )
            for result in results
        ]

        logger.info(f"Found {len(search_results)} similar chunks")

        return SearchResponse(
            success=True,
            query=request.query,
            results=search_results
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching similar chunks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/stats")
async def get_collection_stats(fastapi_request: Request):
    """
    Get collection statistics

    Returns:
        Collection statistics (count, dimension, etc.)
    """
    try:
        # Get embedder and vectordb from app state
        if not hasattr(fastapi_request.app.state, 'embedder'):
            raise HTTPException(
                status_code=500,
                detail="Embedder not initialized"
            )

        if not hasattr(fastapi_request.app.state, 'vectordb'):
            raise HTTPException(
                status_code=500,
                detail="VectorDB not initialized"
            )

        embedder = fastapi_request.app.state.embedder
        vectordb = fastapi_request.app.state.vectordb

        # Initialize document indexer
        indexer = DocumentIndexer(
            vectordb=vectordb,
            embedder=embedder,
            collection_name="user_documents"
        )

        stats = indexer.get_collection_stats()

        return {
            'success': True,
            'stats': stats
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
