"""Thirty-Nine Articles of Religion (1571) adapter.

Primary source: justus.anglican.org has TLS issues per docs/INGESTION_PATTERNS.md.
We use the Wikisource fallback as canonical for stability.
"""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import wikisource_39_articles
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "articles-39"
WORK_ID = "articles-39"
TRADITION: Literal["anglican"] = "anglican"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://en.wikisource.org/wiki/Thirty-Nine_Articles_of_Religion"
FALLBACK_URLS: list[str] = [
    "https://en.wikisource.org/wiki/Thirty-Nine_Articles",
]
WORK_TITLE = "Thirty-Nine Articles of Religion"
DATE_WRITTEN = "1571"
EXPECTED = (39, 39)


def parse(raw: bytes) -> list[CulturalChunk]:
    arts = wikisource_39_articles(raw)
    out: list[CulturalChunk] = []
    for a in arts:
        if a["article"] < 1 or a["article"] > 39:
            continue
        anchor = f"39A.A{a['article']:02d}"
        text_to_embed = f"{a['title']}. {a['text']}"
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=WORK_ID,
                    work_title=WORK_TITLE,
                    author="Convocation of the Church of England",
                    date_written=DATE_WRITTEN,
                    is_confessional_text=True,
                    anchor_id=anchor,
                    language="en",
                    translator=None,
                ),
                text=a["text"],
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
