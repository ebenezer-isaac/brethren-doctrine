"""Attack vector L14: edge direction reversed.

A lazy adapter that emits ``HAS_LEMMA`` edges from Verse to Word
instead of the canonical ``INSTANCE_OF`` (Word to Lemma) per
``RESEED_PLAN`` schema. The required edge floor for ``INSTANCE_OF`` is
therefore zero. The verifier must reject via ``edge_floor[INSTANCE_OF]``.

See ``graph/lexical.cypher`` for the canonical edge type contract.
"""

from __future__ import annotations


REQUIRED_FIELDS = ("lemma", "gloss", "ref")


def emit_records() -> list[dict[str, object]]:
    return [
        {"lemma": "alpha", "gloss": "first", "ref": "GEN 1:1", "strong": "H1"},
        {"lemma": "beta", "gloss": "second", "ref": "GEN 1:1", "strong": "H2"},
        {"lemma": "gamma", "gloss": "third", "ref": "GEN 1:1", "strong": "H3"},
        {"lemma": "delta", "gloss": "fourth", "ref": "GEN 1:1", "strong": "H4"},
        {"lemma": "epsilon", "gloss": "fifth", "ref": "GEN 1:1", "strong": "H5"},
        {"lemma": "zeta", "gloss": "sixth", "ref": "GEN 1:1", "strong": "H6"},
    ]


def emit_edges() -> list[dict[str, str]]:
    return [
        {"type": "IN_VERSE", "src": f"w{i}", "dst": "GEN 1:1"} for i in range(6)
    ] + [
        {"type": "HAS_LEMMA", "src": "GEN 1:1", "dst": f"w{i}"} for i in range(6)
    ]
