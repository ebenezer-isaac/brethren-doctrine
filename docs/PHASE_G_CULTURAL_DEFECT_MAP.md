# Phase G Cultural Defect Map

Static, read-only pre-audit of the 22 cultural adapters plus the shared persistence path,
mirroring the lexical PHASE_D_EDGE_PERF_MANIFEST / JOINKEY_AUDIT / TIERA_PREVERIFICATION work
so Phase G fixes fan out with zero serial rediscovery. No ingest was run; no store was touched.
Verdicts are derived from the bytes of the adapters, `ingest/cultural/_common.py`,
`ingest/cultural/run.py`, `ingest/cultural/autotag.py`, `ingest/cultural/seed_doctrine_question_nodes.py`,
`graph/cultural.cypher`, `ingest/license_guard.py`, `ingest/models.py`,
`docs/cultural_data_inventory_catalog.json`, and `docs/CULTURAL_SCHEMA_DECISIONS.md`.

Defect classes (lexical-proven):

- EDGE-PERF: a relationship MERGE/CREATE whose endpoint MATCH is unlabeled or not backed by a
  constraint/index, producing AllNodesScan or LabelScan+Filter at reseed scale.
- JOIN-KEY: a consumer-side match key whose value/type/format does not equal what the producing
  side writes, so the edge silently resolves zero.
- CATALOG-RECON: catalog `total_records` is a naive line/element count rather than the adapter's
  faithful `record_unit`, so a tier-A count gate false-fails.
- ORDERING: producer-before-consumer hazard in the dispatch order.
- CONTRACT: a CULTURAL_SCHEMA_DECISIONS clause the adapter or shared path does not satisfy.

## Shared-path findings (apply to ALL 22 adapters)

The cultural store has exactly two edge writers and one tag computation:

1. `ingest/cultural/_common.py` `_CHUNK_CYPHER`: `MERGE (c:CulturalChunk {chunk_id})` then
   `MATCH (w:Work {work_id: row.work_id})` then `MERGE (w)-[:HAS_CHUNK]->(c)`.
   Both endpoints are LABEL-SCOPED and key-backed: `cultural_chunk_id` UNIQUE on
   `CulturalChunk.chunk_id` and `work_id` UNIQUE on `Work.work_id` both exist in
   `graph/cultural.cypher`. `_WORK_CYPHER` `MERGE (w:Work {work_id})` is likewise constraint-backed.
   HAS_CHUNK is **EDGE-PERF CLEAN** for every adapter. This is NOT the lexical dead/quadratic
   `_common` pattern: it is live, labeled, and index-backed.
2. `ingest/cultural/seed_doctrine_question_nodes.py`: `MERGE (d:Doctrine {slug})`,
   `MERGE (q:Question {id})`, then `MATCH (d:Doctrine {slug}),(q:Question {id})
   MERGE (d)-[:UNDER_QUESTION]->(q)`. Both endpoints LABEL-SCOPED and backed by
   `doctrine_slug` and `question_id` UNIQUE constraints. **EDGE-PERF CLEAN.**
3. `ingest/cultural/autotag.py` only computes `DoctrineTag` objects and copies them onto chunks.
   It does NOT write any edge. There is **no ADDRESSES edge writer anywhere in the codebase**.

### G-SHARED-1 (CONTRACT, CRITICAL, MUST-ESCALATE-adjacent but clear code bug) - dead redistribute guard

`ingest/cultural/_common.py:138`:

```python
redistribute_ok = check_redistribute(c.license, "bulk")
text_value = c.text if redistribute_ok else c.text_to_embed
```

`ingest/license_guard.check_redistribute` returns `RedistributeResult` = a non-empty dict
`{"allowed": bool, "reason": str}`. A non-empty dict is ALWAYS truthy in Python, so
`if redistribute_ok` is True for every license, including the copyrighted ones. Proven
statically by execution of the pure function: `bool(check_redistribute("©Assemblies-of-God","bulk"))`
is `True` even though `allowed` is `False`.

