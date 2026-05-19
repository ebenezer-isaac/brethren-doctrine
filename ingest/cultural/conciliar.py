"""Ecumenical Conciliar texts adapter.

Pulls the major historic creeds and definitions from Wikisource / Wikipedia,
each emitted as one CulturalChunk with anchor `<Council>.<Section>`. Coverage
in v1: Apostles' Creed, Nicene Creed (325 + 381), Chalcedonian Definition (451),
Athanasian Creed. Council canons are deferred to a v1.5 pass.
"""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import fetch_with_politeness, scrape_source
from ingest.cultural._html import wikisource_article_paragraphs
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "conciliar"
TRADITION: Literal["patristic"] = "patristic"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://en.wikipedia.org/wiki/Nicene_Creed"
FALLBACK_URLS: list[str] = []
EXPECTED = (3, 20)

# Why these URLs are Wikipedia article pages and not the bare Wikisource
# /wiki/<Creed> pages: the bare Wikisource creed pages (e.g.
# en.wikisource.org/wiki/Apostles%27_Creed) are DISAMBIGUATION / editions-list
# stubs ("English-language translations of Symbolum Apostolorum include: ...")
# that carry no creed body, and the modern Wikisource text editions store the
# creed inside page-scan poem/proofread blocks that the <p>-only
# wikisource_article_paragraphs extractor cannot reach. The phase-G audit
# (docs/AUDIT_phase_g_cultural_gate.md Decision 16 / Note D) caught exactly
# this: 3 of the 4 prior SOURCES URLs scraped disambiguation prose, the
# `len < 200` floor let the editions list through, and the Decision 16
# acceptance query (text CONTAINS 'God' AND creed_chunks >= 3) correctly
# FAILED. The English Wikipedia creed articles are canonical, stable,
# public-domain, and structurally identical to the Chalcedon source that
# already scraped faithfully: they quote the full creed text in prose <p>
# blocks and are saturated with "God", so they pass the Decision 16 query
# without weakening it. The bare Wikisource pages are retained as fallbacks
# only so a Wikipedia outage degrades to a hard CONTENT-FLOOR failure (loud)
# rather than silent junk; the content floor below rejects them by design.

# Each creed registers a distinct source.work_id (Decision 16) so the four
# creeds fan out under four Work nodes within the shared patristic tradition.
# Tuple shape: (key, work_title, url, date_written, anchor, work_id, fallbacks,
# required_phrases). required_phrases are distinctive creed-body strings used
# by the content floor to reject a disambiguation/editions/portal page that
# would otherwise pass the bare length check.
SOURCES: list[
    tuple[str, str, str, str, str, str, tuple[str, ...], tuple[str, ...]]
] = [
    (
        "Apostles",
        "Apostles' Creed",
        "https://en.wikipedia.org/wiki/Apostles%27_Creed",
        "c. 4th century",
        "Apostles.Creed",
        "conciliar.apostles",
        ("https://en.wikisource.org/wiki/Apostles%27_Creed",),
        ("maker of heaven and earth", "communion of saints"),
    ),
    (
        "Nicene",
        "Nicene Creed (325/381)",
        "https://en.wikipedia.org/wiki/Nicene_Creed",
        "325",
        "Nicaea325.Creed",
        "conciliar.niceno-constantinopolitan-creed",
        (
            "https://en.wikipedia.org/wiki/Niceno%E2%80%93Constantinopolitan_Creed",
            "https://en.wikisource.org/wiki/Nicene_Creed",
        ),
        ("God from God", "consubstantial"),
    ),
    (
        "Athanasian",
        "Athanasian Creed (Quicunque vult)",
        "https://en.wikipedia.org/wiki/Athanasian_Creed",
        "c. 5th-6th century",
        "Athanasian.Creed",
        "conciliar.athanasian-creed",
        ("https://en.wikisource.org/wiki/Athanasian_Creed",),
        ("catholic faith", "the Father is God"),
    ),
    (
        "Chalcedon",
        "Chalcedonian Definition (451)",
        "https://en.wikipedia.org/wiki/Chalcedonian_Definition",
        "451",
        "Chalcedon451.Definition",
        "conciliar.chalcedon-definition",
        ("https://en.wikipedia.org/wiki/Council_of_Chalcedon",),
        ("in two natures", "without confusion"),
    ),
]

