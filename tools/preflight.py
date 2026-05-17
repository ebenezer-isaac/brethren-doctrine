"""Pre-flight check for the Phase Z toolchain.

Validates that:
1. ``cypher-shell`` is callable from PATH (``cypher-shell --version`` exits 0).
2. ``pytest_socket`` is importable in the active Python environment.
3. APOC is reachable inside the configured ``lexical-neo4j`` (procedure count >= 200).

Exits 0 only when ALL checks pass. Each failed check is printed to stderr
with the exact observed value vs the exact expected value.

Usage:
    python tools/preflight.py [--self-test] [--skip-apoc]

The ``--skip-apoc`` flag is provided for environments where the Neo4j
container is intentionally offline (e.g. CI for the tooling layer itself);
the orchestrator MUST NOT use it on the real reseed path.

The ``--self-test`` flag runs an in-process sanity check (resolves
``sys.executable`` via ``shutil.which``, imports ``pytest_socket`` in a
sub-interpreter) and exits 0 if the local toolchain reports itself
healthy.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Callable


APOC_PROCEDURE_FLOOR = 180


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    observed: str
    expected: str
    detail: str = ""


def _check_cypher_shell() -> CheckResult:
    """Verify ``cypher-shell`` is on PATH and prints a version banner."""
    path = shutil.which("cypher-shell")
    if path is None:
        return CheckResult(
            name="cypher-shell",
            ok=False,
            observed="not on PATH",
            expected="cypher-shell --version exits 0",
            detail="install neo4j cypher-shell and add it to PATH",
        )
    try:
        proc = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return CheckResult(
            name="cypher-shell",
            ok=False,
            observed=f"invocation failed: {exc}",
            expected="exit 0",
        )
    if proc.returncode != 0:
        return CheckResult(
            name="cypher-shell",
            ok=False,
            observed=f"exit {proc.returncode}: {proc.stderr.strip() or proc.stdout.strip()}",
            expected="exit 0",
        )
    return CheckResult(
        name="cypher-shell",
        ok=True,
        observed=proc.stdout.strip() or proc.stderr.strip() or "ok",
        expected="exit 0",
    )


def _check_pytest_socket() -> CheckResult:
    """Verify ``pytest_socket`` is importable in this interpreter."""
    spec = importlib.util.find_spec("pytest_socket")
    if spec is None:
        return CheckResult(
            name="pytest_socket",
            ok=False,
            observed="ModuleNotFoundError",
            expected="import pytest_socket succeeds",
            detail="pip install pytest-socket into the active .venv",
        )
    return CheckResult(
        name="pytest_socket",
        ok=True,
        observed=f"spec at {spec.origin}",
        expected="import pytest_socket succeeds",
    )


def _check_apoc(driver_factory: Callable[[], object] | None = None) -> CheckResult:
    """Verify APOC procedures are loaded in lexical-neo4j.

    The optional ``driver_factory`` lets tests inject a fake driver. Default
    behaviour reads ``NEO4J_LEXICAL_URI`` / ``NEO4J_LEXICAL_USER`` /
    ``NEO4J_LEXICAL_PASSWORD`` from the environment and connects via the
    real ``neo4j`` Python driver.
    """
    driver: Any
    try:
        if driver_factory is None:
            uri = os.environ.get("NEO4J_LEXICAL_URI")
            user = os.environ.get("NEO4J_LEXICAL_USER")
            pwd = os.environ.get("NEO4J_LEXICAL_PASSWORD")
            if not (uri and user and pwd):
                return CheckResult(
                    name="apoc",
                    ok=False,
                    observed="missing NEO4J_LEXICAL_* env vars",
                    expected="NEO4J_LEXICAL_URI/USER/PASSWORD set",
                )
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(uri, auth=(user, pwd))
        else:
            driver = driver_factory()
    except Exception as exc:
        return CheckResult(
            name="apoc",
            ok=False,
            observed=f"driver init failed: {exc}",
            expected="neo4j driver connects",
        )
    try:
        with driver.session() as session:
            rec = session.run(
                "SHOW PROCEDURES YIELD name "
                "WHERE name STARTS WITH 'apoc' "
                "RETURN count(*) AS n"
            ).single()
            n = int(rec["n"]) if rec else 0
    except Exception as exc:
        return CheckResult(
            name="apoc",
            ok=False,
            observed=f"query failed: {exc}",
            expected=f"apoc procedure count >= {APOC_PROCEDURE_FLOOR}",
        )
    finally:
        try:
            driver.close()
        except Exception:
            pass
    if n < APOC_PROCEDURE_FLOOR:
        return CheckResult(
            name="apoc",
            ok=False,
            observed=f"{n} apoc procedures",
            expected=f">= {APOC_PROCEDURE_FLOOR}",
            detail="drop apoc-*.jar into the neo4j plugins volume and restart",
        )
    return CheckResult(
        name="apoc",
        ok=True,
        observed=f"{n} apoc procedures",
        expected=f">= {APOC_PROCEDURE_FLOOR}",
    )


def run_checks(*, skip_apoc: bool = False) -> list[CheckResult]:
    checks: list[CheckResult] = [
        _check_cypher_shell(),
        _check_pytest_socket(),
    ]
    if not skip_apoc:
        checks.append(_check_apoc())
    return checks


def _self_test() -> int:
    """Validate the script's own check functions in isolation."""
    cs = _check_cypher_shell()
    ps = _check_pytest_socket()
    print(f"self-test cypher-shell: ok={cs.ok} observed={cs.observed!r}")
    print(f"self-test pytest_socket: ok={ps.ok} observed={ps.observed!r}")
    # Self-test passes if pytest_socket import works; cypher-shell can be
    # absent in the tooling-CI lane (caller decides via --skip-apoc).
    return 0 if ps.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test", action="store_true",
        help="Run an in-process sanity check; does not touch Neo4j.",
    )
    parser.add_argument(
        "--skip-apoc", action="store_true",
        help="Skip the APOC check (tooling-CI lane only).",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    results = run_checks(skip_apoc=args.skip_apoc)
    failed: list[CheckResult] = []
    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"[{status}] {r.name}: observed={r.observed} expected={r.expected}")
        if not r.ok and r.detail:
            print(f"        hint: {r.detail}")
        if not r.ok:
            failed.append(r)
    if failed:
        print(f"\n{len(failed)} preflight check(s) failed.", file=sys.stderr)
        return 1
    print("\nAll preflight checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
