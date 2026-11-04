"""Units for the scale ruler: typed "50 cm" sets the length and unit, the ruler shows the unit, the
project keeps it, and the plot labels carry it (needs a window for the ruler only).
"""

import numpy as np

from tests import harness as h
h.setup_env()

import matplotlib  # noqa: E402
matplotlib.use("Agg")  # Plots are drawn to nothing: no windows open

import customtkinter as ctk  # noqa: E402
from core.units import parse_length  # noqa: E402


def test_parse_length_reads_value_and_unit():
    h.check("'50 cm' is 50 cm", parse_length("50 cm") == (50.0, "cm"), str(parse_length("50 cm")))
    h.check("'2.5m' with no space", parse_length("2.5m") == (2.5, "m"))
    h.check("a number alone has no unit", parse_length("12") == (12.0, ""))
    h.check("a unit with a slash is kept", parse_length("9.8 m/s^2") == (9.8, "m/s^2"))
    h.check("spaces around the text are ignored", parse_length("  4   mm  ") == (4.0, "mm"))
    for bad in ("", "cm", "0 cm", "-3 cm", "1 2 cm"):
        try:
            parse_length(bad)
            h.check(f"{bad!r} is refused", False)
        except ValueError:
            h.check(f"{bad!r} is refused", True)


def test_plot_labels_carry_the_unit():
    import matplotlib.pyplot as plt
    from gui.components.plot.plot import Plot, _summary
    from core.fit import fit_model

    t = np.arange(600) / 30
    y = 80 * np.exp(-0.1 * t) * np.cos(1.2 * t) + 120

    class _Data:
        unit = "cm"
        timestamps = t
        processed_points = [np.column_stack([np.zeros_like(y), y])]

    plot = Plot.__new__(Plot)
    plot.datamanager = _Data()
    plot._widgets = []
    plot.ploty()
    ax = plt.gcf().axes[0]
    h.check("y axis label has the unit", ax.get_ylabel() == r"$y$ (cm)", ax.get_ylabel())
    h.check("time axis is not given a unit", ax.get_xlabel() == r"$T(s)$", ax.get_xlabel())
    plt.close("all")

    plot.datamanager.unit = "px"
    plot.plotdx()
    ax = plt.gcf().axes[0]
    h.check("velocity label is unit per second", "px/s" in ax.get_ylabel(), ax.get_ylabel())
    plt.close("all")

    fit = fit_model(t, y, "damped_linear")
    text = _summary(fit, _NoPeaks(), float("nan"), float("nan"), None, "cm")
    h.check("fit amplitude is in the unit", "A     =" in text and " cm" in text.split("\n")[0],
            text.split("\n")[0])
    h.check("fit offset is in the unit", any(line.startswith("C") and line.endswith(" cm")
                                              for line in text.split("\n")))


class _NoPeaks:
    period = float("nan")
    period_err = float("nan")
    n_maxima = 0
    n_minima = 0


def test_ruler_shows_saves_and_restores_the_unit():
    root = ctk.CTk()
    root.geometry("900x600")
    canvas = ctk.CTkCanvas(root, width=900, height=600)
    canvas.pack()
    root.update()
    from gui.components.ruler import ScaleRuler

    ruler = ScaleRuler(canvas, 900, 600, {}, None)
    ruler.placed = True
    ruler.p1, ruler.p2 = [100.0, 300.0], [400.0, 300.0]  # 300 px long
    ruler.real_world_length, ruler.unit = 50.0, "cm"
    ruler.draw()
    texts = [canvas.itemcget(i, "text") for i in canvas.find_withtag(ruler.RULER_TAG)
             if canvas.type(i) == "text"]
    h.check("ruler label shows the typed length and unit", texts == ["50.00 cm"], str(texts))
    h.check("unit label is the typed unit once calibrated", ruler.unit_label() == "cm")

    state = ruler.get_state()
    h.check("project state keeps the unit", state["unit"] == "cm", str(state))

    other = ScaleRuler(canvas, 900, 600, {}, None)
    other.restore_state(state)
    h.check("restored ruler has the unit", other.unit == "cm" and other.unit_label() == "cm")

    ruler.real_world_length = None
    h.check("uncalibrated ruler measures in px", ruler.unit_label() == "px")

    # Undo puts the ruler back where Auto Ruler found it
    ruler.placed = True
    ruler.p1, ruler.p2 = [100.0, 300.0], [400.0, 300.0]
    ruler.pack()
    ruler._before_snap = ([100.0, 300.0], [400.0, 300.0])
    ruler.p1, ruler.p2 = [120.0, 290.0], [380.0, 310.0]  # As if Auto Ruler moved it
    ruler.undo_autosnap()
    h.check("Undo puts the ruler back where it was", ruler.p1 == [100.0, 300.0] and
            ruler.p2 == [400.0, 300.0], f"{ruler.p1} {ruler.p2}")
    h.check("Undo only works once", ruler._before_snap is None)
    ruler.clear()
    root.destroy()


if __name__ == "__main__":
    h.run_tests([test_parse_length_reads_value_and_unit, test_plot_labels_carry_the_unit,
                 test_ruler_shows_saves_and_restores_the_unit])
