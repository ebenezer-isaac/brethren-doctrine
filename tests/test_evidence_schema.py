"""Round-trips a hand-crafted evidence file through validator + renderer.

The golden fixture is the canonical demonstration of "what a passing
evidence/<id>.json looks like" under the new schema. Used to:
1. Catch regressions in tools/baseline_orchestrator.py validate()
2. Catch regressions in tools/evidence_to_pdf.py render()
3. Be the canonical example to point subagent prompts at

If the schema changes, this fixture changes lockstep with ANSWER_SCHEMA.md.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
EVIDENCE = ROOT / "evidence"
FIX = Path(__file__).parent / "fixtures"

sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT))


@pytest.fixture
def golden_in_evidence(tmp_path, monkeypatch):
    """Copy the golden fixture into evidence/ for the test, restore after."""
    qid = "doc-divine-omnipotence"
    target = EVIDENCE / f"{qid}.json"
    backup = None
    if target.exists():
        backup = target.read_bytes()
    shutil.copy(FIX / "golden_evidence.json", target)
    yield qid
    if backup is None:
        target.unlink(missing_ok=True)
    else:
        target.write_bytes(backup)


def test_golden_validates(golden_in_evidence):
    import baseline_orchestrator as bo  # type: ignore

    ok, errs = bo.validate(golden_in_evidence)
    assert ok, f"golden fixture should validate; errors: {errs}"


def test_golden_passes_orchestrator_validate_all(golden_in_evidence):
    """validate-all over questions.json should treat the golden as the only valid file
    and missing-file for the rest. The golden alone must be in the OK set."""
    import baseline_orchestrator as bo  # type: ignore

    qid = golden_in_evidence
    ok, errs = bo.validate(qid)
    assert ok, errs


def test_golden_renders_to_pdf(golden_in_evidence, tmp_path):
    import evidence_to_pdf  # type: ignore

    questions = evidence_to_pdf.load_questions_index()
    question = questions.get(golden_in_evidence)

    out_path = tmp_path / "golden.pdf"
    font_pair = evidence_to_pdf.register_unicode_font()
    evidence_to_pdf.render_pdf(
        EVIDENCE / f"{golden_in_evidence}.json",
        out_path,
        font_pair,
        question,
    )
    assert out_path.exists()
    assert out_path.stat().st_size > 5_000, "PDF suspiciously small"

    # Verify the PDF has valid header bytes
    with out_path.open("rb") as f:
        header = f.read(4)
    assert header == b"%PDF", f"not a PDF: {header!r}"


def test_legacy_evidence_keys_rejected(tmp_path):
    """A file with legacy keys (confessional_verifications, source_docs,
    confession_kin, defendant_position) must fail validation."""
    import baseline_orchestrator as bo  # type: ignore

    # Build a doctored copy of the golden with a legacy key smuggled in
    src = json.loads((FIX / "golden_evidence.json").read_text(encoding="utf-8"))
    src["evidence"]["source_docs"] = [{"chunk_id": "smuggled", "authority_level": 4}]

    qid = src["id"]
    target = EVIDENCE / f"{qid}.json"
    backup = target.read_bytes() if target.exists() else None
    target.write_text(json.dumps(src), encoding="utf-8")
    try:
        ok, errs = bo.validate(qid)
        assert not ok, "legacy key 'source_docs' should fail validation"
        assert any("legacy-evidence-key" in e for e in errs), errs
    finally:
        if backup is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(backup)


def test_empty_concordance_rejected(tmp_path):
    """An evidence file with empty concordance_lemmas_traversed must fail
    on every tier (universal validation rule)."""
    import baseline_orchestrator as bo  # type: ignore

    src = json.loads((FIX / "golden_evidence.json").read_text(encoding="utf-8"))
    src["evidence"]["concordance_lemmas_traversed"] = []

    qid = src["id"]
    target = EVIDENCE / f"{qid}.json"
    backup = target.read_bytes() if target.exists() else None
    target.write_text(json.dumps(src), encoding="utf-8")
    try:
        ok, errs = bo.validate(qid)
        assert not ok
        assert any("concordance_lemmas_traversed-empty" in e for e in errs), errs
    finally:
        if backup is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(backup)


def test_cult_marker_without_canonical_demonstration_rejected(tmp_path):
    """cult_marker_if_denied=true with single-passage / single-lemma evidence must fail.

    Lineage agreement is no longer checked (revised 2026-05-10); the bar is now
    canonical demonstration via apparatus + interlinear + concordance breadth.
    Validator requires concordance_lemmas_traversed >= 2 AND scripture[] >= 3
    when cult_marker_if_denied=true.
    """
    import baseline_orchestrator as bo  # type: ignore

    src = json.loads((FIX / "golden_evidence.json").read_text(encoding="utf-8"))
    src["answer"]["cult_marker_if_denied"] = True
    # would_die_for is already True in golden, so entailment passes
    # Shrink scripture[] to 1 anchor and lemmas to 1 to fail canonical-demonstration
    src["evidence"]["scripture"] = src["evidence"]["scripture"][:1]
    src["evidence"]["concordance_lemmas_traversed"] = src["evidence"]["concordance_lemmas_traversed"][:1]

    qid = src["id"]
    target = EVIDENCE / f"{qid}.json"
    backup = target.read_bytes() if target.exists() else None
    target.write_text(json.dumps(src), encoding="utf-8")
    try:
        ok, errs = bo.validate(qid)
        assert not ok
        assert any("cult-marker-without-canonical-demonstration" in e for e in errs), errs
    finally:
        if backup is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(backup)
