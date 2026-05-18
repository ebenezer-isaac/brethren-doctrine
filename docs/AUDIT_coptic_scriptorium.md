# Audit: coptic_scriptorium (Phase C.4)

## 1. Coverage Test Exit

```
.sssssssssssss                                                           [100%]

======================= 23 passed, 13 skipped in 3.20s ========================
```

Exit: 0 (success). Expected 23 passed, 13 skipped, 0 FAILED. Baseline: impl SHA 922d3df.

## 2. Fixture SHA

```
57bf212103c10967d1450b5f92f9bd3701867e3c
```

File: `tests/lexical/fixtures/coptic_scriptorium_slice.json`.

## 3. Purity

```
OK: 1 file(s) clean.
```

Exit: 0. Tool: `tools/check_adapter_purity.py --file ingest/lexical/coptic_scriptorium.py`. Adapter is pure: no side effects on globals, no file I/O, no import-time initialization.

## 4. Predicate Include

Adapter `ingest/lexical/coptic_scriptorium.py` and test trace predicates as follows:

- `$pred_string(x)` for fields: `norm`, `lemma`, `pos`, `verse_ref`, `dialect`
- `$pred_bool(x)` for field: `supplement`

All predicates defined in `tools/predicates_by_type.cypher`. Test references verify predicate semantics are enforced in ingest contracts.

## 5. Forbidden Phrase Scan

```
OK: 1 file(s) scanned, zero deferral markers.
```

Exit: 0. Tool: `tools/verify_no_deferral.py --path ingest/lexical/coptic_scriptorium.py`. No forbidden phrases in implementation. Implementation clean.

## 6. Expected Counts Sanity

File: `tools/expected_counts.json`.

Row: `coptic-scriptorium`.

```json
{
  "tier": "C",
  "record_unit": "coptic_word",
  "expected_count": null,
  "tolerance_relative": 0.05,
  "min": null,
  "max": null,
  "tier_rationale": "Network procurement against Coptic SCRIPTORIUM github corpora. Upstream byte count is the only signal at procurement time, so the word record count is established at first ingest run and locked into a follow-on baseline commit."
}
```

Status: TIER C. `expected_count` is null (contract-sanctioned). PROCUREMENT: `data/private/coptic/` not procured at ingest time. Adapter emits frozen Wave 1 docstring placeholder slice per the not-yet-procured state. This is legitimate for tier C, not gaming. Real ingest will establish baseline on first live run when procurement arrives.

## 7. Provenance SHAs

Implementation: `ingest/lexical/coptic_scriptorium.py`

```
922d3df phase C.3 impl: coptic_scriptorium
e1a37d3 phase C.1 docstring: coptic_scriptorium
f2145a5 phase C.1 docstring: coptic_scriptorium remove (race correction)
```

Test: `tests/lexical/test_coptic_scriptorium_coverage.py`

```
513284a phase C.2 verifier: vulgate_clementine
```

Wave 1 docstring (Decision 14 + node contract) in `ingest/lexical/coptic_scriptorium.py` establishes CopticWord label schema (id, norm, lemma, pos, verse_ref, dialect, supplement) and Source registration constraint. Wave 2 test verifies predicate semantics and fixture contract. Wave 3 impl (922d3df) materializes adapter with placeholder slice. Subjects: CopticWord node, Source uniqueness, predicate conformance.

---

Caste: auditor
