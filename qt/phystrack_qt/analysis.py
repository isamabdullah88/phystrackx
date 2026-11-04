"""
Plot analysis for the Qt spike: a fit of a model (damped oscillator, or quadratic drag) to a
position against time, the period from the peaks, and the initial drop. The results are shown in a
panel beside the plot, with a range slider to choose the part of the data to fit. The model is
chosen in a Qt table beside the figure (fit_table.ModelTable: each model's equation, R² and period);
this panel reports the fits to it through `on_fits`, and is told the choice through `choose`.

Fast and smooth:
- The plot opens with the data alone (its place for the panel kept, so nothing moves later). The
  fit, the slider and the results come together in one redraw when the first fit is done.
- Fits run on a worker thread, so the plot and the main window stay usable, and a plot can be
  closed while it fits (that stops the fit). A new range or model abandons the fit under way.
- When the worker is free it fits the other models on the range shown too, and keeps every fit, so
  choosing another model (or going back to a range) shows its fit at once.

The numbers come from the parent's gui/components/plot/fit.py (numpy and scipy only). The layout
and the text follow the Tk plot (gui/components/plot/plot.py: _add_fit and _summary), so the two
apps report the same values. When either changes, change the other too.
"""

import queue
import threading
import time

import numpy as np
from matplotlib.widgets import RangeSlider

from .parent_imports import import_light

fitting = import_light("core.fit")

# Where the parts go (figure fractions): the plot, the slider under it, the results on the right
PLOT_BOX = dict(left=0.09, right=0.60, bottom=0.25, top=0.9)
PANEL_BOX = [0.63, 0.25, 0.36, 0.65]
SLIDER_BOX = [0.09, 0.08, 0.51, 0.03]
BACKGROUND_REST = 0.002   # s after each trial of a fit made ahead of being asked for


class Fitter:
    """
    Fits on a worker thread. `request(lo, hi, model)` asks for a fit of the data in [lo, hi]; the
    latest request is the one that counts (a fit under way for an older one stops at its next
    trial). `poll` (on the UI thread) returns the latest request's fit once it is done. Between
    requests the worker fits the other models on the latest range, in the background: those
    stop as soon as a request comes. Every finished fit is kept (`cached`). `close` ends it all.
    """

    def __init__(self, t, y, models: list) -> None:
        self.t, self.y = t, y
        self.models = models
        self._lock = threading.Condition()
        self._job = None            # (generation, lo, hi, model): the latest request, not yet started
        self._range = None          # (lo, hi) of the latest request: background fits use it
        self.generation = 0
        self.closed = False
        self._fits: dict = {}       # (model, lo, hi) -> FitResult
        self._warm: dict = {}       # model -> its latest good fit (a start for the next)
        self._done: queue.Queue = queue.Queue()
        self.background_fits = 0    # How many fits were made ahead of being asked for (tests)
        self._thread = threading.Thread(target=self._run, name="plot fit", daemon=True)
        self._thread.start()

    def data(self, lo: float, hi: float):
        mask = (self.t >= lo) & (self.t <= hi)
        return self.t[mask], self.y[mask]

    def cached(self, lo: float, hi: float, model: str):
        with self._lock:
            return self._fits.get((model, lo, hi))

    def request(self, lo: float, hi: float, model: str):
        """Asks for a fit. Returns it at once if it was already made (it is also not queued)."""
        with self._lock:
            self.generation += 1
            self._range = (lo, hi)
            fit = self._fits.get((model, lo, hi))
            self._job = None if fit is not None else (self.generation, lo, hi, model)
            self._lock.notify()
            return fit

    def poll(self):
        """The latest request's fit, once it is done (else None)."""
        latest = None
        while not self._done.empty():
            generation, fit = self._done.get_nowait()
            if generation == self.generation:
                latest = fit
        return latest

    def close(self) -> None:
        with self._lock:
            self.closed = True
            self._job = None
            self._lock.notify()

    def _next(self):
        """The next piece of work: the request, else a model not yet fitted on the latest range
        (in menu order), else None. Called holding the lock."""
        if self._job is not None:
            job, self._job = self._job, None
            return job, False
        if self._range is not None:
            lo, hi = self._range
            for model in self.models:
                if (model, lo, hi) not in self._fits:
                    return (self.generation, lo, hi, model), True
        return None, False

    def _run(self) -> None:
        while True:
            with self._lock:
                job, background = self._next()
                while job is None and not self.closed:
                    self._lock.wait()
                    job, background = self._next()
                if self.closed:
                    return
            generation, lo, hi, model = job
            if background:   # Low priority: gives way to any request, and rests after each trial
                def stop():      # so the window's thread gets Python whenever it wants it
                    time.sleep(BACKGROUND_REST)
                    return self.closed or self._job is not None or self.generation != generation
            else:
                def stop():
                    return self.closed or self.generation != generation
            tp, yp = self.data(lo, hi)
            try:
                fit = fitting.fit_model(tp, yp, model, warm=self._warm.get(model), stop=stop)
            except fitting.FitStopped:
                continue
            except Exception as e:   # A fit must never take the thread down: report it instead
                fit = fitting.FitResult(ok=False, model=model, message=f"The fit failed: {e}")
            with self._lock:
                self._fits[(model, lo, hi)] = fit
                if fit.ok:
                    self._warm[model] = fit
                self.background_fits += background
            if not background:
                self._done.put((generation, fit))


