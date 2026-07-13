#!/usr/bin/env python3
"""Phase-A feasibility check: prove the Apptainer+QEMU OSWorld VM round-trip.

Talks to the in-guest OSWorld server over raw HTTP (no desktop_env deps beyond
`requests`/`Pillow`): wait-for-ready -> screenshot -> execute a pyautogui action
-> screenshot again. Success means live OSWorld on Babel is viable, which is the
whole point of the environment spike.

Usage: spike_phase_a.py --host 127.0.0.1 --port 5000 --outdir <dir> [--boot-timeout 600]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests


def wait_ready(base: str, timeout: int) -> float:
    start = time.time()
    last_err = None
    while time.time() - start < timeout:
        try:
            r = requests.get(base + "/screenshot", timeout=(5, 15))
            if r.status_code == 200 and r.content:
                return time.time() - start
            last_err = f"status={r.status_code}"
        except Exception as e:  # noqa: BLE001
            last_err = repr(e)
        time.sleep(5)
    raise TimeoutError(f"VM server not ready after {timeout}s (last: {last_err})")


def screenshot(base: str, path: Path) -> int:
    r = requests.get(base + "/screenshot", timeout=(5, 30))
    r.raise_for_status()
    path.write_bytes(r.content)
    return len(r.content)


def execute(base: str, command: list[str]) -> dict:
    r = requests.post(
        base + "/execute",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"command": command, "shell": False}),
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--boot-timeout", type=int, default=600)
    args = ap.parse_args()

    base = f"http://{args.host}:{args.port}"
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"[phase-a] waiting for {base}/screenshot (timeout {args.boot_timeout}s) ...", flush=True)
    ready_s = wait_ready(base, args.boot_timeout)
    print(f"[phase-a] VM ready after {ready_s:.1f}s", flush=True)

    n0 = screenshot(base, outdir / "before.png")
    print(f"[phase-a] before.png: {n0} bytes", flush=True)

    # Benign, visible action: move mouse to center and click, then move away.
    action = "import pyautogui; pyautogui.moveTo(960, 540, duration=0.2); pyautogui.click(); pyautogui.moveTo(50, 50, duration=0.2)"
    res = execute(base, ["python3", "-c", action])
    print(f"[phase-a] execute result: {json.dumps(res)[:300]}", flush=True)

    time.sleep(2)
    n1 = screenshot(base, outdir / "after.png")
    print(f"[phase-a] after.png: {n1} bytes", flush=True)

    ok = n0 > 0 and n1 > 0 and isinstance(res, dict)
    summary = {
        "ready_seconds": round(ready_s, 1),
        "before_bytes": n0,
        "after_bytes": n1,
        "execute_status": res.get("status") if isinstance(res, dict) else None,
        "pass": bool(ok),
    }
    (outdir / "phase_a_result.json").write_text(json.dumps(summary, indent=2))
    print(f"[phase-a] RESULT: {json.dumps(summary)}", flush=True)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
