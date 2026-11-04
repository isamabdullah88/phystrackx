"""
End-to-end tracking in the Qt spike: load a clip, mark the ball with a mouse drag, Track, and
compare the tracked centres with where the ball was drawn. Also checks that the box overlay is
drawn on the tracked pixels (through render_picture, not a screenshot).

    ~/.venvs/phystrackx-qt/bin/python tests/test_tracking.py      (PHYSTRACK_QT_SHOW=1 to watch)
"""

import os
import time

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

W, H, FRAMES, FPS, RADIUS = 640, 480, 90, 30, 14


def ball_path(i: int) -> tuple[float, float]:
    """A thrown ball: steady across, falling under gravity."""
    t = i / FPS
    return 80 + 150 * t, 60 + 30 * t + 0.5 * 60 * t * t  # Stays in the frame for all 90 frames


def make_clip() -> str:
    """A ball on a textured wall (so the tracker has a background to tell it from)."""
    path = os.path.join(h.WORK, "thrown_ball.mp4")
    if os.path.isfile(path):
        return path
    rng = np.random.default_rng(1)
    wall = (180 + rng.normal(0, 12, (H, W, 1))).clip(0, 255).astype(np.uint8).repeat(3, 2)
    wall = cv2.GaussianBlur(wall, (5, 5), 0)
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for i in range(FRAMES):
        frame = wall.copy()
        x, y = ball_path(i)
        cv2.circle(frame, (round(x), round(y)), RADIUS, (40, 60, 200), -1, cv2.LINE_AA)
        cv2.circle(frame, (round(x - 4), round(y - 4)), 4, (200, 210, 255), -1, cv2.LINE_AA)
        out.write(frame)
    out.release()
    return path


def drag(view, a, b) -> tuple:
    """A real mouse drag on the view from frame point a to b. Returns the frame points the mouse really
    pressed and let go at: it moves in whole view pixels, so it lands up to half a view pixel off (in a small
    view, over a frame pixel), and a check of where something ended up should go by these."""
    to_view = lambda p: view.mapFromScene(view.picture.mapToScene(*p))  # noqa: E731
    landed = lambda p: view.picture.mapFromScene(view.mapToScene(to_view(p))).toTuple()  # noqa: E731
    vp = view.viewport()
    QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, to_view(a))
    for k in range(1, 6):  # A few moves on the way, as a hand makes
        p = (a[0] + (b[0] - a[0]) * k / 5, a[1] + (b[1] - a[1]) * k / 5)
        QTest.mouseMove(vp, to_view(p))
    QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, to_view(b))
    return landed(a), landed(b)


def test_track_thrown_ball() -> None:
    w = h.window()
    w.load_video(make_clip())
    h.check("proxy is made", h.pump(lambda: w.source.has_proxy, 60))
    h.check("picture is the clip's size", w.view.picture.pixmap().size().toTuple() == (W, H))

    # Mark the ball on frame 0 with the mouse, as a user would
    x0, y0 = ball_path(0)
    pad = RADIUS + 6
    w.start_mark()
    drag(w.view, (x0 - pad, y0 - pad), (x0 + pad, y0 + pad))
    h.pump(timeout=0.1)
    h.check("one object marked by dragging", len(w.objects) == 1, f"{len(w.objects)} objects")
    if not w.objects:
        return
    r = w.objects[0].rect.rect()
    h.check("marked box is where it was dragged",
            abs(r.center().x() - x0) < 1.5 and abs(r.center().y() - y0) < 1.5,
            f"centre ({r.center().x():.1f}, {r.center().y():.1f}) vs ({x0:.1f}, {y0:.1f})")
    QTest.keyClick(w, Qt.Key.Key_Escape)

    t0 = time.perf_counter()
    w.toggle_track()
    h.check("tracking finishes", h.pump(lambda: w.job is None, 60))
    took = time.perf_counter() - t0
    obj = w.objects[0]
    errors = []
    for i in range(FRAMES):
        c = obj.centre(i)
        if c is not None:
            gx, gy = ball_path(i)
            errors.append(np.hypot(c[0] - gx, c[1] - gy))
    errors = np.array(errors)
    print(f"    {len(errors)} frames tracked in {took:.2f} s ({len(errors) / took:.0f} frames/s), "
          f"median error {np.median(errors):.2f} px, worst {errors.max():.2f} px")
    h.check("every frame has a position", len(errors) == FRAMES, f"{len(errors)} of {FRAMES}")
    h.check("median error under 2 px", np.median(errors) < 2.0, f"{np.median(errors):.2f}")
    h.check("worst error under 5 px", errors.max() < 5.0, f"{errors.max():.2f}")
    h.check("trail is drawn", not obj.trail.path().isEmpty())
    h.check("view ends on the last frame", w.seek.value() == FRAMES - 1, str(w.seek.value()))

    # The box overlay is drawn on the tracked box's edge, in frame pixels
    last = obj.boxes[FRAMES - 1]
    image = h.render_picture(w.view)
    x, y = int(round(last[0])), int(round(last[1] + last[3] / 2))  # Middle of the box's left edge
    patch = image[y - 1:y + 2, max(0, x - 1):x + 2].reshape(-1, 3)
    yellow = ((patch[:, 0] > 200) & (patch[:, 1] > 170) & (patch[:, 2] < 90)).any()
    h.check("box overlay is drawn at the tracked box", yellow, f"pixels {patch.tolist()}")

    # Scrubbing back shows the box where the ball was
    w.seek.setValue(30)
    h.pump(timeout=0.2)
    r = obj.rect.rect()
    gx, gy = ball_path(30)
    h.check("scrubbing shows the tracked box for that frame",
            np.hypot(r.center().x() - gx, r.center().y() - gy) < 3,
            f"({r.center().x():.1f}, {r.center().y():.1f}) vs ({gx:.1f}, {gy:.1f})")
    w._dirty = False  # Closing would ask about unsaved changes, and a test has nobody to answer
    w.close()


