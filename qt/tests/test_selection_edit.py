"""
Fine-tuning a selection and re-running Track:
- a new object is selected at once, so D removes it (a quick redo while marking);
- Move (M): a drag anywhere on the picture moves the selected object;
- the size line: dragging its knob, or [ and ], resizes the selected object about its centre;
- Track runs only objects that are new, moved or resized (or tracked another way), and the
  progress bar fills once over the whole run (every object and pass), never starting again.

    ~/.venvs/phystrackx-qt/bin/python tests/test_selection_edit.py
"""

import math

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from phystrack_qt.video_view import TOOL_BOX, TOOL_MOVE, TOOL_NONE  # noqa: E402
from test_tracking import RADIUS, ball_path, drag, make_clip  # noqa: E402


def _window():
    w = h.window()
    w.load_video(make_clip())
    h.check("proxy is made", h.pump(lambda: w.source.has_proxy, 60))
    return w


def test_d_removes_the_new_object() -> None:
    w = _window()
    w.start_mark()
    drag(w.view, (100, 100), (140, 140))
    drag(w.view, (300, 200), (340, 240))
    h.check("the object just marked is the selected one", w._selected_object() is w.objects[-1])
    QTest.keyClick(w, Qt.Key.Key_D)
    h.check("D removes the object just marked (and only it)", [o.number for o in w.objects] == [1],
            str([o.number for o in w.objects]))
    h.check("...and marking goes on", w.view.tool == TOOL_BOX)
    drag(w.view, (300, 200), (330, 230))
    h.check("the next one is marked as usual", len(w.objects) == 2 and w._selected_object() is w.objects[-1])
    w._dirty = False
    w.close()


def test_move_and_size() -> None:
    w = _window()
    w.start_mark()
    w._add_object(QRectF(100, 100, 40, 40))
    w.view.set_tool(TOOL_NONE)
    obj = w.objects[0]
    h.check("the selected object shows its size line and knob", obj.handle.isVisible() and obj.spoke.isVisible())
    h.check("the knob is on the box's right edge, level with its centre",
            abs(obj.handle.pos().x() - 140) < 0.5 and abs(obj.handle.pos().y() - 120) < 0.5, str(obj.handle.pos()))

    QTest.keyClick(w, Qt.Key.Key_M)
    h.check("M turns Move on", w.move_obj_btn.isChecked() and w.view.tool == TOOL_MOVE)
    (ax, ay), (bx, by) = drag(w.view, (300, 300), (330, 310))   # Far from the box: Move drags from anywhere
    moved = (100 + bx - ax, 100 + by - ay, 40, 40)   # By where the mouse landed (whole view pixels)
    h.check("a drag anywhere moves the selected object by the drag",
            all(abs(a - b) < 0.5 for a, b in zip(obj.marked, moved)), f"{obj.marked}; expected {moved}")
    h.check("...and its knob follows", abs(obj.handle.pos().x() - (moved[0] + 40)) < 1.0, str(obj.handle.pos()))
    QTest.keyClick(w, Qt.Key.Key_Escape)
    h.check("Escape ends Move", not w.move_obj_btn.isChecked() and w.view.tool == TOOL_NONE)

    # The knob: dragged out from the centre, the box grows about its centre
    cx, cy = obj.marked[0] + 20, obj.marked[1] + 20
    _, (bx, by) = drag(w.view, (cx + 20, cy), (cx + 30, cy))
    x, y, bw, bh = obj.marked
    reach = 2 * math.hypot(bx - cx, by - cy)   # The knob goes where the mouse let go (in whole view pixels)
    h.check("dragging the knob out grows the box about its centre",
            abs(bw - reach) < 0.5 and abs(bw - 60) < 4 and bw == bh
            and abs(x + bw / 2 - cx) < 1e-6 and abs(y + bh / 2 - cy) < 1e-6, f"{obj.marked}; to {reach:.2f}")
    before = obj.marked[2]
    QTest.keyClick(w, Qt.Key.Key_BracketLeft)
    QTest.keyClick(w, Qt.Key.Key_BracketLeft)
    h.check("[ shrinks it a pixel at a time (in radius)", abs(before - 4 - obj.marked[2]) < 1e-6,
            f"{before} -> {obj.marked[2]}")
    QTest.keyClick(w, Qt.Key.Key_BracketRight)
    h.check("] grows it, about the same centre", abs(before - 2 - obj.marked[2]) < 1e-6
            and abs(obj.marked[0] + obj.marked[2] / 2 - cx) < 1e-6, str(obj.marked))
    w.object_list.clearSelection()
    h.check("without a selection, Move is off and there is no knob",
            not w.move_obj_btn.isEnabled() and not obj.handle.isVisible())
    w._dirty = False
    w.close()


def test_track_only_what_changed() -> None:
    w = _window()
    x0, y0 = ball_path(0)
    pad = RADIUS + 6
    w.start_mark()
    w._add_object(QRectF(x0 - pad, y0 - pad, 2 * pad, 2 * pad))
    w._add_object(QRectF(400 - pad, 300 - pad, 2 * pad, 2 * pad))   # A second one, on the wall
    w.view.set_tool(TOOL_NONE)
    ball, wall = w.objects

    # Whole clip, two objects: one bar, filling once
    values, texts = [], []
    w.start_track("offline")
    while w.job is not None and h.pump(lambda: w.job is None, 0.02) is False:
        if w.progress.isVisible():
            values.append(w.progress.value())
            texts.append(w.progress.text())
    h.check("the bar went up all through the run, never starting again",
            len(values) > 3 and all(b >= a for a, b in zip(values, values[1:])), str(values[:: max(1, len(values) // 15)]))
    h.check("...from near empty to near full over both objects", values[0] < 300 and values[-1] > 700,
            f"{values[0]} .. {values[-1]}")
    h.check("its text is the frame, as beside the seek bar",
            all(t.startswith("frame ") and t.endswith(f"/ {w.source.fcount - 1}") for t in texts), str(texts[-2:]))
    h.check("both objects are tracked", ball.boxes and wall.boxes)

    # Again, with nothing changed: nothing is tracked
    w.seek.setValue(0)
    h.pump(timeout=0.1)
    kept_ball, kept_wall = dict(ball.boxes), dict(wall.boxes)
    w.start_track("offline")
    h.check("nothing changed: Track does not run", w.job is None)
    h.check("...and says why", "Nothing to track" in w.statusBar().currentMessage(), w.statusBar().currentMessage())

    # Move the wall object: only it is tracked again
    w.object_list.setCurrentRow(1)
    w.move_obj_btn.click()
    drag(w.view, (200, 200), (205, 200))
    w.move_obj_btn.click()
    w.start_track("offline")
    h.check("after moving one object, Track runs", w.job is not None)
    h.pump(lambda: w.job is None, 60)
    h.check("...for that object only: the other keeps its track", ball.boxes == kept_ball)
    h.check("...and the moved one is tracked again from its new place", wall.boxes and wall.boxes != kept_wall)
    h.check("...and the message says so", "1 unchanged object(s) kept their tracks" in w.statusBar().currentMessage(),
            w.statusBar().currentMessage())

    # Another method: both are tracked again
    w.seek.setValue(0)
    h.pump(timeout=0.1)
    w.start_track("blob")
    h.check("another method tracks every object again", w.job is not None and len(w._job_objects) == 2)
    h.pump(lambda: w.job is None, 60)
    w._dirty = False
    w.close()


if __name__ == "__main__":
    h.app()
    for test in (test_d_removes_the_new_object, test_move_and_size, test_track_only_what_changed):
        print(test.__name__)
        test()
    h.finish()
