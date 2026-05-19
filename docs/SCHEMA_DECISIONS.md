# Schema Decisions: Lexical Store

## Overview

This document is the binding node-and-edge contract for the lexical Neo4j store. Each `### Decision` block names the source(s) it governs, states a binding `#### Rule`, attaches a `#### Cypher acceptance query` that the triangle-test runner executes, enumerates `#### Edge cases handled`, and lists every persisted property in a `#### Per-field predicate type` table whose predicates resolve via `tools/predicates_by_type.cypher`. Field names are sourced verbatim from `docs/data_inventory_catalog.json` so every adapter Implementer and Verifier compiles their docstring contract against the same identifiers. The decisions cover the nine lexical adapters, the three procurement adapters (Peshitta, Vulgate Clementine, Coptic SCRIPTORIUM), the 3 John CBGM ingest, the Theographic projection, the three STEPBible brief lexicons, the constraint policy for Strong, Source and TFNode labels, the Verse surface and universal-id policy, and the canonical Strong-key join contract for Lemma and GreekLemma identity (Decision 18). Any change to a decision requires a commit whose subject begins with the literal token `[SCHEMA-REVISION]` so `tools/check_thresholds_immutable.py` does not block the run; this is the only mechanism that may move the count contract. The user-locked exclusions (ECM Catholic Letters beyond 3 John, full LXX Rahlfs, Old Latin Vetus Latina, DSS) live in `docs/data_inventory_catalog.json` under `explicit_deadends[]` and are not re-litigated here. No decision references a confessional or denominational source. Citation source slugs used in Pipeline 2 evidence files match the list in `docs/phase_prompts/pipeline2_verdict.md`.

### Universal Verse identity and the cross-version join key

Every verse-resolving edge keys on the universal `Verse.id`, not on `Verse.osisID`. `Verse.id` is populated for every verse on both testaments. `Verse.osisID` is populated only on Old Testament verses and is null on New Testament verses by the Verse-surface policy (Decision 15), because the OT word-slot adapter is the only `osisID` author. `IN_VERSE` (STEPBible TAHOT/TAGNT, Peshitta, Coptic), `PARALLEL_OF` (ETCBC-parallels), `OPENBIBLE_CROSS_REF` (OpenBible), `MENTIONS` (Theographic), and `NAMED_AT` (STEPBible proper nouns) therefore all resolve their verse endpoint on `Verse.id`. A verse-resolving edge keyed on `osisID` would silently resolve zero on every NT verse; keying on `Verse.id` is what makes these edges correct on both testaments. The one documented exception is TSK `CROSS_REF`, which is keyed on `osisID` and is correct only because every TSK target verse is OT (recorded as an intentional scope boundary in `docs/ARCHITECTURE.md`).

### Single-pass dispatch order is a schema contract

The `ingest/lexical/run.py` DATASETS dispatch order is part of this contract, not an implementation detail. Every `{strong}`-keyed `Lemma` / `GreekLemma` endpoint producer runs before its `{strong}`-keyed consumer, so a single fresh ingest pass lands every `INSTANCE_OF` and `LEX_FOR` edge and a second pass over identical inputs is a true no-op (the triangle test). Concretely: `oshb`, `macula_hebrew`, `bhsa`, `etcbc_phono`, `etcbc_parallels`, `macula_greek`, `morphgnt`, `stepbible_morph_codes`, `stepbible_ttesv`, `stepbible_tbesh`, `stepbible_tbesg`, `stepbible_tahot`, `stepbible_tagnt`, `stepbible_tflsj`, `stepbible_proper_nouns`, `stepbible_tvtms`, `peshitta`, `coptic_scriptorium`, `vulgate_clementine`, `open_cbgm_3_john`, `openbible`, `tsk`, `theographic`. `ttesv` and `tbesh` produce the `{strong}`-keyed lemma floor that `tahot` (`MATCH (b:Lemma {strong})`) and `tagnt` (`MATCH (b:GreekLemma {strong})`) consume, so the producers precede the consumers. `macula_greek` precedes `morphgnt` for the `PARSE_OF` `osis_wpos` join. A consumer whose endpoint producer ran after it would `MATCH` nothing and skip the relationship MERGE, making the ingest non-single-pass; the order above prevents that by construction.

### Decision 1: OSHB-to-MACULA-Hebrew morpheme alignment

#### Rule
OSHB-morphology supplies the canonical morpheme identifier through the `id` field and the unicode surface form through the `text` field, while MACULA-Hebrew supplies the syntactic enrichments keyed by `xml:id` and `ref`. Adapters MUST emit one `Word` node per OSHB record with `osis_word_id = OSHB.id` and MUST attach the MACULA `lemma`, `morph`, `pos`, `gloss`, `stronglemma`, and `strongnumberx` properties only when the MACULA `xml:id` resolves through its embedded OSIS reference to the same `book` and `id` tuple. The join is rejected at adapter time whenever the OSHB `lemma` token differs from the MACULA `lemma` token after Unicode NFC normalisation and whitespace strip, and a per-row rejection is recorded in the snapshot ledger so the triangle test cannot mask drift.

#### Cypher acceptance query
```cypher
MATCH (w:Word {source: 'OSHB-morphology'})
OPTIONAL MATCH (w)-[:HAS_MACULA_ENRICHMENT]->(m:MaculaToken)
WITH count(w) AS total, count(m) AS aligned
RETURN aligned, total, aligned * 1.0 / total AS ratio
  WHERE ratio >= 0.98 AND total > 0
```

#### Edge cases handled
- Functional particles such as the definite article `ha-` carry an OSHB morpheme `id` but no `strongnumberx` in MACULA-Hebrew, so the join MUST skip the Strong attachment without rejecting the row, and the per-field predicate table below records `strongnumberx` as nullable.
- Ketiv-Qere divergence presents two surface tokens for one consonantal slot; the adapter MUST attach the qere reading as a separate `Reading` node linked by `IS_QERE_OF` so the canonical OSHB `text` remains the ketiv and downstream MACULA `morph` parsing applies only to the ketiv lemma.
- Hapax legomena whose `freq_lex` in ETCBC-BHSA equals one occasionally carry a MACULA `gloss` value that is the literal English string `?`, which the adapter MUST normalise to a null gloss so `$pred_string(gloss)` returns false for the unknown rather than appearing as a populated value.

#### Per-field predicate type
OSHB-morphology fields:
| Field | Type | Predicate |
|---|---|---|
| book | string | $pred_string(x) |
| id | string | $pred_string(x) |
| lemma | string | $pred_string(x) |
| morph | string | $pred_string(x) |
| text | string | $pred_string(x) |

MACULA-Hebrew enrichment fields persisted on Word:
| Field | Type | Predicate |
|---|---|---|
| xml:id | string | $pred_string(x) |
| ref | string | $pred_string(x) |
| lemma | string | $pred_string(x) |
| morph | string | $pred_string(x) |
| pos | string | $pred_string(x) |
| gloss | string | $pred_string(x) |
| stronglemma | string | $pred_string(x) |
| strongnumberx | int | $pred_int(x) |
| transliteration | string | $pred_string(x) |

