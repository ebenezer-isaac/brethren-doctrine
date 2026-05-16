"""HTML chunking utilities shared by cultural-source adapters.

Adapters pass in fetched bytes; this module strips boilerplate, locates the
main content body, and yields anchored paragraphs. Source-specific parsers
build on top of the helpers here.
"""

from __future__ import annotations

import html as html_unescape
import re
import unicodedata
from collections.abc import Iterable, Iterator
from typing import Any

from lxml import etree, html

WHITESPACE_RUN = re.compile(r"\s+")
SECTION_LEADER = re.compile(r"^\s*(\d+)\.\s+")
QA_LEADER = re.compile(r"^\s*Q\.\s*(\d+)\.?\s*(.*)$")


def _decode(raw: bytes) -> str:
    """Decode HTML bytes. Falls back through utf-8, windows-1252, latin-1."""
    for enc in ("utf-8", "windows-1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_html(raw: bytes | str) -> Any:
    """Robust HTML parse via lxml.html. Handles malformed pages and mixed encodings."""
    if isinstance(raw, bytes):
        return html.fromstring(_decode(raw))
    return html.fromstring(raw)


def text_of(element: Any) -> str:
    """Recursive text content with whitespace normalised."""
    if element is None:
        return ""
    if isinstance(element, str):
        s = element
    else:
        try:
            s = etree.tostring(element, method="text", encoding="unicode")
        except (TypeError, ValueError):
            s = "".join(element.itertext()) if hasattr(element, "itertext") else ""
    s = html_unescape.unescape(s)
    s = unicodedata.normalize("NFC", s)
    return WHITESPACE_RUN.sub(" ", s).strip()


def iter_paragraphs(elements: Iterable[Any]) -> Iterator[str]:
    """Yield non-empty cleaned paragraph text from a sequence of <p>-like elements."""
    for el in elements:
        s = text_of(el)
        if s and len(s) >= 4:
            yield s


def chunk_paragraphs(
    paragraphs: list[str],
    *,
    target_tokens: int = 400,
    min_tokens: int = 80,
) -> list[str]:
    """Group small consecutive paragraphs so each chunk hits the target token band.

    Approx 1 token = 0.75 word. Caller passes raw paragraphs; we return merged
    chunks. Long paragraphs pass through untouched even if they exceed target.
    """
    buf: list[str] = []
    buf_words = 0
    out: list[str] = []
    for para in paragraphs:
        words = para.split()
        if not words:
            continue
        wc = len(words)
        target_words = int(target_tokens / 0.75)
        min_words = int(min_tokens / 0.75)
        if buf and buf_words + wc > target_words and buf_words >= min_words:
            out.append(" ".join(buf))
            buf = [para]
            buf_words = wc
            continue
        buf.append(para)
        buf_words += wc
        if buf_words >= target_words:
            out.append(" ".join(buf))
            buf = []
            buf_words = 0
    if buf:
        out.append(" ".join(buf))
    return out


def opc_style_chapter_sections(
    raw: bytes,
    chapter_anchor_re: re.Pattern[str] | str = r"Chapter_(\d+)",
) -> list[dict[str, Any]]:
    """Parse OPC-style confession HTML.

    Each chapter is wrapped in `<h3 class="divider"><a name="Chapter_NN"></a>CHAPTER N<br><i>Title</i></h3>`
    followed by numbered `<p>N. text</p>` sections. Returns a list of dicts:
    `[{chapter: int, chapter_title: str, sections: [{section: int, text: str}]}]`.
    """
    if isinstance(chapter_anchor_re, str):
        chapter_anchor_re = re.compile(chapter_anchor_re)
    tree = parse_html(raw)
    out: list[dict[str, Any]] = []
    chapters_seen: dict[int, dict[str, Any]] = {}
    current: dict[str, Any] | None = None

    for node in tree.iter():
        tag = node.tag if isinstance(node.tag, str) else ""
        if tag == "h3":
            anchor = node.find(".//a[@name]")
            anchor_name = anchor.get("name") if anchor is not None else None
            if anchor_name:
                m = chapter_anchor_re.search(anchor_name)
                if m:
                    chap = int(m.group(1))
                    if chap in chapters_seen:
                        current = chapters_seen[chap]
                        continue
                    title = text_of(node)
                    title = re.sub(r"^CHAPTER\s+[IVXLCDM\d]+\s*", "", title, flags=re.I)
                    current = {"chapter": chap, "chapter_title": title.strip(), "sections": []}
                    chapters_seen[chap] = current
                    out.append(current)
                    continue
        if tag == "p" and current is not None:
            text = text_of(node)
            if not text:
                continue
            m = SECTION_LEADER.match(text)
            if m:
                section_num = int(m.group(1))
                body = text[m.end() :].strip()
                current["sections"].append({"section": section_num, "text": body})
            elif current["sections"]:
                current["sections"][-1]["text"] += " " + text
    return out


def opc_qa_blocks(raw: bytes) -> list[dict[str, Any]]:
    """Parse OPC catechism HTML (Q.N format).

    Each block is `<p>Q. N. <i>Question</i><br/>A. Answer text</p>`.
    Returns `[{q_num: int, question: str, answer: str}]`.
    """
    tree = parse_html(raw)
    out: list[dict[str, Any]] = []
    for p in tree.iter("p"):
        text = text_of(p)
        if not text.startswith("Q."):
            continue
        m = re.match(r"Q\.\s*(\d+)\.\s*(.+?)\s*A\.\s*(.+)$", text, re.DOTALL)
        if not m:
            continue
        out.append(
            {
                "q_num": int(m.group(1)),
                "question": m.group(2).strip(),
                "answer": m.group(3).strip(),
            }
        )
    return out


def squarespace_paragraphs(raw: bytes) -> list[str]:
    """Extract content paragraphs from a Squarespace block-content body.

    Squarespace wraps body content in `<div class="sqs-block-content">`. We
    pull all <p> descendants and clean. The 1689confession.com site uses this.
    """
    tree = parse_html(raw)
    blocks = tree.xpath("//div[contains(@class,'sqs-block-content')]")
    paras: list[str] = []
    for blk in blocks:
        for p in blk.iter("p"):
            s = text_of(p)
            if s:
                paras.append(s)
    if paras:
        return paras
    return list(iter_paragraphs(tree.iter("p")))


def main_article_paragraphs(raw: bytes) -> list[str]:
    """Heuristic content extractor for arbitrary HTML.

    Tries <article>, then <main>, then the largest <div> by paragraph count.
    Strips nav / footer / header descendants.
    """
    tree = parse_html(raw)
    for xpath in ("//article", "//main", "//div[@id='content']", "//div[@class='content']"):
        nodes = tree.xpath(xpath)
        if nodes:
            paras = list(iter_paragraphs(nodes[0].iter("p")))
            if paras:
                return paras
    candidates = tree.xpath("//div")
    best: list[str] = []
    for div in candidates:
        paras = list(iter_paragraphs(div.iter("p")))
        if len(paras) > len(best):
            best = paras
    if best:
        return best
    return list(iter_paragraphs(tree.iter("p")))


def crcna_qa_blocks(raw: bytes) -> list[dict[str, Any]]:
    """Parse crcna.org Heidelberg catechism HTML.

    Each Q&A appears in markup as a plain-text marker `Q & A N` followed by
    `<p>Q. ...</p>` and `<p>A. ...</p>` paragraphs and additional `<p>` body
    text. Proof-text paragraphs start with a digit and a Bible reference. We
    walk the document order, finding markers and accumulating body text until
    the next marker.

    Returns `[{q_num: int, question: str, answer: str}]`.
    """
    text_blob = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    marker_re = re.compile(r"Q\s*&(?:amp;)?\s*A\s*(\d+)\b")
    out: list[dict[str, Any]] = []
    markers = list(marker_re.finditer(text_blob))
    if not markers:
        return out
    for i, m in enumerate(markers):
        q_num = int(m.group(1))
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text_blob)
        block = text_blob[start:end]
        block_tree = parse_html(f"<root>{block}</root>")
        question_lines: list[str] = []
        answer_lines: list[str] = []
        mode: str | None = None
        for p in block_tree.iter("p"):
            text = text_of(p)
            if not text:
                continue
            if re.match(r"^\s*\d+\s+[A-Z]", text) and any(ref in text for ref in (". ", ":")):
                continue
            if text.startswith("Q.") or text.startswith("Q "):
                mode = "q"
                question_lines.append(text[2:].lstrip(".  "))
                continue
            if text.startswith("A.") or text.startswith("A "):
                mode = "a"
                answer_lines.append(text[2:].lstrip(".  "))
                continue
            if mode == "a":
                answer_lines.append(text)
            elif mode == "q":
                question_lines.append(text)
        out.append(
            {
                "q_num": q_num,
                "question": " ".join(question_lines).strip(),
                "answer": " ".join(answer_lines).strip(),
            }
        )
    return out


