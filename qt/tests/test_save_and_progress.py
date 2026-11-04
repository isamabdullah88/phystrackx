"""
Saving without questions (project, data, plots next to the video, the full path in the status
bar), the whole-clip run's progress (the bar and "frame n / last", as beside the seek bar) and its
best path so far while it reads, and the tracked-centre marker moving along the track in playback.

    ~/.venvs/phystrackx-qt/bin/python tests/test_save_and_progress.py
"""

import os
import shutil

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

import numpy as np  # noqa: E402
from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import test_tracking as tt  # noqa: E402


def _marked_window(folder: str):
    """A window on a copy of the thrown-ball clip in `folder` (so saved files land there), with the
    ball marked on frame 0."""
    os.makedirs(folder, exist_ok=True)
    clip = os.path.join(folder, "thrown ball.mp4")
    if not os.path.exists(clip):
        shutil.copy(tt.make_clip(), clip)
    w = h.window()
    w.load_video(clip)
    h.check("proxy is made", h.pump(lambda: w.source.has_proxy, 60))
    x0, y0 = tt.ball_path(0)
    pad = tt.RADIUS + 6
    w.start_mark()
    tt.drag(w.view, (x0 - pad, y0 - pad), (x0 + pad, y0 + pad))
    h.pump(timeout=0.1)
    QTest.keyClick(w, Qt.Key.Key_Escape)
    return w, clip


def test_whole_clip_progress_and_marker() -> None:
    w, _ = _marked_window(os.path.join(h.WORK, "progress"))
    seen = {"bar": [], "status": [], "paths": 0}
    w.statusBar().messageChanged.connect(lambda m: seen["status"].append(m))
    w.start_track("offline")
    w.job.path.connect(lambda k, boxes: seen.__setitem__("paths", seen["paths"] + 1))
    while w.job is not None and h.pump(lambda: w.job is None, 0.05) is False:
        if w.progress.isVisible():
            seen["bar"].append((w.progress.value(), w.progress.text()))
    last = w.source.fcount - 1
    h.check("the progress bar was shown while it ran", len(seen["bar"]) > 0)
    texts = [t for _, t in seen["bar"]]
    h.check("the bar says 'frame n / last' of the whole video",
            any(t.startswith("frame ") and t.endswith(f"/ {last}") for t in texts), str(texts[-3:]))
    frames = [m for m in seen["status"] if m.startswith("Reading: frame")]
    h.check("the status says what it is doing and 'frame n / last'", frames and frames[-1].endswith(f"/ {last}"),
            str(frames[-2:]))
    h.check("the best path so far arrives while it runs", seen["paths"] >= 1, str(seen["paths"]))
    h.check("the bar is hidden when done", not w.progress.isVisible())
    obj = w.objects[0]
    errors = tt._errors(obj)
    h.check("the whole clip ends on the ball", len(errors) == tt.FRAMES and np.median(errors) < 2.0,
            f"{len(errors)} frames, median {np.median(errors):.2f}")

    # Playback: the marker sits on the tracked centre of the frame shown, and moves with it
    places = []
    for frame in (10, 40, 70):
        w.seek.setValue(frame)
        h.pump(timeout=0.15)
        c = obj.centre(frame)
        m = obj.marker.pos()
        places.append((m.x(), m.y()))
        h.check(f"frame {frame}: the marker is on the tracked centre",
                obj.marker.isVisible() and abs(m.x() - c[0]) < 0.01 and abs(m.y() - c[1]) < 0.01,
                f"marker ({m.x():.1f}, {m.y():.1f}), tracked ({c[0]:.1f}, {c[1]:.1f})")
        gx, gy = tt.ball_path(frame)
        h.check(f"frame {frame}: ...which is on the ball in the picture", np.hypot(m.x() - gx, m.y() - gy) < 3)
    h.check("the marker moves along the track", len({(round(x), round(y)) for x, y in places}) == 3)
    h.check("the trail is bright up to the frame shown", not obj.travelled.path().isEmpty()
            and obj.travelled.path().length() < obj.trail.path().length())
    w.seek.setValue(0)
    w.toggle_play()
    h.pump(timeout=0.6)
    moved = obj.marker.pos()
    w.toggle_play()
    h.check("playing moves the marker", moved.x() > places[0][0] - 50 and w.seek.value() > 0, str(w.seek.value()))

    # Stop during a whole-clip run: it ends at once, with the best path so far
    w.seek.setValue(0)
    h.pump(timeout=0.1)
    w.object_list.setCurrentRow(0)
    w.clear_object_track()   # (an unchanged, tracked object is not tracked again)
    w.start_track("offline")
    h.pump(lambda: w.progress.value() > 5, 30)
    t0 = __import__("time").perf_counter()
    w.toggle_track()   # Stop
    h.check("stopping a whole-clip run ends it", h.pump(lambda: w.job is None, 10),
            f"{__import__('time').perf_counter() - t0:.2f} s")
    h.check("...and says it stopped", "Stopped after" in w.statusBar().currentMessage(),
            w.statusBar().currentMessage())
    w._dirty = False
    w.close()


