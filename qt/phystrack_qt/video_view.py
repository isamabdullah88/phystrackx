"""
The video view of the Qt spike: a QGraphicsView drawn with OpenGL.

Scene coordinates are frame pixels: the picture item sits at (0, 0) unscaled, and the view's
transform does all zooming and panning on the GPU. Overlays are children of the picture item, so
they stay on the same frame pixels at any zoom without coordinate code of their own.
"""

import math
import os

import numpy as np
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import (QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QWidget)

from .tracked_object import OutlineItem

MAX_ZOOM = 50.0  # Times the fitted size, as in the Tk app


# "cpu" draws without OpenGL. Tests use it: Qt cannot capture an OpenGL view on macOS (grab() gives
# a black or garbage picture), and the offscreen platform (no window) has no OpenGL at all.
VIEWPORT = os.environ.get("PHYSTRACK_QT_VIEWPORT", "gl")

TOOL_NONE, TOOL_CLICK, TOOL_BOX, TOOL_CIRCLE, TOOL_AUTO = "none", "click", "box", "circle", "auto"
TOOL_MOVE = "move"   # A drag anywhere on the picture moves the selected object (dragged)
KIND = {TOOL_BOX: "box", TOOL_CIRCLE: "circle", TOOL_AUTO: "auto"}


