"""Attack vector L3: ignores the requested verse and returns a fixed
Genesis 1:1 payload no matter what.

Verifier must reject for ``hardcoded_response``: when asked to emit a
second verse (e.g. MARK 1:1), the same payload is returned.
"""

from __future__ import annotations


REQUIRED_FIELDS = ("lemma", "gloss", "ref")

_FIXED_PAYLOAD: list[dict[str, object]] = [
    {"lemma": "rēšîṯ", "gloss": "beginning", "ref": "GEN 1:1", "strong": "H7225"},
]


def emit_records(verse: str | None = None) -> list[dict[str, object]]:
    # Intentionally ignores ``verse`` -- always returns the same payload.
    return list(_FIXED_PAYLOAD)


def emit_edges(verse: str | None = None) -> list[dict[str, str]]:
    return [
        {"type": "IN_VERSE", "src": "w1", "dst": "GEN 1:1"},
        {"type": "INSTANCE_OF", "src": "w1", "dst": "H7225"},
    ]
