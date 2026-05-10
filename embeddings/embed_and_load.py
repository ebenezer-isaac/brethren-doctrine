"""Embed parsed/*.json chunks via Voyage and load into Qdrant + Neo4j.

Per docs/TIER_2_SPEC.md §4.d:
  - voyage-context-3 contextualized embeddings (chunks grouped by source_doc)
  - 1024-dim, COSINE
  - dense + sparse-IDF (BM25) co-upsert into Qdrant
  - Neo4j upsert via ingest.upsert.upsert_chunk

Voyage's `contextualized_embed` takes `inputs: list[list[str]]` where each
inner list is one document's ordered chunks. We pass one document per call
so each chunk's embedding is informed by its neighbors in the same doc.

Idempotent: MERGE on chunk_id in Neo4j and stable UUID in Qdrant.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

import voyageai
from dotenv import load_dotenv
from fastembed import SparseTextEmbedding
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from rich.console import Console
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from voyageai.error import RateLimitError
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from ingest.adapters.sermon_loader import is_index, is_sof, load_sermon
from ingest.adapters.sof_loader import load_sof
from ingest.models import ChunkRecord
from ingest.upsert import chunk_count, upsert_chunk

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
console = Console()

COLLECTION = "chunks"
DENSE_NAME = "dense"
SPARSE_NAME = "bm25"
DIM = int(os.getenv("EMBEDDING_DIM", "1024"))
DENSE_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-context-3")
SPARSE_MODEL = "Qdrant/bm25"
PARSED_DIR = ROOT / "parsed"

# Voyage free-tier without payment method on file: 3 RPM / 10K TPM.
# Throttle to ~2.5 RPM so we never hit the cap; tenacity covers transient spikes.
FREE_TIER_PACE_SECONDS = 25.0


def discover_records() -> list[ChunkRecord]:
    out: list[ChunkRecord] = []
    for f in sorted(PARSED_DIR.glob("*.json")):
        if is_index(f):
            continue
        loader = load_sof if is_sof(f) else load_sermon
        out.extend(loader(f))
    return out


def group_by_doc(records: Iterable[ChunkRecord]) -> dict[str, list[ChunkRecord]]:
    groups: dict[str, list[ChunkRecord]] = defaultdict(list)
    for r in records:
        groups[r.source_doc].append(r)
    return groups


def _stable_uuid(chunk_id: str) -> str:
    """Qdrant point IDs must be UUID or unsigned int. Hash chunk_id to a stable UUID."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"brethren://chunk/{chunk_id}"))


@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=10, min=20, max=120),
    stop=stop_after_attempt(6),
    reraise=True,
)
def _embed_doc_dense(vo: voyageai.Client, doc_chunks: list[ChunkRecord]) -> list[list[float]]:
    """Contextual embedding: one document's chunks embedded with same-doc neighbor awareness.

    Retries on Voyage free-tier RateLimitError with 20-120s exponential backoff.
    """
    inputs = [[r.text for r in doc_chunks]]
    res = vo.contextualized_embed(
        inputs=inputs,
        model=DENSE_MODEL,
        input_type="document",
        output_dimension=DIM,
    )
    return res.results[0].embeddings


def _embed_sparse(sp: SparseTextEmbedding, chunks: list[ChunkRecord]) -> list[qm.SparseVector]:
    out: list[qm.SparseVector] = []
    for emb in sp.embed([r.text for r in chunks]):
        out.append(qm.SparseVector(indices=emb.indices.tolist(), values=emb.values.tolist()))
    return out


def _qdrant_point(rec: ChunkRecord, dense: list[float], sparse: qm.SparseVector) -> qm.PointStruct:
    payload = {
        "chunk_id": rec.chunk_id,
        "source_doc": rec.source_doc,
        "source_type": rec.source_type,
        "chunk_type": rec.chunk_type,
        "section": rec.section,
        "themes": list(rec.themes),
        "scripture_refs": list(rec.scripture_refs),
        "authority_level": rec.authority_level,
        "text": rec.text,
        "model": DENSE_MODEL,
        "model_dim": DIM,
        "embedded_at": int(time.time()),
    }
    return qm.PointStruct(
        id=_stable_uuid(rec.chunk_id),
        vector={DENSE_NAME: dense, SPARSE_NAME: sparse},
        payload=payload,
    )


def main() -> int:
    voyage_key = os.getenv("VOYAGE_API_KEY")
    if not voyage_key:
        console.print("[red]FAIL[/red] VOYAGE_API_KEY missing in .env")
        return 1

    records = discover_records()
    docs = group_by_doc(records)
    total_chunks = sum(len(v) for v in docs.values())
    console.print(f"[cyan]Discovered {total_chunks} chunks across {len(docs)} documents[/cyan]")

    vo = voyageai.Client(api_key=voyage_key)
    sp = SparseTextEmbedding(model_name=SPARSE_MODEL)
    qc = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6433"), prefer_grpc=False)
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )

    n_qdrant = 0
    n_neo4j = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        t = progress.add_task("embed+load", total=total_chunks)

        last_call_at: float | None = None
        for doc_slug, chunks in docs.items():
            if last_call_at is not None:
                elapsed = time.time() - last_call_at
                if elapsed < FREE_TIER_PACE_SECONDS:
                    pause = FREE_TIER_PACE_SECONDS - elapsed
                    progress.update(t, description=f"throttling {pause:.0f}s before {doc_slug}")
                    time.sleep(pause)
            progress.update(t, description=f"embedding {doc_slug}")
            last_call_at = time.time()
            dense_vecs = _embed_doc_dense(vo, chunks)
            if len(dense_vecs) != len(chunks):
                console.print(
                    f"[red]FAIL[/red] dense embedding count mismatch for {doc_slug}: "
                    f"got {len(dense_vecs)}, expected {len(chunks)}"
                )
                return 2
            sparse_vecs = _embed_sparse(sp, chunks)

            points = [
                _qdrant_point(rec, dense, sparse)
                for rec, dense, sparse in zip(chunks, dense_vecs, sparse_vecs, strict=True)
            ]
            qc.upsert(collection_name=COLLECTION, points=points, wait=True)
            n_qdrant += len(points)

            for rec, dense in zip(chunks, dense_vecs, strict=True):
                upsert_chunk(driver, rec, embedding=dense)
                n_neo4j += 1

            progress.update(t, advance=len(chunks))

    counts = chunk_count(driver)
    qd_info = qc.get_collection(COLLECTION)
    console.print()
    console.print(
        f"[green]OK[/green] Qdrant points written this run: {n_qdrant}; "
        f"total in collection: {qd_info.points_count}"
    )
    console.print(f"[green]OK[/green] Neo4j upserts this run: {n_neo4j}")
    console.print(
        f"[green]OK[/green] Neo4j totals -- SermonChunk={counts['SermonChunk']}, "
        f"SOFChunk={counts['SOFChunk']}, Concept={counts['Concept']}"
    )

    driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
