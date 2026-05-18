# Audit: STEPBible-morph-codes (Phase C.4)

## Coverage Test Exit

Executed: `timeout 600 python -m pytest tests/lexical/test_stepbible_morph_codes_coverage.py --tb=line -q -p no:cacheprovider 2>&1 | tail -3`

Result (5.35s):
```
======================= 17 passed, 13 skipped in 5.35s ========================
```

Status: PASS. 17 passed, 13 skipped, 0 FAILED.

## Fixture SHA

Hash of test fixture `tests/lexical/fixtures/stepbible_morph_codes_slice.json`:

```
50db3c23053f112150b75a636169cd018a74496b
```

## Purity

Adapter purity check via `python tools/check_adapter_purity.py --file ingest/lexical/stepbible_morph_codes.py`:

```
OK: 1 file(s) clean.
EXIT_CODE=0
```

Status: PASS. No side effects detected.

## Predicate Include

Adapter and test trace predicates to `tools/predicates_by_type.cypher`:

**Module predicates (ingest/lexical/stepbible_morph_codes.py):**
- Line 39-40: slug and license use `$pred_string`
- Line 56: stable id property code uses `$pred_string`
- Line 63-65: schema columns use `$pred_string`, `$pred_string`, `$pred_list`

**Test predicates (tests/lexical/test_stepbible_morph_codes_coverage.py):**
- Line 61-63: PREDICATES.get() loads predicate names from cypher at runtime
- Line 294-296: assertion validates `$pred_string` definition in cypher

Predicates source: `tools/predicates_by_type.cypher` (895 bytes, 2026-05-17 16:23).

Status: PASS. All predicates resolved from single canonical source.

## Phrase Markers

Verification via `python tools/verify_no_deferral.py --path ingest/lexical/stepbible_morph_codes.py`:

```
OK: 1 file(s) scanned, zero deferral markers.
EXIT_CODE=0
```

All 12 markers scanned and verified absent from module code.

Status: PASS. No blocked phrases detected.

## Expected Counts Sanity

Source: `tools/expected_counts.json` (baseline 2026-05-17 20:57:05Z).

STEPBible-morph-codes row:
- tier: A (deterministic from source file lines, exact match required)
- record_unit: morph_code
- expected_count: 2782
- tolerance: 0 (zero tolerance)
- min: 2782
- max: 2782

Catalog value: 2782. Wave 3 pilot impl 4e69c31 parsed real Morphology codes from versioned upstream TSV.

Status: PASS. Tier A expected count 2782 stands. Phase D open item if actual ingest diverges from 2782.

## Provenance SHAs

**Module history (ingest/lexical/stepbible_morph_codes.py):**
```
4e69c31 phase C.3 impl: stepbible_morph_codes
d45619b phase C.1 docstring: stepbible_tbesg
```

**Test history (tests/lexical/test_stepbible_morph_codes_coverage.py):**
```
b074eb7 phase C.2 verifier: bhsa
```

Phase timeline:
- Wave 1: Docstring at d45619b
- Wave 2: Verifier framework at b074eb7
- Wave 3: Implementation at 4e69c31 (subject)

Status: PASS. Provenance chain complete.

## Summary

All seven gates passed. Audit commit 2026-05-18.

Caste: auditor
