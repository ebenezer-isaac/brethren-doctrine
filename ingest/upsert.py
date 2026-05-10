"""Single-writer upsert helpers for Neo4j.

Per docs/TIER_2_SPEC.md §4.e, MERGE on chunk_id is idempotent. This module
exposes one entry per node type and is the only place that touches Cypher.

Outbox pattern (§4.e) is deferred until M3: for the personal-use single-writer
load, atomic per-record upsert is sufficient. Add outbox before M5 when
concurrent writers appear.
"""

from __future__ import annotations

from neo4j import Driver, ManagedTransaction

from ingest.models import ChunkRecord

CHUNK_LABEL = {"sermon": "SermonChunk", "sof": "SOFChunk"}


def _chunk_props(rec: ChunkRecord) -> dict:
    return {
        "chunk_id": rec.chunk_id,
        "source_doc": rec.source_doc,
        "text": rec.text,
        "type": rec.chunk_type,
        "section": rec.section,
        "themes": list(rec.themes),
        "claims": list(rec.claims),
        "scripture_refs": list(rec.scripture_refs),
        "authority_level": rec.authority_level,
    }


def _upsert_chunk_tx(tx: ManagedTransaction, rec: ChunkRecord, embedding: list[float] | None) -> None:
    label = CHUNK_LABEL[rec.source_type]
    props = _chunk_props(rec)
    if embedding is not None:
        props["embedding"] = embedding

    tx.run(
        f"""
        MERGE (c:{label} {{chunk_id: $props.chunk_id}})
        ON CREATE SET c += $props, c.created_at = datetime()
        ON MATCH  SET c += $props, c.updated_at = datetime()
        WITH c, $themes AS themes
        UNWIND themes AS theme
            MERGE (k:Concept {{name: theme}})
            ON CREATE SET k.created_at = datetime()
            MERGE (c)-[r:MENTIONS]->(k)
            ON CREATE SET r.salience = 1.0
        """,
        props=props,
        themes=list(rec.themes),
    )


def upsert_chunk(driver: Driver, rec: ChunkRecord, embedding: list[float] | None) -> None:
    """Idempotent upsert of one ChunkRecord into Neo4j with MENTIONS edges to themes."""
    with driver.session() as session:
        session.execute_write(_upsert_chunk_tx, rec, embedding)


def chunk_count(driver: Driver) -> dict[str, int]:
    """Return {label: count} for SermonChunk and SOFChunk — health check."""
    out: dict[str, int] = {}
    with driver.session() as session:
        for label in ("SermonChunk", "SOFChunk", "Concept"):
            res = session.run(f"MATCH (n:{label}) RETURN count(n) AS n")
            out[label] = res.single()["n"]
    return out
