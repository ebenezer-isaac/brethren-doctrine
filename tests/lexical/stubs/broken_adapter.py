"""Aggregator that re-exports the five broken adapter stubs.

Each attack vector lives in its own sibling module so the verifier can
test them independently.

Attack vectors:

1. ``empty_required.py``: every required field returns empty string.
2. ``identical_lemma.py``: every Word maps to the same Lemma placeholder.
3. ``zero_records.py``: returns no records but exits 0.
4. ``hardcoded_fixture.py``: ignores the requested verse and returns a
   fixed Genesis 1:1 payload no matter what.
5. ``minimal_edges.py``: emits exactly 1 edge per required type (below
   the edge floor).
"""

from . import (
    empty_required,
    hardcoded_fixture,
    identical_lemma,
    minimal_edges,
    zero_records,
)


__all__ = [
    "empty_required",
    "hardcoded_fixture",
    "identical_lemma",
    "minimal_edges",
    "zero_records",
]
