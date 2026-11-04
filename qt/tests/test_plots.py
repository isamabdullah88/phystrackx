"""
Plots: the windows, their data, their units, and the fit panel on position against time. Synthetic
motion with known answers, so the plots can be checked against the physics.

    ~/.venvs/phystrackx-qt/bin/python tests/test_plots.py
"""

import math

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

import numpy as np  # noqa: E402

from PySide6.QtWidgets import QLabel  # noqa: E402

from phystrack_qt.analysis import fitting  # noqa: E402
from phystrack_qt.plot_window import open_plots  # noqa: E402


def fitting_label(key: str) -> str:
    return fitting.MODELS[key].label


def _texts(window) -> str:
    return " ".join(t.get_text() for ax in window.figure.axes for t in ax.texts)


def _fitted(window, timeout: float = 30) -> bool:
    """Waits for the window's fit (it runs on a worker thread) to be shown."""
    return h.pump(lambda: window.results is not None and "R²" in window.results.get_text()
                  and "Fitting:" not in window.results.get_text(), timeout)


def _line_y(window):
    """The y data of the first plotted series (the data points)."""
    return np.asarray(window.figure.axes[0].lines[0].get_ydata(), dtype=float)


def test_plots() -> None:
    t = np.linspace(0, 3, 301)
    # Oscillations in both (the fit is quick on these). Non-oscillating data is very slow to fit
    # with the oscillator models; see TODO.md
    w_x = 2 * math.pi * 1.2
    x = 2.0 * np.cos(w_x * t) + 0.5 * t
    y = 5.0 + 3.0 * np.exp(-0.2 * t) * np.cos(2 * math.pi * 1.5 * t)
    xy = np.column_stack([x, y])
    windows = open_plots(7, t, xy, "cm", ["x", "xy", "dx", "d2x", "y"])
    kinds = {w.windowTitle(): w for w in windows}
    h.check("one window per chosen plot, titled with the object",
            len(windows) == 5 and all(w.windowTitle().startswith("[O-7]") for w in windows),
            ", ".join(w.windowTitle() for w in windows))

    xwin = windows[0]
    h.check("x against time has the fit panel", xwin.fit_panel is not None)
    _fitted(xwin)
    h.check("...with its slider once the fit is in", len(xwin.fit_panel.widgets) == 1)
    h.check("x's fit panel reports the oscillation's fit",
            "omega" in _texts(xwin) and "R²" in _texts(xwin))
    h.check("the x-axis label carries the unit",
            "(cm)" in xwin.figure.axes[0].get_ylabel(), xwin.figure.axes[0].get_ylabel())
    h.check("x against time is the data it was given",
            np.allclose(_line_y(xwin), x), "")

    traj = windows[1]
    h.check("the trajectory has no fit panel", traj.fit_panel is None)

    dx = windows[2]
    interior = slice(2, -2)
    v_true = -2.0 * w_x * np.sin(w_x * t) + 0.5
    h.check("velocity dx/dt matches the derivative (interior)",
            np.allclose(_line_y(dx)[interior], v_true[interior], atol=0.02),
            f"max error {np.max(np.abs(_line_y(dx)[interior] - v_true[interior])):.2g}")

    d2x = windows[3]
    a_true = -2.0 * w_x * w_x * np.cos(w_x * t)
    h.check("acceleration d²x/dt² matches the second derivative (interior)",
            np.allclose(_line_y(d2x)[interior], a_true[interior], atol=0.3),
            f"max error {np.max(np.abs(_line_y(d2x)[interior] - a_true[interior])):.2g}")

    ywin = windows[4]
    h.check("y against time fits the oscillation",
            abs(np.max(_line_y(ywin)) - np.max(y)) < 1e-9)
    _fitted(ywin)
    h.check("the fit panel reports the oscillation's fit",
            "omega" in _texts(ywin) and "R²" in _texts(ywin), _texts(ywin)[:80])

    for window in windows:
        window.close()


def test_plots_without_units() -> None:
    t = np.linspace(0, 1, 50)
    windows = open_plots(1, t, np.column_stack([t, t]), "px", ["r"])
    h.check("with no ruler, the unit is pixels", "(px)" in windows[0].figure.axes[0].get_ylabel(),
            windows[0].figure.axes[0].get_ylabel())
    for window in windows:
        window.close()


def test_model_table() -> None:
    """The models are a table beside the plot: a large row each, with its equation, R² and period;
    a click or Up / Down shows another model's fit."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    t, r = _real_like()
    window = open_plots(1, t, np.column_stack([r, np.zeros_like(r)]), "cm", ["x"])[0]
    table = window.model_table
    panel = window.fit_panel
    rows = table.table.rowCount()
    h.check("the table lists every model, the 4 new ones too", rows == 8 and
            {"damped_exp", "both_exp", "gas", "friction"} <= set(table.keys), str(table.keys))
    cells = [table.table.cellWidget(row, 0).findChildren(QLabel)[0].text() for row in range(rows)]
    h.check("each row shows its name and its equation",
            "Damped + linear drift" in cells[1] and "Damped + linear drift" in cells[1], cells[1])
    h.check("the rows are large (easy to click)",
            min(table.table.rowHeight(row) for row in range(rows)) >= 44,
            str([table.table.rowHeight(row) for row in range(rows)]))
    h.check("the default model is selected", table.current == panel.model == "damped_linear")
    h.check("R² and the period fill in as the fits come in",
            h.pump(lambda: all(table.table.item(row, 1).text() not in ("…", "failed")
                               for row in range(rows)), 90),   # slow CI runners
            str([table.table.item(row, 1).text() for row in range(rows)]))
    h.check("the period column is titled Period (s) and shows its error",
            table.table.horizontalHeaderItem(2).text() == "Period (s)"
            and "±" in table.table.item(table.keys.index("damped_linear"), 2).text(),
            table.table.item(table.keys.index("damped_linear"), 2).text())
    h.check("each equation is a LaTeX picture (not text)",
            all(table.table.cellWidget(row, 0).findChildren(QLabel)[-1].pixmap() is not None
                and not table.table.cellWidget(row, 0).findChildren(QLabel)[-1].pixmap().isNull()
                for row in range(rows)))
    r2 = [float(text) if (text := table.table.item(row, 1).text()) not in ("…", "failed") else 0.0
          for row in range(rows)]   # A fit still running is reported above, not parsed
    bold = [row for row in range(rows) if table.table.item(row, 1).font().bold()]
    h.check("the best R² is in bold (one row)", len(bold) == 1 and r2[bold[0]] == max(r2), f"{bold} {r2}")

    QTest.keyClick(window, Qt.Key.Key_Down)
    h.check("Down shows the next model's fit at once", panel.model == "damped_exp"
            and "Damped + exponential settling" in window.results.get_text()
            and "ts    =" in window.results.get_text(), window.results.get_text()[:80])
    QTest.keyClick(window, Qt.Key.Key_Up)
    QTest.keyClick(window, Qt.Key.Key_Up)
    h.check("Up goes back up", panel.model == "damped")
    QTest.keyClick(window, Qt.Key.Key_Up)
    h.check("...and stops at the top", panel.model == "damped")
    row = table.keys.index("gas")
    QTest.mouseClick(table.table.viewport(), Qt.MouseButton.LeftButton,
                     pos=table.table.visualRect(table.table.model().index(row, 0)).center())
    h.check("a click on a row shows that model", panel.model == "gas"
            and "L     =" in window.results.get_text(), window.results.get_text()[:80])
    window.close()


def _real_like():
    """Data like Air Trial 4's distance (a big first swing, smaller ones about a falling line):
    the quadratic drag fit took 87 s on it, all on the window's thread."""
    t = np.arange(10.59, 30.69, 1 / 30)
    tt = t - t[0]
    r = 20 - 0.5 * tt + 55 * np.exp(-0.5 * tt) * np.cos(1.34 * tt)
    return t, r + np.random.default_rng(0).normal(0, 0.3, t.size)


def test_drag_fit_keeps_the_app_usable() -> None:
    from PySide6.QtCore import QElapsedTimer, QTimer
    t, r = _real_like()
    window = open_plots(1, t, np.column_stack([r, np.zeros_like(r)]), "cm", ["x"])[0]
    _fitted(window)
    panel = window.fit_panel
    panel.fitter.close()   # No fits made ahead here: this checks a fit made on request
    panel.fitter = type(panel.fitter)(panel.t, panel.y, [])
    rows = window.model_table.table

    # The event loop keeps turning while the drag fit runs: the longest gap between ticks
    gaps, clock = [], QElapsedTimer()
    clock.start()
    ticker = QTimer()
    ticker.timeout.connect(lambda: (gaps.append(clock.restart())))
    ticker.start(10)
    started = QElapsedTimer()
    started.start()
    rows.selectRow(panel.keys.index("drag"))
    h.check("choosing the drag model returns at once", started.elapsed() < 300, f"{started.elapsed()} ms")
    h.check("...and says it is fitting", "Fitting: Quadratic drag" in window.results.get_text())
    h.check("the drag fit is done within seconds", _fitted(window, 20), window.results.get_text()[-200:])
    ticker.stop()
    # (One redraw of the whole figure, about 0.1-0.25 s, is matplotlib's own; the fit took 87 s here)
    h.check("the window kept responding while it fitted", max(gaps) < 400, f"longest gap {max(gaps)} ms")
    results = window.results.get_text()
    h.check("the drag fit's results are shown", "k     =" in results and "gamma" not in results, results[:120])

    # Closing the window during a fit stops the fit
    rows.selectRow(panel.keys.index("both_exp"))
    fitter = panel.fitter
    window.close()
    h.check("closing the window during a fit stops the worker",
            h.pump(lambda: not fitter._thread.is_alive(), 5))


