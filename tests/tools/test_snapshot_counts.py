"""Tests for tools/snapshot_counts.py.

Use a fake driver populated with a small fixed dataset. Snapshot twice
without mutation -> hashes must be identical. Mutate one node prop ->
hashes must differ. The driver fixture also exercises the APOC fallback
path for property-key discovery.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import snapshot_counts as sc  # noqa: E402


def make_driver(nodes: list[dict[str, Any]], *, apoc: bool = False) -> sc._FakeDriver:
    def planner(q: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if "db.labels()" in q:
            return [{"label": l} for l in {n["label"] for n in nodes}]
        if "db.relationshipTypes()" in q:
            return [{"relationshipType": "REL_X"}]
        if "apoc.meta.nodeTypeProperties" in q:
            if not apoc:
                raise RuntimeError("apoc absent")
            lbl = params["label"]
            keys = sorted({k for n in nodes if n["label"] == lbl for k in n["props"]})
            return [{"propertyName": k} for k in keys]
        if q.startswith("MATCH (n:"):
            lbl = q.split("`")[1]
            rows = [n for n in nodes if n["label"] == lbl]
            if "count(n)" in q:
                return [{"n": len(rows)}]
            if "keys(n)" in q:
                keys = sorted({k for n in rows for k in n["props"]})
                return [{"k": k} for k in keys]
            if "properties(n)" in q:
                rows_sorted = sorted(rows, key=lambda r: (r["props"].get("id", ""), r["label"]))
                return [
                    {"p": dict(r["props"]), "eid": f"{r['label']}#{r['props'].get('id')}"}
                    for r in rows_sorted[: params.get("limit", 1000)]
                ]
        if q.startswith("MATCH ()-[r:"):
            return [{"n": 42}]
        return []

    return sc._FakeDriver(planner)


# ---------- determinism ----------

def test_double_snapshot_is_identical() -> None:
    nodes = [
        {"label": "Lemma", "props": {"id": "H7225", "gloss": "beginning"}},
        {"label": "Lemma", "props": {"id": "G746", "gloss": "beginning"}},
        {"label": "Verse", "props": {"id": "GEN 1:1", "ref": "GEN 1:1"}},
    ]
    drv = make_driver(nodes)
    a = sc.take_snapshot(drv)
    b = sc.take_snapshot(drv)
    assert a.to_dict() == b.to_dict()
    assert a.overall_hash() == b.overall_hash()


def test_snapshot_changes_when_data_mutates() -> None:
    nodes = [
        {"label": "Lemma", "props": {"id": "H7225", "gloss": "beginning"}},
    ]
    drv = make_driver(nodes)
    h1 = sc.take_snapshot(drv).overall_hash()
    nodes[0]["props"]["gloss"] = "head"
    h2 = sc.take_snapshot(drv).overall_hash()
    assert h1 != h2


def test_snapshot_counts_match() -> None:
    nodes = [
        {"label": "Verse", "props": {"id": f"V{i}"}} for i in range(7)
    ]
    drv = make_driver(nodes)
    snap = sc.take_snapshot(drv)
    assert snap.per_label_counts["Verse"] == 7


def test_snapshot_rel_counts() -> None:
    drv = make_driver([{"label": "L", "props": {"id": "1"}}])
    snap = sc.take_snapshot(drv)
    assert snap.per_rel_counts == {"REL_X": 42}


def test_property_keys_apoc_path() -> None:
    nodes = [
        {"label": "L", "props": {"id": "1", "a": "x"}},
        {"label": "L", "props": {"id": "2", "b": "y"}},
    ]
    drv = make_driver(nodes, apoc=True)
    keys = sc.property_keys_for_label(drv, "L")
    assert keys == ["a", "b", "id"]


def test_property_keys_fallback_path() -> None:
    nodes = [
        {"label": "L", "props": {"id": "1", "a": "x"}},
        {"label": "L", "props": {"id": "2", "b": "y"}},
    ]
    drv = make_driver(nodes, apoc=False)
    keys = sc.property_keys_for_label(drv, "L")
    assert keys == ["a", "b", "id"]


def test_canonical_json_sorted_keys() -> None:
    a = sc.canonical_json({"b": 1, "a": 2})
    b = sc.canonical_json({"a": 2, "b": 1})
    assert a == b


# ---------- CLI ----------

def test_self_test_exits_zero() -> None:
    assert sc.main(["--self-test"]) == 0


def test_main_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    drv = make_driver([{"label": "L", "props": {"id": "1"}}])
    monkeypatch.setattr(sc, "_default_driver", lambda: drv)
    out = tmp_path / "snap.json"
    rc = sc.main(["--out", str(out)])
    assert rc == 0
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "per_label_counts" in text


def test_help_flag_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        sc.main(["--help"])
    assert exc.value.code == 0
