"""open-cbgm 3 John CBGM ingest docstring contract (Phase C, Wave 1).

This module is intentionally a single docstring expression. The runnable
implementation is added in a follow-on commit by the implementer-impl
caste. This file freezes the upstream field contract, edge contract,
stable identifier strategy, license posture, and acceptance Cypher
block so the verifier caste can build conformance tests against a
stable specification.

============================================================
1. Scope and source slug
============================================================

Source slug `open-cbgm-3-john` covers exactly 3 John verses one
through fifteen. The scope is locked at chapter one of 3 John and
no other ECM Catholic Letters book is ingested by this adapter:

  tier B, record unit `cbgm_record`, expected count 600,
  tolerance_relative 0.02, tolerance_absolute_cap_records 1000,
  minimum 588, maximum 612.

Tier B means the count is derived from joins across the local
SQLite database tables and the TEI XML elements rather than from a
single line count. The relative tolerance of two percent capped at
one thousand absolute records absorbs minor collation revisions in
the upstream open-cbgm sample without flipping the acceptance gate.
The expected count of 600 is the sum of nodes plus edges expected
across 3 John verses one through fifteen at the collation revision
captured by the local asset.

The exclusion of ECM Catholic Letters beyond 3 John is recorded at
`docs/data_inventory_catalog.json` at `explicit_deadends[0]` with
the binding reason and the dated decision; this adapter MUST NOT
attempt to ingest any other ECM Catholic Letters book even if the
upstream database files happen to contain those rows. The Old Latin
Vetus Latina exclusion at `explicit_deadends[2]` and the LXX Rahlfs
standalone exclusion at `explicit_deadends[1]` are likewise
out-of-scope for this adapter; they are settled at the inventory
layer.

============================================================
2. Decision implemented (Decision 6)
============================================================

Decision 6 in `docs/SCHEMA_DECISIONS.md` titled "CBGM Witness /
Variant / Reading shape (3 John Layer 1 only)" is the single
governing decision for this adapter. The Decision 6 rule binds the
adapter to emit `Witness`, `VariantUnit`, and `Reading` nodes for
the verses one through fifteen scope, with `READS_AT` edges from
Witness to Reading qualified by `variant_unit_id`, and an
`ATTESTED_BY` edge from Reading to VariantUnit. The Decision 6
acceptance Cypher block (see section 7 below) is the authoritative
gate for this ingest.

Decision 14 also applies indirectly: the adapter MUST register a
single `Source` node with slug `open-cbgm-3-john`, license `MIT`,
and `redistribute = true` per the citation slug declaration in
`docs/phase_prompts/pipeline2_verdict.md` and the license tagging
table in `docs/LICENSE_TAGGING.md`. The Source uniqueness constraint
`source_slug` in `graph/lexical.cypher` rejects any duplicate slug
write.

============================================================
3. Upstream fields and per-node predicate tables
============================================================

The Decision 6 per-field predicate tables list the persisted
properties for each emitted label. Every predicate resolves through
`tools/predicates_by_type.cypher`; inline predicates are forbidden
by the verifier conformance rules.

Witness node properties:

  | Field         | Type   | Predicate         |
  |---------------|--------|-------------------|
  | siglum        | string | $pred_string(x)   |
  | date_century  | int    | $pred_int(x)      |
  | language      | string | $pred_string(x)   |
  | ga_number     | string | $pred_string(x)   |

`siglum` is the manuscript siglum verbatim from the collation
header, persisted as the human-readable witness label. The
`witness_siglum` UNIQUE constraint in `graph/lexical.cypher` makes
this the primary join key for witness-coverage queries.

`date_century` is the manuscript dating in calendar centuries (for
example a tenth-century manuscript carries `date_century = 10`).
The `witness_date` index in `graph/lexical.cypher` enables
century-bracketed witness queries without scanning the full label.

`language` is the manuscript language identifier (greek, latin,
coptic, syriac). The string is normalised to lowercase before
persistence so case-sensitive joins against the open-cbgm
collation do not split equivalent values.

`ga_number` is the Gregory-Aland identifier, the canonical
NT-witness key used across critical editions. The `witness_ga`
UNIQUE constraint in `graph/lexical.cypher` enforces global
uniqueness on this key so cross-collation joins (used by the
ATTESTED_BY traversal) cannot collide on duplicated GA numbers.
Witnesses keyed by siglum alone (with no GA number, such as a
purely versional witness) carry `ga_number = null`; the
$pred_string predicate then correctly reports the gap.

VariantUnit node properties:

  | Field           | Type   | Predicate         |
  |-----------------|--------|-------------------|
  | variant_unit_id | string | $pred_string(x)   |
  | book            | string | $pred_string(x)   |
  | chapter         | int    | $pred_int(x)      |
  | verse           | int    | $pred_int(x)      |

`variant_unit_id` is the open-cbgm collation variant-unit
identifier, persisted verbatim. The `variant_unit_id` UNIQUE
constraint in `graph/lexical.cypher` enforces one VariantUnit per
identifier. The `variant_unit_book_ch_v` index covers the
`(book, chapter, verse)` triple for verse-scoped queries.

`book` is the canonical OSIS book code, fixed at the literal string
`3John` for every node this adapter writes. A row from the upstream
that resolves to any other book code is a quarantine event, not a
node-creation event; the inventory-catalog exclusion in section 1
governs the scope.

`chapter` is the integer chapter number, fixed at 1 for every node
this adapter writes. 3 John has a single chapter; any other value
is a quarantine event.

`verse` is the integer verse number, restricted to the closed
range 1 through 15. Rows with `verse` outside that range are
quarantined rather than persisted, because 3 John has fifteen
verses and the open-cbgm collation snapshot at this revision
covers exactly that range.

Reading node properties:

  | Field      | Type   | Predicate         |
  |------------|--------|-------------------|
  | reading_id | string | $pred_string(x)   |
  | text       | string | $pred_string(x)   |
  | is_lacuna  | bool   | $pred_bool(x)     |

`reading_id` is the open-cbgm collation reading identifier,
persisted verbatim. The `reading_id` UNIQUE constraint in
`graph/lexical.cypher` enforces one Reading per identifier. The
`reading_variant_unit` index covers the `variant_unit_id` lookup
used by the ATTESTED_BY traversal.

`text` is the reading surface form. For lacuna readings (see edge
case A in section 8) the `text` value is the empty string, and the
$pred_string predicate correctly reports the absence of text. For
single-reading variant units (see edge case B in section 8) the
`text` value carries the sole attested surface form.

`is_lacuna` is a boolean discriminator that surfaces the lacuna
sentinel directly to coverage queries. The $pred_bool predicate
treats both true and false as populated; the value is never null.

============================================================
4. Emitted edges
============================================================

Edge `READS_AT` (Witness to Reading):
  One edge per upstream witness-to-reading attestation row. The
  edge is qualified by a `variant_unit_id` property carrying the
  variant unit at which the witness reads the given Reading.
  Qualifying the edge with the variant-unit identifier on the edge
  itself (rather than relying on the Reading endpoint to imply the
  unit) is required by Decision 6 so that witness-coverage queries
  can pre-filter by variant unit without walking through Reading.

  | Edge property    | Type   | Predicate         |
  |------------------|--------|-------------------|
  | variant_unit_id  | string | $pred_string(x)   |
  | source           | string | $pred_string(x)   |

  `source` is the literal string `open-cbgm-3-john` for every edge
  this adapter writes, recorded on the edge so Pipeline 2
  provenance filters can isolate this ingest from any other CBGM
  ingest without joining on the endpoint nodes.

Edge `ATTESTED_BY` (Reading to VariantUnit):
  One edge per Reading node. The edge has no property payload
  beyond `source`; it expresses the structural attachment of the
  Reading to its parent VariantUnit. The `reading_variant_unit`
  index on `Reading.variant_unit_id` accelerates the lookup from
  Reading back to VariantUnit when the traversal direction is
  inverted.

  | Edge property | Type   | Predicate         |
  |---------------|--------|-------------------|
  | source        | string | $pred_string(x)   |

Edge `CORRECTOR_OF` (corrector-hand Witness to base-hand Witness):
  One edge per corrector annotation in the collation. Corrector
  hands annotated as `<witness>C` (a correction) or `<witness>*`
  (the original hand reading before correction) are emitted as
  distinct Witness nodes per Decision 6 edge case C, and the
  `CORRECTOR_OF` edge expresses the relationship from the
  corrector-hand witness to its base-hand witness. The direction is
  from the corrector node to the base node. Merging hands into a
  single Witness node is forbidden because doing so silently
  collapses divergent readings into one attestation profile.

  | Edge property | Type   | Predicate         |
  |---------------|--------|-------------------|
  | source        | string | $pred_string(x)   |

The expected edge counts for `HAS_VARIANT_UNIT` (eighty to two
hundred) and `HAS_READING` (two hundred fifty to six hundred) in
`tools/expected_counts.json` are not edges this adapter emits
directly; they are aggregate counts the verifier infers from the
ATTESTED_BY traversal and the Reading-per-VariantUnit aggregation
on the lexical store. The acceptance gate in section 7 below is
the binding check.

============================================================
5. Stable identifier strategy and MERGE pattern
============================================================

Witness keying:
  Witness nodes are keyed by `siglum` (witness_siglum UNIQUE
  constraint) and additionally by `ga_number` (witness_ga UNIQUE
  constraint, when ga_number is non-null). Both constraints are
  enforced by the graph; the implementer-impl caste MUST MERGE on
  the siglum so that witnesses without a GA number remain unique by
  siglum alone, and the GA number is set as a property within the
  ON CREATE / ON MATCH clause rather than acting as a second MERGE
  pivot. Corrector hands carry a distinct siglum suffix (the `*` or
  `C` character is part of the siglum string itself) so the
  uniqueness constraint distinguishes them from the base hand
  without any merge collision.

VariantUnit keying:
  VariantUnit nodes are keyed by `variant_unit_id` (variant_unit_id
  UNIQUE constraint). The triple `(book, chapter, verse)` is also
  indexed for range queries but is NOT a uniqueness pivot, because
  one verse can carry many variant units.

Reading keying:
  Reading nodes are keyed by `reading_id` (reading_id UNIQUE
  constraint). The `variant_unit_id` is also stored on the Reading
  node itself and is indexed for the inverted ATTESTED_BY lookup,
  but it is NOT a uniqueness pivot because the same variant unit
  carries multiple Reading nodes.

The Cypher MERGE pattern the implementer-impl caste MUST use for
the READS_AT edge is:

    MATCH (w:Witness {siglum: $siglum})
    MATCH (rd:Reading {reading_id: $reading_id})
    MERGE (w)-[r:READS_AT {variant_unit_id: $variant_unit_id}]->(rd)
    ON CREATE SET r.source = 'open-cbgm-3-john'
    ON MATCH  SET r.source = 'open-cbgm-3-john'

The MATCH-then-MERGE form is mandatory; a single MERGE with inline
node patterns would create a sentinel `Witness` or `Reading` node
if the lookup failed, which would silently corrupt the keyspace.
The adapter MUST treat a missing endpoint as a quarantine event,
not a node-creation event.

The MERGE pattern for the ATTESTED_BY edge is analogous, keyed by
the ordered tuple `(reading_id, variant_unit_id)`. The MERGE
pattern for the CORRECTOR_OF edge is keyed by the ordered tuple
`(corrector siglum, base siglum)`.

============================================================
6. Procurement, network isolation, and AST purity
============================================================

The procurement entry `open-cbgm-3-john` resolves to a local SQLite
asset at `tmp/poc/cbgm/3_john.db` plus the TEI XML collation at
`tmp/poc/cbgm/3_john_collation.xml`. No network access happens
during ingest: both files MUST be present on disk before the
adapter starts. The Phase 02 runbook records the procurement
boundary explicitly under "Network isolation" and "Group 6:
Procurement sources".

Per `docs/implementation_phases/phase_02_lexical_ingest.md`,
adapter dry-runs execute inside Docker with `--network=none`, which
forbids any HTTP, DNS, or socket access during ingest. The AST scan
`tools/check_adapter_purity.py` rejects any adapter that imports
`subprocess`, `socket`, `httpx`, `requests`, `urllib`, `aiohttp`,
`mmap`, `os.system`, `os.spawn*`, `posix_spawn`,
`multiprocessing.connection`, `pty`, `pipes`, `winreg`, `ctypes`,
or dynamic `__import__`. The implementer-impl caste commit that
adds the runnable adapter body MUST satisfy that purity scan; the
local SQLite plus TEI XML pair under `tmp/poc/cbgm/` is the only
input.

============================================================
7. Acceptance Cypher (verbatim from phase_02 bullet 23)
============================================================

The Phase D verifier asserts the following query, copied verbatim
from `docs/implementation_phases/phase_02_lexical_ingest.md`
bullet 23, returns at least one row with `units > 0`:

    MATCH (w:Witness)-[:READS_AT]->(rd:Reading)-[:ATTESTED_BY]->(v:VariantUnit)
    WHERE v.book = '3John' AND v.chapter = 1 AND v.verse >= 1 AND v.verse <= 15
    WITH count(DISTINCT v) AS units
    RETURN units, units > 0

The Decision 6 acceptance Cypher in `docs/SCHEMA_DECISIONS.md` is
stricter: it asserts both `units > 0` AND `witnesses > 0` over the
same traversal, and the verifier conformance pipeline MUST execute
the Decision 6 form (not just the phase_02 bullet form) before
declaring the ingest acceptable:

    MATCH (w:Witness)-[r:READS_AT]->(rd:Reading)-[:ATTESTED_BY]->(v:VariantUnit)
    WHERE v.book = '3John' AND v.chapter = 1 AND v.verse >= 1 AND v.verse <= 15
    WITH count(DISTINCT v) AS units, count(DISTINCT w) AS witnesses
    RETURN units, witnesses, units > 0 AND witnesses > 0

============================================================
8. Edge cases (from Decision 6 bullets)
============================================================

Case A: lacuna reading.
  A witness physically illegible at a variant unit is represented
  in the open-cbgm collation by an empty reading. The adapter MUST
  emit a sentinel `Reading {is_lacuna: true, text: ''}` rather
  than skipping the edge, so witness-coverage queries do not
  mistake silence for support. The lacuna sentinel carries a
  reading_id distinct from any non-lacuna Reading at the same
  variant unit so the reading_id uniqueness constraint is
  satisfied. The READS_AT edge from the witness to the lacuna
  Reading is qualified with the same `variant_unit_id` property as
  any other Reading edge at that unit.

Case B: single-reading variant unit.
  Some variant units in the open-cbgm sample collapse to a single
  reading attested by every witness in scope (no real variation
  at that unit). The adapter MUST persist them anyway with one
  Reading node and N READS_AT edges, because Pipeline 2 verdict
  logic needs to see the full attestation profile. Skipping
  no-variation units would silently drop coverage data the
  downstream consumer requires.

Case C: corrector hands as distinct Witness nodes.
  The 3 John collation contains a small number of corrector hands
  annotated as `<witness>*` (the original hand reading before
  correction) or `<witness>C` (the corrector hand reading). The
  adapter MUST emit each hand as a distinct Witness node linked
  by `CORRECTOR_OF` rather than merging the hands. The witness_ga
  uniqueness constraint applies only to the GA number, which is
  shared across the hands of a single manuscript; the
  implementer-impl caste MUST therefore null the `ga_number`
  property on all but one hand of a given manuscript (the base
  hand carries the GA number; corrector hands carry siglum-only
  identity) so the witness_ga constraint does not reject the
  second-hand write. The siglum suffix character (`*` or `C`)
  remains part of the siglum string itself so witness_siglum
  distinguishes the hands cleanly.

Case D: dangling endpoint.
  Rows whose witness siglum, variant_unit_id, or reading_id does
  not resolve to a known node MUST be quarantined. The adapter
  MUST NOT create sentinel nodes to bridge the gap. The Decision
  6 rule binds the adapter to a closed keyspace over 3 John
  verses one through fifteen; any unmatched identifier is a
  quarantine event surfaced in the snapshot ledger.

============================================================
9. License and redistribute (Decision 14)
============================================================

Per Decision 14, the adapter registers exactly one `Source` node
with the following property set, written once at ingest start
before any record-level write:

  | Field        | Type   | Predicate         |
  |--------------|--------|-------------------|
  | slug         | string | $pred_string(x)   |
  | license      | string | $pred_string(x)   |
  | redistribute | bool   | $pred_bool(x)     |

Values:

  slug         = 'open-cbgm-3-john'
  license      = 'MIT'
  redistribute = true

The MIT license is recorded for the citation slug
`open-cbgm-3-john-sample` in `docs/LICENSE_TAGGING.md` and the
matching citation slug is declared in
`docs/phase_prompts/pipeline2_verdict.md`. The Source uniqueness
constraint `source_slug` in `graph/lexical.cypher` enforces a
single Source node per slug; the implementer-impl caste MUST write
the Source node exactly once before any READS_AT, ATTESTED_BY, or
CORRECTOR_OF edge is emitted so the constraint check runs against
the registered slug only.

The Source node carries no edges to Witness, VariantUnit, or
Reading directly; provenance is recorded inline as the `source`
property on every edge this adapter emits (sections 4 and 5 above
codify that contract). If a downstream Pipeline 2 evidence file
cites a CBGM attestation, the citation slug is
`open-cbgm-3-john-sample` per the source slug table in
`docs/phase_prompts/pipeline2_verdict.md`.

============================================================
10. Dependence and dispatch order
============================================================

Per `docs/implementation_phases/phase_02_lexical_ingest.md` bullet
23, this adapter runs in Group 6 of the phase 02 dispatch order,
after `Verse` nodes for 3 John have been written by the Group 1
text floor (MorphGNT-SBLGNT for the NT verses). The dependency is
stated explicitly: "Verse nodes for 3 John must exist so the
variant-unit-to-verse join is well-defined." This adapter does
NOT itself create Verse nodes; the variant-unit-to-verse join
relies on the OSIS reference triple `(book, chapter, verse)` on
the VariantUnit node, which the verifier reconciles against the
existing `verse_book_ch_v` index in `graph/lexical.cypher`.

The wipe contract in `tools/wipe_lexical.py` deletes every node
and relationship in the lexical Neo4j before re-ingest so MERGE
writes start from an empty store. The text floor populates the
3 John Verse nodes before this adapter populates the CBGM Witness,
VariantUnit, and Reading nodes over the same OSIS reference range.

============================================================
11. Idempotency
============================================================

MERGE on the stable identifiers in section 5 is the idempotency
guarantee. Re-running the adapter on identical source bytes
produces zero new nodes and zero new edges; `ON MATCH SET`
re-writes property values to the same values, leaving the graph
byte-identical. The per-row presence vector for the triangle test
in Phase D hashes each upstream witness-to-reading attestation row
by SHA-256 over the canonical bytes of
`(siglum, variant_unit_id, reading_id, is_lacuna, text)` after the
normalisation in section 3; the sorted vector must match
byte-for-byte across two runs over identical inputs.

============================================================
12. Out-of-scope clarifications
============================================================

This adapter does NOT ingest the remainder of the ECM Catholic
Letters (1 John, 2 John, James, 1 Peter, 2 Peter, Jude); that
boundary is settled at the inventory catalog under
`explicit_deadends[0]` and is not re-litigated by this adapter.

This adapter does NOT ingest the Old Latin Vetus Latina apparatus;
that boundary is settled at the inventory catalog under
`explicit_deadends[2]`.

This adapter does NOT ingest the LXX Rahlfs standalone edition;
that exclusion is settled at the inventory catalog under
`explicit_deadends[1]`, and the STEPBible LXX columns (Decision
16) resolve the LXX-witness requirements that Pipeline 2 needs.

This adapter does NOT compute CBGM coherence scores, genealogical
relationships between witnesses, or the priority ordering on the
attestation graph. Those analyses belong to the consumer side of
the lexical store; the ingest layer persists the raw attestation
profile only.
"""

