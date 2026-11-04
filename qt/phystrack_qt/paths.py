"""
Where the app keeps what it writes: the proxy videos, the agent bridge's port, the projects of
videos in a read-only folder, and (packaged app) matplotlib's font cache.

Never the folder the app runs from: an installed or packaged app runs from a read-only place (a
signed .app bundle, Program Files, site-packages) and a write there fails or breaks the signature.
PHYSTRACK_QT_HOME moves the data folder (the tests use it, as the recent list does).
"""

import os

from platformdirs import user_cache_dir, user_data_dir

APP_NAME = "PhysTrackX"


def cache_dir() -> str:
    """Proxy videos and the bridge's port file. Large, and safe to delete."""
    home = os.environ.get("PHYSTRACK_QT_HOME")
    return os.path.join(home, "cache") if home else user_cache_dir(APP_NAME, appauthor=False)


def matplotlib_dir() -> str:
    """Matplotlib's config and font-cache folder in the packaged app (packaging/entry.py). Always in the user's
    cache folder, whatever PHYSTRACK_QT_HOME says: it is not something a run writes for itself, and the
    install's hidden launch (which has a throwaway home) fills it, so the first real start finds the font
    cache built. Small, and safe to delete."""
    return os.path.join(user_cache_dir(APP_NAME, appauthor=False), "matplotlib")


def projects_dir() -> str:
    """Projects of a video whose folder is read-only."""
    home = os.environ.get("PHYSTRACK_QT_HOME")
    return os.path.join(home, "projects") if home else os.path.join(user_data_dir(APP_NAME, appauthor=False), "projects")


def runner_dir() -> str:
    """Ollama, when the app installs it for the assistant (agent/runner.py), and its log."""
    home = os.environ.get("PHYSTRACK_QT_HOME")
    return os.path.join(home, "ollama") if home else os.path.join(user_data_dir(APP_NAME, appauthor=False), "ollama")
