"""Desktop integration tools — the ones that make Nova feel like a
system-level agent instead of a file-and-shell wrapper.

Adds: open_app, take_screenshot, read_clipboard, write_clipboard,
      notify, web_search.

Deliberately dependency-light: falls back through OS-native commands
before requiring optional packages (Pillow for screenshot, requests
already required).
"""
from __future__ import annotations

import base64
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path

import requests


_IS_WIN = platform.system() == "Windows"
_IS_MAC = platform.system() == "Darwin"
_IS_LINUX = platform.system() == "Linux"


def open_app(name: str) -> dict:
    """Open an application by name. Falls through a chain of OS-native tricks."""
    try:
        if _IS_WIN:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", f"Start-Process '{name}'"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        elif _IS_MAC:
            subprocess.Popen(["open", "-a", name])
        else:
            if shutil.which(name):
                subprocess.Popen([name])
            elif shutil.which("xdg-open"):
                subprocess.Popen(["xdg-open", name])
            else:
                return {"error": f"no way to open {name} on this system"}
        return {"opened": name}
    except FileNotFoundError:
        return {"error": f"application not found: {name}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def take_screenshot(path: str = "") -> dict:
    """Capture the primary screen. Returns the saved path."""
    if not path:
        out = Path(tempfile.gettempdir()) / f"nova-screenshot-{int(time.time())}.png"
    else:
        out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import ImageGrab  # type: ignore
        img = ImageGrab.grab()
        img.save(str(out))
        return {"path": str(out), "size": img.size, "backend": "pillow"}
    except ImportError:
        pass

    if _IS_MAC:
        subprocess.run(["screencapture", "-x", str(out)], check=False)
        return {"path": str(out), "backend": "screencapture"}
    if _IS_LINUX:
        for cmd in (["scrot", str(out)], ["grim", str(out)], ["import", "-window", "root", str(out)]):
            if shutil.which(cmd[0]):
                subprocess.run(cmd, check=False)
                return {"path": str(out), "backend": cmd[0]}
    if _IS_WIN:
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
            "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
            "$bmp=New-Object Drawing.Bitmap $b.Width,$b.Height; "
            "$g=[Drawing.Graphics]::FromImage($bmp); "
            f"$g.CopyFromScreen($b.Location,[Drawing.Point]::Empty,$b.Size); "
            f"$bmp.Save('{out}')"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return {"path": str(out), "backend": "powershell"}

    return {"error": "no screenshot backend available (install pillow)"}


def read_clipboard() -> dict:
    if _IS_WIN:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return {"content": result.stdout.rstrip("\r\n")}
    if _IS_MAC:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
        return {"content": result.stdout}
    if _IS_LINUX:
        for cmd in (["wl-paste"], ["xclip", "-selection", "clipboard", "-o"], ["xsel", "-b", "-o"]):
            if shutil.which(cmd[0]):
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                return {"content": result.stdout, "backend": cmd[0]}
        return {"error": "install wl-clipboard, xclip, or xsel"}
    return {"error": f"unsupported platform: {platform.system()}"}


def write_clipboard(content: str) -> dict:
    if _IS_WIN:
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
            stdin=subprocess.PIPE, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        proc.communicate(content, timeout=5)
        return {"wrote": len(content)}
    if _IS_MAC:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
        proc.communicate(content, timeout=5)
        return {"wrote": len(content)}
    if _IS_LINUX:
        for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "-b", "-i"]):
            if shutil.which(cmd[0]):
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
                proc.communicate(content, timeout=5)
                return {"wrote": len(content), "backend": cmd[0]}
        return {"error": "install wl-clipboard, xclip, or xsel"}
    return {"error": f"unsupported platform: {platform.system()}"}


def notify(title: str, message: str = "") -> dict:
    """Send a desktop notification."""
    if _IS_WIN:
        ps = (
            "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
            "[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom.XmlDocument,ContentType=WindowsRuntime]|Out-Null;"
            f"$t=@'\n<toast><visual><binding template=\"ToastText02\"><text id=\"1\">{title}</text><text id=\"2\">{message}</text></binding></visual></toast>\n'@;"
            "$x=New-Object Windows.Data.Xml.Dom.XmlDocument;$x.LoadXml($t);"
            "$n=New-Object Windows.UI.Notifications.ToastNotification($x);"
            "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Nova').Show($n);"
        )
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps],
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return {"sent": True, "backend": "windows-toast"}
    if _IS_MAC:
        script = f'display notification "{message}" with title "{title}"'
        subprocess.Popen(["osascript", "-e", script])
        return {"sent": True, "backend": "osascript"}
    if _IS_LINUX:
        if shutil.which("notify-send"):
            subprocess.Popen(["notify-send", title, message])
            return {"sent": True, "backend": "notify-send"}
        return {"error": "install libnotify-bin"}
    return {"error": f"unsupported platform: {platform.system()}"}


def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web via DuckDuckGo Instant Answer API (no key needed)."""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=15,
            headers={"User-Agent": "Nova-Agent/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"search failed: {e}"}

    results: list[dict] = []
    if data.get("AbstractText"):
        results.append({
            "title": data.get("Heading", "Summary"),
            "snippet": data["AbstractText"],
            "url": data.get("AbstractURL", ""),
        })
    for topic in data.get("RelatedTopics", []):
        if len(results) >= max_results:
            break
        if isinstance(topic, dict) and topic.get("Text"):
            results.append({
                "title": topic["Text"].split(" - ")[0][:80],
                "snippet": topic["Text"],
                "url": topic.get("FirstURL", ""),
            })

    if not results:
        results.append({
            "title": f"Search: {query}",
            "snippet": "No instant answer. Open the search page for full results.",
            "url": f"https://duckduckgo.com/?q={urllib.parse.quote(query)}",
        })

    return {"query": query, "count": len(results), "results": results}


DESKTOP_TOOL_FUNCTIONS = {
    "open_app": open_app,
    "take_screenshot": take_screenshot,
    "read_clipboard": read_clipboard,
    "write_clipboard": write_clipboard,
    "notify": notify,
    "web_search": web_search,
}

DESKTOP_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Launch a desktop application by name (e.g. 'chrome', 'code', 'notepad', 'firefox'). Works on Windows/Linux/macOS. Prefer this over run_command when the user asks to 'open' an app.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Application name or executable"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Capture the primary screen to a PNG file and return its path. Use when you need to see what's on the user's screen or verify a GUI action worked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Where to save the PNG (default: a temp file)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_clipboard",
            "description": "Read the current clipboard content as text.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_clipboard",
            "description": "Set the clipboard content. Useful for handing text back to the user to paste elsewhere.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Text to place on the clipboard"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify",
            "description": "Show a desktop notification. Use for long-running tasks or when the user should be alerted to something outside the current window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Notification title"},
                    "message": {"type": "string", "description": "Notification body (optional)"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web via DuckDuckGo and return top result snippets. Use when you need factual information you don't already have.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Maximum results to return (default 5)"},
                },
                "required": ["query"],
            },
        },
    },
]
