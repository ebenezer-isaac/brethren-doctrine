# Phase D Autonomous Owner-Decision Log

Recorded by the orchestrator while the owner was AFK with the directive
"finish everything, do not defer, do not reduce quality, parallelize".
Every decision below follows the brethren-on-trial discipline (trust the
faithful real parse, fix the demonstrably-wrong catalog, never fudge an
adapter) and the pattern the owner explicitly approved for the original 7
catalog reconciliations. All are reversible by the owner.

1. A2 morphgnt PARSE_OF join: Option A (macula_greek emits an indexed
   osis_wpos alias; Word.id stays the TEI xml:id anchor; morphgnt matches
   the alias). Rationale: fail-closed (a bad map drops the edge, never
   mislinks), retains the xml:id anchor, positions proven 1:1 over 7927
   shared verses. Implemented commit f23186a (T17), index 4f6602e.
   Reversible: revert T17 + index, choose Option B.

2. Catalog reconciliation set #3 [SCHEMA-REVISION] commit 7429865:
   ETCBC-phono 426590 -> 420166 (Option A re-baseline; 6424 null slots are
   the faithful assimilated-definite-article class), STEPBible-TFLSJ
   11034 -> 9488, STEPBible-morph-codes 2782 -> 2675, ETCBC-parallels
   8246 -> 5914. Each is the identical proven naive-line-count / wrong-
   record-unit class as the original 7 the owner approved; adapters are
   faithful and unchanged. Reversible: a follow-on [SCHEMA-REVISION].

3. E1/E2 GreekLemma/Lemma population unification: NOT performed. Decision
   18 canonical .strong join makes every Strong-keyed join resolve without
   merging the disjoint macula_hebrew / macula_greek / ttesv lemma node
   populations. Population unification remains an open owner data-model
   choice; the conservative faithful default (keep populations, canonical
   .strong join) is in effect and does not block Phase D. Reversible.

4. Phase F question-id binding (G3): doc-canon-closed is verbatim;
   baptism-mode bound to prc-baptism-by-immersion (unambiguous, the only
   mode-of-administration entry); lords-supper-real-presence bound to
   doc-transubstantiation-denial (the entry whose proposition IS the
   real-presence axis; auditor-recommended canonical pole). The owner may
   re-bind the lords-supper pole (doc-consubstantiation-affirm /
   doc-supper-as-memorial / doc-supper-spiritual-communion are the
   alternate poles). See docs/PHASE_F_QUESTION_ID_MAP.md. Reversible.

5. Lexical store wiped (token-gated tools/wipe_lexical.py) and pass-1
   re-ingested from a clean slate: required because the partial graph was
   contaminated with pre-fix adapter output that idempotent MERGE would
   not clean. Schema re-applied (36 constraints, key indexes ONLINE).

Open items explicitly surfaced for the owner (not blocking the reseed):
- F.1 invariant #2 (lemma completeness) has no modulo-LIMIT carve-out but
  pipeline2 context_builder applies ANCHOR_LEMMA_LIMIT; the F.1 runner
  tool implements the strict invariant and FAILS if the builder caps
  lemmas. Architect/owner must reconcile invariant vs builder at Phase F.
- cultural_data_inventory_catalog.json Ecumenical-Creeds notes contain a
  "deferred to v1.5" phrase (in the catalog data, not a decision doc);
  flag for cultural-side reconciliation in Phase G.
- lords-supper-real-presence pole binding (item 4) is the one genuine
  owner doctrinal choice; defaulted faithfully, awaiting confirmation.

## Phase D relaunch defect fixes (autonomous, brethren-on-trial)

6. macula_hebrew BRIDGES_LXX (commit 3dc79ee): the relaunch died on a
   real-Neo4j SemanticError, MERGE of a relationship with a null pattern
   property greek_strong. The orchestrator hypothesis (drop null rows) was
   REJECTED by the implementer per Decision 4: a null greekstrong with a
   populated greek is a meaningful bridge routed to the sentinel
   GreekLemma macula-hebrew-greek-lemma:unknown and must NOT be dropped.
   Faithful fix applied: nullable greek_strong/greek_surface moved OUT of
   the MERGE pattern into a post-MERGE SET, identity stays Hebrew->Greek
   pair plus source. Zero bridges dropped, count rule unchanged.
   Reversible.

7. theographic entity_id (commit 5b4e29d): same null-property-in-MERGE
   class, IDENTITY-bearing per Decision 10 (cannot move to SET). Empirical
   check of the frozen upstream found ZERO null-id records (all 4849 carry
   a recXXXX id), so the defect was latent, not triggered on current data.
   Faithful Decision-10 guard added: a record with no canonical or
   Decision-10-derivable entity_id is faithfully excluded and surfaced
   (counted, not silent), never null-MERGEd, never sentinel-collapsed.
   Zero records excluded on frozen upstream, emitted counts unchanged
   (4849 entities). Defensive against upstream drift. Reversible.

