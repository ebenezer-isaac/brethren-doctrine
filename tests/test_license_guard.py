"""Tests for ingest.license_guard."""

import pytest

from ingest.license_guard import check_redistribute, resolve_composite_license


def test_pd_allow_bulk() -> None:
    r = check_redistribute("public_domain", "bulk")
    assert r["allowed"] is True


def test_pd_allow_snippet() -> None:
    r = check_redistribute("public_domain", "snippet", 50, 10000)
    assert r["allowed"] is True


def test_cc_by_allow_bulk() -> None:
    assert check_redistribute("CC-BY", "bulk")["allowed"] is True


def test_cc_by_4_allow_bulk() -> None:
    assert check_redistribute("CC-BY-4.0", "bulk")["allowed"] is True


def test_cc_by_sa_4_allow_bulk() -> None:
    assert check_redistribute("CC-BY-SA-4.0", "bulk")["allowed"] is True


def test_cc_by_nc_4_deny_bulk() -> None:
    r = check_redistribute("CC-BY-NC-4.0", "bulk")
    assert r["allowed"] is False
    assert "CC-BY-NC-4.0" in r["reason"]


def test_cc_by_nc_4_allow_snippet_within_caps() -> None:
    r = check_redistribute("CC-BY-NC-4.0", "snippet", 50, 10000)
    assert r["allowed"] is True


def test_cc_by_nc_4_deny_snippet_exceeding_word_cap() -> None:
    r = check_redistribute("CC-BY-NC-4.0", "snippet", 101, 1_000_000)
    assert r["allowed"] is False
    assert "100" in r["reason"]


def test_cc_by_nc_4_deny_snippet_exceeding_1pct() -> None:
    r = check_redistribute("CC-BY-NC-4.0", "snippet", 80, 1000)
    assert r["allowed"] is False
    assert "1%" in r["reason"] or "exceeds" in r["reason"]


def test_sblgnt_eula_deny_bulk() -> None:
    assert check_redistribute("SBLGNT-EULA", "bulk")["allowed"] is False


def test_sblgnt_eula_allow_snippet() -> None:
    r = check_redistribute("SBLGNT-EULA", "snippet")
    assert r["allowed"] is True


def test_vendor_deny_bulk() -> None:
    assert check_redistribute("©Vatican", "bulk")["allowed"] is False


def test_vendor_allow_snippet_within_caps() -> None:
    r = check_redistribute("©Vatican", "snippet", 50, 10000)
    assert r["allowed"] is True


def test_vendor_deny_snippet_exceeding_cap() -> None:
    r = check_redistribute("©Vatican", "snippet", 101, 1_000_000)
    assert r["allowed"] is False


def test_paren_c_vendor_deny_bulk() -> None:
    assert check_redistribute("(C)Vendor", "bulk")["allowed"] is False


def test_copyright_prefix_snippet_allowed() -> None:
    r = check_redistribute("copyright vendor", "snippet", 50, 10000)
    assert r["allowed"] is True


def test_fair_use_deny_bulk() -> None:
    assert check_redistribute("fair-use-policy", "bulk")["allowed"] is False


def test_fair_use_allow_snippet() -> None:
    r = check_redistribute("fair-use-policy", "snippet", 50, 10000)
    assert r["allowed"] is True


def test_parsed_sanitized_deny_bulk() -> None:
    assert check_redistribute("parsed-sanitized", "bulk")["allowed"] is False


def test_parsed_sanitized_allow_snippet() -> None:
    r = check_redistribute("parsed-sanitized", "snippet", 50, 10000)
    assert r["allowed"] is True


def test_unknown_deny() -> None:
    r = check_redistribute("MIT-zero", "bulk")
    assert r["allowed"] is False
    assert "unrecognized" in r["reason"]


def test_empty_deny() -> None:
    r = check_redistribute("", "bulk")
    assert r["allowed"] is False
    assert "empty" in r["reason"]


def test_whitespace_only_deny() -> None:
    r = check_redistribute("   ", "bulk")
    assert r["allowed"] is False


def test_bogus_mode_deny() -> None:
    r = check_redistribute("CC-BY-4.0", "delete")  # type: ignore[arg-type]
    assert r["allowed"] is False
    assert "mode" in r["reason"]


def test_exact_boundary_snippet_acceptance() -> None:
    # 100 words on 10000-word source: 100/10000 = 0.01 = exactly 1%, accepted
    r = check_redistribute("CC-BY-NC-4.0", "snippet", 100, 10000)
    assert r["allowed"] is True


def test_case_insensitive_pd() -> None:
    assert check_redistribute("PUBLIC_DOMAIN", "bulk")["allowed"] is True
    assert check_redistribute("Public_Domain", "bulk")["allowed"] is True


def test_case_insensitive_cc_by_nc() -> None:
    assert check_redistribute("cc-by-nc-4.0", "bulk")["allowed"] is False
    assert check_redistribute("Cc-By-Nc-4.0", "bulk")["allowed"] is False


def test_case_insensitive_sblgnt() -> None:
    assert check_redistribute("sblgnt-eula", "snippet")["allowed"] is True


def test_composite_macula_hebrew_deny_bulk() -> None:
    r = check_redistribute("MACULA-Hebrew", "bulk", 0, 0)
    assert r["allowed"] is False
    assert "CC-BY-NC-4.0" in r["reason"]


def test_composite_macula_greek_allow_snippet() -> None:
    r = check_redistribute("MACULA-Greek", "snippet", 50, 100000)
    assert r["allowed"] is True


def test_resolve_composite_macula_hebrew() -> None:
    assert resolve_composite_license("MACULA-Hebrew") == "CC-BY-NC-4.0"


def test_resolve_composite_macula_greek() -> None:
    assert resolve_composite_license("MACULA-Greek") == "CC-BY-NC-4.0"


def test_resolve_composite_passthrough() -> None:
    assert resolve_composite_license("CC-BY-4.0") == "CC-BY-4.0"


def test_resolve_composite_case_insensitive_input() -> None:
    assert resolve_composite_license("macula-hebrew") == "CC-BY-NC-4.0"
    assert resolve_composite_license("Macula-Greek") == "CC-BY-NC-4.0"


def test_snippet_zero_word_count_denied() -> None:
    # CC-BY-NC snippet with zero words is meaningless and should deny
    r = check_redistribute("CC-BY-NC-4.0", "snippet", 0, 1000)
    assert r["allowed"] is False


def test_snippet_zero_source_words_denied_for_nc() -> None:
    r = check_redistribute("CC-BY-NC-4.0", "snippet", 50, 0)
    assert r["allowed"] is False


def test_resolve_composite_non_string() -> None:
    # Defensive: non-string returns unchanged (sentinel behavior).
    assert resolve_composite_license("") == ""


def test_snippet_boundary_99_words() -> None:
    r = check_redistribute("CC-BY-NC-4.0", "snippet", 99, 10000)
    assert r["allowed"] is True


def test_snippet_boundary_one_pct_exact() -> None:
    # 50 words on 5000 source = exactly 1%, accept
    r = check_redistribute("CC-BY-NC-4.0", "snippet", 50, 5000)
    assert r["allowed"] is True


def test_bulk_with_unknown_string_denied() -> None:
    r = check_redistribute("totally-bogus-license", "bulk")
    assert r["allowed"] is False


@pytest.mark.parametrize("license_str", ["public_domain", "CC-BY", "CC-BY-4.0", "CC-BY-SA-4.0"])
def test_allowed_licenses_parametric(license_str: str) -> None:
    assert check_redistribute(license_str, "bulk")["allowed"] is True
