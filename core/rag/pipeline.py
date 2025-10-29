"""
Complete RAG pipeline orchestration with error handling.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..embeddings import get_embedder
from ..models import get_llm
from .chunker import create_chunker
from .vector_store import get_vector_store
from .retriever import create_retriever


# Custom exceptions for better error handling
class RAGPipelineError(Exception):
    """Base exception for RAG pipeline errors."""
    pass


class ComponentInitializationError(RAGPipelineError):
    """Raised when a component fails to initialize."""
    pass


class IndexingError(RAGPipelineError):
    """Raised when document indexing fails."""
    pass


class RetrievalError(RAGPipelineError):
    """Raised when document retrieval fails."""
    pass


class GenerationError(RAGPipelineError):
    """Raised when answer generation fails."""
    pass


class RAGPipeline:
    """Complete RAG pipeline for document processing and retrieval."""

    def __init__(self, config: Dict[str, Any], verbose: bool = True):
        """
        Initialize RAG pipeline with configuration.

        Args:
            config: Configuration dictionary
            verbose: Whether to print progress messages

        Raises:
            ComponentInitializationError: If any component fails to initialize
        """
        self.config = config
        self.verbose = verbose

        # Setup logging
        self.logger = logging.getLogger('RAGPipeline')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO if verbose else logging.WARNING)

        # Initialize components with error handling
        try:
            self._initialize_components()
        except Exception as e:
            raise ComponentInitializationError(f"Failed to initialize pipeline: {str(e)}") from e

    def _initialize_components(self):
        """Initialize all pipeline components from config with error handling."""
        if self.verbose:
            print("Initializing RAG pipeline components...")

        # Initialize chunker
        try:
            self.chunker = create_chunker(self.config.get('chunking', {}))
            strategy = self.config.get('chunking', {}).get('strategy', 'fixed')
            if self.verbose:
                print(f"✓ Chunker initialized: {strategy}")
            self.logger.info(f"Chunker initialized with strategy: {strategy}")
        except Exception as e:
            error_msg = f"Failed to initialize chunker: {str(e)}"
            self.logger.error(error_msg)
            raise ComponentInitializationError(error_msg) from e

        # Initialize embedder
        try:
            self.embedder = get_embedder(self.config.get('embedding', {}))
            emb_type = self.config.get('embedding', {}).get('type', 'openai')
            emb_model = self.config.get('embedding', {}).get('model', 'unknown')
            if self.verbose:
                print(f"✓ Embedder initialized: {emb_type} ({emb_model})")
            self.logger.info(f"Embedder initialized: {emb_type} with model {emb_model}")
        except Exception as e:
            error_msg = f"Failed to initialize embedder: {str(e)}"
            self.logger.error(error_msg)
            if "API key" in str(e) or "api_key" in str(e).lower():
                error_msg += "\n💡 Hint: Check your .env file or config for API keys"
            raise ComponentInitializationError(error_msg) from e

        # Initialize vector store
        try:
            self.vector_store = get_vector_store(self.config.get('vector_store', {}))
            store_type = self.config.get('vector_store', {}).get('type', 'faiss')
            if self.verbose:
                print(f"✓ Vector store initialized: {store_type}")
            self.logger.info(f"Vector store initialized: {store_type}")
        except Exception as e:
            error_msg = f"Failed to initialize vector store: {str(e)}"
            self.logger.error(error_msg)
            if "not installed" in str(e):
                error_msg += f"\n💡 Hint: Install required library with pip"
            raise ComponentInitializationError(error_msg) from e

        # Initialize retriever
        try:
            self.retriever = create_retriever(
                self.config.get('retrieval', {}),
                vector_store=self.vector_store,
                embedder=self.embedder
            )
            method = self.config.get('retrieval', {}).get('method', 'similarity')
            if self.verbose:
                print(f"✓ Retriever initialized: {method}")
            self.logger.info(f"Retriever initialized with method: {method}")
        except Exception as e:
            error_msg = f"Failed to initialize retriever: {str(e)}"
            self.logger.error(error_msg)
            raise ComponentInitializationError(error_msg) from e

        # Initialize LLM
        try:
            self.llm = get_llm(self.config.get('generation', {}))
            provider = self.config.get('generation', {}).get('provider', 'openai')
            model = self.config.get('generation', {}).get('model', 'unknown')
            if self.verbose:
                print(f"✓ LLM initialized: {provider} ({model})")
            self.logger.info(f"LLM initialized: {provider} with model {model}")
        except Exception as e:
            error_msg = f"Failed to initialize LLM: {str(e)}"
            self.logger.error(error_msg)
            if "API key" in str(e) or "api_key" in str(e).lower():
                error_msg += "\n💡 Hint: Check your .env file or config for API keys"
            raise ComponentInitializationError(error_msg) from e

        self.documents_indexed = False

    def index_documents(self, documents: List[str], metadata: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Index documents into the vector store.

        Args:
            documents: List of document texts
            metadata: Optional metadata for each document

        Returns:
            Indexing statistics

        Raises:
            IndexingError: If indexing fails
        """
        if not documents:
            raise IndexingError("No documents provided for indexing")

        if self.verbose:
            print(f"\nIndexing {len(documents)} documents...")

        self.logger.info(f"Starting indexing of {len(documents)} documents")

        start_time = time.time()
        stats = {
            'num_documents': len(documents),
            'total_chunks': 0,
            'avg_chunk_size': 0,
            'indexing_time': 0
        }

        try:
            # Process each document
            all_chunks = []
            all_metadata = []

            for doc_idx, doc in enumerate(documents):
                try:
                    # Chunk document
                    chunks = self.chunker.chunk(doc)

                    # Add document index to metadata
                    for chunk in chunks:
                        chunk_metadata = chunk.get('metadata', {})
                        chunk_metadata['doc_index'] = doc_idx
                        if metadata and doc_idx < len(metadata):
                            chunk_metadata.update(metadata[doc_idx])

                        all_chunks.append(chunk['content'])
                        all_metadata.append(chunk_metadata)

                    if self.verbose and (doc_idx + 1) % 10 == 0:
                        print(f"  Processed {doc_idx + 1}/{len(documents)} documents...")

                except Exception as e:
                    self.logger.warning(f"Failed to chunk document {doc_idx}: {str(e)}")
                    # Continue with next document
                    continue

            if not all_chunks:
                raise IndexingError("No chunks generated from documents. All documents may be empty or invalid.")

            stats['total_chunks'] = len(all_chunks)
            stats['avg_chunk_size'] = sum(len(c) for c in all_chunks) / len(all_chunks) if all_chunks else 0

            # Generate embeddings in batches
            if self.verbose:
                print(f"  Generating embeddings for {len(all_chunks)} chunks...")

            self.logger.info(f"Generating embeddings for {len(all_chunks)} chunks")

            try:
                embeddings = self.embedder.embed_batch(all_chunks, batch_size=32)
            except Exception as e:
                error_msg = f"Failed to generate embeddings: {str(e)}"
                self.logger.error(error_msg)
                if "rate limit" in str(e).lower():
                    error_msg += "\n💡 Hint: API rate limit exceeded. Wait a moment and try again."
                elif "quota" in str(e).lower():
                    error_msg += "\n💡 Hint: API quota exceeded. Check your API usage."
                raise IndexingError(error_msg) from e

            # Add to vector store
            if self.verbose:
                print("  Adding to vector store...")

            try:
                self.vector_store.add(all_chunks, embeddings, all_metadata)
            except Exception as e:
                error_msg = f"Failed to add to vector store: {str(e)}"
                self.logger.error(error_msg)
                raise IndexingError(error_msg) from e

            # Update retriever if it's hybrid (needs documents for BM25)
            if hasattr(self.retriever, 'add_documents'):
                try:
                    self.retriever.add_documents(all_chunks)
                except Exception as e:
                    self.logger.warning(f"Failed to update retriever documents: {str(e)}")

            self.documents_indexed = True
            stats['indexing_time'] = time.time() - start_time

            if self.verbose:
                print(f"✓ Indexing complete: {stats['total_chunks']} chunks in {stats['indexing_time']:.2f}s")

            self.logger.info(f"Indexing completed: {stats['total_chunks']} chunks in {stats['indexing_time']:.2f}s")

            return stats

        except IndexingError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during indexing: {str(e)}"
            self.logger.error(error_msg)
            raise IndexingError(error_msg) from e

    def query(self, query: str, k: int = None) -> Dict[str, Any]:
        """
        Query the RAG system.

        Args:
            query: User query
            k: Number of documents to retrieve (overrides config)

        Returns:
            Query response with answer and metadata

        Raises:
            ValueError: If no documents indexed
            RetrievalError: If retrieval fails
            GenerationError: If generation fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not self.documents_indexed:
            raise ValueError("No documents indexed. Call index_documents() or load_index() first.")

        start_time = time.time()

        # Use k from config if not provided
        if k is None:
            k = self.config.get('retrieval', {}).get('top_k', 5)

        self.logger.info(f"Processing query: {query[:100]}")

        # Retrieve relevant documents with timing and error handling
        try:
            if self.verbose:
                print(f"\nRetrieving {k} documents for query: {query[:50]}...")

            retrieval_start = time.time()
            retrieved_docs = self.retriever.retrieve(query, k=k)
            retrieval_time = time.time() - retrieval_start

            if not retrieved_docs:
                self.logger.warning("No documents retrieved for query")
                retrieved_docs = []

            self.logger.info(f"Retrieved {len(retrieved_docs)} documents in {retrieval_time:.2f}s")

        except Exception as e:
            error_msg = f"Failed to retrieve documents: {str(e)}"
            self.logger.error(error_msg)
            raise RetrievalError(error_msg) from e

        # Extract content from retrieved documents
        context = [doc['content'] for doc in retrieved_docs] if retrieved_docs else []

        if not context:
            self.logger.warning("No context available for generation")

        # Generate response with timing and error handling
        try:
            if self.verbose:
                print("Generating response...")

            generation_start = time.time()
            response = self.llm.generate_with_context(query, context)
            generation_time = time.time() - generation_start

            self.logger.info(f"Generated response in {generation_time:.2f}s")

        except Exception as e:
            error_msg = f"Failed to generate response: {str(e)}"
            self.logger.error(error_msg)
            if "rate limit" in str(e).lower():
                error_msg += "\n💡 Hint: API rate limit exceeded. Wait a moment and try again."
            elif "quota" in str(e).lower():
                error_msg += "\n💡 Hint: API quota exceeded. Check your API usage."
            elif "context length" in str(e).lower():
                error_msg += "\n💡 Hint: Context too long. Try reducing top_k or chunk_size."
            raise GenerationError(error_msg) from e

        # Prepare result
        result = {
            'query': query,
            'answer': response,
            'sources': retrieved_docs,  # Also add 'sources' alias for compatibility
            'retrieved_documents': retrieved_docs,
            'num_retrieved': len(retrieved_docs),
            'response_time': time.time() - start_time,
            'retrieval_time': retrieval_time,
            'generation_time': generation_time,
            'config': {
                'chunking_strategy': self.config.get('chunking', {}).get('strategy'),
                'embedding_model': self.config.get('embedding', {}).get('model'),
                'retrieval_method': self.config.get('retrieval', {}).get('method'),
                'generation_model': self.config.get('generation', {}).get('model'),
            }
        }

        if self.verbose:
            print(f"✓ Response generated in {result['response_time']:.2f}s")

        self.logger.info(f"Query completed in {result['response_time']:.2f}s")

        return result

    def batch_query(self, queries: List[str], k: int = None) -> List[Dict[str, Any]]:
        """
        Process multiple queries.

        Args:
            queries: List of queries
            k: Number of documents to retrieve per query

        Returns:
            List of query results
        """
        results = []
        for i, query in enumerate(queries):
            if self.verbose:
                print(f"\nProcessing query {i+1}/{len(queries)}")
            result = self.query(query, k=k)
            results.append(result)
        return results

    def save_index(self, path: str):
        """
        Save the vector store index.

        Args:
            path: Directory path to save the index
        """
        Path(path).mkdir(parents=True, exist_ok=True)

        # Save vector store
        self.vector_store.save(path)

        # Save config
        config_path = Path(path) / "pipeline_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

        if self.verbose:
            print(f"✓ Index saved to {path}")

    def load_index(self, path: str):
        """
        Load a saved vector store index.

        Args:
            path: Directory path to load the index from
        """
        # Load vector store
        self.vector_store.load(path)

        # Load config if exists
        config_path = Path(path) / "pipeline_config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                # You might want to validate or merge configs here

        self.documents_indexed = True

        if self.verbose:
            print(f"✓ Index loaded from {path}")

    def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Search for relevant documents without generation.

        Args:
            query: Search query
            top_k: Number of documents to retrieve

        Returns:
            List of retrieved documents with scores
        """
        if not self.documents_indexed:
            raise ValueError("No documents indexed. Call index_documents() or load_index() first.")

        # Use top_k from config if not provided
        if top_k is None:
            top_k = self.config.get('retrieval', {}).get('top_k', 5)

        # Retrieve documents
        retrieved_docs = self.retriever.retrieve(query, k=top_k)

        return retrieved_docs

    def evaluate(self, test_queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate the pipeline on test queries.

        Args:
            test_queries: List of dicts with 'query' and 'expected_answer' keys

        Returns:
            Evaluation metrics
        """
        if self.verbose:
            print(f"\nEvaluating on {len(test_queries)} queries...")

        total_time = 0
        results = []

        for test_case in test_queries:
            result = self.query(test_case['query'])
            total_time += result['response_time']
            results.append(result)

        # Calculate metrics
        metrics = {
            'num_queries': len(test_queries),
            'avg_response_time': total_time / len(test_queries),
            'avg_retrieved_docs': sum(r['num_retrieved'] for r in results) / len(results),
        }

        if self.verbose:
            print(f"✓ Evaluation complete")
            print(f"  Average response time: {metrics['avg_response_time']:.2f}s")
            print(f"  Average retrieved docs: {metrics['avg_retrieved_docs']:.1f}")

        return metrics