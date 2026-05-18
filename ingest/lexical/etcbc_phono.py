"""ETCBC-phono adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the ETCBC-phono adapter for the Pipeline 1 lexical Neo4j
reseed. The body of this file is intentionally empty at this commit
because Phase C.1 of the RESEED_PLAN (verifier-caste architecture)
requires the contract to be committed BEFORE any implementation body and
BEFORE the Verifier-caste subagent writes its coverage tests. The
Verifier compiles its test queries against this docstring plus the
matching sections of docs/SCHEMA_DECISIONS.md without reading the
implementation body. The function-body commit is a separate downstream
commit by the Implementer-impl caste.

Source inventory
================
Source slug:      ETCBC-phono
Tier:             A (deterministic, tolerance 0)
Expected count:   426590 records (record_unit: word)
Tier rationale:   ETCBC phonetic transcription ships one phono value per
                  BHSA word slot in the same text-fabric module. The
                  total equals the BHSA word slot count exactly because
                  the feature is keyed one-to-one with word identifiers.
Decisions implemented: 3.

Upstream and license
====================
Upstream path:    text-fabric phono module bundled with the ETCBC BHSA
                  release at C:/Users/Ebenezer/text-fabric-data/github/
                  ETCBC/bhsa/tf/2021. The phono feature is shipped as a
                  text-fabric feature file keyed by word-slot node
                  identifier, identical join key to the BHSA word otype.
License id:       CC-BY-NC-4.0 per docs/LICENSE_TAGGING.md row for
                  ETCBC-BHSA (the phono feature inherits the BHSA
                  license tag because it is shipped inside the same
                  text-fabric module distribution). The Source node
                  MERGEd by this adapter carries redistribute = false
                  per Decision 14, mirroring the BHSA adapter so the
                  CC-BY-NC clause is respected uniformly across the
                  ETCBC family.
Source record:    The Source node for slug 'ETCBC-phono' is MERGEd once
                  per ingest run with properties:
                    slug          = 'ETCBC-phono'         ($pred_string)
                    license       = 'CC-BY-NC-4.0'        ($pred_string)
                    redistribute  = false                 ($pred_bool)
                  per Decision 14 Source uniqueness constraint
                  (source_slug constraint, graph/lexical.cypher).

Operation
=========
This adapter is a property-attach adapter. It DOES NOT spawn a new node
label. It ATTACHES a single optional 'phono' property onto pre-existing
BhsaWord nodes that were emitted by the ETCBC-BHSA adapter in Group 4
step 14 of docs/implementation_phases/phase_02_lexical_ingest.md. The
attach happens via MATCH-then-SET, not MERGE-then-SET, because the
BhsaWord nodes already exist under the bhsa_word_id uniqueness
constraint in graph/lexical.cypher; a MERGE here would either succeed
no-op or violate the dependency contract that BHSA Group 4 step 14 has
already MERGEd the nodes.

Per Decision 3 Edge cases handled bullet 3, ETCBC-phono ships a single
'phono' field at 0.984 occurrence rate keyed by the same word slot
identifier, and the adapter MUST attach it as an optional property on
BhsaWord rather than spawning a separate node, because the 1.6 percent
null rate reflects ketiv-only slots with no spoken realisation.

Emitted node labels and properties
==================================
The adapter emits ZERO new node labels. It mutates ONE property on
existing BhsaWord nodes plus the shared Source administrative node.
Each row below quotes its persisted property name, the primitive type
the value carries, and the matching predicate from
tools/predicates_by_type.cypher.

BhsaWord (property attach, Decision 3 ETCBC-phono Per-field predicate
table)
----------------------------------------------------------------------
Stable id format:    Inherited verbatim from the ETCBC-BHSA adapter
                     (Group 4 step 14). The BhsaWord stable id is the
                     text-fabric node identifier under the (corpus,
                     node_id) tuple uniqueness constraint declared on
                     the TFNode label in graph/lexical.cypher
                     (tfnode_tuple constraint, Decision 14). The bhsa
                     adapter emits BhsaWord with id property
                     'bhsa:tf:<node_id>' so the bhsa_word_id constraint
                     in graph/lexical.cypher rejects duplicates.
Stable id property:  id (string, $pred_string) carrying the prefix
                     'bhsa:tf:<node_id>'. This adapter MUST NOT change
                     or rewrite the id; it MATCHes by id and SETs the
                     phono property only.
Join key:            (corpus='bhsa', node_id=<text-fabric word node>).
                     The text-fabric word otype enumeration that the
                     bhsa.py adapter walks is identical to the
                     enumeration that backs the phono feature, so the
                     join is one-to-one with the 0.984 occurrence rate
                     reflecting the natural ketiv-only gap rather than
                     a key mismatch.
Persisted properties (Decision 3 ETCBC-phono Per-field predicate type
table, plus inherited administrative fields):
    phono           string  $pred_string(x)   (NULLABLE per Decision 3
                                               Edge cases handled
                                               bullet 3; 1.6 percent of
                                               word slots are
                                               ketiv-only and have no
                                               spoken realisation, so
                                               the property is set to
                                               null and
                                               $pred_string(phono)
                                               returns false on those
                                               slots without a fallback
                                               substitution)

The phono property is the only property this adapter writes onto
BhsaWord. Every other BhsaWord property (id, otype, tf_node, book,
chapter, verse, lex, g_word_utf8, source, plus the syntactic-context
properties from Decision 3 ETCBC-BHSA table) is owned exclusively by
the ETCBC-BHSA adapter at Group 4 step 14 and MUST NOT be overwritten
by this adapter.

Source (Decision 14)
--------------------
Stable id format:    'ETCBC-phono' (verbatim source slug; the phono
                     feature has its own Source node distinct from
                     'bhsa' so provenance filters can separate the
                     phonetic-overlay rows from the syntactic-context
                     rows even though both feed the same BhsaWord
                     records).
Stable id property:  slug (string, $pred_string).
MERGE key:           Source.slug (constraint source_slug,
                     graph/lexical.cypher).
Persisted properties (Decision 14 Per-field predicate type table):
    slug            string  $pred_string(x)
    license         string  $pred_string(x)   (= 'CC-BY-NC-4.0')
    redistribute    bool    $pred_bool(x)     (= false; ETCBC-phono
                                               inherits the CC-BY-NC
                                               constraint of the
                                               surrounding BHSA module
                                               so redistribute is false
                                               per Decision 14, and the
                                               adapter MUST NOT
                                               override this even when
                                               the property attach
                                               itself is internally
                                               distributable)

Emitted edge types
==================
NONE. This adapter is a property-attach adapter. It does not emit any
new edges. The phono property is a scalar attached to existing BhsaWord
nodes, so no relationship row enters the lexical Neo4j store from this
adapter. The shared Source node for slug 'ETCBC-phono' has no FROM_EDITION
edge wired from this adapter because no node-level write happens here
that would justify the edge; the Source node exists purely to register
the provenance slug under the Decision 14 uniqueness constraint.

Dependency on Group 4 step 14
=============================
This adapter has a HARD dependency on the BhsaWord nodes emitted by
ingest/lexical/bhsa.py in Group 4 step 14 of
docs/implementation_phases/phase_02_lexical_ingest.md. The MATCH clause
that selects BhsaWord nodes by their (corpus, node_id) tuple FAILS to
match zero rows if the bhsa adapter has not yet run, and no phono
property is attached. The dispatch order in phase_02_lexical_ingest.md
places this adapter in Group 4 step 16, strictly after step 14, so the
dependency is well-defined under the runbook execution order. Re-running
this adapter before the bhsa adapter is a no-op rather than an error
because MATCH-then-SET on an empty result set writes zero rows.

Stable-id and key derivation
============================
The text-fabric node identifier is a positive integer assigned by the
text-fabric library at module-load time and is stable across reruns of
the same versioned module release (ETCBC/bhsa v2021). The stable id
for the BhsaWord MATCH is the same id property the bhsa adapter wrote
('bhsa:tf:<node_id>'), keyed by (corpus='bhsa', node_id=<int>) under
the TFNode tuple uniqueness constraint (Decision 14, tfnode_tuple).
This adapter MUST resolve the (corpus, node_id) tuple to the matching
BhsaWord by walking the same text-fabric word otype enumeration that
the bhsa adapter walked, so the one-to-one keying between the phono
feature and the BhsaWord nodes is mechanical and not heuristic.

Idempotency
===========
The Source node above is MERGEd by its slug. The BhsaWord property
attach is MATCH-then-SET keyed by the stable id 'bhsa:tf:<node_id>',
which is the same id the bhsa adapter wrote under the bhsa_word_id
uniqueness constraint. Re-running this adapter over identical
text-fabric phono feature bytes produces zero new nodes, zero new
edges, and the SET writes the same phono value byte-identically onto
every BhsaWord, so the triangle test asserts byte-equal snapshot across
two runs over identical inputs. Per RESEED_PLAN D.3 the snapshot ledger
records each row as a sorted SHA-256 over the canonical-JSON of the
property bag, and the triangle test asserts byte-equal snapshot across
two runs. The 1.6 percent null rate for ketiv-only slots is preserved
across reruns because the upstream phono feature returns the same null
for the same word-slot node identifier on every read.

Edge cases handled
==================
Per Decision 3 ETCBC-phono Edge cases handled bullet 3:
  1. ETCBC-phono ships a single 'phono' field at 0.984 occurrence rate
     keyed by the same word slot identifier as the BHSA word feature.
     The adapter MUST attach 'phono' as an optional property on
     BhsaWord rather than spawning a separate node, because the 1.6
     percent null rate reflects ketiv-only slots with no spoken
     realisation. The null is preserved verbatim and no fallback
     substitution (e.g. empty string, transliteration of the consonants,
     or the literal token 'null') is applied, so
     $pred_string(phono) returns false on the ketiv-only slots
     honestly rather than reporting a populated value that does not
     exist upstream.

Per Decision 14 Edge cases handled:
  1. The Source node for slug 'ETCBC-phono' is MERGEd exactly once at
     ingest start, before any record-level write, so the source_slug
     uniqueness constraint check runs against the registered slug only.
     The phono Source slug is distinct from the BHSA Source slug
     ('bhsa') so the Decision 14 source_slug uniqueness constraint
     accepts both registrations and provenance filters can partition
     the phonetic-overlay attach from the syntactic-context emission.
  2. A TFNode tuple collision across corpora would silently corrupt
     syntactic-context bundles, so the tuple constraint tfnode_tuple
     in graph/lexical.cypher includes both 'corpus' and 'node_id'.
     This adapter MUST resolve BhsaWord rows by (corpus='bhsa',
     node_id=<int>) and MUST NOT register 'ETCBC-phono' as a corpus
     value, because the corpus identifier for the text-fabric module
     is 'bhsa' regardless of which feature file is being read.

Acceptance Cypher (phase_02_lexical_ingest.md Group 4 step 16, verbatim)
========================================================================

    MATCH (w:BhsaWord)
    WHERE w.phono IS NOT NULL
    WITH count(w) AS with_phono
    RETURN with_phono, with_phono > 0

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 4 step 16
and is the runbook acceptance gate the Phase D verifier runs against
the populated lexical store. The acceptance gate is permissive
(with_phono > 0) so the Tier A deterministic count of 426590 in
tools/expected_counts.json sources."ETCBC-phono" is the binding
floor, not this acceptance query.

Acceptance Cypher (Decision 3, three-layer containment)
=======================================================

    MATCH (c:BhsaClause)-[:CONTAINS_PHRASE]->(p:BhsaPhrase)-[:CONTAINS_WORD]->(w:BhsaWord)
    WHERE w.lex_utf8 IS NOT NULL AND w.freq_lex >= 1
    WITH count(DISTINCT w) AS covered, count(DISTINCT c) AS clauses
    RETURN covered, clauses, clauses > 0

This query is reproduced byte-for-byte from docs/SCHEMA_DECISIONS.md
Decision 3 Cypher acceptance query. It is the Decision 3 gate for the
ETCBC syntax tree shape as a whole; this adapter does not produce the
edges in the gate (Group 4 step 14 owns CONTAINS_WORD and
CONTAINS_PHRASE), but the gate is reproduced here so the Verifier-caste
subagent can compile a coverage test that ETCBC-phono runs after the
BHSA syntax tree exists.

Network isolation
=================
This adapter reads from local disk only (the text-fabric phono feature
file under the ETCBC/bhsa v2021 release at
C:/Users/Ebenezer/text-fabric-data/github/ETCBC/bhsa/tf/2021). It MUST
NOT import subprocess, socket, httpx, requests, urllib, aiohttp, mmap,
os.system, os.spawn*, posix_spawn, multiprocessing.connection, pty,
pipes, winreg, ctypes, or dynamic __import__, per
tools/check_adapter_purity.py and RESEED_PLAN C.4. The Phase C dry-run
executes the adapter inside Docker with --network=none.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 3   ETCBC syntax tree shape, ETCBC-phono Per-field predicate table, Edge cases handled bullet 3.
docs/SCHEMA_DECISIONS.md Decision 14  Strong / Source / TFNode constraint policy, license slug 'CC-BY-NC-4.0', redistribute false, tfnode_tuple constraint on (corpus, node_id).
docs/implementation_phases/phase_02_lexical_ingest.md Group 4 step 14 (BhsaWord emit) and step 16 (this adapter).
docs/implementation_phases/RESEED_PLAN.md Phase C.1 (TDD workflow per adapter) and Idempotency section of phase_02.
graph/lexical.cypher constraints bhsa_word_id (REQUIRES BhsaWord.id UNIQUE), tfnode_tuple (REQUIRES (corpus, node_id) UNIQUE on TFNode), and source_slug, plus index bhsa_word_lex on BhsaWord.lex_utf8 (no dedicated phono index; the bhsa_word_id constraint plus the id-keyed MATCH is the access path).
tools/expected_counts.json sources."ETCBC-phono" (tier A, expected_count 426590, record_unit word, tolerance 0; equals the BHSA word slot count exactly).
tools/predicates_by_type.cypher for $pred_string, $pred_bool semantics.
docs/LICENSE_TAGGING.md row 'ETCBC-BHSA' for the CC-BY-NC-4.0 license tag the phono feature inherits and the redistribute-false policy under Decision 14.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "ETCBC-phono"
LICENSE_ID = "CC-BY-NC-4.0"
PHONO_TF_PATH = Path(
    "C:/Users/Ebenezer/text-fabric-data/github/ETCBC/phono/tf/2021/phono.tf"
)
WORD_NODE_MIN = 1
WORD_NODE_MAX = 426590
BATCH_SIZE = 5000

_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_ATTACH_PHONO = (
    "UNWIND $rows AS row MATCH (w:`BhsaWord` {id: row.id}) "
    "SET w.phono = row.phono RETURN count(w) AS attached"
)


def _read_tf_body(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as fh:
        text = fh.read()
    lines = text.splitlines()
    blank_at = next((i for i, raw in enumerate(lines) if raw == ""), None)
    if blank_at is None:
        return []
    return lines[blank_at + 1:]


def _parse_phono_feature(lines: list[str]) -> dict[int, str]:
    values: dict[int, str] = {}
    counter = 1
    for raw in lines:
        if raw == "":
            counter += 1
            continue
        if "\t" in raw:
            spec, value = raw.split("\t", 1)
            if "-" in spec:
                lo, hi = (int(x) for x in spec.split("-", 1))
                for node_id in range(lo, hi + 1):
                    values[node_id] = value
                counter = hi + 1
            else:
                node_id = int(spec)
                values[node_id] = value
                counter = node_id + 1
        else:
            values[counter] = raw
            counter += 1
    return values


def _phono_value(raw: str) -> Any:
    return raw if raw.strip() != "" else None


def _load_phono_rows(path: Path) -> list[dict[str, Any]]:
    values = _parse_phono_feature(_read_tf_body(path))
    return [
        {
            "id": f"bhsa:tf:{node_id}",
            "phono": _phono_value(values.get(node_id, "")),
        }
        for node_id in range(WORD_NODE_MIN, WORD_NODE_MAX + 1)
    ]


def _merge_source(session: Any) -> None:
    payload = [{"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": False}]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _attach_phono(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        session.run(_ATTACH_PHONO, rows=batch).consume()
        total += len(batch)
    return total


def ingest_etcbc_phono(settings: Settings) -> dict[str, int]:
    """Attach phono property onto BhsaWord nodes via MATCH-then-SET."""
    rows = _load_phono_rows(PHONO_TF_PATH) if PHONO_TF_PATH.exists() else []
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        attached = _attach_phono(session, rows)
    return {"BhsaWord": attached, "Source": 1}
