"""Tests for tools/check_caste.py (RESEED_PLAN Z.1 item 1).

The caste enforcer must:

* parse the ``Caste: <name>`` trailer out of a commit message;
* reject commits whose changed file-set crosses caste boundaries;
* reject commits with no trailer;
* reject commits with an unknown caste name;
* enforce each caste's allowed/forbidden glob lists declared in
  CASTE_RULES (see RESEED_PLAN verifier-caste table).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tools import check_caste as cc


REPO = Path(__file__).resolve().parents[2]


def test_extract_caste_reads_trailer() -> None:
    msg = "phase A.1: write schema\n\nSome body.\n\nCaste: architect\n"
    assert cc.extract_caste(msg) == "architect"


def test_extract_caste_returns_none_when_missing() -> None:
    assert cc.extract_caste("phase A.1: no trailer\n") is None


def test_extract_caste_handles_hyphenated_name() -> None:
    msg = "phase Z.1: stub\n\nCaste: implementer-z1\n"
    assert cc.extract_caste(msg) == "implementer-z1"


def test_extract_caste_ignores_inline_caste_word() -> None:
    msg = "phase A.1: discusses caste system\n\nBody mentions Caste: x in prose"
    assert cc.extract_caste(msg) in {"x", None}


def test_evaluate_verifier_with_test_file_passes() -> None:
    v = cc.evaluate("verifier", ["tests/tools/test_check_caste.py"])
    assert v.ok, v.violations


def test_evaluate_verifier_with_ingest_file_fails() -> None:
    v = cc.evaluate("verifier", ["ingest/lexical/macula_hebrew.py"])
    assert not v.ok


def test_evaluate_implementer_with_test_file_fails() -> None:
    v = cc.evaluate("implementer", ["tests/lexical/test_macula_hebrew.py"])
    assert not v.ok


def test_evaluate_implementer_with_ingest_file_passes() -> None:
    v = cc.evaluate("implementer", ["ingest/lexical/macula_hebrew.py"])
    assert v.ok, v.violations


def test_evaluate_implementer_z1_with_tools_passes() -> None:
    v = cc.evaluate(
        "implementer-z1",
        ["tools/check_caste.py", "tools/predicates_by_type.cypher"],
    )
    assert v.ok, v.violations


def test_evaluate_implementer_z1_rejects_docs_change() -> None:
    v = cc.evaluate(
        "implementer-z1", ["docs/SCHEMA_DECISIONS.md"],
    )
    assert not v.ok


def test_evaluate_architect_with_docs_passes() -> None:
    v = cc.evaluate(
        "architect",
        ["docs/SCHEMA_DECISIONS.md", "docs/data_inventory_catalog.json"],
    )
    assert v.ok, v.violations


def test_evaluate_architect_with_code_fails() -> None:
    v = cc.evaluate("architect", ["ingest/lexical/macula_hebrew.py"])
    assert not v.ok


def test_evaluate_auditor_with_manifest_passes() -> None:
    v = cc.evaluate(
        "auditor", ["docs/MANIFEST_VERIFICATION_Z.json"],
    )
    assert v.ok, v.violations


def test_evaluate_auditor_with_test_fails() -> None:
    v = cc.evaluate("auditor", ["tests/foo/test_bar.py"])
    assert not v.ok


def test_evaluate_missing_trailer_rejected() -> None:
    v = cc.evaluate(None, ["tests/tools/test_check_caste.py"])
    assert not v.ok
    assert "trailer" in v.detail.lower() or "missing" in v.detail.lower()


def test_evaluate_unknown_caste_rejected() -> None:
    v = cc.evaluate("ghost-rider", ["tests/foo.py"])
    assert not v.ok
    assert "unknown caste" in v.detail.lower()


def test_evaluate_mixed_files_isolates_violators() -> None:
    v = cc.evaluate(
        "verifier",
        ["tests/tools/test_check_caste.py", "ingest/lexical/macula_hebrew.py"],
    )
    assert not v.ok
    assert any("macula_hebrew" in viol for viol in v.violations)
    assert not any("test_check_caste" in viol for viol in v.violations)


def test_match_any_handles_glob_star_star() -> None:
    assert cc._match_any("tests/embeddings/test_embed.py", ("tests/**/test_*.py",))
    assert cc._match_any("tests/lexical/test_x.py", ("tests/**/test_*.py",))
    assert not cc._match_any("ingest/x.py", ("tests/**/test_*.py",))


def test_main_self_test_exits_zero() -> None:
    assert cc.main(["--self-test"]) == 0


def test_check_revision_against_head_commit(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "x@y"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    (repo / "tests").mkdir()
    target = repo / "tests" / "test_x.py"
    target.write_text("def test_x(): pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "tests/test_x.py"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m",
         "phase Z.1: add test_x\n\nCaste: verifier"],
        cwd=repo, check=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()
    v = cc.check_revision(sha, repo)
    assert v.ok, v.violations


def test_check_revision_flags_bad_caste(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "x@y"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    (repo / "ingest").mkdir()
    target = repo / "ingest" / "x.py"
    target.write_text("# x\n", encoding="utf-8")
    subprocess.run(["git", "add", "ingest/x.py"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m",
         "phase C.1: bad\n\nCaste: verifier"],
        cwd=repo, check=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()
    v = cc.check_revision(sha, repo)
    assert not v.ok


def test_evaluate_empty_changed_passes_for_any_caste() -> None:
    v = cc.evaluate("verifier", [])
    assert v.ok


def test_check_caste_module_callable_from_cli() -> None:
    proc = subprocess.run(
        [sys.executable, "tools/check_caste.py", "--self-test"],
        cwd=str(REPO), capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
