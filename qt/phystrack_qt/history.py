"""
Event history: every change to a window's setup, one row each, with a snapshot to go back to.

QUICK-AND-DIRTY (see docs/AGENT_PLAN.md, "Architecture notes"):
- No command layer. The history hangs off MainWindow._touch(), which every change already calls.
  A change is committed after a short pause (a drag makes one event, not hundreds), labelled with
  its op and the status-bar message the app shows for it anyway. The robust version would route
  every action through Command objects with typed params and make them replayable.
- Each event keeps a full _project_state() snapshot (tracked boxes included). Simple and exact,
  but memory grows with events x tracked frames; the robust version stores diffs.
- Revert never deletes: it appends a "revert" event whose snapshot is the target's, and greys the
  events it undid. The log stays append-only, so an agent (or the user) can see what was undone,
  and clicking a greyed event "redoes" it.
"""

import time
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidget, QListWidgetItem

COMMIT_MS = 300  # A change is committed once no other came for this long (drags make one event)
ACTIONS = ("open", "export_csv", "save_plots", "save_project", "plots", "revert", "copy_setup", "note")
COOKBOOK_OPS = ("save_plots", "export_csv", "save_project")   # The saves and exports: kept with the project, for recipes


@dataclass
class Event:
    n: int
    op: str
    text: str
    who: str = "user"                   # "user" or "agent"
    params: dict = field(default_factory=dict)
    snap: dict | None = None            # The window's state after the event (MainWindow._snapshot)
    t: float = field(default_factory=time.time)
    undone: bool = False                # Not part of the state now (greyed): a revert went past it
    base: int = 0                       # The event whose state this one changed (0: none)

    def row(self) -> list:
        """The compact form tools send to an LLM: [n, who, op, text] (+ params when any)."""
        r = [self.n, self.who[0], self.op, self.text[:140]]
        if self.params:
            r.append(self.params)
        if self.undone:
            r.append("undone")
        return r


def _same(a: dict | None, b: dict | None) -> bool:
    """Equal setups, ignoring the frame shown (seeking is not a change)."""
    if a is None or b is None:
        return a is b
    return {k: v for k, v in a.items() if k != "frame"} == {k: v for k, v in b.items() if k != "frame"}


class History(QObject):
    """
    `snapshot()` and `message()` are the window's: its state, and its status-bar text. `note(op)`
    marks a change (committed after COMMIT_MS); `log(op, text)` records an action at once (an
    export, a save). `who` is "agent" while an agent's tool call runs on the window
    (`agent_calls`, counted by the tools, so overlapping calls do not clear each other's mark).

    Each event records the event it changed (`base`): after a revert the state is the reverted-to
    event's, so what is in effect is that event and its chain of bases, and the rest is undone.
    """
    changed = Signal()

    def __init__(self, snapshot, message) -> None:
        super().__init__()
        self.snapshot, self.message = snapshot, message
        self.events: list[Event] = []
        self.cookbook: list[list] = []   # [op, params] of each save and export (COOKBOOK_OPS), kept in the project
        self.agent_calls = 0    # Agent tool calls under way on this window
        self.forced_who = None  # A test harness acting as the user, whatever runs meanwhile
        self.head = 0           # The event whose state is the window's now
        self.paused = False     # True while a revert or an open puts state back (not a change)
        self._op, self._params = None, {}
        self._snap = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(COMMIT_MS)
        self._timer.timeout.connect(self.flush)

    @property
    def who(self) -> str:
        return self.forced_who or ("agent" if self.agent_calls > 0 else "user")

    def reset(self) -> None:
        self._timer.stop()
        self._op, self._params, self._snap = None, {}, None
        self.events.clear()
        self.cookbook.clear()
        self.head = 0
        self.changed.emit()

    def note(self, op: str = "edit", params: dict | None = None) -> None:
        """A change `op` was just made. More of the same op soon after (a drag) join its event; a
        different op commits the pending one first, as it was before this change."""
        if self.paused:
            return
        if self._op is not None and op not in (self._op, "edit") and self._op != "edit":
            self.flush(fresh=False)
        if self._op is None or self._op == "edit":   # A named op wins over a generic edit
            self._op = op
        if params:
            self._params.update(params)
        self._snap = self.snapshot()   # The state after this change (the pending event's, so far)
        self._timer.start()

    def flush(self, fresh: bool = True) -> None:
        """Commits the pending change now (the bridge calls it at the end of each tool call).
        `fresh`: with the state now (else as it was at the pending op's last change)."""
        self._timer.stop()
        if self._op is None:
            return
        op, params = self._op, self._params
        self._op, self._params = None, {}
        snap = self.snapshot() if fresh else self._snap
        if self.events and _same(snap, self.events[-1].snap):
            return    # Nothing actually changed (e.g. a drag that ended where it began)
        self._add(op, self.message() or op, params, snap)

    def log(self, op: str, text: str, params: dict | None = None) -> Event:
        self.flush()
        if op in COOKBOOK_OPS:
            self.cookbook.append([op, params or {}])
        return self._add(op, text, params or {}, self.snapshot())

    def _add(self, op, text, params, snap, base: int | None = None) -> Event:
        event = Event(len(self.events) + 1, op, text, self.who, params, snap,
                      base=self.head if base is None else base)
        self.events.append(event)
        self.head = event.n
        self._mark_undone()
        self.changed.emit()
        return event

    def _mark_undone(self) -> None:
        """Undone: every event not in the chain of bases from the current one."""
        live, n = set(), self.head
        while n and n not in live:
            live.add(n)
            n = self.events[n - 1].base
        for e in self.events:
            e.undone = e.n not in live

    def last(self) -> int:
        return self.events[-1].n if self.events else 0

    def revert_target(self, n: int) -> dict | None:
        """The snapshot to put back to go to event n, and the revert event logged: its state is
        n's, so n and what led to n are in effect, and the rest is undone (going back to a greyed
        event redoes it, with what came before it). None if there is no such event."""
        self.flush()
        if not 1 <= n <= len(self.events) or n == len(self.events):
            return None
        target = self.events[n - 1]
        self._add("revert", f"Back to #{n}: {target.text[:60]}", {"to": n}, target.snap, base=n)
        return target.snap

    def since(self, n: int) -> list[list]:
        return [e.row() for e in self.events[n:]]


class HistoryPanel(QListWidget):
    """The history as a list, newest at the bottom. A click on an earlier event reverts to it."""

    def __init__(self, history: History, revert) -> None:
        super().__init__()
        self.history, self._revert = history, revert
        self.setWordWrap(True)
        self.setToolTip("Every change, in order. Click one to go back to it (that is logged too, so "
                        "it can be undone by clicking a later one)")
        history.changed.connect(self.refresh)
        self.itemClicked.connect(self._clicked)

    def refresh(self) -> None:
        self.blockSignals(True)
        self.clear()
        for e in self.history.events:
            who = "🤖 " if e.who == "agent" else ""
            item = QListWidgetItem(f"#{e.n} {who}{e.op}: {e.text}")
            item.setData(Qt.ItemDataRole.UserRole, e.n)
            item.setToolTip(time.strftime("%H:%M:%S", time.localtime(e.t)) + f"  {e.text}")
            if e.undone:
                item.setForeground(QColor("#888888"))
            elif e.who == "agent":
                item.setForeground(QColor("#3a7bd5"))
            self.addItem(item)
        self.blockSignals(False)
        self.scrollToBottom()

    def _clicked(self, item: QListWidgetItem) -> None:
        n = item.data(Qt.ItemDataRole.UserRole)
        if n != self.history.last():
            self._revert(n)