def crcna_article_blocks(raw: bytes) -> list[dict[str, Any]]:
    """Parse crcna.org Belgic / Dort HTML.

    Article markers look like `Article N: Title` followed by paragraphs.
    Returns `[{article: int, title: str, text: str}]`. Caller maps to anchors.
    """
    text_blob = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    marker_re = re.compile(r"Article\s+(\d+):?\s*([^\n<]{0,120})", re.IGNORECASE)
    markers = list(marker_re.finditer(text_blob))
    out: list[dict[str, Any]] = []
    for i, m in enumerate(markers):
        art_num = int(m.group(1))
        title = re.sub(r"\s+", " ", m.group(2)).strip().rstrip(":").strip()
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text_blob)
        block = text_blob[start:end]
        block_tree = parse_html(f"<root>{block}</root>")
        paras = []
        for p in block_tree.iter("p"):
            t = text_of(p)
            if not t:
                continue
            if re.match(r"^\s*\d+\s+[A-Z]", t):
                continue
            paras.append(t)
        body = " ".join(paras).strip()
        if body:
            out.append({"article": art_num, "title": title, "text": body})
    return out


def crcna_dort_articles(raw: bytes) -> list[dict[str, Any]]:
    """Parse Canons of Dort: 5 main heads, each with numbered articles.

    Returns `[{head: int, article: int, text: str}]`. Heads are roman-numbered
    `First Main Point`, `Second Main Point`, etc., and articles within each
    restart at 1.
    """
    text_blob = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    head_re = re.compile(
        r"(First|Second|Third|Fourth|Fifth)\s+(?:Main\s+Point\s+of\s+Doctrine|and\s+Fourth\s+Main\s+Points)",
        re.IGNORECASE,
    )
    head_lookup = {
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5,
        "third and fourth": 3,
    }
    article_re = re.compile(r"Article\s+(\d+):?\s*([^\n<]{0,120})", re.IGNORECASE)
    heads = list(head_re.finditer(text_blob))
    out: list[dict[str, Any]] = []
    for hi, head_match in enumerate(heads):
        head_word = head_match.group(1).lower()
        head_num = head_lookup.get(head_word, hi + 1)
        seg_start = head_match.end()
        seg_end = heads[hi + 1].start() if hi + 1 < len(heads) else len(text_blob)
        segment = text_blob[seg_start:seg_end]
        article_markers = list(article_re.finditer(segment))
        for ai, am in enumerate(article_markers):
            art_num = int(am.group(1))
            ttl = re.sub(r"\s+", " ", am.group(2)).strip().rstrip(":").strip()
            s = am.end()
            e = article_markers[ai + 1].start() if ai + 1 < len(article_markers) else len(segment)
            block_tree = parse_html(f"<root>{segment[s:e]}</root>")
            paras = []
            for p in block_tree.iter("p"):
                t = text_of(p)
                if not t:
                    continue
                if re.match(r"^\s*\d+\s+[A-Z]", t):
                    continue
                paras.append(t)
            body = " ".join(paras).strip()
            if body:
                out.append(
                    {
                        "head": head_num,
                        "article": art_num,
                        "title": ttl,
                        "text": body,
                    }
                )
    return out


