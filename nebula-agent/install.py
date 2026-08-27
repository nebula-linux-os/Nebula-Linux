#!/usr/bin/env python3
"""First-run installer for Nova.

Interactive: checks Ollama, offers to pull the default model, enables
autostart, and (optionally) creates a desktop shortcut. Idempotent —
running it again just reconfigures.

Usage:
    python install.py
    python install.py --no-autostart
    python install.py --update              # check for a newer release
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

from agent import autostart
from agent.updater import check_for_update
from agent.version import __version__

DEFAULT_MODEL = "qwen2.5:7b"


def ask(question: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        ans = input(f"{question} {suffix} ").strip().lower()
    except EOFError:
        return default
    if not ans:
        return default
    return ans in ("y", "yes")


def check_ollama() -> bool:
    if not shutil.which("ollama"):
        print("  [x] Ollama not found on PATH.")
        print("      Install it from https://ollama.com/download and re-run this script.")
        return False
    print("  [+] Ollama found.")
    return True


def list_installed_models() -> list[str]:
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        lines = result.stdout.strip().splitlines()[1:]
        return [line.split()[0] for line in lines if line.strip()]
    except Exception:
        return []


def offer_model_pull() -> None:
    installed = list_installed_models()
    if installed:
        print(f"  [+] {len(installed)} model(s) installed: {', '.join(installed[:3])}")
        return
    print("  [!] No Ollama models installed.")
    if not ask(f"      Pull {DEFAULT_MODEL} now? (~4.7 GB download)"):
        print("      Skipping. Pull one manually before using Nova.")
        return
    print(f"      Downloading {DEFAULT_MODEL} — this can take a while...")
    subprocess.run(["ollama", "pull", DEFAULT_MODEL], check=False)


def configure_autostart(enable: bool) -> None:
    if not enable:
        result = autostart.disable()
        print(f"  [+] Autostart disabled: {result}")
        return
    if autostart.is_enabled():
        print("  [+] Autostart already enabled.")
        return
    result = autostart.enable()
    if result.get("ok"):
        print(f"  [+] Autostart enabled -> {result.get('path', '?')}")
    else:
        print(f"  [x] Autostart failed: {result.get('error')}")


def run_update_check() -> None:
    print(f"Current version: {__version__}")
    print("Checking for updates...")
    info = check_for_update()
    if info.get("error"):
        print(f"  [x] {info['error']}")
        return
    latest = info.get("latest") or "(no releases yet)"
    print(f"  Latest release: {latest}")
    if info.get("update_available"):
        print(f"  [!] Update available: {info.get('url')}")
        print("      Download the new release and re-run install.py.")
    else:
        print("  [+] You're on the latest version.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Nova first-run installer")
    parser.add_argument("--no-autostart", action="store_true", help="Skip enabling autostart")
    parser.add_argument("--disable-autostart", action="store_true", help="Remove autostart")
    parser.add_argument("--update", action="store_true", help="Only check for updates")
    args = parser.parse_args()

    if args.update:
        run_update_check()
        return

    print(f"=== Nova installer v{__version__} ===\n")

    print("[1/3] Checking Ollama...")
    if not check_ollama():
        sys.exit(1)

    print("\n[2/3] Checking models...")
    offer_model_pull()

    print("\n[3/3] Autostart...")
    if args.disable_autostart:
        configure_autostart(False)
    else:
        configure_autostart(not args.no_autostart)

    print("\n=== Setup complete ===")
    print("Run Nova with:")
    print("  python main.py --tray     # background daemon + tray icon")
    print("  python main.py --web      # foreground web UI")
    print("  python main.py            # interactive REPL")


if __name__ == "__main__":
    main()
