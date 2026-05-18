# Phase D Cross-Adapter Join-Key Consistency Audit, SHARD B

Auditor caste, READ-ONLY exhaustive static source analysis. Branch main,
HEAD 02ebae8. Doctrinal frame brethren-on-trial. No em or en dashes anywhere
(periods, commas, "and", "but" only). Adapter source is ground truth.

## What this audit is

Phase C verified adapters against a lossy FakeDriver and a self-referential
catalog, never against each other in a real graph. The perf manifest
(docs/PHASE_D_EDGE_PERF_MANIFEST.md) found the UNLABELED-endpoint perf class
and the two already-known correctness defects (tahot IN_VERSE id-vs-osisID,
tagnt INSTANCE_OF GreekLemma namespace). This audit is the join-key
VALUE/FORMAT/TYPE consistency pass: for every Shard-B edge, the EXACT value
the consumer supplies vs the EXACT value the producing adapter writes for
that key, read from node-emission bytes on both sides. It finds the
remaining tahot/tagnt-class defects the perf manifest deferred or missed.

Shard B adapters in scope: stepbible_tahot, stepbible_tagnt, stepbible_tvtms,
stepbible_tbesh, stepbible_tbesg, stepbible_tflsj, stepbible_morph_codes,
stepbible_proper_nouns, stepbible_ttesv, openbible, tsk, theographic,
peshitta, vulgate_clementine, coptic_scriptorium. (stepbible_tbesh and
stepbible_tbesg sit in Shard B per the prompt scope list; their cross-shard
GreekLemma/Lemma endpoints are audited against the Shard-A producers.)

## Producer-written key facts (read from node-emission bytes)

| Producer | adapter:line | label.key | EXACT written value/format/type |
|---|---|---|---|
| oshb | oshb.py:628..639 | Verse.id | `verse:<osisRef>` string (e.g. `verse:Gen.1.1`) |
| oshb | oshb.py:632 | Verse.osisID | bare `<osisRef>` string (e.g. `Gen.1.1`), OSIS book codes from WLC XML osisID attr |
| oshb | oshb.py:548..552 | Strong.id | base canonical from `canonical_strongs(raw,'hb')` with suffix split off: zero-padded-to-4, `H` prefix (e.g. `H0430`, `H7225`), string |
| macula_hebrew | macula_hebrew.py:560 | Lemma.id | `macula-hebrew-lemma:<canon[0]>` where canon[0]=`canonical_strongs(strongnumberx,'hb')[0]` = zero-padded-4 WITH uppercased suffix kept in the string (e.g. `macula-hebrew-lemma:H0430`, `macula-hebrew-lemma:H1254A`), string |
| macula_hebrew | macula_hebrew.py:561 | Lemma.strong | `canon[0]` zero-padded-4 + uppercase suffix (e.g. `H0430`, `H1254A`), string |
| macula_greek | macula_greek.py:519 | GreekLemma.id | `<source>:strong-<int(strong):05d>` (e.g. `MACULA-Greek-Nestle1904:strong-00040`), string |
| macula_greek | macula_greek.py:524 | GreekLemma.strong | `int(strong)` INTEGER, no prefix, no pad (e.g. `40`) |
| morphgnt | (perf manifest) | Verse.id | `verse:<osisRef>`; morphgnt does NOT create GreekLemma |
| oshb/morphgnt | n/a | Verse.osisID | bare OSIS dotted `<Book>.<C>.<V>` |

`canonical_strongs` (ingest/canonical_strongs.py:41..72): every accepted form
is normalised to `<PREFIX><digits.zfill(4)><UPPER suffix or ''>`. This is the
single fact that resolves the entire Strong-format defect family below.

## Per-adapter per-edge join-key table

Verdict legend: MATCH-OK (key+value+type+label all consistent and backed);
KEY-MISMATCH (consumer value/format/type the producer never writes that way,
edge resolves 0 or wrong); LABEL/INDEX-GAP (key correct, label/index only,
already in the perf manifest, not re-reported here as a defect).

### stepbible_tahot (DATASETS[8])

