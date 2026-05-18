# Audit stepbible_tagnt

## Coverage test

16 passed, 13 skipped in 65.74s. Exit 0.

## Fixture SHA

7a0801d3ce60e713f2434527abd684b1da3c66fb

## Purity

OK: 1 file(s) clean. Exit 0.

## Predicate include

Adapter and test reference $pred_string and $pred_list tracing to tools/predicates_by_type.cypher. String predicates used for 8 fields (word_and_type, greek, english_translation, dstrongs_grammar, dictionary_gloss, editions, sstrong_instance, alt_strongs). List predicates used for 2 fields (meaning_variants, spelling_variants). Frozen docstring records both (lines 70-79).

## No forbidden phrases

Verified zero deferral markers.

## Expected counts sanity

Catalog entry: expected_count 141720, tier A, tolerance 0.
Real emitted per perf-redo 612336a: 142096 tokens.
Delta: +376 over catalog (142096 - 141720).
Flag: Phase D architect and catalog reconciliation open item.

Note: Phase C.3 perf-redo commit 612336a replaced O(n^2) accumulation with O(n) streaming generators mirroring stepbible_tahot precedent. Full Translators Amalgamated Greek NT corpus parsed; frozen docstring contract unchanged.

## Provenance SHAs

Adapter implementation:
- de38fdb phase C.1 docstring: stepbible_tagnt (Wave 1, frozen docstring contract)
- 1b9f3bc phase C.3 impl: stepbible_tagnt (Wave 2, initial verifier implementation)
- 612336a phase C.3 impl: stepbible_tagnt (Wave 3, O(n) perf redo, real TAGNT parse, FakeDriver edge-label trap closed)

Test verifier:
- 26f0b35 phase C.2 verifier: stepbible_tagnt (Wave 2, coverage harness)
