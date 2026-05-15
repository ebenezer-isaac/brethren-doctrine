// graph/lexical.cypher

CREATE CONSTRAINT lemma_id IF NOT EXISTS FOR (l:Lemma) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT lemma_strong IF NOT EXISTS FOR (l:Lemma) REQUIRE l.strong IS UNIQUE;
CREATE CONSTRAINT word_id IF NOT EXISTS FOR (w:Word) REQUIRE w.id IS UNIQUE;
CREATE CONSTRAINT morpheme_id IF NOT EXISTS FOR (m:Morpheme) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT verse_id IF NOT EXISTS FOR (v:Verse) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT verse_osisID IF NOT EXISTS FOR (v:Verse) REQUIRE v.osisID IS UNIQUE;
CREATE CONSTRAINT clause_id IF NOT EXISTS FOR (c:Clause) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT phrase_id IF NOT EXISTS FOR (p:Phrase) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT place_id IF NOT EXISTS FOR (p:Place) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT variant_id IF NOT EXISTS FOR (v:Variant) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT tfnode_id IF NOT EXISTS FOR (n:TFNode) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT source_edition IF NOT EXISTS FOR (s:Source) REQUIRE s.edition IS UNIQUE;
CREATE CONSTRAINT strong_code IF NOT EXISTS FOR (s:Strong) REQUIRE s.code IS UNIQUE;
// The witness_ga constraint is declared here for the CBGM/manuscript layer per POC_FINDINGS Delta 11.
// Phase 02 does not write :Witness nodes (CBGM is deferred from v1). Reserved for v1.5.
CREATE CONSTRAINT witness_ga IF NOT EXISTS FOR (w:Witness) REQUIRE w.ga_number IS UNIQUE;

CREATE INDEX word_ref IF NOT EXISTS FOR (w:Word) ON (w.ref);
CREATE INDEX word_strong IF NOT EXISTS FOR (w:Word) ON (w.strong);
CREATE INDEX verse_book_ch_v IF NOT EXISTS FOR (v:Verse) ON (v.book, v.chapter, v.verse);
CREATE INDEX morpheme_strong IF NOT EXISTS FOR (m:Morpheme) ON (m.strong);
CREATE INDEX lemma_id_namespaced IF NOT EXISTS FOR (l:Lemma) ON (l.id);
CREATE INDEX hebrew_greek_bridge IF NOT EXISTS FOR ()-[r:GLOSSES_GREEK_LEMMA]-() ON (r.greek_strong);

CREATE FULLTEXT INDEX word_text IF NOT EXISTS FOR (w:Word) ON EACH [w.surface, w.lemma, w.gloss];
CREATE FULLTEXT INDEX verse_text IF NOT EXISTS FOR (v:Verse) ON EACH [v.text];
