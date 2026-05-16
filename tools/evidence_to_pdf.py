"""Render a v3.0 evidence/<id>.json file to a landscape A4 PDF.

Usage:
    python tools/evidence_to_pdf.py evidence/<id>.json
    python tools/evidence_to_pdf.py                           # every evidence/*.json
    python tools/evidence_to_pdf.py FILE --output-dir reports

Schema source of truth: docs/EVIDENCE_SCHEMA.md (v3.0). Sections rendered:
title (with score badge) -> question statement -> verdict block (score,
confidence, affirms, variant_robust, pan_canonical, rationale) -> lay summary
-> lexical evidence (anchor lemmas, scripture, cross refs, complicating texts,
concordance traversed) -> variants -> hermeneutics -> stem audit -> citations
with license -> license audit prominently displayed -> flags.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "evidence"
QUESTIONS_FILE = ROOT / "questions.json"

AFFIRMS_COLOR = {
    True: "#1a7f37",
    False: "#b42318",
    None: "#475467",
    "disputed": "#b54708",
}

SUPPORTS_COLOR = {
    "for": "#1a7f37",
    "complicates": "#b54708",
    "neutral": "#475467",
}


def register_unicode_font() -> tuple[str, str]:
    candidates = [
        (
            "Arial",
            "Arial-Bold",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ),
        (
            "DejaVuSans",
            "DejaVuSans-Bold",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
    ]
    for reg, bold, reg_path, bold_path in candidates:
        if Path(reg_path).exists():
            pdfmetrics.registerFont(TTFont(reg, reg_path))
            if Path(bold_path).exists():
                pdfmetrics.registerFont(TTFont(bold, bold_path))
                return reg, bold
            return reg, reg
    return "Helvetica", "Helvetica-Bold"


def esc(s: object) -> str:
    return html.escape("" if s is None else str(s), quote=False)


def _affirms_label(value: object) -> str:
    if value is True:
        return "AFFIRMS"
    if value is False:
        return "DENIES"
    if value is None:
        return "INSUFFICIENT"
    return str(value).upper()


def _affirms_color(value: object) -> str:
    if value is True:
        return AFFIRMS_COLOR[True]
    if value is False:
        return AFFIRMS_COLOR[False]
    if value is None:
        return AFFIRMS_COLOR[None]
    return AFFIRMS_COLOR.get("disputed", "#475467")


def load_questions_index() -> dict[str, dict[str, Any]]:
    if not QUESTIONS_FILE.exists():
        return {}
    raw = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    items = raw.get("questions") if isinstance(raw, dict) else raw
    return {q["id"]: q for q in (items or []) if isinstance(q, dict) and "id" in q}


def build_styles(regular: str, bold: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]
    body = ParagraphStyle(
        "Body", parent=base, fontName=regular, fontSize=10, leading=13.5, spaceAfter=6
    )
    return {
        "title": ParagraphStyle(
            "Title", parent=body, fontName=bold, fontSize=20, leading=24, spaceAfter=2
        ),
        "score": ParagraphStyle(
            "Score", parent=body, fontName=bold, fontSize=22, leading=26, spaceAfter=4
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=body,
            fontName=regular,
            fontSize=10,
            leading=13,
            textColor=colors.grey,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=body,
            fontName=bold,
            fontSize=13,
            leading=16,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor("#1f2a44"),
        ),
        "h3": ParagraphStyle(
            "H3", parent=body, fontName=bold, fontSize=11, leading=14, spaceAfter=3
        ),
        "body": body,
        "small": ParagraphStyle(
            "Small",
            parent=body,
            fontName=regular,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#444"),
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=body,
            fontName=regular,
            fontSize=9.5,
            leading=12.5,
            leftIndent=10,
            textColor=colors.HexColor("#222"),
            spaceAfter=4,
        ),
        "statement": ParagraphStyle(
            "Statement",
            parent=body,
            fontName=regular,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=0,
        ),
    }


def _score_badge(evidence: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    verdict = evidence.get("verdict", {})
    score = verdict.get("lexical_score")
    score_str = f"{score:.3f}" if isinstance(score, (int, float)) else "N/A"
    color = _affirms_color(verdict.get("affirms"))
    inner = Paragraph(
        f"<font color='{color}'><b>{esc(_affirms_label(verdict.get('affirms')))}</b></font> "
        f"&middot; score <b>{score_str}</b> "
        f"&middot; confidence <b>{esc(verdict.get('confidence', 'N/A'))}</b>",
        styles["score"],
    )
    return Table(
        [[inner]],
        colWidths=[24 * cm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LINEBEFORE", (0, 0), (0, -1), 4, colors.HexColor(color)),
            ]
        ),
    )


def _statement_box(text: str, styles: dict[str, ParagraphStyle]) -> Table:
    inner = Paragraph(esc(text), styles["statement"])
    return Table(
        [[inner]],
        colWidths=[24 * cm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor("#1f2a44")),
            ]
        ),
    )


def _verdict_block(verdict: dict[str, Any], styles: dict[str, ParagraphStyle]) -> KeepTogether:
    bits: list[Any] = [Paragraph("Verdict", styles["h2"])]
    bits.append(
        Paragraph(
            f"<b>variant_robust.</b> {verdict.get('variant_robust')} "
            f"&middot; <b>pan_canonical.</b> {verdict.get('pan_canonical')}",
            styles["body"],
        )
    )
    bits.append(Paragraph(f"<b>Rationale.</b> {esc(verdict.get('rationale'))}", styles["body"]))
    return KeepTogether(bits)


def _lay_summary_block(text: str, styles: dict[str, ParagraphStyle]) -> KeepTogether:
    return KeepTogether(
        [Paragraph("Lay summary", styles["h2"]), Paragraph(esc(text), styles["body"])]
    )


def _anchor_lemmas_block(
    lemmas: list[dict[str, Any]], styles: dict[str, ParagraphStyle]
) -> KeepTogether:
    bits: list[Any] = [Paragraph("Anchor lemmas", styles["h2"])]
    if not lemmas:
        bits.append(Paragraph("(none)", styles["small"]))
        return KeepTogether(bits)
    rows = [["Strong", "Lemma", "Translit", "Occurrences"]]
    for al in lemmas:
        rows.append(
            [
                esc(al.get("strong")),
                esc(al.get("lemma")),
                esc(al.get("transliteration")),
                str(al.get("occurrences_in_canon", "")),
            ]
        )
    table = Table(rows, colWidths=[3 * cm, 6 * cm, 6 * cm, 4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    bits.append(table)
    return KeepTogether(bits)


def _scripture_block(entries: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> list[Any]:
    if not entries:
        return [Paragraph("Scripture", styles["h2"]), Paragraph("(none)", styles["small"])]
    parts: list[Any] = [Paragraph("Scripture", styles["h2"])]
    for s in entries:
        color = SUPPORTS_COLOR.get(s.get("supports", "neutral"), "#475467")
        figs = ", ".join(s.get("figures") or [])
        figs_str = f" &middot; figures: {esc(figs)}" if figs else ""
        terms = ", ".join(
            f"{esc(t.get('strong'))} {esc(t.get('lemma'))}" for t in s.get("key_terms", [])
        )
        parts.append(
            KeepTogether(
                [
                    Paragraph(
                        f"<b>{esc(s.get('ref'))}</b> &middot; "
                        f"<font color='{color}'>{esc(s.get('supports'))}</font> &middot; "
                        f"genre: {esc(s.get('genre'))}{figs_str}",
                        styles["h3"],
                    ),
                    Paragraph(f"<b>Key terms.</b> {terms}", styles["body"]),
                    Paragraph(f"<b>Force.</b> {esc(s.get('force'))}", styles["body"]),
                    Spacer(1, 4),
                ]
            )
        )
    return parts


def _cross_refs_block(
    refs: list[dict[str, Any]], styles: dict[str, ParagraphStyle]
) -> KeepTogether:
    bits: list[Any] = [Paragraph("Cross references invoked", styles["h2"])]
    if not refs:
        bits.append(Paragraph("(none)", styles["small"]))
        return KeepTogether(bits)
    rows = [["From", "To", "Source", "Votes"]]
    for r in refs:
        rows.append(
            [
                esc(r.get("from")),
                esc(r.get("to")),
                esc(r.get("source")),
                str(r.get("votes", "")),
            ]
        )
    table = Table(rows, colWidths=[5 * cm, 5 * cm, 4 * cm, 3 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    bits.append(table)
    return KeepTogether(bits)


def _complicating_block(
    items: list[dict[str, Any]], styles: dict[str, ParagraphStyle]
) -> list[Any]:
    parts: list[Any] = [Paragraph("Complicating texts", styles["h2"])]
    if not items:
        parts.append(Paragraph("(none)", styles["small"]))
        return parts
    for c in items:
        addressed = c.get("addressed")
        badge = "addressed" if addressed else "unaddressed"
        color = "#1a7f37" if addressed else "#b42318"
        parts.append(
            KeepTogether(
                [
                    Paragraph(
                        f"<b>{esc(c.get('ref'))}</b> &middot; "
                        f"<font color='{color}'>{badge}</font>",
                        styles["h3"],
                    ),
                    Paragraph(esc(c.get("resolution")), styles["body"]),
                    Spacer(1, 4),
                ]
            )
        )
    return parts


def _concordance_block(traversed: list[str], styles: dict[str, ParagraphStyle]) -> KeepTogether:
    bits: list[Any] = [Paragraph("Concordance traversed", styles["h2"])]
    if traversed:
        bits.append(Paragraph(", ".join(esc(t) for t in traversed), styles["body"]))
    else:
        bits.append(Paragraph("(empty; concordance-thin flag expected)", styles["small"]))
    return KeepTogether(bits)


def _variants_block(v: dict[str, Any], styles: dict[str, ParagraphStyle]) -> KeepTogether:
    bits: list[Any] = [Paragraph("Variants", styles["h2"])]
    bits.append(
        Paragraph(
            f"<b>verdict_variant_sensitive.</b> {v.get('verdict_variant_sensitive')} "
            f"&middot; <b>ecm_status.</b> {esc(v.get('ecm_status'))}",
            styles["body"],
        )
    )
    units = v.get("variant_units_examined") or []
    if units:
        for u in units:
            bits.append(
                Paragraph(
                    f"<b>{esc(u.get('variant_id'))}</b> at {esc(u.get('ref'))}: "
                    f"impact {esc(u.get('verdict_impact'))}. {esc(u.get('note'))}",
                    styles["body"],
                )
            )
    if v.get("note"):
        bits.append(Paragraph(esc(v["note"]), styles["small"]))
    return KeepTogether(bits)


def _hermeneutics_block(h: dict[str, Any], styles: dict[str, ParagraphStyle]) -> KeepTogether:
    bits: list[Any] = [Paragraph("Hermeneutics", styles["h2"])]
    bits.append(
        Paragraph(
            f"<b>Primary method.</b> {esc(h.get('primary_method'))}",
            styles["body"],
        )
    )
    if h.get("frameworks_in_play"):
        bits.append(
            Paragraph(
                f"<b>Frameworks in play.</b> {esc(', '.join(h['frameworks_in_play']))}",
                styles["body"],
            )
        )
    flags = []
    if h.get("analogia_scripturae"):
        flags.append("analogia scripturae invoked")
    if h.get("progressive_revelation"):
        flags.append("progressive revelation factor")
    if flags:
        bits.append(Paragraph(" &middot; ".join(esc(f) for f in flags), styles["small"]))
    for clv in h.get("competing_lens_verdicts") or []:
        bits.append(
            Paragraph(
                f"<b>{esc(clv.get('framework'))}</b>: {esc(clv.get('verdict'))} "
                f"&middot; {esc(clv.get('rationale'))}",
                styles["body"],
            )
        )
    if h.get("notes"):
        bits.append(Paragraph(esc(h["notes"]), styles["body"]))
    return KeepTogether(bits)


def _stem_audit_block(s: dict[str, Any], styles: dict[str, ParagraphStyle]) -> KeepTogether:
    bits: list[Any] = [Paragraph("Stem audit", styles["h2"])]
    if s.get("verdict_preloaded"):
        bits.append(
            Paragraph(
                "<b><font color='#b54708'>verdict-preloaded: yes</font></b>",
                styles["body"],
            )
        )
        if s.get("neutralized_form"):
            bits.append(
                Paragraph(f"<b>Neutralized form.</b> {esc(s['neutralized_form'])}", styles["body"])
            )
    else:
        bits.append(Paragraph("verdict-preloaded: no", styles["small"]))
    if s.get("notes"):
        bits.append(Paragraph(esc(s["notes"]), styles["small"]))
    return KeepTogether(bits)


def _citations_block(
    cites: list[dict[str, Any]], styles: dict[str, ParagraphStyle]
) -> KeepTogether:
    bits: list[Any] = [Paragraph("Citations", styles["h2"])]
    if not cites:
        bits.append(Paragraph("(none)", styles["small"]))
        return KeepTogether(bits)
    rows = [["Type", "Source", "License", "Redistribute", "Ref"]]
    for c in cites:
        rows.append(
            [
                esc(c.get("type")),
                esc(c.get("source")),
                esc(c.get("license")),
                "yes" if c.get("redistribute") else "no",
                esc(c.get("ref")),
            ]
        )
    table = Table(rows, colWidths=[3 * cm, 6 * cm, 4 * cm, 3 * cm, 6 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ]
        )
    )
    bits.append(table)
    return KeepTogether(bits)


def _license_audit_block(la: dict[str, Any], styles: dict[str, ParagraphStyle]) -> KeepTogether:
    safe = la.get("evidence_safe_to_publish")
    color = "#1a7f37" if safe else "#b42318"
    label = "SAFE TO PUBLISH" if safe else "NOT SAFE TO PUBLISH"
    bits: list[Any] = [
        Paragraph("License audit", styles["h2"]),
        Paragraph(
            f"<font color='{color}'><b>{label}</b></font>",
            styles["body"],
        ),
    ]
    if la.get("non_redistributable_reason"):
        bits.append(
            Paragraph(f"<b>Reason.</b> {esc(la['non_redistributable_reason'])}", styles["body"])
        )
    rows = [["Source", "License", "Redistribute"]]
    for src in la.get("sources_used") or []:
        rows.append(
            [
                esc(src.get("source")),
                esc(src.get("license")),
                "yes" if src.get("redistribute") else "no",
            ]
        )
    if len(rows) > 1:
        table = Table(rows, colWidths=[8 * cm, 5 * cm, 4 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        bits.append(table)
    return KeepTogether(bits)


def _flags_block(flags: list[str], styles: dict[str, ParagraphStyle]) -> KeepTogether:
    bits: list[Any] = [Paragraph("Flags", styles["h2"])]
    if not flags:
        bits.append(Paragraph("(none)", styles["small"]))
    else:
        bits.append(Paragraph(" &middot; ".join(f"<b>{esc(f)}</b>" for f in flags), styles["body"]))
    return KeepTogether(bits)


def build_story(
    data: dict[str, Any],
    styles: dict[str, ParagraphStyle],
    question: dict[str, Any] | None,
) -> list[Any]:
    qid = data.get("id") or data.get("question_id") or "(unknown)"
    story: list[Any] = [Paragraph(esc(qid), styles["title"])]

    crumbs: list[str] = []
    if question:
        if question.get("category"):
            crumbs.append(esc(question["category"]))
        if question.get("subcategory"):
            crumbs.append(esc(question["subcategory"]))
        if question.get("kind"):
            crumbs.append(esc(question["kind"]))
        if question.get("historical_consensus"):
            crumbs.append(esc(question["historical_consensus"]))
        if question.get("brethren_distinctive"):
            crumbs.append("brethren distinctive")
    if crumbs:
        story.append(Paragraph(" &middot; ".join(crumbs), styles["subtitle"]))

    story.append(_score_badge(data, styles))
    story.append(Spacer(1, 8))

    if question and question.get("statement"):
        story.append(Paragraph("Statement under examination", styles["h3"]))
        story.append(_statement_box(question["statement"], styles))
        story.append(Spacer(1, 8))

    verdict = data.get("verdict", {})
    if verdict:
        story.append(_verdict_block(verdict, styles))

    if data.get("lay_summary"):
        story.append(_lay_summary_block(data["lay_summary"], styles))

    lex = data.get("lexical_evidence", {})
    if lex:
        story.append(_anchor_lemmas_block(lex.get("anchor_lemmas") or [], styles))
        story.extend(_scripture_block(lex.get("scripture") or [], styles))
        story.append(_cross_refs_block(lex.get("cross_refs_invoked") or [], styles))
        story.extend(_complicating_block(lex.get("complicating_texts") or [], styles))
        story.append(_concordance_block(lex.get("concordance_traversed") or [], styles))

    if data.get("variants"):
        story.append(_variants_block(data["variants"], styles))

    if data.get("hermeneutics"):
        story.append(_hermeneutics_block(data["hermeneutics"], styles))

    if data.get("stem_audit"):
        story.append(_stem_audit_block(data["stem_audit"], styles))

    story.append(_citations_block(data.get("citations") or [], styles))

    if data.get("license_audit"):
        story.append(_license_audit_block(data["license_audit"], styles))

    story.append(_flags_block(data.get("flags") or [], styles))
    return story


def render_pdf(
    json_path: Path,
    output_path: Path,
    font_pair: tuple[str, str],
    question: dict[str, Any] | None,
) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    styles = build_styles(*font_pair)
    qid = data.get("id") or data.get("question_id") or json_path.stem
    pagesize = landscape(A4)

    def on_page(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont(font_pair[0], 8)
        canvas.setFillColor(colors.HexColor("#888"))
        canvas.drawString(2 * cm, 1.2 * cm, qid)
        canvas.drawRightString(pagesize[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=pagesize,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=qid,
        author="brethren-doctrine",
    )
    doc.build(build_story(data, styles, question), onFirstPage=on_page, onLaterPages=on_page)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="Evidence JSON file(s). Defaults to every evidence/*.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the .pdf output. Defaults to alongside each input.",
    )
    args = parser.parse_args()

    inputs = list(args.inputs) if args.inputs else sorted(EVIDENCE_DIR.glob("*.json"))
    if not inputs:
        print(f"no JSON files found under {EVIDENCE_DIR}", file=sys.stderr)
        return 1

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    font_pair = register_unicode_font()
    questions = load_questions_index()

    for path in inputs:
        if not path.exists():
            print(f"skip: {path} does not exist", file=sys.stderr)
            continue
        out_dir = args.output_dir or path.parent
        out = out_dir / f"{path.stem}.pdf"
        question = questions.get(path.stem)
        try:
            render_pdf(path, out, font_pair, question)
        except Exception as exc:  # noqa: BLE001
            print(f"failed: {path.name}: {exc}", file=sys.stderr)
            continue
        print(f"wrote {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
