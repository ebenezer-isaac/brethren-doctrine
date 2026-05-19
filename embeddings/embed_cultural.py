"""Embed cultural CulturalChunks into Qdrant cult_col collection.

Reads JSONL chunk files from `data/cultural_chunks/`, batches them through
the Voyage embedding API (voyage-4-large, 2048-dim), and upserts dense
vectors into Qdrant. Idempotent: each point uses the chunk_id as deterministic
id (hashed UUID5), and the target collection is dropped + recreated ONCE at
the start of the run (`_recreate_collection`, scoped strictly to
`--collection`, default `cult_col`) so cult_col deterministically mirrors the
current cultural graph with zero stale orphan points across rebuilds
(G-AUDIT-1-E1).

Copyright contract (G-AUDIT-2-E2, mirrors the corrected G-T1
`ingest/cultural/_common.py`): the embed input is always the
redistribute-safe `text_to_embed`, and the persisted Qdrant payload `text`
is gated through `ingest.license_guard.check_redistribute(license,"bulk")
["allowed"]` (fail-closed) so verbatim copyrighted prose for a
redistribute=false source can never leak into cult_col.

Rate-limit posture at usage tier 1 (3M TPM / 2000 RPM for voyage-4-large):
- BATCH=128 chunks per request keeps each request well below the 32K
  context limit and stays inside the per-minute TPM budget.
- MIN_INTERVAL_SECONDS=0 because 2000 RPM is far above what we can saturate.
- Backoff still kicks in if Voyage 429s on a burst.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from embeddings.bootstrap import VOYAGE_MODEL, VOYAGE_OUTPUT_DIMENSION
from ingest.license_guard import check_redistribute

JSONL_DIR = Path("data/cultural_chunks")
NS = uuid.UUID("a4f6e6c0-0000-4000-8000-000000000001")
# 32 keeps every batch inside Voyage's 120,000-token per-request cap even for
# long articles (e.g., OCA Hopko ~4K-word leaves). For confessions where texts
# average <300 tokens this batch lower-bounds throughput but stays well within
# tier-1 RPM. Effective rate observed: ~100 chunks/sec.
BATCH = 32
MAX_TEXT_CHARS = 6000
MIN_INTERVAL_SECONDS = 0.0


def _chunks(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _redistribute_safe_text(chunk: dict[str, Any]) -> str:
    """Return the only payload text that is safe to persist in cult_col.

    Cultural-store copyright contract (mirrors the corrected G-T1
    ``ingest/cultural/_common.py`` gate): the verbatim ``text`` may be
    persisted ONLY when the chunk's license permits bulk redistribution.
    ``check_redistribute`` returns the ``RedistributeResult`` dict
    ``{"allowed": bool, "reason": str}``; a non-empty dict is always
    truthy, so the value MUST be read off the ``["allowed"]`` member
    (the exact dead-guard the lexical/cultural Neo4j side leaked on).
    For every redistribute=false license (``©Assemblies-of-God``,
    ``©OCA-Hopko-estate``, ``©Libreria-Editrice-Vaticana``,
    ``parsed-sanitized``, ``CC-BY-NC-4.0`` ...) ``check_redistribute``
    returns ``allowed=False`` and we fall back to the redistribute-safe
    ``text_to_embed`` variant, never the copyrighted prose. Fail-closed:
    a missing/empty/unrecognized license is denied by the guard, so a
    malformed chunk yields ``text_to_embed`` (or empty), never the
    verbatim ``text``. Brethren-on-trial: redistribution safety is never
    weakened by this embedder; the Qdrant payload can carry no verbatim
    copyrighted text the Neo4j store would itself refuse to persist.
    """
    license_str = chunk.get("license", "")
    if check_redistribute(license_str, "bulk")["allowed"]:
        return chunk.get("text", "")[:MAX_TEXT_CHARS]
    return chunk.get("text_to_embed", "")[:MAX_TEXT_CHARS]


def _point_for(chunk: dict[str, Any], vector: list[float]) -> PointStruct:
    payload: dict[str, Any] = {
        "chunk_id": chunk["chunk_id"],
        "tradition": chunk["tradition"],
        "text": _redistribute_safe_text(chunk),
        "license": chunk["license"],
        "redistribute": chunk["redistribute"],
        "license_note": chunk.get("license_note"),
        "anchor_id": chunk["source"]["anchor_id"],
        "work_id": chunk["source"]["work_id"],
        "work_title": chunk["source"]["work_title"],
        "author": chunk["source"]["author"],
        "date_written": chunk["source"]["date_written"],
        "doctrine_tags": chunk.get("doctrine_tags", []),
    }
    point_id = str(uuid.uuid5(NS, chunk["chunk_id"]))
    return PointStruct(id=point_id, vector={"dense": vector}, payload=payload)


def _recreate_collection(qclient: Any, collection: str) -> None:
    """Drop and recreate exactly ``collection`` before any point is written.

    Deterministic-rebuild rationale (G-AUDIT-1-E1 / G-AUDIT-2 embed
    upsert-without-prune), mirroring the lexical fix in
    ``embeddings/embed_lexical._recreate_collection``: the embed run
    upserts points keyed by ``uuid5(NS, chunk_id)`` and ``upsert`` never
    deletes. Across cultural-graph rebuilds a ``chunk_id`` that existed in
    a prior topology but not the current one (a source that shrinks, a
    re-scrape that shifts an oca_hopko URL anchor, or the G-BRETHREN-1
    chunk_id renamespacing) leaves an orphaned stale vector behind that
    silently poisons retrieval. Recreating the collection here makes the
    embed deterministic and idempotent: after a run ``cult_col`` mirrors
    EXACTLY the current cultural graph's embeddable chunk set with zero
    stale points, so two consecutive full runs on the same frozen graph
    yield the same point ids and the same points_count. This drop is
    scoped STRICTLY to the collection named by ``--collection`` (default
    ``cult_col``); no lexical collection and no other collection is read
    or touched. Vector config is held identical to
    ``embeddings.bootstrap`` (named vector ``"dense"``, size
    ``VOYAGE_OUTPUT_DIMENSION`` == 2048, COSINE distance) so retrieval
    semantics are unchanged.
    """
    existing = {c.name for c in qclient.get_collections().collections}
    if collection in existing:
        qclient.delete_collection(collection_name=collection)
    qclient.create_collection(
        collection_name=collection,
        vectors_config={
            "dense": VectorParams(
                size=VOYAGE_OUTPUT_DIMENSION, distance=Distance.COSINE
            )
        },
    )


def embed_file(
    path: Path,
    client: QdrantClient,
    voyage_client: Any,
    collection: str = "cult_col",
    rate_limit_state: dict[str, float] | None = None,
) -> dict[str, int]:
    count = 0
    failures = 0
    skipped_no_text = 0
    buffer: list[dict[str, Any]] = []
    state = rate_limit_state if rate_limit_state is not None else {"last": 0.0}

    def flush() -> None:
        nonlocal count, failures
        if not buffer:
            return
        now = time.monotonic()
        wait = MIN_INTERVAL_SECONDS - (now - state["last"])
        if wait > 0:
            time.sleep(wait)
        texts = [c["text_to_embed"][:MAX_TEXT_CHARS] for c in buffer]
        retries = 0
        while True:
            try:
                result = voyage_client.embed(
                    texts=texts,
                    model=VOYAGE_MODEL,
                    input_type="document",
                    output_dimension=VOYAGE_OUTPUT_DIMENSION,
                )
                break
            except Exception as exc:
                msg = str(exc)
                if retries < 3 and ("rate" in msg.lower() or "429" in msg or "TPM" in msg):
                    backoff = 30 * (retries + 1)
                    print(f"  rate-limit backoff {backoff}s", file=sys.stderr)
                    time.sleep(backoff)
                    retries += 1
                    continue
                print(f"  voyage error: {msg[:200]}", file=sys.stderr)
                failures += len(buffer)
                buffer.clear()
                state["last"] = time.monotonic()
                return
        points = [_point_for(c, vec) for c, vec in zip(buffer, result.embeddings, strict=False)]
        client.upsert(collection_name=collection, points=points)
        count += len(points)
        state["last"] = time.monotonic()
        buffer.clear()

    for chunk in _chunks(path):
        # Pre-filter textless chunks BEFORE they reach a Voyage batch.
        # Voyage rejects any request whose input list contains an empty
        # string and fails the WHOLE batch, dropping good chunks as
        # collateral (the 84aaeaf empty-string-poisons-batch class). The
        # embed input is always the redistribute-safe ``text_to_embed``;
        # a chunk with no embeddable text has nothing to re-rank on, so
        # skipping it is correct, not a fudge. Skips are counted, never
        # silently dropped, never sent to Voyage.
        text = chunk.get("text_to_embed", "")
        if not text or not text.strip():
            skipped_no_text += 1
            continue
        buffer.append(chunk)
        if len(buffer) >= BATCH:
            flush()
    flush()
    return {
        "embedded": count,
        "skipped_no_text": skipped_no_text,
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources",
        default="all",
        help="Comma-separated source slugs, or 'all'",
    )
    parser.add_argument("--collection", default="cult_col")
    args = parser.parse_args(argv)

    voyage_api_key = os.environ.get("VOYAGE_API_KEY")
    if not voyage_api_key:
        print("VOYAGE_API_KEY not set", file=sys.stderr)
        return 2
    qdrant_url = os.environ.get("QDRANT_CULTURAL_URL")
    if not qdrant_url:
        print("QDRANT_CULTURAL_URL not set", file=sys.stderr)
        return 2

    import voyageai

    voyage_client = voyageai.Client(api_key=voyage_api_key)  # type: ignore[attr-defined]
    qclient = QdrantClient(url=qdrant_url)

    # Rebuild the target collection ONCE, BEFORE any file is embedded, so
    # the run is deterministic and idempotent: cult_col ends mirroring
    # exactly the current cultural graph's embeddable chunk set, with
    # zero cross-rebuild stale points (G-AUDIT-1-E1 / G-AUDIT-2). This is
    # OUTSIDE the per-source loop on purpose: recreating per file would
    # wipe every previously embedded source. Scoped to args.collection
    # only; never touches the lexical collection.
    _recreate_collection(qclient, args.collection)

    if args.sources == "all":
        files = sorted(JSONL_DIR.glob("*.jsonl"))
    else:
        files = [JSONL_DIR / f"{s.strip()}.jsonl" for s in args.sources.split(",") if s.strip()]

    total = {"embedded": 0, "skipped_no_text": 0, "failures": 0}
    rate_state: dict[str, float] = {"last": 0.0}
    for path in files:
        if not path.exists():
            print(f"skip missing: {path}")
            continue
        t0 = time.monotonic()
        counts = embed_file(path, qclient, voyage_client, args.collection, rate_state)
        elapsed = round(time.monotonic() - t0, 1)
        print(
            f"{path.stem}: embedded={counts['embedded']} "
            f"skipped_no_text={counts['skipped_no_text']} "
            f"failures={counts['failures']} ({elapsed}s)",
            flush=True,
        )
        total["embedded"] += counts["embedded"]
        total["skipped_no_text"] += counts["skipped_no_text"]
        total["failures"] += counts["failures"]
    print(f"TOTAL: {json.dumps(total)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
