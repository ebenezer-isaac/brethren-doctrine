"""Tests for retrieval.envelope."""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from retrieval.envelope import (
    CommonEnvelope,
    LicenseAuditEnvelope,
    build_envelope,
)

UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def test_pd_sources_only_safe() -> None:
    env = build_envelope(
        tool="lexical_lookup",
        result={"matches": []},
        sources_used=[
            {"source": "TSK", "license": "public_domain"},
            {"source": "Nestle1904-text", "license": "public_domain"},
        ],
    )
    assert env.ok is True
    assert env.license_audit.response_safe_to_share is True
    assert env.license_audit.non_redistributable_reason is None


def test_ccbync_in_snippet_mode_with_word_caps_safe() -> None:
    env = build_envelope(
        tool="cultural_overlay",
        result={"matches": []},
        sources_used=[{"source": "ETCBC-BHSA", "license": "CC-BY-NC-4.0"}],
        caller_context="personal",
        snippet_word_count=50,
        source_work_word_count=100000,
    )
    assert env.license_audit.response_safe_to_share is True


def test_ccbync_in_public_share_mode_unsafe() -> None:
    env = build_envelope(
        tool="parallel_translation",
        result={"matches": []},
        sources_used=[{"source": "ETCBC-BHSA", "license": "CC-BY-NC-4.0"}],
        caller_context="public-share",
    )
    assert env.license_audit.response_safe_to_share is False
    assert env.license_audit.non_redistributable_reason is not None


def test_sblgnt_eula_in_public_share_unsafe() -> None:
    env = build_envelope(
        tool="parallel_translation",
        result={"matches": []},
        sources_used=[{"source": "SBLGNT-text", "license": "SBLGNT-EULA"}],
        caller_context="public-share",
    )
    assert env.license_audit.response_safe_to_share is False


def test_empty_sources_defensive_unsafe() -> None:
    env = build_envelope(
        tool="some_tool",
        result={},
        sources_used=[],
    )
    assert env.license_audit.response_safe_to_share is False
    assert "no sources declared" in (env.license_audit.non_redistributable_reason or "")


def test_mixed_sources_one_bad_unsafe() -> None:
    env = build_envelope(
        tool="debate_for_verse",
        result={},
        sources_used=[
            {"source": "MorphGNT-morphology", "license": "CC-BY-SA-4.0"},
            {"source": "ETCBC-BHSA", "license": "CC-BY-NC-4.0"},
        ],
        caller_context="export",
    )
    assert env.license_audit.response_safe_to_share is False
    assert "ETCBC-BHSA" in (env.license_audit.non_redistributable_reason or "")


def test_envelope_carries_trace_id_uuid() -> None:
    env = build_envelope(
        tool="t",
        result={},
        sources_used=[{"source": "x", "license": "public_domain"}],
    )
    assert UUID_REGEX.match(env.trace_id) is not None


def test_envelope_accepts_explicit_trace_id() -> None:
    env = build_envelope(
        tool="t",
        result={},
        sources_used=[{"source": "x", "license": "public_domain"}],
        trace_id="abc-123",
    )
    assert env.trace_id == "abc-123"


def test_error_envelope_supported() -> None:
    env = build_envelope(
        tool="t",
        result=None,
        sources_used=[{"source": "x", "license": "public_domain"}],
        ok=False,
        error={"code": "bad_input", "message": "invalid query"},
    )
    assert env.ok is False
    assert env.error is not None
    assert env.error.code == "bad_input"


def test_extra_forbid_on_envelope() -> None:
    with pytest.raises(ValidationError):
        CommonEnvelope.model_validate(
            {
                "ok": True,
                "tool": "x",
                "license_audit": {
                    "sources_used": [],
                    "response_safe_to_share": False,
                },
                "trace_id": "abc",
                "bogus": "field",
            }
        )


def test_warnings_default_empty() -> None:
    env = build_envelope(
        tool="t",
        result={},
        sources_used=[{"source": "x", "license": "public_domain"}],
    )
    assert env.warnings == []


def test_warnings_passed_through() -> None:
    env = build_envelope(
        tool="t",
        result={},
        sources_used=[{"source": "x", "license": "public_domain"}],
        warnings=["truncated to 200 results"],
    )
    assert env.warnings == ["truncated to 200 results"]


def test_license_audit_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        LicenseAuditEnvelope.model_validate(
            {
                "sources_used": [],
                "response_safe_to_share": False,
                "extra": "field",
            }
        )


def test_each_source_carries_redistribute_field() -> None:
    env = build_envelope(
        tool="t",
        result={},
        sources_used=[
            {"source": "TSK", "license": "public_domain"},
            {"source": "ETCBC-BHSA", "license": "CC-BY-NC-4.0"},
        ],
        caller_context="public-share",
    )
    assert env.license_audit.sources_used[0].redistribute is True
    assert env.license_audit.sources_used[1].redistribute is False