| edge | from: matched key/value/type vs producer | to: matched key/value/type vs producer | verdict | producing adapter + file:line both sides | exact faithful fix |
|---|---|---|---|---|---|
| INSTANCE_OF | from `(a {id})`, value `stepbible-tahot:<osis>.w<pos>` = self TaggedToken.id (tahot.py:308 match, :412/473 produce). OK. | to `(b {id})`, consumer value `macula-hebrew-lemma:<tahot _normalize_strong>` = `macula-hebrew-lemma:H430` / `macula-hebrew-lemma:H1254a` (tahot.py:469, :334). Producer macula_hebrew writes `Lemma.id = macula-hebrew-lemma:H0430` / `macula-hebrew-lemma:H1254A` (macula_hebrew.py:560, canonical_strongs zfill+upper). | KEY-MISMATCH | consumer stepbible_tahot.py:469 builds `macula-hebrew-lemma:{t['strong']}`, `_normalize_strong` :334 `f"H{int(digits)}{sense}"` (NO zfill, lowercase sense). Producer macula_hebrew.py:560 `f"{LEMMA_ID_PREFIX}{strong}"`, strong = canonical_strongs[0] (macula_hebrew.py:506/560). | Change tahot `_normalize_strong` to emit the SAME canonical form macula_hebrew keys Lemma.id on: route the raw dStrong through `ingest.canonical_strongs.canonical_strongs(raw, lang='hb')` and use `canon[0]` (zero-padded-4, uppercase suffix) verbatim, so `to_id = f"macula-hebrew-lemma:{canon[0]}"`. Owning adapter: ingest/lexical/stepbible_tahot.py. Producer side is correct (canonical form is the declared Decision 14 contract); consumer must conform. |
| IN_VERSE | from `(a {id})` self TaggedToken.id. OK. | to `(b {id})` consumer value `t["osis"]` = bare `Gen.1.1` (tahot.py:472, :360). Producer Verse keyed `osisID`=`Gen.1.1` but `Verse.id`=`verse:Gen.1.1`. | KEY-MISMATCH | consumer stepbible_tahot.py:312/472 matches Verse on `id` with a bare osis value; producer oshb.py:628/632 writes `Verse.id=verse:<osis>`, `Verse.osisID=<osis>`. | Change the IN_VERSE MATCH key from `id` to `osisID` AND add `:Verse`: `MATCH (b:Verse {osisID: row.to_id})`. (Same fix already in perf manifest task B item 9; restated here as a confirmed value-level KEY-MISMATCH: bare osis never equals `verse:`-prefixed Verse.id.) Owning adapter: ingest/lexical/stepbible_tahot.py:312. |

### stepbible_tagnt (DATASETS[9])

| edge | from vs producer | to vs producer | verdict | producing adapter + file:line | exact faithful fix |
|---|---|---|---|---|---|
| INSTANCE_OF | from `(a {id})` self TaggedToken.id (tagnt.py:247, :317/377). OK. | to `(b {id})` consumer value `t["strong_id"]` = `_strong_from_grammar` = bare Greek Strong before first `=`, e.g. `G0040` (tagnt.py:384, :281). Producer macula_greek writes `GreekLemma.id = MACULA-Greek-Nestle1904:strong-00040` (macula_greek.py:519); macula_greek `GreekLemma.strong = int(40)` (macula_greek.py:524). morphgnt does NOT create GreekLemma. ttesv creates `GreekLemma.id = G0040` but ttesv is DATASETS[10], AFTER tagnt[9]. | KEY-MISMATCH (MUST-ESCALATE) | consumer stepbible_tagnt.py:247/384; producer macula_greek.py:519 (id), :524 (strong int). | `(:GreekLemma {id:'G0040'})` matches ZERO macula_greek nodes (namespace + zero-pad differ). `(:GreekLemma {strong:'G0040'})` also fails: macula_greek strong is INT `40` not string `G0040`, and unindexed. Canonical GreekLemma identity across macula_greek / ttesv / tagnt / tbesg / tflsj is a genuine data-model decision (one namespaced id vs bare Strong; int vs string strong). MUST-ESCALATE. Do NOT guess. Recommended decision once escalated: pick ONE canonical GreekLemma key (e.g. add a string `strong_canonical = canonical_strongs(...,'gk')[0]` property on GreekLemma written by macula_greek/ttesv, indexed, and have tagnt/tbesg/tflsj match on it). Owning adapters if decision taken: macula_greek.py + stepbible_tagnt.py + graph/lexical.cypher. |
| IN_VERSE | from `(a {id})` self TaggedToken.id. OK. | to `(b {osisID})` consumer value `t["osis_ref"]` = osis token from `_parse_word_and_type`, bare `Matt.1.1` form (tagnt.py:252, :397, :268..277). Producer morphgnt writes `Verse.osisID = <osisRef>` bare. | MATCH-OK (value/key/type); LABEL-only gap is perf-manifest item, not a defect here | consumer stepbible_tagnt.py:252; producer morphgnt Verse.osisID bare osis. | None for key/value. Key already `osisID`, value bare osis matches Verse.osisID. The missing `:Verse`/`:TaggedToken` labels are the perf manifest's NEEDS-FIX (label only). No KEY-MISMATCH. |

### stepbible_tvtms (DATASETS[15])

Emits `VersificationRule` and `Source` nodes only (tvtms.py:331..334). NO
relationship edges. No join keys to audit. MATCH-OK (vacuous). Note: the
serialized artifact `data/private/stepbible/tvtms.parsed.json` it documents
is JSON (tvtms.py:369 `json.load`), but tsk.py:418..433 and openbible.py:329..347
parse the SAME path with `line.split("\t")` (TSV). See cross-group hazard 1.

### stepbible_tbesh (DATASETS[11])

