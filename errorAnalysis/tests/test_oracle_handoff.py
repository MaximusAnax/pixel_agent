"""Partner oracle handoff contract (loaders + rejudge gate, no HA runner)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cua_failure_analysis.attribution.pipeline import (
  load_human_reference_steps,
  resolve_oracle_dir,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_TASK = "06fe7178-4491-4589-810f-2e2bc9502122"


def test_resolve_oracle_dir_nested_and_flat(tmp_path: Path):
  nested = tmp_path / "chrome" / EXAMPLE_TASK
  nested.mkdir(parents=True)
  (nested / "human_traj.json").write_text("{}", encoding="utf-8")
  assert resolve_oracle_dir(tmp_path, "chrome", EXAMPLE_TASK) == nested

  flat_root = tmp_path / "flat"
  flat = flat_root / EXAMPLE_TASK
  flat.mkdir(parents=True)
  (flat / "human_traj.json").write_text("{}", encoding="utf-8")
  assert resolve_oracle_dir(flat_root, "chrome", EXAMPLE_TASK) == flat

  assert resolve_oracle_dir(tmp_path / "missing", "chrome", EXAMPLE_TASK) is None


def test_load_human_reference_steps_schema_aliases(tmp_path: Path):
  task_dir = tmp_path / "chrome" / EXAMPLE_TASK
  task_dir.mkdir(parents=True)
  png = task_dir / "obs1.png"
  png.write_bytes(b"\x89PNG\r\n\x1a\n")
  (task_dir / "human_traj.json").write_text(
    json.dumps(
      {
        "task_id": EXAMPLE_TASK,
        "domain": "chrome",
        "oracle_status": "partial",
        "human_steps": [
          {
            "action": "`HOTKEY` Ctrl+Shift+T",
            "image_path": "obs1.png",
          }
        ],
      }
    ),
    encoding="utf-8",
  )
  steps, status = load_human_reference_steps(oracle_dir=task_dir)
  assert status == "partial"
  assert len(steps) == 1
  assert "HOTKEY" in steps[0]["action_text"]
  assert steps[0]["image_path"] and Path(steps[0]["image_path"]).exists()


def test_rejudge_pilot_dry_run_with_ready_oracle(tmp_path: Path):
  """Spot-check 06fe7178 layout + gate opens for ready status (no API call)."""
  run_dir = tmp_path / "run" / "chrome" / EXAMPLE_TASK / "seed0"
  run_dir.mkdir(parents=True)
  (run_dir / "manifest.json").write_text(
    json.dumps(
      {
        "task_id": EXAMPLE_TASK,
        "domain": "chrome",
        "success": False,
        "canonical_instruction": "Bring back the last tab",
      }
    ),
    encoding="utf-8",
  )
  # Minimal trace so attribute_run could load if not dry-run
  (run_dir / "trace.jsonl").write_text(
    json.dumps(
      {
        "step": 1,
        "instruction": "Bring back the last tab",
        "observation": {"screenshot_path": None},
        "action": {"type": "hotkey", "raw_code": "pyautogui.hotkey('ctrl','shift','t')"},
        "reward": 0,
        "done": False,
        "info": {},
      }
    )
    + "\n",
    encoding="utf-8",
  )

  oracle_dir = tmp_path / "oracle" / "chrome" / EXAMPLE_TASK
  oracle_dir.mkdir(parents=True)
  (oracle_dir / "human_step_1_obs.png").write_bytes(b"\x89PNG\r\n\x1a\n")
  (oracle_dir / "human_traj.json").write_text(
    json.dumps(
      {
        "task_id": EXAMPLE_TASK,
        "domain": "chrome",
        "oracle_status": "ready",
        "steps": [
          {
            "step": 1,
            "action_text": "`HOTKEY` Ctrl+Shift+T",
            "observation_screenshot": "human_step_1_obs.png",
            "ok": True,
          }
        ],
      }
    ),
    encoding="utf-8",
  )

  out = tmp_path / "failure_labels_osworld_v1.jsonl"
  proc = subprocess.run(
    [
      sys.executable,
      str(ROOT / "scripts" / "rejudge_pilot.py"),
      "--run-dir",
      str(tmp_path / "run"),
      "--oracle-root",
      str(tmp_path / "oracle"),
      "--output",
      str(out),
      "--dry-run",
    ],
    cwd=str(ROOT),
    capture_output=True,
    text=True,
    check=False,
  )
  assert proc.returncode == 0, proc.stderr
  lines = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
  assert len(lines) == 1
  assert lines[0]["oracle_status"] == "ready"
  assert lines[0]["judge_context_version"] == "osworld_v1"
  assert lines[0]["human_steps"] == 1
  assert lines[0]["dry_run"] is True
