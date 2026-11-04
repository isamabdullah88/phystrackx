"""Damped oscillator fit, period checker, and the range slider on the plots (no window needed).

Synthetic data with known parameters: the fit must recover them, the peak spacing must agree
with the fit period, and a range that only covers part of the data must use only that part.
"""

import math

import numpy as np

from tests import harness as h
h.setup_env()

import matplotlib  # noqa: E402
matplotlib.use("Agg")  # The plots are drawn to nothing: no windows open

from core.fit import (best_period, damped, fit_damped,  # noqa: E402
                                     peak_periods)

A, GAMMA, OMEGA, PHI, C = 80.0, 0.15, 1.2, 0.7, 120.0
PERIOD = 2 * math.pi / OMEGA


def _series(noise=0.0, n=900, dt=1 / 30):
    t = np.arange(n) * dt
    rng = np.random.default_rng(1)
    y = damped(t, A, GAMMA, OMEGA, PHI, C) + rng.normal(0, noise, n)
    return t, y


def test_fit_recovers_the_parameters():
    t, y = _series(noise=0.5)
    fit = fit_damped(t, y)
    h.check("fit converges", fit.ok, fit.message)
    h.check("fit R² is high", fit.r2 > 0.99, f"R² {fit.r2:.4f}")
    h.check("omega is recovered within 1%", abs(fit.params["omega"] - OMEGA) / OMEGA < 0.01,
            f"{fit.params['omega']:.4f}")
    h.check("gamma is recovered within 5%", abs(fit.params["gamma"] - GAMMA) / GAMMA < 0.05,
            f"{fit.params['gamma']:.4f}")
    h.check("offset C is recovered", abs(fit.params["C"] - C) < 0.5, f"{fit.params['C']:.3f}")
    h.check("period from the fit", abs(fit.period - PERIOD) < 0.02 * PERIOD,
            f"{fit.period:.4f} vs {PERIOD:.4f}")
    h.check("period has an error estimate", math.isfinite(fit.period_err) and fit.period_err > 0)
    h.check("decay time is 1/gamma", abs(fit.tau - 1 / GAMMA) < 0.5, f"{fit.tau:.3f}")
    h.check("amplitude is reported positive", fit.params["A"] > 0, f"{fit.params['A']:.3f}")


def test_peak_spacing_agrees_with_the_fit():
    t, y = _series(noise=0.5)
    peaks = peak_periods(t, y)
    h.check("peaks are found", peaks.n_maxima >= 2 and peaks.n_minima >= 2,
            f"{peaks.n_maxima} max, {peaks.n_minima} min")
    h.check("peak period matches the true period", abs(peaks.period - PERIOD) < 0.05 * PERIOD,
            f"{peaks.period:.4f} vs {PERIOD:.4f}")


def test_best_period_prefers_a_good_fit():
    t, y = _series(noise=0.5)
    fit, peaks = fit_damped(t, y), peak_periods(t, y)
    period, _, source = best_period(fit, peaks)
    h.check("good fit is the reported period", source == "fit" and abs(period - fit.period) < 1e-12,
            str(source))


def test_best_period_falls_back_to_peaks_for_a_poor_fit():
    rng = np.random.default_rng(2)
    t = np.arange(600) / 30
    y = damped(t, A, GAMMA, OMEGA, PHI, C) + rng.normal(0, 60, t.size)  # Mostly noise
    fit, peaks = fit_damped(t, y), peak_periods(t, y)
    _, _, source = best_period(fit, peaks)
    h.check("poor fit does not claim the period", source in ("peaks", None) or fit.r2 >= 0.9,
            f"source {source}, R² {fit.r2:.3f}")


