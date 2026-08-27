"""Event-based agent loop — yields events instead of printing.

This lets both the CLI and the web server consume the same underlying
agent loop. Each event is a small dict describing what just happened:
router pick, model text token, tool call proposed, tool result, done, etc.
"""
from __future__ import annotations

import json
import time
from typing import Iterator

import requests

from .executor import execute_tool
from .memory import MemoryStore
from .memory_tools import MEMORY_TOOL_FUNCTIONS, MEMORY_TOOLS_SCHEMA, set_store
from .models import ModelRouter, classify_task
from .session import Session
from .tools import RISKY_TOOLS, TOOL_FUNCTIONS, TOOLS_SCHEMA
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
- Prefer read-only tools to check current state before you act.
- Use edit_file instead of write_file when you only need to change part
  of a file.
- Take one meaningful step at a time and look at its result.
- When the task is fully done, reply with a short plain-text summary
  and make no further tool calls.
- If the request is ambiguous or you're about to do something
  irreversible and unclear, ask the user instead of guessing.
- Use save_memory to remember facts that would help in future sessions.
- At the start of a complex task, use recall_memory if relevant.
"""


def _build_tool_set() -> tuple[list[dict], dict]:
    schemas = TOOLS_SCHEMA + EXTENDED_TOOLS_SCHEMA + MEMORY_TOOLS_SCHEMA
    fns = {**TOOL_FUNCTIONS, **EXTENDED_TOOL_FUNCTIONS, **MEMORY_TOOL_FUNCTIONS}
    return schemas, fns


def _parse_tool_args(raw_args) -> dict:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError:
            return {}
    return {}


def _stream_ollama(model: str, messages: list[dict], tools: list[dict]) -> Iterator[dict]:
    """Streams raw chunks from Ollama's chat endpoint."""
    resp = requests.post(
        OLLAMA_URL,
        json={"model": model, "messages": messages, "tools": tools, "stream": True},
        timeout=180,
        stream=True,
    )
    resp.raise_for_status()
    for line in resp.iter_lines():
        if not line:
            continue
        yield json.loads(line)


def run_task_events(
    task: str,
    model: str | None = None,
    auto_approve: bool = False,
    confirm_fn=None,
    memory: MemoryStore | None = None,
    router: ModelRouter | None = None,
) -> Iterator[dict]:
    """Yields events as the agent works. Consumers decide how to display them.

    Event types:
      {"type": "router", "model": str, "category": str}
      {"type": "token", "text": str}                        # streamed model text
      {"type": "assistant_done"}                            # end of an assistant turn
      {"type": "tool_call", "step": int, "name": str, "args": dict}
      {"type": "tool_awaiting_confirm", "name": str, "args": dict}
      {"type": "tool_result", "name": str, "result": dict}
      {"type": "error", "message": str}
      {"type": "done", "outcome": str, "steps": int, "duration_s": float,
                       "session_path": str}
    """
    if memory is None:
        memory = MemoryStore()
    set_store(memory)

    if router is None:
        router = ModelRouter()

    if model is None:
        model, category = router.pick(task)
    else:
        category = classify_task(task)

    yield {"type": "router", "model": model, "category": category}

    schemas, fns = _build_tool_set()

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

    start = time.time()
    outcome = "completed"
    step = 0

    for step in range(1, MAX_STEPS + 1):
        full_content = ""
        tool_calls: list[dict] = []

        try:
            for chunk in _stream_ollama(model, messages, schemas):
                msg = chunk.get("message", {})
                if msg.get("content"):
                    full_content += msg["content"]
                    yield {"type": "token", "text": msg["content"]}
                if msg.get("tool_calls"):
                    tool_calls.extend(msg["tool_calls"])
                if chunk.get("done"):
                    break
        except requests.ConnectionError:
            yield {"type": "error", "message": "Could not reach Ollama at localhost:11434"}
            outcome = "connection_error"
            break
        except requests.HTTPError as e:
            yield {"type": "error", "message": f"Ollama error: {e}"}
            outcome = "ollama_error"
            break

        message = {"role": "assistant", "content": full_content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        messages.append(message)
        session.log("assistant", full_content)

        if not tool_calls:
            yield {"type": "assistant_done"}
            break

        yield {"type": "assistant_done"}

        for call in tool_calls:
            name = call["function"]["name"]
            args = _parse_tool_args(call["function"].get("arguments", {}))
            yield {"type": "tool_call", "step": step, "name": name, "args": args}
            session.log("tool_call", "", tool_name=name, tool_args=args)

            if name in RISKY_TOOLS and not auto_approve:
                yield {"type": "tool_awaiting_confirm", "name": name, "args": args}
                allowed = confirm_fn(name, args) if confirm_fn else False
                if not allowed:
                    result = {"error": "denied by user"}
                    yield {"type": "tool_result", "name": name, "result": result}
                    session.log("tool_result", json.dumps(result), tool_name=name)
                    messages.append({"role": "tool", "content": json.dumps(result)})
                    continue

            if name in fns:
                try:
                    if name in RISKY_TOOLS:
                        result = execute_tool(name, args, auto_approve=True)
                    else:
                        result = fns[name](**args)
                except Exception as e:
                    result = {"error": f"{name} raised {type(e).__name__}: {e}"}
            else:
                result = {"error": f"unknown tool: {name}"}

            yield {"type": "tool_result", "name": name, "result": result}
            session.log("tool_result", json.dumps(result), tool_name=name)
            messages.append({"role": "tool", "content": json.dumps(result)})
    else:
        outcome = "max_steps"
        yield {"type": "error", "message": f"Stopped after {MAX_STEPS} steps"}

    duration = round(time.time() - start, 1)
    memory.log_task(task, model, step, outcome, duration)
    log_path = session.save(outcome, step)
    yield {
        "type": "done",
        "outcome": outcome,
        "steps": step,
        "duration_s": duration,
        "session_path": str(log_path),
    }
