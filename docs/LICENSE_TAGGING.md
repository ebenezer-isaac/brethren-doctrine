# License Tagging

Every node, every chunk, and every Pipeline 2 evidence file carries an explicit `license` field. The synthesis layer (Pipeline 3 and the MCP server) enforces redistribution rules through `ingest/license_guard.py`.

## Why license tagging is load-bearing

Five facts shape the licensing posture:

1. The most authoritative open biblical data (MACULA, STEPBible, OpenBible) is CC BY 4.0. Bulk redistribution is allowed with attribution.
2. The most authoritative open Hebrew syntax dataset (ETCBC BHSA) is **CC BY-NC 4.0**. Personal use is fine; commercial redistribution requires DBG consent.
3. The open semantic-domain lexicon data (MARBLE / SDBH / Louw-Nida word senses embedded in MACULA) is **CC BY-NC**.
4. SBLGNT text is under the **SBLGNT EULA**: free for non-commercial redistribution, ≤ 500 verses per year without separate license.
5. Many cultural sources (Vatican.va, OCA, AG Fundamental Truths, modern Book of Concord translations) are © copyright with no open license; widespread fair-use practice tolerates personal-use ingest, but redistribution is forbidden.

Without explicit license tagging, the engine cannot honestly answer: "is this response safe to share publicly?" The answer depends on which sources were touched.

## Registered licenses

The canonical license registry. Every source slug maps to exactly one entry.

| License slug | SPDX equivalent | Bulk redistribute | Snippet redistribute | Notes |
|---|---|---|---|---|
| `public_domain` | `CC-PDDC` (informal) | allowed | allowed | Pre-1923 works in the US |
| `CC-BY` | `CC-BY-4.0` (assumed) | allowed (with attribution) | allowed | OpenBible site-wide |
| `CC-BY-4.0` | `CC-BY-4.0` | allowed (with attribution) | allowed | MACULA, STEPBible TAHOT/TAGNT/TVTMS, OSHB morphology, INTF NTVMR transcriptions, First1KGreek |
| `CC-BY-SA-4.0` | `CC-BY-SA-4.0` | allowed (derivative must propagate SA) | allowed | MorphGNT morphology, Theographic Bible Metadata |
| `CC-BY-NC-4.0` | `CC-BY-NC-4.0` | denied (personal use only) | allowed (≤ 100 words, ≤ 1% of source) | ETCBC BHSA, MARBLE / SDBH / Louw-Nida word senses, TTESV, ETCBC Peshitta |
| `SBLGNT-EULA` | proprietary | denied | allowed (≤ 500 verses per year aggregate; caller-tracked) | SBLGNT text |
| `parsed-sanitized` | proprietary | denied | allowed (≤ 100 words fair-use) | Pre-ingested Brethren teaching notes in `parsed/` |
| `©<vendor>` | proprietary | denied | allowed (≤ 100 words, ≤ 1% of source) under fair use | Vatican.va, AG, OCA, modern Tappert / Kolb-Wengert translations of Book of Concord, UMC Discipline glosses |
| `fair-use-policy` | proprietary | denied | allowed (≤ 100 words, ≤ 1% of source) | Anything ingested under fair-use that does not fit `©<vendor>` |
| `<unknown>` | n/a | denied | denied | Default for unrecognized license strings |

## Per-source license map

This is the canonical mapping from source slug to license slug. Used by ingest adapters to tag records at parse time.

### Lexical sources

