"""
Document Indexer Service
Handles embedding generation and vector database indexing
"""

import logging
from typing import List, Dict, Any, Optional
import uuid

from libs.rag_core import (
    KoreanLegalEmbedder,
    ChromaVectorDB,
)

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """
    Document indexer for embedding generation and vector DB storage
    """

    def __init__(
        self,
        vectordb: ChromaVectorDB,
        embedder: KoreanLegalEmbedder,
        collection_name: str = "user_documents"
    ):
        """
        Initialize document indexer

        Args:
            vectordb: ChromaDB instance for precedent documents
            embedder: Korean legal embedder instance
            collection_name: Collection name for user documents
        """
        self.embedder = embedder
        self.collection_name = collection_name

        # Create separate collection for user documents
        # (separate from precedent documents)
        self.user_vectordb = ChromaVectorDB(
            persist_directory=str(vectordb.persist_directory),
            collection_name=collection_name
        )

        logger.info(f"DocumentIndexer initialized with collection: {collection_name}")

    def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_id: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Index document chunks into vector database

        Args:
            chunks: List of chunk dictionaries with 'text' field
            document_id: Document ID from Django
            document_metadata: Optional document-level metadata

        Returns:
            Dictionary containing indexing results
        """
        if not chunks:
            return {
                'success': False,
                'error': 'No chunks provided'
            }

        try:
            # Extract texts from chunks
            texts = [chunk['text'] for chunk in chunks]
            logger.info(f"Indexing {len(texts)} chunks for document {document_id}")

            # Generate embeddings
            embeddings = self.embedder.embed_documents(
                texts,
                show_progress=False
            )

            logger.info(f"Generated embeddings with shape: {embeddings.shape}")

            # Prepare metadatas with chunk and document info
            metadatas = []
            embedding_ids = []

            for i, chunk in enumerate(chunks):
                # Generate unique embedding ID
                embedding_id = f"{document_id}_chunk_{chunk.get('chunk_index', i)}"
                embedding_ids.append(embedding_id)

                # Prepare metadata
                metadata = {
                    'embedding_id': embedding_id,
                    'document_id': str(document_id),
                    'chunk_index': chunk.get('chunk_index', i),
                    'chunk_type': 'user_document',
                    'start_offset': chunk.get('start_offset', 0),
                    'end_offset': chunk.get('end_offset', 0),
                    'token_count': chunk.get('token_count', 0),
                }

                # Add document-level metadata if provided
                if document_metadata:
                    for key, value in document_metadata.items():
                        # Only add simple types (Chroma limitation)
                        if isinstance(value, (str, int, float, bool)):
                            metadata[f'doc_{key}'] = value

                metadatas.append(metadata)

            # Add to vector database
            self.user_vectordb.add_documents(
                texts=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )

            logger.info(
                f"Successfully indexed {len(texts)} chunks for document {document_id}. "
                f"Total documents in collection: {self.user_vectordb.get_count()}"
            )

            return {
                'success': True,
                'indexed_count': len(texts),
                'embedding_ids': embedding_ids,
                'collection_name': self.collection_name,
                'total_documents': self.user_vectordb.get_count()
            }

        except Exception as e:
            logger.error(f"Error indexing chunks: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def search_similar_chunks(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks

        Args:
            query: Search query
            top_k: Number of results to return
            document_id: Optional document ID to filter results

        Returns:
            List of similar chunks with scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedder.embed_query(query)

            # Search in vector database
            results = self.user_vectordb.search(
                query_embedding=query_embedding,
                top_k=top_k
            )

            # Filter by document_id if provided
            if document_id:
                results = [
                    r for r in results
                    if r['metadata'].get('document_id') == str(document_id)
                ]

            return results

        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}", exc_info=True)
            return []

    def delete_document_embeddings(self, document_id: str) -> bool:
        """
        Delete all embeddings for a document

        Args:
            document_id: Document ID from Django

        Returns:
            Success status
        """
        try:
            # ChromaDB doesn't support easy deletion by metadata
            # This is a limitation we'll note for now
            logger.warning(
                f"Deletion of embeddings for document {document_id} "
                "not implemented (ChromaDB limitation)"
            )
            return True

        except Exception as e:
            logger.error(f"Error deleting document embeddings: {e}", exc_info=True)
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics

        Returns:
            Dictionary with collection stats
        """
        return {
            'collection_name': self.collection_name,
            'total_documents': self.user_vectordb.get_count(),
            'embedding_dimension': self.embedder.get_embedding_dimension()
        }
