"""
Auto Object: finds an object's outline from a rough box, for a ball or any other shape, and the
outline waits for the user to accept it before it is tracked. Checked on synthetic pictures with
known shapes, and through the window (box, click, accept, cancel, track).

    ~/.venvs/phystrackx-qt/bin/python tests/test_auto.py
"""

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtCore import QRectF  # noqa: E402

from phystrack_qt.autodetect import find_object, tolerance_to_delta  # noqa: E402
from phystrack_qt.video_view import TOOL_NONE  # noqa: E402
from test_tracking import RADIUS, ball_path, drag, make_clip  # noqa: E402

H, W = 480, 640


def _wall(seed: int = 5) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = np.clip(190 + rng.normal(0, 6, (H, W, 1)), 0, 255).astype(np.uint8).repeat(3, 2)
    return cv2.GaussianBlur(img, (3, 3), 0)


def _mask(points) -> np.ndarray:
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(points).astype(np.int32)], 1)
    return m.astype(bool)


def _iou(a, b) -> float:
    return float((a & b).sum() / max((a | b).sum(), 1))


def test_detector() -> None:
    yy, xx = np.mgrid[:H, :W]
    # A textured ball with a highlight, in a colour the wall does not have
    img = _wall()
    cx, cy, r = 300, 220, 34
    ball = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    img[ball] = (70, 90, 150)
    img[(xx - cx + 10) ** 2 + (yy - cy + 10) ** 2 <= 64] = (230, 235, 240)
    found = find_object(img, (cx - 50, cy - 50, 100, 100))
    h.check("a ball: its outline covers it (IoU over 0.95)", _iou(_mask(found["points"]), ball) > 0.95,
            f"IoU {_iou(_mask(found['points']), ball):.3f}")
    h.check("a ball: its box is the ball's box to within 2 px",
            all(abs(a - b) <= 2 for a, b in zip(found["bbox"], (cx - r, cy - r, 2 * r + 1, 2 * r + 1))),
            str(found["bbox"]))

    # An irregular shape: a rotated L
    img = _wall()
    pts = np.array([[200, 150], [280, 150], [280, 190], [240, 190], [240, 260], [200, 260]], float)
    a = np.radians(25)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    pts = (pts - pts.mean(0)) @ rot.T + [330, 230]
    shape = _mask(pts)
    img[shape] = (60, 110, 160)
    ys, xs = np.nonzero(shape)
    found = find_object(img, (xs.min() - 20, ys.min() - 20, xs.max() - xs.min() + 40, ys.max() - ys.min() + 40))
    h.check("an irregular shape: its outline covers it (IoU over 0.9)",
            _iou(_mask(found["points"]), shape) > 0.9, f"IoU {_iou(_mask(found['points']), shape):.3f}")

    # Grey on grey: no colour of its own, so the box alone finds it
    img = _wall()
    grey = (xx - 300) ** 2 + (yy - 220) ** 2 <= 34 * 34
    img[grey] = (150, 150, 150)
    found = find_object(img, (250, 170, 100, 100))
    h.check("a grey object on grey wall is found from its box",
            _iou(_mask(found["points"]), grey) > 0.9, f"IoU {_iou(_mask(found['points']), grey):.3f}")

    # A box over empty wall is refused, with a reason
    try:
        find_object(_wall(), (100, 100, 80, 80))
        h.check("a box over empty wall is refused", False)
    except ValueError as e:
        h.check("a box over empty wall is refused with a reason", "No object" in str(e), str(e)[:60])


def test_window_flow() -> None:
    w = h.window()
    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)
    x0, y0 = ball_path(0)

    # Auto Object with a loose box around the ball: the outline waits for the user
    w.start_auto()
    pad = RADIUS + 12
    drag(w.view, (x0 - pad, y0 - pad), (x0 + pad, y0 + pad))
    w.view.set_tool(TOOL_NONE)
    h.check("a loose box shows the outline and waits for confirmation",
            w.candidate is not None and w.candidate_panel.isVisible() and len(w.objects) == 0)
    bx, by, bw, bh = w._found["box"]
    h.check("the outline's box is the ball's (within 3 px)",
            abs(bx - (x0 - RADIUS)) <= 3 and abs(by - (y0 - RADIUS)) <= 3 and abs(bw - 2 * RADIUS) <= 3,
            f"box {w._found['box']}")
    w.cancel_candidate()
    h.check("Cancel removes the outline and adds nothing",
            w.candidate is None and not w.candidate_panel.isVisible() and len(w.objects) == 0)

    # A single click on the ball is enough
    w.start_auto()
    drag(w.view, (x0, y0), (x0, y0))
    w.view.set_tool(TOOL_NONE)
    h.check("a click on the object finds it too", w.candidate is not None)
    w.accept_candidate()
    obj = w.objects[-1] if w.objects else None
    h.check("Accept makes it an object, drawn with its outline",
            obj is not None and obj.outline is not None and not obj.circle and w.candidate is None)

    # It is tracked like any other object
    w.toggle_track()
    h.check("the accepted object tracks to the end", h.pump(lambda: w.job is None, 60))
    frames = len(obj.boxes)
    h.check("every frame has a box", frames == 90, f"{frames} frames")
    h.check("the outline is kept with the project's state",
            obj.outline is not None and len(obj.outline) > 4)
    w._dirty = False  # Closing would ask about unsaved changes, and a test has nobody to answer
    w.close()


def test_tolerance_and_edges() -> None:
    deltas = [tolerance_to_delta(t) for t in (0, 25, 50, 75, 100)]
    h.check("higher tolerance selects more: the colour threshold falls as it rises",
            all(a > b for a, b in zip(deltas, deltas[1:])), str([round(d, 1) for d in deltas]))

    w = h.window()
    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)
    x0, y0 = ball_path(0)
    pad = RADIUS + 12
    w.start_auto()
    drag(w.view, (x0 - pad, y0 - pad), (x0 + pad, y0 + pad))
    w.view.set_tool(TOOL_NONE)
    h.check("a box is found at the default tolerance", w.candidate is not None)
    w.tolerance.setValue(90)  # Moving the slider finds it again, once it settles
    h.pump(lambda: False, 0.5)
    h.check("moving the tolerance finds the object again, and keeps the panel",
            w.candidate is not None and w.candidate_panel.isVisible()
            and w.tolerance_label.text().startswith("Tolerance: 90"), w.tolerance_label.text())

    # The selection lines have a black edge: the picture next to the outline has near-black pixels
    image = h.render_picture(w.view)
    bx, by, bw, bh = w._found["box"]
    edge = image[max(by - 2, 0):by + bh + 2, max(bx - 2, 0):bx + bw + 2]
    dark = (edge.max(axis=2) < 60).sum()
    h.check("selection lines have a black edge", dark > 0, f"{dark} dark pixels around the outline")
    w.cancel_candidate()
    w._dirty = False
    w.close()


if __name__ == "__main__":
    h.app()
    for test in (test_detector, test_window_flow, test_tolerance_and_edges):
        print(test.__name__)
        test()
    h.finish()
