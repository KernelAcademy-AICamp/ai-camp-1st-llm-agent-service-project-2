"""
Precedent Indexer Service
판례 데이터의 Qdrant 및 BM25 인덱싱 담당
"""

import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

from libs.rag_core import BM25Index
from libs.rag_core.embeddings.vectordb import VectorDB

if TYPE_CHECKING:
    from libs.rag_core import KoreanLegalEmbedder
    from libs.rag_core.embeddings.qdrant_vectordb import QdrantVectorDB

logger = logging.getLogger(__name__)


class PrecedentIndexer:
    """
    판례 인덱서

    크롤링된 판례 데이터를 Qdrant와 BM25 인덱스에 저장
    """

    def __init__(
        self,
        embedder: "KoreanLegalEmbedder",
        vectordb: VectorDB,
        bm25_index: BM25Index,
        collection_name: str = "law_documents"
    ):
        """
        Initialize precedent indexer

        Args:
            embedder: Korean legal embedder instance
            vectordb: VectorDB instance (Qdrant)
            bm25_index: BM25 index instance
            collection_name: Collection name for precedents
        """
        self.embedder = embedder
        self.vectordb = vectordb
        self.bm25_index = bm25_index
        self.collection_name = collection_name

        logger.info(f"PrecedentIndexer initialized with collection: {collection_name}")

    async def index_single(
        self,
        case_number: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        단일 판례 인덱싱

        Args:
            case_number: 사건번호 (고유 식별자)
            title: 판례 제목
            content: 판례 본문
            metadata: 추가 메타데이터

        Returns:
            인덱싱 결과 딕셔너리
        """
        if not content or not content.strip():
            return {
                'success': False,
                'error': 'Empty content',
                'case_number': case_number
            }

        try:
            # 1. 텍스트 준비 (제목 + 본문)
            full_text = f"{title}\n\n{content}"

            # 2. 임베딩 생성
            embedding = self.embedder.embed_query(full_text[:8000])  # 최대 길이 제한

            # 3. 메타데이터 준비
            doc_metadata = {
                'case_number': case_number,
                'title': title[:500],  # 제목 길이 제한
                'doc_type': 'PRECEDENT',
                'indexed_at': datetime.utcnow().isoformat(),
            }

            if metadata:
                for key, value in metadata.items():
                    # VectorDB는 단순 타입만 지원
                    if isinstance(value, (str, int, float, bool)):
                        doc_metadata[key] = value
                    elif value is None:
                        continue
                    else:
                        doc_metadata[key] = str(value)

            # 4. VectorDB에 저장
            embedding_id = f"prec_{case_number.replace(' ', '_')}"

            self.vectordb.add_documents(
                texts=[full_text[:8000]],
                embeddings=embedding.reshape(1, -1),
                metadatas=[doc_metadata]
            )

            logger.info(f"VectorDB indexed: {case_number}")

            # 5. BM25 인덱스 업데이트
            self.bm25_index.add_documents(
                documents=[full_text],
                metadatas=[doc_metadata]
            )

            logger.info(f"BM25 indexed: {case_number}")

            return {
                'success': True,
                'case_number': case_number,
                'embedding_id': embedding_id,
                'vectordb_count': self.vectordb.get_count(),
                'bm25_count': len(self.bm25_index.documents)
            }

        except Exception as e:
            logger.error(f"Error indexing precedent {case_number}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'case_number': case_number
            }

    async def index_batch(
        self,
        precedents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        배치 판례 인덱싱

        Args:
            precedents: 판례 목록
                각 항목: {'case_number', 'title', 'content', 'metadata'}

        Returns:
            배치 인덱싱 결과
        """
        if not precedents:
            return {
                'success': True,
                'indexed_count': 0,
                'failed_count': 0,
                'errors': []
            }

        indexed_count = 0
        failed_count = 0
        errors = []

        for prec in precedents:
            case_number = prec.get('case_number', '')
            title = prec.get('title', '')
            content = prec.get('content', '')
            metadata = prec.get('metadata', {})

            if not case_number:
                failed_count += 1
                errors.append({'error': 'Missing case_number', 'data': prec})
                continue

            result = await self.index_single(
                case_number=case_number,
                title=title,
                content=content,
                metadata=metadata
            )

            if result['success']:
                indexed_count += 1
            else:
                failed_count += 1
                errors.append({
                    'case_number': case_number,
                    'error': result.get('error', 'Unknown error')
                })

        # BM25 인덱스 저장
        try:
            self.bm25_index.save(str(self.bm25_index.index_path) if hasattr(self.bm25_index, 'index_path') else None)
            logger.info("BM25 index saved after batch indexing")
        except Exception as e:
            logger.warning(f"Failed to save BM25 index: {e}")

        return {
            'success': failed_count == 0,
            'indexed_count': indexed_count,
            'failed_count': failed_count,
            'errors': errors[:10],  # 최대 10개 에러만 반환
            'vectordb_total': self.vectordb.get_count(),
            'bm25_total': len(self.bm25_index.documents)
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        인덱스 통계 조회

        Returns:
            통계 정보
        """
        return {
            'collection_name': self.collection_name,
            'vectordb_count': self.vectordb.get_count(),
            'bm25_count': len(self.bm25_index.documents),
            'embedding_dimension': self.embedder.get_embedding_dimension()
        }
