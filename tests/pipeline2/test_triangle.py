"""Tests for pipeline2.triangle."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from pipeline2.dispatcher import Pipeline2Dispatcher
from pipeline2.triangle import compare, stateful_dispatch, triangle_test
from tests.pipeline2._fixtures import minimal_evidence_dict

LEAN_PROMPT = Path("docs/phase_prompts/pipeline2_verdict.md")


def _bundle_for(question_id: str, _settings: Any = None) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "question_statement": "stmt",
        "question_metadata": {"category": "Theology Proper"},
        "lexical_context_bundle": {
            "anchor_lemmas": [],
            "anchor_verses": [],
            "cross_refs": [],
            "semantic_domain_neighbors": [],
            "variant_units": [],
            "syntactic_context": [],
        },
        "schema_version": "3.0",
    }


def _dispatcher() -> Pipeline2Dispatcher:
    settings = MagicMock()
    return Pipeline2Dispatcher(settings, LEAN_PROMPT)


def _run(payload_a: dict[str, Any], payload_b: dict[str, Any]):
    d = _dispatcher()
    fn = stateful_dispatch([payload_a, payload_b])
    with patch(
        "pipeline2.dispatcher.build_lexical_context_bundle",
        side_effect=_bundle_for,
    ):
        return triangle_test("doc-trinity", d, fn)


def test_two_identical_outputs_pass() -> None:
    a = minimal_evidence_dict()
    b = minimal_evidence_dict()
    result = _run(a, b)
    assert result.passed, result.reasons


def test_different_prose_same_structured_fields_pass() -> None:
    a = minimal_evidence_dict()
    b = minimal_evidence_dict()
    b["verdict"]["rationale"] = "Completely different prose; structured fields match."
    b["lay_summary"] = a["lay_summary"][:-10] + " ending tweak applied here."
    result = _run(a, b)
    assert result.passed, result.reasons


def test_different_affirms_fail() -> None:
    a = minimal_evidence_dict()
    b = minimal_evidence_dict()
    b["verdict"]["affirms"] = False
    result = _run(a, b)
    assert not result.passed
    assert any("affirms mismatch" in r for r in result.reasons)


def test_score_delta_exceeds_epsilon_fail() -> None:
    a = minimal_evidence_dict()
    b = minimal_evidence_dict()
    b["lexical_evidence"]["anchor_lemmas"] = []
    b["lexical_evidence"]["concordance_traversed"] = []
    result = _run(a, b)
    assert not result.passed
    reasons = " ".join(result.reasons)
    assert "anchor_lemmas" in reasons or "lexical_score delta" in reasons


def test_anchor_lemmas_set_mismatch_fail() -> None:
    a = minimal_evidence_dict()
    b = deepcopy(a)
    b["lexical_evidence"]["anchor_lemmas"][0]["strong"] = "H9999"
    result = _run(a, b)
    assert not result.passed
    assert any("anchor_lemmas set mismatch" in r for r in result.reasons)


def test_anchor_lemmas_permuted_same_set_pass() -> None:
    a = minimal_evidence_dict()
    b = deepcopy(a)
    b["lexical_evidence"]["anchor_lemmas"] = list(reversed(b["lexical_evidence"]["anchor_lemmas"]))
    result = _run(a, b)
    assert result.passed, result.reasons


def test_concordance_permuted_same_set_pass() -> None:
    a = minimal_evidence_dict()
    b = deepcopy(a)
    b["lexical_evidence"]["concordance_traversed"] = list(
        reversed(b["lexical_evidence"]["concordance_traversed"])
    )
    result = _run(a, b)
    assert result.passed, result.reasons


def test_complicating_texts_ref_set_mismatch_fail() -> None:
    a = minimal_evidence_dict()
    b = deepcopy(a)
    b["lexical_evidence"]["complicating_texts"][0]["ref"] = "Luke.22.42"
    result = _run(a, b)
    assert not result.passed
    assert any("complicating_texts ref-set mismatch" in r for r in result.reasons)


def test_compare_question_id_mismatch_caught() -> None:
    from pipeline2.evidence_schema import Evidence

    a_payload = minimal_evidence_dict()
    b_payload = minimal_evidence_dict()
    b_payload["id"] = "doc-other"
    b_payload["question_id"] = "doc-other"
    a = Evidence.model_validate(a_payload)
    b = Evidence.model_validate(b_payload)
    from pipeline2.score_calc import compute_lexical_score

    a_dict = a.model_dump(by_alias=True)
    a_dict["verdict"]["lexical_score"] = compute_lexical_score(a)
    b_dict = b.model_dump(by_alias=True)
    b_dict["verdict"]["lexical_score"] = compute_lexical_score(b)
    a = Evidence.model_validate(a_dict)
    b = Evidence.model_validate(b_dict)
    result = compare(a, b)
    assert not result.passed
    assert any("question_id mismatch" in r for r in result.reasons)