| edge | from vs producer | to vs producer | verdict | producing adapter + file:line | exact faithful fix |
|---|---|---|---|---|---|
| LEX_FOR | from `(b {strong_disambig})` self BriefLexEntry (tbesh.py:308, :294/376). OK self. | to `(l {strong})` consumer value `row.base_strong` = raw upstream eStrong/dStrong after sense-suffix strip ONLY, e.g. `H430` (tbesh.py:362..377, NO canonical_strongs). tbesh ALSO produces the Lemma it matches: `MERGE (n:Lemma {strong: row.base_strong})` (tbesh.py:303/439), so the edge is SELF-consistent (`H430` matches `H430`). BUT macula_hebrew (the Group-1 Lemma producer) writes `Lemma.strong = H0430` (zero-pad+upper, macula_hebrew.py:561). `Lemma.strong` is UNIQUE-constrained (lexical.cypher:13). | KEY-MISMATCH (cross-producer; self-consistent but creates a divergent duplicate Lemma) | tbesh.py:303/377/439 vs macula_hebrew.py:561. | tbesh's self-MERGEd `Lemma {strong:'H430'}` is a DISTINCT node from macula_hebrew's `Lemma {strong:'H0430'}` (different string, no constraint collision but no concordance join either: Decision 11 explicitly wants `base_strong` to "hit MACULA-Hebrew strongnumberx"). Faithful fix: tbesh MUST normalise `base_strong` through `canonical_strongs(raw,'hb')[0]` before both the `_MERGE_LEMMA` and `_MERGE_LEX_FOR` payloads so the Lemma it touches is byte-identical to macula_hebrew's `Lemma.strong`. Owning adapter: ingest/lexical/stepbible_tbesh.py:362..377,303,439. (Note the pre-existing tbesh[11]-before-tbesg[12] ordering inversion is a separate perf-manifest flag, not this.) |
| FROM_EDITION | from `(b {strong_disambig})` self BriefLexEntry. OK. | to `(s {slug})` value `STEPBible-TBESH` matches Source.slug written by tbesh.py:419. | MATCH-OK | tbesh.py:315/419. | None. |

### stepbible_tbesg (DATASETS[12])

| edge | from vs producer | to vs producer | verdict | producing adapter + file:line | exact faithful fix |
|---|---|---|---|---|---|
| LEX_FOR | from `(b:BriefLexEntry) WHERE b.strong_disambig=...` self BriefLexEntry (tbesg.py:307, :302/363). OK. | to `(g:GreekLemma {id: row.base_strong})` consumer value `base_strong = parts[_COL_ESTRONG]` = raw upstream eStrong, e.g. `G40` (tbesg.py:308, :343, regex `^G\d` :286/344). Producer macula_greek writes `GreekLemma.id = MACULA-Greek-Nestle1904:strong-00040` (macula_greek.py:519). ttesv writes `GreekLemma.id=G0040` (ttesv.py:539..544) but ttesv[10] runs before tbesg[12] yet still `G0040` != `G40`. | KEY-MISMATCH | consumer stepbible_tbesg.py:308/343; producer macula_greek.py:519 (and ttesv.py:539..544). | `GreekLemma {id:'G40'}` matches NO producer (`MACULA-...:strong-00040` namespaced, or ttesv `G0040` zero-padded). Faithful fix is bound to the tagnt MUST-ESCALATE decision (same canonical-GreekLemma-key question). Until escalated, tbesg LEX_FOR resolves 0 even though its endpoint is already labeled (perf manifest marked tbesg CLEAN for PERF only; it is NOT clean for join-value). Owning adapter: ingest/lexical/stepbible_tbesg.py:343 (transform base_strong to the canonical GreekLemma key chosen by the escalation). MUST-ESCALATE link. |

### stepbible_tflsj (DATASETS[13])

| edge | from vs producer | to vs producer | verdict | producing adapter + file:line | exact faithful fix |
|---|---|---|---|---|---|
| LEX_FOR | from `(e:LsjEntry {id})` self LsjEntry, id `tflsj:<strong>:<lemma>` (tflsj.py:324, :319/348/367). OK. | to `(g:GreekLemma {strong: row.strong})` consumer value `strong = parts[0]` = raw upstream eStrong STRING with prefix, e.g. `G40` (tflsj.py:324, :356/368). Producer macula_greek writes `GreekLemma.strong = int(40)` INTEGER no prefix (macula_greek.py:524). ttesv writes `GreekLemma.strong = 'G0040'` STRING (ttesv.py:540..543). | KEY-MISMATCH (type AND format) | consumer stepbible_tflsj.py:324/356/368; producer macula_greek.py:524 (int), ttesv.py:540..543 (str `G0040`). | Triple divergence: tflsj `'G40'` (str+prefix) vs macula_greek `40` (int, Cypher will not equate int 40 to string 'G40') vs ttesv `'G0040'` (str, zero-pad). The perf manifest classed tflsj as NEEDS-INDEX only (missing `GreekLemma.strong` index); the index is moot because the VALUE/TYPE never matches. Faithful fix is bound to the same canonical-GreekLemma escalation: once a single typed GreekLemma key is decided, tflsj must supply that exact form. Owning adapter: ingest/lexical/stepbible_tflsj.py:368 + graph/lexical.cypher (index on the chosen key). MUST-ESCALATE link. |

### stepbible_morph_codes (DATASETS[7])

Emits `MorphCode` and `Source` nodes only. No relationship edges
(confirmed: no `-[r:` MERGE in the file). MATCH-OK (vacuous).

### stepbible_proper_nouns (DATASETS[14])