from __future__ import annotations

import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "open-cbgm-3-john"
LICENSE_ID = "MIT"
BOOK = "3John"
CHAPTER = 1
VERSE_MIN = 1
VERSE_MAX = 15
LANGUAGE = "greek"
BATCH_SIZE = 500
DB_FILENAME = "3_john.db"
XML_FILENAME = "3_john_collation.xml"
_TEI = "{http://www.tei-c.org/ns/1.0}"

_APP_RE = re.compile(r"^B\d+K(\d+)V(\d+)(U.+)$")

_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_WITNESS = (
    "UNWIND $rows AS row MERGE (n:`Witness` {siglum: row.siglum}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_VARIANT_UNIT = (
    "UNWIND $rows AS row MERGE (n:`VariantUnit` "
    "{variant_unit_id: row.variant_unit_id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_READING = (
    "UNWIND $rows AS row MERGE (n:`Reading` {reading_id: row.reading_id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_READS_AT = (
    "UNWIND $rows AS row "
    "MATCH (w:`Witness` {siglum: row.siglum}) "
    "MATCH (rd:`Reading` {reading_id: row.reading_id}) "
    "MERGE (w)-[r:`READS_AT` {variant_unit_id: row.variant_unit_id}]->(rd) "
    "SET r.source = row.source RETURN count(r) AS edges"
)
_MERGE_ATTESTED_BY = (
    "UNWIND $rows AS row "
    "MATCH (rd:`Reading` {reading_id: row.reading_id}) "
    "MATCH (v:`VariantUnit` {variant_unit_id: row.variant_unit_id}) "
    "MERGE (rd)-[r:`ATTESTED_BY`]->(v) "
    "SET r.source = row.source RETURN count(r) AS edges"
)
_MERGE_CORRECTOR_OF = (
    "UNWIND $rows AS row "
    "MATCH (c:`Witness` {siglum: row.corrector_siglum}) "
    "MATCH (b:`Witness` {siglum: row.base_siglum}) "
    "MERGE (c)-[r:`CORRECTOR_OF`]->(b) "
    "SET r.source = row.source RETURN count(r) AS edges"
)


