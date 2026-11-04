"""
The session: the trial windows open when the app was last closed, so a bare `phystrackx` (no files)
opens them again. Each window is recorded by its video, and by its project file if it has one (the
setup). Windows with no video are not recorded: there is nothing to reopen.

A window that is closed is dropped from the record on a zero-delay timer, not at once. Quitting closes
every window in one pass, and the timer does not run before the app exits, so all of them stay in the
record. A single window closed during use drops out straight away.

While the start reopens the last session's windows one by one (app.open_trials) the record is held, not
written: a quit before the last is open leaves the file as it was, the whole last session.

The file is session-qt.json in the same folder as the recent projects (recent.py); PHYSTRACK_QT_HOME
moves it (the tests use it).
"""

import json
import logging
import os

from PySide6.QtCore import QTimer

from phystrack_qt import recent

logger = logging.getLogger(__name__)

_entries: dict[str, dict] = {}   # window id -> {"project": path or None, "video": path}, in opening order
_held = False        # The record is kept in memory, not written (hold)
_unwritten = False   # A write came due while it was held


def hold() -> None:
    """Keeps the record from being written until release(). The start reopens the last session's windows one
    by one (app.open_trials), and a quit before the last would otherwise save the session with only the
    windows opened so far."""
    global _held
    _held = True


def release() -> None:
    """Lets the record be written again, and writes it if a write came due meanwhile."""
    global _held, _unwritten
    _held = False
    if _unwritten:
        _unwritten = False
        _write()


def session_file() -> str:
    return os.path.join(os.path.dirname(recent.recent_file()), "session-qt.json")


def update(window) -> None:
    """Records what `window` shows now. Called when a window opens a video, a project, or saves one."""
    video = window.source.path
    if not video:
        return
    _entries[window.wid] = {"project": window.project_path, "video": os.path.abspath(video)}
    _write()


def forget(wid: str) -> None:
    """Drops a closed window from the record, once the event loop next runs (see the module's docstring)."""
    QTimer.singleShot(0, lambda: _drop(wid))


def _drop(wid: str) -> None:
    if _entries.pop(wid, None) is not None:
        _write()


def _write() -> None:
    """Writes the record atomically, so a failed write never leaves a half-written file. While held, it only
    notes that a write is due."""
    global _unwritten
    if _held:
        _unwritten = True
        return
    path = session_file()
    tmp = path + ".part"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"windows": list(_entries.values())}, f, indent=2)
        os.replace(tmp, path)
    except OSError:
        logger.exception("Could not save the session")


def restorable() -> list[str] | None:
    """What to open for a bare start, in order: each window's project if its file exists, else its video.
    None if there is no record at all (a first start, or the record was deleted), so the caller can
    fall back to the most recent project. An empty list means the app was closed with nothing open."""
    try:
        with open(session_file(), encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        logger.exception("Could not read the session; starting empty")
        return []
    if not isinstance(data, dict) or not isinstance(data.get("windows"), list):
        return []
    targets = []
    for entry in data["windows"]:
        if not isinstance(entry, dict):
            continue
        project, video = entry.get("project"), entry.get("video")
        if isinstance(project, str) and os.path.isfile(project):
            targets.append(project)
        elif isinstance(video, str) and os.path.isfile(video):
            targets.append(video)
    return targets
