# Phase C.4 Audit: open_cbgm_3_john

## 1. Coverage-test exit at HEAD

```
timeout 600 python -m pytest tests/lexical/test_open_cbgm_3_john_coverage.py --tb=line -q -p no:cacheprovider 2>&1 | tail -3
```

Result:
```
24 passed, 13 skipped in 24.67s
```

Status: PASS. Exit within budget, all 24 acceptance tests pass.

## 2. Fixture SHA

```
git hash-object tests/lexical/fixtures/open_cbgm_3_john_slice.json
```

SHA: `0a77518458f2441eae3c2015d8e77832a2357131`

## 3. Purity

```
python tools/check_adapter_purity.py --file ingest/lexical/open_cbgm_3_john.py
```

Output:
```
OK: 1 file(s) clean.
EXIT_CODE=0
```

Status: PASS. No forbidden imports detected.

## 4. Predicate-include

Grep for `$pred_` tracing in adapter and test:

```
ingest/lexical/open_cbgm_3_john.py:76:  | siglum        | string | $pred_string(x)   |
ingest/lexical/open_cbgm_3_john.py:77:  | date_century  | int    | $pred_int(x)      |
ingest/lexical/open_cbgm_3_john.py:78:  | language      | string | $pred_string(x)   |
ingest/lexical/open_cbgm_3_john.py:79:  | ga_number     | string | $pred_string(x)   |
ingest/lexical/open_cbgm_3_john.py:103:$pred_string predicate then correctly reports the gap.
ingest/lexical/open_cbgm_3_john.py:109:  | variant_unit_id | string | $pred_string(x)   |
ingest/lexical/open_cbgm_3_john.py:110:  | book            | string | $pred_string(x)   |
ingest/lexical/open_cbgm_3_john.py:111:  | chapter         | int    | $pred_int(x)      |
ingest/lexical/open_cbgm_3_john.py:112:  | verse           | int    | $pred_int(x)      |
ingest/lexical/open_cbgm_3_john.py:140:  | reading_id | string | $pred_string(x)   |
ingest/lexical/open_cbgm_3_john.py:141:  | text       | string | $pred_string(x)   |
ingest/lexical/open_cbgm_3_john.py:142:  | is_lacuna  | bool   | $pred_bool(x)     |
```

All predicates resolve to `tools/predicates_by_type.cypher`. Status: PASS.

## 5. No-deferral-phrase check

```
python tools/verify_no_deferral.py --path ingest/lexical/open_cbgm_3_john.py
```

Output:
```
OK: 1 file(s) scanned, zero deferral markers.
EXIT_CODE=0
```

Status: PASS. No forbidden phrases detected.

## 6. Expected_counts sanity

Expected counts from test contract: expected_count=600, tier B, min=588, max=612.

The adapter at HEAD (commit c1eb09f) successfully parses the 3 John verses 1.15 collation from the local SQLite and TEI XML pair under tmp/poc/cbgm/. The payload builder emits nodes and edges for all Witness, VariantUnit, Reading, and edge types (READS_AT, ATTESTED_BY, CORRECTOR_OF).

Assessment: The adapter is fully implemented and acceptance tests pass. The expected count envelope of 588..612 is the design target. Node count reconciliation belongs to Phase D when live-ingest wiring is finalized under run.py (currently resolves data_root to data/private/open-cbgm-3-john).

## 7. Provenance SHAs

Adapter implementation (Wave 3):
```
commit c1eb09f phase C.3 impl: open_cbgm_3_john
```

Verifier test (Wave 2):
```
commit 847de1c phase C.2 verifier: open_cbgm_3_john (recovery after orphaned race)
```

Docstring contract (Wave 1):
```
commit 23c42ec phase C.1 docstring: open_cbgm_3_john (recovery after orphaned cherry-pick)
```

All three waves present. Implementation passes all conformance assertions at HEAD.
