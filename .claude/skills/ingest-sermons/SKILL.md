---
name: ingest-sermons
description: Parse private sermon source documents (images, PDFs, DOCX, PPTX) into structured JSON for the brethren-doctrine GraphRAG. Orchestrates parallel Opus subagents — one per source file — with strict output schemas. Resumable; skips already-parsed files. Use when the user says "ingest sermons", "parse the new sermon notes", "process source-docs", or after dropping new files into source-docs/.
---

# Ingest Sermons — Source Document Pipeline

## Mission

Convert every file in `source-docs/` into a structured JSON record in `parsed/` that captures:
- **Theological themes and topic clusters**
- **Scripture references** (normalized canonical form)
- **Semantic chunks** with type tags (teaching, quote, perspective, application, definition, illustration)
- **Differing perspectives** when multiple distinct views appear within or across documents — anchored to `source_doc` only, never to personal names
- **Raw extracted text** for full-text search fallback

The output schema is the contract for the GraphRAG ingestion layer. Do not deviate.

## STRICT ANONYMIZATION RULE

The parsed/ outputs (and ALL downstream artifacts) must NEVER contain personal names of original teachers or any contributor whose teaching is in this corpus. Strip every such proper name from extracted content, attributions, metadata, and notes. Strip any single-letter initials prefixes (e.g., `X:`, `Y:`) used as speaker tags in the source notes — record only the substance of what was said. The corpus must be usable by strangers who do not know the original teachers. Anchor any differing perspectives to `source_doc` filenames, not to people.

The only personal name permitted anywhere in this repo is the project owner's own name. All other personal contributors must be redacted — including in filenames, slugs, and free-text fields.

## Authority and Context

This skill operates under the project's authority hierarchy (see `memory/authority_hierarchy.md`):
- Sermon notes are **Level 4 — Exegetical Application**.
- They reference but never override Levels 1–3 (interlinear, translations).
- Every chunk MUST carry `authority_level: 4` so the GraphRAG can weight retrieval correctly.

Sermon notes are **the unique irreplaceable asset** in this project — Bible texts and archaeology are public; these notes exist nowhere else. Optimize for fidelity over speed. If a subagent is uncertain, it should record uncertainty in `parsing_notes`, not guess.

## Protocol

### Step 0 — Sanity check

Before doing anything:
1. Confirm the working directory is `e:/projects-working-dir/brethren-doctrine` (or wherever the project lives — read from environment).
2. Confirm `source-docs/`, `parsed/`, and `converted/` exist. Create if missing.
3. Read `memory/MEMORY.md` to refresh project context (speakers, authority hierarchy, naming conventions).

### Step 1 — Inventory

Recursively list `source-docs/`. For each file, classify by extension:

| Category | Extensions | Handling |
|---|---|---|
| `image` | `.png .jpg .jpeg .webp .gif .heic` | Native — Opus subagent reads directly via Read tool (multimodal). |
| `pdf` | `.pdf` | Native — Opus subagent uses Read with `pages` parameter. |
| `docx` | `.docx .doc` | Convert via `pandoc <in> -o converted/<name>.md` first; subagent reads the .md. |
| `pptx` | `.pptx .ppt` | Convert via python-pptx text extraction script (see Step 2.b); subagent reads the .md. |
| `text` | `.txt .md .rtf` | Native — subagent reads directly. |
| `audio` | `.mp3 .m4a .wav .ogg .opus` | **SKIP for now.** Write `parsed/_pending_transcription/<name>.todo` listing the file. Tell user at end. |
| `video` | `.mp4 .mov .mkv .webm` | **SKIP for now.** Same as audio. |
| `other` | anything else | Log to `parsed/_unparseable.log` with reason. |

For each source file, compute the target output path: `parsed/<relative-path-without-ext>.json`. If that file already exists AND its `source_mtime` matches the source file's modification time, **skip it** (resumable).