def bcp1662_qa_blocks(raw: bytes) -> list[dict[str, Any]]:
    """Parse the eskimo.com/~lhowell/bcp1662 catechism page.

    Markup uses `<EM>Question.</EM>` and `<EM>Answer.</EM>` inline tags, with
    questions and answers separated by `<P>` paragraphs. Returns `[{q_num, question, answer}]`.
    """
    text_blob = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    text_blob = re.sub(r"<IMG[^>]*>", " ", text_blob, flags=re.IGNORECASE)
    paragraphs = re.split(r"<P[^>]*>", text_blob, flags=re.IGNORECASE)
    out: list[dict[str, Any]] = []
    pending_q: str | None = None
    counter = 0
    for p in paragraphs:
        p = re.sub(r"&#160;", " ", p)
        wrap = parse_html(f"<root>{p}</root>")
        text = text_of(wrap)
        if not text:
            continue
        q_match = re.search(r"Question\.\s*(.*?)\s*Answer\.\s*(.*)$", text, re.DOTALL)
        if q_match:
            counter += 1
            out.append(
                {
                    "q_num": counter,
                    "question": q_match.group(1).strip(),
                    "answer": q_match.group(2).strip(),
                }
            )
            continue
        if "Question." in text and "Answer." not in text:
            pending_q = re.sub(r".*Question\.\s*", "", text, count=1, flags=re.DOTALL).strip()
            continue
        if pending_q and text.startswith("Answer."):
            counter += 1
            out.append(
                {
                    "q_num": counter,
                    "question": pending_q,
                    "answer": text[len("Answer.") :].strip(),
                }
            )
            pending_q = None
    return out


