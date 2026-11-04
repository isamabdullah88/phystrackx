"""
The fit models as a table beside a plot: one large row per model (its name, with its equation under
it as LaTeX), and the R² and period of its fit on the range shown, filled in as the fits come in
(the best R² in bold). Clicking a row, or Up and Down (set up by the plot window), shows that model's
fit, so models can be compared quickly.

The equations are pictures (equations.equation_png, drawn ahead by the plot warm-up), so they show
as LaTeX whatever the theme; the colours are fixed (dark text on white).
"""

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QHeaderView, QLabel, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from .equations import SCALE, equation_png
from .parent_imports import import_light

fitting = import_light("core.fit")

TEXT = "#111111"
EQUATION = "#2a2a2a"   # Darker than the old light grey, which was hard to read
WAITING = "…"
R2_WIDTH = 70
PERIOD_WIDTH = 130

_STYLE = f"""
QTableWidget {{ background: white; color: {TEXT}; gridline-color: #d8dde4; font-size: 13px; }}
QTableWidget::item {{ padding: 4px; border-bottom: 1px solid #e3e7ec; }}
QTableWidget::item:hover {{ background: #eef4fc; }}
QTableWidget::item:selected {{ background: #cfe0f8; color: {TEXT}; }}
QHeaderView::section {{ background: #f2f4f7; color: {TEXT}; padding: 4px; border: none;
                       border-bottom: 1px solid #c9d0d9; font-weight: bold; }}
"""


def _picture(tex: str) -> QLabel:
    """A label showing the LaTeX `tex` as a picture (its text, if the picture cannot be drawn)."""
    label = QLabel()
    try:
        pixmap = QPixmap()
        pixmap.loadFromData(equation_png(tex))
        pixmap.setDevicePixelRatio(SCALE)   # Drawn at SCALE times the size shown: sharp, and not big
        label.setPixmap(pixmap)
    except Exception:   # A picture that fails must not take the plot window down
        label.setText(tex)
    return label


def _model_cell(key: str) -> QWidget:
    """The model's name, with each line of its equation under it, on a transparent background."""
    model = fitting.MODELS[key]
    cell = QWidget()
    layout = QVBoxLayout(cell)
    layout.setContentsMargins(8, 6, 8, 6)
    layout.setSpacing(2)
    name = QLabel(model.label)
    name.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 600; background: transparent;")
    layout.addWidget(name)
    for line in model.equation:
        picture = _picture(line)
        picture.setStyleSheet("background: transparent;")
        layout.addWidget(picture)
    # Clicks go to the row, not to these labels
    for widget in [cell, *cell.findChildren(QWidget)]:
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    return cell


class ModelTable(QWidget):
    """The model table. `chosen(key)` is emitted when a row is picked (by a click or `step`)."""

    chosen = Signal(str)

    def __init__(self, keys: list, current: str, parent=None) -> None:
        super().__init__(parent)
        self.keys = list(keys)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 0, 6)
        title = QLabel("Fit model   (↑ ↓ to switch)")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        self.table = table = QTableWidget(len(self.keys), 3)
        table.setStyleSheet(_STYLE)
        table.setHorizontalHeaderLabels(["Model", "R²", "Period (s)"])
        table.verticalHeader().hide()
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # Up and Down belong to the plot window
        table.setShowGrid(False)
        table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        width = 0
        for row, key in enumerate(self.keys):
            cell = _model_cell(key)
            table.setCellWidget(row, 0, cell)
            hint = cell.sizeHint()
            table.setRowHeight(row, hint.height() + 8)
            width = max(width, hint.width())
            for col in (1, 2):
                item = QTableWidgetItem(WAITING)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, item)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, width + 8)
        for col, w in ((1, R2_WIDTH), (2, PERIOD_WIDTH)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(col, w)
        table.setFixedWidth(width + 8 + R2_WIDTH + PERIOD_WIDTH + 22)
        layout.addWidget(table, 1)

        layout.addWidget(_picture(fitting.EQUATION_NOTE))

        self.table.selectRow(self.keys.index(current))
        table.currentCellChanged.connect(self._row_changed)

    def rows_height(self) -> int:
        """The table's height with every row in view (and its header)."""
        table = self.table
        return sum(table.rowHeight(row) for row in range(table.rowCount())) + \
            table.horizontalHeader().sizeHint().height() + 4

    @property
    def current(self) -> str:
        return self.keys[max(self.table.currentRow(), 0)]

    def step(self, delta: int) -> None:
        """Picks the model `delta` rows down (up when negative), stopping at the ends."""
        row = min(max(self.table.currentRow() + delta, 0), len(self.keys) - 1)
        if row != self.table.currentRow():
            self.table.selectRow(row)

    def select(self, key: str) -> None:
        """Picks the model `key`, as a click on its row does (from code: a tool, a revert)."""
        if key in self.keys:
            self.table.selectRow(self.keys.index(key))

    def _row_changed(self, row: int, *_) -> None:
        if 0 <= row < len(self.keys):
            self.chosen.emit(self.keys[row])

    def set_fits(self, fits: dict) -> None:
        """Fills in R² and the period (with its error) of each model's fit (key -> FitResult, or
        None while it is still to come). The best R² is in bold."""
        r2 = {k: f.r2 for k, f in fits.items() if f is not None and f.ok and math.isfinite(f.r2)}
        best = max(r2, key=r2.get) if r2 else None
        for row, key in enumerate(self.keys):
            fit = fits.get(key)
            r2_item, t_item = self.table.item(row, 1), self.table.item(row, 2)
            if fit is None:
                r2_item.setText(WAITING)
                t_item.setText(WAITING)
            elif not fit.ok:
                r2_item.setText("failed")
                t_item.setText("–")
            else:
                r2_item.setText(f"{fit.r2:.4f}")
                if math.isfinite(fit.period):
                    err = f" ± {fit.period_err:.2g}" if math.isfinite(fit.period_err) else ""
                    t_item.setText(f"{fit.period:.3f}{err}")
                else:
                    t_item.setText("–")
            font = r2_item.font()
            font.setBold(key == best)
            r2_item.setFont(font)
            r2_item.setToolTip(fit.message if fit is not None and fit.message else "")