Effect: the verbatim copyrighted `text` is persisted for EVERY `redistribute=false` source
(AG-Fundamental-Truths, Dei-Verbum, Vatican-CCC, OCA-Hopko, Brethren-Parsed). This is the exact
cultural analog of the lexical dead-guard `_common` defect. It directly fails the Decision 3
acceptance query (`leaked > 0`) and the Decision 14 / 18 / 19 / 20 redistribute acceptance
queries the moment those sources land. Faithful fix: branch on the dict member, e.g.
`redistribute_ok = check_redistribute(c.license, "bulk")["allowed"]`. Also handle the
non-ASCII glyph license slugs (`©Assemblies-of-God`, `©Libreria-Editrice-Vaticana`,
`©OCA-Hopko-estate`): `_matches_proprietary` keys on the `©`/`(c)`/`copyright` prefixes, so
`check_redistribute` already returns `allowed=False` for them (verified), so the only fix
needed is reading `["allowed"]`. Decision 3 edge-case 3 additionally asks for normalization to
the registered slug from docs/LICENSE_TAGGING.md before lookup; current behavior is fail-closed
(denies bulk) which is the safe direction, so the slug-normalization is a cleanliness follow-up,
not a leak.

### G-SHARED-2 (CONTRACT, HIGH) - ADDRESSES edge never produced; autotag never dispatched

Decision 4 binds an `ADDRESSES` edge model (`CulturalChunk-[:ADDRESSES {stance,confidence,
evidence_phrase}]->Doctrine`) and `graph/cultural.cypher` emits `doctrine_slug` and
`addresses_rel`. No module writes this edge. Worse, `ingest/cultural/run.py` never calls
`ingest/cultural/autotag.tag_chunks` at all (the `--skip-autotag` / `--autotag-only` flags are
parsed but unused; `_run_source` only scrapes and upserts). So `doctrine_tags` is always the
empty list, persisted as `[]` JSON on the chunk, and the ADDRESSES projection step the schema
promises does not exist. Decision 4's acceptance query is written to tolerate zero ADDRESSES
edges pre-autotag (`edges >= 0`), so a fresh reseed still passes the triangle test, but the
contract is unmet for any tagged-store gate. Faithful fix: add an autotag dispatch + an
ADDRESSES-projection Cypher writer (label-scoped `MATCH (c:CulturalChunk {chunk_id}),
(d:Doctrine {slug}) MERGE (c)-[r:ADDRESSES]->(d) SET r += ...`, both endpoints constraint-backed).
This is a builder/architect deliverable, not an adapter edit. Flagged MUST-ESCALATE for scope
(it is a missing Pipeline-1 phase, not a bug in an existing one).

### G-SHARED-3 (CONTRACT, LOW) - magisterial audit validator cannot fire for the Vatican sources

`ingest/models.py` `warn_on_non_confessional_magisterial` only warns when
`is_confessional_text is False AND tradition == catholic-magisterial AND work_id in
_KNOWN_DOGMATIC_WORKS`. `_KNOWN_DOGMATIC_WORKS` contains `ccc`, `vatican-ii`, ... but the
adapters register `work_id` `vatican-ccc` and `vatican-dv`, and both set
`is_confessional_text=True` anyway, so the audit warning is dead for these sources. Not a leak
(redistribute is handled, once G-SHARED-1 is fixed) and not a reseed blocker; record as a
data-model nit for the owner: either align `_KNOWN_DOGMATIC_WORKS` to the registered work_ids
or accept the validator is intentionally narrow.

### G-SHARED-4 (ORDERING, INFO) - run.py order is per-source self-contained

`ADAPTERS` in `run.py` dispatches each adapter independently; `_run_source` upserts Work +
CulturalChunk + HAS_CHUNK inside that source. There is NO cross-adapter producer/consumer
edge (no adapter MATCHes a node another adapter wrote). `seed_doctrine_question_nodes.py` is a
separate entrypoint and MUST run before any future ADDRESSES projection (Decision 7 edge-case 3),
but it is independent of scrape order. **No ordering hazard among the 22 scrape adapters.**
The single ordering rule for Phase G: apply `graph/cultural.cypher` DDL, then run
`seed_doctrine_question_nodes`, then scrape adapters, then (future) autotag+ADDRESSES.

## Per-adapter table

HAS_CHUNK endpoint/index status is identical for all rows (CulturalChunk.chunk_id UNIQUE +
Work.work_id UNIQUE, both in graph/cultural.cypher) so it is summarized once: **EDGE-PERF CLEAN
(labeled, constraint-backed) for all 22**. The table below carries JOIN-KEY (does the adapter's
emitted `source.work_id` reconcile with `_CHUNK_CYPHER`'s `MATCH (w:Work {work_id})`, and is
`chunk_id` unique-by-construction) and CATALOG-RECON (is `total_records` the faithful
`record_unit`).