8. Node-MERGE constraint coverage (commit d41cea0, architect): relaunch
   attempt 1 was killed for a quadratic NodeByLabelScan on
   MERGE (n:MaculaToken {id}) because graph/lexical.cypher had no
   MaculaToken constraint. Exhaustive audit of all 28 node-MERGE
   signatures found MaculaToken.id the sole gap; maculatoken_id UNIQUE
   added; EXPLAIN proven NodeByLabelScan -> NodeUniqueIndexSeek at scale.
   Relaunch attempt 2 then validated index-backed throughput (~5000x).

## Phase D relaunch attempt 3 defect fix (autonomous, brethren-on-trial)

9. macula_greek canonical_strongs (commit b270a9c): relaunch attempt 3
   cleared oshb, macula_hebrew, bhsa, etcbc_phono, etcbc_parallels then
   died in macula_greek with ValueError unrecognized Strong encoding
   15374053. Root cause: ingest.canonical_strongs raises (no sentinel)
   and macula_greek called it uncaught; the value is a compound crasis
   Strong (1537+4053 digit-stripped), 11 rows total (Nestle1904 6,
   SBLGNT 5). Decision 18 forbids a hand-rolled compound split and
   forbids fabricating a Strong. Faithful fix applied: try/except
   ValueError to None, the GreekLemma and its INSTANCE_OF are skipped
   for those 11 rows (Word still emitted, raw int Word.strong per
   Decision 2 untouched, node id unaffected), surfaced via an
   _unresolved_strong count plus a deterministic stderr line, mirroring
   the macula_hebrew pattern. Word counts unchanged and exact
   (Nestle1904 137779, SBLGNT 137741). An audit
   (docs/PHASE_D_CANONICAL_STRONGS_AUDIT.md) confirmed the other 8
   canonical_strongs callers were already guarded, so this class is
   contained. Reversible.

## Phase D.4 verse-key + edge-counts integration (architect, brethren-on-trial)

10. The 9 D.4 / verse-key adapter fixes integrated onto main by
    cherry-pick, each touching exactly one ingest/lexical adapter,
    disjoint, no conflicts (origin SHA -> new main SHA):
    - 2d6fc52 -> 9f008cf stepbible_tvtms.py (emits all 1308 faithful
      TVTMS rows, was dropping 8; id-disambig)
    - 704523d -> d5edf37 openbible.py (OPENBIBLE_CROSS_REF resolves all
      faithful Verse endpoints + two-part range; was 139829/344799)
    - af75380 -> 281988b etcbc_parallels.py (PARALLEL_OF resolves Verse
      endpoints, Decision 15; was 0/5914)
    - ac2c5ff -> 69f8a6b stepbible_tagnt.py (IN_VERSE re-keys to
      universal Verse.id, was osisID NULL on all NT)
    - 74b26b0 -> 91d37f2 stepbible_tahot.py (IN_VERSE re-keys to
      universal Verse.id, Decision 15)
    - 33c4b58 -> 6436827 theographic.py (MENTIONS re-keys to universal
      Verse.id, was losing NT mentions)
    - fa5af7b -> 4e0deef stepbible_proper_nouns.py (NAMED_AT re-keys to
      universal Verse.id, stops phantom Verse stub creation)
    - d7d79e2 -> 3c2b179 peshitta.py (IN_VERSE re-keys to universal
      Verse.id, Decision 15)
    - 99967a2 -> 2fb96fe coptic_scriptorium.py (IN_VERSE re-keys to
      universal Verse.id, Decision 15)
    All faithful, no adapter fudged to a wrong catalog number.

11. ETCBC-parallels [SCHEMA-REVISION] (commit 351d7ee): sources
    expected_count/min/max 5914 -> 5882, tier A tol 0, record_unit
    stays parallel_edge. PARALLEL_OF is Verse-to-Verse (crossref.tf
    node ids are BHSA verse-otype text-fabric nodes, not BhsaWord word
    slots; FIX-PARALLELS re-keyed endpoints to the canonical Verse
    node, Decision 15). Faithful single-target edges after the
    Decision 3 single-comma split (2332 multi-target/non-digit rows
    quarantined, 5914 single-target) with 32 exact-duplicate directed
    (source, target) pairs collapsed by the binding idempotent MERGE
    (contract section 6). Same idempotent-MERGE-collapse class as the
    Phase D reconciliation set; adapter faithful, NOT changed (the
    MERGE idempotency was deliberately not weakened to inflate back to
    5914).

