"""
Measurements, without a window: the axes transform, tracked positions, derivatives, the fit and its
summary (the analysis panel's own functions), and the CSV export.

    ~/.venvs/phystrackx-qt/bin/python tests/test_measure.py
"""

import csv
import math
import os

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

import numpy as np  # noqa: E402

from phystrack_qt.analysis import fitting, summary_text  # noqa: E402
from phystrack_qt.measure import derivative, export_csv, physical, track_series  # noqa: E402


def test_axes_transform() -> None:
    origin, L = (100.0, 50.0), 80.0
    right, above = [origin[0] + L, origin[1]], [origin[0], origin[1] - L]
    got = physical([right, above], origin, 0.0)
    h.check("unrotated: right of the origin is +x", np.allclose(got[0], [L, 0]), str(got[0]))
    h.check("unrotated: above the origin is +y (y is up)", np.allclose(got[1], [0, L]), str(got[1]))

    # Rotated 30 degrees clockwise on screen, as AxesItem draws it: points along its drawn axes
    a = math.radians(30)
    along_x = [origin[0] + L * math.cos(a), origin[1] + L * math.sin(a)]
    along_y = [origin[0] + L * math.sin(a), origin[1] - L * math.cos(a)]
    got = physical([along_x, along_y], origin, 30.0)
    h.check("rotated 30°: along the drawn x axis gives x = L, y = 0",
            np.allclose(got[0], [L, 0], atol=1e-9), str(got[0]))
    h.check("rotated 30°: along the drawn y axis gives y = L, x = 0",
            np.allclose(got[1], [0, L], atol=1e-9), str(got[1]))
    h.check("scale is real units per picture pixel",
            np.allclose(physical([right], origin, 0.0, scale=0.5)[0], [L * 0.5, 0]))


def test_track_series() -> None:
    boxes = {5: (10.0, 20.0, 4.0, 6.0), 3: (0.0, 0.0, 2.0, 2.0), 4: None, 7: (8.0, 8.0, 2.0, 2.0)}
    frames, centres = track_series(boxes, fps=30.0)
    h.check("tracked frames only, in order", frames.tolist() == [3, 5, 7], str(frames.tolist()))
    h.check("centres are box centres in picture pixels",
            np.allclose(centres, [[1, 1], [12, 23], [9, 9]]), str(centres.tolist()))


def test_derivatives() -> None:
    t = np.linspace(0, 2, 201)
    x = 0.5 * 3.0 * t * t  # Constant acceleration 3
    v = derivative(x, t)
    a = derivative(v, t)
    h.check("velocity of constant acceleration is a*t (interior)",
            np.allclose(v[1:-1], 3.0 * t[1:-1], atol=1e-6))
    # The second difference is exact only away from the ends (np.gradient is one-sided there)
    h.check("acceleration is constant (interior)", np.allclose(a[2:-2], 3.0, atol=1e-6))


def test_fit_and_summary() -> None:
    t = np.linspace(0, 10, 400)
    f, gamma, A, phi, C = 0.5, 0.08, 40.0, 0.7, 120.0
    y = C + A * np.exp(-gamma * t) * np.cos(2 * math.pi * f * t + phi)
    fit = fitting.fit_model(t, y, "damped")
    h.check("damped fit succeeds", fit.ok, fit.message)
    h.check("damped fit recovers omega to 1%",
            abs(fit.params["omega"] - 2 * math.pi * f) / (2 * math.pi * f) < 0.01,
            f"{fit.params['omega']:.4f} vs {2 * math.pi * f:.4f}")
    text = summary_text(fit, fitting.peak_periods(t, y), *fitting.best_period(
        fit, fitting.peak_periods(t, y)), "cm", fitting.initial_drop(t, y))
    h.check("summary lists omega and the fit's R²", "omega" in text and "R²" in text)


def test_csv_export() -> None:
    path = os.path.join(h.WORK, "export_test.csv")
    series = [(1, np.array([0, 1, 2]), np.array([0.0, 1 / 30, 2 / 30]),
               np.array([[1.0, 2.0], [1.5, 2.5], [2.0, 3.0]])),
              (2, np.array([1, 2]), np.array([1 / 30, 2 / 30]), np.array([[10.0, 0.0], [11.0, 0.0]]))]
    export_csv(path, series, "cm")
    with open(path, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    h.check("header names each object's x and y in the unit",
            rows[0] == ["frame", "time_s", "x1 (cm)", "y1 (cm)", "x2 (cm)", "y2 (cm)"], str(rows[0]))
    h.check("one row per frame any object was tracked in", len(rows) == 4, str(len(rows) - 1))
    h.check("an object not tracked in a frame leaves its cells empty",
            rows[1][4:] == ["", ""] and rows[2][2] == "1.5", str(rows[1:3]))


if __name__ == "__main__":
    h.app()
    for test in (test_axes_transform, test_track_series, test_derivatives, test_fit_and_summary,
                 test_csv_export):
        print(test.__name__)
        test()
    h.finish()
