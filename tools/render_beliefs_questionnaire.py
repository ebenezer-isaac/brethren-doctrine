"""Render personal-beliefs.json into a printable tick-box questionnaire PDF.

The output is a self-evaluation form: each entry is presented as a numbered
block with the doctrinal/practice STATEMENT and a tick-box grid asking the
respondent for their own:
  - position on the statement (affirm / deny / open / uncertain)
  - martyrdom value (0-10 scale)
  - relationship-ladder responses if a church teaches the opposite
    (visit / participate / serve in ministry / become a member)
  - other action thresholds (marry across / teach to children /
    correct if encountered / break fellowship / denial = cult-grade)

Default scope is tier=essential (the most important entries) so the
questionnaire is fillable in one sitting. Use --tiers to widen.

Run from project root:
    uv add reportlab typer
    uv run python tools/render_beliefs_questionnaire.py
    uv run python tools/render_beliefs_questionnaire.py --tiers essential,convictional
    uv run python tools/render_beliefs_questionnaire.py --all-tiers
    uv run python tools/render_beliefs_questionnaire.py -o my-questionnaire.pdf
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.pdfbase.pdfmetrics import stringWidth
except ImportError:
    sys.stderr.write("reportlab not installed. Run: uv add reportlab\n")
    raise SystemExit(2)

import typer

# -- Tier styling -----------------------------------------------------------

TIER_BG = {
    "essential":    colors.HexColor("#8B0000"),
    "convictional": colors.HexColor("#C0392B"),
    "important":    colors.HexColor("#D68910"),
    "preference":   colors.HexColor("#3498DB"),
    "adiaphora":    colors.HexColor("#7F8C8D"),
}
TIER_FG = {tier: colors.white for tier in TIER_BG}
TIER_ORDER = ["essential", "convictional", "important", "preference", "adiaphora"]

# Plain-ASCII tick-box markers (Helvetica WinAnsi has no ☐ glyph).
BOX = "[ ]"
BOXY = f"{BOX} Y"
BOXN = f"{BOX} N"
LINE = "_______"

# -- Styles -----------------------------------------------------------------

_styles = getSampleStyleSheet()

S_TITLE = ParagraphStyle(
    "title", parent=_styles["Title"], fontSize=22, leading=26, spaceAfter=10
)
S_SUBTITLE = ParagraphStyle(
    "subtitle", parent=_styles["Normal"], fontSize=11, leading=14,
    textColor=colors.HexColor("#5D6D7E"), spaceAfter=6,
)
S_BODY = ParagraphStyle(
    "body", parent=_styles["Normal"], fontSize=10, leading=13, spaceAfter=4,
)
S_INSTR = ParagraphStyle(
    "instr", parent=_styles["Normal"], fontSize=9, leading=12, spaceAfter=3,
    leftIndent=10,
)
S_CATHEAD = ParagraphStyle(
    "cathead", parent=_styles["Heading2"], fontSize=12, leading=14,
    textColor=colors.white, backColor=colors.HexColor("#1F3A5F"),
    leftIndent=4, spaceBefore=10, spaceAfter=4,
)
S_QHEAD = ParagraphStyle(
    "qhead", parent=_styles["Normal"], fontSize=10, leading=13,
    textColor=colors.white, fontName="Helvetica-Bold",
)
S_STMT = ParagraphStyle(
    "stmt", parent=_styles["Normal"], fontSize=10, leading=13,
    fontName="Helvetica-Bold", spaceBefore=2, spaceAfter=2,
)
S_LABEL = ParagraphStyle(
    "label", parent=_styles["Normal"], fontSize=9, leading=12,
    fontName="Helvetica-Bold", spaceBefore=2, spaceAfter=1,
)
S_TICK = ParagraphStyle(
    "tick", parent=_styles["Normal"], fontSize=9, leading=12,
)
S_NOTE = ParagraphStyle(
    "note", parent=_styles["Italic"], fontSize=8, leading=10,
    textColor=colors.HexColor("#5D6D7E"), spaceAfter=2,
)


# -- Page header/footer -----------------------------------------------------

HEADER_TEXT = (
    "Position options:  Affirm  ·  Deny  ·  Open  ·  Uncertain        "
    "Tick boxes are answered as Y (yes) or N (no)"
)
FOOTER_TEXT = (
    "Relationship ladder (most committed at the right):  "
    "Visit  <  Participate in worship  <  Serve in ministry  <  Become a member"
)


def _draw_tier_swatches(canvas, x: float, y: float, height: float = 7) -> float:
    canvas.setFont("Helvetica-Bold", 5.5)
    cursor = x
    for tier in TIER_ORDER:
        label = tier.upper()
        text_w = stringWidth(label, "Helvetica-Bold", 5.5) + 6
        canvas.setFillColor(TIER_BG[tier])
        canvas.rect(cursor, y - 1, text_w, height, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.drawString(cursor + 3, y + 0.5, label)
        cursor += text_w + 2
    return cursor


def page_header_footer(canvas, doc):
    canvas.saveState()
    page_w, page_h = doc.pagesize
    margin = 15 * mm

    # ---- Header
    header_y = page_h - 8 * mm
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#34495E"))
    canvas.drawString(margin, header_y, HEADER_TEXT)

    canvas.setFont("Helvetica-Oblique", 7)
    canvas.setFillColor(colors.HexColor("#7F8C8D"))
    canvas.drawRightString(page_w - margin, header_y, f"Page {doc.page}")

    canvas.setStrokeColor(colors.HexColor("#D5DBDB"))
    canvas.setLineWidth(0.25)
    canvas.line(margin, header_y - 2, page_w - margin, header_y - 2)

    # ---- Footer: tier swatches at left, relationship ladder reminder at right
    footer_y = 7 * mm
    canvas.setFillColor(colors.HexColor("#34495E"))
    canvas.setFont("Helvetica", 6)
    canvas.drawString(margin, footer_y + 3, "Tier:")
    swatch_end_x = _draw_tier_swatches(canvas, margin + 16, footer_y, height=7)

    canvas.setFont("Helvetica", 6.5)
    canvas.drawRightString(page_w - margin, footer_y + 1, FOOTER_TEXT)

    canvas.setStrokeColor(colors.HexColor("#D5DBDB"))
    canvas.line(margin, footer_y + 10, page_w - margin, footer_y + 10)

    canvas.restoreState()


# -- Cover page -------------------------------------------------------------

def cover_page(doc: dict, tier_filter: list[str], total_questions: int) -> list:
    out: list = [
        Paragraph("Doctrinal Position Questionnaire", S_TITLE),
        Paragraph(
            "Self-evaluation against the Brethren-doctrine personal-beliefs taxonomy. "
            "Your responses help map where you stand on each doctrine and practice across "
            "multiple axes (importance, willingness to break fellowship, marry across, etc.).",
            S_SUBTITLE,
        ),
        Spacer(1, 12),
    ]

    # Respondent fields
    respondent = Table(
        [
            ["Name:", LINE * 5],
            ["Date:", LINE * 5],
            ["Church background:", LINE * 5],
            ["Years in current church:", LINE * 2 + "    Years in faith: " + LINE * 2],
            ["Tradition (if any):", LINE * 5],
        ],
        colWidths=[140, 360],
    )
    respondent.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F4F6F7")),
    ]))
    out += [respondent, Spacer(1, 14)]

    # Instructions
    out += [
        Paragraph("Instructions", S_LABEL),
        Paragraph(
            "1. Each numbered question presents a doctrinal or practice STATEMENT phrased "
            "as the orthodox / affirming position. Read it carefully.",
            S_INSTR,
        ),
        Paragraph(
            "2. Mark ONE box for your <b>Position</b>: <b>Affirm</b> = you hold this view; "
            "<b>Deny</b> = you reject it; <b>Open</b> = you can see it but are not committed; "
            "<b>Uncertain</b> = you do not know yet.",
            S_INSTR,
        ),
        Paragraph(
            "3. Fill in your <b>Martyrdom</b> score 0-10. 0 = indifferent. "
            "10 = you would lay down your life rather than deny this. Be honest, not aspirational.",
            S_INSTR,
        ),
        Paragraph(
            "4. For the action questions, &quot;the opposite&quot; means the position contrary "
            "to the statement. <b>Visit / Participate / Serve / Member</b> form an escalating "
            "ladder of involvement — a Y to Member usually implies Y to all the lower rungs, "
            "but answer each independently.",
            S_INSTR,
        ),
        Paragraph(
            "5. Take your time. Honesty over speed. Skip a question only if you genuinely "
            "have no view.",
            S_INSTR,
        ),
        Spacer(1, 10),
    ]

    # KPI legend
    out += [
        Paragraph("Question axes", S_LABEL),
        Paragraph("<b>Position</b> &mdash; your stance on the statement.", S_INSTR),
        Paragraph("<b>Martyrdom (0-10)</b> &mdash; how strongly you hold it.", S_INSTR),
        Paragraph(
            "<b>If church teaches otherwise &mdash; Visit?</b> Would you attend a service?",
            S_INSTR,
        ),
        Paragraph(
            "<b>Participate?</b> Take part in worship / communion / corporate prayer.",
            S_INSTR,
        ),
        Paragraph(
            "<b>Serve?</b> Volunteer, teach, lead a small group under that leadership.",
            S_INSTR,
        ),
        Paragraph(
            "<b>Member?</b> Formally identify yourself with that church under its eldership.",
            S_INSTR,
        ),
        Paragraph(
            "<b>Marry across?</b> Could you marry someone who holds the opposite view.",
            S_INSTR,
        ),
        Paragraph(
            "<b>Teach to children?</b> Would you actively teach this position to your kids.",
            S_INSTR,
        ),
        Paragraph(
            "<b>Correct?</b> Must you attempt correction if you encounter the opposite "
            "(versus letting it pass).",
            S_INSTR,
        ),
        Paragraph(
            "<b>Break fellowship?</b> Would you refuse ongoing close fellowship over this.",
            S_INSTR,
        ),
        Paragraph(
            "<b>Cult-grade?</b> Is denial of this doctrine cult-level error "
            "(rather than a regular disagreement).",
            S_INSTR,
        ),
        Spacer(1, 10),
    ]

    out += [
        Paragraph(
            f"<b>Scope:</b> {total_questions} question(s), tier filter: <b>{', '.join(tier_filter)}</b>. "
            f"Reference baseline owned by {doc.get('owner', 'the baseline owner')}.",
            S_BODY,
        ),
    ]
    return out


# -- Question block ---------------------------------------------------------

USABLE_W = 510  # portrait A4 minus 15mm margins each side


def question_block(e: dict, number: int) -> KeepTogether:
    tier = e["tier"]
    bg, fg = TIER_BG[tier], TIER_FG[tier]

    sub = e.get("subcategory") or ""
    cat_text = e["category"] + (f" › {sub}" if sub else "")

    # Header bar: number, id, category, tier
    header = Table(
        [[
            Paragraph(f"<b>#{number}</b>", S_QHEAD),
            Paragraph(f"<b>{e['id']}</b>", S_QHEAD),
            Paragraph(cat_text, S_QHEAD),
            Paragraph(f"<b>{tier.upper()}</b>", S_QHEAD),
        ]],
        colWidths=[40, 160, 230, 80],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("TEXTCOLOR", (0, 0), (-1, -1), fg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (3, 0), (3, 0), "RIGHT"),
    ]))

    # Statement
    stmt = Paragraph(e["statement"], S_STMT)

    # Position + Martyrdom row
    pos_row = Table(
        [[
            Paragraph("<b>Position:</b>", S_TICK),
            Paragraph(f"{BOX} Affirm", S_TICK),
            Paragraph(f"{BOX} Deny", S_TICK),
            Paragraph(f"{BOX} Open", S_TICK),
            Paragraph(f"{BOX} Uncertain", S_TICK),
            Paragraph("<b>Martyrdom (0-10):</b>", S_TICK),
            Paragraph("______ / 10", S_TICK),
        ]],
        colWidths=[55, 55, 50, 50, 70, 100, 60],
    )
    pos_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    # Ladder label + 2x2 ladder grid (visit/participate/serve/member)
    ladder_label = Paragraph(
        "<b>If a church teaches the opposite of the above, would you...</b>",
        S_LABEL,
    )
    ladder = Table(
        [
            [
                Paragraph("Visit?", S_TICK),
                Paragraph(BOXY, S_TICK), Paragraph(BOXN, S_TICK),
                Paragraph("", S_TICK),
                Paragraph("Participate in worship?", S_TICK),
                Paragraph(BOXY, S_TICK), Paragraph(BOXN, S_TICK),
            ],
            [
                Paragraph("Serve in ministry?", S_TICK),
                Paragraph(BOXY, S_TICK), Paragraph(BOXN, S_TICK),
                Paragraph("", S_TICK),
                Paragraph("Become a member?", S_TICK),
                Paragraph(BOXY, S_TICK), Paragraph(BOXN, S_TICK),
            ],
        ],
        colWidths=[120, 30, 30, 20, 150, 30, 30],
    )
    ladder.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    # Other actions: 5 rows, each "Question? [ ]Y [ ]N"
    other_label = Paragraph("<b>Other actions...</b>", S_LABEL)
    other = Table(
        [
            [Paragraph("Marry someone holding the opposite?", S_TICK),
             Paragraph(BOXY, S_TICK), Paragraph(BOXN, S_TICK)],
            [Paragraph("Teach this affirmatively to your children?", S_TICK),
             Paragraph(BOXY, S_TICK), Paragraph(BOXN, S_TICK)],
            [Paragraph("Correct someone who holds the opposite?", S_TICK),
             Paragraph(BOXY, S_TICK), Paragraph(BOXN, S_TICK)],
            [Paragraph("Break fellowship over this?", S_TICK),
             Paragraph(BOXY, S_TICK), Paragraph(BOXN, S_TICK)],
            [Paragraph("Is denial of this a cult-grade error?", S_TICK),
             Paragraph(BOXY, S_TICK), Paragraph(BOXN, S_TICK)],
        ],
        colWidths=[400, 30, 30],
    )
    other.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#E5E7E9")),
    ]))

    items = [header, stmt, pos_row, ladder_label, ladder, other_label, other,
             Spacer(1, 8)]
    body = Table([[item] for item in items], colWidths=[USABLE_W])
    body.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    block = Table([[body]], colWidths=[USABLE_W])
    block.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return KeepTogether([block, Spacer(1, 4)])


# -- Body section -----------------------------------------------------------

def questions_section(doc: dict, tier_filter: list[str]) -> list:
    out: list = [PageBreak()]
    current_cat = None
    n = 0
    for e in doc["entries"]:
        if e["tier"] not in tier_filter:
            continue
        if e["category"] != current_cat:
            current_cat = e["category"]
            out.append(Paragraph(current_cat, S_CATHEAD))
        n += 1
        out.append(question_block(e, n))
    return out


# -- CLI --------------------------------------------------------------------

app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def render(
    input: Path = typer.Option(
        Path("personal-beliefs.json"), "--input", "-i",
        help="Path to personal-beliefs.json.",
    ),
    output: Path = typer.Option(
        Path("personal-beliefs-questionnaire.pdf"), "--output", "-o",
        help="Output PDF path.",
    ),
    tiers: str = typer.Option(
        "essential", "--tiers",
        help="Comma-separated tiers to include (essential|convictional|important|preference|adiaphora).",
    ),
    all_tiers: bool = typer.Option(
        False, "--all-tiers", help="Include all tiers (overrides --tiers).",
    ),
    categories: str = typer.Option(
        "", "--categories",
        help="Optional comma-separated category names to filter (e.g., 'Christology,Soteriology').",
    ),
):
    """Render personal-beliefs.json into a printable tick-box questionnaire."""
    data = json.loads(input.read_text(encoding="utf-8"))

    if all_tiers:
        tier_filter = TIER_ORDER[:]
    else:
        tier_filter = [t.strip() for t in tiers.split(",") if t.strip()]
        bad = [t for t in tier_filter if t not in TIER_ORDER]
        if bad:
            sys.stderr.write(f"Unknown tier(s): {bad}. Valid: {TIER_ORDER}\n")
            raise SystemExit(1)

    if categories:
        cat_filter = {c.strip() for c in categories.split(",") if c.strip()}
        data = {**data, "entries": [e for e in data["entries"] if e["category"] in cat_filter]}

    matched = [e for e in data["entries"] if e["tier"] in tier_filter]
    total = len(matched)
    if total == 0:
        sys.stderr.write("No entries match the filter.\n")
        raise SystemExit(1)

    pdf = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Doctrinal Position Questionnaire",
        author=data.get("owner", ""),
    )
    flow: list = []
    flow.extend(cover_page(data, tier_filter, total))
    flow.extend(questions_section(data, tier_filter))

    pdf.build(flow, onFirstPage=page_header_footer, onLaterPages=page_header_footer)
    print(f"Wrote {output} — {total} question block(s) across tier filter {tier_filter}.")


if __name__ == "__main__":
    app()
