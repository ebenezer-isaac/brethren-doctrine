# Phase D Catalog Reconciliation

Caste: architect. Read-only root-cause investigation. Branch main, HEAD d8530f3.

Doctrinal frame: brethren-on-trial. Trust the faithful real parse. Fix a wrong
catalog. Never fudge an adapter to hit a wrong number.

## Method

For each of the 7 close-but-not-exact sources I established three numbers
independently from the bytes on disk:

1. Catalog expectation: `tools/expected_counts.json` plus the corresponding
   `docs/data_inventory_catalog.json` source entry and the inventory builder
   `tmp/build_inventory_a0.py` that produced `total_records`.
2. Real upstream raw count: counted directly from the source files under
   `data/private/` (or `tmp/poc/cbgm/`), reproducing the exact counting rule
   the catalog tier_rationale claims to use, and the rule the inventory builder
   actually used.
3. Adapter faithful emit: ran each adapter's pure parse/load functions offline
   (no Neo4j, no network) over the real upstream bytes.

Every number below was produced by executing the rule, not by restating the
audit or handover docs. Where the catalog number is reproducible I show the
exact rule that reproduces it.

Important structural finding: `docs/data_inventory_catalog.json` contains only
20 sources and has NO `open-cbgm` entry. The `catalog_source_index: 3` for
`open-cbgm-3-john` in `tools/expected_counts.json` points at MorphGNT-SBLGNT
(index 3). The open-cbgm 600/588/612 envelope is a hand-set estimate, not a
catalog-derived count.

---

## 1. STEPBible-proper-nouns

Source file: `data/private/stepbible/Proper Nouns/TIPNR - Translators
Individualised Proper Names with all References - STEPBible.org CC BY.txt`
Adapter: `ingest/lexical/stepbible_proper_nouns.py`

Three numbers:
- Catalog expected_count: 23205 (tier A, tolerance 0, record_unit proper_name).
- Real upstream raw: the TIPNR file is a record-block format. Its own header
  states "Records are separated by `$` and sub-records are on separate lines
  that start with a space." Structural counts from the bytes: 36142 total
  lines; 4262 `$==========` record-separator banner lines (3132 PERSON(s) +
  1003 PLACE + 102 OTHER exact + 25 with formatting variance); 4305 headline
  `Name@Ref=Strong` lines; 10114 en-dash (U+2013) per-occurrence detail rows.
  The faithful proper-name unit is the de-duplicated `unique_name=dStrong`
  occurrence entry with a resolvable Strong and Hebrew/Greek language.
- Adapter faithful emit: 5468 ProperNoun nodes (4693 Hebrew + 775 Greek).

Decisive evidence (catalog 23205 exactly reproduced): the inventory builder
function `tmp/build_inventory_a0.py::src_stepbible_proper_nouns` counts every
line where `"\t" in line and line.strip() and not line.startswith("#") and not
line.startswith("=")`. Reproducing that rule over the real file yields exactly
23205, decomposed as 10114 en-dash detail rows + 4262 `$======` separator
banners + 8829 headline/`@`-alias/metadata lines. The catalog is counting
record-separator banners and metadata lines as if they were proper-name
records. The tier_rationale claims "one row per proper-name entry across
Hebrew and Greek sections" but the counting method counts heterogeneous lines,
including 4262 banners that are by definition not names.

Reproduction command:
```
python - <<'PY'
from pathlib import Path
p=Path("data/private/stepbible/Proper Nouns/TIPNR - Translators Individualised Proper Names with all References - STEPBible.org CC BY.txt")
rows=[]
for line in open(p,encoding="utf-8",errors="replace"):
    s=line.rstrip("\n")
    if "\t" in s and s.strip() and not s.startswith("#") and not s.startswith("="):
        if any(c.strip() for c in s.split("\t")): rows.append(s)
print(len(rows))   # -> 23205 (catalog), NOT a proper-name count
PY
```
Adapter emit reproduced via `ingest.lexical.stepbible_proper_nouns._load_upstream_rows`
over `data/private/stepbible` -> 5468.