| Adapter | Edges / endpoint-label+index | Join-key verdict | Catalog-recon verdict | Other |
|---|---|---|---|---|
| schleitheim.py | HAS_CHUNK clean | CLEAN: work_id `schleitheim` constant, chunk_id `schleitheim.Schleitheim.A<n>` unique per article | CLEAN: total 7 == record_unit confession-article, bound [7,7] hard | Decision 13 satisfied (work_id, is_confessional_text=True) |
| augsburg.py | HAS_CHUNK clean | CLEAN: work_id `augsburg` constant; chunk_id `augsburg.Augsburg.A<nn>` unique | CLEAN: fixture total 1 (Article 1 only); bound [25,30]; acceptance asserts anchor-uniqueness not count, so no tier-A false-fail | Decision 12 satisfied |
| heidelberg.py | HAS_CHUNK clean | CLEAN: work_id `heidelberg`; chunk_id `heidelberg.HC.Q<nnn>` unique; q_num<=129 filter present | CLEAN: total 129 == catechism-qa record_unit | Decision 9 satisfied |
| belgic.py | HAS_CHUNK clean | CLEAN: work_id `belgic`; chunk_id `belgic.Belgic.A<nn>` unique; article 1..37 filter | CLEAN: total 37 == confession-article, bound [37,37] hard | Decision 9 satisfied |
| dort.py | HAS_CHUNK clean | CLEAN: work_id `dort`; chunk_id `dort.Dort.<head>.A<nn>` unique by head+article | CLEAN: total 59 == affirmative-article record_unit, bound [50,100] | Decision 9: rejections kept in parent text per rule |
| wcf.py | HAS_CHUNK clean | CLEAN: work_id `wcf`; chunk_id `wcf.WCF.<ch>.<sec>` unique; empty-text sections skipped | CLEAN: total 171 == confession-section, bound [160,200] | Decision 8 satisfied |
| wsc.py | HAS_CHUNK clean | CLEAN: work_id `wsc`; chunk_id `wsc.WSC.Q<nnn>` unique | CLEAN: total 107 == catechism-qa | Decision 8 satisfied |
| wlc_catechism.py | HAS_CHUNK clean | CLEAN: work_id `wlc-catechism` (matches Decision 8 + catalog); chunk_id `wlc-catechism.WLC.Q<nnn>` unique | CLEAN: total 196 == catechism-qa | Decision 8 satisfied |
| lbc_1689.py | HAS_CHUNK clean | CLEAN: work_id `lbc-1689`; chunk_id `lbc-1689.1689.<ch>.<sec>` unique; anchor prefixed `1689.` not `WCF.` per Decision 10 | CLEAN: fixture total 20 (ch 1-3 only); bound [140,160]; acceptance asserts anchor-uniqueness not count | Decision 10 satisfied |
| articles_39.py | HAS_CHUNK clean | CLEAN: work_id `articles-39`; chunk_id `articles-39.39A.A<nn>` unique; 1..39 filter | CLEAN: total 39 == confession-article, bound [39,39] hard | Decision 11: Wikisource fallback canonical, no TLS bypass; CLEAN |
| umc.py | HAS_CHUNK clean | CLEAN: work_id `umc-articles` (distinct from `articles-39` per Decision 15); chunk_id `umc.UMC.A<nn>` unique; 1..25 filter | CLEAN: total 25 within bound [24,26] == confession-article | Decision 15 satisfied (separate work_id, no merge onto 39A) |
| ag.py | HAS_CHUNK clean | CLEAN: work_id `ag-fundamental-truths`; chunk_id `ag.AG.A<nn>` unique | CLEAN: total 16 == statement-truth, bound [16,16] hard | redistribute=false but blocked by **G-SHARED-1** dead guard; LOCAL_SNAPSHOT fallback correct, no WAF evasion |
| oca_hopko.py | HAS_CHUNK clean | SUSPECT-LOW: work_id `oca-hopko` constant; chunk_id `oca-hopko.OCA.<url-path-dotted>`. Anchor derived from live URL path; on a re-crawl a changed URL mints a new chunk_id (Decision 1 edge-case allows this) but two different leaf URLs collapsing to the same dotted suffix would collide. Low risk: URL paths are distinct by construction. | UNVERIFIED-SUSPECT: fixture total 3 (nav pages with prose); live bound [40,200]; acceptance asserts anchor-uniqueness not count, so NOT a tier-A false-fail, but the catalog `total_records=3` is a fixture artifact not the faithful leaf-article unit. Documented as fixture-shape in catalog notes; acceptable. | redistribute=false, blocked by **G-SHARED-1**; Decision 19 |
| vatican_ccc.py | HAS_CHUNK clean | CLEAN: work_id `vatican-ccc`; chunk_id `vatican-ccc.CCC.<n>` unique per paragraph | UNVERIFIED-SUSPECT-BENIGN: fixture total 2 (one paragraph page); live bound [2400,2870]; acceptance asserts redistribute-invariant not count, so no tier-A false-fail | redistribute=false, blocked by **G-SHARED-1**; G-SHARED-3 validator silent |
| vatican_dv.py | HAS_CHUNK clean | CLEAN: work_id `vatican-dv`; chunk_id `vatican-dv.DV.<n>` unique; 1..30 filter | CLEAN: total 26 within bound [24,28] == constitution-paragraph | redistribute=false, blocked by **G-SHARED-1**; G-SHARED-3 |
| ccel_anf.py | HAS_CHUNK clean | CLEAN: work_id is **per-volume** `ccel-anf.vol<n>` (multiple Work nodes, all constraint-backed, reconciles with `_CHUNK_CYPHER` MATCH); chunk_id `ccel-anf.ANF.vol<n>.<chap-slug>.<idx:03d>` carries monotonic block index per Decision 17 edge-case 2 | CLEAN: fixture total 15 (Vol.1 TOC only, representative); bound [200,50000]; acceptance has no fixed count | Decision 17 satisfied; is_confessional_text=False |
| ccel_npnf1.py | HAS_CHUNK clean | CLEAN: per-volume work_id `ccel-npnf1.vol<n>`; chunk_id `ccel-npnf1.NPNF1.vol<n>...idx` unique | CLEAN: fixture total 9 (reuses NPNF2-01 TOC, shape-representative per catalog); bound [200,30000] | Decision 17 edge-case 1 honored (shape sample) |
| ccel_npnf2.py | HAS_CHUNK clean | CLEAN: per-volume work_id `ccel-npnf2.vol<n>`; chunk_id `ccel-npnf2.NPNF2.vol<n>...idx` unique | CLEAN: fixture total 9 (Vol.1 TOC); bound [200,30000] | Decision 17; Vol.14 conciliar kept under CCEL work_id per rule |
| conciliar.py | HAS_CHUNK clean | **JOIN-KEY/CONTRACT MISMATCH**: `WORK_ID="conciliar"` is a SINGLE shared work_id for all 4 creeds. Decision 16 binds "each creed registers a distinct `source.work_id`". chunk_id stays unique (anchor differs) so no constraint violation, but the Work fan-out is 1 Work with 4 children, not 4 Works. Decision 16 acceptance query `count(DISTINCT w.work_id) >= 1` still passes (>=1), so it is a latent contract breach not a triangle-test fail. | CLEAN: total 4 == creed record_unit, bound [3,20] | See G-CONCILIAR-1 |
| stem_publishing.py | HAS_CHUNK clean | CLEAN: work_id per work `stem-publishing.<author>.<work-slug>` (many Works, constraint-backed); chunk_id `stem-publishing.STEM.<author>.<work>.<idx:03d>` unique | CLEAN: fixture total 5; bound [50,10000]; no fixed count | Decision 20 satisfied; public_domain redistribute=true |
| bcp_1662.py | HAS_CHUNK clean | SUSPECT-LOW: work_id `bcp-1662` constant; chunk_id for non-catechism sections is `bcp-1662.BCP.<slug>` (ONE chunk per section). If `parse_section` ever returned >1 chunk per slug they would collide, but it returns at most one, so unique by construction today. Catechism uses `BCP.Catechism.Q<nn>`. | CLEAN: total 13 == liturgy-section record_unit, bound [10,200] | Decision 11: Athanasian also in conciliar; distinct work_id `bcp-1662` vs `conciliar` keeps them separate. CLEAN |
| brethren_parsed.py | HAS_CHUNK clean | SUSPECT: work_id `brethren-parsed.<doc_slug>` per doc. chunk_id = `brethren-parsed.` + (`ch.chunk_id` if present in source JSON else `parsed.<doc_slug>.<idx:03d>`). If two source docs supply the same upstream `chunk_id` string, or a doc reuses a chunk_id, the global `cultural_chunk_id` UNIQUE constraint would reject the second (write-time fail, not silent). anchor_id is always `parsed.<doc_slug>.<idx:03d>` (deterministic) but chunk_id trusts source-supplied `ch.chunk_id`. See G-BRETHREN-1. | CLEAN: total 243 == sanitized-teaching-note record_unit, bound [150,1000]; skips `_index.json`/`_perspectives.json` per Decision 20 | redistribute=false, blocked by **G-SHARED-1**; on-trial corpus, air-gapped |