def _century_for_siglum(base: str) -> int:
    if base.startswith("P"):
        return 3
    if base.startswith("L"):
        return 10
    if base == "Byz":
        return 9
    if base.isalpha():
        return 5
    if base.startswith("0") and len(base) > 1:
        return 5
    digits = "".join(ch for ch in base if ch.isdigit())
    if digits:
        value = int(digits)
        if value < 100:
            return 9
        if value < 1000:
            return 11
    return 12


def _split_hand(token: str) -> tuple[str, str | None]:
    """Return (base_siglum, hand_marker) for a wit token.

    The open-cbgm 3 John collation marks a non-original hand with a
    trailing supplement letter (for example `206S`). Per Decision 6
    edge case C that secondary hand is a corrector-class hand: the
    base manuscript keeps its Gregory-Aland identity, and the
    secondary hand is re-expressed with the canonical `C` suffix so
    `witness_siglum` distinguishes the hands without a merge collision.
    """
    if len(token) > 1 and token[-1] in ("S", "V", "C") and token[:-1]:
        body = token[:-1]
        if any(ch.isdigit() for ch in body) or body.isalpha():
            return body, "C"
    return token, None


def _read_db_witnesses(db_path: Path) -> set[str]:
    connection = sqlite3.connect(str(db_path))
    try:
        cursor = connection.execute("SELECT WITNESS FROM WITNESSES")
        return {str(row[0]).strip() for row in cursor.fetchall() if row[0]}
    finally:
        connection.close()


