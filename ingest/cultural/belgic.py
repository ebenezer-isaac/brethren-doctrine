"""Belgic Confession (1561) adapter.

Source: crcna.org. 37 articles.
"""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import crcna_article_blocks
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "belgic"
WORK_ID = "belgic"
TRADITION: Literal["reformed"] = "reformed"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://www.crcna.org/welcome/beliefs/confessions/belgic-confession"
FALLBACK_URLS: list[str] = []
WORK_TITLE = "Belgic Confession"
DATE_WRITTEN = "1561"
EXPECTED = (37, 37)


def parse(raw: bytes) -> list[CulturalChunk]:
    arts = crcna_article_blocks(raw)
    out: list[CulturalChunk] = []
    for a in arts:
        if a["article"] < 1 or a["article"] > 37:
            continue
        anchor = f"Belgic.A{a['article']:02d}"
        body = a["text"]
        text_to_embed = f"{a['title']}. {body}" if a["title"] else body
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=WORK_ID,
                    work_title=WORK_TITLE,
                    author="Guido de Brès",
                    date_written=DATE_WRITTEN,
                    is_confessional_text=True,
                    anchor_id=anchor,
                    language="en",
                    translator="Christian Reformed Church",
                ),
                text=body,
                text_to_embed=text_to_embed,
                license=LICENSE,
                redistribute=REDISTRIBUTE,
                license_note=None,
            )
        )
    return out


def scrape() -> list[CulturalChunk]:
    raw = scrape_source(SOURCE_SLUG, CANONICAL_URL, FALLBACK_URLS)
    return parse(raw)


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED
