"""
Gets the plots ready before the first one is asked for. The first plot used to wait about 2.5 s:
1.9 s importing matplotlib and scipy, and half a second for matplotlib's first font lookups and its
first equation (mathtext) layout. Here a background thread does all of that a little after the main
window opens: the imports, one tiny fit, and one off-screen drawing with the plot's fonts and an
equation, so the caches are filled.

Only thread-safe work is done here: plain imports and an off-screen (Agg) figure, never a Qt widget.
The Qt side of matplotlib (backend_qtagg) is imported on the UI thread when a plot opens; that part
is quick.

The warm-up is seconds of Python, and Python runs one thread at a time: beside it, the UI thread gets
about half the turns. At the app's start the restored trials are opened on the UI thread, and took
0.85 s instead of 0.5 s with the warm-up running; so the start holds it until the last trial is open.
"""

import threading

_started = False
_held = False     # start() is kept from starting the warm-up until release()
_wanted = False   # start() was called while it was held


def hold() -> None:
    """Keeps the warm-up from starting until release() (start() then only notes that it was called)."""
    global _held
    _held = True


def release() -> None:
    """Lets the warm-up start: at once, if start() was called while it was held."""
    global _held, _wanted
    _held = False
    if _wanted:
        _wanted = False
        start()


def start() -> None:
    """Starts the warm-up once (later calls do nothing), unless it is held."""
    global _started, _wanted
    if _started:
        return
    if _held:
        _wanted = True
        return
    _started = True
    # Not a daemon: a daemon still importing when the app exits can abort the process as the interpreter
    # shuts down (seen on Linux). Quitting within a few seconds of starting then waits for the imports.
    threading.Thread(target=_warm, name="plot warm-up", daemon=False).start()


def warm_now() -> None:
    """The warm-up on this thread, at once (the install's warm launch, app.warm_launch)."""
    _warm()


def _warm() -> None:
    try:
        import numpy as np
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        from .equations import equation_png
        from .parent_imports import import_light
        fitting = import_light("core.fit")
        import matplotlib.widgets  # noqa: F401  (the fit panel's slider and menu)

        t = np.arange(120) / 30
        fitting.fit_model(t, np.cos(3 * t) * np.exp(-0.2 * t), fitting.DEFAULT_MODEL)

        figure = Figure(figsize=(4, 3))
        FigureCanvasAgg(figure)
        ax = figure.add_subplot(111)
        ax.plot(t, t, ".")
        ax.set_title("[O-1] warm-up")
        ax.set_xlabel("$T(s)$")
        ax.set_ylabel("$r$ (cm)")
        figure.text(0, 0, "A     = 1.0 ± 0.1 cm", family="monospace", fontsize=8)
        figure.canvas.draw()
        # The fit table's equations, as pictures (the table only loads them)
        for model in fitting.MODELS.values():
            for line in model.equation:
                equation_png(line)
        equation_png(fitting.EQUATION_NOTE)
    except Exception:   # Only a head start: the plot does all of this itself if it must
        pass
