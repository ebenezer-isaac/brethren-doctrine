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