### Decision 2: Louw-Nida domain encoding

#### Rule
MACULA-Greek-Nestle1904 and MACULA-Greek-SBLGNT both carry the `domain` and `ln` fields at roughly 0.92 occurrence rate, and these are the authoritative Louw-Nida domain references that the adapter projects onto a `LouwNidaDomain` node connected to the source `Word` by `IN_DOMAIN`. The Louw-Nida `ln` value is a colon-delimited string of the form `domain:subdomain`, and adapters MUST split it into `domain_code` and `subdomain_code` integer properties on the relationship so semantic-neighbor queries in Pipeline 2 can pre-filter by `domain_code` without parsing strings at query time. The STEPBible TBESG `gloss_line` and `definition` fields cross-link into the same domain node by Strong key.

#### Cypher acceptance query
```cypher
MATCH (w:Word {source: 'MACULA-Greek-Nestle1904'})
WHERE w.ln IS NOT NULL
WITH w, split(w.ln, ':') AS parts
WHERE size(parts) = 2 AND toInteger(parts[0]) > 0
RETURN count(w) AS conformant
```

#### Edge cases handled
- A small slice of MACULA-Greek-Nestle1904 records emit `domain` and `ln` populated with the literal string `n/a` when MARBLE annotators left the slot empty, and the adapter MUST coerce these to a true null so `$pred_string(ln)` returns false and the LouwNidaDomain edge is suppressed.
- Some Strong codes carry multiple Louw-Nida senses across occurrences (polysemy), and the adapter MUST create one `IN_DOMAIN` relationship per distinct Strong-plus-domain tuple rather than averaging or picking the first, so the semantic-neighbor query returns the full sense set.
- MACULA-Greek-SBLGNT and MACULA-Greek-Nestle1904 occasionally disagree on the `ln` value for the same lemma in the same verse owing to text-critical divergences, and the adapter MUST record both with the differentiating `source` property rather than merging on a winner-take-all rule.

#### Per-field predicate type
| Field | Type | Predicate |
|---|---|---|
| xml:id | string | $pred_string(x) |
| ref | string | $pred_string(x) |
| lemma | string | $pred_string(x) |
| normalized | string | $pred_string(x) |
| strong | int | $pred_int(x) |
| morph | string | $pred_string(x) |
| gloss | string | $pred_string(x) |
| domain | string | $pred_string(x) |
| ln | string | $pred_string(x) |
| text | string | $pred_string(x) |

### Decision 3: ETCBC syntax tree shape

#### Rule
ETCBC-BHSA delivers word-level features `g_word_utf8`, `lex_utf8`, `gloss`, `sp`, `pdp`, `vt`, `vs`, `ps`, `nu`, `gn`, `freq_lex`, and `language`, plus a `function` field that the catalog reports at occurrence rate zero because text-fabric surfaces it only on phrase nodes rather than word nodes. The adapter MUST emit one `BhsaWord` node per text-fabric word slot, one `BhsaPhrase` node per phrase slot with its `function` property attached, and one `BhsaClause` per clause slot, with `CONTAINS_WORD` edges from phrase to word and `CONTAINS_PHRASE` from clause to phrase so the Pipeline 2 syntactic-context bundle can walk three layers without joining on string-encoded clause identifiers.

#### Cypher acceptance query
```cypher
MATCH (c:BhsaClause)-[:CONTAINS_PHRASE]->(p:BhsaPhrase)-[:CONTAINS_WORD]->(w:BhsaWord)
WHERE w.lex_utf8 IS NOT NULL AND w.freq_lex >= 1
WITH count(DISTINCT w) AS covered, count(DISTINCT c) AS clauses
RETURN covered, clauses, clauses > 0
```

#### Edge cases handled
- The `function` field is empty on word slots and populated on phrase slots, so the adapter MUST NOT copy `function` onto BhsaWord nodes and MUST source it only from the text-fabric phrase feature, preventing a 100 percent null property on word records.
- ETCBC-parallels supplies pairs of text-fabric node identifiers in `source_node` and `target_and_value`, where `target_and_value` packs the target node and a similarity score in one string, and the adapter MUST split it on the delimiter before persisting a `PARALLEL_OF` edge with a `similarity` float property.
- ETCBC-phono ships a single `phono` field at 0.984 occurrence rate keyed by the same word slot identifier, and the adapter MUST attach it as an optional property on BhsaWord rather than spawning a separate node, because the 1.6 percent null rate reflects ketiv-only slots with no spoken realisation.

#### Per-field predicate type
ETCBC-BHSA fields:
| Field | Type | Predicate |
|---|---|---|
| g_word_utf8 | string | $pred_string(x) |
| lex_utf8 | string | $pred_string(x) |
| gloss | string | $pred_string(x) |
| sp | string | $pred_string(x) |
| pdp | string | $pred_string(x) |
| vt | string | $pred_string(x) |
| vs | string | $pred_string(x) |
| ps | string | $pred_string(x) |
| nu | string | $pred_string(x) |
| gn | string | $pred_string(x) |
| freq_lex | int | $pred_int(x) |
| language | string | $pred_string(x) |
| function | string | $pred_string(x) |

ETCBC-parallels:
| Field | Type | Predicate |
|---|---|---|
| source_node | string | $pred_string(x) |
| target_and_value | string | $pred_string(x) |

ETCBC-phono:
| Field | Type | Predicate |
|---|---|---|
| phono | string | $pred_string(x) |

### Decision 4: Hebrew-to-Greek bridge granularity

#### Rule
MACULA-Hebrew carries a `greek` field at 0.803 occurrence and a `greekstrong` field at 0.686 occurrence, which together encode the Septuagint-witness pairing the Clear team has annotated on the Hebrew lemma. The adapter MUST persist a `BRIDGES_LXX` relationship from the Hebrew `Lemma` node to a `GreekLemma` node keyed by `greekstrong`, with the surface `greek` token attached as an edge property rather than overwriting the Greek lemma's primary surface form, so STEPBible LXX-column data can co-exist without collision. When `greekstrong` is null but `greek` is populated, the adapter MUST resolve the Greek lemma by lemma-string lookup against STEPBible-TBESG, and on failure record the row in a quarantine log without dropping the edge.

#### Cypher acceptance query
```cypher
MATCH (h:Lemma {source: 'MACULA-Hebrew'})-[b:BRIDGES_LXX]->(g:GreekLemma)
WHERE b.greek_surface IS NOT NULL
WITH count(b) AS bridges, count(DISTINCT h) AS hebrew_lemmas
RETURN bridges, hebrew_lemmas, bridges > 0
```

#### Edge cases handled
- Hebrew proper nouns such as theophoric place names route through multiple Greek transliterations across LXX manuscripts, so the adapter MUST tolerate many-to-many edges from one Hebrew lemma to several GreekLemma nodes and MUST NOT collapse them to a winning translation by frequency.
- Hebrew lemmas whose `strongnumberx` is null (because the original was a functional particle) frequently still carry a `greek` string for the agglutinated host, and the adapter MUST attach the bridge to the host lemma's Strong rather than fabricating a Strong identifier for the particle alone.
- STEPBible TAHOT LXX-variant columns (Decision 16) sometimes assign a different Greek lemma than MACULA-Hebrew for the same verse, and the adapter MUST persist both bridges with distinct `source` properties so Pipeline 2 can see the disagreement rather than presenting a false consensus.

#### Per-field predicate type
| Field | Type | Predicate |
|---|---|---|
| lemma | string | $pred_string(x) |
| stronglemma | string | $pred_string(x) |
| strongnumberx | int | $pred_int(x) |
| greek | string | $pred_string(x) |
| greekstrong | int | $pred_int(x) |
| gloss | string | $pred_string(x) |

### Decision 5: TSK versification policy

#### Rule
TSK ships `book_num`, `chapter`, `verse`, and `word_num` as integer keys plus a `keyword` and an `xref_string` payload, and the adapter MUST emit a `CrossRef` node keyed by the tuple `(book_num, chapter, verse, word_num)` and one outbound `CROSS_REF` relationship per parsed reference inside `xref_string`. Reference parsing MUST go through `STEPBible-TVTMS` `rule_type` reconciliation so that TSK's KJV-numbering targets are reprojected to the canonical OSIS reference space adopted by MACULA. OpenBible-cross-refs supplies its own `From Verse`, `To Verse`, and `Votes` columns and the adapter MUST persist its edges on a parallel `OPENBIBLE_CROSS_REF` relationship type, never on the same `CROSS_REF` edge, so provenance filters in Pipeline 2 stay clean.

#### Cypher acceptance query
```cypher
MATCH (a:CrossRef)-[r:CROSS_REF {source: 'TSK'}]->(b:Verse)
WHERE r.osis_target IS NOT NULL AND a.book_num >= 1
WITH count(r) AS tsk_edges
RETURN tsk_edges, tsk_edges > 100000
```

#### Edge cases handled
- TSK references frequently span ranges such as `Ps.119.1-176` and the adapter MUST expand the range into one edge per verse so the count-based acceptance query and Pipeline 2 graph-walk both see the true cardinality rather than a single packed edge with hidden multiplicity.
- A verse number in TSK that exceeds the canonical chapter length under MACULA's OSIS reflects a KJV-only verse subdivision, and the adapter MUST consult `STEPBible-TVTMS` `rule_type` to map it back; rows the TVTMS mapping cannot resolve MUST be tagged with a quarantine flag rather than silently dropped.
- OpenBible-cross-refs `Votes` is occasionally zero for low-confidence community contributions, and the adapter MUST persist the edge with `votes = 0` rather than filtering it out, so downstream relevance ranking is the consumer's choice and not an ingest-time loss.

#### Per-field predicate type
TSK fields:
| Field | Type | Predicate |
|---|---|---|
| book_num | int | $pred_int(x) |
| chapter | int | $pred_int(x) |
| verse | int | $pred_int(x) |
| word_num | int | $pred_int(x) |
| keyword | string | $pred_string(x) |
| xref_string | string | $pred_string(x) |

OpenBible-cross-refs fields:
| Field | Type | Predicate |
|---|---|---|
| From Verse | string | $pred_string(x) |
| To Verse | string | $pred_string(x) |
| Votes | int | $pred_int(x) |

STEPBible-TVTMS fields:
| Field | Type | Predicate |
|---|---|---|
| tradition_a | string | $pred_string(x) |
| ref_a | string | $pred_string(x) |
| tradition_b | string | $pred_string(x) |
| ref_b | string | $pred_string(x) |
| rule_type | string | $pred_string(x) |
| note | string | $pred_string(x) |

### Decision 6: CBGM Witness / Variant / Reading shape (3 John Layer 1 only)

#### Rule
The local asset at `tmp/poc/cbgm/3_john.db` plus `3_john_collation.xml` covers 3 John verses one through fifteen, and the adapter MUST emit `Witness`, `VariantUnit`, and `Reading` nodes for that scope with `READS_AT` edges from Witness to Reading qualified by `variant_unit_id`, and an `ATTESTED_BY` edge from Reading to VariantUnit. The ingest is gated on the `open-cbgm-3-john-sample` citation slug declared in `docs/phase_prompts/pipeline2_verdict.md` and the `MIT` license declared in `docs/LICENSE_TAGGING.md`. ECM Catholic Letters beyond 3 John is excluded; the inventory catalog records the exclusion at `explicit_deadends[0]` with reason and date. Old Latin Vetus Latina is excluded; the inventory catalog records the exclusion at `explicit_deadends[2]`. LXX Rahlfs standalone is excluded and resolved via STEPBible LXX columns; the inventory catalog records the exclusion at `explicit_deadends[1]`.

#### Cypher acceptance query
```cypher
MATCH (w:Witness)-[r:READS_AT]->(rd:Reading)-[:ATTESTED_BY]->(v:VariantUnit)
WHERE v.book = '3John' AND v.chapter = 1 AND v.verse >= 1 AND v.verse <= 15
WITH count(DISTINCT v) AS units, count(DISTINCT w) AS witnesses
RETURN units, witnesses, units > 0 AND witnesses > 0
```

#### Edge cases handled
- A reading lacuna (witness physically illegible at a variant unit) is represented in the open-cbgm collation by an empty reading, and the adapter MUST emit a sentinel `Reading {is_lacuna: true}` rather than skipping the edge, so witness-coverage queries do not mistake silence for support.
- Some variant units in the open-cbgm sample collapse to a single reading attested by every witness (no real variation), and the adapter MUST persist them anyway with one Reading node and N edges, because Pipeline 2 verdict logic needs to see the full attestation profile.
- The 3 John collation contains a small number of corrector hands annotated as `<witness>*` or `<witness>C` suffixes, and the adapter MUST emit each hand as a distinct Witness node linked by `CORRECTOR_OF` rather than merging the hands.

#### Per-field predicate type
Witness:
| Field | Type | Predicate |
|---|---|---|
| siglum | string | $pred_string(x) |
| date_century | int | $pred_int(x) |
| language | string | $pred_string(x) |

VariantUnit:
| Field | Type | Predicate |
|---|---|---|
| variant_unit_id | string | $pred_string(x) |
| book | string | $pred_string(x) |
| chapter | int | $pred_int(x) |
| verse | int | $pred_int(x) |

Reading:
| Field | Type | Predicate |
|---|---|---|
| reading_id | string | $pred_string(x) |
| text | string | $pred_string(x) |
| is_lacuna | bool | $pred_bool(x) |

### Decision 7: Peshitta integration

#### Rule
The procurement entry `peshitta` resolves to the ETCBC text-fabric Syriac NT module at `github.com/etcbc/peshitta`, and the adapter MUST emit `SyriacWord` nodes carrying the consonantal `lex` and `gloss` features plus a `verse_ref` property mapped through `STEPBible-TVTMS` to OSIS. The citation slug `peshitta-text` is registered in `docs/phase_prompts/pipeline2_verdict.md` and `docs/LICENSE_TAGGING.md`, and Pipeline 2 evidence files tag any Peshitta citation with that slug. License is `CC-BY-SA-4.0` per the upstream LICENSE file; ETCBC's Syriac NT module is identical in license to the Hebrew BHSA.