def _errors(obj) -> np.ndarray:
    out = []
    for i in range(FRAMES):
        c = obj.centre(i)
        if c is not None:
            gx, gy = ball_path(i)
            out.append(np.hypot(c[0] - gx, c[1] - gy))
    return np.array(out)


def test_track_methods() -> None:
    """Every method Track offers follows the thrown ball; the dialog picks the method."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from phystrack_qt.track_methods import METHODS, TrackDialog
    w = h.window()
    w.load_video(make_clip())
    h.check("proxy is made", h.pump(lambda: w.source.has_proxy, 60))
    x0, y0 = ball_path(0)
    pad = RADIUS + 6
    w.start_mark()
    drag(w.view, (x0 - pad, y0 - pad), (x0 + pad, y0 + pad))
    h.pump(timeout=0.1)
    QTest.keyClick(w, Qt.Key.Key_Escape)
    obj = w.objects[0]
    for m in METHODS:
        w.seek.setValue(0)
        h.pump(timeout=0.1)
        t0 = time.perf_counter()
        w.start_track(m.key)
        h.check(f"{m.key}: tracking finishes", h.pump(lambda: w.job is None, 120))
        took = time.perf_counter() - t0
        errors = _errors(obj)
        print(f"    {m.key}: {len(errors)} frames in {took:.2f} s, median error "
              f"{np.median(errors):.2f} px, worst {errors.max():.2f} px")
        h.check(f"{m.key}: every frame has a position", len(errors) == FRAMES, f"{len(errors)} of {FRAMES}")
        h.check(f"{m.key}: median error under 2 px", np.median(errors) < 2.0, f"{np.median(errors):.2f}")
        h.check(f"{m.key}: worst error under 5 px", errors.max() < 5.0, f"{errors.max():.2f}")

    # The dialog: Track asks first; the chosen method runs and is remembered
    w.ask_track_method = True
    w.seek.setValue(0)
    h.pump(timeout=0.1)
    seen = {}

    def answer():
        dialog = QApplication.activeModalWidget()
        if not isinstance(dialog, TrackDialog):
            QTimer.singleShot(50, answer)
            return
        seen["methods"] = list(dialog.radios)
        seen["first"] = dialog.method
        dialog.radios["blob_background"].setChecked(True)
        seen["background on"] = dialog.checks["background"].isChecked()
        dialog.track_btn.click()

    QTimer.singleShot(50, answer)
    w.toggle_track()
    h.check("the dialog lists every method", seen.get("methods") == [m.key for m in METHODS], str(seen))
    h.check("the dialog offers the last method used first", seen.get("first") == "nanotrack", str(seen))
    h.check("the blob method's background option is on by default", seen.get("background on") is True)
    h.check("the chosen method runs", h.pump(lambda: w.job is None, 120) and w.track_method == "blob_background",
            w.track_method)
    h.check("the run is on the ball", np.median(_errors(obj)) < 2.0)
    h.check("the status names the method", "Blob tracker with still background" in w.statusBar().currentMessage(),
            w.statusBar().currentMessage())
    w._dirty = False
    w.close()


if __name__ == "__main__":
    h.app()
    print("test_track_thrown_ball")
    test_track_thrown_ball()
    print("test_track_methods")
    test_track_methods()
    h.finish()
