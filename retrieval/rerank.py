"""Stage 3: cross-encoder rerank, K_fused -> top-N.

Per docs/TIER_2_SPEC.md §5 Stage 3, with the authority-aware tagging trick
from research/hybrid_search_rerank_2026.md §4 Layer B: prepending
`[authority:N] [type:T]` to each candidate so the cross-encoder can bias
toward higher-authority sources without a hard rule.

Lazy model load: importing this module is cheap; the BGE checkpoint is only
fetched on the first call to `rerank()`. CPU-only by default; the spec budgets
~500ms at K=60 for personal-use single-digit QPS.
"""

from __future__ import annotations

import os
from threading import Lock

from retrieval.hybrid import Hit

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
MAX_LENGTH = 512

_reranker = None
_reranker_lock = Lock()


def _get_reranker():
    global _reranker
    with _reranker_lock:
        if _reranker is None:
            from sentence_transformers import CrossEncoder

            _reranker = CrossEncoder(RERANKER_MODEL, max_length=MAX_LENGTH)
    return _reranker


def _tag(hit: Hit) -> str:
    payload = hit.payload
    authority = payload.get("authority_level", 4)
    source_type = payload.get("source_type", "external")
    return f"[authority:{authority}] [type:{source_type}] {payload.get('text','')}"


def rerank(query: str, hits: list[Hit], top_n: int = 10, batch_size: int = 16) -> list[Hit]:
    """Cross-encoder rerank with authority-aware tagging. Returns top_n hits sorted desc."""
    if not hits:
        return []

    reranker = _get_reranker()
    pairs = [(query, _tag(h)) for h in hits]
    scores = reranker.predict(pairs, batch_size=batch_size, show_progress_bar=False)

    rescored = [
        Hit(chunk_id=h.chunk_id, score=float(s), payload=h.payload)
        for h, s in zip(hits, scores, strict=True)
    ]
    rescored.sort(key=lambda h: h.score, reverse=True)
    return rescored[:top_n]
