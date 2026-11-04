"""
plot.py

Responsible for plotting position and motion derivatives from processed data using matplotlib.

Author: Isam Balghari
"""

import os
import re
from tkinter import filedialog

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Button, RadioButtons, RangeSlider

from gui.components.checkbox import Checkbox
from .plottype import PlotType
from .datamanager import DataManager
from core.fit import (DEFAULT_MODEL, MODELS, best_period, fit_model, initial_drop, param_lines,
                  peak_periods)


class Plot:
    def __init__(self, parent, theme: str = 'ggplot') -> None:
        """
        Initializes the Plot component shell.
        Data coupling is deferred until activate() is invoked.

        Args:
            parent: The parent GUI container.
            theme (str): Matplotlib theme style.
        """
        self.parent = parent
        self.datamanager: DataManager | None = None
        self._widgets = []  # Range sliders must stay referenced, or their callbacks stop
        
        # Apply the visual plotting environment profile
        plt.style.use(theme)
        
    def activate(self, datamanager: DataManager, theme: str = 'ggplot') -> None:
    
        """
        Initializes the Plot component for visualizing data.

        Args:
            parent: The parent GUI container.
            datamanager (DataManager): The data manager with transformed coordinates.
            theme (str): Matplotlib theme style.
        """
        self.datamanager = datamanager
        
        self.checkbox = Checkbox(self.parent, PlotType, text="Choose Plots", callback=self.showplots)

    @property
    def points(self):
        return self.datamanager.processed_points

    @property
    def timestamps(self):
        return self.datamanager.timestamps

    def _unit(self) -> str:
        """The unit of the plotted values: the ruler's unit, or px before a scale is set."""
        return getattr(self.datamanager, "unit", "px")

    @staticmethod
    def _axis(symbol: str, unit: str) -> str:
        """Axis label with its unit, e.g. '$x$ (cm)'. Without a unit, just the symbol."""
        return f"{symbol} ({unit})" if unit else symbol

    def showplots(self, selected_plots: list[str]) -> None:
        """Displays all selected plots."""
        plot_map = {
            PlotType.X.name: self.plotx,
            PlotType.Y.name: self.ploty,
            PlotType.R.name: self.plotr,
            PlotType.XY.name: self.plotxy,
            PlotType.DX.name: self.plotdx,
            PlotType.DY.name: self.plotdy,
            PlotType.D2X.name: self.plotd2x,
            PlotType.D2Y.name: self.plotd2y
        }

        for plot_type in selected_plots:
            plot_func = plot_map.get(plot_type)
            if plot_func:
                plot_func()

        plt.show(block=False)

    def _plot(self, xdata, ydata, xlabel, ylabel, title, color):
        plt.figure()
        plt.title(title, fontname="Segoe UI Emoji")
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        xmin, xmax = np.min(xdata), np.max(xdata)
        ymin, ymax = np.min(ydata), np.max(ydata)
        plt.xlim((xmin*0.90, xmax*1.10))  # Add a 10% margin for better visibility
        plt.ylim((ymin*0.90, ymax*1.10))  # Add a 10% margin for better visibility
        plt.plot(xdata, ydata, '.', color=color, label="data")
        legend = plt.legend(loc="best", fontsize=8)  # Placed automatically, away from the data
        legend.set_draggable(True)  # ...and the user can move it if it still covers something
        ax = plt.gca()
        self._add_save_button(ax.figure, title)
        plt.sca(ax)  # Adding the button's axes made them current; the plot's axes come back
        return ax

    def _add_save_button(self, fig, title: str) -> None:
        """A "Save plot" button in the figure's bottom-right corner."""
        button_ax = fig.add_axes([0.84, 0.02, 0.14, 0.05])
        button = Button(button_ax, "Save plot")
        button.label.set_fontsize(9)
        button.on_clicked(lambda _event: self.save_figure(fig, title))
        self._widgets.append(button)

    def save_figure(self, fig, title: str):
        """
        Asks where to save the plot (starting in the project's folder) and writes it there. The
        buttons and sliders are left out of the image; the results panel is kept.

        Returns:
            The saved path, or None if the user cancelled.
        """
        prefix = getattr(self, "save_prefix", "") or ""
        stem = re.sub(r"[^A-Za-z0-9]+", "_", title.replace("$", "")).strip("_") or "plot"
        name = f"{prefix}_{stem}.png" if prefix else f"{stem}.png"
        options = {"initialfile": name, "defaultextension": ".png",
                   "filetypes": [("PNG image", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")]}
        folder = getattr(self, "save_dir", None)
        if folder and os.path.isdir(folder):
            options["initialdir"] = folder
        path = filedialog.asksaveasfilename(**options)
        if not path:
            return None
        controls = [w.ax for w in self._widgets if getattr(w, "ax", None) is not None
                    and w.ax.figure is fig]
        for ax in controls:
            ax.set_visible(False)
        try:
            fig.savefig(path, dpi=200, bbox_inches="tight")
        finally:
            for ax in controls:
                ax.set_visible(True)
            fig.canvas.draw_idle()
        return path

    def _add_fit(self, ax, t, y) -> None:
        """
        Adds a range slider under a time series. Dragging it picks the part of the data to use;
        the damped oscillator fit and the period estimates are then recomputed for that part.
        """
        fig = ax.figure
        # Plot in the middle, fit choice on the left, results and legend in a panel on the right,
        # so nothing covers the data
        fig.set_size_inches(12, 6)
        fig.subplots_adjust(left=0.22, right=0.62, bottom=0.25, top=0.9)
        t = np.asarray(t, dtype=float)
        y = np.asarray(y, dtype=float)
        order = np.argsort(t)
        t, y = t[order], y[order]
        if len(t) < 2 or t[0] == t[-1]:
            return

        fit_line, = ax.plot([], [], '-', color='k', linewidth=2, label='fit')
        drop_marks, = ax.plot([], [], 'o', color='tab:red', markersize=8, label='initial drop')
        if ax.get_legend() is not None:
            ax.get_legend().remove()  # The legend goes in the results panel instead

        panel = fig.add_axes([0.65, 0.25, 0.34, 0.65])
        panel.axis("off")
        info = panel.text(0.0, 1.0, "", transform=panel.transAxes, va="top", ha="left", fontsize=8,
                          family="monospace")
        handles, labels = ax.get_legend_handles_labels()
        legend = panel.legend(handles, labels, loc="lower left", fontsize=8, title="Legend")
        legend.set_draggable(True)

        slider_ax = fig.add_axes([0.25, 0.08, 0.37, 0.03])
        slider = RangeSlider(slider_ax, "Range (s)", float(t[0]), float(t[-1]),
                             valinit=(float(t[0]), float(t[-1])))

        keys = list(MODELS)
        radio_ax = fig.add_axes([0.01, 0.3, 0.22, 0.03 * len(keys)], frameon=False)
        radio_ax.set_title("Fit", fontsize=9, loc="left")
        radio = RadioButtons(radio_ax, [MODELS[k].label for k in keys],
                             active=keys.index(DEFAULT_MODEL))
        for label in radio.labels:
            label.set_fontsize(8)

        last = {"fit": None}  # The previous fit starts the next one, so dragging stays smooth

        def update(_=None):
            lo, hi = slider.val
            mask = (t >= lo) & (t <= hi)
            tp, yp = t[mask], y[mask]
            model = keys[radio.index_selected]
            fit = fit_model(tp, yp, model, warm=last["fit"])
            if fit.ok:
                last["fit"] = fit
            peaks = peak_periods(tp, yp)
            period, perr, source = best_period(fit, peaks)
            drop = initial_drop(tp, yp)
            if drop.ok:
                drop_marks.set_data([drop.t_high, drop.t_low], [drop.y_high, drop.y_low])
            else:
                drop_marks.set_data([], [])

            if fit.ok:
                names = MODELS[fit.model].names
                tt = tp - fit.t0
                fit_line.set_data(tp, MODELS[fit.model].func(tt, *(fit.params[k] for k in names)))
            else:
                fit_line.set_data([], [])
            info.set_text(_summary(fit, peaks, period, perr, source, self._unit(), drop))
            fig.canvas.draw_idle()

        slider.on_changed(update)
        radio.on_clicked(update)
        update()
        self._widgets.extend([slider, radio])

    def plotx(self):
        for k, tpts in enumerate(self.points):
            ax = self._plot(self.timestamps, tpts[:, 0], xlabel=r"$T(s)$", ylabel=self._axis(r"$x$", self._unit()),
                            title=f"[O-{k+1}] " + r"$x$ vs $T$", color='m')
            self._add_fit(ax, self.timestamps, tpts[:, 0])

    def ploty(self):
        for k, tpts in enumerate(self.points):
            ax = self._plot(self.timestamps, tpts[:, 1], xlabel=r"$T(s)$", ylabel=self._axis(r"$y$", self._unit()),
                            title=f"[O-{k+1}] " + r"$y$ vs $T$", color='m')
            self._add_fit(ax, self.timestamps, tpts[:, 1])

    def plotr(self):
        """Distance from the axes origin, r = sqrt(x^2 + y^2), against time, with the fit."""
        for k, tpts in enumerate(self.points):
            r = np.hypot(tpts[:, 0], tpts[:, 1])
            ax = self._plot(self.timestamps, r, xlabel=r"$T(s)$", ylabel=self._axis(r"$r$", self._unit()),
                            title=f"[O-{k+1}] " + r"$r$ vs $T$", color='m')
            self._add_fit(ax, self.timestamps, r)

    def plotxy(self):
        for k, tpts in enumerate(self.points):
            self._plot(tpts[:, 0], tpts[:, 1], xlabel=self._axis(r"$x$", self._unit()), ylabel=self._axis(r"$y$", self._unit()),
                       title=f"[O-{k+1}] " + r"$y$ vs $x$", color='c')

    def plotdx(self):
        for k, tpts in enumerate(self.points):
            dx_dt = np.gradient(tpts[:, 0], self.timestamps)
            self._plot(self.timestamps, dx_dt, xlabel=r"$T(s)$", ylabel=self._axis(r"$\frac{dx}{dt}$", f"{self._unit()}/s"),
                       title=f"[O-{k+1}] " + r"$\frac{dx}{dt}$", color='g')

    def plotdy(self):
        for k, tpts in enumerate(self.points):
            dy_dt = np.gradient(tpts[:, 1], self.timestamps)
            self._plot(self.timestamps, dy_dt, xlabel=r"$T(s)$", ylabel=self._axis(r"$\frac{dy}{dt}$", f"{self._unit()}/s"),
                       title=f"[O-{k+1}] " + r"$\frac{dy}{dt}$", color='g')

    def plotd2x(self):
        for k, tpts in enumerate(self.points):
            dx_dt = np.gradient(tpts[:, 0], self.timestamps)
            d2x_dt2 = np.gradient(dx_dt, self.timestamps)
            self._plot(self.timestamps, d2x_dt2, xlabel=r"$T(s)$", ylabel=self._axis(r"$\frac{d^2x}{dt^2}$", f"{self._unit()}/s²"),
                       title=f"[O-{k+1}] " + r"$\frac{d^2x}{dt^2}$", color='b')

    def plotd2y(self):
        for k, tpts in enumerate(self.points):
            dy_dt = np.gradient(tpts[:, 1], self.timestamps)
            d2y_dt2 = np.gradient(dy_dt, self.timestamps)
            self._plot(self.timestamps, d2y_dt2, xlabel=r"$T(s)$", ylabel=self._axis(r"$\frac{d^2y}{dt^2}$", f"{self._unit()}/s²"),
                       title=f"[O-{k+1}] " + r"$\frac{d^2y}{dt^2}$", color='b')


def _summary(fit, peaks, period, perr, source, unit: str = "", drop=None) -> str:
    """Text box for the fit parameters, period estimates, and the initial drop.
    Amplitude, offset, and drop are in `unit`."""
    lines = []
    if fit.ok:
        lines += param_lines(fit, unit) + [
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
        u = f" {unit}" if unit else ""
        if drop.ok:
            lines.append(f"Initial drop = {drop.drop:.4g}{u} in {drop.duration:.4g} s")
            lines.append(f"  (high at {drop.t_high:.3g} s, low at {drop.t_low:.3g} s)")
        else:
            lines.append(f"Initial drop: {drop.message}")
    return "\n".join(lines)


def main():
    """
    GUI-based test for the Plot system using dummy circular motion data.
    """
    import numpy as np
    import customtkinter as ctk
    from gui.components.tpoints import FPoint
    from gui.components.axes import Axes
    from gui.components.plot.datamanager import DataManager
    from gui.components.plot.plot import Plot
    from experiments.components.ocr import OCRData

    # --- Setup GUI ---
    ctk.set_appearance_mode("System")
    root = ctk.CTk()
    root.geometry("900x800")
    root.title("Plot and Axes Test")

    canvas = ctk.CTkCanvas(root, width=600, height=500, bg="white")
    canvas.pack(pady=10)

    btn_frame = ctk.CTkFrame(root)
    btn_frame.pack(pady=5)
    axes_btn = ctk.CTkButton(btn_frame, text="Set Axes")
    axes_btn.pack()

    btnlist = {"axes": axes_btn}
    axes = Axes(root, canvas, vwidth=600, vheight=500, btnlist=btnlist, activebtn=axes_btn)

    # --- Generate dummy data ---
    t = np.linspace(0, 2*np.pi, 360)
    x = 100 + 200 + 200 * np.cos(t)
    y = 200 + 200 * np.sin(t)

    fpoints = [[FPoint(x[i], y[i], 0, 0) for i in range(len(x))], 
               [FPoint(x[i], y[i], 0, 0) for i in range(len(x))]]

    # --- Dummy OCR data ---
    ocr_text = [["OCR={:.2f}s".format(i / 24) for i in range(len(x))],
                ["OCR={:.2f}s".format(i / 24) for i in range(len(x))]]
    ocrdata = OCRData(ocr_text)

    # --- Create DataManager ---
    datamanager = DataManager(tpoints=fpoints, ocrdata=ocrdata, axes=axes, vwidth=600, vheight=500,
                              fwidth=600, fheight=500, fps=1, scale=1.0)

    # --- Setup Axes and Plot after marking ---
    def on_axes_applied():
        datamanager.transform()
        Plot(parent=root, datamanager=datamanager, theme='ggplot')

    axes_btn.configure(command=lambda: [axes.markaxes(), root.after(3000, on_axes_applied)])
    root.mainloop()


if __name__ == "__main__":
    main()