def test_range_uses_only_the_selected_part():
    """Two parts with different frequencies: a range on each must find its own frequency."""
    dt = 1 / 30
    t1 = np.arange(0, 20, dt)
    t2 = np.arange(20, 40, dt)
    y1 = damped(t1, 50, 0.01, 1.0, 0.0, 100)
    y2 = damped(t2, 50, 0.01, 2.0, 0.0, 100)
    t = np.concatenate([t1, t2])
    y = np.concatenate([y1, y2])
    early = fit_damped(t[t < 20], y[t < 20])
    late = fit_damped(t[t >= 20], y[t >= 20])
    h.check("early range finds its own omega", abs(early.params["omega"] - 1.0) < 0.02,
            f"{early.params['omega']:.4f}")
    h.check("late range finds its own omega", abs(late.params["omega"] - 2.0) < 0.02,
            f"{late.params['omega']:.4f}")


def test_warm_start_gives_the_same_fit():
    """A fit started from a nearby range's result must match a cold fit (it is only faster)."""
    t, y = _series(noise=0.5)
    first = fit_damped(t[t <= 25], y[t <= 25])
    m = (t >= 1.5) & (t <= 24)
    warm = fit_damped(t[m], y[m], warm=first)
    cold = fit_damped(t[m], y[m])
    h.check("warm and cold fits agree on the period",
            abs(warm.period - cold.period) < 1e-3 * cold.period,
            f"{warm.period:.5f} vs {cold.period:.5f}")


def test_distance_r_is_csv_column_and_plot():
    """r = sqrt(x^2 + y^2) from the axes origin: a CSV column and a plot with the fit (headless)."""
    import matplotlib.pyplot as plt
    from gui.components.plot.plot import Plot
    from gui.components.plot.save import Save
    from gui.components.plot.savetype import SaveType

    t = np.arange(900) / 30
    r_true = damped(t, A, GAMMA, OMEGA, PHI, C)  # Distance oscillates about a centre C
    theta = 0.4
    x, y = r_true * np.cos(theta), r_true * np.sin(theta)

    class _Data:
        datacount = 1
        maxcount = t.size
        ocrcount = 0
        timestamps = t
        processed_points = [np.column_stack([x, y])]

    save = Save.__new__(Save)
    save.datamanager = _Data()
    header = save.prepheader([SaveType.XY.name, SaveType.HEADER.name])
    h.check("CSV header has r next to x and y", header == ["x1", "y1", "r1"], str(header))

    plot = Plot.__new__(Plot)
    plot.datamanager = _Data()
    plot._widgets = []
    plot.plotr()
    ax = plt.gcf().axes[0]
    texts = [tx.get_text() for a in plt.gcf().axes for tx in a.texts]
    h.check("r plot shows the fitted period", any("T fit" in tx and f"{PERIOD:.2f}"[:3] in tx
                                                  for tx in texts), str(texts[:1]))
    plt.close("all")


def test_linear_drift_model_recovers_the_slope():
    """Oscillation settling onto a sloped line: the drift model finds the slope and fits better."""
    from core.fit import fit_model
    t, y = _series(noise=0.5)
    slope = 0.4
    y = y + slope * t
    lin = fit_model(t, y, "damped_linear")
    plain = fit_model(t, y, "damped")
    h.check("drift model converges", lin.ok, lin.message)
    h.check("slope is recovered", abs(lin.params["m"] - slope) < 0.02, f"{lin.params['m']:.4f}")
    h.check("omega is recovered with the drift", abs(lin.params["omega"] - OMEGA) / OMEGA < 0.02,
            f"{lin.params['omega']:.4f}")
    h.check("drift model fits better than the plain one", lin.r2 > plain.r2,
            f"{lin.r2:.4f} vs {plain.r2:.4f}")


def test_plot_fit_type_switch():
    """The fit-type buttons on the plot switch between the plain and the drift model."""
    import matplotlib.pyplot as plt
    from gui.components.plot.plot import Plot
    from core.fit import MODELS

    t, y = _series(noise=0.5, n=600)
    y = y + 0.3 * t

    class _Data:
        pass

    data = _Data()
    data.processed_points = [np.column_stack([np.zeros_like(y), y])]
    data.timestamps = t
    plot = Plot.__new__(Plot)
    plot.datamanager = data
    plot._widgets = []
    plot.ploty()
    radio = plot._widgets[-1]
    ax = plt.gcf().axes[0]
    text = lambda: "\n".join(tx.get_text() for a in plt.gcf().axes for tx in a.texts)  # noqa: E731
    h.check("drift model is the default", "m     =" in text(), text()[:80])
    keys = list(MODELS)
    radio.set_active(keys.index("damped"))
    h.check("plain model drops the drift line", "m     =" not in text(), text()[:80])
    plt.close("all")


