"""
The Qt app's start: the main window on the given videos and projects, and the agent bridge.
Imported by cli.py only after the arguments are checked, so a bad command fails without loading Qt.
"""

import logging
import os
import signal
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from phystrack_qt import paths, plot_warmup, recent, session, windows
from phystrack_qt.agent import session as agent_session
from phystrack_qt.version import __version__

OPEN_AFTER_MS = 250   # The pause between bringing the window forward and opening the first trial: the window's
#                       first paint takes about 200 ms of it, the rest is idle time, in which macOS updates the menu bar
#                       (with 100 ms there was none, and the bar stayed the previous app's until all trials were open)
OPEN_GAP_MS = 20      # The pause between one trial and the next: the loop idles, so macOS's events get handled
#                       (a zero delay is only a posted event, which can run again before they are)


def stop_on_ctrl_c(app: QApplication) -> QTimer:
    """Ctrl-C quits the app. Qt's event loop runs in C++, where Python's own Ctrl-C handler never
    gets a turn, and an exception raised inside a Qt callback is printed and dropped; so the
    handler asks the loop to quit, and a short timer keeps Python running often enough to see the
    signal. (As the Tk app does.) Returns the timer, which must be kept alive."""
    # A quit called before the loop runs is lost, so the request is posted to the loop instead (a
    # Ctrl-C while the window is still being built then quits as soon as the loop starts)
    signal.signal(signal.SIGINT, lambda signum, frame: QTimer.singleShot(0, app.quit))
    wake = QTimer()
    wake.timeout.connect(lambda: None)
    wake.start(200)
    return wake


def startup_files(files: list[str]) -> list[str]:
    """What to open at start. Files given: those. None given: the windows that were open when the app was
    last closed (session.py), or, on a first start with no record, the most recent project."""
    if files:
        return files
    restored = session.restorable()
    if restored is None:
        return recent.load()[:1]
    return restored


def run(files: list[str]) -> None:
    """Opens the app. The first file opens in the first tab; each further one in a tab of its own.
    Each file is a video (opened from its first frame) or a .phystrack project. With no files, the
    last session's windows open again (startup_files)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("PhysTrackX")
    app.setApplicationDisplayName("PhysTrackX")
    app.setApplicationVersion(__version__)
    from phystrack_qt import settings_dialog
    settings_dialog.name_settings_item(app)   # "Settings…" in the app menu, as macOS names it now

    wake = stop_on_ctrl_c(app)   # noqa: F841  (kept alive for the run)
    # The first trial, in a tab of the first window
    window = windows.new_window(cache_dir=os.environ.get("PHYSTRACK_QT_CACHE") or paths.cache_dir())
    # Nothing else runs before the event loop: until it runs the window is not painted, and macOS does not
    # bring the app forward. The window is brought forward on its first turn; the trials, the bridge and the
    # assistant follow (start_at_launch, open_trials).
    QTimer.singleShot(0, lambda: start_at_launch(app, window, files))
    sys.exit(app.exec())


def warm_launch() -> None:
    """The install's hidden launch (build.py warm_launch). The first time macOS opens a new app, it checks
    each program and library as it loads (XProtect, syspolicyd): about 5 s for this app, before its window
    shows. Loading them all here, with no window and nothing saved, moves that wait into the install.
    Loads what a start loads (Qt, the main window and its modules), what the plots load, and ffmpeg."""
    import subprocess
    import tempfile

    from core import find_ffmpeg
    from phystrack_qt import plot_warmup

    os.environ["QT_QPA_PLATFORM"] = "offscreen"   # Nothing is shown
    with tempfile.TemporaryDirectory() as home:
        os.environ["PHYSTRACK_QT_HOME"] = home     # Nothing goes to the user's cache, recent list or session
        app = QApplication(sys.argv)   # noqa: F841  (the main window needs one)
        windows.new_window(show=False, cache_dir=paths.cache_dir())   # The tab window and a trial in it
        plot_warmup.warm_now()
        try:
            subprocess.run([find_ffmpeg(), "-version"], capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            pass


def start_at_launch(app: QApplication, window, files: list[str]) -> None:
    """On the event loop's first turn: brings the window to the front, and schedules the opening of the trials
    (open_trials) after a short pause. Opening a trial takes about a quarter of a second on this thread
    (more for a long video or a slow disk), and the event loop does not turn meanwhile: the window cannot
    paint, and macOS cannot finish bringing the app forward, so its menu bar stays the previous app's until
    the opening is over (it did, for up to 17 s, when a trial's opening also loaded matplotlib and scipy). The loop
    gets a pause first, and a turn between the trials. The session record is held until the last trial is
    open, so a quit part-way does not shrink it; and so is the plots' warm-up thread, which would take the
    interpreter's lock from the trials (plot_warmup.py)."""
    windows.focus(window)
    session.hold()
    plot_warmup.hold()
    QTimer.singleShot(OPEN_AFTER_MS, lambda: open_trials(app, window, startup_files(files), 0))


def open_trials(app: QApplication, window, trials: list[str], k: int) -> None:
    """Opens trial k of `trials` (the first in `window`, each further one in a tab of its own), and schedules
    the next after a short pause, even if this one failed (Qt prints the failure). After the last: the
    session record is released, and the agent tools and the assistant start. Stops the assistant's model
    runner when the app quits (not when a window closes).

    QUICK-AND-DIRTY: a trial still opens on this thread, so the window is frozen while it does: about 0.25 s
    each on the Intel MacBook Pro (the source opened and its first frame read, the proxy opened, the saved
    frame shown; the proxy, when there is none yet, is made in a thread already). The robust version reads
    the video on a worker thread and hands the frames to the window, which then never freezes."""
    if k < len(trials):
        try:
            target = window if k == 0 else windows.new_window()
            if trials[k].endswith(".phystrack"):
                target.open_project_file(trials[k])
            else:
                target.load_video(trials[k])
        finally:
            QTimer.singleShot(OPEN_GAP_MS, lambda: open_trials(app, window, trials, k + 1))
        return
    session.release()
    plot_warmup.release()
    # The agent tools, for the MCP shim and ptx.py (docs/AGENT_PLAN.md); PHYSTRACK_BRIDGE=0 turns off
    if os.environ.get("PHYSTRACK_BRIDGE", "1") != "0":
        from phystrack_qt.agent import bridge
        bridge.start()
    assistant = agent_session.shared()
    app.aboutToQuit.connect(assistant.shutdown)
    assistant.warm_up()
