"""
Plot windows for the Qt spike. Each plot is one matplotlib figure in its own window, with the
matplotlib toolbar (zoom, pan, and Save). The plots are the Tk app's (gui/components/plot/plot.py):
the same eight kinds, the same derivatives, and the fit panel on position against time.

Save (the button, or the toolbar's save) asks nothing: it writes the plot's picture, its data and
its fit results (when it has a fit) next to the video, named after it and the plot, and says where.
"""

import csv
import os

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)

from . import project_file
from .analysis import attach_fit
from .fit_table import ModelTable
from .measure import derivative

# Kind, and the name in the dialog
KINDS = [
    ("x", "x against time"),
    ("y", "y against time"),
    ("r", "distance from the origin against time"),
    ("xy", "trajectory (y against x)"),
    ("dx", "velocity dx/dt"),
    ("dy", "velocity dy/dt"),
    ("d2x", "acceleration d²x/dt²"),
    ("d2y", "acceleration d²y/dt²"),
]
DEFAULT_KINDS = ("r",)  # Distance from the origin against time: the one most often wanted first


def choose_plots(parent: QWidget, default=DEFAULT_KINDS) -> list[str] | None:
    """Asks which plots to show (`default` ticked). None if the user cancels, else the chosen kinds."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Plots")
    layout = QVBoxLayout(dialog)
    boxes = {}
    for kind, label in KINDS:
        box = QCheckBox(label)
        box.setChecked(kind in default)
        layout.addWidget(box)
        boxes[kind] = box
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                               QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    if not dialog.exec():
        return None
    chosen = [kind for kind, box in boxes.items() if box.isChecked()]
    return chosen or None


def open_plots(number: int, t: np.ndarray, xy: np.ndarray, unit: str, kinds: list[str],
               video_path: str | None = None, on_saved=None) -> list:
    """Opens one window per kind for the object `number`. Returns them (keep them referenced).
    Saved files go next to `video_path`; `on_saved(message)` is told where."""
    x, y = xy[:, 0], xy[:, 1]
    r = np.hypot(x, y)
    spec = {
        # kind: (name, x data, y data, x label, y label, colour, time for the fit panel or None,
        #        column names for the saved data)
        "x": ("x against time", t, x, "$T(s)$", _axis("$x$", unit), "m", t,
              ("time_s", f"x ({unit})")),
        "y": ("y against time", t, y, "$T(s)$", _axis("$y$", unit), "m", t,
              ("time_s", f"y ({unit})")),
        "r": ("distance against time", t, r, "$T(s)$", _axis("$r$", unit), "m", t,
              ("time_s", f"r ({unit})")),
        "xy": ("y against x", x, y, _axis("$x$", unit), _axis("$y$", unit), "c", None,
               (f"x ({unit})", f"y ({unit})")),
        "dx": ("dx/dt", t, derivative(x, t), "$T(s)$",
               _axis(r"$\frac{dx}{dt}$", f"{unit}/s"), "g", None,
               ("time_s", f"dx/dt ({unit}/s)")),
        "dy": ("dy/dt", t, derivative(y, t), "$T(s)$",
               _axis(r"$\frac{dy}{dt}$", f"{unit}/s"), "g", None,
               ("time_s", f"dy/dt ({unit}/s)")),
        "d2x": ("d²x/dt²", t, derivative(derivative(x, t), t), "$T(s)$",
                _axis(r"$\frac{d^2x}{dt^2}$", f"{unit}/s²"), "b", None,
                ("time_s", f"d2x/dt2 ({unit}/s2)")),
        "d2y": ("d²y/dt²", t, derivative(derivative(y, t), t), "$T(s)$",
                _axis(r"$\frac{d^2y}{dt^2}$", f"{unit}/s²"), "b", None,
                ("time_s", f"d2y/dt2 ({unit}/s2)")),
    }
    windows = []
    for kind in kinds:
        name, xdata, ydata, xlabel, ylabel, colour, fit_time, columns = spec[kind]
        window = PlotWindow(f"[O-{number}] {name}", xdata, ydata, xlabel, ylabel, colour, unit,
                            fit_time, columns)
        window.video_path, window.on_saved = video_path, on_saved
        window.file_suffix = f"_object{number}_{kind}"
        window.kind, window.number = kind, number   # The main window's plot settings (history, tools)
        window.show()
        windows.append(window)
    return windows


def _axis(symbol: str, unit: str) -> str:
    """Axis label with its unit, e.g. '$x$ (cm)'. Without a unit, just the symbol."""
    return f"{symbol} ({unit})" if unit else symbol


def _padded(values: np.ndarray) -> tuple[float, float]:
    """The data's range with a margin, so no point sits on the frame (for negative data too)."""
    lo, hi = float(np.min(values)), float(np.max(values))
    pad = 0.05 * (hi - lo) if hi > lo else 1.0
    return lo - pad, hi + pad


