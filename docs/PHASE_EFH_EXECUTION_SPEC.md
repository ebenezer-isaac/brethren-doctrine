# Phase E / F / H Execution Spec

Auditor caste synthesis. Read-only. Single source for running Phases E, F, and
H with zero further design once Phase D completes. No em or en dashes anywhere.
Doctrinal frame brethren-on-trial: the Brethren parse is the position under
test, never the rubric; Pipeline 2 reads the lexical store only.

This spec freezes contracts already present in the repo. It invents no tool.
Every step states: the ordered action, the exact command or tool, the
pass/fail threshold, the dependency from the prior phase, and whether the step
is auditor-dispatchable (pure Cypher / script, no live ingest or embed) or
requires a real ingest or embed run. Gaps where a RESEED_PLAN requirement has
no backing tool or fixture are flagged inline and consolidated in section 4.

Source-of-truth files cross-referenced:
`docs/implementation_phases/RESEED_PLAN.md` (Phase E, F, H),
`docs/implementation_phases/phase_02_lexical_ingest.md` (acceptance gate),
`docs/ARCHITECTURE.md`, `docs/EVIDENCE_SCHEMA.md`,
`docs/PHASE_D_MASTER_LEDGER.md`, `embeddings/embed_lexical.py`,
`embeddings/bootstrap.py`, `tests/embeddings/test_embed_text.py`,
`pipeline2/context_builder.py`, `pipeline2/triangle.py`,
`tools/snapshot_counts.py`, `tools/check_thresholds_immutable.py`,
`tools/verify_manifest.py`, `tools/check_caste.py`, `tools/predicates.py`,
`tools/predicates_by_type.cypher`, `tools/verify_live_stacks.py`,
`graph/lexical.cypher`.

---

## 0. Phase E entry gate (what Phase D state unblocks E)

Phase E does NOT start until ALL of the following are simultaneously true,
read from `docs/PHASE_D_MASTER_LEDGER.md` section 3 and 4 and the Phase D
verification harness:

1. **EDGE-PERF wave landed and integrated to main.** Every `PERF-*` defect
   (T1..T14 perf portions plus the perf-only adapters) is integrated, not
   merely "LANDED on an isolated worktree branch". Per ledger section 3, the
   reseed AllNodesScans and never finishes without these, so E cannot embed a
   graph that never re-ingested.
2. **ORD-MGNT landed (T18, `ingest/lexical/run.py`).** `morphgnt` runs
   immediately after `macula_greek` in `DATASETS`.
3. **ADAPTER-TVTMS (7eb0b7a) integration-verified.** `VersificationRule`
   count is exactly 1308 on the real artifact (ledger 2.3).
4. **Phase D.4 master ledger green on three sub-gates:**
   - **D.4 count gate** (Section 1, per-source count vs
     `tools/expected_counts.json` to tier tolerance) green, which requires the
     four `RECON-*` `[SCHEMA-REVISION]`s applied after owner per-source review
     (RECON-PHONO, RECON-TFLSJ, RECON-MORPH, RECON-PARALLELS).
   - **Triangle test green** (Phase D.3 per-row presence vector):
     `python tools/snapshot_counts.py` run twice over identical inputs yields
     the identical `overall_hash`.
   - **Per-edge gate green** (D.4 Section 3): every `KEY-*` JOIN-KEY defect
     resolved per Decision 18 so no in-scope edge type resolves to 0; the
     per-edge floors in `tools/expected_counts.json` are met.
5. **D.4 threshold immutability green:** `python
   tools/check_thresholds_immutable.py` exits 0 (expected_counts.json blob SHA
   equals the A.4 baseline, or last change is a `[SCHEMA-REVISION]` commit
   with the baseline moved in the same commit).
6. **Open DATA-MODEL escalations do not block E.** DM-GREEKLEMMA-POP (E1),
   DM-LEMMA-POP (E2), A2-MGNT-ESCALATE / KEY-MGNT-PARSEOF are explicitly
   "D.4 only, does not block relaunch" per ledger; they leave specific edges
   at 0 but do not gate E. They DO remain open items the Phase H audit will
   report against.

Entry-gate one-liner: **E starts when the EDGE-PERF wave plus ORD-MGNT are
integrated, 7eb0b7a is verified (VersificationRule == 1308), and the Phase D
master ledger shows D.4 count gate + triangle + per-edge all green with
`check_thresholds_immutable.py` exit 0.** Until then E is blocked.

---

## Phase E: Re-Embed (RESEED_PLAN section E)

