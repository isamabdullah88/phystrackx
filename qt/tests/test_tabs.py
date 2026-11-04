"""
Tabs: Cmd+W closes the current one and shows the next; the last one is replaced by a blank one. Cmd+T opens
a blank one. Cmd+Shift+T reopens the last closed one, with its setup as it was. In the app the tabs sit in
a tab bar (tab_window.py), named after their trial; a MainWindow made on its own (h.window) has none.

    uv run python tests/test_tabs.py
"""

import os

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from PySide6.QtCore import QRectF  # noqa: E402

from phystrack_qt import windows
from phystrack_qt.main_window import MainWindow  # noqa: E402
from test_tracking import make_clip  # noqa: E402


def close_all() -> None:
    """Every window closed and the closed list cleared, so each test starts alone."""
    for w in list(windows.all_windows().values()):
        w._dirty = False
        w.close()
    for host in windows.hosts():
        host.close()
    h.pump(timeout=0.1)
    windows.closed.clear()


def tab_texts(host) -> list[str]:
    return [host.tabs.tabText(i) for i in range(host.tabs.count())]


def test_tab_bar_names_each_trial() -> None:
    close_all()
    first = windows.new_window()
    host = first.host
    h.check("a new window is a tab of a tab window", host is not None and host.trials() == [first])
    h.check("...named New Tab while blank", tab_texts(host) == ["New Tab"], str(tab_texts(host)))
    clip = make_clip()
    first.load_video(clip)
    h.check("...then after its video", tab_texts(host) == [os.path.basename(clip)], str(tab_texts(host)))
    second = windows.new_window()
    h.check("New Tab adds a tab to the same window", second.host is host and host.trials() == [first, second])
    h.check("...and shows it", host.current() is second and windows.get() is second)
    first._touch()
    h.check("unsaved changes star the tab", tab_texts(host)[0] == os.path.basename(clip) + " *", str(tab_texts(host)))
    windows.focus(first)
    h.check("focus shows that trial's tab", host.current() is first)
    h.check("...and the window title is the tab's", host.windowTitle() == first.windowTitle(), host.windowTitle())
    first._dirty = False
    close_all()


def test_menus_follow_the_tab() -> None:
    close_all()
    first, second = windows.new_window(), windows.new_window()
    host = first.host
    menus = lambda: [a.menu() for a in host.menuBar().actions()]   # noqa: E731
    h.check("the menu bar has the shown tab's menus", second.menuBar().actions()[0].menu() in menus())
    h.check("...not the other tab's", first.menuBar().actions()[0].menu() not in menus())
    h.check("...and the Window menu", host.window_menu in menus())
    windows.focus(first)
    h.check("switching tabs switches the menus", first.menuBar().actions()[0].menu() in menus()
            and second.menuBar().actions()[0].menu() not in menus())
    h.check("a tab's own menu bar is hidden", not first.menuBar().isVisible())
    close_all()


def test_tab_bar_close_and_step() -> None:
    close_all()
    a, b, c = windows.new_window(), windows.new_window(), windows.new_window()
    host = a.host
    windows.focus(b)
    host.step(1)
    h.check("Next Tab shows the one to the right", host.current() is c)
    host.step(1)
    h.check("...round the end", host.current() is a)
    host.select(9)
    h.check("Ctrl+9 shows the last tab", host.current() is c)
    windows.focus(b)
    host.tabs.tabCloseRequested.emit(host.tabs.indexOf(b))
    h.pump(timeout=0.1)
    h.check("the close button closes that tab", host.trials() == [a, c], str([t.wid for t in host.trials()]))
    h.check("...and shows the one to its right", host.current() is c)
    h.check("...and the trial is gone", b.wid not in windows.all_windows())
    c.close_tab()
    a.close_tab()
    h.pump(timeout=0.1)
    h.check("closing the last tab leaves a blank one in the same window",
            len(host.trials()) == 1 and host.trials()[0].source.path in (None, "") and host.isVisible())
    close_all()


def test_new_window_and_its_last_tab() -> None:
    close_all()
    first = windows.new_window()
    other = windows.new_window(separate=True)
    h.check("New Window opens a second tab window", other.host is not first.host and len(windows.hosts()) == 2)
    host = other.host
    other.close_tab()
    h.pump(timeout=0.2)
    h.check("closing the last tab of a second window closes that window",
            host not in windows.hosts() and not host.isVisible())
    h.check("...and leaves the first", windows.hosts() == [first.host])
    close_all()


def test_same_video_in_two_tabs_at_once() -> None:
    """Two tabs opening one video with no proxy yet each make one; neither fails (they once shared a file)."""
    import shutil
    from phystrack_qt.video_source import VideoSource
    cache = os.path.join(h.WORK, "cold_cache")
    shutil.rmtree(cache, ignore_errors=True)
    clip = make_clip()
    sources = [VideoSource(cache), VideoSource(cache)]
    failures = []
    for source in sources:
        source.failed.connect(failures.append)
        source.load(clip)
    h.pump(lambda: failures or all(s.has_proxy for s in sources), timeout=60)
    h.check("both tabs get the proxy, with no failure", not failures and all(s.has_proxy for s in sources),
            str(failures))
    left = [name for name in os.listdir(cache) if not name.endswith("_info.json")]   # (the video's note is beside its proxy)
    h.check("...and one proxy file is left in the cache", len(left) == 1 and left[0].endswith("_proxy.mp4"), str(os.listdir(cache)))


