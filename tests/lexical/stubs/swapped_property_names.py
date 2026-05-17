"""Attack vector L11: lemma and gloss swapped.

A lazy adapter that maps source ``lemma`` text into the ``gloss`` slot
and English ``gloss`` text into the ``lemma`` slot. Every required
field is non-empty so a shallow ``IS NOT NULL`` check passes, but the
semantics are inverted. The Phase C coverage tests must catch this via
a character-set heuristic (e.g. Hebrew lemmas must contain Hebrew code
points; English glosses must be ASCII-ish).

The Z-tier driver detects this indirectly via the second-verse cross-
check, which would observe the same English-in-lemma pattern across
unrelated verses (``hardcoded_response`` semantic divergence) only if
the stub uses one fixed lemma; the explicit attack-vector check is
defined per-adapter in Phase C. For Z purposes the stub fails because
its required ``lemma`` field, while non-empty, has the wrong content
type, which is detected by the dedicated coverage assertion added in
``tests/lexical/test_verify_catches_lazy_adapter.py``.
"""

from __future__ import annotations


REQUIRED_FIELDS = ("lemma", "gloss", "ref")


def emit_records() -> list[dict[str, object]]:
    return [
        {"lemma": "beginning", "gloss": "rēšîṯ", "ref": "GEN 1:1", "strong": "H7225"},
        {"lemma": "create", "gloss": "bārāʾ", "ref": "GEN 1:1", "strong": "H1254"},
        {"lemma": "God", "gloss": "ʾĕlōhîm", "ref": "GEN 1:1", "strong": "H430"},
        {"lemma": "object-marker", "gloss": "ʾēṯ", "ref": "GEN 1:1", "strong": "H853"},
        {"lemma": "heavens", "gloss": "šāmayim", "ref": "GEN 1:1", "strong": "H8064"},
    ]


def emit_edges() -> list[dict[str, str]]:
    return [
        {"type": "IN_VERSE", "src": f"w{i}", "dst": "GEN 1:1"} for i in range(6)
    ] + [
        {"type": "INSTANCE_OF", "src": f"w{i}", "dst": f"H{i}"} for i in range(6)
    ]


def gloss_in_lemma_ratio() -> float:
    """Diagnostic used by the adversarial test.

    Returns the fraction of records whose ``lemma`` contains only
    ASCII letters (i.e. looks like English), which is the swap
    signature for Hebrew/Greek source adapters.
    """
    recs = emit_records()
    ascii_lemmas = sum(
        1 for r in recs
        if isinstance(r["lemma"], str) and r["lemma"].isascii() and r["lemma"].replace(" ", "").replace("-", "").isalpha()
    )
    return ascii_lemmas / len(recs) if recs else 0.0
