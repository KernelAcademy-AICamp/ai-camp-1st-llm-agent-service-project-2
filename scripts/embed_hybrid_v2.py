#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
하이브리드 임베딩 스크립트 V2
Dense (snowflake-arctic-embed) + Sparse (SPLADE) 임베딩

Ubuntu GPU 서버에서 실행

Usage:
    # 전체 실행
    python embed_hybrid_v2.py --input chunks_v2.json

    # 테스트 (1000개만)
    python embed_hybrid_v2.py --input chunks_v2.json --limit 1000

    # 드라이런
    python embed_hybrid_v2.py --input chunks_v2.json --dry-run
"""

import sys
import os
import json
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass

import torch
from tqdm import tqdm

# ============================================================
# Configuration
# ============================================================

@dataclass
class Config:
    # Dense Embedding
    dense_model: str = "dragonkue/snowflake-arctic-embed-l-v2.0-ko"
    dense_dim: int = 1024

    # Sparse Embedding (SPLADE)
    splade_model: str = "yjoonjang/splade-ko-v1"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "law_documents_v2"

    # Processing
    batch_size: int = 32
    max_length: int = 512


# ============================================================
# SPLADE Encoder
# ============================================================

class SPLADEEncoder:
    """SPLADE Sparse Encoder"""

    def __init__(self, model_name: str, device: str = None, max_length: int = 512):
        from transformers import AutoModelForMaskedLM, AutoTokenizer

        self.model_name = model_name
        self.max_length = max_length

        # Device selection
        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

        print(f"[SPLADE] Loading model: {model_name}")
        print(f"[SPLADE] Device: {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForMaskedLM.from_pretrained(model_name)
        self.model.eval()
        self.model.to(self.device)

        self.vocab_size = self.tokenizer.vocab_size
        print(f"[SPLADE] Loaded. Vocab size: {self.vocab_size}")

    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[Tuple[List[int], List[float]]]:
        """Batch encode texts to SPLADE sparse vectors"""
        results = []

        iterator = range(0, len(texts), batch_size)
        if show_progress:
            iterator = tqdm(iterator, desc="SPLADE encoding", unit="batch")

        for i in iterator:
            batch_texts = texts[i:i + batch_size]

            with torch.no_grad():
                inputs = self.tokenizer(
                    batch_texts,
                    return_tensors="pt",
                    max_length=self.max_length,
                    truncation=True,
                    padding=True
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                output = self.model(**inputs)
                logits = output.logits
                attention_mask = inputs["attention_mask"]

                # SPLADE sparse vector: max pooling + ReLU + log
                sparse_vecs = torch.max(
                    torch.log(1 + torch.relu(logits)) * attention_mask.unsqueeze(-1),
                    dim=1
                )[0]

                # Extract non-zero indices and values for each vector
                for vec in sparse_vecs:
                    non_zero_mask = vec > 0
                    indices = torch.nonzero(non_zero_mask).squeeze(-1).cpu().tolist()
                    values = vec[non_zero_mask].cpu().tolist()

                    if isinstance(indices, int):
                        indices = [indices]
                        values = [values]

                    results.append((indices, values))

        return results


# ============================================================
# Dense Encoder
# ============================================================

class DenseEncoder:
    """Dense Embedding Encoder using sentence-transformers"""

    def __init__(self, model_name: str, device: str = None):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name

        # Device selection
        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

        print(f"[Dense] Loading model: {model_name}")
        print(f"[Dense] Device: {self.device}")

        self.model = SentenceTransformer(model_name, device=self.device)
        self.dim = self.model.get_sentence_embedding_dimension()
        print(f"[Dense] Loaded. Dimension: {self.dim}")

    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[List[float]]:
        """Batch encode texts to dense vectors"""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        return embeddings.tolist()


# ============================================================
# Qdrant Manager
# ============================================================

class QdrantManager:
    """Qdrant Vector DB Manager"""

    def __init__(self, url: str, collection_name: str, dense_dim: int):
        from qdrant_client import QdrantClient
        from qdrant_client.models import (
            Distance, VectorParams, SparseVectorParams,
            SparseIndexParams, VectorsConfig
        )

        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.dense_dim = dense_dim

        print(f"[Qdrant] Connected to {url}")

    def create_collection(self, recreate: bool = False):
        """Create hybrid collection with dense + sparse vectors"""
        from qdrant_client.models import (
            Distance, VectorParams, SparseVectorParams,
            SparseIndexParams, VectorsConfig
        )

        # Check if collection exists
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if exists:
            if recreate:
                print(f"[Qdrant] Deleting existing collection: {self.collection_name}")
                self.client.delete_collection(self.collection_name)
            else:
                print(f"[Qdrant] Collection already exists: {self.collection_name}")
                return False

        print(f"[Qdrant] Creating collection: {self.collection_name}")
        print(f"  - Dense vector dim: {self.dense_dim}")
        print(f"  - Sparse vector: SPLADE")

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "dense": VectorParams(
                    size=self.dense_dim,
                    distance=Distance.COSINE
                )
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False)
                )
            }
        )

        print(f"[Qdrant] Collection created successfully")
        return True

    def upsert_points(
        self,
        ids: List[int],
        dense_vectors: List[List[float]],
        sparse_vectors: List[Tuple[List[int], List[float]]],
        payloads: List[Dict[str, Any]],
        batch_size: int = 100
    ):
        """Upsert points with dense and sparse vectors"""
        from qdrant_client.models import PointStruct, SparseVector

        total = len(ids)
        for i in tqdm(range(0, total, batch_size), desc="Upserting to Qdrant"):
            batch_ids = ids[i:i + batch_size]
            batch_dense = dense_vectors[i:i + batch_size]
            batch_sparse = sparse_vectors[i:i + batch_size]
            batch_payloads = payloads[i:i + batch_size]

            points = []
            for j, (pid, dense, sparse, payload) in enumerate(
                zip(batch_ids, batch_dense, batch_sparse, batch_payloads)
            ):
                sparse_indices, sparse_values = sparse

                point = PointStruct(
                    id=pid,
                    vector={
                        "dense": dense,
                        "sparse": SparseVector(
                            indices=sparse_indices,
                            values=sparse_values
                        )
                    },
                    payload=payload
                )
                points.append(point)

            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    def get_collection_info(self):
        """Get collection statistics"""
        info = self.client.get_collection(self.collection_name)
        return {
            'name': self.collection_name,
            'points_count': info.points_count,
            'vectors_count': info.vectors_count,
            'status': info.status
        }


# ============================================================
# Main Embedding Pipeline
# ============================================================

def embed_chunks(
    chunks: List[Dict[str, Any]],
    config: Config,
    dry_run: bool = False,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Main embedding pipeline

    Args:
        chunks: List of chunk dictionaries
        config: Configuration object
        dry_run: If True, skip Qdrant operations
        limit: Limit number of chunks to process

    Returns:
        Statistics dictionary
    """
    if limit:
        chunks = chunks[:limit]
        print(f"\n[Limit] Processing only {limit} chunks")

    total_chunks = len(chunks)
    print(f"\n{'='*60}")
    print(f"Embedding Pipeline Start")
    print(f"{'='*60}")
    print(f"Total chunks: {total_chunks:,}")
    print(f"Dense model: {config.dense_model}")
    print(f"SPLADE model: {config.splade_model}")
    print(f"Batch size: {config.batch_size}")

    # Extract texts
    texts = [c.get('content', '') for c in chunks]
    payloads = [c.get('metadata', {}) for c in chunks]

    # Generate IDs
    ids = list(range(1, total_chunks + 1))

    # Initialize encoders
    print("\n[1/4] Initializing encoders...")
    dense_encoder = DenseEncoder(config.dense_model)
    splade_encoder = SPLADEEncoder(config.splade_model)

    # Dense encoding
    print("\n[2/4] Dense encoding...")
    start_time = time.time()
    dense_vectors = dense_encoder.encode_batch(
        texts,
        batch_size=config.batch_size,
        show_progress=True
    )
    dense_time = time.time() - start_time
    print(f"  Dense encoding completed in {dense_time:.1f}s")

    # SPLADE encoding
    print("\n[3/4] SPLADE sparse encoding...")
    start_time = time.time()
    sparse_vectors = splade_encoder.encode_batch(
        texts,
        batch_size=config.batch_size,
        show_progress=True
    )
    sparse_time = time.time() - start_time
    print(f"  SPLADE encoding completed in {sparse_time:.1f}s")

    # Store in Qdrant
    if dry_run:
        print("\n[4/4] Dry run - skipping Qdrant storage")
    else:
        print("\n[4/4] Storing in Qdrant...")
        qdrant = QdrantManager(
            url=config.qdrant_url,
            collection_name=config.collection_name,
            dense_dim=config.dense_dim
        )

        # Create collection
        qdrant.create_collection(recreate=True)

        # Upsert points
        start_time = time.time()
        qdrant.upsert_points(
            ids=ids,
            dense_vectors=dense_vectors,
            sparse_vectors=sparse_vectors,
            payloads=payloads,
            batch_size=100
        )
        store_time = time.time() - start_time
        print(f"  Storage completed in {store_time:.1f}s")

        # Get collection info
        info = qdrant.get_collection_info()
        print(f"\n[Qdrant Collection Info]")
        print(f"  Name: {info['name']}")
        print(f"  Points: {info['points_count']:,}")
        print(f"  Status: {info['status']}")

    # Statistics
    stats = {
        'total_chunks': total_chunks,
        'dense_dim': config.dense_dim,
        'dense_encoding_time': dense_time,
        'sparse_encoding_time': sparse_time,
        'collection_name': config.collection_name,
        'completed_at': datetime.now().isoformat()
    }

    return stats


