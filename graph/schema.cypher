// brethren-doctrine Tier 2 Neo4j schema
// Per docs/TIER_2_SPEC.md §3.3
// Idempotent: every statement is IF NOT EXISTS.

// ============================================================================
// Uniqueness constraints
// ============================================================================
CREATE CONSTRAINT verse_id_uq IF NOT EXISTS
  FOR (v:Verse) REQUIRE v.verse_id IS UNIQUE;

CREATE CONSTRAINT token_strongs_uq IF NOT EXISTS
  FOR (t:Token) REQUIRE t.strongs IS UNIQUE;

CREATE CONSTRAINT sermon_chunk_id_uq IF NOT EXISTS
  FOR (c:SermonChunk) REQUIRE c.chunk_id IS UNIQUE;

CREATE CONSTRAINT sof_chunk_id_uq IF NOT EXISTS
  FOR (c:SOFChunk) REQUIRE c.chunk_id IS UNIQUE;

CREATE CONSTRAINT concept_name_uq IF NOT EXISTS
  FOR (c:Concept) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT figure_name_uq IF NOT EXISTS
  FOR (f:Figure) REQUIRE f.name IS UNIQUE;

CREATE CONSTRAINT movement_name_uq IF NOT EXISTS
  FOR (m:Movement) REQUIRE m.name IS UNIQUE;

CREATE CONSTRAINT confession_name_uq IF NOT EXISTS
  FOR (c:Confession) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT era_name_uq IF NOT EXISTS
  FOR (e:Era) REQUIRE e.name IS UNIQUE;

CREATE CONSTRAINT site_name_uq IF NOT EXISTS
  FOR (s:Site) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT artifact_name_uq IF NOT EXISTS
  FOR (a:Artifact) REQUIRE a.name IS UNIQUE;

CREATE CONSTRAINT source_uri_uq IF NOT EXISTS
  FOR (s:Source) REQUIRE s.uri IS UNIQUE;

// ============================================================================
// Vector indexes (1024 dim, COSINE, voyage-context-3)
// ============================================================================
CREATE VECTOR INDEX verse_embed IF NOT EXISTS
  FOR (v:Verse) ON v.embedding
  OPTIONS { indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'COSINE'
  } };

CREATE VECTOR INDEX sermon_chunk_embed IF NOT EXISTS
  FOR (c:SermonChunk) ON c.embedding
  OPTIONS { indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'COSINE'
  } };

CREATE VECTOR INDEX sof_chunk_embed IF NOT EXISTS
  FOR (c:SOFChunk) ON c.embedding
  OPTIONS { indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'COSINE'
  } };

CREATE VECTOR INDEX concept_embed IF NOT EXISTS
  FOR (c:Concept) ON c.embedding
  OPTIONS { indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'COSINE'
  } };

// ============================================================================
// Composite + B-tree indexes
// ============================================================================
CREATE INDEX verse_bcv IF NOT EXISTS
  FOR (v:Verse) ON (v.book_osis, v.chapter, v.verse);

CREATE INDEX authority_sermon_chunk IF NOT EXISTS
  FOR (c:SermonChunk) ON (c.authority_level);

CREATE INDEX authority_sof_chunk IF NOT EXISTS
  FOR (c:SOFChunk) ON (c.authority_level);

CREATE INDEX sermon_chunk_source_doc IF NOT EXISTS
  FOR (c:SermonChunk) ON (c.source_doc);

CREATE INDEX sof_chunk_section IF NOT EXISTS
  FOR (c:SOFChunk) ON (c.section);

// ============================================================================
// Full-text indexes (Neo4j-side BM25 fallback for §3.3)
// ============================================================================
CREATE FULLTEXT INDEX chunk_text_ft IF NOT EXISTS
  FOR (n:SermonChunk|SOFChunk) ON EACH [n.text];

CREATE FULLTEXT INDEX concept_alias_ft IF NOT EXISTS
  FOR (c:Concept) ON EACH [c.name, c.aliases];
