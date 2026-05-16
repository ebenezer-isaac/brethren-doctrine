"""Dogmatic Constitution Dei Verbum (Vatican II, 1965) adapter.

26 numbered paragraphs covering revelation, scripture, and tradition.
"""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import vatican_council_paragraphs
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "vatican-dv"
WORK_ID = "vatican-dv"
TRADITION: Literal["catholic-magisterial"] = "catholic-magisterial"
LICENSE = "©Libreria-Editrice-Vaticana"
REDISTRIBUTE = False
LICENSE_NOTE = "Dei Verbum © Libreria Editrice Vaticana; personal ingest only"
CANONICAL_URL = (
    "https://www.vatican.va/archive/hist_councils/ii_vatican_council/"
    "documents/vat-ii_const_19651118_dei-verbum_en.html"
)
FALLBACK_URLS: list[str] = []
WORK_TITLE = "Dogmatic Constitution on Divine Revelation (Dei Verbum)"
DATE_WRITTEN = "1965"
EXPECTED = (24, 28)


def parse(raw: bytes) -> list[CulturalChunk]:
    paras = vatican_council_paragraphs(raw)
    out: list[CulturalChunk] = []
    for p in paras:
        if p["paragraph"] < 1 or p["paragraph"] > 30:
            continue
        anchor = f"DV.{p['paragraph']}"
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=WORK_ID,
                    work_title=WORK_TITLE,
                    author="Second Vatican Council",
                    date_written=DATE_WRITTEN,
                    is_confessional_text=True,
                    anchor_id=anchor,
                    language="en",
                    translator="Vatican Press (English)",
                ),
                text=p["text"],
                text_to_embed=p["text"],
                license=LICENSE,
                redistribute=REDISTRIBUTE,
                license_note=LICENSE_NOTE,
            )
        )
    return out


def scrape() -> list[CulturalChunk]:
    raw = scrape_source(SOURCE_SLUG, CANONICAL_URL, FALLBACK_URLS)
    return parse(raw)


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED
