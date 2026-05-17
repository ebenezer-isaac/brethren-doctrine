"""Derive expected row counts (with +/-5% tolerance) for lexical sources.

Reads source data files under ``data/private/`` and emits
``tools/expected_counts.json``. Each entry uses two independent counting
methods so a silent regression in one method does not propagate:

* Line-based files (TSV, plain text): Python streaming parse vs ``wc -l``.
* XML files: ``lxml.etree.iterparse`` (event stream) vs
  ``etree.fromstring().findall`` over a serialised tree.

The two methods must agree to within 1% or the script aborts. The
recorded counts then take the central value and emit
``{"min": floor(0.95 * n), "max": ceil(1.05 * n), "derivation": "..."}``.

Usage:
    python tools/derive_expected_counts.py [--data-root PATH]
                                           [--out FILE]
                                           [--check]
                                           [--self-test]

``--check`` re-derives and compares to the committed snapshot, exit 0
only on byte-identical JSON.
``--self-test`` runs the counting helpers against an in-process fixture
and exits 0 if both methods agree.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from lxml import etree


TOLERANCE = 0.05  # +/- 5%
METHOD_AGREEMENT = 0.01  # methods must agree within 1%


@dataclass(frozen=True)
class CountResult:
    method_a: int
    method_b: int
    method_a_name: str
    method_b_name: str

    @property
    def central(self) -> int:
        # Use floor average for determinism; methods are required to
        # agree within METHOD_AGREEMENT, so the choice is robust.
        return (self.method_a + self.method_b) // 2

    @property
    def agree(self) -> bool:
        if self.method_a == self.method_b:
            return True
        denom = max(self.method_a, self.method_b)
        if denom == 0:
            return False
        return abs(self.method_a - self.method_b) / denom <= METHOD_AGREEMENT


# ---------- line counters ----------

def _count_lines_python(path: Path, *, skip_header: bool) -> int:
    """Stream-count lines via Python; optionally skip the first line."""
    n = 0
    with path.open("rb") as fh:
        for _ in fh:
            n += 1
    if skip_header and n > 0:
        n -= 1
    return n


def _count_lines_wc(path: Path, *, skip_header: bool) -> int:
    """Count lines via ``wc -l`` if available, else a Python re-implementation
    that uses ``read``+``count`` (independent algorithm)."""
    wc = shutil.which("wc")
    if wc is not None:
        try:
            proc = subprocess.run(
                [wc, "-l", str(path)],
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )
            n = int(proc.stdout.strip().split()[0])
        except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired):
            n = _count_lines_chunked(path)
    else:
        n = _count_lines_chunked(path)
    # wc -l counts newline terminators; a file with no trailing \n loses 1
    # row. Python iter handles that. Normalise: if the file's last byte is
    # not \n, add 1 (only meaningful if file is non-empty).
    if path.stat().st_size > 0:
        with path.open("rb") as fh:
            fh.seek(-1, io.SEEK_END)
            if fh.read(1) != b"\n":
                n += 1
    if skip_header and n > 0:
        n -= 1
    return n


def _count_lines_chunked(path: Path) -> int:
    """Independent chunked newline-count fallback for ``wc``."""
    total = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            total += chunk.count(b"\n")
    return total


def count_lines(path: Path, *, skip_header: bool) -> CountResult:
    a = _count_lines_python(path, skip_header=skip_header)
    b = _count_lines_wc(path, skip_header=skip_header)
    return CountResult(a, b, "python_iter", "wc_or_chunked_count")


# ---------- XML counters ----------

def _count_xml_iterparse(path: Path, tag: str) -> int:
    n = 0
    for _, elem in etree.iterparse(str(path), events=("end",), tag=tag):
        n += 1
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
    return n


def _count_xml_findall(path: Path, tag: str) -> int:
    # Independent: load full tree then findall. Uses a different code
    # path (DOM build) than iterparse (event stream).
    with path.open("rb") as fh:
        tree = etree.fromstring(fh.read())
    # Strip namespaces from the search tag if caller provided a plain
    # local name; emulate iterparse's tag matching by using local-name().
    if tag.startswith("{") or "}" in tag:
        return len(tree.findall(f".//{tag}"))
    found = tree.xpath(f".//*[local-name()='{tag}']")
    return len(found)


def count_xml(path: Path, tag: str) -> CountResult:
    a = _count_xml_iterparse(path, tag)
    b = _count_xml_findall(path, tag)
    return CountResult(a, b, "lxml_iterparse", "lxml_findall")


# ---------- tolerance band ----------

def to_band(n: int, derivation: str) -> dict[str, object]:
    lo = math.floor(n * (1 - TOLERANCE))
    hi = math.ceil(n * (1 + TOLERANCE))
    return {
        "min": lo,
        "max": hi,
        "central": n,
        "derivation": derivation,
    }


# ---------- source registry ----------

@dataclass(frozen=True)
class SourceSpec:
    slug: str
    relpath: str
    kind: str  # "tsv", "txt", "xml-glob"
    xml_tag: str | None = None
    skip_header: bool = False
    optional: bool = False


SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec("macula_hebrew_tsv", "macula-hebrew/WLC/tsv/macula-hebrew.tsv",
               "tsv", skip_header=True),
    SourceSpec("tsk_xref", "tskxref.txt", "txt"),
)


def derive_for_source(data_root: Path, spec: SourceSpec) -> dict[str, object] | None:
    path = data_root / spec.relpath
    if not path.exists():
        if spec.optional:
            return None
        raise FileNotFoundError(
            f"source missing for slug={spec.slug!r}: expected at {path}"
        )
    if spec.kind in ("tsv", "txt"):
        result = count_lines(path, skip_header=spec.skip_header)
    elif spec.kind == "xml":
        assert spec.xml_tag is not None
        result = count_xml(path, spec.xml_tag)
    else:
        raise ValueError(f"unsupported source kind: {spec.kind}")
    if not result.agree:
        raise RuntimeError(
            f"counter mismatch for slug={spec.slug!r}: "
            f"{result.method_a_name}={result.method_a} "
            f"{result.method_b_name}={result.method_b} "
            f"(must agree within {METHOD_AGREEMENT * 100}%)"
        )
    return to_band(
        result.central,
        derivation=(
            f"source={spec.relpath} kind={spec.kind} "
            f"{result.method_a_name}={result.method_a} "
            f"{result.method_b_name}={result.method_b} "
            f"tolerance=+/-{TOLERANCE * 100:.0f}%"
        ),
    )


def derive_all(data_root: Path) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for spec in SOURCES:
        band = derive_for_source(data_root, spec)
        if band is not None:
            out[spec.slug] = band
    return out


def canonical_json(obj: object) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# ---------- self-test ----------

def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tsv = Path(td) / "tiny.tsv"
        tsv.write_text("h1\th2\n1\ta\n2\tb\n3\tc\n", encoding="utf-8")
        r = count_lines(tsv, skip_header=True)
        if not r.agree or r.central != 3:
            print(f"self-test FAIL: line counter central={r.central} a={r.method_a} b={r.method_b}",
                  file=sys.stderr)
            return 1
        xml = Path(td) / "tiny.xml"
        xml.write_text(
            "<root><w/><w/><w/><w/><w/></root>", encoding="utf-8",
        )
        r2 = count_xml(xml, "w")
        if not r2.agree or r2.central != 5:
            print(f"self-test FAIL: xml counter central={r2.central} a={r2.method_a} b={r2.method_b}",
                  file=sys.stderr)
            return 1
    print("self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "private",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "expected_counts.json",
    )
    parser.add_argument("--check", action="store_true",
                        help="Compare against existing snapshot; exit nonzero on drift.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    try:
        result = derive_all(args.data_root)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"derivation failed: {exc}", file=sys.stderr)
        return 1

    payload = {
        "sources": result,
        "tolerance_pct": TOLERANCE * 100,
        "method_agreement_pct": METHOD_AGREEMENT * 100,
    }
    text = canonical_json(payload)

    if args.check:
        if not args.out.exists():
            print(f"--check: snapshot missing at {args.out}", file=sys.stderr)
            return 1
        existing = args.out.read_text(encoding="utf-8")
        if existing != text:
            print("--check: snapshot drift detected", file=sys.stderr)
            return 1
        print("--check: snapshot matches")
        return 0

    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out} with {len(result)} source(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
