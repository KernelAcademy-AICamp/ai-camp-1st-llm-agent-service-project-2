"""
Precedent VectorDB Search API Router
ChromaDB 벡터 검색 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import logging
import numpy as np
from pathlib import Path

from app.backend.core.embeddings.vectordb import ChromaVectorDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/precedents", tags=["precedent-vectordb"])


# ============================================
# Pydantic Models
# ============================================

class VectorSearchRequest(BaseModel):
    """벡터 검색 요청"""
    keyword: str = Field(..., min_length=1, description="검색 키워드")
    top_k: int = Field(default=20, ge=1, le=50, description="최대 20-50건")


class PrecedentResult(BaseModel):
    """판례 검색 결과"""
    case_number: str
    title: str
    summary: str
    court: str
    decision_date: str
    score: float


class VectorSearchResponse(BaseModel):
    """벡터 검색 응답"""
    success: bool
    message: str
    total_count: int
    results: List[PrecedentResult]


# ============================================
# ChromaDB 임베딩 모델 (간단한 TF-IDF 또는 임베딩)
# ============================================

def get_simple_embedding(text: str) -> np.ndarray:
    """
    간단한 임베딩 생성 (실제로는 sentence-transformers 사용 권장)
    여기서는 TF-IDF나 간단한 word2vec 대신
    문자 기반 해싱으로 임시 구현
    """
    # TODO: 실제로는 sentence-transformers 모델 사용
    # from sentence_transformers import SentenceTransformer
    # model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    # embedding = model.encode(text)

    # 임시: 문자 기반 간단한 벡터화 (768차원)
    import hashlib
    hash_obj = hashlib.sha256(text.encode('utf-8'))
    hash_bytes = hash_obj.digest()

    # 768차원으로 확장
    vector = np.zeros(768, dtype=np.float32)
    for i in range(len(hash_bytes)):
        vector[i % 768] += hash_bytes[i] / 255.0

    # 정규화
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector


# ============================================
# API Endpoints
# ============================================

@router.post("/search-vectordb", response_model=VectorSearchResponse)
async def search_precedents_vectordb(request: VectorSearchRequest):
    """
    ChromaDB에서 판례 벡터 검색

    Features:
    - Semantic similarity search
    - Returns top K similar precedents
    - Fast retrieval from ChromaDB

    Args:
        request: VectorSearchRequest with keyword and top_k

    Returns:
        VectorSearchResponse with search results
    """
    try:
        logger.info(f"Searching ChromaDB with keyword: '{request.keyword}', top_k: {request.top_k}")

        # Initialize ChromaDB
        vectordb_path = Path(__file__).parent.parent.parent.parent / "data" / "vectordb" / "chroma_criminal_law"

        if not vectordb_path.exists():
            logger.warning(f"ChromaDB not found at {vectordb_path}")
            return VectorSearchResponse(
                success=False,
                message="ChromaDB가 초기화되지 않았습니다. 먼저 벡터 DB를 구축해주세요.",
                total_count=0,
                results=[]
            )

        # Load ChromaDB
        vector_db = ChromaVectorDB(
            persist_directory=str(vectordb_path),
            collection_name="criminal_law_docs"
        )

        doc_count = vector_db.get_count()
        if doc_count == 0:
            logger.warning("ChromaDB is empty")
            return VectorSearchResponse(
                success=False,
                message="ChromaDB에 데이터가 없습니다.",
                total_count=0,
                results=[]
            )

        logger.info(f"ChromaDB loaded with {doc_count} documents")

        # Generate query embedding
        query_embedding = get_simple_embedding(request.keyword)

        # Search
        search_results = vector_db.search(
            query_embedding=query_embedding,
            top_k=min(request.top_k, 50)  # Hard limit: 50
        )

        if not search_results:
            return VectorSearchResponse(
                success=False,
                message=f"'{request.keyword}' 키워드로 검색된 판례가 없습니다.",
                total_count=0,
                results=[]
            )

        # Format results
        precedent_results = []
        for result in search_results:
            metadata = result.get('metadata', {})

            # Extract data from metadata
            precedent = PrecedentResult(
                case_number=metadata.get('case_number', 'N/A'),
                title=metadata.get('title', result.get('text', '')[:100]),
                summary=result.get('text', '')[:500],  # First 500 chars as summary
                court=metadata.get('court', '대법원'),
                decision_date=metadata.get('decision_date', metadata.get('date', '날짜 미상')),
                score=result.get('score', 0.0)
            )
            precedent_results.append(precedent)

        logger.info(f"Found {len(precedent_results)} results for '{request.keyword}'")

        return VectorSearchResponse(
            success=True,
            message=f"'{request.keyword}' 키워드로 {len(precedent_results)}건 검색 완료",
            total_count=len(precedent_results),
            results=precedent_results
        )

    except Exception as e:
        logger.error(f"Error in search_precedents_vectordb: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"ChromaDB 검색 중 오류 발생: {str(e)}"
        )