## Consolidated defect ledger

| id | class | owning file | faithful fix prescription | owning caste | blocks reseed? |
|---|---|---|---|---|---|
| G-SHARED-1 | CONTRACT (dead guard) | ingest/cultural/_common.py | Read `["allowed"]` from `check_redistribute` result: `redistribute_ok = check_redistribute(c.license, "bulk")["allowed"]`. Add a test that a `redistribute=false` source persists `text == text_to_embed`. | Implementer | BLOCKS-RESEED (any redistribute=false source leaks verbatim copyrighted prose; fails Decision 3/14/18/19/20 acceptance) |
| G-SHARED-2 | CONTRACT (missing phase) | ingest/cultural/run.py + new ADDRESSES writer | Wire `autotag.tag_chunks` into the dispatcher behind `--skip-autotag`; add a label-scoped ADDRESSES projection `MATCH (c:CulturalChunk {chunk_id}),(d:Doctrine {slug}) MERGE (c)-[r:ADDRESSES]->(d) SET r.stance,r.confidence,r.evidence_phrase`. Both endpoints constraint-backed (clean). | Builder/Architect | GATES-VERIFY-ONLY (Decision 4 acceptance tolerates 0 edges pre-autotag; reseed of chunks proceeds, but tagged-store gate cannot pass without it) MUST-ESCALATE for scope |
| G-SHARED-3 | CONTRACT (dead validator) | ingest/models.py | Either add `vatican-ccc`,`vatican-dv` to `_KNOWN_DOGMATIC_WORKS` or document the validator as intentionally narrow. No leak. | Owner decision | NEITHER (informational) |
| G-CONCILIAR-1 | JOIN-KEY/CONTRACT | ingest/cultural/conciliar.py | Replace constant `WORK_ID="conciliar"` with a per-creed work_id (e.g. `conciliar.apostles`, `conciliar.nicaea-381`, `conciliar.chalcedon-451`, `conciliar.athanasian`) carried in the `SOURCES` tuple, so 4 Work nodes fan out per Decision 16. chunk_id already unique; only `source.work_id` and the Work property bag change. | Implementer | GATES-VERIFY-ONLY (Decision 16 acceptance passes at >=1 today, but the per-creed-Work contract is unmet; fix before the Decision-16 triangle is tightened) |
| G-BRETHREN-1 | JOIN-KEY (id trust) | ingest/cultural/brethren_parsed.py | chunk_id derives from source-supplied `ch.chunk_id` un-namespaced beyond the `brethren-parsed.` prefix; two docs with a colliding upstream chunk_id hard-fail the UNIQUE constraint at write time (fail-closed, not silent corruption). Faithful fix: make chunk_id deterministic from `doc_slug`+idx (`brethren-parsed.parsed.<doc_slug>.<idx:03d>`) and ignore source-supplied chunk_id for identity, OR namespace it with doc_slug. Verify against the parsed corpus for actual collisions before changing identity (re-scrape convergence per Decision 1). | Implementer | GATES-VERIFY-ONLY (write-time constraint rejection is loud; no silent zero-edge; but a collision aborts the brethren batch) |
| G-SEED-1 | JOIN-KEY (latent) | ingest/cultural/seed_doctrine_question_nodes.py | Current 26 categories all resolve (21 exact, 5 via `[:5]` prefix). The `next(iter(FINE_SLUGS))` ultimate fallback and the 5-char prefix are latent: a new question category that misses would silently attach UNDER_QUESTION to an arbitrary doctrine. Faithful fix: replace the heuristic with an explicit category->fine-slug map and raise on miss. | Implementer | NEITHER today (verified all 231 questions resolve correctly); harden before category set changes |