#### Cypher acceptance query
```cypher
MATCH (s:SyriacWord {source: 'peshitta'})
WHERE s.lex IS NOT NULL AND s.verse_ref IS NOT NULL
WITH count(s) AS covered
RETURN covered, covered > 100000
```

#### Edge cases handled
- The Syriac text uses Estrangela glyphs whose Unicode normalisation can shift visual identity when round-tripped through certain editors, and the adapter MUST persist the raw upstream bytes verbatim and emit a derived `lex_nfc` property for normalised lookup rather than overwriting the original.
- Verse boundaries in the Peshitta sometimes split differently from Greek NT verse divisions (notably in 1 John), and the adapter MUST use the TVTMS rule set to map Syriac verse identifiers to OSIS, recording an unresolved-mapping quarantine flag when no rule fires.
- A handful of Peshitta words are tagged by ETCBC with a null `lex` because the manuscript reading is conjectural, and the adapter MUST persist the surface `text` while leaving `lex` null so `$pred_string(lex)` correctly reflects the gap.

#### Per-field predicate type
| Field | Type | Predicate |
|---|---|---|
| siglum | string | $pred_string(x) |
| lex | string | $pred_string(x) |
| lex_nfc | string | $pred_string(x) |
| gloss | string | $pred_string(x) |
| verse_ref | string | $pred_string(x) |
| text | string | $pred_string(x) |
| morph | string | $pred_string(x) |

### Decision 8: Vulgate Clementine integration

#### Rule
The procurement entry `vulgate-clementine` resolves to a Wikisource Special:Export dump covering the full canon under public domain, and the adapter MUST emit `VulgateVerse` nodes keyed by OSIS reference with `text_latin` and an optional `notes` property for chapter rubrics. The citation slug `vulgate-clementine` is registered in `docs/phase_prompts/pipeline2_verdict.md` and `docs/LICENSE_TAGGING.md`, license slug `public_domain`. The Clementine upstream is verse-granular only, so VulgateVerse is intentionally a verse-level node with no word-level tokenisation; this is the correct granularity for the source.

#### Cypher acceptance query
```cypher
MATCH (v:VulgateVerse)
WHERE v.text_latin IS NOT NULL AND v.osis IS NOT NULL
WITH count(v) AS verses
RETURN verses, verses >= 30000
```

#### Edge cases handled
- The Clementine Vulgate numbering differs from the modern critical Vulgate in several places, especially the Psalms numbering offset, and the adapter MUST apply the `STEPBible-TVTMS` rule set to project Clementine verse identifiers to the OSIS reference space before key assignment.
- Deuterocanonical books are part of the Clementine canon and MUST be ingested with their canonical OSIS identifiers; the adapter records a `canon = deutero` property on those VulgateVerse nodes so Pipeline 2 can filter them when the question's canon scope excludes them.
- Wikisource markup occasionally contains transcription footnote markers inside the text body, and the adapter MUST strip these to a separate `transcription_notes` array property rather than leaving them embedded in `text_latin`, preserving the surface form for hashing without losing the apparatus.

#### Per-field predicate type
| Field | Type | Predicate |
|---|---|---|
| osis | string | $pred_string(x) |
| text_latin | string | $pred_string(x) |
| canon | string | $pred_string(x) |
| notes | string | $pred_string(x) |
| transcription_notes | list | $pred_list(x) |

### Decision 9: Coptic SCRIPTORIUM integration

#### Rule
The procurement entry `coptic-scriptorium` resolves to the Coptic SCRIPTORIUM corpus on github at CC-BY 4.0, and the adapter MUST emit `CopticWord` nodes carrying `norm`, `lemma`, `pos`, and `verse_ref` features projected through `STEPBible-TVTMS` to OSIS. The citation slug `coptic-scriptorium` is registered in `docs/phase_prompts/pipeline2_verdict.md` and `docs/LICENSE_TAGGING.md`. Sahidic and Bohairic recensions are persisted with a `dialect` property so Pipeline 2 cross-dialect comparison queries remain trivial.

#### Cypher acceptance query
```cypher
MATCH (c:CopticWord {source: 'coptic-scriptorium'})
WHERE c.lemma IS NOT NULL AND c.dialect IN ['sahidic', 'bohairic']
WITH count(c) AS coverage, c.dialect AS dialect
RETURN dialect, coverage
```

#### Edge cases handled
- Coptic SCRIPTORIUM TT (Tagged Text) format includes editorial supplements within angle brackets that the adapter MUST preserve as a `supplement` boolean property on the affected word rather than dropping or merging them with the main `norm` field.
- Some chapters in the Sahidic corpus are extant only as fragments, and the adapter MUST persist the available CopticWord nodes without forcing every OSIS verse identifier to resolve, recording the fragment coverage in the snapshot ledger so Pipeline 2 can mark fragment-only verses as low-evidence.
- Bohairic and Sahidic occasionally disagree on word division for the same Greek source word, and the adapter MUST emit one CopticWord per upstream token without normalising token boundaries across dialects.

#### Per-field predicate type
| Field | Type | Predicate |
|---|---|---|
| norm | string | $pred_string(x) |
| lemma | string | $pred_string(x) |
| pos | string | $pred_string(x) |
| verse_ref | string | $pred_string(x) |
| dialect | string | $pred_string(x) |
| supplement | bool | $pred_bool(x) |

### Decision 10: Theographic Bible Metadata projection schema

#### Rule
The catalog reports `fields = 0` for `Theographic-Bible-Metadata` because the upstream ships as a folder hierarchy of JSON-and-Markdown documents under `people/`, `places/`, `periods/`, `events/`, `groups/`, and `tribes/` rather than as a single tabular file, so the adapter MUST treat each entity file as a record and project its YAML-frontmatter keys into a typed node schema. The decision recorded here IS the projection schema: `Person`, `Place`, `Period`, `Event`, `Group`, and `Tribe` labels each carry the canonical identifier, the human display name, a normalised verse-reference list, and any cross-entity reference arrays. The adapter MUST NOT invent fields the upstream JSON does not supply, and the snapshot ledger MUST record per-entity field presence so the triangle test detects upstream schema drift on re-ingest.

#### Cypher acceptance query
```cypher
MATCH (p:Person {source: 'Theographic-Bible-Metadata'})
WHERE p.entity_id IS NOT NULL AND p.display_name IS NOT NULL
WITH count(p) AS persons
RETURN persons, persons >= 2000
```

#### Edge cases handled
- Several persons share a common name (numerous Marys, several Zechariahs) and the upstream disambiguates via the file slug, which the adapter MUST preserve as `entity_id` so OSIS verse references resolve to the correct individual rather than collapsing on display name.
- Place entries sometimes carry overlapping ancient and modern names, and the adapter MUST persist each as an alias on the same Place node rather than emitting duplicate nodes, while storing the canonical filename slug as `entity_id`.
- A small number of entity files contain free-form Markdown body text under the YAML frontmatter, and the adapter MUST attach that body as a `description_markdown` property without parsing it into structured fields, because the upstream does not promise schema for the prose body.

