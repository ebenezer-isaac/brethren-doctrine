"""Attack vector L10: every record is emitted N times.

A lazy adapter that pads its output by repeating each genuine record
multiple times to inflate the count without adding information. The
verifier must reject either via ``identical_lemma_per_word`` (when
duplicates collapse to one lemma id) or via a deduplication check that
fails when ``len(records) > len(set(canonical_signature))``.

See ``RESEED_PLAN`` Z.1 item 5.
"""

from __future__ import annotations


REQUIRED_FIELDS = ("lemma", "gloss", "ref")


_BASE = [
    {"lemma": "alpha", "gloss": "first", "ref": "GEN 1:1", "strong": "H1"},
    {"lemma": "alpha", "gloss": "first", "ref": "GEN 1:1", "strong": "H1"},
]


def emit_records() -> list[dict[str, object]]:
    return list(_BASE) * 6


def emit_edges() -> list[dict[str, str]]:
    return [
        {"type": "IN_VERSE", "src": "w1", "dst": "GEN 1:1"} for _ in range(8)
    ] + [
        {"type": "INSTANCE_OF", "src": "w1", "dst": "H1"} for _ in range(8)
    ]
