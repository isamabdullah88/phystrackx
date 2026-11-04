"""
recent.py

The most recently opened projects, for the File menu's Open Recent list. Kept in a small JSON file
in the user's home folder (~/.phystrackx/recent.json), so it survives restarts and is shared by
every copy of the app on this account.

Author: Isam Balghari
"""

import json
import logging
import os

RECENT_LIMIT = 8
RECENT_FILE = os.path.join(os.path.expanduser("~"), ".phystrackx", "recent.json")

logger = logging.getLogger(__name__)


def load() -> list[str]:
    """Recent project paths, newest first. Projects that no longer exist are left out."""
    try:
        with open(RECENT_FILE, encoding="utf-8") as f:
            paths = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(paths, list):
        return []
    return [p for p in paths if isinstance(p, str) and os.path.isfile(p)][:RECENT_LIMIT]


def remember(project_path: str) -> None:
    """Puts a project at the top of the list (a repeat moves it up rather than adding it again)."""
    path = os.path.abspath(project_path)
    paths = [path] + [p for p in load() if os.path.abspath(p) != path]
    try:
        os.makedirs(os.path.dirname(RECENT_FILE), exist_ok=True)
        with open(RECENT_FILE, "w", encoding="utf-8") as f:
            json.dump(paths[:RECENT_LIMIT], f, indent=2)
    except OSError:
        logger.exception("Could not save the recent projects list")


def forget_all() -> None:
    """Empties the list (the File menu's Clear Recent)."""
    try:
        os.remove(RECENT_FILE)
    except FileNotFoundError:
        pass
    except OSError:
        logger.exception("Could not clear the recent projects list")
