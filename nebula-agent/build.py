#!/usr/bin/env python3
"""Build a standalone Nova executable via PyInstaller.

Produces `dist/nova` (Linux/macOS) or `dist/nova.exe` (Windows). Bundles
the Flask static files and all Python deps into a single file.

Usage:
    pip install pyinstaller
    python build.py                     # default single-file build
    python build.py --onedir            # folder distribution (faster startup)
"""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Nova standalone")
    parser.add_argument("--onedir", action="store_true", help="Emit a folder instead of one file")
    parser.add_argument("--console", action="store_true", help="Keep the console window (debug)")
    parser.add_argument("--clean", action="store_true", help="Wipe build/dist first")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent

    if args.clean:
        for d in ("build", "dist", "__pycache__"):
            p = root / d
            if p.exists():
                shutil.rmtree(p)
                print(f"  removed {p}")

    if not shutil.which("pyinstaller"):
        print("PyInstaller not found. Install with: pip install pyinstaller")
        sys.exit(1)

    sep = ";" if platform.system() == "Windows" else ":"
    static_dir = root / "web" / "static"

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--name", "nova",
        "--onedir" if args.onedir else "--onefile",
        f"--add-data={static_dir}{sep}web/static",
        # Hidden imports pystray/pyttsx3 don't discover on their own:
        "--hidden-import=pystray._win32" if platform.system() == "Windows" else "--hidden-import=pystray._appindicator",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=pyttsx3.drivers",
        "--hidden-import=pyttsx3.drivers.sapi5" if platform.system() == "Windows" else "--hidden-import=pyttsx3.drivers.espeak",
    ]
    if not args.console:
        cmd.append("--windowed" if args.onedir else "--noconsole")
    cmd.append(str(root / "main.py"))

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=root)
    if result.returncode != 0:
        print(f"\nBuild failed (exit {result.returncode}).")
        sys.exit(result.returncode)

    dist = root / "dist"
    print(f"\n=== Build complete ===")
    for item in dist.iterdir():
        size = f"{item.stat().st_size / (1024*1024):.1f} MB" if item.is_file() else "(directory)"
        print(f"  {item.name}  {size}")


if __name__ == "__main__":
    main()
