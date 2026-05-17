"""Generic adapter verifier exercising the five C.1 acceptance checks.

Takes an importable module name via ``--adapter`` (e.g.
``tests.lexical.stubs.empty_required`` or
``ingest.lexical.macula_hebrew``) and runs:

1. ``required_field_empty``: every required field must be non-empty for
   every emitted record. Required fields are read from
   ``SCHEMA_DECISIONS.md`` (or a stub fallback) for the adapter slug;
   if the markdown is unavailable, the module's own
   ``REQUIRED_FIELDS`` tuple is used.
2. ``record_count_zero``: ``len(records) > 0``.
3. ``identical_lemma_per_word``: rejects when every record points at
   the same Lemma id (placeholder pollution).
4. ``edge_floor``: every required edge type emits at least the
   configured floor (default 5). Required edge types defaulted to
   ``IN_VERSE`` and ``INSTANCE_OF`` if not otherwise supplied.
5. ``hardcoded_response``: re-invokes the adapter on a second verse
   (when its ``emit_records`` accepts a ``verse`` argument) and rejects
   identical responses.

The verifier exits 0 only when all five pass. ``--self-test`` exercises
the verifier against one passing fixture and one failing fixture.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


DEFAULT_REQUIRED_EDGES: tuple[str, ...] = ("IN_VERSE", "INSTANCE_OF")
DEFAULT_EDGE_FLOOR = 5
DEFAULT_REQUIRED_FIELDS: tuple[str, ...] = ("lemma", "gloss", "ref")


@dataclass
class CheckResult:
    name: str
    ok: bool
    observed: str
    expected: str

    def format(self) -> str:
        status = "OK" if self.ok else "FAIL"
        return f"[{status}] {self.name}: observed={self.observed} expected={self.expected}"


# ---------- SCHEMA_DECISIONS parser ----------

def parse_required_fields_for(
    adapter_slug: str,
    schema_md: Path | None,
    module: Any = None,
) -> tuple[str, ...]:
    """Look up a per-adapter ``REQUIRED_FIELDS`` line in SCHEMA_DECISIONS.md.

    Looks for a line of the form::

        Adapter: <slug>
        Required fields: f1, f2, f3

    If the markdown is missing or has no entry, falls back to the
    imported module's own ``REQUIRED_FIELDS`` attribute (Phase Z stubs
    use this path). If neither source is available, returns the
    DEFAULT_REQUIRED_FIELDS tuple.
    """
    if schema_md is not None and schema_md.exists():
        text = schema_md.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"Adapter:\s*{re.escape(adapter_slug)}\s*\n"
            rf"\s*Required fields:\s*([^\n]+)",
            re.IGNORECASE,
        )
        m = pattern.search(text)
        if m:
            return tuple(f.strip() for f in m.group(1).split(",") if f.strip())
    if module is not None:
        mod_required = getattr(module, "REQUIRED_FIELDS", None)
        if mod_required:
            return tuple(mod_required)
    return DEFAULT_REQUIRED_FIELDS


# ---------- check helpers ----------

def _is_empty(v: Any) -> bool:
    import math
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, float):
        return math.isnan(v) or math.isinf(v)
    if isinstance(v, (list, tuple, dict, set)):
        return len(v) == 0
    return False


def check_required_fields(
    records: list[dict[str, Any]], required: tuple[str, ...],
) -> CheckResult:
    if not records:
        return CheckResult(
            "required_field_empty",
            ok=False,
            observed="no records to evaluate",
            expected=f"non-empty values for {required}",
        )
    bad: list[tuple[int, str]] = []
    for i, r in enumerate(records):
        for f in required:
            if _is_empty(r.get(f)):
                bad.append((i, f))
    if bad:
        sample = ", ".join(f"row{i}.{f}" for i, f in bad[:5])
        return CheckResult(
            "required_field_empty",
            ok=False,
            observed=f"{len(bad)} empty cell(s); e.g. {sample}",
            expected=f"all {required} non-empty",
        )
    return CheckResult(
        "required_field_empty",
        ok=True,
        observed=f"all {required} non-empty in {len(records)} record(s)",
        expected=f"all {required} non-empty",
    )


def check_record_count(records: list[dict[str, Any]]) -> CheckResult:
    n = len(records)
    return CheckResult(
        "record_count_zero",
        ok=(n > 0),
        observed=f"{n} records",
        expected="> 0 records",
    )


def check_identical_lemma(records: list[dict[str, Any]]) -> CheckResult:
    if not records:
        return CheckResult(
            "identical_lemma_per_word",
            ok=False,
            observed="no records",
            expected=">= 2 distinct lemma ids",
        )
    ids = {r.get("strong") or r.get("lemma_id") or r.get("lemma") for r in records}
    ids.discard(None)
    return CheckResult(
        "identical_lemma_per_word",
        ok=(len(ids) >= 2 or len(records) < 2),
        observed=f"{len(ids)} distinct lemma id(s) across {len(records)} record(s)",
        expected=">= 2 when records >= 2",
    )


def check_edge_floor(
    edges: list[dict[str, str]],
    required: tuple[str, ...],
    floor: int,
) -> list[CheckResult]:
    counts: dict[str, int] = {t: 0 for t in required}
    for e in edges:
        t = e.get("type", "")
        if t in counts:
            counts[t] += 1
    return [
        CheckResult(
            name=f"edge_floor[{t}]",
            ok=(counts[t] >= floor),
            observed=f"{counts[t]} edges of type {t}",
            expected=f">= {floor}",
        )
        for t in sorted(required)
    ]


def check_hardcoded_response(
    module: Any,
    *,
    verse_a: str = "GEN 1:1",
    verse_b: str = "MARK 1:1",
) -> CheckResult:
    """If ``emit_records`` takes a verse arg, call with two different
    verses and reject identical responses."""
    emit = getattr(module, "emit_records", None)
    if not callable(emit):
        return CheckResult(
            "hardcoded_response",
            ok=False,
            observed="adapter has no emit_records()",
            expected="callable emit_records",
        )
    sig = inspect.signature(emit)
    if "verse" not in sig.parameters:
        # Adapter does not accept verse switching; treat as passing the
        # "hardcoded" check, since it never claims to support a second
        # verse. (The deeper "real-data second-verse" check belongs to
        # the per-adapter coverage test.)
        return CheckResult(
            "hardcoded_response",
            ok=True,
            observed="emit_records has no verse param",
            expected="callable emit_records",
        )
    try:
        a = emit(verse=verse_a)
        b = emit(verse=verse_b)
    except TypeError as exc:
        return CheckResult(
            "hardcoded_response",
            ok=False,
            observed=f"emit_records raised: {exc}",
            expected="callable with verse=",
        )
    same = a == b
    return CheckResult(
        "hardcoded_response",
        ok=not same,
        observed=("identical payload for both verses" if same else "payloads differ"),
        expected="distinct payloads for distinct verses",
    )


# ---------- main verifier ----------

@dataclass
class Config:
    required_fields: tuple[str, ...] = DEFAULT_REQUIRED_FIELDS
    required_edges: tuple[str, ...] = DEFAULT_REQUIRED_EDGES
    edge_floor: int = DEFAULT_EDGE_FLOOR
    verse_a: str = "GEN 1:1"
    verse_b: str = "MARK 1:1"


def verify_module(module: Any, cfg: Config) -> list[CheckResult]:
    emit_records = getattr(module, "emit_records", None)
    emit_edges: Callable[[], list[dict[str, str]]] = getattr(
        module, "emit_edges", lambda: [],
    )
    if not callable(emit_records):
        return [CheckResult(
            "loadable",
            ok=False,
            observed=f"emit_records not callable on {module!r}",
            expected="callable emit_records()",
        )]
    try:
        records = emit_records()
    except TypeError:
        # Adapter requires args; try a default verse.
        records = emit_records(verse=cfg.verse_a)
    edges = emit_edges() if callable(emit_edges) else []
    results: list[CheckResult] = []
    results.append(check_record_count(records))
    results.append(check_required_fields(records, cfg.required_fields))
    results.append(check_identical_lemma(records))
    results.extend(check_edge_floor(edges, cfg.required_edges, cfg.edge_floor))
    results.append(check_hardcoded_response(
        module, verse_a=cfg.verse_a, verse_b=cfg.verse_b,
    ))
    return results


def verify_adapter(
    name: str,
    *,
    schema_md: Path | None,
    edge_floor: int,
) -> tuple[bool, list[CheckResult]]:
    try:
        module = importlib.import_module(name)
    except ImportError as exc:
        return False, [CheckResult(
            "import",
            ok=False,
            observed=f"ImportError: {exc}",
            expected=f"import {name}",
        )]
    slug = name.rsplit(".", 1)[-1]
    required = parse_required_fields_for(slug, schema_md, module=module)
    cfg = Config(required_fields=required, edge_floor=edge_floor)
    results = verify_module(module, cfg)
    return all(r.ok for r in results), results


# ---------- self-test ----------

class _GoodAdapter:
    @staticmethod
    def emit_records(verse: str = "GEN 1:1") -> list[dict[str, Any]]:
        if verse == "GEN 1:1":
            return [
                {"lemma": "rēšîṯ", "gloss": "beginning", "ref": "GEN 1:1", "strong": "H7225"},
                {"lemma": "bārāʾ", "gloss": "create", "ref": "GEN 1:1", "strong": "H1254"},
                {"lemma": "ʾĕlōhîm", "gloss": "God", "ref": "GEN 1:1", "strong": "H430"},
            ]
        return [
            {"lemma": "archē", "gloss": "beginning", "ref": "MARK 1:1", "strong": "G746"},
            {"lemma": "euangelion", "gloss": "gospel", "ref": "MARK 1:1", "strong": "G2098"},
            {"lemma": "Iēsous", "gloss": "Jesus", "ref": "MARK 1:1", "strong": "G2424"},
        ]

    @staticmethod
    def emit_edges() -> list[dict[str, str]]:
        return [
            {"type": "IN_VERSE", "src": f"w{i}", "dst": "GEN 1:1"} for i in range(6)
        ] + [
            {"type": "INSTANCE_OF", "src": f"w{i}", "dst": f"H{i}"} for i in range(6)
        ]


def _self_test() -> int:
    cfg = Config()
    good = verify_module(_GoodAdapter, cfg)
    if not all(r.ok for r in good):
        print(f"self-test FAIL: good adapter flagged: "
              f"{[r.format() for r in good if not r.ok]}", file=sys.stderr)
        return 1
    # Bad adapter: zero records.
    class _Bad:
        @staticmethod
        def emit_records() -> list[dict[str, Any]]: return []
        @staticmethod
        def emit_edges() -> list[dict[str, str]]: return []
    bad = verify_module(_Bad, cfg)
    if all(r.ok for r in bad):
        print("self-test FAIL: bad adapter passed", file=sys.stderr)
        return 1
    print("self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=str, default=None,
                        help="Importable module name (dotted) for the adapter.")
    parser.add_argument(
        "--schema-md", type=Path,
        default=Path(__file__).resolve().parents[1] / "docs" / "SCHEMA_DECISIONS.md",
    )
    parser.add_argument("--edge-floor", type=int, default=DEFAULT_EDGE_FLOOR)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()
    if args.adapter is None:
        parser.error("--adapter is required (or pass --self-test)")
        return 2

    ok, results = verify_adapter(
        args.adapter,
        schema_md=args.schema_md if args.schema_md.exists() else None,
        edge_floor=args.edge_floor,
    )
    for r in results:
        print(r.format())
    if not ok:
        print(f"\n{sum(1 for r in results if not r.ok)} check(s) failed.",
              file=sys.stderr)
        return 1
    print(f"\nAll {len(results)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
