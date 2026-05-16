"""Embed lexical lemmas + verses into Qdrant lex_col collection.

Reads from the lexical Neo4j (Lemma + Verse nodes), batches through Voyage,
and upserts dense vectors to Qdrant. The MCP retrieval layer queries by Strong's
code or lemma text first via Neo4j, then re-ranks via Qdrant cosine on dense.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from typing import Any

from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from embeddings.bootstrap import VOYAGE_OUTPUT_DIMENSION

NS = uuid.UUID("a4f6e6c0-0000-4000-8000-000000000002")
BATCH = 16
MIN_INTERVAL_SECONDS = 22.0


def _iter_lemmas(session: Any, limit: int) -> list[dict[str, Any]]:
    rows = list(
        session.run(
            """
            MATCH (l:Lemma)
            WHERE l.strong IS NOT NULL
            RETURN l.strong AS strong, l.lemma AS lemma,
                   coalesce(l.transliteration, l.lemma) AS transliteration,
                   coalesce(l.gloss, '') AS gloss,
                   coalesce(l.license, 'public_domain') AS license,
                   coalesce(l.redistribute, true) AS redistribute
            ORDER BY l.strong
            LIMIT $lim
            """,
            lim=limit,
        )
    )
    return [dict(r) for r in rows]


def _embed_batch(voyage_client: Any, texts: list[str]) -> list[list[float]] | None:
    retries = 0
    while True:
        try:
            result = voyage_client.embed(
                texts=texts,
                model="voyage-3-large",
                input_type="document",
                output_dimension=VOYAGE_OUTPUT_DIMENSION,
            )
            return list(result.embeddings)
        except Exception as exc:
            msg = str(exc)
            if retries < 3 and ("rate" in msg.lower() or "429" in msg or "TPM" in msg):
                backoff = 30 * (retries + 1)
                print(f"  rate-limit backoff {backoff}s", file=sys.stderr)
                time.sleep(backoff)
                retries += 1
                continue
            print(f"  voyage error: {msg[:200]}", file=sys.stderr)
            return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20000)
    parser.add_argument("--collection", default="lex_col")
    args = parser.parse_args(argv)

    voyage_api_key = os.environ.get("VOYAGE_API_KEY")
    qdrant_url = os.environ.get("QDRANT_LEXICAL_URL")
    if not voyage_api_key or not qdrant_url:
        print("VOYAGE_API_KEY and QDRANT_LEXICAL_URL required", file=sys.stderr)
        return 2

    import voyageai

    voyage_client = voyageai.Client(api_key=voyage_api_key)  # type: ignore[attr-defined]
    qclient = QdrantClient(url=qdrant_url)

    driver = GraphDatabase.driver(
        os.environ["NEO4J_LEXICAL_URI"],
        auth=(os.environ["NEO4J_LEXICAL_USER"], os.environ["NEO4J_LEXICAL_PASSWORD"]),
    )

    embedded = 0
    failures = 0
    with driver.session() as session:
        lemmas = _iter_lemmas(session, args.limit)
        print(f"loaded {len(lemmas)} lemmas", flush=True)

        last = 0.0
        for i in range(0, len(lemmas), BATCH):
            batch = lemmas[i : i + BATCH]
            wait = MIN_INTERVAL_SECONDS - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
            texts = [
                f"{r['lemma']} ({r['transliteration']}): {r['gloss']}".strip()[:6000]
                for r in batch
            ]
            vecs = _embed_batch(voyage_client, texts)
            last = time.monotonic()
            if vecs is None:
                failures += len(batch)
                continue
            points = []
            for r, vec in zip(batch, vecs, strict=False):
                payload = {
                    "strong": r["strong"],
                    "lemma": r["lemma"],
                    "transliteration": r["transliteration"],
                    "gloss": r["gloss"],
                    "license": r["license"],
                    "redistribute": r["redistribute"],
                }
                point_id = str(uuid.uuid5(NS, r["strong"]))
                points.append(PointStruct(id=point_id, vector={"dense": vec}, payload=payload))
            qclient.upsert(collection_name=args.collection, points=points)
            embedded += len(points)
            if (i // BATCH) % 5 == 0:
                print(f"  progress: {embedded}/{len(lemmas)} embedded", flush=True)

    driver.close()
    print(f"TOTAL: embedded={embedded} failures={failures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
