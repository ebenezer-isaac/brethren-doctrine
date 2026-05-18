# OSHB Audit Report (Phase C.4)

## 1. Coverage Test Exit at HEAD

Test execution: `timeout 600 python -m pytest tests/lexical/test_oshb_coverage.py --tb=line -q -p no:cacheprovider`

Result (at HEAD):
```
13 passed, 13 skipped in 242.53s
```

Expected: 13 passed, 13 skipped, 0 FAILED. Performance: 242.53s (within 600s limit, well below historical >2400s O(n^2) prior).

Status: PASS

## 2. Fixture SHA

Fixture file: `tests/lexical/fixtures/oshb_slice.json`

Fixture SHA: `52482d58ee36c5a42f563e7e3ad4bf88a619b3ba`

Status: STABLE

## 3. Purity

Adapter: `ingest/lexical/oshb.py`

Command: `python tools/check_adapter_purity.py --file ingest/lexical/oshb.py`

Result:
```
OK: 1 file(s) clean.
```

Exit code: 0

Status: PASS

## 4. Predicate Inclusion

Predicates referenced in adapter and test:

- `$pred_string`: 43 occurrences across docstring and Word/Morpheme/Verse/Strong/Source/Reading property definitions
- `$pred_int`: 6 occurrences (chapter, verse, position, word_position, morph_position)
- `$pred_bool`: 2 occurrences (redistribute, is_lacuna)

Mapping confirmed against `tools/predicates_by_type.cypher`:
- `$pred_string(x)` := x IS NOT NULL AND trim(toString(x)) <> ''
- `$pred_int(x)` := x IS NOT NULL
- `$pred_bool(x)` := x IS NOT NULL

All predicates traced and validated.

Status: PASS

## 5. Phrase Scan

Command: `python tools/verify_no_deferral.py --path ingest/lexical/oshb.py`

Result:
```
OK: 1 file(s) scanned, zero deferral markers.
```

Exit code: 0

12 forbidden categories scanned: all clear.

Status: PASS

## 6. Expected Counts Sanity

Source: `tools/expected_counts.json`

OSHB-morphology entry (Tier A):
- Record unit: word
- Expected count (catalog): 306785
- Tolerance: 0 (deterministic, exact match required)

Actual emitted Word count (perf-redo commit d004096): 305507

Shortfall: 306785 - 305507 = 1278 words

Tier A sanity gate: FAIL (1278-word delta vs. zero tolerance)

Flag: Phase D architect/catalog reconciliation open item. The adapter was performance-reoptimized (O(n^2) to O(n), full OSIS parse) in commit d004096 with frozen docstring and unchanged edge schema. Real-data loader proof documents 305507 Word nodes from 40 WLC books. Catalog count (306785) requires verification against upstream OSHB release manifest or recount.

Status: FLAGGED FOR REVIEW

## 7. Provenance SHAs

Adapter history:
```
d004096 phase C.3 impl: oshb (O(n) perf redo, real OSIS parse)
5546f9f phase C.3 impl: oshb
ee8d877 phase C.1 docstring: oshb
```

Test history:
```
8096f9b phase C.2 verifier: oshb (rewrite, non-tautological)
8d0f6a1 phase C.2 verifier: oshb
```

Wave 1 (docstring): ee8d877
Wave 2 (verifier, non-tautological rewrite): 8096f9b
Wave 3 (implementation including perf-redo O(n)): d004096

Status: COMPLETE

---

Caste: auditor
