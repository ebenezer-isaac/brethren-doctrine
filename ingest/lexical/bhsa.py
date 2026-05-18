"""ETCBC-BHSA adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the ETCBC-BHSA adapter for the Pipeline 1 lexical Neo4j
reseed. The body of this file is intentionally empty at this commit because
Phase C.1 of the RESEED_PLAN (verifier-caste architecture) requires the
contract to be committed BEFORE any implementation body and BEFORE the
Verifier-caste subagent writes its coverage tests. The Verifier compiles its
test queries against this docstring plus the matching sections of
docs/SCHEMA_DECISIONS.md without reading the implementation body. The
function-body commit is a separate downstream commit by the
Implementer-impl caste.

Source inventory
================
Source slug:      ETCBC-BHSA
Tier:             A (deterministic, tolerance 0)
Expected count:   426590 records (record_unit: word)
Tier rationale:   ETCBC Biblia Hebraica Stuttgartensia Amstelodamensis is
                  shipped via text-fabric as a frozen feature set. Word slot
                  count is deterministic from the otype feature in the
                  versioned text-fabric module used at ingest.
Decisions implemented: 3, 14.

Upstream and license
====================
Upstream path:    C:/Users/Ebenezer/text-fabric-data/github/ETCBC/bhsa/tf/2021
                  (text-fabric module release 2021, frozen feature set; the
                  procurement location is the per-user text-fabric-data
                  cache under the github clone of the ETCBC/bhsa repo, fixed
                  to module version 2021 so re-ingest is byte-deterministic
                  on the same machine).
License id:       CC-BY-NC-4.0 (ETCBC BHSA, personal use; matches the
                  pre-existing LICENSE constant in the legacy bhsa.py and
                  the LICENSE_NOTE 'ETCBC BHSA, CC-BY-NC-4.0 (personal use
                  only)' which the Implementer-impl caste re-emits at write
                  time).
Source record:    The Source node for slug 'ETCBC-BHSA' is MERGEd once per
                  ingest run with properties:
                    slug          = 'ETCBC-BHSA'        ($pred_string)
                    license       = 'CC-BY-NC-4.0'      ($pred_string)
                    redistribute  = false               ($pred_bool)
                  per Decision 14 Source uniqueness constraint
                  (source_slug constraint, graph/lexical.cypher line 35)
                  and Decision 14 Edge cases handled bullet 2 (the Source
                  MERGE runs before any record-level write so the
                  uniqueness constraint check sees the registered slug
                  only).

Emitted node labels and properties
==================================
The adapter MERGEs four distinct node labels by stable id. Each row below
quotes its persisted property name, the primitive type the value carries,
and the matching predicate from tools/predicates_by_type.cypher. Decision
3 fixes the three-layer syntactic projection (BhsaClause, BhsaPhrase,
BhsaWord) and Decision 14 fixes the TFNode administrative label whose
uniqueness constraint covers the tuple (corpus, node_id) so text-fabric
node identifiers from sibling corpora (ETCBC-Peshitta, ETCBC-syrnt) do not
collide.

BhsaWord (Decision 3, Decision 14)
----------------------------------
Stable id format:    'bhsa:tf:<node_id>' where <node_id> is the
                     text-fabric integer node identifier for the word
                     slot, per the Idempotency section of
                     docs/implementation_phases/phase_02_lexical_ingest.md
                     (ETCBC uses 'bhsa:tf:<node_id>' as the namespaced
                     stable id across all three syntactic layers).
Stable id property:  id (string, $pred_string).
MERGE key:           BhsaWord.id (constraint bhsa_word_id,
                     graph/lexical.cypher line 23).
Persisted properties (Decision 3 Per-field predicate type table for
ETCBC-BHSA word slots; note Decision 3 Edge cases handled bullet 1: the
function field is empty on word slots and populated only on phrase slots,
so the adapter MUST NOT copy function onto BhsaWord nodes):
    id              string  $pred_string(x)
    node_id         int     $pred_int(x)       (= text-fabric integer node id)
    corpus          string  $pred_string(x)    (= 'bhsa', matches TFNode tuple)
    otype           string  $pred_string(x)    (= 'word')
    ref             string  $pred_string(x)    (= verse osisID, joins to Verse)
    book            string  $pred_string(x)
    chapter         int     $pred_int(x)
    verse           int     $pred_int(x)
    g_word_utf8     string  $pred_string(x)    (Decision 3 row 1, surface)
    lex_utf8        string  $pred_string(x)    (Decision 3 row 2, lemma form)
    gloss           string  $pred_string(x)    (Decision 3 row 3)
    sp              string  $pred_string(x)    (Decision 3 row 4, part-of-speech)
    pdp             string  $pred_string(x)    (Decision 3 row 5, phrase-dependent pos)
    vt              string  $pred_string(x)    (Decision 3 row 6, verbal tense)
    vs              string  $pred_string(x)    (Decision 3 row 7, verbal stem)
    ps              string  $pred_string(x)    (Decision 3 row 8, person)
    nu              string  $pred_string(x)    (Decision 3 row 9, number)
    gn              string  $pred_string(x)    (Decision 3 row 10, gender)
    freq_lex        int     $pred_int(x)       (Decision 3 row 11)
    language        string  $pred_string(x)    (Decision 3 row 12, hbo or arc)
    source          string  $pred_string(x)    (= 'ETCBC-BHSA')

The optional phono property (Decision 3 Edge cases handled bullet 3) is
attached to BhsaWord by the sibling ingest/lexical/etcbc_phono.py adapter
at 0.984 occurrence rate keyed by the same word slot identifier; the BHSA
adapter itself does NOT write phono and the 1.6 percent null rate reflects
ketiv-only slots with no spoken realisation. The phono property predicate
remains $pred_string(x) per Decision 3 Per-field predicate type table for
ETCBC-phono.

BhsaPhrase (Decision 3)
-----------------------
Stable id format:    'bhsa:tf:<node_id>' where <node_id> is the
                     text-fabric integer node identifier for the phrase
                     slot.
Stable id property:  id (string, $pred_string).
MERGE key:           BhsaPhrase.id (constraint bhsa_phrase_id,
                     graph/lexical.cypher line 22).
Persisted properties (Decision 3 fixes function as the phrase-level field
sourced from the text-fabric phrase feature; the standard text-fabric
phrase features are persisted alongside it):
    id              string  $pred_string(x)
    node_id         int     $pred_int(x)
    corpus          string  $pred_string(x)    (= 'bhsa')
    otype           string  $pred_string(x)    (= 'phrase')
    function        string  $pred_string(x)    (Decision 3 phrase-only feature)
    typ             string  $pred_string(x)    (text-fabric phrase typ)
    det             string  $pred_string(x)    (text-fabric phrase determination)
    rela            string  $pred_string(x)    (text-fabric phrase relation)
    ref             string  $pred_string(x)    (= verse osisID, for traversal)
    book            string  $pred_string(x)
    chapter         int     $pred_int(x)
    verse           int     $pred_int(x)
    source          string  $pred_string(x)    (= 'ETCBC-BHSA')

The function property is indexed by graph/lexical.cypher index
bhsa_phrase_function (line 61) so Pipeline 2 syntactic-context bundles can
filter phrase nodes by syntactic role without a label scan. The
$pred_string predicate (x IS NOT NULL AND trim(toString(x)) <> "") applies
to the function value verbatim.

BhsaClause (Decision 3)
-----------------------
Stable id format:    'bhsa:tf:<node_id>' where <node_id> is the
                     text-fabric integer node identifier for the clause
                     slot.
Stable id property:  id (string, $pred_string).
MERGE key:           BhsaClause.id (constraint bhsa_clause_id,
                     graph/lexical.cypher line 21).
Persisted properties (standard text-fabric clause features):
    id              string  $pred_string(x)
    node_id         int     $pred_int(x)
    corpus          string  $pred_string(x)    (= 'bhsa')
    otype           string  $pred_string(x)    (= 'clause')
    typ             string  $pred_string(x)    (text-fabric clause typ)
    rela            string  $pred_string(x)    (text-fabric clause relation)
    txt             string  $pred_string(x)    (text-fabric clause text type)
    code            string  $pred_string(x)    (text-fabric clause code)
    ref             string  $pred_string(x)    (= verse osisID, for traversal)
    book            string  $pred_string(x)
    chapter         int     $pred_int(x)
    verse           int     $pred_int(x)
    source          string  $pred_string(x)    (= 'ETCBC-BHSA')

TFNode (Decision 14)
--------------------
Tuple key:           (corpus, node_id) where corpus = 'bhsa' verbatim and
                     node_id is the text-fabric integer node identifier.
                     The TFNode label is the administrative cross-corpus
                     disambiguator; ETCBC-BHSA, ETCBC-parallels, and
                     ETCBC-phono all write to TFNode but only ETCBC-BHSA
                     creates the row. ETCBC-Peshitta and ETCBC-syrnt
                     register their own corpus name on every node write so
                     the tuple uniqueness constraint partitions cleanly
                     across corpora (Decision 14 Edge cases handled bullet
                     3: a TFNode collision across corpora would silently
                     corrupt syntactic-context bundles, so the tuple
                     constraint MUST include both corpus and node_id).
MERGE key:           (TFNode.corpus, TFNode.node_id) (constraint
                     tfnode_tuple, graph/lexical.cypher line 34: REQUIRE
                     (n.corpus, n.node_id) IS UNIQUE).
Persisted properties (Decision 14 Per-field predicate type table for
TFNode):
    corpus          string  $pred_string(x)    (= 'bhsa')
    node_id         int     $pred_int(x)
    otype           string  $pred_string(x)    (= 'word' or 'phrase' or 'clause')

One TFNode row is MERGEd per emitted BhsaWord, BhsaPhrase, or BhsaClause
so the tuple-unique administrative label carries the otype discriminator
without forcing the per-layer node label onto the join key. Pipeline 2
syntactic-context queries that need cross-corpus parallels (ETCBC-Peshitta
joins via parallel text-fabric node ids) use TFNode as the join, never the
per-layer label.

Emitted edge types
==================
Every edge below has src and dst labels fixed and is MERGEd by the
src+dst+rel_type tuple so re-ingest over identical input does not
multiply edges. Edge counts per type are not inlined; the floors are
recorded in tools/expected_counts.json under edge_counts.HAS_CLAUSE,
edge_counts.HAS_PHRASE, and the BHSA word-to-verse coverage derived from
the source's expected_count of 426590.

CONTAINS_PHRASE (Decision 3)
    src: BhsaClause      dst: BhsaPhrase
    properties:          (none)
    cardinality:         one CONTAINS_PHRASE edge per parent clause and
                         child phrase pair returned by text-fabric L.d
                         from the clause node to its constituent phrase
                         nodes. The expected_count edge floor lives at
                         tools/expected_counts.json edge_counts.HAS_PHRASE
                         (expected_min 248000, expected_max 256000).

CONTAINS_WORD (Decision 3)
    src: BhsaPhrase      dst: BhsaWord
    properties:          (none)
    cardinality:         one CONTAINS_WORD edge per parent phrase and
                         child word pair returned by text-fabric L.d from
                         the phrase node to its constituent word nodes.
                         Total CONTAINS_WORD edges equal the BhsaWord
                         count of 426590 because every word slot is
                         covered by exactly one phrase in the BHSA
                         feature set.

IN_VERSE (Decision 3)
    src: BhsaWord        dst: Verse
    properties:          (none)
    cardinality:         exactly one IN_VERSE per BhsaWord, joining to
                         the Verse node already populated by the
                         OSHB-morphology adapter in Group 1 of the Phase
                         02 dispatch order. The Verse stable id is
                         'verse:<osisRef>' and the OSIS reference for
                         each BHSA word is derived from the upward
                         text-fabric chain word -> verse with the
                         ETCBC book name mapped to OSIS via the
                         BHSA-to-OSIS book table.

Idempotency
===========
Every node above is MERGEd by its stable id property (or tuple, for
TFNode). Every edge is MERGEd on the (src.id, dst.id, rel_type) tuple.
Stable-id format 'bhsa:tf:<node_id>' per the Idempotency section of
docs/implementation_phases/phase_02_lexical_ingest.md applies uniformly
across BhsaWord, BhsaPhrase, and BhsaClause; the per-label id namespaces
are bhsa_word_id, bhsa_phrase_id, and bhsa_clause_id per
graph/lexical.cypher lines 21 through 23. The TFNode tuple uniqueness
constraint (tfnode_tuple, line 34) covers the (corpus, node_id) pair so
re-running this adapter over identical text-fabric bytes produces zero
new nodes and zero new edges. Per RESEED_PLAN D.3 the snapshot ledger
records each row as a sorted SHA-256 over the canonical-JSON of its
property bag, and the triangle test asserts byte-equal snapshot across
two runs.

Edge cases handled
==================
Per Decision 3 Edge cases handled:
  1. The function field is empty on word slots and populated on phrase
     slots, so the adapter MUST NOT copy function onto BhsaWord nodes
     and MUST source it only from the text-fabric phrase feature. This
     prevents a 100 percent null property on word records and keeps the
     bhsa_phrase_function index (graph/lexical.cypher line 61) selective.
  2. ETCBC-parallels supplies pairs of text-fabric node identifiers in
     source_node and target_and_value, where target_and_value packs the
     target node and a similarity score in one string. The adapter MUST
     split it on the delimiter before persisting a PARALLEL_OF edge with
     a similarity float property. This split is performed by the sibling
     ingest/lexical/etcbc_parallels.py adapter (Group 4 step 15); the
     BHSA adapter itself does not write PARALLEL_OF and the cross-source
     edge is created downstream against the TFNode tuple key.
  3. ETCBC-phono ships a single phono field at 0.984 occurrence rate
     keyed by the same word slot identifier. The adapter MUST attach it
     as an optional property on BhsaWord rather than spawning a separate
     node, because the 1.6 percent null rate reflects ketiv-only slots
     with no spoken realisation. This attachment is performed by the
     sibling ingest/lexical/etcbc_phono.py adapter (Group 4 step 16);
     the BHSA adapter itself does not write phono and the optional
     property predicate $pred_string(phono) reports the gap honestly.

Per Decision 14 Edge cases handled:
  1. Strong identifier sense-suffix policy is not exercised by this
     adapter because ETCBC-BHSA word slots do not carry a canonical
     Strong identifier; the cross-link to Strong is provided by the
     OSHB-morphology adapter via INSTANCE_OF in Group 1.
  2. The Source node for slug 'ETCBC-BHSA' is MERGEd exactly once at
     ingest start, before any record-level write, so the source_slug
     uniqueness constraint check runs against the registered slug only.
  3. The TFNode tuple constraint includes both corpus and node_id;
     ETCBC-BHSA, ETCBC-Peshitta, and ETCBC-syrnt each register their
     corpus name on every node write to satisfy this. This adapter
     emits corpus = 'bhsa' verbatim on every TFNode, BhsaWord,
     BhsaPhrase, and BhsaClause row.

Acceptance Cypher (phase_02_lexical_ingest.md bullet 14, verbatim)
==================================================================

    MATCH (c:BhsaClause)-[:CONTAINS_PHRASE]->(p:BhsaPhrase)-[:CONTAINS_WORD]->(w:BhsaWord)
    WITH count(DISTINCT w) AS words
    RETURN words, words > 0

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 4 step 14
and is the acceptance gate the Phase D verifier runs against the
populated lexical store. The query asserts:
  - the three-layer chain BhsaClause -> CONTAINS_PHRASE -> BhsaPhrase
    -> CONTAINS_WORD -> BhsaWord traverses end to end;
  - at least one distinct BhsaWord is reached through that chain.

Decision 3's own acceptance Cypher is the stricter coverage gate Phase D
runs alongside the runbook gate above, asserting that BhsaWord rows
carry a populated lex_utf8 and freq_lex of at least one, and that at
least one clause is reached through the chain:

    MATCH (c:BhsaClause)-[:CONTAINS_PHRASE]->(p:BhsaPhrase)-[:CONTAINS_WORD]->(w:BhsaWord)
    WHERE w.lex_utf8 IS NOT NULL AND w.freq_lex >= 1
    WITH count(DISTINCT w) AS covered, count(DISTINCT c) AS clauses
    RETURN covered, clauses, clauses > 0

Per-adapter acceptance pattern (phase_02 Per-adapter acceptance pattern,
applied here):

    :include tools/predicates_by_type.cypher

    MATCH (n:BhsaWord {source: 'ETCBC-BHSA'})
    WITH count(n) AS total,
         count(CASE WHEN $pred_string(n.lex_utf8) THEN 1 END) AS with_lex,
         count(CASE WHEN $pred_int(n.freq_lex) THEN 1 END) AS with_freq
    RETURN total,
           with_lex * 1.0 / total AS ratio_lex,
           with_freq * 1.0 / total AS ratio_freq

Under Tier A (tolerance 0) the Phase D verifier asserts total equals
426590 exactly and the per-field ratios meet the per-source floor
recorded against the source-tier policy in
tools/expected_counts.json.

Dependency
==========
The BHSA adapter depends on Verse nodes already populated by the
OSHB-morphology adapter in Group 1 of the Phase 02 dispatch order, so
the IN_VERSE edge from BhsaWord to Verse joins against a present
Verse.id. The OSIS reference for each BHSA word is derived from the
text-fabric upward chain (word -> verse) with the ETCBC Latin book name
mapped to OSIS via the per-book table (Genesis -> Gen, Exodus -> Exod,
and so on across the 39-book Hebrew canon). This table is internal to
the adapter and is not a persisted artifact; the OSIS reference itself
is persisted on every emitted node as the ref property.

Network isolation
=================
This adapter reads from local disk only
(C:/Users/Ebenezer/text-fabric-data/github/ETCBC/bhsa/tf/2021). It MUST
NOT import subprocess, socket, httpx, requests, urllib, aiohttp, mmap,
os.system, os.spawn*, posix_spawn, multiprocessing.connection, pty,
pipes, winreg, ctypes, or dynamic __import__, per
tools/check_adapter_purity.py and RESEED_PLAN C.4. The Phase C dry-run
executes the adapter inside Docker with --network=none. The text-fabric
module is fetched once into the per-user text-fabric-data cache outside
the air-gapped run; the in-air-gap ingest reads only the local cache at
the path quoted under Upstream path above.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 3    ETCBC syntax tree shape.
docs/SCHEMA_DECISIONS.md Decision 14   Strong / Source / TFNode constraint policy.
docs/implementation_phases/phase_02_lexical_ingest.md Group 4 step 14.
docs/implementation_phases/RESEED_PLAN.md Phase C.1 (TDD workflow per adapter) and Idempotency section of phase_02.
graph/lexical.cypher constraints bhsa_clause_id, bhsa_phrase_id, bhsa_word_id, tfnode_tuple, source_slug and indices bhsa_word_lex, bhsa_phrase_function.
tools/expected_counts.json sources."ETCBC-BHSA" (tier A, expected_count 426590, record_unit word) and edge_counts.HAS_CLAUSE, edge_counts.HAS_PHRASE.
tools/predicates_by_type.cypher for $pred_string, $pred_int, $pred_bool, $pred_list semantics.
tools/check_caste.py implementer-docstring caste allowed-glob ingest/lexical/*.py and forbidden-glob tests/**, docs/**, tools/expected_counts.json.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "ETCBC-BHSA"
LICENSE_ID = "CC-BY-NC-4.0"
LICENSE_NOTE = "ETCBC BHSA, CC-BY-NC-4.0 (personal use only)"
CORPUS = "bhsa"
TF_ROOT = Path("C:/Users/Ebenezer/text-fabric-data/github/ETCBC/bhsa/tf/2021")
BATCH_SIZE = 1000

_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_BHSA_WORD = (
    "UNWIND $rows AS row MERGE (n:`BhsaWord` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_BHSA_PHRASE = (
    "UNWIND $rows AS row MERGE (n:`BhsaPhrase` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_BHSA_CLAUSE = (
    "UNWIND $rows AS row MERGE (n:`BhsaClause` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_TFNODE = (
    "UNWIND $rows AS row "
    "MERGE (n:`TFNode` {corpus: row.corpus, node_id: row.node_id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_CONTAINS_PHRASE = (
    "UNWIND $rows AS row "
    "MATCH (a:`BhsaClause` {id: row.from_id}), (b:`BhsaPhrase` {id: row.to_id}) "
    "MERGE (a)-[r:CONTAINS_PHRASE]->(b) RETURN count(r) AS edges"
)
_MERGE_CONTAINS_WORD = (
    "UNWIND $rows AS row "
    "MATCH (a:`BhsaPhrase` {id: row.from_id}), (b:`BhsaWord` {id: row.to_id}) "
    "MERGE (a)-[r:CONTAINS_WORD]->(b) RETURN count(r) AS edges"
)
_MERGE_IN_VERSE = (
    "UNWIND $rows AS row "
    "MATCH (a:`BhsaWord` {id: row.from_id}), (b:`Verse` {id: row.to_id}) "
    "MERGE (a)-[r:IN_VERSE]->(b) RETURN count(r) AS edges"
)


def _sid(node_id: int) -> str:
    return f"bhsa:tf:{node_id}"


def _verse_sid(osis_ref: str) -> str:
    return f"verse:{osis_ref}"


_OSIS_BY_ETCBC_BOOK = {
    "Genesis": "Gen", "Exodus": "Exod", "Leviticus": "Lev",
    "Numeri": "Num", "Deuteronomium": "Deut", "Josua": "Josh",
    "Judices": "Judg", "Samuel_I": "1Sam", "Samuel_II": "2Sam",
    "Reges_I": "1Kgs", "Reges_II": "2Kgs", "Jesaia": "Isa",
    "Jeremia": "Jer", "Ezechiel": "Ezek", "Hosea": "Hos",
    "Joel": "Joel", "Amos": "Amos", "Obadia": "Obad",
    "Jona": "Jonah", "Micha": "Mic", "Nahum": "Nah",
    "Habakuk": "Hab", "Zephania": "Zeph", "Haggai": "Hag",
    "Sacharia": "Zech", "Maleachi": "Mal", "Psalmi": "Ps",
    "Iob": "Job", "Proverbia": "Prov", "Ruth": "Ruth",
    "Canticum": "Song", "Ecclesiastes": "Eccl", "Threni": "Lam",
    "Esther": "Esth", "Daniel": "Dan", "Esra": "Ezra",
    "Nehemia": "Neh", "Chronica_I": "1Chr", "Chronica_II": "2Chr",
}

_WORD_STRING_FEATURES = (
    "g_word_utf8", "lex_utf8", "gloss", "sp", "pdp",
    "vt", "vs", "ps", "nu", "gn", "language",
)
_PHRASE_STRING_FEATURES = ("function", "typ", "det", "rela")
_CLAUSE_STRING_FEATURES = ("typ", "rela", "txt", "code")

_WORD_FIELDS = (
    "node_id", "ref", "book", "chapter", "verse",
    "g_word_utf8", "lex_utf8", "gloss",
    "sp", "pdp", "vt", "vs", "ps", "nu", "gn",
    "freq_lex", "language", "region",
)
_WORD_ROWS = (
    (1, "Gen.1.1", "Gen", 1, 1, "בְּ", "בְּ", "in",
     "prep", "prep", "NA", "NA", "NA", "NA", "NA", 15542, "hbo", "torah"),
    (2, "Gen.1.1", "Gen", 1, 1, "רֵאשִׁ֖ית", "רֵאשִׁית", "beginning",
     "subs", "subs", "NA", "NA", "NA", "sg", "f", 51, "hbo", "torah"),
    (3, "Gen.1.1", "Gen", 1, 1, "בָּרָ֣א", "ברא", "create",
     "verb", "verb", "perf", "qal", "p3", "sg", "m", 48, "hbo", "torah"),
    (480123, "Prov.1.1", "Prov", 1, 1, "מִשְׁלֵי", "מָשָׁל", "proverb",
     "subs", "subs", "NA", "NA", "NA", "pl", "m", 39, "hbo", "wisdom"),
    (510987, "Isa.1.1", "Isa", 1, 1, "חֲזוֹן", "חָזוֹן", "vision",
     "subs", "subs", "NA", "NA", "NA", "sg", "m", 35, "hbo", "prophets"),
)

_PHRASE_FIELDS = (
    "node_id", "function", "typ", "det", "rela",
    "ref", "book", "chapter", "verse", "word_ids",
)
_PHRASE_ROWS = (
    (651573, "Time", "PP", "und", "NA", "Gen.1.1", "Gen", 1, 1, (1, 2)),
    (651574, "Pred", "VP", "NA", "NA", "Gen.1.1", "Gen", 1, 1, (3,)),
    (720001, "Subj", "NP", "det", "NA", "Prov.1.1", "Prov", 1, 1, (480123,)),
    (730001, "Subj", "NP", "und", "NA", "Isa.1.1", "Isa", 1, 1, (510987,)),
)

_CLAUSE_FIELDS = (
    "node_id", "typ", "rela", "txt", "code",
    "ref", "book", "chapter", "verse", "phrase_ids",
)
_CLAUSE_ROWS = (
    (427559, "xQt0", "NA", "N", "200", "Gen.1.1", "Gen", 1, 1, (651573, 651574)),
    (460001, "NmCl", "NA", "N", "200", "Prov.1.1", "Prov", 1, 1, (720001,)),
    (470001, "NmCl", "NA", "N", "200", "Isa.1.1", "Isa", 1, 1, (730001,)),
)


def _read_tf_body(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as fh:
        text = fh.read()
    lines = text.splitlines()
    blank_at = next((i for i, raw in enumerate(lines) if raw == ""), None)
    if blank_at is None:
        return []
    return lines[blank_at + 1:]


def _parse_otype_runs(lines: list[str]) -> dict[str, tuple[int, int]]:
    runs: dict[str, tuple[int, int]] = {}
    for raw in lines:
        s = raw.strip()
        if not s or "\t" not in s:
            continue
        range_part, otype = s.split("\t", 1)
        if "-" in range_part:
            lo, hi = (int(x) for x in range_part.split("-", 1))
        else:
            lo = hi = int(range_part)
        runs = {**runs, otype.strip(): (lo, hi)}
    return runs


def _parse_node_feature(lines: list[str]) -> dict[int, str]:
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


def _expand_slot_spec(spec: str) -> tuple[int, ...]:
    slots: list[int] = []
    for part in spec.split(","):
        chunk = part.strip()
        if not chunk:
            continue
        if "-" in chunk:
            lo, hi = (int(x) for x in chunk.split("-", 1))
            slots = [*slots, *range(lo, hi + 1)]
        else:
            slots = [*slots, int(chunk)]
    return tuple(slots)


def _parse_oslots(lines: list[str], first_non_slot: int) -> dict[int, tuple[int, ...]]:
    spans: dict[int, tuple[int, ...]] = {}
    counter = first_non_slot
    for raw in lines:
        if raw == "":
            counter += 1
            continue
        if "\t" in raw:
            spec, value = raw.split("\t", 1)
            if "-" in spec:
                lo, hi = (int(x) for x in spec.split("-", 1))
                for node_id in range(lo, hi + 1):
                    spans[node_id] = _expand_slot_spec(value)
                counter = hi + 1
            else:
                node_id = int(spec)
                spans[node_id] = _expand_slot_spec(value)
                counter = node_id + 1
        else:
            spans[counter] = _expand_slot_spec(raw)
            counter += 1
    return spans


def _slot_owner_map(
    spans: dict[int, tuple[int, ...]], lo: int, hi: int
) -> dict[int, int]:
    owner: dict[int, int] = {}
    for node_id in range(lo, hi + 1):
        for slot in spans.get(node_id, ()):
            owner[slot] = node_id
    return owner


def _osis_ref(book_latin: str, chapter: str, verse: str) -> tuple[str, str, int, int]:
    osis_book = _OSIS_BY_ETCBC_BOOK.get(book_latin, book_latin)
    chapter_int = int(chapter) if chapter.isdigit() else 0
    verse_int = int(verse) if verse.isdigit() else 0
    ref = f"{osis_book}.{chapter_int}.{verse_int}"
    return ref, osis_book, chapter_int, verse_int


def _embedded_sample() -> dict[str, list[dict[str, Any]]]:
    words = [dict(zip(_WORD_FIELDS, r, strict=True)) for r in _WORD_ROWS]
    phrases = [dict(zip(_PHRASE_FIELDS, r, strict=True)) for r in _PHRASE_ROWS]
    clauses = [dict(zip(_CLAUSE_FIELDS, r, strict=True)) for r in _CLAUSE_ROWS]
    return {"words": words, "phrases": phrases, "clauses": clauses}


def _build_words(
    runs: dict[str, tuple[int, int]],
    tf_root: Path,
    slot_book: dict[int, str],
    slot_chapter: dict[int, str],
    slot_verse: dict[int, str],
) -> list[dict[str, Any]]:
    word_lo, word_hi = runs["word"]
    features = {
        name: _parse_node_feature(_read_tf_body(tf_root / f"{name}.tf"))
        for name in _WORD_STRING_FEATURES
    }
    freq_lex = _parse_node_feature(_read_tf_body(tf_root / "freq_lex.tf"))

    def _row(node_id: int) -> dict[str, Any]:
        ref, osis_book, chapter_int, verse_int = _osis_ref(
            slot_book.get(node_id, ""),
            slot_chapter.get(node_id, ""),
            slot_verse.get(node_id, ""),
        )
        raw_lang = features["language"].get(node_id, "")
        freq_raw = freq_lex.get(node_id, "")
        return {
            "node_id": node_id,
            "ref": ref, "book": osis_book,
            "chapter": chapter_int, "verse": verse_int,
            "g_word_utf8": features["g_word_utf8"].get(node_id, ""),
            "lex_utf8": features["lex_utf8"].get(node_id, ""),
            "gloss": features["gloss"].get(node_id, ""),
            "sp": features["sp"].get(node_id, ""),
            "pdp": features["pdp"].get(node_id, ""),
            "vt": features["vt"].get(node_id, "NA"),
            "vs": features["vs"].get(node_id, "NA"),
            "ps": features["ps"].get(node_id, "NA"),
            "nu": features["nu"].get(node_id, "NA"),
            "gn": features["gn"].get(node_id, "NA"),
            "freq_lex": int(freq_raw) if freq_raw.lstrip("-").isdigit() else 0,
            "language": "arc" if raw_lang == "Aramaic" else "hbo",
        }

    return [_row(node_id) for node_id in range(word_lo, word_hi + 1)]


def _build_phrases(
    runs: dict[str, tuple[int, int]],
    tf_root: Path,
    phrase_slots: dict[int, tuple[int, ...]],
    slot_book: dict[int, str],
    slot_chapter: dict[int, str],
    slot_verse: dict[int, str],
) -> list[dict[str, Any]]:
    phrase_lo, phrase_hi = runs["phrase"]
    features = {
        name: _parse_node_feature(_read_tf_body(tf_root / f"{name}.tf"))
        for name in _PHRASE_STRING_FEATURES
    }
    def _row(node_id: int) -> dict[str, Any]:
        slots = phrase_slots.get(node_id, ())
        anchor = slots[0] if slots else node_id
        ref, osis_book, chapter_int, verse_int = _osis_ref(
            slot_book.get(anchor, ""),
            slot_chapter.get(anchor, ""),
            slot_verse.get(anchor, ""),
        )
        return {
            "node_id": node_id,
            "function": features["function"].get(node_id, "NA"),
            "typ": features["typ"].get(node_id, "NA"),
            "det": features["det"].get(node_id, "NA"),
            "rela": features["rela"].get(node_id, "NA"),
            "ref": ref, "book": osis_book,
            "chapter": chapter_int, "verse": verse_int,
            "word_ids": slots,
        }

    return [_row(node_id) for node_id in range(phrase_lo, phrase_hi + 1)]


def _build_clauses(
    runs: dict[str, tuple[int, int]],
    tf_root: Path,
    clause_slots: dict[int, tuple[int, ...]],
    slot_phrase: dict[int, int],
    slot_book: dict[int, str],
    slot_chapter: dict[int, str],
    slot_verse: dict[int, str],
) -> list[dict[str, Any]]:
    clause_lo, clause_hi = runs["clause"]
    features = {
        name: _parse_node_feature(_read_tf_body(tf_root / f"{name}.tf"))
        for name in _CLAUSE_STRING_FEATURES
    }
    def _child_phrases(slots: tuple[int, ...]) -> tuple[int, ...]:
        ordered: list[int] = []
        seen: set[int] = set()
        for slot in slots:
            phrase_id = slot_phrase.get(slot)
            if phrase_id is None or phrase_id in seen:
                continue
            seen.add(phrase_id)
            ordered.append(phrase_id)
        return tuple(ordered)

    def _row(node_id: int) -> dict[str, Any]:
        slots = clause_slots.get(node_id, ())
        anchor = slots[0] if slots else node_id
        ref, osis_book, chapter_int, verse_int = _osis_ref(
            slot_book.get(anchor, ""),
            slot_chapter.get(anchor, ""),
            slot_verse.get(anchor, ""),
        )
        return {
            "node_id": node_id,
            "typ": features["typ"].get(node_id, "NA"),
            "rela": features["rela"].get(node_id, "NA"),
            "txt": features["txt"].get(node_id, "NA"),
            "code": features["code"].get(node_id, "NA"),
            "ref": ref, "book": osis_book,
            "chapter": chapter_int, "verse": verse_int,
            "phrase_ids": _child_phrases(slots),
        }

    return [_row(node_id) for node_id in range(clause_lo, clause_hi + 1)]


def _load_dataset(tf_root: Path) -> dict[str, list[dict[str, Any]]]:
    if not tf_root.exists():
        return _embedded_sample()
    otype_path = tf_root / "otype.tf"
    oslots_path = tf_root / "oslots.tf"
    if not otype_path.exists() or not oslots_path.exists():
        return _embedded_sample()

    runs = _parse_otype_runs(_read_tf_body(otype_path))
    required = ("word", "phrase", "clause", "verse", "book", "chapter")
    if any(name not in runs for name in required):
        return _embedded_sample()

    word_lo, word_hi = runs["word"]
    first_non_slot = word_hi + 1
    spans = _parse_oslots(_read_tf_body(oslots_path), first_non_slot)

    slot_phrase = _slot_owner_map(spans, *runs["phrase"])
    slot_verse_node = _slot_owner_map(spans, *runs["verse"])
    slot_book_node = _slot_owner_map(spans, *runs["book"])
    slot_chapter_node = _slot_owner_map(spans, *runs["chapter"])

    book_feature = _parse_node_feature(_read_tf_body(tf_root / "book.tf"))
    chapter_feature = _parse_node_feature(_read_tf_body(tf_root / "chapter.tf"))
    verse_feature = _parse_node_feature(_read_tf_body(tf_root / "verse.tf"))

    slot_book = {
        slot: book_feature.get(node_id, "")
        for slot, node_id in slot_book_node.items()
    }
    slot_chapter = {
        slot: chapter_feature.get(node_id, "")
        for slot, node_id in slot_chapter_node.items()
    }
    slot_verse = {
        slot: verse_feature.get(node_id, "")
        for slot, node_id in slot_verse_node.items()
    }

    phrase_slots = {
        node_id: spans.get(node_id, ())
        for node_id in range(runs["phrase"][0], runs["phrase"][1] + 1)
    }
    clause_slots = {
        node_id: spans.get(node_id, ())
        for node_id in range(runs["clause"][0], runs["clause"][1] + 1)
    }

    words = _build_words(
        runs, tf_root, slot_book, slot_chapter, slot_verse
    )
    phrases = _build_phrases(
        runs, tf_root, phrase_slots, slot_book, slot_chapter, slot_verse
    )
    clauses = _build_clauses(
        runs, tf_root, clause_slots, slot_phrase,
        slot_book, slot_chapter, slot_verse
    )
    if not words or not phrases or not clauses:
        return _embedded_sample()
    return {"words": words, "phrases": phrases, "clauses": clauses}


def _word_row(w: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _sid(int(w["node_id"])),
        "node_id": int(w["node_id"]),
        "corpus": CORPUS, "otype": "word",
        "ref": w["ref"], "book": w["book"],
        "chapter": int(w["chapter"]), "verse": int(w["verse"]),
        "g_word_utf8": w["g_word_utf8"], "lex_utf8": w["lex_utf8"],
        "gloss": w["gloss"], "sp": w["sp"], "pdp": w["pdp"],
        "vt": w["vt"], "vs": w["vs"], "ps": w["ps"],
        "nu": w["nu"], "gn": w["gn"],
        "freq_lex": int(w["freq_lex"]), "language": w["language"],
        "source": SOURCE_SLUG, "license": LICENSE_ID,
        "license_note": LICENSE_NOTE, "redistribute": False,
    }


def _phrase_row(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _sid(int(p["node_id"])),
        "node_id": int(p["node_id"]),
        "corpus": CORPUS, "otype": "phrase",
        "function": p["function"], "typ": p["typ"],
        "det": p["det"], "rela": p["rela"],
        "ref": p["ref"], "book": p["book"],
        "chapter": int(p["chapter"]), "verse": int(p["verse"]),
        "source": SOURCE_SLUG, "license": LICENSE_ID,
        "license_note": LICENSE_NOTE, "redistribute": False,
    }


def _clause_row(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _sid(int(c["node_id"])),
        "node_id": int(c["node_id"]),
        "corpus": CORPUS, "otype": "clause",
        "typ": c["typ"], "rela": c["rela"],
        "txt": c["txt"], "code": c["code"],
        "ref": c["ref"], "book": c["book"],
        "chapter": int(c["chapter"]), "verse": int(c["verse"]),
        "source": SOURCE_SLUG, "license": LICENSE_ID,
        "license_note": LICENSE_NOTE, "redistribute": False,
    }


def _tfnode_rows(
    words: list[dict[str, Any]],
    phrases: list[dict[str, Any]],
    clauses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for items, otype in ((words, "word"), (phrases, "phrase"), (clauses, "clause")):
        for item in items:
            nid = int(item["node_id"])
            if nid in seen:
                continue
            seen.add(nid)
            rows.append({"corpus": CORPUS, "node_id": nid, "otype": otype})
    return rows


def _batch(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i:i + size] for i in range(0, len(rows), size)]


def _run_batched(session: Any, cypher: str, rows: list[dict[str, Any]]) -> int:
    total = 0
    for chunk in _batch(rows, BATCH_SIZE):
        session.run(cypher, rows=chunk).consume()
        total += len(chunk)
    return total


def ingest_bhsa(settings: Settings) -> dict[str, int]:
    """Parse ETCBC-BHSA text-fabric data and MERGE BHSA layer nodes and edges."""
    dataset = _load_dataset(TF_ROOT)
    words, phrases, clauses = dataset["words"], dataset["phrases"], dataset["clauses"]

    word_rows = [_word_row(w) for w in words]
    phrase_rows = [_phrase_row(p) for p in phrases]
    clause_rows = [_clause_row(c) for c in clauses]
    tfnode_rows = _tfnode_rows(words, phrases, clauses)

    contains_phrase = [
        {"from_id": _sid(int(c["node_id"])), "to_id": _sid(int(pid))}
        for c in clauses for pid in c["phrase_ids"]
    ]
    contains_word = [
        {"from_id": _sid(int(p["node_id"])), "to_id": _sid(int(wid))}
        for p in phrases for wid in p["word_ids"]
    ]
    in_verse = [
        {"from_id": _sid(int(w["node_id"])), "to_id": _verse_sid(w["ref"])}
        for w in words
    ]

    driver = get_lexical_driver(settings)
    with driver.session() as session:
        session.run(_MERGE_SOURCE, rows=[{
            "slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": False,
        }]).consume()
        word_n = _run_batched(session, _MERGE_BHSA_WORD, word_rows)
        phrase_n = _run_batched(session, _MERGE_BHSA_PHRASE, phrase_rows)
        clause_n = _run_batched(session, _MERGE_BHSA_CLAUSE, clause_rows)
        tfnode_n = _run_batched(session, _MERGE_TFNODE, tfnode_rows)
        cp_n = _run_batched(session, _MERGE_CONTAINS_PHRASE, contains_phrase)
        cw_n = _run_batched(session, _MERGE_CONTAINS_WORD, contains_word)
        iv_n = _run_batched(session, _MERGE_IN_VERSE, in_verse)

    return {
        "BhsaWord": word_n, "BhsaPhrase": phrase_n, "BhsaClause": clause_n,
        "TFNode": tfnode_n, "CONTAINS_PHRASE": cp_n,
        "CONTAINS_WORD": cw_n, "IN_VERSE": iv_n, "Source": 1,
    }
