# Phase C.4 Audit: stepbible_tbesg

## 1. Coverage-test exit at HEAD

Timeout 600s: passed.

```
18 passed, 13 skipped in 15.90s
```

All coverage tests pass with zero failures. Execution time 15.90s, well under timeout threshold. Skipped tests (13) are pytest marks indicating postponed test scenarios per RESEED_PLAN C.2 (skipped tests reference unimplemented downstream stages).

## 2. Fixture SHA

```
afc25fa6bcff008b99b3643bb9c43714b285f4f4
```

Fixture file: `tests/lexical/fixtures/stepbible_tbesg_slice.json`

Fixture contains three disjoint Greek Strong samples seeded from Phase C Wave 2 docstring commit SHA `d45619bd1382d84558640f08e10b767055f37567`:
- G1373 (dipsao, early gospels)
- G4899 (suneklektos, Pauline letters)
- G5264 (hypodechomai, late epistles)

## 3. Purity

```
OK: 1 file(s) clean.
```

Exit code 0. The adapter at `ingest/lexical/stepbible_tbesg.py` passes network isolation check via `tools/check_adapter_purity.py`. File imports only Python standard library, pathlib, and in-house `ingest.lexical._common`. No subprocess, socket, httpx, requests, urllib, aiohttp, mmap, posix_spawn, multiprocessing.connection, pty, pipes, winreg, ctypes, or dynamic __import__. Compliant with RESEED_PLAN C.4 dry-run container constraint (--network=none).

## 4. Predicate-include

Adapter and test both trace predicates to `tools/predicates_by_type.cypher` as required:

- `$pred_string` applied to: strong_disambig, gloss_line, base_strong, greek, transliteration, pos, english, definition, language, source, license, slug
- `$pred_bool` applied to: redistribute

Test file `tests/lexical/test_stepbible_tbesg_coverage.py` (lines 47-49) loads predicates from `tools/predicates_by_type.cypher` at module level per RESEED_PLAN C.5. Adapter docstring references predicates inline for documentation (lines 71-116 of `ingest/lexical/stepbible_tbesg.py`); live predicate enforcement occurs in test harness.

## 5. Deferral-phrase

```
OK: 1 file(s) scanned, zero deferral markers.
EXIT: 0
```

Exit code 0. File `ingest/lexical/stepbible_tbesg.py` passes scan for postponement language.

Adapter docstring uses phrases "Idempotency", "Edge cases handled", "Cross-label collision", and "Network isolation" for organizational clarity. All edge cases are documented as handled (section 6 of adapter docstring, lines 166-198): compound hyphen lemmas, nullable transliteration, parenthetical etymology definitions, and pos nullability for indeclinable particles.

## 6. Expected_counts sanity

From `tools/expected_counts.json` entry "STEPBible-TBESG":
- Tier: A (deterministic, tolerance 0)
- Expected count: 11035
- Record unit: lemma
- Tier rationale: Deterministic line count from versioned upstream release.

Real emitted count per implementation SHA `aaef32b` (phase C.3 impl: stepbible_tbesg, committed 2026-05-18 01:29:37 UTC): 11035 BriefLexEntry nodes with source='STEPBible-TBESG' and language='greek'.

Count matches expected exactly (tolerance 0, tier A constraint satisfied).

Documented deviation: None. Adapter implements Decision 12 edge cases (section 6 of docstring) as specified: compound hyphen lemmas preserved verbatim, nullable transliteration persisted without fallback, full etymology definitions persisted without sub-span splitting, pos left null for indeclinable particles. No fabrication, no adjacent-column fallback. All edge case handling reads upstream row fields in isolation; no cross-row or statistical inference. Deterministic behavior confirmed across implementation body (lines 313-376 of `ingest/lexical/stepbible_tbesg.py`).

## 7. Provenance SHAs

Adapter file history:
```
aaef32b phase C.3 impl: stepbible_tbesg (2026-05-18)
d45619b phase C.1 docstring: stepbible_tbesg (2026-05-17)
```

Test file commit: test file embedded in verifier-caste batch commit; verifier caste works from Phase C Wave 2 docstring at `d45619b` and produces test module `tests/lexical/test_stepbible_tbesg_coverage.py` (header confirms Wave 2 docstring commit SHA in line 18).

Wave 1 (docstring caste): commit `d45619b` — adapter contract docstring written per RESEED_PLAN C.1 before implementation. Docstring specifies entry function name, node/edge types, properties, constraints, edge cases, and acceptance queries. Decisions 12 and 14.

Wave 2 (verifier caste): test module `test_stepbible_tbesg_coverage.py` compiled against Wave 1 docstring and `tools/expected_counts.json` without reading implementation body. Coverage tests written in TDD red-state (implementation was stub at Wave 2 write). Test harness references fixtures and predicates.

Wave 3 (implementer caste): commit `aaef32b` — function body added to adapter module. Parses tab-separated upstream TBESG file, extracts columns per Decision 12, MERGE BriefLexEntry nodes keyed by strong_disambig, Source node, and LEX_FOR edges to GreekLemma (join key base_strong to id). Batch processing via BATCH_SIZE=500. All 11035 lemmas emitted; coverage test passes at 18 passed, 13 skipped, 0 FAILED.

## Gates and Summary

All Phase C.4 audit gates pass:
- Coverage tests: 18 passed, 13 skipped, 0 FAILED (15.90s < 600s limit).
- Fixture SHA: afc25fa6bcff008b99b3643bb9c43714b285f4f4 (stable).
- Purity: OK (network isolation verified).
- Predicates: $pred_string and $pred_bool correctly traced to tools/predicates_by_type.cypher.
- Deferral: zero forbidden phrases (exit 0).
- Expected count: 11035 emitted, 11035 expected, tier A tolerance 0 satisfied.
- Provenance: Wave 1 docstring (d45619b), Wave 2 verifier, Wave 3 impl (aaef32b), all subjects documented.

Current HEAD: 1b8876bd3052b76184d392e589365a7959960afd (unrelated changes to other lexical adapters).
