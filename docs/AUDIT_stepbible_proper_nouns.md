# Audit: stepbible_proper_nouns (Phase C.4)

## 1. Coverage-test exit at HEAD

```
16 passed, 13 skipped in 9.26s
```

Test run exit: 0 (success). Timeout: 600s. Actual: 9.26s.

## 2. Fixture SHA

```
9eb88b2247781b3fc70955ccf53ff461d7cd5bdb
```

Fixture: `tests/lexical/fixtures/stepbible_proper_nouns_slice.json`

## 3. Purity check

```
OK: 1 file(s) clean.
Exit code: 0
```

Tool: `python tools/check_adapter_purity.py --file ingest/lexical/stepbible_proper_nouns.py`

Result: Adapter reads no fixture files. Purity gate passes.

## 4. Predicate-include tracing

Adapter docstring (lines 37-82) and test file (line 3) both reference `tools/predicates_by_type.cypher` for predicate definitions.

Adapter predicates in acceptance cypher (ingest/lexical/stepbible_proper_nouns.py):
- `$pred_string` on proper_name_entry, transliteration, meaning, strong, pos, language, first_occurrence, source, slug, license
- `$pred_int` on verse_count (nullable coercion per Decision 17)
- `$pred_bool` on redistribute

Test file (tests/lexical/test_stepbible_proper_nouns_coverage.py):
- Loads predicates from cypher file at module level (lines 54-62)
- Asserts presence of string, int, bool predicates (lines 511-516)
- Uses $pred_int semantics in test_proper_noun_verse_count_nullable_coercion docstring (line 356)

## 5. Deferred-phrase check

```
OK: 1 file(s) scanned, zero deferral markers.
Exit code: 0
```

Tool: `python tools/verify_no_deferral.py --path ingest/lexical/stepbible_proper_nouns.py`

Result: No banned phrases found (defer, deferred, out of scope, v1.5, v2, future, TBD, FIXME, TODO, XXX, eventually, later).

## 6. Expected counts sanity

Source: `tools/expected_counts.json`

Entry: STEPBible-proper-nouns
- Catalog expected_count: 23205
- Tier: A
- Tolerance: 0
- record_unit: proper_name

Real emitted count per Phase C.3 integrity-redo (commit 6725bf3): 5468 proper noun entries from genuine TIPNR parse (TSV rows minus section headers, Hebrew and Greek combined). Catalog expectation 23205 reflects upstream line-count convention; actual parse yields 5468 records meeting Decision 17 populated projection criteria.

**Phase D reconciliation open item**: unreconciled count mismatch between catalog (23205) and implementation (5468). Catalog reflects upstream file line count; implementation reflects structural projection of qualifying proper-noun entries. Root cause: catalog methodology does not account for Decision 17 projection filtering and source data structure differences.

## 7. Provenance SHAs

Adapter history:

```
6725bf3 phase C.3 impl: stepbible_proper_nouns (integrity redo, real TIPNR parse)
90e3429 phase C.3 impl: stepbible_proper_nouns
91899b4 phase C.2 verifier: stepbible_proper_nouns
e3ed6dc phase C.1 fixup: stepbible_proper_nouns deferral-marker cleanup
```

**Wave 1** (e3ed6dc): Docstring written; deferral markers removed from acceptance cypher docstring.

**Wave 2** (91899b4): Test verifier written (tests/lexical/test_stepbible_proper_nouns_coverage.py); FakeDriver scaffold; 13 stub-rejection tests parameterized.

**Wave 3** (90e3429 and 6725bf3): Implementation incl. TIPNR parse of Hebrew and Greek proper-noun TSV sections; integer coercion of verse_count nullability per Decision 17 Edge case 3; NAMED_AT edge emission on first_occurrence Verse resolution; integrity redo to correct parse semantics against real upstream bytes.

Current HEAD SHA: `fc5ae61883eb3965ab35555b8ee59450d0afe2f7`

Adapter last-modified SHA: `6725bf3e7a2d90ad3a08d28ac604bdd08a5c9637` (Phase C.3 integrity redo)

---

Caste: auditor
