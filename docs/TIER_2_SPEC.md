# Tier 2 Implementation Spec: Semantic + Graph Layer

Status: design-locked draft. Synthesized from `research/embeddings_2026.md`,
`research/graphrag_2026.md`, `research/bible_data_sources_2026.md`,
`research/mcp_server_2026.md`, and `research/hybrid_search_rerank_2026.md`.

---

## 1. Goal & Success Criteria

Tier 1 produces anonymized sermon JSONs in `parsed/`, grep-searchable only.
Tier 2 adds semantic recall, cross-domain joins, and authority-aware ranking.

Five queries the system must answer:

1. *"Show me every chunk that addresses imputed righteousness, ordered by
   authority, with the underlying Greek term."*
2. *"Where do the sermon notes and the SOF disagree on the recipients of
   baptism?"* (contradiction surface across the `PRESENTS_PERSPECTIVE_ON` edge.)
3. *"Which Hebrew word underlies the English `love` in Hosea 3, and what
   archaeological context does Open Context have for the locations named in
   that chapter?"* (pure graph traversal; no semantic search required.)
4. *"Find sermon chunks that paraphrase Romans 6:1–4 without quoting it
   verbatim."* (dense recall on `voyage-context-3` plus BM25 fallback for the
   handful of literal references.)
5. *"Score this 600-word doctrinal statement against my SOF: section-by-section
   alignment, citations, and any divergences."* (`evaluate_statement_of_faith`
   tool exercising the full envelope.)

Success bar:
- Recall@10 ≥ 0.90 on a 30-query gold set covering scripture-anchored,
  thematic, comparative, and exact-name intents (per `hybrid_search_rerank_2026.md` §6).
- p95 latency under 1500 ms on personal hardware (single-digit QPS budget).
- Embedding spend $0/month while the Voyage 200M-token free tier holds (per
  `embeddings_2026.md` §4b).
- Every retrieved item carries `authority_level` and `source_type` so the LLM
  can hedge correctly. Non-negotiable for theological discernment use.

---

## 2. Architecture Decision Summary

One coherent stack, chosen so each component is the smallest piece that still
clears the success bar.

| Layer | Choice | Fallback | Source |
|---|---|---|---|
| Embeddings | **`voyage-context-3`** @ 1024-dim float32, 32k ctx | `voyage-4-large`, then `BGE-M3` self-host | `embeddings_2026.md` §1–2 |
| Vector DB | **Qdrant** (self-host single-node Docker, then Qdrant Cloud free tier) | Neo4j-only vector index | `graphrag_2026.md` §1, `hybrid_search_rerank_2026.md` §3 |
| Knowledge graph | **Neo4j 5.x Community** (Docker), with APOC | Postgres + AGE + pgvector | `graphrag_2026.md` §1 |
| Reranker | **BGE-reranker-v2-m3** in-process via `sentence-transformers`, CPU first | Cohere Rerank 3.5 | `hybrid_search_rerank_2026.md` §2 |
| BM25 | **Qdrant native sparse vectors with `Modifier.IDF`** | Neo4j full-text index | `hybrid_search_rerank_2026.md` §3 |
| MCP server | **FastMCP 3.x** (Python), stdio transport first | Official `mcp` SDK | `mcp_server_2026.md` §2 |
| Orchestration | **`neo4j-graphrag-python`** for the `VectorCypherRetriever` and `QdrantNeo4jRetriever`; thin custom Python around it | LlamaIndex Property Graph Index | `graphrag_2026.md` §4 |

Rationale shorthand:
- **Qdrant over Neo4j-only vector**: 50k nodes × 4 translations + ~700k interlinear words push embedding count past 500k, where Qdrant out-recalls Neo4j HNSW (`graphrag_2026.md` §1). `QdrantNeo4jRetriever` keeps orchestration first-party.
- **Neo4j over Postgres+AGE**: 3 to 5 hop traversals with property filters at every hop are AGE's worst case (`graphrag_2026.md` §1).
- **FastMCP 3.x**: 70%+ install share, Feb-2026 added OAuth + OTel; backend is Python anyway (`mcp_server_2026.md` §2).
- **`neo4j-graphrag-python` over LlamaIndex**: first-party `QdrantNeo4jRetriever` + template Cypher cuts hallucinated traversals 23% → <4% (`graphrag_2026.md` §4).

