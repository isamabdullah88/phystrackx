"""
Coordinate axes overlay for the Qt spike. A child of the picture item, so its position is the
origin in frame pixels and it follows zoom and pan by itself.

Drag either line to move the axes. Drag the red knob at the end of the x axis, or the green knob at
the end of the y axis, to rotate them. Auto Axis (snap_to) lines them up with a straight line in the
picture, with Undo. The lines run across the whole picture (as the Tk app's do);
the arrow tips, labels and knobs sit at the axes' length. Lines, labels and knobs have a black
outline so they read on any video. Lines are cosmetic (a fixed width on screen at any zoom).
"""

import math

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QPainterPath, QPainterPathStroker,
                           QPen)
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsObject

X_COLOR = QColor("#ff4d4d")
Y_COLOR = QColor("#4dff88")
OUTLINE = QColor("black")  # Behind every line, label and knob, so they stand out from the video
GRAB_WIDTH = 14  # Frame pixels either side of a line that pick it up


def _pen(color: QColor, width: float) -> QPen:
    pen = QPen(color, width)
    pen.setCosmetic(True)  # The same width on screen at any zoom
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _outlined(painter, path: QPainterPath, color: QColor) -> None:
    """Fills a path in colour with a black outline (drawn first, so the fill sits on top)."""
    painter.setPen(_pen(OUTLINE, 4))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(color))
    painter.drawPath(path)


class AxesItem(QGraphicsObject):
    changed = Signal()  # Moved or rotated

    def __init__(self, length: float, parent: QGraphicsItem) -> None:
        super().__init__(parent)
        self.length = length
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        # The x knob turns the x axis to the pointer; the y knob turns the y axis to it (y is x turned
        # 90 degrees counter-clockwise on screen, so its knob adds 90)
        self.handle = _RotateHandle(self, QPointF(length, 0), X_COLOR, turn=0.0)
        self.y_handle = _RotateHandle(self, QPointF(0, -length), Y_COLOR, turn=90.0)
        self._before_snap: tuple[QPointF, float] | None = None  # Origin and rotation before Auto Axis

    def _reach(self) -> float:
        """Half the length of the lines: far enough to reach any corner of the picture from the origin."""
        parent = self.parentItem()
        if parent is None:
            return 4 * self.length
        r = parent.boundingRect()
        return math.hypot(r.width(), r.height()) + self.length

    # Screen convention: x to the right, y up (so drawn towards negative item y)
    def _lines(self) -> tuple[QLineF, QLineF]:
        D = self._reach()
        return QLineF(-D, 0, D, 0), QLineF(0, D, 0, -D)

    def boundingRect(self) -> QRectF:
        D = self._reach()
        return QRectF(-D, -D, 2 * D, 2 * D).adjusted(-40, -40, 40, 40)

    def shape(self) -> QPainterPath:
        """Only the lines pick up the mouse, so a click beside them still pans the picture."""
        path = QPainterPath()
        for line in self._lines():
            path.moveTo(line.p1())
            path.lineTo(line.p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(GRAB_WIDTH * 2)
        return stroker.createStroke(path)

    def paint(self, painter, option, widget=None) -> None:
        x_line, y_line = self._lines()
        L = self.length
        font = QFont("Helvetica", max(12, int(L / 8)), QFont.Weight.Bold)
        ascent = QFontMetricsF(font).ascent()
        tips = {"x": QPointF(L, 0), "y": QPointF(0, -L)}  # Where each label goes: at the axis length
        for line, color, label in ((x_line, X_COLOR, "x"), (y_line, Y_COLOR, "y")):
            painter.setPen(_pen(OUTLINE, 5))  # The black edge under each line
            painter.drawLine(line)
            painter.setPen(_pen(color, 2))
            painter.drawLine(line)
            tip = tips[label]
            text = QPainterPath()
            text.addText(QPointF(tip.x() + 10, tip.y() - 60 + ascent), font, label)
            _outlined(painter, text, color)
        painter.setPen(_pen(OUTLINE, 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(0, 0), 5, 5)
        painter.setPen(_pen(QColor("white"), 2))
        painter.drawEllipse(QPointF(0, 0), 5, 5)

    def angle(self) -> float:
        """The x axis' angle in degrees, counter-clockwise from the picture's x (physics sense)."""
        return -self.rotation()

    # --- Auto Axis (core.autoaxis, through MainWindow) -------------------------------------------
    def snap_to(self, origin, rotation: float) -> None:
        """Moves and turns the axes to the snapped origin and rotation, keeping the old ones for Undo."""
        self._before_snap = (QPointF(self.pos()), self.rotation())
        self.setPos(QPointF(float(origin[0]), float(origin[1])))
        self.setRotation(rotation)

    def can_undo(self) -> bool:
        return self._before_snap is not None

    def undo_snap(self) -> None:
        if self._before_snap is not None:
            (pos, rotation), self._before_snap = self._before_snap, None  # Cleared first: both emit
            self.setPos(pos)
            self.setRotation(rotation)

    def itemChange(self, change, value):
        if change in (QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
                      QGraphicsItem.GraphicsItemChange.ItemRotationHasChanged):
            self.changed.emit()
        return super().itemChange(change, value)


class _RotateHandle(QGraphicsEllipseItem):
    """A round knob at the end of an axis. Dragging it turns the axes so that axis points at the
    pointer. Constant size on screen."""

    RADIUS = 7

    def __init__(self, axes: AxesItem, at: QPointF, colour: QColor, turn: float) -> None:
        r = self.RADIUS
        super().__init__(-r, -r, 2 * r, 2 * r, axes)
        self.axes = axes
        self.turn = turn  # Degrees added to the pointer's angle to get the axes' rotation
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setPos(at)
        self.setBrush(QBrush(colour))
        self.setPen(_pen(OUTLINE, 1.5))
        self.setCursor(Qt.CursorShape.CrossCursor)

    def mousePressEvent(self, event) -> None:
        event.accept()  # Without this the press goes to the axes, which would move instead

    def mouseMoveEvent(self, event) -> None:
        # The angle from the origin to the pointer, in the picture's (parent's) pixels
        parent = self.axes.parentItem()
        p = parent.mapFromScene(event.scenePos())
        o = self.axes.pos()
        self.axes.setRotation(math.degrees(math.atan2(p.y() - o.y(), p.x() - o.x())) + self.turn)