def test_too_few_points_is_refused():
    fit = fit_damped([0, 1, 2], [1, 2, 3])
    h.check("fit refuses a tiny range", not fit.ok and "at least" in fit.message, fit.message)


def test_plot_slider_updates_the_fit():
    """The plot's range slider recomputes the fit for the chosen range (headless)."""
    import matplotlib.pyplot as plt
    from gui.components.plot.plot import Plot

    class _Data:
        pass

    t, y = _series(noise=0.5, n=600)
    data = _Data()
    data.processed_points = [np.column_stack([np.zeros_like(y), y])]
    data.timestamps = t
    plot = Plot.__new__(Plot)  # Skip the GUI parent: the test only drives the plot code
    plot.datamanager = data
    plot._widgets = []
    plot.checkbox = None
    plot.ploty()
    from matplotlib.widgets import RangeSlider
    slider = [w for w in plot._widgets if isinstance(w, RangeSlider)][-1]
    slider.set_val((float(t[0]), float(t[-1]) / 2))  # Only the first half
    texts = [tx.get_text() for a in plt.gcf().axes for tx in a.texts]
    h.check("slider shows a summary", any("T fit" in tx for tx in texts))
    h.check("summary reports the fitted period", any(f"{PERIOD:.2f}"[:3] in tx for tx in texts),
            str(texts[:1]))
    plt.close("all")


def test_quadratic_drag_recovers_the_parameters():
    """Data from the quadratic-drag equation: the drag model must recover omega and the drag k."""
    import time
    from core.fit import drag, fit_model
    t = np.arange(900) / 30
    y = drag(t, 60.0, 0.0, 1.2, 0.02, 120.0)
    y = y + np.random.default_rng(3).normal(0, 0.3, t.size)
    start = time.time()
    fit = fit_model(t, y, "drag")
    took = time.time() - start
    h.check("drag fit converges", fit.ok, fit.message)
    h.check("drag fit R² is high", fit.r2 > 0.98, f"R² {fit.r2:.4f}")
    h.check("drag omega is recovered within 2%",
            abs(fit.params["omega"] - 1.2) / 1.2 < 0.02, f"{fit.params['omega']:.4f}")
    h.check("drag strength k is recovered within 25%",
            abs(fit.params["k"] - 0.02) / 0.02 < 0.25, f"{fit.params['k']:.4f}")
    h.check("drag fit is quick enough for the slider", took < 5.0, f"{took:.2f} s")


def test_quadratic_drag_with_drift_recovers_the_slope():
    from core.fit import drag_linear, fit_model
    t = np.arange(900) / 30
    y = drag_linear(t, 60.0, 0.0, 1.2, 0.02, 120.0, 0.4)
    y = y + np.random.default_rng(4).normal(0, 0.3, t.size)
    fit = fit_model(t, y, "drag_linear")
    h.check("drag + drift converges", fit.ok, fit.message)
    h.check("drag + drift slope is recovered", abs(fit.params["m"] - 0.4) < 0.02,
            f"{fit.params['m']:.4f}")
    h.check("drag + drift omega is recovered within 3%",
            abs(fit.params["omega"] - 1.2) / 1.2 < 0.03, f"{fit.params['omega']:.4f}")


