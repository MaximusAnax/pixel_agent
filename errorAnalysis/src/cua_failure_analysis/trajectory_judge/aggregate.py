"""Aggregate judge classifications into tables, charts, and a markdown report.

    python aggregate.py --classifications ../outputs/classifications.jsonl --outdir ../outputs
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from cua_failure_analysis.trajectory_judge.taxonomy import MODE_CATEGORY, FailureMode  # noqa: E402


def load(path: Path) -> pd.DataFrame:
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        c = r.get("classification") or {}
        rows.append({
            "model": r["model"], "domain": r["domain"], "task_id": r["task_id"],
            "num_steps": r.get("num_steps"), "n_images": r.get("n_images"),
            "parse_ok": r.get("parse_ok", False),
            "primary": c.get("primary_failure_mode"),
            "category": c.get("category"),
            "confidence": c.get("confidence"),
            "failing_step": c.get("failing_step"),
            "secondary": ",".join(c.get("secondary_failure_modes", []) or []),
            "analysis": (c.get("analysis") or "")[:500],
        })
    return pd.DataFrame(rows)


def bar(series: pd.Series, title: str, path: Path, xlabel: str = "count") -> None:
    if series.empty:
        return
    fig, ax = plt.subplots(figsize=(9, max(3, 0.4 * len(series))))
    series.iloc[::-1].plot.barh(ax=ax)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--classifications", default="../outputs/classifications.jsonl")
    ap.add_argument("--outdir", default="../outputs")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df = load(Path(args.classifications))

    n = len(df)
    n_ok = int(df["parse_ok"].sum())
    ok = df[df["parse_ok"]].copy()

    # ---- tables ----
    by_mode_model = (
        ok.groupby(["primary", "model"]).size().unstack(fill_value=0)
        if not ok.empty else pd.DataFrame()
    )
    by_mode = ok["primary"].value_counts() if not ok.empty else pd.Series(dtype=int)
    by_cat_model = (
        ok.groupby(["category", "model"]).size().unstack(fill_value=0)
        if not ok.empty else pd.DataFrame()
    )
    by_domain_cat = (
        ok.groupby(["domain", "category"]).size().unstack(fill_value=0)
        if not ok.empty else pd.DataFrame()
    )

    by_mode_model.to_csv(outdir / "failure_by_mode_model.csv")
    by_cat_model.to_csv(outdir / "failure_by_category_model.csv")
    by_domain_cat.to_csv(outdir / "failure_by_domain_category.csv")
    ok.to_csv(outdir / "classifications_flat.csv", index=False)

    # ---- charts ----
    bar(by_mode, "Primary failure mode (all models)", outdir / "fig_modes_overall.png")
    for model, sub in ok.groupby("model"):
        safe = "".join(ch if ch.isalnum() else "_" for ch in model)[:40]
        bar(sub["primary"].value_counts(),
            f"Primary failure mode — {model}", outdir / f"fig_modes_{safe}.png")

    # ---- representative examples per mode ----
    examples: dict[str, list[str]] = defaultdict(list)
    for _, row in ok.sort_values("confidence", ascending=False).iterrows():
        if len(examples[row["primary"]]) < 3:
            examples[row["primary"]].append(f"{row['model']}/{row['domain']}/{row['task_id']}")

    # ---- markdown report ----
    lines = ["# CUA Failure-Mode Analysis (OSWorld-Verified trajectories)", ""]
    lines.append(f"- Trajectories judged: **{n}**  |  parsed OK: **{n_ok}** "
                 f"({100*n_ok/max(n,1):.1f}%)")
    if not ok.empty:
        lines.append(f"- Models: {', '.join(sorted(ok['model'].unique()))}")
        lines.append("")
        lines.append("## Category split (perception/grounding vs cognitive/planning)")
        lines.append("")
        lines.append(by_cat_model.to_markdown() if not by_cat_model.empty else "_n/a_")
        lines.append("")
        lines.append("## Primary failure mode by model")
        lines.append("")
        lines.append(by_mode_model.to_markdown() if not by_mode_model.empty else "_n/a_")
        lines.append("")
        lines.append("## Domain × category")
        lines.append("")
        lines.append(by_domain_cat.to_markdown() if not by_domain_cat.empty else "_n/a_")
        lines.append("")
        lines.append("## Representative examples (highest-confidence per mode)")
        lines.append("")
        for mode in [m.value for m in FailureMode]:
            if mode in examples:
                cat = MODE_CATEGORY[FailureMode(mode)].value
                lines.append(f"**{mode}** _({cat})_")
                for ex in examples[mode]:
                    lines.append(f"  - `{ex}`")
        lines.append("")
        lines.append("## Figures")
        for p in sorted(outdir.glob("fig_*.png")):
            lines.append(f"![{p.stem}]({p.name})")
    (outdir / "report.md").write_text("\n".join(lines) + "\n")

    print(f"Wrote report + CSVs + figures to {outdir}")
    if not by_cat_model.empty:
        print("\nCategory split by model:\n", by_cat_model)
    if not by_mode.empty:
        print("\nTop modes overall:\n", by_mode.head(15))


if __name__ == "__main__":
    main()