class FitPanel:
    """
    The fit panel of a plot of y against t (drawn on `ax`, with no legend of its own). At first
    only the plot's place is set (the data is shown alone) and the default model's fit starts on
    the worker. When it is done, the fit line, the slider, the results and the legend are added in
    one redraw. `results` is the results text (None until then); `close` stops the worker.
    `choose(key)` shows another model's fit; `on_fits(fits)` (if set) is told every model's fit on
    the range shown (key -> FitResult, or None while it is still to come) whenever that changes.
    """

    def __init__(self, figure, ax, t, y, unit: str) -> None:
        order = np.argsort(t)
        self.t, self.y = np.asarray(t, dtype=float)[order], np.asarray(y, dtype=float)[order]
        self.figure, self.ax, self.unit = figure, ax, unit
        self.keys = list(fitting.MODELS)
        self.model = fitting.DEFAULT_MODEL
        self.range = (float(self.t[0]), float(self.t[-1]))
        self.results = None
        self.slider = None
        self.on_fits = None
        self.on_change = None   # Told when the model or range changes (the window's history)
        self._reported = None   # The fits last told to on_fits
        figure.set_size_inches(12, 6)
        figure.subplots_adjust(**PLOT_BOX)   # The panel's place is kept from the start
        self.fitter = Fitter(self.t, self.y, self.keys)
        self.fitter.request(*self.range, self.model)
        self._timer = figure.canvas.new_timer(interval=30)   # Brings finished fits to the UI thread
        self._timer.add_callback(self._check)
        self._timer.start()

    @property
    def widgets(self) -> list:
        return [self.slider] if self.slider is not None else []

    def close(self) -> None:
        self._timer.stop()
        self.fitter.close()

    def fitting(self) -> bool:
        """Waiting for a fit (the first, or one asked for since)."""
        return self.results is None or self.results.get_text().startswith("Fitting:")

    def wait_for_fit(self, timeout: float) -> bool:
        """Lets the event loop run until the fit asked for is shown (at most `timeout` s). True if
        it is."""
        from PySide6.QtCore import QElapsedTimer, QEventLoop
        from PySide6.QtWidgets import QApplication
        clock = QElapsedTimer()
        clock.start()
        while self.fitting() and clock.elapsed() < timeout * 1000:
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
            self._check()
        return not self.fitting()

    def _build(self) -> None:
        """The fit line, the results panel with the legend, and the slider (not drawn)."""
        figure, ax = self.figure, self.ax
        self.fit_line, = ax.plot([], [], "-", color="k", linewidth=2, label="fit")
        self.drop_marks, = ax.plot([], [], "o", color="tab:red", markersize=8, label="initial drop")
        panel = figure.add_axes(PANEL_BOX)
        panel.axis("off")
        self.results = panel.text(0.0, 1.0, "", transform=panel.transAxes, va="top", ha="left",
                                  fontsize=10.5, family="monospace")
        handles, labels = ax.get_legend_handles_labels()
        legend = panel.legend(handles, labels, loc="lower left", fontsize=8, title="Legend")
        legend.set_draggable(True)

        slider_ax = figure.add_axes(SLIDER_BOX)
        self.slider = RangeSlider(slider_ax, "Range (s)", *self.range, valinit=self.range)
        self.slider.on_changed(self._changed)

    def choose(self, key: str) -> None:
        """Shows the model `key`'s fit (at once if it was made already)."""
        if key == self.model:
            return
        self.model = key
        self._changed()

    def set_range(self, lo: float, hi: float) -> None:
        """The fit range from code (a tool, a revert): moves the slider if it is shown yet."""
        lo, hi = max(lo, float(self.t[0])), min(hi, float(self.t[-1]))
        if hi - lo < 0.05 * (float(self.t[-1]) - float(self.t[0])):
            # Wholly outside the data, or too short to fit (e.g. a range copied from a longer
            # trial): the whole data instead, rather than an inverted or empty range
            lo, hi = float(self.t[0]), float(self.t[-1])
        if self.slider is not None:
            self.slider.set_val((lo, hi))   # Calls _changed
        else:
            self.range = (lo, hi)
            self._changed()

    def summary(self) -> dict:
        """The fit shown, compactly (for the history and the agent tools)."""
        out = {"model": self.model, "range": [round(v, 3) for v in self.range]}
        fit = self.fitter.cached(*self.range, self.model)
        if fit is not None and fit.ok:
            tp, yp = self.fitter.data(*self.range)
            period, perr, source = fitting.best_period(fit, fitting.peak_periods(tp, yp))
            drop = fitting.initial_drop(tp, yp)
            out.update(r2=round(fit.r2, 4), T=float(f"{period:.4g}"), dT=float(f"{perr:.2g}"))
            if drop.ok:
                out["drop"] = float(f"{drop.drop:.4g}")
        elif fit is not None:
            out["error"] = fit.message
        else:
            out["fitting"] = True
        return out

    def _changed(self, _=None) -> None:
        """A new range or model: its fit at once if it was made already, else asked for."""
        if self.slider is not None:
            self.range = tuple(float(v) for v in self.slider.val)
        fit = self.fitter.request(*self.range, self.model)
        if fit is not None:
            self._show(fit)
        elif self.results is not None:
            self.results.set_text(f"Fitting: {fitting.MODELS[self.model].label}...\n\n{self._shown}")
            self.figure.canvas.draw_idle()
        self._report()
        if self.on_change is not None:
            self.on_change()

    def _check(self) -> None:
        fit = self.fitter.poll()
        if fit is not None:
            self._show(fit)
        self._report()

    def _report(self) -> None:
        """Tells on_fits every model's fit on the range shown, when that changed."""
        if self.on_fits is None:
            return
        fits = {key: self.fitter.cached(*self.range, key) for key in self.keys}
        state = tuple(id(f) for f in fits.values())
        if state != self._reported:
            self._reported = state
            self.on_fits(fits)

    def _show(self, fit) -> None:
        if self.results is None:
            self._build()   # The first fit: everything appears with it
        tp, yp = self.fitter.data(*self.range)
        if fit.ok:
            names = fitting.MODELS[fit.model].names
            self.fit_line.set_data(tp, fitting.MODELS[fit.model].func(
                tp - fit.t0, *(fit.params[k] for k in names)))
        else:
            self.fit_line.set_data([], [])
        peaks = fitting.peak_periods(tp, yp)
        drop = fitting.initial_drop(tp, yp)
        if drop.ok:
            self.drop_marks.set_data([drop.t_high, drop.t_low], [drop.y_high, drop.y_low])
        else:
            self.drop_marks.set_data([], [])
        period, perr, source = fitting.best_period(fit, peaks)
        self._shown = summary_text(fit, peaks, period, perr, source, self.unit, drop)
        self.results.set_text(self._shown)
        self.figure.canvas.draw_idle()


