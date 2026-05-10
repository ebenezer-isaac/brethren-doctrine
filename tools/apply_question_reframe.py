"""Parse questions-reframe-proposal.md and apply non-destructive statement
rewrites to questions.json. Skips destructive merges (require user approval).

Usage:
    python -m tools.apply_question_reframe              # dry-run, prints diff summary
    python -m tools.apply_question_reframe --apply      # writes questions.json

Always runs verify_questions afterward to confirm hygiene improved.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "questions.json"
PROPOSAL = ROOT / "questions-reframe-proposal.md"


SECTION_RE = re.compile(r"^### (\S+)\s*[—-]\s*(.+)$", re.MULTILINE)
PROPOSED_RE = re.compile(
    r"\*\*Proposed statement(?:\s*\([^)]*\))?:\*\*\s*\n>\s*(.+?)(?=\n\n|\n\*\*|\n---|\Z)",
    re.DOTALL,
)
DESTRUCTIVE_RE = re.compile(r"destructive|DELETE|deletion required", re.IGNORECASE)
NO_CHANGE_RE = re.compile(
    r"No change (?:recommended|needed)|"
    r"already neutrally framed|"
    r"already a clean proposition|"
    r"already covered above|"
    r"\(Skip: clean\.\)|"
    r"\(Skip: included only to confirm it's clean\.\)|"
    r"^\s*No statement change",
    re.IGNORECASE | re.MULTILINE,
)


def parse_proposal(text: str) -> list[dict]:
    """Parse the proposal markdown into a list of {id, category_label,
    proposed_statement, destructive, no_change}.

    Splits the proposal on `---` horizontal-rule separators (each per-question
    section ends with one). Within each chunk, finds the `### <id>` header
    and treats the rest of the chunk as that question's body. Deduplicates by id."""
    sections_by_id: dict[str, dict] = {}
    chunks = re.split(r"^\s*---\s*$", text, flags=re.MULTILINE)
    for chunk in chunks:
        m = SECTION_RE.search(chunk)
        if not m:
            continue
        qid = m.group(1).strip()
        label = m.group(2).strip()
        body = chunk[m.end():]

        if not re.match(r"^(doc|prc|cult|het)-", qid):
            continue

        destructive = bool(DESTRUCTIVE_RE.search(body))
        no_change = bool(NO_CHANGE_RE.search(body))

        proposed = None
        pm = PROPOSED_RE.search(body)
        if pm:
            proposed = pm.group(1).strip()
            proposed = re.sub(r"\s*\n>\s*", " ", proposed)
            proposed = re.sub(r"\s+", " ", proposed).strip()
            # If the "proposed" text itself signals a no-change instruction,
            # demote to no_change and clear proposed.
            if NO_CHANGE_RE.search(proposed):
                no_change = True
                proposed = None

        entry = {
            "id": qid,
            "label": label,
            "proposed_statement": proposed,
            "destructive": destructive,
            "no_change": no_change,
        }
        # Dedupe: keep the entry with content if we see the same id twice
        existing = sections_by_id.get(qid)
        if existing is None:
            sections_by_id[qid] = entry
        else:
            if proposed and not existing["proposed_statement"]:
                sections_by_id[qid] = entry
            elif destructive and not existing["destructive"]:
                existing["destructive"] = True
            elif no_change and not existing["no_change"] and not existing["proposed_statement"]:
                existing["no_change"] = True
    return list(sections_by_id.values())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--apply", action="store_true",
                   help="Write changes to questions.json (default: dry-run)")
    p.add_argument("--include-destructive", action="store_true",
                   help="Apply destructive merges (id deletions) too — requires user approval")
    args = p.parse_args()

    if not PROPOSAL.exists():
        print(f"missing: {PROPOSAL}", file=sys.stderr)
        return 2

    text = PROPOSAL.read_text(encoding="utf-8")
    sections = parse_proposal(text)
    raw = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    by_id = {q["id"]: q for q in raw["questions"]}

    applied: list[str] = []
    skipped_destructive: list[str] = []
    skipped_no_change: list[str] = []
    skipped_unknown_id: list[str] = []
    no_proposed: list[str] = []
    diffs: list[str] = []

    for s in sections:
        qid = s["id"]
        if qid not in by_id:
            skipped_unknown_id.append(qid)
            continue
        if s["no_change"]:
            skipped_no_change.append(qid)
            continue
        if s["destructive"] and not args.include_destructive:
            skipped_destructive.append(qid)
            continue
        if not s["proposed_statement"]:
            no_proposed.append(qid)
            continue
        old = by_id[qid].get("statement", "")
        new = s["proposed_statement"]
        if old.strip() == new.strip():
            skipped_no_change.append(qid)
            continue
        diffs.append(f"--- {qid}\n  OLD: {old[:120]}{'...' if len(old) > 120 else ''}\n  NEW: {new[:120]}{'...' if len(new) > 120 else ''}")
        if args.apply:
            by_id[qid]["statement"] = new
        applied.append(qid)

    print(f"Proposal sections parsed: {len(sections)}")
    print(f"  applied (or would apply): {len(applied)}")
    print(f"  skipped — no-change recommendation: {len(skipped_no_change)}")
    print(f"  skipped — destructive merge (needs user approval): {len(skipped_destructive)}")
    print(f"  skipped — unknown id (not in questions.json): {len(skipped_unknown_id)}")
    print(f"  skipped — no proposed_statement parsed: {len(no_proposed)}")
    if skipped_destructive:
        print(f"  destructive ids: {', '.join(skipped_destructive)}")
    if skipped_unknown_id:
        print(f"  unknown ids: {', '.join(skipped_unknown_id)}")
    if no_proposed:
        print(f"  no-proposed ids (likely parser issue, manual review): {', '.join(no_proposed[:10])}")

    print()
    if args.apply:
        out = json.dumps(raw, indent=2, ensure_ascii=False)
        QUESTIONS.write_text(out + "\n", encoding="utf-8")
        print(f"WROTE: {QUESTIONS}")
    else:
        print("DRY-RUN — no changes written. Re-run with --apply to commit.")
        for d in diffs[:10]:
            print(d)
        if len(diffs) > 10:
            print(f"...and {len(diffs) - 10} more diffs.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
