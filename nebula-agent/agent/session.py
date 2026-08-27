"""Session logging — saves full task transcripts to JSON for review.

Each session gets its own timestamped file under ~/.nebula-agent/sessions/.
The log captures every message (system, user, assistant, tool) plus metadata
so you can replay or debug what the agent did.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

SESSIONS_DIR = Path.home() / ".nebula-agent" / "sessions"


class Session:
    def __init__(self, task: str, model: str) -> None:
        self.task = task
        self.model = model
        self.start_time = time.time()
        self.events: list[dict] = []
        self._file = self._make_path()

    def _make_path(self) -> Path:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S", time.localtime(self.start_time))
        slug = self.task[:40].replace(" ", "_").replace("/", "-")
        return SESSIONS_DIR / f"{ts}_{slug}.json"

    def log(self, role: str, content: str, tool_name: str = "", tool_args: dict | None = None) -> None:
        event: dict = {"time": time.time(), "role": role, "content": content}
        if tool_name:
            event["tool"] = tool_name
        if tool_args:
            event["args"] = tool_args
        self.events.append(event)

    def save(self, outcome: str, steps: int) -> Path:
        record = {
            "task": self.task,
            "model": self.model,
            "start": self.start_time,
            "end": time.time(),
            "duration_s": round(time.time() - self.start_time, 1),
            "steps": steps,
            "outcome": outcome,
            "events": self.events,
        }
        self._file.write_text(json.dumps(record, indent=2))
        return self._file
