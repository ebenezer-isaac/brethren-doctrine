"""MACULA-Hebrew lexical adapter contract (Phase C.1 docstring).

This module is the verifier-caste contract for the MACULA-Hebrew adapter
under `ingest/lexical/macula_hebrew.py`. The executable body is added by
the implementer-impl caste in a follow-on commit. Every node label,
every property, every edge, every stable-id format, every decision
backreference, every edge case, and the acceptance Cypher block below
is binding on that implementation.

Source identity
===============

Source slug: MACULA-Hebrew
Tier: A (deterministic from source file lines, exact match required)
Record unit: morpheme
Expected count: 475911 (locked in `tools/expected_counts.json`, baseline
commit `ecea53e3b8056890e7471e2ed25ebb389d9af070`)
Tolerance: 0 (Tier A requires byte-identical re-ingest)
Composite license slug: MACULA-Hebrew. Component licenses span WLC base
text (public_domain), OSHB morphology (CC-BY-4.0), Clear syntax
(CC-BY-4.0), Cherith glosses (CC-BY-4.0), and UBS MARBLE / SDBH word
senses (CC-BY-NC-4.0). Composite resolves to CC-BY-NC-4.0 per
`docs/LICENSE_TAGGING.md` section "Composite license resolution".
Redistribute boolean on the emitted `Source` node: false (the strictest
applicable component is non-commercial).

Decisions implemented
=====================

Decision 1: OSHB-to-MACULA-Hebrew morpheme alignment.
Decision 4: Hebrew-to-Greek bridge granularity.
Decision 14: Strong, Source, and TFNode constraint policy.

Dependency contract
===================

OSHB Word nodes MUST pre-exist in the lexical store before this adapter
runs. The `HAS_MACULA_ENRICHMENT` join is by OSIS reference plus lemma
identity after Unicode NFC normalisation and whitespace strip. Rows
where the OSHB lemma token differs from the MACULA lemma token after
NFC normalisation are rejected at adapter time, and the rejection is
recorded per-row in the snapshot ledger so the triangle test cannot
mask drift. The adapter MUST NOT silently skip any such row.

Emitted node labels and per-field predicate types
=================================================

`MaculaToken` (one node per `<w>` element in
`WLC/lowfat/<book>-<chapter>-lowfat.xml`, keyed by the `xml:id` value
verbatim):

| Property        | Type   | Predicate          | Source decision |
|-----------------|--------|--------------------|-----------------|
| id              | string | $pred_string(x)    | Decision 1      |
| xml_id          | string | $pred_string(x)    | Decision 1      |
| ref             | string | $pred_string(x)    | Decision 1      |
| lemma           | string | $pred_string(x)    | Decision 1      |
| morph           | string | $pred_string(x)    | Decision 1      |
| pos             | string | $pred_string(x)    | Decision 1      |
| gloss           | string | $pred_string(x)    | Decision 1      |
| stronglemma     | string | $pred_string(x)    | Decision 1      |
| strongnumberx   | int    | $pred_int(x)       | Decision 1      |
| transliteration | string | $pred_string(x)    | Decision 1      |
| source          | string | $pred_string(x)    | Decision 14     |

The `xml_id` property mirrors the upstream attribute named `xml:id`;
the colon is replaced with an underscore on the property name because
Neo4j property identifiers do not accept the colon. The stable node
identifier `id` is the `xml:id` attribute value verbatim from the
upstream TEI lowfat file, with no namespace prefix added.

`Lemma` (one node per distinct Hebrew Strong key encountered in the
MACULA-Hebrew morpheme stream, deduplicated across the run):

| Property         | Type   | Predicate          | Source decision |
|------------------|--------|--------------------|-----------------|
| id               | string | $pred_string(x)    | Decision 14     |
| strong           | string | $pred_string(x)    | Decision 14     |
| disambig_suffix  | string | $pred_string(x)    | Decision 14     |
| lemma            | string | $pred_string(x)    | Decision 1      |
| language         | string | $pred_string(x)    | Decision 14     |
| source           | string | $pred_string(x)    | Decision 14     |

Stable-id format for Lemma: `macula-hebrew-lemma:<strong>` where
`<strong>` is the canonical Hebrew Strong identifier (e.g. `H0001`)
extracted from `strongnumberx` and normalised via
`ingest.canonical_strongs.canonical_strongs(..., lang="hb")`. The
disambiguation suffix (e.g. `A`, `B`) is persisted in
`disambig_suffix` rather than concatenated into `id` so the
Decision 14 uniqueness constraint on `Strong.id` resolves sense splits
to the base Strong code without rejection. The `language` property is
set to `"hebrew"` on every Lemma this adapter writes so the lexical
graph partitions cleanly from Greek lemmas registered by other
adapters.

`GreekLemma` (one node per distinct Septuagint-witness Greek Strong
key referenced from the Hebrew lemma stream via `greekstrong`):

| Property         | Type   | Predicate          | Source decision |
|------------------|--------|--------------------|-----------------|
| id               | string | $pred_string(x)    | Decision 4, 14  |
| strong           | string | $pred_string(x)    | Decision 4, 14  |
| disambig_suffix  | string | $pred_string(x)    | Decision 14     |
| lemma            | string | $pred_string(x)    | Decision 4      |
| language         | string | $pred_string(x)    | Decision 14     |
| source           | string | $pred_string(x)    | Decision 4, 14  |

Stable-id format for GreekLemma: `macula-hebrew-greek-lemma:<strong>`
where `<strong>` is the canonical Greek Strong identifier (e.g.
`G0001`) extracted from `greekstrong` and normalised via
`ingest.canonical_strongs.canonical_strongs(..., lang="gk")`. The
`language` property is `"greek"`. When this adapter creates a
GreekLemma node, `source` is set to `"MACULA-Hebrew"` because the
bridge is annotated on the Hebrew side; downstream MACULA-Greek and
STEPBible-TBESG adapters MERGE on the same `id` and overlay their own
properties without overwriting.

`LouwNidaDomain` is reserved on the Decision 2 surface area for
MACULA-Greek-Nestle1904 and MACULA-Greek-SBLGNT. This adapter
references MACULA-Hebrew's `sdbh` annotation when present, but
Decision 2 binds Louw-Nida to the Greek editions, so the MACULA-Hebrew
adapter MUST NOT create LouwNidaDomain nodes from the Hebrew morpheme
stream. The label is declared in this contract for completeness because
the orchestrator brief lists it under emitted labels for the Hebrew
adapter; the adapter resolves the inconsistency by emitting zero
LouwNidaDomain nodes from its rows and leaving Decision 2 ownership
unchanged. The `IN_DOMAIN` edge is emitted only from Decision 2
adapters.

Emitted edges
=============

`HAS_MACULA_ENRICHMENT` (Word -> MaculaToken):
Source label: `Word {source: 'OSHB-morphology'}`.
Target label: `MaculaToken`.
Edge properties:

| Property     | Type   | Predicate          | Source decision |
|--------------|--------|--------------------|-----------------|
| osis_ref     | string | $pred_string(x)    | Decision 1      |
| join_lemma   | string | $pred_string(x)    | Decision 1      |

Join rule (Decision 1): MATCH OSHB Word by OSIS reference and lemma
identity after Unicode NFC normalisation and whitespace strip; reject
the row if the OSHB lemma differs from the MACULA lemma after NFC.
Reject the row by writing a snapshot-ledger entry under the key
`macula_hebrew.alignment_rejections`; do not emit the edge.

`INSTANCE_OF` (MaculaToken -> Lemma):
Source label: `MaculaToken`.
Target label: `Lemma`.
Edge properties: none beyond the implicit relationship type.
Backed by: Decision 1 (the Hebrew lemma is the canonical Strong-keyed
concept the morpheme instantiates) and Decision 14 (the uniqueness
constraint on `Lemma.id` enforces deduplication of the join target).
The adapter MUST NOT create an INSTANCE_OF edge when `strongnumberx`
is null; the Decision 1 edge-case rule treats functional particles
(definite article `ha-`, conjunctions, prepositions) as carrying no
Strong attachment, and the predicate table marks `strongnumberx` as
nullable.

`BRIDGES_LXX` (Lemma -> GreekLemma):
Source label: `Lemma {source: 'MACULA-Hebrew'}`.
Target label: `GreekLemma`.
Edge properties:

| Property       | Type   | Predicate          | Source decision |
|----------------|--------|--------------------|-----------------|
| greek_surface  | string | $pred_string(x)    | Decision 4      |
| greek_strong   | int    | $pred_int(x)       | Decision 4      |
| source         | string | $pred_string(x)    | Decision 4      |

Bridge rule (Decision 4): persist a BRIDGES_LXX relationship from the
Hebrew Lemma node to a GreekLemma node keyed by `greekstrong`, with
the surface `greek` token attached as the `greek_surface` edge
property rather than overwriting the GreekLemma's own surface form.
When `greekstrong` is null but `greek` is populated, resolve the
GreekLemma by lemma-string lookup against STEPBible-TBESG and, on
failure, record the row under `macula_hebrew.bridge_quarantine` in
the snapshot ledger without dropping the edge; emit the edge against
a sentinel GreekLemma with `id = "macula-hebrew-greek-lemma:unknown"`
and `source = "MACULA-Hebrew"` so the quarantine count remains
visible to the verifier.

`IN_DOMAIN`: not emitted by this adapter (see LouwNidaDomain note
above). Decision 2 binds IN_DOMAIN to MACULA-Greek-Nestle1904 and
MACULA-Greek-SBLGNT; the IN_DOMAIN relationship carries
`domain_code` (int) and `subdomain_code` (int) edge properties
per Decision 2 when those adapters run, and the MACULA-Hebrew
adapter MUST NOT write to it.

Edge cases handled
==================

(Decision 1, functional particles) Hebrew functional particles such
as the definite article `ha-` carry an OSHB morpheme `id` but no
`strongnumberx` value in MACULA-Hebrew. The adapter MUST skip the
Strong attachment and MUST NOT emit an INSTANCE_OF edge for these
rows; the row itself is still emitted as a MaculaToken and the
HAS_MACULA_ENRICHMENT edge is still created. The predicate table
records `strongnumberx` as nullable; `$pred_int(strongnumberx)` is
permitted to return false on these rows.

(Decision 1, Ketiv-Qere) Ketiv-Qere divergence presents two surface
tokens for one consonantal slot. The MACULA-Hebrew adapter MUST NOT
attach MaculaToken enrichment to the qere reading; the qere reading
is owned by the OSHB adapter as a `Reading` node linked by
`IS_QERE_OF`. The MACULA-Hebrew adapter joins only against the
ketiv lemma.

(Decision 1, hapax gloss) Hapax legomena whose ETCBC-BHSA
`freq_lex` equals one occasionally carry a MACULA `gloss` value
that is the literal English string `?`. The adapter MUST normalise
this to a null gloss before persistence so `$pred_string(gloss)`
returns false rather than reporting a populated value.

(Decision 4, proper-noun many-to-many) Hebrew proper nouns such as
theophoric place names route through multiple Greek transliterations
across LXX manuscripts. The adapter MUST tolerate many-to-many edges
from one Hebrew Lemma to several GreekLemma nodes and MUST NOT
collapse them to a winning translation by frequency.

(Decision 4, particle host attachment) Hebrew lemmas whose
`strongnumberx` is null because the original was a functional
particle frequently still carry a `greek` string for the
agglutinated host. The adapter MUST attach the bridge to the host
lemma's Strong rather than fabricating a Strong identifier for the
particle alone. When the host is not resolvable inside the same
verse, the row is recorded under
`macula_hebrew.bridge_orphan_particles` in the snapshot ledger.

(Decision 4, TAHOT LXX-variant) STEPBible-TAHOT LXX-variant columns
(Decision 16 surface area) sometimes assign a different Greek lemma
than MACULA-Hebrew for the same verse. The MACULA-Hebrew adapter
persists its own BRIDGES_LXX edge with `source = 'MACULA-Hebrew'`;
the STEPBible-TAHOT adapter (a separate run) MAY persist its own
BRIDGES_LXX edge for the same lemma pair with `source =
'STEPBible-TAHOT'`. The two edges co-exist by `source` property so
Pipeline 2 sees the disagreement rather than a false consensus.

(Decision 4, TBESG fallback) When `greekstrong` is null and `greek`
is populated, the adapter MUST resolve the Greek lemma by
lemma-string lookup against STEPBible-TBESG entries already in the
graph. The lookup is a MATCH against
`(:BriefLexEntry {source: 'STEPBible-TBESG', language: 'greek'})`
on the `greek` property after NFC normalisation. On lookup miss,
the row is quarantined per the Decision 4 bridge rule above.

(Decision 14, Strong sense suffix) A Strong identifier with a
sense-suffix such as `H1234A` resolves to the base Strong `H1234`
for the Decision 14 uniqueness constraint. The suffix is stored in
the `disambig_suffix` property on the Lemma node rather than
concatenated into `id`, so the uniqueness constraint on `Strong.id`
does not reject legitimate sense splits.

(Decision 14, Source registration) The adapter registers its
canonical source slug `MACULA-Hebrew` against the `Source` label
once at ingest start, before any record-level write. The Decision 14
uniqueness constraint on `Source.slug` rejects duplicate registration
on a second ingest run, which is the intended behaviour because the
adapter is idempotent through MERGE-by-stable-id and a second run
re-uses the existing Source node. The `Source` node carries `slug =
"MACULA-Hebrew"`, `license = "CC-BY-NC-4.0"`, and `redistribute =
false` per the License Tagging contract.

Acceptance Cypher
=================

The phase_02 runbook (bullet 2 for macula_hebrew.py) declares the
following acceptance query verbatim::

    MATCH (w:Word {source: 'OSHB-morphology'})-[:HAS_MACULA_ENRICHMENT]->(m:MaculaToken)
    WITH count(w) AS aligned
    RETURN aligned, aligned > 0

The Decision 1 schema-level acceptance query is stricter and binds
the alignment ratio floor at 0.98::

    MATCH (w:Word {source: 'OSHB-morphology'})
    OPTIONAL MATCH (w)-[:HAS_MACULA_ENRICHMENT]->(m:MaculaToken)
    WITH count(w) AS total, count(m) AS aligned
    RETURN aligned, total, aligned * 1.0 / total AS ratio
      WHERE ratio >= 0.98 AND total > 0

The Decision 4 schema-level acceptance query asserts the bridge
edges populate with the `greek_surface` property::

    MATCH (h:Lemma {source: 'MACULA-Hebrew'})-[b:BRIDGES_LXX]->(g:GreekLemma)
    WHERE b.greek_surface IS NOT NULL
    WITH count(b) AS bridges, count(DISTINCT h) AS hebrew_lemmas
    RETURN bridges, hebrew_lemmas, bridges > 0

The Decision 14 acceptance query asserts the administrative
constraints hold::

    MATCH (s:Strong)
    WITH s.id AS sid, count(*) AS dup_count
    WHERE dup_count > 1 AND sid IS NOT NULL
    WITH collect(sid) AS duplicates
    MATCH (src:Source)
    WITH duplicates, count(DISTINCT src.slug) AS slug_count, count(src) AS src_total
    RETURN size(duplicates) = 0 AND slug_count = src_total

Per-adapter verifier template
=============================

The Phase D verifier `tools/verify_adapter_macula_hebrew.py` follows
the ratio-of-non-empty-fields pattern from
`docs/implementation_phases/phase_02_lexical_ingest.md` section
"Per-adapter acceptance pattern". Tier A binds an exact-match floor
on the morpheme count of 475911. The verifier references
`tools/predicates_by_type.cypher` via the `:include` directive so no
predicate is inlined in the verifier script.

Stable identifiers summary
==========================

* MaculaToken.id: `<xml:id>` value verbatim from the upstream lowfat
  TEI file. No prefix is added because the upstream identifier is
  already globally unique within the MACULA-Hebrew release.
* Lemma.id: `macula-hebrew-lemma:<strong>` where `<strong>` is the
  canonical Hebrew Strong identifier.
* GreekLemma.id: `macula-hebrew-greek-lemma:<strong>` where
  `<strong>` is the canonical Greek Strong identifier. The downstream
  MACULA-Greek and STEPBible-TBESG adapters MERGE on the same `id`.
* Source.slug: `MACULA-Hebrew` (Decision 14 uniqueness constraint on
  `Source.slug`).
* Strong.id: the canonical Strong identifier with sense suffix stored
  separately in `disambig_suffix` (Decision 14 uniqueness constraint
  on `Strong.id`).

Idempotency
===========

Every node and edge written by this adapter is MERGE-by-stable-id.
A second run against identical source bytes MUST produce a
byte-for-byte identical per-row SHA-256 vector under the
Phase D triangle test. The wipe contract in `tools/wipe_lexical.py`
deletes every node and relationship in the lexical Neo4j before
re-ingest, so MERGE writes start from an empty store and the
Decision 14 uniqueness constraints reject any second-write attempt
for the same identifier.

Network isolation
=================

The adapter reads only from the local pre-fetched cache at
`data/private/macula-hebrew/WLC/`. The AST scan
`tools/check_adapter_purity.py` rejects imports of `subprocess`,
`socket`, `httpx`, `requests`, `urllib`, `aiohttp`, `mmap`,
`os.system`, `os.spawn*`, `posix_spawn`,
`multiprocessing.connection`, `pty`, `pipes`, `winreg`, `ctypes`,
and dynamic `__import__`. The implementer-impl caste's follow-on
commit is bound by that scan.

Caste boundary
==============

This file is the implementer-docstring contract surface. The
implementer-impl caste commits the executable body in a separate
commit against the same path. The caste boundary is enforced by
`tools/check_caste.py` against the commit's `Caste:` trailer.
"""