---

## 3. Data Model: Neo4j Schema

Single shared ontology, namespaced by label prefix (per `graphrag_2026.md` §2).
One Neo4j database. Authority lives as a **property on every retrievable
node**, not as a node label, so it can be both a `WHERE` filter and a re-rank
weight in one expression.

### 3.1 Node labels (key properties)

```cypher
// Bible canonical text, one node per OSIS verse_id
(:Verse {
  verse_id,            // OSIS, e.g. 'Rom.8.1', UNIQUE
  book_osis, chapter, verse, testament,
  translations,        // map<trans_code, text>
  embedding,           // 1024-dim, voyage-context-3
  authority_level      // 1 (canonical text)
})

// Original-language word, one per Strong's-disambiguated lemma
(:Token:Hebrew | :Token:Greek {
  strongs,             // extended form, e.g. 'G0026', UNIQUE
  lemma, transliteration, morph,
  gloss_short, gloss_long,
  embedding,           // optional; populate for top-N salient tokens
  authority_level      // 0 (interlinear is source of truth)
})

// Sermon-note chunk from parsed/*.json
(:SermonChunk {
  chunk_id,            // doc_slug + index, UNIQUE
  source_doc,          // filename only, never personal name
  text,                // verbatim chunk content
  type,                // teaching|quote|perspective|application|definition|illustration|...
  themes,              // list<string>
  claims,              // list<string>
  embedding,
  authority_level      // 4
})

// Statement-of-Faith chunk
(:SOFChunk {
  chunk_id,
  section,             // god|god_the_father|god_the_son|holy_spirit|man|salvation|church|last_things
  text, themes, claims,
  embedding,
  authority_level      // 3
})

// Concept / theme node, the join table for cross-domain reasoning
(:Concept {
  name,                // canonical, e.g. 'imputed_righteousness', UNIQUE
  aliases,             // list<string>
  domain,              // soteriology|ecclesiology|...
  embedding
})

// Church-history nodes
(:Figure  { name UNIQUE, era, tradition })
(:Movement { name UNIQUE, date_range })
(:Confession { name UNIQUE, date_range, tradition })
(:Era       { name UNIQUE, date_range })

// Archaeology / geography (Open Context + Pleiades)
(:Site     { name UNIQUE, period, lat, lon, opencontext_uri })
(:Artifact { name UNIQUE, period, opencontext_uri })

// Provenance / source tracking
(:Source   { uri UNIQUE, kind, license, retrieved_at })
```

### 3.2 Relationship types

```
(:Verse)-[:TRANSLATES_TO {translation}]->(:Verse)         // cross-translation pairs
(:Verse)-[:CONTAINS_TOKEN {position}]->(:Token)
(:SermonChunk)-[:REFERENCES {confidence}]->(:Verse)
(:SOFChunk)-[:REFERENCES {confidence}]->(:Verse)
(:SermonChunk|:SOFChunk)-[:MENTIONS {salience}]->(:Concept|:Figure|:Site|:Artifact)
(:Confession|:SermonChunk|:SOFChunk)-[:ALIGNS_WITH {strength}]->(:Concept)
(:SermonChunk|:SOFChunk|:Confession)-[:PRESENTS_PERSPECTIVE_ON
   {stance:'affirms'|'denies'|'qualifies', source_doc}]->(:Concept)   // load-bearing
(:Concept)-[:ORIGINATES_IN]->(:Era|:Movement)
(:Source)-[:VERIFIED_BY]->(:Source)
(:Site)-[:LOCATED_IN]->(:Site)                            // gazetteer hierarchy
```

### 3.3 Indexes & constraints (commit `schema.cypher` on day 1)

