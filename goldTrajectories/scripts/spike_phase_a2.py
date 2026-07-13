#!/usr/bin/env python3
"""Phase-A2: diagnose + fix the black-screen so screenshots show the real desktop.

The Phase-A round-trip worked but the captured frame was pure black. This probes
the guest display state (DISPLAY, xrandr, window list, DPMS, gnome-shell), then
disables screen blanking / DPMS and wakes the screen, and re-captures — so we
learn *why* it was black and whether a wake fixes it.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests


def wait_ready(base: str, timeout: int) -> float:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(base + "/screenshot", timeout=(5, 15))
            if r.status_code == 200 and r.content:
                return time.time() - start
        except Exception:
            pass
        time.sleep(5)
    raise TimeoutError(f"not ready after {timeout}s")


def run(base: str, code: str) -> dict:
    r = requests.post(base + "/execute",
                      headers={"Content-Type": "application/json"},
                      data=json.dumps({"command": ["python3", "-c", code], "shell": False}),
                      timeout=120)
    r.raise_for_status()
    return r.json()


def shot(base: str, path: Path) -> tuple[int, float]:
    r = requests.get(base + "/screenshot", timeout=(5, 30)); r.raise_for_status()
    path.write_bytes(r.content)
    # crude brightness: decode via PIL if available, else just size
    try:
        from PIL import Image
        import numpy as np
        import io
        a = np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"))
        return len(r.content), float(a.mean())
    except Exception:
        return len(r.content), -1.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--boot-timeout", type=int, default=600)
    ap.add_argument("--settle", type=int, default=45)
    args = ap.parse_args()
    base = f"http://{args.host}:{args.port}"
    out = Path(args.outdir); out.mkdir(parents=True, exist_ok=True)

    print(f"[a2] wait ready ...", flush=True)
    print(f"[a2] ready after {wait_ready(base, args.boot_timeout):.1f}s; settling {args.settle}s", flush=True)
    time.sleep(args.settle)

    n, b = shot(base, out / "a2_pre.png")
    print(f"[a2] pre-wake: {n} bytes, brightness={b:.2f}", flush=True)

    diag = (
        "import subprocess,os\n"
        "def sh(c):\n"
        "  try: return subprocess.run(c,shell=True,capture_output=True,text=True,timeout=15).stdout.strip()\n"
        "  except Exception as e: return 'ERR:'+repr(e)\n"
        "print('DISPLAY=',os.environ.get('DISPLAY'))\n"
        "print('WHOAMI=',sh('whoami'))\n"
        "print('XRANDR=',sh('xrandr 2>/dev/null | head -3'))\n"
        "print('WINDOWS=',sh('wmctrl -l 2>/dev/null | head'))\n"
        "print('XSET_Q=',sh('xset q 2>/dev/null | grep -A2 -i \"monitor\\|dpms\\|screen saver\" | head'))\n"
        "print('GNOME=',sh('pgrep -a gnome-shell | head -1'))\n"
        "print('SESS=',sh('ls ~/.config 2>/dev/null | head; echo ---; loginctl 2>/dev/null | head'))\n"
    )
    d = run(base, diag)
    print("[a2] DIAGNOSTICS:\n" + (d.get("output") or "") + "\nERR:" + (d.get("error") or ""), flush=True)

    # Disable blanking/DPMS and wake the screen.
    wake = (
        "import subprocess,time,pyautogui\n"
        "for c in ['xset s off','xset s noblank','xset -dpms','xset dpms force on','xset s reset']:\n"
        "  subprocess.run(c,shell=True)\n"
        "pyautogui.moveTo(400,300); pyautogui.moveRel(200,150); pyautogui.click(); pyautogui.press('esc')\n"
        "time.sleep(1)\n"
    )
    run(base, wake)
    time.sleep(4)

    n2, b2 = shot(base, out / "a2_post.png")
    print(f"[a2] post-wake: {n2} bytes, brightness={b2:.2f}", flush=True)

    res = {"pre_bytes": n, "pre_brightness": round(b, 2),
           "post_bytes": n2, "post_brightness": round(b2, 2),
           "rendered": bool(b2 > 3.0)}
    (out / "a2_result.json").write_text(json.dumps(res, indent=2))
    print("[a2] RESULT: " + json.dumps(res), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
