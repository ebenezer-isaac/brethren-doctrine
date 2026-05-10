# Bible Data Sources for Tier 2 Layer (2026)

Research date: 2026-05-10. Scope: Hebrew OT, Greek NT, Strong's, morphology, English translations, archaeology cross-refs.

---

## 1. Recommended Ingestion Plan (in order)

1. **STEPBible-Data first** (TAHOT + TAGNT). One repo gives Hebrew OT *and* Greek NT with disambiguated extended Strong's, morphology, glosses — already aligned. CC BY 4.0. This is the Tier-2 backbone.
2. **OSHB v2.2** (`openscriptures/morphhb`) as a second Hebrew witness. Public-domain WLC text plus CC-BY lemma/morph. Use it to validate STEPBible's TAHOT and to recover the OSIS XML structure (chapter/verse/word IDs).
3. **MorphGNT/SBLGNT** (`morphgnt/sblgnt`) as a second Greek witness. CCAT-style POS+parsing per word; cross-check against TAGNT.
4. **TBESH + TBESG** (in STEPBible repo) for Hebrew (BDB-abridged) and Greek (Abbott-Smith) lexicon definitions — the "gloss" column for the relational schema.
5. **TTESV** (also STEPBible) — already maps Strong's tags onto ESV English text. Lets you ship interlinear without scraping the ESV API for every verse.
6. **English translations** layered on top:
   - **ESV** via `api.esv.org` (dev key, 5,000/day, 1,000/hr, 60/min, max 500 verses cached).
   - **NLT** via `api.nlt.to` (free non-commercial; anonymous = 50 verses/req, 500/day; keyed = higher).
   - **NIV / NKJV** via `scripture.api.bible` Starter (5,000 calls/mo, pick 3 copyrighted Bibles).
   - **KJV** from any public-domain source (api.bible Starter, or a static SWORD/Zefania module — `bible-api.com` or `wldeh/bible-api` work too).
7. **Open Context** (`opencontext.org/query/`) for archaeology cross-refs. Filter by Levant `bbox` + `allevent-start/-stop`. Send `User-Agent: oc-api-client` or you get blocked.
8. **DAAHL** has no public REST API as of 2026 — site is a PHP front-end over a SQL DB at daahl.ucsd.edu. Treat as reference-only / manual lookup; do not script-scrape (TOU-unfriendly). Use Open Context + Pleiades (gazetteer) for programmatic site data instead.

## 2. Format Normalization Plan (single relational schema)

Canonical key everywhere: **OSIS verse IDs** (`Gen.1.1`, `Matt.5.3`). OSIS book codes per CrossWire's SBL-Handbook-derived list (`Gen`, `Exod`, ..., `Matt`, ..., `Rev`).

```
verse(verse_id PK, book_osis, chapter, verse, testament)
word(word_id PK, verse_id FK, position, surface, lemma, strongs_ext, morph_code, gloss_en, source_tag)
strongs(strongs_ext PK, language[H|G], strongs_base, suffix, headword, definition_short, definition_long)
translation(trans_code PK, name, license, source)        -- ESV, NIV, NKJV, NLT, KJV
verse_translation(verse_id FK, trans_code FK, text)
xref_archaeology(verse_id FK, opencontext_uri, label, period_start, period_stop, geom_geojson)
```

