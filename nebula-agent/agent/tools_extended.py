"""Extended tools added in Phase 2.

These supplement the Phase 0 tool set with capabilities the agent needs
for real-world tasks: inspecting the system, searching for files by
pattern, and surgically editing files instead of full rewrites.
"""
from __future__ import annotations

import fnmatch
import os
import platform
import shutil
import subprocess
from pathlib import Path


def system_info() -> dict:
    info: dict = {
        "os": platform.system(),
        "os_version": platform.version(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "hostname": platform.node(),
    }
    try:
        import psutil
        vm = psutil.virtual_memory()
        info["ram_total_gb"] = round(vm.total / (1024 ** 3), 1)
        info["ram_available_gb"] = round(vm.available / (1024 ** 3), 1)
        du = psutil.disk_usage("/")
        info["disk_total_gb"] = round(du.total / (1024 ** 3), 1)
        info["disk_free_gb"] = round(du.free / (1024 ** 3), 1)
        info["cpu_count"] = psutil.cpu_count()
    except ImportError:
        info["ram_note"] = "install psutil for detailed system stats"
    for cmd_name in ("git", "python3", "node", "docker", "ollama"):
        info[f"has_{cmd_name}"] = shutil.which(cmd_name) is not None
    return info


def find_files(pattern: str, path: str = ".", max_results: int = 50) -> dict:
    root = Path(path).expanduser().resolve()
    if not root.exists():
        return {"error": f"no such path: {root}"}
    matches = []
    skip = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            if fnmatch.fnmatch(name, pattern):
                full = Path(dirpath) / name
                try:
                    rel = full.relative_to(root)
                except ValueError:
                    rel = full
                matches.append(str(rel))
                if len(matches) >= max_results:
                    return {"path": str(root), "pattern": pattern, "matches": matches, "truncated": True}
    return {"path": str(root), "pattern": pattern, "matches": matches, "truncated": False}


def edit_file(path: str, old_text: str, new_text: str) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"no such file: {p}"}
    content = p.read_text(errors="replace")
    count = content.count(old_text)
    if count == 0:
        return {"error": "old_text not found in file", "path": str(p)}
    if count > 1:
        return {"error": f"old_text matches {count} locations — make it more specific", "path": str(p)}
    new_content = content.replace(old_text, new_text, 1)
    p.write_text(new_content)
    return {"path": str(p), "replaced": True, "old_len": len(old_text), "new_len": len(new_text)}


EXTENDED_TOOL_FUNCTIONS = {
    "system_info": system_info,
    "find_files": find_files,
    "edit_file": edit_file,
}

EXTENDED_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description": "Get information about the current system: OS, RAM, disk, CPU, installed tools. Use this before recommending installs or checking compatibility.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Recursively search for files matching a glob pattern (e.g. '*.py', 'Dockerfile', '*.config.js'). Skips .git, node_modules, __pycache__.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern to match filenames (e.g. '*.py', 'README*')"},
                    "path": {"type": "string", "description": "Directory to search in (default: current directory)"},
                    "max_results": {"type": "integer", "description": "Maximum files to return (default: 50)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific piece of text in a file. More precise than write_file — use this when you only need to change part of a file. The old_text must appear exactly once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_text": {"type": "string", "description": "Exact text to find and replace (must be unique in the file)"},
                    "new_text": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
]
