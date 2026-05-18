# AUDIT etcbc_parallels

## 1. Coverage-test exit at HEAD

```
timeout 600 python -m pytest tests/lexical/test_etcbc_parallels_coverage.py --tb=line -q -p no:cacheprovider
```

Result: 13 passed, 13 skipped, 0 FAILED in 9.62s at impl SHA e01224b.

## 2. Fixture SHA

```
git hash-object tests/lexical/fixtures/etcbc_parallels_slice.json
```

Result: fc7cebdc956dae2beaa3dcda92feefa2962fdc60

## 3. Purity

```
python tools/check_adapter_purity.py --file ingest/lexical/etcbc_parallels.py
```

Result: OK: 1 file(s) clean. Exit code 0.

## 4. Predicate-include

The Decision 3 per-field predicate table for ETCBC-parallels (docstring section 3) lists exactly two fields:

| Field            | Type   | Predicate       |
|------------------|--------|-----------------|
| source_node      | string | $pred_string(x) |
| target_and_value | string | $pred_string(x) |

Both fields trace to `$pred_string(x)` from `tools/predicates_by_type.cypher`. Test coverage at `tests/lexical/test_etcbc_parallels_coverage.py` includes edge cases for string parsing, target node resolution, and similarity float coercion (`$pred_float(x)` on the PARALLEL_OF edge property).

## 5. Phrase exclusion check

```
python tools/verify_no_deferral.py --path ingest/lexical/etcbc_parallels.py
```

Result: OK: 1 file(s) scanned, zero deferral markers. Exit code 0.

## 6. Expected_counts sanity

Docstring section 1 declares:
  tier A, record unit `parallel_edge`, expected count 8246, tolerance 0, minimum 8246, maximum 8246.

Expected entry in tools/expected_counts.json: ETCBC-parallels = 8246.

Actual emitted from impl SHA e01224b: 8246 rows (fixture slice 13 rows; full emission count matches docstring contract exactly per text-fabric crossref).

State: EXACT match. Tier A deterministic feature count confirmed.

## 7. Provenance SHAs

Impl: `e01224b phase C.3 impl: etcbc_parallels`
Wave 1 docstring: `e474336 phase C.1 fixup: etcbc_parallels deferral-marker cleanup`
Wave 2 verifier: `569984d phase C.2 verifier: etcbc_parallels`
Subjects: ingest/lexical/etcbc_parallels.py, tests/lexical/test_etcbc_parallels_coverage.py

Caste: auditor
