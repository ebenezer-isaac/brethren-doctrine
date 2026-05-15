# Embedding Model Selection: Tier 2 GraphRAG (May 2026)

Project-internal research. Scope: choose an embedding model for sermon-note JSONs, full Bible (multi-translation), Hebrew/Greek interlinear word-level data with Strong's tags, archaeological metadata, and church-history nodes. Hybrid search + downstream reranker assumed.

---

## 1. Top Recommendation: **`voyage-context-3`** (Voyage AI)

**Why it wins for this corpus.**

- **Contextualized chunk embeddings.** Each chunk's vector encodes both its own content *and* the surrounding document context. For Bible verses (where a single verse is meaningless without its pericope) and sermon-note semantic chunks (which build on prior points), this is exactly the right inductive bias. Voyage reports +6.76% chunk-level and +2.40% document-level retrieval over standard contextual-retrieval pipelines, and +23.66% / +20.54% over Jina-v3 late chunking. It is a drop-in replacement for an isolated-chunk embedder, so the rest of the GraphRAG plumbing is unaffected.
- **Quality on nuanced English.** Built on the voyage-3 family that leads MTEB retrieval (voyage-3-large at ~65-67 MTEB depending on slice) and beats `text-embedding-3-large` by 4-9% on retrieval-flavored benchmarks. Theology is dense, allusive English, the kind of content where Voyage consistently outperforms OpenAI/Cohere on independent tests.
- **Hebrew/Greek code-switching is fine.** Voyage is multilingual at the tokenizer level. Transliterated Hebrew/Greek and the occasional Greek/Hebrew script inside English chunks will embed sensibly. Strong's numbers are short tokens that travel cleanly through any modern BPE.
- **32k context.** Sermon notes and long pericopes fit without forced chunking.
- **Matryoshka + quantization.** Native support for 2048/1024/512/256 dims and int8/binary quantization. We can ship 1024-dim float for indexing and explore int8/512 if storage matters later.
- **Cost is a non-issue.** $0.18/1M tokens, with 200M free tokens per account. Our entire corpus (estimated below) fits inside the free tier multiple times over.

**Trade-offs.** Closed model, single-vendor lock-in, requires API calls (no offline). Acceptable for personal use; mitigated by storing raw text alongside vectors so re-embedding is a script-level operation.

---

## 2. Backup Recommendation: **`voyage-4-large`** (Voyage AI)

If `voyage-context-3` ever underperforms on the GraphRAG eval set, switch to `voyage-4-large`. It's the January-2026 flagship, MoE-backed, $0.12/1M tokens, 32k context, same 2048/1024/512/256 Matryoshka dims, +3.87% over voyage-3-large on RTEB. Also covered by the 200M-token free tier. Bonus: the **shared embedding space** across the Voyage 4 family lets us index once with `voyage-4-large` and query with `voyage-4-lite` for cheaper/faster retrieval at runtime, a nice optimization lever later. The reason it's #2: it doesn't carry voyage-context-3's chunk-level contextualization, which is the single biggest architectural fit for Bible/sermon retrieval.

**Hard fallback (open-source / offline):** `BGE-M3`, 8192 ctx, 100+ languages, dense + sparse + multi-vector from one model (perfect for hybrid search), MTEB ~63. Self-host if Voyage ever becomes unavailable.

---

## 3. Comparison Table

| Model | MTEB (approx) | Price /1M tok | Default dims | Max ctx | Multiling / HE-GR | Notes |
|---|---|---|---|---|---|---|
| **voyage-context-3** | ~65 + contextual gains | $0.18 (200M free) | 1024 (256/512/2048) | 32k | Yes | Chunk-aware, RAG-optimized |
| **voyage-4-large** | ~67 (RTEB +3.87 over v3-large) | $0.12 (200M free) | 1024 (256/512/2048) | 32k | Yes | MoE, shared-space family |
| voyage-3-large | 65.1 (MTEB) | $0.18 | 1024 (256/512/2048) | 32k | Yes | Prev SOTA, still excellent |
| voyage-3.5 | ~64 | $0.06 | 1024 | 32k | Yes | Best $/quality of v3 line |
| voyage-code-3 | code-tuned | $0.18 | 1024 | 32k | Code | Not relevant here |
| OpenAI text-embedding-3-large | 64.6 | $0.13 | 3072 (configurable to 1024) | 8191 | OK | Heavier vectors, weaker retrieval |
| OpenAI text-embedding-3-small | 62.3 | $0.02 | 1536 | 8191 | OK | Cheap baseline |
| Cohere embed-v4 | 65.2 | $0.12 | 1024-3072 (Matryoshka, down to 256) | 128k | 100+ langs, multimodal | Strong long-doc, no chunking needed |
| Cohere embed-multilingual-v3 | ~62 | $0.10 | 1024 | 512 | 100+ langs | Aging |
| BGE-M3 (open) | ~63 | self-host | 1024 | 8192 | 100+ langs | Dense+sparse+ColBERT in one |
| E5-Mistral-7B-instruct (open) | ~66 | self-host (GPU) | 4096 | 4096 | English-strong | Heavy infra |
| gte-Qwen2-1.5B (open) | ~65 | self-host | 1024 (Matryoshka) | 32k | EN | Compact, strong |
| Nomic Embed v2 MoE (open) | ~62 | self-host | 768 | 8192 | OK | Fully open weights+data, hybrid-friendly |
| Qwen3-Embedding-8B (open) | 70.58 (multiling MTEB) | self-host (GPU) | 4096 | 32k | Best multilingual | Heavy; overkill for personal |