def bcp1662_section(raw: bytes, title_default: str = "") -> dict[str, Any]:
    """Parse a generic BCP 1662 prose section page into a single chunk.

    Collects the page title (<H2>) and the body text minus images/navigation.
    Returns `{title, text}`.
    """
    text_blob = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    text_blob = re.sub(r"<IMG[^>]*>", " ", text_blob, flags=re.IGNORECASE)
    text_blob = re.sub(r"&#160;", " ", text_blob)
    tree = parse_html(text_blob)
    title = title_default
    h2 = tree.xpath("//h2")
    if h2:
        h2_text = text_of(h2[0]).strip()
        if h2_text:
            title = h2_text
    body_xpaths = ("//body", "//BODY")
    body_el = None
    for xp in body_xpaths:
        nodes = tree.xpath(xp)
        if nodes:
            body_el = nodes[0]
            break
    if body_el is None:
        body_el = tree
    chunks: list[str] = []
    for chunk in re.split(r"<P[^>]*>", text_blob, flags=re.IGNORECASE):
        wrap = parse_html(f"<root>{chunk}</root>")
        t = text_of(wrap)
        if t and len(t) >= 8:
            chunks.append(t)
    return {"title": title, "text": "\n\n".join(chunks)}


def wikisource_39_articles(raw: bytes) -> list[dict[str, Any]]:
    """Parse the 39 Articles wikisource page.

    Each article is announced by a centered div containing `N. <smallcaps>Title</smallcaps>`,
    followed by one or more body `<p>` paragraphs until the next article div.
    Returns `[{article: int, title: str, text: str}]` for articles 1..39.
    """
    roman_to_int = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8,
        "IX": 9,
        "X": 10,
        "XI": 11,
        "XII": 12,
        "XIII": 13,
        "XIV": 14,
        "XV": 15,
        "XVI": 16,
        "XVII": 17,
        "XVIII": 18,
        "XIX": 19,
        "XX": 20,
        "XXI": 21,
        "XXII": 22,
        "XXIII": 23,
        "XXIV": 24,
        "XXV": 25,
        "XXVI": 26,
        "XXVII": 27,
        "XXVIII": 28,
        "XXIX": 29,
        "XXX": 30,
        "XXXI": 31,
        "XXXII": 32,
        "XXXIII": 33,
        "XXXIV": 34,
        "XXXV": 35,
        "XXXVI": 36,
        "XXXVII": 37,
        "XXXVIII": 38,
        "XXXIX": 39,
    }
    tree = parse_html(raw)
    out: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    body = tree.xpath("//div[contains(@class,'mw-parser-output')]")
    if not body:
        return out
    body_el = body[0]
    for node in body_el.iter():
        tag = node.tag if isinstance(node.tag, str) else ""
        cls = node.get("class") or ""
        if tag == "div" and "wst-center" in cls:
            inner = text_of(node)
            m = re.match(r"^([IVX]+)\.\s+(.+?)\.?$", inner)
            if m and m.group(1) in roman_to_int:
                if current is not None:
                    out.append(current)
                current = {
                    "article": roman_to_int[m.group(1)],
                    "title": m.group(2).rstrip("."),
                    "text": "",
                }
                continue
        if tag == "p" and current is not None:
            parent = node.getparent()
            parent_cls = parent.get("class") if parent is not None else ""
            if parent_cls and "wst-center" in parent_cls:
                continue
            t = text_of(node)
            if t:
                current["text"] = (current["text"] + " " + t).strip()
    if current is not None:
        out.append(current)
    return [a for a in out if a["text"]]