Target collection: Qdrant `lex_col` on `QDRANT_LEXICAL_URL` (lexical stack).
The qdrant healthcheck was just fixed (bash `/dev/tcp` `/readyz`; wget/curl
absent in the image) but qdrant itself was always functional; E does not
depend on the healthcheck cosmetic, only on `lex_col` being reachable and
bootstrapped at 2048 dims cosine per `embeddings/bootstrap.py`
(`VOYAGE_MODEL = voyage-4-large`, `VOYAGE_OUTPUT_DIMENSION = 2048`).

### Step count: 6 ordered steps (E0..E5). E0..E2 auditor-dispatchable; E3 requires a real embed run; E4..E5 are post-embed Cypher/Qdrant gates that require E3.

### E0 - Confirm Phase E entry gate

- Action: assert section 0 items 1..6 all true.
- Command: read `docs/PHASE_D_MASTER_LEDGER.md` section 3/4 plus
  `python tools/check_thresholds_immutable.py` and one
  `python tools/snapshot_counts.py` triangle pair (see Phase H H.5 for the
  exact triangle recipe).
- Pass/fail: all six gate items true. Any false -> E aborts, stays blocked.
- Dependency: Phase D complete.
- Auditor-dispatchable: yes (script + ledger read; the snapshot pair is
  pure read-only Cypher).

### E1 - Embed-text contract unit tests (RESEED_PLAN E.1)

Contract (frozen, from `embeddings/embed_lexical.py::build_embed_text`):
the Voyage input string for one Lemma row is composed, in order, of:

- `lemma` (UTF-8 lemma; required),
- `(transliteration)` in parentheses, only if present and != lemma,
- `: gloss` (required),
- `| pos <pos>` if the `pos` column is present,
- `| domain <domain>` if the `domain` column is present,
- `| LN <louw_nida>` if the `louw_nida` column is present,
- truncated to `EMBED_TEXT_MAX_LEN` (6000) chars at the tail.

`pos`, `domain`, `louw_nida` are Phase E enrichment columns; `_iter_lemmas`
in `embed_lexical.py` currently SELECTs only `strong, lemma,
transliteration, gloss, license, redistribute` (see gap G1 in section 4).

Sub-gates, all in `tests/embeddings/test_embed_text.py` (already implemented):

- **Distinct-token floor**: `len(set(text.split())) >= 6` for every panel
  row (`test_distinct_token_floor`).
- **10-Strong panel, 4 expected substrings each**: the `PANEL` list of 10
  hand-picked Strong's (H430, H3068, H7225, H1254, H4428, G2316, G2962,
  G5547, G3056, G4151), each with a 4-tuple `_expected_substrings` covering
  lemma + transliteration + gloss-word + domain; every substring must appear
  in the built text (`test_panel_expected_substrings_present`,
  `test_panel_has_ten_strongs`).
- **Contrastive Jaccard**: `build_embed_text(H7225) != build_embed_text(H430)`
  with token-set Jaccard < 0.5 (`test_contrastive_jaccard_h7225_vs_h430`);
  plus G2316 vs G4151 (`test_contrastive_jaccard_g2316_vs_g4151`) and a
  pairwise-panel guard (`test_pairwise_jaccard_within_panel_mostly_below_threshold`).
- Determinism, non-empty-for-valid-row, empty-row-empty-string, truncation,
  redundant-transliteration-skip (the remaining tests in the file).

- Command: `python -m pytest -q tests/embeddings/test_embed_text.py`
- Pass/fail: pytest exit 0; every test green. Any failure -> E blocked,
  embed-text contract is broken.
- Dependency: E0 green.
- Auditor-dispatchable: yes (pure unit test, no graph, no embed call).

### E2 - lex_col target preflight

- Action: confirm the lexical Qdrant collection exists at 2048-dim cosine
  with the `dense` named vector and `bm25` sparse vector, per
  `embeddings/bootstrap.py`.
- Command: `python -m embeddings.bootstrap --store lexical` (idempotent;
  creates `lex_col` only if absent, then ensures payload indexes
  book/chapter/verse/strong/license).
- Pass/fail: command exits 0; `lex_col` present. The collection vector
  config must be `size=2048, distance=COSINE` for `dense`.
- Dependency: E0 green; `QDRANT_LEXICAL_URL` set.
- Auditor-dispatchable: yes for the existence/shape check (read-only
  `get_collections`); the create path is idempotent and writes only an empty
  collection, not embeddings.

### E3 - Re-embed run (REQUIRES A REAL EMBED RUN)

