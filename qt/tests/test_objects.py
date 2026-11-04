"""
The object manager: the list shows each object, Remove and Clear Track act on the selected one, and
a new object takes the next free number (a removed one's number is not reused by the next).

    ~/.venvs/phystrackx-qt/bin/python tests/test_objects.py
"""

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from PySide6.QtCore import QRectF  # noqa: E402

import numpy as np  # noqa: E402
from PySide6.QtCore import QRectF  # noqa: E402

from phystrack_qt.video_view import TOOL_NONE  # noqa: E402
from test_tracking import RADIUS, ball_path, drag, make_clip  # noqa: E402


def test_object_manager() -> None:
    w = h.window()
    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)

    x0, y0 = ball_path(0)
    pad = RADIUS + 6
    w.start_mark()
    drag(w.view, (x0 - pad, y0 - pad), (x0 + pad, y0 + pad))
    drag(w.view, (400 - pad, 300 - pad), (400 + pad, 300 + pad))  # A second object, on the wall
    w.toggle_track()
    h.check("tracking finishes", h.pump(lambda: w.job is None, 60))
    h.check("the list shows both objects", w.object_list.count() == 2,
            str([w.object_list.item(i).text() for i in range(w.object_list.count())]))
    h.check("a tracked object's row gives its frames",
            "frames 0 to 89" in w.object_list.item(0).text(), w.object_list.item(0).text())

    w.object_list.setCurrentRow(0)
    h.check("Remove is enabled with a selection", w.remove_obj_btn.isEnabled())
    first = w.objects[0]
    w.remove_object()
    h.check("removing takes the object off the view", first.rect.scene() is None)
    h.check("the remaining object keeps its number", [o.number for o in w.objects] == [2],
            str([o.number for o in w.objects]))
    h.check("the list follows", w.object_list.count() == 1)

    w.object_list.setCurrentRow(0)
    w.clear_object_track()
    kept = w.objects[0]
    h.check("Clear Track empties the object's boxes", kept.boxes == {} and kept.trail.path().isEmpty())
    h.check("and its row says it is only marked",
            "marked on frame" in w.object_list.item(0).text(), w.object_list.item(0).text())

    w._add_object(QRectF(100, 100, 40, 40))
    h.check("a new object takes the next free number (3, not 2 again)",
            [o.number for o in w.objects] == [2, 3], str([o.number for o in w.objects]))

    # A circle: dragged corner to corner, as a box is; the circle is inscribed in the square dragged
    w.start_circle()
    centre = (300.0, 200.0)
    # Top-left to bottom-right: a 40 by 35 drag, so a 40 square. Checked against where the mouse landed (it
    # moves in whole view pixels, over a frame pixel each in a small view, as on the Windows runner)
    (ax, ay), (bx, by) = drag(w.view, (280.0, 180.0), (320.0, 215.0))
    w.view.set_tool(TOOL_NONE)
    circle = w.objects[-1]
    r = circle.rect.rect()
    side = max(bx - ax, by - ay)
    h.check("a circle is kept as its bounding square, from the press point (top-left) to the release",
            circle.circle and abs(r.width() - side) < 1.0 and abs(r.height() - side) < 1.0
            and abs(r.x() - ax) < 1.0 and abs(r.y() - ay) < 1.0, f"{r}; mouse {ax:.1f},{ay:.1f} -> {bx:.1f},{by:.1f}")
    h.check("and the circle is centred in that square", abs(r.center().x() - centre[0]) < 1.5
            and abs(r.center().y() - centre[1]) < 1.5, f"{r.center()}")
    h.check("the list calls it a circle", "Circle 4" in w.object_list.item(w.object_list.count() - 1).text(),
            w.object_list.item(w.object_list.count() - 1).text())
    # Drawn as a circle: the corner of its box is not outlined, its edge is (the object's colour, not grey)
    w.object_list.clearSelection()   # A selected object's size knob sits on its right edge
    image = h.render_picture(w.view)
    cx, cy = int(round(r.center().x())), int(round(r.center().y()))

    def coloured(pixels) -> bool:
        pixels = np.asarray(pixels, dtype=int).reshape(-1, 3)
        return bool(((pixels.max(axis=1) - pixels.min(axis=1)) > 60).any())

    # The top-right corner: the object's number is drawn in the top-left one, and a circle's ellipse
    # does not reach either corner
    corner = image[int(r.top()) + 2:int(r.top()) + 5, int(r.right()) - 5:int(r.right()) - 2]
    h.check("the circle's corner is not outlined (only the ellipse is)", not coloured(corner),
            f"largest colour spread in the corner {int(np.ptp(np.asarray(corner, dtype=int), axis=-1).max())}")
    edge = image[cy - 2:cy + 3, int(r.right()) - 3:int(r.right()) + 1]
    h.check("the circle's edge is outlined", coloured(edge))
    w._dirty = False  # Closing would ask about unsaved changes, and a test has nobody to answer
    w.close()


