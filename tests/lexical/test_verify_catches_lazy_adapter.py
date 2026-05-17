"""Adversarial verifier test (RESEED_PLAN Z.3 + Z.1 item 5).

Run ``tools/verify_adapter_template.py`` against each broken stub in
``tests/lexical/stubs/`` and assert each attack vector is caught.

Attack vector -> required check:
* empty_required.py            -> required_field_empty
* identical_lemma.py           -> identical_lemma_per_word
* zero_records.py              -> record_count_zero
* hardcoded_fixture.py         -> hardcoded_response
* minimal_edges.py             -> edge_floor[*]
* nan_inf_numeric.py           -> required_field_empty (NaN/Inf treated as empty)
* duplicate_records.py         -> identical_lemma_per_word (dedup collapse)
* swapped_property_names.py    -> swap heuristic (custom assertion below)
* mutated_strings.py           -> case-preservation assertion (custom)
* silent_exception_swallow.py  -> count shortfall vs EXPECTED_RECORD_COUNT
* reversed_edge_direction.py   -> edge_floor[INSTANCE_OF]
* hash_ordered.py              -> required_field_empty (omitted transliteration)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import verify_adapter_template as vat  # noqa: E402


EDGE_FLOOR = 5


@pytest.mark.parametrize(
    "module_name, expected_failure_substring",
    [
        ("tests.lexical.stubs.empty_required", "required_field_empty"),
        ("tests.lexical.stubs.identical_lemma", "identical_lemma_per_word"),
        ("tests.lexical.stubs.zero_records", "record_count_zero"),
        ("tests.lexical.stubs.hardcoded_fixture", "hardcoded_response"),
        ("tests.lexical.stubs.minimal_edges", "edge_floor"),
        ("tests.lexical.stubs.nan_inf_numeric", "required_field_empty"),
        ("tests.lexical.stubs.duplicate_records", "identical_lemma_per_word"),
        ("tests.lexical.stubs.reversed_edge_direction", "edge_floor"),
        ("tests.lexical.stubs.hash_ordered", "required_field_empty"),
    ],
)
def test_broken_stub_is_caught(module_name: str, expected_failure_substring: str) -> None:
    ok, results = vat.verify_adapter(module_name, schema_md=None, edge_floor=EDGE_FLOOR)
    assert not ok, (
        f"verifier MISSED attack vector for {module_name}; results: "
        f"{[r.format() for r in results]}"
    )
    failed = [r for r in results if not r.ok]
    assert any(expected_failure_substring in r.name for r in failed), (
        f"verifier failed on something OTHER than {expected_failure_substring!r}; "
        f"failed checks were: {[r.name for r in failed]}"
    )


def test_nan_inf_numeric_records_carry_non_finite() -> None:
    import math
    mod = importlib.import_module("tests.lexical.stubs.nan_inf_numeric")
    recs = mod.emit_records()
    non_finite = sum(
        1 for r in recs
        if isinstance(r.get("confidence"), float)
        and (math.isnan(r["confidence"]) or math.isinf(r["confidence"]))
    )
    assert non_finite == len(recs), (
        f"stub must emit non-finite confidence for every record; got {non_finite}/{len(recs)}"
    )


def test_duplicate_records_stub_has_no_distinct_lemma_ids() -> None:
    mod = importlib.import_module("tests.lexical.stubs.duplicate_records")
    recs = mod.emit_records()
    distinct = {r.get("strong") for r in recs}
    assert len(distinct) < len(recs) / 2, (
        f"stub must duplicate records (collapse strong); got {len(distinct)} distinct"
    )


def test_swapped_property_names_detected_by_ascii_lemma_heuristic() -> None:
    mod = importlib.import_module("tests.lexical.stubs.swapped_property_names")
    ratio = mod.gloss_in_lemma_ratio()
    assert ratio >= 0.8, (
        f"stub must populate lemma slot with ASCII (English) values; got {ratio:.2f}"
    )


def test_mutated_strings_stub_lowercases_greek() -> None:
    mod = importlib.import_module("tests.lexical.stubs.mutated_strings")
    recs = mod.emit_records()
    expected = mod.EXPECTED_VERBATIM
    differences = 0
    for r in recs:
        strong = r.get("strong")
        if strong in expected:
            actual = r["lemma"]
            if actual != expected[strong]:
                differences += 1
    assert differences >= 1, (
        f"stub must produce at least one case-mutated value vs EXPECTED_VERBATIM; "
        f"got {differences} differences"
    )


def test_silent_exception_swallow_shortfall_below_expected() -> None:
    mod = importlib.import_module("tests.lexical.stubs.silent_exception_swallow")
    recs = mod.emit_records()
    assert len(recs) <= mod.EXPECTED_RECORD_COUNT * 0.5, (
        f"stub must drop the majority of records via silent except; "
        f"got {len(recs)}/{mod.EXPECTED_RECORD_COUNT}"
    )


def test_reversed_edge_direction_emits_zero_instance_of() -> None:
    mod = importlib.import_module("tests.lexical.stubs.reversed_edge_direction")
    edges = mod.emit_edges()
    instance_of = [e for e in edges if e["type"] == "INSTANCE_OF"]
    has_lemma = [e for e in edges if e["type"] == "HAS_LEMMA"]
    assert len(instance_of) == 0, "stub must emit zero INSTANCE_OF edges"
    assert len(has_lemma) >= 1, "stub must emit at least one reversed HAS_LEMMA edge"


def test_hash_ordered_stub_omits_transliteration_on_some_rows() -> None:
    mod = importlib.import_module("tests.lexical.stubs.hash_ordered")
    recs = mod.emit_records()
    empty_translit = sum(
        1 for r in recs if not (r.get("transliteration") or "").strip()
    )
    assert empty_translit >= 1, (
        "stub must omit transliteration on at least one row to defeat "
        "naive hash-sort verifiers"
    )


def test_hash_ordered_is_deterministic() -> None:
    mod = importlib.import_module("tests.lexical.stubs.hash_ordered")
    a = mod.emit_records()
    b = mod.emit_records()
    assert a == b


def test_twelve_stubs_present() -> None:
    stubs_dir = REPO / "tests" / "lexical" / "stubs"
    expected = {
        "empty_required.py",
        "identical_lemma.py",
        "zero_records.py",
        "hardcoded_fixture.py",
        "minimal_edges.py",
        "nan_inf_numeric.py",
        "duplicate_records.py",
        "swapped_property_names.py",
        "mutated_strings.py",
        "silent_exception_swallow.py",
        "reversed_edge_direction.py",
        "hash_ordered.py",
    }
    present = {p.name for p in stubs_dir.glob("*.py") if p.name != "__init__.py"
               and p.name != "broken_adapter.py"}
    missing = expected - present
    assert not missing, f"missing stub adapters: {sorted(missing)}"
    assert len(expected) == 12


def test_verifier_self_test_passes() -> None:
    assert vat.main(["--self-test"]) == 0


def test_verifier_main_with_broken_stub_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    rc = vat.main([
        "--adapter", "tests.lexical.stubs.zero_records",
        "--edge-floor", str(EDGE_FLOOR),
    ])
    assert rc == 1
