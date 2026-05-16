"""OCA Hopko 'Orthodox Faith' adapter.

The 4-volume work is a tree of leaf articles under
`/orthodoxy/the-orthodox-faith/<volume>/<chapter>/<article>`. The scraper
walks the index page two levels deep to discover article URLs, then fetches
each leaf and emits one chunk per article.
"""

from __future__ import annotations

from typing import Literal
from urllib.parse import urljoin

from ingest.cultural._common import fetch_with_politeness
from ingest.cultural._html import oca_article_paragraphs
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "oca-hopko"
WORK_ID = "oca-hopko"
TRADITION: Literal["eastern-orthodox"] = "eastern-orthodox"
LICENSE = "©OCA-Hopko-estate"
REDISTRIBUTE = False
LICENSE_NOTE = "Hopko 'Orthodox Faith' © OCA / Hopko estate; personal ingest only"
ROOT = "https://www.oca.org/orthodoxy/the-orthodox-faith"
CANONICAL_URL = ROOT
FALLBACK_URLS: list[str] = []
WORK_TITLE = "The Orthodox Faith"
AUTHOR = "Thomas Hopko"
DATE_WRITTEN = "1981"
EXPECTED = (40, 200)

MAX_LEAVES = 200


def _crawl_links(start_url: str, max_depth: int = 3) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    queue: list[tuple[str, int]] = [(start_url, 0)]
    last_request: dict[str, float] = {}
    while queue and len(out) < MAX_LEAVES:
        url, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            raw = fetch_with_politeness(url, last_request_by_host=last_request)
        except Exception:
            continue
        info = oca_article_paragraphs(raw)
        if info["text"] and len(info["text"]) > 400 and depth >= 2:
            out.append(url)
        if depth < max_depth:
            for child in info["child_links"][:30]:
                full = urljoin(url, child)
                if full not in seen and full.startswith(ROOT):
                    queue.append((full, depth + 1))
    return out


def parse_article(raw: bytes, anchor: str) -> CulturalChunk | None:
    info = oca_article_paragraphs(raw)
    body = info["text"]
    if not body or len(body) < 100:
        return None
    return CulturalChunk(
        chunk_id=f"{SOURCE_SLUG}.{anchor}",
        tradition=TRADITION,
        source=CulturalChunkSource(
            work_id=WORK_ID,
            work_title=WORK_TITLE,
            author=AUTHOR,
            date_written=DATE_WRITTEN,
            is_confessional_text=False,
            anchor_id=anchor,
            language="en",
            translator=None,
        ),
        text=body,
        text_to_embed=f"{info['title']}. {body}",
        license=LICENSE,
        redistribute=REDISTRIBUTE,
        license_note=LICENSE_NOTE,
    )


def scrape() -> list[CulturalChunk]:
    article_urls = _crawl_links(ROOT, max_depth=4)
    out: list[CulturalChunk] = []
    last_request: dict[str, float] = {}
    for url in article_urls:
        try:
            raw = fetch_with_politeness(url, last_request_by_host=last_request)
        except Exception:
            continue
        anchor = url.replace(ROOT + "/", "").replace("/", ".")
        anchor = f"OCA.{anchor}" if not anchor.startswith("OCA") else anchor
        chunk = parse_article(raw, anchor)
        if chunk is not None:
            out.append(chunk)
        if len(out) >= MAX_LEAVES:
            break
    return out


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED


# Re-exports for orchestrator use; satisfies import-tracking discipline.
__all__ = ["scrape", "parse_article", "expected_chunk_count"]
