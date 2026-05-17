"""Tests for tools/preflight.py.

Each prerequisite (cypher-shell, pytest_socket, APOC) is simulated as
present and absent. The script must exit nonzero on any missing prereq.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import preflight  # noqa: E402


# ---------- cypher-shell ----------

def test_cypher_shell_missing_reports_failure() -> None:
    with patch("tools.preflight.shutil.which", return_value=None):
        r = preflight._check_cypher_shell()
    assert not r.ok
    assert "not on PATH" in r.observed


def test_cypher_shell_present_reports_ok() -> None:
    fake_proc = types.SimpleNamespace(returncode=0, stdout="cypher-shell 5.26.0", stderr="")
    with patch("tools.preflight.shutil.which", return_value="/usr/bin/cypher-shell"), \
         patch("tools.preflight.subprocess.run", return_value=fake_proc):
        r = preflight._check_cypher_shell()
    assert r.ok
    assert "5.26.0" in r.observed


def test_cypher_shell_nonzero_exit_reports_failure() -> None:
    fake_proc = types.SimpleNamespace(returncode=2, stdout="", stderr="boom")
    with patch("tools.preflight.shutil.which", return_value="/usr/bin/cypher-shell"), \
         patch("tools.preflight.subprocess.run", return_value=fake_proc):
        r = preflight._check_cypher_shell()
    assert not r.ok
    assert "exit 2" in r.observed


# ---------- pytest_socket ----------

def test_pytest_socket_present() -> None:
    r = preflight._check_pytest_socket()
    # The dev env installs pytest-socket; this asserts the success path.
    assert r.ok, f"pytest_socket should be importable, got {r.observed}"


def test_pytest_socket_absent_reports_failure() -> None:
    with patch("tools.preflight.importlib.util.find_spec", return_value=None):
        r = preflight._check_pytest_socket()
    assert not r.ok
    assert "ModuleNotFoundError" in r.observed


# ---------- APOC ----------

class _FakeSession:
    def __init__(self, count: int) -> None:
        self._count = count
        self._raise: Exception | None = None

    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, *a: object) -> None:
        return None

    def run(self, _query: str) -> "_FakeRecord":
        if self._raise is not None:
            raise self._raise
        return _FakeRecord(self._count)


class _FakeRecord:
    def __init__(self, count: int) -> None:
        self._count = count

    def single(self) -> dict[str, int]:
        return {"n": self._count}


class _FakeDriver:
    def __init__(self, count: int) -> None:
        self._count = count
        self.closed = False

    def session(self) -> _FakeSession:
        return _FakeSession(self._count)

    def close(self) -> None:
        self.closed = True


def test_apoc_pass_when_procedure_count_above_floor() -> None:
    r = preflight._check_apoc(driver_factory=lambda: _FakeDriver(450))
    assert r.ok, r.observed


def test_apoc_fail_when_procedure_count_below_floor() -> None:
    r = preflight._check_apoc(driver_factory=lambda: _FakeDriver(10))
    assert not r.ok
    assert "10 apoc procedures" in r.observed


def test_apoc_fail_when_driver_init_raises() -> None:
    def boom() -> object:
        raise RuntimeError("no socket")
    r = preflight._check_apoc(driver_factory=boom)
    assert not r.ok
    assert "no socket" in r.observed


def test_apoc_fail_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("NEO4J_LEXICAL_URI", "NEO4J_LEXICAL_USER", "NEO4J_LEXICAL_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    r = preflight._check_apoc()
    assert not r.ok
    assert "missing NEO4J_LEXICAL_* env vars" in r.observed


# ---------- main ----------

def test_main_self_test_exits_zero_when_pytest_socket_present() -> None:
    rc = preflight.main(["--self-test"])
    assert rc == 0


def test_main_exits_nonzero_when_any_check_fails() -> None:
    # Force cypher-shell missing; pytest_socket present; skip apoc.
    with patch("tools.preflight.shutil.which", return_value=None):
        rc = preflight.main(["--skip-apoc"])
    assert rc == 1


def test_main_exits_zero_when_all_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_proc = types.SimpleNamespace(returncode=0, stdout="cypher-shell 5", stderr="")
    monkeypatch.setattr("tools.preflight.shutil.which", lambda _x: "/usr/bin/cypher-shell")
    monkeypatch.setattr("tools.preflight.subprocess.run", lambda *a, **k: fake_proc)
    rc = preflight.main(["--skip-apoc"])
    assert rc == 0


def test_help_flag_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        preflight.main(["--help"])
    assert exc.value.code == 0
