"""Tests for tools/verify_no_deferral.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import verify_no_deferral as v  # noqa: E402


def test_clean_file_has_no_hits(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    f.write_text("# Title\nAll sources ingested.\nNothing pending.\n", encoding="utf-8")
    assert v.scan_files([f]) == []


@pytest.mark.parametrize("marker", [
    "TBD", "FIXME", "TODO", "XXX",
    "deferred to phase 4",
    "will defer to next quarter",
    "v1.5 only",
    "future work",
    "eventually we will",
    "later phase",
])
def test_each_marker_flagged(tmp_path: Path, marker: str) -> None:
    f = tmp_path / "doc.md"
    f.write_text(f"some sentence containing {marker} inside.\n", encoding="utf-8")
    hits = v.scan_files([f])
    assert hits, f"expected hit for marker {marker!r}"


def test_case_insensitive(tmp_path: Path) -> None:
    f = tmp_path / "doc.md"
    f.write_text("Section TbD.\n", encoding="utf-8")
    assert v.scan_files([f])


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        v.scan_files([tmp_path / "no.md"])


def test_main_clean_exits_zero(tmp_path: Path) -> None:
    f = tmp_path / "ok.md"
    f.write_text("everything done.\n", encoding="utf-8")
    assert v.main(["--path", str(f)]) == 0


def test_main_dirty_exits_one(tmp_path: Path) -> None:
    f = tmp_path / "bad.md"
    f.write_text("we'll figure it out eventually.\n", encoding="utf-8")
    assert v.main(["--path", str(f)]) == 1


def test_main_missing_path_exits_one(tmp_path: Path) -> None:
    assert v.main(["--path", str(tmp_path / "missing.md")]) == 1


def test_self_test_exits_zero() -> None:
    assert v.main(["--self-test"]) == 0


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        v.main(["--help"])
    assert exc.value.code == 0
