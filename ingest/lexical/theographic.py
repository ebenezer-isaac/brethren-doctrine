"""Theographic Bible Metadata adapter (Pipeline 1).

Parses `CSV/People.csv`, `CSV/Places.csv`, `CSV/Events.csv`. Emits Person /
Place / Event records with MENTIONS edges to Verse nodes (one per verse in
the comma-separated `verses` field).

License: CC-BY-SA-4.0, redistribute True (SA propagation note).
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterator
from pathlib import Path

from ingest.lexical._common import Settings, get_lexical_driver, upsert_records
from ingest.models import GraphEdge, LexicalRecord

LICENSE = "CC-BY-SA-4.0"
LICENSE_NOTE = "Theographic Bible Metadata, CC-BY-SA-4.0 (SA propagation required)"
SOURCE_SLUG = "theographic"

_VERSE_RE = re.compile(r"([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)")


def _explode_verses(field: str) -> list[str]:
    return [".".join(m.groups()) for m in _VERSE_RE.finditer(field)]


def _read_csv(path: Path) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            yield {k.strip() if k else k: (v or "") for k, v in row.items()}


def _people(path: Path) -> Iterator[LexicalRecord]:
    for row in _read_csv(path):
        lookup = row.get("personLookup", "")
        if not lookup:
            continue
        verses = _explode_verses(row.get("verses", ""))
        edges = [
            GraphEdge(to_id=f"verse:{ref}", rel_type="MENTIONS", properties={}) for ref in verses
        ]
        yield LexicalRecord(
            record_type="Person",
            id=f"person:{lookup}",
            properties={
                "personLookup": lookup,
                "name": row.get("name", ""),
                "displayTitle": row.get("displayTitle", ""),
                "gender": row.get("gender", ""),
                "birth_year": _safe_int(row.get("birthYear", "")),
                "death_year": _safe_int(row.get("deathYear", "")),
                "verse_count": _safe_int(row.get("verseCount", "")),
                "source": SOURCE_SLUG,
            },
            edges=edges,
            text_to_embed=row.get("displayTitle", "") or row.get("name", ""),
            license=LICENSE,
            redistribute=True,
            license_note=LICENSE_NOTE,
        )


def _places(path: Path) -> Iterator[LexicalRecord]:
    for row in _read_csv(path):
        lookup = row.get("placeLookup", "") or row.get("place", "")
        if not lookup:
            continue
        verses = _explode_verses(row.get("verses", ""))
        edges = [
            GraphEdge(to_id=f"verse:{ref}", rel_type="MENTIONS", properties={}) for ref in verses
        ]
        yield LexicalRecord(
            record_type="Place",
            id=f"place:{lookup}",
            properties={
                "placeLookup": lookup,
                "name": row.get("displayTitle", "") or row.get("name", ""),
                "feature_type": row.get("featureType", ""),
                "latitude": _safe_float(row.get("latitude", "")),
                "longitude": _safe_float(row.get("longitude", "")),
                "source": SOURCE_SLUG,
            },
            edges=edges,
            text_to_embed=row.get("displayTitle", "") or row.get("name", ""),
            license=LICENSE,
            redistribute=True,
            license_note=LICENSE_NOTE,
        )


def _events(path: Path) -> Iterator[LexicalRecord]:
    for row in _read_csv(path):
        lookup = row.get("eventLookup", "") or row.get("event", "")
        if not lookup:
            continue
        verses = _explode_verses(row.get("verses", ""))
        edges = [
            GraphEdge(to_id=f"verse:{ref}", rel_type="MENTIONS", properties={}) for ref in verses
        ]
        yield LexicalRecord(
            record_type="Event",
            id=f"event:{lookup}",
            properties={
                "eventLookup": lookup,
                "title": row.get("displayTitle", "") or row.get("title", ""),
                "year": _safe_int(row.get("year", "")),
                "source": SOURCE_SLUG,
            },
            edges=edges,
            text_to_embed=row.get("displayTitle", "") or row.get("title", ""),
            license=LICENSE,
            redistribute=True,
            license_note=LICENSE_NOTE,
        )


def _safe_int(s: str) -> int | None:
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def _safe_float(s: str) -> float | None:
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _iter_records(source_dir: Path) -> Iterator[LexicalRecord]:
    csv_dir = source_dir / "CSV"
    people_csv = csv_dir / "People.csv"
    places_csv = csv_dir / "Places.csv"
    events_csv = csv_dir / "Events.csv"
    if people_csv.exists():
        yield from _people(people_csv)
    if places_csv.exists():
        yield from _places(places_csv)
    if events_csv.exists():
        yield from _events(events_csv)


def ingest_theographic(source_dir: Path, settings: Settings) -> dict[str, int]:
    driver = get_lexical_driver(settings)
    try:
        return upsert_records(driver, _iter_records(source_dir))
    finally:
        driver.close()