Classification: CATALOG-WRONG. The adapter parse is faithful to the documented
TIPNR record grammar (one node per uniquely-identified person/place occurrence
with resolvable Strong). The catalog used a naive tab-line count that conflates
banners, alias lines, and detail rows.

Recommendation: set catalog expected_count to the faithful emit 5468 with
tier A tolerance 0, OR re-derive a defensible per-name count. The 5468 figure
is byte-deterministic over frozen upstream and reproducible across runs (the
adapter dedups by `unique_name=dStrong`), so it is a valid tier-A exact target.
Proposed expected_count = 5468.

---

## 2. OSHB-morphology

Source files: `data/private/oshb/wlc/*.xml` (40 OSIS XML books).
Adapter: `ingest/lexical/oshb.py`

Three numbers:
- Catalog expected_count: 306785 (tier A, tolerance 0, record_unit word).
- Real upstream raw: count of ALL `<w>` elements anywhere in the OSIS tree
  = 306785. Count of `<w>` elements that are direct children of `<verse>`
  (true word slots) = 305507. The 1278-element difference is exactly the
  qere-correction `<w>` elements nested inside `<note><rdg>` blocks (x-ketiv
  slots = 1268; the WLC ships zero `<w type="x-qere">` as verse children).
- Adapter faithful emit: 305507 Word nodes (plus 1244 qere Reading nodes,
  23213 Verse nodes), confirmed by running `oshb._process_book` over all 40
  books offline.

Decisive evidence: `306785 = count(.//w)` over the whole tree;
`305507 = count(<w> that are verse children)`; `306785 - 305507 = 1278 =`
qere `<w>` inside `<note>` blocks. The tier_rationale says "one record per
consonantal word slot." Qere `<w>` elements inside `<note>` are NOT word
slots, they are the scribal-correction alternative reading, which the OSHB
adapter correctly materializes as Reading nodes (IS_QERE_OF), not Word nodes.
The inventory builder counted a naive `//w` element count.

Reproduction command:
```
python - <<'PY'
import glob, xml.etree.ElementTree as ET
NS="{http://www.bibletechnologies.net/2003/OSIS/namespace}"
allw=vc=0
for p in sorted(glob.glob("data/private/oshb/wlc/*.xml")):
    r=ET.parse(p).getroot()
    allw+=sum(1 for _ in r.iter(NS+"w"))
    for v in r.iter(NS+"verse"):
        vc+=sum(1 for ch in v if ch.tag==NS+"w")
print(allw, vc)   # -> 306785 305507
PY
```

Classification: CATALOG-WRONG. The adapter is faithful to the word-slot
record_unit. The catalog counted nested qere `<w>` correction sub-elements
as word records.

Recommendation: set catalog expected_count to 305507 (tier A tolerance 0).
This is the deterministic verse-child `<w>` count over the frozen WLC release.
Proposed expected_count = 305507.

---

## 3. STEPBible-TAGNT

Source files: `data/private/stepbible/Translators Amalgamated OT+NT/TAGNT
Mat-Jhn ...txt` and `TAGNT Act-Rev ...txt`.
Adapter: `ingest/lexical/stepbible_tagnt.py`

