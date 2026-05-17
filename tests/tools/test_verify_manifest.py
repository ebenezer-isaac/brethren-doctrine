"""Tests for tools/verify_manifest.py (RESEED_PLAN Z.1 item 3, H.1).

The Auditor's re-executor must:

* read a manifest file, compute each claim's observed value
  INDEPENDENTLY, then compare to the manifest's recorded expected;
* dispatch on ``check_kind`` to the right handler
  (pytest / script / cypher / file_sha / grep);
* tolerate absolute and ratio tolerances on numeric expectations;
* exit non-zero when ANY claim diverges;
* write a verification JSON with the auditor's observed values.

Tests use only in-process / temp-file claims; no real Neo4j needed.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from tools import verify_manifest as vm


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_self_test_exits_zero() -> None:
    assert vm.main(["--self-test"]) == 0


def test_file_sha_claim_matches(tmp_path: Path) -> None:
    target = tmp_path / "fixture.txt"
    payload = b"some content"
    target.write_bytes(payload)
    manifest = {
        "phase": "Z.1-test",
        "claims": [
            {
                "id": "file_sha_match",
                "description": "matches",
                "check_kind": "file_sha",
                "path": "fixture.txt",
                "expected": _sha256_bytes(payload),
                "actual_field": "sha256",
            },
        ],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = vm.audit_manifest(m_path, tmp_path)
    assert out.all_match
    assert out.claims[0].matches


def test_file_sha_claim_mismatch_fails(tmp_path: Path) -> None:
    target = tmp_path / "fixture.txt"
    target.write_bytes(b"hello")
    manifest = {
        "phase": "Z.1-test",
        "claims": [
            {
                "id": "bad",
                "description": "wrong",
                "check_kind": "file_sha",
                "path": "fixture.txt",
                "expected": "deadbeef" * 8,
                "actual_field": "sha256",
            },
        ],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = vm.audit_manifest(m_path, tmp_path)
    assert not out.all_match
    assert "deadbeef" in out.claims[0].detail


def test_file_sha_missing_file_reports_error(tmp_path: Path) -> None:
    manifest = {
        "phase": "Z.1-test",
        "claims": [
            {
                "id": "absent",
                "description": "missing",
                "check_kind": "file_sha",
                "path": "nope.txt",
                "expected": _sha256_bytes(b"x"),
                "actual_field": "sha256",
            },
        ],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = vm.audit_manifest(m_path, tmp_path)
    assert not out.all_match


def test_grep_claim_match_count(tmp_path: Path) -> None:
    target = tmp_path / "doc.md"
    target.write_text("apple\nbanana\napple pie\n", encoding="utf-8")
    manifest = {
        "phase": "Z.1-test",
        "claims": [
            {
                "id": "grep_apples",
                "description": "counts apples",
                "check_kind": "grep",
                "path": "doc.md",
                "pattern": r"apple",
                "expected": 2,
                "actual_field": "match_count",
            },
        ],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = vm.audit_manifest(m_path, tmp_path)
    assert out.all_match


def test_script_claim_captures_exit_code(tmp_path: Path) -> None:
    script = tmp_path / "ok.py"
    script.write_text("import sys; sys.exit(0)\n", encoding="utf-8")
    manifest = {
        "phase": "Z.1-test",
        "claims": [
            {
                "id": "ok_script",
                "description": "script exits 0",
                "check_kind": "script",
                "argv": ["ok.py"],
                "expected": 0,
                "actual_field": "exit_code",
            },
        ],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = vm.audit_manifest(m_path, tmp_path)
    assert out.all_match


def test_script_claim_detects_nonzero_exit(tmp_path: Path) -> None:
    script = tmp_path / "bad.py"
    script.write_text("import sys; sys.exit(7)\n", encoding="utf-8")
    manifest = {
        "phase": "Z.1-test",
        "claims": [
            {
                "id": "bad_script",
                "description": "should be 0 but isn't",
                "check_kind": "script",
                "argv": ["bad.py"],
                "expected": 0,
                "actual_field": "exit_code",
            },
        ],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = vm.audit_manifest(m_path, tmp_path)
    assert not out.all_match


def test_tolerance_absolute(tmp_path: Path) -> None:
    assert vm._compare(100, 102, {"mode": "absolute", "amount": 3}) is True
    assert vm._compare(100, 102, {"mode": "absolute", "amount": 1}) is False


def test_tolerance_ratio(tmp_path: Path) -> None:
    assert vm._compare(95, 100, {"mode": "ratio", "amount": 0.06}) is True
    assert vm._compare(80, 100, {"mode": "ratio", "amount": 0.05}) is False


def test_tolerance_handles_zero_expected() -> None:
    assert vm._compare(0, 0, {"mode": "ratio", "amount": 0.1}) is True
    assert vm._compare(1, 0, {"mode": "ratio", "amount": 0.1}) is False


def test_compare_equality_when_no_tolerance() -> None:
    assert vm._compare(5, 5, None) is True
    assert vm._compare(5, 6, None) is False
    assert vm._compare("a", "a", None) is True
    assert vm._compare("a", "b", None) is False


def test_unknown_check_kind_fails_gracefully(tmp_path: Path) -> None:
    manifest = {
        "phase": "Z.1-test",
        "claims": [
            {
                "id": "weird",
                "description": "unknown kind",
                "check_kind": "telepathy",
                "expected": 42,
            },
        ],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = vm.audit_manifest(m_path, tmp_path)
    assert not out.all_match


def test_audit_writes_verification_json(tmp_path: Path) -> None:
    target = tmp_path / "f.txt"
    target.write_bytes(b"abc")
    manifest = {
        "phase": "Z.1-test",
        "claims": [
            {
                "id": "one",
                "description": "sha check",
                "check_kind": "file_sha",
                "path": "f.txt",
                "expected": _sha256_bytes(b"abc"),
                "actual_field": "sha256",
            },
        ],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest), encoding="utf-8")
    out_path = tmp_path / "verification.json"
    rc = vm.main([
        "--manifest", str(m_path),
        "--repo", str(tmp_path),
        "--out", str(out_path),
    ])
    assert rc == 0
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["phase"] == "Z.1-test"
    assert data["all_match"] is True
    assert "manifest_sha256" in data and len(data["manifest_sha256"]) == 64


def test_audit_writes_verification_json_on_mismatch(tmp_path: Path) -> None:
    target = tmp_path / "f.txt"
    target.write_bytes(b"abc")
    manifest = {
        "phase": "Z.1-test",
        "claims": [
            {
                "id": "one",
                "description": "sha check",
                "check_kind": "file_sha",
                "path": "f.txt",
                "expected": "0" * 64,
                "actual_field": "sha256",
            },
        ],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest), encoding="utf-8")
    out_path = tmp_path / "verification.json"
    rc = vm.main([
        "--manifest", str(m_path),
        "--repo", str(tmp_path),
        "--out", str(out_path),
    ])
    assert rc == 1
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["all_match"] is False


def test_cypher_claim_uses_injected_driver(tmp_path: Path) -> None:
    class FakeRecord:
        def __init__(self, data: dict[str, Any]):
            self._data = data
        def keys(self) -> list[str]:
            return list(self._data.keys())
        def __getitem__(self, k: str) -> Any:
            return self._data[k]

    class FakeSession:
        def run(self, q: str) -> list[FakeRecord]:
            return [FakeRecord({"n": 42})]
        def __enter__(self) -> "FakeSession":
            return self
        def __exit__(self, *a: Any) -> None:
            pass

    class FakeDriver:
        def session(self) -> FakeSession:
            return FakeSession()
        def close(self) -> None:
            pass

    res = vm.run_cypher_claim(
        "MATCH (n) RETURN count(n) AS n", "lexical",
        driver_factory=lambda: FakeDriver(),
    )
    assert res["value"] == 42


def test_evaluate_claim_dispatches_correctly(tmp_path: Path) -> None:
    target = tmp_path / "f.txt"
    target.write_bytes(b"hi")
    claim = {
        "id": "x",
        "description": "x",
        "check_kind": "file_sha",
        "path": "f.txt",
        "expected": _sha256_bytes(b"hi"),
        "actual_field": "sha256",
    }
    res = vm.evaluate_claim(claim, tmp_path)
    assert res.matches


def test_main_requires_manifest_or_self_test() -> None:
    with pytest.raises(SystemExit):
        vm.main([])