No EDGE-PERF defects: every relationship MATCH on the cultural side is label-scoped and
constraint-backed (HAS_CHUNK, UNDER_QUESTION, and the future ADDRESSES if built per G-SHARED-2).
No unlabeled `MATCH (a {..}),(b {..})` exists. The lexical AllNodesScan/quadratic class is
ABSENT on the cultural side.

No CATALOG-RECON MISMATCH: every `total_records` equals the adapter's faithful `record_unit`
for full-corpus sources, and every fixture-only source (augsburg, lbc_1689, vatican_ccc,
oca_hopko, ccel_*, stem_publishing) has an acceptance query that asserts an invariant
(anchor-uniqueness or redistribute-invariant) rather than a fixed count, so no tier-A count
gate can false-fail. The two UNVERIFIED-SUSPECT-BENIGN rows (vatican_ccc, oca_hopko) are
fixture artifacts the catalog notes explicitly disclose; they do not gate.

## Single-touch fix-wave plan (one task per file, parallel-safe)

Mirrors the lexical T1..T19 single-touch structure. Each task is the ONLY edit to that file
and bundles every defect owned by it. All tasks are parallel-safe (no shared file, no ordering
dependency among them; G-T1 is the only reseed blocker and should land first).

- G-T1 (BLOCKER, do first) - `ingest/cultural/_common.py`: fix G-SHARED-1 (read `["allowed"]`).
  Add regression test: a `redistribute=false` chunk persists `text == text_to_embed`.
