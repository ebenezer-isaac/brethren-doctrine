"""UMC Articles of Religion (Wesleyan-Methodist 25 Articles, 1784) adapter."""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import umc_h4_articles
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "umc"
WORK_ID = "umc-articles"
TRADITION: Literal["methodist"] = "methodist"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://www.umc.org/en/content/articles-of-religion"
FALLBACK_URLS: list[str] = []
WORK_TITLE = "Articles of Religion of the Methodist Church"
DATE_WRITTEN = "1784"
EXPECTED = (24, 26)


def parse(raw: bytes) -> list[CulturalChunk]:
    arts = umc_h4_articles(raw)
    out: list[CulturalChunk] = []
    for a in arts:
        if a["article"] < 1 or a["article"] > 25:
            continue
        anchor = f"UMC.A{a['article']:02d}"
        text_to_embed = f"{a['title']}. {a['text']}"
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=WORK_ID,
                    work_title=WORK_TITLE,
                    author="John Wesley (abridged from Thirty-Nine Articles)",
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
