"""Destructive wipe of the lexical Neo4j.

This script is intentionally inconvenient. It:

1. Generates a wipe-token of the form ``WIPE-LEXICAL-<unix_ts>-<random_8>``
   and prints it on stdout.
2. Reads a single line from stdin. If the line does not equal the token
   verbatim (no trailing whitespace tolerated beyond a final newline)
   the wipe is aborted.
3. Performs a batched ``DETACH DELETE`` using
   ``apoc.periodic.iterate`` with ``batchSize=10000``. If APOC is not
   reachable, falls back to manual Python-driven 10k batches.
4. Drops every constraint via ``SHOW CONSTRAINTS`` iteration.
5. Drops every index whose ``type`` is not ``LOOKUP``.
6. Asserts post-conditions: ``MATCH (n) RETURN count(n) = 0``,
   ``SHOW CONSTRAINTS`` empty, non-LOOKUP indexes empty.

A ``--post-check`` flag runs ONLY the post-state assertions (does not
wipe). A ``--token <T>`` flag lets an orchestrator pass the token via
argv instead of stdin; the token still has to match the one generated
at startup.

A ``--self-test`` flag exercises the token machinery against a fake
driver and exits 0 on success.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Protocol, runtime_checkable


BATCH_SIZE = 10_000


@dataclass(frozen=True)
class WipeToken:
    value: str

    @classmethod
    def fresh(cls) -> "WipeToken":
        return cls(f"WIPE-LEXICAL-{int(time.time())}-{secrets.token_hex(4)}")


def _confirm(token: WipeToken, *, stdin_text: str | None) -> bool:
    """Compare the supplied confirmation string to ``token`` constant-time."""
    if stdin_text is None:
        return False
    given = stdin_text.rstrip("\r\n")
    return secrets.compare_digest(given.encode("utf-8"), token.value.encode("utf-8"))


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


# ---------- wipe primitives ----------

def _try_apoc_iterate(driver: _DriverProto) -> bool:
    """Returns True if APOC succeeded, False if not available."""
    with driver.session() as s:
        try:
            s.run(
                "CALL apoc.periodic.iterate("
                "'MATCH (n) RETURN n', "
                "'DETACH DELETE n', "
                f"{{batchSize:{BATCH_SIZE}, parallel:false}}"
                ") YIELD batches, total RETURN batches, total"
            ).consume()
            return True
        except Exception:
            return False


def _manual_batches(driver: _DriverProto) -> int:
    """Manual fallback: delete in 10k batches until count == 0."""
    total_deleted = 0
    while True:
        with driver.session() as s:
            rec = s.run(
                "MATCH (n) WITH n LIMIT $b DETACH DELETE n RETURN count(*) AS d",
                b=BATCH_SIZE,
            ).single()
            d = int(rec["d"]) if rec else 0
        total_deleted += d
        if d == 0:
            break
    return total_deleted


def _drop_all_constraints(driver: _DriverProto) -> int:
    n = 0
    with driver.session() as s:
        names = [r["name"] for r in s.run("SHOW CONSTRAINTS YIELD name RETURN name")]
        for name in names:
            s.run(f"DROP CONSTRAINT `{name}` IF EXISTS").consume()
            n += 1
    return n


def _drop_non_lookup_indexes(driver: _DriverProto) -> int:
    n = 0
    with driver.session() as s:
        rows = list(s.run(
            "SHOW INDEXES YIELD name, type WHERE type <> 'LOOKUP' RETURN name"
        ))
        for r in rows:
            s.run(f"DROP INDEX `{r['name']}` IF EXISTS").consume()
            n += 1
    return n


@dataclass
class PostCheck:
    node_count: int
    constraint_count: int
    nonlookup_index_count: int

    @property
    def clean(self) -> bool:
        return (
            self.node_count == 0
            and self.constraint_count == 0
            and self.nonlookup_index_count == 0
        )


def post_check(driver: _DriverProto) -> PostCheck:
    with driver.session() as s:
        nrec = s.run("MATCH (n) RETURN count(n) AS n").single()
        crec = s.run("SHOW CONSTRAINTS YIELD name RETURN count(*) AS n").single()
        irec = s.run(
            "SHOW INDEXES YIELD name, type WHERE type <> 'LOOKUP' RETURN count(*) AS n"
        ).single()
    return PostCheck(
        node_count=int(nrec["n"]) if nrec else 0,
        constraint_count=int(crec["n"]) if crec else 0,
        nonlookup_index_count=int(irec["n"]) if irec else 0,
    )


def perform_wipe(driver: _DriverProto) -> tuple[bool, int, int, int]:
    """Wipe nodes, then drop constraints + non-LOOKUP indexes.

    Returns ``(used_apoc, deleted_count_or_-1, n_constraints, n_indexes)``.
    ``deleted_count_or_-1`` is -1 when APOC was used (it does not return
    a single deleted count we can compare against).
    """
    used_apoc = _try_apoc_iterate(driver)
    if used_apoc:
        deleted = -1
        # APOC reports completion via the YIELD; we still verify with a
        # count in post_check, so no extra work here.
    else:
        deleted = _manual_batches(driver)
    n_constraints = _drop_all_constraints(driver)
    n_indexes = _drop_non_lookup_indexes(driver)
    return used_apoc, deleted, n_constraints, n_indexes


# ---------- driver factory ----------

def _default_driver() -> _DriverProto:
    from neo4j import GraphDatabase

    uri = os.environ["NEO4J_LEXICAL_URI"]
    user = os.environ["NEO4J_LEXICAL_USER"]
    pwd = os.environ["NEO4J_LEXICAL_PASSWORD"]
    return GraphDatabase.driver(uri, auth=(user, pwd))


# ---------- self-test fake driver ----------

class _FakeSession:
    def __init__(self, drv: "_FakeDriver") -> None:
        self.drv = drv

    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, *a: object) -> None:
        return None

    def run(self, q: str, **params: Any) -> "_FakeResult":
        return self.drv._run(q, params)


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def __iter__(self) -> Any:
        return iter(self.rows)

    def single(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None

    def consume(self) -> None:
        return None


class _FakeDriver:
    def __init__(
        self,
        *,
        nodes: int = 50_000,
        constraints: Iterable[str] = (),
        indexes: Iterable[tuple[str, str]] = (),
        apoc_available: bool = True,
    ) -> None:
        self._nodes = nodes
        self._constraints = list(constraints)
        self._indexes = list(indexes)  # (name, type)
        self._apoc = apoc_available

    def session(self) -> _FakeSession:
        return _FakeSession(self)

    def close(self) -> None:
        return None

    def _run(self, q: str, params: dict[str, Any]) -> _FakeResult:
        ql = q.strip()
        if ql.startswith("CALL apoc.periodic.iterate"):
            if not self._apoc:
                raise RuntimeError("apoc absent")
            self._nodes = 0
            return _FakeResult([{"batches": 1, "total": 1}])
        if ql.startswith("MATCH (n) WITH n LIMIT"):
            d = min(self._nodes, params.get("b", BATCH_SIZE))
            self._nodes -= d
            return _FakeResult([{"d": d}])
        if ql.startswith("MATCH (n) RETURN count(n)"):
            return _FakeResult([{"n": self._nodes}])
        if "SHOW CONSTRAINTS" in ql and "count(*)" in ql:
            return _FakeResult([{"n": len(self._constraints)}])
        if "SHOW CONSTRAINTS" in ql:
            return _FakeResult([{"name": c} for c in self._constraints])
        if "SHOW INDEXES" in ql and "count(*)" in ql:
            n = sum(1 for _, t in self._indexes if t != "LOOKUP")
            return _FakeResult([{"n": n}])
        if "SHOW INDEXES" in ql:
            return _FakeResult([{"name": n} for n, t in self._indexes if t != "LOOKUP"])
        if ql.startswith("DROP CONSTRAINT"):
            name = ql.split("`")[1]
            self._constraints = [c for c in self._constraints if c != name]
            return _FakeResult([])
        if ql.startswith("DROP INDEX"):
            name = ql.split("`")[1]
            self._indexes = [(n, t) for (n, t) in self._indexes if n != name]
            return _FakeResult([])
        return _FakeResult([])


def _self_test() -> int:
    t = WipeToken.fresh()
    assert not _confirm(t, stdin_text=None)
    assert not _confirm(t, stdin_text="")
    assert not _confirm(t, stdin_text="WIPE-LEXICAL-0-00000000")
    assert _confirm(t, stdin_text=t.value)
    assert _confirm(t, stdin_text=t.value + "\n")

    drv = _FakeDriver(
        nodes=25_000,
        constraints=["c1", "c2"],
        indexes=[("idx_a", "RANGE"), ("idx_b", "LOOKUP")],
        apoc_available=True,
    )
    used_apoc, deleted, ncon, nidx = perform_wipe(drv)
    assert used_apoc and ncon == 2 and nidx == 1
    pc = post_check(drv)
    assert pc.clean, pc

    drv2 = _FakeDriver(nodes=23_000, apoc_available=False)
    used_apoc2, deleted2, _, _ = perform_wipe(drv2)
    assert not used_apoc2 and deleted2 == 23_000
    assert post_check(drv2).clean
    print("self-test OK")
    return 0


# ---------- CLI ----------

def main(
    argv: list[str] | None = None,
    *,
    stdin: Any = None,
    driver_factory: Callable[[], _DriverProto] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--post-check", action="store_true",
                        help="Only run post-state assertions; do not wipe.")
    parser.add_argument("--token", default=None,
                        help="Pre-supply the confirmation token instead of "
                             "reading stdin. The script will still generate "
                             "its own token and require yours to match.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    factory = driver_factory or _default_driver
    driver = factory()
    try:
        if args.post_check:
            pc = post_check(driver)
            print(f"nodes={pc.node_count} constraints={pc.constraint_count} "
                  f"non_lookup_indexes={pc.nonlookup_index_count}")
            if not pc.clean:
                print(
                    f"post-check FAIL: expected (0,0,0), "
                    f"got ({pc.node_count},{pc.constraint_count},"
                    f"{pc.nonlookup_index_count})",
                    file=sys.stderr,
                )
                return 1
            return 0

        token = WipeToken.fresh()
        print(f"WIPE TOKEN: {token.value}")
        print("Echo the token to stdin (or pass --token) to proceed.")
        if args.token is not None:
            given = args.token
        else:
            stream = stdin if stdin is not None else sys.stdin
            given = stream.readline()
        if not _confirm(token, stdin_text=given):
            print("token mismatch -- wipe aborted", file=sys.stderr)
            return 2
        used_apoc, deleted, ncon, nidx = perform_wipe(driver)
        print(f"wipe complete: apoc={used_apoc} deleted={deleted} "
              f"constraints_dropped={ncon} indexes_dropped={nidx}")
        pc = post_check(driver)
        if not pc.clean:
            print(
                f"post-check FAIL after wipe: nodes={pc.node_count} "
                f"constraints={pc.constraint_count} "
                f"non_lookup_indexes={pc.nonlookup_index_count}",
                file=sys.stderr,
            )
            return 1
        print("post-check OK")
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
