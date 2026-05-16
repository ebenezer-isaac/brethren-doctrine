"""concordance_walk: enumerate occurrences of a Strong's code or lemma."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from bd_mcp.tools._common import ToolInputBase, success_envelope

TOOL_NAME = "concordance_walk"


class ConcordanceWalkInput(ToolInputBase):
    strong: str | None = None
    lemma: str | None = None
    window: int = Field(default=5, ge=0, le=30)
    filter_book: list[str] | None = None
    limit: int = Field(default=200, ge=1, le=2000)

    @model_validator(mode="after")
    def at_least_one_anchor(self) -> ConcordanceWalkInput:
        if not self.strong and not self.lemma:
            raise ValueError("either strong or lemma must be provided")
        return self


def handle(payload: ConcordanceWalkInput, neo4j_session: Any | None = None) -> dict[str, Any]:
    occurrences: list[dict[str, Any]] = []
    sources: list[dict[str, str]] = []
    if neo4j_session is not None:
        if payload.strong:
            cypher = (
                "MATCH (l:Lemma {strong: $anchor})<-[:INSTANCE_OF]-(w:Word) "
                "MATCH (w)-[:IN_VERSE]->(v:Verse) "
                "RETURN v.osisID AS ref, w.surface AS surface, "
                "coalesce(w.morph, '') AS morph LIMIT $lim"
            )
            params = {"anchor": payload.strong, "lim": payload.limit}
        else:
            cypher = (
                "MATCH (l:Lemma {lemma: $anchor})<-[:INSTANCE_OF]-(w:Word) "
                "MATCH (w)-[:IN_VERSE]->(v:Verse) "
                "RETURN v.osisID AS ref, w.surface AS surface, "
                "coalesce(w.morph, '') AS morph LIMIT $lim"
            )
            params = {"anchor": payload.lemma, "lim": payload.limit}
        for rec in neo4j_session.run(cypher, **params):
            ref = rec["ref"]
            if payload.filter_book and not any(
                ref.startswith(b + ".") for b in payload.filter_book
            ):
                continue
            occurrences.append(
                {
                    "ref": ref,
                    "surface": rec["surface"],
                    "morph": rec["morph"],
                    "context_left": "",
                    "context_right": "",
                }
            )
        sources.append({"source": "MorphGNT-morphology", "license": "CC-BY-SA-4.0"})
    result = {
        "anchor": payload.strong or payload.lemma,
        "occurrences": occurrences,
        "truncated": len(occurrences) >= payload.limit,
    }
    return success_envelope(
        tool=TOOL_NAME,
        result=result,
        sources_used=sources,
        caller_context=payload.caller_context,
    )


def register(server: Any) -> None:
    @server.tool(name=TOOL_NAME, description="Concordance walk over a Strong's code or lemma.")
    def _tool(
        strong: str | None = None,
        lemma: str | None = None,
        window: int = 5,
        filter_book: list[str] | None = None,
        limit: int = 200,
        caller_context: Literal["personal", "public-share", "export"] = "personal",
    ) -> dict[str, Any]:
        payload = ConcordanceWalkInput(
            strong=strong,
            lemma=lemma,
            window=window,
            filter_book=filter_book,
            limit=limit,
            caller_context=caller_context,
        )
        return handle(payload)