| edge | from vs producer | to vs producer | verdict | producing adapter + file:line | exact faithful fix |
|---|---|---|---|---|---|
| NAMED_AT | from `(p) WHERE p.proper_name_entry=...` self ProperNoun (proper_nouns.py:350, :341). OK. | to `(v) WHERE v.osisID=row.osisID` consumer value = `OSIS_REF_RE.match(token).group(0)` (proper_nouns.py:351, :455..459, regex :327 `^[1-4]?[A-Za-z]{2,4}\.\d+\.\d+`). Producer oshb/morphgnt write `Verse.osisID` bare OSIS dotted. STEPBible TIPNR ref column is OSIS-aligned dotted form. | MATCH-OK (key+value+type); label-only gap is perf-manifest item | consumer proper_nouns.py:351; producer oshb.py:632 Verse.osisID. | None for key/value: key already `osisID`, value bare OSIS dotted matches Verse.osisID. Residual low-risk: TIPNR uses a few non-OSIS book spellings (e.g. `Sng`/`Ezk`/`Jdg`/`Nam`) where OSHB osisID uses OSIS standard (`Song`/`Ezek`/`Judg`/`Nah`); those specific entries would resolve 0. Not a structural KEY-MISMATCH (key and form are right for the OSIS-aligned majority); flagged as a MUST-VERIFY data point, see Verify list. The missing `:ProperNoun`/`:Verse` labels are the perf manifest's NEEDS-FIX. proper_nouns also self-`MERGE (n:Verse {osisID})` (:344) so the join is satisfiable. |

### stepbible_ttesv (DATASETS[10])

| edge | from vs producer | to vs producer | verdict | producing adapter + file:line | exact faithful fix |
|---|---|---|---|---|---|
| FROM_EDITION | from `(t {id})` self TaggedToken.id `stepbible-ttesv:<osis>.w<pos_raw>` (ttesv.py:351, :460). OK. | to `(s {slug})` value `STEPBible-TTESV` matches Source.slug (ttesv.py:579..583). | MATCH-OK | ttesv.py:351/579. | None. |
| INSTANCE_OF (Hebrew) | from `(t {id})` self TaggedToken.id. OK. | to `(l {id: row.lemma_id})` value `lemma_id = canonical_strong` = `canonical_strongs(raw,lang)[0]` = `H0430` (ttesv.py:358, :557, :394..397). ttesv SELF-produces `Lemma {id: c}` with the same `c=H0430` (ttesv.py:530..536). Self-consistent. | MATCH-OK (self-consistent); cross-producer fragmentation note | ttesv.py:358/532 vs macula_hebrew.py:560. | Edge resolves (ttesv Lemma.id `H0430` == ttesv consumer `H0430`). BUT this is a DISTINCT Lemma node from macula_hebrew's `macula-hebrew-lemma:H0430` (different id namespace). No constraint collision (lemma_id UNIQUE on different values). Data-model fragmentation: two Lemma nodes per Strong. MUST-ESCALATE note (canonical Lemma identity), not a per-adapter fix. |
| INSTANCE_OF (Greek) | from `(t {id})` self TaggedToken.id. OK. | to `(l {id: row.lemma_id})` value `G0040` (ttesv.py:364, :557). ttesv SELF-produces `GreekLemma {id:'G0040'}` (ttesv.py:539..544). Self-consistent. | MATCH-OK (self-consistent); cross-producer fragmentation note | ttesv.py:364/541 vs macula_greek.py:519. | Edge resolves internally. Distinct from macula_greek `MACULA-...:strong-00040` and from tagnt/tbesg/tflsj expectations. Feeds the canonical-GreekLemma MUST-ESCALATE: ttesv's `GreekLemma {id:'G0040'}` is yet a third GreekLemma identity scheme in the graph. |

### openbible (DATASETS[20])

| edge | from vs producer | to vs producer | verdict | producing adapter + file:line | exact faithful fix |
|---|---|---|---|---|---|
| OPENBIBLE_CROSS_REF | from `(a:Verse {osisID: row.from_osis})` value = TVTMS-projected `from_osis` (openbible.py:307, :350..353, :395). Producer oshb/morphgnt Verse.osisID bare OSIS dotted. | to `(b:Verse {osisID: row.to_osis})` same projection. | MATCH-OK conditional on projection (see hazard 1) | openbible.py:307/353; producer Verse.osisID. | Key already `osisID`, both endpoints already `:Verse` (perf manifest CLEAN). Value correctness depends on `_project_to_osis` returning OSIS-dotted form. Because `_load_tvtms_rules` parses the JSON artifact as TSV (hazard 1), the rules dict is EMPTY, so projection is identity passthrough of the OpenBible CSV `From Verse`/`To Verse` columns. OpenBible.info publishes OSIS dotted refs (`Gen.1.1`), which DO equal Verse.osisID, so the identity passthrough is accidentally correct for OpenBible. No KEY-MISMATCH on the join itself. Hazard 1 still must be fixed for the TVTMS-remap rows (KJV-only subdivisions) or those specific rows quarantine/misproject. |

### tsk (DATASETS[21])

