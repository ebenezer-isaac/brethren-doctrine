# Hybrid Search + Reranking, 2026 Research

Scope: brethren-doctrine GraphRAG. Tens of thousands of chunks max, single-digit QPS, personal use, theology-domain queries spanning theme, scripture-anchored, exact-name, conceptual, and comparative intents.

---

## 1. Recommended Retrieval Pipeline

Three stages, all server-side in Qdrant where possible. Numbers tuned for our corpus size and QPS.

```
Stage 0, Query routing (cheap, classify intent)
   exact-name / scripture-ref  →  weight BM25 0.7, dense 0.3
   conceptual / comparative    →  weight BM25 0.3, dense 0.7
   theme                       →  balanced 0.5 / 0.5

Stage 1, Parallel retrieval, K=80 each
   1a. Dense vectors (Voyage-3-large or text-embedding-3-large), top-80
   1b. Sparse BM25 (Qdrant native, IDF on), top-80
   Optional Stage 1c (graph queries): Neo4j Cypher hop-1 from any
   matched scripture/person/place node, cap 40 chunks

Stage 2, Fusion, K_in≈200 → K_fused=60
   Weighted RRF (k=60) with per-source weights from Stage 0 router.
   RRF chosen over alpha-weighted: scores from BM25 vs cosine
   live in different distributions and naive normalization is brittle.

Stage 3, Cross-encoder rerank, K_fused=60 → K_rerank=10
   Single-stage rerank with BGE-reranker-v2-m3 (self-hosted) OR
   Cohere Rerank 3.5 (hosted). Skip the cheap-then-expensive
   two-stage; at K=60 the marginal latency from a tiny first-pass
   reranker is not worth the orchestration complexity at our scale.

Stage 4, Authority-aware score boost (Qdrant score_boost
   formula or in-process), then truncate to top-K_final (5-8 for
   LLM context, 20+ for browsing UI).
```

Why these K values: ZeroEntropy and Pinecone consistently show 50-100 candidates is the sweet spot for cross-encoder rerankers; below 25 you lose recall on hard queries, above 100 you pay latency without quality lift on a small corpus. Qdrant's own hybrid examples use 25/25 → 50; we go higher (80/80 → 60) because theological corpora reward recall (paraphrase-heavy, dense cross-references).

## 2. Recommended Reranker

**Primary: BGE-reranker-v2-m3** (self-hosted, GPU optional).
- ~50-100ms per 60-doc batch on a modern GPU, ~130ms per 16-pair batch on CPU
- nDCG@10 within 2-3 points of Cohere Rerank 3.5 / Voyage Rerank-2.5 on most BEIR-style benchmarks
- Multilingual (Hebrew/Greek interlinear friendly), open weights, no API spend, no PII egress
- Drop-in for sentence-transformers and FastEmbed

**Fallback if you want zero ops: Cohere Rerank 3.5** ($2/1k searches range, ~600ms p95). Use only if you skip GPU. Voyage Rerank-2.5 is competitive but no clear edge for English+biblical text over BGE-v2-m3.

**Avoid for now:** LLM-as-reranker (Zerank, GPT cross-encoder). Adds 1-3s latency for marginal gain at our scale; better spent on a richer Stage 4.

## 3. BM25 Implementation

**Use Qdrant native sparse vectors with IDF modifier** (Qdrant >= 1.15.2, BM25 model from FastEmbed or Qdrant Cloud Inference).

Why not the alternatives:
- **Tantivy** is faster (~6.5x vs Elasticsearch) but is a second store to keep in sync, not worth it at <50k chunks
- **Elastic / OpenSearch** are overkill for personal use; ops burden is real
- **pgvector + FTS** would require swapping the whole vector store
- **Neo4j full-text** works (`HybridRetriever` in neo4j-graphrag-python uses it), keep this option only if you decide Neo4j becomes the primary retrieval store; otherwise mirror chunks into Qdrant and keep Neo4j for graph traversal

Config sketch:
```python
client.create_collection(
    "chunks",
    vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
    sparse_vectors_config={
        "bm25": SparseVectorParams(modifier=Modifier.IDF)  # server-side IDF
    },
)
```

Then a single Query API call with `prefetch=[dense_query, sparse_query]` and `query=FusionQuery(fusion=Fusion.RRF)`.

