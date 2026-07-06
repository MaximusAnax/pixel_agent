"""Build a static, self-contained HTML viewer for failed OSWorld trajectories.

The viewer lets a human:
  - scroll every failed trajectory (instruction, per-step screenshot + reasoning +
    action, outcome),
  - assign their OWN failure-mode label (category + primary mode + secondary modes
    + failing step + notes), persisted in the browser (localStorage) and
    exportable as JSON,
  - see the 7B and 32B VLM-judge classifications side-by-side and immediately tell
    whether each judge AGREES with the human label (so judge quality can be
    spot-checked).

This script only produces `data.js` + the downscaled `assets/`; the app itself is
the static `index.html` next to it (it reads `data.js` at load time, so it works by
just opening index.html via file:// — no server, no CORS issues). Re-running after
the judges finish only rewrites `data.js` (images already on disk are skipped), so
the judge columns light up without re-encoding thousands of screenshots.

Usage:
    python build_viewer.py \
        --failures ../outputs/failures_a3b.jsonl \
        --judge-7b ../outputs/classifications_a3b.jsonl \
        --judge-32b ../outputs/classifications_a3b_32b.jsonl \
        --outdir ../viewer
Both --judge-* are optional; pass them once the SLURM jobs have written output.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image

from cua_failure_analysis.trajectory_judge.taxonomy import MODE_CATEGORY, MODE_DEFINITION, Category, FailureMode

_JUDGE_FIELDS = (
    "analysis", "category", "primary_failure_mode", "failing_step",
    "secondary_failure_modes", "confidence",
)


def safe_uid(uid: str) -> str:
    return uid.replace("/", "__").replace(" ", "_")


def load_judge(path: Path | None) -> dict[str, dict]:
    """uid -> trimmed classification dict (parse_ok rows only)."""
    out: dict[str, dict] = {}
    if not path or not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not r.get("parse_ok"):
            continue
        c = r.get("classification") or {}
        out[r["uid"]] = {k: c.get(k) for k in _JUDGE_FIELDS}
    return out


def downscale(src: str, dst: Path, max_side: int, quality: int) -> bool:
    """Write a downscaled JPEG copy of `src` to `dst`. Skip if dst already exists
    (idempotent rebuilds). Returns True if an image is available at dst."""
    if dst.exists():
        return True
    try:
        img = Image.open(src).convert("RGB")
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] cannot read {src}: {e}")
        return False
    w, h = img.size
    scale = max_side / max(w, h)
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "JPEG", quality=quality)
    return True


def taxonomy_payload() -> dict:
    modes = []
    for m in FailureMode:
        modes.append({
            "mode": m.value,
            "category": MODE_CATEGORY[m].value,
            "definition": MODE_DEFINITION[m],
        })
    return {
        "categories": [c.value for c in Category],
        "modes": modes,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--failures", required=True)
    ap.add_argument("--judge-7b", default=None)
    ap.add_argument("--judge-32b", default=None)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--assets-subdir", default="assets")
    ap.add_argument("--max-side", type=int, default=1600)
    ap.add_argument("--quality", type=int, default=80)
    ap.add_argument("--model-filter", default=None,
                    help="only include trajectories whose model == this")
    ap.add_argument("--title", default="OSWorld failure viewer")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    assets = outdir / args.assets_subdir
    assets.mkdir(parents=True, exist_ok=True)

    trajs = [json.loads(l) for l in Path(args.failures).read_text().splitlines() if l.strip()]
    if args.model_filter:
        trajs = [t for t in trajs if t.get("model") == args.model_filter]
    j7 = load_judge(Path(args.judge_7b)) if args.judge_7b else {}
    j32 = load_judge(Path(args.judge_32b)) if args.judge_32b else {}

    records = []
    n_img = n_missing = 0
    for t in sorted(trajs, key=lambda x: (x["domain"], x["task_id"])):
        uid = f"{t['model']}/{t['domain']}/{t['task_id']}"
        sdir = safe_uid(uid)
        steps_out = []
        for s in t["steps"]:
            rel = None
            sp = s.get("screenshot_path")
            if sp:
                dst = assets / sdir / f"step_{s['idx']}.jpg"
                if downscale(sp, dst, args.max_side, args.quality):
                    rel = f"{args.assets_subdir}/{sdir}/step_{s['idx']}.jpg"
                    n_img += 1
                else:
                    n_missing += 1
            steps_out.append({
                "idx": s["idx"],
                "img": rel,
                "reasoning": s.get("reasoning", ""),
                "action": s.get("action", ""),
            })
        records.append({
            "uid": uid,
            "model": t["model"],
            "domain": t["domain"],
            "task_id": t["task_id"],
            "instruction": t["instruction"],
            "reward": t["reward"],
            "num_steps": t["num_steps"],
            "steps": steps_out,
            "judges": {"7b": j7.get(uid), "32b": j32.get(uid)},
        })

    meta = {
        "title": args.title,
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "n": len(records),
        "n_images": n_img,
        "judges_present": {"7b": bool(j7), "32b": bool(j32)},
        "n_judged_7b": sum(1 for r in records if r["judges"]["7b"]),
        "n_judged_32b": sum(1 for r in records if r["judges"]["32b"]),
    }

    data_js = (
        "// AUTO-GENERATED by build_viewer.py — do not edit by hand.\n"
        "window.TAXONOMY = " + json.dumps(taxonomy_payload(), ensure_ascii=False) + ";\n"
        "window.META = " + json.dumps(meta, ensure_ascii=False) + ";\n"
        "window.TRAJ_DATA = " + json.dumps(records, ensure_ascii=False) + ";\n"
    )
    (outdir / "data.js").write_text(data_js)

    # Ship the static app + helper next to the data, if present in src/viewer_assets.
    src_index = Path(__file__).parent / "viewer_assets" / "index.html"
    if src_index.exists():
        shutil.copy(src_index, outdir / "index.html")
    src_serve = Path(__file__).parent / "viewer_assets" / "serve.sh"
    if src_serve.exists():
        shutil.copy(src_serve, outdir / "serve.sh")
        (outdir / "serve.sh").chmod(0o755)

    print(f"viewer -> {outdir}")
    print(f"  trajectories: {len(records)}  | images written/seen: {n_img}  | missing: {n_missing}")
    print(f"  judges merged: 7B={meta['n_judged_7b']}  32B={meta['n_judged_32b']}")
    print(f"  open {outdir/'index.html'} (or run serve.sh and port-forward)")


if __name__ == "__main__":
    main()
