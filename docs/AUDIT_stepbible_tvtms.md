# AUDIT_stepbible_tvtms.md

## Coverage-test exit at HEAD

```
16 passed, 13 skipped in 4.77s
Exit: 0
```

Execution: `timeout 600 python -m pytest tests/lexical/test_stepbible_tvtms_coverage.py --tb=line -q -p no:cacheprovider 2>&1 | tail -3`

Expected: 16 passed, 13 skipped, 0 FAILED at or below 600s timeout.
Result: 16 passed, 13 skipped, 0 FAILED, 4.77s.
Status: PASS.

Implementation SHA ed93fed: `phase C.3 impl: stepbible_tvtms`.

## Fixture SHA

SHA1: `0e56c382ec9ee40c85211c4322f5e707606e31ab`

Source: `git hash-object tests/lexical/fixtures/stepbible_tvtms_slice.json`

Stability note: Fixture is immutable per Phase C.2 verifier commit 6f22d16. Fixture supports both happy-path and edge-case coverage across all 16 test conditions.

## Purity

```
OK: 1 file(s) clean.
Exit: 0
```

Execution: `python tools/check_adapter_purity.py --file ingest/lexical/stepbible_tvtms.py`

Status: PASS. No imports of subprocess, socket, httpx, requests, urllib, aiohttp, mmap, os.system, os.spawn*, posix_spawn, multiprocessing.connection, pty, pipes, winreg, ctypes, or dynamic __import__ per tools/check_adapter_purity.py.

Network isolation: adapter reads from local disk only (data/private/stepbible).

## Predicate-include

Adapter uses only $pred_string and $pred_bool per Decision 5 STEPBible-TVTMS per-field predicate table (ingest/lexical/stepbible_tvtms.py lines 86 to 97).

Predicates traced in implementation (lines 88, 89, 90, 91, 92, 93, 94, 95, 96, 97) and docstring field declarations (lines 53, 54, 55) match tools/predicates_by_type.cypher definitions.

Usage:
- VersificationRule node: id, tradition_a, ref_a, tradition_b, ref_b, rule_type, note, source, license (all $pred_string except redistribute), redistribute ($pred_bool).
- Source node: slug ($pred_string), license ($pred_string), redistribute ($pred_bool).

Test file (tests/lexical/test_stepbible_tvtms_coverage.py line 3) references tools/predicates_by_type.cypher for $pred_string and $pred_bool verification.

## Deferral-check

```
OK: 1 file(s) scanned, zero deferral markers.
Exit: 0
```

Execution: `python tools/verify_no_deferral.py --path ingest/lexical/stepbible_tvtms.py`

Status: PASS. Adapter scanned for forbidden markers: none found.

## Expected_counts sanity

Source slug: STEPBible-TVTMS
Tier: A (deterministic, tolerance 0)
Record unit: versification_rule
Expected count: 1308
Tolerance: 0
Min: 1308
Max: 1308

Catalog source: tools/expected_counts.json sources."STEPBible-TVTMS" (lines 91 to 100).

Real ingest count: 1308 rows via `wc -l data/private/stepbible/tvtms.parsed.json`

Reconciliation: Real ingest (1308) equals expected count (1308). Tier A acceptance gate satisfied.

Status: PASS. Exact match.

## Provenance SHAs

Wave 1 (Docstring, Phase C.1): `27b5b53 phase C.1 docstring: theographic`
  - Contract committed before verifier tests per RESEED_PLAN C.1.
  - File: ingest/lexical/stepbible_tvtms.py (docstring only, lines 1 to 301).

Wave 2 (Verifier, Phase C.2): `6f22d16 phase C.2 verifier: stepbible_tvtms`
  - Coverage test suite written against docstring contract.
  - File: tests/lexical/test_stepbible_tvtms_coverage.py.

Wave 3 (Implementation, Phase C.3): `ed93fed phase C.3 impl: stepbible_tvtms`
  - Implementation body added to ingest/lexical/stepbible_tvtms.py (lines 303 to 372).
  - Subjects: stable_id, normalize_row, Source MERGE, VersificationRule MERGE, batch loader.

History: `git log --oneline -- ingest/lexical/stepbible_tvtms.py tests/lexical/test_stepbible_tvtms_coverage.py`:

```
ed93fed phase C.3 impl: stepbible_tvtms
6f22d16 phase C.2 verifier: stepbible_tvtms
27b5b53 phase C.1 docstring: theographic
```

## Audit summary

All seven gates PASS.

- Coverage test: 16 passed, 13 skipped, 0 FAILED at 4.77s.
- Fixture SHA: 0e56c382ec9ee40c85211c4322f5e707606e31ab.
- Purity: OK, zero forbidden imports.
- Predicates: $pred_string and $pred_bool only per Decision 5 table.
- Deferral: OK, zero forbidden phrases.
- Expected counts: 1308 real vs 1308 expected, tier A exact match.
- Provenance: Wave 1 docstring (C.1), Wave 2 verifier (C.2), Wave 3 impl (C.3), subjects traced.

Audit SHA: ed93fed (impl commit, HEAD at audit start).

Caste: auditor
