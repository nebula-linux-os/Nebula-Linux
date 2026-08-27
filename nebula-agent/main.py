#!/usr/bin/env python3
"""Nebula agent engine — Phase 3 CLI + Web.

Single-shot:
    python main.py "create a python web server in ./demo"
    python main.py --model llama3.1:8b "install blender"

Interactive REPL:
    python main.py

Web UI:
    python main.py --web
    python main.py --web --port 8080
"""
from __future__ import annotations

import argparse
import sys

from agent.memory import MemoryStore
from agent.models import ModelRouter
from agent.planner import run_task
from agent.voice import Speaker


def _repl(model: str | None, auto_approve: bool, stream: bool, speaker=None) -> None:
    memory = MemoryStore()
    router = ModelRouter()
    mode_label = f"Model: {model}" if model else "Model: auto-routed"
    print("Nova — Nebula Agent Engine (Phase 2)")
    print(f"{mode_label} | Memory: on | Streaming: {'on' if stream else 'off'}")
    print("Type a task, or '/help' for commands.\n")

    while True:
        try:
            task = input("nova> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not task:
            continue
        if task.lower() in ("quit", "exit", "/quit", "/exit"):
            print("Bye.")
            break

        if task.lower() == "/memory":
            _show_memories(memory)
            continue
        if task.lower() == "/history":
            _show_history(memory)
            continue
        if task.lower().startswith("/forget "):
            _forget(memory, task)
            continue
        if task.lower() == "/models":
            _show_models(router)
            continue
        if task.lower() == "/help":
            _show_help()
            continue

        run_task(
            task, model=model, auto_approve=auto_approve,
            stream=stream, memory=memory, router=router,
            speaker=speaker,
        )
        print()

    memory.close()


def _show_memories(memory: MemoryStore) -> None:
    memories = memory.recall(limit=20)
    if not memories:
        print("  No saved memories yet.")
        return
    for m in memories:
        print(f"  [{m['id']}] ({m['category']}) {m['content']}")
    print()


def _show_history(memory: MemoryStore) -> None:
    tasks = memory.recent_tasks(limit=10)
    if not tasks:
        print("  No task history yet.")
        return
    for t in tasks:
        status = "ok" if t["outcome"] == "completed" else t["outcome"]
        print(f"  [{status}] {t['task'][:60]}  ({t['steps']} steps, {t['duration_s']}s, {t['model']})")
    print()


def _show_models(router: ModelRouter) -> None:
    models = router.list_available()
    if not models:
        print("  No model profiles configured.")
        return
    print("  Model profiles (sorted by priority):")
    for m in models:
        installed = "installed" if m["installed"] else "not installed"
        fits = "fits RAM" if m["fits_ram"] else "too large"
        strengths = ", ".join(m["strengths"])
        print(f"    {m['model']:25s} [{installed}, {fits}] {m['speed']:6s} | {strengths}")
    print()


def _forget(memory: MemoryStore, cmd: str) -> None:
    try:
        mid = int(cmd.split(maxsplit=1)[1])
    except (ValueError, IndexError):
        print("  Usage: /forget <memory_id>")
        return
    if memory.forget(mid):
        print(f"  Forgot memory #{mid}.")
    else:
        print(f"  Memory #{mid} not found.")


def _show_help() -> None:
    print("  Commands:")
    print("    /memory   — list all saved memories")
    print("    /history  — show recent task history")
    print("    /models   — show available models and routing profiles")
    print("    /forget N — delete memory by ID")
    print("    /help     — show this help")
    print("    quit      — exit the REPL")
    print()
    print("  The router auto-picks the best model for each task.")
    print("  Override with --model to force a specific one.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nebula agent engine (Phase 3)")
    parser.add_argument("task", nargs="?", default=None, help="Task for the agent (omit for interactive mode)")
    parser.add_argument("--model", default=None, help="Force a specific Ollama model (default: auto-route)")
    parser.add_argument("--yes", action="store_true", help="Auto-approve risky tool calls")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming (wait for full response)")
    parser.add_argument("--web", action="store_true", help="Launch the web UI instead of the CLI")
    parser.add_argument("--tray", action="store_true", help="Launch web UI + system tray (background daemon)")
    parser.add_argument("--voice", action="store_true", help="Speak responses aloud via pyttsx3 (CLI only)")
    parser.add_argument("--host", default="127.0.0.1", help="Web UI host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5757, help="Web UI port (default: 5757)")
    args = parser.parse_args()

    if args.tray:
        from tray import run as tray_run
        tray_run(host=args.host, port=args.port)
        return

    if args.web:
        from web.server import start
        start(host=args.host, port=args.port)
        return

    stream = not args.no_stream
    speaker = Speaker() if args.voice else None
    if args.voice and speaker and not speaker.available:
        print("[voice] pyttsx3 not available — install with `pip install pyttsx3`")

    if args.task:
        memory = MemoryStore()
        router = ModelRouter()
        try:
            run_task(
                args.task, model=args.model, auto_approve=args.yes,
                stream=stream, memory=memory, router=router,
                speaker=speaker,
            )
        except KeyboardInterrupt:
            print("\nInterrupted.")
            sys.exit(130)
        finally:
            memory.close()
    else:
        _repl(args.model, args.yes, stream, speaker=speaker)


if __name__ == "__main__":
    main()