| edge | from vs producer | to vs producer | verdict | producing adapter + file:line | exact faithful fix |
|---|---|---|---|---|---|
| CROSS_REF | from `(a {id})` self CrossRef.id `tsk:<bn>.<ch>.<v>.<wn>` (tsk.py:625, :564..567/620). OK. | to `(b:Verse {osisID: row.osis_target})` value = `_project(...)` = TVTMS `mapped` OR `f"{osis_book}.{chapter}.{verse}"` dotted (tsk.py:625, :445..454, :580). Producer Verse.osisID bare OSIS dotted. | MATCH-OK conditional (see hazard 1 + 2) | tsk.py:625/454; producer Verse.osisID. | Key `osisID` correct, to-side already `:Verse` (perf manifest: only from-side needs `:CrossRef`). Identity fallback `f"{osis_book}.{chapter}.{verse}"` equals Verse.osisID. The `mapped` branch returns TVTMS `ref_b` verbatim; format of `ref_b` is data-dependent (could be `Gen.1.1` or `Gen 1:1`). Combined with hazard 1 (rules dict empty due to JSON-vs-TSV parse), `mapped` is never taken so identity holds and the join resolves for in-bounds refs. NOT a structural KEY-MISMATCH, but MUST-VERIFY the `ref_b` format once hazard 1 is fixed (see Verify list). |

### theographic (DATASETS[22])

| edge | from vs producer | to vs producer | verdict | producing adapter + file:line | exact faithful fix |
|---|---|---|---|---|---|
| MENTIONS | from `(a {entity_id})` one of 6 self entity labels (theographic.py:503, :498). OK self. | to `(b:Verse {osisID: row.to_id})` value `to_id = osis` from `_verse_lookup` = theographic verses.json `fields.osisRef` (theographic.py:503, :536, :673/681). Producer Verse.osisID bare OSIS dotted. | MATCH-OK conditional | theographic.py:503/536; producer Verse.osisID. | Key `osisID` correct, to-side already `:Verse`. Theographic `osisRef` is OSIS dotted (`Gen.1.1`) matching Verse.osisID. No KEY-MISMATCH. The heterogeneous from-side (6 entity labels, no per-row label tag) is the perf manifest's branched NEEDS-FIX, not a key-value defect. |
| FROM_EDITION | from one of 6 entity labels by entity_id. OK self. | to `(b:Source {slug: row.slug})` value `Theographic-Bible-Metadata` matches Source.slug (theographic.py:508, :495). | MATCH-OK | theographic.py:508. | None (label-only perf item only). |

### peshitta (DATASETS[16])

| edge | from vs producer | to vs producer | verdict | producing adapter + file:line | exact faithful fix |
|---|---|---|---|---|---|
| IN_VERSE | from `(a {id})` self SyriacWord.id `peshitta:<verse_ref>:<pos>` (peshitta.py:227, :262/293). OK. | to `(b {osisID: row.to_id})` value `to_id = row["verse_ref"]` = upstream TSV `verse_ref` column VERBATIM (peshitta.py:378, :273/296). NO TVTMS projection anywhere in peshitta.py (Decision 7 mandates projection; absent). Producer Verse.osisID bare OSIS dotted. | KEY-MISMATCH RISK / CONTRACT VIOLATION (value-format unverifiable, projection missing) | consumer peshitta.py:378; producer oshb/morphgnt Verse.osisID. | Key is `osisID` (correct once `:Verse`/`:SyriacWord` labels added per perf manifest). BUT Decision 7 and peshitta docstring require Syriac verse identifiers be projected through STEPBible-TVTMS to OSIS; the code does NOT load or apply TVTMS at all. If the upstream ETCBC Peshitta `verse_ref` column is already OSIS-dotted the join works (placeholder rows use `Matt.6.9`, which would match); if it is the ETCBC native form (`MATT 6:9`, captured in `raw_verse_ref`) it matches 0. Faithful fix: implement the TVTMS projection peshitta's own docstring promises (load `tvtms.parsed.json`, map `raw_verse_ref` to OSIS, set `verse_ref` to the projected OSIS), so `to_id` is guaranteed to equal Verse.osisID. Owning adapter: ingest/lexical/peshitta.py:337..345 / :376..387. MUST-ESCALATE-adjacent: whether the cached upstream is pre-OSIS or native is a data fact to verify (see Verify list). |

### vulgate_clementine (DATASETS[18])

Emits `VulgateVerse` (osis) and `Source` nodes only (vulgate_clementine.py:308).
NO relationship edges. MATCH-OK (vacuous). `VulgateVerse.osis` is constrained
standalone (vulgate_verse_osis); no cross-adapter join.

### coptic_scriptorium (DATASETS[17])

| edge | from vs producer | to vs producer | verdict | producing adapter + file:line | exact faithful fix |
|---|---|---|---|---|---|
| IN_VERSE | from `(a {id})` self CopticWord.id `coptic-scriptorium:<corpus>:<doc>:<pos>` (coptic.py:384, :468/502). OK. | to `(b {osisID: row.to_id})` value `to_id = r["verse_ref"]` = 4th TT column VERBATIM (coptic.py:575, :497/508). NO TVTMS projection anywhere (Decision 9 mandates it; absent). Producer Verse.osisID bare OSIS dotted. | KEY-MISMATCH RISK / CONTRACT VIOLATION (same class as peshitta) | consumer coptic.py:575; producer oshb/morphgnt Verse.osisID. | Key `osisID` correct once labels added (perf manifest). Decision 9 + coptic docstring require TVTMS projection of Sahidic/Bohairic verse ids to OSIS; code does not load/apply TVTMS. Baseline rows use `Rom.1.1` (OSIS, would match); real `.tt` 4th column format is unverified. Faithful fix: implement the TVTMS projection the docstring promises so `verse_ref` is guaranteed OSIS before the IN_VERSE build. Owning adapter: ingest/lexical/coptic_scriptorium.py:497/508 / :573..583. MUST-VERIFY upstream `.tt` verse-id format (see Verify list). |