- Action: embed every `Lemma {strong IS NOT NULL}` row from the lexical
  Neo4j through `voyage-4-large` at 2048 dims and upsert to `lex_col`. Point
  id is `uuid5(NS, strong)`; payload carries strong/lemma/transliteration/
  gloss/license/redistribute.
- Command:
  `python -m embeddings.embed_lexical --collection lex_col --limit <N>`
  with `VOYAGE_API_KEY`, `QDRANT_LEXICAL_URL`, `NEO4J_LEXICAL_URI/USER/PASSWORD`
  in env. `--limit` must be set high enough to cover all canonical Lemma rows
  (default 20000; raise if Lemma count exceeds it; see gap G1).
- Pass/fail: stdout `TOTAL: embedded=<E> failures=<F>` with `F == 0` and
  `E == count of Lemma {strong IS NOT NULL}` in the lexical store. Any
  `failures > 0` -> E fails.
- Dependency: E1 + E2 green; lexical Neo4j is the post-Phase-D reseeded store.
- Auditor-dispatchable: NO. This is a live Voyage API + Qdrant write run; the
  orchestrator dispatches it, not an auditor.

### E4 - Vector-quality gate: distinct-vector ratio (RESEED_PLAN E.2)

- Threshold: `count(DISTINCT sha256(vec)) / count(*) >= 0.999` over all
  points in `lex_col`. Duplicate-vector groups allowed only if every member
  shares `gloss` exactly.
- Action: scroll all `lex_col` points with vectors, sha256 each dense
  vector's canonical byte form, compute the distinct ratio; for any
  duplicate sha group assert all members' payload `gloss` are identical.
- Command: there is NO existing tool for this (gap G2). The orchestrator
  must run an Auditor-caste Qdrant-scroll script that returns
  `{total, distinct, ratio, dup_groups_with_divergent_gloss}`.
- Pass/fail: `ratio >= 0.999` AND `dup_groups_with_divergent_gloss == 0`.
- Dependency: E3 complete (vectors present).
- Auditor-dispatchable: yes once the script exists (read-only Qdrant
  scroll); BLOCKED today on gap G2.

### E5 - Vector-quality gate: direction-dispersion non-degeneracy (RESEED_PLAN E.2)

- Threshold (amended 2026-05-19, supersedes the prior norm-variance floor):
  over a random sample of disjoint pairs of `lex_col` dense vectors,
  `mean(pairwise_cosine) <= 0.95` AND `pstdev(pairwise_cosine) >= 1e-4`
  (rejects "all vectors point the same direction"). The prior
  `stdev([norm(v)]) >= 0.001` floor was incompatible with the unit-
  normalized voyage-4-large model (every norm approximately 1.0, measured
  norm stdev approximately 3.97e-08) and is replaced, not deleted; the
  embeddings were NOT altered. See `docs/AUDIT_phase_e_vector_quality.md`
  and `docs/PHASE_D_DECISIONS_LOG.md`.
- Command: `tools/check_vector_quality.py` (gap G2 now closed); it computes
  both invariants in one read-only scroll and self-tests the rejection
  property (`--self-test`).
- Pass/fail: `mean(pairwise_cosine) <= 0.95` AND
  `pstdev(pairwise_cosine) >= 1e-4`.
- Dependency: E3 complete.
- Auditor-dispatchable: yes (read-only Qdrant scroll).

Phase E exit: E1 pytest green, E3 `failures == 0` with embedded count equal
to canonical Lemma count, E4 ratio >= 0.999 with zero divergent-gloss dup
groups, E5 mean pairwise cosine <= 0.95 and pairwise-cosine stdev >= 1e-4.

---

## Phase F: Pipeline 2 smoke (RESEED_PLAN section F)

Hard constraint, stated up front and enforced: **Phase F writes NO
`evidence/*.json`.** F is a source-completeness and determinism smoke over
the lexical store and the context bundle only. SME ground truth applies later
at Stage 2/3 (ARCHITECTURE.md phase plan), outside this reseed. The
`context_builder` queries the lexical Neo4j exclusively (no cultural touch),
matching the air-gap.

### Question-id resolution (GAP G3, must resolve before F runs)

RESEED_PLAN F.1 names the three questions `{doc-canon-closed, baptism-mode,
lords-supper-real-presence}`. Verified against `questions.json` (231
questions):

- `doc-canon-closed` EXISTS verbatim. Anchors: `Hebrews 1:1-2`,
  `Ephesians 2:20`, `Jude 1:3`, `Revelation 22:18-19`, `Galatians 1:8-9`,
  `2 Timothy 3:16-17`.
