#!/usr/bin/env python3
"""Format raw Google Doc meeting notes into structured notes.md (Anthropic LLM).

After `pull_gdoc_notes.py`, the pulled `gdoc_notes.md` is often messy — especially
from a rolling doc with multiple weeks. This script uses Claude to produce
`notes.md` with the standard headings the synthesizer and Hermes expect.

Requires ANTHROPIC_API_KEY (or set in ops/config/meetings.env).

Usage
-----
    python ops/format_meeting_notes.py --date 2026-06-24
    python ops/format_meeting_notes.py --date 2026-06-24 --dry-run
    python ops/format_meeting_notes.py --date 2026-06-24 --force
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from llm_client import complete, llm_config
from meeting_lib import ensure_meeting_dir, meeting_dir

_FORMAT_SYSTEM = """You format messy research meeting notes from a Google Doc into clean Markdown for the pixelAgent program (computer-use agents / CUA research).

Output ONLY Markdown. Use these exact H2 section headings (omit a section if truly empty):

## Attendees
## Technologies discussed
## Decisions made
## Feedback / critiques
## Ideas considered
## Ideas & research directions
## Action items
## Open questions

Rules:
- Focus on the meeting date specified in the user message. Rolling docs may contain many weeks — extract the most recent/relevant session for that date; do not dump unrelated historical weeks.
- Deduplicate repeated bullets; preserve paper titles, arXiv/GitHub links, model names, and cluster names (Babel, Bridges, Slurm).
- Action items: `- [ ] @owner — task` when the owner is clear (Abdoul, Raghav, Amaad, Matt).
- Separate **decisions** from **ideas**; tag provisional items when the source is ambiguous.
- Do not invent facts absent from the source text.
- Keep each section scannable: short bullets, not long paragraphs."""

_HEADING_RE = re.compile(r"^## Attendees\s*$", re.M)


def strip_gdoc_header(text: str) -> str:
    """Remove pull_gdoc_notes.py boilerplate header."""
    body = re.sub(r"^# Meeting notes.*?\n\n", "", text, count=1, flags=re.S)
    body = re.sub(r"^>.*\n", "", body, flags=re.M)
    return body.strip()


def format_notes_body(meeting_date: dt.date, gdoc_text: str, cfg: dict) -> str:
    body = strip_gdoc_header(gdoc_text)
    user = (
        f"Meeting date to structure: **{meeting_date.isoformat()}**\n\n"
        f"Raw Google Doc export:\n\n{body}"
    )
    out = complete(cfg, _FORMAT_SYSTEM, user, max_tokens=8192)
    if not _HEADING_RE.search(out):
        out = f"# Meeting notes — {meeting_date.isoformat()}\n\n{out}"
    elif not out.startswith("# Meeting notes"):
        out = f"# Meeting notes — {meeting_date.isoformat()}\n\n{out}"
    return out.rstrip() + "\n"


def format_meeting(meeting: Path, cfg: dict, *, force: bool = False, dry_run: bool = False) -> bool:
    gdoc = meeting / "gdoc_notes.md"
    notes = meeting / "notes.md"
    if not gdoc.exists():
        print(f"Skip {meeting.name}: no gdoc_notes.md", file=sys.stderr)
        return False
    if notes.exists() and not force:
        print(f"Skip {meeting.name}: notes.md exists (use --force)", file=sys.stderr)
        return False

    date = dt.date.fromisoformat(meeting.name)
    text = format_notes_body(date, gdoc.read_text(errors="replace"), cfg)
    if dry_run:
        print(f"===== {meeting.name}/notes.md (preview) =====\n")
        print(text)
        return True
    notes.write_text(text)
    print(f"Wrote {notes}", file=sys.stderr)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", required=True, help="meeting folder date YYYY-MM-DD")
    ap.add_argument("--force", action="store_true", help="overwrite existing notes.md")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = llm_config()
    if not cfg:
        print(
            "No LLM configured. Set ANTHROPIC_API_KEY in the environment or "
            "ops/config/meetings.env (see ops/config/meetings.env.example).",
            file=sys.stderr,
        )
        return 2
    if cfg["provider"] != "anthropic":
        print(
            f"Warning: provider is {cfg['provider']}; Anthropic is recommended for formatting.",
            file=sys.stderr,
        )

    meeting = ensure_meeting_dir(dt.date.fromisoformat(args.date))
    print(
        f"Formatting with {cfg['provider']} model {cfg['model']}…",
        file=sys.stderr,
    )
    ok = format_meeting(meeting, cfg, force=args.force, dry_run=args.dry_run)
    if ok and not args.dry_run:
        print("Next: python ops/synthesize_state.py", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