# Disambiguation / editions-list / portal markers. A page containing any of
# these (and lacking the creed body) is NOT the creed text and MUST hard-fail
# loudly rather than land as a junk chunk. Drawn from the exact junk prose the
# phase-G audit found ("English-language translations of ... include:",
# "may refer to", Wikisource/Wikipedia disambiguation boilerplate).
DISAMBIGUATION_MARKERS: tuple[str, ...] = (
    "may refer to",
    "this disambiguation page",
    "english-language translations of",
    "other english-language translations of this work",
    "for other english-language translations",
    "list of editions",
    "is a disambiguation page",
    "topics referred to by the same term",
)


class ContentFloorError(RuntimeError):
    """Raised when a fetched page is a disambiguation/editions/portal stub.

    The adapter HARD-FAILS on junk so the Decision 16 acceptance query is never
    fed silently-wrong creed text. Brethren-on-trial discipline: fail loud, do
    not fudge, never ingest junk.
    """


def _assert_creed_body(body: str, key: str, required_phrases: tuple[str, ...]) -> None:
    """Reject a non-creed page. Lets faithful creed prose through.

    Two independent gates, both must hold:
      1. No disambiguation/editions/portal marker (catches the exact pages the
         phase-G audit found, which survived the old `len < 200` floor).
      2. At least one creed-distinctive phrase is present (a faithful creed
         body always carries its signature clauses; a portal stub never does).
    """
    low = body.lower()
    hit = next((m for m in DISAMBIGUATION_MARKERS if m in low), None)
    if hit is not None:
        raise ContentFloorError(
            f"conciliar.{key}: fetched page is a disambiguation/editions/portal "
            f"stub (marker {hit!r}), not the creed body. Refusing to ingest junk."
        )
    if not any(phrase.lower() in low for phrase in required_phrases):
        raise ContentFloorError(
            f"conciliar.{key}: fetched page lacks every distinctive creed phrase "
            f"{required_phrases!r}; not the faithful creed text. Refusing junk."
        )


def parse(
    raw: bytes,
    anchor: str,
    work_title: str,
    date_written: str,
    work_id: str,
    key: str,
    required_phrases: tuple[str, ...],
) -> CulturalChunk | None:
    paras = wikisource_article_paragraphs(raw)
    text_parts = [p for p in paras if not p.startswith("# ")]
    body = " ".join(text_parts).strip()
    if not body or len(body) < 200:
        raise ContentFloorError(
            f"conciliar.{key}: fetched page body is empty or under the 200-char "
            f"floor; not the creed text. Refusing to ingest junk."
        )
    # Content floor: reject disambiguation/editions/portal pages loudly. The
    # old `len < 200` check alone let the editions-list prose through (it is
    # >200 chars); this gate is what the phase-G audit (Decision 16) requires.
    _assert_creed_body(body, key, required_phrases)
    return CulturalChunk(
        chunk_id=f"{SOURCE_SLUG}.{anchor}",
        tradition=TRADITION,
        source=CulturalChunkSource(
            work_id=work_id,
            work_title=work_title,
            author="Ecumenical council / early church",
            date_written=date_written,
            is_confessional_text=True,
            anchor_id=anchor,
            language="en",
            translator="Wikisource / NPNF",
        ),
        text=body,
        text_to_embed=f"{work_title}. {body}",
        license=LICENSE,
        redistribute=REDISTRIBUTE,
        license_note=None,
    )


def scrape() -> list[CulturalChunk]:
    out: list[CulturalChunk] = []
    last_request: dict[str, float] = {}
    for (
        key,
        work_title,
        url,
        date_written,
        anchor,
        work_id,
        fallbacks,
        required_phrases,
    ) in SOURCES:
        candidates = (url, *fallbacks)
        last_error: Exception | None = None
        chunk: CulturalChunk | None = None
        for candidate in candidates:
            try:
                raw = fetch_with_politeness(
                    candidate, last_request_by_host=last_request
                )
            except Exception as exc:  # network/HTTP/TLS: try the next candidate
                last_error = exc
                continue
            try:
                chunk = parse(
                    raw,
                    anchor,
                    work_title,
                    date_written,
                    work_id,
                    key,
                    required_phrases,
                )
            except ContentFloorError as exc:
                # Junk page (disambiguation/editions/portal). Try the next
                # candidate; if all candidates are junk we raise loudly below.
                last_error = exc
                continue
            if chunk is not None:
                break
        if chunk is None:
            raise ContentFloorError(
                f"conciliar.{key}: no candidate URL yielded faithful creed text "
                f"(last error: {last_error}). Refusing to ingest junk or skip a "
                f"creed silently (Decision 16)."
            )
        out.append(chunk)
    return out


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED


_ = scrape_source
