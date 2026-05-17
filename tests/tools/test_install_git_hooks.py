"""Tests for tools/install_git_hooks.py.

Verify:
* installed hook rejects a non-matching message
* installed hook accepts a matching message
* refusing to overwrite without ``--force``
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import install_git_hooks as h  # noqa: E402


def _fake_repo(tmp_path: Path) -> Path:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    return tmp_path


# ---------- regex semantics ----------

def test_run_hook_check_accepts_phase_message() -> None:
    ok, _ = h.run_hook_check("phase A.1: write SCHEMA_DECISIONS.md\n")
    assert ok


def test_run_hook_check_accepts_subsequent_phase() -> None:
    ok, _ = h.run_hook_check("phase Z.2: install verification harness\n")
    assert ok


def test_run_hook_check_rejects_blank() -> None:
    ok, _ = h.run_hook_check("")
    assert not ok


def test_run_hook_check_rejects_lowercase_letter() -> None:
    ok, _ = h.run_hook_check("phase a.1: lowercase\n")
    assert not ok


def test_run_hook_check_rejects_no_phase_prefix() -> None:
    ok, _ = h.run_hook_check("feat: do a thing\n")
    assert not ok


def test_run_hook_check_rejects_no_space_after_colon() -> None:
    ok, _ = h.run_hook_check("phase A.1:no-space\n")
    assert not ok


# ---------- install ----------

def test_install_writes_hook(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path)
    target = h.install(repo)
    assert target.exists()
    body = target.read_text(encoding="utf-8")
    assert "phase" in body and "A-Z" in body


def test_install_refuses_overwrite_without_force(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path)
    h.install(repo)
    with pytest.raises(FileExistsError):
        h.install(repo)


def test_install_overwrites_with_force(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path)
    h.install(repo)
    h.install(repo, force=True)  # must not raise


def test_install_fails_without_git_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        h.install(tmp_path)


# ---------- live invocation of installed hook ----------

def test_installed_python_hook_rejects_bad_message(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path)
    hook = h.install(repo)
    msg = tmp_path / "COMMIT_EDITMSG"
    rc, stderr = h.invoke_hook(hook, "wrong commit message\n", msg_path=msg)
    assert rc == 1
    assert "rejected" in stderr.lower()


def test_installed_python_hook_accepts_good_message(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path)
    hook = h.install(repo)
    msg = tmp_path / "COMMIT_EDITMSG"
    rc, _ = h.invoke_hook(hook, "phase A.1: lock schema\n", msg_path=msg)
    assert rc == 0


# ---------- CLI ----------

def test_main_installs_in_repo(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path)
    rc = h.main(["--repo", str(repo)])
    assert rc == 0
    assert h.hook_path(repo).exists()


def test_main_force_overwrites(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path)
    assert h.main(["--repo", str(repo)]) == 0
    assert h.main(["--repo", str(repo), "--force"]) == 0


def test_main_non_repo_fails(tmp_path: Path) -> None:
    assert h.main(["--repo", str(tmp_path)]) == 1


def test_self_test_exits_zero() -> None:
    assert h.main(["--self-test"]) == 0


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        h.main(["--help"])
    assert exc.value.code == 0
