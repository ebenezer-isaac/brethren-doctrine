# Cultural Corpus Schema

Per-chunk metadata schema for the cultural store. Every chunk ingested by a `pipeline1_cultural_scrape` subagent and tagged by a `cultural_autotag` subagent carries this structure.

The Pydantic v2 model lives at `ingest/cultural/models.py` with `extra="forbid"` at every level.

## Top-level shape

```json
{
  "chunk_id": "ccel.npnf1.04.augustine.confessions.01.01.001",
  "tradition": "patristic",

  "source": {
    "work_id": "augustine.confessions",
    "work_title": "Confessions",
    "author": "Augustine of Hippo",
    "date_written": "397",
    "is_confessional_text": false,
    "anchor_id": "Conf.1.1.1",
    "language": "en",
    "translator": "Pilkington (NPNF1-04)"
  },

  "doctrine_tags": [
    {
      "doctrine_coarse": "theology-proper",
      "doctrine_fine": "theology-proper",
      "stance": "affirms",
      "confidence": 0.85,
      "evidence_phrase": "Great art Thou, O Lord, and greatly to be praised"
    }
  ],

  "text": "Great art Thou, O Lord, and greatly to be praised. Great is Thy power, and infinite Thy wisdom...",
  "text_to_embed": "Great art Thou, O Lord, and greatly to be praised. Great is Thy power, and infinite Thy wisdom...",

  "license": "public_domain",
  "redistribute": true,
  "license_note": "Pre-1923 English translation; PD in US."
}
```

## Identity fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `chunk_id` | string | yes | Globally unique. Format: `<source-prefix>.<work>.<anchor_path>.<chunk_index>` |

The chunk_id is the stable identifier across re-scrapes. Re-scraping a source updates content but preserves chunk_ids where the underlying anchor (paragraph number, article number, Q&A number) is stable.

## tradition

Enum, single value per chunk. The 12 tracked traditions plus an escape hatch.

| Slug | Covers |
|---|---|
| `patristic` | Pre-confessional era: ANF, NPNF, Apostolic Fathers |
| `catholic-magisterial` | Vatican.va, CCC, encyclicals, conciliar (Trent, V2), papal documents |
| `eastern-orthodox` | OCA, GOARCH, Philokalia, Confession of Dositheus, Philaret's Catechism |
| `oriental-orthodox` | Coptic, Syriac, Armenian, Ethiopian traditions (deferred in v1) |
| `lutheran` | Book of Concord (Augsburg, Apology, Smalcald, Catechisms, Formula) |
| `reformed` | WCF, 1689 LBC, Heidelberg, Belgic, Dort, Calvin's Institutes (Calvin's Institutes treated as reformed) |
| `anglican` | 39 Articles, BCP 1662, Lambeth Quadrilateral |
| `methodist` | UMC Articles of Religion, Wesley's standard sermons |
| `anabaptist` | Schleitheim 1527, Dordrecht 1632, Mennonite Confession 1995 |
| `pentecostal` | AG Fundamental Truths, Foursquare, Pentecostal Holiness |
| `plymouth-brethren` | BrethrenArchive, STEM Publishing, Darby, Kelly, Mackintosh, the `parsed/` corpus |
| `other` | Escape hatch (e.g., Quaker, Mennonite-non-confessional, modern denominational statements not in the above list) |

A document is tagged to its tradition at scrape time by the `pipeline1_cultural_scrape` subagent. The Brethren parsed/ Tier 1 corpus is tagged `plymouth-brethren`.

## source block

