"""
Projects: a whole setup (trim, axes, ruler with its length, a tracked object) is saved, and opened
again to exactly the same state. A file from another app (or a changed format) is refused.

    ~/.venvs/phystrackx-qt/bin/python tests/test_project.py
"""

import json
import os

import harness as h  # noqa: F401  (sets up Qt before PySide6 is imported)

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from phystrack_qt import project_file  # noqa: E402
from test_tracking import RADIUS, ball_path, drag, make_clip  # noqa: E402


def test_project_round_trip() -> None:
    clip = make_clip()
    w = h.window()
    w.load_video(clip)
    h.pump(lambda: w.source.has_proxy, 60)

    w._trim_marks = [10, 70]
    w._apply_trim()
    w.start_axis()
    w._place_axes(QPointF(100, 90))
    w.axes.setRotation(20)
    w.start_ruler()
    w.ruler.set_length(50, "cm")
    w.seek.setValue(10)
    h.pump(timeout=0.1)
    x0, y0 = ball_path(10)
    pad = RADIUS + 6
    w.start_mark()
    drag(w.view, (x0 - pad, y0 - pad), (x0 + pad, y0 + pad))
    QTest.keyClick(w, Qt.Key.Key_Escape)
    w.toggle_track()
    h.check("tracking finishes", h.pump(lambda: w.job is None, 60))
    h.check("the project has unsaved changes before saving", w._dirty)

    path = os.path.join(h.WORK, "round_trip.phystrack")
    h.check("saving writes the project", w.save_project_file(path) and os.path.isfile(path))
    h.check("saving clears the unsaved changes", not w._dirty)
    state = w._project_state()

    w2 = h.window()
    h.check("opening the project loads its video", w2.open_project_file(path))
    h.pump(lambda: w2.source.has_proxy, 60)
    again = w2._project_state()
    h.check("the reopened setup is the saved one", again == state,
            "" if again == state else f"differs in {[k for k in state if state[k] != again[k]]}")
    h.check("the trim is back", w2.trim == (10, 70), str(w2.trim))
    h.check("the ruler keeps its length and unit",
            w2.ruler is not None and w2.ruler.real_length == 50 and w2.ruler.unit == "cm")
    h.check("the tracked boxes are back", len(w2.objects) == 1 and
            len(w2.objects[0].boxes) == len(w.objects[0].boxes))
    h.check("opening does not count as a change", not w2._dirty)
    h.check("the ruler is not being edited when the project opens",
            w2.ruler is not None and not w2.ruler.editable)

    for window in (w, w2):
        window._dirty = False  # Closing would ask about unsaved changes, and a test has nobody to answer
        window.close()


def test_other_formats_refused() -> None:
    """Tk-app projects are imported (test_migration.py); other formats and newer versions are refused."""
    folder = h.WORK
    other = os.path.join(folder, "other.phystrack")
    with open(other, "w", encoding="utf-8") as f:
        json.dump({"format": "someone-else", "version": 2, "video": make_clip()}, f)
    try:
        project_file.load(other)
        h.check("another app's project is refused", False)
    except ValueError as e:
        h.check("another app's project is refused with a message", "not a project" in str(e), str(e))

    future = os.path.join(folder, "future.phystrack")
    with open(future, "w", encoding="utf-8") as f:
        json.dump({"format": "phystrackx-qt", "version": 9, "video": make_clip()}, f)
    try:
        project_file.load(future)
        h.check("a newer project version is refused", False)
    except ValueError as e:
        h.check("a newer project version is refused with a message", "version" in str(e), str(e))


def test_video_start_and_end() -> None:
    """The sidebar's Video Start and Video End go to the trimmed start and end, or to the first and
    last frame when there is no trim."""
    w = h.window()
    w.load_video(make_clip())
    h.pump(lambda: w.source.has_proxy, 60)
    last = w.source.fcount - 1
    w.go_end()
    h.check("Video End with no trim goes to the last frame", w.seek.value() == last, str(w.seek.value()))
    w.go_start()
    h.check("Video Start with no trim goes to the first frame", w.seek.value() == 0)
    w._trim_marks = [10, 70]
    w._apply_trim()
    w.go_end()
    h.check("Video End goes to the trimmed end", w.seek.value() == 70, str(w.seek.value()))
    w.go_start()
    h.check("Video Start goes to the trimmed start", w.seek.value() == 10, str(w.seek.value()))
    h.check("both buttons are enabled once a video is open",
            w.start_btn.isEnabled() and w.end_btn.isEnabled())
    w._dirty = False
    w.close()


def test_import_video_or_project() -> None:
    """Import Video starts in the open video's folder, and takes a project as well as a video."""
    clip = make_clip()
    w = h.window()
    w.load_video(clip)
    h.pump(lambda: w.source.has_proxy, 60)
    project = os.path.join(h.WORK, "import_test.phystrack")
    h.check("a project is saved for the import test", w.save_project_file(project))
    w._dirty = False
    w.close()

    import phystrack_qt.main_window as main_window
    seen = {}

    class Dialog:
        """Stands in for the file dialog: records where it started and returns the file to test."""
        answer = ""

        @staticmethod
        def getOpenFileName(parent, caption, folder, filters):
            seen["folder"] = folder
            seen["filters"] = filters
            return Dialog.answer, ""

    real_dialog = main_window.QFileDialog
    main_window.QFileDialog = Dialog
    try:
        w2 = h.window()
        w2.load_video(clip)
        h.pump(lambda: w2.source.has_proxy, 60)
        Dialog.answer = project
        w2.choose_video()
        h.check("Import Video starts in the open video's folder",
                seen["folder"] == os.path.dirname(clip), seen.get("folder", ""))
        h.check("the dialog offers projects as well as videos",
                f"*{project_file.EXTENSION}" in seen["filters"], seen["filters"])
        h.check("choosing a project opens it", w2.project_path == project)

        w2._dirty = False
        w3 = h.window()
        Dialog.answer = clip
        w3.choose_video()
        h.check("with no video open, Import Video starts at home",
                seen["folder"] == os.path.expanduser("~"), seen["folder"])
        h.pump(lambda: w3.source.has_proxy, 60)
        h.check("choosing a video still imports it", w3.source.path == clip and w3.project_path is None)
        w3._dirty = False
        w3.close()
        w2._dirty = False
        w2.close()
    finally:
        main_window.QFileDialog = real_dialog


if __name__ == "__main__":
    h.app()
    for test in (test_project_round_trip, test_other_formats_refused, test_video_start_and_end,
                 test_import_video_or_project):
        print(test.__name__)
        test()
    h.finish()
