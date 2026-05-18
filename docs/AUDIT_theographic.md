# AUDIT: Theographic-Bible-Metadata Adapter (Phase C.4)

## 1. Coverage-test exit code at HEAD

Test file: tests/lexical/test_theographic_coverage.py
Cited result at HEAD (a8fc728): 18 passed, 13 skipped, 0 FAILED in 923.50s
Implementation SHA: a8fc728460129cf81df87b1e8a1b8836c4ff4222

Note: Test suite marked KNOWN-LARGE/SLOW (~923s wall clock, 38MB verses.json fixture). Coverage tests not re-run per audit directive; result is cited from commit message and test execution at a8fc728.

## 2. Fixture SHA

tests/lexical/fixtures/theographic_slice.json
SHA: 24ec941b980445599bbcd1c91e5c8c4fb5bca324

Fixture composition: 3 entities seeded from commit SHA 27b5b53 (1 Person: mary-magdalene, 1 Place: bethlehem-of-judah, 1 Period: second-temple-period).

## 3. Adapter purity

Command: python tools/check_adapter_purity.py --file ingest/lexical/theographic.py
Result: OK: 1 file(s) clean.
Exit code: 0

## 4. Predicate-include tracing

Predicates referenced in ingest/lexical/theographic.py:
- $pred_string: used for slug, license, entity_id, display_name, description_markdown, source properties
- $pred_bool: used for redistribute boolean flag on Source node
- $pred_int: used for Period start_year and end_year integer bounds
- $pred_list: used for verses and aliases list properties

Predicates referenced in tests/lexical/test_theographic_coverage.py:
- $pred_string: assertion on IS NOT NULL check
- $pred_int: assertion for integer type validation
- $pred_bool: assertion for boolean predicate presence
- $pred_list: assertion for list type handling

All predicates trace to tools/predicates_by_type.cypher per RESEED_PLAN C.5. No inline predicate definitions found.

## 5. Phrase-ban verification

Command: python tools/verify_no_deferral.py --path ingest/lexical/theographic.py
Result: OK: 1 file(s) scanned, zero deferral markers.
Exit code: 0

## 6. Expected_counts sanity check

Expected_counts.json Theographic-Bible-Metadata row:
- Tier: A (deterministic, tolerance 0)
- Record unit: multi_entity_record
- Expected count: 43690
- Min/max bounds: 43690 (zero tolerance)

Tier rationale: Theographic ships multi-file JSON corpus (books, chapters, verses, people, places, periods, events, easton entries) as exact sum of upstream-published per-file counts from versioned github release.

Emitted count reconciliation: UNVERIFIED. Implementation agent (Wave 3, commit a8fc728) did not report exact per-label or total emitted count in commit message. The expected_counts.json row matches the contract docstring statement, but actual emission tally is Phase D open item.

Documented deviations noted in adapter docstring:
- Upstream data shipped as Airtable-style JSON arrays in folder hierarchy (data/private/theographic/json/), not as the Neo4j contract folder structure.
- Period nodes are derived deterministically from event startDate (century buckets), not sourced directly from upstream Period folder.
- Adapter includes in-file docstring section (Emitted node labels and properties) documenting six entity labels and Source node.

## 7. Provenance SHAs and commit subjects

Adapter commit history:
- a8fc728 (Wave 3, implementer-impl): "phase C.3 impl: theographic" - Projects Theographic entities (Person, Place, Period, Event, Group, Tribe) from Airtable JSON release, derives Period nodes as century buckets, resolves verse references to OSIS, emits MENTIONS and FROM_EDITION edges, routes peopleGroups by "Tribe of" prefix.
- 27b5b53 (Wave 1, implementer-docstring): "phase C.1 docstring: theographic" - Contract committed before implementation; establishes entry function signature, tier policy, expected count, and schema decisions.
- 6643487 (Phase 02 setup): "feat: phase 02 lexical ingest. 9 adapters, lockfile, CLI orchestrator" - Initial adapter skeleton.

Test commit history:
- a63dbc1 (Phase C.2 verifier predecessor): "phase C.2 verifier: stepbible_ttesv" - Previous verifier commit; theographic test file not yet committed to git log output shown.

No verifier-correction commits found in history for theographic adapter. Wave 2 verifier test committed inline with Wave 1 docstring or as separate Wave 2 commit; verifier test file coverage assertions at a8fc728 baseline.

---

Caste: auditor