| Source slug | License slug | Notes |
|---|---|---|
| `WLC` | `public_domain` | Westminster Leningrad Codex text |
| `OSHB-text` | `public_domain` | Underlying WLC text |
| `OSHB-morphology` | `CC-BY-4.0` | OSHB lemma + morph tags |
| `MACULA-Hebrew-text` | `public_domain` | WLC base |
| `MACULA-Hebrew-morphology` | `CC-BY-4.0` | OSHB / Clear morphology |
| `MACULA-Hebrew-syntax` | `CC-BY-4.0` | Clear syntax trees |
| `MACULA-Hebrew-glosses` | `CC-BY-4.0` | Cherith glosses |
| `MACULA-Hebrew-marble-sdbh` | `CC-BY-NC-4.0` | UBS MARBLE / SDBH word senses |
| `SBLGNT-text` | `SBLGNT-EULA` | SBL Greek NT text |
| `Nestle1904-text` | `public_domain` | Pre-1923 |
| `MorphGNT-morphology` | `CC-BY-SA-4.0` | Parse codes and lemmatization |
| `MACULA-Greek-syntax` | `CC-BY-4.0` | Clear syntax trees |
| `MACULA-Greek-glosses` | `CC-BY-4.0` | Berean glosses |
| `MACULA-Greek-louw-nida` | `CC-BY-NC-4.0` | UBS MARBLE Louw-Nida domains |
| `STEPBible-TAHOT` | `CC-BY-4.0` | Tagged Hebrew OT |
| `STEPBible-TAGNT` | `CC-BY-4.0` | Tagged Greek NT |
| `STEPBible-TVTMS` | `CC-BY-4.0` | Versification mapping |
| `STEPBible-TTESV` | `CC-BY-NC-4.0` | Tagged ESV (Tyndale-NC) |
| `STEPBible-TBESH` | `CC-BY-4.0` | Brief Hebrew lexicon |
| `STEPBible-TBESG` | `CC-BY-4.0` | Brief Greek lexicon |
| `STEPBible-TFLSJ` | `CC-BY-4.0` | LSJ formatted subset |
| `ETCBC-BHSA` | `CC-BY-NC-4.0` | Hebrew Bible syntactic database |
| `ETCBC-Peshitta` | `CC-BY-NC-4.0` | Syriac OT |
| `ETCBC-syrnt` | `CC-BY-NC-4.0` | Syriac NT |
| `ETCBC-DSS` | `CC-BY-NC-4.0` | Dead Sea Scrolls biblical fragments |
| `OpenBible-cross-refs` | `CC-BY` | Cross-reference graph |
| `TSK` | `public_domain` | 1880 Treasury of Scripture Knowledge |
| `Theographic-Bible-Metadata` | `CC-BY-SA-4.0` | People / places / events |
| `INTF-NTVMR` | `CC-BY-4.0` | NT manuscript transcriptions |
| `open-cbgm-3-john-sample` | `MIT` | Sample TEI in open-cbgm examples |
| `BibleHub-interlinear` | `fair-use-policy` | Web-fetch for cross-validation only; snippet-cite only |

### Cultural sources

