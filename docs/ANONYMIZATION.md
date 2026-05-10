# Anonymization Policy

Hard rule: outputs of this project must be usable by strangers who have no relationship with the original teachers. Personal identifiers of corpus contributors must not appear in any artifact under `parsed/`, `chunks/`, `embeddings/`, `graph/`, server responses, or client display.

The only personal name permitted anywhere in this repository is the project owner's own. Every other personal contributor (every teacher, friend, fellow believer, or organization member whose name might appear in the source notes) must be stripped from the public corpus.

## What gets stripped

- **Personal names of original teachers**. Anyone whose teaching was personally recorded into this corpus.
- **Names of organizations** that identify the source community of the teaching rather than serving as content.
- **Initials prefixes** used as speaker tags in source notes (e.g., `X:`, `Y:`). Preserve only the substance of what was said.
- **Source filenames containing names** are not used as slugs; sanitized topical slugs (e.g., `church_governance` not `church_governance_<name>`) replace them.
- **Personal anecdotes** that name third parties (friends, family, attendees). Substance kept, names removed.

## What is retained

- **External published theological authors** (e.g., John Piper, Charles Ryrie, Justin Martyr, Augustine, Calvin, the *Didache*, Jamieson-Fausset-Brown). These are public citations the source documents reference. Retaining them preserves the citation chain that lets a reader trace claims back to their published origins.
- **Biblical figures and historical persons** (Moses, David, Paul, Augustine of Hippo, etc.). Content, not contributors.
- **Geographic and place names**. Content.
- **Institutional and confessional names** of public reference (Westminster Confession, Council of Nicaea, etc.). Content.

## The bright line

If a name identifies someone whose teaching is in this corpus *because they personally taught it*, **strip it**.
If a name identifies a public source that the corpus *cites*, **keep it**.

## How "differing perspectives" are anchored

When two or more source documents present different views on the same theme, the system anchors each perspective to its `source_doc` (sanitized slug) and `chunk_id`, never to a person. The cross-document perspective comparison in `parsed/_perspectives.json` follows this convention.

Within a single document, where multiple distinct views are recorded in one chunk, neutral markers `perspective_a`, `perspective_b`, etc. are used in the chunk's `perspectives_within_chunk` array, scoped to that chunk only.

## Source documents stay private

The `source-docs/` and `converted/` directories contain raw inputs that may carry names, filenames, and contextual identifiers. These directories are gitignored and never published. Only sanitized derivatives (`parsed/`, the indexes, downstream embeddings, and server responses) are public.

## Verification before any new component ships

Before a new skill, script, or pipeline ships data into the project, scan its output schema and prompt template for:
- Any `speaker`, `author`, `contributor` field that could leak personal names.
- Any free-text field where the LLM might silently include names.

Add an explicit anonymization clause to every Opus/agent prompt that handles corpus data. Verify with a grep pass over the produced output before declaring the work complete.
