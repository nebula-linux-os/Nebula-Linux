"""Vision capability — send images to a multimodal Ollama model.

Design: the primary agent model (which may not be multimodal) never sees
the raw image. When it calls see_screen or describe_image, the tool
captures/reads the image, base64-encodes it, and sends it to a separately
configured VISION MODEL in a one-shot call. The vision model's textual
description is what comes back into the tool loop.

This keeps the main planner model unchanged and lets you run vision on
top of small text-only models like qwen2.5 or gemma.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

import requests

OLLAMA_GENERATE = "http://localhost:11434/api/generate"

# Ollama vision models, in preference order. First one that's installed wins.
VISION_MODEL_CANDIDATES = [
    "llama3.2-vision:11b",
    "llama3.2-vision",
    "qwen2-vl:7b",
    "qwen2.5-vl:7b",
    "gemma3:4b",
    "moondream",
    "llava:13b",
    "llava:7b",
    "llava",
    "bakllava",
]

DEFAULT_PROMPT = (
    "Describe what you see in this image in concrete detail: the main "
    "subject, any text visible, UI elements if it's a screenshot, and "
    "anything that would help someone act on it. Be direct — no filler."
)

_cached_vision_model: str | None = None
_cache_probed = False


def _list_installed() -> set[str]:
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        resp.raise_for_status()
        return {m["name"] for m in resp.json().get("models", [])}
    except Exception:
        return set()


def _matches_installed(candidate: str, installed: set[str]) -> str | None:
    """Return the exact installed tag matching a candidate (with or without :tag)."""
    if candidate in installed:
        return candidate
    if ":" not in candidate:
        for name in installed:
            if name.startswith(candidate + ":"):
                return name
    return None


def pick_vision_model(override: str | None = None) -> str | None:
    global _cached_vision_model, _cache_probed
    if override:
        return override
    if _cache_probed:
        return _cached_vision_model
    _cache_probed = True

    env_pick = os.environ.get("NOVA_VISION_MODEL")
    if env_pick:
        _cached_vision_model = env_pick
        return env_pick

    installed = _list_installed()
    for candidate in VISION_MODEL_CANDIDATES:
        match = _matches_installed(candidate, installed)
        if match:
            _cached_vision_model = match
            return match
    _cached_vision_model = None
    return None


def _encode_image(path: str) -> tuple[str, int] | tuple[None, int]:
    p = Path(path).expanduser()
    if not p.exists():
        return None, 0
    data = p.read_bytes()
    return base64.b64encode(data).decode("ascii"), len(data)


def describe(image_path: str, prompt: str = DEFAULT_PROMPT, model: str | None = None) -> dict:
    """Ask a vision model to describe an image on disk."""
    vision_model = pick_vision_model(model)
    if not vision_model:
        return {
            "error": "no vision-capable model installed",
            "hint": "pull one, e.g. `ollama pull llama3.2-vision` or `ollama pull moondream`",
        }

    encoded, size = _encode_image(image_path)
    if encoded is None:
        return {"error": f"image not found: {image_path}"}

    try:
        resp = requests.post(
            OLLAMA_GENERATE,
            json={
                "model": vision_model,
                "prompt": prompt,
                "images": [encoded],
                "stream": False,
            },
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.ConnectionError:
        return {"error": "could not reach Ollama at localhost:11434"}
    except requests.HTTPError as e:
        return {"error": f"Ollama HTTP error: {e}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

    return {
        "model": vision_model,
        "image": str(image_path),
        "bytes": size,
        "description": (data.get("response") or "").strip(),
    }
