"""Auto ruler: the ruler's ends snap to the ends of an object, along its left (or right) edge.
Synthetic pictures with known corners (no window needed)."""

import math

import numpy as np

from tests import harness as h
h.setup_env()

import cv2  # noqa: E402
from core.autoruler import snap_ruler  # noqa: E402

BROWN = (60, 110, 160)  # BGR
WHITE = (235, 235, 235)


def _bar(angle_deg=0.0, centre=(220.0, 300.0), half_len=200.0, half_w=20.0, size=(600, 600)):
    """A brown bar with its long axis near vertical. Returns the image and its four corners."""
    th = math.radians(angle_deg)
    u = np.array([math.sin(th), math.cos(th)])   # Along the bar (near vertical)
    n = np.array([math.cos(th), -math.sin(th)])  # Across the bar
    c = np.array(centre)
    corners = [c + a * half_len * u + b * half_w * n for a in (-1, 1) for b in (-1, 1)]
    img = np.full((size[1], size[0], 3), WHITE, np.uint8)
    outline = [corners[0], corners[1], corners[3], corners[2]]  # Walk the perimeter in order
    cv2.fillPoly(img, [np.round(np.array(outline)).astype(np.int32)], BROWN)
    return img, corners, u, n, c


def _edge_corners(corners, left: bool):
    """The two corners of the bar's left (or right) long edge. Corners are made as
    a in (-1, 1) x b in (-1, 1), so the b sign picks the edge across the bar."""
    signs = [(a, b) for a in (-1, 1) for b in (-1, 1)]
    pairs = {b: [p for p, (_, sb) in zip(corners, signs) if sb == b] for b in (-1, 1)}
    mean_x = {b: np.mean([p[0] for p in pairs[b]]) for b in (-1, 1)}
    chosen = min(mean_x, key=mean_x.get) if left else max(mean_x, key=mean_x.get)
    return pairs[chosen]


def _left_corners(corners):
    return _edge_corners(corners, left=True)


def _close_to_any(point, targets, tol):
    return min(math.dist(point, t) for t in targets) <= tol


def test_snaps_to_the_left_edge_of_a_straight_bar():
    img, corners, *_ = _bar()
    left = _left_corners(corners)
    # A rough ruler: inside the bar, a little short of its ends
    q1, q2 = snap_ruler(img, (222, 120), (218, 480), side="left", half_width=20)
    h.check("first end lands on a left corner",
            _close_to_any(q1, left, 2.5), f"{q1} vs {[tuple(np.round(p, 1)) for p in left]}")
    h.check("second end lands on the other left corner",
            _close_to_any(q2, left, 2.5), f"{q2}")
    h.check("the two ends are on different corners",
            min(math.dist(q1, q2) for _ in [0]) > 150, f"{math.dist(q1, q2):.1f}")
    h.check("snapped ruler length is the bar's length",
            abs(math.dist(q1, q2) - 400) < 4, f"{math.dist(q1, q2):.1f} vs 400")


def test_keeps_the_order_of_the_ends():
    img, corners, *_ = _bar()
    left = _left_corners(corners)
    q1, q2 = snap_ruler(img, (218, 480), (222, 120), side="left", half_width=20)
    h.check("the first end stays the first (now at the bottom)",
            math.dist(q1, left[0]) <= 2.5 or math.dist(q1, left[1]) <= 2.5 and
            q1[1] > q2[1], f"{q1} {q2}")


def test_right_side_snaps_to_the_right_edge():
    img, corners, *_ = _bar()
    right = _edge_corners(corners, left=False)
    q1, q2 = snap_ruler(img, (222, 120), (218, 480), side="right", half_width=20)
    h.check("right side ends land on the right corners",
            _close_to_any(q1, right, 2.5) and _close_to_any(q2, right, 2.5), f"{q1} {q2}")


