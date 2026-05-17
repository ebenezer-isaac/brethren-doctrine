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
