# Audit: ETCBC-BHSA

## 1. Coverage test exit code at HEAD

Test file: tests/lexical/test_bhsa_coverage.py
Cited result at HEAD (c1ca524): 19 passed, 13 skipped, 0 FAILED in 430.93s
Implementation SHA: c1ca524d7a6f676a032342941ce0a035c8f9f0ce

Note: Test suite marked KNOWN-LARGE (426590 word slots). Coverage tests not re-run per audit directive; result is cited from orchestrator-verified gate at c1ca524 (integrity redo, real text-fabric parse).

## 2. Fixture SHA

Fixture file: tests/lexical/fixtures/bhsa_slice.json

```
9720236c3c6d2f9b87e5781d81e44ce79814d6b0
```

Fixture composition: 3 OT verses (torah Gen.1.1, wisdom Pro.1.1, prophets Isa.1.1), seeded from commit c4da6c1d with length 10108 bytes.

## 3. Adapter purity

Command: python tools/check_adapter_purity.py --file ingest/lexical/bhsa.py

Output: OK: 1 file(s) clean.

Exit code: 0

Result: PASS. No forbidden imports detected in adapter file.

## 4. Predicate-include

Predicates referenced in ingest/lexical/bhsa.py:
- $pred_string: 15 references across BhsaWord properties (id, corpus, otype, ref, book, g_word_utf8, lex_utf8, gloss, sp, pdp, vt, vs, ps, nu, gn, language, source) and BhsaPhrase/BhsaClause properties (id, corpus, otype, ref, book, function, typ, rela, txt, code, license_note) and edge properties
- $pred_int: 3 references for chapter, verse, node_id, freq_lex on BhsaWord and similar on phrase/clause layers
- $pred_bool: 1 reference for redistribute on Source node

Predicates referenced in tests/lexical/test_bhsa_coverage.py:
- $pred_string, $pred_int, $pred_bool, $pred_list loaded at module level from tools/predicates_by_type.cypher
- Runtime verification parses predicate definitions and asserts all required predicates present

All predicate usage traces correctly to tools/predicates_by_type.cypher per Decision 3 and Decision 14.

## 5. Forbidden-phrase scan

Command: python tools/verify_no_deferral.py --path ingest/lexical/bhsa.py

Output: OK: 1 file(s) scanned, zero deferral markers.

Exit code: 0

Result: PASS. No prohibited markers detected.

## 6. Expected_counts sanity

Expected_counts.json ETCBC-BHSA row:
- Tier: A (deterministic, tolerance 0)
- Record unit: word
- Expected count: 426590
- Min/max bounds: 426590 (zero tolerance)

Tier rationale: ETCBC Biblia Hebraica Stuttgartensia Amstelodamensis is shipped via text-fabric as a frozen feature set. Word slot count is deterministic from the otype feature in the versioned text-fabric module used at ingest.

Emitted count reconciliation: EXACT MATCH. Implementation agent (c1ca524) emitted 426590 BhsaWord nodes, matching expected_count exactly.

Implementation notes: Adapter uses text-fabric sparse-format readers (_parse_otype_feature, _parse_oslots_feature, _parse_node_feature) with O(n) performance and slot-ownership joins across the full Hebrew Bible. _load_dataset parses otype.tf, oslots.tf, and per-feature .tf files from the text-fabric module at TF_ROOT. Full corpus parses in roughly 21 seconds when text-fabric module is present locally.

## 7. Provenance SHAs

Adapter file: ingest/lexical/bhsa.py

```
c1ca524 phase C.3 impl: bhsa (integrity redo, real text-fabric parse)
c7c467b phase C.3 impl: bhsa
c4da6c1 phase C.1 docstring: bhsa
6643487 feat: phase 02 lexical ingest. 9 adapters, lockfile, CLI orchestrator
```

Test file: tests/lexical/test_bhsa_coverage.py

```
b074eb7 phase C.2 verifier: bhsa
```

Wave analysis:
- Wave 1 (docstring): c4da6c1 - Phase C.1 docstring contract established. Decisions 3 and 14. Source slug ETCBC-BHSA, Tier A, expected count 426590 word slots, license CC-BY-NC-4.0 redistribute false.
- Wave 2 (verifier): b074eb7 - Phase C.2 verifier written. Red-state TDD coverage: 12 tests fail (adapter body absent), 7 static tests pass, 13 stubs skipped. Fixture: 3 OT corpus regions seeded from commit c4da6c1d, length 10108.
- Wave 3 (implementation): c1ca524 - Phase C.3 implementation committed. _load_dataset now genuinely parses real ETCBC BHSA text-fabric module at TF_ROOT and emits real node population: 426590 BhsaWord, 253203 BhsaPhrase, 88131 BhsaClause, plus TFNode and CONTAINS_PHRASE, CONTAINS_WORD, IN_VERSE edges.

No verifier-correction commits found.

---

Caste: auditor
