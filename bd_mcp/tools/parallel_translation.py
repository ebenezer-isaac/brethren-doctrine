"""parallel_translation: side-by-side translation lookup with license-aware snippet redaction."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from bd_mcp.tools._common import ToolInputBase, success_envelope

TOOL_NAME = "parallel_translation"


class ParallelTranslationInput(ToolInputBase):
    ref: str = Field(min_length=1)
    translations: list[str] = Field(min_length=1)
    include_original: bool = True


def handle(
    payload: ParallelTranslationInput,
    neo4j_session: Any | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    sources_used: list[dict[str, str]] = []
    if payload.include_original and neo4j_session is not None:
        cypher = (
            "MATCH (v:Verse {osisID: $ref})-[:HAS_WORD]->(w:Word) "
            "RETURN w.surface AS surface ORDER BY w.position"
        )
        original = " ".join(
            rec["surface"] or "" for rec in neo4j_session.run(cypher, ref=payload.ref)
        )
        if original.strip():
            rows.append({"translation": "original", "text": original})
            sources_used.append({"source": "SBLGNT-text", "license": "SBLGNT-EULA"})
    for code in payload.translations:
        rows.append({"translation": code, "text": f"(translation lookup pending for {code})"})
        if code.upper() in {"ESV", "TTESV"}:
            sources_used.append({"source": "STEPBible-TTESV", "license": "CC-BY-NC-4.0"})
        else:
            sources_used.append({"source": f"translation-{code}", "license": "fair-use-policy"})
    result = {"ref": payload.ref, "rows": rows}
    return success_envelope(
        tool=TOOL_NAME,
        result=result,
        sources_used=sources_used,
        caller_context=payload.caller_context,
        snippet_word_count=len(" ".join(r["text"] for r in rows).split()),
        source_work_word_count=600000,
    )


def register(server: Any) -> None:
    @server.tool(name=TOOL_NAME, description="Side-by-side parallel translation rows.")
    def _tool(
        ref: str,
        translations: list[str],
        include_original: bool = True,
        caller_context: Literal["personal", "public-share", "export"] = "personal",
    ) -> dict[str, Any]:
        payload = ParallelTranslationInput(
            ref=ref,
            translations=translations,
            include_original=include_original,
            caller_context=caller_context,
        )
        return handle(payload)