def test_drag_fit_on_damped_data_is_quick_and_stoppable():
    """Data that is not drag-shaped (a damped swing about a falling line, like Air Trial 4's
    distance): the drag fits took 87 s and 12 s here, which froze the plot. They now start from the
    damped fit, so each takes about a second; and `stop` abandons a fit part-way."""
    import time
    from core.fit import FitStopped, damped_linear, fit_model
    t = np.arange(10.59, 30.69, 1 / 30)
    y = damped_linear(t - t[0], 55.0, 0.5, 1.34, 0.0, 20.0, -0.5)
    y = y + np.random.default_rng(0).normal(0, 0.3, t.size)
    damped_r2 = fit_model(t, y, "damped").r2
    for model in ("drag", "drag_linear"):
        start = time.time()
        fit = fit_model(t, y, model)
        took = time.time() - start
        h.check(f"{model} fits damped-shaped data in a few seconds", fit.ok and took < 5.0,
                f"{took:.2f} s")
        h.check(f"{model} does at least nearly as well as the plain damped fit",
                fit.r2 > damped_r2 - 0.05, f"R² {fit.r2:.4f} vs {damped_r2:.4f}")
    calls = []
    try:
        fit_model(t, y, "drag", stop=lambda: calls.append(1) or len(calls) > 20)
        stopped = False
    except FitStopped:
        stopped = True
    h.check("stop abandons the fit at once", stopped and len(calls) == 21, str(len(calls)))


def test_plot_offers_the_drag_models():
    import matplotlib.pyplot as plt
    from gui.components.plot.plot import Plot
    from core.fit import MODELS

    class _Data:
        pass

    t = np.arange(600) / 30
    y = damped(t, A, GAMMA, OMEGA, PHI, C)
    data = _Data()
    data.processed_points = [np.column_stack([np.zeros_like(y), y])]
    data.timestamps = t
    data.unit = "cm"
    plot = Plot.__new__(Plot)
    plot.datamanager = data
    plot._widgets = []
    plot.ploty()
    radio = plot._widgets[-1]
    ax = plt.gcf().axes[0]
    text = lambda: "\n".join(tx.get_text() for a in plt.gcf().axes for tx in a.texts)  # noqa: E731
    h.check("the fit menu lists 8 models", len(MODELS) == 8, str(list(MODELS)))
    radio.set_active(list(MODELS).index("drag"))
    h.check("the drag model shows its drag strength k", "k     =" in text(), text()[:120])
    h.check("the drag model has no gamma line", "gamma =" not in text())
    plt.close("all")


def test_new_models_recover_their_parameters():
    """Data made from each of the newer models: the fit of that model recovers its own parameters
    (the period, and the term the model adds), well within a few seconds."""
    import time
    from core.fit import MODELS, fit_model
    t = np.arange(600) / 30
    rng = np.random.default_rng(5)
    cases = [
        ("damped_exp", (55.0, 0.3, 1.4, 0.2, 10.0, 15.0, 4.0), "ts", 0.1),
        ("both_exp", (50.0, 0.0, 1.4, 0.15, 0.01, 10.0, 15.0, 5.0), "beta", 0.2),
        ("gas", (50.0, 0.0, 1.4, 0.2, 0.0, 100.0, 15.0, -0.3), "L", 0.25),
        ("friction", (50.0, 0.0, 1.4, 0.1, 3.0, 15.0, -0.3), "f", 0.2),
    ]
    for key, truth, term, tolerance in cases:
        spec = MODELS[key]
        y = spec.func(t, *truth) + rng.normal(0, 0.3, t.size)
        start = time.time()
        fit = fit_model(t, y, key)
        took = time.time() - start
        true = dict(zip(spec.names, truth))
        h.check(f"{key}: a close fit, quickly", fit.ok and fit.r2 > 0.99 and took < 10,
                f"R² {fit.r2:.4f}, {took:.2f} s")
        h.check(f"{key}: omega is recovered within 2%",
                abs(fit.params["omega"] - true["omega"]) / true["omega"] < 0.02, f"{fit.params['omega']:.4f}")
        h.check(f"{key}: {term} is recovered within {tolerance:.0%}",
                abs(fit.params[term] - true[term]) / true[term] < tolerance,
                f"{fit.params[term]:.4g} vs {true[term]}")


def test_param_lines_cover_every_model():
    from core.fit import MODELS, FitResult, param_lines
    for key, spec in MODELS.items():
        fit = FitResult(ok=True, model=key, params={n: 1.0 for n in spec.names},
                        errors={n: 0.1 for n in spec.names}, tau=1.0)
        lines = param_lines(fit, "cm")
        h.check(f"{key}: one line per parameter, with units", len(lines) == len(spec.names)
                and all(line.split("=")[0].strip() in spec.names for line in lines), str(lines))