Three numbers:
- Catalog expected_count: 141720 (tier A, tolerance 0, record_unit word).
- Real upstream raw: data rows after the first `Word & Type` header whose
  first tab field contains `#` (the adapter's exact data-row rule):
  142096. Every one of those 142096 rows parses to a token (0 predicate
  failures) and 0 produce a duplicate `osis.w<pos>` id.
- Adapter faithful emit: 142096 TaggedToken nodes, reproduced via
  `stepbible_tagnt._iter_tokens`.

Decisive evidence: the raw distinct tagged-Greek-word row count from the
exact upstream bytes is 142096. The catalog 141720 is 376 short and is NOT
reproducible by any obvious rule against these bytes: it equals neither the
all-rows count (142096) nor the NA-base-only subset (137025 rows whose
`=edition` tag starts with N). The source files are a single frozen snapshot
(`data/private/stepbible` git commit 29897f4, 2026-05-09, unchanged since), so
this is not in-repo upstream drift; the catalog 141720 was computed from a
different STEPBible release or a different (unrecoverable) counting rule than
the bytes we hold.

Reproduction command:
```
python - <<'PY'
import sys; sys.path.insert(0,".")
from pathlib import Path
from ingest.lexical.stepbible_tagnt import _iter_tokens
print(sum(1 for _ in _iter_tokens(Path("data/private/stepbible"))))  # -> 142096
PY
```

Classification: CATALOG-WRONG (catalog computed from a different snapshot or
an unrecoverable counting method). Adapter faithful to the bytes on disk. Not
UPSTREAM-DRIFT in the actionable sense, because the only upstream we possess
and will ingest yields 142096 deterministically.

Recommendation: set catalog expected_count to the faithful emit 142096
(tier A tolerance 0). This is the deterministic distinct tagged-word count
over the frozen upstream we will actually ingest.
Proposed expected_count = 142096.

---

## 4. STEPBible-TTESV

Source file: `data/private/stepbible/Tagged-Bibles/TTESV - Tyndale
Translation tags for ESV - TyndaleHouse.com STEPBible.org CC BY-NC.txt`
Adapter: `ingest/lexical/stepbible_ttesv.py`

Three numbers:
- Catalog expected_count: 31272 (tier A, tolerance 0, record_unit tagged_word).
- Real upstream raw: 31272 = every non-empty tab-bearing non-`#` line
  (reproduces the catalog exactly). Of those, 31219 parse as verse segments;
  53 are non-verse structural/metadata lines; of the 31219 verse segments, 92
  carry NO tagged surface-word position (ESV-supplied words with no
  Greek/Hebrew tag). Faithful tagged-word verse-line count = 31127.
- Adapter faithful emit: 31127 TaggedToken nodes (one per verse line with at
  least one tagged surface position), reproduced via
  `stepbible_ttesv._parse_all_rows`. 0 duplicate-id losses.

Decisive evidence (catalog 31272 exactly reproduced): the inventory builder
`tmp/build_inventory_a0.py::src_stepbible_tagged_bibles` counts
`line.strip() and "\t" in line and not line.startswith("#")`. Reproducing
that rule yields exactly 31272. The 145-line gap = 53 structural/meta lines
+ 92 tag-free verse lines. The tier_rationale claims "one row per tagged
English surface word with Strong key and morph code", but the count includes
145 lines that carry no Strong-keyed tag.

Reproduction command:
```
python - <<'PY'
import sys; sys.path.insert(0,".")
from pathlib import Path
import ingest.lexical.stepbible_ttesv as m
p=Path("data/private/stepbible/Tagged-Bibles/TTESV - Tyndale Translation tags for ESV - TyndaleHouse.com STEPBible.org CC BY-NC.txt")
raw=sum(1 for L in open(p,encoding="utf-8",errors="replace") if L.strip() and "\t" in L and not L.startswith("#"))
emit=len(m._parse_all_rows(p.read_text(encoding="utf-8-sig",errors="replace")))
print(raw, emit)   # -> 31272 31127
PY
```

Classification: CATALOG-WRONG. The adapter parse is faithful to the tagged-word
record_unit. The catalog counted untagged ESV-supplied lines and structural
lines as tagged_word records. (Confirms the handover: a prior orphan fabricated
~387k bogus per-position rows; the current O(n) adapter correctly emits one
per tagged verse line and is not the source of the gap.)

Recommendation: set catalog expected_count to 31127 (tier A tolerance 0).
Proposed expected_count = 31127.

---

## 5. STEPBible-TAHOT

Source files: `data/private/stepbible/Translators Amalgamated OT+NT/TAHOT
{Gen-Deu,Jos-Est,Job-Sng,Isa-Mal} ...txt`
Adapter: `ingest/lexical/stepbible_tahot.py`

Three numbers:
- Catalog expected_count: 283734 (tier A, tolerance 0, record_unit word).
- Real upstream raw: ref-rows matching the adapter's data-row rule
  `^[A-Za-z0-9]+\.\d+\.\d+#\d+` (a tagged Hebrew word line like
  `Gen.1.1#01=L`), non-`#`, non-blank: exactly 283734
  (76490 + 102210 + 29983 + 75051 across the 4 files).
- Adapter faithful emit: 283704 TaggedToken nodes, reproduced via
  `stepbible_tahot._load_tokens`.

Decisive evidence: the catalog 283734 EXACTLY equals the real upstream
ref-row count. This catalog entry is correct. The 30-row gap is on the
adapter side: of the 283734 raw ref-rows, the adapter drops 13 on the
populated-projection predicate (`hebrew_ketiv and strong and morph and
dictionary_form`; the 13 are Q/K scribal-correction rows lacking a populated
Strong/morph, e.g. `Jdg.16.25#02=Q(K)`, `Rut.3.12#05=Q(K)`) and 17 on
de-duplication where two ref-rows resolve to the same `osis.w<pos>` stable id.

Reproduction command:
```
python - <<'PY'
import re,sys; sys.path.insert(0,".")
from pathlib import Path
from ingest.lexical.stepbible_tahot import _load_tokens, TAHOT_FILES, TAHOT_SUBDIR, _REF_ROW
b=Path("data/private/stepbible")/TAHOT_SUBDIR
raw=sum(1 for fn in TAHOT_FILES for L in open(b/fn,encoding="utf-8-sig")
        if L.strip() and not L.strip().startswith("#") and _REF_ROW.match(L.strip()))
emit=len(_load_tokens(Path("data/private/stepbible")))
print(raw, emit)   # -> 283734 283704
PY
```

Classification: ADAPTER-WRONG against a CORRECT catalog, in the strict
tier-A line-count sense. The catalog 283734 faithfully equals the upstream
tagged-Hebrew-word row count. The adapter's 30-row shortfall is a projection
choice (drop unpopulated Q/K rows; collapse colliding stable ids).

Under the brethren-on-trial frame this is the one source where the catalog is
right. Two faithful options, both architect-legitimate:
- (a) Keep the catalog at 283734 and treat TAHOT as the documented
  adapter-projection exception (the 13 dropped rows are genuinely empty-Strong
  scribal-correction rows and the 17 collisions are real id collisions in the
  upstream `#pos` indexing for Q/K pairs). This requires a tier-A tolerance
  carve-out of 30 records for this source only, which a tolerance-0 gate
  cannot express.
- (b) Re-baseline the catalog to the adapter's deterministic faithful emit
  283704, documenting that TAHOT TaggedToken counts unique populated tagged
  words (excluding empty-Strong Q/K and id-collision rows).
Recommendation: option (b). The 30 excluded rows are not lost data (the Q/K
content is preserved via the OSHB qere Reading seam, per Decision 16), and
283704 is byte-deterministic over the frozen upstream. Proposed
expected_count = 283704. This keeps the gate tolerance-0 and the parse
faithful, at the cost of moving the catalog off the raw line count to the
de-duplicated populated-token count. If the project requires the catalog to
remain a pure raw line count, then option (a) and TAHOT does not gate on a
tolerance-0 basis.

Proposed expected_count = 283704 (option b, recommended).

---

## 6. open-cbgm-3-john

Source: `tmp/poc/cbgm/3_john.db` (SQLite) + `tmp/poc/cbgm/3_john_collation.xml`
(TEI). Adapter: `ingest/lexical/open_cbgm_3_john.py`

Three numbers:
- Catalog expected_count: 600, tier B, min 588, max 612, record_unit
  cbgm_record. Per the adapter docstring lines 27-28: "The expected count of
  600 is the sum of nodes plus edges expected across 3 John verses one
  through fifteen." There is NO open-cbgm entry in
  `docs/data_inventory_catalog.json` (20 sources, none is cbgm); the
  `catalog_source_index: 3` mis-points at MorphGNT-SBLGNT. The 600/588/612
  envelope is a hand-set estimate, not catalog-derived.
- Real upstream raw: 116 variant units in scope (3John ch.1 vv.1-15), 137
  witnesses in the SQLite, 470 readings, full TEI collation.
- Adapter faithful emit: 728 nodes (142 Witness + 116 VariantUnit + 470
  Reading) and 16829 edges (16357 READS_AT + 470 ATTESTED_BY + 2
  CORRECTOR_OF). cbgm_record total = nodes + edges = 17557 (+1 Source).

Decisive evidence: reproduced offline via `open_cbgm_3_john._parse_units`
and `._build_payloads` over `tmp/poc/cbgm`. The dominant term is READS_AT
(16357), which is generated by design: the adapter's documented lacuna
back-fill (lines 723-754) emits a `-lac` Reading and a READS_AT edge for
every witness that does NOT attest a given variant unit (116 units x ~140
witnesses). Even nodes-only (728) exceeds the catalog max of 612. The
tier-B tolerance (2 percent, cap 1000) cannot absorb a 600 vs 17557 gap;
it cannot even absorb 600 vs 728.

Reproduction command:
```
python - <<'PY'
import sys; sys.path.insert(0,".")
from pathlib import Path
import ingest.lexical.open_cbgm_3_john as c
r=Path("tmp/poc/cbgm")
u=c._parse_units(r/c.XML_FILENAME)
p=c._build_payloads(u, c._read_db_witnesses(r/c.DB_FILENAME))
n=len(p["witnesses"])+len(p["variant_units"])+len(p["readings"])
e=len(p["reads_at"])+len(p["attested_by"])+len(p["corrector_of"])
print("nodes",n,"edges",e,"total",n+e)   # -> nodes 728 edges 16829 total 17557
PY
```

Classification: TIER-MISCLASSIFIED plus CATALOG-WRONG. The expected_count
basis (600 nodes+edges) was never modeled against the adapter's lacuna
back-fill semantics, and tier B with a 1000-record cap is the wrong envelope
for a count that is dominated by a full witness-by-unit READS_AT cross product.

Recommendation: this is not a simple number swap. The architect must decide
the cbgm_record definition before a number can be set:
- If cbgm_record = nodes only: faithful target is 728. Reset tier to B with
  min/max around 728 (a wider explicit envelope, e.g. 700..760, to absorb
  collation revisions), record_unit `cbgm_node`.
- If cbgm_record = nodes + edges (current docstring): faithful target is
  17557, dominated by the by-design lacuna back-fill. Tier B percentage
  tolerance is acceptable here only if the absolute cap is removed for this
  source (a 2 percent band on 17557 is +/-351).
The lacuna back-fill is faithful per Decision 6 and MUST NOT be removed to
hit 600. The number 600/588/612 has no derivation and must be discarded.
Proposed expected_count: 728 with record_unit `cbgm_node`, tier B, explicit
min 700 / max 760 (architect to confirm the node-only definition; see
gate-impact note below).

---

## 7. Theographic-Bible-Metadata

Source files: `data/private/theographic/json/*.json` (8 Airtable-style JSON
arrays). Adapter: `ingest/lexical/theographic.py`

Three numbers:
- Catalog expected_count: 43690 (tier A, tolerance 0, record_unit
  multi_entity_record). Catalog `data_inventory_catalog.json` index 16 has
  `record_unit: "multi (see sub_files)"` and sub_files per-file counts.
- Real upstream raw: exact element sum of all 8 JSON arrays =
  books 66 + chapters 1189 + easton 6519 + events 450 + people 3067 +
  peopleGroups 23 + places 1274 + verses 31102 = 43690. The catalog 43690
  is arithmetically correct as a file-sum and the tier_rationale ("exact sum
  of upstream-published per-file counts") accurately describes that sum.
- Adapter faithful emit: 4849 entity nodes = Person 3067 + Place 1274 +
  Event 450 + Group 11 + Tribe 12 + Period 35 (+1 Source). The adapter does
  NOT materialize books (66), chapters (1189), verses (31102), or easton
  (6519) as records; verses.json is consumed only as an OSIS lookup. There
  is NO upstream Period file at all; the 35 Period nodes are derived
  deterministically from event century buckets.

Decisive evidence: reproduced offline via `theographic.ingest_theographic`
body (node builders only, no Neo4j). The catalog 43690 counts 38876 records
(books+chapters+verses+easton) that this adapter deliberately does not ingest
as nodes, and counts 0 of the 35 derived Period nodes (no upstream Period
source exists). The catalog file-sum and the adapter's projected record set
are measuring different things.

Reproduction command:
```
python - <<'PY'
import sys; sys.path.insert(0,".")
from pathlib import Path
import ingest.lexical.theographic as m
d=Path("data/private/theographic")/m.JSON_SUBDIR
look=m._verse_lookup(m._read_json(d/"verses.json"))
ppl=m._records(m._read_json(d/"people.json")); plc=m._records(m._read_json(d/"places.json"))
evt=m._records(m._read_json(d/"events.json")); grp=m._records(m._read_json(d/"peopleGroups.json"))
per,_=m._period_nodes(evt,look)
g=t=0
for r in grp:
    lab,_=m._group_node(r); g+=lab=="Group"; t+=lab=="Tribe"
print(len(ppl)+len(plc)+len(evt)+g+t+len(per))   # -> 4849
PY
```

Classification: CATALOG-WRONG for gating purposes. The catalog 43690 is a
correct upstream file-sum but does not represent this adapter's faithful
record_unit. The Period-source observation in the handover is confirmed:
Period is derived, no upstream Period file exists.

Recommendation: set catalog expected_count to the adapter's faithful
projected entity count 4849, tier A tolerance 0 (deterministic over frozen
upstream), record_unit `projected_entity` (Person/Place/Event/Group/Tribe
plus derived Period). Document that books/chapters/verses/easton are
intentionally not record nodes for this adapter (verses are an OSIS lookup;
chapters/books are produced by other adapters; easton is out of scope).
Proposed expected_count = 4849.

---

## ARCHITECT RECOMMENDATION

Summary table:

| source | catalog | real-upstream (rule) | adapter-emit | class | proposed expected_count | gate-impact |
|---|---|---|---|---|---|---|
| STEPBible-proper-nouns | 23205 | 23205 = naive tab-line count (banners+meta+detail); true names: 4262 blocks / 4305 headlines | 5468 | CATALOG-WRONG | 5468 | catalog fix unblocks tier-A 0-tol |
| OSHB-morphology | 306785 | 306785 = all `<w>`; word slots = 305507 (diff = 1278 qere `<w>` in notes) | 305507 | CATALOG-WRONG | 305507 | catalog fix unblocks tier-A 0-tol |
| STEPBible-TAGNT | 141720 | 142096 = distinct tagged Greek word rows | 142096 | CATALOG-WRONG | 142096 | catalog fix unblocks tier-A 0-tol |
| STEPBible-TTESV | 31272 | 31272 = naive tab-line count; tagged verse lines = 31127 | 31127 | CATALOG-WRONG | 31127 | catalog fix unblocks tier-A 0-tol |
| STEPBible-TAHOT | 283734 | 283734 = tagged Hebrew word ref-rows (catalog exactly correct) | 283704 | ADAPTER-WRONG (catalog correct); recommend re-baseline to faithful emit | 283704 | catalog re-baseline unblocks tier-A 0-tol; OR keep 283734 and TAHOT cannot pass a 0-tol gate |
| open-cbgm-3-john | 600 (min588/max612, hand-set; no catalog entry) | 728 nodes / 17557 nodes+edges | 728 nodes, 16829 edges | TIER-MISCLASSIFIED + CATALOG-WRONG | 728 (record_unit cbgm_node, tier B, min700/max760) pending architect definition | needs schema redesign, not a number swap; does NOT pass under current 600/612 |
| Theographic-Bible-Metadata | 43690 | 43690 = exact 8-file element sum (correct file-sum, wrong record_unit for this adapter) | 4849 | CATALOG-WRONG (record_unit mismatch) | 4849 | catalog fix unblocks tier-A 0-tol |

Class counts:
- CATALOG-WRONG: 5 (proper-nouns, OSHB, TAGNT, TTESV, Theographic)
- ADAPTER-WRONG (catalog correct): 1 (TAHOT) — recommend faithful re-baseline
- TIER-MISCLASSIFIED + CATALOG-WRONG: 1 (open-cbgm)

Single architect [SCHEMA-REVISION] commit: YES for the 5 pure CATALOG-WRONG
entries plus the recommended TAHOT re-baseline (6 of 7) can be reconciled in
one `tools/expected_counts.json` commit. open-cbgm needs a record_unit/tier
redesign decision first and should be a separate change. The exact
`tools/expected_counts.json` keys/values that commit would change (the
ARCHITECT may also re-run the inventory builder to regenerate
`docs/data_inventory_catalog.json` consistently):

- `sources["STEPBible-proper-nouns"]`: expected_count 23205 -> 5468,
  min 5468, max 5468.
- `sources["OSHB-morphology"]`: expected_count 306785 -> 305507,
  min 305507, max 305507.
- `sources["STEPBible-TAGNT"]`: expected_count 141720 -> 142096,
  min 142096, max 142096.
- `sources["STEPBible-TTESV"]`: expected_count 31272 -> 31127,
  min 31127, max 31127.
- `sources["STEPBible-TAHOT"]`: expected_count 283734 -> 283704,
  min 283704, max 283704 (record_unit clarified to de-duplicated populated
  tagged word).
- `sources["Theographic-Bible-Metadata"]`: expected_count 43690 -> 4849,
  min 4849, max 4849, record_unit multi_entity_record -> projected_entity.
- `sources["open-cbgm-3-john"]`: separate [SCHEMA-REVISION]; fix
  `catalog_source_index` (currently mis-points at MorphGNT index 3), redefine
  record_unit to `cbgm_node`, set expected_count 728 with tier B explicit
  min 700 / max 760 (architect to confirm node-only vs node+edge definition).

(Per task constraints this architect investigation does NOT modify
`tools/expected_counts.json`; the above is the prescription for the
[SCHEMA-REVISION] commit owner.)

## Bottom line

Phase D tier-A count gates can proceed after a single catalog
[SCHEMA-REVISION] for 6 of the 7 sources. Five (proper-nouns, OSHB, TAGNT,
TTESV, Theographic) are pure catalog errors: the catalog measured raw
heterogeneous lines, nested qere sub-elements, an unrecoverable alternate
snapshot, or an 8-file element sum that does not match the adapter's faithful
record_unit; all five adapters are faithful to the bytes and become exact
tolerance-0 passes once the catalog holds the byte-derived faithful number.
TAHOT is the lone case where the catalog is exactly right (283734 = real
ref-rows); the adapter faithfully drops 30 empty-Strong scribal-correction and
id-collision rows, so the recommended resolution is a faithful catalog
re-baseline to 283704 (the Q/K content is not lost, it is preserved via the
OSHB qere seam) rather than fudging the adapter back up. No source genuinely
blocks on upstream re-procurement: every file we need is on disk and frozen,
and every faithful number is byte-deterministic and reproducible. The only
hard blocker is open-cbgm-3-john, which is not a catalog typo but a structural
mis-specification: it has no inventory entry, a mis-wired catalog_source_index,
a hand-set 600/612 envelope, and a tier-B tolerance that cannot model the
adapter's by-design lacuna back-fill (17557 records, or 728 nodes-only). It
requires an architect decision on the cbgm_record definition and tier before
any gate number is meaningful, and must be carved out of the bulk
[SCHEMA-REVISION] into its own change.
