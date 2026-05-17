"""Contract tests for docs/SCHEMA_DECISIONS.md (Architect output, Phase A.1).

The tests assert min-content gates from RESEED_PLAN.md A.1. The test author was
blind to the file at authoring time; the file is read by pytest at runtime.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DECISIONS = REPO_ROOT / "docs" / "SCHEMA_DECISIONS.md"

FORBIDDEN_PHRASES = (
    "deferred", "defer to", "out of scope", "v1.5", "v2",
    "future", "TBD", "FIXME", "TODO", "XXX", "eventually", "later",
)

PREDICATE_RE = re.compile(r"\$pred_(string|int|float|bool|list)")
DECISION_RE = re.compile(r"(?m)^### Decision ")
COMPARISON_OPS = ("<>", ">=", "<=", ">", "<", "=", "IS NOT NULL", "IS NULL")


@pytest.fixture(scope="module")
def text() -> str:
    """Load the SCHEMA_DECISIONS.md file at test runtime."""
    return SCHEMA_DECISIONS.read_text(encoding="utf-8")


def _decision_chunks(text: str) -> list[tuple[str, str]]:
    """Split text into (title, body) tuples by Decision headers."""
    starts = [m.start() for m in DECISION_RE.finditer(text)]
    if not starts:
        return []
    starts.append(len(text))
    chunks: list[tuple[str, str]] = []
    for i in range(len(starts) - 1):
        body = text[starts[i]:starts[i + 1]]
        title_line = body.split('\n')[0].strip()
        chunks.append((title_line, body))
    return chunks


def test_file_exists(text: str) -> None:
    """The file exists and is non-empty."""
    assert SCHEMA_DECISIONS.exists(), f"missing {SCHEMA_DECISIONS}"
    assert len(text) > 0, "file is empty"


def test_decision_count_at_least_15(text: str) -> None:
    """At least 15 '### Decision ' headings present."""
    n = len(DECISION_RE.findall(text))
    assert n >= 15, f"only {n} '### Decision ' headings; need >= 15"


def test_no_forbidden_phrases(text: str) -> None:
    """No case-insensitive forbidden phrases anywhere in the file."""
    violations: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        line_lower = line.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in line_lower:
                violations.append(f"Line {i}: [{phrase}] {line.rstrip()}")
    assert not violations, f"Found {len(violations)} forbidden phrase(s):\n" + "\n".join(violations[:10])


def test_no_em_or_en_dashes(text: str) -> None:
    """No em-dashes (—) or en-dashes (–) anywhere in the file."""
    violations: list[str] = []
    for offset, char in enumerate(text):
        if char == "—":
            start = max(0, offset - 15)
            end = min(len(text), offset + 15)
            context = text[start:end].replace("\n", " ")
            violations.append(f"Offset {offset} (em-dash): ...{context}...")
        elif char == "–":
            start = max(0, offset - 15)
            end = min(len(text), offset + 15)
            context = text[start:end].replace("\n", " ")
            violations.append(f"Offset {offset} (en-dash): ...{context}...")
    assert not violations, f"Found {len(violations)} dash character(s):\n" + "\n".join(violations[:10])


def test_every_decision_has_four_subsections(text: str) -> None:
    """Each decision chunk contains all four required subsection headings."""
    chunks = _decision_chunks(text)
    required_subsections = {
        "#### Rule",
        "#### Cypher acceptance query",
        "#### Edge cases handled",
        "#### Per-field predicate type",
    }
    missing_by_decision: list[str] = []
    for title, body in chunks:
        found = set()
        for subsection in required_subsections:
            if subsection in body:
                found.add(subsection)
        missing = required_subsections - found
        if missing:
            missing_by_decision.append(f"{title}: missing {missing}")
    assert not missing_by_decision, f"Found {len(missing_by_decision)} decision(s) with missing subsections:\n" + "\n".join(missing_by_decision[:5])


def test_every_rule_has_40_words_and_2_sentences(text: str) -> None:
    """Each decision's Rule section has >= 40 words and >= 2 sentences."""
    chunks = _decision_chunks(text)
    failures: list[str] = []
    for title, body in chunks:
        match = re.search(r"#### Rule\n(.*?)(?=####|\Z)", body, re.DOTALL)
        if not match:
            failures.append(f"{title}: Rule section not found")
            continue
        rule_text = match.group(1).strip()
        word_count = len(rule_text.split())
        sentence_count = len(re.findall(r"[.!?]+", rule_text))
        if word_count < 40 or sentence_count < 2:
            failures.append(
                f"{title}: {word_count} words (need 40+), {sentence_count} sentences (need 2+)"
            )
    assert not failures, f"Found {len(failures)} decision(s) with insufficient Rule content:\n" + "\n".join(failures[:5])