Build a queue of files needing processing. If the queue is empty, report "nothing to do" and stop.

### Step 2 — Pre-conversion for non-native formats

#### 2.a — DOCX via pandoc
```bash
pandoc "source-docs/<path>/<file>.docx" \
  --extract-media="converted/<path>/<file>_media" \
  -o "converted/<path>/<file>.md"
```
Pandoc preserves headings, lists, and embedded images. Embedded images go into the media folder; reference them in the JSON's `embedded_assets` field.

#### 2.b — PPTX via python-pptx

If `python-pptx` is not installed: `pip install python-pptx` first.

Run this extraction script (write it to `.claude/skills/ingest-sermons/scripts/pptx_to_md.py` if not present):

```python
import sys, os
from pptx import Presentation

src, dst = sys.argv[1], sys.argv[2]
prs = Presentation(src)
out = []
for i, slide in enumerate(prs.slides, 1):
    out.append(f"\n## Slide {i}\n")
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                text = "".join(run.text for run in para.runs).strip()
                if text:
                    out.append(text)
        if shape.shape_type == 13:  # picture
            out.append(f"[image: {shape.name}]")
    if slide.has_notes_slide:
        notes = slide.notes_slide.notes_text_frame.text.strip()
        if notes:
            out.append(f"\n**Speaker notes:** {notes}")
os.makedirs(os.path.dirname(dst), exist_ok=True)
open(dst, "w", encoding="utf-8").write("\n".join(out))
```

Invoke: `python .claude/skills/ingest-sermons/scripts/pptx_to_md.py "source-docs/x.pptx" "converted/x.md"`

PPTX with heavy visual content (diagrams, screenshots of verses) will lose information through text-only extraction. For those, **also** export a slide-image fallback if LibreOffice/PowerPoint becomes available later. For now, flag in `parsing_notes`.

### Step 3 — Parallel Opus subagent dispatch

For each file in the queue, spawn an Opus subagent via the Agent tool. **Run all in parallel** — fire every Agent call in a single message. No concurrency cap.

Each subagent gets the prompt in **Step 4** below, parameterized for its file.

Why Opus and not Sonnet/Haiku for this task:
- Theological terminology and scripture-reference normalization require deep reasoning.
- Distinguishing a quoted verse from an original claim, or detecting where multiple distinct perspectives appear within the same notes, is non-trivial.
- The user is on Claude Max 20 — Opus quota is the resource we're trading for quality.

### Step 4 — Subagent prompt template

The Agent call:
- `subagent_type: "general-purpose"`
- `model: "opus"`
- `description: "Parse sermon doc: <basename>"`
- `prompt:` (use the full template below, substituting `{SOURCE_PATH}`, `{TARGET_JSON_PATH}`, `{SOURCE_TYPE}`, `{CONVERTED_PATH}` if applicable)

