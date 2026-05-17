"""MACULA Greek lexical adapter docstring contract (Phase C, Wave 1).

This module is intentionally a single docstring expression. The runnable
implementation is added in a follow-up commit by the implementer-impl
caste. This file freezes the per-field schema contract, edge contract,
stable identifier format, license posture, and acceptance Cypher block
so the verifier caste can build conformance tests against a stable
specification.

============================================================
1. Scope and source slugs
============================================================

The adapter ingests two MACULA Greek editions as distinct rows keyed by
edition slug.

Source slug `MACULA-Greek-Nestle1904`:
  tier A, record unit word, expected count 137779, tolerance 0,
  minimum 137779, maximum 137779. Tier A means the count is a
  deterministic element count from the upstream frozen XML release and
  any deviation fails the acceptance gate. License CC-BY-4.0 per
  Decision 14, redistribute true. The edition slug is also persisted as
  the value of every `Word.source` property emitted from this edition.

Source slug `MACULA-Greek-SBLGNT`:
  tier A, record unit word, expected count 137741, tolerance 0,
  minimum 137741, maximum 137741. License composite: SBLGNT base text
  under the SBLGNT EULA, MACULA syntactic enrichment CC-BY-4.0,
  MARBLE Louw-Nida CC-BY-NC-4.0. Decision 14 records `Source.license`
  as the effective composite slug `CC-BY-NC-4.0` because the most
  restrictive component governs redistribution; `Source.redistribute`
  is false for this edition. The edition slug is the value of every
  `Word.source` property emitted from this edition.

Both editions populate the same node labels and the same edge types.
Disambiguation between editions is by `source` property and by the
stable-id namespace prefix, never by label specialisation.

============================================================
2. Decisions implemented (Decisions 2, 4, 14, 15)
============================================================

Decision 2: Louw-Nida domain encoding.
  The MACULA Greek `ln` field is a colon-delimited string of the form
  `domain:subdomain`. The adapter splits it into `domain_code` (int)
  and `subdomain_code` (int) and stores them on the `IN_DOMAIN`
  relationship rather than on the `LouwNidaDomain` node, because the
  same domain node is reached by multiple distinct subdomain edges.
  The `LouwNidaDomain` node identity is the integer `domain_code`
  alone, which yields a single node per top-level domain rather than
  per subdomain combination.

Decision 4: Hebrew-to-Greek bridge granularity.
  This adapter is on the receiving end of the bridge. MACULA-Hebrew
  emits `BRIDGES_LXX` edges keyed by `greekstrong`, and those edges
  target the `GreekLemma` nodes created here. The adapter therefore
  MUST emit `GreekLemma` nodes whose stable id is constructed in a way
  that MACULA-Hebrew can reproduce by Strong number alone, while still
  satisfying the per-edition namespacing required by Decision 2's
  cross-edition disagreement rule.

Decision 14: Strong / Source / TFNode constraint policy.
  The adapter registers exactly two `Source` nodes (one per edition)
  before any record-level write. Each `Source` carries `slug`,
  `license`, `redistribute`. The Source uniqueness constraint
  `source_slug` in `graph/lexical.cypher` is the gate that prevents
  duplicate registration. No `TFNode` writes happen in this adapter
  (text-fabric is the BHSA path, not MACULA).

Decision 15: Verse.text population policy.
  MACULA-Greek MUST NOT write `Verse.text`. The canonical NT surface
  is owned by `ingest/lexical/morphgnt.py` (MorphGNT-SBLGNT) per
  Decision 15. The adapter MAY MERGE a `Verse` node by `osisID` to
  attach `IN_VERSE` edges, but it MUST NOT set the `text` property.
  The acceptance Cypher in section 5 verifies that no Verse node has
  acquired text from this adapter alone (the verifier checks that
  Verses populated solely by MACULA-Greek leave `text` null until
  MorphGNT writes it).

============================================================
3. Emitted node labels (with property name, type, predicate)
============================================================

Label `Word` (one node per row, both editions):
  Stable id: `<edition>:<xml:id>` where `<edition>` is one of
  `MACULA-Greek-Nestle1904` or `MACULA-Greek-SBLGNT`, and `<xml:id>`
  is the verbatim MACULA token identifier.

  Per Decision 2 per-field predicate table:
  | Field      | Type   | Predicate         |
  |------------|--------|-------------------|
  | xml:id     | string | $pred_string(x)   |
  | ref        | string | $pred_string(x)   |
  | lemma      | string | $pred_string(x)   |
  | normalized | string | $pred_string(x)   |
  | strong     | int    | $pred_int(x)      |
  | morph      | string | $pred_string(x)   |
  | gloss      | string | $pred_string(x)   |
  | domain     | string | $pred_string(x)   |
  | ln         | string | $pred_string(x)   |
  | text       | string | $pred_string(x)   |

  Additional discriminator properties (not in the Decision 2 table,
  required by Decision 14 for cross-source disambiguation):
  | Field   | Type   | Predicate       |
  |---------|--------|-----------------|
  | source  | string | $pred_string(x) |
  | edition | string | $pred_string(x) |

  The `source` value equals the edition slug verbatim. The `edition`
  value is the short form used in stable ids (`Nestle1904` or
  `SBLGNT`).

Label `GreekLemma`:
  Stable id format per Decision 2: `<edition>:<xml:id>` for the lemma
  occurrence captured first per edition. For Decision 4 bridge
  compatibility, the adapter also writes a `strong` property carrying
  the integer Strong number so MACULA-Hebrew `BRIDGES_LXX` edges keyed
  by `greekstrong` can MERGE the bridge target by Strong lookup.

  | Field   | Type   | Predicate       |
  |---------|--------|-----------------|
  | id      | string | $pred_string(x) |
  | lemma   | string | $pred_string(x) |
  | strong  | int    | $pred_int(x)    |
  | source  | string | $pred_string(x) |
  | edition | string | $pred_string(x) |

  Uniqueness is enforced by the `greek_lemma_id` constraint on `id`
  in `graph/lexical.cypher`.

Label `LouwNidaDomain`:
  One node per distinct top-level Louw-Nida domain code observed
  across either edition.

  | Field        | Type   | Predicate       |
  |--------------|--------|-----------------|
  | id           | string | $pred_string(x) |
  | domain_code  | int    | $pred_int(x)    |
  | source       | string | $pred_string(x) |

  `id` is the stringified integer `domain_code` so the
  `louw_nida_id` uniqueness constraint and the
  `louw_nida_code` composite index in `graph/lexical.cypher` both
  apply. The `source` slot is the literal string
  `MACULA-Greek-Louw-Nida` to record provenance.

Label `Source`:
  Two nodes total emitted by this adapter, one per edition. Decision
  14 fields:
  | Field        | Type   | Predicate       |
  |--------------|--------|-----------------|
  | slug         | string | $pred_string(x) |
  | license      | string | $pred_string(x) |
  | redistribute | bool   | $pred_bool(x)   |

  Nestle1904 Source: slug `MACULA-Greek-Nestle1904`, license
  `CC-BY-4.0`, redistribute true.
  SBLGNT Source: slug `MACULA-Greek-SBLGNT`, license `CC-BY-NC-4.0`,
  redistribute false.

============================================================
4. Emitted edges (with src label, dst label, properties)
============================================================

Edge `INSTANCE_OF` (`Word` to `GreekLemma`):
  One edge per Word row. No edge properties. Establishes the lemma
  membership of the word occurrence. The Word's `strong` property and
  the GreekLemma's `strong` property MUST agree; rows where the row
  has no resolvable Strong MUST be persisted without the
  `INSTANCE_OF` edge rather than fabricating a sentinel lemma.

Edge `IN_DOMAIN` (`Word` to `LouwNidaDomain`):
  One edge per distinct `(strong, domain_code, subdomain_code)`
  tuple per word occurrence per Decision 2 polysemy rule. The edge
  carries the per-Decision-2 split:

  | Edge property    | Type | Predicate    |
  |------------------|------|--------------|
  | domain_code      | int  | $pred_int(x) |
  | subdomain_code   | int  | $pred_int(x) |
  | source           | string | $pred_string(x) |

  The `source` property on the edge records the edition that produced
  the assignment so cross-edition disagreement is queryable. When a
  Strong code is annotated with multiple Louw-Nida senses across
  different occurrences in the same edition (polysemy), the adapter
  emits one `IN_DOMAIN` per distinct `(strong, domain_code,
  subdomain_code)` tuple. The adapter MUST NOT collapse polysemy into
  a single edge by majority vote.

Edge `FROM_EDITION` (`Word` to `Source`):
  One edge per Word, no properties. Provides constant-time edition
  filtering without parsing the `Word.source` property at query time.

The adapter emits no other edge types. In particular it does NOT
write `IN_VERSE`, `NEXT_WORD`, `PARSE_OF`, or `BRIDGES_LXX`. The
MorphGNT adapter owns `PARSE_OF` (per Decision 15 dispatch order)
and MACULA-Hebrew owns `BRIDGES_LXX` (per Decision 4).

============================================================
5. Acceptance Cypher (verbatim from phase_02 bullet 3)
============================================================

The Phase D verifier asserts the following query returns at least one
row with `with_ln > 0`, exactly as written in
`docs/implementation_phases/phase_02_lexical_ingest.md` bullet 3:

    MATCH (w:Word)
    WHERE w.source IN ['MACULA-Greek-Nestle1904', 'MACULA-Greek-SBLGNT']
      AND w.ln IS NOT NULL
    WITH count(w) AS with_ln
    RETURN with_ln, with_ln > 0

In addition, the Decision 2 sub-query in `docs/SCHEMA_DECISIONS.md`
runs against the Nestle1904 edition and asserts conformance of the
`ln` split:

    MATCH (w:Word {source: 'MACULA-Greek-Nestle1904'})
    WHERE w.ln IS NOT NULL
    WITH w, split(w.ln, ':') AS parts
    WHERE size(parts) = 2 AND toInteger(parts[0]) > 0
    RETURN count(w) AS conformant

============================================================
6. Edge cases (verbatim from Decision 2)
============================================================

Case A: literal `n/a` coercion.
  A small slice of MACULA-Greek-Nestle1904 records emit `domain` and
  `ln` populated with the literal string `n/a` when MARBLE annotators
  left the slot empty. The adapter MUST coerce these to a true null
  so `$pred_string(ln)` returns false and the `LouwNidaDomain` edge
  is suppressed. Word nodes still write, with `domain` and `ln`
  unset. No `IN_DOMAIN` edge is emitted for those rows.

Case B: polysemy on Strong code.
  Some Strong codes carry multiple Louw-Nida senses across
  occurrences. The adapter MUST create one `IN_DOMAIN` relationship
  per distinct Strong-plus-domain tuple rather than averaging or
  picking the first, so the semantic-neighbor query returns the full
  sense set. Polysemy is detected at the `(strong, domain_code,
  subdomain_code)` tuple level; identical tuples across occurrences
  collapse onto one edge.

Case C: cross-edition `ln` disagreement.
  MACULA-Greek-SBLGNT and MACULA-Greek-Nestle1904 occasionally
  disagree on the `ln` value for the same lemma in the same verse
  owing to text-critical divergences. The adapter MUST record both
  with the differentiating `source` property on the `IN_DOMAIN`
  relationship rather than merging on a winner-take-all rule.
  Specifically, the adapter persists two `IN_DOMAIN` edges from the
  two distinct Word nodes (one per edition; see stable-id rule
  in section 3) to the corresponding `LouwNidaDomain` nodes, each
  edge carrying its own `source` slot. Verifier queries that filter
  by `source` then see the disagreement cleanly.

============================================================
7. Verse.text policy (Decision 15)
============================================================

The `Verse` node label is shared across the lexical store and carries
a canonical surface `text` property per OSIS reference. Decision 15
locks ownership: MorphGNT-SBLGNT writes `Verse.text` for NT verses,
OSHB-morphology writes it for OT verses. MACULA-Greek MUST NOT write
`Verse.text` under any condition. The adapter MAY read upstream
per-word `text` tokens (the MACULA Greek `text` field documented in
Decision 2's per-field predicate table) and persist them on the
`Word` node, but the `Verse.text` slot remains untouched so the
MorphGNT adapter populates it without an ingest-order race.

============================================================
8. License and redistribute (Decision 14)
============================================================

Per Decision 14 the adapter writes one `Source` node per edition
before any record-level write, and the constraint `source_slug` on
`graph/lexical.cypher` prevents a second registration of the same
slug. The Nestle1904 edition is straightforward CC-BY-4.0 with
redistribute true. The SBLGNT edition is the composite slug
`CC-BY-NC-4.0` because the SBLGNT base text is under the SBLGNT EULA
and MARBLE Louw-Nida is CC-BY-NC-4.0; the most restrictive component
governs the effective license, so redistribute is false. The
`license` and `redistribute` properties on the `Source` node are the
canonical reference for downstream Pipeline 2 citation gating.

The license slugs above match the entries in
`docs/LICENSE_TAGGING.md`. The citation slugs used by Pipeline 2
evidence files (`MACULA-Greek-Nestle1904` and `MACULA-Greek-SBLGNT`)
match `docs/phase_prompts/pipeline2_verdict.md` verbatim.

============================================================
9. Stable identifier format (Decision 2, Decision 14)
============================================================

GreekLemma stable id:
  Format `<edition>:<xml:id>`, e.g.
  `MACULA-Greek-SBLGNT:n40001001001` for the SBLGNT token whose
  MACULA `xml:id` is `n40001001001`.

Word stable id:
  Format `<edition>:<xml:id>`, identical pattern. The Word and the
  GreekLemma created for that word's first occurrence share the
  xml:id portion of the namespace; uniqueness is preserved because
  the two labels carry their own constraints
  (`word_id` and `greek_lemma_id` in `graph/lexical.cypher`).

LouwNidaDomain stable id:
  Format `<domain_code>` as string, e.g. `"12"` for domain 12.
  Subdomain is captured on the relationship, not the node, per
  Decision 2.

Source stable id:
  The slug itself, by Decision 14 uniqueness constraint
  `source_slug`.

============================================================
10. Dependence and dispatch order
============================================================

Per `docs/implementation_phases/phase_02_lexical_ingest.md` bullet 3,
this adapter runs in Group 1 alongside OSHB-morphology and
MACULA-Hebrew. It has no dependence on OSHB Word nodes because the
Greek text floor is independent of the Hebrew text floor. MorphGNT-
SBLGNT (Group 1 bullet 4) depends on the MACULA-Greek-SBLGNT Word
nodes for the `PARSE_OF` join, so the MACULA-Greek adapter must
complete before MorphGNT begins. The wipe contract in
`tools/wipe_lexical.py` deletes every node and relationship in the
lexical Neo4j before re-ingest, so MERGE writes start from an empty
store and the constraints reject any second write for the same
stable id.

============================================================
11. Network isolation and AST purity
============================================================

Per `docs/implementation_phases/phase_02_lexical_ingest.md`, adapter
dry-runs execute inside Docker with `--network=none`, which forbids
any HTTP, DNS, or socket access during ingest. The AST scan
`tools/check_adapter_purity.py` rejects any adapter that imports
`subprocess`, `socket`, `httpx`, `requests`, `urllib`, `aiohttp`,
`mmap`, `os.system`, `os.spawn*`, `posix_spawn`,
`multiprocessing.connection`, `pty`, `pipes`, `winreg`, `ctypes`, or
dynamic `__import__`. The implementer-impl caste commit that adds
the runnable adapter body MUST satisfy that purity scan; the local
TSV files at `data/private/macula-greek/` are the only inputs.

============================================================
12. Idempotency
============================================================

MERGE-by-stable-id is the idempotency guarantee. Re-running the
adapter on identical source bytes produces identical Word,
GreekLemma, LouwNidaDomain, Source nodes and identical
INSTANCE_OF, IN_DOMAIN, FROM_EDITION edges. The triangle-test hash
recompute in Phase D re-runs the adapter on the same source bytes;
the per-row presence vector produces a sorted list of per-row
SHA-256 hashes that must match byte-for-byte across two runs.
"""