12. edge_counts taxonomy reconciled (commit 351d7ee): every key
    renamed to the rel-type the committed adapters actually emit and
    bands re-based to the faithful values per
    docs/PHASE_D_EDGECOUNTS_RECONCILE.md Finding 3
    (HAS_CROSS_REF->CROSS_REF, HAS_LOUW_NIDA_DOMAIN->IN_DOMAIN,
    HAS_PHRASE->CONTAINS_PHRASE, HAS_VARIANT_UNIT->VARIANT_UNIT_NODE,
    HAS_READING->ATTESTED_BY, GLOSSES_GREEK_LEMMA->BRIDGES_LXX rebanded
    to the distinct-pair emit, HAS_CLAUSE->BHSA_CLAUSE_NODE rebanded to
    the clause-otype node count, IS_PROPER_NOUN->NAMED_AT rebanded to
    the faithful emit, HAS_PARALLEL->PARALLEL_OF rebanded tol-0-aligned
    to the reconciled 5882). edge_counts["HAS_SDBH_DOMAIN"] RETIRED
    entirely: no committed adapter emits any SDBH edge, no Decision
    contracts it, no schema constraint provisions it; SCHEMA_DECISIONS
    .md has zero "sdbh" occurrences across all 18 decisions and the
    catalog backref to Decision 1/2 is unfounded. Under the project
    authority hierarchy (SCHEMA_DECISIONS = contract, catalog =
    implementation) an uncontracted catalog edge key is the artifact
    to retire, not a capability silently dropped (it was never
    contracted). OWNER-FLAG: the upstream sdbh data genuinely exists
    (244734 sdbh-non-null morphemes, inside the old band); if an SDBH
    semantic-domain overlay is wanted in v1 it requires a NEW architect
    Decision (new node label + constraint + adapter edge emit +
    verifier + re-ingest). Surfaced for owner, NOT autonomously
    invented.

13. E1 SURFACED (MUST-ESCALATE, real defect): data/private/stepbible/
    tvtms.parsed.json is incomplete relative to its own frozen raw
    upstream Condensed section. The Joel 2:28-32 = Joel 3 Hebrew,
    Jonah 1:17 = Jonah 2:1, and Deut 12 KJV-Hebrew shift rows exist in
    the frozen raw TVTMS Condensed section but were dropped by the
    now-quarantined dead procurement parser when it serialized the
    artifact. This is a real procurement defect being fixed faithfully
    in parallel (a producer plus consumer change with per-verse range
    expansion, not a naive catalog reconcile). Consequently the
    openbible sources count 344799, the STEPBible-TVTMS sources count
    1308, and the edge_counts[OPENBIBLE_CROSS_REF] band are HELD (not
    reconciled in commit 351d7ee) pending the E1 fix and relaunch-5
    re-D.4 once the true faithful counts are known. Reconciling
    ETCBC-parallels and the edge_counts taxonomy does not depend on E1
    and proceeded now.

## Phase D.4 reconcile finalization + E1 owner ticket

14. OpenBible-cross-refs reconciled 344799 -> 342130 ([SCHEMA-REVISION],
    this commit). Faithful given the contracted TVTMS artifact
    tvtms.parsed.json (pinned at 1308 by expected_counts.json Tier-A,
    data_inventory_catalog.json, and the adapter docstring). FIX-OPENBIBLE
    (Verse.id key + range-collapse) recovers 139829 -> 342130; the 2669
    residual are genuine KJV-Hebrew versification shifts (Joel 2:28-32,
    Jonah 1:17, Deut 12:32 class) ABSENT from the contracted artifact
    because the quarantined procurement parser dropped the raw upstream
    Condensed-section range rows. openbible faithfully quarantines them,
    never fabricates. STEPBible-TVTMS stays faithful at 1308 (FIX-TVTMS
    makes the adapter emit the full contracted artifact incl the 8
    duplicate-disambiguated rows).

    OWNER TICKET E1 (non-blocking, surfaced with byte evidence in
    docs/PHASE_D_EDGECOUNTS_RECONCILE.md Finding 1 and the E1 STOP
    report): re-procuring/parsing the COMPLETE real upstream TVTMS
    Condensed section (recovering ~2669 openbible cross-refs toward
    344799, and improving peshitta/coptic/tsk versification projection)
    is an irreducibly multi-file producer+consumer change
    (stepbible_tvtms.py re-parse + openbible/tsk per-verse range
    expansion + expected_counts.json + data_inventory_catalog.json +
    the verifier EXPECTED_RULE_COUNT) requiring two owner rulings:
    (a) the committed-artifact-vs-raw-source contract, and (b) the
    range / Absent / NoVerse / Psalm-Title / multi-ref row-scope and
    per-verse-expansion semantics (the versification backbone - any
    autonomous guess silently mis-maps cross-version refs). Deferred to
    owner decision; does NOT block Phase D.4 or the reseed.

    OWNER TICKET E2 (non-blocking): HAS_SDBH_DOMAIN retired from the
    catalog (uncontracted vs SCHEMA_DECISIONS, which has zero SDBH). The
    MACULA-Hebrew sdbh data exists (~244734 non-empty, rate 0.514). If
    an SDBH semantic-domain overlay is wanted in v1 it requires a NEW
    architect Decision (Decision + SdbhDomain label + constraint +
    macula_hebrew emit + verifier + re-ingest); not autonomously
    invented per caste discipline.

