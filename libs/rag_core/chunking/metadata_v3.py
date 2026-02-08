"""Shared helpers for v3 chunk metadata formatting."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Tuple


def compute_content_hash(text: str) -> str:
    """Return a deterministic hash for deduplication."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_date(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    collapsed = "".join(text.split())
    collapsed = collapsed.replace("/", "-").replace(".", "-").strip("-")

    if not collapsed:
        return None

    lowered = collapsed.lower()
    if lowered in {"기타", "없음", "null", "none", "n/a"}:
        return None

    if collapsed.isdigit():
        if len(collapsed) == 8:
            return f"{collapsed[:4]}-{collapsed[4:6]}-{collapsed[6:8]}"
        if len(collapsed) == 6:
            return f"{collapsed[:4]}-{collapsed[4:6]}-01"
        if len(collapsed) == 4:
            return f"{collapsed}-01-01"
        return None

    if "-" in collapsed:
        parts = [part for part in collapsed.split("-") if part]
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            year, month, day = parts
            day = "01" if day == "00" else day
            return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
        if len(parts) == 2 and all(part.isdigit() for part in parts):
            year, month = parts
            return f"{year.zfill(4)}-{month.zfill(2)}-01"
        return None

    return None


def safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_identity(meta: Dict[str, Any]) -> Tuple[str, str]:
    """Return (doc_id, doc_type) inferred from raw metadata."""

    doc_id = meta.get("doc_id") or meta.get("original_doc_id") or "unknown_doc"
    doc_type = meta.get("type") or meta.get("doc_type") or "unknown_type"
    return str(doc_id), str(doc_type)


def build_norm_metadata(doc_type: str, meta: Dict[str, Any]) -> Dict[str, Any]:
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
    elif "결정" in doc_type and meta.get("decision_id"):
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


def build_type_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    drop_keys = {
        "doc_id",
        "split",
        "type",
        "original_doc_type",
        "original_doc_id",
    }
    return {k: v for k, v in meta.items() if k not in drop_keys}


def format_chunk_metadata_v3(
    raw_meta: Dict[str, Any],
    *,
    doc_id: str,
    doc_type: str,
    split: str | None,
    chunk_index: int,
    chunk_version: int,
    pipeline_version: str,
    ingested_at: str,
    content_hash: str,
    content_length: int,
    duplicate_rank: int,
    doc_duplicate_total: int,
) -> Dict[str, Any]:
    chunk_id = f"{doc_id}__chunk_{chunk_index}"

    common = {
        "doc_type": doc_type,
        "doc_id": doc_id,
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "chunk_version": chunk_version,
        "split": split,
        "origin": {
            "original_doc_type": raw_meta.get("original_doc_type", doc_type),
            "original_doc_id": raw_meta.get("original_doc_id", doc_id),
        },
        "pipeline_version": pipeline_version,
        "ingested_at": ingested_at,
        "content_hash": content_hash,
        "length": content_length,
    }

    quality = {
        "duplicate_rank": duplicate_rank,
        "is_duplicate": duplicate_rank > 0,
        "doc_duplicate_total": doc_duplicate_total,
    }

    return {
        "common": common,
        "norm": build_norm_metadata(doc_type, raw_meta),
        "type_meta": build_type_meta(raw_meta),
        "quality": quality,
    }


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
