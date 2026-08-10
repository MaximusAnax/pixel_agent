#!/usr/bin/env python3
"""Generate a weekly research-progress report draft.

Produces a **narrative-first** meeting draft: executive summary, key
advancements, and deduped experiment findings — not a raw dump of every run.

Data sources:
  * merged pull requests (via `gh`),
  * commits (via `git`),
  * experiment runs (`<stage>/data/babel_outputs/*/summary.md`, deduped by package).

Synthesis:
  * LLM mode (default when ANTHROPIC_API_KEY is set): Claude writes narrative sections.
  * Extractive fallback (`--no-llm` or no key): template narrative from parsed facts.

Usage
-----
    python ops/weekly_report.py                 # last 7 days -> ops/reports/<week>.md
    python ops/weekly_report.py --days 14
    python ops/weekly_report.py --since 2026-06-01
    python ops/weekly_report.py --no-llm        # force extractive narrative
    python ops/weekly_report.py --open-issue    # also open a GH issue
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from llm_client import complete, llm_config
from weekly_report_lib import (
    ExperimentGroup,
    dedupe_runs,
    format_label_line,
    group_to_dict,
    parse_summary_md,
    theme_commits,
)

OPS_DIR = _OPS
REPO_ROOT = OPS_DIR.parent
REPORTS_DIR = OPS_DIR / "reports"
STATE_FILE = OPS_DIR / "state" / "PROJECT_STATE.md"
AGENTS_FILE = REPO_ROOT / "AGENTS.md"

_LLM_SYSTEM = """You draft the narrative sections of a weekly research report for pixelAgent —
a computer-use-agent (CUA) failure-analysis research program on OSWorld.

Given structured facts (PRs, commits, deduped experiment rollups, optional project context),
write ONLY these three Markdown sections with exact H2 headings:

## Executive summary
## Key advancements
## Experiment findings

Rules:
- 3–5 bullets in Executive summary: headline progress, key findings, blockers if any.
- Key advancements: implementations, infra, methodology wins (not file-level churn).
- Experiment findings: one ### subsection per deduped experiment group; include model/package,
  episodes inventoried/labeled, human review queue, adapter gaps, top provisional labels,
  and a one-line "so what". Mark all failure labels as provisional until gold-set calibration.
- Do NOT list every raw run id — use the latest run per package only; mention superseded reruns
  only if it clarifies progress within the week.
