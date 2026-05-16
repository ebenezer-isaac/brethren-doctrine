"""Tests for tools.evidence_to_pdf (v3.0)."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline2.evidence_schema import Evidence
from pipeline2.score_calc import compute_lexical_score
from tests.pipeline2._fixtures import minimal_evidence_dict
from tools.evidence_to_pdf import (
    _affirms_color,
    _affirms_label,
    build_story,
    build_styles,
    register_unicode_font,
    render_pdf,
)


def _materialize(tmp_path: Path) -> Path:
    e = Evidence.model_validate(minimal_evidence_dict())
    e_dict = e.model_dump(by_alias=True)
    e_dict["verdict"]["lexical_score"] = compute_lexical_score(e)
    path = tmp_path / "doc-trinity.json"
    path.write_text(json.dumps(e_dict, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def test_render_produces_non_empty_pdf(tmp_path: Path) -> None:
    src = _materialize(tmp_path)
    out = tmp_path / "doc-trinity.pdf"
    font_pair = register_unicode_font()
    render_pdf(src, out, font_pair, {"category": "Theology Proper"})
    assert out.exists()
    assert out.stat().st_size > 1024


def test_render_landscape_orientation(tmp_path: Path) -> None:
    src = _materialize(tmp_path)
    out = tmp_path / "doc-trinity.pdf"
    font_pair = register_unicode_font()
    render_pdf(src, out, font_pair, {"category": "Theology Proper"})
    header = out.read_bytes()[:1024]
    assert b"%PDF-" in header


def _collect_text(items: object) -> str:
    """Walk Paragraphs/Tables and concat their inner text for assertion."""
    from reportlab.platypus import KeepTogether, Paragraph, Table

    buf: list[str] = []
    if isinstance(items, list):
        for it in items:
            buf.append(_collect_text(it))
    elif isinstance(items, Paragraph):
        buf.append(getattr(items, "text", "") or "")
    elif isinstance(items, KeepTogether):
        buf.append(_collect_text(items._content))
    elif isinstance(items, Table):
        for row in items._cellvalues:
            buf.append(_collect_text(list(row)))
    return " ".join(b for b in buf if b)


def test_score_appears_in_story(tmp_path: Path) -> None:
    src = _materialize(tmp_path)
    data = json.loads(src.read_text(encoding="utf-8"))
    font_pair = register_unicode_font()
    styles = build_styles(*font_pair)
    story = build_story(data, styles, {"category": "Theology Proper"})
    rendered = _collect_text(story)
    score = data["verdict"]["lexical_score"]
    assert f"{score:.3f}" in rendered


def test_score_badge_includes_confidence_and_affirms_in_story(tmp_path: Path) -> None:
    src = _materialize(tmp_path)
    data = json.loads(src.read_text(encoding="utf-8"))
    font_pair = register_unicode_font()
    styles = build_styles(*font_pair)
    story = build_story(data, styles, {"category": "Theology Proper"})
    rendered = _collect_text(story)
    assert "AFFIRMS" in rendered
    assert "high" in rendered or "confidence" in rendered


def test_affirms_label_handles_all_states() -> None:
    assert _affirms_label(True) == "AFFIRMS"
    assert _affirms_label(False) == "DENIES"
    assert _affirms_label(None) == "INSUFFICIENT"
    assert _affirms_label("disputed") == "DISPUTED"


def test_affirms_color_handles_all_states() -> None:
    assert _affirms_color(True) == "#1a7f37"
    assert _affirms_color(False) == "#b42318"
    assert _affirms_color(None) == "#475467"
    assert _affirms_color("disputed") == "#b54708"
