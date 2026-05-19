"""Brethren parsed corpus adapter (Pipeline 1 cultural).

Reads sanitized Plymouth-Brethren teaching notes from local `parsed/*.json`
(produced by the `ingest-sermons` skill). License is `parsed-sanitized`,
redistribute False (no scraping; source documents are private).

Each chunk in a parsed doc becomes one CulturalChunk with anchor
`parsed.<doc_slug>.<chunk_index>`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "brethren-parsed"
TRADITION: Literal["plymouth-brethren"] = "plymouth-brethren"
LICENSE = "parsed-sanitized"
REDISTRIBUTE = False
LICENSE_NOTE = "Private brethren teaching notes; sanitized to remove personal names"
PARSED_DIR = Path("parsed")
CANONICAL_URL = "file://parsed/"
FALLBACK_URLS: list[str] = []


def expected_chunk_count() -> tuple[int, int]:
    return (150, 1000)


def _doc_to_chunks(doc: dict[str, object]) -> list[CulturalChunk]:
    doc_slug = str(doc.get("doc_slug", "unknown"))
    session_metadata = doc.get("session_metadata") or {}
    if not isinstance(session_metadata, dict):
        session_metadata = {}
    title = str(session_metadata.get("title") or doc_slug)
    chunks_raw = doc.get("chunks") or []
    if not isinstance(chunks_raw, list):
        return []
    work_id = f"brethren-parsed.{doc_slug}"
    out: list[CulturalChunk] = []
    for idx, ch in enumerate(chunks_raw, start=1):
        if not isinstance(ch, dict):
            continue
        text = str(ch.get("content", "")).strip()
        if not text:
            continue
        # Node identity MUST be deterministic from stable inputs (doc_slug + the
        # stable enumeration index), NOT from the source-supplied ch.chunk_id.
        # Trusting the upstream chunk_id risked a global cultural_chunk_id UNIQUE
        # hard-fail if two docs ever supplied a colliding upstream id, which would
        # abort the air-gapped Brethren batch and break byte-identical reseed
        # (Decision 1 stable-identity / re-scrape convergence). The deterministic
        # `parsed.<doc_slug>.<idx:03d>` scheme is exactly what anchor_id already
        # uses; the upstream ch.chunk_id is a positional label carrying no
        # distinction this scheme does not already encode, and nothing downstream
        # relies on it for identity.
        anchor_id = f"parsed.{doc_slug}.{idx:03d}"
        out.append(
            CulturalChunk(
                chunk_id=f"brethren-parsed.{anchor_id}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=work_id,
                    work_title=title,
                    author=None,
                    date_written=str(doc.get("source_mtime", ""))[:4] or "2026",
                    is_confessional_text=False,
                    anchor_id=anchor_id,
                    language="en",
                    translator=None,
                ),
                text=text,
                text_to_embed=text,
                license=LICENSE,
                redistribute=REDISTRIBUTE,
                license_note=LICENSE_NOTE,
            )
        )
    return out


def scrape() -> list[CulturalChunk]:
    """Read all parsed/<slug>.json (skip _index.json and _perspectives.json) into chunks."""
    if not PARSED_DIR.exists():
        return []
    out: list[CulturalChunk] = []
    for path in sorted(PARSED_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(doc, dict):
            out.extend(_doc_to_chunks(doc))
    return out
