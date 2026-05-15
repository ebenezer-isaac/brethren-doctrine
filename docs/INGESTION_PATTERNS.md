# Ingestion Patterns

Per-dataset ingestion recipes for Pipeline 1. Read by the orchestrator and by every Pipeline 1 ingest subagent. Findings from the 2026-05-12 PoC validation round are baked in.

## Common conventions

### Canonical Strong's normalization

Five sources use five different Strong's encodings. Pipeline 1 ingest subagents normalize at parse time via `ingest/canonical_strongs.py`.

| Source | Raw encoding | Example | Canonical |
|---|---|---|---|
| MACULA Hebrew | zero-padded 4 digits | `0430` | `H0430` |
| OSHB MorphHB | slash-prefixed lemma tokens | `b/7225`, `1254 a` | `H7225`, `H1254A` |
| STEPBible TAHOT / TAGNT | curly brace with suffix | `{H0430G}` | `H0430G` |
| MACULA Greek | plain digits | `2316` | `G2316` |
| MorphGNT / TAGNT | letter prefix | `G2316` | `G2316` |

Canonical form: leading letter (`H` or `G`), zero-padded to 4 digits, optional suffix letter retained as a separate `strong_suffix` field for cases like `H0430G` (Strong's extension disambiguation).

The `canonical_strongs()` utility:
```python
def canonical_strongs(raw: str) -> tuple[str, str | None]:
    """Returns (canonical_strong, suffix_letter_or_None)."""
```

Unit tests cross-validate by parsing the same lemma from all five sources and confirming the canonical form matches.

### License tagging

Every record and every chunk carries an explicit `license` field at ingest. See `docs/LICENSE_TAGGING.md` for the canonical mapping per source. Records that combine sources (e.g., MACULA Hebrew which fuses WLC + OSHB + MARBLE) carry the strictest applicable license in the top-level `license` field, with a `license_components` map detailing each contributing source.

### Versification routing

All cross-version verse operations route through `ingest/versification_mapper.py`, which is backed by STEPBible TVTMS. TVTMS is a 3-stage mapping (rule type, block scope, tradition columns), not a simple lookup. The mapper exposes:

```python
mapper.resolve(ref="Psa.51.1", from_scheme="english", to_scheme="hebrew") -> "Psa.51.3"
mapper.bridge_set(refs, from_scheme, to_scheme) -> list[ResolvedRef]
```

Every Pipeline 1 subagent that emits verse refs uses OSIS BCV format (`Book.Chapter.Verse`) with the OSIS / KJV English scheme as the canonical store key. TVTMS bridges supply alternate-scheme refs as edge properties.

### Sparse-checkout strategy

For repos larger than 200 MB, ingest subagents perform sparse checkout to pull only the canonical data files needed.

| Repo | Full size | Sparse subset | Sparse size |
|---|---|---|---|
| Clear-Bible/macula-hebrew | ~1.5 GB | `WLC/tsv/*` and `WLC/lowfat/*` only | ~100-200 MB |
| Clear-Bible/macula-greek | ~655 MB | `SBLGNT/tsv/*` and `Nestle1904/tsv/*` only | ~40 MB |
| STEPBible/STEPBible-Data | ~484 MB | `Translators Amalgamated OT+NT/*` and `Translators Versification Mapping/*` | ~50 MB |
| robertrouse/theographic-bible-metadata | ~176 MB | `CSV/*` only | ~30 MB |
| ETCBC/bhsa | n/a (via text-fabric) | text-fabric handles caching | ~270 MB in `~/text-fabric-data/` |

### text-fabric path quirk

Modern `text-fabric` resolves `~/github/...` not `~/text-fabric-data/github/...`. The BHSA bootstrap script either symlinks `~/github -> ~/text-fabric-data/github` or passes `locations=` to `use()`.

```python
from tf.app import use
A = use("ETCBC/bhsa", version="2021", locations="~/text-fabric-data/github")
```

### Pinned SHAs

All git-sourced datasets are pinned at commit SHAs in `pipeline1/lockfile.json`. Refresh is manual: bump the SHA, re-ingest, re-embed. No automatic git pulls.

## Lexical datasets

### MACULA Hebrew

| Field | Value |
|---|---|
| URL | `https://github.com/Clear-Bible/macula-hebrew` |
| Format | TEI lowfat XML + per-verse TSV at `WLC/tsv/macula-hebrew.tsv` |
| Loader | `csv.DictReader` on the TSV is sufficient for word-level ingest |
| License | Composite: WLC text PD; OSHB morphology CC BY 4.0; Clear syntax CC BY 4.0; Cherith glosses CC BY 4.0; UBS MARBLE/SDBH **CC BY-NC 4.0** |
| Neo4j model | `(:Word {id, ref, surface, lemma, strong, morph, gloss, sdbh})-[:NEXT]->(:Word)`; `(:Verse)-[:HAS_WORD]->(:Word)`; `(:Clause)-[:CONTAINS]->(:Word)`; `(:Phrase)-[:HEAD]->(:Word)`; `(:Lemma {lemma, strong})-[:OCCURS_AS]->(:Word)` |
| Qdrant payload | Embed gloss + 5-word surface window; payload `{id, ref, lemma, strong, morph, gloss, book, ch, v, source: "macula-hebrew", license: <split per field>}` |
| Gotchas | Multiple versification schemes present; Ketiv/Qere encoded via OSHB conventions; MARBLE/SDBH coverage ~90%; **MARBLE word-sense data is CC BY-NC**, flag in payload `license_components` |
| Hebrew↔Greek bridge | Each `<w>` carries `greek` and `greekstrong` cross-reference attributes. Ingest these as `(:Word)-[:GLOSSES_GREEK_LEMMA {greek, greekstrong}]->(:Lemma)` edges. Free LXX bridge. |
| Expected counts | ~305k Hebrew word tokens; ~17k unique lemmas |

### MACULA Greek

| Field | Value |
|---|---|
| URL | `https://github.com/Clear-Bible/macula-greek` |
| Format | TEI lowfat XML + TSV per source variant under `Nestle1904/` and `SBLGNT/` |
| Loader | `csv.DictReader` on `SBLGNT/tsv/macula-greek-SBLGNT.tsv`. 27 columns including `english`, `mandarin`, `gloss`, `domain` (Louw-Nida), `ln`. |
| License | Nestle1904 PD; **SBLGNT text under SBLGNT EULA** (free non-commercial; ≤ 500 verses per year without separate license); Clear syntax CC BY 4.0; MARBLE Louw-Nida CC BY-NC 4.0 |
| Neo4j model | Same as MACULA Hebrew, plus `:Source {edition: "Nestle1904" | "SBLGNT"}` on each `:Word`. |
| Qdrant payload | Embed gloss + 5-word window; payload `{id, ref, lemma, strong, morph, gloss, louw_nida_domain, source: "macula-greek-N1904" | "macula-greek-sblgnt"}` |
| Gotchas | SBLGNT includes pericope adulterae per Clear's 2023-07-10 import; Nestle1904 ≠ NA28 (use TAGNT for NA28 readings); Louw-Nida domains require attribution and are NC |
| Expected counts | ~138k Greek NT word tokens; ~5,500 unique lemmas |

### STEPBible-Data (TAHOT / TAGNT / TVTMS / TTESV)

| Field | Value |
|---|---|
| URL | `https://github.com/STEPBible/STEPBible-Data` |
| Format | TSV with ~78-line `#`-prefixed comment header; column-header row that looks like data. Filter via regex `^[1-3]?[A-Z][a-z]{2}\.\d+\.\d+#\d+` on first cell. |
| Loader | Tiny custom parser; skip the comment header, parse columns |
| License | **CC BY 4.0** for TAHOT, TAGNT, TVTMS. **TTESV is CC BY-NC 4.0** (different from rest of repo). Tag explicitly. |
| Neo4j model | Add `(:Lemma)-[:HAS_STRONG]->(:Strong {code, ext})`; `(:Variant {edition})-[:READING_OF]->(:Word)` for TAGNT positional/meaning variants over NA27/NA28/TR/SBLGNT/Treg/Byz/WH/THGNT (per-word edition flags). For TVTMS: `(:VerseRef)-[:MAPS_TO {scheme, rule_type}]->(:VerseRef)`. |
| Qdrant payload | TTESV gives ESV-phrase aligned to Strong's + Hebrew/Greek lemma. Embed the ESV phrase; payload `{esv_phrase, strong, lemma_gk_hb, source: "stepbible-ttesv", license: "CC-BY-NC-4.0"}`. |
| Gotchas | Extended Strong's (`H0430A`) back-compat via stripping suffix letter; TAGNT marks editions as bitmask; TVTMS is the canonical versification bridge; TEHMC/TEGMC morphology codes are supersets of OSHB/Robinson |
| Expected counts | TAHOT: ~305k Hebrew tokens; TAGNT: ~138k Greek tokens; TVTMS: ~hundreds of mapping rules |

### OSHB MorphHB

| Field | Value |
|---|---|
| URL | `https://github.com/openscriptures/morphhb` (tag `v.2.2` or later) |
| Format | OSIS XML under `wlc/` |
| Loader | `lxml.etree` with OSIS namespace |
| License | Text PD (WLC); lemma + morphology CC BY 4.0 |
| Neo4j model | Same `:Word` schema as MACULA Hebrew; use OSHB `xml:id` as alternate key |
| Qdrant payload | Skip. Covered by MACULA Hebrew. OSHB ingested only as fallback morphology source. |
| Gotchas | Ketiv/Qere encoded as `type="x-ketiv"` on `<w>`; maqqef entries have type flag (don't double-count); Hebrew word vs morpheme boundary disagrees with MACULA (OSHB collapses prefixes into one `<w>` with slash-prefixed lemma like `b/7225`; MACULA splits into morphemes). Neo4j carries both: `(:Word)-[:HAS_MORPHEME]->(:Morpheme)`. |
| Expected counts | Gen 1:1 has 7 `<w>` elements (collapsed) vs MACULA's 11 morphemes |

### MorphGNT (SBLGNT)

| Field | Value |
|---|---|
| URL | `https://github.com/morphgnt/sblgnt` |
| Format | Plain-text columnar files, **space-delimited** (not tab), one per book. 7 columns: BBCCVV, POS, parsing, text, word, normalized, lemma |
| Loader | Direct `.txt` parse. **`pysblgnt` is dead on PyPI**; do not depend on it. |
| License | SBLGNT text under SBLGNT EULA; morphology + lemmatization **CC BY-SA 4.0** |
| Neo4j model | `:Word {source: "morphgnt-sblgnt"}` reconciled to MACULA Greek SBLGNT by BCV + wordnum |
| Qdrant payload | Skip. MACULA Greek covers. MorphGNT as canonical parse-code source for citations. |
| Gotchas | CC-BY-SA on morphology means SA-propagation for derivatives; cannot be used in a Greek-English diglot without separate SBL license; parse codes are MorphGNT's own scheme (use the `morphgnt/sblgnt` wiki expansion table) |
| Expected counts | John 1:1 has exactly 17 tokens; θεός at positions 12 and 14 (not position 4, historical brief was wrong) |

### TSK (Treasury of Scripture Knowledge)

| Field | Value |
|---|---|
| Status | Use OpenBible's TSK-derived cross-refs (recommended) over raw TSK. The raw 1880 TSK is PD; OpenBible already merges TSK + vote-weighted user data. |
| URL fallback | CrossWire SWORD module; `narthur/tsk-cli` for parser reference |
| License | Public domain |
| Neo4j model | `(:Verse)-[:CROSS_REF {source: "tsk", votes, rank}]->(:Verse)` |
| Qdrant | Skip. Graph-only. |
| Gotchas | Versification: original TSK uses KJV scheme; remap via TVTMS on ingest |

### OpenBible cross-references

| Field | Value |
|---|---|
| URL | `https://www.openbible.info/labs/cross-references/cross_references.zip` |
| Format | TSV: `From_Verse`, `To_Verse`, `Votes` |
| Size | 2 MB zipped, ~10-15 MB unzipped |
| License | CC BY |
| Loader | Trivial; `pandas.read_csv(delimiter="\t")` |
| Neo4j model | `(:Verse {osisID})-[:CROSS_REF {votes, source: "openbible"}]->(:Verse)` |
| Qdrant | Skip. Graph-only. |
| Gotchas | **`To Verse` can be a range** (e.g. `Rom.1.19-Rom.1.20`). Explode at ingest into multiple edges (do NOT store as range property). Direction is asymmetric: A to B does not imply B to A (keep directed, union at query time). |
| Expected counts | **~344,799 edges** (verified by H7 PoC) |
| Refresh | Manual; monthly drift; pin to a release date |

### Theographic Bible Metadata

| Field | Value |
|---|---|
| URL | `https://github.com/robertrouse/theographic-bible-metadata` |
| Format | CSV (`/CSV/`) + parallel JSON (preferred for nested data) |
| Loader | `pandas.read_csv` for CSV mode; `json` for JSON mode |
| License | **CC BY-SA 4.0** |
| Neo4j model | Native fit: `(:Person)`, `(:Place {lat, lon})`, `(:Event {start, end})`, `(:Book)`, `(:Verse)`; relationships `:MENTIONS`, `:OCCURRED_AT`, `:FATHER_OF`, `:MEMBER_OF`, `:PARTNER_OF`, `:CHILD_OF` |
| Qdrant payload | Embed each `Person.dictText` (Easton-style bio) + name aliases; payload `{theographic_id, name, gender, source: "theographic", license: "CC-BY-SA-4.0"}` |
| Gotchas | CC-BY-SA propagates to derivatives; array fields like `verses` are comma-separated OSIS refs with hyphen ranges; `Easton.csv` contains 19th-c. Easton's Dictionary entries (useful but archaic) |
| Expected counts | ~3,069 person rows; ~1,600 places |

### ETCBC BHSA (Hebrew syntax)

| Field | Value |
|---|---|
| Access | `pip install text-fabric` then `from tf.app import use; A = use("ETCBC/bhsa", version="2021")` |
| Format | Text-Fabric `.tf` files (one per feature) |
| Size | ~270 MB in `~/text-fabric-data/` |
| License | **CC BY-NC 4.0** with persistent identifier `10.17026/dans-z6y-skyh`. Personal RAG OK; commercial use requires DBG consent. |
| Neo4j model | `(:TFNode {tf_id, otype})` plus typed labels for `Book/Chapter/Verse/Sentence/Clause/Phrase/Word/Lex`. Map TF `oslots` to `[:HAS_SLOT]` edges. Carry `pargr`, `instruction`, `function`, `typ` as properties. |
| Qdrant payload | Embed `lex_utf8` + English `gloss` + `function` + `typ`; payload `{tf_node, book, ch, v, lex, gloss, source: "bhsa", license: "CC-BY-NC-4.0"}` |
| Gotchas | NC license. Keep `license_components` field; never bulk-export verbatim feature dumps; versification differs from WLC/MACULA in a handful of poetic books; multiple BHSA versions co-resident (pin to `2021` per release notes "most consistent ever"); `language` feature uses ISO codes `hbo`/`arc` |
| Expected counts | ~426,000 word nodes; full Hebrew Bible coverage |
| text-fabric quirk | `use()` resolves `~/github/...`; symlink or pass `locations=` |

### INTF NTVMR (CBGM, ECM-published books only)

| Field | Value |
|---|---|
| **Status** | **DEFERRED FROM v1.** open-cbgm works on Windows (PoC H7 PASS). 3 John MIT-licensed sample available. Full Catholic Letters TEI requires INTF outreach. User decision 2026-05-12 to skip CBGM entirely in v1 and resume after a 3 John pilot proves value. |
| URL (consumer) | `https://github.com/jjmccollum/open-cbgm-standalone/releases/tag/v2.0` (pre-built Windows binaries) |
| URL (data) | `https://raw.githubusercontent.com/jjmccollum/open-cbgm/master/examples/3_john_collation.xml` (sample), INTF NTVMR for full transcriptions |
| Format | TEI XML in IGNTP/INTF flavour (open-cbgm parses this flavour only) |
| License | Transcriptions CC BY 4.0; open-cbgm code MIT; ECM scholarly apparatus © DBG/INTF |
| Neo4j model (when revived) | Sub-graph under lexical store: `(:Witness {GA_number})`, `(:VariantUnit {book, ch, v, vu_id})`, `(:Reading {label, text})-[:READING_OF]->(:VariantUnit)`, `(:Witness)-[:ATTESTS {certainty}]->(:Reading)`, `(:Reading)-[:DERIVES_FROM]->(:Reading)`, `(:Witness)-[:COHERENCE {score, agreement}]->(:Witness)` |
| Coverage | ECM-published: Catholic Letters, Acts, Mark, Revelation. Matthew 2026. Rest by ~2030. |

## Cultural sources

### Common conventions for cultural scraping

- Politeness: 2-second delay between HTTP requests to the same domain.
- User-Agent: `BiblicalDoctrineEngine/0.1 (personal research; contact:<owner email>)`.
- robots.txt respected.
- Chunk size: paragraph-level for prose (~300-500 tokens), per-article for confessions, per-Q&A for catechisms, per-canon for conciliar decrees.
- License-aware. Every chunk carries an explicit license tag.
- Curly quotes preserved (NFC normalization happens downstream, not at scrape time).
- `doctrine_tags` is empty at scrape; the `cultural_autotag` phase fills it.

### CCEL (patristic, ANF / NPNF / Schaff)

| Field | Value |
|---|---|
| Primary | `https://www.ccel.org` (ThML XML / HTML) |
| Alternate | `https://github.com/gregorycrane/nicenefathers` (TEI for ANF vols 1-10 only; last commits 2014; partial) |
| License | Text PD (pre-1923 translations); CCEL editorial markup released for reuse |
| Anchor | ThML `<verse>` and `<pb n="...">` give stable paragraph IDs; chunk per ThML `<p>` inside `<div3>` |
| Gotchas | OCR quality varies; NPNF not in gregorycrane repo; some auxiliary indexes need scraping |

### Vatican.va (Catholic magisterial)

| Field | Value |
|---|---|
| Primary | `https://www.vatican.va/archive/ENG0015/_INDEX.HTM` (CCC), `https://www.vatican.va/content/<pope>/<lang>/encyclicals/documents/...html` |
| Anchor | CCC paragraphs (`CCC.232`); encyclical paragraphs; Vatican II constitutions by article (`DV.9`, `LG.16`, etc.) |
| License | © Libreria Editrice Vaticana; non-commercial educational use is the widespread fair-use practice; **redistribute: false** on all chunks |
| Gotchas | No formal sitemap; walk via table-of-contents pages; light Cloudflare; respect robots.txt |

### Book of Concord (Lutheran)

| Field | Value |
|---|---|
| Primary | `https://bookofconcord.org` |
| Anchor | Per confession (Augsburg, Apology, Smalcald, Small / Large Catechism, Formula of Concord), per numbered article or paragraph |
| License | Older translations PD; modern Tappert / Kolb-Wengert © (do NOT bulk-ingest those; flag chunks if they come from modern editions) |
| Gotchas | Curly-quote encoding; older translations preferred for redistribution |

### Westminster Confession of Faith + Larger / Shorter Catechisms (Reformed)

| Field | Value |
|---|---|
| Primary | `https://www.opc.org/confessions.html` (canonical); `https://reformed.org` (fallback) |
| Anchor | `WCF.<chapter>.<paragraph>`; `WLC.<question_number>`; `WSC.<question_number>` |
| License | Public domain (1646-47 text) |

### 1689 London Baptist Confession (Reformed Baptist)

| Field | Value |
|---|---|
| Primary | `https://www.the1689confession.com`; `https://founders.org/1689/` |
| Anchor | `1689.<chapter>.<section>` |
| License | Public domain |

### Heidelberg Catechism (Reformed)

| Field | Value |
|---|---|
| Primary | `https://www.crcna.org` or `https://www.heidelberg-catechism.com/en/lords-days/<n>.html` |
| Anchor | `HC.LD<n>.Q<n>` (Lord's Day + Question) |
| License | Public domain |

### Belgic Confession + Canons of Dort (Reformed)

| Field | Value |
|---|---|
| Primary | `https://www.crcna.org` |
| Anchor | `Belgic.<article>`; `Dort.<head>.<article>` |
| License | Public domain |

### Thirty-Nine Articles + BCP 1662 (Anglican)

| Field | Value |
|---|---|
| Primary | `https://justus.anglican.org` (TLS-fragile per PoC; use HTTPS only, accept SSL handshake fallback) |
| Alternate | `https://en.wikisource.org/wiki/Thirty-Nine_Articles_of_Religion` |
| Anchor | `39A.<article_number>`; BCP per service / collect / canticle |
| License | 1571 PD; BCP 1662 PD; BCP 1979 has US Episcopal © |
| Gotchas | TLS handshake failure (SSLv3 alert) on justus.anglican.org, automatic fallback to Wikisource |

### UMC Articles of Religion (Methodist)

| Field | Value |
|---|---|
| Primary | `https://www.umc.org/en/content/articles-of-religion-of-the-methodist-church` |
| Anchor | `UMC.A<article_number>` |
| License | 1784/1808 PD; modern Discipline glosses © UMPH (flag those) |

### Schleitheim Confession (Anabaptist)

| Field | Value |
|---|---|
| Primary | `https://en.wikisource.org/wiki/Schleitheim_Confession` (recently 404, verify) |
| Alternate | `https://anabaptists.org/history/the-schleitheim-confession.html` |
| Anchor | `Schleitheim.A<article_number>` (1-7) |
| License | Public domain |
| Gotchas | Wikisource slug drift. Re-probe on 404. |

### AG Fundamental Truths (Pentecostal)

| Field | Value |
|---|---|
| Primary | `https://ag.org/Beliefs/Statement-of-Fundamental-Truths` |
| Anchor | `AG.A<number>` (1-16) |
| License | © General Council of the Assemblies of God; **redistribute: false**; personal-use ingest only |

### OCA topical articles (Eastern Orthodox)

| Field | Value |
|---|---|
| Primary | `https://www.oca.org/orthodoxy/the-orthodox-faith` (Hopko's *Orthodox Faith*) |
| Anchor | per chapter / topic |
| License | © OCA / Hopko estate; **redistribute: false**; personal-use ingest only |

### BrethrenArchive + STEM Publishing (Plymouth Brethren)

| Field | Value |
|---|---|
| Primary | `https://www.brethrenarchive.org` (issue-level PDFs + HTML); `https://www.stempublishing.com` (Darby, Kelly, Mackintosh, Bellett, Stoney HTML) |
| Anchor | per author + work + chapter / section |
| License | Most authors d. before 1928, so PD. Modern editorial layer © |

### Conciliar texts (early ecumenical councils)

| Field | Value |
|---|---|
| Primary | `https://en.wikisource.org` (Wikisource), NPNF series 2 vol XIV (Percival) via CCEL |
| Anchor | `Nicaea325.Canon.<n>`, `Chalcedon451.Definition`, etc. |
| License | Public domain (NPNF translation pre-1923) |
| Gotchas | Tanner's *Decrees of the Ecumenical Councils* is © Brill; do not use that translation |

### Existing parsed/ Brethren Tier 1 corpus

| Field | Value |
|---|---|
| Source | `parsed/*.json` in this repo (15 JSONs from prior `ingest-sermons` skill runs) |
| Tradition | `plymouth-brethren` |
| Anchor | `parsed.<doc_slug>.<chunk_index>` |
| License | `parsed-sanitized`; redistribute: false (private teaching notes) |
| Notes | Ingest into cultural store under tradition=plymouth-brethren. Brethren on trial, not the rubric. |

## Refresh model

- Per-dataset pinned SHA in `pipeline1/lockfile.json`.
- Refresh is a manual decision per dataset.
- OpenBible re-pulled monthly is acceptable (edge count drifts by hundreds).
- BHSA version pinned at `2021` per release notes.
- INTF NTVMR transcriptions pulled per-book on activation.
- Cultural sources re-scraped quarterly with re-probing for link rot.