## SHARD-B DEFECT LEDGER (every KEY-MISMATCH)

D1. tahot INSTANCE_OF, Strong zero-pad + suffix-case divergence (NEW, perf
manifest missed this; it asserted to_id "IS the Lemma.id namespace" without
checking the digit format).
- Producer macula_hebrew.py:560 Lemma.id = `macula-hebrew-lemma:H0430`
  (and `macula-hebrew-lemma:H1254A`).
- Consumer stepbible_tahot.py:469 + :334 builds
  `macula-hebrew-lemma:H430` (no zfill) / `macula-hebrew-lemma:H1254a`
  (lowercase suffix). Every tahot INSTANCE_OF edge for Strong < 1000, and
  every suffixed Strong, resolves to ZERO.
- Faithful fix: in stepbible_tahot.py route the raw dStrong through
  `ingest.canonical_strongs.canonical_strongs(raw,'hb')`, use `canon[0]`
  for the `macula-hebrew-lemma:` join value (replacing `_normalize_strong`'s
  ad hoc `f"H{int(digits)}{sense}"`). Producer is canonical and correct;
  consumer must conform. Owning adapter: ingest/lexical/stepbible_tahot.py.

D2. tahot IN_VERSE, id-vs-osisID + bare-value mismatch (CONFIRMED;
perf-manifest task B item 9, restated as a value-level KEY-MISMATCH).
- Producer oshb.py:628/632: Verse.id=`verse:Gen.1.1`, Verse.osisID=`Gen.1.1`.
- Consumer stepbible_tahot.py:312/472 matches `id` with bare `Gen.1.1`.
- Faithful fix: `MATCH (b:Verse {osisID: row.to_id})` (key id->osisID, add
  label). Owning adapter: ingest/lexical/stepbible_tahot.py:312.

D3. tagnt INSTANCE_OF, GreekLemma namespace + zero-pad + (strong) int/str
mismatch (CONFIRMED; perf-manifest MUST-ESCALATE, restated with the int/str
type fact).
- Producer macula_greek.py:519 GreekLemma.id=`MACULA-...:strong-00040`;
  :524 GreekLemma.strong=int `40`.
- Consumer stepbible_tagnt.py:384 to_id=`G0040`.
- Faithful fix: MUST-ESCALATE. Canonical GreekLemma key is a data-model
  decision (see ESCALATIONS). Owning adapters: macula_greek.py +
  stepbible_tagnt.py + graph/lexical.cypher.

D4. tbesg LEX_FOR, GreekLemma.id `G40` vs producer namespaced/zero-padded
(NEW in defect-ledger terms; perf manifest explicitly marked tbesg "CLEAN"
for PERF and footnoted the value question as out of scope. It is a real
join-value defect: 0 matches).
- Producer macula_greek.py:519 GreekLemma.id=`MACULA-...:strong-00040`;
  ttesv.py:541 GreekLemma.id=`G0040`.
- Consumer stepbible_tbesg.py:308/343 GreekLemma.id=`G40`.
- Faithful fix: bound to the D3 canonical-GreekLemma escalation; tbesg
  must supply the chosen canonical key. Owning adapter:
  ingest/lexical/stepbible_tbesg.py:343.

D5. tflsj LEX_FOR, GreekLemma.strong str-with-prefix `G40` vs producer
int `40` (macula_greek) / str `G0040` (ttesv): TYPE + format mismatch
(NEW in defect-ledger terms; perf manifest classed it NEEDS-INDEX only,
the index is moot because the value/type never matches).
- Producer macula_greek.py:524 GreekLemma.strong=int `40`;
  ttesv.py:540..543 GreekLemma.strong=str `G0040`.
- Consumer stepbible_tflsj.py:324/368 GreekLemma.strong=str `G40`.
- Faithful fix: bound to D3 escalation; once a single typed GreekLemma key
  is decided, tflsj supplies that exact form and lexical.cypher indexes it.
  Owning adapter: ingest/lexical/stepbible_tflsj.py:368 + graph/lexical.cypher.

D6. tbesh LEX_FOR, Lemma.strong `H430` (un-canonical) vs macula_hebrew
`H0430` (NEW; perf manifest marked tbesh NEEDS-FIX label-only and asserted
"Lemma keyed by strong is backed by lemma_strong", but did not compare the
VALUE tbesh writes to the value macula_hebrew writes).
- Producer macula_hebrew.py:561 Lemma.strong=`H0430` (canonical, UNIQUE
  constrained lexical.cypher:13).
- Consumer/self-producer stepbible_tbesh.py:377/303/439 base_strong=`H430`
  (raw, no canonical_strongs). Self-consistent edge BUT creates a divergent
  duplicate Lemma node; the Decision-11-intended concordance join to
  MACULA-Hebrew misses.