def test_every_cypher_block_well_formed(text: str) -> None:
    """Each decision has a well-formed Cypher block with MATCH and comparison operators."""
    chunks = _decision_chunks(text)
    failures: list[str] = []
    for title, body in chunks:
        match = re.search(r"#### Cypher acceptance query\n(.*?)(?=####|\Z)", body, re.DOTALL)
        if not match:
            failures.append(f"{title}: Cypher section not found")
            continue
        cypher_section = match.group(1)
        cypher_block_match = re.search(r"```cypher\n(.*?)\n```", cypher_section, re.DOTALL)
        if not cypher_block_match:
            failures.append(f"{title}: no ```cypher block found")
            continue
        cypher_code = cypher_block_match.group(1)
        non_blank_lines = [line for line in cypher_code.split('\n') if line.strip()]
        if len(non_blank_lines) < 3:
            failures.append(f"{title}: cypher block has only {len(non_blank_lines)} non-blank lines (need 3+)")
            continue
        if not re.search(r"MATCH", cypher_code, re.IGNORECASE):
            failures.append(f"{title}: cypher block missing MATCH")
            continue
        has_comparison = any(op in cypher_code for op in COMPARISON_OPS)
        if not has_comparison:
            failures.append(f"{title}: cypher block missing comparison operator")
    assert not failures, f"Found {len(failures)} decision(s) with malformed Cypher:\n" + "\n".join(failures[:5])


def test_every_edge_cases_has_3_long_bullets(text: str) -> None:
    """Each decision's Edge cases section has >= 3 bullets each with >= 15 words."""
    chunks = _decision_chunks(text)
    failures: list[str] = []
    for title, body in chunks:
        match = re.search(r"#### Edge cases handled\n(.*?)(?=####|\Z)", body, re.DOTALL)
        if not match:
            failures.append(f"{title}: Edge cases section not found")
            continue
        edge_section = match.group(1)
        bullets = [line.lstrip() for line in edge_section.split('\n') if line.lstrip().startswith('- ')]
        if len(bullets) < 3:
            failures.append(f"{title}: only {len(bullets)} bullets (need 3+)")
            continue
        for i, bullet in enumerate(bullets):
            words = bullet.split()
            if len(words) < 15:
                failures.append(f"{title}: bullet {i} has {len(words)} words (need 15+)")
                break
    assert not failures, f"Found {len(failures)} decision(s) with insufficient edge case bullets:\n" + "\n".join(failures[:5])


def test_every_predicate_table_cites_predicate_function(text: str) -> None:
    """Each decision's Per-field predicate type section cites at least one $pred_* function."""
    chunks = _decision_chunks(text)
    failures: list[str] = []
    for title, body in chunks:
        match = re.search(r"#### Per-field predicate type\n(.*?)(?=####|\Z)", body, re.DOTALL)
        if not match:
            failures.append(f"{title}: Per-field predicate type section not found")
            continue
        predicate_section = match.group(1)
        if not PREDICATE_RE.search(predicate_section):
            failures.append(f"{title}: no $pred_* citation found")
    assert not failures, f"Found {len(failures)} decision(s) without predicate citations:\n" + "\n".join(failures[:5])


def test_overall_doc_has_h1(text: str) -> None:
    """First non-blank line is H1 (# ) and document has at least one H2 before first Decision."""
    lines = [line for line in text.split('\n') if line.strip()]
    assert lines, "document is empty or all blank"
    assert lines[0].startswith('# '), f"first non-blank line is not H1: {lines[0][:50]}"
    first_decision_idx = next((i for i, line in enumerate(lines) if line.startswith('### Decision ')), None)
    assert first_decision_idx is not None, "no decisions found"
    section_lines = lines[1:first_decision_idx]
    has_h2 = any(line.startswith('## ') for line in section_lines)
    assert has_h2, "no H2 sections found before first Decision"