def test_file_menu_groups() -> None:
    """The File menu is grouped as a browser's: new and open, then close and save, then export."""
    close_all()
    w = windows.new_window()
    file_menu = [a for a in w.menuBar().actions() if a.text() == "File"][0].menu()
    texts = ["---" if a.isSeparator() else a.text() for a in file_menu.actions()]
    want = ["New Tab", "New Window", "Reopen Closed Tab", "Open Video…", "Open Project…", "Open Recent", "---",
            "Close Window", "Close Tab", "Save Project", "Save Project As…", "---", "Export Data (CSV)…"]
    h.check("File menu order and separators", texts == want, str(texts))
    other = windows.new_window()
    host = w.host
    file_action(other, "Close Window").trigger()
    h.pump(timeout=0.1)
    h.check("Close Window closes the window and its tabs", not host.isVisible() and not windows.all_windows())
    close_all()


def test_closing_the_window_asks_per_tab() -> None:
    close_all()
    a, b = windows.new_window(), windows.new_window()
    host = a.host
    a._dirty = True
    asked = []
    real = MainWindow._confirm_discard
    MainWindow._confirm_discard = lambda self: asked.append(self) or False   # The user chose Cancel
    try:
        h.check("Cancel keeps the window open", not host.close() and host.isVisible())
        h.check("...having shown the unsaved tab first", asked == [a] and host.current() is a)
    finally:
        MainWindow._confirm_discard = real
    a._dirty = False
    h.check("closing it with nothing unsaved closes every tab", host.close() and not windows.all_windows())
    close_all()


def file_action(window, text: str):
    file_menu = [a for a in window.menuBar().actions() if a.text() == "File"][0].menu()
    return [a for a in file_menu.actions() if a.text() == text][0]


def test_close_tab_shows_the_next_window() -> None:
    close_all()
    first, second = h.window(), h.window()
    first.load_video(make_clip())
    second.load_video(make_clip())
    first.close_tab()
    h.check("closing a tab leaves the other one", list(windows.all_windows()) == [second.wid],
            str(list(windows.all_windows())))
    h.check("...and it comes to the front", windows.get() is second)
    close_all()


def test_closing_the_last_tab_shows_a_blank_one() -> None:
    close_all()
    only = h.window()
    only.load_video(make_clip())
    only.close_tab()
    remaining = list(windows.all_windows().values())
    h.check("the last tab is replaced, so there is one window", len(remaining) == 1, str(len(remaining)))
    h.check("...and it is blank (no video)", remaining and remaining[0].source.path in (None, ""))
    h.check("...and it is not the closed one", remaining and remaining[0] is not only)
    close_all()


def test_new_tab_is_blank() -> None:
    close_all()
    existing = h.window()
    existing.load_video(make_clip())
    new = windows.new_window()
    h.check("New Tab adds a window", len(windows.all_windows()) == 2)
    h.check("...that is blank", new.source.path in (None, ""))
    close_all()


def test_reopen_closed_restores_the_setup() -> None:
    close_all()
    clip = make_clip()
    w = h.window()
    w.load_video(clip)
    w._add_object(QRectF(100, 100, 40, 40))
    objects = len(w.objects)
    dirty = w._dirty
    real = MainWindow._confirm_discard
    MainWindow._confirm_discard = lambda self: True   # The user chose to discard the unsaved changes
    try:
        w.close_tab()
    finally:
        MainWindow._confirm_discard = real
    h.check("a closed tab is remembered", len(windows.closed) == 1 and windows.closed[-1]["video"] == os.path.abspath(clip))
    reopened = windows.reopen_closed()
    h.check("Reopen Closed Tab opens a window", reopened is not None)
    if reopened is not None:
        h.check("...with the same video", reopened.source.path == os.path.abspath(clip), str(reopened.source.path))
        h.check("...and its objects as they were", len(reopened.objects) == objects,
                f"{len(reopened.objects)} vs {objects}")
        h.check("...and its unsaved state", reopened._dirty == dirty)
    h.check("nothing is left to reopen after that", windows.reopen_closed() is None)
    close_all()


def test_shortcuts() -> None:
    close_all()
    w = h.window()
    keys = {"Close Tab": "Ctrl+W", "New Tab": "Ctrl+T", "Reopen Closed Tab": "Ctrl+Shift+T",
            "New Window": "Ctrl+N", "Close Window": "Ctrl+Shift+W"}
    for text, key in keys.items():
        h.check(f"{text} is {key}", file_action(w, text).shortcut().toString() == key,
                file_action(w, text).shortcut().toString())
    close_all()


if __name__ == "__main__":
    h.app()
    for test in (test_close_tab_shows_the_next_window, test_closing_the_last_tab_shows_a_blank_one,
                 test_new_tab_is_blank, test_reopen_closed_restores_the_setup, test_shortcuts,
                 test_tab_bar_names_each_trial, test_menus_follow_the_tab, test_tab_bar_close_and_step,
                 test_new_window_and_its_last_tab, test_same_video_in_two_tabs_at_once, test_file_menu_groups, test_closing_the_window_asks_per_tab):
        print(test.__name__)
        test()
    h.finish()
