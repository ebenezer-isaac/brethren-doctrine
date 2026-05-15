# GraphRAG 2026, Tier 2 Implementation Research

Research date: 2026-05-10. Scope: Tier 2 semantic + graph retrieval over sermon notes, Bible, interlinear (Hebrew/Greek + Strong's), archaeology, and church history corpora (~50k node target).

---

## 1. Recommended Architecture

**Choice: Neo4j 5.x as primary store, Qdrant as vector sidecar, with shared `record_id` keys.** Postgres+AGE+pgvector is the runner-up and the right pick if ops simplicity dominates.

Rationale:

- **Neo4j-only** (vector index built into 5.x) is operationally simplest and works to ~1-5M nodes; the `SEARCH` subclause now lets a Cypher `MATCH` be constrained by ANN hits from a vector index, which is the cleanest hybrid pattern. At 50k nodes you do not need anything more. However, multi-translation verses + Hebrew/Greek tokens + sermon chunks easily push embedding count past 500k vectors, where Qdrant outperforms Neo4j's HNSW on recall@k and tail latency.
- **Neo4j + Qdrant** is the production-validated pattern (Lettria reported 100M embeddings, sub-200ms, +20-25% accuracy vs flat RAG). The `neo4j-graphrag-python` library ships a first-party `QdrantNeo4jRetriever` so orchestration is supported, not bespoke. Cost: dual-write consistency. Solve with an outbox table (write Neo4j first inside a tx, then Qdrant; reconcile on retry).
- **Postgres + pgvector + Apache AGE** is a credible single-engine alternative. Pros: one backup, one auth model, JOINs across relational + graph + vectors, no JVM. Cons: AGE Cypher coverage lags Neo4j (no APOC, weaker planner on >3-hop traversals), pgvector HNSW is good but not Qdrant-class for filtered ANN, smaller GraphRAG ecosystem. Pick this if the team already runs Postgres and wants one engine to babysit.

For this corpus the cross-domain traversals (sermon → claim → verse → Strong's → archaeology) are 3-5 hops with property filters at every step. Neo4j's planner handles this materially better than AGE.

---

## 2. Schema Design Pattern

**Single shared ontology with namespaced labels.** Cross-domain queries fail with federated/per-domain schemas because edges that bridge domains (e.g., `MENTIONS` from sermon to verse) have to be denormalized. Use one Neo4j database, one ontology, namespace by label prefix.

### Node labels (and key properties)

- `:Verse` { verse_id (UQ), book, chapter, verse, translations: map<string,string>, authority_level: int }
- `:Token:Hebrew` / `:Token:Greek` { strongs (UQ), lemma, transliteration, morphology, gloss }
- `:SermonChunk` { chunk_id (UQ), text, themes: list, claims: list, preacher, date, authority_level }
- `:Concept` { name (UQ), aliases: list, domain }  // justification, sanctification, ecclesiology
- `:Figure` { name (UQ), era, tradition }
- `:Movement` / `:Confession` / `:Era` { name (UQ), date_range }
- `:Artifact` / `:Location` / `:Site` { name (UQ), period, lat, lon }

### Relationship types

- `(:Verse)-[:TRANSLATES_TO {translation}]->(:Verse)` cross-translation
- `(:Verse)-[:CONTAINS_TOKEN {position}]->(:Token)`
- `(:SermonChunk)-[:REFERENCES {confidence}]->(:Verse)`
- `(:SermonChunk)-[:MENTIONS {salience}]->(:Concept|:Figure|:Site)`
- `(:Source)-[:VERIFIED_BY]->(:Source)` provenance
- `(:Confession|:Sermon)-[:ALIGNS_WITH {strength}]->(:Concept)`
- `(:Concept)-[:ORIGINATES_IN]->(:Era|:Movement)`
- `(:SermonChunk|:Confession)-[:PRESENTS_PERSPECTIVE_ON {stance: "affirms"|"denies"|"qualifies"}]->(:Concept)`, load-bearing for contradiction queries

### Indexes to create on day 1

- Vector index on `:SermonChunk(embedding)`, `:Verse(embedding)`, `:Concept(embedding)` (1536 or 3072 dim).
- Full-text index on `:SermonChunk(text)`, `:Verse.translations`.
- B-tree on every `*_id`, `strongs`, `authority_level`, `name`.
- Composite (book, chapter, verse) on `:Verse`.

Authority is a **property on every retrievable node**, not a separate node, so it can be a `WHERE` filter and a re-rank weight in one expression.

---

## 3. Traversal Patterns (Cypher)

### (a) "What does the corpus say about grace alone?"

Hybrid: vector entry on `:Concept`, then global expansion across perspectives, weighted by authority.

```cypher
CALL db.index.vector.queryNodes('concept_embed', 5, $qvec) YIELD node AS c
MATCH (s)-[r:PRESENTS_PERSPECTIVE_ON]->(c)
WHERE c.name IN ['grace', 'sola gratia', 'monergism']
OPTIONAL MATCH (s)-[:REFERENCES]->(v:Verse)
RETURN s.text, r.stance, labels(s) AS source_type,
       s.authority_level AS auth, collect(DISTINCT v.verse_id) AS verses
ORDER BY auth DESC,
         CASE r.stance WHEN 'affirms' THEN 0 ELSE 1 END
LIMIT 40
```

### (b) "Show all chunks that disagree on a single theme"

Self-join on `PRESENTS_PERSPECTIVE_ON` with opposing stances; surface as pairs.

```cypher
MATCH (a)-[ra:PRESENTS_PERSPECTIVE_ON]->(c:Concept)<-[rb:PRESENTS_PERSPECTIVE_ON]-(b)
WHERE id(a) < id(b)
  AND ra.stance <> rb.stance
  AND NOT (ra.stance = 'qualifies' AND rb.stance = 'qualifies')
RETURN c.name AS theme,
       a.chunk_id, ra.stance, a.authority_level,
       b.chunk_id, rb.stance, b.authority_level
ORDER BY c.name, abs(a.authority_level - b.authority_level) DESC
```

This is the conflict surface. ArbGraph-style atomic-claim arbitration can later be layered on top: store each `claim` as its own node and run support/contradict edges, but for v1 the stance edge is sufficient.

### (c) "Which Hebrew words underlie the English word 'love' in Romans 8?"

Pure graph, no vector needed.

```cypher
MATCH (v:Verse {book:'Romans', chapter:8})-[ct:CONTAINS_TOKEN]->(t:Token)
WHERE any(tr IN keys(v.translations) WHERE v.translations[tr] CONTAINS 'love')
  AND t:Greek  // Romans is NT
RETURN v.verse, t.strongs, t.lemma, t.transliteration, t.gloss, ct.position
ORDER BY v.verse, ct.position
```

(For OT verses swap the `:Greek` label for `:Hebrew`. The label-on-token pattern lets the same query template serve both testaments.)

### Authority-aware re-rank (apply after every retriever)

```
final_score = 0.55 * cosine_sim
            + 0.25 * graph_proximity_score
            + 0.20 * (authority_level / 4.0)
```

Tunable, but keep authority as a **monotone bonus**, not a hard filter, a level-0 sermon citing a level-4 confession should still surface. Use a hard filter only when the user explicitly requests "confessional only."

### Contradiction-aware retrieval

After top-k retrieval, run query (b) restricted to the set of returned chunks. If any opposing-stance pairs exist, return them as a `disagreements: []` field in the response envelope so the LLM (and the UI) can present perspectives explicitly rather than averaging them.

---

## 4. Concrete Next Steps

1. **Scaffold the schema** as a single `schema.cypher` file with constraints + vector indexes. Commit it; treat as source of truth.
2. **Stand up Neo4j 5.x locally via Docker** (`neo4j:5-community`, plus APOC). Skip Qdrant for now, defer until embedding count > 200k or recall@10 dips below 0.85 on the eval set.
3. **Write an ingest adapter per source type** (verse loader, interlinear loader, sermon chunker, archaeology loader). Each emits a typed `GraphRecord` (Pydantic) which a single `upsert_record` function maps to Cypher `MERGE`. Authority level is set by the adapter.
4. **Use `neo4j-graphrag-python`'s `VectorCypherRetriever`** as the v1 retriever, it gives you the entry-vector + traversal pattern for free. Wrap it so the traversal Cypher is a parameterized template (template-based dropped error rates from 23% to <4% in production reports).
5. **Build a 30-query eval set** spanning the three query archetypes above plus 5 known-disagreement queries. Score every retriever change against it.
6. **Defer Microsoft GraphRAG community summarization** (Leiden hierarchical) until the corpus exceeds ~10k sermon chunks. At 50k total nodes the global-summary pattern is overkill; local + drift retrieval is enough.
7. **Add an outbox table** before introducing Qdrant. Don't bolt it on after.

---

## 5. Sources

- [Neo4j GraphRAG Python, User Guide](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html)
- [Neo4j GraphRAG Field Guide, RAG Patterns](https://neo4j.com/blog/developer/graphrag-field-guide-rag-patterns/)
- [Qdrant, GraphRAG with Qdrant and Neo4j](https://qdrant.tech/documentation/examples/graphrag-qdrant-neo4j/)
- [Qdrant case study, Lettria 100M embeddings, +20-25% accuracy](https://qdrant.tech/blog/case-study-lettria-v2/)
- [LlamaIndex, Property Graph Index docs](https://docs.llamaindex.ai/en/stable/examples/property_graph/property_graph_basic/)
- [LlamaIndex, Defining a Custom Property Graph Retriever](https://docs.llamaindex.ai/en/stable/examples/property_graph/property_graph_custom_retriever/)
- [Microsoft GraphRAG, hierarchical Leiden discussion](https://github.com/microsoft/graphrag/discussions/1128)
- [Microsoft Tech Community, pgvector + Apache AGE single engine](https://techcommunity.microsoft.com/blog/adforpostgresql/combining-pgvector-and-apache-age---knowledge-graph--semantic-intelligence-in-a-/4508781)
- [Postgres + AGE + pgvector benchmarking vs Neo4j/OpenSearch](https://codeberg.org/trisolar.faculty/postgres_pgvector_age_benchmarking)
- [ArbGraph, Conflict-Aware Evidence Arbitration (arXiv)](https://arxiv.org/html/2604.18362)
- [Contradiction Detection in RAG Systems (arXiv 2504.00180)](https://arxiv.org/abs/2504.00180)
- [GraphRAG Implementation: 12M Nodes Lessons (Particula)](https://particula.tech/blog/graphrag-implementation-enterprise-data-platform)
- [Graph RAG vs Vector RAG for Agent Memory 2026, when Neo4j beats pgvector](https://agentmarketcap.ai/blog/2026/04/07/graph-rag-vs-vector-rag-agent-memory-neo4j-pgvector)
- [deepsense.ai, Ontology-Driven KG for GraphRAG](https://deepsense.ai/resource/ontology-driven-knowledge-graph-for-graphrag/)
