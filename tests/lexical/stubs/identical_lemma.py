"""Attack vector L9: every Word emits the same placeholder Lemma.

Verifier must reject for ``identical_lemma_per_word``.
"""

from __future__ import annotations


REQUIRED_FIELDS = ("lemma", "gloss", "ref")


def emit_records() -> list[dict[str, object]]:
    return [
        {"lemma": "PLACEHOLDER", "gloss": "x", "ref": "GEN 1:1",
         "strong": "PLACEHOLDER"},
        {"lemma": "PLACEHOLDER", "gloss": "x", "ref": "GEN 1:2",
         "strong": "PLACEHOLDER"},
        {"lemma": "PLACEHOLDER", "gloss": "x", "ref": "GEN 1:3",
         "strong": "PLACEHOLDER"},
    ]


def emit_edges() -> list[dict[str, str]]:
    return [
        {"type": "IN_VERSE", "src": "w1", "dst": "GEN 1:1"},
        {"type": "INSTANCE_OF", "src": "w1", "dst": "PLACEHOLDER"},
        {"type": "INSTANCE_OF", "src": "w2", "dst": "PLACEHOLDER"},
    ]
