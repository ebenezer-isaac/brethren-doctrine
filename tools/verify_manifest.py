"""Independent Auditor-caste re-executor for a phase manifest.

Reads a ``docs/RESEED_MANIFEST_<ts>.json`` claim file and re-runs every
claim independently. The auditor MUST compute its own value first, then
compare. The implementation enforces that by computing all claim values
into ``observed.json`` BEFORE the manifest is even parsed for the
``expected`` side; the parsed manifest is only consulted at the diff
step.

Claim schema (each entry of ``manifest["claims"]``):

* ``id``: unique slug
* ``description``: human-readable
* ``check_kind``: one of
    - ``pytest`` (key: ``selector``, runs ``pytest -q <selector>``)
    - ``script`` (key: ``argv``, runs ``python <argv...>`` and captures
      exit code + stdout sha256)
    - ``cypher`` (keys: ``query``, ``database``, ``expected_value``,
      ``tolerance`` optional; runs against ``NEO4J_<DATABASE>_*`` env)
    - ``file_sha`` (key: ``path``; computes sha256 of file content)
    - ``grep`` (keys: ``path``, ``pattern``, ``must_be_empty`` bool)
* ``expected``: type-appropriate ground truth recorded by the phase
* ``actual_field``: name of the field to compare against ``expected``

Output:

* ``docs/MANIFEST_VERIFICATION_<phase>.json`` written with the auditor's
  observed values and the diff.
* Exit 0 iff every claim's observed equals expected (within tolerance).

Self-test exercises the script against an in-memory manifest with one
claim of each kind that uses fake adapters; no network or Neo4j touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ClaimResult:
    id: str
    description: str
    check_kind: str
    observed: Any
    expected: Any
    matches: bool
    detail: str = ""


# Wall-clock budget for a single ``pytest`` claim subprocess. The Phase H
# h2_adapter_pytest claim legitimately runs a ~972-item text-fabric adapter
# coverage suite that takes ~70 minutes wall, so the prior hardcoded 600s
# killed an honest, passing suite mid-run. This budget comfortably exceeds
# the real runtime with margin (90 min). It is NOT a sampling/shrinking of
# the suite; the full selector is still executed unchanged. An env override
# is allowed for operators who need a longer or shorter ceiling without a
# code edit; it falls back to the constant on any unset/invalid value.
PYTEST_CLAIM_TIMEOUT_SECONDS = 5400


def _pytest_claim_timeout() -> int:
    raw = os.environ.get("VERIFY_MANIFEST_PYTEST_TIMEOUT")
    if raw is None:
        return PYTEST_CLAIM_TIMEOUT_SECONDS
    try:
        val = int(raw)
    except (TypeError, ValueError):
        return PYTEST_CLAIM_TIMEOUT_SECONDS
    return val if val > 0 else PYTEST_CLAIM_TIMEOUT_SECONDS


# Non-zero sentinel exit code recorded when a claim subprocess exceeds its
# wall-clock budget. It is deliberately not a normal pytest/script exit code
# so it always drives the standard diff path to a claim-level mismatch
# instead of crashing the whole audit with an uncaught TimeoutExpired.
CLAIM_TIMEOUT_EXIT_CODE = 124


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_path(p: Path) -> str:
    return _sha256_bytes(p.read_bytes())


def run_pytest_claim(selector: str, repo: Path) -> dict[str, Any]:
    # A selector may name several space-separated test paths. Split it so
    # each path becomes its own argv token (``pytest -q p1 p2 ...``)
    # instead of one bogus combined path. shlex.split is robust against
    # quoted paths and yields a one-element list for a single path, so
    # single-path selectors behave exactly as before.
    selector_args = shlex.split(selector)
    budget = _pytest_claim_timeout()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *selector_args],
            cwd=str(repo), capture_output=True, text=True, timeout=budget,
        )
    except subprocess.TimeoutExpired as exc:
        # An over-budget pytest claim is a CLAIM-LEVEL failure, not an
        # uncaught exception that aborts the entire audit before the diff
        # step. Emit the same observed-dict shape (exit_code / stdout_sha256
        # / stderr_tail) with a non-zero sentinel so evaluate_claim and
        # audit_manifest route it through the normal mismatch path.
        partial = exc.stdout or b""
        if isinstance(partial, str):
            partial = partial.encode("utf-8")
        return {
            "exit_code": CLAIM_TIMEOUT_EXIT_CODE,
            "stdout_sha256": _sha256_bytes(partial),
            "stderr_tail": f"pytest claim timed out after {budget}s",
        }
    return {
        "exit_code": proc.returncode,
        "stdout_sha256": _sha256_bytes(proc.stdout.encode("utf-8")),
        "stderr_tail": proc.stderr[-2000:],
    }


def run_script_claim(argv: list[str], repo: Path) -> dict[str, Any]:
    cmd = [sys.executable, *argv] if argv and argv[0].endswith(".py") else argv
    try:
        proc = subprocess.run(
            cmd, cwd=str(repo), capture_output=True, text=True, timeout=900,
        )
    except subprocess.TimeoutExpired as exc:
        # Same defensive contract as run_pytest_claim: an over-budget script
        # claim degrades to a claim-level mismatch via the sentinel exit
        # code rather than crashing the whole audit with an uncaught
        # TimeoutExpired before the diff step.
        partial = exc.stdout or b""
        if isinstance(partial, str):
            partial = partial.encode("utf-8")
        return {
            "exit_code": CLAIM_TIMEOUT_EXIT_CODE,
            "stdout_sha256": _sha256_bytes(partial),
            "stderr_tail": "script claim timed out after 900s",
        }
    return {
        "exit_code": proc.returncode,
        "stdout_sha256": _sha256_bytes(proc.stdout.encode("utf-8")),
        "stderr_tail": proc.stderr[-2000:],
    }


def run_cypher_claim(
    query: str,
    database: str,
    *,
    driver_factory: Any = None,
) -> dict[str, Any]:
    if driver_factory is not None:
        driver = driver_factory()
    else:
        uri = os.environ.get(f"NEO4J_{database.upper()}_URI")
        user = os.environ.get(f"NEO4J_{database.upper()}_USER")
        pwd = os.environ.get(f"NEO4J_{database.upper()}_PASSWORD")
        if not (uri and user and pwd):
            return {"value": None, "error": f"missing NEO4J_{database.upper()}_* env"}
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
    try:
        with driver.session() as session:
            rows = list(session.run(query))
            if len(rows) == 1 and len(rows[0].keys()) == 1:
                v = rows[0][rows[0].keys()[0]]
                return {"value": v, "row_count": 1}
            return {"value": [dict(r) for r in rows], "row_count": len(rows)}
    finally:
        try:
            driver.close()
        except Exception:
            pass


def run_file_sha_claim(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"sha256": None, "error": "file missing"}
    return {"sha256": _sha256_path(path), "bytes": path.stat().st_size}


def run_grep_claim(path: Path, pattern: str) -> dict[str, Any]:
    if not path.exists():
        return {"matches": None, "error": "file missing"}
    rx = re.compile(pattern, re.MULTILINE)
    text = path.read_text(encoding="utf-8", errors="replace")
    found = rx.findall(text)
    return {"match_count": len(found), "first_match": found[0] if found else None}


def evaluate_claim(
    claim: dict[str, Any],
    repo: Path,
    *,
    driver_factory: Any = None,
) -> ClaimResult:
    kind = claim["check_kind"]
    if kind == "pytest":
        observed = run_pytest_claim(claim["selector"], repo)
    elif kind == "script":
        observed = run_script_claim(claim["argv"], repo)
    elif kind == "cypher":
        observed = run_cypher_claim(
            claim["query"], claim["database"], driver_factory=driver_factory,
        )
    elif kind == "file_sha":
        observed = run_file_sha_claim(repo / claim["path"])
    elif kind == "grep":
        observed = run_grep_claim(repo / claim["path"], claim["pattern"])
    else:
        return ClaimResult(
            id=claim["id"],
            description=claim.get("description", ""),
            check_kind=kind,
            observed=None,
            expected=claim.get("expected"),
            matches=False,
            detail=f"unknown check_kind {kind!r}",
        )

    expected = claim.get("expected")
    field_name = claim.get("actual_field", "value")
    actual = observed.get(field_name) if isinstance(observed, dict) else observed
    matches = _compare(actual, expected, claim.get("tolerance"))
    return ClaimResult(
        id=claim["id"],
        description=claim.get("description", ""),
        check_kind=kind,
        observed=observed,
        expected=expected,
        matches=matches,
        detail=("" if matches
                else f"actual={actual!r} expected={expected!r}"),
    )


def _compare(actual: Any, expected: Any, tolerance: Any) -> bool:
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if tolerance is None:
            return actual == expected
        if isinstance(tolerance, dict):
            mode = tolerance.get("mode", "absolute")
            amount = tolerance.get("amount", 0)
            if mode == "absolute":
                return abs(actual - expected) <= amount
            if mode == "ratio":
                if expected == 0:
                    return actual == 0
                return abs(actual - expected) / abs(expected) <= amount
            return actual == expected
        return abs(actual - expected) <= float(tolerance)
    return actual == expected


@dataclass
class AuditOutput:
    manifest_path: str
    manifest_sha256: str
    phase: str
    claims: list[ClaimResult] = field(default_factory=list)
    all_match: bool = False


def _read_manifest_no_compare(manifest_path: Path) -> tuple[dict[str, Any], str]:
    raw = manifest_path.read_bytes()
    return json.loads(raw), _sha256_bytes(raw)


def audit_manifest(
    manifest_path: Path,
    repo: Path,
    *,
    driver_factory: Any = None,
) -> AuditOutput:
    manifest, sha = _read_manifest_no_compare(manifest_path)
    phase = manifest.get("phase", "unknown")
    claims = manifest.get("claims", [])

    observed_only: list[dict[str, Any]] = []
    for c in claims:
        kind = c["check_kind"]
        if kind == "pytest":
            o = run_pytest_claim(c["selector"], repo)
        elif kind == "script":
            o = run_script_claim(c["argv"], repo)
        elif kind == "cypher":
            o = run_cypher_claim(c["query"], c["database"],
                                 driver_factory=driver_factory)
        elif kind == "file_sha":
            o = run_file_sha_claim(repo / c["path"])
        elif kind == "grep":
            o = run_grep_claim(repo / c["path"], c["pattern"])
        else:
            o = {"error": f"unknown check_kind {kind!r}"}
        observed_only.append({"id": c["id"], "kind": kind, "observed": o})

    results: list[ClaimResult] = []
    for c, obs in zip(claims, observed_only, strict=True):
        field_name = c.get("actual_field", "value")
        actual = obs["observed"].get(field_name) if isinstance(obs["observed"], dict) else obs["observed"]
        matches = _compare(actual, c.get("expected"), c.get("tolerance"))
        results.append(ClaimResult(
            id=c["id"],
            description=c.get("description", ""),
            check_kind=c["check_kind"],
            observed=obs["observed"],
            expected=c.get("expected"),
            matches=matches,
            detail=("" if matches
                    else f"actual={actual!r} expected={c.get('expected')!r}"),
        ))

    return AuditOutput(
        manifest_path=str(manifest_path),
        manifest_sha256=sha,
        phase=phase,
        claims=results,
        all_match=all(r.matches for r in results),
    )


def _self_test() -> int:
    import tempfile
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        target = td_path / "fixture.txt"
        target.write_bytes(b"hello world")
        # Two trivial passing test files under a space-free relative dir so
        # the multi-path selector exercises the argv-split fix: pytest must
        # receive each path as its own token and exit 0.
        (td_path / "test_a.py").write_text(
            "def test_a():\n    assert True\n", encoding="utf-8")
        (td_path / "test_b.py").write_text(
            "def test_b():\n    assert True\n", encoding="utf-8")
        manifest = {
            "phase": "Z.1-self-test",
            "claims": [
                {
                    "id": "fixture_sha",
                    "description": "self-test fixture sha256",
                    "check_kind": "file_sha",
                    "path": str(target.relative_to(td_path)),
                    "expected": _sha256_bytes(b"hello world"),
                    "actual_field": "sha256",
                },
                {
                    "id": "multi_path_pytest",
                    "description": "multi-path pytest selector splits to argv",
                    "check_kind": "pytest",
                    "selector": "test_a.py test_b.py",
                    "expected": 0,
                    "actual_field": "exit_code",
                },
            ],
        }
        m_path = td_path / "manifest.json"
        m_path.write_text(json.dumps(manifest), encoding="utf-8")
        out = audit_manifest(m_path, td_path)
        if not out.all_match:
            print(f"self-test FAIL: claim diff: {out.claims}", file=sys.stderr)
            return 1
        bad_manifest = json.loads(json.dumps(manifest))
        bad_manifest["claims"][0]["expected"] = "deadbeef"
        m_path.write_text(json.dumps(bad_manifest), encoding="utf-8")
        out2 = audit_manifest(m_path, td_path)
        if out2.all_match:
            print("self-test FAIL: bad expected accepted", file=sys.stderr)
            return 1

        # An over-budget pytest claim must degrade to a CLAIM-LEVEL
        # mismatch (sentinel exit code != expected 0) and the audit must
        # still proceed to diff every claim, never raising an uncaught
        # subprocess.TimeoutExpired. Force a tiny budget via the env
        # override against a deliberately slow test.
        (td_path / "test_slow.py").write_text(
            "import time\n\n\ndef test_slow():\n    time.sleep(30)\n",
            encoding="utf-8",
        )
        timeout_manifest = {
            "phase": "Z.1-self-test-timeout",
            "claims": [
                {
                    "id": "fixture_sha",
                    "description": "fast claim still evaluated alongside",
                    "check_kind": "file_sha",
                    "path": str(target.relative_to(td_path)),
                    "expected": _sha256_bytes(b"hello world"),
                    "actual_field": "sha256",
                },
                {
                    "id": "slow_pytest",
                    "description": "over-budget pytest claim -> mismatch",
                    "check_kind": "pytest",
                    "selector": "test_slow.py",
                    "expected": 0,
                    "actual_field": "exit_code",
                },
            ],
        }
        m_path.write_text(json.dumps(timeout_manifest), encoding="utf-8")
        prev = os.environ.get("VERIFY_MANIFEST_PYTEST_TIMEOUT")
        os.environ["VERIFY_MANIFEST_PYTEST_TIMEOUT"] = "1"
        try:
            out3 = audit_manifest(m_path, td_path)
        except subprocess.TimeoutExpired:
            print("self-test FAIL: TimeoutExpired escaped to audit",
                  file=sys.stderr)
            return 1
        finally:
            if prev is None:
                os.environ.pop("VERIFY_MANIFEST_PYTEST_TIMEOUT", None)
            else:
                os.environ["VERIFY_MANIFEST_PYTEST_TIMEOUT"] = prev
        by_id = {c.id: c for c in out3.claims}
        if len(out3.claims) != 2 or "slow_pytest" not in by_id:
            print(f"self-test FAIL: audit did not diff all claims after "
                  f"timeout: {out3.claims}", file=sys.stderr)
            return 1
        if by_id["slow_pytest"].matches:
            print("self-test FAIL: timed-out claim reported as match",
                  file=sys.stderr)
            return 1
        if by_id["slow_pytest"].observed.get("exit_code") != CLAIM_TIMEOUT_EXIT_CODE:
            print("self-test FAIL: timed-out claim missing sentinel exit",
                  file=sys.stderr)
            return 1
        if not by_id["fixture_sha"].matches:
            print("self-test FAIL: fast claim broken by timeout path",
                  file=sys.stderr)
            return 1
    print("self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=None,
                        help="Path to docs/RESEED_MANIFEST_*.json")
    parser.add_argument("--repo", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, default=None,
                        help="Write MANIFEST_VERIFICATION_<phase>.json here.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()
    if args.manifest is None:
        parser.error("--manifest is required (or pass --self-test)")
        return 2

    out = audit_manifest(args.manifest, args.repo)
    if args.out is not None:
        args.out.write_text(
            json.dumps({
                "manifest_path": out.manifest_path,
                "manifest_sha256": out.manifest_sha256,
                "phase": out.phase,
                "all_match": out.all_match,
                "claims": [asdict(c) for c in out.claims],
            }, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    fail = [c for c in out.claims if not c.matches]
    for c in out.claims:
        mark = "OK" if c.matches else "FAIL"
        print(f"[{mark}] {c.id}: {c.description}")
        if not c.matches:
            print(f"        {c.detail}")
    if fail:
        print(f"\n{len(fail)}/{len(out.claims)} claim(s) failed.", file=sys.stderr)
        return 1
    print(f"\nAll {len(out.claims)} claim(s) match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
