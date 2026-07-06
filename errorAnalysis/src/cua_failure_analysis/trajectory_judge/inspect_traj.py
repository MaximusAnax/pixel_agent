"""Step-1 schema probe: discover how each run's trajectories are stored on disk.

Each OSWorld run unzips to <run_root>/<domain>/<task_id>/ with a `result.txt`
(reward) plus per-step logs + screenshots whose field/file names vary per harness.
This prints, for a few task dirs (preferring failures), the file listing and the
keys/sample of the first trajectory record, so we can finalize `parse_trajs.py`.

    python inspect_traj.py <run_root_dir> [num_dirs]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def read_reward(task_dir: Path) -> float | None:
    rt = task_dir / "result.txt"
    if not rt.exists():
        return None
    try:
        return float(rt.read_text().strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return None


def find_task_dirs(run_root: Path) -> list[Path]:
    return [p.parent for p in run_root.rglob("result.txt")]


def peek_jsonl(path: Path, n: int = 2) -> None:
    print(f"    -> first record(s) of {path.name}:")
    with path.open() as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if isinstance(rec, dict):
                    print(f"       keys: {list(rec.keys())}")
                    for k, v in rec.items():
                        sv = json.dumps(v) if not isinstance(v, str) else v
                        print(f"         {k!r}: {sv[:200]}")
                else:
                    print(f"       (non-dict line: {type(rec)}) {str(rec)[:200]}")
            except json.JSONDecodeError:
                print(f"       (not JSON) {line[:200]}")


def peek_json(path: Path) -> None:
    print(f"    -> {path.name} (json):")
    try:
        data = json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        print(f"       could not parse: {e}")
        return
    if isinstance(data, dict):
        print(f"       top-level keys: {list(data.keys())}")
    elif isinstance(data, list):
        print(f"       list of {len(data)}; first item type {type(data[0]).__name__ if data else 'n/a'}")
        if data and isinstance(data[0], dict):
            print(f"       first item keys: {list(data[0].keys())}")


def inspect_dir(task_dir: Path) -> None:
    reward = read_reward(task_dir)
    files = sorted(task_dir.iterdir())
    pngs = [f for f in files if f.suffix.lower() in (".png", ".jpg", ".jpeg")]
    others = [f for f in files if f not in pngs]
    print(f"\n=== {task_dir.parent.name}/{task_dir.name}  (reward={reward}) ===")
    print(f"  {len(pngs)} image(s); other files:")
    for f in others:
        print(f"    {f.name}  ({f.stat().st_size} bytes)")
    if pngs:
        print(f"  sample image names: {[p.name for p in pngs[:3]]} ... {[p.name for p in pngs[-1:]]}")
    for f in others:
        if f.suffix == ".jsonl" or f.name.endswith(".jsonl"):
            peek_jsonl(f)
        elif f.suffix == ".json" and f.name not in ("result.json",):
            peek_json(f)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    run_root = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    task_dirs = find_task_dirs(run_root)
    print(f"Run root: {run_root}")
    print(f"Found {len(task_dirs)} task dirs.")
    domains = sorted({d.parent.name for d in task_dirs})
    print(f"Domains: {domains}")

    failures = [d for d in task_dirs if read_reward(d) == 0.0]
    successes = [d for d in task_dirs if read_reward(d) == 1.0]
    print(f"Failures (reward 0.0): {len(failures)} | Successes (1.0): {len(successes)} "
          f"| Total with reward: {sum(1 for d in task_dirs if read_reward(d) is not None)}")

    print("\n########## SAMPLE FAILED TRAJECTORIES ##########")
    for d in failures[:n]:
        inspect_dir(d)


if __name__ == "__main__":
    main()