#### Per-field predicate type
Person projection:
| Field | Type | Predicate |
|---|---|---|
| entity_id | string | $pred_string(x) |
| display_name | string | $pred_string(x) |
| verses | list | $pred_list(x) |
| description_markdown | string | $pred_string(x) |

Place projection:
| Field | Type | Predicate |
|---|---|---|
| entity_id | string | $pred_string(x) |
| display_name | string | $pred_string(x) |
| aliases | list | $pred_list(x) |
| verses | list | $pred_list(x) |

Period projection:
| Field | Type | Predicate |
|---|---|---|
| entity_id | string | $pred_string(x) |
| display_name | string | $pred_string(x) |
| start_year | int | $pred_int(x) |
| end_year | int | $pred_int(x) |

### Decision 11: STEPBible-TBESH (Hebrew brief lexicon) node shape

#### Rule
STEPBible-TBESH carries `strong_disambig`, `gloss_line`, `base_strong`, `hebrew`, `transliteration`, `pos`, `english`, and `definition` all at 1.0 occurrence rate, and the adapter MUST emit one `BriefLexEntry` node per row keyed by `strong_disambig` with `base_strong` indexed for join performance. The `gloss_line` is the headword summary used in Pipeline 2 anchor-lemma bundles, and the `definition` is the long-form prose the engine cites under the `STEPBible-TBESH` slug. The node MUST carry a `language = 'hebrew'` discriminator so Decision 12 (TBESG) does not collide on Strong identifier ranges.

#### Cypher acceptance query
```cypher
MATCH (l:BriefLexEntry {source: 'STEPBible-TBESH'})
WHERE l.strong_disambig IS NOT NULL AND l.definition IS NOT NULL AND l.language = 'hebrew'
WITH count(l) AS entries
RETURN entries, entries >= 8000
```

#### Edge cases handled
- Some Hebrew Strong codes have a disambiguation suffix (e.g. H1234A and H1234B for distinct senses), and the adapter MUST persist `strong_disambig` verbatim while exposing `base_strong` separately so concordance traversal against MACULA-Hebrew `strongnumberx` can hit the base code without sense suffixes.
- Aramaic portions of the Hebrew canon (parts of Daniel, Ezra) carry their own Strong range, and the adapter MUST tag those entries with `subscript_aramaic = true` while keeping the `language = 'hebrew'` discriminator so the brief-lex node still partitions cleanly from Greek TBESG entries.
- A small set of entries contain Greek transliteration characters in the `transliteration` field for LXX-correspondence notes, and the adapter MUST persist them as-is rather than coercing to ASCII, since the Pipeline 2 embed-text builder downstream depends on the distinct token set including the Greek characters.

#### Per-field predicate type
| Field | Type | Predicate |
|---|---|---|
| strong_disambig | string | $pred_string(x) |
| gloss_line | string | $pred_string(x) |
| base_strong | string | $pred_string(x) |
| hebrew | string | $pred_string(x) |
| transliteration | string | $pred_string(x) |
| pos | string | $pred_string(x) |
| english | string | $pred_string(x) |
| definition | string | $pred_string(x) |

### Decision 12: STEPBible-TBESG (Greek brief lexicon) node shape

#### Rule
STEPBible-TBESG ships `strong_disambig`, `gloss_line`, `base_strong`, `greek`, `transliteration` (occ 0.99), `pos` (occ 0.885), `english`, and `definition`, and the adapter MUST emit one `BriefLexEntry` node per row keyed by `strong_disambig` with `language = 'greek'` so the node label is shared with TBESH while the language partitions remain clean. The `pos` field's 0.885 occurrence reflects a small population of indeclinable particles whose part-of-speech is unknown, and the predicate table records the field as nullable accordingly.

#### Cypher acceptance query
```cypher
MATCH (l:BriefLexEntry {source: 'STEPBible-TBESG'})
WHERE l.strong_disambig IS NOT NULL AND l.greek IS NOT NULL AND l.language = 'greek'
WITH count(l) AS entries
RETURN entries, entries >= 5000
```

#### Edge cases handled
- Some Greek Strong codes correspond to compound lemmas whose `greek` field contains a hyphen joining the component lemmas, and the adapter MUST persist the hyphen verbatim because removing it changes the surface lookup behaviour of downstream `embed_text` for compound-word concordance.
- The `transliteration` 0.99 occurrence reflects entries where STEPBible authors flagged transliteration as ambiguous and left it empty; the adapter MUST leave it null rather than substituting a fallback so `$pred_string(transliteration)` accurately reports the gap.
- Some entries have a `definition` that begins with a parenthetical etymology in Greek script, and the adapter MUST persist the full string without splitting, since Pipeline 2 cites the full definition slot rather than parsed sub-spans.

#### Per-field predicate type
| Field | Type | Predicate |
|---|---|---|
| strong_disambig | string | $pred_string(x) |
| gloss_line | string | $pred_string(x) |
| base_strong | string | $pred_string(x) |
| greek | string | $pred_string(x) |
| transliteration | string | $pred_string(x) |
| pos | string | $pred_string(x) |
| english | string | $pred_string(x) |
| definition | string | $pred_string(x) |

### Decision 13: STEPBible-TFLSJ (LSJ extract) node shape

#### Rule
STEPBible-TFLSJ carries `strong`, `lemma`, `transliteration`, `pos`, `english` (occ 0.991), and `lsj_definition` (occ 0.896) along with two residual `col_6` and `col_7` columns the upstream uses for cross-reference annotations, and the adapter MUST emit one `LsjEntry` node per row keyed by `strong` plus `lemma` together because `strong` is not unique across LSJ sub-entries. The `lsj_definition` is treated as a long-form prose field cited under the `STEPBible-TFLSJ` slug and the per-field predicate table marks `english` and `lsj_definition` as nullable on their respective occurrence rates.

#### Cypher acceptance query
```cypher
MATCH (e:LsjEntry {source: 'STEPBible-TFLSJ'})
WHERE e.strong IS NOT NULL AND e.lemma IS NOT NULL
WITH count(e) AS entries
RETURN entries, entries > 0
```

#### Edge cases handled
- LSJ entries occasionally contain Greek polytonic accents that some downstream consumers strip, and the adapter MUST preserve the accents in `lemma` and provide a derived `lemma_unaccented` property for matching against MACULA-Greek lemmas that may use different accent conventions.
- A non-trivial 10 percent of entries have `lsj_definition` null because STEPBible only excerpted the headword line for those lemmas, and the adapter MUST persist them without rejection so Pipeline 2 anchor-lemma bundles still see the headword.
- LSJ entries sometimes carry abbreviation tokens such as `cf.` and `v.` inside `english`, and the adapter MUST leave the abbreviations in place rather than expanding them, because the abbreviation set is part of the citation grammar Pipeline 2 forwards verbatim.

