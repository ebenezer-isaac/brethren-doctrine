"""Build the response envelope per docs/TIER_2_SPEC.md §5.

Stage 4 (authority + recency boost) is a small post-rerank nudge; recency
isn't usable yet because parsed/ docs lack stable date fields, so we apply
authority-only.
"""

from __future__ import annotations

from typing import Any

from retrieval.hybrid import Hit

CITATION_BASE = "brethren://"

# Stage 4 caps from spec §5. Authority nudges ties, never overrides rerank.
AUTHORITY_BOOST = 0.08


def _citation(payload: dict[str, Any]) -> str:
    source_type = payload.get("source_type", "external")
    source_doc = payload.get("source_doc", "unknown")
    chunk_id = payload.get("chunk_id", "")
    n = chunk_id.rsplit("_", 1)[-1] if "_" in chunk_id else chunk_id
    return f"{CITATION_BASE}{source_type}/{source_doc}#chunk-{n}"


def _boost(hit: Hit) -> float:
    """Authority boost only. Recency lands when parsed docs carry preached_at dates."""
    authority_level = hit.payload.get("authority_level", 4)
    return hit.score + AUTHORITY_BOOST * (authority_level / 4.0)


def apply_boost(hits: list[Hit]) -> list[Hit]:
    boosted = [Hit(chunk_id=h.chunk_id, score=_boost(h), payload=h.payload) for h in hits]
    boosted.sort(key=lambda h: h.score, reverse=True)
    return boosted


def build_envelope(
    hits: list[Hit],
    total_candidates: int,
    elapsed_ms: float,
    intent: str,
) -> dict[str, Any]:
    """Spec §5 envelope. Disagreements + graph_context land in M4-M6."""
    if not hits:
        return {
            "status": "no_results",
            "answer_context": [],
            "disagreements": [],
            "pagination": {"total": total_candidates, "returned": 0, "next_cursor": None},
            "meta": {"elapsed_ms": round(elapsed_ms, 1), "intent": intent},
        }

    answer_context = []
    for h in hits:
        p = h.payload
        answer_context.append(
            {
                "chunk_id": p.get("chunk_id"),
                "score": round(h.score, 4),
                "source_type": p.get("source_type"),
                "source_doc": p.get("source_doc"),
                "authority_level": p.get("authority_level"),
                "chunk_type": p.get("chunk_type"),
                "section": p.get("section"),
                "themes": p.get("themes", []),
                "scripture_refs": p.get("scripture_refs", []),
                "text": p.get("text", ""),
                "citations": [_citation(p)],
                "graph_context": None,
            }
        )

    return {
        "status": "ok",
        "answer_context": answer_context,
        "disagreements": [],
        "pagination": {
            "total": total_candidates,
            "returned": len(answer_context),
            "next_cursor": None,
        },
        "meta": {"elapsed_ms": round(elapsed_ms, 1), "intent": intent},
    }
