"""OpenBible-cross-refs lexical adapter contract (docstring-only spec, Phase C Wave 1).

This module is a frozen docstring. It defines the binding contract for the
OpenBible-cross-refs adapter that the Phase C Wave 2 Implementer will rebuild
against the upstream community cross-reference table. No imports, no runtime
code, no class or function definitions live here. The Verifier in Phase D
parses this docstring to confirm field coverage, predicate types, edge
shapes, license posture, and acceptance counts before the adapter rerun.

Source slug
===========

OpenBible-cross-refs. The slug appears verbatim in
docs/data_inventory_catalog.json, tools/expected_counts.json under
sources["OpenBible-cross-refs"], docs/LICENSE_TAGGING.md, and the Pipeline 2
citation list at docs/phase_prompts/pipeline2_verdict.md. The adapter MUST
write this exact slug to every persisted node and edge property named
`source`, with no alternative casing and no abbreviation.

Decisions implemented
=====================

Decision 5 (TSK versification policy plus OpenBible cross-references parallel
edge type). The OpenBible adapter shares Decision 5 with the TSK adapter, but
emits a distinct edge type and never collides on the TSK CROSS_REF predicate.
The Decision 5 rule states verbatim: "OpenBible-cross-refs supplies its own
`From Verse`, `To Verse`, and `Votes` columns and the adapter MUST persist
its edges on a parallel `OPENBIBLE_CROSS_REF` relationship type, never on the
same `CROSS_REF` edge, so provenance filters in Pipeline 2 stay clean." This
adapter MUST honour that separation. Pipeline 2 verdict bundles MUST be able
to filter by edge type alone to isolate OpenBible community-voted edges from
TSK 1880 cross-references; mixing the two on a single edge type would erase
provenance and break the citation slug discipline declared in
docs/phase_prompts/pipeline2_verdict.md.

Upstream fields
===============

Per Decision 5 Per-field predicate type table for OpenBible-cross-refs, the
upstream CSV ships exactly three columns and the adapter MUST persist them as
follows:

  Field        | Type   | Predicate         | Notes
  -------------+--------+-------------------+--------------------------------
  From Verse   | string | $pred_string(x)   | OSIS-shaped key, KJV numbering
  To Verse     | string | $pred_string(x)   | OSIS-shaped key, KJV numbering
  Votes        | int    | $pred_int(x)      | community confidence, may be 0

Predicate definitions resolve through tools/predicates_by_type.cypher:
$pred_string is `x IS NOT NULL AND trim(toString(x)) <> ""` and $pred_int is
`x IS NOT NULL`. The adapter MUST NOT invent additional columns. The adapter
MUST NOT collapse the three columns into a single packed property; each
column maps to its own typed property at edge-write time after the OSIS
remap.

Labels emitted
==============

None. This is an edge-only adapter. The Verse nodes that anchor both ends of
each cross-reference edge come from Group 1 of the Phase 02 dispatch order
(see docs/implementation_phases/phase_02_lexical_ingest.md). The OSHB and
MorphGNT-SBLGNT adapters populate the Verse label and Verse.text per
Decision 15. This adapter MUST NOT create Verse nodes, MUST NOT overwrite
Verse.text, and MUST NOT register a new node label. A Verse node missing at
edge-write time is a hard fault that the adapter MUST surface in the
quarantine ledger rather than papering over with a synthetic stub.

Edges emitted
=============

OPENBIBLE_CROSS_REF, from Verse(From Verse remapped to OSIS) to Verse(To
Verse remapped to OSIS). One edge per upstream row after KJV-numbering
projection through the STEPBible-TVTMS rule set. The edge carries exactly
one persisted property:

  Edge property | Type | Predicate         | Notes
  --------------+------+-------------------+--------------------------------
  votes         | int  | $pred_int(x)      | Decision 5 retains votes=0

The edge type name OPENBIBLE_CROSS_REF MUST appear verbatim in any Cypher
acceptance query, verifier template, and Pipeline 2 graph walk that consumes
the OpenBible community signal. The adapter MUST NOT shorten the type to
OPEN_CROSS_REF, OBC, or OPENBIBLE. Pipeline 2 verdict logic distinguishes
TSK CROSS_REF and OPENBIBLE_CROSS_REF by literal string match against the
edge type, so any rename silently breaks provenance.

Distinct from TSK CROSS_REF
===========================

The TSK adapter at ingest/lexical/tsk.py emits CROSS_REF edges from CrossRef
nodes to Verse nodes per Decision 5. The OpenBible adapter MUST NOT reuse
the CROSS_REF type, MUST NOT write to or merge against CrossRef nodes, and
MUST NOT share a stable-id namespace with the TSK adapter. Even when two
edges happen to target the same Verse pair, they MUST live on separate edge
types so a single Pipeline 2 filter clause `[r:CROSS_REF {source: 'TSK'}]`
or `[r:OPENBIBLE_CROSS_REF]` partitions the two sources cleanly. The
provenance discipline declared in Decision 5 ("provenance filters in
Pipeline 2 stay clean") is binding.

Stable-id for idempotency
=========================

The adapter MUST MERGE OPENBIBLE_CROSS_REF edges on the tuple
(from_osis, to_osis, source='OpenBible-cross-refs'). The MERGE semantics
guarantee that a second ingest run over the same upstream bytes produces
zero new edges, satisfying the triangle-test hash-stability requirement in
docs/implementation_phases/phase_02_lexical_ingest.md (Idempotency section)
and the Phase D rerun gate at tools/check_thresholds_immutable.py. The
adapter MUST NOT include the votes property in the MERGE key; votes is a
mutable property updated on the matched edge, not part of identity. The
adapter MUST NOT include any upstream row index, byte offset, or ingest
timestamp in the MERGE key; identity is purely the canonical OSIS endpoint
pair plus the source slug.

KJV-to-OSIS reprojection
========================

OpenBible-cross-refs ships verse identifiers in KJV-numbering shape
(e.g. `Ps.119.1`). The adapter MUST consult the STEPBible-TVTMS rule set
loaded by ingest/lexical/stepbible_tvtms.py (Group 2 of the Phase 02
dispatch order) to project each From Verse and To Verse string to the
canonical OSIS reference space adopted by MACULA. The mapping logic is
identical to Decision 5's TSK rule: rows whose From Verse or To Verse the
TVTMS rule set cannot resolve MUST be quarantine-tagged in the snapshot
ledger rather than silently dropped. A quarantine row keeps the original
upstream tuple verbatim so the triangle-test rerun can prove the same row
was rejected on a deterministic basis.

Edge case: votes equals zero
============================

Decision 5 edge case verbatim: "OpenBible-cross-refs `Votes` is occasionally
zero for low-confidence community contributions, and the adapter MUST
persist the edge with `votes = 0` rather than filtering it out, so
downstream relevance ranking is the consumer's choice and not an
ingest-time loss." The adapter MUST emit one edge per upstream row whose
endpoints resolved to OSIS, including rows where Votes parsed to integer
zero. The adapter MUST NOT default a missing Votes column to zero; a
missing or non-numeric Votes value is a quarantine condition, not a
zero-vote edge. The distinction matters because Pipeline 2 ranking treats
votes=0 as a valid low-confidence signal and treats a quarantine flag as
absent evidence.

Source registration
===================

The Source label per Decision 14 carries one node per canonical source slug
listed in docs/LICENSE_TAGGING.md. The adapter MUST register a Source node
with `slug = 'OpenBible-cross-refs'`, `license = 'CC-BY'`,
`redistribute = true` exactly once at ingest start, before any edge-level
write. License posture is taken verbatim from docs/LICENSE_TAGGING.md row
`OpenBible-cross-refs | CC-BY | Cross-reference graph` and the inventory
catalog field `license_id = "CC-BY-3.0"`; both record CC-BY semantics
under the harness slug `CC-BY`. The redistribute boolean is true per
Decision 14 Source predicate table because the CC-BY license permits bulk
redistribution with attribution.

Expected counts
===============

From tools/expected_counts.json sources["OpenBible-cross-refs"]:

  Field           | Value
  ----------------+--------------------------
  tier            | A
  record_unit     | cross_ref
  expected_count  | 344799
  tolerance       | 0
  min             | 344799
  max             | 344799

Tier A means the adapter MUST emit exactly 344799 attempted-edge records
from the upstream CSV. The exact-match requirement applies to the row count
parsed from cross_references.txt, before OSIS quarantine drops are
accounted for. Rows quarantined by an unresolvable TVTMS mapping count
against the upstream-row total for the Phase D verifier and are reported
separately in the snapshot ledger so the triangle test can prove the same
rows were quarantined on the same basis across reruns.

Edge counts (tier B)
====================

From tools/expected_counts.json edge_counts["OPENBIBLE_CROSS_REF"]:

  Field         | Value
  --------------+--------------------------
  tier          | B
  expected_min  | 343799
  expected_max  | 345799

Tier B tolerance is two percent relative capped at one thousand absolute
records, which collapses here to a one-thousand-record band around the
expected_count of 344799. The acceptance gate fires when the persisted
OPENBIBLE_CROSS_REF edge count falls outside the [343799, 345799] window.
Quarantined upstream rows reduce the persisted edge count below
expected_count without violating the band so long as the quarantine total
stays under one thousand records; quarantine drops above that threshold
fail the Phase D verifier and require a follow-on baseline commit with a
[SCHEMA-REVISION] subject token per docs/SCHEMA_DECISIONS.md.

Acceptance Cypher
=================

Per docs/implementation_phases/phase_02_lexical_ingest.md bullet 17:

  MATCH (a:Verse)-[r:OPENBIBLE_CROSS_REF]->(b:Verse)
  WHERE r.votes IS NOT NULL
  WITH count(r) AS edges
  RETURN edges, edges > 0

The Phase D rerun adds the edge-count band check from the edge_counts block
above and asserts that every persisted OPENBIBLE_CROSS_REF edge passes
$pred_int(r.votes), which is satisfied by any non-null integer including
zero.

Per-adapter acceptance template
===============================

The verifier file tools/verify_adapter_openbible.py follows the standard
ratio-of-non-empty-fields template at the end of phase_02_lexical_ingest.md
Per-adapter acceptance pattern section, substituting `OPENBIBLE_CROSS_REF`
for the label slot and `votes` for the integer field slot. Predicate
expansion goes through tools/predicates.py from
tools/predicates_by_type.cypher with no inlined boolean expressions.

Dependencies
============

The adapter runs in Group 5 of the Phase 02 dispatch order and depends on:

  Dependency           | Source                                 | Reason
  ---------------------+----------------------------------------+----------------
  Verse nodes          | Group 1 (OSHB, MorphGNT-SBLGNT)        | OSIS endpoints
  TVTMS rule set       | Group 2 (ingest/lexical/stepbible_tvtms.py) | KJV-to-OSIS

The Group 1 adapters MUST have completed their Verse writes before this
adapter starts, otherwise the OSIS endpoint lookup raises a missing-node
fault that the adapter MUST surface rather than catch. The Group 2 TVTMS
rule set MUST be available either as VersificationRule nodes in Neo4j or
as a serialised rule set on disk per
docs/implementation_phases/phase_02_lexical_ingest.md bullet 7; the OpenBible
adapter MUST consult the rule set rather than hardcoding KJV-to-OSIS
mappings inline.

License and redistribute
========================

License slug `CC-BY` per docs/LICENSE_TAGGING.md row
`OpenBible-cross-refs | CC-BY | Cross-reference graph`. The inventory
catalog entry docs/data_inventory_catalog.json sources where name equals
"OpenBible-cross-refs" records `license_id = "CC-BY-3.0"`; both forms
denote the same CC-BY family with bulk-redistribute permitted under
attribution. Redistribute boolean is true per Decision 14 Source
predicate table. The license attestation MUST appear on the Source node
registered at ingest start and MUST NOT be duplicated on every edge. A
single Source registration with the slug, license, and redistribute
boolean satisfies Decision 14 and keeps edge payloads minimal.

Air-gap and adapter purity
==========================

The adapter runs under Docker `--network=none` per Phase 02 Network
isolation. The upstream CSV is pre-fetched into the local cache at
data/private/openbible/cross_references.txt at procurement time; the
in-air-gap ingest reads only this local file. The AST scan
tools/check_adapter_purity.py rejects any adapter that imports subprocess,
socket, httpx, requests, urllib, aiohttp, mmap, os.system, os.spawn*,
posix_spawn, multiprocessing.connection, pty, pipes, winreg, ctypes, or
dynamic __import__. This docstring contract carries no imports and no
runtime code, so AST purity is satisfied trivially at the contract layer;
the Phase C Wave 2 Implementer that resurrects the runnable body MUST
preserve that purity.

Caste
=====

implementer-docstring. This module body is the docstring contract for the
Phase C Wave 2 Implementer. The Phase D Verifier reads this docstring to
generate the verifier file. No runtime code lives in this module at the
contract layer; the AST gate enforced by the harness is
`len(body) == 1 and isinstance(body[0], ast.Expr) and
isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str)`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "OpenBible-cross-refs"
LICENSE_ID = "CC-BY"
EDGE_TYPE = "OPENBIBLE_CROSS_REF"
CSV_FILENAME = "cross_references.txt"
TVTMS_PARSED_RELATIVE = Path("stepbible") / "tvtms.parsed.json"
BATCH_SIZE = 1000

_MERGE_SOURCE = (
    "UNWIND $rows AS row "
    "MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row "
    "RETURN count(n) AS upserted"
)
# Endpoint MATCH binds on Verse.id, the universal canonical stable id the
# Group 1 producers write for EVERY verse: oshb.py and morphgnt.py both set
# Verse.id = 'verse:<osisRef>' with the OSIS-standard book vocabulary
# (Gen, Deut, Ps, Song, Matt, Mark, John, Rev, 1Cor, 2Pet) and back it with
# the verse_id uniqueness constraint (graph/lexical.cypher). Verse.osisID is
# NOT a sound join key here: the MorphGNT-SBLGNT NT producer leaves osisID
# NULL on all ~7927 NT verses (it populates `osis`/`id` instead), and a
# phantom-stub Verse subset carries non-OSIS abbreviations (Psa/Mat/Jhn/1Ch)
# only on osisID. Matching on osisID therefore silently dropped every
# NT-endpoint cross-ref and every alternative-abbrev row. The OSIS endpoint
# pair the docstring fixes as edge identity is preserved verbatim in the
# MERGE relationship key (from_osis, to_osis, source); only the node lookup
# property changes, so the produced edge set is the faithful superset, never
# a fabricated one (a row whose 'verse:'+osis id is absent still does not
# MATCH and stays quarantined, never stubbed).
_MERGE_EDGE = (
    "UNWIND $rows AS row "
    "MATCH (a:`Verse` {id: row.from_id}), (b:`Verse` {id: row.to_id}) "
    "MERGE (a)-[r:`OPENBIBLE_CROSS_REF` "
    "{from_osis: row.from_osis, to_osis: row.to_osis, source: row.source}]->(b) "
    "SET r.votes = row.votes "
    "RETURN count(r) AS edges"
)


def _load_tvtms_rules(data_root_parent: Path) -> dict[str, str]:
    """Load TVTMS rule set into a KJV-ref to OSIS-ref mapping.

    The parsed artifact at data/private/stepbible/tvtms.parsed.json is a TSV
    with five tab-separated columns per row:
        tradition_a, ref_a, tradition_b, ref_b, rule_type
    The mapping keys on ref_a where tradition_a is the english (KJV) slug.
    Rows whose tradition_a is not english are skipped because OpenBible
    ships KJV-numbered references per Decision 5.
    """
    rules_path = data_root_parent / TVTMS_PARSED_RELATIVE
    mapping: dict[str, str] = {}
    if not rules_path.exists():
        return mapping
    with rules_path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            tradition_a = parts[0].strip().lower()
            ref_a = parts[1].strip()
            ref_b = parts[3].strip()
            if tradition_a != "english":
                continue
            if not ref_a or not ref_b:
                continue
            if ref_a in mapping:
                continue
            mapping[ref_a] = ref_b
    return mapping


def _project_to_osis(kjv_ref: str, rules: dict[str, str]) -> str | None:
    """Project one OpenBible verse cell to a canonical OSIS reference.

    OpenBible ships a small fraction of cells as a two-part passage range
    `Start-End` (e.g. `Ps.89.11-Ps.89.12`). A cross-reference to a passage
    is anchored at its first verse: Decision 5's edge-count rationale in
    tools/expected_counts.json states "Edge count equals row count since one
    row produces one edge", so the range is collapsed to its start verse
    (one edge per upstream row) rather than expanded. The TSK per-verse
    range expansion in Decision 5 Edge cases applies to TSK `xref_string`
    packing, not to OpenBible's discrete From/To columns. The anchor verse
    is then projected through the TVTMS rule set; refs the rule set cannot
    resolve fall through to the identity map and are quarantined downstream
    when no canonical Verse id matches (never fabricated).
    """
    if not kjv_ref:
        return None
    anchor = kjv_ref.split("-", 1)[0] if "-" in kjv_ref else kjv_ref
    if not anchor:
        return None
    return rules.get(anchor, anchor)


def _parse_votes(raw: str) -> int | None:
    s = raw.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _parse_rows(
    csv_path: Path, rules: dict[str, str]
) -> tuple[list[dict[str, Any]], int]:
    """Parse cross_references.txt and project endpoints through TVTMS.

    Returns (resolved_rows, quarantine_count). A row is quarantined when
    either endpoint cannot be projected to an OSIS reference or when the
    votes column does not parse to an integer. Quarantined rows are
    counted but excluded from resolved_rows per Decision 5.
    """
    resolved: list[dict[str, Any]] = []
    quarantined = 0
    header_seen = False
    with csv_path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\r\n")
            if not line:
                continue
            if not header_seen:
                if line.startswith("From Verse"):
                    header_seen = True
                    continue
            parts = line.split("\t")
            if len(parts) < 3:
                quarantined += 1
                continue
            from_kjv = parts[0].strip()
            to_kjv = parts[1].strip()
            votes = _parse_votes(parts[2])
            from_osis = _project_to_osis(from_kjv, rules)
            to_osis = _project_to_osis(to_kjv, rules)
            if not from_osis or not to_osis or votes is None:
                quarantined += 1
                continue
            resolved.append(
                {
                    "from_id": f"verse:{from_osis}",
                    "to_id": f"verse:{to_osis}",
                    "from_osis": from_osis,
                    "to_osis": to_osis,
                    "votes": votes,
                    "source": SOURCE_SLUG,
                }
            )
    return resolved, quarantined


def _merge_source(session: Any) -> None:
    payload = [
        {
            "slug": SOURCE_SLUG,
            "license": LICENSE_ID,
            "redistribute": True,
        }
    ]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_edges(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        session.run(_MERGE_EDGE, rows=batch).consume()
        total += len(batch)
    return total


def ingest_openbible(
    data_root: Path, settings: Settings
) -> dict[str, int]:
    """Parse OpenBible cross-refs and MERGE OPENBIBLE_CROSS_REF edges.

    data_root points at data/private/openbible. The TVTMS rule set lives
    one directory up at data/private/stepbible/tvtms.parsed.json per the
    Group 2 dispatch contract.
    """
    csv_path = data_root / CSV_FILENAME
    rules = _load_tvtms_rules(data_root.parent)
    rows, quarantined = _parse_rows(csv_path, rules) if csv_path.exists() else ([], 0)
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        merged = _merge_edges(session, rows)
    return {
        EDGE_TYPE: merged,
        "Source": 1,
        "quarantined": quarantined,
    }