- Faithful fix: normalise `base_strong` via
  `canonical_strongs(raw,'hb')[0]` before BOTH `_MERGE_LEMMA` and
  `_MERGE_LEX_FOR` payloads so tbesh touches the SAME Lemma node
  macula_hebrew writes. Owning adapter: ingest/lexical/stepbible_tbesh.py:362..377.

D7. peshitta IN_VERSE, missing mandated TVTMS projection; `verse_ref`
verbatim may not equal Verse.osisID (CONTRACT VIOLATION + KEY-MISMATCH RISK).
- Producer oshb/morphgnt Verse.osisID bare OSIS dotted.
- Consumer peshitta.py:378 to_id=upstream `verse_ref` verbatim; Decision 7
  + docstring require TVTMS projection that the code never performs.
- Faithful fix: implement the TVTMS projection the docstring promises
  (load tvtms.parsed.json, project raw_verse_ref to OSIS). Owning adapter:
  ingest/lexical/peshitta.py:337..345 / :376..387. Verify upstream format.

D8. coptic_scriptorium IN_VERSE, missing mandated TVTMS projection (same
class as D7).
- Consumer coptic_scriptorium.py:575 to_id=`.tt` 4th column verbatim;
  Decision 9 + docstring require TVTMS projection never performed.
- Faithful fix: implement the documented TVTMS projection. Owning adapter:
  ingest/lexical/coptic_scriptorium.py:497/508 / :573..583.

## ESCALATIONS (MUST-ESCALATE: genuine data-model decision, do NOT guess)

E1. Canonical GreekLemma identity. FOUR incompatible GreekLemma identity
schemes coexist:
- macula_greek: `GreekLemma.id = MACULA-<edition>:strong-<int:05d>`,
  `GreekLemma.strong = int` (macula_greek.py:519/524).
- ttesv: `GreekLemma.id = <bare canonical G, zero-padded-4>` e.g. `G0040`,
  `GreekLemma.strong = same string` (ttesv.py:539..544).
- tagnt consumer expects `GreekLemma.id = G0040` (bare, zero-padded)
  (tagnt.py:384).
- tbesg consumer expects `GreekLemma.id = G40` (raw eStrong) (tbesg.py:343).
- tflsj consumer expects `GreekLemma.strong = 'G40'` (str+prefix)
  (tflsj.py:368).
`greek_lemma_id` is UNIQUE on `GreekLemma.id` (lexical.cypher:14);
`GreekLemma.strong` has NO constraint and NO index (the single missing
index the perf manifest named). Picking the canonical key (one namespaced
id vs bare Strong; int vs string strong; whether ttesv and macula_greek
must converge on one GreekLemma per Strong rather than two) is a schema
decision affecting macula_greek, ttesv, tagnt, tbesg, tflsj and
graph/lexical.cypher simultaneously. DO NOT GUESS. Resolves D3, D4, D5.

E2. Canonical Lemma (Hebrew) identity. macula_hebrew writes
`Lemma.id = macula-hebrew-lemma:H0430` (macula_hebrew.py:560); ttesv writes
a SEPARATE `Lemma.id = H0430` (ttesv.py:530..536); tbesh writes a SEPARATE
`Lemma {strong:'H430'}` with NO id (tbesh.py:303). Three Lemma populations
for the same Strong. `lemma_id` UNIQUE on `Lemma.id`, `lemma_strong` UNIQUE
on `Lemma.strong`. Whether the graph should hold ONE Lemma per Strong
(shared id namespace) or accept per-source Lemma fragments is a data-model
decision. D1 and D6 can be fixed to make each consumer self-consistent OR
to converge on macula_hebrew's namespace; which is correct is the
escalation. The recommended brethren-on-trial-safe direction (one Lemma
per Strong, macula_hebrew namespace as canonical, every consumer conforms)
is stated for the decider, not applied.

## TVTMS-projection ref-format findings

- tsk._project (tsk.py:445..454): identity fallback returns
  `f"{osis_book}.{chapter}.{verse}"` which EQUALS Verse.osisID bare dotted
  form. The `mapped` branch returns TVTMS `ref_b` verbatim, format
  data-dependent and UNVERIFIED.
- openbible._project_to_osis (openbible.py:350..353): `rules.get(kjv,kjv)`,
  identity fallback returns the OpenBible CSV ref verbatim. OpenBible.info
  publishes OSIS dotted refs, so identity == Verse.osisID. The `rules`
  mapped branch is data-dependent.
- peshitta and coptic_scriptorium: NO TVTMS projection performed at all
  despite Decisions 7/9 and their own docstrings mandating it. `verse_ref`
  is the upstream column verbatim. This is the highest-risk projection
  finding: the projected ref is NOT guaranteed to equal Verse.osisID
  because no projection runs (D7, D8).
- Net: where TVTMS projection IS run (tsk, openbible) the identity-fallback
  form matches Verse.osisID; the TVTMS-`mapped` form is unverified pending
  hazard 1. Where projection is contractually required but ABSENT (peshitta,
  coptic) the join correctness is unproven and likely 0 for native upstream
  forms.

## Cross-group ordering / dependency hazards

