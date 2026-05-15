"""ETCBC BHSA adapter (Pipeline 1) via text-fabric.

Loads ETCBC/bhsa v2021 via text-fabric. Emits :TFNode records for clauses,
phrases, and words. License: CC-BY-NC-4.0, redistribute False.

Phase 02 keeps BHSA optional: if text-fabric is not installed or BHSA data is
not available locally, ingest_bhsa returns an empty count dict and logs a
skip reason. Real-run verification requires running the actual ingest.
"""

from __future__ import annotations

from collections.abc import Iterator

from ingest.lexical._common import Settings, get_lexical_driver, upsert_records
from ingest.models import GraphEdge, LexicalRecord

LICENSE = "CC-BY-NC-4.0"
LICENSE_NOTE = "ETCBC BHSA, CC-BY-NC-4.0 (personal use only)"
SOURCE_SLUG = "bhsa"
ID_PREFIX = "bhsa"

_BHSA_BOOK_OSIS = {
    "Genesis": "Gen",
    "Exodus": "Exod",
    "Leviticus": "Lev",
    "Numeri": "Num",
    "Deuteronomium": "Deut",
    "Josua": "Josh",
    "Judices": "Judg",
    "Ruth": "Ruth",
    "Samuel_I": "1Sam",
    "Samuel_II": "2Sam",
    "Reges_I": "1Kgs",
    "Reges_II": "2Kgs",
    "Chronica_I": "1Chr",
    "Chronica_II": "2Chr",
    "Esra": "Ezra",
    "Nehemia": "Neh",
    "Esther": "Esth",
    "Iob": "Job",
    "Psalmi": "Ps",
    "Proverbia": "Prov",
    "Ecclesiastes": "Eccl",
    "Canticum": "Song",
    "Jesaia": "Isa",
    "Jeremia": "Jer",
    "Threni": "Lam",
    "Ezechiel": "Ezek",
    "Daniel": "Dan",
    "Hosea": "Hos",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obadia": "Obad",
    "Jona": "Jonah",
    "Micha": "Mic",
    "Nahum": "Nah",
    "Habakuk": "Hab",
    "Zephania": "Zeph",
    "Haggai": "Hag",
    "Sacharia": "Zech",
    "Maleachi": "Mal",
}


def _try_load_tf() -> object | None:
    try:
        from tf.app import use  # type: ignore[import-untyped]
    except ImportError:
        return None
    try:
        app: object = use("ETCBC/bhsa", version="2021", locations="~/text-fabric-data/github")
        return app
    except Exception:  # noqa: BLE001
        return None


def _emit_tfnodes(app: object) -> Iterator[LexicalRecord]:
    F = app.api.F  # type: ignore[attr-defined]
    L = app.api.L  # type: ignore[attr-defined]

    for otype in ("word", "phrase", "clause"):
        for node in F.otype.s(otype):
            book_node = L.u(node, otype="book")
            if not book_node:
                continue
            book_name = F.book.v(book_node[0])
            book = _BHSA_BOOK_OSIS.get(book_name, book_name)
            chap_node = L.u(node, otype="chapter")
            verse_node = L.u(node, otype="verse")
            chap = F.chapter.v(chap_node[0]) if chap_node else 0
            verse = F.verse.v(verse_node[0]) if verse_node else 0
            node_id = f"{ID_PREFIX}:tf:{node}"
            edges: list[GraphEdge] = []
            yield LexicalRecord(
                record_type="TFNode",
                id=node_id,
                properties={
                    "otype": otype,
                    "tf_node": int(node),
                    "book": book,
                    "chapter": int(chap) if chap else 0,
                    "verse": int(verse) if verse else 0,
                    "lex": F.lex.v(node) or "",
                    "g_word_utf8": F.g_word_utf8.v(node) or "" if otype == "word" else "",
                    "source": SOURCE_SLUG,
                },
                edges=edges,
                text_to_embed=F.g_word_utf8.v(node) or "" if otype == "word" else "",
                license=LICENSE,
                redistribute=False,
                license_note=LICENSE_NOTE,
            )


def ingest_bhsa(settings: Settings) -> dict[str, int]:
    app = _try_load_tf()
    if app is None:
        return {"_skipped": 0}
    driver = get_lexical_driver(settings)
    try:
        return upsert_records(driver, _emit_tfnodes(app), batch_size=5000)
    finally:
        driver.close()