def _parse_units(xml_path: Path) -> list[dict[str, Any]]:
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    units: list[dict[str, Any]] = []
    for ab in root.iter(f"{_TEI}ab"):
        for app in ab.findall(f"{_TEI}app"):
            parsed = _parse_app(app)
            if parsed is not None:
                units = [*units, parsed]
    return units


def _parse_app(app: ET.Element) -> dict[str, Any] | None:
    raw_name = (app.attrib.get("n") or "").strip()
    match = _APP_RE.match(raw_name)
    if match is None:
        return None
    chapter = int(match.group(1))
    verse = int(match.group(2))
    if chapter != CHAPTER or not (VERSE_MIN <= verse <= VERSE_MAX):
        return None
    unit_segment = match.group(3)
    variant_unit_id = f"{BOOK}.{CHAPTER}.{verse}/{unit_segment}"
    readings: list[dict[str, Any]] = []
    for rdg in app.findall(f"{_TEI}rdg"):
        reading_name = (rdg.attrib.get("n") or "").strip()
        if not reading_name:
            continue
        text = (rdg.text or "").strip()
        wit_tokens = (rdg.attrib.get("wit") or "").split()
        readings = [
            *readings,
            {
                "reading_id": f"{variant_unit_id}-{reading_name}",
                "text": text,
                "is_lacuna": False,
                "witnesses": tuple(wit_tokens),
            },
        ]
    if not readings:
        return None
    return {
        "variant_unit_id": variant_unit_id,
        "verse": verse,
        "readings": readings,
    }


