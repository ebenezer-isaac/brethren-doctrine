// graph/lexical.cypher
//
// Lexical-store schema for the brethren-doctrine GraphRAG.
// Authority: docs/SCHEMA_DECISIONS.md (17 decisions). Each constraint or index
// here implements one or more decisions; cross-reference by Decision N in the
// adjacent inline /* */ comment.
//
// Verse.text is populated by the MorphGNT-SBLGNT adapter for NT verses and
// by the OSHB-morphology adapter for OT verses per Decision 15. No other
// adapter writes Verse.text.

CREATE CONSTRAINT lemma_id IF NOT EXISTS FOR (l:Lemma) REQUIRE l.id IS UNIQUE /* Decision 1, 11 */;
CREATE CONSTRAINT lemma_strong IF NOT EXISTS FOR (l:Lemma) REQUIRE l.strong IS UNIQUE /* Decision 1, 11 */;
CREATE CONSTRAINT greek_lemma_id IF NOT EXISTS FOR (g:GreekLemma) REQUIRE g.id IS UNIQUE /* Decision 2, 4, 12 */;
CREATE CONSTRAINT word_id IF NOT EXISTS FOR (w:Word) REQUIRE w.id IS UNIQUE /* Decision 1, 2, 15 */;
CREATE CONSTRAINT morpheme_id IF NOT EXISTS FOR (m:Morpheme) REQUIRE m.id IS UNIQUE /* Decision 1 */;
CREATE CONSTRAINT verse_id IF NOT EXISTS FOR (v:Verse) REQUIRE v.id IS UNIQUE /* Decision 15 */;
CREATE CONSTRAINT verse_osisID IF NOT EXISTS FOR (v:Verse) REQUIRE v.osisID IS UNIQUE /* Decision 15 */;
CREATE CONSTRAINT clause_id IF NOT EXISTS FOR (c:Clause) REQUIRE c.id IS UNIQUE /* Decision 3 */;
CREATE CONSTRAINT phrase_id IF NOT EXISTS FOR (p:Phrase) REQUIRE p.id IS UNIQUE /* Decision 3 */;
CREATE CONSTRAINT bhsa_clause_id IF NOT EXISTS FOR (c:BhsaClause) REQUIRE c.id IS UNIQUE /* Decision 3 */;
CREATE CONSTRAINT bhsa_phrase_id IF NOT EXISTS FOR (p:BhsaPhrase) REQUIRE p.id IS UNIQUE /* Decision 3 */;
CREATE CONSTRAINT bhsa_word_id IF NOT EXISTS FOR (w:BhsaWord) REQUIRE w.id IS UNIQUE /* Decision 3 */;
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.entity_id IS UNIQUE /* Decision 10 */;
CREATE CONSTRAINT place_id IF NOT EXISTS FOR (p:Place) REQUIRE p.entity_id IS UNIQUE /* Decision 10 */;
CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.entity_id IS UNIQUE /* Decision 10 */;
CREATE CONSTRAINT period_id IF NOT EXISTS FOR (p:Period) REQUIRE p.entity_id IS UNIQUE /* Decision 10 */;
CREATE CONSTRAINT group_id IF NOT EXISTS FOR (g:Group) REQUIRE g.entity_id IS UNIQUE /* Decision 10 */;
CREATE CONSTRAINT tribe_id IF NOT EXISTS FOR (t:Tribe) REQUIRE t.entity_id IS UNIQUE /* Decision 10 */;
CREATE CONSTRAINT witness_ga IF NOT EXISTS FOR (w:Witness) REQUIRE w.ga_number IS UNIQUE /* Decision 6 */;
CREATE CONSTRAINT witness_siglum IF NOT EXISTS FOR (w:Witness) REQUIRE w.siglum IS UNIQUE /* Decision 6 */;
CREATE CONSTRAINT variant_unit_id IF NOT EXISTS FOR (v:VariantUnit) REQUIRE v.variant_unit_id IS UNIQUE /* Decision 6 */;
CREATE CONSTRAINT reading_id IF NOT EXISTS FOR (r:Reading) REQUIRE r.reading_id IS UNIQUE /* Decision 6 */;
CREATE CONSTRAINT tfnode_tuple IF NOT EXISTS FOR (n:TFNode) REQUIRE (n.corpus, n.node_id) IS UNIQUE /* Decision 14 */;
CREATE CONSTRAINT source_slug IF NOT EXISTS FOR (s:Source) REQUIRE s.slug IS UNIQUE /* Decision 14 */;
CREATE CONSTRAINT strong_id IF NOT EXISTS FOR (s:Strong) REQUIRE s.id IS UNIQUE /* Decision 14 */;
CREATE CONSTRAINT crossref_id IF NOT EXISTS FOR (c:CrossRef) REQUIRE c.id IS UNIQUE /* Decision 5 */;
CREATE CONSTRAINT brief_lex_entry_id IF NOT EXISTS FOR (l:BriefLexEntry) REQUIRE l.strong_disambig IS UNIQUE /* Decision 11, 12 */;
CREATE CONSTRAINT lsj_entry_id IF NOT EXISTS FOR (e:LsjEntry) REQUIRE e.id IS UNIQUE /* Decision 13 */;
CREATE CONSTRAINT morph_code_unique IF NOT EXISTS FOR (m:MorphCode) REQUIRE m.code IS UNIQUE /* Decision 17 */;
CREATE CONSTRAINT proper_noun_entry IF NOT EXISTS FOR (p:ProperNoun) REQUIRE p.proper_name_entry IS UNIQUE /* Decision 17 */;
CREATE CONSTRAINT tagged_token_id IF NOT EXISTS FOR (t:TaggedToken) REQUIRE t.id IS UNIQUE /* Decision 16 */;
CREATE CONSTRAINT louw_nida_id IF NOT EXISTS FOR (d:LouwNidaDomain) REQUIRE d.id IS UNIQUE /* Decision 2 */;
CREATE CONSTRAINT syriac_word_id IF NOT EXISTS FOR (s:SyriacWord) REQUIRE s.id IS UNIQUE /* Decision 7 */;
CREATE CONSTRAINT vulgate_verse_osis IF NOT EXISTS FOR (v:VulgateVerse) REQUIRE v.osis IS UNIQUE /* Decision 8 */;
CREATE CONSTRAINT coptic_word_id IF NOT EXISTS FOR (c:CopticWord) REQUIRE c.id IS UNIQUE /* Decision 9 */;
CREATE CONSTRAINT versification_rule_id IF NOT EXISTS FOR (r:VersificationRule) REQUIRE r.id IS UNIQUE /* Decision 5 */;

