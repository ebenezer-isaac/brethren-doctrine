"""Tests for tools.verify_questions (v3.0 schema integrity)."""

from __future__ import annotations

import pytest

from tools.verify_questions import (
    HISTORICAL_CONSENSUS_ENUM,
    audit_question,
    schema_integrity_check,
)


def test_schema_integrity_passes_clean_question() -> None:
    questions = [
        {
            "id": "doc-x",
            "statement": "x",
            "historical_consensus": "unanimous_lineages",
        }
    ]
    assert schema_integrity_check(questions) == []


def test_schema_integrity_flags_tier_field() -> None:
    questions = [
        {
            "id": "doc-x",
            "statement": "x",
            "tier": "primary",
            "historical_consensus": "unanimous_lineages",
        }
    ]
    errors = schema_integrity_check(questions)
    assert len(errors) == 1
    assert "STALE_TIER_FIELD" in errors[0]
    assert "doc-x" in errors[0]


def test_schema_integrity_flags_bad_historical_consensus() -> None:
    questions = [
        {
            "id": "doc-x",
            "statement": "x",
            "historical_consensus": "made-up-enum",
        }
    ]
    errors = schema_integrity_check(questions)
    assert len(errors) == 1
    assert "BAD_HISTORICAL_CONSENSUS" in errors[0]


def test_schema_integrity_passes_when_no_historical_consensus() -> None:
    questions = [{"id": "doc-x", "statement": "x"}]
    assert schema_integrity_check(questions) == []


@pytest.mark.parametrize("value", sorted(HISTORICAL_CONSENSUS_ENUM))
def test_schema_integrity_each_enum_value_ok(value: str) -> None:
    questions = [{"id": "doc-x", "statement": "x", "historical_consensus": value}]
    assert schema_integrity_check(questions) == []


def test_audit_question_clean() -> None:
    q = {"statement": "There is one God eternally existing in three persons."}
    assert audit_question(q) == []


def test_audit_question_flags_verdict_word() -> None:
    q = {"statement": "Modalism is heresy."}
    flags = audit_question(q)
    assert any(name == "VERDICT_PRELOADED" for name, _ in flags)


def test_audit_question_flags_named_carrier() -> None:
    q = {"statement": "Mormonism teaches a different gospel."}
    flags = audit_question(q)
    assert any(name == "NAMED_CARRIERS" for name, _ in flags)
