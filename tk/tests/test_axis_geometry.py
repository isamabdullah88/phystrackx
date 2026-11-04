"""Axis lines keep their direction and stay visible when the view is zoomed (no window needed).

The visible part of an axis is the stretch of its line inside the canvas. The line keeps its
direction at every zoom, and it is still drawn when the origin is off the visible view.
"""

import math

from tests import harness as h
h.setup_env()

from gui.components.axes import Axes  # noqa: E402
from gui.components.view import ViewTransform  # noqa: E402

W, H = 400, 600


def _collinear(s, d, p) -> bool:
    """True if p lies on the line through s along d."""
    vx, vy = p[0] - s[0], p[1] - s[1]
    cross = vx * d[1] - vy * d[0]
    return abs(cross) < 1e-6 * max(1.0, math.hypot(*d) * math.hypot(vx, vy))


def _on_canvas(p) -> bool:
    return -1e-6 <= p[0] <= W + 1e-6 and -1e-6 <= p[1] <= H + 1e-6


def test_origin_on_canvas_starts_there():
    s, d = (100.0, 300.0), (1.0, -0.2)
    near, far = Axes.visible_segment(*s, *d, W, H)
    h.check("near end is the origin", near == s, str(near))
    h.check("far end is on the axis line", _collinear(s, d, far), str(far))
    h.check("far end is on the canvas edge", _on_canvas(far) and
            min(far[0], W - far[0], far[1], H - far[1]) < 1e-6, str(far))


def test_direction_is_the_same_at_every_zoom():
    """Zoom maps the origin to the screen and scales the axis, but must not change its angle."""
    base_origin = (150.0, 420.0)
    d = (0.6, -0.8)  # Unit direction, in screen pixels
    angles = []
    for zoom in (1.0, 2.0, 4.0, 8.0):
        v = ViewTransform()
        v.configure((0, 0), (W, H))
        v.set_zoom(zoom)
        s = v.to_canvas(*base_origin)
        near, far = Axes.visible_segment(s[0], s[1], *d, W, H)
        angles.append(math.degrees(math.atan2(far[1] - near[1], far[0] - near[0])))
    spread = max(angles) - min(angles)
    h.check("the angle is the same at every zoom", spread < 1e-6, f"angles {angles}")


def test_origin_off_the_view_still_shows_the_axis():
    """Zoomed to a part away from the origin: the line still crosses the view, so it is drawn."""
    seg = Axes.visible_segment(-100.0, 300.0, 1.0, 0.0, W, H)  # Horizontal line y = 300
    h.check("line crossing the view is visible", seg is not None, str(seg))
    if seg is not None:
        (x0, y0), (x1, y1) = seg
        h.check("visible part runs across the view", abs(x0) < 1e-6 and abs(x1 - W) < 1e-6
                and abs(y0 - 300) < 1e-6 and abs(y1 - 300) < 1e-6, str(seg))


def test_line_that_misses_the_view_is_not_drawn():
    seg = Axes.visible_segment(-300.0, 900.0, 1.0, 0.0, W, H)  # Horizontal line y = 900
    h.check("line outside the view gives nothing to draw", seg is None, str(seg))


if __name__ == "__main__":
    h.run_tests([test_origin_on_canvas_starts_there, test_direction_is_the_same_at_every_zoom,
                 test_origin_off_the_view_still_shows_the_axis,
                 test_line_that_misses_the_view_is_not_drawn])
