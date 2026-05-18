"""STEPBible-TAGNT adapter contract (Decision 16 semantic projection).

This module is the docstring-only contract for the STEPBible Translators
Amalgamated Greek NT adapter. The implementation commit replaces this
docstring with executable code; until then this file declares the node
shape, edge shape, stable-id format, predicate types, expected counts,
acceptance Cypher, edge-case handling, dependencies, and license posture
that the Phase C implementer-impl caste must honour.

Adapter target
==============
File path: ingest/lexical/stepbible_tagnt.py
Phase: Phase 02, Group 2 (witness layer), bullet 6 of
docs/implementation_phases/phase_02_lexical_ingest.md.
Inventory source slug: STEPBible-TAGNT.
Upstream input: TSV files under data/private/stepbible/Translators
Amalgamated OT+NT/ matching TAGNT*.txt, one tagged Greek word per row.

Decisions implemented
=====================
Decision 16 (STEPBible-TAHOT and STEPBible-TAGNT column coverage). The
TAGNT projection table from Decision 16 names ten semantic columns the
adapter MUST emit on every TaggedToken row, replacing the upstream
placeholder column names (col_2 through col_16) with the README header
identifiers recorded in the snapshot ledger.

Labels emitted
==============
TaggedToken (with property source set to the string 'STEPBible-TAGNT').
No additional node labels are introduced by this adapter; the GreekLemma
nodes joined by INSTANCE_OF and the Verse nodes joined by IN_VERSE are
populated by the Group 1 adapters listed under Dependencies.

Edges emitted
=============
INSTANCE_OF: TaggedToken to GreekLemma, keyed by the canonical Greek
Strong identifier carried in the dstrongs_grammar column. The edge has
no properties beyond its rel_type; the join key is the GreekLemma node
property id, which MACULA-Greek and MorphGNT-SBLGNT register in Group 1.

IN_VERSE: TaggedToken to Verse, keyed by the OSIS reference derived
from the upstream word_and_type reference column. The edge has no
properties; the join key is the Verse node property osisID, populated
by MorphGNT-SBLGNT for NT verses per Decision 15.

Stable id
=========
Each TaggedToken node id is the string formed by joining the source
slug prefix, the OSIS verse reference, and the per-verse word position:

    stepbible-tagnt:<osisRef>.w<pos>

where osisRef is the canonical three-token OSIS reference of the form
Book.Chapter.Verse (e.g. Matt.1.1) and pos is the zero-padded two-digit
position of the word within the verse (e.g. w01, w02). The format
mirrors the OSHB and MorphGNT stable-id format documented under the
Idempotency section of docs/implementation_phases/phase_02_lexical_ingest.md
so that MERGE-by-stable-id re-runs are byte-identical across two ingest
passes. The uniqueness constraint tagged_token_id in graph/lexical.cypher
enforces uniqueness on the TaggedToken.id property and rejects any
second-write attempt for the same identifier.

Per-field predicate type table (Decision 16 TAGNT projection)
=============================================================
Each property on the TaggedToken node carries the type and predicate
declared below. Predicates resolve at acceptance time through the macro
expander in tools/predicates_by_type.cypher; verifier scripts MUST NOT
inline a predicate body.

    word_and_type        string   $pred_string(x)
    greek                string   $pred_string(x)
    english_translation  string   $pred_string(x)
    dstrongs_grammar     string   $pred_string(x)
    dictionary_gloss     string   $pred_string(x)
    editions             string   $pred_string(x)
    meaning_variants     list     $pred_list(x)
    spelling_variants    list     $pred_list(x)
    sstrong_instance     string   $pred_string(x)
    alt_strongs          string   $pred_string(x)

The two list-typed properties (meaning_variants and spelling_variants)
are populated by splitting the upstream semicolon-delimited string into
its component tokens, so the $pred_list(x) predicate reports honest
presence (size greater than zero) rather than reading a single packed
string as one populated value. The other eight properties are persisted
as the upstream string verbatim after Unicode NFC normalisation and
whitespace strip.

Source slug, tier, and expected count
=====================================
Source slug: STEPBible-TAGNT.
Tier: A (deterministic line count over the versioned upstream tarball).
Expected count: 141720 records, locked in tools/expected_counts.json
at sources.STEPBible-TAGNT.expected_count with tolerance 0 (Tier A
exact match required).
Record unit: word (one TaggedToken node per tagged Greek word row).

Acceptance Cypher (from phase_02 bullet 6)
==========================================
The phase-02 runbook bullet 6 declares this adapter's acceptance query
as the following Cypher, which the Phase D triangle-test runner asserts
returns a non-zero token count:

    MATCH (t:TaggedToken {source: 'STEPBible-TAGNT'})
    WHERE size(t.meaning_variants) >= 0
    WITH count(t) AS tokens
    RETURN tokens, tokens > 0

The size predicate on meaning_variants forces the verifier to confirm
that the list-typed property exists as a list (Cypher size() rejects a
scalar string), which catches the Decision 16 edge case where an
implementer might forget the semicolon split.

A second acceptance ratio query, generated per the per-adapter pattern
section of phase_02, applies $pred_string and $pred_list against the
ten projected fields and asserts each per-field ratio meets the Tier A
exact match against the expected_count baseline.

Edge cases handled (Decision 16)
================================
Edge case 1 (TAGNT specific): the upstream Spelling variants and
Meaning variants columns carry semicolon-delimited token lists. The
adapter MUST split each on the semicolon, strip surrounding whitespace
on each component, drop empty components, and persist the result as a
list-typed property. The predicate $pred_list(x) returns true only when
the list is non-empty; this ensures the verifier's per-field presence
ratio measures real population rather than the artefact of a single
packed string registering as one populated value.

Edge case 2 (shared with TAHOT through Decision 16): an upstream column
the inventory catalog rendered at zero occurrence in the sample is
populated only on selected books. The adapter MUST persist the column
when present on a given row and leave it null on rows where the
upstream emits an empty cell. The predicate table marks every nullable
column as such, so $pred_string(x) returns false for the null and the
acceptance ratio reflects the gap honestly.

Edge case 3: the alt_strongs column may carry a Strong code that
differs from the dstrongs_grammar primary Strong when the upstream
records a sense alternative. The adapter MUST persist alt_strongs
verbatim without overwriting the primary Strong on the INSTANCE_OF
edge join key. Both Strong values stay queryable through the node
properties; downstream Pipeline 2 consumers decide which one to follow.

Edge case 4: the editions column packs a comma-delimited token set
identifying the manuscript editions that attest the row's reading. The
adapter MUST persist editions as the upstream string verbatim (typed
string, predicate $pred_string) and MUST NOT split it into a list; the
list-typed split is reserved for the two semicolon-delimited columns
named in edge case 1 to keep the predicate table stable across the
TAHOT and TAGNT siblings of Decision 16.

Edge case 5: word_and_type packs both the OSIS reference token and the
upstream type tag in one column. The adapter MUST parse the leading
reference token to derive the IN_VERSE join key and persist the full
word_and_type string on the node so the upstream payload remains
auditable through the snapshot ledger.

Dependencies
============
Verse nodes (from Group 1 MorphGNT-SBLGNT for NT verses per Decision
15) MUST exist before this adapter runs so the IN_VERSE join resolves
on Verse.osisID. GreekLemma nodes (from Group 1 MACULA-Greek-Nestle1904
and MACULA-Greek-SBLGNT per Decision 2) MUST exist before this adapter
runs so the INSTANCE_OF join resolves on GreekLemma.id. The wipe
contract in tools/wipe_lexical.py guarantees an empty store at the
start of the Phase 02 run, so MERGE-by-stable-id writes start from a
clean baseline and the uniqueness constraints in graph/lexical.cypher
reject any second-write attempt for the same TaggedToken.id.

License posture (Decision 14)
=============================
License slug: CC-BY-4.0 per docs/LICENSE_TAGGING.md row 'STEPBible-TAGNT'.
Redistribute: true. The adapter MUST register a Source node with
slug = 'STEPBible-TAGNT', license = 'CC-BY-4.0', and redistribute = true
once at ingest start, before any record-level write, so the Decision 14
source_slug uniqueness constraint runs against the registered slug. The
Phase 03 ingest job exporter forwards the redistribute boolean into the
chunk envelope so Pipeline 3 honours bulk-redistribution rules per the
license_guard.check_redistribute contract.

Non-goals for this adapter
==========================
This adapter does not write to Verse.text (Decision 15 names MorphGNT
as the only NT writer of the canonical Verse.text surface). This
adapter does not write to GreekLemma (the lemma node set is established
by Group 1 MACULA-Greek adapters per Decision 2). This adapter does not
emit edges other than INSTANCE_OF and IN_VERSE; cross-reference,
parallel, and bridge edges belong to the adapters named in their
respective Decision blocks. This adapter does not invoke any embedding
or Pipeline 2 verdict logic; per the Phase 02 runbook 'What this phase
does not do' section, embedding belongs to Phase E and Pipeline 2
belongs to Phase F.

Idempotency
===========
Re-running the adapter over the same upstream bytes produces a
byte-identical set of MERGE writes because every TaggedToken.id is a
pure function of the upstream osisRef and per-verse position, every
INSTANCE_OF edge resolves to a GreekLemma keyed on a deterministic
Strong identifier, and every IN_VERSE edge resolves to a Verse keyed
on a deterministic osisID. The Phase D triangle test recomputes the
per-row SHA-256 hash twice over identical inputs and asserts the
sorted hash list matches byte-for-byte across the two runs.

Network isolation
=================
The adapter reads only the pre-fetched cache at data/private/stepbible.
It MUST NOT import subprocess, socket, httpx, requests, urllib,
aiohttp, mmap, os.system, os.spawn, posix_spawn, pty, pipes, winreg,
ctypes, or dynamic __import__; tools/check_adapter_purity.py rejects
any of those imports under the AST scan that gates the Phase 02
in-air-gap ingest run.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "STEPBible-TAGNT"
LICENSE_ID = "CC-BY-4.0"
TAGNT_SUBDIR = "Translators Amalgamated OT+NT"
TAGNT_FILES = (
    "TAGNT Mat-Jhn - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt",
    "TAGNT Act-Rev - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt",
)
BATCH_SIZE = 500
ID_PREFIX = "stepbible-tagnt"

_HEADER_TOKEN = "Word & Type"

_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_TOKEN = (
    "UNWIND $rows AS row MERGE (n:`TaggedToken` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_INSTANCE_OF = (
    "UNWIND $rows AS row "
    "MATCH (a {id: row.from_id}), (b {id: row.to_id}) "
    "MERGE (a)-[r:`INSTANCE_OF`]->(b) RETURN count(r) AS edges"
)
_MERGE_IN_VERSE = (
    "UNWIND $rows AS row "
    "MATCH (a {id: row.from_id}), (b {osisID: row.to_id}) "
    "MERGE (a)-[r:`IN_VERSE`]->(b) RETURN count(r) AS edges"
)


def _normalise(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def _split_semicolon_list(value: str) -> list[str]:
    if not value:
        return []
    parts = [p.strip() for p in value.split(";")]
    return [p for p in parts if p]


def _parse_word_and_type(word_and_type: str) -> tuple[str, str] | None:
    if "#" not in word_and_type:
        return None
    osis_ref, rest = word_and_type.split("#", 1)
    pos_token = rest.split("=", 1)[0]
    osis_ref = osis_ref.strip()
    pos_token = pos_token.strip()
    if not osis_ref or not pos_token:
        return None
    return osis_ref, pos_token


def _strong_from_grammar(dstrongs_grammar: str) -> str:
    return dstrongs_grammar.split("=", 1)[0].strip() if dstrongs_grammar else ""


def _iter_file_lines(path: Path) -> Iterator[str]:
    with path.open(encoding="utf-8-sig") as fh:
        for raw in fh:
            yield raw.rstrip("\r\n")


def _iter_data_rows(lines: Iterator[str]) -> Iterator[list[str]]:
    header_seen = False
    for line in lines:
        if not header_seen:
            if line.startswith(_HEADER_TOKEN):
                header_seen = True
            continue
        if "\t" not in line:
            continue
        first = line.split("\t", 1)[0].strip()
        if not first or first.startswith("#") or "#" not in first:
            continue
        yield [p.strip() for p in line.split("\t")]


def _row_to_token(parts: list[str]) -> dict[str, Any] | None:
    if len(parts) < 5:
        return None
    word_and_type = _normalise(parts[0])
    parsed = _parse_word_and_type(word_and_type)
    if parsed is None:
        return None
    osis_ref, pos_token = parsed
    digits = "".join(ch for ch in pos_token if ch.isdigit())
    if not digits:
        return None
    pos_padded = digits.zfill(2)
    stable_id = f"{ID_PREFIX}:{osis_ref}.w{pos_padded}"
    greek = _normalise(parts[1]) if len(parts) > 1 else ""
    english_translation = _normalise(parts[2]) if len(parts) > 2 else ""
    dstrongs_grammar = _normalise(parts[3]) if len(parts) > 3 else ""
    dictionary_gloss = _normalise(parts[4]) if len(parts) > 4 else ""
    editions = _normalise(parts[5]) if len(parts) > 5 else ""
    meaning_raw = parts[6] if len(parts) > 6 else ""
    spelling_raw = parts[7] if len(parts) > 7 else ""
    sstrong_instance = _normalise(parts[11]) if len(parts) > 11 else ""
    alt_strongs = _normalise(parts[12]) if len(parts) > 12 else ""
    return {
        "id": stable_id,
        "osis_ref": osis_ref,
        "strong_id": _strong_from_grammar(dstrongs_grammar),
        "properties": {
            "id": stable_id,
            "source": SOURCE_SLUG,
            "word_and_type": word_and_type,
            "greek": greek,
            "english_translation": english_translation,
            "dstrongs_grammar": dstrongs_grammar,
            "dictionary_gloss": dictionary_gloss,
            "editions": editions,
            "meaning_variants": _split_semicolon_list(meaning_raw),
            "spelling_variants": _split_semicolon_list(spelling_raw),
            "sstrong_instance": sstrong_instance,
            "alt_strongs": alt_strongs,
        },
    }


def _iter_tokens(data_root: Path) -> Iterator[dict[str, Any]]:
    tagnt_dir = data_root / TAGNT_SUBDIR
    seen: set[str] = set()
    for filename in TAGNT_FILES:
        path = tagnt_dir / filename
        if not path.exists():
            continue
        for parts in _iter_data_rows(_iter_file_lines(path)):
            token = _row_to_token(parts)
            if token is None or token["id"] in seen:
                continue
            seen.add(token["id"])
            yield token


def _load_tokens(data_root: Path) -> list[dict[str, Any]]:
    return list(_iter_tokens(data_root))


def _merge_source(session: Any) -> None:
    payload = [{"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": True}]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_tokens(session: Any, tokens: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(tokens), BATCH_SIZE):
        chunk = tokens[start:start + BATCH_SIZE]
        rows = [t["properties"] for t in chunk]
        session.run(_MERGE_TOKEN, rows=rows).consume()
        total += len(chunk)
    return total


def _merge_instance_edges(session: Any, tokens: list[dict[str, Any]]) -> int:
    edge_rows = [
        {"from_id": t["id"], "to_id": t["strong_id"]}
        for t in tokens if t["strong_id"]
    ]
    total = 0
    for start in range(0, len(edge_rows), BATCH_SIZE):
        chunk = edge_rows[start:start + BATCH_SIZE]
        session.run(_MERGE_INSTANCE_OF, rows=chunk).consume()
        total += len(chunk)
    return total


def _merge_in_verse_edges(session: Any, tokens: list[dict[str, Any]]) -> int:
    edge_rows = [
        {"from_id": t["id"], "to_id": t["osis_ref"]}
        for t in tokens if t["osis_ref"]
    ]
    total = 0
    for start in range(0, len(edge_rows), BATCH_SIZE):
        chunk = edge_rows[start:start + BATCH_SIZE]
        session.run(_MERGE_IN_VERSE, rows=chunk).consume()
        total += len(chunk)
    return total


def ingest_stepbible_tagnt(
    data_root: Path, settings: Settings
) -> dict[str, int]:
    """Parse STEPBible-TAGNT and MERGE TaggedToken nodes plus INSTANCE_OF and IN_VERSE edges."""
    tokens = _load_tokens(Path(data_root))
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        merged = _merge_tokens(session, tokens)
        instance_edges = _merge_instance_edges(session, tokens)
        verse_edges = _merge_in_verse_edges(session, tokens)
    return {
        "TaggedToken": merged,
        "Source": 1,
        "INSTANCE_OF": instance_edges,
        "IN_VERSE": verse_edges,
    }
