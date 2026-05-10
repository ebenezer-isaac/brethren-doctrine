"""Render personal-beliefs.json to a hybrid PDF.

Layout:
  1. Front matter: title, owner, discernment principle, tier legend, KPI legend.
  2. Index table: every entry, grouped by category, color-coded tier badges.
  3. Detail cards: full info for entries matching --tiers (default essential+convictional).

Run from project root:
    uv add reportlab typer
    uv run python tools/render_beliefs_pdf.py
    uv run python tools/render_beliefs_pdf.py --tiers essential,convictional,important
    uv run python tools/render_beliefs_pdf.py --no-cards   # index only
    uv run python tools/render_beliefs_pdf.py -i path/to.json -o path/to.pdf
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
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

POSITION_GLYPH = {"affirm": "A", "deny": "D", "open": "O", "uncertain": "?"}
POSITION_COLOR = {
    "affirm":    colors.HexColor("#1E7E34"),
    "deny":      colors.HexColor("#A93226"),
    "open":      colors.HexColor("#5D6D7E"),
    "uncertain": colors.HexColor("#B7950B"),
}

# Helvetica (reportlab default) uses WinAnsi encoding which lacks ✓/✗.
# Use ASCII-safe markers so no font registration is required.
TRUE_MARK = "Y"
FALSE_MARK = "-"

# -- Paragraph styles -------------------------------------------------------

_styles = getSampleStyleSheet()

S_TITLE = ParagraphStyle(
    "title", parent=_styles["Title"], fontSize=20, leading=24, spaceAfter=8
)
S_SUBTITLE = ParagraphStyle(
    "subtitle", parent=_styles["Normal"], fontSize=11, leading=14,
    textColor=colors.HexColor("#5D6D7E"), spaceAfter=8,
)
S_PRINCIPLE = ParagraphStyle(
    "principle", parent=_styles["Italic"], fontSize=10, leading=13,
    leftIndent=10, rightIndent=10, spaceBefore=6, spaceAfter=12,
)
S_CATHEAD = ParagraphStyle(
    "cathead", parent=_styles["Heading2"], fontSize=12, leading=14,
    textColor=colors.white, backColor=colors.HexColor("#1F3A5F"),
    leftIndent=4, spaceBefore=8, spaceAfter=4,
)
S_STMT_INDEX = ParagraphStyle(
    "stmtIndex", parent=_styles["Normal"], fontSize=8, leading=10,
)
S_ID_INDEX = ParagraphStyle(
    "idIndex", parent=_styles["Normal"], fontName="Courier",
    fontSize=7, leading=9,
)
S_CARD_HEADER = ParagraphStyle(
    "cardHead", parent=_styles["Heading4"], fontSize=11, leading=13,
    textColor=colors.white,
)
S_CARD_STMT = ParagraphStyle(
    "cardStmt", parent=_styles["Normal"], fontSize=10, leading=13,
    fontName="Helvetica-Bold", spaceBefore=2, spaceAfter=3,
)
S_CARD_BODY = ParagraphStyle(
    "cardBody", parent=_styles["Normal"], fontSize=9, leading=12, spaceAfter=2,
)
S_CARD_META = ParagraphStyle(
    "cardMeta", parent=_styles["Normal"], fontSize=8, leading=10,
    textColor=colors.HexColor("#5D6D7E"), spaceAfter=2,
)
S_CARD_NOTES = ParagraphStyle(
    "cardNotes", parent=_styles["Italic"], fontSize=8, leading=10,
    textColor=colors.HexColor("#566573"), spaceAfter=2,
)


def truncate(text: str, n: int) -> str:
    if not text:
        return ""
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def yn(b) -> str:
    if b is True:
        return TRUE_MARK
    if b is False:
        return FALSE_MARK
    return ""


# -- Front matter -----------------------------------------------------------

# -- Page header/footer (drawn on every page via canvas) --------------------

HEADER_TEXT = (
    "Position glyphs:  A = Affirm   D = Deny   O = Open   ? = Uncertain"
    "        Booleans:  Y = applies   - = does not apply"
)
FOOTER_TEXT = (
    "Columns:  M = Martyrdom (0-10)   "
    "V = Visit  ·  P = Participate  ·  S = Serve in ministry  ·  Mb = Become member  "
    "(if a church teaches the opposite)   "
    "Cult = denial flags cult-grade error   "
    "Brt = Brethren distinctive"
)


def _draw_tier_swatches(canvas, x: float, y: float, height: float = 8) -> float:
    """Draw a short row of tier color swatches with labels. Returns ending x."""
    canvas.setFont("Helvetica-Bold", 6)
    cursor = x
    for tier in TIER_ORDER:
        label = tier.upper()
        text_w = stringWidth(label, "Helvetica-Bold", 6) + 6
        canvas.setFillColor(TIER_BG[tier])
        canvas.rect(cursor, y - 1, text_w, height, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.drawString(cursor + 3, y + 1, label)
        cursor += text_w + 2
    return cursor


def page_header_footer(canvas, doc):
    canvas.saveState()
    page_w, page_h = doc.pagesize
    margin = 10 * mm

    # ---- Header (top): position glyphs + boolean markers + page number
    header_y = page_h - 7 * mm
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#34495E"))
    canvas.drawString(margin, header_y, HEADER_TEXT)

    canvas.setFont("Helvetica-Oblique", 7)
    canvas.setFillColor(colors.HexColor("#7F8C8D"))
    canvas.drawRightString(page_w - margin, header_y, f"Page {doc.page}")

    # Subtle separator under header
    canvas.setStrokeColor(colors.HexColor("#D5DBDB"))
    canvas.setLineWidth(0.25)
    canvas.line(margin, header_y - 2, page_w - margin, header_y - 2)

    # ---- Footer (bottom): tier color key + column-letter glossary
    footer_y = 6 * mm

    # Tier swatches at left
    canvas.setFillColor(colors.HexColor("#34495E"))
    canvas.setFont("Helvetica", 6)
    canvas.drawString(margin, footer_y + 3, "Tier:")
    swatch_x = margin + 16
    _draw_tier_swatches(canvas, swatch_x, footer_y, height=8)

    # Column glossary at right of swatches
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(colors.HexColor("#34495E"))
    canvas.drawRightString(page_w - margin, footer_y + 1, FOOTER_TEXT)

    # Subtle separator above footer
    canvas.setStrokeColor(colors.HexColor("#D5DBDB"))
    canvas.line(margin, footer_y + 11, page_w - margin, footer_y + 11)

    canvas.restoreState()


def front_matter(doc: dict) -> list:
    out = [
        Paragraph("Personal Beliefs Baseline", S_TITLE),
        Paragraph(
            f"{doc['owner']} — {doc['tradition_baseline']}<br/>"
            f"<font size='9'>Generated {doc['generated_at']} · "
            f"{doc['stats']['total']} entries · {doc['location_context']}</font>",
            S_SUBTITLE,
        ),
        Paragraph(f"<i>{doc['discernment_principle']}</i>", S_PRINCIPLE),
    ]

    rows = [["Tier", "Definition", "Count"]]
    for tier in TIER_ORDER:
        if tier in doc["tier_definitions"]:
            rows.append([
                tier.upper(),
                doc["tier_definitions"][tier],
                str(doc["stats"]["by_tier"].get(tier, 0)),
            ])
    legend = Table(rows, colWidths=[80, 600, 40])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BDC3C7")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9F9")]),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, tier in enumerate(TIER_ORDER, start=1):
        style += [
            ("BACKGROUND", (0, i), (0, i), TIER_BG[tier]),
            ("TEXTCOLOR", (0, i), (0, i), TIER_FG[tier]),
            ("FONTNAME", (0, i), (0, i), "Helvetica-Bold"),
            ("ALIGN", (0, i), (0, i), "CENTER"),
        ]
    legend.setStyle(TableStyle(style))
    out.append(legend)
    out.append(Spacer(1, 8))

    out.append(Paragraph(
        "<b>Index columns &mdash; full legend:</b> "
        "<b>Tier</b> = importance (color-coded; see footer of every page). "
        "<b>M</b> = martyrdom 0-10 (0 = indifferent, 10 = would die for it). "
        "<b>Pos</b> = personal stance &mdash; "
        "<b>A</b>ffirm, <b>D</b>eny, <b>O</b>pen, <b>?</b> Uncertain. "
        "<b>V / P / S / Mb</b> = relationship ladder if a church teaches the opposite: "
        "<b>V</b>isit, <b>P</b>articipate, <b>S</b>erve in ministry, become a <b>M</b>em<b>b</b>er. "
        f"<b>{TRUE_MARK}</b> = applies (allowed), <b>{FALSE_MARK}</b> = does not. "
        "<b>Cult</b> = denial of this doctrine flags cult-grade error. "
        "<b>Brt</b> = position is a Brethren-tradition distinctive.",
        S_CARD_META,
    ))
    out.append(Spacer(1, 4))
    out.append(Paragraph(
        "<i>The header on every page lists the position glyphs and Y/&minus; markers. "
        "The footer lists the column abbreviations and the tier color key. "
        "The two are complementary &mdash; together they cover every symbol on the page.</i>",
        S_CARD_NOTES,
    ))
    return out


# -- Index table ------------------------------------------------------------

INDEX_HEADERS = ["ID", "Statement", "Tier", "M", "Pos", "V", "P", "S", "Mb", "Cult", "Brt"]
INDEX_COLS = [105, 350, 65, 22, 28, 18, 18, 18, 24, 30, 30]


def index_section(doc: dict) -> list:
    out = [PageBreak(), Paragraph("Index — All Entries", S_TITLE), Spacer(1, 4)]

    rows: list = []
    style_cmds: list = []
    current_cat: str | None = None

    def flush():
        nonlocal rows, style_cmds
        if not rows:
            return
        full = [INDEX_HEADERS] + rows
        t = Table(full, colWidths=INDEX_COLS, repeatRows=1)
        base = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D5DBDB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9F9")]),
            ("ALIGN", (2, 1), (-1, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
        t.setStyle(TableStyle(base + style_cmds))
        out.append(t)
        out.append(Spacer(1, 6))
        rows.clear()
        style_cmds.clear()

    for e in doc["entries"]:
        if e["category"] != current_cat:
            flush()
            current_cat = e["category"]
            cnt = doc["stats"]["by_category"].get(current_cat, 0)
            out.append(Paragraph(f"{current_cat} ({cnt})", S_CATHEAD))

        tier = e["tier"]
        ridx = len(rows) + 1
        rows.append([
            Paragraph(e["id"], S_ID_INDEX),
            Paragraph(truncate(e["statement"], 160), S_STMT_INDEX),
            tier.upper(),
            str(e["martyrdom_value"]),
            POSITION_GLYPH.get(e["personal_position"], "?"),
            yn(e["visit_if_taught_otherwise"]),
            yn(e["participate_if_taught_otherwise"]),
            yn(e["serve_in_ministry_if_held_otherwise"]),
            yn(e["member_if_taught_otherwise"]),
            TRUE_MARK if e["cult_marker_if_denied"] else "",
            TRUE_MARK if e["brethren_distinctive"] else "",
        ])
        style_cmds += [
            ("BACKGROUND", (2, ridx), (2, ridx), TIER_BG[tier]),
            ("TEXTCOLOR", (2, ridx), (2, ridx), TIER_FG[tier]),
            ("FONTNAME", (2, ridx), (2, ridx), "Helvetica-Bold"),
            ("TEXTCOLOR", (4, ridx), (4, ridx),
                POSITION_COLOR.get(e["personal_position"], colors.black)),
            ("FONTNAME", (4, ridx), (4, ridx), "Helvetica-Bold"),
        ]
        if e["cult_marker_if_denied"]:
            style_cmds += [
                ("TEXTCOLOR", (9, ridx), (9, ridx), colors.HexColor("#A93226")),
                ("FONTNAME", (9, ridx), (9, ridx), "Helvetica-Bold"),
            ]
        if e["brethren_distinctive"]:
            style_cmds += [
                ("TEXTCOLOR", (10, ridx), (10, ridx), colors.HexColor("#1F3A5F")),
                ("FONTNAME", (10, ridx), (10, ridx), "Helvetica-Bold"),
            ]

    flush()
    return out


# -- Detail cards -----------------------------------------------------------

CARD_W = 760  # landscape A4 minus 10mm margins


def detail_card(e: dict) -> KeepTogether:
    tier = e["tier"]
    bg, fg = TIER_BG[tier], TIER_FG[tier]

    sub = e.get("subcategory") or ""
    cat_text = e["category"] + (f" › {sub}" if sub else "")

    header = Table(
        [[
            Paragraph(f"<b>{e['id']}</b>", S_CARD_HEADER),
            Paragraph(cat_text, S_CARD_HEADER),
            Paragraph(f"<b>{tier.upper()}</b>", S_CARD_HEADER),
        ]],
        colWidths=[200, 460, 100],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("TEXTCOLOR", (0, 0), (-1, -1), fg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
    ]))

    meta_parts = [
        f"<b>Position:</b> {e['personal_position'].upper()}",
        f"<b>Martyrdom:</b> {e['martyrdom_value']}/10",
        f"<b>Consensus:</b> {e['historical_consensus']}",
    ]
    if e.get("brethren_distinctive"):
        meta_parts.append("<b>Brethren distinctive</b>")
    if e.get("cult_marker_if_denied"):
        meta_parts.append("<font color='#A93226'><b>Cult marker</b></font>")
    if e.get("evangelism_target_if_denied"):
        meta_parts.append("<b>Evangelism target if denied</b>")

    body_items = [
        Paragraph(e["statement"], S_CARD_STMT),
        Paragraph(" · ".join(meta_parts), S_CARD_META),
        Paragraph(f"<b>Rationale.</b> {e.get('position_rationale', '')}", S_CARD_BODY),
    ]
    refs = []
    if e.get("scripture_anchors"):
        refs.append(f"<b>Scripture:</b> {', '.join(e['scripture_anchors'])}")
    if e.get("confessional_anchors"):
        refs.append(f"<b>Confessions:</b> {', '.join(e['confessional_anchors'])}")
    if refs:
        body_items.append(Paragraph(" &nbsp;|&nbsp; ".join(refs), S_CARD_META))

    kpi_rows = [
        ["Visit",         yn(e["visit_if_taught_otherwise"]),
         "Participate",   yn(e["participate_if_taught_otherwise"]),
         "Serve in min.", yn(e["serve_in_ministry_if_held_otherwise"]),
         "Member",        yn(e["member_if_taught_otherwise"])],
        ["Marry across",  yn(e["marry_if_held_otherwise"]),
         "Teach to kids", yn(e["teach_to_children"]),
         "Correct",       yn(e["correct_if_encountered"]),
         "Break fellow.", yn(e["break_fellowship_if_denied"])],
    ]
    kpi = Table(kpi_rows, colWidths=[70, 22, 75, 22, 75, 22, 80, 22])
    kpi.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F6F7")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#34495E")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("ALIGN", (5, 0), (5, -1), "CENTER"),
        ("ALIGN", (7, 0), (7, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    body_items.append(kpi)

    if e.get("notes"):
        body_items.append(Paragraph(f"<i>{e['notes']}</i>", S_CARD_NOTES))

    body = Table([[item] for item in body_items], colWidths=[CARD_W])
    body.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    card = Table([[header], [body]], colWidths=[CARD_W])
    card.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return KeepTogether([card, Spacer(1, 6)])


def detail_section(doc: dict, tier_filter: list[str]) -> list:
    out = [
        PageBreak(),
        Paragraph("Detail — Filtered Entries", S_TITLE),
        Paragraph(
            f"<font size='9' color='#5D6D7E'>Tier filter: {', '.join(tier_filter)}.</font>",
            _styles["Normal"],
        ),
        Spacer(1, 6),
    ]
    current_cat = None
    for e in doc["entries"]:
        if e["tier"] not in tier_filter:
            continue
        if e["category"] != current_cat:
            current_cat = e["category"]
            out.append(Spacer(1, 4))
            out.append(Paragraph(current_cat, S_CATHEAD))
        out.append(detail_card(e))
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
        Path("personal-beliefs.pdf"), "--output", "-o",
        help="Output PDF path.",
    ),
    tiers: str = typer.Option(
        "essential,convictional", "--tiers",
        help="Comma-separated tiers to include in detail cards.",
    ),
    no_cards: bool = typer.Option(
        False, "--no-cards", help="Skip detail cards; index only.",
    ),
):
    """Render personal-beliefs.json to a hybrid PDF (index table + detail cards)."""
    data = json.loads(input.read_text(encoding="utf-8"))
    tier_filter = [t.strip() for t in tiers.split(",") if t.strip()]
    bad = [t for t in tier_filter if t not in TIER_ORDER]
    if bad:
        sys.stderr.write(f"Unknown tier(s): {bad}. Valid: {TIER_ORDER}\n")
        raise SystemExit(1)

    pdf = SimpleDocTemplate(
        str(output),
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Personal Beliefs Baseline",
        author=data.get("owner", ""),
    )
    flow: list = []
    flow.extend(front_matter(data))
    flow.extend(index_section(data))
    if not no_cards:
        flow.extend(detail_section(data, tier_filter))

    pdf.build(flow, onFirstPage=page_header_footer, onLaterPages=page_header_footer)
    cards = sum(1 for e in data["entries"] if e["tier"] in tier_filter) if not no_cards else 0
    print(
        f"Wrote {output} — {data['stats']['total']} entries indexed, "
        f"{cards} detail cards."
    )


if __name__ == "__main__":
    app()
