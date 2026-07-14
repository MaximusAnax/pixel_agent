#!/usr/bin/env python3
"""Build a static HTML viewer for gold (guided-replay) trajectories.

Reads every `$GOLD_ROOT/<task_uuid>/` produced by replay_agent.py
(manifest.json + trace.jsonl + screenshots/) and writes a self-contained
viewer dir: index.html + downscaled JPEG assets. For each grounded step the
before-screenshot is stamped with a crosshair at the pixel UGround chose, so
grounding quality can be audited at a glance. Works via file:// or
`python -m http.server` from the output dir — no external deps in the page.

Usage:
    python build_gold_viewer.py \
        --gold-root /data/group_data/mattlab/raghavg3/osworld_env/gold \
        --outdir    /data/group_data/mattlab/raghavg3/osworld_env/gold_viewer \
        [--include-failures]
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from PIL import Image, ImageDraw

THUMB_W = 960


def stamp_and_thumb(src: Path, dst: Path, coords=None) -> None:
    if dst.exists():
        return
    img = Image.open(src).convert("RGB")
    if coords:
        x, y = coords
        d = ImageDraw.Draw(img)
        r = 22
        d.ellipse([x - r, y - r, x + r, y + r], outline="#ff2d2d", width=5)
        d.line([x - r - 14, y, x + r + 14, y], fill="#ff2d2d", width=3)
        d.line([x, y - r - 14, x, y + r + 14], fill="#ff2d2d", width=3)
    scale = THUMB_W / img.width
    img = img.resize((THUMB_W, int(img.height * scale)))
    img.save(dst, "JPEG", quality=70)


def load_run(run_dir: Path):
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    run = json.loads(manifest_path.read_text())
    steps = []
    trace_path = run_dir / "trace.jsonl"
    if trace_path.exists():
        for line in trace_path.read_text().splitlines():
            if line.strip():
                steps.append(json.loads(line))
    run["steps"] = steps
    run["dir"] = run_dir
    return run


STEP_CARD = """
<div class="step">
  <div class="shots">
    <figure><img loading="lazy" src="{before}"><figcaption>before (grounded point marked)</figcaption></figure>
    <figure><img loading="lazy" src="{after}"><figcaption>after</figcaption></figure>
  </div>
  <div class="meta">
    <div class="verb">step {n} — <code>{verb}</code></div>
    <div><b>human step:</b> {human}</div>
    <div><b>sent to UGround:</b> {gdesc}</div>
    <div><b>model raw → pixels:</b> <code>{raw}</code> → <code>{coords}</code></div>
    <div><b>executed:</b> <code>{cmd}</code></div>
  </div>
</div>"""

TASK_SECTION = """
<section class="task {cls}">
  <h2>{badge} {task_id}</h2>
  <p class="instr">{instruction}</p>
  <p class="sub">score={score} · {nsteps} steps · guided_by={guided}</p>
  {steps}
  <figure class="final"><img loading="lazy" src="{final}"><figcaption>final screen at evaluation</figcaption></figure>
</section>"""

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>Gold trajectories — guided replay viewer</title>
<style>
 body {{ font: 15px/1.45 system-ui, sans-serif; margin: 0 auto; max-width: 1080px;
        padding: 1rem 2rem; background: #14161a; color: #e8e8e8; }}
 h1 {{ font-size: 1.4rem; }} h2 {{ font-size: 1.1rem; margin: 0 0 .2rem; }}
 code {{ background: #23262d; padding: 1px 5px; border-radius: 4px; font-size: .85em; }}
 .task {{ border: 1px solid #333; border-radius: 10px; padding: 1rem 1.2rem; margin: 1.4rem 0; }}
 .task.gold {{ border-color: #b8860b; }} .task.fail {{ border-color: #7a2b2b; opacity: .9; }}
 .instr {{ font-weight: 600; margin: .2rem 0; }} .sub {{ color: #9aa; margin-top: 0; }}
 .step {{ border-top: 1px solid #2a2d33; padding: .8rem 0; }}
 .shots {{ display: flex; gap: 10px; }} .shots figure {{ margin: 0; flex: 1; min-width: 0; }}
 .shots img, .final img {{ width: 100%; border-radius: 6px; }}
 figcaption {{ color: #889; font-size: .8em; }}
 .meta div {{ margin: .15rem 0; overflow-wrap: anywhere; }} .verb {{ color: #d4a017; }}
 .final {{ margin: .8rem 0 0; max-width: 480px; }}
</style></head><body>
<h1>Gold trajectories — guided grounded replay (UGround-V1-72B)</h1>
<p>{summary}</p>
{sections}
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-root", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--include-failures", action="store_true",
                    help="also render runs whose evaluator score < 1 (marked red)")
    args = ap.parse_args()

    runs = sorted(filter(None, (load_run(d) for d in args.gold_root.iterdir() if d.is_dir())),
                  key=lambda r: (not r["success"], r["task_id"]))
    if not args.include_failures:
        runs = [r for r in runs if r["success"]]

    assets = args.outdir / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    sections = []
    for run in runs:
        tid = run["task_id"]
        cards = []
        for s in run["steps"]:
            n = s["step"]
            before_src = run["dir"] / "screenshots" / f"step{n:02d}_before.png"
            after_src = run["dir"] / "screenshots" / f"step{n:02d}_after.png"
            before_dst = assets / f"{tid}_s{n:02d}_before.jpg"
            after_dst = assets / f"{tid}_s{n:02d}_after.jpg"
            if before_src.exists():
                stamp_and_thumb(before_src, before_dst, s.get("coords"))
            if after_src.exists():
                stamp_and_thumb(after_src, after_dst)
            cards.append(STEP_CARD.format(
                n=n, verb=html.escape(s.get("verb") or "?"),
                human=html.escape(s.get("human_step", "")),
                gdesc=html.escape(s.get("grounded_desc", "")) if s.get("coords")
                      else "<i>not grounded (keyboard/scroll step)</i>",
                raw=html.escape(str(s.get("ground_raw"))),
                coords=html.escape(str(s.get("coords"))),
                cmd=html.escape(s.get("action", {}).get("command", "")),
                before=f"assets/{before_dst.name}", after=f"assets/{after_dst.name}"))
        final_src = run["dir"] / "screenshots" / "final.png"
        final_dst = assets / f"{tid}_final.jpg"
        if final_src.exists():
            stamp_and_thumb(final_src, final_dst)
        sections.append(TASK_SECTION.format(
            cls="gold" if run["success"] else "fail",
            badge="🏅" if run["success"] else "❌",
            task_id=tid, instruction=html.escape(run["instruction"]),
            score=run["score"], nsteps=run["total_steps"],
            guided=html.escape(run.get("guided_by", "?")),
            steps="".join(cards), final=f"assets/{final_dst.name}"))

    n_gold = sum(r["success"] for r in runs)
    summary = (f"{n_gold} gold / {len(runs)} rendered runs from "
               f"<code>{html.escape(str(args.gold_root))}</code>. Red crosshair = pixel "
               f"chosen by the grounding model for that step.")
    (args.outdir / "index.html").write_text(PAGE.format(summary=summary, sections="".join(sections)))
    print(f"viewer: {args.outdir}/index.html ({len(runs)} runs, gold={n_gold})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
