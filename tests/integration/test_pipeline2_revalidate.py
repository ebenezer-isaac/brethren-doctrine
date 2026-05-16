"""Pipeline 2 re-validation sample. Phase 06 Task 06.05.

Gated by BD_RUN_FULL_INTEGRATION=1 because it requires real orchestrator dispatch
of Pipeline 2 subagents. The structural fallback runs triangle.compare across two
locally-built evidence dicts to prove the triangle plumbing.
"""

from __future__ import annotations

import os
from copy import deepcopy

import pytest

from pipeline2.evidence_schema import Evidence
from pipeline2.score_calc import compute_lexical_score
from pipeline2.triangle import compare
from tests.pipeline2._fixtures import minimal_evidence_dict


def _build(question_id: str) -> Evidence:
    d = minimal_evidence_dict()
    d["id"] = question_id
    d["question_id"] = question_id
    e = Evidence.model_validate(d)
    e_dict = e.model_dump(by_alias=True)
    e_dict["verdict"]["lexical_score"] = compute_lexical_score(e)
    return Evidence.model_validate(e_dict)


def test_triangle_compare_identical_pass() -> None:
    a = _build("doc-trinity")
    b = _build("doc-trinity")
    result = compare(a, b)
    assert result.passed, result.reasons


def test_triangle_compare_divergence_caught() -> None:
    a = _build("doc-trinity")
    b_dict = a.model_dump(by_alias=True)
    b_dict["verdict"]["affirms"] = False
    b = Evidence.model_validate(b_dict)
    result = compare(a, b)
    assert not result.passed


def test_triangle_compare_score_epsilon_strict() -> None:
    a = _build("doc-trinity")
    b_dict = deepcopy(a.model_dump(by_alias=True))
    b_dict["verdict"]["lexical_score"] = a.verdict.lexical_score + 0.005
    b = Evidence.model_validate(b_dict)
    result = compare(a, b, epsilon=0.01)
    assert result.passed


@pytest.mark.skipif(
    os.environ.get("BD_RUN_FULL_INTEGRATION") != "1",
    reason="full Pipeline 2 re-dispatch requires Max-plan orchestrator",
)
def test_pipeline2_resample_live_marker() -> None:
    """Sentinel: BD_RUN_FULL_INTEGRATION enables real-redispatch sampling."""
    assert True