#### Per-field predicate type
| Field | Type | Predicate |
|---|---|---|
| strong | string | $pred_string(x) |
| lemma | string | $pred_string(x) |
| lemma_unaccented | string | $pred_string(x) |
| transliteration | string | $pred_string(x) |
| pos | string | $pred_string(x) |
| english | string | $pred_string(x) |
| lsj_definition | string | $pred_string(x) |

### Decision 14: Strong / Source / TFNode constraint policy

#### Rule
The lexical graph carries three administrative node labels (`Strong`, `Source`, `TFNode`) whose purpose is cross-source disambiguation, and the policy decision below specifies whether `graph/lexical.cypher` EMITS or DROPS the uniqueness constraint for each. `Strong` is EMITTED as `CREATE CONSTRAINT strong_id_unique IF NOT EXISTS FOR (s:Strong) REQUIRE s.id IS UNIQUE` because Strong identifiers are the canonical join key between MACULA, OSHB, ETCBC, and the three STEPBible brief lexicons. `Source` is EMITTED as a unique constraint on the source slug. `TFNode` (text-fabric node identifier) is EMITTED as a uniqueness constraint on the tuple `(corpus, node_id)` because text-fabric node identifiers are only unique within their corpus.

#### Cypher acceptance query
```cypher
MATCH (s:Strong)
WITH s.id AS sid, count(*) AS dup_count
WHERE dup_count > 1 AND sid IS NOT NULL
WITH collect(sid) AS duplicates
MATCH (src:Source)
WITH duplicates, count(DISTINCT src.slug) AS slug_count, count(src) AS src_total
RETURN size(duplicates) = 0 AND slug_count = src_total
```

#### Edge cases handled
- A Strong identifier with a sense-suffix (H1234A) MUST resolve to the base Strong (H1234) for the uniqueness constraint, which is enforced by storing the suffix in a separate `disambig_suffix` property rather than concatenating into `id`, preventing the uniqueness constraint from rejecting legitimate sense splits.
- The `Source` label carries one node per canonical source slug listed in `docs/LICENSE_TAGGING.md`, and the constraint enforces no two ingest runs collide on slug; the adapter that registers a new slug (e.g. `peshitta-text`) MUST do so once at ingest start, before any record-level write, so the constraint check runs against the registered slug only.
- A `TFNode` collision across corpora would silently corrupt syntactic-context bundles, so the tuple constraint MUST include both `corpus` and `node_id`; ETCBC-BHSA, ETCBC-Peshitta, and ETCBC-syrnt each register their corpus name on every node write to satisfy this.

#### Per-field predicate type
Strong:
| Field | Type | Predicate |
|---|---|---|
| id | string | $pred_string(x) |
| disambig_suffix | string | $pred_string(x) |
| language | string | $pred_string(x) |

Source:
| Field | Type | Predicate |
|---|---|---|
| slug | string | $pred_string(x) |
| license | string | $pred_string(x) |
| redistribute | bool | $pred_bool(x) |

TFNode:
| Field | Type | Predicate |
|---|---|---|
| corpus | string | $pred_string(x) |
| node_id | int | $pred_int(x) |
| otype | string | $pred_string(x) |

### Decision 15: Verse.text population policy

#### Rule
The `Verse` node carries a canonical surface `text` property per OSIS reference, and the adapter that populates it MUST be the MorphGNT-SBLGNT adapter for NT verses (fields `bcv`, `pos`, `parsing_code`, `text`, `word`, `normalized`, `lemma`) and the OSHB-morphology adapter for OT verses (fields `book`, `id`, `lemma`, `morph`, `text`). The population MUST concatenate the per-word `text` field in document order, separated by single spaces, with no normalisation of Hebrew vowel points or Greek diacritics, so the persisted `text` is byte-identical to the upstream surface. Other adapters (MACULA-Greek, MACULA-Hebrew, ETCBC-BHSA) MUST NOT write to `Verse.text` even when they have access to surface tokens, to prevent ingest-order races overwriting the canonical value.

#### Cypher acceptance query
```cypher
MATCH (v:Verse)
WHERE v.text IS NOT NULL AND v.text <> ''
WITH count(v) AS populated, sum(CASE WHEN v.osis STARTS WITH 'OT.' THEN 1 ELSE 0 END) AS ot
RETURN populated, ot, populated >= 31000
```

#### Edge cases handled
- The Hebrew text sometimes contains a maqqef joining two words into one surface unit, and the adapter MUST treat the maqqef as part of the joined token rather than splitting on it, so `Verse.text` reconstruction preserves the upstream surface exactly without inserting whitespace where the manuscript has none.
- Greek NT verses occasionally contain editorial brackets (e.g. doubtful pericopes) and the MorphGNT-SBLGNT adapter MUST persist the bracketed surface verbatim in the per-word `text` field, with the bracket characters retained in `Verse.text` so consumers downstream of the lexical store can decide whether to honour or strip them.
- Some OT verses split differently across editions (e.g. Psalm superscriptions counted as verse one in some traditions and verse zero in others), and the adapter MUST defer the boundary to the OSIS reference attached to each OSHB word identifier rather than re-segmenting, because OSIS is the join key Pipeline 2 walks.

#### Per-field predicate type
MorphGNT-SBLGNT fields:
| Field | Type | Predicate |
|---|---|---|
| bcv | string | $pred_string(x) |
| pos | string | $pred_string(x) |
| parsing_code | string | $pred_string(x) |
| text | string | $pred_string(x) |
| word | string | $pred_string(x) |
| normalized | string | $pred_string(x) |
| lemma | string | $pred_string(x) |

OSHB-morphology fields:
| Field | Type | Predicate |
|---|---|---|
| book | string | $pred_string(x) |
| id | string | $pred_string(x) |
| lemma | string | $pred_string(x) |
| morph | string | $pred_string(x) |
| text | string | $pred_string(x) |

Verse node:
| Field | Type | Predicate |
|---|---|---|
| osis | string | $pred_string(x) |
| text | string | $pred_string(x) |
| canon_section | string | $pred_string(x) |

### Decision 16: STEPBible-TAHOT and STEPBible-TAGNT column coverage

#### Rule
STEPBible-TAHOT and STEPBible-TAGNT both carry seventeen tabular columns the catalog has rendered with placeholder names (`col_2` through `col_16`) because the upstream uses multi-line headers the inventory pass did not unpack, and the adapter MUST resolve those placeholders to their semantic names (e.g. `ref_eng`, `hebrew_words_ketiv`, `lemma_strong`, `morph`, `dictionary_form`, `lxx_lemma`) by reading the upstream README header table and recording the mapping in the snapshot ledger. The adapter MUST emit one `TaggedToken` node per row with the canonical Strong code, the lemma, the morph code, and (when populated) the LXX-variant lemma, so STEPBible LXX columns satisfy the LXX-Rahlfs exclusion noted in `explicit_deadends[1]`.