```cypher
CREATE CONSTRAINT verse_id_uq IF NOT EXISTS
  FOR (v:Verse) REQUIRE v.verse_id IS UNIQUE;
CREATE CONSTRAINT token_strongs_uq IF NOT EXISTS
  FOR (t:Token) REQUIRE t.strongs IS UNIQUE;
CREATE CONSTRAINT chunk_id_uq IF NOT EXISTS
  FOR (c:SermonChunk) REQUIRE c.chunk_id IS UNIQUE;
CREATE CONSTRAINT sof_chunk_id_uq IF NOT EXISTS
  FOR (c:SOFChunk) REQUIRE c.chunk_id IS UNIQUE;
CREATE CONSTRAINT concept_name_uq IF NOT EXISTS
  FOR (c:Concept) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT figure_name_uq IF NOT EXISTS
  FOR (f:Figure) REQUIRE f.name IS UNIQUE;

// Vector indexes (1024 dim, COSINE, voyage-context-3 default)
CREATE VECTOR INDEX verse_embed       IF NOT EXISTS
  FOR (v:Verse)       ON v.embedding       OPTIONS { indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'COSINE'} };
CREATE VECTOR INDEX sermon_chunk_embed IF NOT EXISTS
  FOR (c:SermonChunk) ON c.embedding       OPTIONS { indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'COSINE'} };
CREATE VECTOR INDEX sof_chunk_embed   IF NOT EXISTS
  FOR (c:SOFChunk)    ON c.embedding       OPTIONS { indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'COSINE'} };
CREATE VECTOR INDEX concept_embed     IF NOT EXISTS
  FOR (c:Concept)     ON c.embedding       OPTIONS { indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'COSINE'} };

// Composite + B-tree
CREATE INDEX verse_bcv IF NOT EXISTS FOR (v:Verse) ON (v.book_osis, v.chapter, v.verse);
CREATE INDEX authority_chunk IF NOT EXISTS FOR (c:SermonChunk) ON (c.authority_level);
CREATE INDEX authority_sof   IF NOT EXISTS FOR (c:SOFChunk)    ON (c.authority_level);

// Full-text (used as Neo4j-side BM25 fallback if Qdrant unavailable)
CREATE FULLTEXT INDEX chunk_text_ft IF NOT EXISTS FOR (n:SermonChunk|SOFChunk) ON EACH [n.text];
```

Authority levels (per project convention, Tier 1 SKILL.md §"Authority and Context"):

| Level | Meaning | Examples |
|---|---|---|
| 0 | Interlinear / morphology | STEPBible TAHOT/TAGNT, OSHB, MorphGNT |
| 1 | Canonical text | Verse nodes (translations) |
| 2 | Lexical / language reference | TBESH, TBESG glosses |
| 3 | Confessional / SOF | `SOFChunk`, historic confessions |
| 4 | Exegetical application | `SermonChunk`, archaeology, history |

---

## 4. Ingestion Pipeline

Six phases. Every adapter emits a typed `GraphRecord` (Pydantic) which the
single `upsert_record(rec, tx)` writer maps to Neo4j `MERGE` + Qdrant
`upsert`. Authority stamped by the adapter, never inferred downstream.

### 4.a Sermon chunk preparation (already 80% done)

`parsed/*.json` is the input. For each chunk:

```python
# scripts/build_chunk_payloads.py
def chunk_to_payload(doc, chunk) -> dict:
    return {
        "chunk_id":        chunk["chunk_id"],
        "source_doc":      doc["doc_slug"],
        "text":            chunk["content"],
        "type":            chunk["type"],
        "themes":          chunk["themes"],
        "claims":          chunk["claims"],
        "scripture_refs":  chunk["scripture_refs"],          # OSIS normalized
        "perspectives":    chunk["perspectives_within_chunk"],
        "authority_level": doc["authority_level"],            # 4
    }
```

Output: `chunks/sermons.jsonl` (one chunk per line). SOF chunks go to
`chunks/sof.jsonl` with `authority_level: 3` and `section` extracted from the
filename (`sof_god.json` → `god`).

No re-chunking. Tier 1's chunks (100 to 600 words) fit `voyage-context-3`'s 32k
ctx; each embeds as one vector with the parent doc passed as `context`.

### 4.b Bible text ingest

Per `bible_data_sources_2026.md` §1, in this exact order:

1. `git clone https://github.com/STEPBible/STEPBible-Data data/private/stepbible`.
   Load TAHOT (Hebrew OT) + TAGNT (Greek NT) TSVs via `pandas.read_csv(sep='\t', comment='#')`.
   Each row becomes a `Verse`-or-`Token` upsert. `verse_id` is OSIS.
2. `git clone https://github.com/openscriptures/morphhb data/private/oshb`.
   Parse OSIS XML with `lxml`; cross-validate token counts vs TAHOT,
   write diffs to `logs/oshb_vs_tahot.diff`.
