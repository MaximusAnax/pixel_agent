"""Unified whole-trajectory judge runner: local vLLM and/or Anthropic API.

Reads normalized failures (from ``parse_trajs.py``) and writes one classification
per line, in the SAME schema regardless of backend, so ``compare_judges.py`` and
the viewer can diff local-vs-API (or 7B-vs-32B) directly. Runs are resumable:
trajectories already present in an output file are skipped.

Examples (run from ``errorAnalysis/``):
    # local vLLM judge (Qwen2.5-VL-7B) — needs a GPU
    python -m cua_failure_analysis.trajectory_judge.run_judge \
        --failures outputs/failures.jsonl --backend local --limit 40

    # Claude API judge — needs ANTHROPIC_API_KEY
    python -m cua_failure_analysis.trajectory_judge.run_judge \
        --failures outputs/failures.jsonl --backend api --api-model claude-sonnet-4-6

    # both, same trajectories, two output files for an apples-to-apples compare
    python -m cua_failure_analysis.trajectory_judge.run_judge \
        --failures outputs/failures.jsonl --backend both --limit 40
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from cua_failure_analysis.trajectory_judge.judge_common import (
    DEFAULT_API_MODEL,
    DEFAULT_LOCAL_MODEL,
    already_done,
    build_record,
    load_failures,
    stratified_head,
    uid_of,
)

DEFAULT_LOCAL_OUT = "outputs/classifications_local.jsonl"
DEFAULT_API_OUT = "outputs/classifications_api.jsonl"


def _run_backend(backend, trajs: list[dict], out_path: Path, chunk: int) -> None:
    import json

    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = already_done(out_path)
    todo = [t for t in trajs if uid_of(t) not in done]
    print(
        f"[{backend.name}:{backend.model}] {len(trajs)} in scope; "
        f"{len(done)} already done; processing {len(todo)} -> {out_path}",
        flush=True,
    )
    if not todo:
        return

    n_ok = total = 0
    with_usage = False
    in_tok = out_tok = 0
    for traj, result in backend.iter_classify(todo, chunk):
        rec = build_record(traj, backend.name, backend.model, result)
        with out_path.open("a") as fout:
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
        total += 1
        n_ok += result.parse_ok
        if result.usage:
            with_usage = True
            in_tok += result.usage.get("input_tokens", 0)
            out_tok += result.usage.get("output_tokens", 0)
        if total % 20 == 0 or total == len(todo):
            msg = f"  [{backend.name}] {total}/{len(todo)} done, parsed OK {n_ok}"
            if with_usage:
                msg += f"  (tokens in/out: {in_tok}/{out_tok})"
            print(msg, flush=True)
    print(f"[{backend.name}] finished. Parsed OK: {n_ok}/{total}. Wrote -> {out_path}")


def _make_local(args):
    from cua_failure_analysis.trajectory_judge.backends.local_vllm import (
        LocalVLLMConfig,
        LocalVLLMJudge,
    )

    cfg = LocalVLLMConfig(
        model=args.model,
        max_images=args.max_images,
        max_model_len=args.max_model_len,
        max_pixels=args.max_pixels,
        max_side=args.max_side,
        tensor_parallel_size=args.tensor_parallel_size,
        gpu_mem_frac=args.gpu_mem_frac,
        max_tokens=args.max_tokens,
        seed=args.seed,
    )
    return LocalVLLMJudge(cfg)


def _make_api(args):
    from cua_failure_analysis.trajectory_judge.backends.anthropic_api import (
        AnthropicConfig,
        AnthropicTrajectoryJudge,
    )

    cfg = AnthropicConfig(
        model=args.api_model,
        api_key=args.api_key,
        max_images=args.max_images,
        max_side=args.max_side,
        max_tokens=args.max_tokens,
    )
    return AnthropicTrajectoryJudge(cfg)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--failures", default="outputs/failures.jsonl")
    ap.add_argument("--backend", choices=["local", "api", "both"], default="local")
    ap.add_argument("--out", default=None,
                    help="output path for a single backend; ignored when --backend both")
    ap.add_argument("--local-out", default=DEFAULT_LOCAL_OUT)
    ap.add_argument("--api-out", default=DEFAULT_API_OUT)
    ap.add_argument("--limit", type=int, default=0, help="0 = all; stratified across models/domains")
    ap.add_argument("--chunk", type=int, default=48,
                    help="trajectories per vLLM generate() batch (local backend)")

    # shared prompt/image budget
    ap.add_argument("--max-images", type=int, default=10)
    ap.add_argument("--max-side", type=int, default=1280, help="pre-downscale longest image side")
    ap.add_argument("--max-tokens", type=int, default=1024)

    # local (vLLM) options
    ap.add_argument("--model", default=DEFAULT_LOCAL_MODEL, help="local judge model")
    ap.add_argument("--max-model-len", type=int, default=32768)
    ap.add_argument("--max-pixels", type=int, default=1024 * 1024)
    ap.add_argument("--tensor-parallel-size", type=int, default=1)
    ap.add_argument("--gpu-mem-frac", type=float, default=0.9)
    ap.add_argument("--seed", type=int, default=0)

    # api (Anthropic) options
    ap.add_argument("--api-model", default=DEFAULT_API_MODEL)
    ap.add_argument("--api-key", default=None, help="defaults to $ANTHROPIC_API_KEY")
    args = ap.parse_args()

    trajs = load_failures(Path(args.failures))
    if args.limit:
        # Select the sample once (deterministically) so a --backend both run
        # judges the SAME trajectories with local and API.
        trajs = stratified_head(trajs, args.limit)

    jobs: list[tuple[object, Path]] = []
    if args.backend in ("local", "both"):
        out = Path(args.out) if (args.out and args.backend == "local") else Path(args.local_out)
        jobs.append((_make_local(args), out))
    if args.backend in ("api", "both"):
        out = Path(args.out) if (args.out and args.backend == "api") else Path(args.api_out)
        jobs.append((_make_api(args), out))

    for backend, out_path in jobs:
        _run_backend(backend, trajs, out_path, args.chunk)


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