def _build_payloads(
    units: list[dict[str, Any]], db_witnesses: set[str]
) -> dict[str, list[dict[str, Any]]]:
    witness_props: dict[str, dict[str, Any]] = {}
    corrector_edges: dict[tuple[str, str], dict[str, Any]] = {}
    variant_units: list[dict[str, Any]] = []
    readings: list[dict[str, Any]] = []
    reads_at: list[dict[str, Any]] = []
    attested_by: list[dict[str, Any]] = []

    in_scope: set[str] = set()
    for unit in units:
        for reading in unit["readings"]:
            for token in reading["witnesses"]:
                base, marker = _split_hand(token)
                in_scope.add(base if marker is None else f"{base}{marker}")
                if marker is not None:
                    in_scope.add(base)
    for token in db_witnesses:
        base, marker = _split_hand(token)
        in_scope.add(base if marker is None else f"{base}{marker}")
        if marker is not None:
            in_scope.add(base)

    def _register(siglum: str, is_hand: bool, base: str) -> None:
        if siglum in witness_props:
            return
        witness_props[siglum] = {
            "siglum": siglum,
            "date_century": _century_for_siglum(base),
            "language": LANGUAGE.lower(),
            "ga_number": None if is_hand else siglum,
        }

    for siglum in sorted(in_scope):
        if siglum.endswith("C") or siglum.endswith("*"):
            _register(siglum, True, siglum[:-1])
        else:
            _register(siglum, False, siglum)

    for unit in units:
        variant_unit_id = unit["variant_unit_id"]
        verse = unit["verse"]
        variant_units = [
            *variant_units,
            {
                "variant_unit_id": variant_unit_id,
                "book": BOOK,
                "chapter": CHAPTER,
                "verse": verse,
            },
        ]
        attested_here: set[str] = set()
        for reading in unit["readings"]:
            readings = [
                *readings,
                {
                    "reading_id": reading["reading_id"],
                    "text": reading["text"],
                    "is_lacuna": False,
                    "variant_unit_id": variant_unit_id,
                },
            ]
            attested_by = [
                *attested_by,
                {
                    "reading_id": reading["reading_id"],
                    "variant_unit_id": variant_unit_id,
                    "source": SOURCE_SLUG,
                },
            ]
            for token in reading["witnesses"]:
                base, marker = _split_hand(token)
                siglum = base if marker is None else f"{base}{marker}"
                if siglum not in witness_props:
                    continue
                attested_here.add(siglum)
                reads_at = [
                    *reads_at,
                    {
                        "siglum": siglum,
                        "reading_id": reading["reading_id"],
                        "variant_unit_id": variant_unit_id,
                        "source": SOURCE_SLUG,
                    },
                ]
                if marker is not None and base in witness_props:
                    firsthand = f"{base}*"
                    _register(firsthand, True, base)
                    corrector_edges[(siglum, base)] = {
                        "corrector_siglum": siglum,
                        "base_siglum": base,
                        "source": SOURCE_SLUG,
                    }
                    corrector_edges[(firsthand, base)] = {
                        "corrector_siglum": firsthand,
                        "base_siglum": base,
                        "source": SOURCE_SLUG,
                    }

        missing = sorted(
            s for s in witness_props if s not in attested_here and "*" not in s
        )
        if missing:
            lacuna_id = f"{variant_unit_id}-lac"
            readings = [
                *readings,
                {
                    "reading_id": lacuna_id,
                    "text": "",
                    "is_lacuna": True,
                    "variant_unit_id": variant_unit_id,
                },
            ]
            attested_by = [
                *attested_by,
                {
                    "reading_id": lacuna_id,
                    "variant_unit_id": variant_unit_id,
                    "source": SOURCE_SLUG,
                },
            ]
            for siglum in missing:
                reads_at = [
                    *reads_at,
                    {
                        "siglum": siglum,
                        "reading_id": lacuna_id,
                        "variant_unit_id": variant_unit_id,
                        "source": SOURCE_SLUG,
                    },
                ]

    return {
        "witnesses": [witness_props[s] for s in sorted(witness_props)],
        "variant_units": variant_units,
        "readings": readings,
        "reads_at": reads_at,
        "attested_by": attested_by,
        "corrector_of": [
            corrector_edges[k] for k in sorted(corrector_edges)
        ],
    }


