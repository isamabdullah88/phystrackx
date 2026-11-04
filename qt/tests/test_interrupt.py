"""
Ctrl-C quits the app, even with a plot open (its fit timer keeps Python waking up). Qt's loop runs in
C++, where Python's own Ctrl-C handler never gets a turn, so run.py asks the loop to quit instead.

    ~/.venvs/phystrackx-qt/bin/python tests/test_interrupt.py
"""

import os
import signal
import sys
import time

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

import numpy as np  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402

from phystrack_qt import app as run  # noqa: E402  (the Ctrl-C wiring lives in phystrack_qt/app.py)
from phystrack_qt.plot_window import open_plots  # noqa: E402


def test_ctrl_c_stops_the_app_with_a_plot_open() -> None:
    app = h.app()
    t = np.arange(600) / 30
    window = open_plots(1, t, np.column_stack([np.cos(2 * t), t]), "cm", ["x"])[0]
    wake = run.stop_on_ctrl_c(app)
    started = time.time()
    QTimer.singleShot(300, lambda: os.kill(os.getpid(), signal.SIGINT))   # The user presses Ctrl-C
    failsafe = QTimer()   # If Ctrl-C did nothing, the loop would still be running: stop it at 10 s
    failsafe.setSingleShot(True)
    failsafe.timeout.connect(app.quit)
    failsafe.start(10000)
    app.exec()
    took = time.time() - started
    failsafe.stop()
    h.check("Ctrl-C returns from the event loop at once", took < 5, f"{took:.2f} s")
    signal.signal(signal.SIGINT, signal.default_int_handler)
    window.close()
    del wake


def test_ctrl_c_during_setup_quits_when_the_loop_starts() -> None:
    """Ctrl-C while the window is still being built (before the loop runs): the quit is posted, so
    the loop returns at once when it starts. (A plain app.quit() here was lost, and the app ran on.)"""
    app = h.app()
    wake = run.stop_on_ctrl_c(app)
    os.kill(os.getpid(), signal.SIGINT)   # Before exec: the user pressed Ctrl-C during start-up
    failsafe = QTimer()
    failsafe.setSingleShot(True)
    failsafe.timeout.connect(app.quit)
    failsafe.start(10000)
    started = time.time()
    app.exec()
    took = time.time() - started
    failsafe.stop()
    h.check("Ctrl-C during start-up quits once the loop starts", took < 5, f"{took:.2f} s")
    signal.signal(signal.SIGINT, signal.default_int_handler)
    del wake


if __name__ == "__main__":
    if os.name == "nt":   # On Windows os.kill(pid, SIGINT) ends the process rather than sending Ctrl-C
        print("skipped: os.kill cannot send Ctrl-C on Windows")
        sys.exit(0)
    h.app()
    for test in (test_ctrl_c_stops_the_app_with_a_plot_open,
                 test_ctrl_c_during_setup_quits_when_the_loop_starts):
        print(test.__name__)
        test()
    h.finish()
