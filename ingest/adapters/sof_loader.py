"""SOF adapter: parsed/sof_*.json -> ChunkRecord(authority_level=3).

Per docs/TIER_2_SPEC.md §4.f, the SOF loader OVERRIDES authority_level to 3
at the boundary. Tier 1 stamped every doc as 4; this is the canonical
correction point.

Section is derived from filename: sof_god.json -> 'god',
sof_god_the_son.json -> 'god_the_son'.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from ingest.models import ChunkRecord
from ingest.adapters.sermon_loader import _normalize_type

SOF_SECTIONS = {
    "god", "god_the_father", "god_the_son", "holy_spirit",
    "man", "salvation", "church", "last_things",
}


def section_from_filename(path: Path) -> str:
    stem = path.stem
    if not stem.startswith("sof_"):
        raise ValueError(f"sof_loader called on non-SOF file: {path}")
    section = stem[len("sof_"):]
    return section


def load_sof(path: Path) -> Iterator[ChunkRecord]:
    """Yield ChunkRecord for each chunk in a sof_*.json with authority_level=3."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc_slug = doc["doc_slug"]
    section = section_from_filename(path)

    for ch in doc["chunks"]:
        yield ChunkRecord(
            chunk_id=ch["chunk_id"],
            source_doc=doc_slug,
            source_type="sof",
            text=ch["content"],
            chunk_type=_normalize_type(ch.get("type")),
            section=section,
            themes=ch.get("themes", []),
            claims=ch.get("claims", []),
            scripture_refs=ch.get("scripture_refs", []),
            perspectives_within_chunk=ch.get("perspectives_within_chunk", []),
            cross_references=ch.get("cross_references", []),
            authority_level=3,
        )
