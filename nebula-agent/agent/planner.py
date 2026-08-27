"""Planner: talks to Ollama, drives the plan -> execute -> verify loop.

Phase 2 additions:
- Multi-model routing (auto-picks best model per task type)
- Extended tool set (system_info, find_files, edit_file)
- All Phase 1 features (streaming, memory, session logging)
"""
from __future__ import annotations

import json
import sys
import time

import requests

from .executor import execute_tool
from .memory import MemoryStore
from .memory_tools import MEMORY_TOOL_FUNCTIONS, MEMORY_TOOLS_SCHEMA, set_store
from .models import ModelRouter
from .session import Session
from .tools import RISKY_TOOLS, TOOLS_SCHEMA
from .tools_extended import EXTENDED_TOOL_FUNCTIONS, EXTENDED_TOOLS_SCHEMA

OLLAMA_URL = "http://localhost:11434/api/chat"
MAX_STEPS = 15

SYSTEM_PROMPT = """You are Nova, a desktop automation agent for Nebula Linux.
You have tools to read/write/edit files, list and find files, run shell
commands, install packages, open URLs, and check system information. You
also have memory tools to save and recall facts across sessions.

Break the user's request into concrete steps and call tools to carry
them out.

Rules:
- Prefer read-only tools (read_file, list_dir, find_files, system_info)
  to check current state before you act, rather than assuming.
- Use edit_file instead of write_file when you only need to change part
  of a file — it's safer and preserves the rest of the content.
- Take one meaningful step at a time and look at its result before
  deciding the next step.
- If a tool call fails or a result looks wrong, try a different approach
  once before giving up.
- When the task is fully done, reply with a short plain-text summary and
  make no further tool calls.
- If the request is ambiguous or you're about to do something
  irreversible and unclear, ask the user instead of guessing.
- Use save_memory to remember facts that would help you in future
  sessions (user preferences, project paths, things you learned).
- At the start of a complex task, use recall_memory if the task might
  relate to something you've done before.
"""


def _build_tool_set() -> tuple[list[dict], dict[str, object]]:
    schemas = TOOLS_SCHEMA + EXTENDED_TOOLS_SCHEMA + MEMORY_TOOLS_SCHEMA
    fns: dict = {}
    from .tools import TOOL_FUNCTIONS
    fns.update(TOOL_FUNCTIONS)
    fns.update(EXTENDED_TOOL_FUNCTIONS)
    fns.update(MEMORY_TOOL_FUNCTIONS)
    return schemas, fns


def _call_ollama_stream(model: str, messages: list[dict], tools: list[dict]) -> dict:
    resp = requests.post(
        OLLAMA_URL,
        json={"model": model, "messages": messages, "tools": tools, "stream": True},
        timeout=180,
        stream=True,
    )
    resp.raise_for_status()

    full_content = ""
    tool_calls = []
    role = "assistant"

    for line in resp.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        msg = chunk.get("message", {})
        role = msg.get("role", role)

        if msg.get("content"):
            text = msg["content"]
            full_content += text
            sys.stdout.write(text)
            sys.stdout.flush()

        if msg.get("tool_calls"):
            tool_calls.extend(msg["tool_calls"])

        if chunk.get("done"):
            break

    if full_content and not tool_calls:
        sys.stdout.write("\n")
        sys.stdout.flush()

    result = {"role": role, "content": full_content}
    if tool_calls:
        result["tool_calls"] = tool_calls
    return result


def _call_ollama_blocking(model: str, messages: list[dict], tools: list[dict]) -> dict:
    resp = requests.post(
        OLLAMA_URL,
        json={"model": model, "messages": messages, "tools": tools, "stream": False},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["message"]


def _parse_tool_args(raw_args) -> dict:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError:
            return {}
    return {}


def run_task(
    task: str,
    model: str | None = None,
    auto_approve: bool = False,
    stream: bool = True,
    memory: MemoryStore | None = None,
    router: ModelRouter | None = None,
) -> None:
    if memory is None:
        memory = MemoryStore()
    set_store(memory)

    if router is None:
        router = ModelRouter()

    if model is None:
        model, category = router.pick(task)
        print(f"[router] task type: {category} -> model: {model}")
    else:
        from .models import classify_task
        category = classify_task(task)
        print(f"[router] task type: {category} (using requested model: {model})")

    all_tools, all_fns = _build_tool_set()

    memory_context = memory.format_for_prompt()
    system_content = SYSTEM_PROMPT
    if memory_context:
        system_content += "\n\n" + memory_context

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": task},
    ]

    session = Session(task, model)
    session.log("system", system_content)
    session.log("user", task)

    call_fn = _call_ollama_stream if stream else _call_ollama_blocking
    start = time.time()
    outcome = "completed"
    step = 0

    for step in range(1, MAX_STEPS + 1):
        try:
            message = call_fn(model, messages, all_tools)
        except requests.ConnectionError:
            print("\nCould not reach Ollama at localhost:11434 — is `ollama serve` running?")
            outcome = "connection_error"
            break
        except requests.HTTPError as e:
            print(f"\nOllama returned an error: {e}")
            outcome = "ollama_error"
            break

        messages.append(message)
        session.log("assistant", message.get("content", ""))
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            if not stream:
                print(f"\n{message.get('content', '').strip()}")
            break

        for call in tool_calls:
            name = call["function"]["name"]
            args = _parse_tool_args(call["function"].get("arguments", {}))
            print(f"\n[step {step}] {name}({args})")
            session.log("tool_call", "", tool_name=name, tool_args=args)

            if name in RISKY_TOOLS:
                result = execute_tool(name, args, auto_approve=auto_approve)
            elif name in all_fns:
                try:
                    result = all_fns[name](**args)
                except Exception as e:
                    result = {"error": f"{name} raised {type(e).__name__}: {e}"}
            else:
                result = {"error": f"unknown tool: {name}"}

            print(f"  -> {result}")
            session.log("tool_result", json.dumps(result), tool_name=name)

            messages.append({"role": "tool", "content": json.dumps(result)})
    else:
        print(f"\nStopped after {MAX_STEPS} steps without a final answer — the model may be looping.")
        outcome = "max_steps"

    duration = round(time.time() - start, 1)
    memory.log_task(task, model, step, outcome, duration)
    log_path = session.save(outcome, step)
    print(f"\n[session saved to {log_path}]")
