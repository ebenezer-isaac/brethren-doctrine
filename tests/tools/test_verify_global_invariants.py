"""Tests for tools/verify_global_invariants.py."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import verify_global_invariants as g  # noqa: E402


def _driver_from(state: dict[str, int]) -> g._FakeDriver:
    def planner(q: str, p: dict[str, Any]) -> list[dict[str, Any]]:
        if "WHERE NOT (n)--()" in q:
            return [{"n": state["orphans"]}]
        if "WHERE c > 1" in q:
            return [{"dups": state["dup_strongs"]}]
        if "INSTANCE_OF" in q and "a = b" in q:
            return [{"n": state["self_loops"]}]
        if "l.gloss IS NULL" in q:
            return [{"n": state["missing_gloss"]}]
        if q.startswith("MATCH ()-[r:"):
            return [{"n": state["rel_count"]}]
        if "l.id = $sid" in q:
            return [{"n": state["placeholder"]}]
        return [{"n": 0}]
    return g._FakeDriver(planner)


CLEAN = {"orphans": 0, "dup_strongs": 0, "self_loops": 0,
         "missing_gloss": 0, "rel_count": 1000, "placeholder": 0}
DIRTY_ORPHANS = {**CLEAN, "orphans": 5}
DIRTY_DUPS = {**CLEAN, "dup_strongs": 3}
DIRTY_LOOPS = {**CLEAN, "self_loops": 1}
DIRTY_GLOSS = {**CLEAN, "missing_gloss": 9}
DIRTY_EDGES = {**CLEAN, "rel_count": 0}
DIRTY_PLACEHOLDER = {**CLEAN, "placeholder": 1}


CFG = g.Config(
    labels=("Lemma", "Verse"),
    expected_edges={"IN_VERSE": {"low": 100}},
    placeholder_ids=("PLACEHOLDER",),
)


def test_clean_passes_all() -> None:
    r = g.run_all(_driver_from(CLEAN), CFG)
    assert all(x.ok for x in r), [x.format() for x in r if not x.ok]


def test_orphans_caught() -> None:
    r = g.run_all(_driver_from(DIRTY_ORPHANS), CFG)
    bad = [x for x in r if not x.ok]
    assert any(x.name.startswith("orphan_free") for x in bad)


def test_duplicate_strongs_caught() -> None:
    r = g.run_all(_driver_from(DIRTY_DUPS), CFG)
    assert any(x.name == "lemma_distinct_per_strong" and not x.ok for x in r)


def test_self_loops_caught() -> None:
    r = g.run_all(_driver_from(DIRTY_LOOPS), CFG)
    assert any(x.name == "instance_of_no_self_loops" and not x.ok for x in r)


def test_gloss_caught() -> None:
    r = g.run_all(_driver_from(DIRTY_GLOSS), CFG)
    assert any(x.name == "gloss_coverage" and not x.ok for x in r)


def test_edge_floor_caught() -> None:
    r = g.run_all(_driver_from(DIRTY_EDGES), CFG)
    assert any(x.name.startswith("edge_floor") and not x.ok for x in r)


def test_placeholder_caught() -> None:
    r = g.run_all(_driver_from(DIRTY_PLACEHOLDER), CFG)
    assert any(x.name.startswith("no_placeholder") and not x.ok for x in r)


def test_main_clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    edges = tmp_path / "edges.json"
    edges.write_text('{"edges": {"IN_VERSE": {"low": 100}}}', encoding="utf-8")
    drv = _driver_from(CLEAN)
    rc = g.main(
        ["--labels", "Lemma", "Verse",
         "--expected-edges", str(edges)],
        driver_factory=lambda: drv,
    )
    assert rc == 0


def test_main_dirty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    edges = tmp_path / "edges.json"
    edges.write_text('{"edges": {"IN_VERSE": {"low": 100}}}', encoding="utf-8")
    drv = _driver_from(DIRTY_ORPHANS)
    rc = g.main(
        ["--labels", "Lemma", "Verse",
         "--expected-edges", str(edges)],
        driver_factory=lambda: drv,
    )
    assert rc == 1


def test_self_test_exits_zero() -> None:
    assert g.main(["--self-test"]) == 0


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        g.main(["--help"])
    assert exc.value.code == 0
