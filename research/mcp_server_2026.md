# MCP Server Patterns for Brethren-Doctrine GraphRAG (2026)

Research synthesis for the query-engine MCP server exposing the brethren-doctrine corpus
(Bible interlinear, sermon graph, doctrine perspectives, archaeology, statement-of-faith eval)
to LLM clients (Claude Desktop, VSCode Claude Code, Flutter app).

---

## 1. Recommended Tool Surface

Five tools — within the current 5-15 sweet spot recommended by Phil Schmid, Docker, and
Block. Each is **outcome-oriented**, returns a uniform response envelope (see §3),
supports pagination where lists are unbounded, and uses `Literal`-style enums over
free-text wherever feasible. The corpus uses scripture references, not arbitrary IDs, so
`reference` strings (e.g., `"Romans 8:28-30"`) are the natural keys.

```jsonc
// Tool 1 — interlinear lookup over a fixed verse range.
{
  "name": "search_bible_interlinear",
  "description": "Return Hebrew/Greek interlinear + selected English translations for a verse range. Use when the user asks about original-language meaning, Strong's numbers, or word-by-word morphology.",
  "inputSchema": {
    "reference": "string (USFM-ish: 'John 3:16', 'Rom 8:28-30')",
    "versions": "array<enum['ESV','KJV','NASB','NIV','LSB','NET']>  // default ['ESV']",
    "include_morphology": "boolean (default true)",
    "include_strongs": "boolean (default true)"
  },
  "outputSchema": "{ reference, verses: [{ ref, original_lang, words: [{surface, lemma, strongs, morph, gloss}], translations: {ESV: '...', KJV: '...'} }] }"
}

// Tool 2 — semantic search over the sermon/teaching graph.
{
  "name": "query_sermon_graph",
  "description": "GraphRAG over the brethren sermon corpus + linked teachings. Returns ranked passages with their position in the doctrine graph (related concepts, parent topic, contradicting views). Use for thematic / conceptual questions.",
  "inputSchema": {
    "concept": "string (free-text query, max 500 chars)",
    "filters": {
      "speaker": "string?",
      "date_range": "{from: ISO-date, to: ISO-date}?",
      "doctrine_area": "enum['soteriology','ecclesiology','pneumatology','eschatology','hamartiology','christology','theology-proper','anthropology']?",
      "min_authority": "enum['draft','reviewed','council-approved','scripture'] default 'reviewed'"
    },
    "limit": "integer (1-25, default 10)",
    "cursor": "string? (opaque pagination token)"
  }
}

// Tool 3 — multi-perspective doctrine retrieval.
{
  "name": "get_doctrine_perspectives",
  "description": "Return the spectrum of views on a theme as held by named brethren teachers, plus contrasting external perspectives (Reformed/Arminian/Dispensational/etc). Use when the user asks 'what do brethren believe about X' or wants comparison.",
  "inputSchema": {
    "theme": "string",
    "include_external_views": "boolean (default true)",
    "max_perspectives_per_camp": "integer (default 3)"
  }
}

// Tool 4 — geo/archaeology lookup.
{
  "name": "lookup_archaeology",
  "description": "Find archaeological / geographical / historical-cultural context for a biblical location, person, artifact, or event.",
  "inputSchema": {
    "subject": "string",
    "subject_type": "enum['location','person','artifact','event','custom'] (optional, server will infer)",
    "depth": "enum['brief','standard','deep'] default 'standard'"
  }
}

// Tool 5 — SOF alignment evaluation.
{
  "name": "evaluate_statement_of_faith",
  "description": "Compare a free-text doctrinal statement against the brethren SOF corpus. Returns alignment score per SOF section, citations, and flagged divergences. Use for catechesis, sermon review, or membership interviews.",
  "inputSchema": {
    "text": "string (max 8000 chars)",
    "sof_sections": "array<enum['god','god_the_father','god_the_son','holy_spirit','man','salvation','church','last_things']> (default = all)",
    "strictness": "enum['lenient','standard','strict'] default 'standard'"
  }
}
```

Deliberately **not** included: separate `list_*`, `get_by_id`, `count`, or per-translation tools.
Those are the granular API mistake Schmid and Workato warn against — agents end up chaining
calls and burning tokens. Each of the five tools above maps to a workflow the user actually
performs.

---

## 2. Recommended SDK: **FastMCP 3.x (Python)**

- 70%+ of MCP servers run on some FastMCP fork; 4M+ daily downloads (March 2026).
- 3.0 (Feb 2026) added OAuth, OpenTelemetry, and server composition.
- 3.1's "code mode" pattern can collapse our five-tool catalog further if context bloat shows up later.
- Migration to the official `mcp` SDK is straightforward (FastMCP wraps it) if we hit framework limits.
- Our backend will be Python anyway (LightRAG / LangGraph / sentence-transformers ecosystem), so this avoids a Node boundary.

Pick the **official `mcp` SDK** only if we needed a custom transport — we don't.

---

## 3. Response Format — Uniform Envelope with Citation-First Design

Every tool returns the same shape. `content[0]` is a model-readable text summary;
`structuredContent` carries the machine-parseable payload (zero token cost in
strict-content clients per the 2025-06-18 spec). Citations are first-class via
`resource_link` content blocks — the LLM can reproduce them verbatim, and Flutter / Claude
Desktop can render them as deep links.

