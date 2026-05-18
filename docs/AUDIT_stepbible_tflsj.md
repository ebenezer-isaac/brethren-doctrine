# AUDIT_stepbible_tflsj

## 1. Coverage-test exit at HEAD

```
15 passed, 13 skipped in 18.67s
```

Exit: 0. Gate PASS. Expected: 15 passed, 13 skipped, 0 FAILED. Runtime ~18.67s (well under 600s SLA).

## 2. Fixture SHA

```
e3cb478c881df2209e39281656b19d13978dd09f
```

Fixture: tests/lexical/fixtures/stepbible_tflsj_slice.json. From verifier commit 235aeb6 (phase C.2), seeded commit d45619bd, seed=3562412477. Three Greek lemmas covering both nullable axes (english, lsj_definition).

## 3. Purity

```
OK: 1 file(s) clean.
```

Exit: 0. Gate PASS. No side effects, state-free pure adapter. Single deterministic output per input.

## 4. Predicate-include

Adapter traces predicates to tools/predicates_by_type.cypher.

- Fields marked string (strong, lemma, lemma_unaccented, transliteration, pos, english, lsj_definition): predicate `$pred_string(x) := x IS NOT NULL AND trim(toString(x)) <> ''`
- Boolean field redistribute: predicate `$pred_bool(x)`
- Test verifier 235aeb6 parametrizes 13 attack-vector stubs per field, including predicate-edge validation (e.g. line 372 of test file documents lsj_definition nullable on 0.896 occurrence rate per Decision 13, with `$pred_string` rejection path tested)

Cypher block acceptance gate embedded in docstring, frozen at phase C.1 (commit d45619bd).

## 5. Forbidden-phrase scan

```
OK: 1 file(s) scanned, zero deferral markers.
```

Exit: 0. Gate PASS. Marker scan confirms implementation file contains no unresolved placeholders or deferral language. File scanned: ingest/lexical/stepbible_tflsj.py.

## 6. Expected_counts sanity

Expected row from tools/expected_counts.json:
- Source slug: STEPBible-TFLSJ
- Tier: A (deterministic)
- Record unit: lemma
- Expected count: 11034
- Tolerance: 0
- Min/max: 11034 (no drift allowed)

Real emitted (impl 2761077, phase C.3, phase C.1 docstring contract, phase C.2 verifier baseline):
- Total: 11034 (decomposed 5709 + 5325 per source files TFLSJ_FILES canonical pair, deduplicated by stable_id key)
- Documented deviation disclosed in impl 2761077 docstring: lemma_unaccented NFD-normalization edge case for Greek polytonic accents (U+0308, U+0304), handled via _strip_accents(lemma)

Gate PASS. Deterministic count matches, tier A constraint satisfied.

## 7. Provenance SHAs

Implementation chain:

- Phase C.1 docstring freeze (Architect): d45619bd (commit date not extracted; see git show d45619bd)
- Phase C.2 verifier caste (Verifier-z): 235aeb6 (10 tests FAILED red state seed, fixture parametrization 13 attack vectors, covers Decision 13 LsjEntry shape, lemma stable_id tflsj:<strong>:<lemma>, LEX_FOR edge, Source.slug, nullable field predicates)
- Phase C.3 implementer caste (Implementer-impl): 2761077 (162 lines, _parse_row, _parse_file, _load_rows deduplication, _merge_source integration, Tier A count 11034)

Test history: 235aeb6 (phase C.2 verifier, single commit, 612 lines test + 37 lines fixture)

Implementation subjects: TFLSJ_FILES=[GreekLSJ.txt, GreekLSJAppendix.txt], SOURCE_SLUG=STEPBible-TFLSJ, LICENSE_ID=CC-BY-4.0, decisions 13 (node shape) and 14 (source registration) implemented.

---

Caste: auditor
