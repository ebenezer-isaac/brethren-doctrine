# USAGE — Querying the brethren-doctrine corpus

This guide is for any Claude session opening the project in VSCode (or any other tool with file access). It tells you what's where, what queries work today, and what's planned but not yet built.

For the full project picture, read [docs/PROJECT.md](docs/PROJECT.md) first.

---

## Tier 1 (available now)

The static corpus is queryable using only Read + Grep — no external services, no embeddings, no graph DB. This is the baseline working today.

### What's in `parsed/`

15 structured JSON files, one per source document. Each follows the schema in `.claude/skills/ingest-sermons/SKILL.md` Step 4.

Per-document fields you'll use most:
- `doc_slug` — anchor identifier
- `session_metadata.title`, `session_metadata.session_topic`, `session_metadata.topic_clusters`
- `theological_themes` — top-level themes for the document
- `scripture_refs` — every scripture reference, OSIS-normalized
- `chunks[]` — semantic chunks with `content`, `themes`, `claims`, `scripture_refs`, optional `perspectives_within_chunk`
- `confidence` — extraction confidence per dimension

Two aggregate files at the root of `parsed/`:
- `_index.json` — corpus-wide aggregate (themes, scripture coverage, per-doc summaries)
- `_perspectives.json` — cross-document perspective sets (where different docs address the same theme with distinct claims)

### Common query patterns

**"What documents touch a theme?"**
- Read `parsed/_index.json` → `by_theme["<theme>"]` returns document slugs.
- For finer matching, Grep across `parsed/*.json` for the theme keyword.

**"What does the corpus say about [topic]?"**
- Find candidate docs via `_index.json` themes.
- Read those JSONs and pull the matching `chunks[]` by their `themes` array.
- Quote the chunk `content`; cite the chunk `claims`.

**"Show me everything referencing [scripture]"**
- Read `_index.json` → `scripture_coverage["<OSIS book>"]` gives doc slugs.
- For exact verse: Grep across `parsed/*.json` for the OSIS form (e.g., `"Rom 8:1"`).

**"Where do documents disagree or present multiple angles?"**
- Read `parsed/_perspectives.json` → `perspective_sets[]`.
- Each set has `shared_theme`, `perspectives[]` (each anchored to `source_doc` + `chunk_id`), and a `relationship` tag.
- For deeper context, follow the `chunk_id` back to its document JSON.

**"Find every claim about [doctrine]"**
- For each candidate document, iterate `chunks[].claims[]`.
- Filter by theme overlap or keyword match.

**"What's the doctrinal position on [topic]?"**
- Look at any `sof_*.json` (Statement of Faith documents) first — they state positions canonically.
- Then expand to teaching documents (`baptism_and_communion`, `salvation_soteriology`, etc.) for the supporting reasoning.

### Example: jq one-liners

If `jq` is available:

```bash
# All themes from a doc
jq '.theological_themes' parsed/sof_holy_spirit.json

# All scripture refs across the corpus
jq -r '.documents[].doc_slug + " " + (.unique_scripture_books|tostring)' parsed/_index.json

# Perspective sets touching a theme
jq '.perspective_sets[] | select(.shared_theme | contains("baptism"))' parsed/_perspectives.json
```

If `jq` is not available, just Read the JSONs directly.

### Authority hierarchy in Tier 1

Every parsed chunk is `authority_level: 4` (exegetical application). When you cite a Tier 1 result, label it as a *teaching claim*, not as Bible-textual ground truth. The interlinear and original-language verification layer arrive in Tier 2.

---

## Tier 2 (planned — see `docs/TIER_2_SPEC.md`)

Tier 2 adds:
- Semantic search ("find chunks about anxiety even if the word isn't used").
- Hybrid retrieval (BM25 + dense vectors) with cross-encoder reranking.
- Full Bible (multiple translations), Hebrew/Greek interlinear, archaeological metadata, church history.
- Knowledge graph traversal (sermon claim → verse → Hebrew word → archaeological site).
- An MCP server exposing the whole surface as tools (`search_bible_interlinear`, `query_sermon_graph`, `get_doctrine_perspectives`, `lookup_archaeology`, `evaluate_statement_of_faith`).

When Tier 2 lands, you'll switch most queries from Read+Grep to MCP tool calls. Tier 1 remains as the local fallback.

---

## What you should NOT do (in any tier)

- **Never write personal contributor names into outputs.** See [docs/ANONYMIZATION.md](docs/ANONYMIZATION.md). External published authors are fine; teachers whose lessons populate this corpus are not.
- **Never override authority levels** — a teaching claim doesn't trump an interlinear reading. See [docs/AUTHORITY_HIERARCHY.md](docs/AUTHORITY_HIERARCHY.md).
- **Never modify `source-docs/`** — those files are read-only inputs.
- **Don't reinvent ingestion** — re-run the `ingest-sermons` skill if new docs land in `source-docs/`. It's resumable (skips files whose JSON is already current).

---

## Re-running the ingestion

If new files land in `source-docs/`, invoke the `ingest-sermons` skill (or just say "ingest the sermons" / "process source-docs"). It will:
1. Inventory new/changed files.
2. Pre-convert DOCX (pandoc) and PPTX (python-pptx).
3. Dispatch parallel Opus subagents — one per file.
4. Rebuild `parsed/_index.json` and `parsed/_perspectives.json`.

Existing parsed files are not re-processed unless their source `mtime` has changed.

---

## When in doubt

- Project shape and architecture: `docs/PROJECT.md`
- Stack and Tier 2 plan: `docs/TIER_2_SPEC.md`
- Authority rules: `docs/AUTHORITY_HIERARCHY.md`
- Privacy/anonymization: `docs/ANONYMIZATION.md`
- Ingestion mechanics: `.claude/skills/ingest-sermons/SKILL.md`
