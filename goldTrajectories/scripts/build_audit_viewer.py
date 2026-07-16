#!/usr/bin/env python3
"""Build the failure-audit viewer: every task (gold / failed / incomplete),
filterable index, per-task pages with grounded-pixel crosshairs, replay-log
tails, and a notes panel that saves through serve_audit.py to
audit_labels.json. Serve with scripts/serve_audit.py (labels need the POST
endpoint; plain file:// shows pages read-only).

Usage:
    python build_audit_viewer.py \
        --gold-root /data/group_data/mattlab/raghavg3/osworld_env/gold \
        --task-list /data/group_data/mattlab/raghavg3/osworld_env/run/all_tasks.txt \
        --outdir    /data/group_data/mattlab/raghavg3/osworld_env/gold_audit
"""

from __future__ import annotations

import argparse
import html
import json
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw

THUMB_W = 960

# Provisional audit tags only — NOT the errorAnalysis taxonomy (which needs
# Abdoul's approval to change). These label why a *guided replay* failed.
CATEGORIES = ["ui-drift", "grounding-miss", "human-steps-wrong", "evaluator-strict",
              "setup-fail", "timeout", "infra", "infeasible-ok", "unsure"]


def thumb_job(job):
    src, dst, coords = job
    try:
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
        img.save(dst, "JPEG", quality=68)
    except Exception as e:  # noqa: BLE001
        print(f"thumb failed {src}: {e}")


CSS = """
 :root { --bg:#f6f5f1; --surface:#fff; --ink:#26272b; --muted:#6f7176; --line:#e4e2da;
   --gold:#96700f; --gold-bg:#f5ecd4; --fail:#a83430; --fail-bg:#f8e5e2;
   --inc:#7a6a9c; --inc-bg:#ece7f5; --code-bg:#efede6; }
 @media (prefers-color-scheme: dark) { :root { --bg:#16171b; --surface:#1e2025; --ink:#e5e3dc;
   --muted:#9b9da3; --line:#2d2f36; --gold:#d5a52a; --gold-bg:#2b2312; --fail:#e0685e;
   --fail-bg:#301d1b; --inc:#a794cf; --inc-bg:#262138; --code-bg:#26282f; } }
 * { box-sizing:border-box; }
 body { background:var(--bg); color:var(--ink); margin:0 auto; max-width:1080px;
   padding:1.6rem 1.6rem 4rem; font:14.5px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
 a { color:inherit; }
 code { font:12px ui-monospace,Menlo,Consolas,monospace; background:var(--code-bg);
   border-radius:4px; padding:1px 5px; overflow-wrap:anywhere; }
 .chip { font:600 11px ui-monospace,Menlo,monospace; letter-spacing:.04em;
   border-radius:999px; padding:4px 10px; white-space:nowrap; }
 .chip.gold { background:var(--gold-bg); color:var(--gold); }
 .chip.failed { background:var(--fail-bg); color:var(--fail); }
 .chip.incomplete { background:var(--inc-bg); color:var(--inc); }
 .notebadge { color:var(--gold); font-size:15px; }
"""

INDEX_JS = """
const rows = [...document.querySelectorAll('tr[data-uuid]')];
const stateSel = document.getElementById('f-state'), appSel = document.getElementById('f-app'),
      noteSel = document.getElementById('f-note'), count = document.getElementById('count');
let labels = {};
function apply() {
  let shown = 0;
  for (const r of rows) {
    const lb = labels[r.dataset.uuid] || null;
    r.querySelector('.notebadge').textContent = lb && (lb.note || lb.category) ? '\\u270E' : '';
    r.querySelector('.cat').textContent = lb && lb.category ? lb.category : '';
    const okState = stateSel.value === 'all' || r.dataset.state === stateSel.value;
    const okApp = appSel.value === 'all' || r.dataset.app === appSel.value;
    const hasNote = lb && (lb.note || lb.category);
    const okNote = noteSel.value === 'all' || (noteSel.value === 'with' ? !!hasNote : !hasNote);
    r.style.display = okState && okApp && okNote ? '' : 'none';
    if (okState && okApp && okNote) shown++;
  }
  count.textContent = shown + ' shown';
}
fetch('audit_labels.json').then(r => r.ok ? r.json() : {}).then(d => { labels = d; apply(); })
  .catch(() => apply());
for (const el of [stateSel, appSel, noteSel]) el.addEventListener('change', apply);
"""

