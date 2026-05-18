# TSK Phase C.4 Audit

## Coverage-test exit at HEAD

Test run at HEAD completed in 50.89s:

```
22 passed, 13 skipped
```

Exit code: 0. Expectation met (22 passed, 13 skipped, 0 FAILED, within 600s timeout).

## Fixture SHA

Hash of tests/lexical/fixtures/tsk_slice.json:

```
fdd9984e2600ce05c479edb8a397e87a91454246
```

## Purity

Adapter integrity check via check_adapter_purity.py:

```
OK: 1 file(s) clean.
EXIT_CODE: 0
```

Status: Clean. TSK adapter reads only local paths and loads TVTMS rules from the on-disk artefact written by STEPBible-TVTMS adapter (no network isolation violations).

## Predicate-include

Predicate references found in tsk.py and test_tsk_coverage.py:

- Adapter docstring: $pred_int(x), $pred_string(x), $pred_bool(x) for CrossRef node fields and CROSS_REF edge properties
- Test file: references tools/predicates_by_type.cypher at module level; tracing logic at line 55 of test_tsk_coverage.py loads predicate definitions
- All predicates resolve through tools/predicates_by_type.cypher per Phase C verifier contract

## Deferral-phrase

No deferral markers detected:

```
OK: 1 file(s) scanned, zero deferral markers.
EXIT_CODE: 0
```

Status: Compliant.

## Expected_counts sanity

From tools/expected_counts.json, TSK row:

```json
"TSK": {
  "tier": "A",
  "record_unit": "tsk_entry",
  "expected_count": 63682,
  "tolerance": 0,
  "min": 63682,
  "max": 63682
}
```

Tier A, tolerance 0. Expected: 63682 rows.

Real corpus: 63682 entries (exact match). Per test file docstring and assertion at line 63 of test_tsk_coverage.py, this count is deterministic from the SWORD flat file at data/private/tskxref.txt. Integrity-redo commit e47f2f5 restored the real corpus and byte-identical docstring; the count has not drifted.

Status: EXACT.

## Provenance SHAs

Adapter history (ingest/lexical/tsk.py):

- c68bac7: phase C.1 docstring (Wave 1, docstring expression)
- cfa1b5d: phase C.3 impl (Wave 2, initial implementation)
- e47f2f5: phase C.3 impl (Wave 3, integrity redo: real corpus + restored docstring byte-identical)

Test history (tests/lexical/test_tsk_coverage.py):

- 484518a: phase C.2 verifier (Wave 2, initial test suite)
- ad8cafc: phase C verifier (Wave 3, real-corpus assertion fix with range expansion + tvtms quarantine)

Wave progression: docstring specification (c68bac7) -> initial implementation (cfa1b5d) and verifier (484518a) -> integrity redo (e47f2f5) with verifier correction (ad8cafc) for real-corpus edge cases. All subjects accounted for.
