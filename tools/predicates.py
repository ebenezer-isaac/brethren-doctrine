"""Load and substitute Cypher predicates declared in
``tools/predicates_by_type.cypher``.

The predicates file is the single source of truth for the
"non-empty value" predicate per primitive type. Adapter verifier scripts
authored in Phase C reference these predicates rather than inlining
``IS NOT NULL`` checks, so that adding a new type (e.g. ``vector``) is a
one-line change in one file.

Public surface:

* :func:`load_predicates` parses the cypher file into a mapping
  ``{type_name: (placeholder, expression)}``.
* :func:`substitute` rewrites a query string by replacing every
  ``$pred_<type>(<expr>)`` token with the parsed expression, with
  ``<placeholder>`` textually replaced by ``<expr>``.
* :func:`available_types` returns the sorted tuple of declared types.

The substitution is intentionally syntactic, not semantic: callers pass
a Cypher expression (e.g. ``n.gloss``) and receive a Cypher expression
back. The file is never executed as Cypher in this module; callers are
responsible for shipping the substituted query to ``cypher-shell`` or
the Neo4j driver.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PRED_FILE = Path(__file__).resolve().parent / "predicates_by_type.cypher"

_DECL_RE = re.compile(
    r"^\$pred_(?P<type>[a-z]+)\(\s*(?P<placeholder>[A-Za-z_][A-Za-z0-9_]*)\s*\)"
    r"\s*:=\s*(?P<expr>.+?)\s*$",
    re.MULTILINE,
)

_CALL_RE = re.compile(
    r"\$pred_(?P<type>[a-z]+)\((?P<arg>[^()]*(?:\([^()]*\)[^()]*)*)\)"
)


@dataclass(frozen=True)
class Predicate:
    type_name: str
    placeholder: str
    expression: str


def load_predicates(path: Path | None = None) -> dict[str, Predicate]:
    p = path if path is not None else PRED_FILE
    text = p.read_text(encoding="utf-8")
    preds: dict[str, Predicate] = {}
    for m in _DECL_RE.finditer(text):
        t = m.group("type")
        if t in preds:
            raise ValueError(
                f"duplicate predicate declaration for type {t!r} in {p}"
            )
        preds[t] = Predicate(
            type_name=t,
            placeholder=m.group("placeholder"),
            expression=m.group("expr").strip(),
        )
    if not preds:
        raise ValueError(f"no predicates parsed from {p}")
    return preds


def substitute(query: str, predicates: dict[str, Predicate] | None = None) -> str:
    preds = predicates if predicates is not None else load_predicates()

    def _sub(match: re.Match[str]) -> str:
        t = match.group("type")
        arg = match.group("arg").strip()
        pred = preds.get(t)
        if pred is None:
            raise KeyError(
                f"unknown predicate type {t!r}; declared types: "
                f"{sorted(preds)}"
            )
        ph_re = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(pred.placeholder)}(?![A-Za-z0-9_])")
        substituted = ph_re.sub(arg, pred.expression)
        return f"({substituted})"

    out = _CALL_RE.sub(_sub, query)
    if "$pred_" in out:
        leftover = re.findall(r"\$pred_[a-z]+", out)
        raise ValueError(
            f"unresolved predicate token(s) remain after substitution: {leftover}"
        )
    return out


def available_types(predicates: dict[str, Predicate] | None = None) -> tuple[str, ...]:
    preds = predicates if predicates is not None else load_predicates()
    return tuple(sorted(preds))


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true",
                        help="Print declared predicate types and exit.")
    parser.add_argument("--substitute", type=str, default=None,
                        help="Cypher query with $pred_<type>(expr) tokens.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        preds = load_predicates()
        required = {"string", "int", "float", "bool", "list"}
        missing = required - set(preds)
        if missing:
            print(f"self-test FAIL: missing predicate types {sorted(missing)}",
                  file=sys.stderr)
            return 1
        out = substitute("WHERE $pred_string(n.gloss) AND $pred_list(n.tags)", preds)
        if "$pred_" in out or "n.gloss" not in out or "n.tags" not in out:
            print(f"self-test FAIL: bad substitution output: {out!r}",
                  file=sys.stderr)
            return 1
        print("self-test OK")
        return 0
    if args.list:
        for t in available_types():
            print(t)
        return 0
    if args.substitute is not None:
        print(substitute(args.substitute))
        return 0
    parser.error("pass --list, --substitute, or --self-test")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