- G-T2 - `ingest/cultural/conciliar.py`: fix G-CONCILIAR-1 (per-creed work_id in `SOURCES`).
- G-T3 - `ingest/cultural/brethren_parsed.py`: fix G-BRETHREN-1 (deterministic doc-namespaced
  chunk_id; stop trusting source-supplied chunk_id for node identity).
- G-T4 - `ingest/cultural/seed_doctrine_question_nodes.py`: fix G-SEED-1 (explicit
  category->fine-slug map, raise on miss).
- G-T5 (MUST-ESCALATE, scope = new phase) - `ingest/cultural/run.py` + new ADDRESSES writer
  module: fix G-SHARED-2 (autotag dispatch + label-scoped ADDRESSES projection). Owner/architect
  sign-off required; not an adapter edit.
- G-T6 (owner decision, optional) - `ingest/models.py`: G-SHARED-3 (align
  `_KNOWN_DOGMATIC_WORKS` or document narrow intent).

No edits required to the other 18 adapters: they are CLEAN on all three lexical-proven classes.

## Cultural acceptance gate (analog of lexical Phase D.4 count gate + D.3 triangle + per-edge)

1. Count gate (D.4 analog): for each of the 22 sources, the post-reseed CulturalChunk count
   under its `Work` fan-out MUST fall inside `live_corpus_bound` from
   `docs/cultural_data_inventory_catalog.json` (NOT the fixture `total_records`, which is a
   snapshot artifact). Hard-bound sources (schleitheim [7,7], belgic [37,37], articles-39
   [39,39], ag [16,16]) MUST hit the exact count or quarantine.
2. Triangle test (D.3 analog): run every `#### Cypher acceptance query` in
   `docs/CULTURAL_SCHEMA_DECISIONS.md` Decisions 1-20 against the reseeded cultural store; all
   `ok`/`*_ok` columns MUST be true. Decision 3's redistribute-leak query (`leaked = 0`) is the
   gate that catches a regression of G-SHARED-1 and MUST be green for AG / Vatican-DV /
   Vatican-CCC / OCA-Hopko / Brethren-Parsed.
3. Per-edge gate: HAS_CHUNK fan-out conformance (Decision 2 query: every Work has >=1 child and
   exactly one Work node per work_id); UNDER_QUESTION conformance (every seeded Question reachable
   from a Doctrine); ADDRESSES enum+threshold conformance (Decision 4 query) once G-SHARED-2 is
   built (tolerant of 0 edges pre-autotag).
4. Air-gap gate (Decision 5): the cultural driver resolves only `NEO4J_CULTURAL_*`; assert no
   cultural label is reachable from the lexical store. Static: `_common.py` `Settings` reads
   only `neo4j_cultural_*` / `qdrant_cultural_*` - CLEAN, no lexical env var present.
5. Constraint/index gate (Decision 7): `SHOW CONSTRAINTS` includes the five UNIQUE constraints
   and `SHOW INDEXES` the four range + two rel-property + one fulltext index from
   `graph/cultural.cypher` before any scrape adapter runs.

Ordering for the gate run: apply `graph/cultural.cypher` -> `seed_doctrine_question_nodes` ->
22 scrape adapters (any order, no inter-adapter dependency) -> (future) autotag + ADDRESSES ->
triangle test.
