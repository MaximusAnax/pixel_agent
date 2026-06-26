"""Helpers for ops/weekly_report.py — parse runs, dedupe, theme commits."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedSummary:
    run_id: str
    stage: str
    path: str
    modified: str
    model_id: str
    package: str
    episodes_inventoried: int
    episodes_labeled: int
    human_review_queue: int
    adapter_gaps: int
    label_counts: dict[str, int] = field(default_factory=dict)
    judge_calls: int | None = None
    judge_cost_usd: float | None = None


@dataclass
class ExperimentGroup:
    stage: str
    package: str
    model_id: str
    latest: ParsedSummary
    prior_in_window: list[ParsedSummary] = field(default_factory=list)

    @property
    def superseded_count(self) -> int:
        return len(self.prior_in_window)

    @property
    def display_name(self) -> str:
        slug = self.latest.run_id.split("_", 2)[-1] if "_" in self.latest.run_id else self.latest.run_id
        if len(slug) > 60:
            slug = slug[:57] + "…"
        return slug


def _parse_int_after(label: str, line: str) -> int | None:
    if label.lower() not in line.lower():
        return None
    m = re.search(r":\s*(\d+)", line)
    return int(m.group(1)) if m else None


def parse_summary_md(summary_path: Path, repo_root: Path) -> ParsedSummary | None:
    try:
        text = summary_path.read_text(errors="replace")
        mtime = summary_path.stat().st_mtime
    except OSError:
        return None

    rel = summary_path.relative_to(repo_root)
    stage = rel.parts[0]
    run_id = summary_path.parent.name

    model_id = ""
    package = ""
    episodes_inventoried = 0
    episodes_labeled = 0
    human_review_queue = 0
    adapter_gaps = 0
    label_counts: dict[str, int] = {}
    judge_calls: int | None = None
    judge_cost_usd: float | None = None

    in_labels = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("# HF OSWorld Failure Analysis:"):
            model_id = line.split(":", 1)[-1].strip()
            continue
        if line.startswith("- Package:"):
            package = line.split("`")[1] if "`" in line else line.split(":", 1)[-1].strip()
            continue
        if v := _parse_int_after("Episodes inventoried", line):
            episodes_inventoried = v
            continue
        if v := _parse_int_after("Episodes analyzed/sample-labeled", line):
            episodes_labeled = v
            continue
        if v := _parse_int_after("Human review queue", line):
            human_review_queue = v
            continue
        if v := _parse_int_after("Adapter gaps", line):
            adapter_gaps = v
            continue
        if line == "## Primary Label Counts":
            in_labels = True
            continue
        if line.startswith("## ") and in_labels:
            in_labels = False
        if in_labels and line.startswith("- ") and ":" in line:
            parts = line[2:].rsplit(":", 1)
            if len(parts) == 2:
                try:
                    label_counts[parts[0].strip()] = int(parts[1].strip())
                except ValueError:
                    pass
            continue
        if line.startswith("- Judge calls:"):
            m = re.search(r":\s*(\d+)", line)
            if m:
                judge_calls = int(m.group(1))
            continue
        if line.startswith("- Estimated USD:"):
            m = re.search(r"\$([\d.]+)", line)
            if m:
                judge_cost_usd = float(m.group(1))

    if not package and not model_id:
        return None

    return ParsedSummary(
        run_id=run_id,
        stage=stage,
        path=str(rel),
        modified=dt.date.fromtimestamp(mtime).isoformat(),
        model_id=model_id or package,
        package=package or model_id,
        episodes_inventoried=episodes_inventoried,
        episodes_labeled=episodes_labeled,
        human_review_queue=human_review_queue,
        adapter_gaps=adapter_gaps,
        label_counts=label_counts,
        judge_calls=judge_calls,
        judge_cost_usd=judge_cost_usd,
    )


def dedupe_runs(parsed: list[ParsedSummary]) -> list[ExperimentGroup]:
    """Group by (stage, package); keep latest mtime per group."""
    buckets: dict[tuple[str, str], list[ParsedSummary]] = {}
    for run in parsed:
        key = (run.stage, run.package or run.model_id)
        buckets.setdefault(key, []).append(run)

    groups: list[ExperimentGroup] = []
    for (stage, package), runs in buckets.items():
        runs.sort(key=lambda r: r.modified)
        latest = runs[-1]
        prior = runs[:-1]
        groups.append(
            ExperimentGroup(
                stage=stage,
                package=package,
                model_id=latest.model_id,
                latest=latest,
                prior_in_window=prior,
            )
        )
    groups.sort(key=lambda g: (g.stage, g.latest.modified))
    return groups


def top_labels(label_counts: dict[str, int], limit: int = 5) -> list[tuple[str, int]]:
    return sorted(label_counts.items(), key=lambda x: (-x[1], x[0]))[:limit]


_THEME_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("HF failure-analysis pipeline", re.compile(r"hf|osworld|babel|opencua|adapter|attribution|judge|failure.?label", re.I)),
    ("Hermes / project ops", re.compile(r"hermes|ops/|synthesize|weekly.?report|gdoc|meeting|project.?state", re.I)),
    ("Docs & protocol", re.compile(r"docs/|taxonomy|protocol|readme|agents\.md", re.I)),
    ("Infrastructure & tooling", re.compile(r"script|workflow|ci|docker|slurm|rsync|venv", re.I)),
]


def theme_commits(commits: list[str], prs: list[dict]) -> dict[str, list[str]]:
    """Lightweight commit/PR grouping by keyword themes."""
    themes: dict[str, list[str]] = {name: [] for name, _ in _THEME_RULES}
    themes["Other"] = []

    def assign(text: str, item: str) -> None:
        for name, pat in _THEME_RULES:
            if pat.search(text):
                themes[name].append(item)
                return
        themes["Other"].append(item)

    for pr in prs:
        assign(pr.get("title", ""), f"PR #{pr['number']}: {pr['title']}")

    for c in commits:
        parts = c.split("\t")
        if len(parts) >= 4:
            subj = parts[3]
            assign(subj, subj)

    return {k: v for k, v in themes.items() if v}


def format_label_line(label_counts: dict[str, int]) -> str:
    items = top_labels(label_counts)
    if not items:
        return "No labels emitted yet."
    return ", ".join(f"{name} ({count})" for name, count in items)


def group_to_dict(group: ExperimentGroup) -> dict:
    return {
        "stage": group.stage,
        "package": group.package,
        "model_id": group.model_id,
        "display_name": group.display_name,
        "latest_run_id": group.latest.run_id,
        "latest_modified": group.latest.modified,
        "summary_path": group.latest.path,
        "episodes_inventoried": group.latest.episodes_inventoried,
        "episodes_labeled": group.latest.episodes_labeled,
        "human_review_queue": group.latest.human_review_queue,
        "adapter_gaps": group.latest.adapter_gaps,
        "top_labels": top_labels(group.latest.label_counts),
        "superseded_runs_in_window": group.superseded_count,
        "judge_calls": group.latest.judge_calls,
        "judge_cost_usd": group.latest.judge_cost_usd,
    }