- `baptism-mode` does NOT exist verbatim. Faithful canonical match:
  **`prc-baptism-by-immersion`** ("Baptism is administered by full immersion
  ... identification with Christ's death, burial, and resurrection").
  Anchors: `Romans 6:3-4`, `Colossians 2:12`, `Acts 8:36-38`.
- `lords-supper-real-presence` does NOT exist verbatim. The real-presence
  cluster splits across **`doc-transubstantiation-denial`** and
  **`doc-consubstantiation-affirm`** (and the spiritual-communion question
  `doc-supper-spiritual-communion`, anchors `1 Corinthians 10:16-17`,
  `John 6:53-58`, `John 6:63`). No single id equals
  "lords-supper-real-presence".

F MUST NOT proceed on guessed ids. The orchestrator/owner picks the canonical
id for the baptism-mode and real-presence slots before F1 runs. The
recommended faithful pick is `prc-baptism-by-immersion` and
`doc-transubstantiation-denial`, but this is an owner decision, not an
auditor invention. This is gap G3.

### Step count: 4 ordered steps (F0..F3). All auditor-dispatchable (pure Cypher + a deterministic in-process bundle build); none writes evidence and none requires an embed run.

### F0 - Resolve the three question ids

- Action: bind the three slots to concrete `questions.json` ids
  (`doc-canon-closed` is fixed; the other two per G3 owner decision).
- Pass/fail: each chosen id is present in `questions.json`; abort if any is
  guessed.
- Dependency: Phase E exit green (lexical store is reseeded and embedded; F1
  invariants query the same reseeded store, embeddings not required for F).
- Auditor-dispatchable: yes (read questions.json).

### F1 - Source-completeness invariants (RESEED_PLAN F.1, five invariants)

For each resolved question `Q` with anchor refs converted to OSIS via
`pipeline2.context_builder.to_osis` (single-verse expansion of ranges), build
the bundle once with
`pipeline2.context_builder.build_lexical_context_bundle(Q)` and assert ALL
five invariants. All five are pure Cypher against the lexical store
(`NEO4J_LEXICAL_*`); no SME truth, no anchor list to author.

Concrete runnable Cypher (parameterise `$ref` per OSIS anchor; the bundle
side is the deterministic projection from `build_lexical_context_bundle`):

1. **Word completeness** (set equality):
   ```cypher
   MATCH (v:Verse {osisID: $ref})<-[:IN_VERSE]-(w:Word)
   RETURN w.id AS word_id ORDER BY w.id
   ```
   Pass iff the set of `word_id` equals
   `{ w.id for w in bundle.anchor_verses[ref].words/morphology }`.

2. **Lemma completeness + property coverage**: for every Word above with
   `strong IS NOT NULL`:
   ```cypher
   MATCH (v:Verse {osisID: $ref})<-[:IN_VERSE]-(w:Word)-[:INSTANCE_OF]->(l:Lemma)
   WHERE w.strong IS NOT NULL
   RETURN l.strong AS strong, l.gloss AS gloss,
          l.transliteration AS translit, l.louw_nida AS ln
   ```
   Pass iff every such lemma appears in `bundle.anchor_lemmas` AND `gloss`
   and `transliteration` are non-empty under `tools/predicates_by_type.cypher`
   `$pred_string`, AND where the MACULA-Greek source carries Louw-Nida,
   `louw_nida` is non-empty under `$pred_string`. Use
   `tools/predicates.py::substitute` to expand `$pred_string(...)` into the
   real Cypher boolean; do NOT inline `IS NOT NULL` (RESEED_PLAN C.5).

3. **Cross-ref completeness modulo LIMIT**:
   ```cypher
   MATCH (cr:CrossRef {from_ref: $ref})
   RETURN count(cr) AS total_cross_refs
   ```
   Pass iff `count(bundle.cross_refs where from == $ref) ==
   min(CROSS_REF_LIMIT, total_cross_refs)` where `CROSS_REF_LIMIT == 20`
   (`pipeline2/context_builder.py`).

4. **Variant completeness, 3 John verses only**: for each `$ref` in
   `["3John.1.1" .. "3John.1.15"]` intersected with `Q`'s anchors:
   ```cypher
   MATCH (v:Verse {osisID: $ref})-[:HAS_VARIANT]->(vu:Variant)
   RETURN vu.id AS variant_id ORDER BY vu.id
   ```
   Pass iff every `variant_id` appears in `bundle.variant_units`. For any
   anchor verse OUTSIDE 3 John, `bundle.variant_units` filtered to that ref
   must be empty AND the bundle must carry a `not_in_ecm_scope` marker (gap
   G4: the current `build_lexical_context_bundle` does not emit a
   `not_in_ecm_scope` flag; the invariant's empty-set half is checkable
   today, the flag half is not).

5. **Syntactic-context completeness**:
   ```cypher
   MATCH (v:Verse {osisID: $ref})
   OPTIONAL MATCH (v)-[:HAS_CLAUSE]->(c:Clause)-[:HAS_PHRASE]->(p:Phrase)
   RETURN c.id AS clause_id, p.id AS phrase_id
   ORDER BY clause_id, phrase_id
   ```
   Pass iff every Clause+Phrase covering the verse (BHSA for Hebrew anchors,
   MACULA syntax tree for Greek anchors) appears in
   `bundle.syntactic_context`.

- Command: an Auditor-caste invariant runner that, per resolved id, calls
  `build_lexical_context_bundle(id)` and runs the five Cypher checks above
  through `tools/predicates.py.substitute`. No such single runner exists yet
  (gap G5); the five queries themselves are runnable today via the Neo4j
  driver / cypher-shell.
- Pass/fail: all five invariants hold for all three resolved questions.
- Dependency: F0 done; reseeded lexical store (post Phase D); KEY-* JOIN-KEY
  defects resolved (else invariant 2 sees 0 lemmas via INSTANCE_OF and
  false-fails; this is why F sits after Phase D/E, not before).
- Auditor-dispatchable: yes (pure read-only Cypher + deterministic in-process
  bundle build; no evidence write, no embed).

### F2 - context_builder triangle test, deep-hash sort (RESEED_PLAN F.2)

- Action: build the bundle for each resolved question TWICE on identical
  inputs. Serialise each bundle element and sort element lists by
  `sha256(json.dumps(element, sort_keys=True))` (deep-hash sort, NOT by id).
  Two runs are identical only if every field of every element matches
  byte-for-byte after the deep-hash sort.
- Command: an Auditor-caste runner: call
  `build_lexical_context_bundle(id)` twice, deep-hash-sort every list inside
  `lexical_context_bundle` (anchor_lemmas, anchor_verses, cross_refs,
  semantic_domain_neighbors, variant_units, syntactic_context), then assert
  `sha256(canonical_json(run1)) == sha256(canonical_json(run2))`. No such
  runner exists yet (gap G5); `pipeline2/triangle.py` is the Pipeline-2
  verdict triangle (Evidence objects), NOT the context_builder bundle
  triangle, so it is not reusable here.
- CI grep (RESEED_PLAN F.2, same as v2): every `LIMIT` in
  `pipeline2/context_builder.py` is preceded within 5 lines by an `ORDER BY`
  containing `elementId(` or a known-unique tuple. NOTE / gap G6: several
  queries in `context_builder.py` (`_query_anchor_verses`,
  `_query_variant_units`, `_query_syntactic_context`) use `LIMIT` with no
  preceding `ORDER BY`; the deep-hash sort in F2 compensates at compare time,
  but the CI-grep invariant as written does not pass against the current
  file. This is an ordering-determinism gap to surface to the orchestrator,
  not an auditor fix.
- Pass/fail: byte-identical bundles across the two runs for all three
  questions, after deep-hash sort.
- Dependency: F1 green.
- Auditor-dispatchable: yes (deterministic, read-only, no evidence write).

### F3 - Assert no evidence written

- Action: confirm `evidence/` is unchanged by Phase F (git status clean for
  `evidence/**`, no new `evidence/<id>.json`).
- Command: `git status --porcelain evidence/` returns empty for F's scope.
- Pass/fail: zero changes under `evidence/`.
- Dependency: F1 + F2 complete.
- Auditor-dispatchable: yes.

Phase F exit: F1 five invariants green for all three resolved questions, F2
deep-hash triangle byte-identical, F3 evidence untouched.

---

## Phase H: Final verification (Auditor caste, RESEED_PLAN section H)

Auditor subagent (Haiku per RESEED_PLAN caste table; allowed write
`docs/MANIFEST_VERIFICATION_<ts>.json` only). The Auditor MUST compute its
own observed values BEFORE reading `docs/RESEED_MANIFEST_<ts>.json`;
`tools/verify_manifest.py` enforces this structurally (it computes all
`observed` values first, parses the manifest only at the diff step).

GAP G7: no `docs/RESEED_MANIFEST_<ts>.json` exists in the repo today. Phase H
cannot run until the reseed (Phases D/E) emits its manifest. H is fully
specified here but is unrunnable until that manifest file is produced.

### Step count: 9 ordered steps (H0..H8). All auditor-dispatchable (script + Cypher re-execution + git-history scan); none requires a fresh ingest or embed (it re-checks the artifacts the reseed already produced).

### H0 - Manifest present

- Action: locate `docs/RESEED_MANIFEST_<ts>.json`.
- Pass/fail: file exists and is valid JSON with a `claims` array.
- Dependency: Phases D, E, F complete; reseed manifest emitted (gap G7).
- Auditor-dispatchable: yes.

### H1 - Independent manifest re-execution (RESEED_PLAN H.1)

- Action: run `tools/verify_manifest.py` which re-executes every claim
  (pytest / script / cypher / file_sha / grep) independently, writes its own
  observed values, and only then diffs against the manifest's `expected`.
- Command:
  `python tools/verify_manifest.py --manifest docs/RESEED_MANIFEST_<ts>.json
  --out docs/MANIFEST_VERIFICATION_<ts>.json`
- Pass/fail: exit 0; every claim `matches == true`;
  `MANIFEST_VERIFICATION_<ts>.json` and `RESEED_MANIFEST_<ts>.json` agree
  byte-for-byte on every claim value (RESEED_PLAN H.1 acceptance:
  disagreement -> fail).
- Dependency: H0.
- Auditor-dispatchable: yes (the script is the auditor tool; cypher claims
  are read-only `MATCH`).

H1 internally re-runs (RESEED_PLAN H.1 list), each a manifest claim:
per-adapter pytest; per-source count Cypher; per-collection point count;
triangle hash recompute; adapter-purity AST scan; `check_thresholds_immutable.py`;
`verify_no_deferral.py`; `check_caste.py` over full history since A.1. The
explicit per-step gates H2..H8 below pin the threshold for each so the
Auditor does not depend on the manifest authoring them correctly.

### H2 - Per-adapter pytest

- Command: `python -m pytest -q tests/lexical tests/embeddings tests/pipeline2`
  (the adapter coverage suites plus the embed-text and Pipeline-2 suites).
- Pass/fail: pytest exit 0; zero failures.
- Dependency: H1 dispatched.
- Auditor-dispatchable: yes.

### H3 - Per-source count Cypher vs expected_counts.json (phase_02 acceptance gate)

- Action: for every in-scope source, run its acceptance Cypher from
  `docs/implementation_phases/phase_02_lexical_ingest.md` and the per-source
  count, compare to `tools/expected_counts.json` at its tier tolerance
  (Tier A exact tol 0; Tier B +/-2% capped 1000; Tier C +/-5%).
- Command: re-run via the manifest `cypher` claims (H1); thresholds read
  from `tools/expected_counts.json`.
- Pass/fail: every source within its tier tolerance.
- Dependency: H1; reseeded lexical store reachable.
- Auditor-dispatchable: yes (read-only Cypher).

### H4 - Per-collection Qdrant point count + E.2 vector gates

- Action: re-assert `lex_col` point count is the canonical Lemma count and
  re-run the E.2 distinct-vector ratio (>= 0.999, divergent-gloss dup groups
  == 0) and the direction-dispersion non-degeneracy gate
  (mean pairwise cosine <= 0.95 AND pairwise-cosine stdev >= 1e-4, amended
  2026-05-19; the prior norm-stdev >= 0.001 floor was incompatible with the
  unit-normalized voyage-4-large model and is superseded).
- Command: `python tools/verify_live_stacks.py` covers the `lex_col` point
  count band only `[1, 25000]`; the E.2 gates run via
  `python tools/check_vector_quality.py` (gap G2 closed).
- Pass/fail: point count in band AND E.2 distinct-ratio + direction-
  dispersion pass.
- Dependency: Phase E complete; H1.
- Auditor-dispatchable: yes (read-only Qdrant scroll).

### H5 - Triangle hash recompute (Phase D.3 per-row presence vector)

- Action: run `python tools/snapshot_counts.py --out tmp/h_snap_1.json`
  then again `--out tmp/h_snap_2.json` over identical lexical-store inputs;
  compare `overall_hash`.
- Pass/fail: the two `overall_hash` values are identical (printed as
  `overall hash=<sha>`); any drift -> fail.
- Dependency: H1; lexical store quiescent (no writes between the two runs).
- Auditor-dispatchable: yes (read-only `MATCH`/`SHOW` only, by the tool's
  own docstring).

### H6 - Adapter-purity AST scan

- Command: `python tools/check_adapter_purity.py` over every file in
  `ingest/lexical/` (rejects subprocess, socket, httpx, requests, urllib,
  aiohttp, mmap, os.system, os.spawn*, posix_spawn,
  multiprocessing.connection, pty, pipes, winreg, ctypes, dynamic
  `__import__`).
- Pass/fail: exit 0; zero impure adapters.
- Dependency: H1.
- Auditor-dispatchable: yes.

### H7 - Threshold immutability + no-deferral

- Commands:
  - `python tools/check_thresholds_immutable.py` (expected_counts.json blob
    SHA equals A.4 baseline, or last change is `[SCHEMA-REVISION]` with the
    baseline moved in the same commit).
  - `python tools/verify_no_deferral.py` against
    `docs/implementation_phases/phase_02_lexical_ingest.md`,
    `docs/ARCHITECTURE.md`, `docs/SCHEMA_DECISIONS.md` (forbidden phrases:
    deferred, defer to, out of scope, v1.5, v2, future, TBD, FIXME, TODO,
    XXX, eventually, later).
- Pass/fail: both exit 0.
- Dependency: H1; the four `RECON-*` `[SCHEMA-REVISION]`s landed (else the
  immutability check still passes only if the baseline moved in the same
  tagged commit; an undeclared drift -> fail).
- Auditor-dispatchable: yes.

### H8 - check_caste over full history since A.1 (RESEED_PLAN H.1)

- Command: `python tools/check_caste.py --range <A.1-sha>..HEAD`
  (phase_02 acceptance uses `b4d1a1a..HEAD`; the A.1 sha is the Phase A.1
  schema-lock commit).
- Pass/fail: every commit in the range has a `Caste:` trailer whose declared
  caste matches its changed-file set; exit 0. Any commit crossing caste
  boundaries -> fail.
- Dependency: H1.
- Auditor-dispatchable: yes (git-history scan, read-only).

### H.2 - Procurement-list completeness (RESEED_PLAN H.2)

Folded into H1 as a manifest claim and re-stated here as a hard gate:

- Rule: every `procurement_required` entry in
  `docs/data_inventory_catalog.json` with `compatible_with_project == true`
  AND `deadend == false` has a corresponding adapter in the manifest with
  `status == passed`.
- Deadend allowance (H.2 rule): an entry is exempt ONLY if it has
  `deadend == true` plus `deadend_evidence` (URL + date + screenshot
  reference) plus user approval committed in `docs/DEADEND_APPROVALS.md`.
  The in-scope deadends per RESEED_PLAN procurement table:
  ECM Catholic Letters beyond 3 John (`explicit_deadends[0]`), Old Latin
  Vetus Latina, LXX Rahlfs standalone, DSS (revisited post 3 John pilot).
  3 John CBGM is IN scope (local asset `tmp/poc/cbgm/`), not a deadend.
- Pass/fail: zero non-deadend compatible procurement entries lack a passed
  adapter; every claimed deadend has the full evidence triple plus
  `docs/DEADEND_APPROVALS.md` approval.
- Dependency: H1; `docs/data_inventory_catalog.json` and
  `docs/DEADEND_APPROVALS.md` present.
- Auditor-dispatchable: yes (JSON + doc read; the manifest re-exec covers it).

Phase H exit: H1 byte-for-byte manifest agreement AND every explicit gate
H2..H8 plus H.2 green. Any single failure fails Phase H.

---

## 4. Gaps for the orchestrator (RESEED_PLAN E/F/H requirements currently unimplementable)

These are flagged, not invented around. Each blocks a specific gate.

- **G1 (Phase E, E1/E3) - embed-text enrichment columns not selected.**
  `embeddings/embed_lexical.py::_iter_lemmas` SELECTs only
  `strong, lemma, transliteration, gloss, license, redistribute`. The E.1
  contract and the panel tests require `pos`, `domain`, `louw_nida` so the
  distinct-token floor (>= 6) and 4-substring panel are met on REAL rows
  (the tests pass today only because the PANEL supplies pos/domain inline).
  Until `_iter_lemmas` is extended to project pos/domain/louw_nida from the
  Lemma nodes, the live E3 embed text will fall short of 6 distinct tokens
  for many rows. Owning caste: implementer (`embeddings/embed_lexical.py`,
  one-file edit). Also: `--limit` default 20000 may under-cover canonical
  Lemma count; the orchestrator must set `--limit` >= live Lemma count.

- **G2 (Phase E E4/E5, Phase H H4) - CLOSED.** `tools/check_vector_quality.py`
  is the read-only Qdrant-scroll gate. It computes
  `count(distinct sha256(vec))/count(*)` with the identical-gloss duplicate
  exception (>= 0.999) and, as amended 2026-05-19, the direction-dispersion
  non-degeneracy invariant (mean pairwise cosine <= 0.95 AND pairwise-cosine
  stdev >= 1e-4) which replaces the prior norm-stdev >= 0.001 floor. That
  floor was a gate/spec defect: voyage-4-large returns L2-unit-normalized
  vectors (norm stdev approximately 3.97e-08, COSINE distance), so a norm-
  variance floor is mathematically unpassable for the faithful embeddings;
  the embeddings were NOT altered. The script self-tests the rejection
  property (`--self-test`). E4, E5, and the E.2 half of H4 are runnable.

- **G3 (Phase F F0/F1) - two of three F.1 question ids do not exist
  verbatim.** `doc-canon-closed` exists. `baptism-mode` and
  `lords-supper-real-presence` are not `questions.json` ids. Faithful
  canonical candidates: `prc-baptism-by-immersion`;
  `doc-transubstantiation-denial` (or the real-presence cluster
  `doc-consubstantiation-affirm` / `doc-supper-spiritual-communion`). Owner
  decision required before F runs; the auditor must not guess.

- **G4 (Phase F F1 invariant 4) - no `not_in_ecm_scope` bundle flag.**
  `build_lexical_context_bundle` emits no `not_in_ecm_scope` marker. The
  empty-variant-set half of invariant 4 is checkable today; the flag half is
  not. Owning caste: implementer (`pipeline2/context_builder.py`) if the flag
  is required, else the orchestrator relaxes invariant 4 to the empty-set
  half only.

- **G5 (Phase F F1/F2) - no F invariant/triangle runner.** The five F.1
  Cypher invariants and the F.2 deep-hash bundle triangle have no single
  Auditor-caste runner. The Cypher and the bundle build are individually
  runnable; the orchestrator must dispatch an Auditor script that wires them
  (read-only, no evidence write). `pipeline2/triangle.py` is the Evidence
  triangle, not the context-bundle triangle, and is not reusable for F2.

- **G6 (Phase F F2 CI grep) - context_builder LIMIT not ORDER BY-guarded.**
  `_query_anchor_verses`, `_query_variant_units`, `_query_syntactic_context`
  in `pipeline2/context_builder.py` use `LIMIT` with no preceding
  `ORDER BY ... elementId(...)`. The F.2 CI-grep invariant as written fails
  against the current file. The deep-hash compare compensates at test time,
  but the determinism-of-truncation risk is real (a non-deterministic LIMIT
  set can flip across runs). Owning caste: implementer
  (`pipeline2/context_builder.py`) to add stable `ORDER BY` before each
  `LIMIT`; or the orchestrator accepts the deep-hash compare as the
  determinism gate and formally drops the CI-grep sub-rule for these three
  queries.

- **G7 (Phase H, all steps) - no RESEED_MANIFEST.** No
  `docs/RESEED_MANIFEST_<ts>.json` exists. Phase H is fully specified but
  unrunnable until the reseed (Phases D/E) emits its manifest of claims.
  Owning caste: the reseed phase that writes the manifest (architect/
  orchestrator), not the auditor.

None of G1..G7 is an auditor fix; all are surfaced for the orchestrator to
route to the correct caste before the corresponding gate can pass.

---

## 5. Auditor-dispatchable vs live-run summary

| Phase | Steps | Auditor-dispatchable (pure Cypher/script) | Requires live ingest/embed |
|---|---|---|---|
| E | E0,E1,E2,E4,E5 | E0,E1,E2 fully; E4,E5 once G2 script exists | E3 (real Voyage embed + Qdrant write) |
| F | F0,F1,F2,F3 | all (read-only Cypher + deterministic bundle; no evidence write) | none |
| H | H0..H8 + H.2 | all (re-checks reseed artifacts; read-only) | none (depends on E/F outputs already produced) |

Cross-reference lock: **Phase E does not start until the Phase D master
ledger (`docs/PHASE_D_MASTER_LEDGER.md`) shows D.4 count gate green, the
triangle test green, and the per-edge gate green, with the EDGE-PERF wave +
ORD-MGNT integrated and 7eb0b7a verified.** Phase F follows Phase E. Phase H
follows Phases D, E, F and requires the reseed manifest (gap G7).
