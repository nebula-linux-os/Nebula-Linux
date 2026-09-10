"""Vision tools — let the agent see the screen and read images.

Both tools funnel through agent.vision.describe(), which picks the best
installed multimodal Ollama model. The main planner model stays
text-only; vision is a sub-call.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from .tools_desktop import take_screenshot
from .vision import describe, pick_vision_model


def see_screen(question: str = "") -> dict:
    """Take a screenshot and describe it with a vision model."""
    shot = take_screenshot()
    if "error" in shot:
        return shot

    prompt_extra = f"\n\nUser's question: {question}" if question.strip() else ""
    result = describe(
        shot["path"],
        prompt=(
            "You are looking at a screenshot of the user's desktop. "
            "Describe what's on the screen: active window(s), any visible "
            "text or UI elements, what the user seems to be doing. Be "
            "concrete and actionable."
            + prompt_extra
        ),
    )
    # Screenshots go to a temp file; clean it up after describing.
    try:
        Path(shot["path"]).unlink(missing_ok=True)
    except Exception:
        pass
    if "error" in result:
        return result
    result["captured"] = True
    return result


def describe_image(path: str, question: str = "") -> dict:
    """Describe an image file (PNG/JPG/etc.) with a vision model."""
    if question.strip():
        prompt = (
            f"Look at this image and answer the user's question directly.\n\n"
            f"Question: {question}"
        )
    else:
        prompt = None
    result = describe(path, prompt=prompt) if prompt else describe(path)
    return result


def vision_info() -> dict:
    """Report which vision model is available (or none)."""
    model = pick_vision_model()
    return {
        "vision_available": model is not None,
        "vision_model": model,
    }


VISION_TOOL_FUNCTIONS = {
    "see_screen": see_screen,
    "describe_image": describe_image,
    "vision_info": vision_info,
}

VISION_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "see_screen",
            "description": "Take a screenshot of the user's desktop and get a description of what's on it from a vision model. Use when you need to see the current state of the user's screen — active app, error dialog, GUI status, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Optional specific question about the screen (e.g. 'is chrome open', 'what's the error message'). Leave empty for a general description.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_image",
            "description": "Describe or answer questions about an image file (PNG/JPG/GIF/etc.) on disk. Use for user-supplied images, screenshots the user references, or images produced by other tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the image file"},
                    "question": {
                        "type": "string",
                        "description": "Optional specific question about the image",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vision_info",
            "description": "Check whether a vision-capable model is installed and available for see_screen and describe_image. Call this before trying to use vision if you're unsure.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