def test_initial_drop_is_high_to_first_low():
    """A motion that starts high and falls: the drop runs from the first high to the first low."""
    from core.fit import initial_drop
    t = np.arange(0, 6, 1 / 30)
    y = 50 + 40 * np.cos(2 * math.pi * 0.5 * t)  # Starts at 90 (high), first low at t = 1 s, value 10
    drop = initial_drop(t, y)
    h.check("initial drop is found", drop.ok, drop.message)
    h.check("the start is the first high", abs(drop.t_high) < 0.05 and abs(drop.y_high - 90) < 0.5,
            f"t {drop.t_high:.3f}, y {drop.y_high:.2f}")
    h.check("the low is the first turnaround", abs(drop.t_low - 1.0) < 0.05 and
            abs(drop.y_low - 10) < 0.5, f"t {drop.t_low:.3f}, y {drop.y_low:.2f}")
    h.check("drop and duration are right", abs(drop.drop - 80) < 1 and abs(drop.duration - 1.0) < 0.05,
            f"drop {drop.drop:.2f}, duration {drop.duration:.3f}")


def test_initial_drop_from_a_rest():
    """The object rests at the top (with a little tracking jitter) before it is let go, as in Air
    Trial 4: the drop runs from the resting place to the first low. It used to find no start
    (find_peaks never counts the first sample) and give up."""
    from core.fit import initial_drop
    t = np.arange(0, 20, 1 / 30)
    falling = t >= 0.5
    y = np.full(t.size, 71.2)
    y[falling] = 12 + 59.2 * np.exp(-0.4 * (t[falling] - 0.5)) * np.cos(1.34 * (t[falling] - 0.5))
    y[3:7] += [0.05, 0.1, 0.08, 0.05]   # The jitter: a tiny bump at the top, as tracked
    drop = initial_drop(t, y)
    h.check("the drop from a rest is found", drop.ok, drop.message)
    h.check("it starts at the resting place", drop.t_high < 0.55 and abs(drop.y_high - 71.3) < 0.1,
            f"t {drop.t_high:.2f}, y {drop.y_high:.2f}")
    h.check("it ends at the first low", abs(drop.t_low - (0.5 + 2.15)) < 0.2, f"t {drop.t_low:.2f}")


def test_initial_drop_heavily_damped():
    """A heavily damped motion, as water 270 trial 1: the swing back after the drop (10 cm) is less
    than a fifth of the drop (51 cm). The low must still be found (it was not: a low had to stand
    out by a fifth of the range); a dip on the way down must not be taken for it."""
    from core.fit import initial_drop
    t = np.arange(3.3, 5.6, 1 / 120)
    s = t - 3.3
    y = 25 + 46 * np.exp(-1.0 * s) * np.cos(5.45 * s)   # 71 at the start, first low near 4.0 s
    y[(s > 0.2) & (s < 0.23)] += 0.3                      # Tracking jitter on the way down
    drop = initial_drop(t, y)
    h.check("the drop of a heavily damped motion is found", drop.ok, drop.message)
    low = 3.3 + math.pi / 5.45 + math.atan(-1.0 / 5.45) / 5.45   # Where d/dt of the curve is 0 (its first low)
    h.check("it ends at the first low, not at a dip on the way", abs(drop.t_low - low) < 0.03,
            f"t {drop.t_low:.3f}, expected {low:.3f}")
    h.check("it starts at the top", abs(drop.y_high - 71) < 0.5, f"y {drop.y_high:.2f}")


