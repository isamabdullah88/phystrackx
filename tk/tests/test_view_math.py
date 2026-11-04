"""Zoom and pan transform (no window needed)."""

import random

from tests import harness as h
h.setup_env()

from gui.components.view import ViewTransform  # noqa: E402


def test_round_trip_at_random_zooms():
    random.seed(1)
    v = ViewTransform()
    v.configure((50, 40), (400, 600))
    ok = True
    for _ in range(200):
        v.set_zoom(random.uniform(1, 8))
        v.set_fraction(random.random(), random.random())
        p = (random.uniform(0, 1140), random.uniform(0, 641))
        q = v.to_base(*v.to_canvas(*p))
        ok &= abs(q[0] - p[0]) < 1e-6 and abs(q[1] - p[1]) < 1e-6
    h.check("to_base(to_canvas(p)) == p at random zoom and pan", ok)


def test_window_stays_inside_frame():
    v = ViewTransform()
    v.configure((50, 40), (400, 600))
    v.set_zoom(4)
    v.set_fraction(0.5, 0.5)
    x, y, w, h_ = v.window()
    h.check("zoom 4 window is a quarter of the frame", (w, h_) == (100, 150), str((w, h_)))
    h.check("window lies inside the frame", x + w <= 400 and y + h_ <= 600)
    v.set_fraction(-5, 9)
    h.check("pan clamps to the frame edges", v.ox == 0.0 and v.oy == 600 - 600 / 4, str((v.ox, v.oy)))


def test_zoom_keeps_centre():
    v = ViewTransform()
    v.configure((0, 0), (400, 600))
    v.set_zoom(2)
    v.set_fraction(0.3, 0.6)
    before = v.ox + v.size[0] / v.zoom / 2
    v.set_zoom(6)
    after = v.ox + v.size[0] / v.zoom / 2
    h.check("zooming keeps the centre of the view", abs(before - after) < 1e-6 or v.ox == 0.0,
            str((before, after)))

def test_zoom_at_pointer_keeps_the_point_under_it():
    v = ViewTransform()
    v.configure((50, 40), (400, 600))
    v.set_zoom(1.5)
    v.set_fraction(0.5, 0.5)  # Centred, so zooming out does not hit an edge
    for zoom in (2.0, 4.0, 8.0, 1.25):
        point = (300.0, 220.0)
        before = v.to_base(*point)
        v.zoom_at(point[0], point[1], zoom)
        after = v.to_base(*point)
        h.check(f"zoom to {zoom} keeps the point under the pointer",
                abs(before[0] - after[0]) < 1e-6 and abs(before[1] - after[1]) < 1e-6,
                str((before, after)))


def test_pan_moves_the_picture_with_the_fingers():
    v = ViewTransform()
    v.configure((0, 0), (400, 600))
    v.set_zoom(2)
    v.set_fraction(0.5, 0.5)
    ox, oy = v.ox, v.oy
    v.pan(0, 10)  # Fingers move down: the picture moves down, so the window moves up
    h.check("pan down moves the window up by pixels / zoom", abs(v.oy - (oy - 5)) < 1e-9,
            f"{v.oy} from {oy}")
    h.check("pan down leaves x alone", v.ox == ox)
    v.pan(1000, 0)  # Content moves right, so the window moves left to the edge
    h.check("pan clamps at the left edge", v.ox == 0.0, str(v.ox))


if __name__ == "__main__":
    h.run_tests([test_round_trip_at_random_zooms, test_window_stays_inside_frame,
                 test_zoom_keeps_centre,
                 test_zoom_at_pointer_keeps_the_point_under_it, test_pan_moves_the_picture_with_the_fingers])
