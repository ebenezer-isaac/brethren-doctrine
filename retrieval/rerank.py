"""BGE cross-encoder reranker.

Loads BAAI/bge-reranker-v2-m3 once per process. Heavy model; the constructor
takes an optional `model` parameter so tests can inject a stub.
"""

from __future__ import annotations

from typing import Protocol

from retrieval.hybrid import RetrievedChunk

MODEL_ID = "BAAI/bge-reranker-v2-m3"


class _Scorer(Protocol):
    def compute_score(self, pairs: list[list[str]]) -> list[float]:  # pragma: no cover
        ...


class BGEReranker:
    def __init__(self, model: _Scorer | None = None) -> None:
        if model is not None:
            self._model: _Scorer = model
            return
        try:
            from FlagEmbedding import FlagReranker

            self._model = FlagReranker(MODEL_ID, use_fp16=True)
        except Exception:
            self._model = _NullScorer()

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []
        pairs = [[query, c.text] for c in candidates]
        scores = self._model.compute_score(pairs)
        scored = list(zip(candidates, scores, strict=False))
        scored.sort(key=lambda kv: kv[1], reverse=True)
        out: list[RetrievedChunk] = []
        for chunk, score in scored[:top_k]:
            payload = dict(chunk.payload)
            payload["bge_rerank_score"] = float(score)
            out.append(
                RetrievedChunk(
                    id=chunk.id,
                    text=chunk.text,
                    score=float(score),
                    source_store=chunk.source_store,
                    license=chunk.license,
                    redistribute=chunk.redistribute,
                    payload=payload,
                )
            )
        return out


class _NullScorer:
    """Fallback when FlagEmbedding is unavailable. Returns 0.0 for every pair."""

    def compute_score(self, pairs: list[list[str]]) -> list[float]:
        return [0.0] * len(pairs)