H1. tvtms.parsed.json format mismatch (correctness, all five
cross-version consumers). stepbible_tvtms.py:369 treats the artifact as
JSON (`json.load`). tsk.py:411..433 and openbible.py:315..347 parse the
SAME file path with `line.split("\t")` (TSV, 4..5 columns). A JSON document
split on tabs yields no valid `tradition_a=='english'` rows, so the rules
dict is EMPTY and every projection degrades to identity passthrough. For
TSK/OpenBible this is accidentally non-fatal (upstream refs are already
OSIS dotted) but it silently disables every KJV-only-subdivision remap
Decision 5 requires. Owning surface: the artifact writer (legacy
ingest/lexical/stepbible.py) vs the TSV readers in tsk.py / openbible.py
must agree on one format. Flagged, OUT OF SCOPE for this read-only audit's
deliverable; record only.

H2. tbesh[11] before tbesg[12] (DATASETS order, run.py:55..56). tbesh
LEX_FOR/FROM_EDITION presuppose BriefLexEntry, but BriefLexEntry for the
Greek side is produced by tbesg which runs AFTER. Already flagged by the
perf manifest as a pre-existing ordering inversion out of scope for the
perf wave; restated here because D6's fix must not be blamed for this
pre-existing zero-match, and because tbesh's Hebrew BriefLexEntry is
self-produced (tbesh.py:294) so tbesh's own LEX_FOR from-side is fine; only
its Lemma to-side (D6) is the join-value defect.

H3. Producer-before-consumer for the Strong/Lemma/GreekLemma joins is
SATISFIED by DATASETS order (macula_hebrew[1], macula_greek[6] before
tahot[8]/tagnt[9]/ttesv[10]/tbesh[11]/tbesg[12]/tflsj[13]). The Shard-B
INSTANCE_OF/LEX_FOR defects are therefore VALUE-format defects, NOT
ordering defects. No new cross-group ordering hazard is introduced by any
prescribed fix.

## MUST-VERIFY data points (cannot be settled by static bytes alone)

V1. STEPBible TIPNR proper-nouns book codes vs OSHB osisID book codes for
the divergent spellings (Sng/Song, Ezk/Ezek, Jdg/Judg, Nam/Nah). Static
code is correct in key and form; only those specific entries risk 0.
V2. TVTMS `ref_b` format in the real tvtms.parsed.json (dotted vs spaced).
V3. Cached ETCBC Peshitta `verse_ref` column form (OSIS dotted vs native
`BOOK C:V`) and cached Coptic SCRIPTORIUM `.tt` 4th column form. D7/D8
severity hinges on these.

## Counts

- Adapters in Shard B scope: 15.
- Edges audited (relationship MERGE templates with a cross-node join):
  17. (tahot 2, tagnt 2, tbesh 2, tbesg 1, tflsj 1, proper_nouns 1,
  ttesv 3, openbible 1, tsk 1, theographic 2, peshitta 1,
  coptic_scriptorium 1. tvtms 0, morph_codes 0, vulgate_clementine 0:
  no relationship edges, vacuously consistent.)
- MATCH-OK: 8 (tagnt IN_VERSE; proper_nouns NAMED_AT; ttesv FROM_EDITION;
  ttesv INSTANCE_OF Hebrew; ttesv INSTANCE_OF Greek; theographic MENTIONS;
  theographic FROM_EDITION; tbesh FROM_EDITION). ttesv INSTANCE_OF pair and
  proper_nouns carry MUST-ESCALATE / MUST-VERIFY annotations but the edge
  resolves as written.
- KEY-MISMATCH: 8 (D1 tahot INSTANCE_OF; D2 tahot IN_VERSE; D3 tagnt
  INSTANCE_OF; D4 tbesg LEX_FOR; D5 tflsj LEX_FOR; D6 tbesh LEX_FOR;
  D7 peshitta IN_VERSE; D8 coptic IN_VERSE).
- LABEL/INDEX-GAP only (already in perf manifest, not double-reported as
  defects here): every edge additionally needs the perf manifest's label
  add; that is tracked there, not counted as a Shard-B join-value defect.
- MUST-ESCALATE: 2 data-model decisions (E1 canonical GreekLemma identity,
  resolves D3/D4/D5; E2 canonical Hebrew Lemma identity, frames D1/D6).

## Bottom line

The perf manifest's label/index pass is necessary but NOT sufficient. Eight
join-value defects remain that would silently resolve 0 or wrong edges at
ingest even after every label is added. The most dangerous NEW finding the
perf manifest missed is the Strong zero-pad family: `canonical_strongs`
zero-pads to 4 digits and uppercases suffixes, but stepbible_tahot
(`_normalize_strong`), stepbible_tbesh (`base_strong`), stepbible_tbesg
(`base_strong`) and stepbible_tflsj (`strong`) all feed RAW un-padded
Strong tokens into joins against producers that wrote the canonical padded
form. Every Strong below 1000 and every sense-suffixed Strong drops. The
GreekLemma identity question (E1) and Hebrew Lemma identity question (E2)
are genuine schema decisions and MUST be escalated before any implementer
touches D3/D4/D5/D1/D6. peshitta and coptic ship with the TVTMS projection
their own contracts mandate entirely absent (D7/D8). Assume the fix wave is
NOT provably complete until D1 through D8 are closed and E1/E2 are decided.