| Source slug | License slug | Notes |
|---|---|---|
| `CCEL-ANF` | `public_domain` | Ante-Nicene Fathers, pre-1923 translations |
| `CCEL-NPNF1` | `public_domain` | Nicene/Post-Nicene Fathers series 1 |
| `CCEL-NPNF2` | `public_domain` | Nicene/Post-Nicene Fathers series 2 |
| `CCEL-Schaff-Creeds` | `public_domain` | Schaff's Creeds of Christendom |
| `First1KGreek` | `CC-BY-SA-4.0` | Open Greek and Latin |
| `Vatican.va-CCC` | `©Libreria-Editrice-Vaticana` | Catechism of the Catholic Church |
| `Vatican.va-encyclical` | `©Libreria-Editrice-Vaticana` | Papal encyclicals |
| `Vatican.va-vat2` | `©Libreria-Editrice-Vaticana` | Vatican II documents |
| `bookofconcord.org-PD` | `public_domain` | Triglotta-based older translations |
| `bookofconcord.org-modern` | `©Kolb-Wengert` | Modern Tappert / Kolb-Wengert (do not ingest) |
| `opc.org-WCF` | `public_domain` | Westminster Confession 1646 |
| `opc.org-WLC` | `public_domain` | Westminster Larger Catechism |
| `opc.org-WSC` | `public_domain` | Westminster Shorter Catechism |
| `the1689confession.com` | `public_domain` | 1689 LBC |
| `crcna.org-Heidelberg` | `public_domain` | Heidelberg Catechism 1563 |
| `crcna.org-Belgic` | `public_domain` | Belgic Confession 1561 |
| `crcna.org-Dort` | `public_domain` | Canons of Dort 1619 |
| `justus.anglican.org-39A` | `public_domain` | 39 Articles 1571 |
| `wikisource-39A` | `public_domain` | Wikisource 39 Articles |
| `justus.anglican.org-BCP1662` | `public_domain` | BCP 1662 |
| `umc.org-articles` | `public_domain` | UMC Articles of Religion |
| `wikisource-Schleitheim` | `public_domain` | Schleitheim Confession 1527 |
| `anabaptists.org-Schleitheim` | `public_domain` | Anabaptist mirror of Schleitheim |
| `ag.org-FT` | `©Assemblies-of-God` | AG Fundamental Truths; personal ingest only |
| `oca.org-Hopko` | `©OCA-Hopko-estate` | Hopko's *Orthodox Faith* |
| `brethrenarchive.org-PD` | `public_domain` | Darby / Kelly / Mackintosh pre-1928 |
| `stempublishing.com-PD` | `public_domain` | Same author cohort |
| `parsed/<doc>` | `parsed-sanitized` | This repo's Tier 1 Brethren corpus |
| `wikisource-conciliar` | `public_domain` | Conciliar texts (Nicaea, Constantinople, Ephesus, Chalcedon, etc.) |

## Composite license resolution

Some Pipeline 2 citations use composite source slugs that fuse multiple licensed components (e.g., `MACULA-Hebrew` = WLC text PD + OSHB morphology CC-BY-4.0 + Clear syntax CC-BY-4.0 + Cherith glosses CC-BY-4.0 + MARBLE/SDBH CC-BY-NC-4.0). The license registry above declares the **components** individually. The verdict file may cite the **composite** slug.

A pure function `resolve_composite_license(slug: str) -> str` in `ingest/license_guard.py` maps composite slugs to the **strictest applicable license** among components. Composite map:

| Composite slug | Components considered | Resolved license |
|---|---|---|
| `MACULA-Hebrew` | text PD, morphology CC-BY-4.0, syntax CC-BY-4.0, glosses CC-BY-4.0, MARBLE/SDBH CC-BY-NC-4.0 | `CC-BY-NC-4.0` |
| `MACULA-Greek` | Nestle1904 PD, SBLGNT EULA, syntax CC-BY-4.0, glosses CC-BY-4.0, Louw-Nida CC-BY-NC-4.0 | `CC-BY-NC-4.0` |

Severity ordering (strictest last):
```
public_domain < CC-BY < CC-BY-4.0 < CC-BY-SA-4.0 < CC-BY-NC-4.0 < SBLGNT-EULA < parsed-sanitized < fair-use-policy < ©<vendor> < <unknown>
```

`check_redistribute(license_str, ...)` accepts either a component slug or a composite slug. If the input matches a composite key, `resolve_composite_license` is invoked first and the resolved component-license drives the rule lookup.

Unit tests in `tests/test_license_guard.py` cover: `check_redistribute("MACULA-Hebrew", "bulk", ...)` returns `allowed: false` with reason "composite resolved to CC-BY-NC-4.0".

## license_guard contract

The single point of redistribution enforcement. Lives at `ingest/license_guard.py`.