```json
{
  "work_id": "<slug>",
  "work_title": "<full title>",
  "author": "<full name or null for collective documents>",
  "date_written": "<year as string, BCE/CE if needed>",
  "is_confessional_text": <bool>,
  "anchor_id": "<stable section identifier>",
  "language": "<ISO 639-1 code>",
  "translator": "<name or null>"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `work_id` | string | yes | Slug like `augustine.confessions`, `wcf`, `ccc`, `1689-lbc` |
| `work_title` | string | yes | Full title |
| `author` | string or null | yes | Null for collective documents (e.g., WCF, CCC, conciliar canons) |
| `date_written` | string | yes | Year of composition (use earliest known) |
| `is_confessional_text` | bool | yes | True for binding confessions; false for theological treatises, sermons, commentary |
| `anchor_id` | string | yes | Stable identifier within the work |
| `language` | string | yes | ISO 639-1 code (`en`, `la`, `el`, `de`, `fr`) |
| `translator` | string or null | yes | Translator name for translated works |

### work_id conventions

| Work | work_id |
|---|---|
| Augustine, Confessions | `augustine.confessions` |
| Athanasius, De Incarnatione | `athanasius.de-incarnatione` |
| Catechism of the Catholic Church | `ccc` |
| Westminster Confession | `wcf` |
| Westminster Larger Catechism | `wlc-catechism` (distinguished from WLC the manuscript) |
| Westminster Shorter Catechism | `wsc` |
| 1689 London Baptist Confession | `1689-lbc` |
| Heidelberg Catechism | `heidelberg` |
| Belgic Confession | `belgic` |
| Canons of Dort | `dort` |
| 39 Articles | `39-articles` |
| BCP 1662 | `bcp-1662` |
| UMC Articles of Religion | `umc-articles` |
| Schleitheim Confession | `schleitheim` |
| Dordrecht Confession | `dordrecht` |
| AG Fundamental Truths | `ag-fundamental-truths` |
| Hopko, Orthodox Faith | `hopko.orthodox-faith` |
| Darby, Synopsis | `darby.synopsis` |
| Mackintosh, Notes on Pentateuch | `mackintosh.notes-on-pentateuch` |
| Nicene Creed (381) | `niceno-constantinopolitan-creed` |
| Council of Chalcedon Definition | `chalcedon-definition` |
| Council of Trent | `trent` |
| Vatican II Dei Verbum | `vat2.dei-verbum` |

### anchor_id conventions

| Source type | Pattern | Example |
|---|---|---|
| CCC paragraphs | `CCC.<n>` | `CCC.232` |
| Encyclicals | `<encyclical-slug>.<para>` | `humanae-vitae.14` |
| Vat II constitutions | `<doc-slug>.<article>` | `DV.9`, `LG.16` |
| Confession article | `<work-slug>.<chapter>.<section>` | `WCF.1.6`, `1689.1.6` |
| Catechism Q&A | `<work-slug>.LD<n>.Q<n>` or `<work-slug>.Q<n>` | `HC.LD1.Q1`, `WSC.Q1` |
| Patristic prose | `<author>.<work>.<book>.<chapter>.<section>` | `Augustine.Confessions.1.1.1` |
| Conciliar canon | `<council-slug>.Canon.<n>` | `Nicaea325.Canon.1` |
| Conciliar definition | `<council-slug>.Definition` | `Chalcedon451.Definition` |
| Patristic homily | `<author>.<work>.Homily.<n>.<section>` | `Chrysostom.HomiliesOnJohn.Homily.1.3` |
| 39 Articles | `39A.<article_number>` | `39A.1` |
| BCP 1662 | `BCP1662.<service-or-collect>.<part>` | `BCP1662.MorningPrayer.GeneralConfession` |
| Brethren author | `<author-slug>.<work-slug>.<chapter>.<section>` | `darby.synopsis.romans.1` |

### is_confessional_text

True for binding confessional documents (WCF, 1689, Heidelberg, Belgic, Dort, Augsburg, Schleitheim, 39 Articles, UMC Articles, AG Fundamental Truths, conciliar definitions).

False for non-binding theological texts (Augustine's Confessions, Calvin's Institutes, Aquinas's Summa, Wesley's sermons, Darby's Synopsis, Hopko's Orthodox Faith, encyclicals are arguably borderline, treat as false unless the encyclical is a definitive dogmatic act).

This boolean drives retrieval ranking. Confessional text is weighted higher when the user asks "what does Tradition X officially teach" vs. theological text which is "what did Author A argue."

## doctrine_tags array

Each chunk may carry 1-5 doctrine tags. Empty array means no doctrine substantively addressed (rare; such chunks usually filtered at ingest).

```json
{
  "doctrine_coarse": "<11-bucket slug>",
  "doctrine_fine": "<26-slug from questions.json categories>",
  "stance": "affirms | denies | qualifies | disputed",
  "confidence": <0.0-1.0>,
  "evidence_phrase": "<verbatim phrase from chunk, max 30 words>"
}
```

### doctrine_coarse (11 buckets)

| Slug | Covers |
|---|---|
| `scripture` | Bibliology, canon, inspiration, authority, sufficiency |
| `theology-proper` | God's nature, attributes, Trinity, divine simplicity, aseity |
| `christology` | Person and natures of Christ, hypostatic union, two wills, ascension |
| `pneumatology` | Personhood and deity of the Spirit, gifts, procession, indwelling |
| `anthropology` | Image of God, creation of humanity, body / soul, gender |
| `hamartiology` | Sin, fall, original sin, inherited corruption, inherited guilt |
| `soteriology` | Salvation: election, calling, regeneration, justification, sanctification, perseverance, atonement |
| `ecclesiology` | Church: marks, polity, governance, discipline, succession |
| `sacraments` | Baptism, Lord's Supper, sacramental theology |
| `eschatology` | Last things, millennium, judgment, heaven, hell, intermediate state |
| `ethics` | Christian living, marriage, sexuality, money, social engagement, calendar |

### doctrine_fine (26 slugs from questions.json category_index)

Slugified (lowercase, hyphenated):
```
bibliology
theology-proper
christology
pneumatology
anthropology
hamartiology
soteriology
ecclesiology
sacraments
leadership-and-polity
church-discipline
worship-structure
inter-church-relations
eschatology
angelology
demonology
cult-marker
heterodoxy-marker
spiritual-gifts
worship-style
christian-ethics
marriage-and-sexuality
family-and-discipleship
money-and-stewardship
engagement-with-world
calendar-and-customs
```

Pydantic validator: `doctrine_fine` must be in this set.

Coarse-to-fine consistency: each `doctrine_fine` slug maps to exactly one `doctrine_coarse` bucket. The validator enforces this. Mapping table at `ingest/cultural/doctrine_taxonomy.py`.

### stance enum

- `affirms`: chunk asserts the doctrine as true
- `denies`: chunk asserts the doctrine as false
- `qualifies`: chunk affirms with significant restrictions or exceptions
- `disputed`: chunk explicitly notes intra-tradition disagreement

`silent` is NOT in this enum. Chunks that do not substantively address a doctrine simply lack a tag for that doctrine; we do not record silence.

### confidence

Float in [0.0, 1.0]. Self-reported by the Opus auto-tagger.

| Range | Meaning |
|---|---|
| ≥ 0.85 | Chunk explicitly and unambiguously addresses the doctrine |
| 0.60-0.85 | Implicit but clearly inferable |
| < 0.60 | Guessing; flagged for human review |

The orchestrator's policy: tags with confidence ≥ 0.6 ship to the cultural store; tags with confidence < 0.6 are written to `tmp/cultural_autotag/<task_id>/low_confidence.jsonl` for human review.

### evidence_phrase

Verbatim phrase from the chunk that justifies the tag. **Max 30 words, hard semantic cap** enforced by a Pydantic `@field_validator` that runs `len(v.split()) <= 30`. A separate byte-cap of 500 characters acts as a sanity ceiling. Mandatory.

Used by:
- The orchestrator's human-review UI for low-confidence tags.
- The MCP server's `debate_for_verse` and `cultural_overlay` tools as a short justification cite.
- The validation subagent's spot-check mode.

## text and text_to_embed

```json
{
  "text": "<full chunk text, NFC-normalized>",
  "text_to_embed": "<same as text, or shorter excerpt for embedding if chunk is very long>"
}
```

`text` preserves the full chunk content for retrieval.

`text_to_embed` is what gets sent to Voyage. For chunks ≤ 500 tokens, equal to `text`. For longer chunks, an extract or summary suitable for embedding (the chunker decides; the schema is agnostic).

Validator: both fields are non-empty strings; `text` is NFC-normalized; curly quotes preserved.

## license fields

```json
{
  "license": "<license slug from docs/LICENSE_TAGGING.md>",
  "redistribute": <bool>,
  "license_note": "<optional human-readable clarification>"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `license` | string | yes | Must be a registered license slug in `docs/LICENSE_TAGGING.md` |
| `redistribute` | bool | yes | Should match the license registry; if false, retrieval defaults to paraphrase rather than verbatim quote |
| `license_note` | string or null | no | Free-form clarification (e.g., "pre-1923 PD in US") |

## Neo4j cultural store model

```cypher
(:Tradition {slug, label})
    -[:CONTAINS]->
(:Work {work_id, title, author, date_written, language, is_confessional_text})
    -[:HAS_CHUNK]->
(:CulturalChunk {chunk_id, anchor_id, text, language, license, redistribute})
    -[:ADDRESSES {stance, confidence, evidence_phrase}]->
(:Doctrine {slug, coarse, fine})

(:Doctrine)-[:UNDER_QUESTION]->(:Question {id})
```

Join to `questions.json`:
- For each question in `questions.json`, a `:Question {id}` node exists in the cultural store.
- For each question, the `category` field maps to a `doctrine_fine` slug; that slug's `:Doctrine` node connects via `:UNDER_QUESTION`.
- Retrieval can therefore traverse: question → doctrine → chunks → work → tradition.

## Qdrant cultural collection (`cult_col`) payload

```json
{
  "chunk_id": "<>",
  "tradition": "<>",
  "work_id": "<>",
  "is_confessional_text": <bool>,
  "doctrine_coarse_list": ["theology-proper"],
  "doctrine_fine_list": ["theology-proper"],
  "stance_per_doctrine": {"theology-proper": "affirms"},
  "language": "<>",
  "license": "<>",
  "redistribute": <bool>,
  "anchor_id": "<>"
}
```

The `_list` and `_per_doctrine` projections flatten the doctrine_tags array into Qdrant-payload-friendly formats for filter queries.

## Pipeline 1 cultural scrape contract

The scrape subagent (`docs/phase_prompts/pipeline1_cultural_scrape.md`) produces chunks with all fields populated EXCEPT `doctrine_tags`, which is an empty array. The `cultural_autotag` subagent (`docs/phase_prompts/cultural_autotag.md`) fills `doctrine_tags`.

## Validator rules

Pydantic validator at `ingest/cultural/models.py` enforces:

1. `chunk_id` is unique globally (verified at ingest by Neo4j unique constraint).
2. `tradition` is one of the 12 registered values.
3. `source.language` is a valid ISO 639-1 code.
4. `source.is_confessional_text` is consistent with the tradition (e.g., confessional texts can be in any tradition; non-confessional cannot be in `catholic-magisterial` for documents marked dogmatic).
5. `doctrine_tags` length ≤ 5.
6. For each tag: `doctrine_coarse` is in the 11-bucket list; `doctrine_fine` is in the 26-slug list; the coarse-fine pair is consistent per `doctrine_taxonomy.py`.
7. `text` and `text_to_embed` are non-empty NFC strings.
8. `license` is a registered slug from `docs/LICENSE_TAGGING.md`.
9. `redistribute` matches the license registry (validator looks up and warns on mismatch).

## Auto-tag review workflow

1. `cultural_autotag` subagent processes a batch of ~50 chunks.
2. Tags with confidence ≥ 0.6 are persisted to the cultural store.
3. Tags with confidence < 0.6 are written to `tmp/cultural_autotag/<task_id>/low_confidence.jsonl`.
4. The orchestrator surfaces the low-confidence file to the user.
5. The user reviews, accepts, modifies, or rejects each tag.
6. Accepted / modified tags are persisted via a `cultural_tag_apply` orchestrator step.

This is the only human-in-the-loop step in the cultural ingestion pipeline. The volume should be low: confessional texts get high-confidence tags reliably; commentary documents produce more low-confidence cases.

## Retrieval semantics

When the MCP `cultural_overlay` tool queries the cultural store:

```cypher
MATCH (q:Question {id: $question_id})<-[:UNDER_QUESTION]-(d:Doctrine)
MATCH (c:CulturalChunk)-[r:ADDRESSES]->(d)
WHERE c.tradition IN $traditions_filter
RETURN c, r.stance, r.confidence, r.evidence_phrase
ORDER BY r.confidence DESC, c.is_confessional_text DESC
LIMIT $k
```

The retrieval emits chunks ranked by:
1. `confidence` descending.
2. `is_confessional_text` true first (confessional carries more weight in "official position" queries).
3. Optional: tradition_weight (deferred for v1; flat across traditions).

Hybrid retrieval can additionally embed-search the chunk text via Qdrant `cult_col` and fuse via RRF before reranking with BGE.

## What is NOT in the cultural schema

- `tradition_weight`: was considered, deferred for v1. Cultural overlay is diagnostic; weighting smuggles authority.
- `question_ids_addressed`: dropped per architecture decision; the Neo4j `:UNDER_QUESTION` edge handles linkage.
- `verdict` field on a chunk: chunks do not carry verdicts. Only `evidence/<id>.json` (Pipeline 2 output) carries verdicts.
- `counter_witness_for_lexical_verdict`: explicitly NO. Cultural is diagnostic, never adjudicative.
