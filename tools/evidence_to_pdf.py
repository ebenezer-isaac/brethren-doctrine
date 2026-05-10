"""Render an A4 PDF report from an evidence/<id>.json answer file.

Usage:
    python tools/evidence_to_pdf.py evidence/<id>.json
    python tools/evidence_to_pdf.py                           # every evidence/*.json
    python tools/evidence_to_pdf.py FILE --output-dir reports

Output: <stem>.pdf next to the input JSON (or under --output-dir).

Schema source of truth: docs/ANSWER_SCHEMA.md. Evidence sections rendered:
question statement (from questions.json) → answer summary → rationale →
position-thresholds table → notes → stem audit → hermeneutics block →
scripture (with genre + figures) → concordance lemmas traversed →
counter-witness → web → flags. Greek/Hebrew render via Arial (Windows) or
DejaVuSans (Linux/macOS); falls back to Helvetica.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
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

ATTITUDE_FIELDS = (
    ("would_die_for", "Would die for if challenged"),
    ("cult_marker_if_denied", "Cult marker if denied"),
    ("would_visit_if_otherwise", "Would visit if otherwise"),
    ("would_participate_if_otherwise", "Would participate if otherwise"),
    ("would_serve_if_otherwise", "Would serve if otherwise"),
    ("would_be_member_if_otherwise", "Would be member if otherwise"),
    ("would_let_children_be_taught_otherwise", "Would let children be taught otherwise"),
    ("would_marry_if_held_otherwise", "Would marry if held otherwise"),
    ("would_publicly_correct_if_otherwise", "Would publicly correct if otherwise"),
)

SUPPORTS_COLOR = {
    "for": "#1a7f37",
    "against": "#b42318",
    "complicates": "#b54708",
    "neutral": "#475467",
}
STANCE_COLOR = {
    "affirms": "#1a7f37",
    "denies": "#b42318",
    "complicates": "#b54708",
}


def register_unicode_font() -> tuple[str, str]:
    candidates = [
        ("Arial", "Arial-Bold", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        (
            "DejaVuSans", "DejaVuSans-Bold",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        (
            "DejaVuSans", "DejaVuSans-Bold",
            "/Library/Fonts/DejaVuSans.ttf",
            "/Library/Fonts/DejaVuSans-Bold.ttf",
        ),
    ]
    for reg_name, bold_name, reg_path, bold_path in candidates:
        if not Path(reg_path).exists():
            continue
        pdfmetrics.registerFont(TTFont(reg_name, reg_path))
        if Path(bold_path).exists():
            pdfmetrics.registerFont(TTFont(bold_name, bold_path))
            return reg_name, bold_name
        return reg_name, reg_name
    print(
        "warning: no Unicode TTF found; Greek/Hebrew glyphs will render as boxes.",
        file=sys.stderr,
    )
    return "Helvetica", "Helvetica-Bold"


def esc(s: object) -> str:
    return html.escape("" if s is None else str(s), quote=False)


def yes_no(v: object) -> str:
    if v is True:
        return "Yes"
    if v is False:
        return "No"
    return "—"


def load_questions_index() -> dict[str, dict]:
    if not QUESTIONS_FILE.exists():
        return {}
    raw = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    items = raw.get("questions") if isinstance(raw, dict) else raw
    return {q["id"]: q for q in (items or []) if isinstance(q, dict) and "id" in q}


def build_styles(regular: str, bold: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]
    body = ParagraphStyle("Body", parent=base, fontName=regular, fontSize=10, leading=13.5, spaceAfter=6)
    return {
        "title": ParagraphStyle("Title", parent=body, fontName=bold, fontSize=18, leading=22, spaceAfter=4),
        "subtitle": ParagraphStyle("Subtitle", parent=body, fontName=regular, fontSize=10, leading=13,
                                   textColor=colors.grey, spaceAfter=14),
        "h2": ParagraphStyle("H2", parent=body, fontName=bold, fontSize=13, leading=16,
                             spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#1f2a44")),
        "h3": ParagraphStyle("H3", parent=body, fontName=bold, fontSize=11, leading=14, spaceAfter=3),
        "body": body,
        "small": ParagraphStyle("Small", parent=body, fontName=regular, fontSize=8.5, leading=11,
                                textColor=colors.HexColor("#444")),
        "quote": ParagraphStyle("Quote", parent=body, fontName=regular, fontSize=9.5, leading=12.5,
                                leftIndent=10, textColor=colors.HexColor("#222"), spaceAfter=4),
        "statement": ParagraphStyle("Statement", parent=body, fontName=regular, fontSize=11,
                                    leading=15, textColor=colors.HexColor("#0f172a"), spaceAfter=0),
        "code": ParagraphStyle("Code", parent=body, fontName=regular, fontSize=9, leading=11.5,
                               textColor=colors.HexColor("#475467"), spaceAfter=4),
    }


def metadata_line(question: dict | None, answer: dict, evidence: dict, styles: dict) -> Paragraph:
    bits: list[str] = []
    affirms = answer.get("affirms")
    if affirms is True:
        bits.append("<font color='#1a7f37'><b>Affirms</b></font>")
    elif affirms is False:
        bits.append("<font color='#b42318'><b>Denies</b></font>")
    else:
        bits.append("<font color='#b54708'><b>Open / Uncertain</b></font>")

    if question:
        crumbs = [esc(question[k]) for k in ("category", "subcategory") if question.get(k)]
        if crumbs:
            bits.append(" &rsaquo; ".join(crumbs))
        if question.get("kind"):
            bits.append(esc(question["kind"]))
        if question.get("tier"):
            bits.append(f"tier: <b>{esc(question['tier'])}</b>")
        if question.get("historical_consensus"):
            bits.append(esc(question["historical_consensus"]))
        if question.get("brethren_distinctive"):
            bits.append("Brethren distinctive")
    bits.append(f"confidence: <b>{esc(evidence.get('confidence', '—'))}</b>")
    return Paragraph(" &middot; ".join(bits), styles["subtitle"])


def statement_box(text: str, styles: dict) -> Table:
    inner = Paragraph(esc(text), styles["statement"])
    table = Table([[inner]], colWidths=[17 * cm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor("#1f2a44")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


def attitude_table(answer: dict, styles: dict) -> Table:
    rows = []
    for key, label in ATTITUDE_FIELDS:
        rows.append([
            Paragraph(esc(label), styles["body"]),
            Paragraph(f"<b>{yes_no(answer.get(key))}</b>", styles["body"]),
        ])
    table = Table(rows, colWidths=[12 * cm, 4.5 * cm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f5f5f7")]),
    ]))
    return table


def stem_audit_block(stem_audit: dict, styles: dict) -> KeepTogether | None:
    if not stem_audit:
        return None
    if not stem_audit.get("verdict_preloaded"):
        return KeepTogether([
            Paragraph("Stem audit", styles["h3"]),
            Paragraph("verdict-preloaded: <b>no</b>", styles["small"]),
            Spacer(1, 4),
        ])
    parts = [
        Paragraph("Stem audit", styles["h3"]),
        Paragraph(
            f"verdict-preloaded: <b><font color='#b54708'>yes</font></b>",
            styles["small"],
        ),
        Paragraph(f"<b>Neutralized form.</b> {esc(stem_audit.get('neutralized_form'))}", styles["body"]),
    ]
    if stem_audit.get("notes"):
        parts.append(Paragraph(f"<b>Notes.</b> {esc(stem_audit['notes'])}", styles["body"]),)
    parts.append(Spacer(1, 4))
    return KeepTogether(parts)


def hermeneutics_block(h: dict, styles: dict) -> KeepTogether | None:
    if not h:
        return None
    parts = [Paragraph("Hermeneutics", styles["h2"])]
    parts.append(Paragraph(
        f"<b>Primary method.</b> {esc(h.get('primary_method'))}",
        styles["body"],
    ))
    if h.get("frameworks_in_play"):
        parts.append(Paragraph(
            f"<b>Frameworks in play.</b> {esc(', '.join(h['frameworks_in_play']))}",
            styles["body"],
        ))
    flags = []
    if h.get("analogia_scripturae_invoked"):
        flags.append("analogia scripturae invoked")
    if h.get("progressive_revelation_factor"):
        flags.append("progressive revelation factor")
    if flags:
        parts.append(Paragraph(" &middot; ".join(esc(f) for f in flags), styles["small"]))
    if h.get("competing_lens_verdicts"):
        parts.append(Paragraph("Competing lens verdicts", styles["h3"]))
        for c in h["competing_lens_verdicts"]:
            parts.append(Paragraph(
                f"<b>{esc(c.get('lens'))}</b> &middot; "
                f"<font color='{STANCE_COLOR.get(c.get('verdict'), '#475467')}'>"
                f"{esc(c.get('verdict'))}</font>: {esc(c.get('note'))}",
                styles["body"],
            ))
    if h.get("notes"):
        parts.append(Paragraph(esc(h["notes"]), styles["body"]))
    parts.append(Spacer(1, 4))
    return KeepTogether(parts)


def scripture_block(item: dict, styles: dict) -> KeepTogether:
    color = SUPPORTS_COLOR.get(item.get("supports"), "#475467")
    figs = item.get("figures") or []
    figs_str = f" &middot; figures: {esc(', '.join(figs))}" if figs else ""
    parts = [
        Paragraph(
            f"<b>{esc(item.get('ref'))}</b> &middot; "
            f"<font color='{color}'>{esc(item.get('supports'))}</font> &middot; "
            f"genre: {esc(item.get('genre'))}{figs_str}",
            styles["h3"],
        ),
        Paragraph(f"<b>Key term.</b> {esc(item.get('key_term'))}", styles["body"]),
        Paragraph(f"<b>Force.</b> {esc(item.get('force'))}", styles["body"]),
        Spacer(1, 4),
    ]
    return KeepTogether(parts)


def counter_witness_block(item: dict, styles: dict) -> KeepTogether:
    color = STANCE_COLOR.get(item.get("stance"), "#475467")
    badge = "verified" if item.get("verified") else "unverified"
    badge_color = "#1a7f37" if item.get("verified") else "#b54708"
    parts = [
        Paragraph(
            f"<b>{esc(item.get('tradition'))}</b> &middot; "
            f"{esc(item.get('anchor'))} &middot; "
            f"<font color='{color}'>{esc(item.get('stance'))}</font> &middot; "
            f"<font color='{badge_color}'>{badge}</font>",
            styles["h3"],
        ),
        Paragraph(f"&ldquo;{esc(item.get('key_phrase'))}&rdquo;", styles["quote"]),
        Spacer(1, 4),
    ]
    return KeepTogether(parts)


def web_block(item: dict, styles: dict) -> KeepTogether:
    color = {"supports": "#1a7f37", "opposes": "#b42318",
             "complicates": "#b54708", "nuance": "#475467"}.get(item.get("stance"), "#475467")
    url = esc(item.get("url"))
    parts = [
        Paragraph(
            f"<font color='{color}'>{esc(item.get('stance'))}</font> &middot; "
            f"category: {esc(item.get('category'))} &middot; "
            f"<link href='{url}' color='#0969da'>{url}</link>",
            styles["small"],
        ),
        Paragraph(f"&ldquo;{esc(item.get('quote'))}&rdquo;", styles["quote"]),
        Spacer(1, 4),
    ]
    return KeepTogether(parts)


def build_story(data: dict, styles: dict, question: dict | None) -> list:
    answer = data.get("answer", {}) or {}
    evidence = data.get("evidence", {}) or {}
    qid = data.get("id") or answer.get("id") or "(unknown)"

    story: list = []
    story.append(Paragraph(esc(qid), styles["title"]))
    story.append(metadata_line(question, answer, evidence, styles))

    statement = (question or {}).get("statement")
    if statement:
        story.append(Paragraph("Statement under examination", styles["h3"]))
        story.append(statement_box(statement, styles))
        story.append(Spacer(1, 10))

    # Rationale (lexical verdict justification) appears FIRST so the reader sees
    # the verdict-deciding logic before the contextual lay paragraphs.
    if answer.get("rationale"):
        story.append(Paragraph("Rationale", styles["h2"]))
        story.append(Paragraph(esc(answer["rationale"]), styles["body"]))
        story.append(Spacer(1, 10))

    lay = evidence.get("lay_summary")
    if isinstance(lay, dict):
        reasoning = lay.get("reasoning")
        if reasoning:
            story.append(Paragraph("Reasoning", styles["h2"]))
            story.append(Paragraph(esc(reasoning), styles["body"]))
            story.append(Spacer(1, 10))
        denom = lay.get("denominational_landscape")
        if denom:
            story.append(Paragraph("Denominational landscape", styles["h2"]))
            story.append(Paragraph(esc(denom), styles["body"]))
            story.append(Spacer(1, 10))
    elif isinstance(lay, str) and lay:
        # Backward compatibility for older evidence files with flat lay_summary.
        story.append(Paragraph("Reasoning", styles["h2"]))
        story.append(Paragraph(esc(lay), styles["body"]))
        story.append(Spacer(1, 10))

    story.append(Paragraph("Position thresholds", styles["h2"]))
    story.append(attitude_table(answer, styles))

    if answer.get("notes"):
        story.append(Paragraph("Notes", styles["h2"]))
        story.append(Paragraph(esc(answer["notes"]), styles["body"]))

    sa = stem_audit_block(evidence.get("stem_audit", {}), styles)
    if sa:
        story.append(sa)

    h = hermeneutics_block(evidence.get("hermeneutics", {}), styles)
    if h:
        story.append(h)

    scripture = evidence.get("scripture") or []
    if scripture:
        story.append(Paragraph("Scripture (apparatus + interlinear)", styles["h2"]))
        for s in scripture:
            story.append(scripture_block(s, styles))

    lemmas = evidence.get("concordance_lemmas_traversed") or []
    story.append(Paragraph("Concordance lemmas traversed", styles["h2"]))
    if lemmas:
        story.append(Paragraph(", ".join(esc(l) for l in lemmas), styles["code"]))
    else:
        story.append(Paragraph(
            "<font color='#b42318'><b>EMPTY</b></font> — validation failure",
            styles["body"],
        ))
    cts = evidence.get("complicating_texts_searched")
    story.append(Paragraph(
        f"complicating texts searched: <b>{yes_no(cts)}</b>",
        styles["small"],
    ))

    counter = evidence.get("counter_witness") or []
    if counter:
        story.append(Paragraph("Counter-witness traditions", styles["h2"]))
        for c in counter:
            story.append(counter_witness_block(c, styles))
    else:
        story.append(Paragraph("Counter-witness traditions", styles["h2"]))
        story.append(Paragraph("(none recorded)", styles["small"]))

    web = evidence.get("web") or []
    if web:
        story.append(Paragraph("Web sources", styles["h2"]))
        for w in web:
            story.append(web_block(w, styles))

    flags = evidence.get("flags") or []
    if flags:
        story.append(Paragraph("Flags", styles["h2"]))
        for f in flags:
            story.append(Paragraph(f"&bull; {esc(f)}", styles["body"]))

    return story


def render_pdf(json_path: Path, output_path: Path, font_pair: tuple[str, str], question: dict | None) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    styles = build_styles(*font_pair)
    qid = data.get("id") or data.get("answer", {}).get("id") or json_path.stem

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_pair[0], 8)
        canvas.setFillColor(colors.HexColor("#888"))
        canvas.drawString(2 * cm, 1.2 * cm, qid)
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=qid, author="brethren-doctrine",
    )
    doc.build(build_story(data, styles, question), onFirstPage=on_page, onLaterPages=on_page)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("inputs", nargs="*", type=Path,
                        help="Evidence JSON file(s). Defaults to every evidence/*.json.")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Directory for the .pdf output. Defaults to alongside each input.")
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
        if question is None:
            print(
                f"warning: no entry for '{path.stem}' in {QUESTIONS_FILE.name}; "
                "rendering without statement",
                file=sys.stderr,
            )
        try:
            render_pdf(path, out, font_pair, question)
        except Exception as exc:  # noqa: BLE001
            print(f"failed: {path.name}: {exc}", file=sys.stderr)
            continue
        print(f"wrote {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