def test_saving_without_questions() -> None:
    folder = os.path.join(h.WORK, "saving")
    shutil.rmtree(folder, ignore_errors=True)
    w, clip = _marked_window(folder)
    w.start_track("blob")
    h.pump(lambda: w.job is None, 60)

    # Project: next to the video, named after it, no dialog
    h.check("Save Project saves without asking", w.save_project())
    project = os.path.join(folder, "thrown ball.phystrack")
    h.check("...next to the video, named after it", os.path.isfile(project), str(os.listdir(folder)))
    h.check("...and the status bar shows the full path", project in w.statusBar().currentMessage(),
            w.statusBar().currentMessage())

    # Data: needs the axes (measured from their origin)
    w.start_axis()
    w._place_axes(QPointF(320, 240))
    h.pump(timeout=0.1)
    w.export_data()
    data = os.path.join(folder, "thrown ball_data.csv")
    h.check("Export Data saves without asking, next to the video", os.path.isfile(data), str(os.listdir(folder)))
    h.check("...and the status bar shows the full path", data in w.statusBar().currentMessage(),
            w.statusBar().currentMessage())
    w.export_data()
    h.check("a second export does not overwrite the first",
            os.path.isfile(os.path.join(folder, "thrown ball_data 2.csv")), str(os.listdir(folder)))

    # Plots: Save writes the picture, the data and the fit results
    from phystrack_qt.plot_window import open_plots
    t = np.linspace(0, 3, 91)
    xy = np.column_stack([np.cos(6 * t), 2 + np.exp(-t) * np.cos(9 * t)])
    messages = []
    window = open_plots(1, t, xy, "px", ["y"], clip, on_saved=messages.append)[0]
    paths = window.save_all()
    names = sorted(os.path.basename(p) for p in paths)
    h.check("a plot's Save writes picture, data and fit results next to the video",
            names == ["thrown ball_object1_y.csv", "thrown ball_object1_y.png", "thrown ball_object1_y_fit.txt"]
            and all(os.path.isfile(p) for p in paths), str(names))
    h.check("...and says where, in full", messages and folder in messages[-1] and folder in window.saved_label.text(),
            messages[-1] if messages else "")
    window.toolbar.save_figure()
    h.check("the toolbar's save does the same, without a dialog",
            os.path.isfile(os.path.join(folder, "thrown ball_object1_y 2.png")), str(sorted(os.listdir(folder))))
    window.close()
    w._dirty = False
    w.close()


if __name__ == "__main__":
    h.app()
    print("test_whole_clip_progress_and_marker")
    test_whole_clip_progress_and_marker()
    print("test_saving_without_questions")
    test_saving_without_questions()
    h.finish()