class VideoView(QGraphicsView):
    clicked = Signal(QPointF)     # A click on the picture for TOOL_CLICK, in frame pixels
    box_drawn = Signal(QRectF, str)   # A box dragged out for a marking tool, in frame pixels, and its kind:
                                      # "box", "circle" (the box is its bounding square) or "auto"
    zoom_changed = Signal(float)  # Zoom relative to the fitted size
    dragged = Signal(QPointF, QPointF, bool)  # TOOL_MOVE: where the drag started and where it is now,
                                              # in frame pixels, and whether it has ended

    def __init__(self) -> None:
        super().__init__()
        # GPU drawing: about 9 ms a frame, vs about 26 ms on CPU
        self.setViewport(QWidget() if VIEWPORT == "cpu" else QOpenGLWidget())
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(QColor("#4d535c"))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)

        self.picture = QGraphicsPixmapItem()
        self.picture.setShapeMode(QGraphicsPixmapItem.ShapeMode.BoundingRectShape)
        self.scene().addItem(self.picture)
        self._current_frame: np.ndarray | None = None
        self._current_frame_index: int | None = None
        self._fitted = True    # Follows the window's size until the user zooms
        self.tool = TOOL_NONE
        self._box_start: QPointF | None = None
        self._rubber: QGraphicsRectItem | None = None
        self._move_start: QPointF | None = None

    # --- Picture ---------------------------------------------------------------------------------
    def show_frame(self, frame: np.ndarray, index: int | None = None) -> None:
        """Shows a BGR frame. The first one (or a new size) also fits the view to it."""
        self._current_frame = np.array(frame, copy=True)
        self._current_frame_index = index
        h, w = frame.shape[:2]
        image = QImage(frame.data, w, h, frame.strides[0], QImage.Format.Format_BGR888)
        new_size = self.picture.pixmap().size().toTuple() != (w, h)
        self.picture.setPixmap(QPixmap.fromImage(image))  # Copies, so frame may be reused after
        if new_size:
            self.scene().setSceneRect(self.picture.boundingRect())
            self.fit()

    @property
    def current_frame(self) -> np.ndarray | None:
        """The BGR pixels most recently handed to the view, independent of its OpenGL viewport."""
        return self._current_frame

    @property
    def current_frame_index(self) -> int | None:
        """The index associated with the pixels most recently handed to the view."""
        return self._current_frame_index

    # --- Zoom and pan ----------------------------------------------------------------------------
    def fit(self) -> None:
        """The whole picture in the view (double-click, or a new video)."""
        if self.picture.pixmap().isNull():
            return
        self.fitInView(self.picture, Qt.AspectRatioMode.KeepAspectRatio)
        self._fitted = True
        self._update_sharpness()

    def _fit_scale(self) -> float:
        rect = self.picture.boundingRect()
        if rect.isEmpty():
            return 1.0
        return min(self.viewport().width() / rect.width(), self.viewport().height() / rect.height())

    def zoom(self) -> float:
        return self.transform().m11() / self._fit_scale()

    def zoom_by(self, factor: float) -> None:
        current = self.zoom()
        factor = max(1.0, min(MAX_ZOOM, current * factor)) / current
        if abs(factor - 1) < 1e-6:
            return
        self.scale(factor, factor)
        self._fitted = self.zoom() <= 1.0001
        self._update_sharpness()

    def _update_sharpness(self) -> None:
        """Enlarged pixels stay sharp (as in the Tk app); a shrunk picture is smoothed."""
        enlarged = self.transform().m11() * self.devicePixelRatioF() > 1
        self.picture.setTransformationMode(Qt.TransformationMode.FastTransformation if enlarged
                                           else Qt.TransformationMode.SmoothTransformation)
        self.zoom_changed.emit(self.zoom())

    def wheelEvent(self, event) -> None:
        # Cmd (Ctrl on other systems) + scroll zooms; plain scroll pans, as on a trackpad
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_by(1.0015 ** event.angleDelta().y())
        else:
            super().wheelEvent(event)

    def viewportEvent(self, event) -> bool:
        if event.type() == QEvent.Type.NativeGesture and \
                event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
            self.zoom_by(1 + event.value())  # Trackpad pinch
            return True
        return super().viewportEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fitted:
            self.fit()

    def mouseDoubleClickEvent(self, event) -> None:
        if self.itemAt(event.position().toPoint()) in (self.picture, None):
            self.fit()
        else:
            super().mouseDoubleClickEvent(event)

    # --- Tools: a click, or a box dragged out --------------------------------------------------
    def set_tool(self, tool: str) -> None:
        """While a tool waits for the mouse, dragging does not pan the picture."""
        self.tool = tool
        on = tool != TOOL_NONE
        self.setDragMode(QGraphicsView.DragMode.NoDrag if on else
                         QGraphicsView.DragMode.ScrollHandDrag)
        self.viewport().setCursor(Qt.CursorShape.SizeAllCursor if tool == TOOL_MOVE else
                                  Qt.CursorShape.CrossCursor if on else Qt.CursorShape.OpenHandCursor)

    def _frame_point(self, event) -> QPointF:
        return self.picture.mapFromScene(self.mapToScene(event.position().toPoint()))

    def mousePressEvent(self, event) -> None:
        if self.tool != TOOL_NONE and event.button() == Qt.MouseButton.LeftButton:
            point = self._frame_point(event)
            if self.tool == TOOL_MOVE and getattr(self.itemAt(event.position().toPoint()), "is_handle", False):
                super().mousePressEvent(event)   # The size handle is dragged as itself
                return
            if self.picture.contains(point):
                if self.tool == TOOL_MOVE:
                    self._move_start = point
                    self.dragged.emit(point, point, False)
                elif self.tool == TOOL_CLICK:
                    self.clicked.emit(point)
                else:
                    self._box_start = point
                    self._rubber = OutlineItem(QRectF(point, point), self.picture,
                                               circle=self.tool == TOOL_CIRCLE)
                    pen = QPen(QColor("#ffd400"), 2, Qt.PenStyle.DashLine)
                    pen.setCosmetic(True)
                    self._rubber.setPen(pen)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._move_start is not None:
            self.dragged.emit(self._move_start, self._frame_point(event), False)
            return
        if self._rubber is not None:
            self._rubber.setRect(self._box_rect(event))
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._move_start is not None:
            start, self._move_start = self._move_start, None
            self.dragged.emit(start, self._frame_point(event), True)
            return
        if self._rubber is not None:
            rect = self._box_rect(event)
            start, tool = self._box_start, self.tool
            self.scene().removeItem(self._rubber)
            self._rubber = self._box_start = None
            if rect.width() >= 4 and rect.height() >= 4:
                self.box_drawn.emit(rect, KIND[tool])
            elif tool == TOOL_AUTO:  # A click alone: a box of a typical object's size around it
                self.box_drawn.emit(self._default_box(start), KIND[tool])
            return
        super().mouseReleaseEvent(event)

    def _default_box(self, centre: QPointF) -> QRectF:
        half = 0.08 * min(self.picture.boundingRect().width(), self.picture.boundingRect().height())
        box = QRectF(centre.x() - half, centre.y() - half, 2 * half, 2 * half)
        return box.intersected(self.picture.boundingRect())

    def _box_rect(self, event) -> QRectF:
        """The dragged box, kept inside the picture. A circle is dragged corner to corner, as a box is,
        and is the circle inscribed in the square that the drag makes: the square's side is the drag's
        longer side, grown from the press point in the drag's direction, and shrunk if it would leave
        the picture."""
        if self.tool == TOOL_CIRCLE:
            a = self._box_start
            p = self._frame_point(event)
            picture = self.picture.boundingRect()
            right, down = p.x() >= a.x(), p.y() >= a.y()
            room_x = picture.right() - a.x() if right else a.x() - picture.left()
            room_y = picture.bottom() - a.y() if down else a.y() - picture.top()
            side = min(max(abs(p.x() - a.x()), abs(p.y() - a.y())), room_x, room_y)
            x = a.x() if right else a.x() - side
            y = a.y() if down else a.y() - side
            return QRectF(x, y, side, side)
        rect = QRectF(self._box_start, self._frame_point(event)).normalized()
        return rect.intersected(self.picture.boundingRect())
