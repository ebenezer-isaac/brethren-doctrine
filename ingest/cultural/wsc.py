"""Westminster Shorter Catechism (1647) adapter.

Source: opc.org. 107 Q&A pairs.
"""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import opc_qa_blocks
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "wsc"
WORK_ID = "wsc"
TRADITION: Literal["reformed"] = "reformed"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://www.opc.org/sc.html"
FALLBACK_URLS: list[str] = [
    "https://www.reformed.org/documents/wsc/",
]
WORK_TITLE = "Westminster Shorter Catechism"
DATE_WRITTEN = "1647"
EXPECTED = (100, 115)


def parse(raw: bytes) -> list[CulturalChunk]:
    qs = opc_qa_blocks(raw)
    out: list[CulturalChunk] = []
    for q in qs:
        anchor = f"WSC.Q{q['q_num']:03d}"
        text = f"Q. {q['q_num']}. {q['question']} A. {q['answer']}"
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=WORK_ID,
                    work_title=WORK_TITLE,
                    author="Westminster Assembly",
                    date_written=DATE_WRITTEN,
                    is_confessional_text=True,
                    anchor_id=anchor,
                    language="en",
                    translator=None,
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
