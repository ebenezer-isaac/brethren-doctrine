# Related work

A scan of public GitHub / HuggingFace projects in the Bible-RAG, biblical knowledge-graph, theology-MCP, and confession-text spaces. Recorded so the README's novelty claim is anchored against actual neighbours rather than asserted in a vacuum.

This file is **descriptive, not exhaustive**. New entries should be added when discovered; obsolete entries should be pruned, not preserved as fallbacks.

---

## What this project is, in one sentence

A tradition-neutral lexical-philological **baseline-derivation pipeline** (apparatus + interlinear + concordance, with confessions demoted to a `counter_witness[]` field) plus per-respondent overlays, used downstream to **evaluate churches** Ebenezer is considering visiting or joining.

The four discriminators against everything below:

1. Critical Apparatus (Level 0) → Interlinear (Level 1) is **source of truth**; confessions are explicitly **not a tier**.
2. **Two-pipeline split**: tradition-neutral `baseline.json` is a separate artefact from per-respondent `responses/<id>.json`.
3. **Cult-marker bar** — canonical demonstration + ≥6-lineage corroboration; even Trinity is not exempt from the bar.
4. **Diagnostic / discernment** is the downstream use case, not study or chatbot.

No project surveyed combines all four. Most overlap on one or two layers of the stack; this file records *which* layer.

---

## Closest architectural neighbours (GraphRAG + Bible)

| Project | Overlap | Gap vs. this project |
|---|---|---|
| [robertrouse/theographic-bible-metadata](https://github.com/robertrouse/theographic-bible-metadata) | Neo4j knowledge graph of biblical people, places, periods, passages | No LLM/RAG layer, no doctrinal-evaluation pipeline. Useful as a graph-data input, not as a competing system. |
| [calebyhan/bible-rag](https://github.com/calebyhan/bible-rag) | FastAPI + multilingual-e5-large + Strong's + morphological parsing; closest in retrieval-CLI shape | Vector-only (no graph), no confessional-comparison angle, no apparatus tier |
| [jacobweiss2305/bible-rag](https://github.com/jacobweiss2305/bible-rag) | Embedding-space clustering on the Bible | Research toy, not infrastructure |
| [dssjon/biblos](https://github.com/dssjon/biblos) | Chroma vector DB + Church Fathers' commentaries via RAG; closest spirit to "counter-witness as research aid" | Treats commentary as authoritative; no apparatus floor; no per-respondent overlay |
| [kennethreitz/kjvstudy.org](https://github.com/kennethreitz/kjvstudy.org) | KJV + interlinear + Strong's + AI commentary; FastAPI + Tufte CSS | Study-platform UI, not a baseline-derivation pipeline |

## MCP-server cousins (planned Tier 2 surface)

| Project | Overlap | Gap |
|---|---|---|
| [djayatillake/studybible-mcp](https://github.com/djayatillake/studybible-mcp) | LSJ + BDB + Abbott-Smith lexicons + morphology + Fee & Stuart hermeneutics baked in. Closest precedent for the planned MCP server. | Single-tradition hermeneutic; no graph backbone; no `counter_witness[]` schema |
| [TJ-Frederick/TheologAI](https://github.com/TJ-Frederick/TheologAI) | 7 tools, 8 translations, 6 commentaries, 18 historical documents, Strong's at 14,298 entries | Aggregation-style, not derivation-style; no answer-schema lock |
| [robrawks/LogosBibleSoftwareMCP](https://github.com/robrawks/LogosBibleSoftwareMCP) | 20 MCP tools wrapping Logos Bible Software | Closed-corpus dependency on Logos; not reproducible without licence |
| [AdbC99/ai-bible](https://github.com/AdbC99/ai-bible) | MCP server + container for repeatable LLM lookup of Bible data | Lookup-only; no derivation, no graph |

Worth studying `studybible-mcp`'s tool shape before building this project's planned five tools (`search_bible_interlinear`, `query_sermon_graph`, `get_doctrine_perspectives`, `lookup_archaeology`, `evaluate_statement_of_faith`).

## Strong's / lexicon data sources (inputs, not competitors)

| Project | What it provides |
|---|---|
| [openscriptures/strongs](https://github.com/openscriptures/strongs) | Strong's Dictionaries of Hebrew and Greek (canonical upstream) |
| [ZionSoft/strongs](https://github.com/ZionSoft/strongs) | Strong's-indexed Bible data |
| [tahmmee/interlinear_bibledata](https://github.com/tahmmee/interlinear_bibledata) | Interlinear OT and NT with Strong's numbers |
| [eliranwong/OpenGNT](https://github.com/eliranwong/OpenGNT) | NA28/NA27-equivalent Greek New Testament + resources |
| [openbibleinfo/Bible-Passage-Reference-Parser](https://github.com/openbibleinfo/Bible-Passage-Reference-Parser) | Reference-string parsing for "John 3:16"-style refs |
| [biblenerd/awesome-bible-developer-resources](https://github.com/biblenerd/awesome-bible-developer-resources) | Curated index of Bible-developer resources |

These are upstream feedstock candidates for the concordance loader ([../ingest/adapters/concordance_loader.py](../ingest/adapters/concordance_loader.py)). STEPBible TAHOT/TAGNT remains the primary source per [CONCORDANCE.md](CONCORDANCE.md).

## Doctrinal / denominational angle

| Project | Approach | Relation to this project |
|---|---|---|
| [AiForTheChurch (HuggingFace)](https://huggingface.co/AiForTheChurch) | Denomination-specific fine-tuned LLMs (e.g., ChristianGPT-catholic) | **Opposite approach.** Bakes the confession into the model rather than evaluating *against* a tradition-neutral floor. A user querying ChristianGPT-catholic and ChristianGPT-reformed cannot adjudicate which is closer to the lexical force of the original languages. |
| [llm-mar/study-bible](https://github.com/llm-mar/study-bible) | Multi-agent reasoning for multi-perspective Bible study | Closest spirit to the `counter_witness[]` field, but no apparatus floor and no derivation gate |
| [ortegaalfredo/ChristGPT](https://github.com/ortegaalfredo/ChristGPT) | LLM trained on the Bible and Jesus's teachings | Generative chatbot, not a derivation system |
| [fennsaji/bible-king-llm](https://github.com/fennsaji/bible-king-llm) | LangChain Bible expert | Same shape as ChristGPT |
| [khornberg/lbcf-1689](https://github.com/khornberg/lbcf-1689) | 1689 LBCF text in machine-readable form | **Useful input** — feedstock for a Brethren / Reformed Baptist respondent overlay |

Confession-text repos (1689 LBCF, WCF, Savoy Declaration, Belgic) and tabular comparisons (`proginosko.com/docs/wcf_lbcf.html`) are inputs to pipeline B (respondent overlays); they are explicitly not part of pipeline A.

---

## What no surveyed project does

The combination listed at the top — apparatus-as-Level-0 + tradition-neutral baseline derivation + per-respondent overlay split + cult-marker bar with ≥6-lineage corroboration + diagnostic-use downstream — was not found in any public project at the time of this survey.

Projects that touch any *one* of those layers exist; projects that compose all four are absent. The novelty claim is therefore **architectural composition**, not any single technique.

---

## Update protocol

When a new project is found that touches any of the four discriminators, add it to the appropriate table with a one-line gap analysis. If a surveyed project pivots to cover one of the discriminators, move it up the table and update the gap column. If this project's architecture changes, re-evaluate the discriminator list before claiming novelty.