TASK_JS = """
const uuid = document.body.dataset.uuid;
const cat = document.getElementById('n-cat'), note = document.getElementById('n-note'),
      btn = document.getElementById('n-save'), status = document.getElementById('n-status');
fetch('../audit_labels.json').then(r => r.ok ? r.json() : {}).then(d => {
  const lb = d[uuid]; if (!lb) return;
  cat.value = lb.category || ''; note.value = lb.note || '';
  status.textContent = 'saved ' + (lb.updated || '');
}).catch(() => { status.textContent = 'labels need serve_audit.py (read-only over file://)'; });
btn.addEventListener('click', () => {
  fetch('/api/labels', { method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ uuid, category: cat.value, note: note.value }) })
    .then(r => { status.textContent = r.ok ? 'saved \\u2713' : 'save failed: HTTP ' + r.status; })
    .catch(e => { status.textContent = 'save failed: ' + e; });
});
"""


def load_run(gold_root: Path, uuid: str):
    d = gold_root / uuid
    run = {"uuid": uuid, "state": "incomplete", "score": None, "instruction": "",
           "steps": [], "log_tail": "", "dir": d}
    m = d / "manifest.json"
    if m.exists():
        mf = json.loads(m.read_text())
        run["state"] = "gold" if mf.get("success") else "failed"
        run["score"] = mf.get("score")
        run["instruction"] = mf.get("instruction", "")
    tr = d / "trace.jsonl"
    if tr.exists():
        run["steps"] = [json.loads(l) for l in tr.read_text().splitlines() if l.strip()]
    lg = d / "replay.log"
    if lg.exists():
        lines = lg.read_text(errors="replace").splitlines()
        run["log_tail"] = "\n".join(lines[-10:])
        if not run["instruction"]:
            for ln in lines:
                if "]: " in ln and "task " in ln:
                    run["instruction"] = ln.split(": ", 2)[-1]
                    break
    return run


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-root", type=Path, required=True)
    ap.add_argument("--task-list", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    tasks = [l.strip() for l in args.task_list.read_text().splitlines() if l.strip()]
    assets = args.outdir / "assets"
    pages = args.outdir / "tasks"
    assets.mkdir(parents=True, exist_ok=True)
    pages.mkdir(parents=True, exist_ok=True)
    if not (args.outdir / "audit_labels.json").exists():
        (args.outdir / "audit_labels.json").write_text("{}\n")

    runs, jobs = [], []
    for app_id in tasks:
        app, uuid = app_id.split("/", 1)
        run = load_run(args.gold_root, uuid)
        run["app"] = app
        runs.append(run)
        shots = run["dir"] / "screenshots"
        for s in run["steps"]:
            n = s["step"]
            b, a = shots / f"step{n:02d}_before.png", shots / f"step{n:02d}_after.png"
            bd, ad = assets / f"{uuid}_s{n:02d}_before.jpg", assets / f"{uuid}_s{n:02d}_after.jpg"
            if b.exists() and not bd.exists():
                jobs.append((b, bd, tuple(s["coords"]) if s.get("coords") else None))
            if a.exists() and not ad.exists():
                jobs.append((a, ad, None))
        f = shots / "final.png"
        fd = assets / f"{uuid}_final.jpg"
        if f.exists() and not fd.exists():
            jobs.append((f, fd, None))

    print(f"{len(runs)} tasks; encoding {len(jobs)} thumbnails with {args.workers} workers ...")
    if jobs:
        with Pool(args.workers) as pool:
            pool.map(thumb_job, jobs, chunksize=16)

    order = {"failed": 0, "incomplete": 1, "gold": 2}
    runs.sort(key=lambda r: (order[r["state"]], r["app"], r["uuid"]))
    apps = sorted({r["app"] for r in runs})

    # ---- index ----
    rows = []
    for r in runs:
        score = "" if r["score"] is None else f"{r['score']:g}"
        rows.append(
            f'<tr data-uuid="{r["uuid"]}" data-state="{r["state"]}" data-app="{r["app"]}">'
            f'<td><span class="chip {r["state"]}">{r["state"]}</span></td>'
            f'<td>{r["app"]}</td>'
            f'<td><a href="tasks/{r["uuid"]}.html"><code>{r["uuid"][:8]}</code></a></td>'
            f'<td>{len(r["steps"])}</td><td>{score}</td>'
            f'<td class="cat"></td><td><span class="notebadge"></span></td>'
            f'<td class="instr">{html.escape(r["instruction"][:110])}</td></tr>')
    n_g = sum(r["state"] == "gold" for r in runs)
    n_f = sum(r["state"] == "failed" for r in runs)
    n_i = sum(r["state"] == "incomplete" for r in runs)
    index = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Gold-replay failure audit</title><style>{CSS}
 h1 {{ font-size:1.3rem; margin:.2rem 0 .6rem; }}
 .filters {{ display:flex; gap:10px; align-items:center; margin:.8rem 0 1rem; flex-wrap:wrap; }}
 select {{ background:var(--surface); color:var(--ink); border:1px solid var(--line);
   border-radius:7px; padding:5px 9px; font:inherit; }}
 table {{ border-collapse:collapse; width:100%; background:var(--surface);
   border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
 th,td {{ text-align:left; padding:6px 9px; border-top:1px solid var(--line);
   font-variant-numeric:tabular-nums; }}
 th {{ font-size:.7rem; text-transform:uppercase; letter-spacing:.07em; color:var(--muted); border-top:none; }}
 .instr {{ color:var(--muted); }} #count {{ color:var(--muted); }}
</style></head><body>
<h1>Gold-replay failure audit — {len(runs)} tasks ({n_g} gold · {n_f} failed · {n_i} incomplete)</h1>
<div class="filters">
 <label>state <select id="f-state"><option value="all">all</option>
  <option value="failed" selected>failed</option><option value="incomplete">incomplete</option>
  <option value="gold">gold</option></select></label>
 <label>domain <select id="f-app"><option value="all">all</option>
  {''.join(f'<option>{a}</option>' for a in apps)}</select></label>
 <label>notes <select id="f-note"><option value="all">all</option>
  <option value="with">with notes</option><option value="without">without notes</option></select></label>
 <span id="count"></span>
</div>
<table><tr><th>state</th><th>domain</th><th>task</th><th>steps</th><th>score</th>
<th>category</th><th></th><th>instruction</th></tr>{''.join(rows)}</table>
<script>{INDEX_JS}</script></body></html>"""
    (args.outdir / "index.html").write_text(index)

    # ---- per-task pages ----
    for idx, r in enumerate(runs):
        uuid = r["uuid"]
        cards = []
        for s in r["steps"]:
            n = s["step"]
            b = f"../assets/{uuid}_s{n:02d}_before.jpg"
            a = f"../assets/{uuid}_s{n:02d}_after.jpg"
            has_b = (assets / f"{uuid}_s{n:02d}_before.jpg").exists()
            has_a = (assets / f"{uuid}_s{n:02d}_after.jpg").exists()
            shots = ""
            if has_b or has_a:
                figs = []
                if has_b:
                    figs.append(f'<figure><img loading="lazy" src="{b}"><figcaption>before · crosshair = grounded point</figcaption></figure>')
                if has_a:
                    figs.append(f'<figure><img loading="lazy" src="{a}"><figcaption>after</figcaption></figure>')
                shots = f'<div class="shots">{"".join(figs)}</div>'
            grounded = (f'<div><b>sent to UGround:</b> {html.escape(s.get("grounded_desc",""))} '
                        f'· <b>raw:</b> <code>{html.escape(str(s.get("ground_raw")))}</code> '
                        f'→ <code>{s.get("coords")}</code></div>') if s.get("coords") else ""
            cards.append(f"""<div class="step"><div class="stephead">step {n:02d} — <code>{html.escape(s.get("verb") or "?")}</code></div>
{shots}<div class="meta"><div><b>human:</b> {html.escape(s.get("human_step",""))}</div>{grounded}
<div><b>executed:</b> <code>{html.escape(s.get("action",{}).get("command",""))}</code></div></div></div>""")
        fin = f"{uuid}_final.jpg"
        final_fig = (f'<figure class="final"><img loading="lazy" src="../assets/{fin}">'
                     f'<figcaption>final screen at evaluation</figcaption></figure>'
                     if (assets / fin).exists() else "")
        prev_link = f'<a href="{runs[idx-1]["uuid"]}.html">&larr; prev</a>' if idx else ""
        next_link = f'<a href="{runs[idx+1]["uuid"]}.html">next &rarr;</a>' if idx + 1 < len(runs) else ""
        score = "" if r["score"] is None else f" · score {r['score']:g}"
        page = f"""<!doctype html><html><head><meta charset="utf-8">
<title>{uuid[:8]} — audit</title><style>{CSS}
 .nav {{ display:flex; justify-content:space-between; margin-bottom:.8rem; }}
 h1 {{ font-size:1.05rem; margin:.4rem 0; }}
 .shots {{ display:flex; gap:10px; }} .shots figure {{ margin:0; flex:1; min-width:0; }}
 .shots img, .final img {{ width:100%; border-radius:6px; border:1px solid var(--line); }}
 figcaption {{ color:var(--muted); font-size:.74rem; margin-top:3px; }}
 .step {{ border-top:1px solid var(--line); padding:.8rem 0; }}
 .stephead {{ font-weight:700; color:var(--gold); margin-bottom:.4rem; }}
 .meta div {{ margin:.14rem 0; overflow-wrap:anywhere; }}
 .final {{ max-width:440px; margin:.8rem 0; }}
 pre {{ background:var(--code-bg); border-radius:8px; padding:.7rem .9rem; overflow-x:auto;
   font:12px ui-monospace,Menlo,monospace; }}
 .notes {{ background:var(--surface); border:1px solid var(--line); border-radius:10px;
   padding:1rem 1.2rem; margin:1.2rem 0; }}
 .notes select, .notes textarea, .notes button {{ font:inherit; background:var(--bg);
   color:var(--ink); border:1px solid var(--line); border-radius:7px; padding:6px 9px; }}
 textarea {{ width:100%; min-height:70px; margin:.5rem 0; }}
 button {{ cursor:pointer; font-weight:600; }} #n-status {{ color:var(--muted); margin-left:10px; }}
</style></head><body data-uuid="{uuid}">
<div class="nav"><a href="../index.html">&larr; index</a><span>{prev_link} {next_link}</span></div>
<span class="chip {r["state"]}">{r["state"]}</span> <b>{r["app"]}</b> <code>{uuid}</code>{score}
<h1>{html.escape(r["instruction"])}</h1>
<div class="notes"><b>Audit note</b><br>
 <label>category <select id="n-cat"><option value=""></option>
  {''.join(f'<option>{c}</option>' for c in CATEGORIES)}</select></label>
 <textarea id="n-note" placeholder="what actually went wrong / evidence step / retry idea"></textarea>
 <button id="n-save">Save note</button><span id="n-status"></span></div>
{''.join(cards) or "<p><i>No steps recorded (setup crash or pre-replay failure — see log below).</i></p>"}
{final_fig}
<h3>replay.log tail</h3><pre>{html.escape(r["log_tail"] or "(no log)")}</pre>
<script>{TASK_JS}</script></body></html>"""
        (pages / f"{uuid}.html").write_text(page)

    print(f"audit viewer: {args.outdir}/index.html ({len(runs)} tasks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