```python
from typing import Literal

Mode = Literal["bulk", "snippet"]

def check_redistribute(
    license_str: str,
    mode: Mode,
    snippet_word_count: int = 0,
    source_work_word_count: int = 0,
) -> dict:
    """
    Returns: {"allowed": bool, "reason": str}

    Rules:
      - "public_domain", "CC-BY", "CC-BY-4.0" (case-insensitive): always allowed.
      - "CC-BY-SA-4.0": always allowed; SA-compat is the caller's responsibility downstream.
      - "CC-BY-NC-4.0": denied for bulk; allowed for snippet iff
            snippet_word_count <= 100 AND
            snippet_word_count <= 0.01 * source_work_word_count
      - "SBLGNT-EULA": denied for bulk; allowed for snippet (caller tracks 500-verses-per-year cap).
      - starts with "©" / "(C)" / "copyright" / "proprietary" / "fair-use" / "parsed-sanitized":
            denied for bulk; allowed for snippet iff
            snippet_word_count <= 100 AND
            snippet_word_count <= 0.01 * source_work_word_count.
      - empty or unrecognized: deny.
      - mode not in {"bulk", "snippet"}: deny.
    """
```

The function is pure (no I/O, no clocks, no random), case-insensitive on license_str, and bound by the registered licenses table above. Adding a new license string requires updating both this function and the registry above.

## evidence_safe_to_publish derivation

Every Pipeline 2 evidence file carries a `license_audit` block with `evidence_safe_to_publish: bool`. This is computed as:

```
evidence_safe_to_publish = all(
    check_redistribute(license=src.license, mode="bulk", ...)["allowed"]
    for src in license_audit.sources_used
)
```

If any cited source has `redistribute: false`, the evidence file is flagged as NOT safe to publish in bulk. The orchestrator records the question id in `evidence/_non_redistributable.txt` for the public release pipeline.

## response_safe_to_share derivation

Pipeline 3 synthesis output adds `response_safe_to_share: bool` to its envelope. This is stricter:

```
response_safe_to_share = (
    evidence_safe_to_publish AND
    all(
        check_redistribute(license=chunk.license, mode="snippet", ...)["allowed"]
        for chunk in cultural_overlay.representative_chunks
    )
)
```

If any cultural overlay chunk is `redistribute: false` AND would exceed snippet caps, the response is flagged as personal-use only and the chunk must be paraphrased rather than quoted verbatim.

## Public release flow

When publishing the engine code to GitHub:

1. Engine code (orchestrator, ingest adapters, MCP server, retrieval, embeddings, tests) ships under MIT or Apache-2.0 (final license decision pending).
2. `questions.json` ships (no licensed text; the question statements are the user's own framing).
3. `docs/` ships (own writing).
4. `tools/verify_*.py` ship.
5. `evidence/*.json` files where `evidence_safe_to_publish: true` ship.
6. `evidence/_non_redistributable.txt` ships (the list itself), but the listed evidence files are git-ignored from public push.
7. `parsed/` is gitignored entirely.
8. `responses/*.json` is gitignored entirely.
9. `data/private/` and `source-docs/` are gitignored entirely.

Anything tagged `CC-BY-NC-4.0`, `©<vendor>`, `parsed-sanitized`, or `SBLGNT-EULA` derived in bulk form does NOT go in the public push.

## Caller responsibilities

Callers of `license_guard.check_redistribute` carry three responsibilities the function cannot enforce:

1. **CC-BY attribution string**: include the source name in the published derivative.
2. **CC-BY-SA propagation**: if redistributing a SA-derived chunk, license the derivative under SA too.
3. **SBLGNT-EULA per-year counter**: track aggregate snippet-quote count across all calls; if approaching 500 verses per year, switch to paraphrase or pursue separate license.

These three are not in `check_redistribute` because they require state the function does not own. They live in the calling layer (Pipeline 3 synthesis or the MCP server's per-session tracker).

## Adding a new source

Steps:

1. Determine the license. Check the source repo / website for explicit license statement. Default to `<unknown>` if not stated; this denies all redistribution by default.
2. Add a row to the per-source map above.
3. If the license slug is new, add a row to the registered-licenses table and extend `check_redistribute` accordingly.
4. Update the ingest adapter for the source to emit the correct `license` field.
5. Run validation in license_audit mode to verify the new source's tags are coherent across emitted records.