```
You are extracting structured theological data from a sermon note document for a personal GraphRAG system.

## Project context (read these for speaker disambiguation and conventions)
- e:/projects-working-dir/brethren-doctrine/memory/MEMORY.md
- e:/projects-working-dir/brethren-doctrine/memory/source_materials.md
- e:/projects-working-dir/brethren-doctrine/memory/authority_hierarchy.md
- e:/projects-working-dir/brethren-doctrine/memory/doctrinal_context.md

## Your input
- Source file: {SOURCE_PATH}
- Source type: {SOURCE_TYPE}
- For docx/pptx: read the converted markdown at {CONVERTED_PATH} AND inspect referenced media if relevant.
- For images/PDFs: use the Read tool directly. For multi-page PDFs, read page ranges sequentially.

## Your output
Write a single JSON file to {TARGET_JSON_PATH} matching the schema below EXACTLY. Validate before writing — reject your own output if any required field is missing. Do not write any other files.

## JSON schema (every field required unless marked optional)

{
  "source_file": "<relative path from project root>",
  "source_type": "image|pdf|docx|pptx|text",
  "source_mtime": "<ISO timestamp of source file>",
  "ingested_at": "<ISO timestamp now>",
  "ingester_model": "claude-opus-4-7",
  "authority_level": 4,

  "session_metadata": {
    "title": "<inferred or stated session title; null if not determinable>",
    "estimated_date": "<YYYY-MM-DD if mentioned, else null>",
    "session_topic": "<one-line summary of overall topic>",
    "topic_clusters": ["<2-6 broad theological domains, e.g. Soteriology, Ecclesiology, Pneumatology>"],
    "presents_multiple_perspectives": <bool — true if the doc itself records two or more distinct views on any topic>
  },

  "scripture_refs": [
    {
      "raw": "<as written in source, e.g. 'Rom 8:1-11' or 'Romans 8'>",
      "book": "<canonical book name, e.g. 'Romans'>",
      "chapter": <int>,
      "verse_start": <int or null>,
      "verse_end": <int or null>,
      "normalized": "<canonical form, e.g. 'Rom 8:1-11'>"
    }
  ],

  "theological_themes": ["<specific concepts, e.g. 'imputed righteousness', 'eternal security', 'priesthood of believers'>"],

  "chunks": [
    {
      "chunk_id": "<doc-slug + index, e.g. 'baptism_communion_01'>",
      "type": "teaching|quote|perspective|application|definition|illustration|question|prayer|other",
      "content": "<the actual text of this chunk, verbatim where possible — names of original teachers stripped>",
      "scripture_refs": ["<normalized refs touching this chunk>"],
      "themes": ["<themes from theological_themes touching this chunk>"],
      "claims": ["<distinct doctrinal assertions made in this chunk; one claim per array element>"],
      "perspectives_within_chunk": [
        {"marker": "perspective_a", "view": "<concise statement>", "reasoning": "<why, if given>"},
        {"marker": "perspective_b", "view": "<concise statement>", "reasoning": "<why, if given>"}
      ],
      "cross_references": ["<other chunk_ids in this doc this chunk depends on or contradicts; usually empty>"]
    }
  ],

  "embedded_assets": [
    {"path": "<converted/.../media/...>", "description": "<one-line description from context>"}
  ],

  "raw_extracted_text": "<full text dump, plain UTF-8, preserves no formatting>",

  "parsing_notes": "<free-text. Record ANY of: handwriting illegibility, ambiguous attribution, low-confidence sections, format limitations, items skipped, manual review needed>",

  "confidence": {
    "text_extraction": "high|medium|low",
    "scripture_normalization": "high|medium|low",
    "perspective_separation": "high|medium|low|n/a"
  }
}

## Chunking guidance

Chunk semantically, not by length. A chunk should be ONE coherent unit — a single argument, a single quoted verse with its commentary, a single illustration. Aim for 100–600 words per chunk; smaller is fine for short claims.

DO NOT split mid-argument. DO NOT merge unrelated topics into one chunk.

## Anonymization rules (CRITICAL)

1. NEVER write proper names of contributors into ANY field of the JSON. Strip them from `content`, `claims`, `parsing_notes`, `session_topic`, `title`, `raw_extracted_text` — everywhere. The only personal name permitted anywhere is the project owner's own.
2. Strip any single-letter initials prefixes used as speaker tags (e.g., `X:`, `Y:`) from extracted content; preserve only the substance of what was said.
3. If a single document presents one teaching, present it without attribution.
4. If a document records multiple distinct views on the same topic, populate `perspectives_within_chunk` with neutral markers (`perspective_a`, `perspective_b`, ...). Markers are scoped to the chunk only — do not carry meaning across chunks.
5. The `presents_multiple_perspectives` boolean in session_metadata flags whether the doc itself contains multiple views.
6. Filename references in metadata are fine (the source_doc filename is the anchor for any cross-doc analysis later).

## Scripture reference normalization

Use OSIS book abbreviations (Gen, Exod, Lev ... Rev). Format: "Book Ch:V" or "Book Ch:V-V" or "Book Ch" for whole-chapter refs. Keep the user's raw form in `raw` and the normalized form in `normalized`.

## Quality bar

This is a personal corpus the user will rely on for theological discernment. Errors propagate downstream into the GraphRAG and corrupt his diagnostic queries. Bias toward LESS CONFIDENT claims (more "unknown", more parsing_notes flags) over HALLUCINATED PRECISION.

When you're done, reply with a one-line summary: "Parsed <basename>: <N chunks>, speakers: <list>, themes: <top 3>, confidence: <overall>". Do not narrate your process.
```

