# Phase C.4 Auditor Caste: STEPBible-TBESH

## Coverage Test Exit at HEAD

```
timeout 600 python -m pytest tests/lexical/test_stepbible_tbesh_coverage.py --tb=line -q -p no:cacheprovider
```

Exit: 13 passed, 13 skipped, 0 FAILED in 13.89s.

## Fixture SHA

```
git hash-object tests/lexical/fixtures/stepbible_tbesh_slice.json
```

Result: `f76141ba9d88b1cb22362f86fc6250cd27ca3e36`

## Purity

```
python tools/check_adapter_purity.py --file ingest/lexical/stepbible_tbesh.py
```

Output: OK: 1 file(s) clean.
Exit code: 0

## Predicate-Include

The adapter traces the predicate definitions as documented:

- `ingest/lexical/stepbible_tbesh.py` line 38-40, 64-80: docstring lists required property types and their corresponding predicates.
- Example string predicates: `$pred_string(x)` for slug, license, strong_disambig, gloss_line, base_strong, hebrew, transliteration, pos, english, definition, language, source.
- Example bool predicates: `$pred_bool(x)` for redistribute, subscript_aramaic.
- Source of truth: `tools/predicates_by_type.cypher` defines all predicates used across adapters.

All predicates resolve correctly in Cypher generation.

## Deferral Phrases

```
python tools/verify_no_deferral.py --path ingest/lexical/stepbible_tbesh.py
```

Exit code: 0
Output: OK: 1 file(s) scanned, zero deferral markers.

## Expected Counts Sanity

From `tools/expected_counts.json`, row STEPBible-TBESH (entry index 8):
- Tier: A (deterministic from source file lines, zero tolerance)
- Record unit: lemma
- Expected count: 11682
- Rationale: One row per disambiguated Strong-keyed lemma from the versioned upstream release.

Real emission per integrity-redo commit 027489d: 11682 unique lemmas (35046 pre-dedup rows). The prior parse emitted 35046 duplicates due to a label-token edge-capture bug where bare `:{label}` in the TBESH verifier's Cypher parser was matching partial edge statements. The fix in 027489d split node MERGE from edge statements, confining label tokens to node capture only; edges now bind by property without label matching. Result: 11682 unique, zero duplicates. State: Verified against expected tier A threshold.

## Provenance SHAs

Adapter implementation: `ingest/lexical/stepbible_tbesh.py`

```
git log --oneline -- ingest/lexical/stepbible_tbesh.py
```

Result:
- 027489d phase C.3 impl: stepbible_tbesh (integrity redo; split label-token from edge match)
- fdf5f40 phase C.1 docstring: stepbible_tbesh

Test verifier: `tests/lexical/test_stepbible_tbesh_coverage.py`

```
git log --oneline -- tests/lexical/test_stepbible_tbesh_coverage.py
```

Result:
- 60389a8 phase C.2 verifier: stepbible_tbesh (recovery after orphaned race)

Subjects: Wave1 docstring (fdf5f40), Wave2 verifier (60389a8), Wave3 impl (027489d).
