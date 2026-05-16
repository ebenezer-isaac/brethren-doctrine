"""Tests for retrieval.rerank."""

from __future__ import annotations

import os

import pytest

from retrieval.hybrid import RetrievedChunk
from retrieval.rerank import BGEReranker


class _StubScorer:
    def __init__(self, scores: list[float]) -> None:
        self._scores = list(scores)
        self.calls: list[list[list[str]]] = []

    def compute_score(self, pairs: list[list[str]]) -> list[float]:
        self.calls.append(pairs)
        return self._scores[: len(pairs)]


def _chunk(id_: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        id=id_,
        text=text,
        score=0.0,
        source_store="lexical",
        license="public_domain",
        redistribute=True,
    )


def test_rerank_reorders_by_score() -> None:
    stub = _StubScorer([0.1, 0.9, 0.5])
    r = BGEReranker(model=stub)
    candidates = [_chunk("a", "A"), _chunk("b", "B"), _chunk("c", "C")]
    out = r.rerank("query", candidates, top_k=3)
    assert [c.id for c in out] == ["b", "c", "a"]


def test_rerank_top_k_caps_output() -> None:
    stub = _StubScorer([0.1, 0.9, 0.5])
    r = BGEReranker(model=stub)
    candidates = [_chunk("a", "A"), _chunk("b", "B"), _chunk("c", "C")]
    out = r.rerank("query", candidates, top_k=1)
    assert len(out) == 1
    assert out[0].id == "b"


def test_rerank_empty_returns_empty() -> None:
    stub = _StubScorer([])
    r = BGEReranker(model=stub)
    assert r.rerank("query", [], top_k=5) == []


def test_rerank_attaches_score_to_payload() -> None:
    stub = _StubScorer([0.42])
    r = BGEReranker(model=stub)
    out = r.rerank("q", [_chunk("a", "A")], top_k=1)
    assert out[0].payload["bge_rerank_score"] == 0.42


def test_rerank_called_with_pairs() -> None:
    stub = _StubScorer([0.1, 0.2])
    r = BGEReranker(model=stub)
    r.rerank("query", [_chunk("a", "A"), _chunk("b", "B")])
    assert stub.calls == [[["query", "A"], ["query", "B"]]]


def test_rerank_preserves_license_and_store() -> None:
    stub = _StubScorer([0.5])
    r = BGEReranker(model=stub)
    chunk = RetrievedChunk(
        id="x",
        text="t",
        score=0.0,
        source_store="cultural",
        license="CC-BY-NC-4.0",
        redistribute=False,
    )
    out = r.rerank("q", [chunk])
    assert out[0].source_store == "cultural"
    assert out[0].license == "CC-BY-NC-4.0"
    assert out[0].redistribute is False


@pytest.mark.skipif(
    os.environ.get("BD_RUN_INTEGRATION") != "1",
    reason="integration test requires FlagEmbedding + model download",
)
def test_load_real_bge_model() -> None:
    r = BGEReranker()
    candidates = [
        _chunk("right", "God is one being in three persons"),
        _chunk("wrong", "Recipes for bread"),
    ]
    out = r.rerank("trinity doctrine", candidates, top_k=1)
    assert out[0].id == "right"
