"""Vulgate Clementine adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the Vulgate Clementine adapter for the Pipeline 1 lexical
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
Source slug:      vulgate-clementine
Tier:             C (procurement, tolerance plus or minus 5 percent)
Expected count:   null (record_unit: vulgate_verse). The expected verse
                  record count is unknown at procurement time and is locked
                  into a follow-on baseline commit at first ingest. The
                  upstream byte count is the only signal at procurement
                  time because Wikisource Special:Export does not publish a
                  manifest of verse cardinality.
Tier rationale:   Network procurement against Wikisource Special:Export.
                  Upstream byte count is the only signal at procurement
                  time, so the verse record count is established at first
                  ingest run and locked into a follow-on baseline commit.
                  Tier C tolerance is plus or minus 5 percent per
                  tools/expected_counts.json.
Decisions implemented: 8.

Upstream and license
====================
Procurement entry: vulgate-clementine (Wikisource Special:Export bundle of
                   the Clementine Vulgate, covering the full canon).
Upstream path:     data/private/vulgate/ (pre-fetched local cache; no
                   network access during ingest).
License id:        public_domain. The Clementine Vulgate text was first
                   promulgated in 1592 and is in the public domain in every
                   jurisdiction the project ships to. The redistribute flag
                   on the Source node is true per Decision 14 because
                   public-domain text carries no redistribution restriction.
Source record:     The Source node for slug 'vulgate-clementine' is MERGEd
                   once per ingest run with properties:
                     slug          = 'vulgate-clementine'  ($pred_string)
                     license       = 'public_domain'       ($pred_string)
                     redistribute  = true                  ($pred_bool)
                   per Decision 14 Source uniqueness constraint
                   (source_slug constraint, graph/lexical.cypher line 35).
Citation slug:     'vulgate-clementine'. This slug was amended into both
                   docs/phase_prompts/pipeline2_verdict.md (citation slug
                   table) and docs/LICENSE_TAGGING.md (license slug table)
                   during Phase A.2 per Decision 8. Pipeline 2 evidence
                   files tag any Clementine citation with this slug only.

Emitted node labels and properties
==================================
The adapter MERGEs one record-level node label (VulgateVerse) plus the
ingest-level Source node listed above. Each row below quotes its persisted
property name, the primitive type the value carries, and the matching
predicate from tools/predicates_by_type.cypher. The upstream is
verse-granular only, so no word-level tokenisation, lemma, morph, or
strong attachment is in scope for this adapter.

VulgateVerse (Decision 8)
-------------------------
Stable id format:    'vulgate-clementine:<osis>' where <osis> is the
                     canonical OSIS verse reference produced by projecting
                     the Wikisource Clementine reference through the
                     STEPBible-TVTMS rule set (see Edge cases handled
                     bullet 1 below). The constraint vulgate_verse_osis at
                     graph/lexical.cypher line 45 REQUIRES v.osis IS
                     UNIQUE, so the stable id namespace is keyed on the
                     osis property directly. The 'vulgate-clementine:'
                     prefix is the slug-namespaced form used by Pipeline 2
                     evidence files when they cite the verse by stable id.
Stable id property:  osis (string, $pred_string).
MERGE key:           VulgateVerse.osis (constraint vulgate_verse_osis,
                     graph/lexical.cypher line 45).
Persisted properties (Decision 8 Per-field predicate type table for the
VulgateVerse node):
    osis                  string  $pred_string(x)
    text_latin            string  $pred_string(x)   (Clementine surface,
                                                     byte-identical to
                                                     Wikisource Special:Export
                                                     after transcription
                                                     footnote stripping)
    canon                 string  $pred_string(x)   ('protocanonical' for
                                                     books in the
                                                     protestant canon
                                                     intersection; 'deutero'
                                                     for the Clementine
                                                     deuterocanonical books;
                                                     see Edge cases handled
                                                     bullet 2)
    notes                 string  $pred_string(x)   (chapter rubrics and
                                                     other paratextual
                                                     annotation extracted
                                                     from the Wikisource
                                                     source; nullable when
                                                     the verse carries no
                                                     rubric and $pred_string
                                                     returns false in that
                                                     case)
    transcription_notes   list    $pred_list(x)     (Wikisource transcription
                                                     footnote markers
                                                     stripped from
                                                     text_latin and
                                                     preserved here as an
                                                     ordered list of strings;
                                                     see Edge cases handled
                                                     bullet 3)
    source                string  $pred_string(x)   (= 'vulgate-clementine')

Source (Decision 14, registered once at ingest start)
-----------------------------------------------------
Stable id format:    'vulgate-clementine' (verbatim source slug).
Stable id property:  slug (string, $pred_string).
MERGE key:           Source.slug (constraint source_slug,
                     graph/lexical.cypher line 35).
Persisted properties (Decision 14 Per-field predicate type table):
    slug            string  $pred_string(x)
    license         string  $pred_string(x)   (= 'public_domain')
    redistribute    bool    $pred_bool(x)     (= true per Decision 14)

Emitted edge types
==================
No edges. The Clementine is verse-granular only because the Wikisource
Special:Export bundle does not carry per-word tokenisation, lemma, morph,
or Strong identifiers. The adapter MUST NOT emit IN_VERSE, INSTANCE_OF,
HAS_MORPHEME, FROM_EDITION, CROSS_REF, or any other edge from VulgateVerse
to any node in the lexical store. Pipeline 2 reads the surface text_latin
directly off the VulgateVerse node by osis lookup; no traversal is
required to render the verse.

Idempotency
===========
The VulgateVerse node is MERGEd by its osis property. Re-running this
adapter over identical Wikisource Special:Export bytes produces zero new
nodes and zero new edges; Decision 14 uniqueness on Source.slug plus the
Decision 8 uniqueness on VulgateVerse.osis (constraint vulgate_verse_osis)
additionally enforce this at the Neo4j storage layer. Per RESEED_PLAN D.3
the snapshot ledger records each row as a sorted SHA-256 over the
canonical-JSON of its property bag, and the triangle test asserts
byte-equal snapshot across two runs. Because transcription_notes is
extracted to a separate list-typed property (Edge cases handled bullet 3),
the hash of text_latin is stable across Wikisource transcription footnote
re-formatting that does not change the canonical surface.

Edge cases handled
==================
Per Decision 8 Edge cases handled:
  1. The Clementine Vulgate numbering differs from the modern critical
     Vulgate in several places, most notably the Psalms numbering offset
     where Clementine Ps 9 covers the modern Ps 9 plus Ps 10. The adapter
     MUST apply the STEPBible-TVTMS rule set (see Group 2 dependency
     below) to project Clementine verse identifiers to the OSIS reference
     space before assigning VulgateVerse.osis. Rows the TVTMS mapping
     cannot resolve MUST be tagged with a quarantine flag in the snapshot
     ledger rather than silently dropped, so the triangle test surfaces
     unresolved mappings on re-ingest.
  2. Deuterocanonical books (Tobit, Judith, 1 and 2 Maccabees, Wisdom,
     Sirach, Baruch, plus the Greek additions to Esther and Daniel) are
     part of the Clementine canon and MUST be ingested with their
     canonical OSIS identifiers. The adapter records a canon = 'deutero'
     property on those VulgateVerse nodes so Pipeline 2 can filter them
     when the question's canon scope excludes them. Protocanonical books
     are tagged canon = 'protocanonical' so the filter remains a positive
     selector rather than a negative one.
  3. Wikisource markup occasionally contains transcription footnote
     markers (e.g. editorial superscripts marking a manuscript variant or
     a transcription apparatus note) embedded inside the text body. The
     adapter MUST strip these to a separate transcription_notes list
     property rather than leaving them embedded in text_latin. This
     preserves the surface form for hashing without losing the apparatus.
     The stripping is byte-exact: the original character offsets of the
     footnote markers and their content are recorded as ordered list
     entries so the apparatus can be reconstructed from
     (text_latin, transcription_notes) without the original Wikisource
     XML.

Acceptance Cypher (phase_02_lexical_ingest.md bullet 21, verbatim)
==================================================================

    MATCH (v:VulgateVerse)
    WHERE v.text_latin IS NOT NULL AND v.osis IS NOT NULL
    WITH count(v) AS verses
    RETURN verses, verses > 0

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 6 step 21 and
is the acceptance gate the Phase D verifier runs against the populated
lexical store. The query asserts that at least one VulgateVerse node
exists with both osis and text_latin populated.

Decision 8's own acceptance Cypher carries a tighter verse-count floor of
30000 (full Clementine canon including deuterocanonicals is roughly 35000
verses), reproduced here for cross-reference:

    MATCH (v:VulgateVerse)
    WHERE v.text_latin IS NOT NULL AND v.osis IS NOT NULL
    WITH count(v) AS verses
    RETURN verses, verses >= 30000

The Phase D verifier runs both queries: the bullet-21 floor (verses > 0)
gates ingest sanity, and the Decision 8 floor (verses >= 30000) gates
canon completeness. The expected_count in tools/expected_counts.json is
null at A.4 freeze and will be locked into a follow-on baseline commit at
first ingest, after which the Tier C plus or minus 5 percent tolerance
applies against that locked count.

Procurement and network isolation
=================================
The Wikisource Special:Export bundle is fetched once into
data/private/vulgate/ outside the air-gapped run. The in-air-gap ingest
reads only the local cache, never the network. This adapter MUST NOT
import subprocess, socket, httpx, requests, urllib, aiohttp, mmap,
os.system, os.spawn*, posix_spawn, multiprocessing.connection, pty,
pipes, winreg, ctypes, or dynamic __import__, per
tools/check_adapter_purity.py and RESEED_PLAN C.4. The Phase C dry-run
executes the adapter inside Docker with --network=none. Procurement
itself is documented in docs/data_inventory_catalog.json under the
procurement entry vulgate-clementine and is performed outside this
adapter's call path.

Dependencies
============
This adapter depends on the STEPBible-TVTMS rule set from Group 2 of the
Phase 02 dispatch order (bullet 7,
ingest/lexical/stepbible_tvtms.py). TVTMS provides the versification
rules required to project Clementine verse identifiers to the OSIS
reference space adopted by MACULA. The adapter MUST NOT run before
TVTMS has populated the VersificationRule nodes, because the
Clementine-to-OSIS verse map relies on the TVTMS rule_type column
(Decision 5 Per-field predicate type table) to resolve the Psalms
numbering offset and other Clementine-specific divergences. No other
upstream dependency exists; the Verse nodes from Group 1 are NOT
required because VulgateVerse is a parallel node label keyed on osis
without any FK relationship to the canonical Verse label.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 8   Vulgate Clementine integration.
docs/SCHEMA_DECISIONS.md Decision 14  Strong / Source / TFNode constraint policy (Source slug, license, redistribute).
docs/implementation_phases/phase_02_lexical_ingest.md Group 6 step 21.
docs/implementation_phases/RESEED_PLAN.md Phase C.1 (TDD workflow per adapter) and Idempotency section of phase_02.
docs/phase_prompts/pipeline2_verdict.md citation slug 'vulgate-clementine' (amended in Phase A.2).
docs/LICENSE_TAGGING.md license slug 'public_domain' for source slug 'vulgate-clementine' (amended in Phase A.2).
graph/lexical.cypher constraint vulgate_verse_osis (line 45) and source_slug (line 35).
tools/expected_counts.json sources."vulgate-clementine" (tier C, record_unit vulgate_verse, expected_count null, tolerance_relative 0.05).
tools/predicates_by_type.cypher for $pred_string, $pred_bool, $pred_list semantics.
"""
