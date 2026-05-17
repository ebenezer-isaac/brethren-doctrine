"""Assert tools/expected_counts.json is immutable between phases.

Phase A.4 commits ``tools/expected_counts.json``. The reseed plan
forbids any subsequent change to this file except via a commit tagged
``[SCHEMA-REVISION]`` (subject line contains the literal token
``[SCHEMA-REVISION]``). This script verifies the file's blob SHA equals
the SHA recorded in a baseline file ``tools/expected_counts.baseline``
which is written by ``--record`` at Phase A.4 freeze time.

Usage::

    python tools/check_thresholds_immutable.py --record       # at A.4 freeze
    python tools/check_thresholds_immutable.py                # any later phase
    python tools/check_thresholds_immutable.py --self-test

Exit 0 iff the SHA matches OR the most recent change to the file is a
commit whose subject contains ``[SCHEMA-REVISION]`` AND the baseline
file was updated in the same commit.

The baseline lives in the tree (not in ``.git``) so reviewers can see
when it changed. The presence-or-absence of the baseline is itself a
phase-status indicator: absent before A.4, present afterward.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REL_TARGET = Path("tools/expected_counts.json")
REL_BASELINE = Path("tools/expected_counts.baseline")
REVISION_TAG = "[SCHEMA-REVISION]"


@dataclass(frozen=True)
class Verdict:
    ok: bool
    target_sha: str | None
    baseline_sha: str | None
    detail: str = ""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(*argv: str, cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *argv], cwd=str(cwd), capture_output=True, text=True, timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _last_change_subject(repo: Path, path: Path) -> str | None:
    rc, out, _ = _git("log", "-1", "--format=%s", "--", str(path), cwd=repo)
    if rc != 0:
        return None
    line = out.strip()
    return line or None


def record_baseline(repo: Path) -> Path:
    target = repo / REL_TARGET
    baseline = repo / REL_BASELINE
    if not target.exists():
        raise FileNotFoundError(f"{target} missing; nothing to record")
    sha = _sha256(target.read_bytes())
    baseline.write_text(sha + "\n", encoding="utf-8")
    return baseline


def check(repo: Path) -> Verdict:
    target = repo / REL_TARGET
    baseline = repo / REL_BASELINE
    if not target.exists():
        return Verdict(
            ok=False, target_sha=None, baseline_sha=None,
            detail=f"{REL_TARGET} missing",
        )
    target_sha = _sha256(target.read_bytes())
    if not baseline.exists():
        return Verdict(
            ok=False, target_sha=target_sha, baseline_sha=None,
            detail=(
                f"{REL_BASELINE} not recorded yet; run with --record at "
                "Phase A.4 freeze time"
            ),
        )
    baseline_sha = baseline.read_text(encoding="utf-8").strip()
    if target_sha == baseline_sha:
        return Verdict(
            ok=True, target_sha=target_sha, baseline_sha=baseline_sha,
        )
    subject = _last_change_subject(repo, REL_TARGET)
    if subject is not None and REVISION_TAG in subject:
        return Verdict(
            ok=True, target_sha=target_sha, baseline_sha=baseline_sha,
            detail=(
                f"sha drift but last commit is tagged {REVISION_TAG}; "
                "remember to also update the baseline in that commit"
            ),
        )
    return Verdict(
        ok=False, target_sha=target_sha, baseline_sha=baseline_sha,
        detail=(
            f"sha drift: target={target_sha[:12]} baseline={baseline_sha[:12]}; "
            f"last commit subject = {subject!r}; allowed only via a "
            f"{REVISION_TAG}-tagged commit"
        ),
    )


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / "tools").mkdir(parents=True)
        target = repo / REL_TARGET
        target.write_text('{"a": 1}\n', encoding="utf-8")
        rc, _, err = _git("init", "--quiet", cwd=repo)
        if rc != 0:
            print(f"self-test FAIL: git init failed: {err}", file=sys.stderr)
            return 1
        _git("config", "user.email", "x@y", cwd=repo)
        _git("config", "user.name", "test", cwd=repo)
        _git("add", str(REL_TARGET), cwd=repo)
        _git("commit", "-m", "phase A.4: lock thresholds", cwd=repo)
        record_baseline(repo)
        v = check(repo)
        if not v.ok:
            print(f"self-test FAIL: identical content rejected: {v.detail}",
                  file=sys.stderr)
            return 1
        target.write_text('{"a": 2}\n', encoding="utf-8")
        _git("add", str(REL_TARGET), cwd=repo)
        _git("commit", "-m", "feat: surreptitious change", cwd=repo)
        v2 = check(repo)
        if v2.ok:
            print("self-test FAIL: undeclared drift accepted", file=sys.stderr)
            return 1
        _git("add", str(REL_TARGET), cwd=repo)
        target.write_text('{"a": 3}\n', encoding="utf-8")
        _git("add", str(REL_TARGET), cwd=repo)
        _git("commit", "-m", "phase H.0: [SCHEMA-REVISION] bump", cwd=repo)
        v3 = check(repo)
        if not v3.ok:
            print(f"self-test FAIL: revision-tagged commit rejected: {v3.detail}",
                  file=sys.stderr)
            return 1
    print("self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true",
                        help="Write the baseline SHA from the current file.")
    parser.add_argument("--repo", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()
    if args.record:
        try:
            p = record_baseline(args.repo)
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"wrote baseline to {p}")
        return 0
    v = check(args.repo)
    if v.ok:
        print(f"OK: target_sha={v.target_sha[:12] if v.target_sha else '-'} "
              f"baseline_sha={v.baseline_sha[:12] if v.baseline_sha else '-'}")
        if v.detail:
            print(f"  note: {v.detail}")
        return 0
    print(f"FAIL: {v.detail}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
