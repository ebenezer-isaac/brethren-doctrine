"""Bootstrap the `chunks` Qdrant collection.

Idempotent: safe to re-run. Creates the collection if absent; verifies the
schema (vector size, distance, sparse vector config) if present.

Per docs/TIER_2_SPEC.md §4.d:
  - dense vector: voyage-context-3 @ 1024-dim COSINE (named "dense")
  - sparse vector: BM25 with IDF modifier (named "bm25")
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from rich.console import Console

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
console = Console()

COLLECTION = "chunks"
DENSE_NAME = "dense"
SPARSE_NAME = "bm25"
DIM = int(os.getenv("EMBEDDING_DIM", "1024"))


def _client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY") or None
    return QdrantClient(url=url, api_key=api_key, prefer_grpc=False)


def _ensure_collection(qc: QdrantClient) -> None:
    existing = {c.name for c in qc.get_collections().collections}
    if COLLECTION in existing:
        info = qc.get_collection(COLLECTION)
        params = info.config.params
        dense_cfg = (params.vectors or {}).get(DENSE_NAME)
        if dense_cfg is None or dense_cfg.size != DIM:
            raise RuntimeError(
                f"Existing collection '{COLLECTION}' has incompatible dense vector config "
                f"(size={dense_cfg.size if dense_cfg else None}, expected {DIM}). "
                "Migrate or drop before re-running."
            )
        if SPARSE_NAME not in (params.sparse_vectors or {}):
            raise RuntimeError(
                f"Existing collection '{COLLECTION}' is missing the '{SPARSE_NAME}' sparse vector."
            )
        console.print(f"[green]OK[/green] Collection '{COLLECTION}' already exists with correct schema.")
        return

    qc.create_collection(
        collection_name=COLLECTION,
        vectors_config={
            DENSE_NAME: qm.VectorParams(size=DIM, distance=qm.Distance.COSINE),
        },
        sparse_vectors_config={
            SPARSE_NAME: qm.SparseVectorParams(modifier=qm.Modifier.IDF),
        },
        optimizers_config=qm.OptimizersConfigDiff(default_segment_number=2),
        on_disk_payload=False,
    )

    qc.create_payload_index(COLLECTION, "source_doc", qm.PayloadSchemaType.KEYWORD)
    qc.create_payload_index(COLLECTION, "source_type", qm.PayloadSchemaType.KEYWORD)
    qc.create_payload_index(COLLECTION, "authority_level", qm.PayloadSchemaType.INTEGER)
    qc.create_payload_index(COLLECTION, "chunk_type", qm.PayloadSchemaType.KEYWORD)
    qc.create_payload_index(COLLECTION, "themes", qm.PayloadSchemaType.KEYWORD)
    qc.create_payload_index(COLLECTION, "scripture_refs", qm.PayloadSchemaType.KEYWORD)

    console.print(
        f"[green]OK[/green] Created collection '{COLLECTION}' "
        f"(dense={DIM}/COSINE, sparse=bm25/IDF, payload indexes on source_doc/type/authority/themes/scripture_refs)."
    )


def main() -> int:
    qc = _client()
    try:
        _ensure_collection(qc)
    except Exception as exc:
        console.print(f"[red]FAIL bootstrap:[/red] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