### Step 5 — Aggregate index

After all subagents complete (or as they complete — can be incremental), build/update `parsed/_index.json`:

```json
{
  "generated_at": "<ISO ts>",
  "total_documents": <int>,
  "total_chunks": <int>,
  "by_theme": {"<theme>": <chunk count>, ...},
  "scripture_coverage": {"<OSIS book>": [<chapters touched>], ...},
  "documents": [
    {"path": "...", "title": "...", "topics": [...], "chunk_count": N, "presents_multiple_perspectives": <bool>, "confidence_overall": "high|medium|low"}
  ],
  "pending_transcription": ["<audio/video files awaiting transcription>"],
  "unparseable": ["<files that failed>"],
  "low_confidence_documents": ["<docs flagged for manual review>"]
}
```

The index is the entry point for the next pipeline stage (chunking → embedding → graph load).

### Step 6 — Cross-document perspective comparison (second pass)

After the per-document pass completes, spawn ONE additional Opus subagent with this prompt:

> Read every JSON in `parsed/`. Find chunks across DIFFERENT source documents that address the same `theological_themes` but make different or complementary `claims`. Output `parsed/_perspectives.json` with structure: `[{theme, scripture_refs, perspectives: [{source_doc, chunk_id, claim}]}]`. NEVER include personal names. Anchor each perspective only to its `source_doc` filename and `chunk_id`. This captures the diversity of views in the corpus without identifying who wrote them.

### Step 7 — Report

Final user-facing message format (keep it tight):

```
Ingested <N> documents into parsed/.
- Chunks: <total>
- Top themes: <top 5>
- Scripture coverage: <N unique verses across N books>
- Documents presenting multiple perspectives: <count>
- Pending transcription (audio/video): <list or "none">
- Manual review flagged: <list of low-confidence docs or "none">
- Cross-document perspective groups: <count, file: parsed/_perspectives.json>

Next: chunks are ready for embedding. Run /embed-sermons (or scaffold that pipeline) to push into the vector + graph layer.
```

## Failure modes to handle

- **Pandoc fails on .doc (old format):** ask user to convert to .docx in Word, or try `libreoffice` if installed (it isn't currently — just flag).
- **PPTX missing python-pptx:** `pip install python-pptx` then retry.
- **Subagent writes invalid JSON:** re-spawn that subagent ONCE with the prior output included and instruction to fix. If second attempt fails, write the raw output to `parsed/_failed/<basename>.txt` and continue.
- **Image is illegible / handwriting unreadable:** subagent records what it can plus parsing_notes flag. Do not retry — escalate to user in final report.
- **Source file modified mid-run:** trust mtime check at start; don't re-check during run.

## What this skill does NOT do

- It does not embed or vector-index anything. That's the next pipeline stage.
- It does not modify `source-docs/` — those files are read-only.
- It does not push to Neo4j or Qdrant.
- It does not transcribe audio/video — those are flagged for a future skill.
- It does not call external APIs (no LlamaParse, OpenAI, etc.) — Opus subagents do all the work using only Read + Bash + Write tools.

## When to invoke

Trigger when the user says any of:
- "ingest the sermons"
- "parse source-docs"
- "process the new notes"
- "run the sermon pipeline"
- After confirming new files have been dropped into `source-docs/`.
