"""AST-walk every adapter under ``ingest/lexical/`` and reject impure code.

The lexical adapter contract is: read local source files under
``data/private/``, parse, emit Pydantic records. Nothing else. This
verifier statically rejects:

* Imports of network / dynamic-loader modules:
  ``subprocess``, ``socket``, ``httpx``, ``requests``, ``urllib``,
  ``aiohttp``, ``importlib.import_module``, ``__import__``.
* ``open()`` calls whose path argument is not a string literal starting
  with ``data/private/`` (or a ``pathlib.Path("data/private/...")``
  call). Dynamic paths must be rejected because we cannot statically
  prove they stay inside the sandbox.
* Any non-docstring string constant (including the arguments of
  ``Path(...)`` / ``PurePath(...)`` constructions and
  ``os.path.join(...)`` calls) whose normalised path segments contain a
  segment equal to ``tests`` (case-insensitive), or that references
  ``tests/lexical/fixtures``. Wave 3 adapters were caught reading the
  verifier test fixtures from production code (one evaded the earlier
  ``open()`` guard via ``Path(var).open()`` plus a tests-path literal);
  this rule kills that class regardless of the open() receiver form.
  Module / class / function docstrings are exempt because they document
  the verifier contract in prose, not executable paths. The documented
  adapter data roots (``data/private/``, the per-user text-fabric cache
  ``C:/Users/Ebenezer/text-fabric-data``, and ``tmp/poc/`` for
  procurement) carry no ``tests`` segment and stay clean.

Usage:
    python tools/check_adapter_purity.py --all
    python tools/check_adapter_purity.py --file path/to/adapter.py
    python tools/check_adapter_purity.py --self-test
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


FORBIDDEN_TOP_LEVEL_MODULES: frozenset[str] = frozenset(
    {"subprocess", "socket", "httpx", "requests", "urllib", "aiohttp"}
)
# ``import foo.bar`` is rejected if ``foo`` is in the set above; also we
# special-case explicit imports of ``importlib.import_module``.
FORBIDDEN_FROM_IMPORTS: frozenset[tuple[str, str]] = frozenset(
    {("importlib", "import_module")}
)
ALLOWED_PATH_PREFIXES: tuple[str, ...] = (
    "data/private/",
    "data\\private\\",
)


@dataclass(frozen=True)
class Violation:
    file: Path
    line: int
    rule: str
    detail: str

    def format(self) -> str:
        return f"{self.file}:{self.line}: {self.rule}: {self.detail}"


def _module_root(name: str) -> str:
    return name.split(".", 1)[0]


def _has_tests_path_segment(value: str) -> bool:
    """Return True if ``value`` contains a path segment equal to ``tests``
    (case-insensitive) or references the verifier fixtures directory.

    Both POSIX and Windows separators are normalised so ``tests\\x`` and
    ``a/tests/b`` are caught alongside the bare ``tests`` segment.
    """
    normalised = value.replace("\\", "/")
    lowered = normalised.lower()
    if "tests/lexical/fixtures" in lowered:
        return True
    return any(seg.strip().lower() == "tests" for seg in normalised.split("/"))


def _collect_docstring_constants(tree: ast.AST) -> frozenset[int]:
    """Identity-set of string ``Constant`` nodes that are module / class /
    function docstrings.

    Docstrings document the verifier contract in prose (``peshitta.py``
    names ``tests/lexical/fixtures/peshitta_slice.json`` to explain the
    locked structural shape) and must not be treated as executable
    paths. Only the leading ``Expr`` statement of each scope qualifies.
    """
    ids: set[int] = set()
    for parent in ast.walk(tree):
        if isinstance(
            parent,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            body = getattr(parent, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return frozenset(ids)


def _arg_is_safe_path_literal(node: ast.AST) -> bool:
    """Return True if ``node`` is a literal whose value starts with
    ``data/private/`` or ``data\\private\\``, OR a ``Path("data/private/...")``
    call/construction."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return any(node.value.startswith(p) for p in ALLOWED_PATH_PREFIXES)
    if isinstance(node, ast.JoinedStr):
        # f-strings: must start with a literal "data/private/..." prefix.
        if node.values and isinstance(node.values[0], ast.Constant):
            v = node.values[0].value
            if isinstance(v, str) and any(v.startswith(p) for p in ALLOWED_PATH_PREFIXES):
                return True
        return False
    if isinstance(node, ast.Call):
        # Path("data/private/...") or pathlib.Path("data/private/...")
        callee = node.func
        name = None
        if isinstance(callee, ast.Name):
            name = callee.id
        elif isinstance(callee, ast.Attribute):
            name = callee.attr
        if name in ("Path", "PurePath", "PurePosixPath", "PureWindowsPath"):
            return bool(node.args) and _arg_is_safe_path_literal(node.args[0])
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        # Path("data/private") / "x" form
        return _arg_is_safe_path_literal(node.left)
    return False


