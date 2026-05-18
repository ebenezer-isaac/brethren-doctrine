# Phase C.4 Audit: OpenBible-cross-refs

## 1. Coverage Test Exit

Test suite: `tests/lexical/test_openbible_coverage.py`

```
17 passed, 13 skipped in 19.04s
EXIT_CODE: 0
```

Expected: 17 passed, 13 skipped, 0 FAILED. Gate: PASS (19.04s under 600s timeout).

## 2. Fixture SHA

Fixture: `tests/lexical/fixtures/openbible_slice.json`

```
bd5a0d2693ad50b618b9fc05b9eb93fc15e80a27
```

## 3. Purity

Command: `python tools/check_adapter_purity.py --file ingest/lexical/openbible.py`

```
OK: 1 file(s) clean.
EXIT_CODE: 0
```

Gate: PASS (no subprocess, socket, httpx, requests, urllib, aiohttp, mmap, os.system, os.spawn*, posix_spawn, multiprocessing.connection, pty, pipes, winreg, ctypes, or dynamic __import__).

## 4. Predicate Include

Adapter references: `ingest/lexical/openbible.py` lines 45-50

Test trace: `tests/lexical/test_openbible_coverage.py` lines 63-71

Cypher source: `tools/predicates_by_type.cypher`

Predicates used:
- `$pred_string(x) := x IS NOT NULL AND trim(toString(x)) <> ""` (From Verse, To Verse)
- `$pred_int(x) := x IS NOT NULL` (Votes field and votes edge property)

Test verifies both predicates are defined and contain required null checks per docstring Decision 5 table. Gate: PASS (both predicates found in predicates_by_type.cypher).

## 5. Forbidden Phrase Scan

Command: `python tools/verify_no_deferral.py --path ingest/lexical/openbible.py`

```
OK: 1 file(s) scanned, zero deferral markers.
EXIT_CODE: 0
```

Gate: PASS (no forbidden phrases: defer, defer to, out of scope, v1.5, v2, future, TBD, FIXME, TODO, XXX, eventually, later).

## 6. Expected Counts Sanity

OpenBible-cross-refs entry in `tools/expected_counts.json` sources:

```json
{
  "tier": "A",
  "record_unit": "cross_ref",
  "expected_count": 344799,
  "tolerance": 0,
  "min": 344799,
  "max": 344799,
  "tier_rationale": "OpenBible.info community cross-reference table ships one row per voted From-Verse to-Verse pair. Total is a deterministic line count from the versioned upstream CSV release used at ingest, no derivation involved."
}
```

Tier A deterministic requirement: exact match expected_count = 344799.

Real emission (perf-redo 3be5fb5): adapter parses cross_references.txt, projects KJV refs through TVTMS to OSIS endpoints, persists OPENBIBLE_CROSS_REF edges with votes property. Expected behavior unchanged from docstring contract at ingest/lexical/openbible.py lines 158-178.

O(n^2) perfected to O(n) in perf-redo 3be5fb5 via direct TVTMs.parsed.json parse and cached OSIS lookups. Docstring frozen; runnable body matches contract.

Gate: PASS (expected_count 344799 matches docstring tier A definition).

Edge counts in `tools/expected_counts.json`:

```json
{
  "OPENBIBLE_CROSS_REF": {
    "tier": "B",
    "expected_min": 343799,
    "expected_max": 345799,
    "tier_rationale": "Derived from OpenBible cross-refs as the parallel edge type per Decision 5. Edge count equals row count since one row produces one edge. Two percent capped at one thousand absolute records covers ingest-time row drops."
  }
}
```

Tier B tolerance: two percent relative capped at one thousand absolute. Band [343799, 345799] permits up to one thousand quarantine rows without gate violation.

Gate: PASS (edge count band correctly calibrated per Decision 5).

## 7. Provenance SHAs

Commit history for `ingest/lexical/openbible.py`:

```
3be5fb5 phase C.3 impl: openbible (O(n) perf redo, real cross-refs parse)
18c2f9a phase C.3 impl: openbible
d66faa3 phase C.1 docstring: openbible
6643487 feat: phase 02 lexical ingest. 9 adapters, lockfile, CLI orchestrator
```

Wave1 docstring: `d66faa3 phase C.1 docstring: openbible`
Wave2 verifier: (none; verifier generated in Phase D from docstring)
Wave3 impl: `18c2f9a phase C.3 impl: openbible` and `3be5fb5 phase C.3 impl: openbible (O(n) perf redo, real cross-refs parse)`

Subject coverage:
- Docstring contract (Wave 1): d66faa3
- Phase C.3 implementation and perf optimization (Wave 3): 18c2f9a, 3be5fb5
- Source registration per Decision 14: lines 411-419 (MERGE Source node with slug, license, redistribute)
- Edge MERGE on (from_osis, to_osis, source) idempotency tuple per Decision 5: lines 305-312
- TVTMS projection per Decision 5: lines 315-353
- Votes parse and quarantine per Decision 5 edge case: lines 356-408

---

Caste: auditor
