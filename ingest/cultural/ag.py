"""Assemblies of God Statement of Fundamental Truths (16 truths) adapter."""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import ag_truths_accordion
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "ag"
WORK_ID = "ag-fundamental-truths"
TRADITION: Literal["pentecostal"] = "pentecostal"
LICENSE = "©Assemblies-of-God"
REDISTRIBUTE = False
LICENSE_NOTE = (
    "AG Fundamental Truths © General Council of the Assemblies of God; personal ingest only"
)
CANONICAL_URL = "https://ag.org/Beliefs/Statement-of-Fundamental-Truths"
FALLBACK_URLS: list[str] = []
WORK_TITLE = "Statement of Fundamental Truths"
DATE_WRITTEN = "1916"
EXPECTED = (16, 16)


def parse(raw: bytes) -> list[CulturalChunk]:
    truths = ag_truths_accordion(raw)
    out: list[CulturalChunk] = []
    for t in truths:
        anchor = f"AG.A{t['number']:02d}"
        text_to_embed = f"{t['title']}. {t['text']}"
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=WORK_ID,
                    work_title=WORK_TITLE,
                    author="General Council of the Assemblies of God",
                    date_written=DATE_WRITTEN,
                    is_confessional_text=True,
                    anchor_id=anchor,
                    language="en",
                    translator=None,
                ),
                text=t["text"],
                text_to_embed=text_to_embed,
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