_AG_TITLES = {
    1: "The Scriptures Inspired",
    2: "The One True God",
    3: "The Deity of the Lord Jesus Christ",
    4: "The Fall of Man",
    5: "The Salvation of Man",
    6: "The Ordinances of the Church",
    7: "The Baptism in the Holy Spirit",
    8: "The Initial Physical Evidence of the Baptism in the Holy Spirit",
    9: "Sanctification",
    10: "The Church and Its Mission",
    11: "The Ministry",
    12: "Divine Healing",
    13: "The Blessed Hope",
    14: "The Millennial Reign of Christ",
    15: "The Final Judgment",
    16: "The New Heavens and the New Earth",
}


def ag_truths_accordion(raw: bytes) -> list[dict[str, Any]]:
    """Parse Assemblies of God Statement of Fundamental Truths accordion.

    Each truth is in an `accordion`-class element; headers look like "01. Title"
    followed by body text. Returns `[{number, title, text}]` for truths 1..16.
    """
    tree = parse_html(raw)
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    for node in tree.xpath("//*[contains(@class, 'accordion')]"):
        text = text_of(node)
        m = re.match(r"(\d+)\.\s+(.+)", text)
        if not m:
            continue
        n = int(m.group(1))
        if n in seen or n < 1 or n > 16:
            continue
        seen.add(n)
        title = _AG_TITLES.get(n, "")
        rest = m.group(2).strip()
        body = rest[len(title) :].strip() if title and rest.startswith(title) else rest
        out.append({"number": n, "title": title, "text": body})
    return sorted(out, key=lambda d: d["number"])


def umc_h4_articles(raw: bytes) -> list[dict[str, Any]]:
    """Parse UMC Articles of Religion page.

    Markup: `<h4><a name="anchor"></a>Article N -- Title</h4><p>body</p>` (em dash).
    Returns `[{article, title, text}]`.
    """
    text_blob = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    text_blob = re.sub(r"&mdash;", "-", text_blob)
    text_blob = re.sub(r"&#8212;", "-", text_blob)
    roman_to_int = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8,
        "IX": 9,
        "X": 10,
        "XI": 11,
        "XII": 12,
        "XIII": 13,
        "XIV": 14,
        "XV": 15,
        "XVI": 16,
        "XVII": 17,
        "XVIII": 18,
        "XIX": 19,
        "XX": 20,
        "XXI": 21,
        "XXII": 22,
        "XXIII": 23,
        "XXIV": 24,
        "XXV": 25,
    }
    parts = re.split(
        r"<h4[^>]*>\s*(?:<a[^>]*>\s*</a>)?\s*Article\s+([IVXLCDM]+)\s*-+\s*([^<]+)</h4>",
        text_blob,
        flags=re.IGNORECASE,
    )
    out: list[dict[str, Any]] = []
    for i in range(1, len(parts), 3):
        roman = parts[i].upper().strip()
        if roman not in roman_to_int:
            continue
        title = parts[i + 1].strip().rstrip(":").strip()
        body_html = parts[i + 2]
        body_tree = parse_html(f"<root>{body_html}</root>")
        paras = [text_of(p) for p in body_tree.iter("p")]
        body = " ".join(p for p in paras if p).strip()
        if not body:
            continue
        out.append(
            {
                "article": roman_to_int[roman],
                "title": title,
                "text": body,
            }
        )
    return out


