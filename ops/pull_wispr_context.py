#!/usr/bin/env python3
"""Optional supplement: pull Wispr Flow dictations from the local desktop database.

Wispr Flow does not push into Google Docs automatically — it inserts text where
your cursor is. During meetings you likely dictate *into* the Google Doc, so the
Doc remains the source of truth. This script captures *additional* Wispr
dictations during the meeting window (Scratchpad, side comments in Slack/Cursor,
etc.) from the local SQLite history.

Requires Wispr Flow desktop with Cloud Sync (history stored locally in flow.sqlite).
No official bulk-export API for individuals; this reads the same local DB used by
community tools like WisprMCP (https://github.com/pedramamini/WisprMCP).

Usage
-----
    python ops/pull_wispr_context.py --date 2026-06-27
    python ops/pull_wispr_context.py --date 2026-06-27 --start 11:00 --end 12:45
    python ops/pull_wispr_context.py --date 2026-06-27 --apps Google,Chrome,Cursor
"""
from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))
from meeting_lib import ensure_meeting_dir, load_meetings_env, write_meta

DEFAULT_DB = Path.home() / "Library/Application Support/Wispr Flow/flow.sqlite"


def parse_hm(s: str) -> dt.time:
    h, m = s.split(":")
    return dt.time(int(h), int(m))


def query_history(
    db_path: Path,
    start: dt.datetime,
    end: dt.datetime,
    apps: list[str] | None,
) -> list[tuple[str, str, str]]:
    if not db_path.exists():
        raise FileNotFoundError(f"Wispr database not found: {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(History)")}
    except sqlite3.Error as e:
        conn.close()
        raise RuntimeError(f"Cannot read Wispr History table: {e}") from e

    text_col = "formattedText" if "formattedText" in cols else "text" if "text" in cols else None
    if not text_col:
        conn.close()
        raise RuntimeError(f"Unknown Wispr History schema; columns: {sorted(cols)}")

    ts_col = "timestamp" if "timestamp" in cols else "createdAt" if "createdAt" in cols else None
    if not ts_col:
        conn.close()
        raise RuntimeError("No timestamp column in Wispr History table")

    app_col = "app" if "app" in cols else None

    # Wispr stores UTC unix timestamps (float or int)
    start_ts = start.timestamp()
    end_ts = end.timestamp()

    app_expr = app_col if app_col else "''"
    sql = (
        f"SELECT {ts_col} AS ts, {app_expr} AS app, {text_col} AS text "
        f"FROM History WHERE {ts_col} >= ? AND {ts_col} <= ? ORDER BY {ts_col}"
    )
    rows = conn.execute(sql, (start_ts, end_ts)).fetchall()
    conn.close()

    out: list[tuple[str, str, str]] = []
    for row in rows:
        app = row["app"] or "unknown"
        if apps and not any(a.lower() in app.lower() for a in apps):
            continue
        text = (row["text"] or "").strip()
        if not text:
            continue
        ts = float(row["ts"])
        when = dt.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        out.append((when, app, text))
    return out


def render(date: dt.date, entries: list[tuple[str, str, str]], window: str) -> str:
    lines = [
        f"# Wispr Flow supplement — {date.isoformat()}",
        "",
        f"> Local dictation history during **{window}**. Supplementary to "
        "`gdoc_notes.md`; not a substitute for the shared Google Doc.",
        "",
    ]
    if not entries:
        lines.append("_No Wispr dictations in this window (or app filter excluded all)._")
    else:
        for when, app, text in entries:
            lines.append(f"- **[{when}]** ({app}) {text}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", required=True, help="meeting date YYYY-MM-DD")
    ap.add_argument("--start", help="local start time HH:MM (default MEETING_START or 11:00)")
    ap.add_argument("--end", help="local end time HH:MM (default MEETING_END or 12:30)")
    ap.add_argument("--db", help="path to flow.sqlite (default WISPR_DB_PATH or Mac default)")
    ap.add_argument(
        "--apps",
        help="comma-separated app name filters (default: no filter; e.g. Google,Chrome,Cursor)",
    )
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    env = load_meetings_env()
    date = dt.date.fromisoformat(args.date)
    start_t = parse_hm(args.start or env.get("MEETING_START", "11:00"))
    end_t = parse_hm(args.end or env.get("MEETING_END", "12:30"))
    start = dt.datetime.combine(date, start_t)
    end = dt.datetime.combine(date, end_t)
    if end <= start:
        print("--end must be after --start", file=sys.stderr)
        return 1

    db_path = Path(args.db or env.get("WISPR_DB_PATH", str(DEFAULT_DB))).expanduser()
    apps = [a.strip() for a in args.apps.split(",")] if args.apps else None

    meeting = ensure_meeting_dir(date)
    out_path = meeting / "wispr_supplement.md"
    if out_path.exists() and not args.force:
        print(f"{out_path} exists (use --force).", file=sys.stderr)
        return 1

    try:
        entries = query_history(db_path, start, end, apps)
    except FileNotFoundError as e:
        print(f"{e}\nIs Wispr Flow installed on this Mac?", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    window = f"{start_t.strftime('%H:%M')}–{end_t.strftime('%H:%M')} local"
    out_path.write_text(render(date, entries, window))
    write_meta(meeting, wispr_pulled_at=dt.datetime.now(dt.timezone.utc).isoformat())
    print(f"Wrote {out_path} ({len(entries)} entries)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
