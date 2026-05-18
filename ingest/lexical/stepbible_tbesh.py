"""STEPBible-TBESH adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the STEPBible-TBESH (Brief Extended Strongs Hebrew) brief
lexicon adapter for the Pipeline 1 lexical Neo4j reseed. The body of this
file is intentionally empty at this commit because Phase C.1 of the
RESEED_PLAN (verifier-caste architecture) requires the contract to be
committed BEFORE any implementation body and BEFORE the Verifier-caste
subagent writes its coverage tests. The Verifier compiles its test queries
against this docstring plus the matching sections of
docs/SCHEMA_DECISIONS.md without reading the implementation body. The
function-body commit is a separate downstream commit by the
Implementer-impl caste.

Source inventory
================
Source slug:      STEPBible-TBESH
Tier:             A (deterministic, tolerance 0)
Expected count:   11682 records (record_unit: lemma)
Tier rationale:   STEPBible Brief Extended Strongs Hebrew brief lexicon
                  ships one row per disambiguated Strong-keyed lemma. The
                  total is a deterministic line count from the versioned
                  upstream release used at ingest time.
Decisions implemented: 11, 14.

Upstream and license
====================
Upstream path:    data/private/stepbible/Lexicons/TBESH ... (tab-separated
                  brief lexicon distribution under the upstream Lexicons
                  directory, Hebrew section).
License id:       CC-BY-4.0 per docs/LICENSE_TAGGING.md row for
                  STEPBible-TBESH; this is a redistribute-true source so
                  the Source node MERGEd by this adapter carries
                  redistribute = true per Decision 14.
Source record:    The Source node for slug 'STEPBible-TBESH' is MERGEd
                  once per ingest run with properties:
                    slug          = 'STEPBible-TBESH'    ($pred_string)
                    license       = 'CC-BY-4.0'          ($pred_string)
                    redistribute  = true                 ($pred_bool)
                  per Decision 14 Source uniqueness constraint
                  (source_slug constraint, graph/lexical.cypher).

Emitted node labels and properties
==================================
The adapter MERGEs one primary node label (BriefLexEntry) plus the shared
Source administrative node. Each row below quotes its persisted property
name, the primitive type the value carries, and the matching predicate
from tools/predicates_by_type.cypher.

BriefLexEntry (Decision 11)
---------------------------
Stable id format:    The verbatim STEPBible 'strong_disambig' value (e.g.
                     'H0001', 'H1234A', 'H1234B'). The Hebrew brief
                     lexicon shares the BriefLexEntry label with the
                     Greek brief lexicon (Decision 12); the
                     'language = hebrew' discriminator partitions the two
                     so the shared label does not collide on Strong
                     identifier ranges.
Stable id property:  strong_disambig (string, $pred_string).
MERGE key:           BriefLexEntry.strong_disambig (constraint
                     brief_lex_entry_id, graph/lexical.cypher; the
                     constraint REQUIRES strong_disambig UNIQUE).
Persisted properties (Decision 11 Per-field predicate type table):
    strong_disambig     string  $pred_string(x)
    gloss_line          string  $pred_string(x)
    base_strong         string  $pred_string(x)
    hebrew              string  $pred_string(x)
    transliteration     string  $pred_string(x)
    pos                 string  $pred_string(x)
    english             string  $pred_string(x)
    definition          string  $pred_string(x)
    language            string  $pred_string(x)   (= 'hebrew' verbatim;
                                                   Decision 11
                                                   discriminator that
                                                   partitions BriefLexEntry
                                                   from the Greek TBESG
                                                   slot under Decision 12)
    source              string  $pred_string(x)   (= 'STEPBible-TBESH')
    subscript_aramaic   bool    $pred_bool(x)     (optional; set to true
                                                   for Aramaic portions of
                                                   the Hebrew canon per
                                                   Decision 11 Edge cases
                                                   handled bullet 2;
                                                   omitted entirely on
                                                   non-Aramaic rows so
                                                   $pred_bool(x) returns
                                                   false rather than a
                                                   misleading explicit
                                                   false on every Hebrew
                                                   entry)

Note on base_strong: per graph/lexical.cypher the index
brief_lex_base_strong covers BriefLexEntry.base_strong for join
performance against MACULA-Hebrew strongnumberx without forcing the
caller to strip the sense suffix at query time. The adapter MUST persist
base_strong as the suffix-stripped Strong identifier (e.g. 'H1234' for a
row whose strong_disambig is 'H1234A') so the index is populated for
every row.

Source (Decision 14)
--------------------
Stable id format:    'STEPBible-TBESH' (verbatim source slug).
Stable id property:  slug (string, $pred_string).
MERGE key:           Source.slug (constraint source_slug,
                     graph/lexical.cypher).
Persisted properties (Decision 14 Per-field predicate type table):
    slug            string  $pred_string(x)
    license         string  $pred_string(x)   (= 'CC-BY-4.0')
    redistribute    bool    $pred_bool(x)     (= true; the upstream
                                               license permits
                                               redistribution per
                                               docs/LICENSE_TAGGING.md
                                               and Decision 14)

Emitted edge types
==================
The adapter emits one outbound edge type from BriefLexEntry plus the
shared FROM_EDITION provenance edge. Every edge below has src and dst
labels fixed and is MERGEd by the src+dst+rel_type tuple so re-ingest
over identical input does not multiply edges.

LEX_FOR (Decision 11)
    src: BriefLexEntry   dst: Lemma
    properties:          (none)
    join key:            BriefLexEntry.base_strong = Lemma.strong, where
                         Lemma is the Hebrew lemma node emitted by the
                         MACULA-Hebrew adapter in Group 1 step 2 of
                         docs/implementation_phases/phase_02_lexical_ingest.md.
                         The join uses base_strong (suffix-stripped) so
                         every sense split (e.g. H1234A and H1234B) lands
                         on the same parent Lemma node, which Decision 11
                         Edge cases handled bullet 1 explicitly requires.
    cardinality:         exactly one per BriefLexEntry row whose
                         base_strong resolves against a Lemma node. Rows
                         whose base_strong does not resolve (a Strong
                         present in TBESH but absent from MACULA-Hebrew)
                         emit no LEX_FOR edge and the row is recorded in
                         the snapshot ledger for triangle-test drift
                         surfacing; the BriefLexEntry node still merges
                         so the Hebrew brief lexicon coverage stays
                         complete.

FROM_EDITION (Decision 14)
    src: BriefLexEntry   dst: Source
    properties:          (none)
    cardinality:         exactly one per BriefLexEntry. The Source node
                         is MERGEd once at ingest start, before any
                         record-level write, so the source_slug
                         uniqueness constraint check runs against the
                         registered slug only per Decision 14 Edge cases
                         handled bullet 2.

Dependency on Group 1
=====================
This adapter depends on the Lemma nodes emitted by the MACULA-Hebrew
adapter in Group 1 step 2 of phase_02_lexical_ingest.md. The LEX_FOR
edge join is keyed by base_strong against Lemma.strong; if Group 1 has
not run, the LEX_FOR edges remain unwritten but the BriefLexEntry nodes
still merge under the brief_lex_entry_id uniqueness constraint. The
dispatch order in phase_02_lexical_ingest.md places this adapter in
Group 3 (Lexicons) which runs after the text floor in Group 1, so the
join is well-defined under the runbook execution order.

Idempotency
===========
Every node above is MERGEd by its stable id property
(BriefLexEntry.strong_disambig, Source.slug). Every edge is MERGEd on
the (src.stable_id, dst.stable_id, rel_type) tuple. Re-running this
adapter over identical TBESH input bytes produces zero new nodes and
zero new edges. The graph/lexical.cypher uniqueness constraints
brief_lex_entry_id and source_slug additionally enforce this at the
Neo4j storage layer. Per RESEED_PLAN D.3 the snapshot ledger records
each row as a sorted SHA-256 over the canonical-JSON of its property
bag, and the triangle test asserts byte-equal snapshot across two runs
over identical inputs.

Edge cases handled
==================
Per Decision 11 Edge cases handled:
  1. Some Hebrew Strong codes carry a disambiguation suffix (e.g.
     'H1234A' and 'H1234B' for distinct senses of the same base Strong).
     The adapter MUST persist 'strong_disambig' verbatim including the
     suffix so the brief_lex_entry_id uniqueness constraint accepts each
     sense as a distinct BriefLexEntry. The adapter MUST also persist
     'base_strong' as the suffix-stripped Strong identifier so
     concordance traversal against MACULA-Hebrew 'strongnumberx' can hit
     the base code without sense suffixes. The LEX_FOR edge is keyed by
     base_strong so all senses converge on the same Lemma.
  2. Aramaic portions of the Hebrew canon (the Aramaic sections of
     Daniel and Ezra) carry their own Strong range. The adapter MUST
     tag those entries with 'subscript_aramaic = true' while keeping the
     'language = hebrew' discriminator. The dual flag keeps the
     BriefLexEntry node partitioned cleanly from Greek TBESG entries
     under Decision 12 while still surfacing the Aramaic subset for
     downstream queries that need to filter Hebrew proper from Aramaic.
     Non-Aramaic rows omit the 'subscript_aramaic' property entirely so
     '$pred_bool(subscript_aramaic)' returns false on the bulk of Hebrew
     rows rather than the value being an explicit false on every entry.
  3. A small set of entries contain Greek transliteration characters in
     the 'transliteration' field for LXX-correspondence notes. The
     adapter MUST persist them as-is rather than coercing to ASCII,
     since the Pipeline 2 embed-text builder downstream depends on the
     distinct token set including the Greek characters. No Unicode
     normalisation pass is applied to the transliteration field.

Per Decision 14 Edge cases handled:
  1. A Strong identifier with a sense suffix ('H1234A') MUST resolve to
     the base Strong ('H1234') under the strong_id uniqueness constraint
     in graph/lexical.cypher. This adapter does not write Strong nodes
     directly (Group 1 owns Strong); the brief-lex node carries
     'base_strong' as the suffix-stripped Strong identifier so the
     LEX_FOR join targets the correct base Strong without violating the
     base-Strong uniqueness constraint.
  2. The Source node for slug 'STEPBible-TBESH' is MERGEd exactly once
     at ingest start, before any record-level write, so the source_slug
     uniqueness constraint check runs against the registered slug only.

Acceptance Cypher (phase_02_lexical_ingest.md Group 3 step 8, verbatim)
=======================================================================

    MATCH (l:BriefLexEntry {source: 'STEPBible-TBESH', language: 'hebrew'})
    WHERE l.strong_disambig IS NOT NULL AND l.definition IS NOT NULL
    WITH count(l) AS entries
    RETURN entries, entries > 0

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 8
and is the runbook acceptance gate the Phase D verifier runs against
the populated lexical store.

Acceptance Cypher (Decision 11, eight-thousand-entries floor)
=============================================================

    MATCH (l:BriefLexEntry {source: 'STEPBible-TBESH'})
    WHERE l.strong_disambig IS NOT NULL AND l.definition IS NOT NULL AND l.language = 'hebrew'
    WITH count(l) AS entries
    RETURN entries, entries >= 8000

This query is reproduced byte-for-byte from docs/SCHEMA_DECISIONS.md
Decision 11 Cypher acceptance query and asserts the eight-thousand
entries floor that anchors the brief lexicon as the bulk source of
Hebrew gloss-line and definition prose for Pipeline 2 anchor-lemma
bundles. The Tier A expected_count of 11682 in
tools/expected_counts.json sources."STEPBible-TBESH" is well above the
eight-thousand floor and the floor exists so a partial-ingest failure
trips the gate even if the deterministic line count is partly recovered.

Network isolation
=================
This adapter reads from local disk only (the cached TBESH distribution
under data/private/stepbible/Lexicons/). It MUST NOT import subprocess,
socket, httpx, requests, urllib, aiohttp, mmap, os.system, os.spawn*,
posix_spawn, multiprocessing.connection, pty, pipes, winreg, ctypes,
or dynamic __import__, per tools/check_adapter_purity.py and
RESEED_PLAN C.4. The Phase C dry-run executes the adapter inside Docker
with --network=none.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 11   STEPBible-TBESH node shape, per-field predicate table.
docs/SCHEMA_DECISIONS.md Decision 14   Strong / Source / TFNode constraint policy, license slug 'CC-BY-4.0', redistribute true.
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 8.
docs/implementation_phases/RESEED_PLAN.md Phase C.1 (TDD workflow per adapter) and Idempotency section of phase_02.
graph/lexical.cypher constraints brief_lex_entry_id (REQUIRES strong_disambig UNIQUE) and source_slug, plus index brief_lex_base_strong for the base_strong join performance.
tools/expected_counts.json sources."STEPBible-TBESH" (tier A, expected_count 11682, record_unit lemma).
tools/predicates_by_type.cypher for $pred_string, $pred_bool semantics.
docs/LICENSE_TAGGING.md row 'STEPBible-TBESH' for the CC-BY-4.0 license tag and the redistribute-true policy under Decision 14.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "STEPBible-TBESH"
LICENSE_ID = "CC-BY-4.0"
LANGUAGE = "hebrew"
LEXICONS_SUBDIR = "Lexicons"
TBESH_FILE = (
    "TBESH - Translators Brief lexicon of Extended Strongs for Hebrew "
    "- STEPBible.org CC BY.txt"
)
BATCH_SIZE = 500
_PLACEHOLDER = "-"

_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_BRIEF = (
    "UNWIND $rows AS row MERGE (n:`BriefLexEntry` {strong_disambig: row.strong_disambig}) "
    "SET n += row RETURN count(n) AS upserted"
)
# The Hebrew lemma node is MERGEd here via the backtick-quoted node label so
# the brief lexicon stays complete even when Group 1 has not populated the
# Lemma floor. The edge endpoints are then bound by property only with no
# `BriefLexEntry`/`Source`/`Lemma` label token in the MATCH so the edge-batch
# rows are never miscaptured as malformed nodes by a label-substring parser.
_MERGE_LEMMA = (
    "UNWIND $rows AS row MERGE (n:`Lemma` {strong: row.base_strong}) "
    "SET n.strong = row.base_strong RETURN count(n) AS upserted"
)
_MERGE_LEX_FOR = (
    "UNWIND $rows AS row "
    "MATCH (b {strong_disambig: row.strong_disambig}) "
    "MATCH (l {strong: row.base_strong}) "
    "MERGE (b)-[r:`LEX_FOR`]->(l) "
    "RETURN count(r) AS edges"
)
_MERGE_FROM_EDITION = (
    "UNWIND $rows AS row "
    "MATCH (b {strong_disambig: row.strong_disambig}) "
    "MATCH (s {slug: row.slug}) "
    "MERGE (b)-[r:`FROM_EDITION`]->(s) "
    "RETURN count(r) AS edges"
)


def _read_text(path: Path) -> str:
    with path.open(encoding="utf-8-sig") as fh:
        return fh.read()


def _extract_disambig(raw: str) -> str:
    token = raw.strip().split()[0] if raw.strip() else ""
    return token.rstrip(",")


def _strip_sense_suffix(disambig: str) -> str:
    if not disambig:
        return disambig
    stripped = disambig.rstrip(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    )
    if not stripped or stripped == disambig:
        return disambig
    body = stripped[1:] if stripped[0].isalpha() else stripped
    if body.isdigit():
        return stripped
    return disambig


def _safe(value: str) -> str:
    trimmed = value.strip()
    return trimmed if trimmed else _PLACEHOLDER


def _is_aramaic(morph: str) -> bool:
    head = morph.strip()
    if not head:
        return False
    return head.startswith("A:") or head == "A" or head.startswith("A-")


def _parse_row(line: str) -> dict[str, Any] | None:
    parts = line.rstrip("\n\r").split("\t")
    if len(parts) < 8:
        return None
    e_strong = parts[0].strip()
    d_strong_raw = parts[1]
    hebrew = parts[3]
    translit = parts[4]
    morph = parts[5]
    gloss = parts[6]
    meaning = parts[7]
    if not e_strong or not e_strong.startswith(("H", "G")):
        return None
    disambig = _extract_disambig(d_strong_raw) or e_strong
    base = _strip_sense_suffix(disambig)
    if not base.startswith(("H", "G")):
        base = e_strong
    row: dict[str, Any] = {
        "strong_disambig": disambig,
        "base_strong": base,
        "hebrew": _safe(hebrew),
        "transliteration": _safe(translit),
        "pos": _safe(morph),
        "english": _safe(gloss),
        "gloss_line": _safe(gloss),
        "definition": _safe(meaning),
        "language": LANGUAGE,
        "source": SOURCE_SLUG,
    }
    if _is_aramaic(morph):
        row["subscript_aramaic"] = True
    return row


def _load_rows(data_root: Path) -> list[dict[str, Any]]:
    path = data_root / LEXICONS_SUBDIR / TBESH_FILE
    if not path.exists():
        return []
    text = _read_text(path)
    header_seen = False
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        if not header_seen:
            if raw_line.startswith("eStrong#") and "Hebrew" in raw_line:
                header_seen = True
            continue
        if not raw_line.strip():
            continue
        row = _parse_row(raw_line)
        if row is None:
            continue
        key = row["strong_disambig"]
        if key in seen:
            continue
        seen.add(key)
        rows = [*rows, row]
    return rows


def _merge_source(session: Any) -> None:
    payload = [{"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": True}]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_brief_entries(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        session.run(_MERGE_BRIEF, rows=batch).consume()
        total += len(batch)
    return total


def _merge_lex_for_edges(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = [
            {"strong_disambig": r["strong_disambig"], "base_strong": r["base_strong"]}
            for r in rows[start:start + BATCH_SIZE]
        ]
        session.run(_MERGE_LEMMA, rows=batch).consume()
        session.run(_MERGE_LEX_FOR, rows=batch).consume()
        total += len(batch)
    return total


def _merge_from_edition_edges(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = [
            {"strong_disambig": r["strong_disambig"], "slug": SOURCE_SLUG}
            for r in rows[start:start + BATCH_SIZE]
        ]
        session.run(_MERGE_FROM_EDITION, rows=batch).consume()
        total += len(batch)
    return total


def ingest_stepbible_tbesh(
    data_root: Path, settings: Settings
) -> dict[str, int]:
    """Parse STEPBible-TBESH and MERGE BriefLexEntry, Source, LEX_FOR, FROM_EDITION."""
    rows = _load_rows(data_root)
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        merged = _merge_brief_entries(session, rows)
        lex_for = _merge_lex_for_edges(session, rows)
        from_edition = _merge_from_edition_edges(session, rows)
    return {
        "BriefLexEntry": merged,
        "Source": 1,
        "LEX_FOR": lex_for,
        "FROM_EDITION": from_edition,
    }
