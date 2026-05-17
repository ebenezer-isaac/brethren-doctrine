"""Tests for docs/data_inventory_catalog.json schema contract.

Verifies the catalog against the RESEED_PLAN A.0 acceptance contract.
Loads the catalog at test-run time (not at authoring time per blind-verifier
constraint). Asserts top-level shape, per-source shape, per-field invariants,
procurement contract, required procurement coverage, and forbidden-phrase
absence (sample_values keys exempt).

No em-dashes or en-dashes in output or file content.
"""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO / "docs" / "data_inventory_catalog.json"


@functools.lru_cache(maxsize=1)
def _load_catalog() -> dict[str, Any]:
    """Load and parse the catalog JSON file."""
    if not CATALOG_PATH.exists():
        pytest.skip(f"Catalog file not found: {CATALOG_PATH}")
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_catalog_file_parses() -> None:
    """Catalog JSON parses without error."""
    catalog = _load_catalog()
    assert isinstance(catalog, dict)


def test_top_level_keys_present() -> None:
    """Top-level keys include required fields."""
    catalog = _load_catalog()
    required = {"$schema_version", "generated_at", "commit_baseline", "scope",
                "sources", "procurement_required", "explicit_deadends"}
    assert required.issubset(catalog.keys())


def test_scope_shape() -> None:
    """Scope has correct shape."""
    catalog = _load_catalog()
    scope = catalog["scope"]
    assert isinstance(scope, dict)
    assert "in_scope_layer_0" in scope
    assert "procurement_required" in scope
    assert "explicit_deadends" in scope
    assert isinstance(scope["in_scope_layer_0"], list)
    assert len(scope["in_scope_layer_0"]) > 0
    assert all(isinstance(s, str) for s in scope["in_scope_layer_0"])
    assert isinstance(scope["procurement_required"], list)
    assert len(scope["procurement_required"]) > 0
    assert all(isinstance(s, str) for s in scope["procurement_required"])
    assert isinstance(scope["explicit_deadends"], list)
    assert all(isinstance(s, str) for s in scope["explicit_deadends"])


def test_sources_is_nonempty_list() -> None:
    """Sources is a non-empty list of dicts."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    assert isinstance(sources, list)
    assert len(sources) > 0
    assert all(isinstance(s, dict) for s in sources)


def test_source_required_fields() -> None:
    """Each source has required fields (fields key optional for metadata sources)."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    required_fields = {
        "name", "layer", "license_id", "root_path", "record_unit",
        "total_records"
    }
    for i, source in enumerate(sources):
        missing = required_fields - source.keys()
        if missing:
            pytest.fail(
                f"Source index {i} ({source.get('name', 'unknown')}) "
                f"missing fields: {missing}"
            )


def test_source_field_types() -> None:
    """Each source has correct field types."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    for i, source in enumerate(sources):
        assert isinstance(source["name"], str) and source["name"]
        assert isinstance(source["layer"], (int, float))
        assert isinstance(source["license_id"], str)
        assert isinstance(source["root_path"], str)
        assert isinstance(source["record_unit"], str)
        assert isinstance(source["total_records"], int)
        assert source["total_records"] >= 0
        if "fields" in source:
            assert isinstance(source["fields"], list)


def test_source_names_unique() -> None:
    """Source names are unique."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    names = [s["name"] for s in sources]
    if len(set(names)) != len(names):
        dupes = [n for n in set(names) if names.count(n) > 1]
        pytest.fail(f"Duplicate source names: {dupes}")


def test_per_field_required_keys() -> None:
    """Each field in a source has required keys."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    required_field_keys = {
        "name", "type", "sample_seed", "sample_indices", "sample_values",
        "occurrence_rate", "null_rate"
    }
    for src_idx, source in enumerate(sources):
        if "fields" not in source:
            continue
        for field_idx, field in enumerate(source["fields"]):
            missing = required_field_keys - field.keys()
            if missing:
                pytest.fail(
                    f"Source {source['name']} field {field_idx} "
                    f"({field.get('name', 'unknown')}) "
                    f"missing keys: {missing}"
                )


def test_per_field_name_and_type() -> None:
    """Each field has non-empty name and valid type."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    valid_types = {"string", "int", "float", "bool", "list"}
    for source in sources:
        if "fields" not in source:
            continue
        for field in source["fields"]:
            assert isinstance(field["name"], str) and field["name"]
            assert field["type"] in valid_types


def test_per_field_sample_seed() -> None:
    """Each field has sample_seed equal to 1729."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    for source in sources:
        if "fields" not in source:
            continue
        for field in source["fields"]:
            assert field["sample_seed"] == 1729


def test_per_field_sample_indices_and_values_parallel() -> None:
    """sample_indices and sample_values have equal length."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    for source in sources:
        if "fields" not in source:
            continue
        for field in source["fields"]:
            indices = field["sample_indices"]
            values = field["sample_values"]
            assert isinstance(indices, list)
            assert isinstance(values, list)
            if len(indices) != len(values):
                pytest.fail(
                    f"Source {source['name']} field {field['name']}: "
                    f"sample_indices length {len(indices)} != "
                    f"sample_values length {len(values)}"
                )


def test_per_field_occurrence_and_null_rates() -> None:
    """occurrence_rate and null_rate are None or float in [0, 1]."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    for source in sources:
        if "fields" not in source:
            continue
        for field in source["fields"]:
            occ = field["occurrence_rate"]
            null = field["null_rate"]
            assert occ is None or isinstance(occ, (int, float))
            assert null is None or isinstance(null, (int, float))
            if occ is not None:
                assert 0.0 <= occ <= 1.0
            if null is not None:
                assert 0.0 <= null <= 1.0


def test_per_field_rate_sum() -> None:
    """If both rates numeric, sum to approximately 1.0 (tolerance 1e-6)."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    for source in sources:
        if "fields" not in source:
            continue
        for field in source["fields"]:
            occ = field["occurrence_rate"]
            null = field["null_rate"]
            if occ is not None and null is not None:
                total = occ + null
                if not (0.999999 <= total <= 1.000001):
                    pytest.fail(
                        f"Source {source['name']} field {field['name']}: "
                        f"occurrence_rate {occ} + null_rate {null} = {total}, "
                        f"not approximately 1.0"
                    )


def test_sampling_large_sources() -> None:
    """Sources with total_records >= 1000 have 1000 sample indices."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    for source in sources:
        if "fields" not in source:
            continue
        if source["total_records"] >= 1000:
            for field in source["fields"]:
                indices = field["sample_indices"]
                assert len(indices) == 1000, (
                    f"Source {source['name']} field {field['name']}: "
                    f"total_records={source['total_records']} >= 1000 "
                    f"but len(sample_indices)={len(indices)}"
                )


def test_sampling_indices_in_range() -> None:
    """Sample indices are in [0, total_records)."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    for source in sources:
        if "fields" not in source:
            continue
        if source["total_records"] >= 1000:
            total = source["total_records"]
            for field in source["fields"]:
                indices = field["sample_indices"]
                if indices:
                    if min(indices) < 0 or max(indices) >= total:
                        pytest.fail(
                            f"Source {source['name']} field {field['name']}: "
                            f"index out of range [0, {total})"
                        )


def test_sampling_indices_unique() -> None:
    """Sample indices have no duplicates."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    for source in sources:
        if "fields" not in source:
            continue
        if source["total_records"] >= 1000:
            for field in source["fields"]:
                indices = field["sample_indices"]
                if len(set(indices)) != len(indices):
                    pytest.fail(
                        f"Source {source['name']} field {field['name']}: "
                        f"sample_indices has duplicates"
                    )


def test_sampling_anti_contiguity() -> None:
    """Large sources have max stride >= 5 in sorted sample indices."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    for source in sources:
        if "fields" not in source:
            continue
        if source["total_records"] >= 1000:
            for field in source["fields"]:
                indices = field["sample_indices"]
                if len(indices) > 1:
                    sorted_idx = sorted(indices)
                    strides = [
                        sorted_idx[i + 1] - sorted_idx[i]
                        for i in range(len(sorted_idx) - 1)
                    ]
                    if strides and max(strides) < 5:
                        pytest.fail(
                            f"Source {source['name']} field {field['name']}: "
                            f"max stride {max(strides)} < 5 (too contiguous)"
                        )


def test_sampling_small_sources() -> None:
    """Sources with total_records < 1000 allowed to be contiguous or full."""
    catalog = _load_catalog()
    sources = catalog["sources"]
    for source in sources:
        if source["total_records"] < 1000:
            for field in source["fields"]:
                indices = field["sample_indices"]
                assert isinstance(indices, list)


def test_procurement_required_nonempty() -> None:
    """procurement_required is a non-empty list."""
    catalog = _load_catalog()
    procure = catalog["procurement_required"]
    assert isinstance(procure, list)
    assert len(procure) > 0


def test_procurement_entry_shape() -> None:
    """Each procurement entry has required fields."""
    catalog = _load_catalog()
    procure = catalog["procurement_required"]
    required_keys = {
        "source", "upstream_url", "url_status", "license_url",
        "license_text_sha256", "download_test", "license_id",
        "compatible_with_project", "deadend"
    }
    for i, entry in enumerate(procure):
        missing = required_keys - entry.keys()
        if missing:
            pytest.fail(
                f"Procurement entry {i} ({entry.get('source', 'unknown')}) "
                f"missing keys: {missing}"
            )


def test_procurement_download_test_shape() -> None:
    """Each procurement download_test has endpoint, status, bytes."""
    catalog = _load_catalog()
    procure = catalog["procurement_required"]
    for entry in procure:
        dl = entry["download_test"]
        assert isinstance(dl, dict)
        assert "endpoint" in dl
        assert "status" in dl
        assert "bytes" in dl
        assert isinstance(dl["status"], int)
        assert isinstance(dl["bytes"], int)


def test_procurement_contract() -> None:
    """Procurement entries satisfy download success or failure contract."""
    catalog = _load_catalog()
    procure = catalog["procurement_required"]
    failures = []
    for i, entry in enumerate(procure):
        dl = entry["download_test"]
        compat = entry.get("compatible_with_project", True)
        status = dl.get("status")
        bytes_count = dl.get("bytes", 0)
        success = (status == 200 and bytes_count >= 1024)
        if success:
            continue
        if compat is False:
            notes = entry.get("notes", "")
            if not notes:
                failures.append(
                    f"{i}: incompatible but no notes explaining failure"
                )
        else:
            failures.append(
                f"{i} ({entry.get('source', 'unknown')}): "
                f"download failed (status {status}, bytes {bytes_count}) "
                f"but compatible_with_project not False"
            )
    if failures:
        pytest.fail(
            f"Procurement contract violations: {failures[:5]}"
        )


def test_procurement_required_coverage() -> None:
    """Required procurement sources included."""
    catalog = _load_catalog()
    procure = catalog["procurement_required"]
    sources = {p["source"] for p in procure}
    required = {"peshitta", "vulgate-clementine", "coptic-scriptorium",
                "open-cbgm-3-john"}
    missing = required - sources
    if missing:
        pytest.fail(f"Missing required procurement sources: {missing}")


def test_no_em_or_en_dashes_in_file() -> None:
    """File text contains no em-dashes or en-dashes."""
    with open(CATALOG_PATH, encoding="utf-8") as f:
        content = f.read()
    if "—" in content:
        pytest.fail("File contains em-dashes (—)")
    if "–" in content:
        pytest.fail("File contains en-dashes (–)")


def test_no_forbidden_phrases_in_authored_prose() -> None:
    """Authored prose (outside sample_values) has no forbidden phrases."""
    catalog = _load_catalog()
    forbidden = {
        "deferred", "defer to", "out of scope", "v1.5", "TBD",
        "FIXME", "TODO", "XXX", "eventually"
    }

    def _walk_tree(node: Any, in_sample_values: bool = False) -> list[str]:
        """Recursively walk JSON tree, return violations."""
        violations = []
        if isinstance(node, dict):
            for key, value in node.items():
                in_samples = in_sample_values or key == "sample_values"
                violations.extend(_walk_tree(value, in_samples))
        elif isinstance(node, list):
            for item in node:
                violations.extend(_walk_tree(item, in_sample_values))
        elif isinstance(node, str) and not in_sample_values:
            lower = node.lower()
            for phrase in forbidden:
                if phrase in lower:
                    violations.append(
                        f"Found phrase {repr(phrase)} in {repr(node[:80])}"
                    )
        return violations

    violations = _walk_tree(catalog)
    if violations:
        pytest.fail(
            f"Forbidden phrases in authored prose: {violations[:5]}"
        )


def test_explicit_deadends_shape() -> None:
    """explicit_deadends is a list of dicts with required keys."""
    catalog = _load_catalog()
    deadends = catalog["explicit_deadends"]
    assert isinstance(deadends, list)
    required_keys = {"source", "reason", "evidence_ref"}
    for i, entry in enumerate(deadends):
        assert isinstance(entry, dict)
        missing = required_keys - entry.keys()
        if missing:
            pytest.fail(
                f"Deadend entry {i} ({entry.get('source', 'unknown')}) "
                f"missing keys: {missing}"
            )
        assert isinstance(entry["source"], str)
        assert isinstance(entry["reason"], str) and entry["reason"]
        assert isinstance(entry["evidence_ref"], str)