#### Cypher acceptance query
```cypher
MATCH (t:TaggedToken {source: 'STEPBible-TAHOT'})
WHERE t.strong IS NOT NULL AND t.morph IS NOT NULL
WITH count(t) AS tokens, count(t.lxx_lemma) AS with_lxx
RETURN tokens, with_lxx, tokens >= 300000 AND with_lxx > 0
```

#### Edge cases handled
- The upstream column `col_10` is 0.0 occurrence in the catalog because the column is empty for the sampled rows, but the README documents it as carrying an LXX-variant Strong code that appears only in select books; the adapter MUST persist it when present and the predicate table records it as nullable.
- TAGNT `Spelling variants` and `Meaning variants` columns carry semicolon-delimited lists, and the adapter MUST split on semicolons into a list-typed property so `$pred_list(x)` predicate reports presence honestly rather than measuring the whole concatenated string.
- A small number of TAHOT rows for the Aramaic portions of Daniel carry an Aramaic-language flag in `col_11`, and the adapter MUST surface that flag as a `language` property on the TaggedToken so concordance queries can partition Hebrew and Aramaic without re-parsing the morph code.

#### Per-field predicate type
STEPBible-TAHOT (semantic projection):
| Field | Type | Predicate |
|---|---|---|
| ref_eng | string | $pred_string(x) |
| hebrew_words_ketiv | string | $pred_string(x) |
| strong | string | $pred_string(x) |
| morph | string | $pred_string(x) |
| dictionary_form | string | $pred_string(x) |
| lxx_lemma | string | $pred_string(x) |
| language | string | $pred_string(x) |

STEPBible-TAGNT (semantic projection):
| Field | Type | Predicate |
|---|---|---|
| word_and_type | string | $pred_string(x) |
| greek | string | $pred_string(x) |
| english_translation | string | $pred_string(x) |
| dstrongs_grammar | string | $pred_string(x) |
| dictionary_gloss | string | $pred_string(x) |
| editions | string | $pred_string(x) |
| meaning_variants | list | $pred_list(x) |
| spelling_variants | list | $pred_list(x) |
| sstrong_instance | string | $pred_string(x) |
| alt_strongs | string | $pred_string(x) |

### Decision 17: STEPBible morph-codes and proper-nouns reference tables

#### Rule
STEPBible-morph-codes provides a `code` and `expansion` two-column dictionary plus 53 residual placeholder columns that are sparse or empty in the inventory sample, and the adapter MUST emit one `MorphCode` node per row keyed by `code` with `expansion` as the human-readable parse, so adapter verifiers can look up morphology decoding without inlining the table. STEPBible-proper-nouns provides a `proper_name_entry` headline plus eight populated detail columns and 30 sparse residual columns, and the adapter MUST emit one `ProperNoun` node per row keyed by the headline with the detail columns mapped to typed properties resolved from the upstream README. Sparse columns are not persisted; only columns with occurrence > 0 in the inventory catalog enter the node.

#### Cypher acceptance query
```cypher
MATCH (m:MorphCode {source: 'STEPBible-morph-codes'})
WHERE m.code IS NOT NULL AND m.expansion IS NOT NULL AND size(m.code) > 0
WITH count(m) AS codes
RETURN codes, codes > 100
```

#### Edge cases handled
- A handful of morph codes resolve to multiple expansions because the upstream documents alternative analyses, and the adapter MUST persist all expansions in an `expansions` list-typed property when the row has more than one populated detail column, preventing silent loss of alternative parses.
- The proper-nouns table contains both Hebrew and Greek names in distinct sections, and the adapter MUST tag each ProperNoun node with a `language` discriminator derived from the section the row was parsed from, because the headline field alone does not disambiguate cross-language homographs.
- A small subset of proper-noun entries carry a numeric verse-count column with a non-numeric placeholder when the upstream count is uncertain, and the adapter MUST coerce non-numeric placeholders to a null integer rather than rejecting the row, so `$pred_int(verse_count)` accurately reports the uncertainty.

#### Per-field predicate type
STEPBible-morph-codes:
| Field | Type | Predicate |
|---|---|---|
| code | string | $pred_string(x) |
| expansion | string | $pred_string(x) |
| expansions | list | $pred_list(x) |

STEPBible-proper-nouns (populated projection):
| Field | Type | Predicate |
|---|---|---|
| proper_name_entry | string | $pred_string(x) |
| transliteration | string | $pred_string(x) |
| meaning | string | $pred_string(x) |
| strong | string | $pred_string(x) |
| pos | string | $pred_string(x) |
| language | string | $pred_string(x) |
| verse_count | int | $pred_int(x) |
| first_occurrence | string | $pred_string(x) |

### Decision 18: Canonical Strong join-key contract for Lemma and GreekLemma identity

#### Rule

Strong's number is the single cross-source join key between MACULA-Hebrew, MACULA-Greek, OSHB, ETCBC, and every STEPBible adapter (the Decision 14 premise). The Strong VALUE every source could otherwise carry is fragmented across at least four incompatible encodings (zero-padded versus unpadded digits, uppercase versus lowercase sense suffix, namespaced id versus bare token, string versus integer type); under any such fragmentation an `INSTANCE_OF` or `LEX_FOR` edge silently resolves to zero rows even when every endpoint label is present. This decision freezes ONE canonical Strong string per language and binds it as the join key, so every Strong-keyed join resolves. It does not re-litigate Decisions 1, 2, 4, 11, 12, or 14; it extends them by naming the exact byte form their Strong join keys carry.

Canonical Strong string format, both languages, byte-justified from `ingest/canonical_strongs.py` (the already-committed normaliser, lines 41 to 72): `canonical_strongs(raw, lang)` returns `(<PREFIX><digits.zfill(4)><UPPER suffix or ''>, suffix_or_None)`. The canonical Strong string is `canon[0]`:

- Hebrew: `H` + the Strong number zero-padded to exactly 4 digits + an OPTIONAL single uppercase sense-suffix letter. Examples: `H0430`, `H0001`, `H1254A`, `H7225`. A Strong below 1000 is padded (`H430` is NOT canonical; `H0430` is). A sense suffix is uppercased and kept attached in the string (`H1254a` is NOT canonical; `H1254A` is).
- Greek: `G` + the Strong number zero-padded to exactly 4 digits + an OPTIONAL single uppercase sense-suffix letter. Examples: `G0040`, `G3056`, `G5547`. `G40` is NOT canonical; `G0040` is. Greek augmented Strongs that carry a letter suffix follow the identical suffix rule as Hebrew.
- Strong numbers with 5 digits (the maximum the upstream encodings emit) are left at 5 digits by `zfill(4)` (zfill never truncates); the rule is "minimum 4, zero-padded", which is what `digits.zfill(4)` produces.
- No-Strong / unresolvable token: when `canonical_strongs` raises (empty, malformed, non-Strong), the producing adapter MUST NOT fabricate a Strong. It either skips the Strong attachment (Decision 1 functional-particle rule, Decision 4 null-greekstrong rule) or routes to the adapter's documented sentinel node (e.g. macula_hebrew `GREEK_SENTINEL_ID`). The canonical form is never the empty string.