Pipeline:
- TAHOT/TAGNT TSV → row-per-word → load into `word` (Strong's = `strongs_ext`, morph in their compressed code).
- OSHB OSIS XML → second `word` source for cross-validation; do not duplicate, just QA-flag mismatches.
- TBESH/TBESG → `strongs` table.
- TTESV → `verse_translation` for ESV with word-level Strong's already attached.
- ESV/NLT/NIV/NKJV/KJV API pulls → `verse_translation` rows; cache aggressively (everything is static text).
- Open Context queries by bbox/period → `xref_archaeology` linked manually (or via gazetteer matching) to verse_ids that mention the place.

## 3. Per-Source Notes

| Source | License | Format | Freshness | Sync method |
|---|---|---|---|---|
| **STEPBible-Data** (TAHOT/TAGNT/TBESH/TBESG/TTESV) | CC BY 4.0 | Tab-separated UTF-8, `$`-separated multi-record headers | Last formal release 2021; repo actively curated | `git clone`; re-pull quarterly |
| **OSHB / morphhb** | WLC text PD; lemma+morph CC BY 4.0 | OSIS XML; JSON via `morphhb` npm | v2.2, Dec 2021 | `git clone` (or `npm i morphhb` for JSON) |
| **MorphGNT/SBLGNT** | SBLGNT EULA + CC BY-SA on morph | TSV, one word/line, 27 files | v6.12, Mar 2017 (stable) | `git clone` or `pip install py-sblgnt` |
| **ESV API** | Personal/dev free; max 500 verses cached, no text edits | JSON / plain / HTML | Live | REST: `GET /v3/passage/text/`, `Authorization: Token …` |
| **NLT API** (`api.nlt.to`) | Free non-commercial, key via signup | HTML / parsed refs | Live | REST: `?key=…&ref=…` |
| **API.Bible** (NIV, NKJV, NASB, CSB; also KJV) | Starter = 5k/mo non-commercial, 3 copyrighted Bibles | JSON | Live | REST with `api-key` header |
| **Zefania / SWORD modules** | Per-module (NIV/NKJV/NLT redistribution restricted) | XML / SWORD binary | Varies | Use only public-domain modules (KJV, ASV, WEB); read with `pysword` |
| **Open Context** | CC BY (per record) | JSON-LD / GeoJSON-LD | Live | REST: `GET /query/?bbox=…&allevent-start=…`, `User-Agent: oc-api-client` |
| **DAAHL** | Academic, no API | HTML/KML | Static | Manual reference only |

Personal-use note for NIV/NKJV/NLT: the user owns physical copies, so storing a personal local copy from a Sword/Zefania module for offline querying is fine for personal study — but **do not commit copyrighted text to the public repo**. Keep those texts in a gitignored `data/private/` and pull from API.Bible/NLT.to in CI.

## 4. Concrete Next Steps (libraries)

- Python:
  - `pip install py-sblgnt` — Greek NT with morph, native Python API.
  - `pip install pythonbible` + `pythonbible-parser` — OSIS XML parsing & reference normalization.
  - `pip install pysword` — read SWORD modules (KJV, ASV, WEB).
  - `pip install lxml` + custom loader for OSHB OSIS XML (`<w lemma="strong:H0430" morph="HNcmpa">`).
  - `pip install pandas` — load STEPBible TSVs (`pd.read_csv(sep='\t', comment='#')`, then handle `$` sub-records manually).
  - `pip install httpx` (async) for ESV / NLT / api.bible / Open Context calls; wrap with `tenacity` for retry, `diskcache` for response caching.
- Node:
  - `npm i morphhb` — pre-built JSON of OSHB.
  - `npm i bible-passage-reference-parser` (openbibleinfo) — robust ref parser, OSIS output.
- Schema: PostgreSQL with `verse_id text PRIMARY KEY` (OSIS), `tsvector` for text search, `PostGIS` for archaeology geoms. SQLite fine for v1.

Build order:
1. Land STEPBible TSV loader → populate `verse`, `word`, `strongs`.
2. Cross-validate against OSHB and MorphGNT loaders; log diffs.
3. Layer TTESV as the first English text + word-level Strong's join.
4. Add ESV API client with disk cache.
5. Add NLT/NIV/NKJV/KJV via api.bible & nlt.to.
6. Add Open Context client (Levant bbox `[34, 29, 39, 34]`, period filters per book).

## 5. Source Links

- [openscriptures/morphhb (OSHB)](https://github.com/openscriptures/morphhb)
- [OSHB v2.0 release notes](https://github.com/openscriptures/morphhb/releases/tag/v.2.0)
- [STEPBible-Data repo (TAHOT/TAGNT/TBESH/TBESG/TTESV)](https://github.com/STEPBible/STEPBible-Data)
- [morphgnt/sblgnt](https://github.com/morphgnt/sblgnt)
- [py-sblgnt](https://github.com/morphgnt/py-sblgnt)
- [Faithlife/SBLGNT (canonical SBLGNT source)](https://github.com/LogosBible/SBLGNT)
- [ESV API docs](https://api.esv.org/docs/)
- [NLT.TO API docs](https://api.nlt.to/documentation)
- [API.Bible documentation](https://docs.api.bible/guides/bibles/)
- [Open Context services & API](https://opencontext.org/about/services)
- [CrossWire OSIS Book Abbreviations](https://wiki.crosswire.org/OSIS_Book_Abbreviations)
- [DAAHL home (reference-only)](https://daahl.ucsd.edu/DAAHL/Home.php)
- [pythonbible](https://github.com/avendesora/pythonbible)
- [pysword](https://pypi.org/project/pysword/)
- [biblenerd/awesome-bible-developer-resources (curated index)](https://github.com/biblenerd/awesome-bible-developer-resources)