def test_plot_shows_drop_markers_and_a_legend():
    import matplotlib.pyplot as plt
    from gui.components.plot.plot import Plot

    class _Data:
        pass

    t = np.arange(600) / 30
    y = 50 + 40 * np.cos(2 * math.pi * 0.5 * t)
    data = _Data()
    data.processed_points = [np.column_stack([np.zeros_like(y), y])]
    data.timestamps = t
    data.unit = "cm"
    plot = Plot.__new__(Plot)
    plot.datamanager = data
    plot._widgets = []
    plot.ploty()
    fig = plt.gcf()
    ax = fig.axes[0]
    texts = "\n".join(tx.get_text() for a in fig.axes for tx in a.texts)
    h.check("the plot reports the initial drop", "Initial drop =" in texts, texts[-120:])
    h.check("nothing is written over the data", not ax.texts and ax.get_legend() is None,
            f"{len(ax.texts)} texts, legend {ax.get_legend()}")
    legends = [a.get_legend() for a in fig.axes if a.get_legend() is not None]
    labels = [tx.get_text() for lg in legends for tx in lg.get_texts()]
    h.check("the side panel has a legend with the fit and the drop", "fit" in labels and
            "initial drop" in labels, str(labels))
    h.check("the legend can be dragged", all(lg._draggable is not None for lg in legends))
    plt.close("all")


def test_save_plot_starts_in_the_project_folder():
    """Save plot: the dialog opens in the project's folder with a name from the video and the
    plot, and the file written leaves the buttons and sliders out."""
    import os
    import tempfile
    import matplotlib.pyplot as plt
    import gui.components.plot.plot as plot_module
    from gui.components.plot.plot import Plot

    class _Data:
        pass

    t = np.arange(300) / 30
    y = 50 + 40 * np.cos(2 * math.pi * 0.5 * t)
    data = _Data()
    data.processed_points = [np.column_stack([np.zeros_like(y), y])]
    data.timestamps = t
    data.unit = "cm"
    plot = Plot.__new__(Plot)
    plot.datamanager = data
    plot._widgets = []
    folder = tempfile.mkdtemp(dir=h.WORK_DIR)
    plot.save_dir = folder
    plot.save_prefix = "Air Trial 1"
    plot.plotr()
    asked = {}

    def fake_dialog(**options):
        asked.update(options)
        return os.path.join(folder, options["initialfile"])

    real = plot_module.filedialog.asksaveasfilename
    plot_module.filedialog.asksaveasfilename = fake_dialog
    try:
        buttons = [w for w in plot._widgets if w.__class__.__name__ == "Button"]
        h.check("the plot has a Save plot button", len(buttons) == 1)
        path = plot.save_figure(plt.gcf(), "[O-1] $r$ vs $T$")
    finally:
        plot_module.filedialog.asksaveasfilename = real
    h.check("the dialog starts in the project folder", asked.get("initialdir") == folder, str(asked))
    h.check("the suggested name comes from the video and the plot",
            asked.get("initialfile") == "Air Trial 1_O_1_r_vs_T.png", asked.get("initialfile"))
    h.check("the plot is written", path is not None and os.path.getsize(path) > 10000, str(path))
    h.check("the controls are shown again after saving",
            all(w.ax.get_visible() for w in plot._widgets))
    plt.close("all")


if __name__ == "__main__":
    h.run_tests([test_fit_recovers_the_parameters, test_linear_drift_model_recovers_the_slope, test_plot_fit_type_switch, test_distance_r_is_csv_column_and_plot, test_warm_start_gives_the_same_fit, test_peak_spacing_agrees_with_the_fit,
                 test_best_period_prefers_a_good_fit, test_best_period_falls_back_to_peaks_for_a_poor_fit,
                 test_range_uses_only_the_selected_part, test_too_few_points_is_refused,
                 test_plot_slider_updates_the_fit,
                 test_quadratic_drag_recovers_the_parameters, test_quadratic_drag_with_drift_recovers_the_slope,
                 test_drag_fit_on_damped_data_is_quick_and_stoppable,
                 test_plot_offers_the_drag_models, test_new_models_recover_their_parameters,
                 test_param_lines_cover_every_model, test_initial_drop_is_high_to_first_low,
                 test_initial_drop_from_a_rest, test_initial_drop_heavily_damped,
                 test_plot_shows_drop_markers_and_a_legend,
                 test_save_plot_starts_in_the_project_folder])
