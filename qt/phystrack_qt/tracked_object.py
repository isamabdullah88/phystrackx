"""
A marked object for the Qt spike: its box on the picture, its tracked boxes by frame, and the trail
of its centre. All in proxy pixels, as children of the picture item, so they follow zoom and pan.
On a tracked frame, a dot marks the tracked centre and the trail is drawn bright up to it, so
playing or scrubbing shows the track moving along against the ball in the picture.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem, QGraphicsPathItem,
                               QGraphicsRectItem, QGraphicsSimpleTextItem)

COLORS = ["#ffd400", "#00e5ff", "#ff6bd6", "#7cff4d", "#ff9f1a"]
OUTLINE = QColor("black")  # Under every selection line, so it reads on any video


def _pen(color: str, width: float, style=Qt.PenStyle.SolidLine) -> QPen:
    pen = QPen(QColor(color), width, style)
    pen.setCosmetic(True)  # The same width on screen at any zoom
    return pen


class OutlineItem(QGraphicsRectItem):
    """A box; with `circle` set, the ellipse inscribed in the box (the box is the bounding square of a
    circle, which is what the tracker is given, as the Tk app does for balls); or with `outline` set,
    the object's own outline, drawn in its box. The outline is kept as fractions of the box, so it
    follows the box when the tracker moves or resizes it."""

    def __init__(self, box: QRectF, parent: QGraphicsItem | None = None, circle: bool = False,
                 outline: list | None = None) -> None:
        super().__init__(box, parent)
        self.circle = circle
        self.outline = outline
        self.on_moved = None  # Called with the new box after the user drags it (see TrackedObject)

    def _path(self) -> QPainterPath:
        r = self.rect()
        path = QPainterPath()
        if self.outline:
            polygon = QPolygonF([QPointF(r.x() + u * r.width(), r.y() + v * r.height())
                                 for u, v in self.outline])
            path.addPolygon(polygon)
            path.closeSubpath()
        elif self.circle:
            path.addEllipse(r)
        else:
            path.addRect(r)
        return path

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if not self.pos().isNull():  # Dragged: bake the move into the box, so it is the box's own
            box = self.rect().translated(self.pos())
            self.setPos(QPointF(0, 0))
            self.setRect(box)
            if self.on_moved is not None:
                self.on_moved(box)

    def paint(self, painter, option, widget=None) -> None:
        # A black edge under the line, so it reads on any video; then the line in its own colour
        path = self._path()
        edge = QPen(OUTLINE, self.pen().widthF() + 2.5)
        edge.setCosmetic(True)
        for pen in (edge, self.pen()):
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)


class SizeHandle(QGraphicsEllipseItem):
    """The knob at the end of a selected object's size line (from its centre to its right edge):
    dragging it grows or shrinks the object about its centre. The same size on screen at any zoom."""

    is_handle = True   # The view's Move tool lets it be dragged as itself

    def __init__(self, parent: QGraphicsItem, on_drag) -> None:
        super().__init__(-6, -6, 12, 12, parent)
        self.on_drag = on_drag   # Called as on_drag(point in frame pixels, done)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setToolTip("Drag to make the selection bigger or smaller")

    def _point(self, event) -> QPointF:
        return self.parentItem().mapFromScene(event.scenePos())

    def mousePressEvent(self, event) -> None:
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        self.on_drag(self._point(event), False)

    def mouseReleaseEvent(self, event) -> None:
        self.on_drag(self._point(event), True)


class TrackedObject:
    def __init__(self, number: int, box: QRectF, frame: int, picture: QGraphicsItem,
                 circle: bool = False, outline: list | None = None) -> None:
        self.number = number
        self.circle = circle  # Drawn as the ellipse in its box; tracked as the box
        self.outline = outline  # Drawn as this outline (fractions of the box), if found automatically
        self.color = COLORS[(number - 1) % len(COLORS)]
        self.marked = (box.x(), box.y(), box.width(), box.height())  # Where tracking starts
        self.marked_frame = frame
        self.boxes: dict[int, tuple | None] = {}  # Frame -> tracked box, or None where lost
        self.changed = True       # New, moved or resized since it was last tracked (Track runs it again)
        self.tracked_with = None  # (method, settings, start, end) of its last run
        self.restart_frame = None  # Where the user corrected its tracked box (tracking goes on from there)

        self.selected = False  # Chosen in the object list: drawn thicker, and it can be dragged
        self.on_move = None  # Called as on_move(obj, box) when the user drags the box
        self.rect = OutlineItem(box, picture, circle, outline)
        self.rect.on_moved = self._dragged
        self.rect.setPen(_pen(self.color, 2))
        self.rect.setZValue(2)
        self.label = QGraphicsSimpleTextItem(str(number), self.rect)
        self.label.setBrush(QColor(self.color))
        self.label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.trail_edge = QGraphicsPathItem(picture)  # The black edge under the trail
        self.trail_edge.setPen(_pen(OUTLINE, 3.5))
        self.trail_edge.setZValue(0.9)
        self.trail = QGraphicsPathItem(picture)
        trail = QColor(self.color)
        trail.setAlpha(110)   # The whole track, faint; the part up to the frame shown is bright
        self.trail.setPen(_pen(trail.name(QColor.NameFormat.HexArgb), 1.5))
        self.trail.setZValue(1)
        self.travelled = QGraphicsPathItem(picture)
        self.travelled.setPen(_pen(self.color, 2))
        self.travelled.setZValue(1.1)
        self.marker = QGraphicsEllipseItem(-4.5, -4.5, 9, 9, picture)   # The tracked centre, same size at any zoom
        self.marker.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.marker.setBrush(QColor(self.color))
        self.marker.setPen(_pen("black", 1.5))
        self.marker.setZValue(3)
        self.marker.hide()
        self._points: list = []   # (frame, centre) along the track, in order (draw_trail)
        # The size line and its knob, on the selected object (set_selected)
        self.spoke = QGraphicsLineItem(picture)
        self.spoke.setPen(_pen(self.color, 1.5, Qt.PenStyle.DashLine))
        self.spoke.setZValue(3)
        self.handle = SizeHandle(picture, self._resize_to)
        self.handle.setBrush(QColor("white"))
        self.handle.setPen(_pen(self.color, 2.5))
        self.handle.setZValue(4)
        self._sizing = False
        self._place_label()
        self.show_handle(False)

    def set_selected(self, selected: bool, movable: bool) -> None:
        """Selected: a thicker line, and (if movable) the box can be dragged on the picture."""
        self.selected = selected
        self.rect.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, movable)
        self.rect.setCursor(Qt.CursorShape.SizeAllCursor if movable else Qt.CursorShape.ArrowCursor)
        self._style_rect(lost=False)
        self.show_handle(selected and movable)

    def show_handle(self, on: bool) -> None:
        """The size line and knob (on the selected object, while the box is shown)."""
        self._handle_on = on
        visible = on and self.rect.isVisible()
        self.spoke.setVisible(visible)
        self.handle.setVisible(visible)
        if visible:
            self._place_handle()

    def _place_handle(self) -> None:
        r = self.rect.rect().translated(self.rect.pos())
        c = r.center()
        self.spoke.setLine(c.x(), c.y(), r.right(), c.y())
        self.handle.setPos(r.right(), c.y())

    def _resize_to(self, point: QPointF, done: bool) -> None:
        """The knob was dragged to `point`: the box keeps its centre and shape, and its half-width
        becomes the distance from the centre (at least 2 px)."""
        self.resize_by(None, done, point)

    def resize_by(self, pixels: float | None, done: bool = True, point: QPointF | None = None) -> None:
        """Grows (or shrinks, if negative) the box's half-width by `pixels` about its centre, keeping
        its shape; or makes it reach `point` (the size knob). When `done`, the new box is the
        object's (on_move), as a drag of the box is."""
        r = self.rect.rect()
        c = r.center()
        half = r.width() / 2
        new_half = half + pixels if point is None else math.hypot(point.x() - c.x(), point.y() - c.y())
        k = max(2.0, new_half) / max(half, 1e-6)
        box = QRectF(c.x() - r.width() * k / 2, c.y() - r.height() * k / 2, r.width() * k, r.height() * k)
        self.rect.setRect(box)
        self._place_label()
        if done:
            self._dragged(box)

    def _dragged(self, box: QRectF) -> None:
        if self.on_move is not None:
            self.on_move(self, box)

    def _style_rect(self, lost: bool) -> None:
        width = 4 if self.selected else 2
        self.rect.setPen(_pen(self.color, width, Qt.PenStyle.DotLine if lost else
                              Qt.PenStyle.SolidLine))

    def _place_label(self) -> None:
        """Inside the box's top-left corner (the label keeps its size on screen); and the size line
        on the box's centre."""
        r = self.rect.rect()
        self.label.setPos(r.x() + 1, r.y() + 1)
        if getattr(self, "_handle_on", False):
            self.show_handle(True)

    def clear_track(self) -> None:
        self.boxes.clear()
        self._points = []
        self.trail.setPath(QPainterPath())
        self.trail_edge.setPath(QPainterPath())
        self.travelled.setPath(QPainterPath())
        self.marker.hide()

    def keep_before(self, frame: int, first: int = 0) -> None:
        """Tracking again from `frame`: the track from there on goes, what came before stays (a
        correction part-way, then Track, must not lose the good start of the track), from `first`
        on (the trim's start: a track from before a later trim is not kept)."""
        self.boxes = {f: b for f, b in self.boxes.items() if first <= f < frame}
        self.draw_trail()
        self.travelled.setPath(QPainterPath())
        self.marker.hide()

    def add(self, frame: int, box) -> None:
        """A tracked result. The trail is rebuilt from all frames, in order, by draw_trail."""
        self.boxes[frame] = box

    def draw_trail(self) -> None:
        self._points = [(frame, None if (box := self.boxes[frame]) is None else
                         QPointF(box[0] + box[2] / 2, box[1] + box[3] / 2)) for frame in sorted(self.boxes)]
        path = self._path_to(None)
        self.trail.setPath(path)
        self.trail_edge.setPath(path)

    def _path_to(self, last: int | None) -> QPainterPath:
        """The trail's path through the tracked centres, up to frame `last` (all if None)."""
        path = QPainterPath()
        pen_down = False
        for frame, centre in self._points:
            if last is not None and frame > last:
                break
            if centre is None:
                pen_down = False  # A gap where the object was lost
                continue
            if pen_down:
                path.lineTo(centre)
            else:
                path.moveTo(centre)
                pen_down = True
        return path

    def show_frame(self, frame: int) -> None:
        """The box where the object is in this frame: tracked, or as marked before tracking."""
        if self.boxes:
            box = self.boxes.get(frame)
            lost = frame in self.boxes and box is None
            self.rect.setVisible(box is not None)
            if box is not None:
                self.rect.setRect(QRectF(*box))
                self.marker.setPos(box[0] + box[2] / 2, box[1] + box[3] / 2)
            self.marker.setVisible(box is not None)
            self.travelled.setPath(self._path_to(frame) if self._points else QPainterPath())
            self._style_rect(lost)
        else:
            self.rect.setVisible(True)
            self.rect.setRect(QRectF(*self.marked))
            self.marker.hide()
            self.travelled.setPath(QPainterPath())
        self._place_label()

    def centre(self, frame: int) -> tuple[float, float] | None:
        box = self.boxes.get(frame)
        return None if box is None else (box[0] + box[2] / 2, box[1] + box[3] / 2)

    def remove(self) -> None:
        scene = self.rect.scene()
        if scene is not None:
            scene.removeItem(self.rect)
            scene.removeItem(self.trail)
            scene.removeItem(self.trail_edge)
            scene.removeItem(self.travelled)
            scene.removeItem(self.marker)
            scene.removeItem(self.spoke)
            scene.removeItem(self.handle)