No production embedding model is *trained on biblical corpora* (`Embible`, `AlephBERT` etc. exist but are MLM models for Hebrew reconstruction, not sentence/passage embeddings, wrong tool). General-purpose top-tier models handle theological English better than any boutique biblical embedder available in 2026.

---

## 4. Concrete Next Steps

**a. First-pass model:** `voyage-context-3` at **1024 dims, float32**, 32k chunks (whole sermons / whole chapters where possible).

**b. Corpus size estimate:**
- Bible (4 translations × ~31k verses × ~25 tokens) ≈ **3.1M tokens**
- Hebrew/Greek interlinear (~700k words × ~5 tokens) ≈ **3.5M tokens**
- Sermon notes (~15 × ~5k tokens) ≈ **75k tokens**
- Archaeology + church history ≈ **<500k tokens**
- **Total approximately 7-8M tokens**, fits approximately 25x inside the 200M-token free tier. Effective embedding cost: **$0**.

**c. Storage budget:** 1024-dim float32 = 4 KB/vector. If we end up with ~50k vectors (verses + chunks + interlinear groups + nodes), that's **~200 MB** raw vector payload, trivial in any vector DB. With int8 quantization: ~50 MB. With binary 512-dim: ~3 MB.

**d. Benchmark protocol (run before bulk indexing):**
1. Embed 30 representative chunks: 10 verses (one per genre, narrative/poetry/prophecy/epistle/gospel/wisdom + 4 cross-translation pairs), 10 sermon-note chunks, 5 interlinear word groups, 5 history/archaeology nodes.
2. Author 10 test queries spanning literal lookup ("verse about mustard seed"), thematic ("covenant fidelity in the prophets"), cross-reference ("NT use of Isaiah 53"), Hebrew/Greek term ("agape vs philia"), and sermon-recall ("notes mentioning eschatology").
3. Measure **recall@5 and recall@10** against a hand-labelled gold set. Also eyeball MRR.
4. Repeat with `voyage-4-large` and `text-embedding-3-large` on the same set.
5. Promote the winner. Expected: voyage-context-3 wins on cross-reference and sermon-recall; voyage-4-large wins on raw verse lookup; OpenAI loses on theological nuance.

**e. Hybrid search:** Pair vector retrieval with BM25 (over original text) and Strong's-number exact match. The reranker (next agent's domain) handles final ordering.

**f. Re-embedding hygiene:** Store `(model_name, model_version, dim, quantization, embedded_at)` alongside every vector so a future model swap is a clean migration.

---

## 5. Sources (current, 2026)

- [voyage-context-3 announcement (Voyage AI blog)](https://blog.voyageai.com/2025/07/23/voyage-context-3/)
- [Voyage 4 family release: shared embedding space + MoE (Voyage AI blog, Jan 2026)](https://blog.voyageai.com/2026/01/15/voyage-4/)
- [voyage-3-large announcement (Voyage AI blog)](https://blog.voyageai.com/2025/01/07/voyage-3-large/)
- [Voyage AI pricing page](https://docs.voyageai.com/docs/pricing)
- [Voyage AI models overview](https://docs.voyageai.com/docs/embeddings)
- [Flexible Dimensions and Quantization (Voyage AI docs)](https://docs.voyageai.com/docs/flexible-dimensions-and-quantization)
- [OpenAI text-embedding-3-large model card](https://developers.openai.com/api/docs/models/text-embedding-3-large)
- [Cohere Embed v4 deep dive (Ailog RAG)](https://app.ailog.fr/en/blog/news/cohere-embed-v4)
- [Embedding Model Leaderboard: MTEB Rankings March 2026 (Awesome Agents)](https://awesomeagents.ai/leaderboards/embedding-model-leaderboard-mteb-march-2026/)
- [Best Embedding Models for RAG 2026, MTEB + cost + self-hosting (PremAI)](https://blog.premai.io/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/)
- [The Best Open-Source Embedding Models in 2026 (BentoML)](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)
- [Biblos: open-source biblical RAG reference implementation](https://github.com/dssjon/biblos)
