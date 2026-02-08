#!/usr/bin/env python3
"""Validate v3 chunk metadata schema."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


REQUIRED_TOP_LEVEL = {"common", "norm", "type_meta", "quality"}
REQUIRED_COMMON = {
    "doc_type",
    "doc_id",
    "chunk_id",
    "chunk_index",
    "chunk_version",
    "split",
    "origin",
    "pipeline_version",
    "ingested_at",
    "content_hash",
    "length",
}
REQUIRED_ORIGIN = {"original_doc_type", "original_doc_id"}
ISO_FIELDS = {"decision_date": "%Y-%m-%d"}
INT_FIELDS = {"decision_year"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate chunks_v3 metadata")
    parser.add_argument("--input", required=True, help="chunks_v3 JSON path")
    parser.add_argument("--report", default=None, help="Optional JSON report output path")
    return parser.parse_args()


def is_iso_date(value: Any) -> bool:
    if not value:
        return False
    try:
        datetime.strptime(str(value), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_chunk(chunk: Dict[str, Any], idx: int, issues: Dict[str, list]) -> None:
    meta = chunk.get("metadata")
    if not isinstance(meta, dict):
        issues["missing_metadata"].append(idx)
        return

    missing_sections = REQUIRED_TOP_LEVEL - meta.keys()
    if missing_sections:
        issues["missing_sections"].append({"index": idx, "missing": sorted(missing_sections)})
        return

    common = meta.get("common", {})
    missing_common = REQUIRED_COMMON - common.keys()
    if missing_common:
        issues["missing_common"].append({"index": idx, "missing": sorted(missing_common)})

    origin = common.get("origin", {}) if isinstance(common, dict) else {}
    missing_origin = REQUIRED_ORIGIN - origin.keys()
    if missing_origin:
        issues["missing_origin"].append({"index": idx, "missing": sorted(missing_origin)})

    ingested_at = common.get("ingested_at")
    if ingested_at:
        try:
            datetime.fromisoformat(ingested_at.replace("Z", "+00:00"))
        except ValueError:
            issues["invalid_ingested_at"].append({"index": idx, "value": ingested_at})

    norm = meta.get("norm", {})
    for field in ISO_FIELDS:
        if norm.get(field) and not is_iso_date(norm[field]):
            issues["invalid_dates"].append({"index": idx, "field": field, "value": norm[field]})

    for field in INT_FIELDS:
        if field in norm:
            try:
                int(norm[field])
            except (TypeError, ValueError):
                issues["invalid_int"].append({"index": idx, "field": field, "value": norm[field]})

    quality = meta.get("quality", {})
    if not isinstance(quality.get("duplicate_rank", 0), int):
        issues["invalid_quality"] .append(idx)


def main() -> None:
    args = parse_args()
    path = Path(args.input)
    data = json.loads(path.read_text(encoding="utf-8"))

    chunks = data.get("chunks", [])
    issues: Dict[str, list] = defaultdict(list)
    length_hist = Counter()
    duplicate_flags = Counter()

    for idx, chunk in enumerate(chunks):
        validate_chunk(chunk, idx, issues)
        meta = chunk.get("metadata", {})
        quality = meta.get("quality", {})
        if quality.get("is_duplicate"):
            duplicate_flags["duplicates"] += 1
        length = meta.get("common", {}).get("length")
        if isinstance(length, int):
            bucket = min(length // 100 * 100, 1500)
            length_hist[bucket] += 1

    summary = {
        "total_chunks": len(chunks),
        "issues": {k: len(v) for k, v in issues.items()},
        "length_histogram": dict(length_hist),
        "duplicate_chunks": duplicate_flags.get("duplicates", 0),
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.report:
        report_payload = {
            "summary": summary,
            "details": issues,
        }
        Path(args.report).write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

