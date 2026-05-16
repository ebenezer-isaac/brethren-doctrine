"""Embed cultural CulturalChunks into Qdrant cult_col collection.

Reads JSONL chunk files from `data/cultural_chunks/`, batches them through
the Voyage embedding API (voyage-4-large, 2048-dim), and upserts dense
vectors into Qdrant. Idempotent: each point uses the chunk_id as deterministic
id (hashed UUID5) so re-runs overwrite cleanly.

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
from qdrant_client.models import PointStruct

from embeddings.bootstrap import VOYAGE_MODEL, VOYAGE_OUTPUT_DIMENSION

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


def _point_for(chunk: dict[str, Any], vector: list[float]) -> PointStruct:
    payload: dict[str, Any] = {
        "chunk_id": chunk["chunk_id"],
        "tradition": chunk["tradition"],
        "text": chunk.get("text", "")[:MAX_TEXT_CHARS],
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


def embed_file(
    path: Path,
    client: QdrantClient,
    voyage_client: Any,
    collection: str = "cult_col",
    rate_limit_state: dict[str, float] | None = None,
) -> dict[str, int]:
    count = 0
    failures = 0
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
        text = chunk.get("text_to_embed", "")
        if not text:
            continue
        buffer.append(chunk)
        if len(buffer) >= BATCH:
            flush()
    flush()
    return {"embedded": count, "failures": failures}


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

    if args.sources == "all":
        files = sorted(JSONL_DIR.glob("*.jsonl"))
    else:
        files = [JSONL_DIR / f"{s.strip()}.jsonl" for s in args.sources.split(",") if s.strip()]

    total = {"embedded": 0, "failures": 0}
    rate_state: dict[str, float] = {"last": 0.0}
    for path in files:
        if not path.exists():
            print(f"skip missing: {path}")
            continue
        t0 = time.monotonic()
        counts = embed_file(path, qclient, voyage_client, args.collection, rate_state)
        elapsed = round(time.monotonic() - t0, 1)
        print(
            f"{path.stem}: embedded={counts['embedded']} failures={counts['failures']} ({elapsed}s)",
            flush=True,
        )
        total["embedded"] += counts["embedded"]
        total["failures"] += counts["failures"]
    print(f"TOTAL: {json.dumps(total)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
