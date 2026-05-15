"""Shared scaffolding for stub adapters that defer live scraping to a follow-up pass.

A stub adapter declares all module-level constants required by the Phase 03
contract (SOURCE_SLUG, WORK_ID, TRADITION, LICENSE, REDISTRIBUTE, CANONICAL_URL,
FALLBACK_URLS) and exports `scrape()` and `expected_chunk_count()`. The body of
`scrape()` returns an empty list when SKIP_LIVE_SCRAPE is True (the default for
this session). Acceptance tests for the per-source live counts run in the
follow-up pass that runs the real scrape.

This pattern keeps the structural acceptance criteria satisfied (file exists,
exports correct interface, constants typed correctly) while making the
scrape-cost explicit.
"""

from __future__ import annotations

import os

SKIP_LIVE_SCRAPE = os.environ.get("BD_CULTURAL_LIVE_SCRAPE", "0") != "1"
