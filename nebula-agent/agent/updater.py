"""Check GitHub Releases for a newer Nova version.

Non-invasive: only tells you if an update is available and returns the
release URL. Does NOT auto-download or overwrite anything — the user
opts in via `install.py --update` or a UI prompt.

The repo also publishes Nebula Linux ISO releases (tags like
`arch-beta-1.1`), and one of those may be marked "Latest". So this does
not use /releases/latest: it lists releases and considers only Nova's
own tags (`vMAJOR.MINOR.PATCH`), ignoring drafts and pre-releases.
"""
from __future__ import annotations

import re

import requests

from .version import __github_repo__, __version__

# Nova release tags: v0.8.0, v1.2.3. Distro tags (arch-beta-1.1, v1.0-beta) don't match.
NOVA_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def _parse(v: str) -> tuple[int, ...]:
    m = re.findall(r"\d+", v)
    return tuple(int(x) for x in m[:3]) if m else (0, 0, 0)


def _latest_nova_release(releases: list[dict]) -> dict | None:
    """Newest published, non-prerelease release with a Nova tag, or None."""
    best, best_ver = None, None
    for rel in releases:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        m = NOVA_TAG.match(rel.get("tag_name") or "")
        if not m:
            continue
        ver = tuple(int(x) for x in m.groups())
        if best_ver is None or ver > best_ver:
            best, best_ver = rel, ver
    return best


def check_for_update(timeout: int = 8) -> dict:
    """Returns {'current': str, 'latest': str|None, 'update_available': bool, ...}"""
    result: dict = {"current": __version__, "latest": None, "update_available": False}
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{__github_repo__}/releases",
            params={"per_page": 50},
            timeout=timeout,
            headers={"Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        data = _latest_nova_release(resp.json())
        if data is None:
            result["note"] = "no Nova releases published yet"
            return result
        tag = data["tag_name"].lstrip("v")
        result["latest"] = tag
        result["url"] = data.get("html_url")
        result["published_at"] = data.get("published_at")
        result["notes"] = (data.get("body") or "")[:500]
        if _parse(tag) > _parse(__version__):
            result["update_available"] = True
    except (requests.RequestException, ValueError) as e:
        result["error"] = f"could not reach GitHub: {e}"
    return result
