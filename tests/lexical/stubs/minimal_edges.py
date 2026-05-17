"""Attack vector L8: emits exactly one edge per required type.

Verifier must reject for ``edge_floor`` (configured floor > 1).
"""

from __future__ import annotations


REQUIRED_FIELDS = ("lemma", "gloss", "ref")


def emit_records() -> list[dict[str, object]]:
    return [
        {"lemma": "a", "gloss": "alpha", "ref": "GEN 1:1", "strong": "H1"},
        {"lemma": "b", "gloss": "beta", "ref": "GEN 1:2", "strong": "H2"},
        {"lemma": "c", "gloss": "gamma", "ref": "GEN 1:3", "strong": "H3"},
    ]


def emit_edges() -> list[dict[str, str]]:
    return [
        {"type": "IN_VERSE", "src": "w1", "dst": "GEN 1:1"},
        {"type": "INSTANCE_OF", "src": "w1", "dst": "H1"},
    ]
