#!/usr/bin/env python3
"""Upgrade chunked dataset to v3 metadata schema."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upgrade chunk metadata to v3 schema")
    parser.add_argument("--input", required=True, help="Input chunks JSON (v2 schema)")
    parser.add_argument("--output", required=True, help="Output path for v3 schema JSON")
    parser.add_argument(
        "--pipeline-version",
        default="v3",
        help="Pipeline version tag recorded in metadata.common.pipeline_version",
    )
    parser.add_argument(
        "--chunk-version",
        type=int,
        default=1,
        help="Integer chunk schema/content version to record per chunk",
    )
    parser.add_argument(
        "--ingested-at",
        default=datetime.utcnow().isoformat(),
        help="ISO timestamp recorded in metadata.common.ingested_at",
    )
    parser.add_argument(
        "--dedup-report",
        default=None,
        help="Optional path to write deduplication summary JSON",
    )
    return parser.parse_args()


def normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    if "." in text:
        cleaned = text.replace(".", "-").strip("-")
        return cleaned or None
    return text


def safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_norm(doc_type: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    norm: Dict[str, Any] = {}

    law_id = meta.get("law_id")
    if law_id:
        norm["law_id"] = str(law_id)

    article = meta.get("article") or meta.get("article_num")
    if article:
        norm["article"] = str(article)

    case_num = meta.get("case_num")
    if case_num:
        norm["case_number"] = str(case_num)
    elif "결정" in (doc_type or "") and meta.get("decision_id"):
        norm["case_number"] = str(meta["decision_id"])

    decision_date = meta.get("sentence_date") or meta.get("final_date") or meta.get("interp_date")
    parsed_date = normalize_date(decision_date)
    if parsed_date:
        norm["decision_date"] = parsed_date
        year = safe_int(parsed_date[:4])
        if year:
            norm["decision_year"] = year

    court = meta.get("court_name") or meta.get("court_code")
    if court:
        norm["court"] = str(court)

    section = meta.get("section") or meta.get("section_type")
    if section:
        norm["section"] = str(section)

    label_type = meta.get("label_type")
    if label_type:
        norm["label_type"] = label_type

    sentence_type = meta.get("sentence_type")
    if sentence_type:
        norm["sentence_type"] = sentence_type

    return norm


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_dedup_stats(global_hash_refs: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    total_hashes = len(global_hash_refs)
    duplicate_hashes = {h: refs for h, refs in global_hash_refs.items() if len(refs) > 1}

    top_duplicates = sorted(duplicate_hashes.items(), key=lambda kv: len(kv[1]), reverse=True)
    sample = []
    for content_hash, refs in top_duplicates[:100]:
        doc_ids = sorted({ref["doc_id"] for ref in refs})
        sample.append(
            {
                "content_hash": content_hash,
                "count": len(refs),
                "doc_ids": doc_ids[:20],
            }
        )

    return {
        "unique_hashes": total_hashes,
        "duplicate_hash_count": len(duplicate_hashes),
        "duplicate_examples": sample,
    }


def upgrade_chunks(
    data: Dict[str, Any],
    pipeline_version: str,
    chunk_version: int,
    ingested_at: str,
) -> Dict[str, Any]:
    chunks = data.get("chunks", [])
    doc_counters: Dict[str, int] = defaultdict(int)
    doc_hashes: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    global_hash_refs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    upgraded_chunks: List[Dict[str, Any]] = []

    for chunk in chunks:
        content = chunk.get("content", "")
        old_meta = chunk.get("metadata", {})
        doc_id = old_meta.get("doc_id") or old_meta.get("original_doc_id") or "unknown_doc"
        doc_type = old_meta.get("type") or old_meta.get("doc_type") or "unknown_type"

        chunk_index = doc_counters[doc_id]
        doc_counters[doc_id] += 1

        new_chunk_id = f"{doc_id}__chunk_{chunk_index}"
        content_hash = sha256_text(content)

        dup_rank = doc_hashes[doc_id][content_hash]
        doc_hashes[doc_id][content_hash] += 1

        global_hash_refs[content_hash].append({"doc_id": doc_id, "chunk_index": chunk_index})

        common_meta = {
            "doc_type": doc_type,
            "doc_id": doc_id,
            "chunk_id": new_chunk_id,
            "chunk_index": chunk_index,
            "chunk_version": chunk_version,
            "split": old_meta.get("split"),
            "origin": {
                "original_doc_type": old_meta.get("original_doc_type", doc_type),
                "original_doc_id": old_meta.get("original_doc_id", doc_id),
            },
            "pipeline_version": pipeline_version,
            "ingested_at": ingested_at,
            "content_hash": content_hash,
            "length": len(content),
        }

        norm_meta = build_norm(doc_type, old_meta)

        drop_keys = {
            "doc_id",
            "split",
            "type",
            "original_doc_type",
            "original_doc_id",
        }
        type_meta = {k: v for k, v in old_meta.items() if k not in drop_keys}

        quality_meta = {
            "duplicate_rank": dup_rank,
            "is_duplicate": dup_rank > 0,
            "doc_duplicate_total": doc_hashes[doc_id][content_hash],
        }

        upgraded_chunks.append(
            {
                "content": content,
                "metadata": {
                    "common": common_meta,
                    "norm": norm_meta,
                    "type_meta": type_meta,
                    "quality": quality_meta,
                },
            }
        )

    new_metadata = dict(data.get("metadata", {}))
    new_metadata.update(
        {
            "schema_version": "v3",
            "pipeline_version": pipeline_version,
            "ingested_at": ingested_at,
        }
    )

    return {
        "metadata": new_metadata,
        "chunks": upgraded_chunks,
        "_dedup_stats": build_dedup_stats(global_hash_refs),
    }


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    upgraded = upgrade_chunks(
        data,
        pipeline_version=args.pipeline_version,
        chunk_version=args.chunk_version,
        ingested_at=args.ingested_at,
    )

    dedup_stats = upgraded.pop("_dedup_stats", None)

    output_path.write_text(json.dumps(upgraded, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.dedup_report and dedup_stats is not None:
        report_path = Path(args.dedup_report)
        report_path.write_text(json.dumps(dedup_stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Upgraded chunks saved to: {output_path}")
    if args.dedup_report:
        print(f"Dedup report saved to: {args.dedup_report}")


if __name__ == "__main__":
    main()