## 2026-05-19 OpenBible cross-ref count gate correction (architect, [SCHEMA-REVISION], brethren-on-trial)

    DECISION: corrected the OpenBible-cross-refs catalog figure in
    tools/expected_counts.json from 342130 to 342128, in both
    sources["OpenBible-cross-refs"] (expected_count, min, max all tier-A
    tol-0) and the internally-consistent edge_counts["OPENBIBLE_CROSS_REF"]
    band (expected_min, expected_max), exactly as PARALLEL_OF mirrors the
    reconciled ETCBC-parallels source value. Regenerated the baseline
    lock tools/expected_counts.baseline; check_thresholds_immutable.py
    passes exit 0 with target_sha == baseline_sha == 3a62c1f1f771.

    ARITHMETIC ROOT CAUSE: the prior 342130 was set at FIX-OPENBIBLE
    (commit 704523d) as 344799 raw - 2669 unresolved = 342130. That
    subtraction OMITTED the 2-edge idempotent-MERGE-collapse term. The
    faithful ingest deterministically lands 344799 - 2 idempotent-collapse
    - 2669 KJV-Hebrew versification shifts = 342128. The 2 collapsed
    rows are exact-duplicate directed verse-pairs that the binding
    idempotent MERGE on {from_osis, to_osis, source} collapses by design;
    the 2669 are the genuine Joel/Jonah/Deut KJV-Hebrew shift rows the
    adapter faithfully quarantines (never stubs).

    PRECEDENT: this is the IDENTICAL idempotent-MERGE-collapse class the
    catalog already applies to the sibling source ETCBC-parallels
    (5914 -> 5882 via a documented 32-pair collapse) and the Phase D
    reconciliation set. The catalog applied the collapse term to
    ETCBC-parallels but omitted it for OpenBible. This is a catalog
    arithmetic error, not a parse defect.

    BRETHREN-ON-TRIAL: trust the faithful parse, correct the
    demonstrably-wrong catalog. The openbible adapter is faithful and was
    NOT changed; weakening its MERGE idempotency to inflate back to 342130
    would fabricate 2 duplicate edges. NO adapter, run.py, ingest code,
    or graph data was changed. Only tools/expected_counts.json,
    tools/expected_counts.baseline, and this log were touched.

    EVIDENCE: independent read-only auditor report
    docs/AUDIT_phase_d4_count_gate.md (Task 4 openbible section, live
    graph 342128 confirmed against the frozen lexical Neo4j, read-only
    adapter parse replay against the consumed tvtms.parsed.json). The E1
    owner-decision TVTMS-completeness ticket (recovering the ~2669 shift
    rows toward 344799) is unaffected and remains a separate follow-on.

