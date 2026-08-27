"""System tray launcher — keeps the Nova web UI running in the background
with an icon in the taskbar. Right-click for open/quit.
"""
from __future__ import annotations

import threading
import webbrowser

import pystray
from PIL import Image, ImageDraw

from web.server import start


def _make_icon(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Nebula blue circle with a small dot inside (matching the web UI brand)
    d.ellipse((4, 4, size - 4, size - 4), fill=(90, 140, 255, 255))
    d.ellipse((size // 2 - 6, size // 2 - 6, size // 2 + 6, size // 2 + 6),
              fill=(255, 255, 255, 255))
    return img


def _open_ui(port: int):
    def _o(icon, item):
        webbrowser.open(f"http://127.0.0.1:{port}")
    return _o


def _quit(icon, item):
    icon.stop()


def run(host: str = "127.0.0.1", port: int = 5757) -> None:
    server_thread = threading.Thread(
        target=start, args=(host, port), daemon=True,
    )
    server_thread.start()

    icon = pystray.Icon(
        "Nova",
        _make_icon(),
        "Nova · Nebula Agent",
        menu=pystray.Menu(
            pystray.MenuItem("Open Nova", _open_ui(port), default=True),
            pystray.MenuItem("Quit", _quit),
        ),
    )
    icon.run()
