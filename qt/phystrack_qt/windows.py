"""
Every open trial window, by a short id ("w1", "w2", ...), and the agent gate (Space stops an agent).

Any number of trial windows: each is one video (one trial) with its own setup and history. The agent
tools name them by id. In the app each is a tab of a TabWindow (tab_window.py): File > New Tab (Ctrl+T)
adds one to the window in front, File > New Window (Ctrl+N) opens another TabWindow. A MainWindow made
directly (as the tests do) is a window of its own, with no tab bar.

QUICK-AND-DIRTY (see docs/AGENT_PLAN.md, "Architecture notes"): a module-level registry, one per
process, rather than an application/document model passed around. Ids are never reused within a
run, so an agent's "w2" never silently means a different trial.
"""

import itertools
import os
import time

from PySide6.QtCore import QObject, Signal

from phystrack_qt import paths

_windows: dict = {}          # id -> MainWindow, in the order they were opened
_ids = itertools.count(1)
active: str | None = None    # The window the user last brought to the front
_hosts: list = []            # The open TabWindows, oldest first
closed: list[dict] = []      # Trials closed during this run, most recent last (see MainWindow._closed_entry)
CLOSED_LIMIT = 20


def add(window) -> str:
    global active
    wid = f"w{next(_ids)}"
    _windows[wid] = window
    active = active or wid
    return wid


def remove(wid: str) -> None:
    global active
    _windows.pop(wid, None)
    if active == wid:
        active = next(reversed(_windows), None) if _windows else None


def activated(wid: str) -> None:
    global active
    if wid in _windows:
        active = wid


def neighbour(wid: str) -> str | None:
    """The window opened after `wid`, else the one before it: the tab to show when `wid` closes. None if
    `wid` is the only window."""
    ids = list(_windows)
    if wid not in ids or len(ids) < 2:
        return None
    i = ids.index(wid)
    return ids[i + 1] if i + 1 < len(ids) else ids[i - 1]


def remember_closed(entry: dict) -> None:
    closed.append(entry)
    del closed[:-CLOSED_LIMIT]


def reopen_closed():
    """Reopens the last trial closed (Cmd+Shift+T) in a new window, as it was when closed. Trials whose video
    is gone are passed over. Returns the window, or None if nothing can be reopened."""
    while closed:
        entry = closed.pop()
        if not os.path.isfile(entry["video"]):
            continue
        window = new_window()
        if window.restore_closed(entry):
            focus(window)
            return window
        window.close()
    return None


def add_host(host) -> None:
    _hosts.append(host)


def remove_host(host) -> None:
    if host in _hosts:
        _hosts.remove(host)


def hosts() -> list:
    return list(_hosts)


def _front_host():
    """The TabWindow of the active trial, else the newest one open, else None."""
    window = get()
    if window is not None and window.host is not None:
        return window.host
    return _hosts[-1] if _hosts else None


def get(wid: str | None = None):
    """The window `wid` (None: the active one), or None."""
    return _windows.get(wid or active) if (wid or active) else None


def all_windows() -> dict:
    return dict(_windows)


def new_window(path: str | None = None, show: bool = True, separate: bool = False, host=None,
               cache_dir: str | None = None):
    """A new, empty trial (with the same proxy cache as the others), opening `path` if given (a video or a
    project). It is a new tab of `host`, else of the window in front; `separate` (or no window open) puts
    it in a new window. `show`: the tab is shown and its window too."""
    from .main_window import MainWindow
    from .tab_window import TabWindow
    cache = cache_dir or (next(iter(_windows.values())).cache_dir if _windows else paths.cache_dir())
    host = host or (None if separate else _front_host())
    if host is None:
        host = TabWindow()
        host.resize(1440, 900)
    window = MainWindow(cache)
    host.add(window, select=show)
    if show:
        host.show()
        activated(window.wid)
    if path:
        if path.endswith(".phystrack"):
            window.open_project_file(path)
        else:
            window.load_video(path)
    return window


def focus(window) -> None:
    """Brings `window` to the front (its tab, and the window the tab is in): the user's view follows the
    agent to it."""
    front = window
    if window.host is not None:
        window.host.show_tab(window)
        front = window.host
    front.show()
    front.raise_()
    front.activateWindow()
    activated(window.wid)


class AgentGate(QObject):
    """
    Whether an agent is working, and the user's brake on it. Space (in any window) stops a working
    agent: its tool calls are refused until it calls `resume`, which tells it what the user changed
    meanwhile (the history events since the stop).

    QUICK-AND-DIRTY: an outside agent (MCP) counts as working during a tool call and for ACTIVE_S
    after one (it thinks between calls). The in-app assistant says exactly (`session_busy`).
    """
    changed = Signal()
    ACTIVE_S = 30.0

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0          # Tool calls under way
        self.last = 0.0         # When the last one ended
        self.stopped = False
        self.marks: dict = {}   # Window id -> its last event when the user stopped the agent
        self.session_busy = False   # The in-app assistant is working (thinking or calling)

    def busy(self) -> bool:
        """Working right now: a tool call runs, or the in-app assistant is thinking."""
        return not self.stopped and (self.calls > 0 or self.session_busy)

    def running(self) -> bool:
        return self.busy() or (not self.stopped and time.time() - self.last < self.ACTIVE_S)

    def begin(self) -> None:
        self.calls += 1
        self.changed.emit()

    def end(self) -> None:
        self.calls = max(0, self.calls - 1)
        self.last = time.time()
        self.changed.emit()

    def stop(self) -> None:
        """The user's brake: refuses the agent's calls, and stops a track it started."""
        self.stopped = True
        self.marks = {wid: w.history.last() for wid, w in _windows.items()}
        for w in _windows.values():
            if w.job is not None and w.agent_track:   # Only a track the agent started
                w._stop_track()
        self.changed.emit()

    def resume(self) -> dict:
        """Lets the agent go on. Returns, per window, the events since the stop (what the user did)."""
        if not self.stopped:
            return {}
        changes = {wid: w.history.since(self.marks.get(wid, 0)) for wid, w in _windows.items()
                   if w.history.since(self.marks.get(wid, 0))}
        self.stopped = False
        self.last = time.time()
        self.changed.emit()
        return changes


AGENT = AgentGate()
