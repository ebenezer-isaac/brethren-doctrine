"""Tests for tools/check_thresholds_immutable.py (RESEED_PLAN Z.1 item 4, D.4).

The immutability check must:

* succeed when ``tools/expected_counts.json`` sha matches the
  baseline file recorded at Phase A.4 freeze;
* fail when the sha drifts under an ordinary commit;
* succeed when the sha drifts under a commit whose subject contains
  ``[SCHEMA-REVISION]`` (the explicit revision-tag escape hatch);
* refuse to operate if the baseline is absent (Phase A.4 not yet
  executed);
* refuse to operate if the target file is missing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools import check_thresholds_immutable as cti


def _git(*argv: str, cwd: Path) -> None:
    subprocess.run(["git", *argv], cwd=str(cwd), check=True,
                   capture_output=True, text=True)


def _init_repo(p: Path) -> None:
    _git("init", "--quiet", cwd=p)
    _git("config", "user.email", "x@y", cwd=p)
    _git("config", "user.name", "test", cwd=p)


def _setup(repo: Path, initial: str = '{"a": 1}\n') -> None:
    _init_repo(repo)
    (repo / "tools").mkdir(parents=True, exist_ok=True)
    (repo / cti.REL_TARGET).write_text(initial, encoding="utf-8")
    _git("add", str(cti.REL_TARGET), cwd=repo)
    _git("commit", "-m", "phase A.4: lock thresholds", cwd=repo)


def test_self_test_exits_zero() -> None:
    assert cti.main(["--self-test"]) == 0


def test_record_then_check_passes(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _setup(repo)
    cti.record_baseline(repo)
    v = cti.check(repo)
    assert v.ok
    assert v.target_sha == v.baseline_sha


def test_undeclared_drift_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _setup(repo)
    cti.record_baseline(repo)
    (repo / cti.REL_TARGET).write_text('{"a": 2}\n', encoding="utf-8")
    _git("add", str(cti.REL_TARGET), cwd=repo)
    _git("commit", "-m", "feat: bump threshold without authorization", cwd=repo)
    v = cti.check(repo)
    assert not v.ok
    assert "drift" in v.detail.lower()


def test_revision_tagged_commit_accepted(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _setup(repo)
    cti.record_baseline(repo)
    (repo / cti.REL_TARGET).write_text('{"a": 99}\n', encoding="utf-8")
    _git("add", str(cti.REL_TARGET), cwd=repo)
    _git("commit", "-m",
         "phase H.0: [SCHEMA-REVISION] bump after auditor finding", cwd=repo)
    v = cti.check(repo)
    assert v.ok


def test_missing_target_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _init_repo(repo)
    (repo / "tools").mkdir()
    v = cti.check(repo)
    assert not v.ok
    assert "missing" in v.detail.lower()


def test_missing_baseline_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _setup(repo)
    v = cti.check(repo)
    assert not v.ok
    assert "baseline" in v.detail.lower() or "record" in v.detail.lower()


def test_record_baseline_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _setup(repo)
    p1 = cti.record_baseline(repo)
    sha1 = p1.read_text(encoding="utf-8").strip()
    p2 = cti.record_baseline(repo)
    sha2 = p2.read_text(encoding="utf-8").strip()
    assert sha1 == sha2


def test_record_raises_when_target_missing(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _init_repo(repo)
    (repo / "tools").mkdir()
    with pytest.raises(FileNotFoundError):
        cti.record_baseline(repo)


def test_main_record_writes_baseline(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _setup(repo)
    rc = cti.main(["--record", "--repo", str(repo)])
    assert rc == 0
    assert (repo / cti.REL_BASELINE).exists()


def test_main_check_returns_nonzero_on_drift(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _setup(repo)
    cti.record_baseline(repo)
    (repo / cti.REL_TARGET).write_text('{"a": 2}\n', encoding="utf-8")
    _git("add", str(cti.REL_TARGET), cwd=repo)
    _git("commit", "-m", "feat: rogue", cwd=repo)
    rc = cti.main(["--repo", str(repo)])
    assert rc == 1


def test_main_check_returns_zero_when_clean(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _setup(repo)
    cti.record_baseline(repo)
    rc = cti.main(["--repo", str(repo)])
    assert rc == 0
