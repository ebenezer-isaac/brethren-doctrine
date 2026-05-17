"""Run the global cross-adapter invariants from RESEED_PLAN D.2.

Five hard invariants on the live lexical Neo4j; any failure exits 1.

1. **Orphan-free**: for every declared label,
   ``MATCH (n:<L>) WHERE NOT (n)--() RETURN count(n)`` returns 0.
2. **Lemma cleanliness**: per ``Lemma.strong``, exactly 1 Lemma node;
   no self-loops on ``INSTANCE_OF``.
3. **Gloss coverage**: ``Lemma`` rows with empty ``gloss`` whose source
   is not in the configured nullable set must be zero.
4. **Edge floors**: every relationship type X declared in
   ``EXPECTED_EDGES`` meets its ``low`` bound.
5. **No placeholder pollution**: zero ``Lemma {id:"PLACEHOLDER"}`` and
   zero of any other reserved sentinel id.

Usage:
    python tools/verify_global_invariants.py [--self-test]
                                              [--labels L1 L2 ...]
                                              [--expected-edges PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol, runtime_checkable


DEFAULT_LABELS: tuple[str, ...] = (
    "Verse", "Word", "Lemma", "CrossRef", "Person", "Place",
)
DEFAULT_NULLABLE_GLOSS_SOURCES: tuple[str, ...] = ()
DEFAULT_PLACEHOLDER_IDS: tuple[str, ...] = ("PLACEHOLDER", "TBD", "FIXME", "")


@dataclass
class InvariantResult:
    name: str
    ok: bool
    observed: str
    expected: str
    detail: str = ""

    def format(self) -> str:
        status = "OK" if self.ok else "FAIL"
        return f"[{status}] {self.name}: observed={self.observed} expected={self.expected}"


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


# ---------- invariants ----------

def check_orphans(driver: _DriverProto, labels: Iterable[str]) -> list[InvariantResult]:
    results: list[InvariantResult] = []
    with driver.session() as s:
        for lbl in labels:
            rec = s.run(
                f"MATCH (n:`{lbl}`) WHERE NOT (n)--() RETURN count(n) AS n"
            ).single()
            n = int(rec["n"]) if rec else 0
            results.append(InvariantResult(
                name=f"orphan_free[{lbl}]",
                ok=(n == 0),
                observed=str(n),
                expected="0",
            ))
    return results


def check_lemma_cleanliness(driver: _DriverProto) -> list[InvariantResult]:
    results: list[InvariantResult] = []
    with driver.session() as s:
        # per Lemma.strong, exactly 1 Lemma node
        rec = s.run(
            "MATCH (l:Lemma) WHERE l.strong IS NOT NULL "
            "WITH l.strong AS s, count(l) AS c WHERE c > 1 "
            "RETURN count(*) AS dups"
        ).single()
        dups = int(rec["dups"]) if rec else 0
        results.append(InvariantResult(
            name="lemma_distinct_per_strong",
            ok=(dups == 0),
            observed=f"{dups} duplicate strong codes",
            expected="0",
        ))
        # no self-loops on INSTANCE_OF
        rec2 = s.run(
            "MATCH (a)-[r:INSTANCE_OF]->(b) WHERE a = b RETURN count(r) AS n"
        ).single()
        loops = int(rec2["n"]) if rec2 else 0
        results.append(InvariantResult(
            name="instance_of_no_self_loops",
            ok=(loops == 0),
            observed=str(loops),
            expected="0",
        ))
    return results


def check_gloss_coverage(
    driver: _DriverProto, *, nullable_sources: Iterable[str],
) -> InvariantResult:
    with driver.session() as s:
        rec = s.run(
            "MATCH (l:Lemma) "
            "WHERE (l.gloss IS NULL OR l.gloss = '') "
            "AND coalesce(l.source,'') IN $sources = false "
            "RETURN count(l) AS n",
            sources=list(nullable_sources),
        ).single()
        n = int(rec["n"]) if rec else 0
    return InvariantResult(
        name="gloss_coverage",
        ok=(n == 0),
        observed=f"{n} Lemma rows missing gloss outside nullable sources",
        expected="0",
    )


def check_edge_floors(
    driver: _DriverProto, *, expected_edges: dict[str, dict[str, int]],
) -> list[InvariantResult]:
    """``expected_edges = {rel_type: {"low": N}}``."""
    results: list[InvariantResult] = []
    with driver.session() as s:
        for rel, spec in sorted(expected_edges.items()):
            low = int(spec["low"])
            rec = s.run(
                f"MATCH ()-[r:`{rel}`]->() RETURN count(r) AS n"
            ).single()
            n = int(rec["n"]) if rec else 0
            results.append(InvariantResult(
                name=f"edge_floor[{rel}]",
                ok=(n >= low),
                observed=str(n),
                expected=f">= {low}",
            ))
    return results


def check_no_placeholders(
    driver: _DriverProto, *, ids: Iterable[str],
) -> list[InvariantResult]:
    results: list[InvariantResult] = []
    with driver.session() as s:
        for sentinel in ids:
            rec = s.run(
                "MATCH (l:Lemma) WHERE l.id = $sid OR l.strong = $sid "
                "RETURN count(l) AS n",
                sid=sentinel,
            ).single()
            n = int(rec["n"]) if rec else 0
            results.append(InvariantResult(
                name=f"no_placeholder[{sentinel!r}]",
                ok=(n == 0),
                observed=str(n),
                expected="0",
            ))
    return results


@dataclass
class Config:
    labels: tuple[str, ...] = DEFAULT_LABELS
    nullable_gloss_sources: tuple[str, ...] = DEFAULT_NULLABLE_GLOSS_SOURCES
    placeholder_ids: tuple[str, ...] = DEFAULT_PLACEHOLDER_IDS
    expected_edges: dict[str, dict[str, int]] = field(default_factory=dict)


def run_all(driver: _DriverProto, cfg: Config) -> list[InvariantResult]:
    out: list[InvariantResult] = []
    out.extend(check_orphans(driver, cfg.labels))
    out.extend(check_lemma_cleanliness(driver))
    out.append(check_gloss_coverage(driver, nullable_sources=cfg.nullable_gloss_sources))
    out.extend(check_edge_floors(driver, expected_edges=cfg.expected_edges))
    out.extend(check_no_placeholders(driver, ids=cfg.placeholder_ids))
    return out


# ---------- self-test driver ----------

class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def single(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None


class _FakeSession:
    def __init__(self, planner: Callable[[str, dict[str, Any]], list[dict[str, Any]]]) -> None:
        self.planner = planner

    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, *a: object) -> None:
        return None

    def run(self, q: str, **params: Any) -> _FakeResult:
        return _FakeResult(self.planner(q, params))


class _FakeDriver:
    def __init__(self, planner: Callable[[str, dict[str, Any]], list[dict[str, Any]]]) -> None:
        self.planner = planner

    def session(self) -> _FakeSession:
        return _FakeSession(self.planner)

    def close(self) -> None:
        return None


def _build_clean_driver() -> _FakeDriver:
    def planner(q: str, p: dict[str, Any]) -> list[dict[str, Any]]:
        if "WHERE NOT (n)--()" in q:
            return [{"n": 0}]
        if "WHERE c > 1" in q:
            return [{"dups": 0}]
        if "INSTANCE_OF" in q and "a = b" in q:
            return [{"n": 0}]
        if "l.gloss IS NULL" in q:
            return [{"n": 0}]
        if q.startswith("MATCH ()-[r:"):
            return [{"n": 10_000}]
        if "l.id = $sid" in q:
            return [{"n": 0}]
        return [{"n": 0}]

    return _FakeDriver(planner)


def _build_dirty_driver() -> _FakeDriver:
    def planner(q: str, p: dict[str, Any]) -> list[dict[str, Any]]:
        if "WHERE NOT (n)--()" in q:
            return [{"n": 5}]  # orphans exist
        if "WHERE c > 1" in q:
            return [{"dups": 3}]
        if "INSTANCE_OF" in q and "a = b" in q:
            return [{"n": 1}]
        if "l.gloss IS NULL" in q:
            return [{"n": 7}]
        if q.startswith("MATCH ()-[r:"):
            return [{"n": 0}]
        if "l.id = $sid" in q:
            return [{"n": 2}]
        return [{"n": 0}]

    return _FakeDriver(planner)


def _self_test() -> int:
    cfg = Config(
        labels=("Lemma", "Verse"),
        expected_edges={"IN_VERSE": {"low": 100}},
    )
    clean = run_all(_build_clean_driver(), cfg)
    if not all(r.ok for r in clean):
        print(f"self-test FAIL: clean driver flagged: "
              f"{[r.format() for r in clean if not r.ok]}", file=sys.stderr)
        return 1
    dirty = run_all(_build_dirty_driver(), cfg)
    if all(r.ok for r in dirty):
        print("self-test FAIL: dirty driver passed", file=sys.stderr)
        return 1
    print("self-test OK")
    return 0


# ---------- driver factory ----------

def _default_driver() -> _DriverProto:
    from neo4j import GraphDatabase

    uri = os.environ["NEO4J_LEXICAL_URI"]
    user = os.environ["NEO4J_LEXICAL_USER"]
    pwd = os.environ["NEO4J_LEXICAL_PASSWORD"]
    return GraphDatabase.driver(uri, auth=(user, pwd))


def _load_expected_edges(path: Path | None) -> dict[str, dict[str, int]]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    edges = payload.get("edges", {})
    return {str(k): {str(kk): int(vv) for kk, vv in v.items()}
            for k, v in edges.items()}


def main(
    argv: list[str] | None = None,
    *,
    driver_factory: Callable[[], _DriverProto] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", nargs="*", default=None)
    parser.add_argument("--expected-edges", type=Path, default=None)
    parser.add_argument("--nullable-gloss-source", action="append", default=[])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    cfg = Config(
        labels=tuple(args.labels) if args.labels else DEFAULT_LABELS,
        nullable_gloss_sources=tuple(args.nullable_gloss_source),
        expected_edges=_load_expected_edges(args.expected_edges),
    )

    driver = (driver_factory or _default_driver)()
    try:
        results = run_all(driver, cfg)
    finally:
        driver.close()
    failed = [r for r in results if not r.ok]
    for r in results:
        print(r.format())
    if failed:
        print(f"\n{len(failed)} invariant(s) failed.", file=sys.stderr)
        return 1
    print(f"\nAll {len(results)} invariants passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
