"""Cross-platform autostart management.

Enables/disables Nova starting on user login. Backends:
- Windows: shortcut in the Startup folder
- Linux: XDG .desktop file under ~/.config/autostart
- macOS: LaunchAgent plist under ~/Library/LaunchAgents
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

_APP_NAME = "Nova"
_ENTRY_ARGS = ["--tray"]


def _entry_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable] + _ENTRY_ARGS
    return [sys.executable, str(Path(__file__).resolve().parent.parent / "main.py")] + _ENTRY_ARGS


def _startup_path_windows() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"{_APP_NAME}.lnk"


def _autostart_path_linux() -> Path:
    return Path.home() / ".config" / "autostart" / f"{_APP_NAME.lower()}.desktop"


def _launchagent_path_mac() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"com.nebula.{_APP_NAME.lower()}.plist"


def is_enabled() -> bool:
    system = platform.system()
    if system == "Windows":
        return _startup_path_windows().exists()
    if system == "Linux":
        return _autostart_path_linux().exists()
    if system == "Darwin":
        return _launchagent_path_mac().exists()
    return False


def enable() -> dict:
    system = platform.system()
    cmd = _entry_command()
    try:
        if system == "Windows":
            return _enable_windows(cmd)
        if system == "Linux":
            return _enable_linux(cmd)
        if system == "Darwin":
            return _enable_mac(cmd)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": False, "error": f"unsupported platform: {system}"}


def disable() -> dict:
    system = platform.system()
    try:
        if system == "Windows":
            p = _startup_path_windows()
        elif system == "Linux":
            p = _autostart_path_linux()
        elif system == "Darwin":
            p = _launchagent_path_mac()
        else:
            return {"ok": False, "error": f"unsupported platform: {system}"}
        if p.exists():
            p.unlink()
            return {"ok": True, "removed": str(p)}
        return {"ok": True, "note": "was not enabled"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _enable_windows(cmd: list[str]) -> dict:
    dest = _startup_path_windows()
    dest.parent.mkdir(parents=True, exist_ok=True)
    target = cmd[0]
    args = " ".join(f'"{a}"' if " " in a else a for a in cmd[1:])
    ps = f"""
$s = New-Object -ComObject WScript.Shell
$sc = $s.CreateShortcut('{dest}')
$sc.TargetPath = '{target}'
$sc.Arguments = '{args}'
$sc.WorkingDirectory = '{Path(cmd[-1] if len(cmd) > 1 else target).parent}'
$sc.WindowStyle = 7
$sc.Save()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return {"ok": True, "path": str(dest)}


def _enable_linux(cmd: list[str]) -> dict:
    dest = _autostart_path_linux()
    dest.parent.mkdir(parents=True, exist_ok=True)
    exec_line = " ".join(cmd)
    dest.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={_APP_NAME}\n"
        "Comment=Nebula agent engine\n"
        f"Exec={exec_line}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    dest.chmod(0o755)
    return {"ok": True, "path": str(dest)}


def _enable_mac(cmd: list[str]) -> dict:
    dest = _launchagent_path_mac()
    dest.parent.mkdir(parents=True, exist_ok=True)
    args_xml = "\n".join(f"        <string>{a}</string>" for a in cmd)
    dest.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        '  <dict>\n'
        f'    <key>Label</key><string>com.nebula.{_APP_NAME.lower()}</string>\n'
        '    <key>ProgramArguments</key>\n'
        f'    <array>\n{args_xml}\n    </array>\n'
        '    <key>RunAtLoad</key><true/>\n'
        '  </dict>\n'
        '</plist>\n'
    )
    return {"ok": True, "path": str(dest)}