def test_drag_selected_object() -> None:
    """Only the object selected in the list can be dragged on the picture: before tracking, that
    moves where tracking starts; after it, the box on the frame shown. Dragged with the mouse."""
    w = h.window()
    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)
    w.start_mark()
    # A small window (as the Windows runner's: about 4 frame pixels a view pixel), where the 40-pixel box
    # is about 9 view pixels across: the size knob (12) steps aside, so the box can still be dragged
    w._add_object(QRectF(100, 100, 40, 40))
    w._add_object(QRectF(300, 200, 40, 40))
    w.view.set_tool(TOOL_NONE)
    first, second = w.objects
    w.resize(500, 350)
    h.pump(lambda: False, 0.5)

    drag(w.view, (120, 120), (160, 140))  # Not selected: the drag must not move it
    h.check("an unselected object does not move", first.marked == (100, 100, 40, 40), str(first.marked))

    w.object_list.setCurrentRow(0)
    h.check("the selected object is the one that can be dragged",
            first.rect.flags() & first.rect.GraphicsItemFlag.ItemIsMovable and not
            second.rect.flags() & second.rect.GraphicsItemFlag.ItemIsMovable)
    knob = first.handle.pos().x()
    h.check("the size knob steps aside from a box that is small on screen", knob > 140 + 1, f"knob at x {knob:.1f}")
    (ax, ay), (bx, by) = drag(w.view, (120, 120), (160, 140))
    x, y, bw, bh = first.marked
    h.check("dragging the selected object moves its box (before tracking)",   # By where the mouse landed
            abs(x - (100 + bx - ax)) < 0.5 and abs(y - (100 + by - ay)) < 0.5 and bw == 40 and bh == 40,
            f"{first.marked}; mouse {ax:.1f},{ay:.1f} -> {bx:.1f},{by:.1f}")
    h.check("and the other object stays put", second.marked == (300, 200, 40, 40), str(second.marked))
    h.check("moving it marks the project as changed", w._dirty)

    w.toggle_track()
    h.check("tracking finishes", h.pump(lambda: w.job is None, 60))
    h.check("while the selected object is tracked, the object can be dragged on the frame shown",
            first.boxes.get(0) is not None)
    before = first.boxes[0]
    centre = (before[0] + before[2] / 2, before[1] + before[3] / 2)
    w.seek.setValue(0)
    h.check("frame 0 is shown before the drag", h.pump(lambda: w.frame_label.text().startswith("frame 0 "), 5))
    drag(w.view, centre, (centre[0] + 10, centre[1]))
    after = first.boxes[0]
    h.check("the box on frame 0 moves with the drag",
            abs(after[0] - before[0] - 10) < 1.5 and abs(after[1] - before[1]) < 1.5,
            f"{before} -> {after}")
    h.check("other frames keep their boxes", first.boxes[1] != after)
    w._dirty = False
    w.close()


if __name__ == "__main__":
    h.app()
    print("test_object_manager")
    test_object_manager()
    print("test_drag_selected_object")
    test_drag_selected_object()
    h.finish()
