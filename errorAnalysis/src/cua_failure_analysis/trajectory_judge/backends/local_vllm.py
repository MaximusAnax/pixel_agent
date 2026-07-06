"""Local backend: offline, batched vLLM inference with guided-JSON decoding.

Loads a Qwen2.5-VL model once, then classifies trajectories in batches — the
image tensors for a batch are freed between chunks (memory) and results are
yielded per chunk so the runner can write incrementally (resumability). Guided
decoding forces the ``Classification`` JSON schema, so parse rate is ~100%.

vLLM + transformers are imported lazily (heavy, GPU-only) so that importing this
module — or running the API backend — never requires them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from cua_failure_analysis.trajectory_judge.judge_common import (
    DEFAULT_LOCAL_MODEL,
    JudgeOutput,
    parse_json_text,
    select_images,
)
from cua_failure_analysis.trajectory_judge.judge_prompt import build_messages
from cua_failure_analysis.trajectory_judge.schema import Classification


@dataclass
class LocalVLLMConfig:
    model: str = DEFAULT_LOCAL_MODEL
    max_images: int = 10
    max_model_len: int = 32768
    max_pixels: int = 1024 * 1024  # per-image pixel cap for the Qwen processor
    max_side: int = 1280           # pre-downscale before the processor sees it
    tensor_parallel_size: int = 1
    gpu_mem_frac: float = 0.9
    max_tokens: int = 1024
    seed: int = 0


class LocalVLLMJudge:
    name = "local"

    def __init__(self, config: LocalVLLMConfig | None = None) -> None:
        self.config = config or LocalVLLMConfig()
        self._llm = None
        self._processor = None
        self._sampling = None

    @property
    def model(self) -> str:
        return self.config.model

    def _ensure_loaded(self) -> None:
        if self._llm is not None:
            return
        cfg = self.config
        from transformers import AutoProcessor
        from vllm import LLM, SamplingParams
        try:
            from vllm.sampling_params import GuidedDecodingParams
        except ImportError:  # pragma: no cover
            from vllm import GuidedDecodingParams  # type: ignore

        self._processor = AutoProcessor.from_pretrained(cfg.model, max_pixels=cfg.max_pixels)
        self._llm = LLM(
            model=cfg.model,
            max_model_len=cfg.max_model_len,
            limit_mm_per_prompt={"image": cfg.max_images},
            mm_processor_kwargs={"max_pixels": cfg.max_pixels},
            tensor_parallel_size=cfg.tensor_parallel_size,
            gpu_memory_utilization=cfg.gpu_mem_frac,
            seed=cfg.seed,
        )
        guided = GuidedDecodingParams(json=Classification.model_json_schema())
        self._sampling = SamplingParams(
            temperature=0.0, max_tokens=cfg.max_tokens, guided_decoding=guided
        )

    def _build_item(self, traj: dict) -> tuple[dict, int]:
        kept, images = select_images(traj, self.config.max_images, self.config.max_side)
        messages = build_messages(traj, kept)
        prompt = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        item: dict = {"prompt": prompt}
        if images:
            item["multi_modal_data"] = {"image": images}
        return item, len(images)

    def iter_classify(self, todo: list[dict], chunk: int = 48) -> Iterator[tuple[dict, JudgeOutput]]:
        self._ensure_loaded()
        for c0 in range(0, len(todo), chunk):
            batch = todo[c0:c0 + chunk]
            items, metas = [], []
            for traj in batch:
                item, n_img = self._build_item(traj)
                items.append(item)
                metas.append((traj, n_img))
            outputs = self._llm.generate(items, self._sampling)
            for (traj, n_img), out in zip(metas, outputs):
                raw = out.outputs[0].text.strip()
                parsed, parse_ok = parse_json_text(raw)
                yield traj, JudgeOutput(parsed=parsed, parse_ok=parse_ok, raw=raw, n_images=n_img)
