"""Ecumenical Conciliar texts adapter.

Pulls the major historic creeds and definitions from Wikisource / Wikipedia,
each emitted as one CulturalChunk with anchor `<Council>.<Section>`. Coverage
in v1: Apostles' Creed, Nicene Creed (325 + 381), Chalcedonian Definition (451),
Athanasian Creed. Council canons are deferred to a v1.5 pass.
"""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import fetch_with_politeness, scrape_source
from ingest.cultural._html import wikisource_article_paragraphs
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "conciliar"
TRADITION: Literal["patristic"] = "patristic"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://en.wikisource.org/wiki/Nicene_Creed"
FALLBACK_URLS: list[str] = []
EXPECTED = (3, 20)

# Each creed registers a distinct source.work_id (Decision 16) so the four
# creeds fan out under four Work nodes within the shared patristic tradition.
# Tuple shape: (key, work_title, url, date_written, anchor, work_id).
SOURCES: list[tuple[str, str, str, str, str, str]] = [
    (
        "Apostles",
        "Apostles' Creed",
        "https://en.wikisource.org/wiki/Apostles%27_Creed",
        "c. 4th century",
        "Apostles.Creed",
        "conciliar.apostles",
    ),
    (
        "Nicene",
        "Nicene Creed (325/381)",
        "https://en.wikisource.org/wiki/Nicene_Creed",
        "325",
        "Nicaea325.Creed",
        "conciliar.niceno-constantinopolitan-creed",
    ),
    (
        "Athanasian",
        "Athanasian Creed (Quicunque vult)",
        "https://en.wikisource.org/wiki/Athanasian_Creed",
        "c. 5th-6th century",
        "Athanasian.Creed",
        "conciliar.athanasian-creed",
    ),
    (
        "Chalcedon",
        "Chalcedonian Definition (451)",
        "https://en.wikipedia.org/wiki/Chalcedonian_Definition",
        "451",
        "Chalcedon451.Definition",
        "conciliar.chalcedon-definition",
    ),
]


def parse(
    raw: bytes, anchor: str, work_title: str, date_written: str, work_id: str
) -> CulturalChunk | None:
    paras = wikisource_article_paragraphs(raw)
    text_parts = [p for p in paras if not p.startswith("# ")]
    body = " ".join(text_parts).strip()
    if not body or len(body) < 200:
        return None
    return CulturalChunk(
        chunk_id=f"{SOURCE_SLUG}.{anchor}",
        tradition=TRADITION,
        source=CulturalChunkSource(
            work_id=work_id,
            work_title=work_title,
            author="Ecumenical council / early church",
            date_written=date_written,
            is_confessional_text=True,
            anchor_id=anchor,
            language="en",
            translator="Wikisource / NPNF",
        ),
        text=body,
        text_to_embed=f"{work_title}. {body}",
        license=LICENSE,
        redistribute=REDISTRIBUTE,
        license_note=None,
    )


def scrape() -> list[CulturalChunk]:
    out: list[CulturalChunk] = []
    last_request: dict[str, float] = {}
    for _key, work_title, url, date_written, anchor, work_id in SOURCES:
        try:
            raw = fetch_with_politeness(url, last_request_by_host=last_request)
        except Exception:
            continue
        chunk = parse(raw, anchor, work_title, date_written, work_id)
        if chunk is not None:
            out.append(chunk)
    return out


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED


_ = scrape_source
