"""Sermon adapter: parsed/<non-sof>.json -> ChunkRecord(authority_level=4).

Per docs/TIER_2_SPEC.md §4.f, authority is stamped here, never inferred.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from ingest.models import ChunkRecord


def is_sof(path: Path) -> bool:
    return path.stem.startswith("sof_")


def is_index(path: Path) -> bool:
    return path.stem.startswith("_")


def load_sermon(path: Path) -> Iterator[ChunkRecord]:
    """Yield ChunkRecord for each chunk in a non-SOF parsed JSON."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc_slug = doc["doc_slug"]

    for ch in doc["chunks"]:
        yield ChunkRecord(
            chunk_id=ch["chunk_id"],
            source_doc=doc_slug,
            source_type="sermon",
            text=ch["content"],
            chunk_type=_normalize_type(ch.get("type")),
            section=None,
            themes=ch.get("themes", []),
            claims=ch.get("claims", []),
            scripture_refs=ch.get("scripture_refs", []),
            perspectives_within_chunk=ch.get("perspectives_within_chunk", []),
            cross_references=ch.get("cross_references", []),
            authority_level=4,
        )


def _normalize_type(raw: str | None) -> str:
    """Map free-form chunk types in parsed/ to the closed enum in models.ChunkType."""
    if not raw:
        return "other"
    t = raw.strip().lower().replace("/", "_")
    allowed = {
        "definition", "teaching", "quote", "perspective", "application",
        "illustration", "exegesis", "exhortation", "warning", "summary", "narrative",
    }
    return t if t in allowed else "other"
