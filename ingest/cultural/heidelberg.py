"""Heidelberg Catechism (1563) adapter.

Source: crcna.org. 129 Q&A (the catechism proper); the parser may extract a
few extra headings, which we filter by q_num <= 129.
"""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import crcna_qa_blocks
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "heidelberg"
WORK_ID = "heidelberg"
TRADITION: Literal["reformed"] = "reformed"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://www.crcna.org/welcome/beliefs/confessions/heidelberg-catechism"
FALLBACK_URLS: list[str] = []
WORK_TITLE = "Heidelberg Catechism"
DATE_WRITTEN = "1563"
EXPECTED = (125, 135)


def parse(raw: bytes) -> list[CulturalChunk]:
    qs = crcna_qa_blocks(raw)
    out: list[CulturalChunk] = []
    for q in qs:
        if q["q_num"] < 1 or q["q_num"] > 129:
            continue
        if not q["answer"]:
            continue
        anchor = f"HC.Q{q['q_num']:03d}"
        text = f"Q. {q['q_num']}. {q['question']} A. {q['answer']}"
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=WORK_ID,
                    work_title=WORK_TITLE,
                    author="Zacharias Ursinus; Caspar Olevianus",
                    date_written=DATE_WRITTEN,
                    is_confessional_text=True,
                    anchor_id=anchor,
                    language="en",
                    translator="Christian Reformed Church",
                ),
                text=text,
                text_to_embed=text,
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
