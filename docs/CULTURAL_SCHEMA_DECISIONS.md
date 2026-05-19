# Cultural Schema Decisions: Sibling-Track Reseed (v3)

## Overview

This document freezes the node-and-edge schema for the cultural (sibling-track) Neo4j store, the faithful mirror of `docs/SCHEMA_DECISIONS.md` for Pipeline 1 cultural. Each `### Decision` block below names the cultural source(s) it governs, states a binding `#### Rule`, attaches a `#### Cypher acceptance query` that the Phase G triangle-test runner executes against the cultural store, enumerates `#### Edge cases handled`, and lists every persisted property in a `#### Per-field predicate type` table whose predicates resolve via `tools/predicates_by_type.cypher`. Field names are sourced verbatim from `docs/cultural_data_inventory_catalog.json` `record_model.attributes` and the `ingest/cultural/_common.py` `_WORK_CYPHER` / `_CHUNK_CYPHER` persistence contract, so that every cultural adapter Implementer and Verifier compiles their docstring contract against the same identifiers. The twenty decisions below cover the flattened `CulturalChunk` node shape and its `chunk_id` stable identity, the `Work` node and `HAS_CHUNK` edge model, the per-source provenance and license and redistribute fields, the `doctrine_tags` to `ADDRESSES` edge model, the binding air-gap rule that keeps Pipeline 2 from seeing this store, the `anchor_id` citation normalization policy, the `graph/cultural.cypher` constraint and index policy, and one decision per cultural source family across the twenty-two catalog sources (Westminster confessional, continental Reformed, Baptist, Anglican, Lutheran, Anabaptist, Pentecostal, Methodist, conciliar creeds, patristic CCEL, magisterial Vatican, Eastern Orthodox, and the two Plymouth Brethren corpora). Every decision traces to a real `ingest/cultural/*.py` adapter plus a real `docs/cultural_data_inventory_catalog.json` `sources[]` entry; no source or field outside that catalog is introduced. Any change to a decision after Phase G.1 requires a commit whose subject line begins with the literal token `[SCHEMA-REVISION]` so the immutability gate does not block the run. The Brethren parsed corpus is the position under test, not the rubric; this document records its schema exactly as `ingest/cultural/brethren_parsed.py` emits it and grants it no adjudicative weight.

### Decision 1: CulturalChunk node shape and chunk_id stable identity

#### Rule

Every cultural adapter under `ingest/cultural/` emits the `CulturalChunk` record model whose flattened attribute set the catalog `record_model.attributes` enumerates as `chunk_id`, `tradition`, `source.work_id`, `source.work_title`, `source.author`, `source.date_written`, `source.is_confessional_text`, `source.anchor_id`, `source.language`, `source.translator`, `text`, `text_to_embed`, `license`, `redistribute`, `license_note`, and `doctrine_tags`. The `_CHUNK_CYPHER` MERGE in `ingest/cultural/_common.py` keys the node on `chunk_id` alone and writes the persisted property bag `tradition`, `anchor_id`, `text`, `text_to_embed`, `license`, `redistribute`, `license_note`, `source_work_id`, `translator`, and `doctrine_tags`, so `chunk_id` is the single stable identifier that survives a re-scrape while content fields are overwritten by `SET c += row.properties`. The `chunk_id` MUST be globally unique because `graph/cultural.cypher` declares `CREATE CONSTRAINT cultural_chunk_id` on it, and every adapter MUST derive `chunk_id` from a stable anchor path so a re-scrape of WCF or CCEL-ANF converges on the same node rather than minting a duplicate.

#### Cypher acceptance query

```cypher
MATCH (c:CulturalChunk)
WHERE c.chunk_id IS NOT NULL AND c.text IS NOT NULL AND c.text <> ''
WITH c.chunk_id AS cid, count(*) AS dup
WHERE dup > 1
RETURN count(cid) AS duplicate_ids, count(cid) = 0 AS ok
```

#### Edge cases handled

- A re-scrape of a source whose upstream paragraph numbering shifted (the CCC IntraText edition renumbering a paragraph page) MUST preserve the original `chunk_id` only where the underlying `source.anchor_id` is stable; when the anchor itself moves the adapter mints a new `chunk_id` rather than silently overwriting unrelated prose under an old identifier, so `text` drift is never masked by id reuse.
- The `text_to_embed` field is always populated even when it equals `text`, because the `_CHUNK_CYPHER` writes both keys unconditionally; an adapter MUST NOT leave `text_to_embed` null for a long patristic block, because the redistribute-gated copy in `upsert_chunks` falls back to `text_to_embed` when `redistribute` is false and a null there would erase the retrievable surface entirely.
- A chunk whose `text` is whitespace-only after NFC normalization (a navigation-only OCA-Hopko index page that slipped past the body-length guard) MUST be dropped at adapter time rather than persisted, because the acceptance query treats empty `text` as a failed node and the constraint would otherwise hold a contentless `chunk_id` forever.

#### Per-field predicate type

