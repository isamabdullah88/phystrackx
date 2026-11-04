"""
The recent projects of the Qt spike, for the File menu's Open Recent. A small JSON file in
~/.phystrackx (beside the Tk app's recent.json, but its own list): the Tk app cannot open these
projects, so they must not appear in its menu. PHYSTRACK_QT_HOME moves the folder (the tests use it).
"""

import json
import logging
import os

RECENT_LIMIT = 8
logger = logging.getLogger(__name__)


def recent_file() -> str:
    home = os.environ.get("PHYSTRACK_QT_HOME") or os.path.join(os.path.expanduser("~"), ".phystrackx")
    return os.path.join(home, "recent-qt.json")


def load() -> list[str]:
    """Recent project paths, newest first. Projects that no longer exist are left out."""
    try:
        with open(recent_file(), encoding="utf-8") as f:
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
        os.makedirs(os.path.dirname(recent_file()), exist_ok=True)
        with open(recent_file(), "w", encoding="utf-8") as f:
            json.dump(paths[:RECENT_LIMIT], f, indent=2)
    except OSError:
        logger.exception("Could not save the recent projects list")


def forget_all() -> None:
    """Empties the list (the File menu's Clear Recent)."""
    try:
        os.remove(recent_file())
    except FileNotFoundError:
        pass
    except OSError:
        logger.exception("Could not clear the recent projects list")
