"""Reject deferral/punt language in architecture + phase-02 docs.

Grep-style scan over a fixed allowlist of documentation files (override
with ``--path``) looking for any of these case-insensitive markers:

    deferred, defer to, v1.5, future, TBD, FIXME, TODO, XXX,
    eventually, later

A single hit anywhere exits 1 with the offending file:line:text printed.

Usage:
    python tools/verify_no_deferral.py [--path FILE [FILE ...]]
                                       [--self-test]
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PATTERN = re.compile(
    r"(deferred|defer to|v1\.5|future|TBD|FIXME|TODO|XXX|eventually|later)",
    re.IGNORECASE,
)

DEFAULT_PATHS: tuple[str, ...] = (
    "docs/ARCHITECTURE.md",
    "docs/implementation_phases/phase_02_lexical_ingest.md",
)


@dataclass(frozen=True)
class Hit:
    path: Path
    line_no: int
    text: str
    match: str


def scan_text(text: str, path: Path) -> list[Hit]:
    hits: list[Hit] = []
    for i, line in enumerate(text.splitlines(), start=1):
        m = PATTERN.search(line)
        if m:
            hits.append(Hit(path=path, line_no=i, text=line.rstrip(), match=m.group(0)))
    return hits


def scan_files(paths: Iterable[Path]) -> list[Hit]:
    hits: list[Hit] = []
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"verify_no_deferral: path missing: {p}")
        hits.extend(scan_text(p.read_text(encoding="utf-8"), p))
    return hits


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        clean = Path(td) / "clean.md"
        clean.write_text("# Architecture\n\nAll layers are ingested today.\n",
                         encoding="utf-8")
        dirty = Path(td) / "dirty.md"
        dirty.write_text("# Plan\n\nThis will be done eventually (TBD).\n",
                         encoding="utf-8")
        if scan_files([clean]):
            print("self-test FAIL: clean file flagged", file=sys.stderr)
            return 1
        bad = scan_files([dirty])
        if len(bad) < 1:
            print(f"self-test FAIL: dirty file not flagged: {bad}", file=sys.stderr)
            return 1
        matches = {h.match.lower() for h in bad}
        if not (matches & {"tbd", "eventually"}):
            print(f"self-test FAIL: dirty file flagged wrong tokens: {matches}",
                  file=sys.stderr)
            return 1
    print("self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path", nargs="+", type=Path, default=None,
        help="Override default doc paths.",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    repo_root = Path(__file__).resolve().parents[1]
    paths = args.path if args.path else [repo_root / p for p in DEFAULT_PATHS]
    try:
        hits = scan_files(paths)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not hits:
        print(f"OK: {len(paths)} file(s) scanned, zero deferral markers.")
        return 0
    print(f"FAIL: {len(hits)} deferral marker(s) found", file=sys.stderr)
    for h in hits:
        print(f"  {h.path}:{h.line_no}: [{h.match}] {h.text}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
