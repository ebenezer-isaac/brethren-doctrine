"""Bootstrap Qdrant collections for lexical and cultural stores.

Voyage model: `voyage-4-large` (Voyage 4 series flagship; multilingual handles
Hebrew + Greek + English in one space; 2048 native dim). v1 uses native 2048
for max retrieval quality now that the account is on paid tier (3M TPM /
2000 RPM at usage tier 1, well within our ~22M token v1 ingest budget).
"""

from __future__ import annotations

import os
from typing import Literal

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Modifier,
    PayloadSchemaType,
    SparseVectorParams,
    VectorParams,
)

VOYAGE_MODEL = "voyage-4-large"
VOYAGE_OUTPUT_DIMENSION = 2048

_COLLECTION_BY_STORE: dict[str, tuple[str, str]] = {
    "lexical": ("lex_col", "QDRANT_LEXICAL_URL"),
    "cultural": ("cult_col", "QDRANT_CULTURAL_URL"),
}

_LEXICAL_PAYLOAD_INDEXES: dict[str, PayloadSchemaType] = {
    "book": PayloadSchemaType.KEYWORD,
    "chapter": PayloadSchemaType.INTEGER,
    "verse": PayloadSchemaType.INTEGER,
    "strong": PayloadSchemaType.KEYWORD,
    "license": PayloadSchemaType.KEYWORD,
}

_CULTURAL_PAYLOAD_INDEXES: dict[str, PayloadSchemaType] = {
    "tradition": PayloadSchemaType.KEYWORD,
    "doctrine_fine": PayloadSchemaType.KEYWORD,
    "license": PayloadSchemaType.KEYWORD,
    "anchor_id": PayloadSchemaType.KEYWORD,
}


def _embed_with_voyage(text: str, api_key: str) -> list[float]:
    """Production-time call."""
    import voyageai

    client = voyageai.Client(api_key=api_key)  # type: ignore[attr-defined]
    result = client.embed(
        [text], model=VOYAGE_MODEL, output_dimension=VOYAGE_OUTPUT_DIMENSION
    )
    return list(result.embeddings[0])


def bootstrap_qdrant_collection(store: Literal["lexical", "cultural"]) -> None:
    if store not in _COLLECTION_BY_STORE:
        raise ValueError(f"unknown store: {store!r}")
    collection_name, url_env = _COLLECTION_BY_STORE[store]
    url = os.environ.get(url_env)
    if not url:
        raise ValueError(f"{url_env} environment variable required")

    client = QdrantClient(url=url)

    existing = {c.name for c in client.get_collections().collections}
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(size=VOYAGE_OUTPUT_DIMENSION, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "bm25": SparseVectorParams(modifier=Modifier.IDF),
            },
        )

    payload_indexes = _LEXICAL_PAYLOAD_INDEXES if store == "lexical" else _CULTURAL_PAYLOAD_INDEXES
    for field_name, schema in payload_indexes.items():
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=schema,
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--store", choices=["lexical", "cultural"], required=True)
    args = parser.parse_args()
    bootstrap_qdrant_collection(args.store)
