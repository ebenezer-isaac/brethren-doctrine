"""Shared helpers for Pipeline 1 lexical adapters.

All adapters import from here for: settings (env-driven), Neo4j driver factory,
batched upsert, and a count tolerance asserter used in --verify-only mode.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from neo4j import Driver, GraphDatabase
from pydantic_settings import BaseSettings, SettingsConfigDict

from ingest.models import LexicalRecord

# Label hints for edge upserts: rel_type -> (from_label, to_label). Without these,
# the MATCH on edge endpoints scans all nodes, which makes the upsert quadratic.
# When a rel_type is missing here, we fall back to unlabeled MATCH (slower).
_REL_LABELS: dict[str, tuple[str, str]] = {
    "CROSS_REF": ("Verse", "Verse"),
    "MENTIONS": ("Person", "Verse"),
    "INSTANCE_OF": ("Word", "Lemma"),
    "IN_VERSE": ("Word", "Verse"),
    "NEXT_WORD": ("Word", "Word"),
    "HAS_MORPHEME": ("Word", "Morpheme"),
    "HAS_WORD": ("Verse", "Word"),
    "GLOSSES_GREEK_LEMMA": ("Word", "Lemma"),
    "FROM_EDITION": ("Word", "Variant"),
    "PARSE_OF": ("Word", "Word"),
    "ADDRESSES": ("Variant", "Variant"),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    neo4j_lexical_uri: str
    neo4j_lexical_user: str
    neo4j_lexical_password: str
    qdrant_lexical_url: str
    voyage_api_key: str = ""


def get_lexical_driver(settings: Settings) -> Driver:
    return GraphDatabase.driver(
        settings.neo4j_lexical_uri,
        auth=(settings.neo4j_lexical_user, settings.neo4j_lexical_password),
    )


_UPSERT_CYPHER = """
UNWIND $records AS rec
CALL apoc.merge.node([rec.record_type], {id: rec.id}, rec.properties, rec.properties)
YIELD node
RETURN count(node) AS upserted
"""


def _chunks(it: Iterable[LexicalRecord], size: int) -> Iterator[list[LexicalRecord]]:
    batch: list[LexicalRecord] = []
    for rec in it:
        batch.append(rec)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def upsert_records(
    driver: Driver, records: Iterable[LexicalRecord], batch_size: int = 1000
) -> dict[str, int]:
    """Idempotent batched node upsert. Returns record_type -> count_upserted.

    Uses a label-parameterized MERGE: each batch is grouped by record_type so that
    the label can be inlined in Cypher. Edges are upserted in a second pass per record.
    """
    counts: dict[str, int] = {}
    with driver.session() as session:
        for batch in _chunks(records, batch_size):
            grouped: dict[str, list[dict[str, Any]]] = {}
            for r in batch:
                payload = {
                    "id": r.id,
                    "properties": dict(r.properties)
                    | {
                        "license": r.license,
                        "redistribute": r.redistribute,
                        "license_note": r.license_note,
                    },
                    "edges": [e.model_dump() for e in r.edges],
                }
                grouped.setdefault(r.record_type, []).append(payload)
            for label, rows in grouped.items():
                cypher = (
                    f"UNWIND $rows AS row "
                    f"MERGE (n:`{label}` {{id: row.id}}) "
                    f"SET n += row.properties "
                    f"RETURN count(n) AS upserted"
                )
                result = session.run(cypher, rows=rows)
                upserted = result.single()["upserted"]  # type: ignore[index]
                counts[label] = counts.get(label, 0) + upserted

            edge_rows: list[dict[str, Any]] = []
            for r in batch:
                for e in r.edges:
                    edge_rows.append(
                        {
                            "from_id": r.id,
                            "to_id": e.to_id,
                            "rel_type": e.rel_type,
                            "properties": dict(e.properties),
                        }
                    )
            if edge_rows:
                by_rel: dict[str, list[dict[str, Any]]] = {}
                for er in edge_rows:
                    by_rel.setdefault(er["rel_type"], []).append(er)
                for rel_type, rows in by_rel.items():
                    labels = _REL_LABELS.get(rel_type)
                    if labels:
                        from_lbl, to_lbl = labels
                        cypher = (
                            f"UNWIND $rows AS row "
                            f"MATCH (a:`{from_lbl}` {{id: row.from_id}}), "
                            f"(b:`{to_lbl}` {{id: row.to_id}}) "
                            f"MERGE (a)-[r:`{rel_type}`]->(b) "
                            f"SET r += row.properties "
                            f"RETURN count(r) AS edges"
                        )
                    else:
                        cypher = (
                            f"UNWIND $rows AS row "
                            f"MATCH (a {{id: row.from_id}}), (b {{id: row.to_id}}) "
                            f"MERGE (a)-[r:`{rel_type}`]->(b) "
                            f"SET r += row.properties "
                            f"RETURN count(r) AS edges"
                        )
                    session.run(cypher, rows=rows).consume()
    return counts


def assert_counts_match(actual: dict[str, int], expected: dict[str, tuple[int, int]]) -> None:
    """Raise AssertionError if any actual count is outside (low, high) inclusive."""
    errors: list[str] = []
    for key, (low, high) in expected.items():
        got = actual.get(key, 0)
        if got < low or got > high:
            errors.append(f"{key}: got {got}, expected [{low}, {high}]")
    if errors:
        raise AssertionError("count mismatch:\n  " + "\n  ".join(errors))
