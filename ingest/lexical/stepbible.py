"""QUARANTINED dead module. Do NOT revive. Do NOT wire into run.py.

This shared STEPBible TAHOT / TAGNT / TVTMS helper is DEAD CODE and a
revival hazard. It is retained only as an importable, defect-inert husk
so that the stale dead test scaffolding in
``tests/lexical/test_parsers.py`` (a module-level
``from ingest.lexical import (..., stepbible, ...)`` on a file whose
adapter calls already reference long-removed private symbols and fail
with AttributeError before this module is reached) keeps collecting
exactly as before. Deleting the file outright would turn that stale
import into a brand-new pytest collection error, which is precisely the
regression this quarantine must not introduce.

Why it is quarantined (forensic, from the bytes):

* ``docs/AUDIT_pos_collapse_blast_radius.md`` section 3 classifies this
  module DEFECTIVE-but-DEAD. Its id construction did
  ``pos = int(m.group(4))`` followed by ``f"{id_prefix}:{osis}.w{pos:02d}"``,
  the IDENTICAL position-collapse defect confirmed in
  ``docs/AUDIT_tahot_30row_deepdive.md``: ``int("0001") == int("01") == 1``,
  so two distinct zero-pad widths of an upstream ``#pos`` token collapse
  onto one stable id and silently overwrite the canonical record.
* Reproduced offline through this module's exact former code path over
  the real TAHOT bytes: 282239 raw rows, 282222 distinct ids, **17
  silent canonical overwrites** at 4 verses (Deu.30.16, Jdg.16.14,
  2Sa.23.33, 2Ki.25.3), the exact ``=X``-overwrites-``=L`` corruption.
* It was never imported by ``ingest/lexical/run.py`` (which dispatches
  only the per-source adapters ``ingest_stepbible_tahot`` /
  ``ingest_stepbible_tagnt`` / ``ingest_stepbible_ttesv`` / ...), so it
  never enlarged the live blast radius. The only repo reference is the
  stale dead test scaffolding noted above.

The faithful per-source adapters supersede this helper entirely:
``ingest/lexical/stepbible_tahot.py``, ``stepbible_tagnt.py``,
``stepbible_ttesv.py``, ``stepbible_proper_nouns.py``,
``stepbible_morph_codes.py``, ``stepbible_tvtms.py``, etc. Any need that
this module appeared to serve is met by those, none of which routes a
parsed upstream ``#pos`` token through ``int()``.

Every callable below raises immediately. There is no remaining code path
that can construct an ``int(pos)``-collapsed id. Re-enabling parsing here
is forbidden; use the per-source adapters.
"""

from __future__ import annotations

from typing import Any, NoReturn

_QUARANTINE_MESSAGE = (
    "ingest.lexical.stepbible is QUARANTINED dead code: it carried the "
    "int(pos) -> f'{pos:02d}' canonical-overwrite defect (17 silent TAHOT "
    "overwrites; see docs/AUDIT_pos_collapse_blast_radius.md section 3 and "
    "docs/AUDIT_tahot_30row_deepdive.md). It is not wired into "
    "ingest/lexical/run.py and must not be revived. Use the faithful "
    "per-source adapters instead: ingest.lexical.stepbible_tahot, "
    "stepbible_tagnt, stepbible_ttesv, stepbible_proper_nouns, "
    "stepbible_morph_codes, stepbible_tvtms."
)


def _quarantined(_name: str) -> NoReturn:
    raise RuntimeError(f"{_name}: {_QUARANTINE_MESSAGE}")


def _parse_ref(*_args: Any, **_kwargs: Any) -> NoReturn:
    _quarantined("stepbible._parse_ref")


def _iter_word_records(*_args: Any, **_kwargs: Any) -> NoReturn:
    _quarantined("stepbible._iter_word_records")


def parse_tvtms(*_args: Any, **_kwargs: Any) -> NoReturn:
    _quarantined("stepbible.parse_tvtms")


def _iter_records(*_args: Any, **_kwargs: Any) -> NoReturn:
    _quarantined("stepbible._iter_records")


def ingest_stepbible(*_args: Any, **_kwargs: Any) -> NoReturn:
    _quarantined("stepbible.ingest_stepbible")
