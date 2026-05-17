"""Snapshot the lexical Neo4j into a canonical, hashable JSON payload.

Used for the triangle test: two consecutive runs of the same ingest must
produce byte-identical snapshots. The payload covers four invariants:

1. ``per_label_counts`` -- ``MATCH (n:<L>) RETURN count(n)`` per label.
2. ``per_rel_counts`` -- ``MATCH ()-[r:<T>]->() RETURN count(r)`` per type.
3. ``per_label_property_keys`` -- the multiset (sorted) of property keys
   observed on each label.
4. ``per_label_sample_hash`` -- sha256 of the canonical JSON of the first
   1000 nodes ordered by ``(n.id, elementId(n))`` (stable tie-break).

Usage:
    python tools/snapshot_counts.py [--out PATH] [--label L1 L2 ...]
                                    [--sample-limit N] [--self-test]

The script is read-only -- it issues only ``MATCH`` / ``SHOW`` queries
and never writes to the graph.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol, runtime_checkable


SAMPLE_LIMIT_DEFAULT = 1000


@dataclass
class Snapshot:
    per_label_counts: dict[str, int]
    per_rel_counts: dict[str, int]
    per_label_property_keys: dict[str, list[str]]
    per_label_sample_hash: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "per_label_counts": dict(sorted(self.per_label_counts.items())),
            "per_rel_counts": dict(sorted(self.per_rel_counts.items())),
            "per_label_property_keys": {
                k: sorted(v) for k, v in sorted(self.per_label_property_keys.items())
            },
            "per_label_sample_hash": dict(sorted(self.per_label_sample_hash.items())),
        }

    def overall_hash(self) -> str:
        return hashlib.sha256(canonical_json(self.to_dict()).encode("utf-8")).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# ---------- driver protocol ----------

@runtime_checkable
class _SessionProto(Protocol):
    def __enter__(self) -> "_SessionProto": ...
    def __exit__(self, *a: object) -> None: ...
    def run(self, query: str, **params: Any) -> Any: ...


@runtime_checkable
class _DriverProto(Protocol):
    def session(self) -> Any: ...
    def close(self) -> None: ...


# ---------- snapshot queries ----------

def list_labels(driver: _DriverProto) -> list[str]:
    with driver.session() as s:
        return sorted(rec["label"] for rec in s.run("CALL db.labels() YIELD label RETURN label"))


def list_rel_types(driver: _DriverProto) -> list[str]:
    with driver.session() as s:
        return sorted(
            rec["relationshipType"]
            for rec in s.run(
                "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
            )
        )


def count_label(driver: _DriverProto, label: str) -> int:
    with driver.session() as s:
        rec = s.run(f"MATCH (n:`{label}`) RETURN count(n) AS n").single()
        return int(rec["n"]) if rec else 0


def count_rel(driver: _DriverProto, rel: str) -> int:
    with driver.session() as s:
        rec = s.run(f"MATCH ()-[r:`{rel}`]->() RETURN count(r) AS n").single()
        return int(rec["n"]) if rec else 0


def property_keys_for_label(driver: _DriverProto, label: str) -> list[str]:
    """Return the sorted union of property keys observed on nodes of <label>.

    Uses ``apoc.meta.nodeTypeProperties`` when available; falls back to a
    pure-Cypher sampler that unions ``keys(n)`` across all nodes.
    """
    with driver.session() as s:
        try:
            rows = list(
                s.run(
                    "CALL apoc.meta.nodeTypeProperties({labels:[$label]}) "
                    "YIELD propertyName RETURN propertyName",
                    label=label,
                )
            )
            keys = sorted({r["propertyName"] for r in rows if r["propertyName"]})
            if keys:
                return keys
        except Exception:
            pass
        rows = list(
            s.run(f"MATCH (n:`{label}`) UNWIND keys(n) AS k RETURN DISTINCT k AS k")
        )
        return sorted(r["k"] for r in rows if r["k"])


def sample_hash_for_label(
    driver: _DriverProto, label: str, *, limit: int = SAMPLE_LIMIT_DEFAULT,
) -> str:
    """Hash the first ``limit`` nodes of ``label`` ordered for determinism."""
    with driver.session() as s:
        rows = list(
            s.run(
                f"MATCH (n:`{label}`) "
                f"RETURN properties(n) AS p, elementId(n) AS eid "
                f"ORDER BY coalesce(n.id, ''), elementId(n) "
                f"LIMIT $limit",
                limit=limit,
            )
        )
    serialised = [
        {"p": dict(sorted(r["p"].items())), "eid": r["eid"]}
        for r in rows
    ]
    return hashlib.sha256(canonical_json(serialised).encode("utf-8")).hexdigest()


def take_snapshot(
    driver: _DriverProto,
    *,
    labels: Iterable[str] | None = None,
    rel_types: Iterable[str] | None = None,
    sample_limit: int = SAMPLE_LIMIT_DEFAULT,
) -> Snapshot:
    lbls = list(labels) if labels is not None else list_labels(driver)
    rels = list(rel_types) if rel_types is not None else list_rel_types(driver)
    per_label_counts = {l: count_label(driver, l) for l in lbls}
    per_rel_counts = {r: count_rel(driver, r) for r in rels}
    per_keys = {l: property_keys_for_label(driver, l) for l in lbls}
    per_sample = {
        l: sample_hash_for_label(driver, l, limit=sample_limit) for l in lbls
    }
    return Snapshot(per_label_counts, per_rel_counts, per_keys, per_sample)


# ---------- driver factory ----------

def _default_driver() -> _DriverProto:
    from neo4j import GraphDatabase

    uri = os.environ["NEO4J_LEXICAL_URI"]
    user = os.environ["NEO4J_LEXICAL_USER"]
    pwd = os.environ["NEO4J_LEXICAL_PASSWORD"]
    return GraphDatabase.driver(uri, auth=(user, pwd))


# ---------- self-test ----------

class _FakeRecord(dict[str, Any]):
    def single(self) -> "_FakeRecord":
        return self


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def __iter__(self) -> Any:
        return iter(self._rows)

    def single(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, planner: Callable[[str, dict[str, Any]], list[dict[str, Any]]]) -> None:
        self.planner = planner

    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, *a: object) -> None:
        return None

    def run(self, query: str, **params: Any) -> _FakeResult:
        return _FakeResult(self.planner(query, params))


class _FakeDriver:
    def __init__(self, planner: Callable[[str, dict[str, Any]], list[dict[str, Any]]]) -> None:
        self.planner = planner

    def session(self) -> _FakeSession:
        return _FakeSession(self.planner)

    def close(self) -> None:
        return None


def _build_demo_driver() -> _FakeDriver:
    nodes: list[dict[str, Any]] = [
        {"label": "Lemma", "props": {"id": "H7225", "gloss": "beginning"}},
        {"label": "Lemma", "props": {"id": "G746", "gloss": "beginning"}},
        {"label": "Verse", "props": {"id": "GEN 1:1", "ref": "GEN 1:1"}},
    ]

    def planner(q: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if "db.labels()" in q:
            return [{"label": l} for l in {n["label"] for n in nodes}]
        if "db.relationshipTypes()" in q:
            return [{"relationshipType": "IN_VERSE"}]
        if q.startswith("MATCH (n:"):
            lbl = q.split("`")[1]
            rows = [n for n in nodes if n["label"] == lbl]
            if "count(n)" in q:
                return [{"n": len(rows)}]
            if "keys(n)" in q:
                keys = sorted({k for n in rows for k in n["props"]})
                return [{"k": k} for k in keys]
            if "properties(n)" in q:
                ordered = sorted(
                    rows, key=lambda r: (r["props"].get("id", ""), str(r["label"]))
                )
                limit = int(params.get("limit", SAMPLE_LIMIT_DEFAULT))
                return [
                    {"p": dict(r["props"]), "eid": f"{r['label']}/{r['props']['id']}"}
                    for r in ordered[:limit]
                ]
        if q.startswith("MATCH ()-[r:"):
            return [{"n": 1}]
        if "apoc.meta.nodeTypeProperties" in q:
            raise RuntimeError("apoc absent in self-test fixture")
        return []

    return _FakeDriver(planner)


def _self_test() -> int:
    drv = _build_demo_driver()
    snap1 = take_snapshot(drv)
    snap2 = take_snapshot(drv)
    if snap1.to_dict() != snap2.to_dict():
        print("self-test FAIL: snapshots differ on repeat", file=sys.stderr)
        return 1
    print(f"self-test OK; overall hash={snap1.overall_hash()[:12]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=Path("tools") / "snapshot_lexical.json")
    parser.add_argument("--label", nargs="*", default=None,
                        help="Restrict to these labels; default = all labels in DB.")
    parser.add_argument("--rel-type", nargs="*", default=None)
    parser.add_argument("--sample-limit", type=int, default=SAMPLE_LIMIT_DEFAULT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    driver = _default_driver()
    try:
        snap = take_snapshot(
            driver,
            labels=args.label,
            rel_types=args.rel_type,
            sample_limit=args.sample_limit,
        )
    finally:
        driver.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(canonical_json(snap.to_dict()), encoding="utf-8")
    print(f"wrote {args.out} (overall hash={snap.overall_hash()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
