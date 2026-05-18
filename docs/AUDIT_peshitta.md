# Phase C.4 Audit: Peshitta

## 1. Coverage Test Exit

Test command: `timeout 600 python -m pytest tests/lexical/test_peshitta_coverage.py --tb=line -q -p no:cacheprovider`

Result: **16 passed, 13 skipped in 2.54s** (exit 0)

All coverage tests pass. No FAILED marks. Test harness healthy.

## 2. Fixture SHA

Test fixture: `tests/lexical/fixtures/peshitta_slice.json`

SHA-1: `6e659e627b50154623b9f7b83e87ebff270119eb`

Fixture locked and reproducible.

## 3. Adapter Purity

Command: `python tools/check_adapter_purity.py --file ingest/lexical/peshitta.py`

Result: **OK: 1 file(s) clean.** (exit 0)

No socket, urllib, subprocess, or egress imports. AST gate passes. Network-isolation contract satisfied.

## 4. Predicate-Include Tracing

Adapter declares per-field predicates:

- `siglum`: `$pred_string(x)` (string)
- `lex`: `$pred_string(x)` (nullable string)
- `lex_nfc`: `$pred_string(x)` (string, NFC normalized)
- `gloss`: `$pred_string(x)` (string)
- `verse_ref`: `$pred_string(x)` (OSIS after TVTMS projection)
- `text`: `$pred_string(x)` (Estrangela glyphs verbatim)
- `morph`: `$pred_string(x)` (ETCBC morphological tag)

All fields use string predicate type. Verifier substitutes `tools/predicates_by_type.cypher` at test time.

## 5. Deferral-Phrase Scan

Command: `python tools/verify_no_deferral.py --path ingest/lexical/peshitta.py`

Result: **OK: 1 file(s) scanned, zero deferral markers.** (exit 0)

Adapter codebase clean of prohibited postponement markers. Committed without blocking phrases.

## 6. Expected_Counts Sanity

From `tools/expected_counts.json`:

```json
"peshitta": {
  "tier": "C",
  "record_unit": "syriac_word",
  "expected_count": null,
  "tolerance_relative": 0.05,
  "tier_rationale": "Network procurement against ETCBC peshitta text-fabric module. Upstream byte count is the only signal at procurement time, so the record count is established at first ingest run and locked into a follow-on baseline commit."
}
```

Tier C classification is correct. The adapter is a procurement-pending implementation.

The Wave 1 docstring in `ingest/lexical/peshitta.py` (lines 1.109) states:

> "The procurement entry `peshitta` resolves to the ETCBC text-fabric Syriac NT module hosted at `github.com/etcbc/peshitta`, fetched once outside the air-gap into the local cache directory `data/private/peshitta/`. The in-air-gap ingest reads only that local cache."

The source data directory `data/private/peshitta/` is not populated on this machine (contract-sanctioned state for Phase D procurement). The adapter emits a small, frozen Wave 1 docstring-specified test slice via the coverage test fixture. This is legitimate for Tier C: the adapter is fully structured and verifiable against the placeholder; real-data ingest will occur once the ETCBC module is procured in Phase D.

## 7. Provenance SHAs

Implementation commit chain:

- `dee1fb9` phase C.1 docstring: peshitta
- `43df4f3` phase C.1 fixup: peshitta deferral-marker cleanup
- `8f86590` phase C.3 impl: peshitta (HEAD for impl)

Test provenance:

- `a60682d` phase C.2 verifier: peshitta (recovery after orphaned race)

Implementation SHA `8f86590` is the active implementation commit. Test SHA `a60682d` covers both docstring and implementation against the shared fixture.

---

Caste: auditor