The single normalization function is `ingest.canonical_strongs.canonical_strongs(raw, lang=...)`; `canon[0]` is the canonical Strong string and `canon[1]` is the separately retained suffix. No adapter may hand-roll a Strong normaliser (the audited defects are exactly the hand-rolled `f"H{int(digits)}{sense}"` / raw-`parts[0]` / `int(strong)` paths). Every adapter that writes or matches a Strong join key MUST route the raw upstream token through this function and use `canon[0]` verbatim as the key value.

Producer binding (the canonical-form authorities):

- `macula_hebrew` writes `Lemma.strong = canon[0]` (canonical string, e.g. `H0430`, `H1254A`) and `Lemma.id = "macula-hebrew-lemma:" + canon[0]`. `macula_hebrew` is the canonical Hebrew Lemma authority. `Lemma.strong` is a STRING.
- `macula_greek` writes `GreekLemma.strong` as the canonical STRING `canon[0]` (e.g. `G0040`). `GreekLemma.strong` is the canonical string, never an int. `GreekLemma.id` namespacing (`<source>:strong-<int:05d>`) is independent of this decision (see the id-namespacing clause); only `.strong` is the canonical join key.

Consumer binding (every Strong-keyed joiner matches the canonical `.strong`, never a hand-rolled value, never an int):

- `stepbible_tahot` INSTANCE_OF: matches `(b:Lemma {strong: canon[0]})` where `canon[0] = canonical_strongs(raw_dStrong,'hb')[0]`. Joining on `Lemma.strong` with the canonical value resolves every Strong below 1000 and every suffixed Strong (an unpadded or lowercase-suffix `Lemma.id` join would resolve zero on those).
- `stepbible_tagnt` INSTANCE_OF: matches `(b:GreekLemma {strong: canon[0]})` where `canon[0] = canonical_strongs(raw_strong_id,'gk')[0]`. The join is on the canonical `GreekLemma.strong` string, not on the producer-specific `GreekLemma.id` namespace.
- `stepbible_tbesh` LEX_FOR: matches `(l:Lemma {strong: canon[0]})` where `canon[0] = canonical_strongs(raw_base_strong,'hb')[0]`, and its self-`MERGE (:Lemma {strong: ...})` uses the same canonical value so it converges on the `macula_hebrew` Lemma rather than minting a divergent duplicate.
- `stepbible_tbesg` LEX_FOR: matches `(g:GreekLemma {strong: canon[0]})` where `canon[0] = canonical_strongs(raw_base_strong,'gk')[0]`.
- `stepbible_tflsj` LEX_FOR: matches `(g:GreekLemma {strong: canon[0]})` where `canon[0] = canonical_strongs(raw_strong,'gk')[0]`, against the canonical string producer value; the `greek_lemma_strong` index (Decision 14, `graph/lexical.cypher`) backs it.
- `stepbible_ttesv` INSTANCE_OF both branches: the Hebrew branch matches `(:Lemma {id: row.lemma_id})` and the Greek branch `(:GreekLemma {id: row.lemma_id})` where `lemma_id = canonical_strongs(raw,lang)[0]`. `ttesv` self-produces its own `Lemma {id: canon[0]}` and `GreekLemma {id: canon[0]}` so each edge is self-consistent and already canonical-string valued. `ttesv` keeps a separate Lemma/GreekLemma id namespace (bare canonical Strong); it is not required to change its key value under Decision 18, and population unification across the disjoint Lemma/GreekLemma populations is a separate data-model question this decision intentionally does not decide.

Lemma.id / GreekLemma.id namespacing clause: `Lemma.id` (`macula-hebrew-lemma:<canon0>`) and `GreekLemma.id` (`<source>:strong-<int:05d>`) are unchanged. The canonical join key is `.strong` only. Keying every cross-source joiner on the canonical `.strong` string (rather than the producer-specific `.id` namespace) changes no node identity, breaks no `lemma_id` / `greek_lemma_id` uniqueness constraint, and does not force the disjoint `ttesv` / `macula-hebrew-greek-lemma` / `macula_greek` GreekLemma populations to merge. `GreekLemma.strong` is the canonical string; no `.id` value changes.

#### Cypher acceptance query

```cypher
MATCH (l:Lemma) WHERE l.strong IS NOT NULL
WITH count(l) AS lem,
     sum(CASE WHEN l.strong =~ '^H\\d{4,}[A-Z]?$' THEN 0 ELSE 1 END) AS bad_heb
MATCH (g:GreekLemma) WHERE g.strong IS NOT NULL
WITH lem, bad_heb, count(g) AS grk,
     sum(CASE WHEN toString(g.strong) =~ '^G\\d{4,}[A-Z]?$' THEN 0 ELSE 1 END) AS bad_grk
RETURN lem, grk, bad_heb, bad_grk, bad_heb = 0 AND bad_grk = 0
```

The query asserts every populated `Lemma.strong` matches `^H\d{4,}[A-Z]?$` and every populated `GreekLemma.strong` matches `^G\d{4,}[A-Z]?$` (a string, not an int: `toString` over a conformant value is idempotent and the regex would reject the bare integer form `40`). Zero non-conformant on both sides is the gate.

#### Edge cases handled

- A Strong below 1000 (`H7`, `G40`, `H430`) MUST appear as 4-digit zero-padded (`H0007`, `G0040`, `H0430`). An unpadded form would silently drop the INSTANCE_OF/LEX_FOR edge for every Strong below 1000. Padding is mandatory and is exactly what `digits.zfill(4)` in `canonical_strongs` produces.
- A sense-suffixed Strong (`H1254A`, `H8675B`) keeps the suffix in the canonical string, uppercased. A lowercased suffix (`H1254a`) is not canonical. The base-Strong-only behaviour (Decision 14 `Strong.id` uniqueness, Decision 11 `base_strong` concordance) is independent: those decisions strip the suffix into `disambig_suffix`; Decision 18 governs the Lemma/GreekLemma `.strong` join key which retains the suffix per `canon[0]`.
- `GreekLemma.strong` is a STRING. Cypher never equates integer `40` to string `'G0040'`, so a Greek Strong join would silently fail against an integer producer value; the canonical form is unambiguously a string.
- No-Strong tokens (functional particles with null `strongnumberx`, malformed upstream cells) do not get a fabricated canonical Strong; the producing adapter follows its existing Decision 1 / Decision 4 skip-or-sentinel rule. The canonical form is never `''`.
- Augmented / extended Strongs (digits beyond 4) are left at their natural width by `zfill(4)` (it pads to a minimum of 4, never truncates), so a 5-digit Strong stays 5 digits with the same `H`/`G` prefix and optional uppercase suffix.

#### Per-field predicate type

Canonical Strong join key (the only fields this decision binds; all other Lemma/GreekLemma fields are governed by Decisions 1, 4, 11, 12, 14 and are unchanged):

| Field | Type | Predicate |
|---|---|---|
| Lemma.strong | string | $pred_string(x) |
| Lemma.id | string | $pred_string(x) |
| GreekLemma.strong | string | $pred_string(x) |
| GreekLemma.id | string | $pred_string(x) |
