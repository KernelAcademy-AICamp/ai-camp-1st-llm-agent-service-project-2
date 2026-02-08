#!/usr/bin/env python3
"""Chunking pipeline (v3 schema)."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from tqdm import tqdm

from libs.rag_core.chunking.metadata_v3 import (
    build_dedup_stats,
    compute_content_hash,
    extract_identity,
    format_chunk_metadata_v3,
)
from scripts.criminal_law_data_loader import CriminalLawDataLoader
from libs.rag_core.chunking.legal_chunker_v2 import get_chunker_v2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chunk documents and emit v3 schema")
    parser.add_argument("--base-path", type=str, default=None, help="Custom data root")
    parser.add_argument(
        "--split",
        type=str,
        default="both",
        choices=["training", "validation", "both"],
        help="Dataset split",
    )
    parser.add_argument("--max-per-type", type=int, default=None, help="Optional cap per type")
    parser.add_argument("--output", type=str, default="chunks_v3.json", help="Output filename")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: data/processed)",
    )
    parser.add_argument("--pipeline-version", type=str, default="v3", help="Pipeline tag")
    parser.add_argument("--chunk-version", type=int, default=1, help="Chunk schema version")
    parser.add_argument(
        "--ingested-at",
        type=str,
        default=datetime.utcnow().isoformat(),
        help="Timestamp recorded in metadata",
    )
    parser.add_argument(
        "--dedup-report",
        type=str,
        default=None,
        help="Optional dedup report json path",
    )
    return parser.parse_args()


def chunk_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chunks = []
    for doc in tqdm(documents, desc="Chunking"):
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})
        doc_type = metadata.get("type", "")

        if not content.strip():
            continue

        chunker = get_chunker_v2(doc_type)

        try:
            parts = chunker.chunk(content, metadata)
            for part in parts:
                part_meta = part.get("metadata", {})
                part_meta.setdefault("original_doc_type", doc_type)
                part_meta.setdefault("original_doc_id", metadata.get("doc_id", ""))
            chunks.extend(parts)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Warning: failed to chunk document {metadata.get('doc_id', 'unknown')}: {exc}")
    return chunks


def convert_to_v3(
    chunks: List[Dict[str, Any]],
    *,
    pipeline_version: str,
    chunk_version: int,
    ingested_at: str,
) -> Dict[str, Any]:
    doc_counters = defaultdict(int)
    doc_hash_stats = defaultdict(lambda: defaultdict(int))
    global_hash_refs = defaultdict(list)

    converted = []
    for chunk in chunks:
        content = chunk.get("content", "")
        raw_meta = chunk.get("metadata", {})
        doc_id, doc_type = extract_identity(raw_meta)

        chunk_index = doc_counters[doc_id]
        doc_counters[doc_id] += 1

        content_hash = compute_content_hash(content)
        dup_rank = doc_hash_stats[doc_id][content_hash]
        doc_hash_stats[doc_id][content_hash] += 1
        global_hash_refs[content_hash].append({"doc_id": doc_id, "chunk_index": chunk_index})

        formatted_meta = format_chunk_metadata_v3(
            raw_meta,
            doc_id=doc_id,
            doc_type=doc_type,
            split=raw_meta.get("split"),
            chunk_index=chunk_index,
            chunk_version=chunk_version,
            pipeline_version=pipeline_version,
            ingested_at=ingested_at,
            content_hash=content_hash,
            content_length=len(content),
            duplicate_rank=dup_rank,
            doc_duplicate_total=doc_hash_stats[doc_id][content_hash],
        )

        converted.append({"content": content, "metadata": formatted_meta})

    dedup_stats = build_dedup_stats(global_hash_refs)
    return {"chunks": converted, "dedup_stats": dedup_stats}


def main() -> None:
    args = parse_args()

    loader = CriminalLawDataLoader(base_path=args.base_path)

    source_types = ["법령", "판결문", "결정례", "해석례"]
    labeled_types = [
        "법령_QA",
        "판결문_QA",
        "판결문_SUM",
        "결정례_QA",
        "결정례_SUM",
        "해석례_QA",
        "해석례_SUM",
    ]

    splits = [args.split] if args.split != "both" else ["training", "validation"]

    stats = {}
    all_chunks: List[Dict[str, Any]] = []

    for split in splits:
        print("=" * 40)
        print(f"Processing {split.upper()} split")
        print("=" * 40)

        source_docs = loader.load_source_data(
            types=source_types,
            max_per_type=args.max_per_type,
            split=split,
        )
        print(f"  Source docs: {len(source_docs):,}")
        if source_docs:
            source_chunks = chunk_documents(source_docs)
            print(f"  Source chunks: {len(source_chunks):,}")
            all_chunks.extend(source_chunks)
            stats[f"{split}_source_docs"] = len(source_docs)
            stats[f"{split}_source_chunks"] = len(source_chunks)

        labeled_docs = loader.load_labeled_data(
            types=labeled_types,
            max_per_type=args.max_per_type,
            split=split,
        )
        print(f"  Labeled docs: {len(labeled_docs):,}")
        if labeled_docs:
            labeled_chunks = chunk_documents(labeled_docs)
            print(f"  Labeled chunks: {len(labeled_chunks):,}")
            all_chunks.extend(labeled_chunks)
            stats[f"{split}_labeled_docs"] = len(labeled_docs)
            stats[f"{split}_labeled_chunks"] = len(labeled_chunks)

    print("=" * 60)
    print(f"Total chunks (raw): {len(all_chunks):,}")

    converted = convert_to_v3(
        all_chunks,
        pipeline_version=args.pipeline_version,
        chunk_version=args.chunk_version,
        ingested_at=args.ingested_at,
    )

    chunks_v3 = converted["chunks"]
    dedup_stats = converted["dedup_stats"]

    print(f"Total chunks (v3): {len(chunks_v3):,}")

    type_counts = defaultdict(int)
    for chunk in chunks_v3:
        doc_type = chunk.get("metadata", {}).get("common", {}).get("doc_type", "unknown")
        type_counts[doc_type] += 1

    output_dir = Path(args.output_dir) if args.output_dir else Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / args.output

    metadata = {
        "created_at": datetime.utcnow().isoformat(),
        "split": args.split,
        "max_per_type": args.max_per_type,
        "total_chunks": len(chunks_v3),
        "stats": stats,
        "type_counts": dict(type_counts),
        "schema_version": "v3",
        "pipeline_version": args.pipeline_version,
        "ingested_at": args.ingested_at,
    }

    payload = {"metadata": metadata, "chunks": chunks_v3}

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved chunks to {output_path}")

    if args.dedup_report:
        report_path = Path(args.dedup_report)
        report_path.write_text(json.dumps(dedup_stats, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved dedup stats to {report_path}")


if __name__ == "__main__":
    main()