CREATE INDEX word_ref IF NOT EXISTS FOR (w:Word) ON (w.ref) /* Decision 1, 2 */;
CREATE INDEX crossref_from_ref IF NOT EXISTS FOR (c:CrossRef) ON (c.from_ref) /* Decision 5 */;
CREATE INDEX crossref_to_ref IF NOT EXISTS FOR (c:CrossRef) ON (c.to_ref) /* Decision 5 */;
CREATE INDEX word_strong IF NOT EXISTS FOR (w:Word) ON (w.strong) /* Decision 1, 14 */;
CREATE INDEX verse_book_ch_v IF NOT EXISTS FOR (v:Verse) ON (v.book, v.chapter, v.verse) /* Decision 15 */;
CREATE INDEX morpheme_strong IF NOT EXISTS FOR (m:Morpheme) ON (m.strong) /* Decision 1, 14 */;
CREATE INDEX lemma_id_namespaced IF NOT EXISTS FOR (l:Lemma) ON (l.id) /* Decision 1 */;
// Lemma.strong is the canonical Hebrew Strong join key (Decision 18). It is
// already index-backed by the lemma_strong UNIQUE constraint (line 13), so no
// separate range index is created here: a uniqueness constraint provides the
// backing index and a duplicate plain index would be rejected / redundant.
// GreekLemma.strong is the canonical Greek Strong join key (Decision 18) and
// has NO uniqueness constraint and NO backing index; tagnt/tbesg/tflsj match
// (:GreekLemma {strong}) so the lookup MUST be index-backed.
CREATE INDEX greek_lemma_strong IF NOT EXISTS FOR (g:GreekLemma) ON (g.strong) /* Decision 4, 12, 14, 18 */;
CREATE INDEX hebrew_greek_bridge IF NOT EXISTS FOR ()-[r:BRIDGES_LXX]-() ON (r.greek_strong) /* Decision 4 */;
CREATE INDEX variant_unit_book_ch_v IF NOT EXISTS FOR (v:VariantUnit) ON (v.book, v.chapter, v.verse) /* Decision 6 */;
CREATE INDEX reading_variant_unit IF NOT EXISTS FOR (r:Reading) ON (r.variant_unit_id) /* Decision 6 */;
CREATE INDEX witness_date IF NOT EXISTS FOR (w:Witness) ON (w.date_century) /* Decision 6 */;
CREATE INDEX bhsa_word_lex IF NOT EXISTS FOR (w:BhsaWord) ON (w.lex_utf8) /* Decision 3 */;
CREATE INDEX bhsa_phrase_function IF NOT EXISTS FOR (p:BhsaPhrase) ON (p.function) /* Decision 3 */;
CREATE INDEX person_display_name IF NOT EXISTS FOR (p:Person) ON (p.display_name) /* Decision 10 */;
CREATE INDEX place_display_name IF NOT EXISTS FOR (p:Place) ON (p.display_name) /* Decision 10 */;
CREATE INDEX brief_lex_base_strong IF NOT EXISTS FOR (l:BriefLexEntry) ON (l.base_strong) /* Decision 11, 12 */;
CREATE INDEX tagged_token_strong IF NOT EXISTS FOR (t:TaggedToken) ON (t.strong) /* Decision 16 */;
CREATE INDEX syriac_word_verse_ref IF NOT EXISTS FOR (s:SyriacWord) ON (s.verse_ref) /* Decision 7 */;
CREATE INDEX coptic_word_verse_ref IF NOT EXISTS FOR (c:CopticWord) ON (c.verse_ref) /* Decision 9 */;
CREATE INDEX coptic_word_dialect IF NOT EXISTS FOR (c:CopticWord) ON (c.dialect) /* Decision 9 */;
CREATE INDEX louw_nida_code IF NOT EXISTS FOR (d:LouwNidaDomain) ON (d.domain_code, d.subdomain_code) /* Decision 2 */;

CREATE FULLTEXT INDEX word_text IF NOT EXISTS FOR (w:Word) ON EACH [w.surface, w.lemma, w.gloss] /* Decision 1, 2, 15 */;
CREATE FULLTEXT INDEX verse_text IF NOT EXISTS FOR (v:Verse) ON EACH [v.text] /* Decision 15 */;
