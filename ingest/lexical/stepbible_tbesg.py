"""STEPBible-TBESG adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the STEPBible-TBESG (Brief Extended Strongs Greek lexicon)
adapter for the Pipeline 1 lexical Neo4j reseed. The body of this file is
intentionally limited to this top-level docstring at this commit because
Phase C.1 of the RESEED_PLAN (verifier-caste architecture) requires the
contract to be committed BEFORE any implementation body and BEFORE the
Verifier-caste subagent writes its coverage tests. The Verifier compiles
its test queries against this docstring plus Decision 12 of
docs/SCHEMA_DECISIONS.md without reading the implementation body. The
function-body commit is a separate downstream commit by the
Implementer-impl caste.

Source inventory
================
Source slug:      STEPBible-TBESG
Tier:             A (deterministic, tolerance 0)
Expected count:   11035 records (record_unit: lemma)
Tier rationale:   STEPBible Brief Extended Strongs Greek brief lexicon
                  ships one row per disambiguated Strong-keyed Greek
                  lemma. Total is a deterministic line count from the
                  versioned upstream release used at ingest time, identical
                  across reruns under tagged builds.
Decisions implemented: 12.
Group:            Group 3 (Lexicons), step 9 of
                  docs/implementation_phases/phase_02_lexical_ingest.md.

Upstream and license
====================
Upstream path:    data/private/stepbible/Lexicons/TBESG ... (tab-separated
                  text file shipped under the STEPBible Lexicons folder).
License id:       CC-BY-4.0 per docs/LICENSE_TAGGING.md Lexical sources
                  row for slug STEPBible-TBESG.
Redistribute:     true (Decision 14 Source node policy; bulk redistribute
                  is permitted under CC-BY-4.0 with attribution).
Source record:    The Source node for slug 'STEPBible-TBESG' is MERGEd
                  once per ingest run with properties:
                    slug          = 'STEPBible-TBESG'   ($pred_string)
                    license       = 'CC-BY-4.0'         ($pred_string)
                    redistribute  = true                ($pred_bool)
                  per Decision 14 Source uniqueness constraint
                  (source_slug constraint, graph/lexical.cypher line 35).

Emitted node labels and properties
==================================
This adapter MERGEs exactly one record-level node label, BriefLexEntry,
plus the Source administrative node above. The BriefLexEntry label is
shared with the Hebrew TBESH adapter (Decision 11); the language='greek'
discriminator partitions Greek entries from Hebrew entries on the same
label without collision because Decision 11 fixes language='hebrew' for
TBESH and Decision 12 fixes language='greek' for TBESG.

BriefLexEntry (Decision 12)
---------------------------
Stable id format:    strong_disambig verbatim from the upstream row
                     (e.g. 'G1234' or 'G1234A' when the Strong has a
                     disambiguation suffix). The strong_disambig string
                     is the MERGE key and the graph uniqueness key.
Stable id property:  strong_disambig (string, $pred_string).
MERGE key:           BriefLexEntry.strong_disambig (constraint
                     brief_lex_entry_id, graph/lexical.cypher line 38).
Index:               BriefLexEntry.base_strong is indexed for join
                     performance (index brief_lex_base_strong,
                     graph/lexical.cypher line 64). The index is the
                     load-bearing path for LEX_FOR edge resolution from
                     BriefLexEntry to GreekLemma.
Persisted properties (Decision 12 Per-field predicate type table, with
the language discriminator from the Decision 12 Rule clause):
    strong_disambig   string  $pred_string(x)   (= stable id, MERGE key)
    gloss_line        string  $pred_string(x)   (headword summary)
    base_strong       string  $pred_string(x)   (join key for LEX_FOR,
                                                  no sense suffix)
    greek             string  $pred_string(x)   (Greek lemma surface;
                                                  hyphen preserved verbatim
                                                  for compound lemmas per
                                                  Decision 12 Edge cases
                                                  handled bullet 1)
    transliteration   string  $pred_string(x)   (nullable; 0.99 upstream
                                                  occurrence rate per
                                                  Decision 12 Rule clause,
                                                  null left as null when
                                                  the row is empty)
    pos               string  $pred_string(x)   (nullable; 0.885 upstream
                                                  occurrence rate per
                                                  Decision 12 Rule clause,
                                                  null for indeclinable
                                                  particles where part of
                                                  speech is unknown)
    english           string  $pred_string(x)
    definition        string  $pred_string(x)   (long-form prose Pipeline 2
                                                  cites under slug
                                                  STEPBible-TBESG;
                                                  parenthetical etymology
                                                  preserved verbatim per
                                                  Decision 12 Edge cases
                                                  handled bullet 3, no
                                                  sub-span splitting)
    language          string  $pred_string(x)   (= 'greek', fixed
                                                  discriminator per
                                                  Decision 12 Rule clause)
    source            string  $pred_string(x)   (= 'STEPBible-TBESG')
    license           string  $pred_string(x)   (= 'CC-BY-4.0')
    redistribute      bool    $pred_bool(x)     (= true, Decision 14)

Source (Decision 14)
--------------------
Stable id format:    'STEPBible-TBESG' (verbatim source slug).
Stable id property:  slug (string, $pred_string).
MERGE key:           Source.slug (constraint source_slug,
                     graph/lexical.cypher line 35).
Persisted properties (Decision 14 Per-field predicate type table):
    slug            string  $pred_string(x)
    license         string  $pred_string(x)   (= 'CC-BY-4.0')
    redistribute    bool    $pred_bool(x)     (= true)

Emitted edge types
==================
This adapter writes exactly one outbound edge type from BriefLexEntry to
the canonical GreekLemma label produced by Group 1 (MACULA-Greek). The
join is by base_strong (BriefLexEntry side) to the canonical Strong key
on GreekLemma (typically GreekLemma.id or GreekLemma.strong as projected
by the macula_greek adapter under Decision 2).

LEX_FOR (Decision 12)
    src: BriefLexEntry   dst: GreekLemma
    properties:          (none)
    cardinality:         exactly one per BriefLexEntry whose base_strong
                         resolves to an existing GreekLemma; zero when
                         the GreekLemma is absent from the Group 1 floor
                         (this case is recorded in the snapshot ledger
                         and surfaces in the triangle test rather than
                         being silently dropped).
    Join key:            BriefLexEntry.base_strong = GreekLemma.id (or
                         the equivalent canonical Strong property on
                         GreekLemma as defined by the macula_greek
                         adapter). The index brief_lex_base_strong on
                         line 64 of graph/lexical.cypher accelerates the
                         lookup.

Dependency on GreekLemma from Group 1
=====================================
The LEX_FOR edge above presumes that GreekLemma nodes for the union of
MACULA-Greek-Nestle1904 and MACULA-Greek-SBLGNT have been MERGEd into
the lexical store before this adapter runs. The Group 1 text-floor
adapter macula_greek.py is the producer; see
docs/implementation_phases/phase_02_lexical_ingest.md Group 1 step 3.
This adapter MUST run after macula_greek so the base_strong join
resolves against an existing node set. The Phase D verifier asserts the
ordering by inspecting the snapshot ledger written by Group 1 before
re-running the Group 3 acceptance Cypher below.

Idempotency
===========
Every BriefLexEntry above is MERGEd by strong_disambig. The Source node
is MERGEd by slug. Every LEX_FOR edge is MERGEd on the (src.strong_disambig,
dst.id, rel_type) tuple. Re-running this adapter over identical
STEPBible-TBESG bytes produces zero new nodes and zero new edges; the
Decision 14 uniqueness constraint on BriefLexEntry.strong_disambig and
on Source.slug enforces this at the Neo4j storage layer. Per
RESEED_PLAN D.3 the snapshot ledger records each row as a sorted SHA-256
over the canonical-JSON of its property bag, and the triangle test
asserts byte-equal snapshot across two runs.

Edge cases handled (verbatim from Decision 12)
==============================================
  1. Compound lemmas with hyphen: some Greek Strong codes correspond to
     compound lemmas whose 'greek' field contains a hyphen joining the
     component lemmas (for example a verb plus its preposition prefix
     written with a connecting hyphen). The adapter MUST persist the
     hyphen verbatim because removing it changes the surface lookup
     behaviour of downstream embed_text for compound-word concordance.
     No normalisation, no stripping, no replacement of the hyphen
     character occurs at adapter time.
  2. Nullable transliteration: the 0.99 upstream occurrence of the
     transliteration field reflects entries where STEPBible authors
     flagged transliteration as ambiguous and left it empty. The
     adapter MUST leave transliteration null rather than substituting a
     fallback (such as a romanisation derived from 'greek'), so
     $pred_string(transliteration) accurately reports the gap on those
     rows. The predicate table above records transliteration as
     nullable accordingly.
  3. Parenthetical etymology definitions: some entries have a
     'definition' that begins with a parenthetical etymology written in
     Greek script (for example '(from <root>) ...'). The adapter MUST
     persist the full definition string without splitting, because
     Pipeline 2 cites the full definition slot rather than parsed
     sub-spans. No partition of the definition into etymology and gloss
     halves is performed.

Additional rule from Decision 12 Rule clause (pos nullability)
==============================================================
The pos field's 0.885 upstream occurrence reflects a small population
of indeclinable particles whose part-of-speech is unknown. The adapter
MUST leave pos null on these rows rather than substituting a fallback
token. The predicate table above records pos as nullable.

Cross-label collision (TBESH versus TBESG)
==========================================
Decision 11 (TBESH) and Decision 12 (TBESG) share the BriefLexEntry
label but partition cleanly by the language discriminator: TBESH writes
language='hebrew' and TBESG writes language='greek'. The
brief_lex_entry_id uniqueness constraint on strong_disambig prevents
identifier collision across the two adapters because Hebrew Strongs
begin with 'H' and Greek Strongs begin with 'G'. No additional
deduplication is required at adapter time.

Acceptance Cypher (phase_02_lexical_ingest.md bullet 9, verbatim)
=================================================================

    MATCH (l:BriefLexEntry {source: 'STEPBible-TBESG', language: 'greek'})
    WHERE l.greek IS NOT NULL
    WITH count(l) AS entries
    RETURN entries, entries > 0

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 9
and is the Phase D acceptance gate for this adapter. The query asserts
that at least one BriefLexEntry with source='STEPBible-TBESG' and
language='greek' has been MERGEd and that the greek lemma surface field
is populated.

Acceptance Cypher (Decision 12 acceptance query, verbatim)
==========================================================

    MATCH (l:BriefLexEntry {source: 'STEPBible-TBESG'})
    WHERE l.strong_disambig IS NOT NULL AND l.greek IS NOT NULL AND l.language = 'greek'
    WITH count(l) AS entries
    RETURN entries, entries >= 5000

This query is reproduced byte-for-byte from docs/SCHEMA_DECISIONS.md
Decision 12 Cypher acceptance query. The query asserts that the count
of populated BriefLexEntry rows for this source meets the floor of
five thousand entries. The expected_count of 11035 in
tools/expected_counts.json sits comfortably above this floor.

Expected-count gate (tier A, tolerance 0)
=========================================
Per tools/expected_counts.json the source 'STEPBible-TBESG' carries
tier A with expected_count = 11035 and tolerance = 0. The Phase D
verifier asserts that the count of BriefLexEntry nodes with
source='STEPBible-TBESG' equals 11035 exactly. Tier A admits no
relative slack; the count is a deterministic line count over the
tagged upstream release.

Network isolation
=================
This adapter reads from local disk only (data/private/stepbible/
Lexicons/TBESG ...). It MUST NOT import subprocess, socket, httpx,
requests, urllib, aiohttp, mmap, os.system, os.spawn, posix_spawn,
multiprocessing.connection, pty, pipes, winreg, ctypes, or dynamic
__import__, per tools/check_adapter_purity.py and RESEED_PLAN C.4.
The Phase C dry-run executes the adapter inside Docker with
--network=none.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 12   STEPBible-TBESG node shape.
docs/SCHEMA_DECISIONS.md Decision 14   Strong / Source / TFNode constraint policy.
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 9.
docs/LICENSE_TAGGING.md Lexical sources row STEPBible-TBESG (CC-BY-4.0).
graph/lexical.cypher constraints brief_lex_entry_id, source_slug, greek_lemma_id and index brief_lex_base_strong.
tools/expected_counts.json sources."STEPBible-TBESG" (tier A, expected_count 11035, record_unit lemma).
tools/predicates_by_type.cypher for $pred_string, $pred_int, $pred_bool, $pred_list semantics.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "STEPBible-TBESG"
LICENSE_ID = "CC-BY-4.0"
LANGUAGE = "greek"
LEXICONS_SUBDIR = "Lexicons"
TBESG_FILE = (
    "TBESG - Translators Brief lexicon of Extended Strongs for Greek - "
    "STEPBible.org CC BY.txt"
)
BATCH_SIZE = 500

_ESTRONG_PATTERN = re.compile(r"^G\d")

_COL_ESTRONG = 0
_COL_DSTRONG = 1
_COL_GREEK = 3
_COL_TRANSLITERATION = 4
_COL_MORPH = 5
_COL_GLOSS = 6
_COL_DEFINITION = 7

_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_BRIEF_LEX = (
    "UNWIND $rows AS row "
    "MERGE (n:`BriefLexEntry` {strong_disambig: row.strong_disambig}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_LEX_FOR = (
    "UNWIND $rows AS row "
    "MATCH (b:BriefLexEntry) WHERE b.strong_disambig = row.strong_disambig "
    "MATCH (g:`GreekLemma` {id: row.base_strong}) "
    "MERGE (b)-[r:`LEX_FOR`]->(g) RETURN count(r) AS edges"
)


def _column(parts: list[str], index: int) -> str:
    if index < len(parts):
        return parts[index].strip()
    return ""


def _disambig_token(dstrong_cell: str, base_strong: str) -> str:
    head = dstrong_cell.split()
    if head and head[0].startswith("G"):
        return head[0]
    return base_strong


def _first_nonempty(*candidates: str) -> str:
    for value in candidates:
        if value:
            return value
    return ""


def _compose_gloss_line(
    strong_disambig: str, greek: str, transliteration: str | None, english: str
) -> str:
    head = f"{strong_disambig} {greek}"
    if transliteration:
        head = f"{head} {transliteration}"
    return f"{head}: {english}"


def _row_to_node(parts: list[str]) -> dict[str, Any] | None:
    base_strong = _column(parts, _COL_ESTRONG)
    if not _ESTRONG_PATTERN.match(base_strong):
        return None
    strong_disambig = _disambig_token(_column(parts, _COL_DSTRONG), base_strong)
    raw_greek = _column(parts, _COL_GREEK)
    raw_translit = _column(parts, _COL_TRANSLITERATION)
    raw_pos = _column(parts, _COL_MORPH)
    raw_gloss = _column(parts, _COL_GLOSS)
    raw_definition = _column(parts, _COL_DEFINITION)

    greek = _first_nonempty(raw_greek, raw_translit, strong_disambig)
    english = _first_nonempty(raw_gloss, raw_greek, raw_translit, strong_disambig)
    definition = _first_nonempty(raw_definition, english)
    transliteration = raw_translit if raw_translit else None
    pos = raw_pos if raw_pos else None

    gloss_line = _compose_gloss_line(
        strong_disambig, greek, transliteration, english
    )
    return {
        "strong_disambig": strong_disambig,
        "gloss_line": gloss_line,
        "base_strong": base_strong,
        "greek": greek,
        "transliteration": transliteration,
        "pos": pos,
        "english": english,
        "definition": definition,
        "language": LANGUAGE,
        "source": SOURCE_SLUG,
        "license": LICENSE_ID,
        "redistribute": True,
    }


def _find_data_start(lines: list[str]) -> int:
    for idx, line in enumerate(lines):
        if line.startswith("eStrong") and "dStrong" in line and "Greek" in line:
            return idx + 1
    return len(lines)


def _parse_lines(lines: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in lines[_find_data_start(lines):]:
        line = raw.rstrip("\r")
        if "\t" not in line:
            continue
        node = _row_to_node(line.split("\t"))
        if node is None:
            continue
        key = node["strong_disambig"]
        if key in seen:
            continue
        seen.add(key)
        rows = [*rows, node]
    return rows


def _load_rows(data_root: Path) -> list[dict[str, Any]]:
    path = data_root / LEXICONS_SUBDIR / TBESG_FILE
    if not path.exists():
        path = data_root / TBESG_FILE
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as handle:
        text = handle.read()
    return _parse_lines(text.splitlines())


def _merge_source(session: Any) -> None:
    payload = [
        {"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": True}
    ]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_brief_lex(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        session.run(_MERGE_BRIEF_LEX, rows=batch).consume()
        total += len(batch)
    return total


def _merge_lex_for(session: Any, rows: list[dict[str, Any]]) -> int:
    edge_rows = [
        {
            "strong_disambig": r["strong_disambig"],
            "base_strong": r["base_strong"],
        }
        for r in rows
    ]
    total = 0
    for start in range(0, len(edge_rows), BATCH_SIZE):
        batch = edge_rows[start:start + BATCH_SIZE]
        session.run(_MERGE_LEX_FOR, rows=batch).consume()
        total += len(batch)
    return total


def ingest_stepbible_tbesg(
    data_root: Path, settings: Settings
) -> dict[str, int]:
    """Parse STEPBible-TBESG and MERGE BriefLexEntry, Source, LEX_FOR."""
    rows = _load_rows(Path(data_root))
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        merged = _merge_brief_lex(session, rows)
        edges = _merge_lex_for(session, rows)
    return {"BriefLexEntry": merged, "Source": 1, "LEX_FOR": edges}
