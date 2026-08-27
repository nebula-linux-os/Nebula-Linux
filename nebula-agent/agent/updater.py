"""Check GitHub Releases for a newer Nova version.

Non-invasive: only tells you if an update is available and returns the
release URL. Does NOT auto-download or overwrite anything — the user
opts in via `install.py --update` or a UI prompt.
"""
from __future__ import annotations

import re

import requests

from .version import __github_repo__, __version__


def _parse(v: str) -> tuple[int, ...]:
    m = re.findall(r"\d+", v)
    return tuple(int(x) for x in m[:3]) if m else (0, 0, 0)


def check_for_update(timeout: int = 8) -> dict:
    """Returns {'current': str, 'latest': str|None, 'update_available': bool, ...}"""
    result: dict = {"current": __version__, "latest": None, "update_available": False}
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{__github_repo__}/releases/latest",
            timeout=timeout,
            headers={"Accept": "application/vnd.github+json"},
        )
        if resp.status_code == 404:
            result["note"] = "no releases published yet"
            return result
        resp.raise_for_status()
        data = resp.json()
        tag = data.get("tag_name", "").lstrip("v")
        result["latest"] = tag
        result["url"] = data.get("html_url")
        result["published_at"] = data.get("published_at")
        result["notes"] = (data.get("body") or "")[:500]
        if _parse(tag) > _parse(__version__):
            result["update_available"] = True
    except requests.RequestException as e:
        result["error"] = f"could not reach GitHub: {e}"
    return result
