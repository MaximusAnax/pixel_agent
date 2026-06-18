#!/usr/bin/env python3
"""AgentNetBench offline pilot — clone OpenCUA eval and run detectors on outputs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENCUA_REPO = ROOT / "external" / "OpenCUA"
AGENTNETBENCH = OPENCUA_REPO / "AgentNetBench"


def ensure_opencua() -> None:
  if AGENTNETBENCH.exists():
    return
  OPENCUA_REPO.parent.mkdir(parents=True, exist_ok=True)
  print("Cloning xlang-ai/OpenCUA (shallow)...")
  subprocess.run(
    [
      "git",
      "clone",
      "--depth",
      "1",
      "https://github.com/xlang-ai/OpenCUA.git",
      str(OPENCUA_REPO),
    ],
    check=True,
  )


def run_pilot(output_dir: Path, model_endpoint: str | None) -> dict:
  ensure_opencua()
  output_dir.mkdir(parents=True, exist_ok=True)
  readme = AGENTNETBENCH / "README.md"
  instructions = {
    "status": "setup",
    "opencua_path": str(OPENCUA_REPO),
    "agentnetbench_path": str(AGENTNETBENCH),
    "next_steps": [
      "Install OpenCUA / AgentNetBench deps per upstream README",
      f"Run offline eval; write per-step predictions to {output_dir}",
      "python -m cua_failure_analysis.cli attribute --traces-root ...",
    ],
  }
  if model_endpoint:
    instructions["vllm_endpoint"] = model_endpoint
  if readme.exists():
    instructions["upstream_readme"] = str(readme)
  out_path = output_dir / "pilot_manifest.json"
  out_path.write_text(json.dumps(instructions, indent=2), encoding="utf-8")
  return instructions


def main() -> None:
  p = argparse.ArgumentParser(description="AgentNetBench offline pilot setup")
  p.add_argument("--output", type=Path, default=ROOT / "data" / "agentnetbench")
  p.add_argument("--vllm-url", default=None)
  args = p.parse_args()
  manifest = run_pilot(args.output, args.vllm_url)
  print(json.dumps(manifest, indent=2))
  print("\nPilot manifest written. Complete upstream AgentNetBench eval on Bridges.")


if __name__ == "__main__":
  main()
