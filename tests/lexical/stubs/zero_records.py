"""Attack vector L5: returns zero records but exits 0.

Verifier must reject for ``record_count_zero``.
"""

from __future__ import annotations


REQUIRED_FIELDS = ("lemma", "gloss", "ref")


def emit_records() -> list[dict[str, object]]:
    return []


def emit_edges() -> list[dict[str, str]]:
    return []