## 2026-05-19 D.3 INSTANCE_OF non-idempotency: run.py DATASETS reorder (architect, brethren-on-trial)

    DECISION: reordered the ingest/lexical/run.py DATASETS dispatch list so
    the {strong}-keyed Lemma / GreekLemma endpoint producers run BEFORE the
    {strong}-keyed TaggedToken consumers. The dispatch order in run.py is a
    schema/contract artifact (it encodes the Group 1 -> Group 2 -> Group 3
    dependency contract of docs/implementation_phases/phase_02_lexical_ingest
    .md and the Dependencies docstring sections of tahot/tagnt/ttesv/tbesh),
    so the change is recorded here as an architectural ordering decision.

    EXACT REORDER: stepbible_ttesv, stepbible_tbesh, and (defensively)
    stepbible_tbesg were moved from positions 11, 12, 13 to positions 9, 10,
    11, immediately after stepbible_morph_codes and immediately BEFORE
    stepbible_tahot and stepbible_tagnt. New full order:
    oshb, macula_hebrew, bhsa, etcbc_phono, etcbc_parallels, macula_greek,
    morphgnt, stepbible_morph_codes, stepbible_ttesv, stepbible_tbesh,
    stepbible_tbesg, stepbible_tahot, stepbible_tagnt, stepbible_tflsj,
    stepbible_proper_nouns, stepbible_tvtms, peshitta, coptic_scriptorium,
    vulgate_clementine, open_cbgm_3_john, openbible, tsk, theographic.

    ROOT CAUSE (D.3): stepbible_tahot.py resolves its INSTANCE_OF endpoint
    with MATCH (b:Lemma {strong: row.to_id}) and stepbible_tagnt.py with
    MATCH (b:GreekLemma {strong: row.to_id}). The {strong}-keyed Lemma /
    GreekLemma floor is only fully minted once stepbible_tbesh (a Lemma
    {strong} producer) and stepbible_ttesv (a net-new GreekLemma {strong}
    producer) have run, but in the prior order those producers ran AFTER the
    consumers. On a single fresh pass tahot/tagnt MATCHed nothing for the
    affected rows so the MERGE rel was silently skipped; a second pass (no
    wipe) found the now-existing endpoints and completed them, making the
    ingest non-idempotent on a single fresh pass and failing the triangle
    test. FakeDriver did not surface this because it does not model
    MATCH-finds-nothing-so-MERGE-rel-skipped.

    ARITHMETIC: tagnt -> GreekLemma minted by ttesv = 99,811; tahot ->
    Lemma{strong} minted by tbesh = 6,965; 99,811 + 6,965 = 106,776. This
    equals the observed pass1 -> pass2 INSTANCE_OF growth exactly
    (2,025,687 - 1,918,911 = 106,776). After the reorder a single fresh
    pass lands all 106,776 edges and a second pass is a true no-op.

    DIAGNOSIS REFERENCE: full read-only diagnosis with live-graph
    quantification and the containment scan is
    docs/PHASE_D3_INSTANCEOF_NONIDEMPOTENT.md (recommended fix Option (a),
    section 9).

    DEPENDENCIES PRESERVED: macula_greek still precedes morphgnt (Decision
    A2 / ORD-MGNT PARSE_OF osis_wpos join, item 1); the
    oshb -> macula_hebrew -> bhsa -> etcbc_phono -> etcbc_parallels relative
    order is unchanged; stepbible_morph_codes still precedes the tagged-token
    adapters; ttesv still mints its own Lemma/GreekLemma before its own
    INSTANCE_OF, tbesh still mints its Lemma in the same batch as its
    LEX_FOR, and tbesg/tflsj still find the macula_greek GreekLemma floor.
    Every MATCH-endpoint-then-MERGE-rel template in the section-7
    containment scan still has its endpoint producer running before its
    consumer.

    BRETHREN-ON-TRIAL: NO adapter Cypher was changed (Decision 18 producer
    authority forbids the consumer minting endpoint lexeme nodes; the
    adapter Cypher is correct given a correct dispatch order). No data is
    fabricated and none is lost: the same source-tagged nodes exist, only
    WHEN they are minted relative to the consumers changed. The reorder
    touches only ingest/lexical/run.py (the DATASETS list; no _run_one body,
    import, adapter, expected_counts, or test changed) and this log. The
    section-6 non-unique GreekLemma.strong fan-out and the tbesg/tflsj
    lemma-identity question remain SEPARATE architect items, out of D.3
    scope, and were NOT folded into this fix.

    CASTE NOTE: the mechanical run.py edit is implementer-caste
    (ingest/lexical/*.py) and this decisions-log entry is architect-caste
    (docs/PHASE_*.md). check_caste forbids crossing castes in one commit and
    no single caste's allowed_globs covers both files, so the fix lands as
    two disjoint commits (run.py under Caste: implementer, this log under
    Caste: architect), mirroring the item-10 per-adapter-cherry-pick +
    separate-architect-log precedent.

## 2026-05-19 E.2 norm-variance floor replaced by direction-dispersion (architect, brethren-on-trial)

    DECISION: replaced the RESEED_PLAN E.2 second invariant. The prior
    invariant was a vector-norm variance floor,
    stdev([norm(v) for v in sample]) >= 0.001, intended to reject a store
    where "all vectors point the same direction". It is replaced (NOT
    merely deleted) by a model-appropriate direction-dispersion non-
    degeneracy test: over a random sample of disjoint vector pairs,
    mean(pairwise_cosine) <= 0.95 AND pstdev(pairwise_cosine) >= 1e-4.
    The distinct-vector-ratio invariant (>= 0.999 with the identical-gloss
    duplicate exception) is UNCHANGED and continues to pass at 1.0.

    DEFECT (gate/spec, not embedding): the embedding model is
    voyage-4-large, which returns L2-UNIT-NORMALIZED vectors by
    construction; the lexical Qdrant collection correctly uses COSINE
    distance, for which the vector norm is irrelevant by design. Every
    stored norm is approximately 1.0 with only float32 jitter, so a
    "norm stdev >= 0.001" test is mathematically impossible to pass for
    ANY unit-normalized embedding model. It is therefore the wrong
    degeneracy proxy, the same class of defect as the earlier openbible
    catalog-arithmetic error: the faithful data is correct, the gate was
    wrong. embed_lexical.py and embeddings/bootstrap.py perform NO
    normalization; vectors are stored exactly as Voyage returns them.

    EVIDENCE: docs/AUDIT_phase_e_vector_quality.md (independent read-only
    auditor) measured vector L2-norm population stdev 3.97479e-08
    (mean approximately 1.0) and distinct-vector ratio 1.000000 (0
    penalised duplicates, 0 zero/NaN/Inf vectors) over the live lex_col.
    An independent re-measure for this decision (read-only scroll,
    512-point sample) gave norm min 0.99999999, max 1.00000026, mean
    1.00000013, population stdev 4.108e-08, dim 2048. Direction-
    dispersion on a 4000-point live sample: mean pairwise cosine
    0.484880, pairwise-cosine stdev 0.12215 (distinct ratio 1.000000).

    REPLACEMENT INVARIANT + THRESHOLDS + RATIONALE: for a unit-normalized
    COSINE store, degeneracy is DIRECTION collapse, detected directly via
    pairwise cosine over disjoint random pairs (fixed seed -> deterministic
    verdict). Thresholds: mean pairwise cosine <= 0.95 (live approximately
    0.483; a constant-direction or near-collinear store pins this to
    approximately 1.0) and population stdev of pairwise cosine >= 1e-4
    (live approximately 0.125; a collapsed store collapses this to 0.0
    to approximately 1.8e-11). Both conditions must hold; either failing
    flags degeneracy. Each threshold sits roughly three orders of
    magnitude clear of both the healthy value and the degenerate value,
    so it cannot be tripped by a healthy store nor passed by a collapsed
    one. VALIDATED that the test still FAILS a genuinely collapsed
    collection: tools/check_vector_quality.py --self-test now includes a
    constant-direction case (2000 distinct-magnitude same-direction
    vectors, each unique gloss so distinct-ratio passes at 1.0; gate
    correctly rejects, cos_mean 1.0, cos_stdev 0.0) and a near-collinear
    unit-vector case (fixed direction plus float jitter; gate correctly
    rejects, cos_mean 1.0, cos_stdev 1.52e-14). Both are precisely the
    family the deleted norm floor was meant to catch but, for a unit-
    normalized model, never could. Self-test exits 0; the amended gate
    run over the faithful live lex_col returns OK.

    EMBEDDINGS NOT ALTERED: no de-normalization, perturbation, or any
    change to embeddings/embed_lexical.py, embeddings/bootstrap.py, the
    stored vectors, the collection, expected_counts.json/.baseline,
    adapters, or the graph. De-normalizing the faithful unit vectors to
    satisfy the broken test would degrade COSINE retrieval and fabricate
    a property the model does not produce, the exact fudge brethren-on-
    trial forbids.

    SCOPE: tools/check_vector_quality.py (the gate, including its module
    docstring and self-test) is implementer-z1 caste (tools/*.py). The
    spec/contract edits docs/implementation_phases/RESEED_PLAN.md (E.2
    text + summary table), docs/PHASE_EFH_EXECUTION_SPEC.md (E5, Phase E
    exit, H4, gap G2) and this log entry are architect caste
    (docs/implementation_phases/*.md, docs/PHASE_*.md). check_caste
    forbids crossing castes in one commit and no single caste's
    allowed_globs covers both the tools/ script and the docs/, so the fix
    lands as TWO disjoint caste-correct commits (the gate under
    Caste: implementer-z1, the spec/decisions docs under Caste: architect),
    mirroring the immediately-preceding run.py-reorder split and the
    item-10 separate-architect-log precedent. Reversible by the owner.

## 2026-05-19 Phase G cultural gate: D10/D11/D19 work_id doc-drift + STEM bound ([SCHEMA-REVISION], architect, brethren-on-trial)

15. Phase G cultural acceptance gate honesty correction. Evidence:
    independent read-only auditor report docs/AUDIT_phase_g_cultural_gate.md
    (Notes B and C, plus the Decision 1-20 triangle table rows 10, 11, 19,
    20). Two demonstrably-wrong NON-DATA contract literals were making the
    gate dishonest. The live cultural data is faithful and was NOT altered;
    only the wrong doc/catalog literals were corrected to the faithful
    reality. Brethren-on-trial: trust the faithful parse and the adapters'
    real constants, fix the demonstrably-wrong contract text, never widen
    merely to pass.

    A. DOC-DRIFT, three acceptance-query work_id literals in
    docs/CULTURAL_SCHEMA_DECISIONS.md corrected to the adapters' actual
    emitted constants (verified in source):
      - Decision 10 Cypher acceptance query: '1689-lbc' -> 'lbc-1689'
        (ingest/cultural/lbc_1689.py:17 WORK_ID = "lbc-1689").
      - Decision 11 Cypher acceptance query: '39-articles' -> 'articles-39'
        (ingest/cultural/articles_39.py:16 WORK_ID = "articles-39"); the
        'bcp-1662' literal in the same IN list was already correct and was
        left untouched.
      - Decision 19 Cypher acceptance query: 'hopko.orthodox-faith' ->
        'oca-hopko' (ingest/cultural/oca_hopko.py:19 WORK_ID = "oca-hopko").
    Only the wrong work_id string literals inside the three "#### Cypher
    acceptance query" blocks were changed. NO invariant logic, threshold,
    Rule prose, edge-case text, or any other Decision was modified (the
    Rule prose still narrates the old source-side work_id phrasing as
    historical Rule text; only the executable acceptance query, which must
    bind the real graph, was corrected, matching the auditor's stated fix
    locus). Live read-only re-verification against the cultural store
    (bolt 7689, NEO4J_CULTURAL_*): Decision 10 returns sections=159
    distinct_anchors=159 anchors_unique_ok=true; Decision 19 returns
    articles=200 distinct_anchors=200 anchors_unique_ok=true; Decision 11
    binds both works (articles-39=39 chunks, bcp-1662=13 chunks, two
    distinct anglican works present, the intended invariant true), exactly
    as docs/AUDIT_phase_g_cultural_gate.md row 11 reported. Before the fix
    all three queries returned EMPTY on the stale literal; after the fix
    they bind the faithful graph. The per-row count(wid)=2 rendering of
    the Decision 11 query as authored is a pre-existing Cypher-aggregation
    syntax artifact of the doc query (same class the auditor flagged for
    the Decision 7 SHOW...YIELD chain at lines 125-133), not a data
    failure and out of scope for a literal-only correction.

    B. CATALOG bound, docs/cultural_data_inventory_catalog.json source
    STEM-Publishing-Brethren live_corpus_bound upper bound corrected
    [50, 10000] -> [50, 20000]. Justification (principled, not a barely-fit
    to the observed 12595): the stem_publishing adapter's own design
    contract caps a live crawl at MAX_CHUNKS = 20000
    (ingest/cultural/stem_publishing.py:34), the documented faithful crawl
    envelope already recorded in this source's catalog notes ("Live crawl
    MAX_CHUNKS 20000, MAX_WORKS_PER_AUTHOR 80"). The old upper of 10000 was
    demonstrably narrower than the adapter's own coded ceiling, so it would
    false-fail a faithful within-contract corpus (live 12595, inside the
    20000 design envelope). The upper bound is aligned to the adapter
    MAX_CHUNKS contract value, not to 12595. The lower bound 50 is
    unchanged. NO other source's bound, no Augsburg bound (its count miss
    is a separate pre-logged owner ticket, not widened here), and no
    adapter, harness, embedding, graph, evidence file, or any faithful
    live data was touched.

    IMMUTABILITY: tools/check_thresholds_immutable.py locks ONLY the
    lexical tools/expected_counts.json (against tools/expected_counts.baseline);
    docs/cultural_data_inventory_catalog.json has no baseline lock and is
    not in that tool's scope, so no cultural baseline regeneration applies
    (and the lexical baseline/json were deliberately NOT touched). Both
    changed files (docs/CULTURAL_SCHEMA_DECISIONS.md,
    docs/cultural_data_inventory_catalog.json) plus this log entry are
    architect caste under check_caste.py; a single [SCHEMA-REVISION]-tagged
    Caste: architect commit is the sanctioned mechanism, the same as the
    lexical OpenBible catalog correction precedent commit c1464f2. No
    caste split needed (all three paths are in the architect allowed set).
    Reversible by the owner.

## 2026-05-19 GAP G7 closed: Phase H reseed manifest emitted (architect, brethren-on-trial)

GAP G7 (docs/PHASE_EFH_EXECUTION_SPEC.md section 4 and Phase H notes:
"no docs/RESEED_MANIFEST_<ts>.json exists; Phase H is fully specified but
unrunnable until the reseed emits its manifest of claims") is now closed.
Phases D/E/F/G are all GREEN per their rev2 audits but never emitted the
manifest, so Phase H step H0 (manifest present) failed. The reseed-phase
CLAIM file is now authored.

MANIFEST: docs/RESEED_MANIFEST_20260519T161126Z.json, 25 claims, top-level
{manifest_version, generated_utc, head_sha, phase, provenance, claims}.
Schema validated by a dry parse against tools/verify_manifest.py
evaluate_claim (every claim has id/description/check_kind/expected/
actual_field plus the kind-specific keys: pytest->selector, script->argv,
cypher->query+database, file_sha->path, grep->path+pattern; no duplicate
ids; grep regexes compile under re.MULTILINE). The claim set mirrors the
docs/PHASE_EFH_EXECUTION_SPEC.md H1 list plus the H2..H8 + H.2 per-step
pins; no claim was invented beyond the spec enumeration. Breakdown:
1 pytest (H2 adapter suites), 15 cypher (H3 per-source/edge + INSTANCE_OF
completeness + H.2/Phase-G cultural counts), 6 script (H7
check_thresholds_immutable, H7 verify_no_deferral, H6 check_adapter_purity,
H8 check_caste full-history range, H5 snapshot determinism, H4 vector-
quality gate), 1 file_sha (H7 expected_counts.json lock), 2 grep (H7
no-deferral phase_02, H.2 procurement no-unapproved-deadend).

EXPECTED PROVENANCE (every value sourced from a named committed
artifact/audit; nothing queried by the author to set expected; nothing
back-fitted to make a check pass):

- per-source counts (MaculaToken 475911, OSHB Word 305507, TAHOT 283721,
  TAGNT 142096, TVTMS 1308): tools/expected_counts.json reconciled tier-A
  tol-0 expected_count, confirmed live-exact (delta 0) in
  docs/AUDIT_phase_d4_count_gate_rev2.md Task 2/3/4.
- OPENBIBLE_CROSS_REF 342128, PARALLEL_OF 5882: tools/expected_counts.json
  edge_counts (expected_min == expected_max) and sources['ETCBC-parallels'];
  confirmed in docs/AUDIT_phase_d4_count_gate_rev2.md and
  docs/AUDIT_phase_d4_edge_correctness_rev2.md section 1.
- INSTANCE_OF 2025687: docs/AUDIT_phase_d4_edge_correctness_rev2.md graph
  fingerprint (not a catalog gate; recorded rev2 audit topology figure).
- cultural CulturalChunk 60040 / HAS_CHUNK 60040 / Work 390 / Doctrine 26 /
  Question 231 / UNDER_QUESTION 231 / conciliar work_ids 4:
  docs/AUDIT_phase_g_cultural_gate.md (rev2) Live baseline table, section 4
  per-edge gate, and Decision 16 row.
- check_thresholds_immutable exit 0: docs/AUDIT_phase_d4_count_gate_rev2.md
  Task 1 (target_sha == baseline_sha == 3a62c1f1f771, EXIT_CODE=0).
- expected_counts.json sha256 3a62c1f1f771...07712: the committed
  tools/expected_counts.baseline content (recomputed live, not a stale
  hardcode) and corroborated by the same rev2 audit Task 1.
- verify_no_deferral / check_adapter_purity / check_caste exit 0:
  docs/PHASE_EFH_EXECUTION_SPEC.md Phase H sections H6/H7/H8 and
  docs/implementation_phases/phase_02_lexical_ingest.md acceptance
  (check_caste --range b4d1a1a..HEAD; A.1 sha
  b4d1a1adbf7b7844599e95ebaeae54fac46914e3).
- snapshot determinism exit 0: the committed tools/snapshot_counts.py
  byte-deterministic property plus the D.3 reorder entry above (single
  fresh pass lands all 106,776 INSTANCE_OF edges, second pass a true
  no-op, triangle GREEN). The H5 live two-pass overall_hash comparison is
  re-executed by the auditor; this claim pins the deterministic-snapshot
  precondition rather than a tmp/ (gitignored, non-committed) constant.
- vector-quality gate exit 0: docs/AUDIT_phase_e_vector_quality_rev2.md
  self-test Exit 0 and GO verdict.
- procurement no-unapproved-deadend: docs/data_inventory_catalog.json
  procurement_required block (4 entries, every one "deadend": false,
  compatible_with_project true) and docs/PHASE_EFH_EXECUTION_SPEC.md
  Phase H section H.2 rule.

INDEPENDENCE: tools/verify_manifest.py computes every observed value
(pytest/script/cypher/file_sha/grep) into its own result set BEFORE the
manifest expected side is read, then diffs; exit 0 iff every claim
matches. The auditor independently re-executes this manifest; the author
did NOT run tools/verify_manifest.py (running it to tune values would
defeat the structural independence and risk back-fitting). All Neo4j /
Qdrant access by the author was zero: every expected was RECORDED from the
committed audits, not queried.

CASTE: docs/RESEED_MANIFEST_*.json is an architect contract artifact by
nature but was NOT covered by any existing tools/check_caste.py architect
glob (architect docs globs are docs/PHASE_*.md, docs/SCHEMA_DECISIONS.md,
docs/ARCHITECTURE.md, the two data_inventory catalogs, etc.; auditor owns
docs/MANIFEST_VERIFICATION_*.json and docs/AUDIT_*.md only). This is a
caste-config gap. Per the architect contract-artifact nature, a minimal
docs/RESEED_MANIFEST_*.json -> architect glob addition is warranted, but
tools/check_caste.py is implementer-z1 caste, so that glob addition is a
SEPARATE implementer-z1 commit. This manifest + this log entry commit
under Caste: architect (docs/PHASE_*.md governs the log; the manifest is
landed in the same architect commit only after the glob addition makes it
architect-covered, sequenced as: (1) implementer-z1 adds the glob, then
(2) architect commits the manifest + this log entry under the now-valid
architect coverage). Reversible by the owner.
