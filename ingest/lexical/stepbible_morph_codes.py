"""STEPBible-morph-codes adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the STEPBible-morph-codes adapter for the Pipeline 1 lexical
Neo4j reseed. The body of this file is intentionally empty at this commit
because Phase C.1 of the RESEED_PLAN (verifier-caste architecture) requires
the contract to be committed BEFORE any implementation body and BEFORE the
Verifier-caste subagent writes its coverage tests. The Verifier compiles
its test queries against this docstring plus the matching sections of
docs/SCHEMA_DECISIONS.md without reading the implementation body. The
function-body commit is a separate downstream commit by the
Implementer-impl caste.

The adapter populates a pure reference lookup table. The MorphCode nodes
this adapter writes are joined by downstream Phase D verifier queries via
MATCH on the code property; no outbound edges are emitted from this
adapter.

Source inventory
================
Source slug:      STEPBible-morph-codes
Tier:             A (deterministic, tolerance 0)
Expected count:   2782 records (record_unit: morph_code)
Tier rationale:   STEPBible morphology code dictionary ships one row per
                  code with human-readable expansion. Total is a
                  deterministic line count from the versioned upstream
                  release used at ingest, identical across reruns under
                  tagged builds.
Decisions implemented: 17.

Upstream and license
====================
Upstream path:    data/private/stepbible/Morphology codes/ ... (versioned
                  release tarball under the Tyndale STEPBible data tree).
License id:       CC-BY-4.0 per docs/LICENSE_TAGGING.md per-source map.
Source record:    The Source node for slug 'STEPBible-morph-codes' is
                  MERGEd once per ingest run with properties:
                    slug          = 'STEPBible-morph-codes'  ($pred_string)
                    license       = 'CC-BY-4.0'              ($pred_string)
                    redistribute  = true                     ($pred_bool)
                  per Decision 14 Source uniqueness constraint
                  (source_slug constraint, graph/lexical.cypher).

Emitted node labels and properties
==================================
The adapter MERGEs one node label: MorphCode. No edges are written.

MorphCode (Decision 17)
-----------------------
Stable id format:    The natural key is the upstream code value verbatim
                     (e.g. 'HVqp3ms' for a Hebrew Qal perfect 3rd masculine
                     singular verb code). The code property is the
                     canonical join key downstream verifier queries
                     reference via MATCH (m:MorphCode {code: $code}).
Stable id property:  code (string, $pred_string).
MERGE key:           MorphCode.code (constraint morph_code_unique,
                     graph/lexical.cypher: CREATE CONSTRAINT
                     morph_code_unique IF NOT EXISTS FOR (m:MorphCode)
                     REQUIRE m.code IS UNIQUE per Decision 17).
Persisted properties (Decision 17 Per-field predicate type table for
STEPBible-morph-codes):
    code            string  $pred_string(x)   (canonical morph code, natural key)
    expansion       string  $pred_string(x)   (human-readable parse text)
    expansions      list    $pred_list(x)     (alternative analyses; nullable when row carries exactly one expansion)
    source          string  $pred_string(x)   (= 'STEPBible-morph-codes')

The expansion property is the singular canonical analysis carried on
every MorphCode node. The expansions property is a list-typed property
populated only when the upstream row has more than one populated detail
column (the alternative-analyses edge case enumerated under Decision 17
Edge cases handled bullet 1). When the upstream row carries exactly one
expansion, expansions is left null and the $pred_list(expansions)
predicate returns false on that node, honestly reflecting the absence
of alternatives.

Sparse residual columns are NOT persisted. The data inventory catalog
records 53 residual placeholder columns on this source whose occurrence
rate is zero or near-zero in the inventory sample. Per Decision 17 Rule
("Sparse columns are not persisted; only columns with occurrence > 0 in
the inventory catalog enter the node"), this adapter MUST skip every
residual column whose inventory occurrence is zero. Only code,
expansion, and the alternatives list when present enter the MorphCode
node.

Emitted edge types
==================
None. STEPBible-morph-codes is a pure reference lookup table consumed
by downstream verifier queries via MATCH on the code property; the
adapter writes zero outbound relationships from MorphCode nodes.
Provenance attribution travels through the source property on each
MorphCode node and through the Source node MERGEd at ingest start per
Decision 14, with no FROM_EDITION edge required because no other label
references this lookup.

Idempotency
===========
Every MorphCode node is MERGEd by its stable code property. Re-running
this adapter over identical upstream bytes produces zero new nodes;
Decision 14 plus Decision 17 uniqueness constraint morph_code_unique on
MorphCode.code additionally enforces this at the Neo4j storage layer.
Per RESEED_PLAN D.3 the snapshot ledger records each row as a sorted
SHA-256 over the canonical-JSON of its property bag, and the triangle
test asserts byte-equal snapshot across two runs over identical inputs.

Edge cases handled
==================
Per Decision 17 Edge cases handled:
  1. A handful of morph codes resolve to multiple expansions because
     the upstream documents alternative analyses. The adapter MUST
     persist all expansions in an expansions list-typed property when
     the row has more than one populated detail column, preventing
     silent loss of alternative parses. Single-expansion rows leave
     expansions null so $pred_list(expansions) honestly reports the
     absence of alternatives.
  2. The proper-nouns table (a sibling Decision 17 source handled by
     ingest/lexical/stepbible_proper_nouns.py, not by this adapter)
     contains both Hebrew and Greek names in distinct sections. This
     adapter does not write ProperNoun nodes and is unaffected by the
     proper-nouns edge case; it is cross-referenced here because both
     adapters implement Decision 17 and share the sparse-residual-
     column rule.
  3. A small subset of proper-noun entries (handled by the sibling
     adapter, not by this one) carry a numeric verse-count column with
     a non-numeric placeholder. This adapter does not write a
     verse_count property and is unaffected; the rule is referenced
     here only for cross-decision audit completeness.

Per Decision 14 Edge cases handled:
  1. The Source node carries one node per canonical source slug listed
     in docs/LICENSE_TAGGING.md, and the source_slug uniqueness
     constraint enforces no two ingest runs collide on slug. This
     adapter MERGEs the 'STEPBible-morph-codes' Source node exactly
     once at ingest start, before any record-level write, so the
     constraint check runs against the registered slug only.

Acceptance Cypher (phase_02_lexical_ingest.md bullet 11, verbatim)
==================================================================

    MATCH (m:MorphCode {source: 'STEPBible-morph-codes'})
    WHERE m.code IS NOT NULL AND m.expansion IS NOT NULL
    WITH count(m) AS codes
    RETURN codes, codes > 0

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 11
and is the runbook-level acceptance gate the Phase D verifier runs
against the populated lexical store. The query asserts:
  - at least one MorphCode node exists with source
    'STEPBible-morph-codes';
  - every counted node carries a non-null code and a non-null
    expansion, matching the $pred_string predicate semantics from
    tools/predicates_by_type.cypher.

In addition to the runbook gate, Decision 17's own acceptance Cypher
is the codes-floor gate Phase D runs (reproduced here verbatim from
docs/SCHEMA_DECISIONS.md Decision 17):

    MATCH (m:MorphCode {source: 'STEPBible-morph-codes'})
    WHERE m.code IS NOT NULL AND m.expansion IS NOT NULL AND size(m.code) > 0
    WITH count(m) AS codes
    RETURN codes, codes > 100

The Decision 17 acceptance Cypher tightens the runbook gate with a
codes-greater-than-one-hundred floor and an additional size-greater-
than-zero check on the code property, asserting that no MorphCode node
carries an empty-string code value. The expected total per
tools/expected_counts.json is 2782 records under tier A (tolerance 0),
so the codes-greater-than-one-hundred floor is comfortably exceeded by
the deterministic line count of the versioned upstream release.

Predicate semantics
===================
Predicate evaluation follows tools/predicates_by_type.cypher verbatim:
    $pred_string(x) := x IS NOT NULL AND trim(toString(x)) <> ""
    $pred_list(x)   := x IS NOT NULL AND size(x) > 0
    $pred_bool(x)   := x IS NOT NULL
Verifier scripts MUST NOT inline these predicates per RESEED_PLAN C.5;
the predicate file is the single source of truth for non-empty value
semantics across the lexical adapter contract set.

Network isolation
=================
This adapter reads from local disk only (the cached upstream tarball
under data/private/stepbible/). It MUST NOT import subprocess, socket,
httpx, requests, urllib, aiohttp, mmap, os.system, os.spawn, posix_spawn,
multiprocessing.connection, pty, pipes, winreg, ctypes, or dynamic
__import__, per tools/check_adapter_purity.py and RESEED_PLAN C.4. The
Phase C dry-run executes the adapter inside Docker with --network=none.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 17  STEPBible morph-codes and proper-nouns reference tables.
docs/SCHEMA_DECISIONS.md Decision 14  Strong / Source / TFNode constraint policy (Source node MERGE).
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 11.
docs/implementation_phases/RESEED_PLAN.md Phase C.1 (TDD workflow per adapter) and Idempotency section of phase_02.
docs/LICENSE_TAGGING.md per-source map (CC-BY-4.0 row).
graph/lexical.cypher constraint morph_code_unique on MorphCode.code per Decision 17.
tools/expected_counts.json sources."STEPBible-morph-codes" (tier A, expected_count 2782, record_unit morph_code).
tools/predicates_by_type.cypher for $pred_string, $pred_list, $pred_bool semantics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "STEPBible-morph-codes"
LICENSE_ID = "CC-BY-4.0"
MORPH_SUBDIR = "Morphology codes"
HEBREW_FILE = (
    "TEHMC - Translators Expansion of Hebrew Morphology Codes - STEPBible.org CC BY.txt"
)
GREEK_FILE = (
    "TEGMC - Translators Expansion of Greek Morphhology Codes - STEPBible.org CC BY.txt"
)
BATCH_SIZE = 500
_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_MORPH = (
    "UNWIND $rows AS row MERGE (n:`MorphCode` {code: row.code}) "
    "SET n += row RETURN count(n) AS upserted"
)


def _read_text(path: Path) -> str:
    with path.open(encoding="utf-8-sig") as fh:
        return fh.read()


def _split_sections(text: str) -> tuple[str, str]:
    full_idx = text.find("FULL MORPHOLOGY CODES")
    if full_idx == -1:
        return text, ""
    brief_idx = text.find("BRIEF LEXICAL MORPHOLOGY CODES")
    brief = text[brief_idx:full_idx] if brief_idx != -1 else ""
    return brief, text[full_idx:]


def _split_alternatives(meaning: str) -> list[str]:
    for sep in (" OR ", " / "):
        if sep in meaning:
            return [p.strip() for p in meaning.split(sep) if p.strip()]
    return [meaning]


def _parse_brief(section: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    header = False
    for raw in section.splitlines():
        line = raw.rstrip("\r")
        s = line.strip()
        if not s or (set(s) <= {"="}):
            continue
        if not header:
            if s.startswith("Code") and "Meaning" in s:
                header = True
            continue
        if "\t" not in line:
            continue
        parts = [p.strip() for p in line.split("\t")]
        code = parts[0]
        meaning = parts[-1] if len(parts) >= 2 else ""
        if not code or not meaning or code in seen:
            continue
        seen.add(code)
        alts = _split_alternatives(meaning)
        rows = [*rows, {
            "code": code,
            "expansion": meaning,
            "expansions": alts if len(alts) > 1 else None,
            "source": SOURCE_SLUG,
        }]
    return rows


def _iter_blocks(section: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw in section.splitlines():
        line = raw.rstrip("\r")
        if line.strip() == "$":
            if current:
                blocks = [*blocks, current]
            current = []
            continue
        current = [*current, line]
    if current:
        blocks = [*blocks, current]
    return blocks


def _block_to_node(block: list[str], seen: set[str]) -> dict[str, Any] | None:
    head: str | None = None
    head_idx = -1
    for idx, line in enumerate(block):
        if line.strip() and not line.startswith("\t") and not line.startswith(" "):
            head = line
            head_idx = idx
            break
    if head is None:
        return None
    parts = head.split("\t", 1)
    code = parts[0].strip()
    if not code or code in seen:
        return None
    seen.add(code)
    spec = parts[1].strip() if len(parts) > 1 else ""
    details = [block[i].strip() for i in range(head_idx + 1, len(block)) if block[i].strip()]
    primary = spec or (details[0] if details else code)
    if len(details) > 1:
        items: list[str] = [spec] if spec else []
        for d in details:
            if d and d not in items:
                items = [*items, d]
        expansions = items
    else:
        expansions = None
    return {
        "code": code,
        "expansion": primary,
        "expansions": expansions,
        "source": SOURCE_SLUG,
    }


def _parse_full(section: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for block in _iter_blocks(section):
        node = _block_to_node(block, seen)
        if node is not None:
            rows = [*rows, node]
    return rows


def _load_rows(data_root: Path) -> list[dict[str, Any]]:
    morph_dir = data_root / MORPH_SUBDIR
    collected: list[dict[str, Any]] = []
    for filename in (HEBREW_FILE, GREEK_FILE):
        path = morph_dir / filename
        if not path.exists():
            continue
        brief, full = _split_sections(_read_text(path))
        collected = [*collected, *_parse_brief(brief), *_parse_full(full)]
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in collected:
        c = r["code"]
        if c in seen:
            continue
        seen.add(c)
        deduped = [*deduped, r]
    return deduped


def _merge_source(session: Any) -> None:
    payload = [{"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": True}]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_morph_codes(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        session.run(_MERGE_MORPH, rows=batch).consume()
        total += len(batch)
    return total


def ingest_stepbible_morph_codes(
    data_root: Path, settings: Settings
) -> dict[str, int]:
    """Parse STEPBible morphology codes and MERGE MorphCode + Source nodes."""
    rows = _load_rows(data_root)
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        merged = _merge_morph_codes(session, rows)
    return {"MorphCode": merged, "Source": 1}
