"""Thirty-Nine Articles of Religion adapter (Pipeline 1 cultural, stub).

Stub adapter: deferred to live-scrape pass. scrape() returns an empty list when
BD_CULTURAL_LIVE_SCRAPE is unset. Live implementation pulls from CANONICAL_URL
(with FALLBACK_URLS) per docs/INGESTION_PATTERNS.md politeness rules.
"""

from __future__ import annotations

from ingest.cultural._adapter_stub import SKIP_LIVE_SCRAPE
from ingest.models import CulturalChunk

SOURCE_SLUG = "articles-39"
WORK_ID = "articles-39"
TRADITION = "anglican"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://justus.anglican.org/resources/bcp/1662/articles.htm"
FALLBACK_URLS: list[str] = ["https://en.wikisource.org/wiki/Thirty-Nine_Articles"]
EXPECTED = (39, 39)


def scrape() -> list[CulturalChunk]:
    if SKIP_LIVE_SCRAPE:
        return []
    raise NotImplementedError(
        f"{SOURCE_SLUG} live scrape not implemented in this session; "
        "set BD_CULTURAL_LIVE_SCRAPE=1 only after the per-source live implementation lands"
    )


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED
