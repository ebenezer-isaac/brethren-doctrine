"""OpenBible cross-references adapter (Pipeline 1).

Parses `cross_references.txt` (tab-separated From_Verse / To_Verse / Votes).
Explodes verse ranges (e.g., `Rom.1.19-Rom.1.20`) into one edge per verse.
License: CC-BY, redistribute True.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from ingest.lexical._common import Settings, get_lexical_driver, upsert_records
from ingest.models import GraphEdge, LexicalRecord

LICENSE = "CC-BY"
LICENSE_NOTE = "OpenBible cross-references, CC-BY"
SOURCE_SLUG = "openbible"

_REF_RE = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$")
_RANGE_RE = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)-([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$")


def _expand_to_verses(ref: str) -> list[str]:
    m = _RANGE_RE.match(ref.strip())
    if m:
        book_a, ch_a, vs_a = m.group(1), int(m.group(2)), int(m.group(3))
        book_b, ch_b, vs_b = m.group(4), int(m.group(5)), int(m.group(6))
        if book_a == book_b and ch_a == ch_b and vs_b >= vs_a:
            return [f"{book_a}.{ch_a}.{v}" for v in range(vs_a, vs_b + 1)]
        return [f"{book_a}.{ch_a}.{vs_a}", f"{book_b}.{ch_b}.{vs_b}"]
    m = _REF_RE.match(ref.strip())
    if m:
        return [ref.strip()]
    return []


def _iter_records(cross_refs_path: Path) -> Iterator[LexicalRecord]:
    verse_seen: set[str] = set()
    with cross_refs_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            stripped = line.rstrip("\n")
            if not stripped or stripped.startswith("From") or stripped.startswith("#"):
                continue
            parts = stripped.split("\t")
            if len(parts) < 2:
                continue
            from_ref = parts[0].strip()
            to_field = parts[1].strip()
            votes = parts[2].strip() if len(parts) > 2 else ""
            for to_ref in _expand_to_verses(to_field):
                from_id = f"verse:{from_ref}"
                to_id = f"verse:{to_ref}"
                if from_id not in verse_seen:
                    verse_seen.add(from_id)
                    fm = _REF_RE.match(from_ref)
                    if fm:
                        yield LexicalRecord(
                            record_type="Verse",
                            id=from_id,
                            properties={
                                "osisID": from_ref,
                                "book": fm.group(1),
                                "chapter": int(fm.group(2)),
                                "verse": int(fm.group(3)),
                            },
                            license="public_domain",
                            redistribute=True,
                            license_note="Verse stub",
                        )
                if to_id not in verse_seen:
                    verse_seen.add(to_id)
                    tm = _REF_RE.match(to_ref)
                    if tm:
                        yield LexicalRecord(
                            record_type="Verse",
                            id=to_id,
                            properties={
                                "osisID": to_ref,
                                "book": tm.group(1),
                                "chapter": int(tm.group(2)),
                                "verse": int(tm.group(3)),
                            },
                            license="public_domain",
                            redistribute=True,
                            license_note="Verse stub",
                        )
                edge_id = f"cross:openbible:{from_ref}:{to_ref}"
                yield LexicalRecord(
                    record_type="CrossRef",
                    id=edge_id,
                    properties={
                        "from_ref": from_ref,
                        "to_ref": to_ref,
                        "source": SOURCE_SLUG,
                        "votes": int(votes) if votes.isdigit() else 0,
                    },
                    edges=[
                        GraphEdge(
                            to_id=to_id,
                            rel_type="CROSS_REF",
                            properties={
                                "source": SOURCE_SLUG,
                                "votes": int(votes) if votes.isdigit() else 0,
                                "license": LICENSE,
                                "redistribute": True,
                            },
                        )
                    ],
                    license=LICENSE,
                    redistribute=True,
                    license_note=LICENSE_NOTE,
                )


def ingest_openbible(source_dir: Path, settings: Settings) -> dict[str, int]:
    cross_refs_path = source_dir / "cross_references.txt"
    driver = get_lexical_driver(settings)
    try:
        return upsert_records(driver, _iter_records(cross_refs_path))
    finally:
        driver.close()