class _PurityVisitor(ast.NodeVisitor):
    def __init__(self, file: Path, docstring_ids: frozenset[int]) -> None:
        self.file = file
        self.docstring_ids = docstring_ids
        self.violations: list[Violation] = []

    def visit_Constant(self, node: ast.Constant) -> None:
        if (
            isinstance(node.value, str)
            and id(node) not in self.docstring_ids
            and _has_tests_path_segment(node.value)
        ):
            self.violations.append(Violation(
                self.file, node.lineno,
                "forbidden_tests_path",
                f"string references a 'tests' path segment: {node.value!r}",
            ))
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = _module_root(alias.name)
            if root in FORBIDDEN_TOP_LEVEL_MODULES:
                self.violations.append(Violation(
                    self.file, node.lineno,
                    "forbidden_import",
                    f"import {alias.name}",
                ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        root = _module_root(mod)
        if root in FORBIDDEN_TOP_LEVEL_MODULES:
            self.violations.append(Violation(
                self.file, node.lineno,
                "forbidden_import",
                f"from {mod} import ...",
            ))
        for alias in node.names:
            if (mod, alias.name) in FORBIDDEN_FROM_IMPORTS:
                self.violations.append(Violation(
                    self.file, node.lineno,
                    "forbidden_import",
                    f"from {mod} import {alias.name}",
                ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # __import__(...)
        if isinstance(node.func, ast.Name) and node.func.id == "__import__":
            self.violations.append(Violation(
                self.file, node.lineno,
                "forbidden_call",
                "__import__()",
            ))
        # importlib.import_module(...)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "importlib"
        ):
            self.violations.append(Violation(
                self.file, node.lineno,
                "forbidden_call",
                "importlib.import_module(...)",
            ))
        # open(...) -> first positional arg must be a safe literal path
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            self._check_open_call(node)
        # Path.open / pathlib.Path(...).open / fh.open(...) - if the
        # receiver is a Path literal we already approved, skip; else
        # require static safety.
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "open"
            and isinstance(node.func.value, (ast.Call, ast.Constant, ast.JoinedStr))
        ):
            if not _arg_is_safe_path_literal(node.func.value):
                # only flag if the receiver looks like a path literal
                # we could not prove safe; runtime Path objects are out
                # of scope for static analysis.
                if isinstance(node.func.value, ast.Constant) or isinstance(
                    node.func.value, ast.JoinedStr
                ):
                    self.violations.append(Violation(
                        self.file, node.lineno,
                        "forbidden_open",
                        "open() on non-data/private path literal",
                    ))
        self.generic_visit(node)

    def _check_open_call(self, node: ast.Call) -> None:
        if not node.args:
            # open() with no args is a syntax error at runtime; ignore.
            return
        first = node.args[0]
        if _arg_is_safe_path_literal(first):
            return
        if isinstance(first, ast.Name):
            # Variable -- cannot prove safety statically. Reject.
            self.violations.append(Violation(
                self.file, node.lineno,
                "forbidden_open",
                f"open() with non-literal path variable {first.id!r}",
            ))
            return
        # Other expression types (calls returning paths, attribute
        # accesses): rejected because we cannot prove the path stays
        # inside data/private/.
        self.violations.append(Violation(
            self.file, node.lineno,
            "forbidden_open",
            f"open() with non-literal path expression ({type(first).__name__})",
        ))


def check_file(path: Path) -> list[Violation]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    v = _PurityVisitor(path, _collect_docstring_constants(tree))
    v.visit(tree)
    return v.violations


def check_paths(paths: Iterable[Path]) -> list[Violation]:
    out: list[Violation] = []
    for p in paths:
        out.extend(check_file(p))
    return out


def _adapter_files() -> list[Path]:
    repo = Path(__file__).resolve().parents[1]
    return sorted(
        p for p in (repo / "ingest" / "lexical").glob("*.py")
        if p.name not in {"__init__.py"}
    )


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        good = Path(td) / "good.py"
        good.write_text(
            "from pathlib import Path\n"
            "def run():\n"
            "    with open('data/private/x.tsv') as fh:\n"
            "        return fh.read()\n",
            encoding="utf-8",
        )
        bad = Path(td) / "bad.py"
        bad.write_text(
            "import requests\n"
            "def run(p):\n"
            "    return open(p).read()\n",
            encoding="utf-8",
        )
        # Gaming form that evaded the earlier open() guard: a Path
        # variable receiver plus a tests-fixture string literal.
        gamed = Path(td) / "gamed.py"
        gamed.write_text(
            "from pathlib import Path\n"
            "def run():\n"
            "    p = Path('tests/lexical/fixtures/x_slice.json')\n"
            "    with p.open(encoding='utf-8') as fh:\n"
            "        return fh.read()\n",
            encoding="utf-8",
        )
        # Docstring naming the verifier fixture must NOT be flagged: it
        # is contract prose, not an executable path.
        doc_ok = Path(td) / "doc_ok.py"
        doc_ok.write_text(
            '"""Mirrors tests/lexical/fixtures/peshitta_slice.json shape."""\n'
            "from pathlib import Path\n"
            "def run():\n"
            "    with open('data/private/x.tsv') as fh:\n"
            "        return fh.read()\n",
            encoding="utf-8",
        )
        if check_file(good):
            print(f"self-test FAIL: good adapter flagged: {check_file(good)}",
                  file=sys.stderr)
            return 1
        if check_file(doc_ok):
            print(
                "self-test FAIL: docstring fixture reference flagged: "
                f"{check_file(doc_ok)}",
                file=sys.stderr,
            )
            return 1
        gamed_v = check_file(gamed)
        gamed_rules = {v.rule for v in gamed_v}
        if "forbidden_tests_path" not in gamed_rules:
            print(
                "self-test FAIL: gamed tests-path read not caught: "
                f"{gamed_v}",
                file=sys.stderr,
            )
            return 1
        bad_v = check_file(bad)
        if len(bad_v) < 2:
            print(f"self-test FAIL: bad adapter under-flagged: {bad_v}",
                  file=sys.stderr)
            return 1
        rules = {v.rule for v in bad_v}
        if "forbidden_import" not in rules or "forbidden_open" not in rules:
            print(f"self-test FAIL: missing rule coverage: {rules}",
                  file=sys.stderr)
            return 1
    print("self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true",
                   help="Check every adapter in ingest/lexical/.")
    g.add_argument("--file", type=Path, default=None,
                   help="Check a single file.")
    g.add_argument("--adapter", type=str, default=None,
                   help="Adapter slug -- maps to ingest/lexical/<slug>.py.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    if args.file is not None:
        paths = [args.file]
    elif args.adapter is not None:
        repo = Path(__file__).resolve().parents[1]
        paths = [repo / "ingest" / "lexical" / f"{args.adapter}.py"]
    elif args.all:
        paths = _adapter_files()
    else:
        parser.error("one of --all / --file / --adapter required")
        return 2  # unreachable

    for p in paths:
        if not p.exists():
            print(f"missing adapter file: {p}", file=sys.stderr)
            return 1
    violations = check_paths(paths)
    if not violations:
        print(f"OK: {len(paths)} file(s) clean.")
        return 0
    print(f"FAIL: {len(violations)} purity violation(s)", file=sys.stderr)
    for v in violations:
        print(f"  {v.format()}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
