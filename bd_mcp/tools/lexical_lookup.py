"""lexical_lookup: Strong's / lemma / surface / gloss lookup against the lexical store."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from bd_mcp.tools._common import ToolInputBase, success_envelope

TOOL_NAME = "lexical_lookup"


class LexicalLookupInput(ToolInputBase):
    query: str = Field(min_length=1)
    lang: Literal["hb", "gk"]
    id_type: Literal["strong", "lemma", "surface", "gloss"] = "strong"
    limit: int = Field(default=20, ge=1, le=200)


def handle(payload: LexicalLookupInput, neo4j_session: Any | None = None) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    sources: list[dict[str, str]] = []
    if neo4j_session is not None:
        cypher_by_type = {
            "strong": "MATCH (l:Lemma {strong: $q}) RETURN l LIMIT $lim",
            "lemma": "MATCH (l:Lemma {lemma: $q}) RETURN l LIMIT $lim",
            "surface": "MATCH (w:Word {surface: $q})-[:INSTANCE_OF]->(l:Lemma) RETURN DISTINCT l LIMIT $lim",
            "gloss": "MATCH (l:Lemma) WHERE l.gloss CONTAINS $q RETURN l LIMIT $lim",
        }
        cypher = cypher_by_type[payload.id_type]
        for rec in neo4j_session.run(cypher, q=payload.query, lim=payload.limit):
            lemma = dict(rec["l"])
            matches.append(
                {
                    "strong": lemma.get("strong"),
                    "lemma": lemma.get("lemma"),
                    "transliteration": lemma.get("transliteration"),
                    "occurrences_in_canon": lemma.get("occurrences_in_canon"),
                    "gloss": lemma.get("gloss"),
                }
            )
        source_slug = "STEPBible-TBESH" if payload.lang == "hb" else "STEPBible-TBESG"
        sources.append({"source": source_slug, "license": "CC-BY-4.0"})
    result = {
        "query": payload.query,
        "lang": payload.lang,
        "id_type": payload.id_type,
        "matches": matches,
        "truncated": len(matches) >= payload.limit,
    }
    return success_envelope(
        tool=TOOL_NAME,
        result=result,
        sources_used=sources,
        caller_context=payload.caller_context,
    )


def register(server: Any) -> None:
    @server.tool(
        name=TOOL_NAME, description="Strong's / lemma / surface lookup in the lexical store."
    )
    def _tool(
        query: str,
        lang: Literal["hb", "gk"],
        id_type: Literal["strong", "lemma", "surface", "gloss"] = "strong",
        limit: int = 20,
        caller_context: Literal["personal", "public-share", "export"] = "personal",
    ) -> dict[str, Any]:
        payload = LexicalLookupInput(
            query=query,
            lang=lang,
            id_type=id_type,
            limit=limit,
            caller_context=caller_context,
        )
        return handle(payload)
