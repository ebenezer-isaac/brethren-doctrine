"""cross_ref: OpenBible / TSK cross-references for a verse."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from bd_mcp.tools._common import ToolInputBase, success_envelope

TOOL_NAME = "cross_ref"


class CrossRefInput(ToolInputBase):
    ref: str = Field(min_length=1)
    sources: list[str] | None = None
    min_votes: int | None = Field(default=None, ge=0)
    limit: int = Field(default=50, ge=1, le=500)


def handle(payload: CrossRefInput, neo4j_session: Any | None = None) -> dict[str, Any]:
    edges: list[dict[str, Any]] = []
    sources_used: list[dict[str, str]] = []
    if neo4j_session is not None:
        cypher = (
            "MATCH (v:Verse {osisID: $ref})-[r:CROSS_REF]->(v2:Verse) "
            "WHERE ($min_votes IS NULL OR r.votes >= $min_votes) "
            "AND ($sources IS NULL OR r.source IN $sources) "
            "RETURN v.osisID AS from_ref, v2.osisID AS to_ref, "
            "coalesce(r.source, 'openbible') AS source, "
            "coalesce(r.votes, 1) AS votes "
            "ORDER BY votes DESC LIMIT $lim"
        )
        for rec in neo4j_session.run(
            cypher,
            ref=payload.ref,
            min_votes=payload.min_votes,
            sources=payload.sources,
            lim=payload.limit,
        ):
            edges.append(
                {
                    "from": rec["from_ref"],
                    "to": rec["to_ref"],
                    "source": rec["source"],
                    "votes": rec["votes"],
                }
            )
        if any(e["source"] == "openbible" for e in edges):
            sources_used.append({"source": "OpenBible-cross-refs", "license": "CC-BY"})
        if any(e["source"] == "tsk" for e in edges):
            sources_used.append({"source": "TSK", "license": "public_domain"})
    result = {"ref": payload.ref, "edges": edges, "count": len(edges)}
    return success_envelope(
        tool=TOOL_NAME,
        result=result,
        sources_used=sources_used,
        caller_context=payload.caller_context,
    )


def register(server: Any) -> None:
    @server.tool(name=TOOL_NAME, description="Cross-references for a verse.")
    def _tool(
        ref: str,
        sources: list[str] | None = None,
        min_votes: int | None = None,
        limit: int = 50,
        caller_context: Literal["personal", "public-share", "export"] = "personal",
    ) -> dict[str, Any]:
        payload = CrossRefInput(
            ref=ref,
            sources=sources,
            min_votes=min_votes,
            limit=limit,
            caller_context=caller_context,
        )
        return handle(payload)
