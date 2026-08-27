"""Executes tool calls the planner proposes.

The model never runs anything itself — it only proposes a tool name +
arguments. This module is the single choke point that actually touches
the filesystem or a shell, and it's where the confirmation gate and
post-action verification live.
"""
from __future__ import annotations

from pathlib import Path

from .tools import RISKY_TOOLS, TOOL_FUNCTIONS


def confirm(name: str, args: dict) -> bool:
    printable = ", ".join(f"{k}={v!r}" for k, v in args.items())
    answer = input(f"  Allow agent to run {name}({printable})? [y/N] ").strip().lower()
    return answer == "y"


def verify(name: str, args: dict, result: dict) -> str | None:
    """Lightweight post-action sanity check. Returns a warning string, or None."""
    if name == "write_file" and "error" not in result:
        p = Path(args.get("path", "")).expanduser()
        if not p.exists() or p.stat().st_size == 0:
            return f"write_file reported success but {p} is missing or empty"
    if name == "run_command" and result.get("exit_code", 0) != 0:
        return f"command exited with code {result.get('exit_code')}"
    if name == "install_package" and result.get("exit_code", 0) != 0:
        return f"install exited with code {result.get('exit_code')}"
    return None


def execute_tool(name: str, args: dict, auto_approve: bool = False) -> dict:
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}

    if name in RISKY_TOOLS and not auto_approve:
        if not confirm(name, args):
            return {"error": "denied by user"}

    try:
        result = fn(**args)
    except TypeError as e:
        return {"error": f"bad arguments for {name}: {e}"}
    except Exception as e:  # tool implementations shouldn't crash the agent loop
        return {"error": f"{name} raised {type(e).__name__}: {e}"}

    warning = verify(name, args, result)
    if warning:
        result["_verification_warning"] = warning
    return result
