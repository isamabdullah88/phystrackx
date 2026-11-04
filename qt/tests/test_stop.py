"""
Stop during a run: the button changes at once, the run stops within a fraction of a second, and the
results from before the stop are kept.

    ~/.venvs/phystrackx-qt/bin/python tests/test_stop.py
"""

import time

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from test_tracking import RADIUS, ball_path, drag, make_clip  # noqa: E402


def test_stop_is_prompt() -> None:
    w = h.window()
    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)
    x0, y0 = ball_path(0)
    pad = RADIUS + 6
    w.start_mark()
    drag(w.view, (x0 - pad, y0 - pad), (x0 + pad, y0 + pad))
    w.toggle_track()
    h.pump(timeout=0.25)  # Let the run get going
    h.check("the run is going", w.job is not None)

    t0 = time.perf_counter()
    w.toggle_track()  # Stop
    h.check("the button says so at once", w.track_btn.text() == "Stopping…", w.track_btn.text())
    h.check("the run ends", h.pump(lambda: w.job is None, 5))
    latency = time.perf_counter() - t0
    h.check("the stop takes effect within 0.3 s", latency < 0.3, f"{latency * 1000:.0f} ms")

    tracked = len(w.objects[0].boxes)
    h.check("results from before the stop are kept, and the run did stop early",
            2 <= tracked < 90, f"{tracked} frames")
    h.check("the button is back to Track", w.track_btn.text() == "Track" and w.track_btn.isEnabled())
    w._dirty = False  # Closing would ask about unsaved changes, and a test has nobody to answer
    w.close()


if __name__ == "__main__":
    h.app()
    print("test_stop_is_prompt")
    test_stop_is_prompt()
    h.finish()