def _merge_source(session: Any) -> None:
    payload = [
        {"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": True}
    ]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_batched(session: Any, cypher: str, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        session.run(cypher, rows=batch).consume()
        total += len(batch)
    return total


def ingest_open_cbgm_3_john(
    data_root: Path, settings: Settings
) -> dict[str, int]:
    """Parse the open-cbgm 3 John collation and MERGE CBGM nodes and edges."""
    root = Path(data_root)
    db_path = root / DB_FILENAME
    xml_path = root / XML_FILENAME
    db_witnesses = _read_db_witnesses(db_path) if db_path.exists() else set()
    units = _parse_units(xml_path)
    payloads = _build_payloads(units, db_witnesses)

    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        witnesses = _merge_batched(
            session, _MERGE_WITNESS, payloads["witnesses"]
        )
        variant_units = _merge_batched(
            session, _MERGE_VARIANT_UNIT, payloads["variant_units"]
        )
        readings = _merge_batched(
            session, _MERGE_READING, payloads["readings"]
        )
        reads_at = _merge_batched(
            session, _MERGE_READS_AT, payloads["reads_at"]
        )
        attested_by = _merge_batched(
            session, _MERGE_ATTESTED_BY, payloads["attested_by"]
        )
        corrector_of = _merge_batched(
            session, _MERGE_CORRECTOR_OF, payloads["corrector_of"]
        )

    return {
        "Source": 1,
        "Witness": witnesses,
        "VariantUnit": variant_units,
        "Reading": readings,
        "READS_AT": reads_at,
        "ATTESTED_BY": attested_by,
        "CORRECTOR_OF": corrector_of,
    }
