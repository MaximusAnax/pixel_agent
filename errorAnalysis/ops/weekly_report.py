#!/usr/bin/env python3
"""Generate a weekly research-progress report draft.

The report summarizes everything that changed in the repo over a time window so
the team walks into the weekly meeting with a draft instead of building one by
hand. It pulls:

  * merged pull requests (via the `gh` CLI, when available),
  * commits and an aggregated file-change diffstat (via `git`),
  * new experiment runs (any fresh `summary.md` under data/babel_outputs/).

Design notes
------------
* Pure stdlib + the `git`/`gh` CLIs, so it runs unchanged in GitHub Actions
  (where `gh` is preinstalled and authenticated via GITHUB_TOKEN) and locally.
* It degrades gracefully: if `gh` is missing/unauthenticated, the PR section is
  skipped with a note rather than failing.
* Output is a Markdown draft written to ops/reports/<ISO-week>.md and echoed to
  stdout. Pass --open-issue to also file a GitHub issue with the same body.

Usage
-----
    python ops/weekly_report.py                 # last 7 days -> ops/reports/<week>.md
    python ops/weekly_report.py --days 14
    python ops/weekly_report.py --since 2026-06-01
    python ops/weekly_report.py --open-issue    # also open a GH issue
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

# ops/ -> errorAnalysis/ (the repo's research root and Hermes working dir)
OPS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = OPS_DIR.parent
REPORTS_DIR = OPS_DIR / "reports"
BABEL_OUTPUTS = PROJECT_ROOT / "data" / "babel_outputs"


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a command, returning (returncode, stdout, stderr). Never raises."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {' '.join(cmd)}"


def iso_week_id(date: dt.date) -> str:
    year, week, _ = date.isocalendar()
    return f"{year}-W{week:02d}"


def resolve_since(args: argparse.Namespace) -> dt.date:
    if args.since:
        return dt.date.fromisoformat(args.since)
    return dt.date.today() - dt.timedelta(days=args.days)


# --------------------------------------------------------------------------- #
# Data collection
# --------------------------------------------------------------------------- #
def collect_merged_prs(since: dt.date) -> tuple[list[dict], str | None]:
    """Return (prs, note). `note` is set when PRs could not be fetched."""
    code, out, err = _run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "merged",
            "--limit",
            "100",
            "--search",
            f"merged:>={since.isoformat()}",
            "--json",
            "number,title,author,mergedAt,url,labels,additions,deletions",
        ],
        cwd=PROJECT_ROOT,
    )
    if code != 0:
        return [], f"`gh` unavailable or not authenticated ({err or 'see logs'}); PR section skipped."
    try:
        prs = json.loads(out) if out else []
    except json.JSONDecodeError:
        return [], "Could not parse `gh` output; PR section skipped."
    prs.sort(key=lambda p: p.get("mergedAt", ""))
    return prs, None


def collect_commits(since: dt.date) -> list[str]:
    code, out, _ = _run(
        ["git", "log", f"--since={since.isoformat()}", "--no-merges",
         "--pretty=format:%h\t%an\t%ad\t%s", "--date=short"],
        cwd=PROJECT_ROOT,
    )
    if code != 0 or not out:
        return []
    return out.splitlines()


def collect_diffstat(since: dt.date) -> tuple[list[tuple[str, int, int]], int, int]:
    """Aggregate per-file (path, added, deleted) over the window via numstat."""
    code, out, _ = _run(
        ["git", "log", f"--since={since.isoformat()}", "--no-merges",
         "--numstat", "--pretty=format:"],
        cwd=PROJECT_ROOT,
    )
    files: dict[str, list[int]] = {}
    if code == 0 and out:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, deleted, path = parts
            if added == "-" or deleted == "-":  # binary file
                continue
            entry = files.setdefault(path, [0, 0])
            entry[0] += int(added)
            entry[1] += int(deleted)
    ranked = sorted(
        ((p, a, d) for p, (a, d) in files.items()),
        key=lambda t: t[1] + t[2],
        reverse=True,
    )
    total_add = sum(a for _, a, _ in ranked)
    total_del = sum(d for _, _, d in ranked)
    return ranked, total_add, total_del


def collect_experiment_runs(since: dt.date) -> list[dict]:
    """Find experiment run summaries created/updated within the window."""
    if not BABEL_OUTPUTS.exists():
        return []
    since_ts = dt.datetime.combine(since, dt.time.min).timestamp()
    runs: list[dict] = []
    for summary in sorted(BABEL_OUTPUTS.glob("*/summary.md")):
        try:
            mtime = summary.stat().st_mtime
        except OSError:
            continue
        if mtime < since_ts:
            continue
        head = summary.read_text(errors="replace").strip().splitlines()
        preview = "\n".join(head[:12])
        runs.append(
            {
                "run_id": summary.parent.name,
                "modified": dt.date.fromtimestamp(mtime).isoformat(),
                "preview": preview,
            }
        )
    return runs


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render(since: dt.date, today: dt.date) -> str:
    prs, pr_note = collect_merged_prs(since)
    commits = collect_commits(since)
    files, tot_add, tot_del = collect_diffstat(since)
    runs = collect_experiment_runs(since)

    L: list[str] = []
    L.append(f"# Weekly research report — {iso_week_id(today)}")
    L.append("")
    L.append(f"> **DRAFT** auto-generated on {today.isoformat()} covering "
             f"**{since.isoformat()} → {today.isoformat()}**. "
             "Edit freely before/at the meeting; this is a starting point, not the record.")
    L.append("")

    # At-a-glance
    L.append("## At a glance")
    L.append("")
    L.append(f"- **Merged PRs:** {len(prs)}")
    L.append(f"- **Commits:** {len(commits)}")
    L.append(f"- **Lines changed:** +{tot_add} / -{tot_del} across {len(files)} files")
    L.append(f"- **New experiment runs:** {len(runs)}")
    L.append("")

    # Merged PRs
    L.append("## Merged pull requests")
    L.append("")
    if pr_note:
        L.append(f"_{pr_note}_")
    elif not prs:
        L.append("_No PRs merged in this window._")
    else:
        for pr in prs:
            author = (pr.get("author") or {}).get("login", "?")
            labels = ", ".join(lbl["name"] for lbl in pr.get("labels", [])) or "—"
            merged = (pr.get("mergedAt") or "")[:10]
            L.append(
                f"- [#{pr['number']}]({pr['url']}) **{pr['title']}** "
                f"(@{author}, {merged}, +{pr.get('additions', 0)}/-{pr.get('deletions', 0)}, labels: {labels})"
            )
    L.append("")

    # Code changes
    L.append("## Code changes (top files by churn)")
    L.append("")
    if not files:
        L.append("_No tracked file changes in this window._")
    else:
        for path, add, dele in files[:15]:
            L.append(f"- `{path}` (+{add}/-{dele})")
        if len(files) > 15:
            L.append(f"- … and {len(files) - 15} more files")
    L.append("")

    # Experiments
    L.append("## Experiments & runs")
    L.append("")
    if not runs:
        L.append("_No new `data/babel_outputs/*/summary.md` in this window._")
    else:
        for run in runs:
            L.append(f"### `{run['run_id']}` ({run['modified']})")
            L.append("")
            L.append("```")
            L.append(run["preview"])
            L.append("```")
            L.append("")

    # Commit log (collapsed)
    L.append("## Commit log")
    L.append("")
    if not commits:
        L.append("_No commits in this window._")
    else:
        L.append("<details><summary>{} commits</summary>".format(len(commits)))
        L.append("")
        for c in commits:
            sha, an, date, *subj = c.split("\t")
            L.append(f"- `{sha}` {date} {' '.join(subj)} — {an}")
        L.append("")
        L.append("</details>")
    L.append("")

    # Human-owned sections (the report invites discussion, doesn't replace it)
    L.append("## To discuss at the meeting")
    L.append("")
    L.append("<!-- The bot fills the facts above. Add talking points, blockers, and decisions here. -->")
    L.append("- ")
    L.append("")
    L.append("## Next week's targets")
    L.append("")
    L.append("- ")
    L.append("")

    return "\n".join(L)


def maybe_open_issue(body: str, week: str) -> None:
    title = f"Weekly research report — {week}"
    code, out, err = _run(
        ["gh", "issue", "create", "--title", title, "--body", body, "--label", "weekly-report"],
        cwd=PROJECT_ROOT,
    )
    if code == 0:
        print(f"Opened issue: {out}", file=sys.stderr)
    else:
        # Label may not exist; retry without it.
        code2, out2, err2 = _run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            cwd=PROJECT_ROOT,
        )
        if code2 == 0:
            print(f"Opened issue: {out2}", file=sys.stderr)
        else:
            print(f"Could not open issue: {err or err2}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=7, help="window length in days (default 7)")
    ap.add_argument("--since", help="explicit start date YYYY-MM-DD (overrides --days)")
    ap.add_argument("--open-issue", action="store_true", help="also open a GitHub issue")
    ap.add_argument("--stdout-only", action="store_true", help="print only; do not write a file")
    args = ap.parse_args()

    today = dt.date.today()
    since = resolve_since(args)
    body = render(since, today)
    week = iso_week_id(today)

    if not args.stdout_only:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = REPORTS_DIR / f"{week}.md"
        out_path.write_text(body)
        print(f"Wrote {out_path}", file=sys.stderr)

    print(body)

    if args.open_issue:
        maybe_open_issue(body, week)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
