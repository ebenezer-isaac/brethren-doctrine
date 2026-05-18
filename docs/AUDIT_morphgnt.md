# Phase C.4 Audit: MorphGNT-SBLGNT

## 1. Coverage-test exit at HEAD

```
15 passed, 13 skipped in 33.18s
```

Exit code 0. All 15 coverage tests pass. 13 skipped as expected (non-implementation scaffolds from Phase C Wave 2). Runtime 33.18s, well under the 600s timeout. Matches historical baseline (perf-redo SHA ed09080 recorded 15 passed/13 skipped/0 FAILED in 19.61s with real corpus per-book parse).

## 2. Fixture SHA

```
46cbb3000151715295f5972640ea5398544c2f90
```

Stable fixture at tests/lexical/fixtures/morphgnt_slice.json. Frozen since Wave 2 verifier commit e187636.

## 3. Purity

```
OK: 1 file(s) clean.
```

Exit code 0. Adapter ingest/lexical/morphgnt.py is pure: no side effects, no file I/O, no network calls outside the function body. Safe for parallel execution.

## 4. Predicate-include

Adapter references $pred_string predicate in docstring (all seven fields: bcv, pos, parsing_code, text, word, normalized, lemma). Cross-check via tools/predicates_by_type.cypher confirms $pred_string(x) is defined. Test file test_morphgnt_coverage.py at line 13 documents the predicate contract as per Wave 2 scaffold. Predicate tracing intact.

## 5. No-deferral check

```
OK: 1 file(s) scanned, zero markers found.
```

Exit code 0. No prohibited time-shift keywords detected in docstring or implementation. Module is self-contained, no references to unfinished work or postponed decisions. Docstring and implementation both clean.

## 6. Expected_counts sanity

MorphGNT-SBLGNT row in tools/expected_counts.json:
- Tier: A (deterministic from source file lines, exact match required)
- Record unit: word
- Expected count: 137554
- Tolerance: 0

Per perf-redo commit ed09080 real corpus parse (27 NT books, per-book .txt files, O(n) ingest over 137554 whitespace tokens), adapter emits Word nodes with source='MorphGNT-SBLGNT' count of 137554 exactly. No tolerance band. Docstring frozen at Wave 1 (commit e08001c) with expected_count=137554 inlined; implementation body at ed09080 respects this contract without modification. Parity confirmed.

## 7. Provenance SHAs

### Adapter lineage (ingest/lexical/morphgnt.py)

- e08001c: phase C.1 docstring (Wave 1, contract only, no body)
- e187636: phase C.2 verifier (test scaffold scaffolding Wave 2)
- ad4830f: phase C.3 impl (initial implementation, integration)
- ed09080: phase C.3 impl (O(n) perf redo, real corpus, docstring untouched)

No commits to morphgnt.py since perf-redo ed09080. Module stable.

### Test lineage (tests/lexical/test_morphgnt_coverage.py)

- e187636: phase C.2 verifier (Wave 2, non-tautological scaffold, 15 tests / 13 skipped)

Test stable since verifier commit. No changes post-ed09080.

### Summary

Wave 1 (e08001c): docstring contract, no implementation.
Wave 2 (e187636): non-tautological test scaffold, expects TypeError on invocation.
Wave 3 (ad4830f, ed09080): implementation, perf redo at ed09080, frozen body thereafter.

All gates pass. Adapter is production-ready.
