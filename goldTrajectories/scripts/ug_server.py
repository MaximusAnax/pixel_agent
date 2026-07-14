#!/usr/bin/env python3
"""UGround-V1-7B grounding server (runs in venv-ground on the GPU).

POST /ground  {"image": <base64 PNG/JPEG>, "description": "the address bar"}
          ->  {"x": <px>, "y": <px>, "nx": <0-1000>, "ny": <0-1000>, "raw": "(..)"}

UGround takes a screenshot + a natural-language referring expression and returns a
point in normalized [0,1000) coords; we rescale to pixels using the image's own
size. Temperature 0 for deterministic grounding. Kept as a separate process/venv
because UGround needs transformers>=4.49 while the OSWorld driver pins 4.35.
"""
from __future__ import annotations

import argparse
import base64
import io
import re
import threading

import torch
from flask import Flask, jsonify, request
from PIL import Image
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
from qwen_vl_utils import process_vision_info

PROMPT = """Your task is to help the user identify the precise coordinates (x, y) of a specific area/element/object on the screen based on a description.
- Your response should aim to point to the center or a representative point within the described area/element/object as accurately as possible.
- If the description is unclear or ambiguous, infer the most relevant area or element based on its likely context or purpose.
- Your answer should be a single string (x, y) corresponding to the point of interest.

Description: {description}

Answer:"""

app = Flask(__name__)
STATE = {}
GEN_LOCK = threading.Lock()


def load(model_path: str, max_pixels: int, device_map: str = "cuda"):
    print(f"[ug] loading {model_path} (max_pixels={max_pixels}, device_map={device_map}) ...", flush=True)
    kwargs = {}
    if device_map == "auto":
        # Cap per-GPU weight placement to leave activation headroom; without this,
        # auto packs GPU 0 to the brim and 1080p screenshots OOM at inference.
        # GPU 0 needs extra: it hosts the vision tower + embeddings.
        max_memory = {}
        for i in range(torch.cuda.device_count()):
            total_gib = torch.cuda.get_device_properties(i).total_memory / 2**30
            headroom = 10 if i == 0 else 6
            max_memory[i] = f"{max(1, int(total_gib - headroom))}GiB"
        kwargs["max_memory"] = max_memory
        print(f"[ug] max_memory caps: {max_memory}", flush=True)
    # sdpa, not eager: eager materializes the full vision-tower attention matrix
    # (~10k patch tokens for a 1080p screenshot -> 6+ GiB softmax alloc -> OOM).
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_path, torch_dtype=torch.bfloat16, device_map=device_map, attn_implementation="sdpa",
        **kwargs,
    )
    processor = AutoProcessor.from_pretrained(model_path, min_pixels=256 * 28 * 28, max_pixels=max_pixels)
    model.eval()
    STATE["model"], STATE["processor"] = model, processor
    print("[ug] model ready", flush=True)


@app.get("/health")
def health():
    return jsonify(ok="model" in STATE)


@app.post("/ground")
def ground():
    data = request.get_json(force=True)
    img = Image.open(io.BytesIO(base64.b64decode(data["image"]))).convert("RGB")
    W, H = img.size
    desc = data["description"]

    messages = [{"role": "user", "content": [
        {"type": "image", "image": img},
        {"type": "text", "text": PROMPT.format(description=desc)},
    ]}]
    processor = STATE["processor"]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs,
                       padding=True, return_tensors="pt").to("cuda")
    # Serialize generation: concurrent batch shards otherwise stack activation
    # memory on GPU 0 and OOM. Requests queue here instead.
    with GEN_LOCK, torch.no_grad():
        gen = STATE["model"].generate(**inputs, max_new_tokens=32, do_sample=False)
    out = processor.batch_decode(gen[:, inputs.input_ids.shape[1]:],
                                 skip_special_tokens=True)[0].strip()

    nums = re.findall(r"-?\d+\.?\d*", out)
    if len(nums) < 2:
        return jsonify(error=f"could not parse coords from {out!r}"), 422
    nx, ny = float(nums[0]), float(nums[1])
    x, y = int(round(nx / 1000.0 * W)), int(round(ny / 1000.0 * H))
    x, y = max(0, min(W - 1, x)), max(0, min(H - 1, y))
    return jsonify(x=x, y=y, nx=nx, ny=ny, raw=out, w=W, h=H)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="/data/group_data/mattlab/raghavg3/osworld_env/models/UGround-V1-7B")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8500)
    # Default ~native 1080p (1920x1080) so small targets aren't lost to downscaling.
    ap.add_argument("--max-pixels", type=int, default=1920 * 1080)
    # "cuda" for a single GPU (7B); "auto" to shard a 72B across multiple GPUs.
    ap.add_argument("--device-map", default="cuda")
    args = ap.parse_args()
    load(args.model, args.max_pixels, args.device_map)
    app.run(host=args.host, port=args.port, threaded=False)
