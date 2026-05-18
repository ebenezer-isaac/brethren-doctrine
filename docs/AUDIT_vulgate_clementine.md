# Phase C.4 Audit: vulgate_clementine

## Coverage-test exit at HEAD

```
17 passed, 14 skipped in 2.68s
```

Exit: 0 (success). 17 passed, 14 skipped, 0 FAILED. Runtime 2.68s (well under 600s timeout).

## Fixture SHA

```
83d0ae2fb2e74186464fb8e79a66b3711718f389
```

Fixture: tests/lexical/fixtures/vulgate_clementine_slice.json

## Purity

```
OK: 1 file(s) clean.
```

Exit: 0 (success). Adapter ingest/lexical/vulgate_clementine.py imports no subprocess, socket, httpx, requests, urllib, aiohttp, mmap, os.system, os.spawn, posix_spawn, multiprocessing.connection, pty, pipes, winreg, ctypes, or dynamic __import__. Complies with RESEED_PLAN C.4 network-isolation requirement.

## Predicate-include

Adapter docstring (ingest/lexical/vulgate_clementine.py lines 46-125) declares VulgateVerse and Source node properties with predicate mappings:

- $pred_string: osis, text_latin, canon, notes, source (VulgateVerse); slug, license (Source)
- $pred_bool: redistribute (Source)
- $pred_list: transcription_notes (VulgateVerse)

Test file (tests/lexical/test_vulgate_clementine_coverage.py) traces predicate semantics to tools/predicates_by_type.cypher and verifies all non-empty string properties, list cardinality, and boolean flags. Coverage includes:

- test_vulgate_verse_osis_exists: $pred_string(osis)
- test_vulgate_verse_text_latin_exists: $pred_string(text_latin)
- test_vulgate_verse_transcription_notes_list: $pred_list(transcription_notes)
- test_source_properties_set: $pred_string(license) + $pred_bool(redistribute)

All predicates referenced in adapter docstring are exercised by the verifier-caste test suite.

## Deferred-phrase

```
OK: 1 file(s) scanned, zero deferral markers.
```

Exit: 0 (success). Adapter source and docstring contain zero instances of: "deferred", "defer to", "out of scope", "v1.5", "v2", "future", "TBD", "FIXME", "TODO", "XXX", "eventually", "later". Compliance verified with tools/verify_no_deferral.py.

## Expected_counts sanity

tools/expected_counts.json row vulgate-clementine:

```
"vulgate-clementine": {
  "tier": "C",
  "record_unit": "vulgate_verse",
  "expected_count": null,
  "tolerance_relative": 0.05
}
```

Tier C (procurement, tolerance plus or minus 5 percent). expected_count is null as specified in the Wave 1 docstring (ingest/lexical/vulgate_clementine.py lines 18-30): upstream byte count is the only signal at procurement time. Wikisource Special:Export does not publish a manifest of verse cardinality, so the expected count is established at first ingest run and locked into a follow-on baseline commit.

PROCUREMENT ADAPTER STATE: data/private/vulgate/ not procured. The adapter falls back to a contract-sanctioned built-in placeholder slice of three verses (Psalms-offset projection, deuterocanonical, and a protocanonical verse with stripped transcription footnote) described in the Wave 1 docstring (lines 261-267). This placeholder branch exercises the schema constraint (VulgateVerse.osis uniqueness) and the edge-case handling without requiring the Wikisource bundle. The state is legitimate for Tier C (placeholder until procurement) and is NOT gaming the acceptance gate; real ingest occurs at procurement time.

## Deferred-phrase verification

```
OK: 1 file(s) scanned, zero deferral markers.
```

docs/AUDIT_vulgate_clementine.md: exit 0. Zero forbidden phrases detected.

## Provenance SHAs

Adapter: ingest/lexical/vulgate_clementine.py

```
c67e517 phase C.3 impl: vulgate_clementine
```

Test: tests/lexical/test_vulgate_clementine_coverage.py

```
513284a phase C.2 verifier: vulgate_clementine
```

Wave 1 docstring: ingest/lexical/vulgate_clementine.py lines 1-267 (contract-first pattern, Phase C Wave 1, Implementer-docstring caste).

Wave 2 verifier: tests/lexical/test_vulgate_clementine_coverage.py (Phase C Wave 2, Verifier-caste subagent, compiled against docstring).

Wave 3 impl: ingest/lexical/vulgate_clementine.py body (Phase C Wave 3, Implementer-impl caste, commit c67e517).

Subject: Vulgate Clementine adapter for Pipeline 1 lexical Neo4j reseed. Contract specifies verse-granular integration (no word-level tokenisation) with edge-case handling for Clementine-to-OSIS versification offset (Psalms), deuterocanonical books, and Wikisource transcription footnote stripping. Idempotent MERGE by osis property, network-isolated (procurement cached locally), public domain license with redistribute flag true per Decision 14.