def write_plot_csv(path: str, columns: tuple[str, str], xdata, ydata) -> None:
    """The plotted points: one row per point, with the two column names as the header."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for x, y in zip(xdata, ydata):
            writer.writerow([f"{x:.6g}", f"{y:.6g}"])


def write_results(path: str, title: str, text: str) -> None:
    """The fit's results as shown in the plot's panel (the parameters, periods and drop)."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{title}\n\n{text}\n")


class _Toolbar(NavigationToolbar2QT):
    """matplotlib's toolbar, with its save button saving as the window's Save does (no dialog)."""

    def save_figure(self, *args):
        self.parent().save_all()


class PlotWindow(QWidget):
    """One plot. For position against time, `fit_time` is the time, and the fit panel is shown."""

    def __init__(self, title: str, xdata: np.ndarray, ydata: np.ndarray, xlabel: str, ylabel: str,
                 colour: str, unit: str = "", fit_time: np.ndarray | None = None,
                 columns: tuple[str, str] = ("x", "y")) -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.resize(1100, 640)
        self.title_text = title
        self.columns = columns
        self.xdata, self.ydata = np.asarray(xdata), np.asarray(ydata)
        self.figure = Figure(figsize=(12, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = _Toolbar(self.canvas, self)
        self.video_path: str | None = None   # Saved files go next to it (set by open_plots)
        self.on_saved = None                 # Told where they went
        self.file_suffix = ""                # Added to the video's name in the saved files' names
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        middle = QHBoxLayout()
        layout.addLayout(middle, 1)
        middle.addWidget(self.canvas, 1)
        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setToolTip("Saves the picture, the data and the fit results next to the video")
        self.save_btn.clicked.connect(self.save_all)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close)   # Cmd+W on macOS: closes this plot only
        buttons.addWidget(self.save_btn)
        self.saved_label = QLabel("")        # Where the files went, in full
        self.saved_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        buttons.addWidget(self.saved_label, 1)
        layout.addLayout(buttons)

        ax = self.figure.add_subplot(111)
        ax.plot(xdata, ydata, ".", color=colour, label="data")
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_xlim(*_padded(xdata))
        ax.set_ylim(*_padded(ydata))
        # Position against time: the data is shown at once, and the fit panel (with the legend)
        # follows when its first fit is done (analysis.FitPanel). Other plots get a legend here,
        # placed away from the data, and movable.
        self.fit_panel = attach_fit(self.figure, ax, fit_time, ydata, unit) if fit_time is not None else None
        self.model_table = None
        if self.fit_panel is not None:
            # The models, on the left: a click or Up / Down shows another model's fit
            self.model_table = ModelTable(self.fit_panel.keys, self.fit_panel.model)
            middle.insertWidget(0, self.model_table)
            self.model_table.chosen.connect(self.fit_panel.choose)
            self.fit_panel.on_fits = self.model_table.set_fits
            QShortcut(QKeySequence(Qt.Key.Key_Up), self, lambda: self.model_table.step(-1))
            QShortcut(QKeySequence(Qt.Key.Key_Down), self, lambda: self.model_table.step(1))
            self.resize(1100 + self.model_table.sizeHint().width(),
                        max(680, self.model_table.rows_height() + 240))   # Every row in view
        else:
            legend = ax.legend(loc="best", fontsize=8)
            legend.set_draggable(True)
        self.canvas.draw_idle()

    @property
    def results(self):
        """The fit results text (None without a fit panel, or until its first fit is done)."""
        return self.fit_panel.results if self.fit_panel is not None else None

    def closeEvent(self, event) -> None:
        if self.fit_panel is not None:
            self.fit_panel.close()   # A fit under way stops at its next trial
        super().closeEvent(event)

    def save_all(self) -> list[str]:
        """Saves the plot's picture (PNG), its data (CSV) and its fit results (text, for the part
        of the data the range slider chose, when it has a fit), next to the video. Returns the paths."""
        if not self.video_path:
            return []
        if self.fit_panel is not None:
            self.fit_panel.wait_for_fit(10.0)   # Saved with its fit (the window keeps responding)
        picture = project_file.output_path(self.video_path, self.file_suffix, ".png")
        stem = picture[:-len(".png")]       # The same name for all three, so they sort together
        paths = [picture, stem + ".csv"]
        try:
            self.figure.savefig(picture, dpi=150)
            write_plot_csv(paths[1], self.columns, self.xdata, self.ydata)
            if self.results is not None:
                paths.append(stem + "_fit.txt")
                write_results(paths[2], self.title_text, self.results.get_text())
        except OSError as e:
            QMessageBox.warning(self, "Save", f"The plot could not be saved:\n{e}")
            return []
        folder = os.path.dirname(picture)
        message = f"Saved to {folder}: " + ", ".join(os.path.basename(p) for p in paths)
        self.saved_label.setText(message)
        if self.on_saved is not None:
            self.on_saved(message)
        return paths