- Do not invent experiments, labels, or PRs absent from the facts bundle.
- Be concise: short bullets, scannable prose. No appendix sections."""


def experiment_summary_globs() -> list[Path]:
    paths: list[Path] = []
    for summary in REPO_ROOT.glob("*/data/babel_outputs/*/summary.md"):
        if "external" in summary.parts:
            continue
        paths.append(summary)
    return sorted(paths)


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
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
    code, out, err = _run(
        [
            "gh", "pr", "list", "--state", "merged", "--limit", "100",
            "--search", f"merged:>={since.isoformat()}",
            "--json", "number,title,author,mergedAt,url,labels,additions,deletions",
        ],
        cwd=REPO_ROOT,
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
        cwd=REPO_ROOT,
    )
    if code != 0 or not out:
        return []
    return out.splitlines()


def collect_diffstat(since: dt.date) -> tuple[list[tuple[str, int, int]], int, int]:
    code, out, _ = _run(
        ["git", "log", f"--since={since.isoformat()}", "--no-merges",
         "--numstat", "--pretty=format:"],
        cwd=REPO_ROOT,
    )
    files: dict[str, list[int]] = {}
    if code == 0 and out:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, deleted, path = parts
            if added == "-" or deleted == "-":
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


def collect_parsed_runs(since: dt.date) -> list:
    since_ts = dt.datetime.combine(since, dt.time.min).timestamp()
    parsed = []
    for summary in experiment_summary_globs():
        try:
            mtime = summary.stat().st_mtime
        except OSError:
            continue
        if mtime < since_ts:
            continue
        row = parse_summary_md(summary, REPO_ROOT)
        if row:
            parsed.append(row)
    return parsed


def project_context_snippet(max_chars: int = 1200) -> str:
    for path in (STATE_FILE, AGENTS_FILE):
        if not path.exists():
            continue
        text = path.read_text(errors="replace")
        if "<!-- BEGIN:PROJECT_STATE" in text:
            m = text.split("<!-- BEGIN:PROJECT_STATE", 1)
            if len(m) > 1:
                block = m[1].split("<!-- END:PROJECT_STATE", 1)[0]
                text = block[:max_chars]
                return text.strip()
        return text[:max_chars].strip()
    return ""


def build_facts_bundle(
    since: dt.date,
    today: dt.date,
    prs: list[dict],
    pr_note: str | None,
    commits: list[str],
    files: list[tuple[str, int, int]],
    tot_add: int,
    tot_del: int,
    raw_runs: list,
    groups: list[ExperimentGroup],
) -> dict:
    return {
        "window": {"since": since.isoformat(), "until": today.isoformat()},
        "merged_prs": [
            {
                "number": p["number"],
                "title": p["title"],
                "url": p["url"],
                "author": (p.get("author") or {}).get("login"),
                "merged": (p.get("mergedAt") or "")[:10],
            }
            for p in prs
        ],
        "pr_note": pr_note,
        "commit_count": len(commits),
        "commit_subjects": [" ".join(c.split("\t")[3:]) for c in commits[:25]],
        "themes": theme_commits(commits, prs),
        "lines_changed": {"added": tot_add, "deleted": tot_del, "files": len(files)},
        "experiment_groups": [group_to_dict(g) for g in groups],
        "raw_run_count": len(raw_runs),
        "deduped_group_count": len(groups),
        "project_context": project_context_snippet(),
    }


# --------------------------------------------------------------------------- #
# Narrative synthesis
# --------------------------------------------------------------------------- #
def build_llm_prompt(facts: dict) -> str:
    parts = [
        f"Report window: {facts['window']['since']} → {facts['window']['until']}",
        "",
        "## Structured facts (JSON)",
        json.dumps(facts, indent=2),
    ]
    return "\n".join(parts)


def llm_narrative(cfg: dict, facts: dict) -> str:
    return complete(cfg, _LLM_SYSTEM, build_llm_prompt(facts), max_tokens=4096)


def extractive_narrative(facts: dict, groups: list[ExperimentGroup], prs: list[dict]) -> str:
    L: list[str] = []
    L.append("_Narrative mode: extractive (set ANTHROPIC_API_KEY for richer draft)._")
    L.append("")
    L.append("## Executive summary")

    summary_bullets: list[str] = []
    if prs:
        for pr in prs[-3:]:
            summary_bullets.append(f"Merged [#{pr['number']}]({pr['url']}): {pr['title']}.")
    if groups:
        g = max(groups, key=lambda x: x.latest.episodes_labeled)
        labels = format_label_line(g.latest.label_counts)
        summary_bullets.append(
            f"Latest experiment ({g.stage} / {g.display_name}): "
            f"{g.latest.episodes_inventoried} episodes inventoried, "
            f"{g.latest.episodes_labeled} labeled; top labels: {labels} (provisional)."
        )
    raw = facts.get("raw_run_count", 0)
    deduped = facts.get("deduped_group_count", 0)
    if raw > deduped:
        summary_bullets.append(
            f"{deduped} deduped experiment group(s) from {raw} raw run(s) in this window."
        )
    if facts.get("commit_count"):
        summary_bullets.append(f"{facts['commit_count']} commits across the repo.")
    if not summary_bullets:
        summary_bullets.append("_No major activity recorded in this window._")

    L.append("")
    for b in summary_bullets[:5]:
        L.append(f"- {b}")
    L.append("")

    L.append("## Key advancements")
    L.append("")
    themes = facts.get("themes") or {}
    if themes:
        for theme, items in themes.items():
            if theme == "Other" and len(items) > 8:
                L.append(f"- **{theme}:** {len(items)} commits (see appendix)")
            else:
                sample = "; ".join(items[:3])
                if len(items) > 3:
                    sample += f"; … (+{len(items) - 3} more)"
                L.append(f"- **{theme}:** {sample}")
    else:
        L.append("_No themed commit activity._")
    L.append("")

    L.append("## Experiment findings")
    L.append("")
    if not groups:
        L.append("_No new experiment summaries in this window._")
    else:
        for g in groups:
            latest = g.latest
            L.append(f"### {g.stage} — {g.display_name} (latest: `{latest.run_id}`)")
            L.append("")
            L.append(
                f"- {latest.episodes_inventoried} inventoried · "
                f"{latest.episodes_labeled} labeled · "
                f"{latest.human_review_queue} in human review · "
                f"{latest.adapter_gaps} adapter gaps"
            )
            L.append(f"- Top labels: {format_label_line(latest.label_counts)}")
            if g.superseded_count:
                L.append(
                    f"- _{g.superseded_count} earlier run(s) in this window superseded by latest._"
                )
            if latest.judge_calls is not None:
                cost = f", ~${latest.judge_cost_usd:.2f}" if latest.judge_cost_usd else ""
                L.append(f"- Judge: {latest.judge_calls} calls{cost} (provisional cost estimate)")
            L.append(f"- Summary: `{latest.path}`")
            L.append("- _All labels provisional until gold-set calibration._")
            L.append("")

    return "\n".join(L).rstrip()


# --------------------------------------------------------------------------- #
# Report assembly
# --------------------------------------------------------------------------- #
def render_metrics(
    prs: list[dict],
    commits: list[str],
    files: list[tuple[str, int, int]],
    tot_add: int,
    tot_del: int,
    raw_run_count: int,
    groups: list[ExperimentGroup],
) -> list[str]:
    total_labeled = sum(g.latest.episodes_labeled for g in groups)
    total_inventoried = sum(g.latest.episodes_inventoried for g in groups)
    L = ["## Metrics at a glance", ""]
    L.append(f"- **Merged PRs:** {len(prs)}")
    L.append(f"- **Commits:** {len(commits)}")
    L.append(f"- **Lines changed:** +{tot_add} / -{tot_del} across {len(files)} files")
    L.append(
        f"- **Experiment groups (deduped):** {len(groups)} "
        f"({raw_run_count} raw run(s) in window)"
    )
    if groups:
        L.append(
            f"- **Episodes (latest per group):** {total_inventoried} inventoried, "
            f"{total_labeled} labeled"
        )
    L.append("")
    return L


def render_appendix(
    prs: list[dict],
    pr_note: str | None,
    commits: list[str],
    files: list[tuple[str, int, int]],
    raw_runs: list,
) -> list[str]:
    summary_line = f"Appendix: {len(raw_runs)} raw runs, {len(prs)} PRs, {len(commits)} commits"
    L = [f"<details><summary>{summary_line}</summary>", ""]

    L.append("### Merged pull requests")
    L.append("")
    if pr_note:
        L.append(f"_{pr_note}_")
    elif not prs:
        L.append("_None._")
    else:
        for pr in prs:
            author = (pr.get("author") or {}).get("login", "?")
            merged = (pr.get("mergedAt") or "")[:10]
            L.append(
                f"- [#{pr['number']}]({pr['url']}) **{pr['title']}** "
                f"(@{author}, {merged})"
            )
    L.append("")

    L.append("### Experiment run index")
    L.append("")
    if not raw_runs:
        L.append("_None._")
    else:
        for run in sorted(raw_runs, key=lambda r: r.modified):
            L.append(
                f"- `{run.stage}` / `{run.run_id}` ({run.modified}) — `{run.path}`"
            )
    L.append("")

    L.append("### Top files by churn")
    L.append("")
    if not files:
        L.append("_None._")
    else:
        for path, add, dele in files[:15]:
            L.append(f"- `{path}` (+{add}/-{dele})")
        if len(files) > 15:
            L.append(f"- … and {len(files) - 15} more")
    L.append("")

    L.append("### Commit log")
    L.append("")
    if not commits:
        L.append("_None._")
    else:
        for c in commits:
            sha, an, date, *subj = c.split("\t")
            L.append(f"- `{sha}` {date} {' '.join(subj)} — {an}")
    L.append("")
    L.append("</details>")
    L.append("")
    return L


def render(since: dt.date, today: dt.date, *, use_llm: bool = True) -> str:
    prs, pr_note = collect_merged_prs(since)
    commits = collect_commits(since)
    files, tot_add, tot_del = collect_diffstat(since)
    raw_runs = collect_parsed_runs(since)
    groups = dedupe_runs(raw_runs)

    facts = build_facts_bundle(
        since, today, prs, pr_note, commits, files, tot_add, tot_del, raw_runs, groups
    )

    narrative = ""
    cfg = llm_config() if use_llm else None
    if cfg:
        try:
            print(f"Generating narrative with {cfg['provider']} ({cfg['model']})…", file=sys.stderr)
            narrative = llm_narrative(cfg, facts)
        except Exception as e:
            print(f"LLM narrative failed ({e}); using extractive.", file=sys.stderr)
            narrative = extractive_narrative(facts, groups, prs)
    else:
        if use_llm:
            print("No LLM key; using extractive narrative.", file=sys.stderr)
        narrative = extractive_narrative(facts, groups, prs)

    L: list[str] = []
    L.append(f"# Weekly research report — {iso_week_id(today)}")
    L.append("")
    L.append(
        f"> **DRAFT** auto-generated on {today.isoformat()} covering "
        f"**{since.isoformat()} → {today.isoformat()}**. "
        "Edit freely before/at the meeting; this is a starting point, not the record."
    )
    L.append("")
    L.append(narrative.rstrip())
    L.append("")
    L.extend(render_metrics(prs, commits, files, tot_add, tot_del, len(raw_runs), groups))
    L.extend(render_appendix(prs, pr_note, commits, files, raw_runs))

    L.append("## To discuss at the meeting")
    L.append("")
    L.append("<!-- Add talking points, blockers, and decisions here. -->")
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
        cwd=REPO_ROOT,
    )
    if code == 0:
        print(f"Opened issue: {out}", file=sys.stderr)
    else:
        code2, out2, err2 = _run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            cwd=REPO_ROOT,
        )
        if code2 == 0:
            print(f"Opened issue: {out2}", file=sys.stderr)
        else:
            print(f"Could not open issue: {err or err2}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=7, help="window length in days (default 7)")
    ap.add_argument("--since", help="explicit start date YYYY-MM-DD (overrides --days)")
    ap.add_argument("--no-llm", action="store_true", help="force extractive narrative")
    ap.add_argument("--open-issue", action="store_true", help="also open a GitHub issue")
    ap.add_argument("--stdout-only", action="store_true", help="print only; do not write a file")
    args = ap.parse_args()

    today = dt.date.today()
    since = resolve_since(args)
    body = render(since, today, use_llm=not args.no_llm)
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
