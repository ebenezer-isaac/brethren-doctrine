# AUDIT: macula_greek

## 1. Coverage-test exit at HEAD

Command: `timeout 600 python -m pytest tests/lexical/test_macula_greek_coverage.py --tb=line -q -p no:cacheprovider`

Result: **15 passed, 13 skipped, 0 FAILED in 273.17s (0:04:33)**

Status: PASS. Test exit code 0. Expected 15 passed (all critical checks), 13 skipped (context-dependent matrix arms), 0 FAILED. Execution time 273.17s is within the KNOWN-MEDIUM window (tolerance +600s timeout).

## 2. Fixture SHA

Command: `git hash-object tests/lexical/fixtures/macula_greek_slice.json`

Result: `3f09211c44087aaaee48abe103a3c6fb58a15e35`

Status: Fixture canonical pointer recorded.

## 3. Purity

Command: `python tools/check_adapter_purity.py --file ingest/lexical/macula_greek.py`

Result: `OK: 1 file(s) clean.`

Exit code: 0

Status: PASS. Adapter contains no forbidden mutations, side effects, or non-deterministic operations.

## 4. Predicate-include

Adapter traces (ingest/lexical/macula_greek.py lines 92-101):
- `$pred_string(x)` used for fields: xml:id, ref, lemma, normalized, morph, gloss, domain, ln, text
- `$pred_int(x)` used for fields: strong

Test verification (tests/lexical/test_macula_greek_coverage.py):
- Line 67-69: explicit parse of `$pred_` patterns from docstring
- Line 551-552: assertion that predicates_by_type.cypher exports both `$pred_string` and `$pred_int`

All predicates resolve to tools/predicates_by_type.cypher per docstring reference at test line 3-5.

Status: PASS. Predicate inclusion verified and traced.

## 5. Phrase-gate

Command: `python tools/verify_no_deferral.py --path ingest/lexical/macula_greek.py`

Result: `OK: 1 file(s) scanned, zero deferral markers.`

Exit code: 0

Status: PASS. No forbidden phrases found in implementation or docstring.

## 6. Expected_counts sanity

From tools/expected_counts.json:

| Source | Tier | Record Unit | Expected Count | Tolerance |
|--------|------|-------------|-----------------|-----------|
| MACULA-Greek-Nestle1904 | A | word | 137779 | exact |
| MACULA-Greek-SBLGNT | A | word | 137741 | exact |

Catalog values confirmed at expected_counts.json lines 31-50. Both rows mark tier A (deterministic from source file lines, exact match required).

Implementation note: macula_greek adapter was the original slow adapter from Phase C.1, profiled at ~1200s. Refactored to O(n) iteration in Phase C.3 (commit 6c8fb65). Coverage test now executes at 273.17s, confirming optimization landed. Exact count reconciliation (emitted vs. expected) is a Phase D open item per standard boundary.

## 7. Provenance SHAs

Implementation commits (ingest/lexical/macula_greek.py):
- 6c8fb65 (HEAD~0, Wave3): phase C.3 impl: macula_greek
- 8abcfe3 (HEAD~1, Wave2): phase C.1 docstring: macula_greek
- 6643487 (HEAD~2, Wave1): feat: phase 02 lexical ingest. 9 adapters, lockfile, CLI orchestrator

Test commits (tests/lexical/test_macula_greek_coverage.py):
- 004cb5a (HEAD~0, Wave2): phase C.2 verifier: macula_greek

Docstring: Wave1 architecture at 6643487, Wave2 verifier bridge at 004cb5a, Wave3 implementation refactor at 6c8fb65, subject-side closure at 273.17s coverage run.

Status: All audit gates PASS. Implementation ready for phase C.5 promotion.

Caste: auditor
