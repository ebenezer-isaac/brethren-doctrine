"""Schleitheim Confession (1527) adapter.

Wikisource page returns 404 in recent probes; we use anabaptists.org as
the canonical source. The confession has 7 articles.
"""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import schleitheim_articles
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "schleitheim"
WORK_ID = "schleitheim"
TRADITION: Literal["anabaptist"] = "anabaptist"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://anabaptists.org/history/the-schleitheim-confession.html"
FALLBACK_URLS: list[str] = [
    "https://en.wikisource.org/wiki/Schleitheim_Confession",
]
WORK_TITLE = "Schleitheim Confession"
DATE_WRITTEN = "1527"
EXPECTED = (7, 7)


def parse(raw: bytes) -> list[CulturalChunk]:
    arts = schleitheim_articles(raw)
    out: list[CulturalChunk] = []
    for a in arts:
        anchor = f"Schleitheim.A{a['article']}"
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=WORK_ID,
                    work_title=WORK_TITLE,
                    author="Michael Sattler (attrib.)",
                    date_written=DATE_WRITTEN,
                    is_confessional_text=True,
                    anchor_id=anchor,
                    language="en",
                    translator="John Howard Yoder",
                ),
                text=a["text"],
                text_to_embed=a["text"],
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
