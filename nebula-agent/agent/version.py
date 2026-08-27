"""Single source of truth for Nova's version.

Bumped on each release. `agent/updater.py` reads this and compares
against the GitHub Releases API to decide if there's an update available.
"""
__version__ = "0.6.0"
__github_repo__ = "nebula-linux-os/Nebula-Linux"
