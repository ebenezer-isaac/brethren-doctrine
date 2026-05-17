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
"""
