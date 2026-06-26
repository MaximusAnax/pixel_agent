#!/usr/bin/env python3
"""Pull weekly meeting notes from a shared Google Doc into the repo.

Your team already takes notes in Google Docs during Zoom meetings — this script
makes that doc the primary input to the Hermes context loop instead of a local
Markdown template or Whisper transcript.

What it writes
--------------
  ops/meetings/<YYYY-MM-DD>/gdoc_notes.md   — text pulled from the Doc
  ops/meetings/<YYYY-MM-DD>/meta.json       — doc id, url, pull timestamp

Setup (one-time)
----------------
1. Enable Google Docs API + Google Drive API in a GCP project.
2. Create a service account; download the JSON key to
   ops/config/gdoc-service-account.json (git-ignored).
3. Share the meeting notes Google Doc with the service account email (Viewer).
4. cp ops/config/meetings.env.example ops/config/meetings.env
   Set MEETING_GDOC_ID to the doc id or URL.

Usage
-----
    python ops/pull_gdoc_notes.py --date 2026-06-27
    python ops/pull_gdoc_notes.py --doc-id https://docs.google.com/document/d/ABC.../edit
    python ops/pull_gdoc_notes.py --date 2026-06-27 --section-only   # rolling doc: one date's section
    python ops/pull_gdoc_notes.py --date 2026-06-27 --force

After pulling, run: python ops/synthesize_state.py
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
from meeting_lib import (
    CONFIG_DIR,
    ensure_meeting_dir,
    load_meetings_env,
    parse_doc_id,
    write_meta,
)

SCOPES = ("https://www.googleapis.com/auth/documents.readonly",)


def _load_credentials(sa_file: Path):
    try:
        from google.oauth2 import service_account
    except ImportError:
        print(
            "Google API libraries not installed. Run:\n"
            "    pip install google-api-python-client google-auth\n",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if not sa_file.exists():
        print(
            f"Service account file not found: {sa_file}\n"
            "See ops/config/meetings.env.example and docs/meeting_notes_workflow.md.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return service_account.Credentials.from_service_account_file(
        str(sa_file), scopes=SCOPES
    )


def fetch_doc_text(doc_id: str, sa_file: Path) -> tuple[str, str]:
    from googleapiclient.discovery import build

    creds = _load_credentials(sa_file)
    service = build("docs", "v1", credentials=creds, cache_discovery=False)
    doc = service.documents().get(documentId=doc_id).execute()
    title = doc.get("title", doc_id)
    body = doc.get("body", {}).get("content", [])
    parts: list[str] = []
    for element in body:
        para = element.get("paragraph")
        if not para:
            continue
        for el in para.get("elements", []):
            tr = el.get("textRun")
            if tr and tr.get("content"):
                parts.append(tr["content"])
    return title, "".join(parts).strip()


def extract_section(full_text: str, date: dt.date) -> str | None:
    """Best-effort: pull one meeting's section from a rolling doc.

    Looks for a line that contains the ISO date or a long-form date, then returns
    text until the next date-like heading or a horizontal rule of dashes.
    """
    iso = date.isoformat()
    long_form = date.strftime("%B %-d, %Y") if sys.platform != "win32" else date.strftime("%B %d, %Y").replace(" 0", " ")
    long_form_no_comma = long_form.replace(",", "")
    patterns = [
        re.compile(rf"^\s*#{{1,3}}\s+.*{re.escape(iso)}", re.I | re.M),
        re.compile(rf"^\s*#{{1,3}}\s+.*{re.escape(long_form)}", re.I | re.M),
        re.compile(rf"^\s*#{{1,3}}\s+.*{re.escape(long_form_no_comma)}", re.I | re.M),
        re.compile(rf"^\s*{re.escape(iso)}\s*$", re.M),
    ]
    start = None
    for pat in patterns:
        m = pat.search(full_text)
        if m:
            start = m.start()
            break
    if start is None:
        return None
    rest = full_text[start:]
    # Stop at next major date heading (rough heuristic)
    next_heading = re.search(
        r"\n#{1,3}\s+(?:\d{4}-\d{2}-\d{2}|[A-Z][a-z]+ \d{1,2}, \d{4})",
        rest[1:],
    )
    if next_heading:
        rest = rest[: next_heading.start() + 1]
    return rest.strip()


def render_markdown(
    date: dt.date,
    title: str,
    doc_id: str,
    body: str,
    *,
    section_only: bool,
    full_title: str,
) -> str:
    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    lines = [
        f"# Meeting notes — {date.isoformat()}",
        "",
        f"> Pulled from Google Doc **{full_title}** on {dt.date.today().isoformat()}.",
        f"> Source: [{doc_id}]({url})",
    ]
    if section_only:
        lines.append("> Section extracted for this meeting date from a rolling doc.")
    lines.extend(["", body, ""])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="meeting date YYYY-MM-DD")
    ap.add_argument("--doc-id", help="Google Doc id or URL (else MEETING_GDOC_ID from meetings.env)")
    ap.add_argument(
        "--service-account",
        help="path to service account JSON (else GOOGLE_SERVICE_ACCOUNT_FILE / meetings.env)",
    )
    ap.add_argument(
        "--section-only",
        action="store_true",
        help="extract only this date's section from a rolling doc (best-effort)",
    )
    ap.add_argument("--force", action="store_true", help="overwrite existing gdoc_notes.md")
    args = ap.parse_args()

    date = dt.date.fromisoformat(args.date)
    env = load_meetings_env()
    doc_id = parse_doc_id(args.doc_id or env.get("MEETING_GDOC_ID", ""))
    if not doc_id:
        print("No doc id. Pass --doc-id or set MEETING_GDOC_ID in ops/config/meetings.env", file=sys.stderr)
        return 1

    sa_path = Path(
        args.service_account
        or env.get("GOOGLE_SERVICE_ACCOUNT_FILE", "ops/config/gdoc-service-account.json")
    ).expanduser()
    if not sa_path.is_absolute():
        candidate = (_OPS.parent / sa_path).resolve()
        sa_path = candidate if candidate.exists() else (_OPS / sa_path.name).resolve()

    meeting = ensure_meeting_dir(date)
    out_path = meeting / "gdoc_notes.md"
    if out_path.exists() and not args.force:
        print(f"{out_path} exists (use --force to overwrite).", file=sys.stderr)
        return 1

    print(f"Fetching Google Doc {doc_id}…", file=sys.stderr)
    full_title, full_text = fetch_doc_text(doc_id, sa_path)
    body = full_text
    section_only = args.section_only
    if section_only:
        extracted = extract_section(full_text, date)
        if extracted:
            body = extracted
        else:
            print(
                "Warning: --section-only but no date heading found; using full doc.",
                file=sys.stderr,
            )
            section_only = False

    md = render_markdown(date, full_title, doc_id, body, section_only=section_only, full_title=full_title)
    out_path.write_text(md)
    write_meta(
        meeting,
        gdoc_id=doc_id,
        gdoc_url=f"https://docs.google.com/document/d/{doc_id}/edit",
        gdoc_title=full_title,
        pulled_at=dt.datetime.now(dt.timezone.utc).isoformat(),
    )
    print(f"Wrote {out_path} ({len(body)} chars)", file=sys.stderr)
    print("Next: python ops/synthesize_state.py", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
