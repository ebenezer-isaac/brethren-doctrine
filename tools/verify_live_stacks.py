"""Verify live stacks are populated end-to-end.

Run after the ingest and embed pipelines complete. Surfaces a tabular report
of counts per store and per collection, then exits 0 if every count is
within tolerance and 1 otherwise.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from neo4j import GraphDatabase
from qdrant_client import QdrantClient

EXPECTED: dict[str, tuple[int, int]] = {
    "cultural.CulturalChunk": (1000, 60000),
    "cultural.Work": (10, 600),
    "lexical.Word": (300000, 1500000),
    "lexical.Verse": (20000, 35000),
    "lexical.Lemma": (10000, 25000),
    "lexical.CrossRef": (300000, 800000),
    "lexical.Person": (3000, 3100),
    "lexical.Place": (1200, 1700),
    "qdrant.cult_col": (1, 60000),
    "qdrant.lex_col": (1, 25000),
}


def _cypher_count(driver: Any, label: str) -> int:
    with driver.session() as session:
        rec = session.run(f"MATCH (n:`{label}`) RETURN count(n) AS n").single()
        return int(rec["n"]) if rec else 0


def _qdrant_count(client: QdrantClient, collection: str) -> int:
    try:
        return int(client.get_collection(collection).points_count or 0)
    except Exception:
        return 0


def main() -> int:
    cul = GraphDatabase.driver(
        os.environ["NEO4J_CULTURAL_URI"],
        auth=(os.environ["NEO4J_CULTURAL_USER"], os.environ["NEO4J_CULTURAL_PASSWORD"]),
    )
    lex = GraphDatabase.driver(
        os.environ["NEO4J_LEXICAL_URI"],
        auth=(os.environ["NEO4J_LEXICAL_USER"], os.environ["NEO4J_LEXICAL_PASSWORD"]),
    )
    qcul = QdrantClient(url=os.environ["QDRANT_CULTURAL_URL"])
    qlex = QdrantClient(url=os.environ["QDRANT_LEXICAL_URL"])

    counts: dict[str, int] = {}
    try:
        counts["cultural.CulturalChunk"] = _cypher_count(cul, "CulturalChunk")
        counts["cultural.Work"] = _cypher_count(cul, "Work")
        counts["lexical.Word"] = _cypher_count(lex, "Word")
        counts["lexical.Verse"] = _cypher_count(lex, "Verse")
        counts["lexical.Lemma"] = _cypher_count(lex, "Lemma")
        counts["lexical.CrossRef"] = _cypher_count(lex, "CrossRef")
        counts["lexical.Person"] = _cypher_count(lex, "Person")
        counts["lexical.Place"] = _cypher_count(lex, "Place")
        counts["qdrant.cult_col"] = _qdrant_count(qcul, "cult_col")
        counts["qdrant.lex_col"] = _qdrant_count(qlex, "lex_col")
    finally:
        cul.close()
        lex.close()

    failures: list[str] = []
    for key, n in counts.items():
        low, high = EXPECTED.get(key, (0, 0))
        ok = low <= n <= high
        status = "OK" if ok else "OUT-OF-RANGE"
        print(f"{key:35s} {n:>10}  [{low}, {high}]  {status}")
        if not ok:
            failures.append(f"{key}: {n} not in [{low}, {high}]")

    if failures:
        print(f"\n{len(failures)} failure(s):", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print("\nAll counts within tolerance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
