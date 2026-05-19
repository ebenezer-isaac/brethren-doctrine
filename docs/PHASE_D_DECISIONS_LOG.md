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
