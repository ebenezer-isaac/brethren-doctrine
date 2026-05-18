# AUDIT: etcbc_phono

## 1. Coverage-test exit at HEAD

```
19 passed, 13 skipped in 26.74s
```

Expected: 19 passed, 13 skipped, 0 FAILED. Actual: 19 passed, 13 skipped, 0 FAILED. Timing: 26.74s (within 600s limit). Status: PASS.

## 2. Fixture SHA

```
b72f57b7cdb15acec51dbe6b2b93312f9c211335
```

File: tests/lexical/fixtures/etcbc_phono_slice.json. Status: RECORDED.

## 3. Purity

```
OK: 1 file(s) clean.
EXIT: 0
```

Adapter: ingest/lexical/etcbc_phono.py. Status: PASS (exit code 0, no side effects detected).

## 4. Predicate-include

Predicate references traced in adapter and test:

Adapter (ingest/lexical/etcbc_phono.py):
- Line 43: $pred_string for slug field
- Line 44: $pred_string for license field
- Line 45: $pred_bool for redistribute field
- Lines 87, 100, 108, 128, 132, 133, 134: phono and slug field validation via $pred_string and $pred_bool
- Line 280: docstring references tools/predicates_by_type.cypher for $pred_string and $pred_bool semantics

Test (tests/lexical/test_etcbc_phono_coverage.py):
- Lines 3-4: Module-level predicate loading from tools/predicates_by_type.cypher
- Line 62-64: Predicate name extraction (parsing "$pred_" prefix)
- Lines 395-400: Validation that non-null phono satisfies $pred_string (non-empty string)
- Line 414: Docstring references $pred_string from tools/predicates_by_type.cypher
- Line 460: Docstring references $pred_bool from tools/predicates_by_type.cypher
- Lines 510-515: Module docstring confirms predicates_by_type.cypher defines $pred_string and $pred_bool for phono

Source: tools/predicates_by_type.cypher. Status: PASS (predicates traced and validated).

## 5. Forbidden-phrase check

```
OK: 1 file(s) scanned, zero deferral markers.
EXIT: 0
```

File: ingest/lexical/etcbc_phono.py. Scan result: zero forbidden phrases found. Status: PASS (exit code 0).

## 6. Expected_counts sanity

Source file: tools/expected_counts.json. Entry: ETCBC-phono.

- Tier: A (deterministic from source file lines, exact match required)
- Record unit: word
- Expected count: 426590
- Tolerance: 0 (exact match)
- Min: 426590
- Max: 426590

Rationale: "ETCBC phonetic transcription ships one phono value per BHSA word slot in the same text-fabric module. Total equals the BHSA word slot count exactly because the feature is keyed one-to-one with word identifiers."

Real emitted count (per perf-redo 1c3bcf7): 426590 rows. Match: EXACT. Data source: ETCBC text-fabric phono.tf (C:/Users/Ebenezer/text-fabric-data/github/ETCBC/phono/tf/2021). Composition: 426590 total word slots, 420166 non-null phono values, 6424 ketiv-only null values. Adapter implementation: O(n) text-fabric node-feature parse via _parse_phono_feature (dict-based) plus _load_phono_rows materialization. Docstring unchanged from Wave1 (Wave1 docstring, Wave2 verifier, Wave3 impl incl perf-redo 1c3bcf7). Status: PASS (exact count match, tier A satisfied).

## 7. Provenance SHAs

Adapter commit history (ingest/lexical/etcbc_phono.py):

```
1c3bcf7 phase C.3 impl: etcbc_phono (O(n) perf redo, real text-fabric parse)
6d51c96 phase C.3 impl: etcbc_phono
dde7690 phase C.1 docstring: etcbc_phono
```

Wave1 (docstring): dde7690. Wave2 (verifier): 6d51c96. Wave3 (impl incl perf-redo O(n^2) -> O(n)): 1c3bcf7. Perf-redo commit 1c3bcf7 details: replaced immutable-append idiom (rows = [*rows, x] per record, quadratic) with proven O(n) text-fabric node-feature parse using dict[int, str] with O(1) per-record assignment. Handles implicit counter, explicit nodeid<TAB>value, and lo-hi<TAB>value range rows. Genuinely parses real phono.tf. Data source unchanged; only quadratic accumulation rewritten.

Test commit history (tests/lexical/test_etcbc_phono_coverage.py):

```
9d2867c test: phase C.2 verifier: etcbc_phono
```

Subject: etcbc_phono. Status: Wave2 verifier committed.

Adapter subjects: perf-redo 1c3bcf7 (O(n) text-fabric node-feature parse, real phono.tf data, 426590 rows, 420166 non-null, 6424 ketiv-only nulls). Docstring untouched from Wave1. Status: RECORDED.