def schleitheim_articles(raw: bytes) -> list[dict[str, Any]]:
    """Parse Schleitheim Confession (anabaptists.org).

    Articles are marked by Roman numeral + period + space, e.g., "I.", "II.",
    "III.", inside bold or other inline markup. We split on these markers and
    extract the surrounding body text.
    """
    text_blob = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    tree = parse_html(text_blob)
    body_text = text_of(tree.xpath("//body")[0]) if tree.xpath("//body") else text_of(tree)
    roman_to_int = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}
    markers: list[tuple[int, int]] = []
    for m in re.finditer(r"(?<!\w)([IV]+)\.\s+(?=[A-Z])", body_text):
        if m.group(1) in roman_to_int:
            markers.append((roman_to_int[m.group(1)], m.start()))
    seen: dict[int, tuple[int, int]] = {}
    for art_num, start in markers:
        if art_num in seen:
            continue
        seen[art_num] = (start, len(body_text))
    sorted_markers = sorted(seen.items(), key=lambda kv: kv[1][0])
    out: list[dict[str, Any]] = []
    for i, (art_num, (start, _)) in enumerate(sorted_markers):
        end = sorted_markers[i + 1][1][0] if i + 1 < len(sorted_markers) else len(body_text)
        body = body_text[start:end]
        body = re.sub(r"^[IV]+\.\s+", "", body, count=1)
        body = body.strip()
        if len(body) < 80:
            continue
        out.append({"article": art_num, "text": body})
    return out


def oca_article_paragraphs(raw: bytes) -> dict[str, Any]:
    """Parse an OCA leaf article page. Returns `{title, text, child_links}`."""
    tree = parse_html(raw)
    title = ""
    h1s = tree.xpath("//h1")
    if h1s:
        title = text_of(h1s[0])
    paras: list[str] = []
    for p in tree.iter("p"):
        parent_classes = " ".join(
            (p.getparent().get("class") or "") if p.getparent() is not None else "" for _ in [0]
        )
        if "footer" in parent_classes.lower():
            continue
        t = text_of(p)
        if not t or len(t) < 40:
            continue
        if t.startswith("Home /") or "All rights reserved" in t:
            continue
        if "Twitter" in t and "Facebook" in t:
            continue
        paras.append(t)
    child_links: list[str] = []
    for li_h3 in tree.xpath("//section[contains(@class,'categories')]//a/@href"):
        child_links.append(li_h3)
    return {"title": title, "text": "\n\n".join(paras), "child_links": child_links}


def vatican_ccc_paragraphs(raw: bytes) -> list[dict[str, Any]]:
    """Parse Vatican.va CCC paragraphs.

    CCC text is numbered (1..2865). Each paragraph appears in markup as
    `<p class=MsoNormal>NUMBER\\n body text...</p>`. We split on those.
    """
    text_blob = raw.decode("latin-1", errors="replace") if isinstance(raw, bytes) else raw
    tree = parse_html(text_blob)
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for p in tree.iter("p"):
        body = text_of(p)
        m = re.match(r"^(\d{1,4})\s+(.+)$", body, re.DOTALL)
        if not m:
            continue
        n = int(m.group(1))
        if n < 1 or n > 2865 or n in seen:
            continue
        seen.add(n)
        text = re.sub(r"\s+", " ", m.group(2)).strip()
        if len(text) < 20:
            continue
        out.append({"paragraph": n, "text": text})
    return out


