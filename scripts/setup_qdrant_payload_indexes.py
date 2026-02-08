#!/usr/bin/env python3
"""Create recommended payload indexes for Qdrant collection."""

import argparse

from qdrant_client import QdrantClient
from qdrant_client.http.models import PayloadSchemaType


FIELDS = [
    ("metadata.common.doc_type", PayloadSchemaType.KEYWORD),
    ("metadata.common.split", PayloadSchemaType.KEYWORD),
    ("metadata.norm.case_number", PayloadSchemaType.KEYWORD),
    ("metadata.norm.decision_date", PayloadSchemaType.KEYWORD),
    ("metadata.norm.court", PayloadSchemaType.KEYWORD),
    ("metadata.origin.original_doc_type", PayloadSchemaType.KEYWORD),
    ("metadata.norm.decision_year", PayloadSchemaType.INTEGER),
    ("metadata.quality.duplicate_rank", PayloadSchemaType.INTEGER),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Setup Qdrant payload indexes")
    parser.add_argument("--url", default="http://localhost:6333", help="Qdrant URL")
    parser.add_argument("--collection", required=True, help="Collection name")
    parser.add_argument("--api-key", default=None, help="Optional Qdrant API key")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = QdrantClient(url=args.url, api_key=args.api_key)

    for field, schema_type in FIELDS:
        print(f"Creating payload index: {field} ({schema_type})")
        client.create_payload_index(
            collection_name=args.collection,
            field_name=field,
            field_schema=schema_type,
            wait=True,
        )

    print("Payload index setup complete.")


if __name__ == "__main__":
    main()

