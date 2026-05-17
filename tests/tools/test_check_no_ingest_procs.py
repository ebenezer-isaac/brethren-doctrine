"""Tests for tools/check_no_ingest_procs.py."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import check_no_ingest_procs as c  # noqa: E402


def test_find_offenders_catches_each_pattern() -> None:
    cases = [
        ("python.exe -m ingest.lexical.run", True),
        ("python.exe -m INGEST.LEXICAL.RUN", True),  # case-insensitive
        ("python.exe embed_lexical.py", True),
        ("python.exe -m embeddings.embed_cultural", True),
        ("python.exe -m tools.run_cultural_scrape", True),
        ("python.exe my_safe_script.py", False),
        ("python.exe -m pytest", False),
        ("python.exe -m tools.preflight", False),
    ]
    for cmdline, should_flag in cases:
        procs = [c.Process(pid=1, command_line=cmdline)]
        offenders = c.find_offenders(procs)
        if should_flag:
            assert offenders, f"expected to flag: {cmdline!r}"
        else:
            assert not offenders, f"unexpected flag: {cmdline!r}"


def test_parse_wmic_csv_basic() -> None:
    sample = (
        "Node,CommandLine,ProcessId\r\n"
        "HOST,python.exe -m ingest.lexical.run --dataset macula_hebrew,1234\r\n"
        "HOST,python.exe -m pytest tests,5678\r\n"
    )
    procs = c._parse_wmic_csv(sample)
    assert len(procs) == 2
    assert procs[0].pid == 1234
    assert "ingest.lexical" in procs[0].command_line
    assert procs[1].pid == 5678


def test_parse_wmic_csv_with_embedded_comma() -> None:
    sample = (
        "Node,CommandLine,ProcessId\r\n"
        "HOST,python.exe -c \"import x,y\" -m embed_lexical,42\r\n"
    )
    procs = c._parse_wmic_csv(sample)
    assert len(procs) == 1
    assert procs[0].pid == 42
    assert "embed_lexical" in procs[0].command_line


def test_main_zero_when_no_offenders() -> None:
    with patch("tools.check_no_ingest_procs.list_python_procs",
               return_value=[c.Process(1, "python.exe -m pytest")]):
        rc = c.main([])
    assert rc == 0


def test_main_nonzero_when_offenders() -> None:
    procs = [
        c.Process(1, "python.exe -m ingest.lexical.run"),
        c.Process(2, "python.exe -m pytest"),
    ]
    with patch("tools.check_no_ingest_procs.list_python_procs", return_value=procs):
        rc = c.main([])
    assert rc == 1


def test_self_test_exits_zero() -> None:
    assert c.main(["--self-test"]) == 0


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        c.main(["--help"])
    assert exc.value.code == 0
