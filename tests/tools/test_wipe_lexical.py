"""Tests for tools/wipe_lexical.py.

Uses a fake Neo4j driver. Covers:
* token format
* refuses on missing / mismatched token
* APOC path wipe
* manual-batch path when APOC absent
* constraint + non-LOOKUP index drop
* post-check refuses to call clean when residue remains
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import wipe_lexical as w  # noqa: E402


# ---------- token ----------

def test_token_format() -> None:
    t = w.WipeToken.fresh()
    assert t.value.startswith("WIPE-LEXICAL-")
    parts = t.value.split("-")
    # WIPE LEXICAL <ts> <rand>
    assert len(parts) == 4
    assert parts[2].isdigit()
    assert len(parts[3]) == 8


def test_confirm_exact() -> None:
    t = w.WipeToken(value="WIPE-LEXICAL-1-aabbccdd")
    assert w._confirm(t, stdin_text="WIPE-LEXICAL-1-aabbccdd")
    assert w._confirm(t, stdin_text="WIPE-LEXICAL-1-aabbccdd\n")
    assert not w._confirm(t, stdin_text="WIPE-LEXICAL-1-AABBCCDD")
    assert not w._confirm(t, stdin_text="wrong")
    assert not w._confirm(t, stdin_text="")
    assert not w._confirm(t, stdin_text=None)


# ---------- wipe via fake driver ----------

def test_apoc_path_wipes_everything() -> None:
    drv = w._FakeDriver(
        nodes=100_000,
        constraints=["c1", "c2", "c3"],
        indexes=[("a", "RANGE"), ("b", "LOOKUP"), ("c", "TEXT")],
        apoc_available=True,
    )
    used_apoc, deleted, ncon, nidx = w.perform_wipe(drv)
    assert used_apoc is True
    assert deleted == -1
    assert ncon == 3
    assert nidx == 2  # the LOOKUP one survives
    pc = w.post_check(drv)
    assert pc.clean


def test_manual_batch_path_when_apoc_absent() -> None:
    drv = w._FakeDriver(nodes=25_000, apoc_available=False)
    used_apoc, deleted, _, _ = w.perform_wipe(drv)
    assert used_apoc is False
    assert deleted == 25_000
    assert w.post_check(drv).node_count == 0


def test_post_check_detects_residue() -> None:
    drv = w._FakeDriver(nodes=10, constraints=[], indexes=[])
    pc = w.post_check(drv)
    assert not pc.clean
    assert pc.node_count == 10


# ---------- CLI ----------

def test_main_refuses_without_token() -> None:
    drv = w._FakeDriver(nodes=10)
    rc = w.main(
        ["--token", "nope"],
        driver_factory=lambda: drv,
    )
    assert rc == 2
    assert drv._nodes == 10  # untouched


def test_main_proceeds_with_correct_token(monkeypatch: pytest.MonkeyPatch) -> None:
    drv = w._FakeDriver(nodes=1_500, constraints=["x"], indexes=[("idx", "RANGE")])
    # The token is generated inside main(); intercept it.
    captured: list[str] = []
    real = w.WipeToken.fresh

    def fake_fresh() -> w.WipeToken:
        t = real()
        captured.append(t.value)
        return t

    monkeypatch.setattr(w.WipeToken, "fresh", classmethod(lambda cls: fake_fresh()))
    # Have stdin read the token main() will print.
    # We can't pre-know it; instead feed via --token after calling main with
    # an interactive stdin fed *after* fresh() runs. Use a Capturing Stream.

    class LateStream:
        def __init__(self) -> None:
            self._buf: str | None = None

        def readline(self) -> str:
            if self._buf is None:
                self._buf = captured[-1]
            return self._buf + "\n"

    rc = w.main([], stdin=LateStream(), driver_factory=lambda: drv)
    assert rc == 0
    pc = w.post_check(drv)
    assert pc.clean


def test_main_post_check_only_does_not_wipe() -> None:
    drv = w._FakeDriver(nodes=10, constraints=[], indexes=[])
    rc = w.main(["--post-check"], driver_factory=lambda: drv)
    # post-check alone should fail because residue exists
    assert rc == 1
    assert drv._nodes == 10  # untouched


def test_main_post_check_passes_when_clean() -> None:
    drv = w._FakeDriver(nodes=0, constraints=[], indexes=[])
    rc = w.main(["--post-check"], driver_factory=lambda: drv)
    assert rc == 0


def test_self_test_exits_zero() -> None:
    assert w.main(["--self-test"]) == 0


def test_help_flag_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        w.main(["--help"])
    assert exc.value.code == 0
