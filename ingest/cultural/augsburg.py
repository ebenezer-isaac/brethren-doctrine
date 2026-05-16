"""Augsburg Confession (1530) adapter.

Source: bookofconcord.org. Each article is on its own URL under
/augsburg-confession/<slug>/. The TOC page lists 28 articles with stable
slugs. We crawl each article page in turn.
"""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import boc_augsburg_paragraphs
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "augsburg"
WORK_ID = "augsburg"
TRADITION: Literal["lutheran"] = "lutheran"
LICENSE = "public_domain"
REDISTRIBUTE = True
BASE = "https://bookofconcord.org/augsburg-confession"
CANONICAL_URL = f"{BASE}/"
FALLBACK_URLS: list[str] = []
WORK_TITLE = "Augsburg Confession"
DATE_WRITTEN = "1530"
EXPECTED = (25, 30)

ARTICLE_SLUGS: list[tuple[int, str, str]] = [
    (1, "of-god", "Of God"),
    (2, "original-sin", "Of Original Sin"),
    (3, "son-of-god", "Of the Son of God"),
    (4, "of-justification", "Of Justification"),
    (5, "of-the-ministry", "Of the Ministry"),
    (6, "of-new-obedience", "Of New Obedience"),
    (7, "of-the-church", "Of the Church"),
    (8, "what-the-church-is", "What the Church Is"),
    (9, "of-baptism", "Of Baptism"),
    (10, "of-the-lords-supper", "Of the Lord's Supper"),
    (11, "of-confession", "Of Confession"),
    (12, "of-repentance", "Of Repentance"),
    (13, "of-the-use-of-the-sacraments", "Of the Use of the Sacraments"),
    (14, "of-ecclesiastical-order", "Of Ecclesiastical Order"),
    (15, "of-ecclesiastical-rites", "Of Ecclesiastical Rites"),
    (16, "of-civil-affairs", "Of Civil Affairs"),
    (17, "of-christs-return-to-judgment", "Of Christ's Return to Judgment"),
    (18, "of-free-will", "Of Free Will"),
    (19, "of-the-cause-of-sin", "Of the Cause of Sin"),
    (20, "of-good-works", "Of Good Works"),
    (21, "of-the-worship-of-the-saints", "Of the Worship of the Saints"),
]


def parse_article_page(raw: bytes, article: int, title: str) -> CulturalChunk | None:
    paras = boc_augsburg_paragraphs(raw)
    body = " ".join(paras).strip()
    if not body:
        return None
    anchor = f"Augsburg.A{article:02d}"
    return CulturalChunk(
        chunk_id=f"{SOURCE_SLUG}.{anchor}",
        tradition=TRADITION,
        source=CulturalChunkSource(
            work_id=WORK_ID,
            work_title=WORK_TITLE,
            author="Philip Melanchthon (lead drafter)",
            date_written=DATE_WRITTEN,
            is_confessional_text=True,
            anchor_id=anchor,
            language="en",
            translator="F. Bente / W. H. T. Dau (Triglotta)",
        ),
        text=body,
        text_to_embed=f"{title}. {body}",
        license=LICENSE,
        redistribute=REDISTRIBUTE,
        license_note=None,
    )


def scrape() -> list[CulturalChunk]:
    out: list[CulturalChunk] = []
    for article, slug, title in ARTICLE_SLUGS:
        url = f"{BASE}/{slug}/"
        raw = scrape_source(f"{SOURCE_SLUG}.A{article:02d}", url, [])
        chunk = parse_article_page(raw, article, title)
        if chunk is not None:
            out.append(chunk)
    return out


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED
