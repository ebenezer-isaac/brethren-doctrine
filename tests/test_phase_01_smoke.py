"""Phase 01 end-to-end smoke test.

These integration assertions run against the live Docker stacks brought up by
Task 01.05. They are skipped if the stacks are unreachable.
"""

from __future__ import annotations

import os
import subprocess
import urllib.error
import urllib.request

import pytest

from ingest.canonical_strongs import canonical_strongs
from ingest.license_guard import check_redistribute, resolve_composite_license
from ingest.versification_mapper import VersificationMapper


def _container_running(name: str) -> bool:
    try:
        out = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", name],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return out.stdout.strip() == "true"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def test_lexical_stack_up() -> None:
    assert _container_running("lexical-neo4j")
    assert _container_running("lexical-qdrant")


def test_cultural_stack_up() -> None:
    assert _container_running("cultural-neo4j")
    assert _container_running("cultural-qdrant")


def test_both_neo4j_respond() -> None:
    assert _http_ok("http://localhost:7475")
    assert _http_ok("http://localhost:7476")


def test_qdrant_collections_present() -> None:
    assert _http_ok("http://localhost:7100/collections/lex_col")
    assert _http_ok("http://localhost:7101/collections/cult_col")


def test_airgap_dns_cross_network_fails() -> None:
    lex_to_cul = subprocess.run(
        ["docker", "exec", "lexical-neo4j", "getent", "hosts", "cultural-neo4j"],
        capture_output=True,
        timeout=10,
        check=False,
    )
    cul_to_lex = subprocess.run(
        ["docker", "exec", "cultural-neo4j", "getent", "hosts", "lexical-neo4j"],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert lex_to_cul.returncode == 2
    assert cul_to_lex.returncode == 2


def test_canonical_strongs_ambiguous_raises_without_lang() -> None:
    with pytest.raises(ValueError):
        canonical_strongs("0430")
    assert canonical_strongs("0430", lang="hb") == ("H0430", None)


def test_license_guard_nc_bulk_denied() -> None:
    assert check_redistribute("CC-BY-NC-4.0", "bulk", 0, 0)["allowed"] is False


def test_versification_mapper_stub_identity() -> None:
    mapper = VersificationMapper(None)
    res = mapper.resolve("Psa.51.1", "english", "hebrew")
    assert res["to_ref"] == "Psa.51.1"
    assert res["rule_type"] == "identity"


def test_composite_license_resolves_macula_hebrew() -> None:
    assert resolve_composite_license("MACULA-Hebrew") == "CC-BY-NC-4.0"


@pytest.fixture(autouse=True)
def _skip_if_docker_absent() -> None:
    if os.environ.get("SKIP_DOCKER_TESTS"):
        pytest.skip("docker tests skipped via env")