def drop_low(t, y):
    """(size, time of the low, time of the high) of the initial drop of y(t) (first high to first
    low), or None. A copied fit range is kept from this drop (agent/tools.py,
    MainWindow._apply_plot_settings)."""
    d = fitting.initial_drop(np.asarray(t, dtype=float), np.asarray(y, dtype=float))
    return (abs(float(d.drop)), float(d.t_low), float(d.t_high)) if d.ok else None


def attach_fit(figure, ax, t, y, unit: str):
    """The fit panel for a plot of y against t (see FitPanel), or None if there is too little data
    to fit."""
    t = np.asarray(t, dtype=float)
    if len(t) < 2 or np.min(t) == np.max(t):
        return None
    return FitPanel(figure, ax, t, y, unit)


def summary_text(fit, peaks, period, perr, source, unit: str = "", drop=None) -> str:
    """The results panel's text: the fit's parameters, the period estimates, and the initial drop.
    Amplitude, offset and drop are in `unit`."""
    lines = []
    u = f" {unit}" if unit else ""
    if fit.ok:
        lines += [fitting.MODELS[fit.model].label] + fitting.param_lines(fit, unit) + [
            f"R²    = {fit.r2:.4f}",
            f"T fit = {fit.period:.4g} ± {fit.period_err:.2g} s",
        ]
        if fit.message:
            lines.append(fit.message)
    else:
        lines.append(fit.message)
    if peaks.period == peaks.period:  # Not NaN
        lines.append(f"T peaks = {peaks.period:.4g} ± {peaks.period_err:.2g} s "
                     f"({peaks.n_maxima} max, {peaks.n_minima} min)")
    if source is not None:
        lines.append(f"Best T = {period:.4g} ± {perr:.2g} s  [{source}]")
    if drop is not None:
        if drop.ok:
            lines.append(f"Initial drop = {drop.drop:.4g}{u} in {drop.duration:.4g} s")
            lines.append(f"  (high at {drop.t_high:.3g} s, low at {drop.t_low:.3g} s)")
        else:
            lines.append(f"Initial drop: {drop.message}")
    return "\n".join(lines)