def test_data_first_then_fits_made_ahead() -> None:
    """The data shows at once; the fit panel comes whole with the first fit; the other models are
    fitted in the background, so choosing one shows its fit at once."""
    from PySide6.QtCore import QElapsedTimer
    t, r = _real_like()
    clock = QElapsedTimer()
    clock.start()
    window = open_plots(1, t, np.column_stack([r, np.zeros_like(r)]), "cm", ["x"])[0]
    window.canvas.draw()
    h.check("the data is drawn at once", clock.elapsed() < 500, f"{clock.elapsed()} ms")
    h.check("...alone, the panel's place kept",
            window.results is None and len(window.figure.axes) == 1
            and abs(window.figure.axes[0].get_position().x0 - 0.09) < 1e-6)
    h.check("the fit comes soon after", _fitted(window, 10), f"{clock.elapsed()} ms")
    h.check("...with the slider and the results together",
            len(window.fit_panel.widgets) == 1 and len(window.figure.axes) == 3)
    panel = window.fit_panel
    lo, hi = panel.range
    h.check("the other models are fitted in the background",
            h.pump(lambda: all(panel.fitter.cached(lo, hi, k) for k in panel.keys), 90),   # slow CI runners
            str(panel.fitter.background_fits))
    for index, key in enumerate(panel.keys):
        window.model_table.table.selectRow(index)
        text = window.results.get_text()
        h.check(f"choosing {key} shows its fit at once", "Fitting" not in text and "R²" in text
                and fitting_label(key) in text, text[:60])
    window.close()


def test_a_copied_fit_range_is_put_on_the_open_plots_drop() -> None:
    """A fit range copied from another trial ("from_low", counted from the end of that trial's initial drop) is put on
    this trial's own drop once its plot is open. With no plot open it waits (and loads nothing to look for one:
    opening a project must not load the plot libraries, test_startup.py)."""
    t = np.linspace(0, 6, 301)
    r = 30 + 25 * np.exp(-0.3 * t) * np.cos(2 * math.pi * t / 3)   # High at the start, its first low at 1.43 s
    w = h.window()
    window = open_plots(1, t, np.column_stack([r, np.zeros_like(r)]), "cm", ["r"])[0]
    _fitted(window)
    w._plot_windows.append(window)
    model = window.fit_panel.model
    w.plots = {"kinds": ["r"], "fits": {"r": {"model": model, "from_low": [0.0, 2.0]}}}
    w._apply_plot_settings()
    fit = w.plots["fits"]["r"]
    low = 1.432
    h.check("the copied range is resolved: it counts from the plot's own low",
            "from_low" not in fit and abs(fit["range"][0] - low) < 0.05 and abs(fit["range"][1] - (low + 2.0)) < 0.05,
            str(fit))
    h.check("...and the plot's fit range follows it",
            abs(window.fit_panel.range[0] - fit["range"][0]) < 1e-6 and abs(window.fit_panel.range[1] - fit["range"][1]) < 1e-6,
            str(window.fit_panel.range))

    waiting = h.window()
    waiting.plots = {"fits": {"r": {"model": model, "from_low": [0.0, 2.0]}}}
    waiting._apply_plot_settings()
    h.check("with no plot open, the copied range waits for one", waiting.plots["fits"]["r"].get("from_low") == [0.0, 2.0],
            str(waiting.plots))
    window.close()
    for main in (w, waiting):
        main._dirty = False
        main.close()


if __name__ == "__main__":
    h.app()
    for test in (test_plots, test_plots_without_units, test_model_table,
                 test_drag_fit_keeps_the_app_usable, test_data_first_then_fits_made_ahead,
                 test_a_copied_fit_range_is_put_on_the_open_plots_drop):
        print(test.__name__)
        test()
    h.finish()