## 4. Incorporating `authority_level` Into Final Ranking

Two viable layers. Use both.

**Layer A, Qdrant Score Boost (post-rerank, in-engine, v1.14+).**
After RRF + cross-encoder produces a normalized relevance score `r in [0,1]`, apply:

```
final = r + 0.08 * (authority_level / max_authority)
      + 0.04 * recency_decay(date)
      - 0.05 * is_speculative_flag
```

Keep weights small (<=10% of `r`); rerankers already encode topical relevance and you don't want authority to override a clearly-better chunk. The 0.08 cap roughly equals one rerank-rank slot at our K, meaningful but not dominating.

**Layer B, Authority as a re-ranking input feature.** Most cross-encoders don't read structured metadata, but you can prepend a tiny authority tag to the document text before reranking, e.g. `[authority:high] [type:sermon] {chunk_text}`. BGE-reranker-v2-m3 picks up on these tokens; tested in legal/medical RAG with measurable nDCG lift. Keep tags short, they consume the reranker's 512/8192 token budget.

Do NOT bake authority into the dense or sparse retrieval scores directly, it pollutes recall and is hard to debug.

## 5. ColBERT / ColPali, Not Yet for Us

ColBERTv2 and Jina-ColBERT-v2 are production-ready in Qdrant via multivector support, and ColPali is brilliant for visual/PDF-layout corpora. But:
- 1k+ vectors per chunk → ~30-100x storage vs single-vector
- Ingest cost and index build time scale poorly even at our size
- For text-only theology with strong dense + BM25 + reranker baseline, late-interaction's ~3-5 nDCG@10 lift doesn't justify the complexity

Revisit if/when you index PDF page-images of original sermons or Hebrew/Greek manuscript scans (then ColPali becomes very interesting).

## 6. Concrete Next Steps

1. Enable Qdrant sparse vectors with `Modifier.IDF` on the chunks collection; backfill BM25 sparse vectors via FastEmbed `Qdrant/bm25`.
2. Implement intent router (regex + small classifier) producing `{bm25_w, dense_w, use_graph}` per query.
3. Wire single `client.query_points(prefetch=[...], query=FusionQuery(RRF))` for Stage 1+2.
4. Stand up BGE-reranker-v2-m3 behind a thin FastAPI service (or use `sentence-transformers` in-process). Benchmark p95 at K=60 on target hardware; budget 150ms.
5. Add Qdrant score-boost formula for `authority_level` + `recency`; plumb a feature flag so you can A/B with/without authority boost.
6. Build a 30-50 query gold set spanning all 5 query types; track nDCG@10 and recall@60. Re-run after each pipeline change.
7. Defer ColBERT/ColPali; revisit only if recall@60 plateaus below 0.9 on the gold set.

---

## Sources

- [Qdrant, Hybrid Search Revamped (Query API)](https://qdrant.tech/articles/hybrid-search/)
- [Qdrant, Sparse Vectors & BM25](https://qdrant.tech/articles/sparse-vectors/)
- [Qdrant, Score Boosting / Decay Functions](https://qdrant.tech/blog/decay-functions/)
- [Agentset, Reranker Leaderboard 2026](https://agentset.ai/rerankers)
- [ZeroEntropy, Ultimate Guide to Choosing the Best Reranking Model (2026)](https://www.zeroentropy.dev/articles/ultimate-guide-to-choosing-the-best-reranking-model-in-2025)
- [Pinecone, Rerankers and Two-Stage Retrieval](https://www.pinecone.io/learn/series/rag/rerankers/)
- [Elastic, Weighted RRF in Elasticsearch](https://www.elastic.co/search-labs/blog/weighted-reciprocal-rank-fusion-rrf)
- [Neo4j, Hybrid Retrieval for GraphRAG (Python)](https://neo4j.com/blog/developer/hybrid-retrieval-graphrag-python-package/)
- [Qdrant + ColPali, Multi-Vector Retrieval at Scale](https://qdrant.tech/blog/colpali-qdrant-optimization/)
- [Supermemory, Hybrid Search Guide (April 2026)](https://supermemory.ai/blog/hybrid-search-guide/)
- [ColBERTv2 paper (arXiv)](https://arxiv.org/abs/2112.01488)