def main():
    parser = argparse.ArgumentParser(description='Hybrid Embedding V2')
    parser.add_argument('--input', type=str, required=True,
                       help='Input chunks JSON file')
    parser.add_argument('--collection', type=str, default='law_documents_v2',
                       help='Qdrant collection name')
    parser.add_argument('--qdrant-url', type=str, default='http://localhost:6333',
                       help='Qdrant URL')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='Batch size for encoding')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of chunks to process')
    parser.add_argument('--dry-run', action='store_true',
                       help='Skip Qdrant storage')
    parser.add_argument('--dense-model', type=str,
                       default='dragonkue/snowflake-arctic-embed-l-v2.0-ko',
                       help='Dense embedding model')
    parser.add_argument('--splade-model', type=str,
                       default='yjoonjang/splade-ko-v1',
                       help='SPLADE model')

    args = parser.parse_args()

    # Load chunks
    print(f"Loading chunks from: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict) and 'chunks' in data:
        chunks = data['chunks']
        metadata = data.get('metadata', {})
        print(f"Loaded {len(chunks):,} chunks")
        print(f"Source metadata: {metadata}")
    else:
        chunks = data
        print(f"Loaded {len(chunks):,} chunks (raw format)")

    # Config
    config = Config(
        dense_model=args.dense_model,
        splade_model=args.splade_model,
        qdrant_url=args.qdrant_url,
        collection_name=args.collection,
        batch_size=args.batch_size
    )

    # Run embedding
    stats = embed_chunks(
        chunks=chunks,
        config=config,
        dry_run=args.dry_run,
        limit=args.limit
    )

    print("\n" + "=" * 60)
    print("Embedding Complete!")
    print("=" * 60)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Save stats
    stats_file = Path(args.input).stem + '_embed_stats.json'
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"\nStats saved to: {stats_file}")


if __name__ == "__main__":
    main()