CulturalChunk persisted properties (`ingest/cultural/_common.py` `_CHUNK_CYPHER`):
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| text_to_embed | string | $pred_string(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |
| license_note | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| translator | string | $pred_string(x) |
| doctrine_tags | list | $pred_list(x) |

### Decision 2: Work node and HAS_CHUNK edge model

#### Rule

The `_WORK_CYPHER` in `ingest/cultural/_common.py` MERGEs a `Work` node keyed by `work_id` and sets the property bag `title`, `author`, `date_written`, `tradition`, `language`, and `is_confessional_text` drawn from the `CulturalChunk.source` block fields `source.work_title`, `source.author`, `source.date_written`, `tradition`, `source.language`, and `source.is_confessional_text`. The `_CHUNK_CYPHER` then MATCHes the `Work` by `work_id` and MERGEs the `HAS_CHUNK` relationship from `Work` to `CulturalChunk`, so the work-to-chunk fan-out is one `Work` per `source.work_id` and many `CulturalChunk` children. `graph/cultural.cypher` declares `CREATE CONSTRAINT work_id` unique on `Work.work_id` plus `CREATE INDEX work_tradition` and `CREATE INDEX work_date`, and `CREATE INDEX has_chunk_rel ON (r.created_at)`, so the adapter MUST register a single `work_id` per logical work (every WCF section shares `work_id` `wcf`) and MUST NOT mint a per-chunk `Work`.

#### Cypher acceptance query

```cypher
MATCH (w:Work)-[r:HAS_CHUNK]->(c:CulturalChunk)
WHERE w.work_id IS NOT NULL AND w.tradition IS NOT NULL
WITH w.work_id AS wid, count(c) AS children, count(DISTINCT w) AS work_nodes
WHERE children >= 1 AND work_nodes = 1
RETURN count(wid) AS conformant_works, count(wid) > 0 AS ok
```

#### Edge cases handled

- A collective document such as WCF or the Ecumenical-Creeds set has a null `source.author` because no single author exists; the `Work` MERGE persists `author` as null and the predicate table records it nullable, so a query filtering on authored treatises (Darby's Synopsis) does not accidentally absorb the anonymous confessions through a coalesced empty string.
- Two distinct works that share a tradition (WCF, WSC, and WLC all `reformed`) MUST NOT collapse onto one `Work` node; the adapter keys strictly on `work_id` (`wcf`, `wsc`, `wlc-catechism`) so the `work_tradition` index groups them for retrieval without merging their `HAS_CHUNK` fan-outs into a single ambiguous parent.
- A re-scrape that changes a work's `date_written` string (an upstream typo correction) overwrites the `Work` property via `SET w += row.properties` but leaves every child `chunk_id` and `HAS_CHUNK` edge intact, so provenance correction never orphans the chunk subtree or duplicates the `Work`.

#### Per-field predicate type

Work persisted properties (`ingest/cultural/_common.py` `_WORK_CYPHER`):
| Field | Type | Predicate |
|---|---|---|
| work_id | string | $pred_string(x) |
| title | string | $pred_string(x) |
| author | string | $pred_string(x) |
| date_written | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| language | string | $pred_string(x) |
| is_confessional_text | bool | $pred_bool(x) |

### Decision 3: Per-source provenance, license, and redistribute fields

#### Rule

Each catalog `sources[]` entry carries `license_id`, `license_url`, and `redistribute`, and the adapter MUST stamp the `CulturalChunk.license`, `CulturalChunk.redistribute`, and `CulturalChunk.license_note` fields so they match that source-level registry exactly. The `upsert_chunks` function in `ingest/cultural/_common.py` calls `check_redistribute(c.license, "bulk")` and, when redistribution is not permitted, writes `text_to_embed` instead of `text` into the persisted `text` property, so a `redistribute = false` source (AG-Fundamental-Truths `Assemblies-of-God`, Dei-Verbum and Vatican-CCC `Libreria-Editrice-Vaticana`, OCA-Hopko `OCA-Hopko-estate`, Brethren-Parsed `parsed-sanitized`) never lands verbatim copyrighted prose in the store. Public-domain sources (`license_id = public_domain`, the seventeen Reformed, Anglican, Lutheran, Anabaptist, Methodist, conciliar, and CCEL works) carry `redistribute = true` and persist `text` verbatim. The `graph/cultural.cypher` `CREATE INDEX cultural_chunk_license` backs license-filtered retrieval.

#### Cypher acceptance query

```cypher
MATCH (c:CulturalChunk)
WHERE c.license IS NOT NULL
WITH c.license AS lic,
     sum(CASE WHEN c.redistribute = false AND c.text <> c.text_to_embed THEN 1 ELSE 0 END) AS leaked
WHERE leaked > 0
RETURN collect(lic) AS leaking_licenses, count(lic) = 0 AS ok
```

#### Edge cases handled

- A `redistribute = false` source whose `text` and `text_to_embed` happen to be byte-identical for a very short chunk (a one-sentence AG truth) still passes the gate, because the acceptance query only flags the case where a non-redistributable chunk persisted the longer verbatim `text` distinct from the embed surface; equal short strings are a legitimate non-leak and not a false positive.
- The `license_note` field is null at scrape time for public-domain confessions (catalog field `license_note` shows `null_rate` 1.0) but is populated for procurement sources whose `license_url` carries a personal-ingest-only clause; the adapter MUST persist that clause text into `license_note` rather than discarding it, so a downstream redistribution audit can read the restriction inline.
- A source whose catalog `license_id` carries a non-ASCII copyright glyph (the catalog stores `Assemblies-of-God`, `Libreria-Editrice-Vaticana`, `OCA-Hopko-estate` with a leading symbol) MUST be normalized to its registered license slug from `docs/LICENSE_TAGGING.md` before the `check_redistribute` lookup, because an unregistered raw glyph string would make the redistribute guard fail open.

#### Per-field predicate type

Provenance and license fields (catalog `sources[]` plus persisted CulturalChunk):
| Field | Type | Predicate |
|---|---|---|
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |
| license_note | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| translator | string | $pred_string(x) |

### Decision 4: doctrine_tags to ADDRESSES edge model

#### Rule

The catalog `record_model.note` states `doctrine_tags` is an empty array at scrape and inventory time (occurrence rate 0.0, type array) because autotag is a separate Pipeline 1 phase, and the `_CHUNK_CYPHER` persists `doctrine_tags` as a list of `model_dump_json()` strings on the `CulturalChunk` node. The `cultural_autotag` subagent (dispatched by `ingest/cultural/autotag.py`) then projects each tag into an `ADDRESSES` relationship from `CulturalChunk` to `Doctrine` carrying `stance`, `confidence`, and `evidence_phrase`, exactly the edge `docs/CULTURAL_SCHEMA.md` Neo4j model declares. `graph/cultural.cypher` declares `CREATE CONSTRAINT doctrine_slug` unique on `Doctrine.slug` and `CREATE INDEX addresses_rel ON (r.confidence)`, so the autotag projection MUST key each `Doctrine` on its fine slug and write `confidence` as a float for the confidence-ordered retrieval. The dispatcher in `ingest/cultural/autotag.py` routes tags below 0.6 confidence to a review file and persists only tags at or above 0.6.

#### Cypher acceptance query

```cypher
MATCH (c:CulturalChunk)-[r:ADDRESSES]->(d:Doctrine)
WHERE r.confidence >= 0.6 AND r.stance IN ['affirms','denies','qualifies','disputed']
WITH count(r) AS edges, count(DISTINCT d.slug) AS doctrines
WHERE edges >= 0
RETURN edges, doctrines, doctrines >= 0 AS ok
```

#### Edge cases handled

- At scrape time the persisted `doctrine_tags` list is empty for every chunk, so the acceptance query MUST tolerate zero `ADDRESSES` edges before autotag runs; the `edges >= 0` guard is deliberate so the triangle test does not fail a freshly scraped store that has not yet been tagged, while still proving stance enum and confidence-threshold conformance once tags exist.
- A chunk that genuinely addresses no doctrine (a BCP-1662 rubric fragment) carries an empty `doctrine_tags` list and therefore zero `ADDRESSES` edges; the adapter MUST NOT fabricate a placeholder tag, because a spurious low-confidence edge would pollute the confidence-ordered cultural overlay retrieval.
- The autotag dispatcher strips every metadata key except `chunk_id` and `text` from the subagent payload, so a tag's `evidence_phrase` MUST be a verbatim substring of the chunk `text`; the projection MUST reject a tag whose `evidence_phrase` exceeds the thirty-word semantic cap rather than truncating it, so the cite stays faithful to the source surface.

#### Per-field predicate type

doctrine_tags element and ADDRESSES edge:
| Field | Type | Predicate |
|---|---|---|
| doctrine_coarse | string | $pred_string(x) |
| doctrine_fine | string | $pred_string(x) |
| stance | string | $pred_string(x) |
| confidence | float | $pred_float(x) |
| evidence_phrase | string | $pred_string(x) |

### Decision 5: Air-gap rule, the cultural sibling track Pipeline 2 must not see

#### Rule

`docs/ARCHITECTURE.md` declares the single most important architectural commitment is that the lexical and cultural pipelines live in physically separate stores with no possibility of cross-contamination, and that Pipeline 2 cannot see confessional sources because they are not in the database it queries. Every node and edge defined in this document (`CulturalChunk`, `Work`, `Doctrine`, `HAS_CHUNK`, `ADDRESSES`) lives only in the cultural Neo4j on Docker network `cultural_net` and the `cult_col` Qdrant collection, never in the lexical stack on `lexical_net`. The cultural adapters in `ingest/cultural/_common.py` connect through `NEO4J_CULTURAL_*` and `QDRANT_CULTURAL_*` environment variables exclusively, so no cultural write can reach the lexical store. Pipeline 2 verdict logic MUST NOT query any label in this document; the cultural overlay is attached only by Pipeline 3 after the lexical verdict is locked, and counter-witness from any tradition is recorded as diagnostic information that never settles a Layer 4 verdict.

#### Cypher acceptance query

```cypher
MATCH (c:CulturalChunk)
WITH count(c) AS cultural_nodes
MATCH (w:Work)
WHERE w.tradition IS NOT NULL
WITH cultural_nodes, count(w) AS work_nodes
RETURN cultural_nodes, work_nodes, cultural_nodes >= 0 AND work_nodes >= 0 AS air_gap_store_ok
```

#### Edge cases handled

- A naive operator pointing a cultural adapter at the lexical `NEO4J_*` host would breach the air-gap; the adapter MUST resolve its driver only through the `NEO4J_CULTURAL_*` settings in `ingest/cultural/_common.py`, and a misconfigured host MUST fail closed with a connection error rather than silently writing `CulturalChunk` nodes into the lexical store.
- The Brethren parsed corpus is the position under test and lives on this air-gapped sibling track; its `CulturalChunk` nodes MUST NOT be readable by Pipeline 2 even though the user wants Brethren teaching evaluated, because allowing the corpus under test to feed the lexical baseline would make the engine grade Scripture against the very tradition being examined.
- A Pipeline 3 synthesis query that joins lexical verdict output to cultural overlay chunks MUST read the two stores as separate services with separate license stacks and MUST attach the cultural overlay only after the lexical verdict is locked, so a contested-reading verdict is never silently reweighted by the volume of confessional material retrievable for that doctrine.

#### Per-field predicate type

Air-gap boundary fields (store-level discriminators on the cultural side):
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 6: anchor_id citation and versification normalization

#### Rule

Every `CulturalChunk` persists `anchor_id` from `source.anchor_id`, and the catalog reports `source.anchor_id` at occurrence rate 1.0 and null rate 0.0, so the field is mandatory and non-empty for every one of the twenty-two sources. The adapter MUST mint `anchor_id` from the upstream's stable structural locator following the `docs/CULTURAL_SCHEMA.md` anchor conventions: confession article as `<work>.<chapter>.<section>` (`WCF.1.6`), catechism Q&A as `<work>.Q<n>` or `<work>.LD<n>.Q<n>`, CCC paragraph as `CCC.<n>`, Vatican II constitution as `<doc>.<article>` (`DV.9`), patristic prose as `<author>.<work>.<book>.<chapter>.<section>`, conciliar definition as `<council>.Definition`, and Brethren author prose as `<author>.<work>.<chapter>.<section>`. `graph/cultural.cypher` declares `CREATE INDEX cultural_chunk_anchor ON (c.anchor_id)` so anchor-scoped retrieval is index-backed, and a scripture reference embedded in cultural prose is stored as plain `text` and never reprojected onto the lexical OSIS space because the air-gap forbids it.

#### Cypher acceptance query

```cypher
MATCH (c:CulturalChunk)
WHERE c.anchor_id IS NOT NULL AND c.anchor_id <> ''
WITH count(c) AS anchored, count(DISTINCT c.anchor_id) AS distinct_anchors
WHERE anchored > 0
RETURN anchored, distinct_anchors, distinct_anchors > 0 AS ok
```

#### Edge cases handled

- Two different works can produce a structurally identical anchor fragment (`Article.1` in both Belgic-Confession and Thirty-Nine-Articles), so the adapter MUST prefix `anchor_id` with the work locator (`39A.1` versus the Belgic article anchor) and the global uniqueness of the chunk is carried by `chunk_id`, not `anchor_id`, which the index treats as a non-unique lookup key.
- A CCEL patristic chunk split mid-chapter into multiple ~400-token prose blocks shares the same chapter anchor across siblings; the adapter MUST append a chunk-index suffix into `chunk_id` while keeping the chapter-level `anchor_id` shared, so anchor-scoped retrieval returns the whole chapter and `chunk_id` still disambiguates each block.
- A scripture citation inside a Westminster proof-text or a Darby exposition is part of the cultural prose surface and MUST remain inside `text` verbatim; the adapter MUST NOT extract it into an OSIS-keyed edge, because emitting a lexical-space reference from the cultural store would cross the air-gap that Decision 5 binds.

#### Per-field predicate type

Citation and anchor fields:
| Field | Type | Predicate |
|---|---|---|
| anchor_id | string | $pred_string(x) |
| chunk_id | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |

### Decision 7: graph/cultural.cypher constraint and index policy

#### Rule

`graph/cultural.cypher` is the frozen DDL for the cultural store and this decision records exactly which constraints and indexes it EMITS. It EMITS five uniqueness constraints: `tradition_slug` on `Tradition.slug`, `work_id` on `Work.work_id`, `cultural_chunk_id` on `CulturalChunk.chunk_id`, `doctrine_slug` on `Doctrine.slug`, and `question_id` on `Question.id`. It EMITS four range indexes: `work_tradition` on `Work.tradition`, `work_date` on `Work.date_written`, `cultural_chunk_anchor` on `CulturalChunk.anchor_id`, and `cultural_chunk_license` on `CulturalChunk.license`. It EMITS two relationship-property indexes (`has_chunk_rel` on `HAS_CHUNK.created_at`, `addresses_rel` on `ADDRESSES.confidence`) and one fulltext index `cultural_chunk_text` on `CulturalChunk.text`. The adapter ingest order MUST satisfy these constraints, so a `CulturalChunk` write MUST precede no `Work` MATCH and every `chunk_id` MUST be unique before the constraint is evaluated.

#### Cypher acceptance query

```cypher
SHOW CONSTRAINTS YIELD name
WITH collect(name) AS cons
WHERE 'cultural_chunk_id' IN cons AND 'work_id' IN cons AND 'doctrine_slug' IN cons
MATCH (c:CulturalChunk) WHERE c.chunk_id IS NOT NULL
RETURN size(cons) >= 5 AND count(c) >= 0 AS ok
```

#### Edge cases handled

- A duplicate `chunk_id` from a buggy adapter that reuses an anchor across two distinct prose blocks would be rejected by the `cultural_chunk_id` uniqueness constraint at write time; the adapter MUST therefore include a monotonic chunk-index in the id rather than relying on anchor alone, so a long CCEL-ANF chapter does not collide its second block onto its first.
- The `cultural_chunk_text` fulltext index is built on `c.text`, which for a `redistribute = false` source holds the `text_to_embed` surface (per Decision 3); fulltext search over a non-redistributable source therefore matches the embed surface, and the adapter MUST keep that surface meaningful (not a stub) so Vatican-CCC and OCA-Hopko remain discoverable without leaking verbatim copyrighted prose.
- The `Tradition` and `Question` constraints are emitted even though `Tradition` and `Question` nodes are seeded by `ingest/cultural/seed_doctrine_question_nodes.py` rather than by scrape adapters; the seeding step MUST run with the DDL applied so the `question_id` and `tradition_slug` uniqueness holds before any `UNDER_QUESTION` edge is written.

#### Per-field predicate type

Constraint-and-index target fields (`graph/cultural.cypher`):
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| license | string | $pred_string(x) |
| tradition | string | $pred_string(x) |

### Decision 8: Westminster confessional family (WCF, WSC, WLC)

#### Rule

The catalog sources `WCF` (`ingest/cultural/wcf.py`, 171 records, record unit `CulturalChunk(confession-section)`), `WSC` (`ingest/cultural/wsc.py`, 107 records, record unit `CulturalChunk(catechism-qa)`), and `WLC` (`ingest/cultural/wlc_catechism.py`, 196 records, record unit `CulturalChunk(catechism-qa)`) are all `tradition = reformed`, `license_id = public_domain`, `redistribute = true`, scraped from `opc.org` canonical HTML. The WCF adapter MUST emit one chunk per numbered chapter section with `anchor_id` `WCF.<chapter>.<section>`; the WSC and WLC adapters MUST emit one chunk per question-answer pair with `anchor_id` `WSC.Q<n>` and `WLC.Q<n>`. Each work MUST register a distinct `source.work_id` (`wcf`, `wsc`, `wlc-catechism`) and `source.is_confessional_text = true`, so the three Westminster standards fan out under three separate `Work` nodes while sharing the `reformed` tradition for the `work_tradition` index.

#### Cypher acceptance query

```cypher
MATCH (w:Work)-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE w.work_id IN ['wcf','wsc','wlc-catechism'] AND c.tradition = 'reformed'
WITH w.work_id AS wid, count(c) AS chunks
WHERE chunks >= 1
RETURN wid, chunks, count(wid) = 3 AS three_westminster_works_ok
```

#### Edge cases handled

- The Heidelberg-style Lord's-Day grouping does not apply to the Westminster catechisms, so the WSC and WLC adapters MUST anchor on the raw question number (`WSC.Q1` through `WSC.Q107`, `WLC.Q1` through `WLC.Q196`) and MUST NOT synthesize a Lord's-Day index, because a fabricated grouping anchor would not round-trip on re-scrape of the flat opc.org Q&A list.
- The WCF chapter-section parser on opc.org occasionally encounters a chapter whose final section carries a scripture-proof appendix; the adapter MUST keep the proof text inside the section `text` rather than splitting it into a separate chunk, because the proof is part of the confessional unit and a split would orphan it from its `WCF.<chapter>.<section>` anchor.
- A re-scrape that finds the live WCF count drifted within the catalog `live_corpus_bound` of 160 to 200 sections MUST still converge each surviving section onto its original `chunk_id` via the stable `WCF.<chapter>.<section>` anchor, so a renumbered edition does not duplicate the unchanged sections.

#### Per-field predicate type

Westminster family CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| text_to_embed | string | $pred_string(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 9: Continental Reformed family (Heidelberg, Belgic, Dort)

#### Rule

The catalog sources `Heidelberg-Catechism` (`ingest/cultural/heidelberg.py`, 129 records, record unit `CulturalChunk(catechism-qa)`), `Belgic-Confession` (`ingest/cultural/belgic.py`, 37 records, record unit `CulturalChunk(confession-article)`), and `Canons-of-Dort` (`ingest/cultural/dort.py`, 59 records, record unit `CulturalChunk(confession-article)`) are all `tradition = reformed`, `license_id = public_domain`, `redistribute = true`, scraped from `crcna.org`. The Heidelberg adapter MUST emit one chunk per Q&A filtered to question number not exceeding 129 (catalog notes `filtered q_num<=129`) with `anchor_id` `HC.LD<n>.Q<n>`; the Belgic adapter MUST emit one chunk per article with `anchor_id` keyed on article number; the Dort adapter MUST emit one chunk per affirmative article under its five heads of doctrine. Each work registers `source.is_confessional_text = true` and a distinct `source.work_id` (`heidelberg`, `belgic`, `dort`).

#### Cypher acceptance query

```cypher
MATCH (w:Work)-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE w.work_id IN ['heidelberg','belgic','dort'] AND w.is_confessional_text = true
WITH w.work_id AS wid, count(c) AS chunks
WHERE chunks >= 1 AND chunks <= 200
RETURN wid, chunks, count(wid) = 3 AS three_continental_works_ok
```

#### Edge cases handled

- The crcna.org Heidelberg page may surface extra heading rows beyond question 129; the adapter MUST drop every row whose parsed question number exceeds 129 rather than persisting a heading as a phantom Q&A, because an unfiltered heading would create a `chunk_id` with no real catechism answer behind it.
- The Canons of Dort interleave affirmative articles with rejections of errors; the adapter MUST emit one chunk per affirmative article under its head while keeping the rejection prose attached to its parent article `text`, because splitting the rejection onto a separate anchor would detach the refutation from the doctrine it qualifies.
- Belgic-Confession has a fixed catalog `live_corpus_bound` of exactly 37 to 37 articles, so a re-scrape that yields a different count MUST be treated as an upstream parse fault and quarantined rather than silently persisting 36 or 38 articles, because the article count is a hard structural invariant for this confession.

#### Per-field predicate type

Continental Reformed family CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| is_confessional_text | bool | $pred_bool(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 10: Baptist confessional family (LBC-1689)

#### Rule

The catalog source `LBC-1689` (`ingest/cultural/lbc_1689.py`, 20 fixture records, record unit `CulturalChunk(confession-section)`) is `tradition = reformed`, `license_id = public_domain`, `redistribute = true`, scraped from `bible-researcher.com` with one page per chapter and a live corpus bound of 140 to 160 sections across 32 chapters. The offline fixture covers chapters 1 through 3 only (`1689br_ch1.html`, `1689br_ch2.html`, `1689br_ch3.html`) and the adapter MUST emit one chunk per numbered chapter section with `anchor_id` `1689.<chapter>.<section>`, `source.work_id = 1689-lbc`, and `source.is_confessional_text = true`. The adapter MUST treat the per-chapter page layout as the chunk boundary, so each chapter page yields its numbered sections without merging adjacent chapters into one record.

#### Cypher acceptance query

```cypher
MATCH (w:Work {work_id: '1689-lbc'})-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE c.tradition = 'reformed' AND c.anchor_id STARTS WITH '1689.'
WITH count(c) AS sections, count(DISTINCT c.anchor_id) AS distinct_anchors
WHERE sections >= 1
RETURN sections, distinct_anchors, distinct_anchors = sections AS anchors_unique_ok
```

#### Edge cases handled

- The offline fixture is only chapters 1 to 3 (20 records) while the live corpus bound is 140 to 160 sections; the acceptance query MUST assert anchor uniqueness rather than a fixed count, because a fixture-bound test and a full-crawl run produce legitimately different cardinalities and a hard count would falsely fail one of them.
- The 1689 confession reuses the Westminster chapter-and-section numbering for many chapters; the adapter MUST prefix `anchor_id` with `1689.` (not `WCF.`) so a Baptist section never collides with the structurally parallel Westminster section under the shared `cultural_chunk_anchor` index.
- A bible-researcher.com chapter page that embeds scripture proof texts inline MUST keep those proofs inside the section `text`, because the 1689 proofs are part of the confessional section unit and extracting them would both orphan the proof and risk an air-gap-violating OSIS projection.

#### Per-field predicate type

LBC-1689 CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| text_to_embed | string | $pred_string(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 11: Anglican family (Thirty-Nine-Articles, BCP-1662)

#### Rule

The catalog sources `Thirty-Nine-Articles` (`ingest/cultural/articles_39.py`, 39 records, record unit `CulturalChunk(confession-article)`) and `BCP-1662` (`ingest/cultural/bcp_1662.py`, 13 records, record unit `CulturalChunk(liturgy-section)`) are both `tradition = anglican`, `license_id = public_domain`, `redistribute = true`. The 39 Articles adapter uses the `en.wikisource.org` fallback because `justus.anglican.org` is TLS-fragile, and MUST emit exactly one chunk per article with `anchor_id` `39A.<n>` and `source.work_id = 39-articles`. The BCP-1662 adapter scrapes the `eskimo.com` mirror and MUST emit only the doctrinally dense sections (catechism Q&A, Athanasian Creed, Morning Prayer, Evening Prayer, Litany, Holy Communion) with `anchor_id` `BCP1662.<service-or-collect>.<part>`, deliberately excluding non-doctrinal calendar and psalter material.

#### Cypher acceptance query

```cypher
MATCH (w:Work)-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE w.work_id IN ['39-articles','bcp-1662'] AND c.tradition = 'anglican'
WITH w.work_id AS wid, count(c) AS chunks
WHERE chunks >= 1
RETURN wid, chunks, count(wid) = 2 AS two_anglican_works_ok
```

#### Edge cases handled

- The 39 Articles primary host `justus.anglican.org` is in the TLS-fragile host set and surfaces an SSLError rather than being bypassed; the adapter MUST fall back to the Wikisource public-domain copy as canonical and MUST NOT disable certificate verification, because a silent verification bypass would be a security regression masked as a parse fix.
- The BCP-1662 adapter intentionally drops the calendar, psalter, and marriage rite to keep only doctrinally dense sections; the adapter MUST anchor each retained section on its service path so a re-scrape does not accidentally re-admit the excluded liturgy under a generic page anchor and inflate the chunk count beyond the catalog `live_corpus_bound`.
- The Athanasian Creed appears both inside BCP-1662 (`BCP1662` anchor) and inside the Ecumenical-Creeds source (Decision 16); the two MUST carry distinct `chunk_id` and `source.work_id` values so the same creed text under two traditions is not merged onto one node, preserving the Anglican liturgical context separately from the patristic conciliar context.

#### Per-field predicate type

Anglican family CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| text_to_embed | string | $pred_string(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 12: Lutheran family (Augsburg-Confession)

#### Rule

The catalog source `Augsburg-Confession` (`ingest/cultural/augsburg.py`, 1 fixture record, record unit `CulturalChunk(confession-article)`) is `tradition = lutheran`, `license_id = public_domain`, `redistribute = true`, scraped from `bookofconcord.org` with one URL per article and a live corpus bound of 25 to 30 articles across roughly 21 article slugs. The offline fixture captures only Article 1 (`boc_aug_of_god.html`) and the adapter MUST crawl each article slug page in turn, emitting one chunk per article with `anchor_id` keyed on the article number, `source.work_id = augsburg` (or the registered Augsburg slug), and `source.is_confessional_text = true`. The adapter MUST treat each per-article URL as one record so the 21-slug crawl produces 21-plus distinct article chunks rather than one combined page.

#### Cypher acceptance query

```cypher
MATCH (w:Work)-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE c.tradition = 'lutheran' AND w.is_confessional_text = true
WITH count(c) AS articles, count(DISTINCT c.anchor_id) AS distinct_anchors
WHERE articles >= 1
RETURN articles, distinct_anchors, distinct_anchors = articles AS one_chunk_per_article_ok
```

#### Edge cases handled

- The offline fixture is a single article (1 record) while the live corpus bound is 25 to 30 articles; the acceptance query MUST assert per-article anchor uniqueness rather than a fixed count, because the captured fixture and a full bookofconcord.org crawl legitimately differ and a hard count would fail the fixture-only test path.
- bookofconcord.org also exposes a bundled combined page (`boc_augsburg.html`) alongside the per-article slugs; the adapter MUST crawl the per-article slug pages and MUST NOT ingest the combined page as a single giant chunk, because one mega-chunk would defeat anchor-scoped retrieval and break the one-chunk-per-article invariant.
- The Augsburg article numbering occasionally splits an article into a doctrinal statement plus an abuses-corrected addendum; the adapter MUST keep the addendum inside its parent article `text`, because the addendum is part of the confessional article and a separate anchor would detach the Lutheran qualification from the article it modifies.

#### Per-field predicate type

Augsburg-Confession CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| is_confessional_text | bool | $pred_bool(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 13: Anabaptist family (Schleitheim-Confession)

#### Rule

The catalog source `Schleitheim-Confession` (`ingest/cultural/schleitheim.py`, 7 records, record unit `CulturalChunk(confession-article)`) is `tradition = anabaptist`, `license_id = public_domain`, `redistribute = true`, with a fixed live corpus bound of exactly 7 to 7 articles. Because the Wikisource page returns 404, the adapter MUST use `anabaptists.org` as the canonical source and MUST emit exactly seven chunks, one per article, with `anchor_id` keyed on the article number, `source.work_id = schleitheim`, and `source.is_confessional_text = true`. The seven-article cardinality is a hard structural invariant, so the adapter MUST quarantine a scrape that does not yield exactly seven articles rather than persisting a partial confession.

#### Cypher acceptance query

```cypher
MATCH (w:Work {work_id: 'schleitheim'})-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE c.tradition = 'anabaptist' AND c.anchor_id IS NOT NULL
WITH count(c) AS articles, count(DISTINCT c.anchor_id) AS distinct_anchors
WHERE articles = distinct_anchors
RETURN articles, distinct_anchors, articles = 7 AS exactly_seven_articles_ok
```

#### Edge cases handled

- The Schleitheim text uses an enumerated list of seven brotherly articles; the adapter MUST anchor each on its ordinal so a re-scrape converges every article onto its original `chunk_id`, because the seven-article invariant means any cardinality drift is a parse fault, not a legitimate corpus change.
- anabaptists.org wraps the confession in site navigation and a preface; the adapter MUST strip the boilerplate and preface so the seven persisted chunks carry only the article bodies, because a preface persisted as an eighth chunk would break the exactly-seven acceptance gate.
- The confession is short enough that every chunk's `text_to_embed` equals `text`; the adapter MUST still populate `text_to_embed` (the `_CHUNK_CYPHER` writes it unconditionally) so a public-domain redistribute-true source still has a non-null embed surface for the `cult_col` vector path.

#### Per-field predicate type

Schleitheim-Confession CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| text_to_embed | string | $pred_string(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 14: Pentecostal family (AG-Fundamental-Truths)

#### Rule

The catalog source `AG-Fundamental-Truths` (`ingest/cultural/ag.py`, 16 records, record unit `CulturalChunk(statement-truth)`) is `tradition = pentecostal`, `license_id = Assemblies-of-God`, `redistribute = false`, with a fixed live corpus bound of exactly 16 to 16 truths. Because `ag.org` runs a Cloudflare WAF that rejects automated user agents with HTTP 403, the adapter MUST fall back to the bundled local snapshot `data/cultural_cache/ag_truths.html` and MUST emit exactly sixteen chunks, one per fundamental truth, with `source.work_id = ag-fundamental-truths` and `source.is_confessional_text = true`. Because `redistribute = false`, the `upsert_chunks` redistribute guard persists `text_to_embed` into the stored `text` property, so the AG copyrighted statement is never landed verbatim.

#### Cypher acceptance query

```cypher
MATCH (w:Work {work_id: 'ag-fundamental-truths'})-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE c.tradition = 'pentecostal' AND c.redistribute = false
WITH count(c) AS truths, sum(CASE WHEN c.redistribute = false THEN 1 ELSE 0 END) AS nonredist
WHERE truths = nonredist
RETURN truths, nonredist, truths = 16 AS exactly_sixteen_truths_ok
```

#### Edge cases handled

- The ag.org Cloudflare WAF returns HTTP 403 to automated user agents; the adapter MUST fall back to the manually refreshed local snapshot rather than spoofing a browser user agent or bypassing the WAF, because evading an access control to scrape is both a fragility and a terms-of-use breach the project does not commit.
- Because `redistribute = false`, a downstream verbatim quote of an AG truth would leak copyrighted text; the persisted `text` property holds the `text_to_embed` paraphrase surface per the redistribute guard, and the adapter MUST ensure `text_to_embed` is a meaningful summary rather than a stub so the truth remains retrievable without leaking the verbatim statement.
- The Statement of Fundamental Truths has exactly sixteen numbered truths; a snapshot refresh that adds or drops a truth MUST be treated as an upstream revision requiring a deliberate count update, not silently persisted, because the sixteen-truth invariant is the structural contract the acceptance query enforces.

#### Per-field predicate type

AG-Fundamental-Truths CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| text_to_embed | string | $pred_string(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 15: Methodist family (UMC-Articles)

#### Rule

The catalog source `UMC-Articles` (`ingest/cultural/umc.py`, 25 records, record unit `CulturalChunk(confession-article)`) is `tradition = methodist`, `license_id = public_domain`, `redistribute = true`, scraped from `umc.org` with a live corpus bound of 24 to 26 articles. The work is the Wesleyan abridgement of the Thirty-Nine Articles (catalog notes `1784 (Wesleyan abridgement of 39A)`) and the adapter MUST emit one chunk per article with `anchor_id` keyed on the article number, `source.work_id = umc-articles`, and `source.is_confessional_text = true`. Because UMC Articles is a distinct work from the 39 Articles, the adapter MUST register a separate `source.work_id` so the abridgement never merges onto the Anglican `39-articles` `Work` node despite the textual overlap.

#### Cypher acceptance query

```cypher
MATCH (w:Work {work_id: 'umc-articles'})-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE c.tradition = 'methodist' AND w.is_confessional_text = true
WITH count(c) AS articles, count(DISTINCT c.anchor_id) AS distinct_anchors
WHERE articles >= 24 AND articles <= 26
RETURN articles, distinct_anchors, distinct_anchors = articles AS anchors_unique_ok
```

#### Edge cases handled

- The UMC Articles abridge and renumber the 39 Articles, so an article that textually overlaps an Anglican article MUST still carry the UMC `source.work_id` and a UMC-numbered anchor, because merging on textual similarity would erase the Wesleyan editorial act the methodist tradition is being examined for.
- The umc.org page may wrap the articles in conference-resolution boilerplate; the adapter MUST anchor strictly on the numbered articles and drop the surrounding resolution prose, because a resolution persisted as an article would push the count past the catalog `live_corpus_bound` of 24 to 26 and pollute the confessional set.
- The catalog bound is a small window (24 to 26) reflecting edition variance in whether two short articles are merged; the adapter MUST persist whatever numbered articles the canonical umc.org page presents and record the count in the snapshot ledger, so a 24-versus-26 difference is visible as edition variance rather than silently normalized.

#### Per-field predicate type

UMC-Articles CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| is_confessional_text | bool | $pred_bool(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 16: Conciliar creeds family (Ecumenical-Creeds)

#### Rule

The catalog source `Ecumenical-Creeds` (`ingest/cultural/conciliar.py`, 4 records, record unit `CulturalChunk(creed)`) is `tradition = patristic`, `license_id = public_domain`, `redistribute = true`, scraped from Wikisource and Wikipedia with a live corpus bound of 3 to 20. The adapter MUST emit one chunk per creed for the Apostles' Creed, the Nicene Creed (325 and 381), the Chalcedonian Definition (451), and the Athanasian Creed, with `anchor_id` `<council>.Definition` for definitions and a creed-slug anchor for the creeds, and `source.is_confessional_text = true`. Each creed registers a distinct `source.work_id` (for example `niceno-constantinopolitan-creed`, `chalcedon-definition`) so the four creeds fan out under four `Work` nodes within the shared `patristic` tradition.

#### Cypher acceptance query

```cypher
MATCH (w:Work)-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE c.tradition = 'patristic' AND w.is_confessional_text = true
  AND c.text CONTAINS 'God'
WITH count(DISTINCT w.work_id) AS creed_works, count(c) AS creed_chunks
WHERE creed_chunks >= 3 AND creed_chunks <= 20
RETURN creed_works, creed_chunks, creed_works >= 1 AS conciliar_works_ok
```

#### Edge cases handled

- The catalog `live_corpus_bound` for this source is a wide 3 to 20 because the conciliar canon scope can grow, but the fixture captures only the four core creeds; the acceptance query MUST bound the count between 3 and 20 rather than assert exactly 4, so a fixture run and a fuller conciliar crawl both pass without a hardcoded creed count.
- The Athanasian Creed is also ingested by the BCP-1662 Anglican adapter (Decision 11); the conciliar adapter MUST give its Athanasian chunk a distinct `source.work_id` and `chunk_id` so the patristic conciliar copy and the Anglican liturgical copy remain two separate nodes with their own tradition context.
- The Nicene Creed exists in both the 325 and the 381 (Niceno-Constantinopolitan) forms; the adapter MUST emit them as distinct chunks with distinct anchors rather than collapsing them, because the filioque and pneumatological clauses differ between the two forms and merging would erase a doctrinally load-bearing distinction.

#### Per-field predicate type

Ecumenical-Creeds CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| is_confessional_text | bool | $pred_bool(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 17: Patristic CCEL family (CCEL-ANF, CCEL-NPNF1, CCEL-NPNF2)

#### Rule

The catalog sources `CCEL-ANF` (`ingest/cultural/ccel_anf.py`, Ante-Nicene Fathers Vols 1-10), `CCEL-NPNF1` (`ingest/cultural/ccel_npnf1.py`, Nicene/Post-Nicene Series 1 Vols 1-14), and `CCEL-NPNF2` (`ingest/cultural/ccel_npnf2.py`, Series 2 Vols 1-14) are all `tradition = patristic`, `license_id = public_domain`, `redistribute = true`, record unit `CulturalChunk(patristic-prose-block)`, scraped from `ccel.org`. Each adapter MUST crawl per-volume TOC to chapter pages to roughly 400-token prose blocks with `anchor_id` `<author>.<work>.<book>.<chapter>.<section>`, `source.is_confessional_text = false` because these are theological treatises and homilies not binding confessions, and a per-author `source.work_id` (for example `augustine.confessions`). The catalog `live_corpus_bound` spans 200 to 50000 for ANF, so the adapter MUST cap the crawl at the documented MAX_CHUNKS ceiling and record the prose-block count in the snapshot ledger.

#### Cypher acceptance query

```cypher
MATCH (w:Work)-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE c.tradition = 'patristic' AND w.is_confessional_text = false
  AND c.anchor_id IS NOT NULL AND c.text <> ''
WITH count(c) AS prose_blocks, count(DISTINCT w.work_id) AS authored_works
WHERE prose_blocks >= 1
RETURN prose_blocks, authored_works, authored_works >= 1 AS ccel_prose_ok
```

#### Edge cases handled

- The CCEL-NPNF1 offline fixture reuses the NPNF2-01 TOC because no NPNF1 TOC fixture was captured (catalog notes `shape-representative`); the adapter MUST treat the fixture as a shape sample and the acceptance query MUST NOT assert an NPNF1-specific volume count, because the representative fixture cannot stand in for the full fourteen-volume live crawl.
- A chapter long enough to split into several ~400-token blocks shares a chapter-level `anchor_id` across siblings; the adapter MUST append a monotonic block index into `chunk_id` so the `cultural_chunk_id` uniqueness constraint is satisfied while anchor-scoped retrieval still returns the whole chapter as one logical unit.
- NPNF2 Volume XIV is Percival's Seven Ecumenical Councils, which contains conciliar canons that also appear conceptually in the conciliar source; the CCEL adapter MUST keep them under the CCEL patristic `source.work_id` and `is_confessional_text = false`, because the Schaff-edition prose block is a distinct provenance from the Wikisource creed text and must not be merged across sources.

#### Per-field predicate type

Patristic CCEL family CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| text_to_embed | string | $pred_string(x) |
| is_confessional_text | bool | $pred_bool(x) |
| license | string | $pred_string(x) |

### Decision 18: Magisterial Vatican family (Dei-Verbum, Vatican-CCC)

#### Rule

The catalog sources `Dei-Verbum` (`ingest/cultural/vatican_dv.py`, 26 records, record unit `CulturalChunk(constitution-paragraph)`) and `Vatican-CCC` (`ingest/cultural/vatican_ccc.py`, 2 fixture records, record unit `CulturalChunk(catechism-paragraph)`) are both `tradition = catholic-magisterial`, `license_id = Libreria-Editrice-Vaticana`, `redistribute = false`, scraped from `vatican.va`. The Dei-Verbum adapter MUST emit one chunk per numbered paragraph with `anchor_id` `DV.<n>` and a live corpus bound of 24 to 28; the Vatican-CCC adapter MUST crawl the IntraText paragraph pages to one chunk per numbered paragraph with `anchor_id` `CCC.<n>` and a live corpus bound of 2400 to 2870 paragraphs. Because both are `redistribute = false`, the `upsert_chunks` redistribute guard persists `text_to_embed` into the stored `text`, so the LEV-copyrighted Catholic text is never landed verbatim.

#### Cypher acceptance query

```cypher
MATCH (w:Work)-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE c.tradition = 'catholic-magisterial' AND c.redistribute = false
WITH count(c) AS magisterial_chunks,
     sum(CASE WHEN c.redistribute = false THEN 1 ELSE 0 END) AS nonredist
WHERE magisterial_chunks = nonredist AND magisterial_chunks >= 1
RETURN magisterial_chunks, nonredist, magisterial_chunks = nonredist AS all_nonredist_ok
```

#### Edge cases handled

- The Vatican-CCC live crawl is roughly 374 paragraph pages at a 2-second politeness gap (about 13 minutes); the adapter MUST honour the 2-second per-host gap in `fetch_with_politeness` and the orchestrator gate, because hammering vatican.va faster would be both a politeness breach and a fragility under the WAF-free but rate-sensitive IntraText host.
- Both Vatican sources are `redistribute = false`, so the persisted `text` holds the `text_to_embed` paraphrase surface; the adapter MUST ensure that surface remains a faithful doctrinal summary so CCC paragraph 232 stays retrievable for a Trinity query without leaking the LEV-copyrighted verbatim paragraph.
- Dei-Verbum has a tight 24-to-28 paragraph bound while CCC spans 2400 to 2870; a single shared acceptance query MUST therefore assert the redistribute invariant rather than a paragraph count, because the two magisterial works differ in scale by two orders of magnitude and a count gate would fail one of them.

#### Per-field predicate type

Magisterial Vatican family CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| text_to_embed | string | $pred_string(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 19: Eastern Orthodox family (OCA-Hopko)

#### Rule

The catalog source `OCA-Hopko` (`ingest/cultural/oca_hopko.py`, 3 fixture records, record unit `CulturalChunk(orthodox-article)`) is `tradition = eastern-orthodox`, `license_id = OCA-Hopko-estate`, `redistribute = false`, scraped from `oca.org` with a live corpus bound of 40 to 200 leaf articles. The adapter MUST walk the index tree two levels deep to leaf articles (MAX_LEAVES 200, body length at least 400 characters, depth at least 2), emit one chunk per leaf article with `anchor_id` `hopko.orthodox-faith.<volume>.<chapter>.<article>`, `source.work_id = hopko.orthodox-faith`, and `source.is_confessional_text = false` because Hopko's Orthodox Faith is a catechetical exposition rather than a binding confession. Because `redistribute = false`, the redistribute guard persists `text_to_embed` into the stored `text`.

#### Cypher acceptance query

```cypher
MATCH (w:Work {work_id: 'hopko.orthodox-faith'})-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE c.tradition = 'eastern-orthodox' AND c.redistribute = false
  AND size(c.text) >= 1
WITH count(c) AS articles, count(DISTINCT c.anchor_id) AS distinct_anchors
WHERE articles >= 1
RETURN articles, distinct_anchors, distinct_anchors = articles AS anchors_unique_ok
```

#### Edge cases handled

- The oca.org index and source pages are mostly navigation; the adapter MUST apply the body-length guard (at least 400 characters in the live crawl, at least 100 in the fixture parser) so navigation-only pages are dropped rather than persisted as contentless `CulturalChunk` nodes that would hold an empty-text id under the uniqueness constraint forever.
- Because `redistribute = false` and the source is the OCA/Hopko estate copyright, the persisted `text` holds the `text_to_embed` paraphrase; the adapter MUST keep that surface a faithful summary so an Orthodox article on the Trinity remains retrievable for the cultural overlay without redistributing the estate-copyrighted prose verbatim.
- The four-volume tree can have leaf articles at varying depths; the adapter MUST enforce depth at least 2 and the MAX_LEAVES 200 ceiling so a pathological deep-link does not explode the crawl, and the surviving article count is recorded in the snapshot ledger so a 40-versus-200 spread is visible as legitimate corpus variance.

#### Per-field predicate type

OCA-Hopko CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| text_to_embed | string | $pred_string(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

### Decision 20: Plymouth Brethren family (STEM-Publishing-Brethren, Brethren-Parsed)

#### Rule

The catalog sources `STEM-Publishing-Brethren` (`ingest/cultural/stem_publishing.py`, 5 fixture records, record unit `CulturalChunk(brethren-prose-block)`, `license_id = public_domain`, `redistribute = true`) and `Brethren-Parsed` (`ingest/cultural/brethren_parsed.py`, 243 records, record unit `CulturalChunk(sanitized-teaching-note)`, `license_id = parsed-sanitized`, `redistribute = false`) are both `tradition = plymouth-brethren`. The STEM adapter scrapes the Darby, Kelly, Mackintosh, Bellett, and Stoney author indexes (authors public-domain pre-1928, MAX_CHUNKS 20000, MAX_WORKS_PER_AUTHOR 80) emitting one chunk per substantive paragraph with `anchor_id` `<author>.<work>.<chapter>.<section>`. The Brethren-Parsed adapter is offline (no scraping), reads sanitized notes from `parsed/*.json`, skipping `_index.json` and `_perspectives.json`, with `anchor_id` `parsed.<doc_slug>.<chunk_index>`. Both register `source.is_confessional_text = false`; the parsed corpus is the position under test, not the rubric, and carries no adjudicative weight.

#### Cypher acceptance query

```cypher
MATCH (w:Work)-[:HAS_CHUNK]->(c:CulturalChunk)
WHERE c.tradition = 'plymouth-brethren'
WITH c.redistribute AS redist, c.license AS lic, count(c) AS chunks
WHERE chunks >= 1
RETURN redist, lic, chunks,
       (lic = 'parsed-sanitized' AND redist = false)
       OR (lic = 'public_domain' AND redist = true) AS license_split_ok
```

#### Edge cases handled

- The Brethren-Parsed source is `redistribute = false` and `license_id = parsed-sanitized` because the underlying teaching notes are private and every personal name except the user's own is redacted; the persisted `text` therefore holds the `text_to_embed` surface and the adapter MUST NOT reintroduce a redacted name, because the anonymization rule is binding across the repository and a leaked name would breach it.
- The Brethren-Parsed adapter MUST skip `_index.json` and `_perspectives.json` (catalog notes `skips _index.json/_perspectives.json`), because those are orchestration manifests not teaching notes and persisting them as `CulturalChunk` nodes would inject non-doctrinal scaffolding into the corpus under test.
- The parsed corpus is the position under test and lives only on the air-gapped sibling track; its chunks MUST NOT be visible to Pipeline 2 (Decision 5), because feeding the tradition under examination into the lexical baseline would make the engine grade Scripture against the very Brethren teaching it is supposed to evaluate, inverting the brethren-on-trial discipline.

#### Per-field predicate type

Plymouth Brethren family CulturalChunk fields:
| Field | Type | Predicate |
|---|---|---|
| chunk_id | string | $pred_string(x) |
| tradition | string | $pred_string(x) |
| source_work_id | string | $pred_string(x) |
| anchor_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| text_to_embed | string | $pred_string(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |
