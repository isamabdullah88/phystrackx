"""
Tracking again part-way keeps the track before that frame. The user's water 270 workflow: the
reflection on the ball shifts the tracked box, they stop, move the box back onto the ball, and
Track again from there; the track before the correction must still be there afterwards.

    ~/.venvs/phystrackx-qt/bin/python tests/test_retrack.py      (PHYSTRACK_QT_SHOW=1 to watch)
"""

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from PySide6.QtCore import QRectF  # noqa: E402

from test_tracking import RADIUS, ball_path, drag, make_clip  # noqa: E402

FIX = 40   # The frame the box is corrected on


def test_retrack_keeps_earlier_frames() -> None:
    # The whole-clip engine sends whole paths; the blob tracker sends frame by frame
    for method in ("offline", "blob"):
        w = h.window()
        w.load_video(make_clip())
        h.pump(lambda: w.source.has_proxy, 60)
        pad = RADIUS + 6
        x0, y0 = ball_path(5)
        w.seek.setValue(5)
        h.pump(timeout=0.1)
        w.start_mark()
        drag(w.view, (x0 - pad, y0 - pad), (x0 + pad, y0 + pad))
        w._cancel_tool()
        w.start_track(method)
        h.check(f"{method}: the first run finishes", h.pump(lambda: w.job is None, 90))
        obj = w.objects[0]
        first = dict(obj.boxes)
        h.check(f"{method}: the first run tracked from frame 5", min(first) == 5 and max(first) > FIX, str(sorted(first)[:3]))

        # The correction: on frame FIX the box is moved onto the ball, then Track from there
        w.seek.setValue(FIX)
        h.pump(timeout=0.1)
        w._show(FIX)
        x, y = ball_path(FIX)
        w._object_dragged(obj, QRectF(x - pad, y - pad, 2 * pad, 2 * pad))
        h.check(f"{method}: the correction is remembered as where to go on from", obj.restart_frame == FIX)
        w.start_track(method)
        h.check(f"{method}: the second run finishes", h.pump(lambda: w.job is None, 90))

        kept = [f for f in range(5, FIX) if f in obj.boxes and obj.boxes[f] == first[f]]
        h.check(f"{method}: the track before the correction is kept", len(kept) == FIX - 5,
                f"{len(kept)} of {FIX - 5} frames")
        h.check(f"{method}: the track goes on from the correction", FIX in obj.boxes and max(obj.boxes) > 80,
                f"last frame {max(obj.boxes)}")
        h.check(f"{method}: the trail is drawn from the first frame", obj._points and obj._points[0][0] == 5)
        w._dirty = False
        w.close()


if __name__ == "__main__":
    h.app()
    test_retrack_keeps_earlier_frames()
    h.finish()
