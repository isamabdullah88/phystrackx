"""
The scale ruler of the Qt spike: a bar laid along something of known length. Its length in real
units ("50 cm") gives the scale for every measurement. Behaves as the Tk ruler
(gui/components/ruler.py): the ends move freely, the typed length is kept when the ruler is moved
or stretched (so the scale changes with its picture length), and the unit is shown on the ruler.

A child of the picture, so it follows zoom and pan. Ends and bar are in picture pixels; the bar,
ticks, handles and label are drawn in screen pixels, so they keep their size at any zoom.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPainterPath, \
    QPainterPathStroker, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject

from core.units import unit_suffix

BAR_WIDTH = 16      # Screen pixels: the dark bar over the ruler's line
TICKS = 11          # As the Tk ruler
TICK_HALF = 8       # Screen pixels either side of the line, for each tick
HANDLE = 6          # Screen pixels: the radius of the two end handles
GRAB = 12           # Screen pixels: how close to an end, or to the bar, a press counts
MIN_LENGTH = 10     # Picture pixels: an end cannot be dragged closer to the other than this
HANDLE_COLOR = QColor("#ec17c5")  # The Tk ruler's handle colour


class RulerItem(QGraphicsObject):
    changed = Signal()           # Moved, stretched, or calibrated
    length_requested = Signal()  # Double-clicked while editable: the user types the real length

    def __init__(self, p1: QPointF, p2: QPointF, parent: QGraphicsItem) -> None:
        super().__init__(parent)
        self.p1, self.p2 = QPointF(p1), QPointF(p2)  # Picture pixels
        self.real_length: float | None = None        # Typed length, once calibrated
        self.unit = ""                               # Typed unit, e.g. "cm" ("" when none)
        self.editable = False
        self._grab: str | None = None                # "p1", "p2" or "move" while dragging
        self._grab_offset = QPointF()                # Pointer to the bar's middle, for "move"
        self._before_snap: tuple[QPointF, QPointF] | None = None
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)  # Pans the picture until editable
        self.setZValue(3)                            # Above the axes and the tracked boxes

    # --- Geometry and calibration ----------------------------------------------------------------
    def px_length(self) -> float:
        return math.hypot(self.p2.x() - self.p1.x(), self.p2.y() - self.p1.y())

    def scale(self) -> float:
        """Real units per picture pixel: 1 until the ruler has a real length."""
        if self.real_length is None or self.px_length() == 0:
            return 1.0
        return self.real_length / self.px_length()

    def unit_label(self) -> str:
        """The unit of the measurements: the typed unit once calibrated, else pixels."""
        return "px" if self.real_length is None else self.unit

    def label_text(self) -> str:
        if self.real_length is None:
            return f"{self.px_length():.1f} px"
        return f"{self.real_length:.2f}{unit_suffix(self.unit)}"

    def set_length(self, real_length: float, unit: str) -> None:
        """Calibrates the ruler: its current picture length is this real length."""
        self.real_length, self.unit = real_length, unit
        self._emit()

    def set_ends(self, p1: QPointF, p2: QPointF) -> None:
        self.p1, self.p2 = self._clamp(QPointF(p1)), self._clamp(QPointF(p2))
        self._emit()

    def set_editable(self, on: bool) -> None:
        """While editable, the ruler takes the mouse (drag its ends or bar); otherwise the picture
        pans under it, as everywhere else."""
        self.editable = on
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton if on else Qt.MouseButton.NoButton)
        self.update()

    # --- Auto Ruler (core.autoruler, through MainWindow) -----------------------------------------
    def snap_to(self, p1, p2) -> None:
        """Moves the ends to the snapped points, keeping the old ones for Undo."""
        self._before_snap = (QPointF(self.p1), QPointF(self.p2))
        self.set_ends(QPointF(float(p1[0]), float(p1[1])), QPointF(float(p2[0]), float(p2[1])))

    def can_undo(self) -> bool:
        return self._before_snap is not None

    def undo_snap(self) -> None:
        if self._before_snap is not None:
            before, self._before_snap = self._before_snap, None  # Cleared first: set_ends emits
            self.set_ends(*before)

    # --- Drawing ---------------------------------------------------------------------------------
    def boundingRect(self) -> QRectF:
        """The whole picture (plus a margin): the drawing is in screen pixels, so how much of the
        picture it covers depends on the zoom, and the picture is the simplest safe bound."""
        parent = self.parentItem()
        if parent is None:
            return QRectF()
        return parent.boundingRect().adjusted(-200, -200, 200, 200)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        # Work in screen pixels: map the ends with the painter's transform, then draw unscaled
        to_screen = painter.worldTransform()
        a, b = to_screen.map(self.p1), to_screen.map(self.p2)
        dx, dy = b.x() - a.x(), b.y() - a.y()
        length = math.hypot(dx, dy)
        if length < 1:
            return
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux  # Across the bar

        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(0, 0, 0, 150), BAR_WIDTH, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.FlatCap))
        painter.drawLine(a, b)
        painter.setPen(QPen(QColor("white"), 1.5))
        painter.drawLine(a, b)
        painter.setPen(QPen(QColor("white"), 2))
        for i in range(TICKS):
            t = i / (TICKS - 1)
            x, y = a.x() + dx * t, a.y() + dy * t
            painter.drawLine(QPointF(x - nx * TICK_HALF, y - ny * TICK_HALF),
                             QPointF(x + nx * TICK_HALF, y + ny * TICK_HALF))

        # The label sits above the bar, on a dark background so it reads on any picture
        font = QFont("Helvetica", 12, QFont.Weight.Bold)
        painter.setFont(font)
        metrics = QFontMetricsF(font)
        text, width, height = self.label_text(), metrics.horizontalAdvance(self.label_text()), \
            metrics.height()
        mid_x, mid_y = (a.x() + b.x()) / 2, (a.y() + b.y()) / 2
        offset = BAR_WIDTH / 2 + height / 2 + 6
        centre_x, centre_y = mid_x - nx * offset, mid_y - ny * offset
        rect = QRectF(centre_x - width / 2 - 6, centre_y - height / 2, width + 12, height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 170))
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(QColor("white"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        if self.editable:
            painter.setPen(QPen(QColor("white"), 1.5))
            painter.setBrush(QBrush(HANDLE_COLOR))
            for p in (a, b):
                painter.drawEllipse(p, HANDLE, HANDLE)
        painter.restore()

    def shape(self) -> QPainterPath:
        """The bar and the two ends pick up the mouse, with the grab area kept the same on screen."""
        s = self._screen_scale()
        line = QPainterPath()
        line.moveTo(self.p1)
        line.lineTo(self.p2)
        stroker = QPainterPathStroker()
        stroker.setWidth(2 * GRAB / s)
        path = stroker.createStroke(line)
        for p in (self.p1, self.p2):
            ends = QPainterPath()
            ends.addEllipse(p, GRAB / s, GRAB / s)
            path = path.united(ends)
        return path

    def _screen_scale(self) -> float:
        """Screen pixels per picture pixel (1 when there is no view)."""
        views = self.scene().views() if self.scene() is not None else []
        return (views[0].transform().m11() or 1.0) if views else 1.0

    # --- Mouse -----------------------------------------------------------------------------------
    def mousePressEvent(self, event) -> None:
        if not self.editable or event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        pos = event.pos()
        tolerance = GRAB / self._screen_scale()
        mid = QPointF((self.p1.x() + self.p2.x()) / 2, (self.p1.y() + self.p2.y()) / 2)
        if _dist(pos, self.p1) < tolerance:
            self._grab = "p1"
        elif _dist(pos, self.p2) < tolerance:
            self._grab = "p2"
        elif _distance_to_segment(pos, self.p1, self.p2) < tolerance:
            self._grab = "move"
            self._grab_offset = pos - mid
        else:
            event.ignore()
            return
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._grab is None:
            event.ignore()
            return
        pos = event.pos()
        if self._grab == "p1" and _dist(pos, self.p2) >= MIN_LENGTH:
            self.p1 = self._clamp(QPointF(pos))
        elif self._grab == "p2" and _dist(pos, self.p1) >= MIN_LENGTH:
            self.p2 = self._clamp(QPointF(pos))
        elif self._grab == "move":
            mid = QPointF((self.p1.x() + self.p2.x()) / 2, (self.p1.y() + self.p2.y()) / 2)
            shift = (pos - self._grab_offset) - mid  # Keeps the grab point under the pointer
            self.p1, self.p2 = self.p1 + shift, self.p2 + shift
        self._emit()

    def mouseReleaseEvent(self, event) -> None:
        self._grab = None
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        if self.editable:
            self.length_requested.emit()
            event.accept()
        else:
            event.ignore()

    # --- Helpers ---------------------------------------------------------------------------------
    def _clamp(self, p: QPointF) -> QPointF:
        """Keeps an end on the picture."""
        parent = self.parentItem()
        if parent is None:
            return p
        r = parent.boundingRect()
        return QPointF(min(max(p.x(), r.left()), r.right()), min(max(p.y(), r.top()), r.bottom()))

    def _emit(self) -> None:
        self.update()
        self.changed.emit()


def _dist(a: QPointF, b: QPointF) -> float:
    return math.hypot(a.x() - b.x(), a.y() - b.y())


def _distance_to_segment(p: QPointF, a: QPointF, b: QPointF) -> float:
    dx, dy = b.x() - a.x(), b.y() - a.y()
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return _dist(p, a)
    t = max(0.0, min(1.0, ((p.x() - a.x()) * dx + (p.y() - a.y()) * dy) / length2))
    return math.hypot(p.x() - (a.x() + t * dx), p.y() - (a.y() + t * dy))
