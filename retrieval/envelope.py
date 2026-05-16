"""Common MCP response envelope builder.

Computes license_audit and response_safe_to_share per docs/MCP_TOOLS.md.
Every tool emits an envelope with these fields.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ingest.license_guard import Mode, check_redistribute

CallerContext = Literal["personal", "public-share", "export"]


class SourceUsed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    license: str
    redistribute: bool


class LicenseAuditEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources_used: list[SourceUsed]
    response_safe_to_share: bool
    non_redistributable_reason: str | None = None


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str


class CommonEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool
    tool: str
    result: dict[str, Any] | None = None
    error: ErrorEnvelope | None = None
    warnings: list[str] = Field(default_factory=list)
    license_audit: LicenseAuditEnvelope
    trace_id: str


def build_envelope(
    tool: str,
    result: dict[str, Any] | None,
    sources_used: list[dict[str, Any]],
    caller_context: CallerContext = "personal",
    warnings: list[str] | None = None,
    ok: bool = True,
    error: dict[str, Any] | None = None,
    trace_id: str | None = None,
    snippet_word_count: int = 0,
    source_work_word_count: int = 0,
) -> CommonEnvelope:
    mode: Mode = "bulk" if caller_context in {"public-share", "export"} else "snippet"
    normalised: list[SourceUsed] = []
    redistribute_results: list[bool] = []
    reasons: list[str] = []

    for src in sources_used:
        license_str = src.get("license", "")
        check = check_redistribute(
            license_str=license_str,
            mode=mode,
            snippet_word_count=snippet_word_count,
            source_work_word_count=source_work_word_count,
        )
        allowed = bool(check["allowed"])
        normalised.append(
            SourceUsed(
                source=src.get("source", ""),
                license=license_str,
                redistribute=allowed,
            )
        )
        redistribute_results.append(allowed)
        if not allowed:
            reasons.append(f"{src.get('source', '?')}: {check['reason']}")

    if not sources_used:
        # Defensive: empty sources means we cannot prove safety.
        safe = False
        reasons.append("no sources declared")
    else:
        safe = all(redistribute_results)

    audit = LicenseAuditEnvelope(
        sources_used=normalised,
        response_safe_to_share=safe,
        non_redistributable_reason="; ".join(reasons) if reasons else None,
    )
    err = ErrorEnvelope.model_validate(error) if error else None
    return CommonEnvelope(
        ok=ok,
        tool=tool,
        result=result,
        error=err,
        warnings=list(warnings or []),
        license_audit=audit,
        trace_id=trace_id or str(uuid.uuid4()),
    )
