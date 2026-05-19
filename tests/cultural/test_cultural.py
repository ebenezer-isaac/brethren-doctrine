"""Unit tests for Pipeline 1 cultural adapters and infrastructure."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from ingest.cultural import autotag, brethren_parsed
from ingest.cultural._common import (
    POLITENESS_GAP_SECONDS,
    fetch_with_politeness,
    upsert_chunks,
)
from ingest.models import CulturalChunk, CulturalChunkSource, DoctrineTag

ADAPTER_NAMES = [
    "schleitheim",
    "augsburg",
    "heidelberg",
    "belgic",
    "dort",
    "wcf",
    "wlc_catechism",
    "wsc",
    "lbc_1689",
    "articles_39",
    "umc",
    "ag",
    "oca_hopko",
    "vatican_ccc",
    "vatican_dv",
    "ccel_anf",
    "ccel_npnf1",
    "ccel_npnf2",
    "conciliar",
    "stem_publishing",
    "bcp_1662",
    "brethren_parsed",
]


@pytest.mark.parametrize("name", ADAPTER_NAMES)
def test_adapter_module_imports_and_exports_contract(name: str) -> None:
    import importlib

    mod = importlib.import_module(f"ingest.cultural.{name}")
    assert hasattr(mod, "SOURCE_SLUG") and isinstance(mod.SOURCE_SLUG, str)
    assert hasattr(mod, "TRADITION") and isinstance(mod.TRADITION, str)
    assert hasattr(mod, "LICENSE") and isinstance(mod.LICENSE, str)
    assert hasattr(mod, "REDISTRIBUTE") and isinstance(mod.REDISTRIBUTE, bool)
    assert hasattr(mod, "CANONICAL_URL") and isinstance(mod.CANONICAL_URL, str)
    assert isinstance(mod.FALLBACK_URLS, list)
    assert callable(mod.scrape)
    assert callable(mod.expected_chunk_count)
    low, high = mod.expected_chunk_count()
    assert isinstance(low, int) and isinstance(high, int) and low <= high


def test_brethren_parsed_reads_local_corpus() -> None:
    chunks = brethren_parsed.scrape()
    assert len(chunks) >= 150
    assert all(c.tradition == "plymouth-brethren" for c in chunks)
    assert all(c.license == "parsed-sanitized" for c in chunks)
    assert all(c.redistribute is False for c in chunks)
    chunk_ids = [c.chunk_id for c in chunks]
    assert len(chunk_ids) == len(set(chunk_ids))


def test_fetch_with_politeness_enforces_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    state: dict[str, float] = {}
    calls: list[float] = []

    class FakeResp:
        def __init__(self) -> None:
            self.read_called = False

        def read(self) -> bytes:
            calls.append(time.monotonic())
            return b"ok"

        def __enter__(self) -> FakeResp:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    def fake_urlopen(req: Any, timeout: float = 30.0) -> FakeResp:
        return FakeResp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    t0 = time.monotonic()
    fetch_with_politeness("https://example.com/a", last_request_by_host=state)
    fetch_with_politeness("https://example.com/b", last_request_by_host=state)
    elapsed = time.monotonic() - t0
    assert elapsed >= POLITENESS_GAP_SECONDS - 0.1


def _fixture_chunk(idx: int) -> CulturalChunk:
    return CulturalChunk(
        chunk_id=f"fixture.{idx}",
        tradition="reformed",
        source=CulturalChunkSource(
            work_id="fixture",
            work_title="Fixture",
            author=None,
            date_written="2026",
            is_confessional_text=False,
            anchor_id=f"fx.{idx}",
            language="en",
        ),
        text=f"text {idx}",
        text_to_embed=f"text {idx}",
        license="public_domain",
        redistribute=True,
        license_note=None,
    )


class _CapturingResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def single(self) -> dict[str, int]:
        return {"upserted": len(self._rows)}

    def consume(self) -> None:
        return None


class _CapturingSession:
    def __init__(self, captured: dict[str, list[dict[str, Any]]]) -> None:
        self._captured = captured

    def __enter__(self) -> _CapturingSession:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def run(self, cypher: str, **params: Any) -> _CapturingResult:
        rows = list(params.get("rows", []))
        if "MERGE (c:CulturalChunk" in cypher:
            self._captured["chunk_rows"] = rows
        else:
            self._captured["work_rows"] = rows
        return _CapturingResult(rows)


class _CapturingDriver:
    def __init__(self) -> None:
        self.captured: dict[str, list[dict[str, Any]]] = {}

    def session(self) -> _CapturingSession:
        return _CapturingSession(self.captured)


def _redistribute_false_chunk() -> CulturalChunk:
    # Copyrighted source: verbatim `text` MUST NOT be persisted; the
    # redistribute-safe `text_to_embed` surface is distinct and shorter.
    return CulturalChunk(
        chunk_id="ag.AG.A01",
        tradition="pentecostal",
        source=CulturalChunkSource(
            work_id="ag-fundamental-truths",
            work_title="Statement of Fundamental Truths",
            author=None,
            date_written="1916",
            is_confessional_text=True,
            anchor_id="AG.A1",
            language="en",
        ),
        text="VERBATIM COPYRIGHTED PROSE that may not be redistributed in bulk.",
        text_to_embed="redistribute-safe paraphrase surface",
        license="©Assemblies-of-God",
        redistribute=False,
        license_note="personal ingest only",
    )


def test_upsert_redistribute_false_persists_embed_surface_not_verbatim_text() -> None:
    """A redistribute=false (copyrighted) source must persist text == text_to_embed.

    Regression for G-SHARED-1: check_redistribute returns a non-empty dict that
    is ALWAYS truthy, so the pre-fix guard `if check_redistribute(...)` treated
    every copyrighted license as redistributable and leaked verbatim `text`.
    This asserts the persisted CulturalChunk.text equals text_to_embed (guard
    denies bulk), and FAILS against the truthy-dict bug.
    """
    chunk = _redistribute_false_chunk()
    driver = _CapturingDriver()

    counts = upsert_chunks(driver, [chunk])  # type: ignore[arg-type]

    assert counts["CulturalChunk"] == 1
    rows = driver.captured["chunk_rows"]
    assert len(rows) == 1
    persisted = rows[0]["properties"]
    # The verbatim copyrighted prose must NOT reach the store.
    assert persisted["text"] == chunk.text_to_embed
    assert persisted["text"] != chunk.text
    assert persisted["text_to_embed"] == chunk.text_to_embed
    assert persisted["redistribute"] is False


def test_upsert_public_domain_persists_verbatim_text() -> None:
    """A public_domain / redistribute=true source persists verbatim `text`."""
    chunk = CulturalChunk(
        chunk_id="wcf.WCF.1.1",
        tradition="reformed",
        source=CulturalChunkSource(
            work_id="wcf",
            work_title="Westminster Confession of Faith",
            author=None,
            date_written="1646",
            is_confessional_text=True,
            anchor_id="WCF.1.1",
            language="en",
        ),
        text="Although the light of nature, and the works of creation and providence",
        text_to_embed="WCF 1.1 embed surface",
        license="public_domain",
        redistribute=True,
        license_note=None,
    )
    driver = _CapturingDriver()

    upsert_chunks(driver, [chunk])  # type: ignore[arg-type]

    persisted = driver.captured["chunk_rows"][0]["properties"]
    assert persisted["text"] == chunk.text
    assert persisted["text"] != chunk.text_to_embed
    assert persisted["text_to_embed"] == chunk.text_to_embed
    assert persisted["redistribute"] is True


def test_autotag_batches_130_into_3_groups() -> None:
    chunks = [_fixture_chunk(i) for i in range(130)]
    observed: list[int] = []

    def fake_tag_batch(payload: list[dict[str, str]]) -> list[list[DoctrineTag]]:
        observed.append(len(payload))
        return [
            [
                DoctrineTag(
                    doctrine_coarse="theology-proper",
                    doctrine_fine="theology-proper",
                    stance="affirms",
                    confidence=0.9,
                    evidence_phrase="The Father, the Son, and the Holy Spirit",
                )
            ]
            for _ in payload
        ]

    high, low = autotag.tag_chunks(chunks, fake_tag_batch)
    assert observed == [50, 50, 30]
    assert len(high) == 130
    assert len(low) == 0


def test_autotag_routes_by_confidence(tmp_path: Path) -> None:
    chunks = [_fixture_chunk(i) for i in range(4)]
    confidences = [0.5, 0.6, 0.85, 0.92]

    def fake_tag_batch(payload: list[dict[str, str]]) -> list[list[DoctrineTag]]:
        return [
            [
                DoctrineTag(
                    doctrine_coarse="theology-proper",
                    doctrine_fine="theology-proper",
                    stance="affirms",
                    confidence=confidences[i],
                    evidence_phrase="The Father, the Son, and the Holy Spirit",
                )
            ]
            for i in range(len(payload))
        ]

    high, low = autotag.tag_chunks(chunks, fake_tag_batch, low_confidence_dir=tmp_path)
    assert len(high) == 3
    assert len(low) == 1
    out = tmp_path / "low_confidence.jsonl"
    assert out.exists()
    assert sum(1 for _ in out.open()) == 1


def test_autotag_rejects_extra_payload_keys() -> None:
    chunks = [_fixture_chunk(0)]

    def bad_tag(payload: list[dict[str, str]]) -> list[list[DoctrineTag]]:
        return [[]]

    autotag.tag_chunks(chunks, bad_tag)


def test_autotag_payload_contains_only_chunk_id_and_text() -> None:
    chunks = [_fixture_chunk(0)]
    captured: list[list[dict[str, str]]] = []

    def capture(payload: list[dict[str, str]]) -> list[list[DoctrineTag]]:
        captured.append(payload)
        return [[]]

    autotag.tag_chunks(chunks, capture)
    assert captured
    assert set(captured[0][0].keys()) == {"chunk_id", "text"}


def test_autotag_rejects_more_than_5_tags() -> None:
    chunks = [_fixture_chunk(0)]

    def too_many_tags(payload: list[dict[str, str]]) -> list[list[DoctrineTag]]:
        return [
            [
                DoctrineTag(
                    doctrine_coarse="theology-proper",
                    doctrine_fine="theology-proper",
                    stance="affirms",
                    confidence=0.9,
                    evidence_phrase="example",
                )
                for _ in range(6)
            ]
        ]

    with pytest.raises(ValueError, match="max 5"):
        autotag.tag_chunks(chunks, too_many_tags)


def test_autotag_warns_on_canned_evidence(recwarn: pytest.WarningsRecorder) -> None:
    chunks = [_fixture_chunk(0)]

    def canned_tag(payload: list[dict[str, str]]) -> list[list[DoctrineTag]]:
        return [
            [
                DoctrineTag(
                    doctrine_coarse="theology-proper",
                    doctrine_fine="theology-proper",
                    stance="affirms",
                    confidence=0.95,
                    evidence_phrase="Great art Thou, O Lord, and greatly to be praised",
                )
            ]
        ]

    autotag.tag_chunks(chunks, canned_tag)
    assert any("anti-canned-output" in str(w.message) for w in recwarn.list)
