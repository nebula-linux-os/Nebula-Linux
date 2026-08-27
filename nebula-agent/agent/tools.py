"""Tool implementations for the Nebula agent engine (Phase 0).

Each tool is a plain Python function plus an OpenAI-style JSON schema so it
can be handed to Ollama's tool-calling API. The model picks a tool and
arguments; it never runs anything directly — execute_tool() is the only
thing that touches the filesystem or a shell.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path

# Tools in here require user confirmation before running (see executor.py).
# Read-only tools (read_file, list_dir) are not in this set.
RISKY_TOOLS = {
    "run_command", "install_package", "write_file", "edit_file",
    "open_app", "write_clipboard",
}


def _package_manager_command(name: str) -> list[str]:
    system = platform.system()
    if system == "Windows":
        if shutil.which("winget"):
            return ["winget", "install", "-e", "--id", name]
        raise RuntimeError("winget not found on this machine")
    if system == "Linux":
        if shutil.which("pacman"):
            return ["sudo", "pacman", "-S", "--noconfirm", name]
        if shutil.which("apt"):
            return ["sudo", "apt", "install", "-y", name]
        raise RuntimeError("no supported package manager found (pacman/apt)")
    if system == "Darwin":
        if shutil.which("brew"):
            return ["brew", "install", name]
        raise RuntimeError("homebrew not found on this machine")
    raise RuntimeError(f"unsupported platform: {system}")


def run_command(command: str) -> dict:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=120
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"error": "command timed out after 120s"}


def write_file(path: str, content: str) -> dict:
    p = Path(path).expanduser()
    existed = p.exists()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return {"path": str(p), "bytes_written": len(content), "overwrote": existed}


def read_file(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"no such file: {p}"}
    text = p.read_text(errors="replace")
    return {"path": str(p), "content": text[:8000]}


def list_dir(path: str = ".") -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"no such path: {p}"}
    entries = sorted(e.name + ("/" if e.is_dir() else "") for e in p.iterdir())
    return {"path": str(p), "entries": entries[:200]}


def install_package(name: str) -> dict:
    try:
        cmd = _package_manager_command(name)
    except RuntimeError as e:
        return {"error": str(e)}
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return {
        "command": " ".join(cmd),
        "exit_code": result.returncode,
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-1000:],
    }


def open_url(url: str) -> dict:
    if not (url.startswith("http://") or url.startswith("https://")):
        return {"error": "refusing to open a non-http(s) url"}
    webbrowser.open(url)
    return {"opened": url}


TOOL_FUNCTIONS = {
    "run_command": run_command,
    "write_file": write_file,
    "read_file": read_file,
    "list_dir": list_dir,
    "install_package": install_package,
    "open_url": open_url,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command on the user's machine and return stdout/stderr/exit code. Use for running scripts, starting servers, checking system state — anything not covered by a more specific tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with the given text content. Creates parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Full text content of the file"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file's contents. Use this to check state before deciding what to do next.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path to read"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the contents of a directory. Use this to check whether a file/project already exists before acting.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Directory path, defaults to current directory"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "install_package",
            "description": "Install a software package using the system's package manager (winget/pacman/apt/brew, auto-detected).",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Package name to install"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a URL in the default web browser.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "http(s) URL to open"}},
                "required": ["url"],
            },
        },
    },
]
