"""Tests for tools/predicates.py (RESEED_PLAN Z.1 item 2).

The predicates loader is the single source of truth for non-empty-value
Cypher predicates per primitive type. These tests enforce the contract
declared in the loader's module docstring without reading the loader's
function bodies.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools import predicates as pred


REPO = Path(__file__).resolve().parents[2]
PRED_FILE = REPO / "tools" / "predicates_by_type.cypher"


def test_pred_file_exists() -> None:
    assert PRED_FILE.exists(), "predicates_by_type.cypher must ship in tools/"


def test_required_types_declared() -> None:
    preds = pred.load_predicates()
    required = {"string", "int", "float", "bool", "list"}
    missing = required - set(preds)
    assert not missing, f"missing required types: {sorted(missing)}"


def test_available_types_sorted() -> None:
    types = pred.available_types()
    assert types == tuple(sorted(types))
    assert "string" in types and "list" in types


def test_predicate_placeholder_appears_in_expression() -> None:
    preds = pred.load_predicates()
    for t, p in preds.items():
        assert p.placeholder in p.expression, (
            f"placeholder {p.placeholder!r} not referenced in expression "
            f"for type {t!r}: {p.expression!r}"
        )


def test_substitute_replaces_with_caller_expression() -> None:
    out = pred.substitute("WHERE $pred_string(n.gloss)")
    assert "$pred_" not in out
    assert "n.gloss" in out


def test_substitute_handles_multiple_calls() -> None:
    q = (
        "WHERE $pred_string(n.gloss) "
        "AND $pred_list(n.tags) "
        "AND $pred_int(n.position)"
    )
    out = pred.substitute(q)
    assert "$pred_" not in out
    for needle in ("n.gloss", "n.tags", "n.position"):
        assert needle in out, f"{needle!r} missing from substituted output"


def test_substitute_rejects_unknown_type() -> None:
    with pytest.raises(KeyError):
        pred.substitute("$pred_blob(n.x)")


def test_substitute_idempotent_when_no_tokens() -> None:
    q = "MATCH (n:Lemma) RETURN count(n)"
    assert pred.substitute(q) == q


def test_load_predicates_rejects_duplicate_declaration(tmp_path: Path) -> None:
    bad = tmp_path / "bad.cypher"
    bad.write_text(
        "$pred_string(x) := x IS NOT NULL\n"
        "$pred_string(y) := y IS NOT NULL\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        pred.load_predicates(bad)


def test_load_predicates_rejects_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.cypher"
    empty.write_text("// only comments\n", encoding="utf-8")
    with pytest.raises(ValueError):
        pred.load_predicates(empty)


def test_string_predicate_rejects_empty_string_semantically() -> None:
    preds = pred.load_predicates()
    expr = preds["string"].expression
    assert "trim" in expr.lower() or '<> ""' in expr or "<>\"\"" in expr, (
        f"string predicate must reject empty strings: {expr!r}"
    )


def test_float_predicate_rejects_nan() -> None:
    preds = pred.load_predicates()
    expr = preds["float"].expression
    nospace = expr.replace(" ", "")
    assert ("x<>x" in nospace or "isNaN" in expr or "NaN" in expr), (
        f"float predicate must reject NaN: {expr!r}"
    )


def test_list_predicate_requires_size_floor() -> None:
    preds = pred.load_predicates()
    expr = preds["list"].expression
    assert "size(" in expr or "length(" in expr, (
        f"list predicate must check non-zero length: {expr!r}"
    )


def test_substitute_handles_dot_path_argument() -> None:
    out = pred.substitute("$pred_string(n.payload.gloss)")
    assert "n.payload.gloss" in out


def test_main_self_test_exits_zero() -> None:
    assert pred.main(["--self-test"]) == 0


def test_main_list_prints_types(capsys: pytest.CaptureFixture[str]) -> None:
    rc = pred.main(["--list"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "string" in captured.out
    assert "list" in captured.out


def test_main_substitute_emits_clean_cypher(capsys: pytest.CaptureFixture[str]) -> None:
    rc = pred.main(["--substitute", "WHERE $pred_string(n.x)"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "$pred_" not in captured.out
    assert "n.x" in captured.out


def test_predicate_substitution_no_placeholder_leak() -> None:
    """Substituted output must not contain the placeholder identifier as
    a free variable when the caller passed a different argument."""
    preds = pred.load_predicates()
    out = pred.substitute("$pred_string(n.gloss)", preds)
    for p in preds.values():
        bare = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(p.placeholder)}(?![A-Za-z0-9_])")
        assert not bare.search(out.replace("n.gloss", "")), (
            f"placeholder {p.placeholder!r} leaked into output: {out!r}"
        )
