"""Attack vector L15: records ordered by hash with seed-correlated content.

A lazy adapter that sorts its output by ``sha256(record)`` so that the
snapshot triangle-test sort step (``tools/snapshot_counts.py``) becomes
a no-op; whatever the content, the post-sort byte sequence depends only
on the hash. This can mask a missing-field bug if the verifier compares
sorted-hash sequences without inspecting field values.

The Z driver detects this via the per-row presence vector
(``snapshot_counts.per_row_presence_vector``) which records the SET of
field names per row before sorting; if the field set differs across
runs, the vector differs even if the hash sort is stable.

For the adversarial harness, the stub deliberately omits an expected
field on a fraction of records; the verifier must flag
``required_field_empty`` despite the apparently-clean sorted output.
"""

from __future__ import annotations

import hashlib
import json


REQUIRED_FIELDS = ("lemma", "gloss", "ref", "transliteration")


_RAW = [
    {"lemma": "alpha", "gloss": "first", "ref": "GEN 1:1",
     "strong": "H1", "transliteration": "ʾalp"},
    {"lemma": "beta", "gloss": "second", "ref": "GEN 1:1",
     "strong": "H2", "transliteration": "bet"},
    {"lemma": "gamma", "gloss": "third", "ref": "GEN 1:1",
     "strong": "H3", "transliteration": ""},
    {"lemma": "delta", "gloss": "fourth", "ref": "GEN 1:1",
     "strong": "H4", "transliteration": "dlt"},
    {"lemma": "epsilon", "gloss": "fifth", "ref": "GEN 1:1",
     "strong": "H5", "transliteration": ""},
    {"lemma": "zeta", "gloss": "sixth", "ref": "GEN 1:1",
     "strong": "H6", "transliteration": "zyn"},
]


def _hash_key(r: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(r, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def emit_records() -> list[dict[str, object]]:
    return sorted(_RAW, key=_hash_key)


def emit_edges() -> list[dict[str, str]]:
    return [
        {"type": "IN_VERSE", "src": f"w{i}", "dst": "GEN 1:1"} for i in range(6)
    ] + [
        {"type": "INSTANCE_OF", "src": f"w{i}", "dst": f"H{i}"} for i in range(6)
    ]