def test_tilted_bar_follows_its_own_edge():
    img, corners, *_ = _bar(angle_deg=8.0)
    left = _left_corners(corners)
    # A rough ruler, drawn along the bar's tilt but a little off it, as a user would place it
    q1, q2 = snap_ruler(img, (196, 125), (243, 475), side="left", half_width=20)
    h.check("tilted bar: ends land on its left corners",
            _close_to_any(q1, left, 3.0) and _close_to_any(q2, left, 3.0),
            f"{q1} {q2} vs {[tuple(np.round(p, 1)) for p in left]}")


def test_no_object_under_the_ruler_is_refused():
    """A ruler on a wall of the same colour: refused, rather than snapping to the whole picture."""
    img = np.full((300, 300, 3), WHITE, np.uint8)
    try:
        snap_ruler(img, (100, 50), (100, 250))
        h.check("a ruler on empty wall is refused", False)
    except ValueError as e:
        h.check("a ruler on empty wall is refused", "No object" in str(e), str(e))


def test_short_ruler_is_refused():
    img = np.full((300, 300, 3), WHITE, np.uint8)
    try:
        snap_ruler(img, (100, 100), (105, 100))
        h.check("a tiny ruler is refused", False)
    except ValueError as e:
        h.check("a tiny ruler is refused", "too short" in str(e), str(e))


def test_segment_anything_snaps_to_the_left_edge():
    """With the Segment Anything model installed, its outline gives the same left-edge corners."""
    import os
    from core import abspath
    path = abspath("models/sam_vit_b_01ec64.pth")
    if not os.path.isfile(path):
        h.say("  (skipped: Segment Anything model not installed)")
        return
    from media.segmenter import SamSegmenter
    img, corners, *_ = _bar(angle_deg=8.0)
    left = _left_corners(corners)
    q1, q2 = snap_ruler(img, (196, 125), (243, 475), side="left", half_width=20,
                        segmenter=SamSegmenter(path))
    h.check("SAM outline: ends land on the bar's left corners",
            _close_to_any(q1, left, 4.0) and _close_to_any(q2, left, 4.0),
            f"{q1} {q2} vs {[tuple(np.round(p, 1)) for p in left]}")


def test_auto_ruler_button_is_quick():
    """The button finds the object on the UI thread in well under a second, moves the ruler, and
    enables Undo."""
    import time
    import customtkinter as ctk
    from gui.components.ruler import ScaleRuler
    img, corners, *_ = _bar()
    root = ctk.CTk()
    root.geometry("700x700")
    canvas = ctk.CTkCanvas(root, width=600, height=600)
    canvas.pack()
    root.update()
    ruler = ScaleRuler(canvas, 600, 600, {}, None)
    ruler.height = 40  # The ruler covers the bar's width
    ruler.frame_source = lambda: img
    ruler.p1, ruler.p2 = [222.0, 120.0], [218.0, 480.0]
    ruler.pack()
    started = time.time()
    ruler.autosnap()
    elapsed = time.time() - started
    h.check("Auto Ruler takes under a second", elapsed < 1.0, f"{elapsed:.2f} s")
    left = _left_corners(corners)
    h.check("the ruler moved onto the bar's left corners",
            _close_to_any(ruler.p1, left, 4.0) and _close_to_any(ruler.p2, left, 4.0),
            f"{ruler.p1} {ruler.p2}")
    h.check("Undo is available after the snap", str(ruler.undobtn.cget("state")) == "normal")
    h.check("the button is back to normal", ruler.autobtn.cget("text") == "Auto Ruler")
    ruler.undo_autosnap()
    h.check("Undo puts the ruler back", ruler.p1 == [222.0, 120.0] and ruler.p2 == [218.0, 480.0])
    ruler.clear()
    root.destroy()


if __name__ == "__main__":
    h.run_tests([test_snaps_to_the_left_edge_of_a_straight_bar, test_keeps_the_order_of_the_ends,
                 test_right_side_snaps_to_the_right_edge, test_tilted_bar_follows_its_own_edge,
                 test_no_object_under_the_ruler_is_refused, test_short_ruler_is_refused,
                 test_segment_anything_snaps_to_the_left_edge, test_auto_ruler_button_is_quick])
