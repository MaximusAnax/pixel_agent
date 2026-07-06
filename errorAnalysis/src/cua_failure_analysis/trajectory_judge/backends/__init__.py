"""Interchangeable whole-trajectory judge backends (local vLLM / Anthropic API).

Every backend exposes:
  - ``name``: short backend id ("local" | "api"), recorded in each output row;
  - ``model``: the concrete model id being used;
  - ``iter_classify(todo, chunk) -> Iterator[tuple[traj, JudgeOutput]]``: yields a
    result per input trajectory (local yields per batch; API yields one at a
    time). The runner writes each result immediately, so runs stay resumable.
"""