3. `pip install py-sblgnt`. Cross-validate Greek tokens vs TAGNT.
4. Load TBESH + TBESG into the `:Token` `gloss_short`/`gloss_long` properties.
5. Load TTESV (ESV with Strong's already mapped) → `Verse.translations.ESV`
   plus `(:Verse)-[:CONTAINS_TOKEN]->(:Token)` edges.
6. ESV / NLT / NIV / NKJV / KJV via API (`httpx` + `tenacity` + `diskcache`).
   Cache aggressively; text is static. Store private translations under
   `data/private/`; gitignore.

### 4.c Interlinear (Hebrew/Greek)

Side effect of 4.b. STEPBible is the single backbone. OSHB + MorphGNT are
loaded as second witnesses for QA only; we flag mismatches, do not duplicate
token nodes (`bible_data_sources_2026.md` §1.1).

### 4.d Embedding & vector load

Driver script `scripts/embed_and_load.py`:

```python
import voyageai, qdrant_client
vo = voyageai.Client()                         # reads VOYAGE_API_KEY
qc = qdrant_client.QdrantClient(url="http://localhost:6333")

# One-time collection bootstrap
qc.create_collection(
    "chunks",
    vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
    sparse_vectors_config={"bm25": SparseVectorParams(modifier=Modifier.IDF)},
)

# Embed in batches of 128, contextual mode
for batch in batched(jsonl_iter("chunks/sermons.jsonl"), 128):
    texts    = [c["text"]    for c in batch]
    contexts = [c["source_doc"] for c in batch]
    res = vo.contextualized_embed(inputs=texts, contexts=contexts,
                                  model="voyage-context-3", output_dimension=1024)
    for c, vec in zip(batch, res.embeddings):
        qc.upsert("chunks", points=[PointStruct(
            id=c["chunk_id"], vector={"dense": vec},
            payload={**c, "model": "voyage-context-3", "model_v": "1.0",
                     "embedded_at": now()}
        )])
```

Per `embeddings_2026.md` §4f, every vector record stores
`(model_name, model_version, dim, quantization, embedded_at)` so a future
model swap is a clean migration.

Sparse BM25 vectors are produced by FastEmbed's `Qdrant/bm25` model and
co-upserted in the same call.

### 4.e Neo4j load

Same `upsert_record` walks `chunks/*.jsonl`. Pseudocode:

```cypher
MERGE (c:SermonChunk {chunk_id: $chunk_id})
ON CREATE SET c += $props, c.created_at = datetime()
ON MATCH  SET c += $props, c.updated_at = datetime()
WITH c
UNWIND $scripture_refs AS ref
  MATCH (v:Verse {verse_id: ref})
  MERGE (c)-[:REFERENCES {confidence: 1.0}]->(v)
WITH c
UNWIND $themes AS theme
  MERGE (k:Concept {name: theme})
  MERGE (c)-[:MENTIONS {salience: 1.0}]->(k)
```

Embeddings are written to Qdrant first; Neo4j stores the same chunk_id and
optionally a copy of the embedding for graph-side ANN entry points
(`Verse.embedding`, `Concept.embedding`, `SermonChunk.embedding`). Outbox
table (`outbox_events`) ensures dual-write consistency: Neo4j tx writes the
graph + an outbox row; a worker drains outbox into Qdrant; row deleted on ack.
Per `graphrag_2026.md` §4 step 7: add the outbox before Qdrant goes live, not
after.

### 4.f Authority binding

`authority_level` is stamped by the adapter at the boundary:

| Adapter | Level |
|---|---|
| `verse_loader.py` | 1 |
| `token_loader.py` | 0 |
| `lexicon_loader.py` (TBESH/TBESG) | 2 |
| `sof_loader.py` (parsed/sof_*.json) | 3 |
| `sermon_loader.py` (other parsed/*.json) | 4 |
| `archaeology_loader.py` | 4 |
| `history_loader.py` | 4 |

Pydantic models reject any record missing `authority_level`. No defaults, no
inference downstream.

---

## 5. Retrieval Pipeline

Server-side in Qdrant where possible (`hybrid_search_rerank_2026.md` §1). K
values tuned high (80/80 → 60) because theology is paraphrase-heavy.

### Stage 0: Intent routing

Cheap regex + small classifier returns `{bm25_w, dense_w, use_graph}`:

```python
def route(query: str) -> Routing:
    if SCRIPTURE_RE.search(query):                  # "Rom 8:28"
        return Routing(bm25_w=0.7, dense_w=0.3, use_graph=True)
    if NAMED_FIGURE_RE.search(query):
        return Routing(bm25_w=0.6, dense_w=0.4, use_graph=True)
    if any(w in query.lower() for w in ("vs", "versus", "differ", "disagree")):
        return Routing(bm25_w=0.3, dense_w=0.7, use_graph=True)  # comparative; graph traversal
    return Routing(bm25_w=0.5, dense_w=0.5, use_graph=False)
```

### Stage 1: Parallel hybrid retrieval, K=80 each

One Qdrant Query-API call:

```python
qc.query_points(
    collection_name="chunks",
    prefetch=[
        Prefetch(query=dense_vec,  using="dense", limit=80),
        Prefetch(query=sparse_vec, using="bm25",  limit=80),
    ],
    query=FusionQuery(fusion=Fusion.RRF),
    limit=60,
    with_payload=True,
    score_threshold=None,
)
```

If Stage 0 set `use_graph=True`: in parallel, run a Cypher hop-1 query from
matched scripture/figure/concept nodes via the `VectorCypherRetriever`, cap 40
chunks. Merge into the fusion input.

### Stage 2: Weighted RRF

Use Qdrant's `Fusion.RRF` (`k=60`) with per-source weights from Stage 0. RRF
beats alpha-weighted normalization here because BM25 and cosine scores live in
different distributions (`hybrid_search_rerank_2026.md` §1).

### Stage 3: Cross-encoder rerank, 60 → 10

```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)

# Authority-aware tagging (Layer B from research §4)
def tag(doc):
    return f"[authority:{doc['authority_level']}] [type:{doc['source_type']}] {doc['text']}"

pairs = [(query, tag(d)) for d in fused]
scores = reranker.predict(pairs, batch_size=16)
```

### Stage 4: Authority + recency boost

```python
final = rerank_score \
      + 0.08 * (authority_level / 4.0) \
      + 0.04 * recency_decay(date) \
      - 0.05 * is_speculative_flag
```

Caps small (`hybrid_search_rerank_2026.md` §4). Authority nudges ties, never overrides.

### Stage 5: Graph expansion (route-flagged): hop-1 Cypher per top-K chunk
(verses, concepts, opposing-stance peers) → `graph_context`.

### Stage 6: Contradiction surface: query (b) from `graphrag_2026.md` §3 over the top-K set; opposing-stance pairs → `disagreements: []`.

### Response envelope (returned to caller and to MCP clients)

```jsonc
{
  "status": "ok | no_results | ambiguous | partial",
  "answer_context": [
    {
      "chunk_id": "...",
      "source_type": "sermon|sof|bible|archaeology|external|interlinear",
      "authority_level": 4,
      "text": "...",
      "citations": ["brethren://sermon/baptism_and_communion#chunk-02"],
      "graph_context": { "verses": [...], "concepts": [...] }
    }
  ],
  "disagreements": [
    { "concept": "baptism_recipients",
      "left":  { "chunk_id": "...", "stance": "affirms"  },
      "right": { "chunk_id": "...", "stance": "qualifies" } }
  ],
  "pagination": { "total": 142, "returned": 10, "next_cursor": "..." }
}
```

---

## 6. MCP Tool Surface

Five tools, within Phil Schmid's 5 to 15 sweet spot
(`mcp_server_2026.md` §1). All return the uniform envelope from §5.

```jsonc
// 1. Interlinear lookup over a verse range.
{ "name": "search_bible_interlinear",
  "input": {
    "reference": "string  // 'Rom 8:28-30'",
    "versions":  "array<enum['ESV','KJV','NIV','NLT','NKJV']>  // default ['ESV']",
    "include_morphology": "boolean // default true",
    "include_strongs":    "boolean // default true"
  } }

// 2. Semantic search over the sermon + SOF graph.
{ "name": "query_sermon_graph",
  "input": {
    "concept": "string // free-text, max 500 chars",
    "filters": {
      "source_doc":    "string?",
      "doctrine_area": "enum['soteriology','ecclesiology','pneumatology','eschatology','hamartiology','christology','theology-proper','anthropology']?",
      "min_authority": "integer 0-4 // default 3"
    },
    "limit":  "integer 1-25 // default 10",
    "cursor": "string?"
  } }

// 3. Multi-perspective doctrine retrieval. Surfaces the contradiction graph.
{ "name": "get_doctrine_perspectives",
  "input": {
    "theme": "string",
    "include_external_views": "boolean // default true",
    "max_perspectives_per_camp": "integer // default 3"
  } }

// 4. Geo / archaeology / cultural-context lookup.
{ "name": "lookup_archaeology",
  "input": {
    "subject":      "string",
    "subject_type": "enum['location','person','artifact','event','custom']?",
    "depth":        "enum['brief','standard','deep'] // default 'standard'"
  } }

// 5. Statement-of-faith alignment evaluation.
{ "name": "evaluate_statement_of_faith",
  "input": {
    "text":         "string  // max 8000 chars",
    "sof_sections": "array<enum['god','god_the_father','god_the_son','holy_spirit','man','salvation','church','last_things']> // default = all",
    "strictness":   "enum['lenient','standard','strict'] // default 'standard'"
  } }
```

Deliberately excluded: per-translation getters, list/count helpers, separate
Qdrant/Neo4j tools. Each exposed tool maps to a workflow the user actually
performs (`mcp_server_2026.md` §1).

URI scheme for citations:
`brethren://{source_type}/{slug}#chunk-{n}`. Examples:
`brethren://sermon/baptism_and_communion#chunk-02`,
`brethren://sof/god_the_son#section-3.2`,
`brethren://verse/Rom.8.28`.

---

## 7. Project Directory Additions

```
brethren-doctrine/
├── chunks/                       # NEW. JSONL output of build_chunk_payloads.py
│   ├── sermons.jsonl
│   └── sof.jsonl
├── data/
│   └── private/                  # NEW, gitignored
│       ├── stepbible/            # git submodule of STEPBible-Data
│       ├── oshb/                 # git submodule of openscriptures/morphhb
│       └── translations/         # cached JSON from ESV/NLT/api.bible
├── graph/                        # NEW
│   ├── schema.cypher             # constraints + vector indexes
│   ├── seed_concepts.cypher      # canonical Concept nodes (soteriology, etc.)
│   └── migrations/               # numbered .cypher files
├── embeddings/                   # NEW
│   ├── bootstrap_qdrant.py       # collection + sparse-vector config
│   └── reembed.py                # idempotent re-embed driver (model swap)
├── ingest/                       # NEW
│   ├── adapters/
│   │   ├── verse_loader.py
│   │   ├── token_loader.py
│   │   ├── lexicon_loader.py
│   │   ├── sermon_loader.py
│   │   ├── sof_loader.py
│   │   ├── archaeology_loader.py
│   │   └── history_loader.py
│   ├── models.py                 # Pydantic GraphRecord, with authority_level required
│   ├── upsert.py                 # single upsert_record(rec, tx) writer
│   └── outbox.py                 # dual-write reconciliation worker
├── retrieval/                    # NEW
│   ├── router.py                 # Stage 0 intent classifier
│   ├── hybrid.py                 # Stage 1+2: Qdrant query_points + RRF
│   ├── rerank.py                 # Stage 3: BGE-reranker-v2-m3
│   ├── boost.py                  # Stage 4: authority + recency
│   ├── graph_expand.py           # Stage 5: Cypher hop-1
│   └── contradictions.py         # Stage 6: opposing-stance scan
├── server/                       # NEW. FastMCP 3.x server
│   ├── main.py                   # FastMCP() + tool registrations
│   ├── tools/
│   │   ├── search_bible_interlinear.py
│   │   ├── query_sermon_graph.py
│   │   ├── get_doctrine_perspectives.py
│   │   ├── lookup_archaeology.py
│   │   └── evaluate_statement_of_faith.py
│   └── envelope.py               # uniform response envelope helpers
├── eval/                         # NEW
│   ├── gold_set.jsonl            # 30 to 50 query × expected-chunk_id pairs
│   ├── run_eval.py               # recall@10, nDCG@10, MRR
│   └── results/                  # per-run JSON + markdown report
├── docker/                       # NEW
│   ├── docker-compose.yml        # neo4j + qdrant + (optional) reranker
│   └── neo4j.conf
└── docs/
    └── TIER_2_SPEC.md            # this file
```

---

## 8. Implementation Milestones

Five milestones, dependency-ordered. S = 1 to 2 days, M = 3 to 7 days, L = 2 weeks.

| # | Name | Build | Testable when | Effort |
|---|---|---|---|---|
| M1 | Schema + dev infra | `docker-compose.yml` (neo4j:5-community + qdrant), `schema.cypher` applied, `bootstrap_qdrant.py` creates `chunks` collection with dense + sparse-IDF | `SHOW INDEXES` lists vector + B-tree + FT; `GET /collections/chunks` returns schema | S |
| M2 | Sermon + SOF E2E | `sermon_loader.py`, `sof_loader.py`, `build_chunk_payloads.py`, `embed_and_load.py`, outbox; embed all 15 `parsed/*.json` | Neo4j has every `SermonChunk` + `SOFChunk` with `authority_level` + `embedding`; Qdrant returns sane hits for "believers baptism"; smallest E2E proof | M |
| M3 | Bible + interlinear | STEPBible/OSHB/MorphGNT loaders, TBESH/TBESG glosses, ESV via API | Cypher query (c) §3 returns Hebrew/Greek under "love" for a chosen passage; gold-set scripture intents pass | M |
| M4 | Hybrid retrieval + rerank + boost | `router`, `hybrid`, `rerank`, `boost`, `graph_expand`, `contradictions`; 30-query gold set | `recall@10 ≥ 0.90`, `nDCG@10 ≥ 0.75`, p95 < 1500 ms; toggling boost moves SOF above sermons on ambiguous queries | M |
| M5 | MCP server | FastMCP 3.x, all 5 tools, uniform envelope, opaque cursor pagination, `no_results` + `ambiguous` paths populated, stdio | `tools_eval.py` (happy/no-result/ambiguous/adversarial) all envelopes valid; Claude Desktop runs `evaluate_statement_of_faith` end-to-end | M |
| M6 | Cross-doc perspectives + archaeology | Emit `PRESENTS_PERSPECTIVE_ON` from `parsed/_perspectives.json`; Open Context client for Levant bbox `[34,29,39,34]` | Query (b) §3 surfaces real disagreements; archaeology tool returns ≥3 Open Context records for "Capernaum" | S to M |
| M7 | Production hardening | Streamable-HTTP (`stateless_http=True, json_response=True`), health checks, snapshot backup, re-embed migration script | `curl` against HTTP endpoint works; snapshot restore clean; `voyage-context-3` → `voyage-4-large` swap in <30 min | S |
| M8 | Bible translation expansion (optional) | NIV/NKJV/NLT/KJV adapters via api.bible + nlt.to with diskcache | `search_bible_interlinear(reference="Rom 8:28", versions=['ESV','NIV','KJV','NLT'])` returns all four | S |

---

## 9. Cost Estimate

Numbers in 2026 USD, single-user / personal-use load.

| Line item | One-shot | Monthly |
|---|---|---|
| Embeddings: `voyage-context-3` for entire corpus (~7 to 8M tokens, per `embeddings_2026.md` §4b) | **$0** (200M-token free tier covers it ~25×) | **$0** baseline; deltas (~50 to 500k tokens / month for new sermons) also free |
| Reranker: BGE-reranker-v2-m3 self-host on CPU, in-process | $0 | **$0** |
| Vector DB: Qdrant self-host (Docker, ~200 MB at 50k vectors per `embeddings_2026.md` §4c) | $0 | **$0** locally; **$0** on Qdrant Cloud free tier (1 GB) |
| Knowledge graph: Neo4j Community (Docker) on personal machine | $0 | **$0** locally; if pushed to Aura Free, **$0** (50k-node ceiling matches our scale) |
| MCP server hosting: stdio for desktop, fly.io shared-cpu-1x if HTTP needed | $0 | **$0** stdio only; **~$2** if HTTP-hosted |
| Bible API calls: ESV / NLT / api.bible (cached) | $0 | **$0** within free tiers (5k/mo api.bible) |
| Open Context: public CC BY API | $0 | **$0** |
| Cohere reranker (only if BGE self-host fails) | n/a | **~$2** at single-digit QPS |
| Voyage AI overflow (only if free tier exhausted) | n/a | **~$1.50** worst case ($0.18/1M × 8M tokens monthly delta) |
| **Expected total** | **$0** | **$0 to $5** |

Worst case <$10/month. No LLM inference cost in this layer; Claude Max 20
covers orchestration.

---

## 10. Risks & Open Questions

### Top 5 risks

1. **Voyage AI lock-in / free-tier change.** Stamp `(model, version, dim)` on every vector; `embeddings/reembed.py` one-command swap; `BGE-M3` self-host fallback (`embeddings_2026.md` §2). Drill the swap in M7.
2. **Dual-write Neo4j/Qdrant inconsistency.** Outbox table from day one (`graphrag_2026.md` §4 step 7), idempotent `upsert_record`, nightly chunk_id reconciliation. Do not bolt the outbox on after.
3. **Reranker latency on CPU.** BGE-reranker-v2-m3 ≈130 ms / 16 pairs (`hybrid_search_rerank_2026.md` §2) → ~500 ms at K=60. Benchmark in M4; if p95 > 800 ms reranker-only, drop K_fused to 30 or move to a small GPU box.
4. **Anonymization regression at retrieval.** Server-side guard in `server/envelope.py` regex-checks outgoing `text` + `citations` for known contributor name patterns; blocks + logs. Citations anchor to `source_doc` filename only.
5. **Cypher template drift.** Templates cut hallucinations 23% → <4% (`graphrag_2026.md` §4) only if synced with schema. Every migration runs `eval/run_eval.py`; CI fails on > 5-point recall drop.

### Open questions for user

- Which historic confessions to load (Westminster / Heidelberg / 1689 LBC / Belgic / etc.)? Affects `:Confession.tradition`.
- Audio/video transcription path: Whisper self-host, Whisper API, or deferred? Required if `parsed/_pending_transcription/` enters M2.
- Open Context bbox: is Levant `[34,29,39,34]` enough, or expand to Egypt + Asia Minor for later books?
- Public-facing surface: Flutter app in scope at M5 (HTTP), or stdio + Claude Desktop only?
- Embedding spend ceiling if Voyage free tier ends: pay up to $X, or hard switch to BGE-M3?

---

## 11. Build Order: First 3 Steps

Smallest viable slice that proves the architecture E2E. No other Tier-2 work
starts until green.

### Step 1: Stand up Neo4j + Qdrant locally, apply schema (≈ half a day)

```powershell
# docker/docker-compose.yml: neo4j:5-community + qdrant/qdrant + APOC mounted
cd docker; docker compose up -d
docker exec -i neo4j cypher-shell -u neo4j -p $env:NEO4J_PASSWORD < ../graph/schema.cypher
python -m embeddings.bootstrap_qdrant
```

Done when both services start clean, all constraints + vector indexes show in
`SHOW INDEXES`, and Qdrant returns the `chunks` collection schema.

### Step 2: Ingest the existing 15 parsed/*.json into both stores (≈ 1 to 2 days)

`ingest/adapters/sermon_loader.py` + `sof_loader.py` →
`build_chunk_payloads.py` → `embed_and_load.py`.

Done when:
- Neo4j has every `SermonChunk` + `SOFChunk` node from `parsed/`, each with
  `authority_level` and `embedding`.
- Qdrant `chunks` collection has the same count of points with both dense and
  sparse vectors.
- A sanity Cypher query
  `MATCH (c:SermonChunk)-[:MENTIONS]->(k:Concept {name:'believers baptism'}) RETURN c.chunk_id, c.source_doc LIMIT 5`
  returns expected chunks from `baptism_and_communion.json`.

### Step 3: Wire hybrid retrieval + reranker behind a one-shot CLI (≈ 2 days)

`retrieval/router.py` + `hybrid.py` + `rerank.py` exposed as
`python -m retrieval.cli "what do the notes say about communion?"` returning
the §5 envelope (without graph expansion / contradictions yet; those land
in M4/M6).

Done when:
- Five sample queries (one per intent class) return non-empty
  `answer_context`, with `authority_level` populated and BGE rerank applied.
- Removing one chunk from Qdrant degrades recall in the expected way (smoke
  test that the pipeline is actually retrieving live).
- p95 latency on the sample queries logged for the M4 baseline.

After Step 3, M3 and M5 proceed in parallel on independent branches.