def vatican_ccc_paragraph_pages(raw: bytes) -> list[str]:
    """Return the list of `__PNN.HTM` paragraph-page filenames from the CCC index."""
    text_blob = raw.decode("latin-1", errors="replace") if isinstance(raw, bytes) else raw
    out: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r"HREF=([A-Z_0-9]+\.HTM)", text_blob, re.IGNORECASE):
        href = m.group(1).upper()
        if href.startswith("__P") and href.endswith(".HTM") and href not in seen:
            seen.add(href)
            out.append(href)
    return out


def vatican_council_paragraphs(raw: bytes) -> list[dict[str, Any]]:
    """Parse a Vatican II conciliar document (Dei Verbum, Lumen Gentium, etc.).

    Paragraphs are numbered (e.g., `1.`, `2.`, ...) inline within `<p>` tags.
    Returns `[{paragraph: int, text: str}]`.
    """
    text_blob = raw.decode("latin-1", errors="replace") if isinstance(raw, bytes) else raw
    tree = parse_html(text_blob)
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for p in tree.iter("p"):
        body = text_of(p)
        m = re.match(r"^(\d{1,3})\.\s+(.+)$", body, re.DOTALL)
        if not m:
            continue
        n = int(m.group(1))
        if n in seen or n < 1 or n > 200:
            continue
        seen.add(n)
        text = re.sub(r"\s+", " ", m.group(2)).strip()
        if len(text) < 20:
            continue
        out.append({"paragraph": n, "text": text})
    return out


def ccel_toc_chapter_links(raw: bytes, base_url: str) -> list[str]:
    """Extract chapter-document links from a CCEL volume TOC."""
    from urllib.parse import urljoin

    tree = parse_html(raw)
    links: list[str] = []
    seen: set[str] = set()
    for a in tree.xpath("//a/@href"):
        if not isinstance(a, str):
            continue
        if a in seen:
            continue
        if a.startswith("javascript") or a.startswith("#"):
            continue
        if not (a.endswith(".html") or ".html#" in a):
            continue
        if "toc" in a.lower():
            continue
        seen.add(a)
        links.append(urljoin(base_url, a))
    return links


def ccel_page_paragraphs(raw: bytes) -> list[str]:
    """Extract substantive prose paragraphs from a CCEL chapter page."""
    tree = parse_html(raw)
    paras: list[str] = []
    for p in tree.iter("p"):
        t = text_of(p)
        if not t or len(t) < 60:
            continue
        if t.lower().startswith(("next", "previous", "back to", "table of contents")):
            continue
        paras.append(t)
    return paras


def stem_publishing_index_links(raw: bytes) -> list[str]:
    """Extract work-document links from a STEM Publishing author index."""
    tree = parse_html(raw)
    out: list[str] = []
    for a in tree.xpath("//a/@href"):
        if not isinstance(a, str):
            continue
        if a.endswith(".html") and "stempublishing.com" not in a and "../" not in a:
            out.append(a)
    return out


def boc_augsburg_paragraphs(raw: bytes) -> list[str]:
    """Extract numbered paragraph text from one BoC augsburg-confession article page."""
    tree = parse_html(raw)
    mains = tree.xpath("//main")
    if not mains:
        return []
    body_paras: list[str] = []
    for p in mains[0].iter("p"):
        t = text_of(p)
        if not t or len(t) < 20:
            continue
        body_paras.append(t)
    return body_paras


def wikisource_article_paragraphs(raw: bytes) -> list[str]:
    """Wikisource HTML: content is in <div class="mw-parser-output">."""
    tree = parse_html(raw)
    nodes = tree.xpath("//div[contains(@class,'mw-parser-output')]")
    if not nodes:
        return main_article_paragraphs(raw)
    body = nodes[0]
    paras: list[str] = []
    for el in body:
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag in {"p", "blockquote"}:
            s = text_of(el)
            if s:
                paras.append(s)
        elif tag in {"ol", "ul"}:
            for li in el.iter("li"):
                s = text_of(li)
                if s:
                    paras.append(s)
        elif tag in {"h2", "h3", "h4"}:
            s = text_of(el)
            if s:
                paras.append(f"# {s}")
    return paras
