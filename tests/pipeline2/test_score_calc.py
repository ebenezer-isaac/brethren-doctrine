"""Tests for pipeline2.score_calc."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

import pytest

from pipeline2.evidence_schema import Evidence
from pipeline2.score_calc import compute_lexical_score
from tests.pipeline2._fixtures import minimal_evidence_dict


def _maximal_dict() -> dict[str, Any]:
    d = minimal_evidence_dict()
    d["verdict"]["pan_canonical"] = True
    d["verdict"]["variant_robust"] = True
    d["lexical_evidence"]["anchor_lemmas"] = [
        {
            "strong": f"H{i:04d}",
            "lemma": f"lemma{i}",
            "transliteration": f"t{i}",
            "occurrences_in_canon": 10,
            "in_anchors": True,
        }
        for i in range(1, 9)
    ]
    d["lexical_evidence"]["concordance_traversed"] = [f"H{i:04d}" for i in range(1, 11)]
    d["lexical_evidence"]["cross_refs_invoked"] = [
        {"from": "John.1.1", "to": f"John.1.{i}", "source": "openbible", "votes": 100}
        for i in range(1, 13)
    ]
    d["lexical_evidence"]["complicating_texts"] = [
        {"ref": f"Mark.1.{i}", "addressed": True, "resolution": f"resolved {i}"}
        for i in range(1, 4)
    ]
    return d


def _minimal_score_dict() -> dict[str, Any]:
    d = minimal_evidence_dict()
    d["verdict"]["pan_canonical"] = False
    d["verdict"]["variant_robust"] = False
    d["lexical_evidence"]["anchor_lemmas"] = []
    d["lexical_evidence"]["concordance_traversed"] = []
    d["lexical_evidence"]["cross_refs_invoked"] = []
    d["lexical_evidence"]["complicating_texts"] = []
    return d


def test_upper_bound_is_1_0() -> None:
    e = Evidence.model_validate(_maximal_dict())
    assert compute_lexical_score(e) == 1.0


def test_lower_bound_above_zero() -> None:
    e = Evidence.model_validate(_minimal_score_dict())
    score = compute_lexical_score(e)
    expected = 0.25 * 0.3 + 0.15 * 1.0 + 0.15 * 0.5
    assert score == pytest.approx(round(expected, 6))
    assert score > 0.0


def test_pan_canonical_false_reduces_by_0_175() -> None:
    base = _maximal_dict()
    base["verdict"]["pan_canonical"] = False
    e = Evidence.model_validate(base)
    score = compute_lexical_score(e)
    assert score == pytest.approx(1.0 - 0.25 * 0.7)


def test_anchor_lemma_capped_at_8() -> None:
    d = _maximal_dict()
    d["lexical_evidence"]["anchor_lemmas"] = [
        {
            "strong": f"H{i:04d}",
            "lemma": f"lemma{i}",
            "transliteration": f"t{i}",
            "occurrences_in_canon": 10,
            "in_anchors": True,
        }
        for i in range(1, 20)
    ]
    e = Evidence.model_validate(d)
    assert compute_lexical_score(e) == 1.0


def test_complicating_zero_yields_factor_1() -> None:
    d = _maximal_dict()
    d["lexical_evidence"]["complicating_texts"] = []
    e = Evidence.model_validate(d)
    assert compute_lexical_score(e) == 1.0


def test_complicating_all_addressed_factor_1() -> None:
    d = _maximal_dict()
    d["lexical_evidence"]["complicating_texts"] = [
        {"ref": "Mark.1.1", "addressed": True, "resolution": "r1"},
        {"ref": "Mark.1.2", "addressed": True, "resolution": "r2"},
    ]
    e = Evidence.model_validate(d)
    assert compute_lexical_score(e) == 1.0


def test_complicating_half_addressed_factor_0_5() -> None:
    d = _maximal_dict()
    d["lexical_evidence"]["complicating_texts"] = [
        {"ref": "Mark.1.1", "addressed": True, "resolution": "r1"},
        {"ref": "Mark.1.2", "addressed": False, "resolution": "r2"},
    ]
    e = Evidence.model_validate(d)
    assert compute_lexical_score(e) == pytest.approx(1.0 - 0.15 * 0.5)


def test_cross_ref_count_capped_at_12() -> None:
    d = _maximal_dict()
    d["lexical_evidence"]["cross_refs_invoked"] = [
        {"from": "John.1.1", "to": f"John.1.{i}", "source": "openbible", "votes": 100}
        for i in range(1, 30)
    ]
    e = Evidence.model_validate(d)
    assert compute_lexical_score(e) == 1.0


def test_variant_robust_false_reduces_by_0_075() -> None:
    d = _maximal_dict()
    d["verdict"]["variant_robust"] = False
    e = Evidence.model_validate(d)
    score = compute_lexical_score(e)
    assert score == pytest.approx(1.0 - 0.15 * 0.5)


def test_concordance_capped_at_10() -> None:
    d = _maximal_dict()
    d["lexical_evidence"]["concordance_traversed"] = [f"H{i:04d}" for i in range(1, 25)]
    e = Evidence.model_validate(d)
    assert compute_lexical_score(e) == 1.0


def test_order_invariance_anchor_lemmas() -> None:
    d1 = _maximal_dict()
    d2 = deepcopy(d1)
    d2["lexical_evidence"]["anchor_lemmas"] = list(
        reversed(d2["lexical_evidence"]["anchor_lemmas"])
    )
    e1 = Evidence.model_validate(d1)
    e2 = Evidence.model_validate(d2)
    assert compute_lexical_score(e1) == compute_lexical_score(e2)


def test_order_invariance_cross_refs() -> None:
    d1 = _maximal_dict()
    d2 = deepcopy(d1)
    d2["lexical_evidence"]["cross_refs_invoked"] = list(
        reversed(d2["lexical_evidence"]["cross_refs_invoked"])
    )
    e1 = Evidence.model_validate(d1)
    e2 = Evidence.model_validate(d2)
    assert compute_lexical_score(e1) == compute_lexical_score(e2)


def test_order_invariance_complicating_texts() -> None:
    d = _maximal_dict()
    d["lexical_evidence"]["complicating_texts"] = [
        {"ref": "Mark.1.1", "addressed": True, "resolution": "r1"},
        {"ref": "Mark.1.2", "addressed": False, "resolution": "r2"},
        {"ref": "Mark.1.3", "addressed": True, "resolution": "r3"},
    ]
    d2 = deepcopy(d)
    d2["lexical_evidence"]["complicating_texts"] = list(
        reversed(d2["lexical_evidence"]["complicating_texts"])
    )
    e1 = Evidence.model_validate(d)
    e2 = Evidence.model_validate(d2)
    assert compute_lexical_score(e1) == compute_lexical_score(e2)


def test_order_invariance_concordance() -> None:
    d1 = _maximal_dict()
    d2 = deepcopy(d1)
    d2["lexical_evidence"]["concordance_traversed"] = list(
        reversed(d2["lexical_evidence"]["concordance_traversed"])
    )
    e1 = Evidence.model_validate(d1)
    e2 = Evidence.model_validate(d2)
    assert compute_lexical_score(e1) == compute_lexical_score(e2)


def test_determinism_sha256_stable_across_runs() -> None:
    e = Evidence.model_validate(_maximal_dict())
    digests = set()
    for _ in range(10):
        score = compute_lexical_score(e)
        digests.add(
            hashlib.sha256(json.dumps({"score": score}, sort_keys=True).encode()).hexdigest()
        )
    assert len(digests) == 1


def test_deterministic_repr_identical() -> None:
    e1 = Evidence.model_validate(_maximal_dict())
    e2 = Evidence.model_validate(_maximal_dict())
    assert repr(compute_lexical_score(e1)) == repr(compute_lexical_score(e2))


def test_partial_anchor_lemmas_proportional() -> None:
    d = _maximal_dict()
    d["lexical_evidence"]["anchor_lemmas"] = d["lexical_evidence"]["anchor_lemmas"][:4]
    e = Evidence.model_validate(d)
    score = compute_lexical_score(e)
    assert score == pytest.approx(1.0 - 0.20 * 0.5)


def test_partial_cross_refs_proportional() -> None:
    d = _maximal_dict()
    d["lexical_evidence"]["cross_refs_invoked"] = d["lexical_evidence"]["cross_refs_invoked"][:6]
    e = Evidence.model_validate(d)
    score = compute_lexical_score(e)
    assert score == pytest.approx(1.0 - 0.15 * 0.5)


def test_partial_concordance_proportional() -> None:
    d = _maximal_dict()
    d["lexical_evidence"]["concordance_traversed"] = d["lexical_evidence"]["concordance_traversed"][
        :5
    ]
    e = Evidence.model_validate(d)
    score = compute_lexical_score(e)
    assert score == pytest.approx(1.0 - 0.10 * 0.5)


def test_score_in_unit_range() -> None:
    for d_maker in (_maximal_dict, _minimal_score_dict):
        e = Evidence.model_validate(d_maker())
        score = compute_lexical_score(e)
        assert 0.0 <= score <= 1.0


def test_score_precision_6_decimals() -> None:
    d = _maximal_dict()
    d["lexical_evidence"]["complicating_texts"] = [
        {"ref": f"r{i}", "addressed": (i % 3 == 0), "resolution": f"x{i}"} for i in range(7)
    ]
    e = Evidence.model_validate(d)
    score = compute_lexical_score(e)
    fractional = repr(score).split(".")[-1] if "." in repr(score) else ""
    assert len(fractional) <= 6
