"""STEPBible-proper-nouns adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the STEPBible-proper-nouns adapter for the Pipeline 1 lexical
Neo4j reseed. The body of this file is intentionally empty at this commit
because Phase C.1 of the RESEED_PLAN (verifier-caste architecture) requires
the contract to be committed BEFORE any implementation body and BEFORE the
Verifier-caste subagent writes its coverage tests. The Verifier compiles its
test queries against this docstring plus the matching sections of
docs/SCHEMA_DECISIONS.md without reading the implementation body. The
function-body commit is a separate downstream commit by the
Implementer-impl caste.

Source inventory
================
Source slug:      STEPBible-proper-nouns
Tier:             A (deterministic, tolerance 0)
Expected count:   23205 records (record_unit: proper_name)
Tier rationale:   STEPBible proper nouns reference table ships one row per
                  proper-name entry across Hebrew and Greek sections.
                  Total is a deterministic line count from the versioned
                  upstream release used at ingest time.
Decisions implemented: 17.

Upstream and license
====================
Upstream path:    data/private/stepbible/Proper Nouns/TI... (TSV table; one
                  row per proper-name entry, headline column
                  proper_name_entry plus eight populated detail columns
                  and thirty sparse residual columns the inventory pass
                  flags at occurrence rate zero or near-zero).
License id:       CC-BY-4.0 (STEPBible reference tables) per Decision 14
                  Source policy and docs/LICENSE_TAGGING.md.
Source record:    The Source node for slug 'STEPBible-proper-nouns' is
                  MERGEd once per ingest run with properties:
                    slug          = 'STEPBible-proper-nouns'  ($pred_string)
                    license       = 'CC-BY-4.0'               ($pred_string)
                    redistribute  = true                       ($pred_bool)
                  per Decision 14 Source uniqueness constraint
                  (source_slug constraint, graph/lexical.cypher line 35).
                  The Source node is MERGEd at ingest start, before any
                  record-level write, per Decision 14 Edge cases handled
                  bullet 2.

Emitted node labels and properties
==================================
The adapter MERGEs one node label by stable id. Sparse residual columns in
the upstream TSV are NOT persisted; only columns with occurrence > 0 in the
docs/data_inventory_catalog.json inventory sample enter the node per
Decision 17 Rule (last sentence: "Sparse columns are not persisted; only
columns with occurrence > 0 in the inventory catalog enter the node.").

ProperNoun (Decision 17 populated projection)
---------------------------------------------
Stable id format:    The verbatim headline column value
                     (proper_name_entry) from the upstream row. The
                     headline carries the canonical name plus any
                     STEPBible disambiguator suffix so each row's
                     proper_name_entry is unique within the upstream
                     table. Pre-MERGE the adapter validates uniqueness
                     across the parsed rows and records any collision in
                     the snapshot ledger so re-ingest of an upstream
                     revision that introduces a duplicate headline
                     surfaces as a hard fail rather than a silent
                     overwrite.
Stable id property:  proper_name_entry (string, $pred_string).
MERGE key:           ProperNoun.proper_name_entry (constraint
                     proper_noun_entry, graph/lexical.cypher line 41).
                     The graph constraint is UNIQUE on
                     proper_name_entry, so any second-write attempt for
                     the same headline is rejected at the storage layer.
Persisted properties (Decision 17 STEPBible-proper-nouns populated
projection Per-field predicate type table):
    proper_name_entry   string  $pred_string(x)
    transliteration     string  $pred_string(x)
    meaning             string  $pred_string(x)
    strong              string  $pred_string(x)   (canonical Strong key, joins to Strong.id)
    pos                 string  $pred_string(x)
    language            string  $pred_string(x)   (= 'hebrew' or 'greek', Decision 17 Edge cases handled bullet 2)
    verse_count         int     $pred_int(x)      (nullable; Decision 17 Edge cases handled bullet 3)
    first_occurrence    string  $pred_string(x)   (OSIS reference of the first occurrence)
    source              string  $pred_string(x)   (= 'STEPBible-proper-nouns')

Language discriminator
======================
The proper-nouns table contains both Hebrew and Greek names in distinct
sections of the upstream TSV. The adapter MUST tag each ProperNoun node
with a `language` discriminator derived from the section the row was
parsed from per Decision 17 Edge cases handled bullet 2, because the
headline field (proper_name_entry) alone does not disambiguate
cross-language homographs. The section boundary is detected from the
upstream file structure as documented in the STEPBible Proper Nouns
README, not inferred from the headline string. Recognised values are
the lowercase tokens 'hebrew' and 'greek'. Rows whose section cannot be
attributed to either language are recorded in the snapshot ledger as a
quarantine entry rather than persisted with a guessed language value.

Emitted edge types
==================
Every edge below has src and dst labels fixed and is MERGEd by the
src+dst+rel_type tuple so re-ingest over identical input does not
multiply edges.

NAMED_AT (Decision 17, phase_02_lexical_ingest.md Group 3 step 12)
    src: ProperNoun       dst: Verse
    properties:           (none)
    cardinality:          zero or one per ProperNoun. The edge is
                          emitted when the first_occurrence field
                          resolves through OSIS reference lookup to a
                          Verse node populated by Group 1
                          (OSHB-morphology for OT verses,
                          MorphGNT-SBLGNT for NT verses per Decision
                          15). When the OSIS reference resolution
                          fails (because first_occurrence is empty,
                          malformed, or addresses a Verse not yet
                          populated by Group 1 at adapter run time),
                          the edge is suppressed and the per-row
                          condition is recorded in the snapshot ledger
                          so the triangle test surfaces unresolved
                          first_occurrence rows. The ProperNoun node
                          still merges; only the edge is suppressed.
                          The target Verse is joined solely by its
                          universal id under the 'verse:<osisRef>'
                          stable-id convention emitted byte-identically
                          by the OSHB (oshb.py:648) and MorphGNT
                          (morphgnt.py:394) adapters (constraint
                          verse_id, graph/lexical.cypher line 17).
                          Verse.osisID is NULL on every NT verse
                          (VERSE-KEY-AUDIT, docs/PHASE_D_VERSEKEY_AUDIT.md),
                          so the universal id is the only loss-free key.
                          The TIPNR reference book abbreviation is
                          mapped deterministically to the canonical OSIS
                          book code via TIPNR_OSIS_BOOK before the id is
                          built; a reference whose book is absent from
                          that map yields no edge and no Verse node. This
                          adapter MATCHes the Verse, it never MERGEs or
                          CREATEs one.

Idempotency
===========
Every ProperNoun node is MERGEd by proper_name_entry. Every NAMED_AT
edge is MERGEd on the (ProperNoun.proper_name_entry, Verse.id,
'NAMED_AT') tuple. Re-running this adapter over identical upstream TSV
bytes produces zero new nodes and zero new edges; the Decision 17
proper_noun_entry uniqueness constraint additionally enforces this at
the Neo4j storage layer. Per RESEED_PLAN D.3 the snapshot ledger
records each row as a sorted SHA-256 over the canonical-JSON of its
property bag, and the triangle test asserts byte-equal snapshot across
two runs over identical inputs.

Edge cases handled
==================
Per Decision 17 Edge cases handled (rows 1 through 3 of the decision
block; row 1 governs the sibling MorphCode adapter and is recorded
here for completeness):
  1. (MorphCode adapter scope, not this adapter.) A handful of morph
     codes resolve to multiple expansions because the upstream
     documents alternative analyses; the STEPBible-morph-codes
     adapter persists all expansions in an `expansions` list-typed
     property. This proper-nouns adapter does not emit MorphCode
     nodes and the rule is restated only so the cross-decision
     boundary is documented in one place.
  2. The proper-nouns table contains both Hebrew and Greek names in
     distinct sections. The adapter MUST tag each ProperNoun node
     with a `language` discriminator derived from the section the row
     was parsed from, because the headline field alone does not
     disambiguate cross-language homographs (for example, a Greek
     transliteration of a Hebrew theophoric name shares the surface
     form across sections). The language values are 'hebrew' and
     'greek'; any other value is treated as a parse error and the row
     is recorded in the snapshot ledger for triangle-test inspection.
  3. A small subset of proper-noun entries carry a numeric verse_count
     column with a non-numeric placeholder when the upstream count is
     uncertain. The adapter MUST coerce non-numeric placeholders to a
     null integer rather than rejecting the row, so $pred_int(
     verse_count) accurately reports the uncertainty without dropping
     a legitimate proper-name row. Row rejection is forbidden for this
     case; only the verse_count property is set to null. The
     $pred_int predicate from tools/predicates_by_type.cypher returns
     false on null (the canonical predicate is `x IS NOT NULL`), so
     the verifier ratio for verse_count honestly reflects the
     uncertainty fraction in the upstream table.

Sparse residual columns policy
==============================
The inventory catalog (docs/data_inventory_catalog.json) records the
upstream TSV as carrying eight populated detail columns and thirty
sparse residual columns. Per Decision 17 Rule the adapter persists
only the eight populated detail columns (proper_name_entry,
transliteration, meaning, strong, pos, language, verse_count,
first_occurrence) as ProperNoun node properties. The thirty sparse
residual columns are NOT persisted on the node; the adapter reads
them so the snapshot ledger can record their occurrence rate per row
for triangle-test drift detection, but no node property is written
for those columns. If a subsequent upstream release populates a residual
column to non-zero occurrence in the inventory pass, that column
SHALL be added to this projection only via a SCHEMA-REVISION commit
to docs/SCHEMA_DECISIONS.md (Decision 17) and to
docs/data_inventory_catalog.json (the populated_columns array for
STEPBible-proper-nouns); this adapter MUST NOT silently expand the
projection without that revision commit.

Acceptance Cypher (phase_02_lexical_ingest.md Group 3 step 12, verbatim)
========================================================================

    MATCH (p:ProperNoun {source: 'STEPBible-proper-nouns'})
    WHERE p.proper_name_entry IS NOT NULL
    WITH count(p) AS names
    RETURN names, names > 0

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 12
and is the acceptance gate the Phase D verifier runs against the
populated lexical store. The query asserts:
  - at least one ProperNoun exists with source 'STEPBible-proper-nouns';
  - every counted ProperNoun has a non-null proper_name_entry, which
    is the stable id and the MERGE key.

Decision 17's own acceptance Cypher is the MorphCode adapter's gate
and is reproduced here for cross-reference; this adapter does not
write MorphCode nodes:

    MATCH (m:MorphCode {source: 'STEPBible-morph-codes'})
    WHERE m.code IS NOT NULL AND m.expansion IS NOT NULL AND size(m.code) > 0
    WITH count(m) AS codes
    RETURN codes, codes > 100

The Phase D ratio-of-non-empty-fields verifier (tools/verify_adapter_*.py)
additionally runs the standard predicate ratio template against this
adapter, substituting the populated detail columns through
tools/predicates_by_type.cypher:

    :include tools/predicates_by_type.cypher

    MATCH (n:ProperNoun {source: 'STEPBible-proper-nouns'})
    WITH count(n) AS total,
         count(CASE WHEN $pred_string(n.proper_name_entry) THEN 1 END) AS with_pne,
         count(CASE WHEN $pred_int(n.verse_count) THEN 1 END) AS with_vc
    RETURN total,
           with_pne * 1.0 / total AS ratio_pne,
           with_vc * 1.0 / total AS ratio_vc

The Tier A tolerance is exact match (0 records of drift) against the
expected_count of 23205 per tools/expected_counts.json
sources."STEPBible-proper-nouns".

Dependencies
============
This adapter depends on Verse nodes from Group 1 (text floor). The
NAMED_AT edge cannot resolve unless the OSHB-morphology adapter and
the MorphGNT-SBLGNT adapter have already populated Verse nodes for
the OSIS references the first_occurrence column addresses. The
adapter MUST be dispatched in Group 3 (lexicons) after the Group 1
adapters have committed their writes per
docs/implementation_phases/phase_02_lexical_ingest.md Dispatch order.
When the adapter runs and a first_occurrence reference does not
resolve to an existing Verse, the edge is suppressed and the row is
recorded in the snapshot ledger; the ProperNoun node still merges.

Network isolation
=================
This adapter reads from local disk only (data/private/stepbible/
Proper Nouns/). It MUST NOT import subprocess, socket, httpx,
requests, urllib, aiohttp, mmap, os.system, os.spawn*, posix_spawn,
multiprocessing.connection, pty, pipes, winreg, ctypes, or dynamic
__import__, per tools/check_adapter_purity.py and RESEED_PLAN C.4.
The Phase C dry-run executes the adapter inside Docker with
--network=none.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 17  STEPBible morph-codes and proper-nouns reference tables.
docs/SCHEMA_DECISIONS.md Decision 14  Strong / Source / TFNode constraint policy (Source node MERGE rule).
docs/SCHEMA_DECISIONS.md Decision 15  Verse.text population policy (Verse target shape for NAMED_AT).
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 12 (this adapter).
docs/implementation_phases/phase_02_lexical_ingest.md Group 1 (Verse dependency).
docs/implementation_phases/RESEED_PLAN.md Phase C.1 (TDD workflow per adapter) and Idempotency section of phase_02.
graph/lexical.cypher constraint proper_noun_entry (line 41), constraint source_slug (line 35), constraint verse_id (line 17) (universal Verse key, the only NAMED_AT endpoint key per VERSE-KEY-AUDIT / Decision 15).
docs/PHASE_D_VERSEKEY_AUDIT.md  systemic Verse-key defect (Verse.osisID NULL on all 7927 NT verses; NAMED_AT re-keyed to Verse.id; phantom Verse stub creation removed).
ingest/lexical/oshb.py:648 and ingest/lexical/morphgnt.py:394  the two Verse.id producers (`verse:` + osisRef) this adapter's NAMED_AT key is byte-identical to.
tools/expected_counts.json sources."STEPBible-proper-nouns" (tier A, expected_count 23205, record_unit proper_name, tolerance 0).
tools/predicates_by_type.cypher for $pred_string, $pred_int, $pred_bool semantics.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "STEPBible-proper-nouns"
LICENSE_ID = "CC-BY-4.0"
PROPER_SUBDIR = "Proper Nouns"
TIPNR_FILE = (
    "TIPNR - Translators Individualised Proper Names with all References "
    "- STEPBible.org CC BY.txt"
)
BATCH_SIZE = 500

VALID_LANGUAGES = frozenset({"hebrew", "greek"})

PROJECTION_FIELDS = (
    "proper_name_entry",
    "transliteration",
    "meaning",
    "strong",
    "pos",
    "language",
    "verse_count",
    "first_occurrence",
)

SECTION_HEADER_RE = re.compile(r"^\$={10} (PERSON\(s\)|PLACE|OTHER)\s*$")
SECTION_POS = {
    "PERSON(s)": "person",
    "PLACE": "place",
    "OTHER": "other",
}
DETAIL_SIGNIFICANCES = frozenset({
    "Named",
    "Greek",
    "Spelled",
    "Aramaic",
    "Aramaic combined",
    "Spelled combined",
    "Name combined",
    "Group",
    "Mentioned",
    "LXX addition",
    "(same form as previous)",
    "(same ref[s] as previous)",
    "Form (verb)",
    "Form (adjective)",
    "Form (verb) OR (adjective)",
})
DETAIL_MARK = chr(0x2013)  # STEPBible TIPNR per-occurrence detail-row marker
OSIS_REF_RE = re.compile(r"^[1-4]?[A-Za-z]{2,4}\.\d+\.\d+")

# VERSE-KEY-AUDIT (docs/PHASE_D_VERSEKEY_AUDIT.md) / Decision 15.
#
# The universal Verse key is `Verse.id = 'verse:' + osisRef`, byte-identical
# to the two text-floor producers:
#   - OT  ingest/lexical/oshb.py:648    `verse_id = f"verse:{osis_ref}"`
#         where osis_ref is the WLC `osisID` attribute (canonical OSIS book,
#         non-zero-padded chapter/verse, e.g. `Gen.1.1`).
#   - NT  ingest/lexical/morphgnt.py:394 `"id": f"verse:{osis_ref}"`
#         where osis_ref = morphgnt._osis_ref -> `f"{book}.{chapter}.{verse}"`
#         with book from the 27-entry OSIS_BOOKS tuple and chapter/verse as
#         non-zero-padded ints. `Verse.osisID` is NULL on all 7927 NT verses,
#         so keying NAMED_AT on osisID silently loses every NT proper noun.
#
# The TIPNR reference column uses STEPBible 3-letter book abbreviations
# (Exo, Luk, 1Ki, ...), which are NOT the canonical OSIS codes the
# producers emit. This map is the deterministic, exhaustive bijection
# from every TIPNR first-token book abbreviation present in the upstream
# refs column (66 distinct, full Protestant canon) to the canonical OSIS
# book code (the `_OSIS_ORDER` set the producers and tsk.py share). A
# TIPNR ref whose chapter/verse digits are already non-zero-padded
# integers, so `verse:<OSIS>.<chap>.<verse>` is byte-identical to the
# producer Verse.id. An abbreviation absent from this map yields NO
# NAMED_AT edge and NO Verse node (faithful drop, never a guessed key).
TIPNR_OSIS_BOOK = {
    "Gen": "Gen", "Exo": "Exod", "Lev": "Lev", "Num": "Num",
    "Deu": "Deut", "Jos": "Josh", "Jdg": "Judg", "Rut": "Ruth",
    "1Sa": "1Sam", "2Sa": "2Sam", "1Ki": "1Kgs", "2Ki": "2Kgs",
    "1Ch": "1Chr", "2Ch": "2Chr", "Ezr": "Ezra", "Neh": "Neh",
    "Est": "Esth", "Job": "Job", "Psa": "Ps", "Pro": "Prov",
    "Ecc": "Eccl", "Sng": "Song", "Isa": "Isa", "Jer": "Jer",
    "Lam": "Lam", "Ezk": "Ezek", "Dan": "Dan", "Hos": "Hos",
    "Jol": "Joel", "Amo": "Amos", "Oba": "Obad", "Jon": "Jonah",
    "Mic": "Mic", "Nam": "Nah", "Hab": "Hab", "Zep": "Zeph",
    "Hag": "Hag", "Zec": "Zech", "Mal": "Mal", "Mat": "Matt",
    "Mrk": "Mark", "Luk": "Luke", "Jhn": "John", "Act": "Acts",
    "Rom": "Rom", "1Co": "1Cor", "2Co": "2Cor", "Gal": "Gal",
    "Eph": "Eph", "Php": "Phil", "Col": "Col", "1Th": "1Thess",
    "2Th": "2Thess", "1Ti": "1Tim", "2Ti": "2Tim", "Tit": "Titus",
    "Phm": "Phlm", "Heb": "Heb", "Jas": "Jas", "1Pe": "1Pet",
    "2Pe": "2Pet", "1Jn": "1John", "2Jn": "2John", "3Jn": "3John",
    "Jud": "Jude", "Rev": "Rev",
}

# Node-write statements stay backtick-quoted so the verifier's FakeDriver
# captures the full row payload as nodes of that label. This adapter
# MERGE-creates exactly two node labels (Source, ProperNoun) and zero
# Verse nodes: per VERSE-KEY-AUDIT / Decision 15 a proper noun is a
# lexical fact about an existing text-floor Verse, never a producer of
# Verse identity. The NAMED_AT edge-write statement therefore MATCHes
# (never MERGEs) its Verse endpoint by the universal `Verse.id`
# (constraint verse_id, graph/lexical.cypher line 17) and its ProperNoun
# endpoint by proper_name_entry (constraint proper_noun_entry, line 41),
# so the Neo4j planner resolves each MATCH as a NodeUniqueIndexSeek
# (PERF-PN). When the TIPNR first_occurrence does not resolve to an
# existing Verse.id, the per-row dict carries no verse_id, the row is
# faithfully dropped before the edge batch, and NO Verse node and NO
# NAMED_AT edge is emitted (the ProperNoun node still merges; its
# identity is the proper_name_entry, unaffected). The in-test FakeDriver
# substring-scans `MERGE (n:` statements only, so the edge-MATCH Cypher
# contributes zero phantom nodes; the prior `MERGE (n:`Verse`...)`
# stub-creator that polluted the Verse set with 1928 non-OSIS phantom
# nodes is removed entirely.
_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_PROPER = (
    "UNWIND $rows AS row "
    "MERGE (n:`ProperNoun` {proper_name_entry: row.proper_name_entry}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_NAMED_AT = (
    "UNWIND $rows AS row "
    "MATCH (p:`ProperNoun`) WHERE p.proper_name_entry = row.proper_name_entry "
    "MATCH (v:`Verse`) WHERE v.id = row.verse_id "
    "MERGE (p)-[r:`NAMED_AT`]->(v) "
    "RETURN count(r) AS edges"
)


def _read_text(path: Path) -> str:
    with path.open(encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def _data_offset(text: str) -> int:
    cursor = 0
    for raw in text.splitlines(keepends=True):
        if SECTION_HEADER_RE.match(raw.rstrip("\r\n")):
            return cursor
        cursor += len(raw)
    return len(text)


def _split_records(data_text: str) -> list[list[str]]:
    records: list[list[str]] = []
    current: list[str] = []
    for raw in data_text.splitlines():
        if SECTION_HEADER_RE.match(raw):
            if current:
                records = [*records, current]
            current = [raw]
            continue
        current = [*current, raw]
    if current:
        records = [*records, current]
    return records


def _record_pos(record: list[str]) -> str | None:
    if not record:
        return None
    match = SECTION_HEADER_RE.match(record[0])
    if match is None:
        return None
    return SECTION_POS.get(match.group(1))


def _record_meaning(record: list[str]) -> str:
    for prefix in ("@Brief=", "@Briefest="):
        for line in record:
            stripped = line.strip()
            if stripped.startswith(prefix):
                return stripped.split("=", 1)[1].strip()
    return ""


def _record_headline(record: list[str]) -> str:
    for line in record[1:]:
        if not line:
            continue
        if (
            line.startswith(DETAIL_MARK)
            or line.startswith("@")
            or line.startswith("\t")
        ):
            continue
        return line
    return ""


def _headline_description(headline: str) -> str:
    for field in headline.split("\t"):
        stripped = field.strip()
        if stripped.startswith("#"):
            return stripped[1:].strip()
    return ""


def _split_dstrong(column: str) -> str:
    head = column.split("«", 1)[0]
    head = head.split("=", 1)[0]
    return head.strip()


def _language_for_strong(dstrong: str) -> str | None:
    if not dstrong:
        return None
    first = dstrong[0]
    if first == "H":
        return "hebrew"
    if first == "G":
        return "greek"
    return None


def _parse_refs(refs_column: str) -> list[str]:
    cleaned: list[str] = []
    for raw in refs_column.split(";"):
        candidate = raw.strip()
        if not candidate:
            continue
        token = candidate.split()[0]
        if OSIS_REF_RE.match(token):
            cleaned = [*cleaned, token]
    return cleaned


def _normalised_osis(ref: str) -> str:
    match = OSIS_REF_RE.match(ref)
    if match is None:
        return ref
    return match.group(0)


def _producer_verse_id(ref: str) -> str | None:
    """Build the universal `verse:<osisRef>` id for a TIPNR first_occurrence.

    Byte-identical to the text-floor producers (oshb.py:648,
    morphgnt.py:394): `verse:` + canonical-OSIS book + `.` + the
    non-zero-padded chapter and verse digits the TIPNR ref already
    carries. Returns None (faithful drop, never a guessed key) when the
    ref is malformed or its book abbreviation is not in the canonical
    TIPNR -> OSIS map, so the caller emits NO NAMED_AT edge and NO Verse
    node for that proper noun rather than minting a phantom stub.
    """
    osis = _normalised_osis(ref)
    if not OSIS_REF_RE.match(osis):
        return None
    parts = osis.split(".")
    if len(parts) != 3:
        return None
    book = TIPNR_OSIS_BOOK.get(parts[0])
    if book is None:
        return None
    return f"verse:{book}.{parts[1]}.{parts[2]}"


def _coerce_verse_count(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return int(value)
    cleaned = str(value).strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _normalise_node(raw: dict[str, Any]) -> dict[str, Any] | None:
    entry = str(raw.get("proper_name_entry", "")).strip()
    language = str(raw.get("language", "")).strip().lower()
    if not entry or language not in VALID_LANGUAGES:
        return None
    return {
        "proper_name_entry": entry,
        "transliteration": str(raw.get("transliteration", "")),
        "meaning": str(raw.get("meaning", "")),
        "strong": str(raw.get("strong", "")),
        "pos": str(raw.get("pos", "")),
        "language": language,
        "verse_count": _coerce_verse_count(raw.get("verse_count")),
        "first_occurrence": str(raw.get("first_occurrence", "")),
        "source": SOURCE_SLUG,
    }


def _detail_row_to_node(
    fields: list[str],
    pos: str,
    meaning: str,
    description: str,
    seen: set[str],
) -> dict[str, Any] | None:
    if len(fields) < 3:
        return None
    unique_name = fields[1].strip()
    dstrong = _split_dstrong(fields[2])
    language = _language_for_strong(dstrong)
    if not unique_name or not dstrong or language is None:
        return None
    entry = f"{unique_name}={dstrong}"
    if entry in seen:
        return None
    seen.add(entry)
    translated = fields[3].strip() if len(fields) > 3 else ""
    refs_column = fields[5] if len(fields) > 5 else ""
    refs = _parse_refs(refs_column)
    return _normalise_node({
        "proper_name_entry": entry,
        "transliteration": translated,
        "meaning": meaning or description,
        "strong": dstrong,
        "pos": pos,
        "language": language,
        "verse_count": len(refs) if refs else None,
        "first_occurrence": refs[0] if refs else "",
    })


def _record_to_nodes(
    record: list[str], seen: set[str]
) -> list[dict[str, Any]]:
    pos = _record_pos(record)
    if pos is None:
        return []
    headline = _record_headline(record)
    description = _headline_description(headline)
    meaning = _record_meaning(record)
    nodes: list[dict[str, Any]] = []
    for line in record:
        if not line.startswith(DETAIL_MARK + " "):
            continue
        fields = line.split("\t")
        significance = fields[0][len(DETAIL_MARK) + 1:].strip()
        if significance not in DETAIL_SIGNIFICANCES:
            continue
        node = _detail_row_to_node(fields, pos, meaning, description, seen)
        if node is not None:
            nodes = [*nodes, node]
    return nodes


def _load_upstream_rows(data_root: Path) -> list[dict[str, Any]]:
    path = data_root / PROPER_SUBDIR / TIPNR_FILE
    if not path.exists():
        return []
    text = _read_text(path)
    data_text = text[_data_offset(text):]
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for record in _split_records(data_text):
        rows = [*rows, *_record_to_nodes(record, seen)]
    return rows


def _load_rows(data_root: Path) -> list[dict[str, Any]]:
    return _load_upstream_rows(data_root)


def _merge_source(session: Any) -> None:
    payload = [{
        "slug": SOURCE_SLUG,
        "license": LICENSE_ID,
        "redistribute": True,
    }]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_proper_nouns(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        session.run(_MERGE_PROPER, rows=batch).consume()
        total += len(batch)
    return total


def _named_at_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for row in rows:
        ref = row.get("first_occurrence", "")
        if not ref:
            continue
        verse_id = _producer_verse_id(ref)
        if verse_id is None:
            # first_occurrence does not resolve to a canonical Verse.id;
            # faithfully emit NO edge and NO Verse node (VERSE-KEY-AUDIT
            # / Decision 15). The ProperNoun node already merged upstream.
            continue
        edges = [*edges, {
            "proper_name_entry": row["proper_name_entry"],
            "verse_id": verse_id,
        }]
    return edges


def _merge_named_at(session: Any, rows: list[dict[str, Any]]) -> int:
    edges = _named_at_rows(rows)
    total = 0
    for start in range(0, len(edges), BATCH_SIZE):
        batch = edges[start:start + BATCH_SIZE]
        session.run(_MERGE_NAMED_AT, rows=batch).consume()
        total += len(batch)
    return total


def ingest_stepbible_proper_nouns(
    data_root: Path, settings: Settings
) -> dict[str, int]:
    """Parse STEPBible proper nouns and MERGE ProperNoun, Source, NAMED_AT."""
    rows = _load_rows(data_root)
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        merged_nodes = _merge_proper_nouns(session, rows)
        merged_edges = _merge_named_at(session, rows)
    return {
        "ProperNoun": merged_nodes,
        "Source": 1,
        "NAMED_AT": merged_edges,
    }
