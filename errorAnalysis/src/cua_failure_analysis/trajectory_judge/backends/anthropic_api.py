"""API backend: Anthropic Claude judging the whole trajectory.

Uses the SAME system prompt, step log, screenshot selection, and output schema as
the local vLLM backend — only the transport differs. Structured output is forced
via a single tool whose ``input_schema`` is the ``Classification`` JSON schema
(the API analogue of vLLM guided decoding), with a robust text-JSON fallback.

The ``anthropic`` SDK is imported lazily so the local backend never requires it.
"""

from __future__ import annotations

import base64
import io
import json
import os
from dataclasses import dataclass
from typing import Iterator

from PIL import Image

from cua_failure_analysis.trajectory_judge.judge_common import (
    DEFAULT_API_MODEL,
    JudgeOutput,
    parse_json_obj,
    parse_json_text,
    select_images,
)
from cua_failure_analysis.trajectory_judge.judge_prompt import SYSTEM_PROMPT, build_messages
from cua_failure_analysis.trajectory_judge.schema import Classification

TOOL_NAME = "submit_classification"


@dataclass
class AnthropicConfig:
    model: str = DEFAULT_API_MODEL
    api_key: str | None = None  # falls back to $ANTHROPIC_API_KEY
    max_images: int = 10
    max_side: int = 1280
    max_tokens: int = 1024
    jpeg_quality: int = 85  # screenshots are re-encoded to JPEG to cut token cost


def _jpeg_b64(img: Image.Image, quality: int) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.standard_b64encode(buf.getvalue()).decode("ascii")


class AnthropicTrajectoryJudge:
    name = "api"

    def __init__(self, config: AnthropicConfig | None = None) -> None:
        self.config = config or AnthropicConfig()
        self._client = None
        self._tool = {
            "name": TOOL_NAME,
            "description": (
                "Record the failure-mode classification for this failed "
                "computer-use-agent trajectory."
            ),
            "input_schema": Classification.model_json_schema(),
        }

    @property
    def model(self) -> str:
        return self.config.model

    def _ensure_client(self):
        if self._client is not None:
            return
        from anthropic import Anthropic

        key = self.config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "No Anthropic API key. Set ANTHROPIC_API_KEY or pass --api-key."
            )
        self._client = Anthropic(api_key=key)

    def _content_blocks(self, traj: dict) -> tuple[list[dict], int]:
        """Map build_messages' interleaved text/image placeholders onto Anthropic
        content blocks, substituting each placeholder with the next image (order
        is preserved by build_messages)."""
        kept, images = select_images(traj, self.config.max_images, self.config.max_side)
        _system, user = build_messages(traj, kept)
        img_iter = iter(images)
        blocks: list[dict] = []
        for part in user["content"]:
            if part["type"] == "text":
                blocks.append({"type": "text", "text": part["text"]})
            elif part["type"] == "image":
                img = next(img_iter, None)
                if img is None:
                    continue
                blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": _jpeg_b64(img, self.config.jpeg_quality),
                    },
                })
        return blocks, len(images)

    def classify(self, traj: dict) -> JudgeOutput:
        self._ensure_client()
        blocks, n_img = self._content_blocks(traj)
        response = self._client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=SYSTEM_PROMPT,
            temperature=0.0,
            tools=[self._tool],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{"role": "user", "content": blocks}],
        )
        usage = {
            "input_tokens": getattr(response.usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(response.usage, "output_tokens", 0) or 0,
            "model": self.config.model,
        }

        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == TOOL_NAME:
                raw = json.dumps(block.input, ensure_ascii=False)
                parsed, parse_ok = parse_json_obj(block.input)
                return JudgeOutput(parsed, parse_ok, raw, n_img, usage)

        # Fallback: no tool block (e.g. the model narrated JSON as text).
        raw = "".join(
            b.text for b in response.content if getattr(b, "type", None) == "text"
        )
        parsed, parse_ok = parse_json_text(raw)
        return JudgeOutput(parsed, parse_ok, raw, n_img, usage)

    def iter_classify(self, todo: list[dict], chunk: int | None = None) -> Iterator[tuple[dict, JudgeOutput]]:
        for traj in todo:
            yield traj, self.classify(traj)
