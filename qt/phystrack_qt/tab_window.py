"""
The window that holds trials as tabs: a tab bar (one tab per trial, named after its project or video) over
the trial shown. Each tab is a MainWindow, embedded: it keeps its own docks, status bar, menus and keys.

Menus: the window's menu bar shows the current tab's menus (they are the tab's own QMenus, added here), and
a Window menu of its own. Settings… (Cmd+,) is in the app menu on macOS (Qt moves it there), else in a
Settings menu before Window. A tab's own menu bar is hidden and not native, so only the current tab's menu
shortcuts are live; a tab that is not shown is hidden, so its keys (QShortcut) are not live either.

Ctrl+T (Cmd+T) adds a tab here, Ctrl+N (Cmd+N) opens another of these windows (windows.new_window).
"""

import os
import sys

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QKeySequence, QPainter, QPalette, QPen
from PySide6.QtWidgets import (QAbstractButton, QHBoxLayout, QMainWindow, QMenu, QStackedWidget, QTabBar,
                               QVBoxLayout, QWidget)

from . import windows

# The physical Control key: Qt calls it Meta on macOS (where Ctrl is Cmd, and Cmd+Tab is the system's)
_CONTROL = Qt.KeyboardModifier.MetaModifier if sys.platform == "darwin" else Qt.KeyboardModifier.ControlModifier


TAB_WIDTH = (160, 260)   # A tab's narrowest and widest, in pixels: wide as a browser's, names elided past it


class _TabBar(QTabBar):
    def tabSizeHint(self, index: int) -> QSize:
        hint = super().tabSizeHint(index)
        return QSize(max(TAB_WIDTH[0], min(TAB_WIDTH[1], hint.width())), max(hint.height(), 30))


class _MarkButton(QAbstractButton):
    """The tab's × or the + after the tabs: two strokes drawn at the button's centre (a font's × or + sits
    off it, on the text's baseline), flat, with a rounded highlight under the pointer, as a browser's."""

    def __init__(self, mark: str, size: int, tip: str) -> None:
        super().__init__()
        self.mark, self.arm = mark, size * 0.22   # Half a stroke's length
        self.setFixedSize(size, size)
        self.setToolTip(tip)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.underMouse():
            shade = QColor(128, 128, 128, 140 if self.isDown() else 90)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(shade)
            p.drawRoundedRect(QRectF(self.rect()), 4, 4)
        pen = QPen(self.palette().color(QPalette.ColorRole.ButtonText), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        c, a = QPointF(self.width() / 2, self.height() / 2), self.arm
        if self.mark == "x":
            p.drawLine(c + QPointF(-a, -a), c + QPointF(a, a))
            p.drawLine(c + QPointF(-a, a), c + QPointF(a, -a))
        else:
            p.drawLine(c + QPointF(-a, 0), c + QPointF(a, 0))
            p.drawLine(c + QPointF(0, -a), c + QPointF(0, a))
        p.end()


class Tabs(QWidget):
    """A browser's tab strip over the page shown: the tabs, each with a close button (×) always shown, then
    a + button just after the last tab. The part of QTabWidget's interface this app uses; a QTabWidget puts
    its + at the window's far edge instead (its corner)."""
    currentChanged = Signal(int)
    tabCloseRequested = Signal(int)

    def __init__(self, on_new_tab) -> None:
        super().__init__()
        self.bar = _TabBar()
        self.bar.setDocumentMode(True)
        self.bar.setMovable(True)
        self.bar.setExpanding(False)
        self.bar.setUsesScrollButtons(True)
        self.bar.setElideMode(Qt.TextElideMode.ElideMiddle)
        self.bar.setDrawBase(False)
        self.bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # Keys stay with the trial (Space, arrows, letters)
        self.plus = _MarkButton("+", 24, "New Tab")
        self.plus.clicked.connect(on_new_tab)
        strip = QHBoxLayout()
        strip.setContentsMargins(4, 2, 4, 0)
        strip.setSpacing(4)
        strip.addWidget(self.bar)
        strip.addWidget(self.plus)
        strip.addStretch(1)
        self.stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(strip)
        layout.addWidget(self.stack, 1)
        self.bar.currentChanged.connect(self._bar_changed)

    def _bar_changed(self, index: int) -> None:
        page = self.widget(index)
        if page is not None:
            self.stack.setCurrentWidget(page)
        self.currentChanged.emit(index)

    def addTab(self, page, text: str) -> int:
        self.stack.addWidget(page)
        index = self.bar.addTab(text)
        self.bar.setTabData(index, page)
        close = _MarkButton("x", 18, "Close Tab")
        close.clicked.connect(lambda _=False, p=page: self.tabCloseRequested.emit(self.indexOf(p)))
        self.bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, close)
        if self.bar.count() == 1:
            self._bar_changed(0)   # The bar's first tab is current without a signal from it
        return index

    def removeTab(self, index: int) -> None:
        page = self.widget(index)
        self.bar.removeTab(index)   # Shows the tab to its right, else the one to its left
        if page is not None:
            self.stack.removeWidget(page)

    def widget(self, index: int):
        return self.bar.tabData(index) if 0 <= index < self.bar.count() else None

    def indexOf(self, page) -> int:
        return next((i for i in range(self.bar.count()) if self.bar.tabData(i) is page), -1)

    def count(self) -> int:
        return self.bar.count()

    def currentIndex(self) -> int:
        return self.bar.currentIndex()

    def setCurrentIndex(self, index: int) -> None:
        self.bar.setCurrentIndex(index)

    def currentWidget(self):
        return self.widget(self.bar.currentIndex())

    def setCurrentWidget(self, page) -> None:
        index = self.indexOf(page)
        if index >= 0:
            self.bar.setCurrentIndex(index)

    def tabText(self, index: int) -> str:
        return self.bar.tabText(index)

    def setTabText(self, index: int, text: str) -> None:
        self.bar.setTabText(index, text)

    def setTabToolTip(self, index: int, text: str) -> None:
        self.bar.setTabToolTip(index, text)


class TabWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._closing = False
        self.tabs = Tabs(lambda: windows.new_window(host=self))
        self.tabs.tabCloseRequested.connect(lambda i: self.tabs.widget(i).close_tab())
        self.tabs.currentChanged.connect(self._current_changed)
        self.setCentralWidget(self.tabs)

        self.window_menu = QMenu("Window", self)
        for text, step, keys in (("Next Tab", 1, (QKeySequence(_CONTROL | Qt.Key.Key_Tab), QKeySequence("Ctrl+}"))),
                                 ("Previous Tab", -1, (QKeySequence(_CONTROL | Qt.KeyboardModifier.ShiftModifier |
                                                                    Qt.Key.Key_Tab), QKeySequence("Ctrl+{")))):
            action = QAction(text, self.window_menu)
            action.setShortcuts(list(keys))
            action.triggered.connect(lambda _=False, s=step: self.step(s))
            self.window_menu.addAction(action)
        self.window_menu.addSeparator()
        self._tab_actions: list[QAction] = []    # One per tab, under the separator (filled when shown)
        self.window_menu.aboutToShow.connect(self._fill_window_menu)
        for n in range(1, 10):   # Ctrl+1..9 (Cmd on macOS): that tab; 9 is the last, as in browsers
            action = QAction(self)
            action.setShortcut(QKeySequence(f"Ctrl+{n}"))
            action.triggered.connect(lambda _=False, k=n: self.select(k))
            self.addAction(action)
        # Settings…: on macOS, Qt moves an action with this role to the app menu, wherever it is put
        self.settings_action = QAction("Settings…", self)
        self.settings_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.settings_action.setShortcut(QKeySequence("Ctrl+,"))
        self.settings_action.triggered.connect(self._open_settings)
        self.settings_menu = None
        if sys.platform == "darwin":
            self.window_menu.insertAction(self.window_menu.actions()[0], self.settings_action)
        else:
            self.settings_menu = QMenu("Settings", self)
            self.settings_menu.addAction(self.settings_action)
            self.menuBar().addMenu(self.settings_menu)
        self.menuBar().addMenu(self.window_menu)
        windows.add_host(self)

    # --- Tabs ------------------------------------------------------------------------------------
    def add(self, tab, select: bool = True) -> None:
        """Puts the trial window `tab` in a new tab at the end (shown, if `select`)."""
        menu_bar = tab.menuBar()
        menu_bar.setNativeMenuBar(False)   # Its menus show in this window's menu bar instead
        menu_bar.hide()
        tab.host = self
        index = self.tabs.addTab(tab, "")
        tab.windowTitleChanged.connect(lambda _title, t=tab: self._retitle(t))
        self._retitle(tab)
        if select:
            self.tabs.setCurrentIndex(index)

    def remove(self, tab) -> None:
        """Drops a closed trial's tab. This window closes when its last tab goes."""
        index = self.tabs.indexOf(tab)
        if index < 0:
            return
        self.tabs.removeTab(index)
        tab.host = None
        # Out of this window once its close is over, so it lives only as long as something refers to it
        QTimer.singleShot(0, lambda: tab.setParent(None))
        if self.tabs.count() == 0 and not self._closing:
            QTimer.singleShot(0, self.close)

    def trials(self) -> list:
        """The trial windows, in tab order."""
        return [self.tabs.widget(i) for i in range(self.tabs.count())]

    def current(self):
        return self.tabs.currentWidget()

    def show_tab(self, tab) -> None:
        self.tabs.setCurrentWidget(tab)

    def step(self, by: int) -> None:
        """The next tab (by=1) or the one before (-1), round the end."""
        if self.tabs.count():
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + by) % self.tabs.count())

    def select(self, n: int) -> None:
        """Ctrl+n: the nth tab; 9 is the last one."""
        count = self.tabs.count()
        if count:
            self.tabs.setCurrentIndex(count - 1 if n == 9 else min(n, count) - 1)

    def _retitle(self, tab) -> None:
        index = self.tabs.indexOf(tab)
        if index < 0:
            return
        self.tabs.setTabText(index, tab.tab_name())
        path = tab.project_path or tab.source.path
        self.tabs.setTabToolTip(index, f"{os.path.abspath(path)}  [{tab.wid}]" if path else f"[{tab.wid}]")
        if tab is self.current():
            self.setWindowTitle(tab.windowTitle())

    def _current_changed(self, index: int) -> None:
        tab = self.tabs.widget(index)
        if tab is None:
            return
        self._show_menus(tab)
        self.setWindowTitle(tab.windowTitle())
        if self.isVisible():
            windows.activated(tab.wid)
            tab.view.setFocus()

    def _show_menus(self, tab) -> None:
        """This window's menu bar: the tab's menus, then Settings (not on macOS) and the Window menu."""
        bar = self.menuBar()
        bar.clear()   # Takes the menus out; they belong to their tab, so are not deleted
        for action in tab.menuBar().actions():
            bar.addAction(action)
        if self.settings_menu is not None:
            bar.addMenu(self.settings_menu)
        bar.addMenu(self.window_menu)

    def _open_settings(self) -> None:
        from . import settings_dialog
        settings_dialog.show()

    def _fill_window_menu(self) -> None:
        """The Window menu lists the tabs; choosing one shows it."""
        for action in self._tab_actions:
            self.window_menu.removeAction(action)
            action.deleteLater()
        self._tab_actions = []
        current = self.current()
        for tab in self.trials():
            action = QAction(tab.tab_name(), self.window_menu)
            action.setCheckable(True)
            action.setChecked(tab is current)
            action.triggered.connect(lambda _=False, t=tab: windows.focus(t))
            self.window_menu.addAction(action)
            self._tab_actions.append(action)

    # --- Window ----------------------------------------------------------------------------------
    def changeEvent(self, event) -> None:
        if event.type() == event.Type.ActivationChange and self.isActiveWindow() and self.current() is not None:
            windows.activated(self.current().wid)
        super().changeEvent(event)

    def closeEvent(self, event) -> None:
        """Closing the window closes each tab, each with its unsaved-changes check (shown on its tab). A
        Cancel keeps the window open, with the tabs not yet closed."""
        self._closing = True
        try:
            for tab in self.trials():
                if tab._dirty:
                    self.show_tab(tab)
                if not tab.close():
                    event.ignore()
                    return
        finally:
            self._closing = False
        windows.remove_host(self)
        event.accept()
