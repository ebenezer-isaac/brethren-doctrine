// graph/cultural.cypher

CREATE CONSTRAINT tradition_slug IF NOT EXISTS FOR (t:Tradition) REQUIRE t.slug IS UNIQUE;
CREATE CONSTRAINT work_id IF NOT EXISTS FOR (w:Work) REQUIRE w.work_id IS UNIQUE;
CREATE CONSTRAINT cultural_chunk_id IF NOT EXISTS FOR (c:CulturalChunk) REQUIRE c.chunk_id IS UNIQUE;
CREATE CONSTRAINT doctrine_slug IF NOT EXISTS FOR (d:Doctrine) REQUIRE d.slug IS UNIQUE;
CREATE CONSTRAINT question_id IF NOT EXISTS FOR (q:Question) REQUIRE q.id IS UNIQUE;

CREATE INDEX work_tradition IF NOT EXISTS FOR (w:Work) ON (w.tradition);
CREATE INDEX work_date IF NOT EXISTS FOR (w:Work) ON (w.date_written);
CREATE INDEX cultural_chunk_anchor IF NOT EXISTS FOR (c:CulturalChunk) ON (c.anchor_id);
CREATE INDEX cultural_chunk_license IF NOT EXISTS FOR (c:CulturalChunk) ON (c.license);

CREATE INDEX has_chunk_rel IF NOT EXISTS FOR ()-[r:HAS_CHUNK]-() ON (r.created_at);
CREATE INDEX addresses_rel IF NOT EXISTS FOR ()-[r:ADDRESSES]-() ON (r.confidence);

CREATE FULLTEXT INDEX cultural_chunk_text IF NOT EXISTS FOR (c:CulturalChunk) ON EACH [c.text];