```jsonc
{
  "content": [
    { "type": "text", "text": "<concise human/LLM summary, <= 800 tokens, includes inline [^1] markers>" },
    { "type": "resource_link", "uri": "brethren://sermon/2024-03-17-eph2",
      "name": "Sermon — Ephesians 2 (2024-03-17)",
      "annotations": { "audience": ["assistant","user"], "priority": 0.9 } },
    { "type": "resource_link", "uri": "brethren://sof/god_the_son#section-3.2",
      "name": "SOF — God the Son §3.2" }
  ],
  "structuredContent": {
    "status": "ok | no_results | ambiguous | partial",
    "result": [ /* per-tool payload */ ],
    "citations": [
      {
        "id": "c1",
        "uri": "brethren://sermon/2024-03-17-eph2#chunk-42",
        "title": "Sermon — Ephesians 2 (2024-03-17), 14:32–16:10",
        "authority_level": "council-approved | reviewed | draft | scripture | external",
        "confidence": 0.87,
        "snippet": "...",
        "source_type": "sermon | sof | bible | archaeology | external"
      }
    ],
    "pagination": { "total": 142, "returned": 10, "next_cursor": "eyJvIjoxMH0=" },
    "disambiguation": null   // or [{label, hint, refine_with}]
  },
  "isError": false
}
```

Key design rules:

- **`authority_level`** on every citation lets the LLM hedge appropriately ("the brethren SOF teaches…" vs "one elder has suggested…"). Drives prompt-side phrasing without us needing to engineer per-call instructions.
- **`status: "no_results"`** returns a *helpful string*, not an empty array — Schmid's "User not found. Try searching by email instead." pattern. Server suggests reformulations.
- **`status: "ambiguous"`** populates `disambiguation` with concrete refinements (e.g., "Did you mean baptism-as-ordinance or baptism-of-Spirit?"). Avoids the LLM guessing.
- **Pagination via opaque cursor** (per 2025-06-18 spec). Default `limit` 10; hard cap 25 for sermon graph, 5 for perspectives.
- **No streaming for v1.** Streamable-HTTP transport is enabled, but each tool returns a single response. Streaming adds complexity we don't need until a single result exceeds ~4k tokens — at which point switch `query_sermon_graph` to incremental.
- **Backwards-compat**: serialize `structuredContent` into the trailing `content` text block as JSON, per spec.

---

## 4. Concrete Next Steps

1. **Scaffold**: `uv init brethren-mcp && uv add fastmcp pydantic` — start from FastMCP's quickstart with stdio transport for local Claude Desktop + Claude Code testing.
2. Build `evaluate_statement_of_faith` first — it has the smallest scope (compare text to existing `converted/sof_*.md`) and exercises the full envelope (citations, authority_level, status). Forces us to design the citation URI scheme (`brethren://...`) early.
3. Add `query_sermon_graph` second — drives the GraphRAG indexing work (LightRAG over `converted/` + future sermon transcripts).
4. Wire **Streamable-HTTP** with `stateless_http=True, json_response=True` once we deploy beyond stdio. Defer OAuth 2.1 / WorkOS until we expose the server to the Flutter app over the public internet.
5. Write a `tools_eval.py` harness that calls every tool with happy-path, no-result, ambiguous, and adversarial inputs (per the testing rules) — MCP servers without this regress silently when the corpus changes.
6. Add `resources/` exposure for the underlying SOF docs as MCP Resources so clients can also subscribe / fetch them directly when a `resource_link` is followed.

---

## 5. Sources

- [The 2026 MCP Roadmap — modelcontextprotocol.io](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [MCP Tools Specification (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [Phil Schmid — MCP is Not the Problem, It's Your Server: Best Practices](https://www.philschmid.de/mcp-best-practices)
- [Block Engineering — Block's Playbook for Designing MCP Servers](https://engineering.block.xyz/blog/blocks-playbook-for-designing-mcp-servers)
- [The New Stack — 15 Best Practices for Building MCP Servers in Production](https://thenewstack.io/15-best-practices-for-building-mcp-servers-in-production/)
- [FutureSearch — MCP `structuredContent`: How to Return Large Results Without Flooding the Context Window](https://futuresearch.ai/blog/mcp-results-widget/)
- [Cisco Blogs — What's New in MCP: Elicitation, Structured Content, OAuth Enhancements](https://blogs.cisco.com/developer/whats-new-in-mcp-elicitation-structured-content-and-oauth-enhancements)
- [FastMCP 2.0 vs MCP Python SDK — modelcontextprotocol/python-sdk #1068](https://github.com/modelcontextprotocol/python-sdk/issues/1068)
- [FastMCP — gofastmcp.com docs](https://gofastmcp.com/getting-started/welcome)
- [Sacred Scriptures MCP (reference RAG-over-religious-corpus implementation)](https://github.com/Traves-Theberge/sacred-scriptures-mcp)
- [TheologAI — Bible Study MCP Server (interlinear/morphology reference)](https://lobehub.com/mcp/tj-frederick-theologai)
- [RAG-MCP: Mitigating Prompt Bloat in LLM Tool Selection (arXiv 2505.03275)](https://arxiv.org/html/2505.03275v1)
- [Stack Overflow Blog — Authentication and Authorization in MCP](https://stackoverflow.blog/2026/01/21/is-that-allowed-authentication-and-authorization-in-model-context-protocol/)
