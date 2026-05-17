"""Tests for tools/derive_expected_counts.py.

Builds tiny fixture files in a temp dir, runs the deriver, and asserts
both methods agree and the +/-5% band is correct. A deliberately
divergent counter is also tested.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import derive_expected_counts as d  # noqa: E402


# ---------- counters agree ----------

def test_line_count_tsv_with_header(tmp_path: Path) -> None:
    p = tmp_path / "x.tsv"
    p.write_text("h1\th2\n1\ta\n2\tb\n3\tc\n4\td\n", encoding="utf-8")
    r = d.count_lines(p, skip_header=True)
    assert r.method_a == r.method_b == 4
    assert r.agree


def test_line_count_missing_trailing_newline(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("a\nb\nc", encoding="utf-8")  # no trailing \n
    r = d.count_lines(p, skip_header=False)
    assert r.method_a == r.method_b == 3, (r.method_a, r.method_b)


def test_xml_count_simple(tmp_path: Path) -> None:
    p = tmp_path / "x.xml"
    p.write_text("<r><w/><w/><w/></r>", encoding="utf-8")
    r = d.count_xml(p, "w")
    assert r.method_a == r.method_b == 3


def test_xml_count_nested(tmp_path: Path) -> None:
    p = tmp_path / "x.xml"
    p.write_text(
        "<r><a><w/></a><a><w/><w/></a><b><w/></b></r>", encoding="utf-8",
    )
    r = d.count_xml(p, "w")
    assert r.method_a == r.method_b == 4


# ---------- tolerance band ----------

def test_to_band_5pct() -> None:
    band = d.to_band(1000, derivation="x")
    assert band["min"] == 950
    assert band["max"] == 1050
    assert band["central"] == 1000


def test_to_band_rounding() -> None:
    band = d.to_band(7, derivation="x")
    assert band["min"] == math.floor(7 * 0.95)
    assert band["max"] == math.ceil(7 * 1.05)


# ---------- derive_for_source ----------

def test_derive_for_source_tsv(tmp_path: Path) -> None:
    root = tmp_path
    sub = root / "tiny"
    sub.mkdir()
    f = sub / "data.tsv"
    f.write_text("h1\th2\n" + "x\ty\n" * 100, encoding="utf-8")
    spec = d.SourceSpec("tiny", "tiny/data.tsv", "tsv", skip_header=True)
    band = d.derive_for_source(root, spec)
    assert band is not None
    assert band["central"] == 100
    assert band["min"] == 95
    assert band["max"] == 105
    assert "source=tiny/data.tsv" in band["derivation"]


def test_derive_for_source_missing_raises(tmp_path: Path) -> None:
    spec = d.SourceSpec("missing", "no/such/file.tsv", "tsv", skip_header=False)
    with pytest.raises(FileNotFoundError) as exc:
        d.derive_for_source(tmp_path, spec)
    assert "no/such/file.tsv" in str(exc.value).replace("\\", "/")


def test_derive_for_source_optional_missing_returns_none(tmp_path: Path) -> None:
    spec = d.SourceSpec("o", "no/such.tsv", "tsv", optional=True)
    assert d.derive_for_source(tmp_path, spec) is None


def test_counter_mismatch_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Force the two counters to disagree by >1%; deriver must raise."""
    p = tmp_path / "x.tsv"
    p.write_text("a\nb\nc\nd\ne\nf\ng\nh\ni\nj\n", encoding="utf-8")

    def fake_python_count(_p: Path, *, skip_header: bool) -> int:
        return 10

    def fake_wc_count(_p: Path, *, skip_header: bool) -> int:
        return 20  # 100% off

    monkeypatch.setattr(d, "_count_lines_python", fake_python_count)
    monkeypatch.setattr(d, "_count_lines_wc", fake_wc_count)
    spec = d.SourceSpec("bad", "x.tsv", "tsv", skip_header=False)
    with pytest.raises(RuntimeError) as exc:
        d.derive_for_source(tmp_path, spec)
    assert "counter mismatch" in str(exc.value)


# ---------- canonical json + check mode ----------

def test_canonical_json_is_stable() -> None:
    a = d.canonical_json({"b": 1, "a": [3, 2, 1]})
    b = d.canonical_json({"a": [3, 2, 1], "b": 1})
    assert a == b


def test_main_self_test() -> None:
    assert d.main(["--self-test"]) == 0


def test_main_writes_snapshot(tmp_path: Path) -> None:
    # Build a tiny fixture data root with just tskxref-shaped file.
    root = tmp_path / "data" / "private"
    (root / "macula-hebrew" / "WLC" / "tsv").mkdir(parents=True)
    (root / "macula-hebrew" / "WLC" / "tsv" / "macula-hebrew.tsv").write_text(
        "hdr1\thdr2\n" + "v\tv\n" * 50, encoding="utf-8",
    )
    (root / "tskxref.txt").write_text("a\nb\nc\n", encoding="utf-8")
    out = tmp_path / "out.json"
    rc = d.main(["--data-root", str(root), "--out", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "macula_hebrew_tsv" in payload["sources"]
    assert payload["sources"]["macula_hebrew_tsv"]["central"] == 50
    assert payload["sources"]["tsk_xref"]["central"] == 3


def test_main_check_detects_drift(tmp_path: Path) -> None:
    root = tmp_path / "data" / "private"
    (root / "macula-hebrew" / "WLC" / "tsv").mkdir(parents=True)
    (root / "macula-hebrew" / "WLC" / "tsv" / "macula-hebrew.tsv").write_text(
        "hdr1\thdr2\n" + "v\tv\n" * 50, encoding="utf-8",
    )
    (root / "tskxref.txt").write_text("a\nb\nc\n", encoding="utf-8")
    out = tmp_path / "out.json"
    assert d.main(["--data-root", str(root), "--out", str(out)]) == 0
    # Mutate fixture so re-derivation produces different counts.
    (root / "tskxref.txt").write_text("a\nb\nc\nd\ne\nf\n", encoding="utf-8")
    rc = d.main(["--data-root", str(root), "--out", str(out), "--check"])
    assert rc == 1
