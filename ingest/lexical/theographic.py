"""Theographic Bible Metadata adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the Theographic Bible Metadata projection adapter for the
Pipeline 1 lexical Neo4j reseed. The body of this file is intentionally
empty at this commit because Phase C.1 of the RESEED_PLAN
(verifier-caste architecture) requires the contract to be committed
BEFORE any implementation body and BEFORE the Verifier-caste subagent
writes its coverage tests. The Verifier compiles its test queries
against this docstring plus the matching sections of
docs/SCHEMA_DECISIONS.md without reading the implementation body. The
function-body commit is a separate downstream commit by the
Implementer-impl caste.

Source inventory
================
Source slug:      Theographic-Bible-Metadata
Tier:             A (deterministic, tolerance 0)
Expected count:   43690 records (record_unit: multi_entity_record). The
                  total is the exact sum of upstream-published per-file
                  counts in the versioned github release, summed across
                  all entity types this adapter projects (Person, Place,
                  Period, Event, Group, Tribe) plus the upstream books,
                  chapters, verses, and easton entries the catalog row
                  records under the same source slug. This adapter does
                  not project books, chapters, verses, or easton entries
                  into the graph because those overlap canonical Verse
                  nodes already populated by Group 1 (text floor); the
                  43690 record_unit total is the line-count fingerprint
                  that the snapshot ledger pins, not a per-node-label
                  count.
Tier rationale:   Theographic ships a multi-file JSON corpus across
                  books, chapters, verses, people, places, periods,
                  events, and easton entries. The total is a
                  deterministic per-file row count from the versioned
                  github release used at ingest, identical across reruns
                  under tagged builds.
Decisions implemented: 10, 14.

Upstream and license
====================
Upstream path:    data/private/theographic/json/ (folder hierarchy of
                  JSON-and-Markdown documents under people/, places/,
                  periods/, events/, groups/, and tribes/ as Decision
                  10 Rule specifies). Each entity is one file; the
                  filename slug is the canonical identifier preserved
                  as entity_id verbatim.
License id:       CC-BY-SA-4.0 per docs/LICENSE_TAGGING.md row for
                  Theographic-Bible-Metadata; the SA propagation
                  requirement attaches to any derivative that
                  redistributes the data. The Source node MERGEd by
                  this adapter carries redistribute = true per Decision
                  14 because the upstream license permits
                  redistribution under the SA terms.
Source record:    The Source node for slug 'Theographic-Bible-Metadata'
                  is MERGEd once per ingest run with properties:
                    slug          = 'Theographic-Bible-Metadata'  ($pred_string)
                    license       = 'CC-BY-SA-4.0'                ($pred_string)
                    redistribute  = true                          ($pred_bool)
                  per Decision 14 Source uniqueness constraint
                  (source_slug constraint, graph/lexical.cypher).

Stable identifier policy
========================
Decision 10 Edge cases handled bullet 1 (several persons share a common
name, e.g. numerous Marys and several Zechariahs) and bullet 2 (place
entries with overlapping ancient and modern names) both require the
canonical filename slug from the upstream folder hierarchy to be
preserved verbatim as entity_id rather than the display name. The
display_name is a free-form human label that collides across distinct
entities (the canonical example is 'Mary' resolving to at least Mary
mother of Jesus, Mary Magdalene, Mary of Bethany, Mary of Clopas, Mary
mother of John Mark, and Mary of Rome). The upstream disambiguates via
the file slug (e.g. 'mary-mother-of-jesus', 'mary-magdalene',
'mary-of-bethany'); this adapter MUST persist that slug as entity_id
verbatim so OSIS verse references resolve to the correct individual
rather than collapsing on display name.

The uniqueness constraints in graph/lexical.cypher
(person_id, place_id, event_id, period_id, group_id, tribe_id) all
REQUIRE entity_id UNIQUE per Decision 10. Two entities of the same
upstream type whose slugs collide are an upstream schema violation and
MUST be rejected at adapter time with a quarantine ledger entry; the
adapter MUST NOT mint a synthetic suffix to side-step the constraint.

Emitted node labels and properties
==================================
The adapter MERGEs six entity labels (Person, Place, Period, Event,
Group, Tribe) plus the shared Source administrative node. Each row
below quotes its persisted property name, the primitive type the value
carries, and the matching predicate from
tools/predicates_by_type.cypher. The adapter MUST NOT invent fields
the upstream JSON does not supply (Decision 10 Rule, second sentence);
per-entity field presence is recorded in the snapshot ledger so the
triangle test detects upstream schema drift on re-ingest.

Person (Decision 10 Person projection)
--------------------------------------
Stable id format:    The upstream filename slug for the person entry
                     under data/private/theographic/json/people/ (e.g.
                     'mary-mother-of-jesus', 'zechariah-priest-of-the-
                     division-of-abijah', 'paul-of-tarsus'). The slug
                     is preserved verbatim from the upstream filename
                     stem.
Stable id property:  entity_id (string, $pred_string).
MERGE key:           Person.entity_id (constraint person_id,
                     graph/lexical.cypher; REQUIRES entity_id UNIQUE).
Persisted properties (Decision 10 Per-field predicate type table,
Person projection):
    entity_id              string  $pred_string(x)
    display_name           string  $pred_string(x)
    verses                 list    $pred_list(x)
    description_markdown   string  $pred_string(x)   (nullable; only
                                                      populated on
                                                      person files that
                                                      carry a free-form
                                                      Markdown body
                                                      under the YAML
                                                      frontmatter per
                                                      Decision 10 Edge
                                                      cases handled
                                                      bullet 3)
    source                 string  $pred_string(x)   (= 'Theographic-Bible-Metadata')

The verses list is the normalised OSIS reference list extracted from
the upstream verses array; each element is a verse osisID string (e.g.
'Matt.1.16', 'Luke.1.27'). The adapter MUST NOT silently rewrite
upstream verse identifiers; if an upstream reference does not resolve
under the canonical OSIS reference space the row is recorded in the
quarantine ledger and the unresolved reference is dropped from the
verses list rather than fabricated.

Place (Decision 10 Place projection)
------------------------------------
Stable id format:    The upstream filename slug for the place entry
                     under data/private/theographic/json/places/ (e.g.
                     'bethlehem-of-judah', 'caesarea-philippi',
                     'jerusalem'). Slug is preserved verbatim.
Stable id property:  entity_id (string, $pred_string).
MERGE key:           Place.entity_id (constraint place_id,
                     graph/lexical.cypher; REQUIRES entity_id UNIQUE).
Persisted properties (Decision 10 Per-field predicate type table,
Place projection):
    entity_id      string  $pred_string(x)
    display_name   string  $pred_string(x)
    aliases        list    $pred_list(x)   (alternative ancient and
                                            modern names for the same
                                            place; Decision 10 Edge
                                            cases handled bullet 2
                                            requires aliases to be
                                            persisted on the same Place
                                            node rather than emitting
                                            duplicate nodes)
    verses         list    $pred_list(x)
    source         string  $pred_string(x)   (= 'Theographic-Bible-Metadata')

Period (Decision 10 Period projection)
--------------------------------------
Stable id format:    The upstream filename slug for the period entry
                     under data/private/theographic/json/periods/ (e.g.
                     'patriarchal-period', 'united-monarchy',
                     'second-temple-period'). Slug is preserved
                     verbatim.
Stable id property:  entity_id (string, $pred_string).
MERGE key:           Period.entity_id (constraint period_id,
                     graph/lexical.cypher; REQUIRES entity_id UNIQUE).
Persisted properties (Decision 10 Per-field predicate type table,
Period projection):
    entity_id      string  $pred_string(x)
    display_name   string  $pred_string(x)
    start_year     int     $pred_int(x)    (BCE years are negative
                                            integers, CE years are
                                            positive; the adapter MUST
                                            persist the upstream
                                            integer verbatim without
                                            sign coercion so the
                                            triangle-test hash recompute
                                            preserves byte-identical
                                            output)
    end_year       int     $pred_int(x)
    source         string  $pred_string(x)   (= 'Theographic-Bible-Metadata')

Event (Decision 10 extrapolated from Person/Place pattern)
----------------------------------------------------------
Stable id format:    The upstream filename slug for the event entry
                     under data/private/theographic/json/events/ (e.g.
                     'crucifixion-of-jesus', 'exodus-from-egypt',
                     'fall-of-jerusalem-586-bce'). Slug is preserved
                     verbatim.
Stable id property:  entity_id (string, $pred_string).
MERGE key:           Event.entity_id (constraint event_id,
                     graph/lexical.cypher; REQUIRES entity_id UNIQUE).
Upstream-supplied fields (the adapter MUST NOT invent fields the
upstream JSON does not supply per Decision 10 Rule sentence two; the
fields below are the projection contract for fields the upstream
records on event entries):
    entity_id      string  $pred_string(x)
    display_name   string  $pred_string(x)
    verses         list    $pred_list(x)   (OSIS reference list of
                                            verses that narrate or
                                            mention the event)
    source         string  $pred_string(x)   (= 'Theographic-Bible-Metadata')
    description_markdown   string  $pred_string(x)   (nullable; only
                                                      populated on
                                                      event files that
                                                      carry a free-form
                                                      Markdown body
                                                      under the YAML
                                                      frontmatter per
                                                      Decision 10 Edge
                                                      cases handled
                                                      bullet 3)

Group (Decision 10 extrapolated from Person/Place pattern)
----------------------------------------------------------
Stable id format:    The upstream filename slug for the group entry
                     under data/private/theographic/json/groups/ (e.g.
                     'pharisees', 'sadducees', 'samaritans',
                     'twelve-apostles'). Slug is preserved verbatim.
Stable id property:  entity_id (string, $pred_string).
MERGE key:           Group.entity_id (constraint group_id,
                     graph/lexical.cypher; REQUIRES entity_id UNIQUE).
Upstream-supplied fields (projection contract; the adapter MUST NOT
invent fields the upstream JSON does not supply):
    entity_id      string  $pred_string(x)
    display_name   string  $pred_string(x)
    verses         list    $pred_list(x)
    source         string  $pred_string(x)   (= 'Theographic-Bible-Metadata')
    description_markdown   string  $pred_string(x)   (nullable; same
                                                      free-form
                                                      Markdown body rule
                                                      as Person and
                                                      Event)

Tribe (Decision 10 extrapolated from Person/Place pattern)
----------------------------------------------------------
Stable id format:    The upstream filename slug for the tribe entry
                     under data/private/theographic/json/tribes/ (e.g.
                     'tribe-of-judah', 'tribe-of-levi',
                     'tribe-of-benjamin'). Slug is preserved verbatim.
Stable id property:  entity_id (string, $pred_string).
MERGE key:           Tribe.entity_id (constraint tribe_id,
                     graph/lexical.cypher; REQUIRES entity_id UNIQUE).
Upstream-supplied fields (projection contract; the adapter MUST NOT
invent fields the upstream JSON does not supply):
    entity_id      string  $pred_string(x)
    display_name   string  $pred_string(x)
    verses         list    $pred_list(x)
    source         string  $pred_string(x)   (= 'Theographic-Bible-Metadata')

Source (Decision 14)
--------------------
Stable id format:    'Theographic-Bible-Metadata' (verbatim source slug).
Stable id property:  slug (string, $pred_string).
MERGE key:           Source.slug (constraint source_slug,
                     graph/lexical.cypher).
Persisted properties (Decision 14 Per-field predicate type table):
    slug            string  $pred_string(x)
    license         string  $pred_string(x)   (= 'CC-BY-SA-4.0')
    redistribute    bool    $pred_bool(x)     (= true; the upstream
                                               license permits
                                               redistribution under
                                               the SA propagation
                                               requirement per
                                               docs/LICENSE_TAGGING.md
                                               and Decision 14)

Emitted edge types
==================
The adapter emits one outbound edge type from each entity label plus
the shared FROM_EDITION provenance edge. Every edge below has src and
dst labels fixed and is MERGEd by the src+dst+rel_type tuple so
re-ingest over identical input does not multiply edges.

MENTIONS (Decision 10)
    src: Person / Place / Period / Event / Group / Tribe
    dst: Verse
    properties:          (none)
    join key:            entity.verses list element is the dst Verse
                         osisID. The Verse nodes are emitted by Group 1
                         (text floor) per the dispatch order in
                         docs/implementation_phases/phase_02_lexical_ingest.md;
                         this adapter only MERGEs the edge from the
                         entity to the existing Verse, never creating
                         Verse nodes itself.
    cardinality:         one MENTIONS edge per (entity, osis_reference)
                         tuple. Entities that mention the same verse
                         more than once in upstream prose produce one
                         edge, not many, because the upstream verses
                         array is a deduplicated set per entity in the
                         Decision 10 projection contract.

FROM_EDITION (Decision 14)
    src: Person / Place / Period / Event / Group / Tribe
    dst: Source
    properties:          (none)
    cardinality:         exactly one per entity. The Source node is
                         MERGEd once at ingest start, before any
                         record-level write, so the source_slug
                         uniqueness constraint check runs against the
                         registered slug only per Decision 14 Edge
                         cases handled bullet 2.

Dependency on Group 1
=====================
This adapter depends on the Verse nodes emitted by the text-floor
group in docs/implementation_phases/phase_02_lexical_ingest.md Group 1
(OSHB-morphology, MACULA-Greek, MorphGNT-SBLGNT). The MENTIONS edge
join is keyed by entity.verses element against Verse.osisID; if Group
1 has not run, the MENTIONS edges remain unwritten but the entity
nodes still merge under their entity_id uniqueness constraints. The
dispatch order in phase_02_lexical_ingest.md places this adapter in
Group 5 (Cross-references and metadata) step 19 which runs after the
text floor, so the join is well-defined under the runbook execution
order.

Idempotency
===========
Every node above is MERGEd by its stable entity_id property (slug from
the upstream filename) or by Source.slug for the Source node. Every
edge is MERGEd on the (src.entity_id, dst.osisID, rel_type) tuple for
MENTIONS, or (src.entity_id, Source.slug, 'FROM_EDITION') for
FROM_EDITION. Re-running this adapter over identical Theographic input
bytes produces zero new nodes and zero new edges. The
graph/lexical.cypher uniqueness constraints person_id, place_id,
event_id, period_id, group_id, tribe_id, and source_slug additionally
enforce this at the Neo4j storage layer. Per RESEED_PLAN D.3 the
snapshot ledger records each row as a sorted SHA-256 over the
canonical-JSON of its property bag, and the triangle test asserts
byte-equal snapshot across two runs over identical inputs.

Edge cases handled
==================
Per Decision 10 Edge cases handled:
  1. Several persons share a common name. Numerous Marys (Mary mother
     of Jesus, Mary Magdalene, Mary of Bethany, Mary of Clopas, Mary
     mother of John Mark, Mary of Rome) and several Zechariahs (the
     priest of the division of Abijah, the prophet son of Berechiah,
     the son of Jehoiada the priest) all carry the same display_name
     in the upstream JSON. The adapter MUST preserve the upstream
     filename slug verbatim as entity_id so the uniqueness constraint
     person_id accepts each as a distinct Person node and OSIS verse
     references resolve to the correct individual rather than
     collapsing on display name. The display_name is persisted only
     for human-readable display; it is never used as a MERGE key.
  2. Place entries sometimes carry overlapping ancient and modern
     names (e.g. an ancient place known by a different modern toponym).
     The adapter MUST persist each as an alias on the same Place node
     rather than emitting duplicate nodes, storing the canonical
     filename slug as entity_id and the alternative names in the
     aliases list. The place_id uniqueness constraint on entity_id
     ensures one node per upstream file regardless of how many alias
     surface forms the entry carries.
  3. A small number of entity files contain free-form Markdown body
     text under the YAML frontmatter. The adapter MUST attach that
     body as a description_markdown property without parsing it into
     structured fields, because the upstream does not promise schema
     for the prose body. Entities whose upstream file carries no body
     omit the description_markdown property entirely so
     $pred_string(description_markdown) returns false on those nodes
     rather than an empty string being a misleading explicit empty
     value.

Per Decision 14 Edge cases handled:
  1. A Strong identifier with a sense suffix is not relevant to this
     adapter because Theographic entities do not carry Strong codes;
     the Decision 14 Strong constraint policy applies to other
     adapters in the lexical store. This adapter still respects the
     constraint by never writing Strong nodes.
  2. The Source node for slug 'Theographic-Bible-Metadata' is MERGEd
     exactly once at ingest start, before any record-level write, so
     the source_slug uniqueness constraint check runs against the
     registered slug only.

Adapter MUST NOT invent fields
==============================
Decision 10 Rule sentence two states the adapter MUST NOT invent
fields the upstream JSON does not supply. The snapshot ledger MUST
record per-entity field presence so the triangle test detects upstream
schema drift on re-ingest. Concretely:

  * Person, Event, and Group entries that lack a Markdown body in the
    upstream file MUST omit description_markdown entirely from the
    Neo4j node property bag; the adapter does not write null, does
    not write an empty string, and does not write a synthesised
    placeholder.
  * Place entries with no alias list in the upstream YAML MUST omit
    aliases entirely; the adapter does not write an empty list to
    satisfy the $pred_list predicate.
  * Period entries with missing start_year or end_year (some periods
    are open-ended at one boundary) MUST omit the missing field
    entirely; the adapter does not write zero or a sentinel value.
  * Tribe entries with no upstream verses array MUST omit verses
    entirely; the adapter does not write an empty list.

Per-entity field presence is recorded in the snapshot ledger as a
sorted vector of (entity_id, present_field_name) pairs. The triangle
test compares the snapshot ledger across two runs over identical
upstream bytes and rejects any drift in present-field membership.

Acceptance Cypher (phase_02_lexical_ingest.md Group 5 step 19, verbatim)
========================================================================

    MATCH (p:Person {source: 'Theographic-Bible-Metadata'})
    WHERE p.entity_id IS NOT NULL AND p.display_name IS NOT NULL
    WITH count(p) AS persons
    RETURN persons, persons > 0

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 5 step 19
and is the runbook acceptance gate the Phase D verifier runs against
the populated lexical store.

Acceptance Cypher (Decision 10, two-thousand-persons floor)
===========================================================

    MATCH (p:Person {source: 'Theographic-Bible-Metadata'})
    WHERE p.entity_id IS NOT NULL AND p.display_name IS NOT NULL
    WITH count(p) AS persons
    RETURN persons, persons >= 2000

This query is reproduced byte-for-byte from docs/SCHEMA_DECISIONS.md
Decision 10 Cypher acceptance query and asserts the two-thousand
persons floor that anchors Theographic as the bulk source of
biblical-person metadata for Pipeline 2 entity-resolution bundles. The
Tier A expected_count of 43690 in tools/expected_counts.json
sources."Theographic-Bible-Metadata" is the upstream multi-file row
count fingerprint and is well above the two-thousand-persons floor;
the floor exists so a partial-ingest failure of the people/ folder
trips the gate even if other entity folders ingested cleanly.

Network isolation
=================
This adapter reads from local disk only (the cached Theographic
release under data/private/theographic/json/). It MUST NOT import
subprocess, socket, httpx, requests, urllib, aiohttp, mmap,
os.system, os.spawn*, posix_spawn, multiprocessing.connection, pty,
pipes, winreg, ctypes, or dynamic __import__, per
tools/check_adapter_purity.py and RESEED_PLAN C.4. The Phase C dry-run
executes the adapter inside Docker with --network=none.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 10   Theographic Bible Metadata projection schema, per-field predicate tables for Person, Place, and Period (Event, Group, Tribe extrapolated from the Person and Place pattern under the Decision 10 Rule that the adapter MUST NOT invent fields).
docs/SCHEMA_DECISIONS.md Decision 14   Strong / Source / TFNode constraint policy, license slug 'CC-BY-SA-4.0', redistribute true.
docs/implementation_phases/phase_02_lexical_ingest.md Group 5 step 19.
docs/implementation_phases/RESEED_PLAN.md Phase C.1 (TDD workflow per adapter) and Idempotency section of phase_02.
graph/lexical.cypher constraints person_id, place_id, event_id, period_id, group_id, tribe_id (all REQUIRE entity_id UNIQUE), plus source_slug for the Source node, plus indexes person_display_name and place_display_name for display-name lookup performance against the bulk of Theographic entities.
tools/expected_counts.json sources."Theographic-Bible-Metadata" (tier A, expected_count 43690, record_unit multi_entity_record, tolerance 0).
tools/predicates_by_type.cypher for $pred_string, $pred_int, $pred_list, $pred_bool semantics.
docs/LICENSE_TAGGING.md row 'Theographic-Bible-Metadata' for the CC-BY-SA-4.0 license tag and the redistribute-true policy under Decision 14 with the SA propagation note.
docs/phase_prompts/pipeline2_verdict.md citation slug 'Theographic-Bible-Metadata' for Pipeline 2 evidence-file tagging of any Theographic citation.
"""
