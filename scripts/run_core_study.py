#!/usr/bin/env python3
"""Generate OSWorld run matrix and SLURM job stubs for pilot / core study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = ROOT / "config" / "stratified_tasks.json"
MODELS_PATH = ROOT / "config" / "models.yaml"


def load_tasks(phase: str) -> list[dict]:
  data = json.loads(TASKS_PATH.read_text())
  tasks = data["tasks"]
  if phase == "pilot":
    pilot_ids = set(data.get("pilot_task_ids", [t["task_id"] for t in tasks[:30]]))
    return [t for t in tasks if t["task_id"] in pilot_ids]
  return tasks


def main() -> None:
  p = argparse.ArgumentParser()
  p.add_argument("--phase", choices=["pilot", "core"], default="pilot")
  p.add_argument("--output-dir", type=Path, default=ROOT / "data" / "run_matrix")
  args = p.parse_args()

  import yaml

  models_cfg = yaml.safe_load(MODELS_PATH.read_text())
  agents = [m for m in models_cfg["agents"] if m["role"] != "optional_mid"]
  seeds = models_cfg["study"]["seeds"]
  tasks = load_tasks(args.phase)

  matrix = []
  for model in agents:
    for seed in seeds:
      for task in tasks:
        matrix.append(
          {
            "model_id": model["id"],
            "seed": seed,
            "task_id": task["task_id"],
            "domain": task["domain"],
            "task_tags": task["task_tags"],
            "max_steps": models_cfg["study"]["max_steps"],
            "vllm_served_name": model["served_name"],
            "osworld_agent": model["osworld_agent"],
          }
        )

  args.output_dir.mkdir(parents=True, exist_ok=True)
  out = args.output_dir / f"{args.phase}_matrix.json"
  out.write_text(json.dumps({"runs": matrix, "count": len(matrix)}, indent=2))
  print(f"Wrote {len(matrix)} runs to {out}")

  # SLURM array stub
  stub = args.output_dir / f"run_{args.phase}_osworld.sbatch"
  stub.write_text(
    f"""#!/bin/bash
#SBATCH -A cis260099p
#SBATCH -p RM-shared
#SBATCH -t 8:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -J osworld-{args.phase}
#SBATCH -o logs/osworld-{args.phase}-%A_%a.out

# Array size: {len(matrix)} — adjust % array spec after splitting batches
# Requires OSWorld installed and VLLM_BASE_URL set to Bridges GPU node

MATRIX="{out}"
echo "Run matrix: $MATRIX"
echo "Set OPENAI_BASE_URL and invoke OSWorld per docs/vllm_runbook.md"
""",
    encoding="utf-8",
  )
  print(f"Wrote SLURM stub to {stub}")


if __name__ == "__main__":
  main()
