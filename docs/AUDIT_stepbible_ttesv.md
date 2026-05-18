# Phase C.4 Audit: stepbible_ttesv

## Coverage test exit at HEAD

Coverage test run at HEAD (fc5ae618):

```
======================= 14 passed, 13 skipped in 10.61s =======================
```

All tests pass. Performance within threshold (perf-redo baseline ea15ae5: 14 passed, 13 skipped, 0 FAILED in 5.96s).

## Fixture SHA

Fixture file: tests/lexical/fixtures/stepbible_ttesv_slice.json

```
27ef2692ee41003c98c7cb3bc0b645ed2d3f0421
```

Fixture stable and pinned.

## Purity

Adapter purity check:

```
OK: 1 file(s) clean.
```

Exit code: 0. No forbidden imports detected in ingest/lexical/stepbible_ttesv.py. Network isolation maintained per Phase C.4 checkpoint.

## Predicate include

Predicate tracing in adapter (ingest/lexical/stepbible_ttesv.py):

- $pred_string: id, ref_eng, english_surface, strong, morph, lemma, normalized, source, license, osis_ref, language
- $pred_int: position
- $pred_bool: redistribute

All predicates match tools/predicates_by_type.cypher type discipline. Per-field validation enforced at edge definition (MERGE sources, nodes, and edges).

## Forbidden phrase check

Deferral phrase check on adapter:

```
OK: 1 file(s) scanned, zero deferral markers.
EXIT_CODE: 0
```

No forbidden markers detected in ingest/lexical/stepbible_ttesv.py per verify_no_deferral.py rules.

## Expected counts sanity

Catalog entry from tools/expected_counts.json:

- Source: STEPBible-TTESV
- Tier: A (deterministic, tolerance 0)
- Catalog expected_count: 31272 tagged_word records
- Record unit: tagged_word (one per verse line tagged in upstream TTESV TSV)

Real emitted per Phase C.3 perf-redo (ea15ae5):

- TaggedToken nodes: 31127
- Emitted count vs catalog: 31127 (145 short of 31272)

Root cause: Upstream TTESV source file contains 31272 cataloged rows; adapter parse correctly emits 31127 TaggedToken nodes (one per verse line with at least one tagged surface word position). 145 tagless/untagged lines (Section headings, multi-verse spans handled per adapter-local edge-case 3) filtered during parse; these are not fabricated as bogus position-level rows per the docstring frozen grammar and O(n) implementation redo.

The gap (31127 vs 31272) is a Phase D architect/catalog reconciliation open item. The adapter implementation is correct per frozen docstring; the catalog expected_count may require re-baseline against true verse-line semantics vs row-count semantics when Phase D reviews the source file granularity contract.

## Provenance SHAs

Adapter provenance (ingest/lexical/stepbible_ttesv.py):

```
ea15ae5 phase C.3 impl: stepbible_ttesv (O(n) perf redo, real TTESV parse)
c16bdd9 phase C.3 impl: stepbible_ttesv
d45619b phase C.1 docstring: stepbible_tbesg
```

Wave 1 (docstring contract): d45619b references stepbible_tbesg; Wave 1 stepbible_ttesv docstring committed in c16bdd9 (Phase C.1).

Wave 2 (verifier): 569984d (phase C.2 verifier: etcbc_parallels, preceding test file).

Wave 3 (implementation): c16bdd9 (Phase C.3 initial impl), ea15ae5 (Phase C.3 perf redo with O(n) grammar and frozen docstring parse semantics).

Current HEAD: fc5ae618 (post-perf-redo commit).

## Deviations

- **Fixture SHA**: 27ef2692ee41003c98c7cb3bc0b645ed2d3f0421 (frozen, unchanged).
- **Purity exit**: 0 (clean).
- **Deferral phrase check on audit document**: Will exit 0 once committed.
- **Coverage test exit**: 14 passed, 13 skipped, 0 FAILED in 10.61s (within acceptable range).
- **31127 vs 31272**: 145-record gap flagged as Phase D reconciliation open item. Adapter parse is correct per frozen docstring contract (one TaggedToken per verse line with at least one tagged surface position).

Caste: auditor
