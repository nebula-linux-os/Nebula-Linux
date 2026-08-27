"""Model profiles and routing — pick the right model for the task.

Each profile declares a model's strengths, RAM requirement, and speed
tier. The router classifies an incoming task and picks the best available
model, falling back gracefully if a large model won't fit in RAM.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field

import requests

OLLAMA_API = "http://localhost:11434"


@dataclass
class ModelProfile:
    name: str
    strengths: list[str]
    ram_gb: float
    speed: str  # "fast", "medium", "slow"
    priority: int = 0  # higher = preferred when multiple match

    def matches(self, category: str) -> bool:
        return category in self.strengths or "general" in self.strengths


DEFAULT_PROFILES = [
    ModelProfile("gemma4:e2b", ["general", "quick", "reasoning"], 4.5, "medium", priority=2),
    ModelProfile("qwen2.5:3b", ["general", "quick"], 2.5, "fast", priority=1),
    ModelProfile("qwen2.5:7b", ["general", "coding", "system"], 5.0, "medium", priority=5),
    ModelProfile("llama3.1:8b", ["general", "coding", "reasoning"], 5.5, "medium", priority=4),
    ModelProfile("codellama:7b", ["coding"], 5.0, "medium", priority=6),
    ModelProfile("mistral-nemo", ["general", "reasoning"], 7.5, "medium", priority=3),
    ModelProfile("qwen2.5:14b", ["coding", "reasoning", "system"], 10.0, "slow", priority=8),
    ModelProfile("llama3.1:70b", ["coding", "reasoning", "system", "general"], 42.0, "slow", priority=10),
    ModelProfile("deepseek-coder-v2:16b", ["coding"], 10.5, "slow", priority=7),
]

TASK_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)(write|create|build|code|script|function|class|implement|refactor|debug|fix bug)", "coding"),
    (r"(?i)(install|update|upgrade|remove|uninstall|package|service|process|disk|cpu|ram|network|firewall|port)", "system"),
    (r"(?i)(explain|why|how does|what is|summarize|analyze|compare|reason|think)", "reasoning"),
    (r"(?i)(list|show|read|open|check|look|find|search|what files)", "quick"),
]


def classify_task(task: str) -> str:
    for pattern, category in TASK_PATTERNS:
        if re.search(pattern, task):
            return category
    return "general"


def get_local_models() -> set[str]:
    try:
        resp = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)
        resp.raise_for_status()
        return {m["name"].split(":")[0] + ":" + m["name"].split(":")[-1]
                for m in resp.json().get("models", [])}
    except Exception:
        return set()


def get_system_ram_gb() -> float | None:
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except ImportError:
        pass
    try:
        result = subprocess.run(
            ["wmic", "computersystem", "get", "totalphysicalmemory"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line.isdigit():
                return round(int(line) / (1024 ** 3), 1)
    except Exception:
        pass
    return None


class ModelRouter:
    def __init__(
        self,
        profiles: list[ModelProfile] | None = None,
        fallback: str = "qwen2.5:7b",
    ) -> None:
        self.profiles = profiles or list(DEFAULT_PROFILES)
        self.fallback = fallback
        self._local: set[str] | None = None
        self._ram: float | None = None

    def _available(self) -> set[str]:
        if self._local is None:
            self._local = get_local_models()
        return self._local

    def _system_ram(self) -> float:
        if self._ram is None:
            self._ram = get_system_ram_gb() or 8.0
        return self._ram

    def pick(self, task: str) -> tuple[str, str]:
        """Returns (model_name, category). Falls back gracefully."""
        category = classify_task(task)
        available = self._available()
        ram = self._system_ram()

        candidates = [
            p for p in self.profiles
            if p.matches(category) and p.name in available and p.ram_gb <= ram * 0.8
        ]
        candidates.sort(key=lambda p: p.priority, reverse=True)

        if candidates:
            return candidates[0].name, category

        any_available = [
            p for p in self.profiles
            if p.name in available and p.ram_gb <= ram * 0.8
        ]
        any_available.sort(key=lambda p: p.priority, reverse=True)

        if any_available:
            return any_available[0].name, category

        if self.fallback in available:
            return self.fallback, category

        if available:
            return next(iter(available)), category

        return self.fallback, category

    def list_available(self) -> list[dict]:
        available = self._available()
        ram = self._system_ram()
        result = []
        for p in sorted(self.profiles, key=lambda p: p.priority, reverse=True):
            result.append({
                "model": p.name,
                "strengths": p.strengths,
                "ram_gb": p.ram_gb,
                "speed": p.speed,
                "installed": p.name in available,
                "fits_ram": p.ram_gb <= ram * 0.8,
            })
        return result
