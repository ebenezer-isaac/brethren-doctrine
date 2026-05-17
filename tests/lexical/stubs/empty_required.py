"""Attack vector L7: required fields are empty strings.

A lazy adapter that returns records but leaves required string fields
blank. The verifier must reject for ``required_field_empty``.
"""

from __future__ import annotations


REQUIRED_FIELDS = ("lemma", "gloss", "ref")


def emit_records() -> list[dict[str, object]]:
    return [
        {"lemma": "", "gloss": "", "ref": "GEN 1:1", "strong": "H7225"},
        {"lemma": "", "gloss": "", "ref": "GEN 1:2", "strong": "H776"},
    ]


def emit_edges() -> list[dict[str, str]]:
    return [
        {"type": "IN_VERSE", "src": "w1", "dst": "GEN 1:1"},
        {"type": "INSTANCE_OF", "src": "w1", "dst": "H7225"},
    ]
